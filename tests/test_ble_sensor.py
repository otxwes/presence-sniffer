"""Unit tests for the ESP32 serial BLE-advertisement adapter (no hardware needed)."""
import json
import time

from presence.events import PresenceEvent, anonymize_id
from presence.sensors.ble_sensor import parse_ble_line
from presence.sensors.serial_wifi import parse_probe_line


def _line(**overrides):
    payload = {
        "ts_ms": 12345,
        "mac": "aa:bb:cc:dd:ee:ff",
        "rssi": -79,
        "name": "iPhone",
    }
    payload.update(overrides)
    return json.dumps(payload)


def test_parse_ble_line_builds_ble_event():
    before = time.time()
    ev = parse_ble_line(_line())
    after = time.time()

    assert isinstance(ev, PresenceEvent)
    assert ev.source == "ble-esp32"
    assert ev.band == "ble"
    assert ev.rssi == -79
    assert ev.name == "iPhone"
    assert ev.device_id == anonymize_id("ble", "aa:bb:cc:dd:ee:ff")
    assert before <= ev.ts <= after


def test_parse_ble_line_hides_raw_mac():
    ev = parse_ble_line(_line())
    assert "aa:bb:cc:dd:ee:ff" not in ev.device_id
    assert "aa:bb:cc:dd:ee:ff" not in repr(ev)


def test_ble_and_wifi_ids_use_separate_namespaces():
    """A BLE line and a WiFi line for the same opaque MAC never share an id."""
    ble_ev = parse_ble_line(_line())
    wifi_ev = parse_probe_line(
        json.dumps({"ts_ms": 1, "mac": "aa:bb:cc:dd:ee:ff", "rssi": -79,
                    "ch": 6, "ssid": None})
    )
    assert ble_ev is not None and wifi_ev is not None
    assert ble_ev.device_id != wifi_ev.device_id


def test_null_name_is_none():
    ev = parse_ble_line(_line(name=None))
    assert ev is not None
    assert ev.name is None


def test_missing_name_field_is_none():
    payload = json.loads(_line())
    del payload["name"]
    ev = parse_ble_line(json.dumps(payload))
    assert ev is not None
    assert ev.name is None


def test_empty_name_is_none():
    ev = parse_ble_line(_line(name=""))
    assert ev is not None
    assert ev.name is None


def test_mac_case_is_normalized():
    lower = parse_ble_line(_line(mac="aa:bb:cc:dd:ee:ff"))
    upper = parse_ble_line(_line(mac="AA:BB:CC:DD:EE:FF"))
    assert lower.device_id == upper.device_id


def test_heartbeat_line_returns_none():
    assert parse_ble_line('{"hb":5001,"adverts":123}') is None


def test_boot_line_returns_none():
    assert parse_ble_line('{"boot":"ble_scan","fw":"0.1"}') is None


def test_ready_line_returns_none():
    assert parse_ble_line('{"ready":true,"mode":"passive"}') is None


def test_malformed_json_returns_none():
    assert parse_ble_line("not json") is None


def test_non_object_json_returns_none():
    assert parse_ble_line("[]") is None


def test_missing_mac_returns_none():
    payload = json.loads(_line())
    del payload["mac"]
    assert parse_ble_line(json.dumps(payload)) is None


def test_invalid_mac_returns_none():
    assert parse_ble_line(_line(mac="nope")) is None


def test_missing_rssi_returns_none():
    payload = json.loads(_line())
    del payload["rssi"]
    assert parse_ble_line(json.dumps(payload)) is None


def test_non_numeric_rssi_returns_none():
    assert parse_ble_line(_line(rssi="loud")) is None


def test_bool_rssi_returns_none():
    assert parse_ble_line(_line(rssi=True)) is None


def test_non_string_name_returns_none():
    assert parse_ble_line(_line(name=42)) is None
