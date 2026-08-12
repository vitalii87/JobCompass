from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from app.core.source_registry import (
    AtsType,
    SourceRegistryEntry,
    SourceRegistryStatus,
)
from app.storage import LocalJsonStore


class SourceRegistryTests(unittest.TestCase):
    def test_entry_normalizes_url_and_records_health(self) -> None:
        entry = SourceRegistryEntry(
            company=" Acme GmbH ",
            career_url="HTTPS://JOBS.LEVER.CO/acme/",
            ats_type=AtsType.LEVER,
            country=" DE ",
        )
        checked_at = datetime(2026, 8, 12, 8, 30, tzinfo=timezone.utc)

        active = entry.checked(succeeded=True, at=checked_at)

        self.assertEqual(active.career_url, "https://jobs.lever.co/acme")
        self.assertEqual(active.company, "Acme GmbH")
        self.assertEqual(active.status, SourceRegistryStatus.ACTIVE)
        self.assertEqual(active.last_success, checked_at)
        self.assertEqual(SourceRegistryEntry.from_dict(active.to_dict()), active)

    def test_store_upserts_and_preserves_registry_between_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "store.json"
            store = LocalJsonStore(path)
            store.initialize()
            generic = SourceRegistryEntry(
                company="",
                career_url="https://jobs.lever.co/acme",
                ats_type=AtsType.GENERIC_HTML,
            )
            detected = SourceRegistryEntry(
                company="Acme",
                career_url="https://jobs.lever.co/acme/",
                ats_type=AtsType.LEVER,
                country="DE",
            )

            self.assertEqual(store.upsert_source_registry([generic]), 1)
            self.assertEqual(store.upsert_source_registry([detected]), 0)

            saved = LocalJsonStore(path).list_source_registry()
            self.assertEqual(len(saved), 1)
            self.assertEqual(saved[0].ats_type, AtsType.LEVER)
            self.assertEqual(saved[0].company, "Acme")
            self.assertEqual(saved[0].country, "DE")


if __name__ == "__main__":
    unittest.main()
