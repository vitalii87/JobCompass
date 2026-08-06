from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.core.location import LocationSelection
from app.core.models import CandidateProfile, JobPosting
from app.core.profiles import SavedSearchPreferences, SearchSchedule
from app.services.scheduled_search import run_scheduled_search
from app.storage import LocalJsonStore


class _FakeOnlineSource:
    name = "Fake"

    def search(self, _query: object) -> list[JobPosting]:
        return [
            JobPosting(
                source=self.name,
                external_id="1",
                title="Teamassistenz",
                company="ACME",
                location="Stuttgart",
            )
        ]


class ScheduledSearchServiceTests(unittest.TestCase):
    def test_headless_search_records_only_new_discoveries_and_restores_context(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = LocalJsonStore(Path(directory) / "jobcompass.json")
            searched = store.create_profile(
                "Anna",
                CandidateProfile(
                    full_name="Anna", desired_roles=("Teamassistenz",)
                ),
            )
            store.save_search_preferences(
                SavedSearchPreferences(
                    sources=("Fake",),
                    roles=("Teamassistenz",),
                    locations=(LocationSelection(name="Stuttgart"),),
                )
            )
            store.save_schedule(SearchSchedule(enabled=True, daily_time="00:00"))
            active = store.create_profile("Vitalii")

            with patch(
                "app.services.scheduled_search.ONLINE_SOURCE_TYPES",
                (_FakeOnlineSource,),
            ):
                first = run_scheduled_search(store, searched.profile_id, force=True)
                second = run_scheduled_search(store, searched.profile_id, force=True)

            self.assertEqual(first.matched_count, 1)
            self.assertEqual(first.new_count, 1)
            self.assertEqual(second.new_count, 0)
            self.assertEqual(store.active_profile_id, active.profile_id)
            store.set_profile_context(searched.profile_id)
            self.assertEqual(len(store.list_unseen_jobs()), 1)


if __name__ == "__main__":
    unittest.main()
