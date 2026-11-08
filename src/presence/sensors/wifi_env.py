"""ALFA WiFi-environment sensor.

The ALFA (``wlan1``, monitor mode) is a **WiFi environment** sensor, not a
presence sensor. A root capture process counts:

* ``aps``  — unique AP BSSIDs seen in the rolling window (beacons)
* ``busy`` — non-beacon 802.11 frames/second in the rolling window

It sends ``{"ts": ..., "aps": 18, "busy": 27.4}`` to localhost UDP; the
aggregator's :class:`UdpWifiEnvSensor` turns those into ``environment`` bus
events. The counts contain no client identities; AP BSSIDs never leave the
capture process.

Run the capture as root (Scapy raw sockets + ``iw`` channel changes)::

    sudo ~/.venvs/presence/bin/python -m presence.sensors.wifi_env \
        --iface wlan1 --udp-port 9998 --exclude 88:a2:9e:6a:5a:94

The ALFA must already be in monitor mode; restart ``sniffer-monitor`` after a
replug. The capture hops 5 GHz channels by default.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import socket
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Optional

from ..bus import EventBus
from .base import BaseSensor

log = logging.getLogger(__name__)

APS_WINDOW = 10.0
BUSY_WINDOW = 5.0
CHANNELS_5G = (
    36, 40, 44, 48, 100, 104, 108, 112, 116, 120, 124, 128, 132, 136, 140,
    144, 149, 153, 157, 161, 165,
)


@dataclass(frozen=True, slots=True)
class WifiEnvironment:
    """One ALFA environment reading: AP count + non-beacon frame rate."""

    ts: float
    aps: int
    busy: float


def parse_env_line(line: str) -> Optional[WifiEnvironment]:
    """Parse one UDP JSON line into a WifiEnvironment, or None if invalid."""
    try:
        msg = json.loads(line)
    except (TypeError, ValueError):
        return None
    if not isinstance(msg, dict):
        return None

    aps = msg.get("aps")
    if isinstance(aps, bool) or not isinstance(aps, int) or aps < 0:
        return None

    busy = msg.get("busy")
    if isinstance(busy, bool) or not isinstance(busy, (int, float)) or busy < 0:
        return None

    ts = msg.get("ts", time.time())
    if isinstance(ts, bool) or not isinstance(ts, (int, float)):
        return None

    return WifiEnvironment(ts=float(ts), aps=aps, busy=float(busy))


class UdpWifiEnvSensor(BaseSensor):
    """Receives environment JSON from the root ALFA capture over localhost UDP."""

    source = "wifi-env"

    def __init__(self, bus: EventBus, host: str = "127.0.0.1",
                 port: int = 9998) -> None:
        super().__init__(bus)
        self.host = host
        self.port = port

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.host, self.port))
        sock.setblocking(False)
        log.info("wifi-env sensor listening on %s:%s", self.host, self.port)
        try:
            while True:
                data, _ = await loop.sock_recvfrom(sock, 65535)
                env = parse_env_line(data.decode("utf-8", "replace"))
                if env is not None:
                    await self.bus.publish("environment", env)
        finally:
            sock.close()


def _default_exclude() -> set[str]:
    try:
        with open("/sys/class/net/wlan0/address") as fh:
            return {fh.read().strip().lower()}
    except OSError:
        return set()


def run_capture(iface: str = "wlan1", udp_host: str = "127.0.0.1",
                udp_port: int = 9998, channels: tuple[int, ...] = CHANNELS_5G,
                dwell: float = 0.35, exclude: Optional[set[str]] = None,
                aps_window: float = APS_WINDOW,
                busy_window: float = BUSY_WINDOW) -> None:
    """Capture beacons/non-beacon frames and send environment JSON over UDP."""
    from scapy.all import AsyncSniffer, Dot11, Dot11Beacon  # local: root-only path

    info = subprocess.run(["/usr/sbin/iw", "dev", iface, "info"],
                          capture_output=True, text=True)
    if "type monitor" not in info.stdout:
        raise SystemExit(f"{iface} is not in monitor mode; restart sniffer-monitor")

    exclude = exclude or set()
    lock = threading.Lock()
    aps: deque[tuple[float, str]] = deque()
    frames: deque[float] = deque()
    stop = threading.Event()

    def handle(pkt) -> None:
        if not pkt.haslayer(Dot11):
            return
        now = time.monotonic()
        dot11 = pkt[Dot11]
        if pkt.haslayer(Dot11Beacon):
            bssid = (dot11.addr3 or "").lower()
            if bssid:
                with lock:
                    aps.append((now, bssid))
            return
        addresses = (dot11.addr1, dot11.addr2, dot11.addr3)
        if any(a and a.lower() in exclude for a in addresses):
            return
        with lock:
            frames.append(now)

    def hop() -> None:
        while not stop.is_set():
            for ch in channels:
                if stop.is_set():
                    break
                res = subprocess.run(
                    ["/usr/sbin/iw", "dev", iface, "set", "channel", str(ch)],
                    capture_output=True, text=True)
                if res.returncode != 0:
                    log.warning("channel %s failed: %s", ch, res.stderr.strip()[:80])
                time.sleep(dwell)

    sniffer = AsyncSniffer(iface=iface, prn=handle, store=False)
    sniffer.start()
    hop_thread = threading.Thread(target=hop, daemon=True)
    hop_thread.start()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        while True:
            time.sleep(1.0)
            now = time.monotonic()
            with lock:
                while aps and now - aps[0][0] > aps_window:
                    aps.popleft()
                while frames and now - frames[0] > busy_window:
                    frames.popleft()
                aps_count = len({b for _, b in aps})
                busy = len(frames) / busy_window
            payload = json.dumps({"ts": time.time(), "aps": aps_count,
                                  "busy": round(busy, 2)})
            sock.sendto(payload.encode("utf-8"), (udp_host, udp_port))
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        try:
            sniffer.stop()
        except Exception:  # noqa: BLE001 - shutdown best effort
            pass
        hop_thread.join(timeout=2.0)
        sock.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="ALFA WiFi-environment capture")
    parser.add_argument("--iface", default="wlan1")
    parser.add_argument("--udp-host", default="127.0.0.1")
    parser.add_argument("--udp-port", type=int, default=9998)
    parser.add_argument("--channels", default=",".join(str(c) for c in CHANNELS_5G))
    parser.add_argument("--dwell", type=float, default=0.35)
    parser.add_argument("--exclude", default="",
                        help="comma-separated MACs to ignore (default: wlan0 MAC)")
    parser.add_argument("--aps-window", type=float, default=APS_WINDOW)
    parser.add_argument("--busy-window", type=float, default=BUSY_WINDOW)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(name)s %(message)s")
    channels = tuple(int(x) for x in args.channels.split(",") if x.strip())
    exclude = {x.strip().lower() for x in args.exclude.split(",") if x.strip()}
    if not exclude:
        exclude = _default_exclude()
    log.info("wifi-env capture iface=%s channels=%s exclude=%s",
             args.iface, len(channels), sorted(exclude))
    run_capture(args.iface, args.udp_host, args.udp_port, channels,
                args.dwell, exclude, args.aps_window, args.busy_window)


if __name__ == "__main__":
    main()
