import importlib.util
import unittest
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


if __name__ == "__main__":
    unittest.main()
