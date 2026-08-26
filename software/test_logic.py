#!/usr/bin/env python3
"""Offline tests for pure decision logic; Raspberry Pi hardware is not required."""

import importlib.util
import sys
import types
from pathlib import Path

gpiozero = types.ModuleType("gpiozero")
gpiozero.Button = type("Button", (), {})
gpiozero.DigitalInputDevice = type("DigitalInputDevice", (), {})
gpiozero.DigitalOutputDevice = type("DigitalOutputDevice", (), {})
sys.modules["gpiozero"] = gpiozero

# The main module catches ImportError for these, but explicit stubs make the
# offline import predictable on development systems.
sys.modules.setdefault("board", types.ModuleType("board"))
sys.modules.setdefault("adafruit_dht", types.ModuleType("adafruit_dht"))

module_path = Path(__file__).with_name("hydro_monitor.py")
spec = importlib.util.spec_from_file_location("hydro_monitor", module_path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

assert module.update_temperature_state("NORMAL", 23.0, 24.0, 25.0, 23.5) == "NORMAL"
assert module.update_temperature_state("NORMAL", 24.0, 24.0, 25.0, 23.5) == "WARNING"
assert module.update_temperature_state("WARNING", 25.0, 24.0, 25.0, 23.5) == "CRITICAL"
assert module.update_temperature_state("CRITICAL", 23.4, 24.0, 25.0, 23.5) == "NORMAL"

assert module.select_alarm(False, True, False, "NORMAL", False) == "LOW_WATER"
assert module.select_alarm(False, False, True, "NORMAL", False) == "FLOW_LOSS"
assert module.select_alarm(False, False, False, "CRITICAL", False) == "TEMP_CRITICAL"
assert module.select_alarm(False, False, False, "NORMAL", True) == "TEMP_SENSOR_FAULT"
assert module.select_alarm(True, True, True, "CRITICAL", True) is None

status = module.select_system_status
assert status(True, False, None, True, True, True, "NORMAL", False) == "INHIBITED"
assert status(False, False, "LOW_WATER", True, False, True, "NORMAL", False) == "ALARM"
assert status(False, True, None, False, False, True, "NORMAL", False) == "STARTING"
assert status(False, False, None, True, False, True, "NORMAL", False) == "CHECKING_LEVEL"
assert status(False, False, None, False, True, True, "NORMAL", False) == "CHECKING_RETURN"
assert status(False, False, None, True, True, False, "NORMAL", False) == "CHECKING_WATER_TEMP"
assert status(False, False, None, True, True, True, "WARNING", False) == "UNHEALTHY_TEMP"
assert status(False, False, None, True, True, True, "NORMAL", False) == "HEALTHY"

assert module.status_led_pattern("HEALTHY", 99.0) is True
assert module.status_led_pattern("STARTING", 0.25) is True
assert module.status_led_pattern("STARTING", 0.75) is False
assert module.status_led_pattern("ALARM", 0.25) is False
assert module.status_led_pattern("INHIBITED", 0.25) is False

print("Core monitor logic tests passed.")


class FakeLevelInput:
    def __init__(self, is_active):
        self.is_active = is_active

raw, ok = module.read_low_level_state(FakeLevelInput(True), True)
assert raw == 0
assert ok is True

raw, ok = module.read_low_level_state(FakeLevelInput(False), True)
assert raw == 1
assert ok is False

raw, ok = module.read_low_level_state(FakeLevelInput(True), False)
assert raw == 0
assert ok is False

raw, ok = module.read_low_level_state(None, True)
assert raw is None
assert ok is None

assert module.buzzer_pattern("LOW_WATER", 0.2) is True
assert module.buzzer_pattern("LOW_WATER", 1.2) is False

print("Current-release core and low-level logic tests passed.")


assert module.temperature_notification_mode("NORMAL", False) == "NORMAL"
assert module.temperature_notification_mode("WARNING", False) == "WARNING"
assert module.temperature_notification_mode("CRITICAL", False) == "CRITICAL"
assert module.temperature_notification_mode("WARNING", True) == "SENSOR_FAULT"
assert module.temperature_transition_events("NORMAL", "WARNING") == ["TEMP_WARNING_ACTIVE"]
assert module.temperature_transition_events("WARNING", "CRITICAL") == ["TEMP_CRITICAL_ACTIVE"]
assert module.temperature_transition_events("CRITICAL", "WARNING") == ["TEMP_CRITICAL_EASED"]
assert module.temperature_transition_events("WARNING", "NORMAL") == ["TEMP_NORMAL"]
assert module.temperature_transition_events("SENSOR_FAULT", "CRITICAL") == [
    "TEMP_SENSOR_RESTORED", "TEMP_CRITICAL_ACTIVE"
]

title, message = module.build_notification_message(
    "FLOW_LOSS_ACTIVE",
    module.datetime.now().astimezone(),
    18.25,
    False,
    True,
    24.0,
    25.0,
    15,
    30,
    0,
    "Strawberry Hydroponics",
)
assert "Return flow LOST" in title
assert "18.2°C" in message
assert "NOT DETECTED" in message

print("Current-release notification transition/message tests passed.")


# Dual-probe configuration and exact-ID resolution.
import tempfile

assert module.normalise_ds18b20_id(" 28-000000000001 ") == "28-000000000001"
assert module.validate_temperature_probe_config({
    "reservoir_sensor_id": "28-a",
    "grow_pipe_enabled": True,
    "grow_pipe_sensor_id": "28-b",
}) == ("28-a", "28-b", True)
for invalid in (
    {
        "reservoir_sensor_id": "",
        "grow_pipe_enabled": True,
        "grow_pipe_sensor_id": "28-b",
    },
    {
        "reservoir_sensor_id": "28-a",
        "grow_pipe_enabled": True,
        "grow_pipe_sensor_id": "",
    },
):
    try:
        module.validate_temperature_probe_config(invalid)
    except ValueError:
        pass
    else:
        raise AssertionError("Enabled temperature roles must have assigned hardware IDs")

assert module.validate_temperature_probe_config({
    "reservoir_sensor_id": "28-a",
    "grow_pipe_enabled": False,
    "grow_pipe_sensor_id": "",
}) == ("28-a", "", False)
try:
    module.validate_temperature_probe_config({
        "reservoir_sensor_id": "28-a",
        "grow_pipe_enabled": True,
        "grow_pipe_sensor_id": "28-a",
    })
except ValueError:
    pass
else:
    raise AssertionError("Duplicate DS18B20 IDs must be rejected")

try:
    module.validate_temperature_probe_config({
        "reservoir_sensor_id": "28-a",
        "grow_pipe_enabled": True,
        "grow_pipe_sensor_id": "28-b",
        "grow_pipe_alarm_enabled": True,
    })
except ValueError:
    pass
else:
    raise AssertionError("Unvalidated grow-pipe alarms must be rejected")

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    for sensor_id, value in (("28-a", 18000), ("28-b", 19500)):
        device = root / sensor_id
        device.mkdir()
        (device / "w1_slave").write_text(
            f"aa bb cc YES\naa bb t={value}\n", encoding="utf-8"
        )
    assert module.list_ds18b20_ids(root) == ["28-a", "28-b"]
    assert module.find_ds18b20("28-b", root) == root / "28-b" / "w1_slave"
    assert module.find_ds18b20("", root) is None  # never guess between two probes
    assert module.read_ds18b20(module.find_ds18b20("28-a", root)) == 18.0

print("Current-release dual-DS18B20 identity tests passed.")

# The continuous monitor must reject the shipped blank IDs before any GPIO object
# is constructed. The simple gpiozero stubs above would fail if hardware setup ran.
import contextlib
import io
old_argv = sys.argv[:]
try:
    sys.argv = [
        str(module_path),
        "--config",
        str(Path(__file__).with_name("config.json")),
    ]
    captured = io.StringIO()
    with contextlib.redirect_stderr(captured):
        assert module.main() == 2
    assert "reservoir_sensor_id is not assigned" in captured.getvalue()
finally:
    sys.argv = old_argv

print("Pre-commissioning configuration safety test passed.")


class FakeOutput:
    def __init__(self):
        self.value = False
    def on(self):
        self.value = True
    def off(self):
        self.value = False


class FakeInput:
    value = 0


class FakeOverride:
    is_pressed = False


with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    reservoir_file = root / "reservoir"
    grow_file = root / "grow"
    reservoir_file.write_text("aa YES\naa t=18000\n", encoding="utf-8")
    grow_file.write_text("aa YES\naa t=19500\n", encoding="utf-8")
    outputs = [FakeOutput() for _ in range(4)]
    original_sleep = module.time.sleep
    original_cpu = module.read_cpu_temp
    try:
        module.time.sleep = lambda _seconds: None
        module.read_cpu_temp = lambda: 40.0
        passed_output = io.StringIO()
        with contextlib.redirect_stdout(passed_output):
            assert module.run_self_test(
                FakeInput(), None, True, FakeOverride(),
                outputs[0], outputs[1], outputs[2], outputs[3],
                reservoir_file, grow_file, True, 0,
                module.AmbientState(sensor=None), {"enabled": False},
            ) is True
        assert "REQUIRED TEMPERATURE PROBES PASSED" in passed_output.getvalue()

        failed_output = io.StringIO()
        failed_error = io.StringIO()
        with contextlib.redirect_stdout(failed_output), contextlib.redirect_stderr(failed_error):
            assert module.run_self_test(
                FakeInput(), None, True, FakeOverride(),
                outputs[0], outputs[1], outputs[2], outputs[3],
                reservoir_file, root / "missing", True, 0,
                module.AmbientState(sensor=None), {"enabled": False},
            ) is False
        assert "NO VALID READING" in failed_output.getvalue()
        assert "SELF-TEST RESULT: FAILED" in failed_error.getvalue()
    finally:
        module.time.sleep = original_sleep
        module.read_cpu_temp = original_cpu

print("Hardware self-test pass/fail tests passed.")
