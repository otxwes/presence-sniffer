"""Unit tests for the ESP32 serial WiFi-probe adapter (no hardware needed)."""
import json
import time

from presence.events import PresenceEvent, anonymize_id
from presence.sensors.serial_wifi import parse_probe_line


def _line(**overrides):
    payload = {
        "ts_ms": 12345,
        "mac": "a4:5e:60:1a:2b:3c",
        "rssi": -63,
        "ch": 6,
        "ssid": "Flock-1A2B3C",
    }
    payload.update(overrides)
    return json.dumps(payload)


def test_presence_event_carries_ssid():
    ev = PresenceEvent(device_id="x", source="wifi", ssid="Flock-1A2B3C")
    assert ev.ssid == "Flock-1A2B3C"


def test_parse_probe_line_builds_wifi_event():
    before = time.time()
    ev = parse_probe_line(_line())
    after = time.time()

    assert isinstance(ev, PresenceEvent)
    assert ev.source == "wifi"
    assert ev.band == "2.4g"
    assert ev.rssi == -63
    assert ev.ssid == "Flock-1A2B3C"
    assert ev.device_id == anonymize_id("wifi", "a4:5e:60:1a:2b:3c")
    assert before <= ev.ts <= after


def test_parse_probe_line_hides_raw_mac():
    ev = parse_probe_line(_line())
    assert "a4:5e:60:1a:2b:3c" not in ev.device_id
    assert "a4:5e:60:1a:2b:3c" not in repr(ev)


def test_wildcard_probe_has_no_ssid():
    ev = parse_probe_line(_line(ssid=""))
    assert ev is not None
    assert ev.ssid is None


def test_mac_case_is_normalized():
    lower = parse_probe_line(_line(mac="a4:5e:60:1a:2b:3c"))
    upper = parse_probe_line(_line(mac="A4:5E:60:1A:2B:3C"))
    assert lower.device_id == upper.device_id


def test_missing_ssid_field_is_none():
    payload = json.loads(_line())
    del payload["ssid"]
    ev = parse_probe_line(json.dumps(payload))
    assert ev is not None
    assert ev.ssid is None


def test_malformed_json_returns_none():
    assert parse_probe_line("not json") is None


def test_non_object_json_returns_none():
    assert parse_probe_line("[]") is None


def test_missing_mac_returns_none():
    payload = json.loads(_line())
    del payload["mac"]
    assert parse_probe_line(json.dumps(payload)) is None


def test_invalid_mac_returns_none():
    assert parse_probe_line(_line(mac="nope")) is None


def test_missing_rssi_returns_none():
    payload = json.loads(_line())
    del payload["rssi"]
    assert parse_probe_line(json.dumps(payload)) is None


def test_non_numeric_rssi_returns_none():
    assert parse_probe_line(_line(rssi="loud")) is None


def test_bool_rssi_returns_none():
    assert parse_probe_line(_line(rssi=True)) is None
