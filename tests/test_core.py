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


def test_aggregator_folds_events_into_snapshot():
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
