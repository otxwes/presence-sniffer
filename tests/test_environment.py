"""Unit tests for the environment layers (ALFA wifi env + Nooelec rf warmth)."""
import asyncio
import json
import time

from presence.aggregator import Aggregator, build_environment_sensors
from presence.bus import EventBus
from presence.events import PresenceSnapshot
from presence.osc_bridge import OscBridge
from presence.sensors.rf_sensor import RfReading, RfWarmthSensor, parse_power_csv
from presence.sensors.wifi_env import (
    UdpWifiEnvSensor,
    WifiEnvironment,
    parse_env_line,
)


def test_snapshot_has_environment_fields():
    snap = PresenceSnapshot(wifi_aps=18, wifi_busy=27.4, rf_warmth=0.42)
    d = snap.to_dict()
    assert d["wifi_aps"] == 18
    assert d["wifi_busy"] == 27.4
    assert d["rf_warmth"] == 0.42


def test_snapshot_environment_defaults():
    snap = PresenceSnapshot()
    assert snap.wifi_aps == 0
    assert snap.wifi_busy == 0.0
    assert snap.rf_warmth == 0.0


def test_parse_env_line_builds_reading():
    env = parse_env_line(json.dumps({"ts": 123.0, "aps": 18, "busy": 27.4}))
    assert isinstance(env, WifiEnvironment)
    assert env.ts == 123.0
    assert env.aps == 18
    assert env.busy == 27.4


def test_parse_env_line_ts_optional():
    before = time.time()
    env = parse_env_line(json.dumps({"aps": 1, "busy": 2.0}))
    after = time.time()
    assert env is not None
    assert before <= env.ts <= after


def test_parse_env_line_rejects_invalid_payloads():
    bad = [
        "not json",
        "[]",
        json.dumps({"aps": 18}),
        json.dumps({"busy": 1.0}),
        json.dumps({"aps": True, "busy": 1}),
        json.dumps({"aps": -1, "busy": 1}),
        json.dumps({"aps": 1, "busy": -1}),
        json.dumps({"aps": "1", "busy": 1}),
        json.dumps({"aps": 1, "busy": "1"}),
        json.dumps({"ts": "now", "aps": 1, "busy": 1}),
    ]
    for line in bad:
        assert parse_env_line(line) is None


def _csv_row(values):
    meta = ["2026-11-08", "17:00:00", "88000000", "90500000", "156250.00", "1024"]
    return ",".join(meta + [str(v) for v in values]) + "\n"


def test_parse_power_csv_computes_floor_peak_occupancy_warmth(tmp_path):
    path = tmp_path / "fm.csv"
    values = [-90] * 8 + [-60] * 2
    path.write_text(_csv_row(values) + _csv_row(values))
    reading = parse_power_csv(str(path))
    assert isinstance(reading, RfReading)
    assert reading.floor == -90
    assert reading.peak == -60
    assert abs(reading.occupancy - 0.2) < 1e-9
    assert abs(reading.warmth - 0.8) < 1e-9
    assert reading.ts > 0


def test_parse_power_csv_empty_returns_none(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("")
    assert parse_power_csv(str(path)) is None


def test_aggregator_merges_environment_and_rf():
    agg = Aggregator(EventBus())
    asyncio.run(agg.on_environment(WifiEnvironment(ts=time.time(), aps=18, busy=27.4)))
    asyncio.run(agg.on_rf(RfReading(ts=time.time(), warmth=0.42, floor=-90.0,
                                    peak=-60.0, occupancy=0.2)))
    snap = agg._make_snapshot()
    assert snap.wifi_aps == 18
    assert snap.wifi_busy == 27.4
    assert snap.rf_warmth == 0.42


def test_build_environment_sensors_wires_both():
    sensors = build_environment_sensors(EventBus(), wifi_env_port=9998,
                                        rf_warmth=True)
    assert [type(s) for s in sensors] == [UdpWifiEnvSensor, RfWarmthSensor]
    assert sensors[0].port == 9998
    assert sensors[1].band == "88M:108M:200k"
    assert sensors[1].interval == 2.0
    assert sensors[1].gain == 42


def test_build_environment_sensors_none_configured():
    assert build_environment_sensors(EventBus(), wifi_env_port=0,
                                     rf_warmth=False) == []


def test_osc_bridge_sends_environment_addresses():
    class FakeClient:
        def __init__(self):
            self.sent = []

        def send_message(self, address, value):
            self.sent.append((address, value))

    osc = OscBridge()
    fake = FakeClient()
    osc._client = fake
    asyncio.run(osc.on_snapshot(PresenceSnapshot(
        density=6, wifi_aps=18, wifi_busy=27.4, rf_warmth=0.42)))
    assert ("/wifi_aps", 18) in fake.sent
    assert ("/wifi_busy", 27.4) in fake.sent
    assert ("/rf_warmth", 0.42) in fake.sent
