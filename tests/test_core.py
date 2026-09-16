"""Unit tests for the Phase 0 core: event model, bus, simulator, aggregator folding."""
import asyncio
import time

import pytest

from presence.bus import EventBus
from presence.events import PresenceEvent, PresenceSnapshot, anonymize_id
from presence.simulator import DeviceSimulator


def test_anonymize_id_is_deterministic_and_nonreversible():
    a = anonymize_id("wifi", "aa:bb:cc:11:22:33")
    b = anonymize_id("wifi", "aa:bb:cc:11:22:33")
    c = anonymize_id("ble", "aa:bb:cc:11:22:33")
    assert a == b and a != c and len(a) == 12
    assert "aa:bb:cc" not in a


def test_rssi_to_proximity_bounds():
    assert PresenceEvent("x", "sim", rssi=-100).proximity == 0.0
    assert PresenceEvent("x", "sim", rssi=-20).proximity == 1.0
    assert PresenceEvent("x", "sim", rssi=-60).proximity == pytest.approx(0.5)


def test_snapshot_math():
    now = time.time()
    snap = PresenceSnapshot(ts=now, density=3, churn=0.5, proximity=0.8,
                            band_balance=-0.5, by_class={"smartphone": 2, "hearable": 1})
    d = snap.to_dict()
    assert d["density"] == 3
    assert d["churn"] == 0.5
    assert d["by_class"] == {"smartphone": 2, "hearable": 1}


def test_bus_publishes_to_subscribers():
    bus = EventBus()
    got: list = []

    async def collect(e):
        got.append(e)

    async def scenario():
        bus.subscribe("event", collect)
        ev = PresenceEvent(device_id="abc", source="sim")
        await bus.publish("event", ev)
        return ev

    ev = asyncio.run(scenario())
    assert got == [ev]


def test_simulator_produces_plausible_events():
    sim = DeviceSimulator(seed=42)

    async def scenario():
        async for batch in sim.events():
            return batch

    batch = asyncio.run(scenario())
    assert len(batch) >= 1
    for ev in batch:
        assert ev.source == "sim"
        assert -100.0 <= ev.rssi <= -20.0
        assert 0.0 <= ev.proximity <= 1.0
        assert ev.device_class


def test_surveillance_device_classes_are_registered():
    from presence.events import DEVICE_CLASSES

    for cls in ("body_camera", "alpr", "drone", "tracker", "incident"):
        assert cls in DEVICE_CLASSES


def test_signal_feature_stack_counts_and_unknowns():
    from presence.sensors.crowd_proxy import (
        FEAT_ORDER,
        SignalFeatures,
        build_feature_stack,
    )
    from presence.sensors.crowd_proxy import SurveillanceContext

    base_ts = 1_757_971_200  # arbitrary epoch seconds
    evs = [
        PresenceEvent("d1", "wifi", device_class="body_camera", rssi=-40, ts=base_ts),
        PresenceEvent("d2", "wifi", device_class="body_camera", rssi=-60, ts=base_ts - 5),
        PresenceEvent("d3", "crowd", device_class="incident", rssi=-100, ts=base_ts - 1),
        PresenceEvent("d4", "wifi", device_class="smartphone", rssi=-35, ts=base_ts - 2),
    ]
    feats = build_feature_stack(evs, context=SurveillanceContext(
        known_alpr_distance_m=120.0,
        helicopter_distance_m=2400.0,
        dispatch_activity=0.4,
    ))
    assert feats.oui_match == 2
    assert feats.ssid_match == 1
    assert feats.surveillance_event_count == 3
    assert feats.rssi_max == -35.0
    assert feats.rssi_delta == pytest.approx(-40.0 - (-60.0))  # body cams only
    assert 0.0 <= feats.mac_persistence <= 1.0
    assert 0.0 <= feats.time_of_day_frac <= 1.0
    assert feats.known_alpr_distance_m == 120.0
    assert feats.dispatch_activity == 0.4

    vec = feats.to_vector()
    assert len(vec) == len(FEAT_ORDER)


def test_signal_feature_stack_empty_is_all_unknowns():
    from presence.sensors.crowd_proxy import build_feature_stack

    feats = build_feature_stack([])
    assert feats.surveillance_event_count == 0
    assert feats.rssi_max == -101.0
    assert feats.mac_persistence == -1.0
    assert feats.band_balance == -1.0
    assert feats.time_of_day_frac == -1.0
    assert feats.known_alpr_distance_m == -1.0
    assert feats.helicopter_distance_m == -1.0
    assert feats.dispatch_activity == -1.0


def test_crowd_proxy_sensor_is_bus_wired_but_unimplemented():
    import asyncio

    from presence.bus import EventBus
    from presence.sensors.crowd_proxy import CrowdProxySensor

    async def scenario():
        sensor = CrowdProxySensor(EventBus())
        try:
            await sensor.run()
            raise AssertionError("should have raised NotImplementedError")
        except NotImplementedError:
            pass

    asyncio.run(scenario())

    from presence.aggregator import Aggregator

    async def scenario():
        bus = EventBus()
        agg = Aggregator(bus)
        ev1 = PresenceEvent("d1", "sim", rssi=-40)
        ev2 = PresenceEvent("d2", "sim", rssi=-90)
        await agg.on_event(ev1)
        await agg.on_event(ev2)
        await agg.on_event(ev1)  # duplicate should not bump churn twice
        return agg, ev1

    agg, ev1 = asyncio.run(scenario())
    snap = agg._make_snapshot()
    assert snap.density == 2
    assert snap.churn == pytest.approx(2 / Aggregator.WINDOW_SECONDS)
    assert snap.proximity == pytest.approx(ev1.proximity)


