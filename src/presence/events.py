"""Core event model for presence-sniffer.

Design rule (from PLAN.md Phase 2): never feed raw device identifiers downstream.
Sensors emit PresenceEvents with hashed ids; the Aggregator folds them into
PresenceSnapshots (density / churn / proximity / RF warmth) which is what the
audio bridge and visualizer consume.
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field, replace
from typing import Optional

# Coarse device classes inferred from BLE advertised names / OUI prefixes.
DEVICE_CLASSES = ("smartphone", "wearable", "hearable", "laptop", "access_point", "unknown")


def _rssi_to_proximity(rssi: float) -> float:
    """Map RSSI (dBm, typically -100..-20) to 0..1 proximity."""
    return max(0.0, min(1.0, (rssi + 100.0) / 80.0))


def anonymize_id(source: str, addr: str) -> str:
    """Deterministic, non-reversible id: sender keeps the raw addr, downstream does not."""
    return hashlib.sha256(f"{source}|{addr}".encode()).hexdigest()[:12]


@dataclass(frozen=True, slots=True)
class PresenceEvent:
    """A single observation of a nearby device."""
    device_id: str                    # anonymized id
    source: str                       # 'wifi', 'ble', 'rf', 'sim'
    device_class: str = "unknown"     # one of DEVICE_CLASSES
    rssi: float = -100.0              # dBm of the strongest frame we saw
    band: str = "2.4g"                # '2.4g', '5g', 'ble', or e.g. '470mhz'
    name: Optional[str] = None        # advertised name (may be None; not identifying)
    ts: float = field(default_factory=time.time)

    @property
    def proximity(self) -> float:
        return _rssi_to_proximity(self.rssi)


@dataclass(slots=True)
class PresenceSnapshot:
    """Aggregated per-tick state consumed by audio / viz. No identities live here."""
    ts: float = field(default_factory=time.time)
    density: int = 0                  # distinct devices seen in the window
    churn: float = 0.0                # new devices per second
    proximity: float = 0.0            # 0..1, proximity of the closest device
    band_balance: float = 0.0         # -1 (all wifi) .. +1 (all ble)
    rf_warmth: float = 0.0            # 0..1, SDR noise-floor above baseline (Phase 1+)
    by_class: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "ts": self.ts,
            "density": self.density,
            "churn": round(self.churn, 2),
            "proximity": round(self.proximity, 3),
            "band_balance": round(self.band_balance, 3),
            "rf_warmth": round(self.rf_warmth, 3),
            "by_class": self.by_class,
        }
