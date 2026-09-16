"""Stress-test the pipeline end-to-end: jam the bus with adversarial event
patterns and print what the aggregator + scorer actually output.

Scenarios:
  flash    - 40 devices appear in one tick (flash crowd / stadium door)
  churn    - 12 new devices per second sustained (anonymized MAC rotation)
  spike    - 6 body cameras at RSSI -30 (max score + cooldown hold)
  flyer    - alpr spike every 4s (cooldown repeater - must NOT stack)
  fluft    - 200 events in a single tick (flooding / malformed burst)

Usage: .venv/bin/python scripts/stress.py [scenario]
"""
from __future__ import annotations

import asyncio
import random
import sys

from presence.bus import EventBus
from presence.events import PresenceEvent, anonymize_id
from presence.threat import SurveillanceScorer, ThreatSnapshot

MAC = lambda i: anonymize_id("stress", f"aa:{i:02x}:bb")


def ev(cls, rssi, mac, ts):
    return PresenceEvent(mac, "stress", device_class=cls, rssi=rssi, ts=ts)


async def run(name: str) -> None:
    rng = random.Random(7)
    bus = EventBus()
    threats: list[ThreatSnapshot] = []

    async def capture(t: ThreatSnapshot) -> None:
        threats.append(t)

    bus.subscribe("threat", capture)
    scorer = SurveillanceScorer(bus)
    clock = {"t": 0.0}
    scorer._clock = lambda: clock["t"]

    print(f"--- {name} ---")

    if name == "flash":
        # 40 devices materialize at once; scorer must stay 0 (no surveillance
        # classes) while per-tick state must not blow up.
        batch = [ev("smartphone", rng.randint(-90, -30), MAC(i), clock["t"]) for i in range(40)]
        for e in batch:
            await scorer.on_event(e)
        await scorer.on_snapshot(None)
        print("  threat (must be raw=0, no surveillance classes):", threats[-1].to_dict())
    elif name == "churn":
        # 12 fresh MACs per second for 10s (randomized/anonymized rotation).
        for _ in range(10):
            clock["t"] += 1.0
            batch = [ev("wearable", -55, MAC(rng.getrandbits(32)), clock["t"]) for _ in range(12)]
            for e in batch:
                await scorer.on_event(e)
            await scorer.on_snapshot(None)
        print("  threat (must be raw=0):", threats[-1].to_dict())
    elif name == "spike":
        batch = [ev("body_camera", -30, MAC(i), clock["t"]) for i in range(6)]
        for e in batch:
            await scorer.on_event(e)
        await scorer.on_snapshot(None)
        print("  threat at t=0 (peak):", threats[-1].to_dict())
        for _ in range(30):  # 15s of silence - cooldown then decay
            clock["t"] += 0.5
            await scorer.on_snapshot(None)
        print("  threat at t=15s:", threats[-1].to_dict())
    elif name == "flyer":
        # An ALPR spikes every 4s - the 12s cooldown must swallow intermediates.
        for _ in range(4):
            clock["t"] += 4.0
            await scorer.on_event(ev("alpr", -25, MAC(1), clock["t"]))
            for _ in range(8):
                clock["t"] += 0.5
                await scorer.on_snapshot(None)
        scores = [round(t.score, 3) for t in threats[-24:]]
        print("  last 12s of scores:", scores)
        print("  max ceiling:", max(scores), "- must never exceed the single spike peak")
    elif name == "fluft":
        # 200 events in one tick - throughput budget check.
        batch = [ev("drone", -35, MAC(i), clock["t"]) for i in range(200)]
        import time as time
        t0 = time.perf_counter()
        for e in batch:
            await scorer.on_event(e)
        await scorer.on_snapshot(None)
        ms = (time.perf_counter() - t0) * 1000.0
        print(f"  200 events + snapshot in {ms:.1f} ms -> raw={threats[-1].raw:.3f}")


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "spike"
    asyncio.run(run(name))