# --- Phase 2b: SurveillanceScorer -------------------------------------------


def _feed_and_tick(clock, scorer, events_per_tick, n_ticks):
    """Advance the fake clock, publish event batches, tick the scorer.

    Events are re-stamped with the fake clock so window pruning behaves
    as it does in production (real clock == event ts).
    """
    import asyncio
    from dataclasses import replace

    async def scenario():
        for evs in events_per_tick:
            clock.advance(0.5)
            for ev in evs:
                await scorer.on_event(replace(ev, ts=clock()))
            await scorer.on_snapshot(None)

    asyncio.run(scenario())


def _make_scorer():
    """Scorer + fake clock (advances in TICK_SECONDS steps)."""
    from presence.bus import EventBus
    from presence.threat import SurveillanceScorer

    class FakeClock:
        def __init__(self):
            self.t = 1_000_000.0

        def __call__(self):
            return self.t

        def advance(self, dt):
            self.t += dt

    received = []

    async def _capture(t):
        received.append(t)

    bus = EventBus()
    bus.subscribe("threat", _capture)
    clock = FakeClock()
    scorer = SurveillanceScorer(bus, clock=clock)
    return clock, scorer, received


def test_scorer_zero_when_no_surveillance_events():
    clock, scorer, received = _make_scorer()
    ds = lambda: PresenceEvent("d", "sim", device_class="smartphone", rssi=-30)
    _feed_and_tick(clock, scorer, [[ds(), ds()], [ds()]], 2)
    assert all(r.score == 0.0 and r.raw == 0.0 and not r.contributing for r in received)


def test_scorer_rises_with_close_body_camera_and_saturates_density():
    clock, scorer, received = _make_scorer()
    bc = lambda rid, rssi: PresenceEvent(rid, "wifi", device_class="body_camera", rssi=rssi)
    events = [[bc("a", -35), bc("b", -40), bc("c", -50), bc("d", -60), bc("e", -70)]]
    _feed_and_tick(clock, scorer, events, 1)
    snap = received[-1]
    w = scorer.weights
    expected = w.proximity * bc("x", -35).proximity + w.density * 1.0
    assert snap.raw == pytest.approx(expected)
    assert snap.score == pytest.approx(snap.raw)
    assert snap.contributing == {"body_camera": 5}


def test_scorer_holds_ceiling_through_cooldown_then_decays():
    import math

    from presence.threat import SurveillanceScorer

    clock, scorer, received = _make_scorer()
    spike = [PresenceEvent("a", "wifi", device_class="alpr", rssi=-25)]  # prox 0.9375
    _feed_and_tick(clock, scorer, [spike], 1)
    peak = received[-1].score
    assert peak >= scorer.TRIGGER
    # mid-cooldown (10s in): ceiling held, cooldown fraction still live
    _feed_and_tick(clock, scorer, [[] for _ in range(20)], 20)
    assert received[-1].score == pytest.approx(peak)
    assert received[-1].cooldown == pytest.approx((12.0 - 10.0) / 12.0)
    # after cooldown: exponential decay at exp(-0.5/TAU) per tick
    _feed_and_tick(clock, scorer, [[] for _ in range(10)], 10)  # 5s past expiry
    tail = received[-10:]
    assert tail[-1].score < tail[0].score, "must decay once cooldown expires"
    for prev, cur in zip(tail, tail[1:]):
        if prev.score > scorer.TRIGGER and prev.cooldown == 0.0:
            assert cur.score == pytest.approx(prev.score * math.exp(-0.5 / SurveillanceScorer.TAU), rel=1e-6)


def test_scorer_is_deterministic():
    clock, scorer, received = _make_scorer()
    events = [
        [PresenceEvent("h", "wifi", device_class="drone", rssi=-45)],
        [],
        [PresenceEvent("t", "wifi", device_class="tracker", rssi=-55)],
    ]
    _feed_and_tick(clock, scorer, [events[0] + events[2]], 1)
    first = received[-1].to_dict()

    clock2, scorer2, received2 = _make_scorer()
    _feed_and_tick(clock2, scorer2, [events[0] + events[2]], 1)
    second = received2[-1].to_dict()

    first.pop("ts"), second.pop("ts")
    assert first == second


def test_scorer_publishes_and_resets():
    clock, scorer, received = _make_scorer()
    _feed_and_tick(
        clock,
        scorer,
        [[PresenceEvent("h", "wifi", device_class="drone", rssi=-35)]],
        1,
    )
    assert received, "scorer must publish a ThreatSnapshot per tick"
    assert 0.0 <= received[-1].score <= 1.0
    scorer.reset()
    assert scorer._held == 0.0 and not scorer._events

