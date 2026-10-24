"""Unit tests for aggregator sensor wiring (no hardware, no serial)."""
from presence.bus import EventBus
from presence.sensors.ble_sensor import SerialBleSensor
from presence.sensors.serial_wifi import SerialWifiSensor


def _wire(serial_wifi=None, serial_ble=None, simulator=False):
    from presence.aggregator import build_serial_sensors

    bus = EventBus()
    sensors = build_serial_sensors(bus, serial_wifi=serial_wifi,
                                   serial_ble=serial_ble, simulator=simulator)
    return sensors


def test_build_serial_sensors_both_ports():
    sensors = _wire(serial_wifi="/dev/ttyACM0", serial_ble="/dev/ttyACM1")
    assert [type(s) for s in sensors] == [SerialWifiSensor, SerialBleSensor]
    assert sensors[0].port == "/dev/ttyACM0"
    assert sensors[1].port == "/dev/ttyACM1"


def test_build_serial_sensors_wifi_only():
    sensors = _wire(serial_wifi="/dev/ttyACM0")
    assert [type(s) for s in sensors] == [SerialWifiSensor]
    assert sensors[0].port == "/dev/ttyACM0"


def test_build_serial_sensors_ble_only():
    sensors = _wire(serial_ble="/dev/ttyACM1")
    assert [type(s) for s in sensors] == [SerialBleSensor]


def test_build_serial_simulator_wins_over_serial_ports():
    sensors = _wire(serial_wifi="/dev/ttyACM0", serial_ble="/dev/ttyACM1",
                    simulator=True)
    assert sensors == []


def test_build_serial_sensors_none_configured():
    assert _wire() == []


def test_wired_sensors_carry_sources_and_bands():
    sensors = _wire(serial_wifi="/dev/ttyACM0", serial_ble="/dev/ttyACM1")
    assert sensors[0].source == "wifi"
    assert sensors[1].source == "ble-esp32"
    # Band label lives on the parsed events (band="ble"), not the sensor.
