from __future__ import annotations

import unittest

from app.core.location import (
    LocationQuery,
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


if __name__ == "__main__":
    unittest.main()
