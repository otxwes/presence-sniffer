"""Hardware-free device generator (PLAN.md Phase 0).

Simulates a plausible street/venue crowd: devices wander in and out of range,
RSSI fluctuates, occasionally someone walks past fast (high churn). Lets you
build and tune the Ableton mappings before any radio hardware arrives.

In Phase 1 the simulator is swapped for the ESP32 / Pi adapters in sensors/.
"""
from __future__ import annotations

import asyncio
import random
import time
from typing import AsyncIterator

from .events import PresenceEvent, anonymize_id

_AD_NAMES = [
    ("AirPods (someone's)", "hearable"),
    ("WH-1000XM4", "hearable"),
    ("Apple Watch", "wearable"),
    ("Galaxy Watch", "wearable"),
    (None, "smartphone"),
    (None, "laptop"),
]


class DeviceSimulator:
    """Async iterator of plausible PresenceEvents."""

    def __init__(self, seed: int | None = None, max_devices: int = 12) -> None:
        self._rng = random.Random(seed)
        self._max_devices = max_devices
        self._devices: list[dict] = []

    def _spawn(self) -> dict | None:
        if len(self._devices) >= self._max_devices:
            return None
        name, dclass = self._rng.choice(_AD_NAMES)
        # Realistic RSSI: most devices are far, occasional close passerby.
        rssi = self._rng.choices(
            [-max(20, 95 - self._rng.randint(15, 55)), -self._rng.randint(35, 65)],
            weights=[0.25, 0.75],
        )[0]
        return {
            "id": anonymize_id("sim", f"aa:bb:cc:{self._rng.getrandbits(24):06x}"),
            "name": name,
            "device_class": dclass,
            "rssi": rssi,
            "ttl_frames": self._rng.randint(3, 25),
            "band": self._rng.choice(["ble", "2.4g", "5g"]),
        }

    def _tick(self, devices: list[dict]) -> list[PresenceEvent]:
        events = []
        now = time.time()
        for d in devices:
            d["rssi"] += self._rng.uniform(-3, 3)
            d["rssi"] = max(-100.0, min(-20.0, d["rssi"]))
            d["ttl_frames"] -= 1
            events.append(
                PresenceEvent(
                    device_id=d["id"],
                    source="sim",
                    device_class=d["device_class"],
                    rssi=d["rssi"],
                    band=d["band"],
                    name=d["name"],
                    ts=now,
                )
            )
        # drop stale, spawn a couple newcomers
        devices[:] = [d for d in devices if d["ttl_frames"] > 0]
        for _ in range(self._rng.randint(0, 3)):
            if (d := self._spawn()) is not None:
                devices.append(d)
        return events

    async def events(self, interval: float = 0.25) -> AsyncIterator[list[PresenceEvent]]:
        self._devices = [d for d in (self._spawn() for _ in range(4)) if d]
        while True:
            yield self._tick(self._devices)
            await asyncio.sleep(interval)
