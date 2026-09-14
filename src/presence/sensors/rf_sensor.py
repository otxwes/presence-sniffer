"""Phase 1 stub: RTL-SDR/HackRF broadband noise-floor monitor.

Plan: block-FFT the sampled spectrum across bands of interest, compute RMS
power per band, subtract a slow rolling baseline -> PresenceSnapshot.rf_warmth
(0..1 above baseline).
"""
from __future__ import annotations

from .base import BaseSensor


class RfSensor(BaseSensor):
    source = "rf"
