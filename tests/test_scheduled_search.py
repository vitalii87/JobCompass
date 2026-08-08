from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from app.core.location import LocationSelection
from app.core.models import CandidateProfile, JobPosting, utc_now
from app.core.profiles import SavedSearchPreferences, SearchSchedule
from app.services.scheduled_search import fresh_scheduled_jobs, run_scheduled_search
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
                published_at=utc_now(),
            )
        ]


class ScheduledSearchServiceTests(unittest.TestCase):
    def test_freshness_uses_last_run_date_and_rejects_unreliable_dates(self) -> None:
        now = datetime(2026, 8, 8, 10, 0, tzinfo=timezone.utc)
        jobs = [
            JobPosting("Fake", "fresh", "Fresh", "ACME", published_at=now),
            JobPosting(
                "Fake",
                "same-day",
                "Date-only source",
                "ACME",
                published_at=datetime(2026, 8, 7, tzinfo=timezone.utc),
            ),
            JobPosting(
                "Fake",
                "old",
                "Old",
                "ACME",
                published_at=now - timedelta(days=3),
            ),
            JobPosting("Fake", "unknown", "Unknown", "ACME"),
            JobPosting(
                "Fake",
                "future",
                "Future",
                "ACME",
                published_at=now + timedelta(days=1),
            ),
        ]

        fresh = fresh_scheduled_jobs(
            jobs,
            datetime(2026, 8, 7, 9, 0, tzinfo=timezone.utc),
            now=now,
        )

        self.assertEqual([job.external_id for job in fresh], ["fresh", "same-day"])

    def test_first_run_uses_last_24_hours_calendar_window(self) -> None:
        now = datetime(2026, 8, 8, 1, 0, tzinfo=timezone.utc)
        yesterday = JobPosting(
            "Fake",
            "yesterday",
            "Yesterday",
            "ACME",
            published_at=datetime(2026, 8, 7, tzinfo=timezone.utc),
        )

        self.assertEqual(
            fresh_scheduled_jobs([yesterday], None, now=now), [yesterday]
        )

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
