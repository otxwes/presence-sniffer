"""Phase 2b: hand-rolled surveillance_proxy scorer (deterministic, testable).

Weighted composite over this window's surveillance-adjacent signals:
    score = w.proximity * max_proximity
          + w.density   * min(count, 4) / 4
          + w.dispatch  * local_dispatch_activity
          + w.helo      * airborne_proximity

Decay: held score *= exp(-dt / TAU). Spikes at or above TRIGGER freeze their
ceiling for COOLDOWN_SECONDS so a single passing flyer can't retrigger
endlessly. Emits a ThreatSnapshot on the "threat" bus channel per snapshot
tick — consumed by OSC (/surveillance_proxy, /surveillance_raw,
/surveillance_cooldown) and the visualizer. No raw device identifiers ever
pass through here, per PLAN.md's design rule.
"""
from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field

from .events import PresenceEvent

_log = logging.getLogger(__name__)

# Proxy classes that feed the score; everything else (crowd/signals) is
# summarized in PresenceSnapshot.by_class but never scored here.
SURVEILLANCE_CLASSES = frozenset(
    {"body_camera", "alpr", "drone", "tracker", "incident"}
)
CONFIDENCE_CLASSES = SURVEILLANCE_CLASSES  # scoring vocabulary == confidence vocabulary


@dataclass(slots=True)
class ThreatWeights:
    """Eye-spy-inspired weighted heuristic; tunable live without restart."""
    proximity: float = 0.45
    density: float = 0.25
    dispatch: float = 0.15
    helo: float = 0.15



@dataclass(slots=True)
class ThreatSnapshot:
    """Audio/viz-facing output of the surveillance proxy scorer."""
    ts: float = field(default_factory=time.time)
    score: float = 0.0            # 0..1 weighted, decayed, cooldown-held
    raw: float = 0.0              # pre-decay composite (debug/tuning)
    cooldown: float = 0.0         # 0..1 remaining cooldown fraction
    contributing: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "ts": self.ts,
            "score": round(self.score, 3),
            "raw": round(self.raw, 3),
            "cooldown": round(self.cooldown, 3),
            "contributing": dict(self.contributing),
        }


class SurveillanceScorer:
    """Stateful, deterministic scorer: same events in, same scores out.

    Wire-up (mirrors the Aggregator's bus pattern):
        scorer = SurveillanceScorer(bus)
        bus.subscribe("event", scorer.on_event)        # fold per-window state
        bus.subscribe("snapshot", scorer.on_snapshot)  # publish per tick
    """

    WINDOW_SECONDS = 6.0   # keep in sync with Aggregator.WINDOW_SECONDS
    TICK_SECONDS = 0.5     # keep in sync with aggregator.SNAPSHOT_INTERVAL
    TAU = 6.0              # exponential decay tau (s)
    TRIGGER = 0.45         # raw composite that arms the cooldown
    COOLDOWN_SECONDS = 12.0
    DENSITY_SATURATE = 4   # >4 concurrent signers saturates the density term

    def __init__(self, bus, weights: ThreatWeights | None = None, clock=time.time) -> None:
        self._bus = bus
        self.weights = weights or ThreatWeights()
        self._clock = clock  # injectable for deterministic tests
        self._events: list[PresenceEvent] = []
        self._held = 0.0
        self._cooldown_until = 0.0
        self._last_tick: float | None = None

    async def on_event(self, event: PresenceEvent) -> None:
        if event.device_class in SURVEILLANCE_CLASSES:
            self._events.append(event)

    def _raw_composite(self, now: float) -> tuple[float, dict[str, int]]:
        fresh = [e for e in self._events if now - e.ts <= self.WINDOW_SECONDS]
        self._events = fresh
        contributing: dict[str, int] = {}
        for e in fresh:
            contributing[e.device_class] = contributing.get(e.device_class, 0) + 1
        if not fresh:
            return 0.0, contributing

        w = self.weights
        proximity_term = max(e.proximity for e in fresh)
        density_term = min(len(fresh), self.DENSITY_SATURATE) / self.DENSITY_SATURATE
        # In-window incident events with placeholder-strong RSSI mean the
        # crowd feed marks dispatch activity co-located with us right now.
        dispatch_term = 1.0 if any(
            e.device_class == "incident" and e.rssi > -40 for e in fresh
        ) else 0.0
        helo_term = proximity_term if any(e.device_class == "drone" for e in fresh) else 0.0

        composite = (
            w.proximity * proximity_term
            + w.density * density_term
            + w.dispatch * dispatch_term
            + w.helo * helo_term
        )
        return max(0.0, min(1.0, composite)), contributing

    async def on_snapshot(self, _snap) -> None:
        """Tick-driven: compute, decay-or-hold through cooldown, publish."""
        now = self._clock()
        raw, contributing = self._raw_composite(now)
        dt = self.TICK_SECONDS if self._last_tick is None else min(2.0, now - self._last_tick)
        self._last_tick = now

        cooldown = 0.0
        if raw >= self.TRIGGER and raw > self._held:
            self._held = raw
            self._cooldown_until = now + self.COOLDOWN_SECONDS
        elif now < self._cooldown_until:
            cooldown = (self._cooldown_until - now) / self.COOLDOWN_SECONDS
            # hold (no decay) — the spike ceiling persists through cooldown
        else:
            self._held = max(raw, self._held * math.exp(-dt / self.TAU))

        out = ThreatSnapshot(
            ts=now,
            score=max(0.0, min(1.0, self._held)),
            raw=raw,
            cooldown=max(0.0, min(1.0, cooldown)),
            contributing=contributing,
        )
        await self._bus.publish("threat", out)

    def reset(self) -> None:
        self._events.clear()
        self._held = 0.0
        self._cooldown_until = 0.0
        self._last_tick = None


__all__ = [
    "SurveillanceScorer",
    "ThreatSnapshot",
    "ThreatWeights",
    "SURVEILLANCE_CLASSES",
    "CONFIDENCE_CLASSES",
]
