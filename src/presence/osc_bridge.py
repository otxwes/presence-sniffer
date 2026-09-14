"""OSC bridge: publishes PresenceSnapshots to Ableton / Max for Live over UDP OSC.

Max for Live patch (maxforlive/) receives on port 9090 with this layout:

  /density      <int>     distinct devices in window
  /churn        <float>   new devices per second
  /proximity    <float>   0..1 closest device
  /band_balance <float>   -1 wifi-dominant .. +1 ble-dominant
  /rf_warmth    <float>   0..1 SDR noise floor above baseline (Phase 1+)
"""
from __future__ import annotations

from pythonosc.udp_client import SimpleUDPClient

from .events import PresenceSnapshot


class OscBridge:
    """Bus subscriber that forwards snapshots as OSC messages."""

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
