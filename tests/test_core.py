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
