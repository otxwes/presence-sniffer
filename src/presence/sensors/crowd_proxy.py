"""Crowd-proxy sensor: fuse public/crowdsourced data feeds as bus events.

This does NOT detect people or "police" — it detects signals correlated with
public-safety hardware/activity (deflock.me camera maps, city CAD open data,
ADS-B helicopters, dispatch archives) and emits them as ordinary PresenceEvents
so the aggregator treats them like any other sensor.

Ethical framing (RESEARCH.md §5): output is "device class / event feed with
confidence", never identity. All feeds are consumed through official APIs where
they exist; ToS-respecting access is a hard requirement.
"""
from __future__ import annotations

import dataclasses

from .base import BaseSensor

__all__ = [
    "SignalFeatures",
    "SurveillanceContext",
    "build_feature_stack",
    "SURVEILLANCE_CLASSES",
    "FEAT_ORDER",
    "CrowdProxySensor",
]

# Surveillance-adjacent device classes (added to events.DEVICE_CLASSES).
SURVEILLANCE_CLASSES = ("body_camera", "alpr", "drone", "tracker", "incident")


@dataclasses.dataclass(frozen=True, slots=True)
class SurveillanceContext:
    """External-context hints fused into the signal stack.

    Unknown values stay ``-1.0`` so "missing" stays distinguishable from "no
    hits" — reverent to the detect-with-confidence semantics of RESEARCH.md §5.
    """

    known_alpr_distance_m: float = -1.0
    helicopter_distance_m: float = -1.0
    dispatch_activity: float = -1.0  # 0..1 when fused from dispatch archives


@dataclasses.dataclass(frozen=True, slots=True)
class SignalFeatures:
    """One training/inference row per device-or-event window.

    All fields default to a *distinguishable unknown* (-1 / -1.0) rather than 0
    so that "no observation" never reads as "observed nothing".
    """

    oui_match: int = 0              # events matching surveillance OUIs
    ssid_match: int = 0             # events matching surveillance SSID/name patterns
    surveillance_event_count: int = 0
    rssi_max: float = -101.0        # strongest signal seen in window
    rssi_delta: float = 0.0         # swing of strongest signer (movement proxy)
    mac_persistence: float = -1.0   # 0..1 fraction of window MACs still visible
    band_balance: float = -1.0
    time_of_day_frac: float = -1.0  # 0..1 UTC day fraction
    known_alpr_distance_m: float = -1.0
    helicopter_distance_m: float = -1.0
    dispatch_activity: float = -1.0

    def to_vector(self) -> list[float]:
        return [float(getattr(self, name)) for name in FEAT_ORDER]


# Canonical column order for sklearn LogisticRegression / HistGradientBoosting.
FEAT_ORDER = (
    "oui_match",
    "ssid_match",
    "surveillance_event_count",
    "rssi_max",
    "rssi_delta",
    "mac_persistence",
    "band_balance",
    "time_of_day_frac",
    "known_alpr_distance_m",
    "helicopter_distance_m",
    "dispatch_activity",
)


def build_feature_stack(
    events: list,
    snapshot=None,
    context: SurveillanceContext | None = None,
) -> SignalFeatures:
    """Derive a SignalFeatures row from raw PresenceEvents (+ optional context).

    Pure function — no bus, no I/O — so it is trivially unit-testable and
    reusable by both the live scorer and the offline labeler.
    """
    ctx = context if context is not None else SurveillanceContext()

    # Level-1 lookup counts. OUI matches are RF-hardware observations; crowd
    # feed events (source == "crowd") are counted only as ssid_match/feed
    # signals so a single event is never double-counted.
    oui_match = sum(
        1 for e in events if e.source != "crowd" and e.device_class in SURVEILLANCE_CLASSES
    )
    ssid_match = sum(
        1 for e in events
        if e.source == "crowd" and e.device_class in SURVEILLANCE_CLASSES
    )
    surveillance_event_count = oui_match + ssid_match

    rssi_values = [e.rssi for e in events]
    rssi_max = max(rssi_values) if rssi_values else -101.0
    # Movement proxy uses only surveillance-adjacent physical observations —
    # mixing in feed RSSI placeholders or unrelated devices would corrupt the
    # delta with noise.
    surv_rssi = [
        e.rssi for e in events
        if e.source != "crowd" and e.device_class in SURVEILLANCE_CLASSES
    ]
    rssi_delta = (max(surv_rssi) - min(surv_rssi)) if len(surv_rssi) > 1 else 0.0

    band_balance = getattr(snapshot, "band_balance", -1.0)

    # Naive persistence: fraction of events still "fresh" relative to the
    # newest event in the window. The Aggregator refines this; scaffold is
    # deterministic and window-source-of-truth constant is below.
    WINDOW_SECONDS = 6.0  # keep in sync with Aggregator.WINDOW_SECONDS
    if events:
        now = max(e.ts for e in events)
        mac_persistence = sum(1 for e in events if (now - e.ts) <= WINDOW_SECONDS) / len(events)
        time_of_day_frac = (now % 86400) / 86400.0  # UTC day fraction
    else:
        mac_persistence = -1.0
        time_of_day_frac = -1.0

    return SignalFeatures(
        oui_match=oui_match,
        ssid_match=ssid_match,
        surveillance_event_count=surveillance_event_count,
        rssi_max=rssi_max,
        rssi_delta=rssi_delta,
        mac_persistence=mac_persistence,
        band_balance=band_balance,
        time_of_day_frac=time_of_day_frac,
        known_alpr_distance_m=ctx.known_alpr_distance_m,
        helicopter_distance_m=ctx.helicopter_distance_m,
        dispatch_activity=ctx.dispatch_activity,
    )


class CrowdProxySensor(BaseSensor):
    """Adapter for crowd/feed data sources (CAD JSON, ADS-B REST, etc.).

    Hardware adapters speak pulse-serial; crowd feeds speak REST/JSON and only
    deliver event occurrences with timestamps, wrapped in PresenceEvents by the
    feed adapters. The bus stays the single sink, one adapter per backend.
    """

    source = "crowd"

    # Feeds to implement, in confidence order (RESEARCH.md §5):
    #  1. adsb (OpenSky / ADSB Exchange): helicopter proximity
    #  2. deflock: known ALPR locations -> SurveillanceContext priors
    #  3. city CAD Socrata JSON: incident PresenceEvents w/ feed timestamp
    #  4. Broadcastify archives: weak labels only; never realtime fusion

    def __init__(self, bus) -> None:
        super().__init__(bus)
        self.feeds: dict[str, object] = {}

    async def run(self) -> None:  # pragma: no cover - feeds wired in later phase
        raise NotImplementedError(
            "CrowdProxySensor is a scaffold: wire a feed adapter (adsb first)."
        )

