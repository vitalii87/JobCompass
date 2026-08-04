from __future__ import annotations

import unittest

from app.core.location import (
    LocationQuery,
    LocationSelection,
    build_location_queries,
)


class LocationQueryTests(unittest.TestCase):
    def test_slider_radius_is_applied_to_each_location(self) -> None:
        queries = build_location_queries(("Berlin", " Köngen "), 50)

        self.assertEqual(queries[0], LocationQuery(name="Berlin", radius_km=50))
        self.assertEqual(queries[1], LocationQuery(name="Köngen", radius_km=50))

    def test_no_slider_radius_keeps_plain_location(self) -> None:
        query = build_location_queries(("Stuttgart",))[0]

        self.assertIsNone(query.radius_km)

    def test_invalid_slider_radius_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "between 0 and 500"):
            LocationQuery(name="Köngen", radius_km=600)

    def test_selected_cities_keep_identity_and_share_slider_radius(self) -> None:
        locations = (
            LocationSelection(
                name="Köngen",
                geonames_id=1,
                admin1="Baden-Württemberg",
                admin3="Landkreis Esslingen",
                country="Deutschland",
                country_code="DE",
                latitude=48.68333,
                longitude=9.36667,
            ),
            LocationSelection(
                name="Neustadt",
                geonames_id=2,
                admin1="Rheinland-Pfalz",
                country="Deutschland",
                country_code="DE",
                latitude=49.35,
                longitude=8.14,
                postcodes=("67433",),
            ),
        )

        queries = build_location_queries((), 50, locations)

        self.assertEqual([query.radius_km for query in queries], [50, 50])
        self.assertEqual(queries[0].source_query, "Köngen, Baden-Württemberg")
        self.assertEqual(queries[1].source_query, "67433 Neustadt")
        self.assertIn("Landkreis Esslingen", locations[0].display_name)


if __name__ == "__main__":
    unittest.main()
