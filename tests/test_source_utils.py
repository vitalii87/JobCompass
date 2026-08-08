from __future__ import annotations

import unittest
from datetime import datetime, timezone

from app.sources.utils import parse_published_at


class SourceDateParsingTests(unittest.TestCase):
    def test_parses_iso_german_compact_rfc_and_epoch_milliseconds(self) -> None:
        expected = datetime(2026, 8, 8, tzinfo=timezone.utc)

        self.assertEqual(parse_published_at("2026-08-08"), expected)
        self.assertEqual(parse_published_at("08.08.2026"), expected)
        self.assertEqual(parse_published_at("20260808"), expected)
        self.assertEqual(
            parse_published_at("Sat, 08 Aug 2026 00:00:00 GMT"), expected
        )
        self.assertEqual(
            parse_published_at(expected.timestamp() * 1000), expected
        )

    def test_invalid_or_empty_date_is_unknown(self) -> None:
        self.assertIsNone(parse_published_at(None))
        self.assertIsNone(parse_published_at("not a date"))


if __name__ == "__main__":
    unittest.main()
