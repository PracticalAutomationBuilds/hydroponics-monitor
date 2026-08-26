#!/usr/bin/env python3
"""Offline Pushover sender tests; no network request is made."""

import importlib.util
import io
import json
import sys
import types
from pathlib import Path
from unittest.mock import patch

# Hardware-library stubs for importing the monitor on a non-Pi system.
gpiozero = types.ModuleType("gpiozero")
gpiozero.Button = type("Button", (), {})
gpiozero.DigitalInputDevice = type("DigitalInputDevice", (), {})
gpiozero.DigitalOutputDevice = type("DigitalOutputDevice", (), {})
sys.modules["gpiozero"] = gpiozero
sys.modules.setdefault("board", types.ModuleType("board"))
sys.modules.setdefault("adafruit_dht", types.ModuleType("adafruit_dht"))

module_path = Path(__file__).with_name("hydro_monitor.py")
spec = importlib.util.spec_from_file_location("hydro_monitor_notifications", module_path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class FakeResponse:
    def __init__(self, body):
        self.body = body
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self):
        return self.body


payload = {
    "token": "A" * 30,
    "user": "B" * 30,
    "title": "Test",
    "message": "Test message",
    "priority": 0,
}
with patch.object(
    module.urllib_request,
    "urlopen",
    return_value=FakeResponse(b'{"status":1,"request":"abc123"}'),
):
    result = module.send_pushover_request(payload, 1)
assert result["status"] == 1
assert result["request"] == "abc123"

notifier = module.PushoverNotifier({"enabled": False})
assert notifier.ready is False
assert notifier.notify("FLOW_LOSS_ACTIVE", "x", "y") is False
assert notifier.snapshot()["enabled"] is False

print("Mocked Pushover API tests passed.")
