"""Nooelec/RTL-SDR RF-environment sensor.

Runs ``rtl_power`` on a band, parses the CSV, and publishes an ``rf`` reading
with ``rf_warmth`` in 0..1. The metric is the fraction of scanned bins more
than 6 dB above the band median (occupancy), scaled ×4 and clamped. This is a
coarse "RF weather" signal, not a calibrated spectrum measurement.

The Nooelec is the working SDR (Stage 2b closed 2026-11-08). The aggregator
wires this in with ``--rf-warmth``; the existing ``PresenceSnapshot.rf_warmth``
field and ``/rf_warmth`` OSC address carry the result.
"""
from __future__ import annotations

import asyncio
import logging
import os
import statistics
import subprocess
import tempfile
import time
from dataclasses import dataclass
from typing import Optional

from ..bus import EventBus
from .base import BaseSensor

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RfReading:
    """One rtl_power scan summarized into a 0..1 warmth value."""

    ts: float
    warmth: float
    floor: float
    peak: float
    occupancy: float


def parse_power_csv(path: str) -> Optional[RfReading]:
    """Parse an rtl_power CSV into floor/peak/occupancy/warmth, or None."""
    values: list[float] = []
    try:
        with open(path) as fh:
            for line in fh:
                parts = [p.strip() for p in line.split(",")]
                if len(parts) < 7:
                    continue
                for raw in parts[6:]:
                    if not raw:
                        continue
                    try:
                        values.append(float(raw))
                    except ValueError:
                        continue
    except OSError:
        return None

    if not values:
        return None
    floor = statistics.median(values)
    peak = max(values)
    occupancy = sum(1 for v in values if v > floor + 6.0) / len(values)
    warmth = min(1.0, occupancy * 4.0)
    return RfReading(ts=time.time(), warmth=warmth, floor=floor, peak=peak,
                     occupancy=occupancy)


class RfSensor(BaseSensor):
    """Kept for the sensor vocabulary; the concrete implementation is below."""

    source = "rf"


class RfWarmthSensor(BaseSensor):
    """Periodically scans a band with rtl_power and publishes rf readings."""

    source = "rf"

    def __init__(self, bus: EventBus, band: str = "88M:108M:200k",
                 interval: float = 2.0, gain: int = 42,
                 bin: str = "rtl_power") -> None:
        super().__init__(bus)
        self.band = band
        self.interval = interval
        self.gain = gain
        self.bin = bin

    async def run(self) -> None:
        while True:
            started = time.monotonic()
            tmp = tempfile.NamedTemporaryFile(
                prefix="presence-rf-", suffix=".csv", delete=False)
            path = tmp.name
            tmp.close()
            try:
                await asyncio.to_thread(
                    subprocess.run,
                    [self.bin, "-f", self.band, "-i", "1",
                     "-e", str(max(1, int(self.interval))),
                     "-g", str(self.gain), path],
                    capture_output=True,
                    timeout=self.interval + 15.0,
                )
                reading = parse_power_csv(path)
                if reading is not None:
                    await self.bus.publish("rf", reading)
                    log.info("rf_warmth %.2f (floor %.1f, peak %.1f)",
                             reading.warmth, reading.floor, reading.peak)
            except (OSError, subprocess.SubprocessError) as exc:
                log.warning("rtl_power failed: %s", exc)
            finally:
                try:
                    os.unlink(path)
                except OSError:
                    pass
            elapsed = time.monotonic() - started
            await asyncio.sleep(max(0.0, self.interval - elapsed))
