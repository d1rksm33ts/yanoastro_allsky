import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "client" / "weather_receiver.py"
SPEC = importlib.util.spec_from_file_location("weather_receiver", MODULE_PATH)
weather = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(weather)


class WeatherPayloadTests(unittest.TestCase):
    def test_legacy_station_fields_are_mapped(self):
        payload = weather.telemetry_payload({
            "datetime": "2026-09-15 10:30:00",
            "t1tem": "18.5",
            "t1dew": "13.1",
            "t1hum": "72",
            "t1wdir": "215",
        })
        self.assertEqual(payload["stationID"], "IZONHO45")
        self.assertEqual(payload["metric"]["temp"], 18.5)
        self.assertEqual(payload["metric"]["dewpt"], 13.1)
        self.assertEqual(payload["humidity"], 72.0)
        self.assertEqual(payload["winddir"], 215)
        self.assertEqual(payload["obsTimeUtc"], "2026-09-15T08:30:00Z")


if __name__ == "__main__":
    unittest.main()
