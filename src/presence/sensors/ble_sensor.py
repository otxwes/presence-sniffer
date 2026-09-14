"""Phase 1 stub: BLE advertisement capture.

Real implementation plan: run the nRF52840 Sniffer firmware, read its UART/USB
packet stream (or use btmon on Linux/Pi), extract BLE advertisements with RSSI,
map advertised fields to device_class, and publish as PresenceEvent(source="ble").
"""
from __future__ import annotations

from .base import BaseSensor


class BleSensor(BaseSensor):
    source = "ble"


class SerialBleSensor(BleSensor):
    """Reads BLE adverts from an ESP32 board over serial (firmware emits JSON lines)."""
    source = "ble-esp32"

