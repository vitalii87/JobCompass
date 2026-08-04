from __future__ import annotations

import unittest
from typing import Any

from app.services.geocoding import LocationGeocoder


class FakeClient:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.calls: list[dict[str, object]] = []

    def get_json(
        self,
        url: str,
        params: dict[str, object] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        self.calls.append(dict(params or {}))
        return self.payload


class LocationGeocoderTests(unittest.TestCase):
    def test_city_results_include_region_country_and_coordinates(self) -> None:
        client = FakeClient(
            {
                "results": [
                    {
                        "id": 2890248,
                        "name": "Köngen",
                        "latitude": 48.68333,
                        "longitude": 9.36667,
                        "country_code": "DE",
                        "country": "Deutschland",
                        "admin1": "Baden-Württemberg",
                        "admin3": "Landkreis Esslingen",
                    }
                ]
            }
        )

        result = LocationGeocoder(client=client).search("Köngen")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "Köngen")
        self.assertEqual(result[0].source_query, "Köngen, Baden-Württemberg")
        self.assertIn("Landkreis Esslingen", result[0].display_name)
        self.assertEqual(result[0].latitude, 48.68333)
        self.assertEqual(client.calls[0]["countryCode"], "DE")

    def test_postcode_disambiguates_source_query(self) -> None:
        client = FakeClient(
            {
                "results": [
                    {
                        "id": 1,
                        "name": "Neustadt",
                        "latitude": 49.35,
                        "longitude": 8.14,
                        "country_code": "DE",
                        "country": "Deutschland",
                        "admin1": "Rheinland-Pfalz",
                        "postcodes": ["67433", "67434"],
                    }
                ]
            }
        )

        result = LocationGeocoder(client=client).search("Neustadt")

        self.assertEqual(result[0].source_query, "67433 Neustadt")
        self.assertIn("67433/67434", result[0].display_name)

    def test_short_query_does_not_call_service(self) -> None:
        client = FakeClient({"results": []})

        result = LocationGeocoder(client=client).search("K")

        self.assertEqual(result, [])
        self.assertEqual(client.calls, [])


if __name__ == "__main__":
    unittest.main()
