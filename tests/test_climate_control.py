import importlib.util
import unittest
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import patch
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "client" / "climate_control.py"
SPEC = importlib.util.spec_from_file_location("climate_control", MODULE_PATH)
climate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(climate)


class ClimateCalculationTests(unittest.TestCase):
    def test_missing_weather_is_safe_and_silent_at_normal_temperature(self):
        self.assertEqual(climate.calculate(None, 20.0, 48.0), (0, 0, "sensor-data-unavailable"))

    def test_missing_sensor_still_protects_hot_cpu(self):
        self.assertEqual(climate.calculate(None, None, 72.0), (0, 70, "sensor-data-unavailable"))

    def test_warm_dome_needs_no_heating(self):
        weather = {"ambient": 10.0, "dewpoint": 5.0, "humidity": 70.0}
        self.assertEqual(climate.calculate(weather, 13.0, 45.0), (0, 0, "active"))

    def test_high_humidity_applies_dew_protection_and_air_mixing(self):
        weather = {"ambient": 8.0, "dewpoint": 7.5, "humidity": 98.0}
        heater, fan, status = climate.calculate(weather, 8.5, 45.0)
        self.assertGreaterEqual(heater, 25)
        self.assertGreaterEqual(fan, 28)
        self.assertEqual(status, "active")

    def test_telemetry_payload_contains_control_and_weather_values(self):
        state = {
            "timestamp": datetime(2026, 9, 25, 8, 0, tzinfo=timezone.utc).timestamp(),
            "status": "active",
            "cpu_c": 43.2,
            "dome_c": 18.5,
            "weather": {"ambient": 12.0, "dewpoint": 9.0, "humidity": 88.0},
            "heater_pct": 25,
            "fan_pct": 22,
        }
        payload = climate.telemetry_payload(state)
        self.assertEqual(payload["schema_version"], "allsky-climate.v1")
        self.assertEqual(payload["metrics"]["heater_pct"], 25)
        self.assertEqual(payload["metrics"]["ambient_c"], 12.0)
        self.assertEqual(payload["attributes"]["component"], "climate-control")

    def test_remote_weather_fallback_maps_central_telemetry(self):
        response = BytesIO(b'{"humidity":81,"metric":{"temp":13.2,"dewpt":9.9}}')
        response.__enter__ = lambda value: value
        response.__exit__ = lambda *args: None
        with patch.object(climate.urllib.request, "urlopen", return_value=response):
            current = climate.remote_weather()
        self.assertEqual(current, {"ambient": 13.2, "dewpoint": 9.9, "humidity": 81.0})


if __name__ == "__main__":
    unittest.main()
