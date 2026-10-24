"""Serial adapter for the ESP32 BLE advertisement scanner (board 2).

The firmware emits one JSON object per unique advertiser per 1 s scan window:

    {"ts_ms": 12345, "mac": "aa:bb:cc:dd:ee:ff", "rssi": -79, "name": "iPhone"}

``name`` is null unless the advertised name fits the primary advertising
packet (passive scan receives no scan-response payloads). Heartbeats
(``{"hb": ...}``) and boot/ready lines carry no ``mac`` and are dropped here.
BLE randomized (RPA) addresses are the norm; whatever address the radio saw is
anonymized. Raw MACs never leave this boundary: the published
``PresenceEvent`` carries only the anonymized ``device_id``.

Usage (on the machine with the ESP32 plugged in):

    python -m presence.sensors.ble_sensor --port /dev/ttyACM1

``--port`` also accepts pyserial URLs such as ``socket://host:5555``.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import time
from typing import Optional

from ..bus import EventBus
from ..events import PresenceEvent, anonymize_id
from .base import BaseSensor

log = logging.getLogger(__name__)

_MAC_RE = re.compile(r"^[0-9a-f]{2}(?::[0-9a-f]{2}){5}$")


class BleSensor(BaseSensor):
    """Passive BLE advertisement capture via an ESP32 scanner board."""

    source = "ble"


def parse_ble_line(line: str) -> Optional[PresenceEvent]:
    """Parse one firmware line into a PresenceEvent, or None if invalid."""
    try:
        msg = json.loads(line)
    except (TypeError, ValueError):
        return None
    if not isinstance(msg, dict):
        return None

    mac = msg.get("mac")
    if not isinstance(mac, str):
        return None
    mac = mac.lower()
    if not _MAC_RE.match(mac):
        return None

    rssi = msg.get("rssi")
    if isinstance(rssi, bool) or not isinstance(rssi, (int, float)):
        return None

    name = msg.get("name")
    if name is not None and not isinstance(name, str):
        return None
    if name == "":
        name = None

    return PresenceEvent(
        device_id=anonymize_id("ble", mac),
        source="ble-esp32",
        rssi=float(rssi),
        band="ble",
        name=name,
        ts=time.time(),
    )


class SerialBleSensor(BleSensor):
    """Reads BLE advertisement JSON lines from a serial port and publishes events."""

    source = "ble-esp32"

    def __init__(
        self,
        bus: EventBus,
        port: str = "/dev/ttyACM1",
        baudrate: int = 115200,
        reconnect_delay: float = 2.0,
    ) -> None:
        super().__init__(bus)
        self.port = port
        self.baudrate = baudrate
        self.reconnect_delay = reconnect_delay

    async def run(self) -> None:
        import serial  # local import: tests and Mac dev do not need pyserial

        while True:
            try:
                ser = serial.serial_for_url(self.port, self.baudrate, timeout=1)
            except (serial.SerialException, OSError, ValueError) as exc:
                log.warning("serial open failed on %s: %s", self.port, exc)
                await asyncio.sleep(self.reconnect_delay)
                continue

            log.info("serial ble sensor reading %s", self.port)
            try:
                while True:
                    raw = await asyncio.to_thread(ser.readline)
                    if not raw:
                        continue
                    event = parse_ble_line(raw.decode("utf-8", "replace"))
                    if event is not None:
                        await self.bus.publish("event", event)
            except (serial.SerialException, OSError) as exc:
                log.warning("serial read failed on %s: %s", self.port, exc)
            finally:
                try:
                    ser.close()
                except Exception:  # noqa: BLE001 - close best-effort
                    pass
            await asyncio.sleep(self.reconnect_delay)


async def _run(port: str, baudrate: int) -> None:
    bus = EventBus()

    async def printer(event: PresenceEvent) -> None:
        print(
            f"{event.ts:.3f} rssi={event.rssi:6.1f} "
            f"name={event.name!r} id={event.device_id}",
            flush=True,
        )

    bus.subscribe("event", printer)
    await SerialBleSensor(bus, port=port, baudrate=baudrate).run()


def main() -> None:
    parser = argparse.ArgumentParser(description="ESP32 serial BLE advert sensor")
    parser.add_argument("--port", default="/dev/ttyACM1", help="serial port or pyserial URL")
    parser.add_argument("--baud", type=int, default=115200)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    try:
        asyncio.run(_run(args.port, args.baud))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
