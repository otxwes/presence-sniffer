"""Exhibition mode: derive a single /purity lane from PresenceSnapshots.

Concept (visitor-facing): the room's audio is pristine when the RF
environment is clean — devices off or outside. Any device the sensors hear
degrades purity. This is a *presence* incentive, not an identity penalty:
nothing here knows or shows who.

Scoring
    interference = 0.55*proximity   (closest device dominates audibly)
                 + 0.30*density     (crowd saturation, half-life ramp)
                 + 0.15*churn       (restlessness / new arrivals)
    purity = 1 - interference, smoothed with an asymmetric envelope:
        - fast attack  (0.4s tau)   - walking in degrades immediately
        - slow release (8s tau)     - leaving lets the room *recover*
                                      audibly, rewarding the no-device goal
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

from .events import PresenceSnapshot

DENSITY_SATURATE = 10  # devices at which density term hits 1.0
ATTACK_TAU = 0.4
RELEASE_TAU = 8.0


@dataclass(slots=True)
class PurityScore:
    ts: float = field(default_factory=time.time)
    value: float = 1.0          # 1 pristine .. 0 saturated
    interference: float = 0.0   # the raw inverse, for viz/tuning

    def to_dict(self) -> dict:
        return {"ts": self.ts, "purity": round(self.value, 3),
                "interference": round(self.interference, 3)}


class PurityCalculator:
    """Smoothing + weighting layer over PresenceSnapshot -> PurityScore.

    Deterministic given the same snapshot sequence (clock injected) — same
    pattern as SurveillanceScorer.
    """

    W_PROXIMITY = 0.55
    W_DENSITY = 0.30
    W_CHURN = 0.15

    def __init__(self, clock=time.time) -> None:
        self._clock = clock
        self._last_ts: float | None = None
        self._interference_raw = 0.0
        self._interference = 0.0

    def _capture_interference(self, snap: PresenceSnapshot) -> float:
        """Pure function: a snapshot -> instantaneous interference 0..1."""
        density_term = min(snap.density, DENSITY_SATURATE) / DENSITY_SATURATE
        churn_term = min(snap.churn / 2.0, 1.0)  # 2 arrivals/sec saturates
        return max(0.0, min(1.0, (
            self.W_PROXIMITY * snap.proximity
            + self.W_DENSITY * density_term
            + self.W_CHURN * churn_term
        )))

    async def on_snapshot(self, snap: PresenceSnapshot, bus) -> None:
        now = self._clock()
        self._interference_raw = self._capture_interference(snap)

        if self._last_ts is None:
            dt = 0.5
        else:
            dt = min(2.0, now - self._last_ts)
        self._last_ts = now

        tau = ATTACK_TAU if self._interference_raw > self._interference else RELEASE_TAU
        target = self._interference_raw
        self._interference = target - (target - self._interference) * math.exp(-dt / tau)

        out = PurityScore(
            ts=now,
            value=max(0.0, min(1.0, 1.0 - self._interference)),
            interference=max(0.0, min(1.0, self._interference)),
        )
        await bus.publish("purity", out)

    def reset(self) -> None:
        self._last_ts = None
        self._interference = 0.0


__all__ = ["PurityCalculator", "PurityScore"]
