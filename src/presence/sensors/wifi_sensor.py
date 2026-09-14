"""Phase 1 stub: Scapy monitor-mode probe-request capture.

On the Pi (with an AR9271-class monitor-mode dongle):

    sudo airmon-ng start wlan1          # or: ip link set wlan1mon up
    python -m presence.sensors.wifi_sensor --iface wlan1mon

Implementation sketch: sniff(PROBE_REQUEST), extract addr2, signal_dbm, publish
PresenceEvent(source='wifi', rssi=signal). Identifiers are anonymized before
publish (see events.anonymize_id).
"""
from __future__ import annotations

import argparse

from .base import BaseSensor


class WifiSensor(BaseSensor):
    source = "wifi"


def main() -> None:
    parser = argparse.ArgumentParser(description="Wi-Fi probe-request sensor")
    parser.add_argument("--iface", default="wlan1mon")
    args = parser.parse_args()
    print(f"wifi sensor stub - Phase 1 will capture probe requests on {args.iface}")


if __name__ == "__main__":
    main()
