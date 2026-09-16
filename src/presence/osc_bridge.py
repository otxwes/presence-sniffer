"""OSC bridge: publishes PresenceSnapshots to Ableton / Max for Live over UDP OSC.

Max for Live patch (maxforlive/) receives on port 9090 with this layout:

  /density      <int>     distinct devices in window
  /churn        <float>   new devices per second
  /proximity    <float>   0..1 closest device
  /band_balance <float>   -1 wifi-dominant .. +1 ble-dominant
  /rf_warmth    <float>   0..1 SDR noise floor above baseline (Phase 1+)
  /class/<cls>  <int>     count of that device class in window
  /surveillance_proxy    <float> 0..1 weighted surveillance proxy (Phase 2b)
  /surveillance_raw      <float> 0..1 pre-decay composite (tuning aid)
  /surveillance_cooldown <float> 0..1 remaining cooldown hold
  /purity       <float>   1.0 pristine (clean RF) .. 0.0 saturated (exhibition lane)
  /interference <float>   1.0 - purity, the flip side for viz/mapping
"""
from __future__ import annotations

from pythonosc.udp_client import SimpleUDPClient

from .events import PresenceSnapshot
from .threat import ThreatSnapshot


class OscBridge:
    """Bus subscriber that forwards snapshots + surveillance proxy as OSC messages."""

    def __init__(self, host: str = "127.0.0.1", port: int = 9090) -> None:
        self._client = SimpleUDPClient(host, port)
        self.host = host
        self.port = port

    @staticmethod
    def _f(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
        return max(lo, min(hi, value))

    async def on_snapshot(self, snap: PresenceSnapshot) -> None:
        self._client.send_message("/density", int(snap.density))
        self._client.send_message("/churn", self._f(snap.churn / 10.0))  # 0..1 for macros
        self._client.send_message("/proximity", self._f(snap.proximity))
        self._client.send_message("/band_balance", max(-1.0, min(1.0, snap.band_balance)))
        self._client.send_message("/rf_warmth", self._f(snap.rf_warmth))
        for cls, n in snap.by_class.items():
            if n:
                self._client.send_message(f"/class/{cls}", int(n))

    async def on_threat(self, threat: ThreatSnapshot) -> None:
        """Surveillance proxy lane — confidence-weighted device-class signal,
        never a binary 'person/police' flag (see RESEARCH.md §5)."""
        self._client.send_message("/surveillance_proxy", self._f(threat.score))
        self._client.send_message("/surveillance_raw", self._f(threat.raw))
        self._client.send_message("/surveillance_cooldown", self._f(threat.cooldown))

    async def on_purity(self, purity: "PurityScore") -> None:
        """Exhibition lane: 1.0 = pristine (no devices frustrating the RF
        environment), 0.0 = saturated. Slow-attack/fast-release so visitors
        earn back clean audio by keeping devices away."""
        self._client.send_message("/purity", self._f(purity.value))
        self._client.send_message("/interference", self._f(1.0 - purity.value))
