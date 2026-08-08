from __future__ import annotations

from datetime import datetime
import json
import tempfile
import unittest
from pathlib import Path

from app.core.location import LocationSelection
from app.core.models import ApplicationStatus, CandidateProfile, JobPosting
from app.core.profiles import SavedSearchPreferences, SearchSchedule
from app.storage import LocalJsonStore


class MultiProfileStorageTests(unittest.TestCase):
    def test_guest_candidate_is_not_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jobcompass.json"
            store = LocalJsonStore(path)
            store.initialize()
            store.set_guest_profile(CandidateProfile(full_name="Guest"))

            reloaded = LocalJsonStore(path)

            self.assertTrue(reloaded.is_guest)
            self.assertEqual(reloaded.list_profiles(), [])
            self.assertEqual(reloaded.load_profile(), CandidateProfile())

    def test_temporary_guest_mode_keeps_last_profile_for_next_launch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jobcompass.json"
            store = LocalJsonStore(path)
            profile = store.create_profile("Anna")

            store.activate_profile(None)

            self.assertTrue(store.is_guest)
            reloaded = LocalJsonStore(path)
            self.assertEqual(reloaded.active_profile_id, profile.profile_id)

    def test_guest_activity_can_be_moved_into_a_new_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jobcompass.json"
            store = LocalJsonStore(path)
            job = JobPosting(
                source="test", external_id="guest", title="Job", company="ACME"
            )
            store.save_jobs([job])
            store.record_job_discoveries([job.job_id])
            store.set_job_favorite(job.job_id)
            store.set_application_status(job.job_id, ApplicationStatus.INTERESTING)
            snapshot = store.snapshot_activity()

            store.create_profile("Saved guest")
            store.restore_activity(snapshot)

            reloaded = LocalJsonStore(path)
            self.assertEqual(reloaded.list_favorite_job_ids(), {job.job_id})
            self.assertEqual(len(reloaded.list_applications()), 1)
            self.assertEqual(reloaded.list_unseen_jobs(), [job])

    def test_candidate_history_favorites_and_filters_are_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jobcompass.json"
            store = LocalJsonStore(path)
            anna = store.create_profile(
                "Anna", CandidateProfile(full_name="Anna", skills=("Excel",))
            )
            job = JobPosting(
                source="test", external_id="1", title="Assistenz", company="ACME"
            )
            store.save_jobs([job])
            store.save_search_preferences(
                SavedSearchPreferences(
                    roles=("Teamassistenz",),
                    locations=(LocationSelection(name="Köngen"),),
                    radius_km=50,
                )
            )
            store.record_job_discoveries([job.job_id])
            store.set_job_favorite(job.job_id)
            store.set_application_status(job.job_id, ApplicationStatus.INTERESTING)

            vitalii = store.create_profile(
                "Vitalii", CandidateProfile(full_name="Vitalii")
            )

            self.assertEqual(store.list_applications(), [])
            self.assertEqual(store.list_favorite_job_ids(), set())
            self.assertEqual(store.load_search_preferences().roles, ())

            store.activate_profile(anna.profile_id)
            self.assertEqual(store.load_profile().full_name, "Anna")
            self.assertEqual(store.load_search_preferences().radius_km, 50)
            self.assertEqual(store.list_favorite_job_ids(), {job.job_id})
            self.assertEqual(len(store.list_applications()), 1)

            store.activate_profile(vitalii.profile_id)
            reloaded = LocalJsonStore(path)
            self.assertEqual(reloaded.active_profile_id, vitalii.profile_id)
            self.assertEqual(reloaded.load_profile().full_name, "Vitalii")

    def test_schema_one_is_migrated_to_a_named_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jobcompass.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "profile": CandidateProfile(full_name="Anna").to_dict(),
                        "jobs": [],
                        "applications": [],
                        "cover_letters": [],
                    }
                ),
                encoding="utf-8",
            )

            store = LocalJsonStore(path)

            self.assertFalse(store.is_guest)
            self.assertEqual([item.name for item in store.list_profiles()], ["Anna"])
            self.assertEqual(store.load_profile().full_name, "Anna")
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8"))["schema_version"], 2
            )

    def test_unseen_jobs_are_profile_specific(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = LocalJsonStore(Path(directory) / "jobcompass.json")
            first = store.create_profile("First")
            job = JobPosting(
                source="test", external_id="new", title="New job", company="ACME"
            )
            store.save_jobs([job])
            self.assertEqual(store.record_job_discoveries([job.job_id]), 1)
            self.assertEqual(store.list_unseen_jobs(), [job])
            store.mark_job_seen(job.job_id)
            self.assertEqual(store.list_unseen_jobs(), [])
            discovered = store.list_discovered_jobs()
            self.assertEqual([item[0] for item in discovered], [job])
            self.assertIsNotNone(discovered[0][1].get("seen_at"))

            store.create_profile("Second")
            self.assertEqual(store.list_unseen_jobs(), [])
            self.assertEqual(store.list_discovered_jobs(), [])
            store.activate_profile(first.profile_id)
            self.assertEqual(store.list_unseen_jobs(), [])
            self.assertEqual(
                [item[0] for item in store.list_discovered_jobs()], [job]
            )

    def test_manual_discovery_does_not_appear_in_scheduled_jobs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = LocalJsonStore(Path(directory) / "jobcompass.json")
            store.create_profile("Candidate")
            job = JobPosting("test", "manual", "Manual", "ACME")
            store.save_jobs([job])

            store.record_job_discoveries([job.job_id], scheduled=False)

            self.assertEqual(len(store.list_discovered_jobs()), 1)
            self.assertEqual(store.list_scheduled_jobs(), [])
            self.assertEqual(store.list_unseen_jobs(), [])


class SearchScheduleTests(unittest.TestCase):
    def test_daily_schedule_runs_only_after_time_and_once_per_day(self) -> None:
        local_zone = datetime.now().astimezone().tzinfo
        before = datetime(2026, 8, 6, 8, 30, tzinfo=local_zone)
        after = datetime(2026, 8, 6, 10, 0, tzinfo=local_zone)

        self.assertFalse(SearchSchedule(True, "09:00").is_due(before))
        self.assertTrue(SearchSchedule(True, "09:00").is_due(after))
        self.assertFalse(
            SearchSchedule(True, "09:00", last_run_at=after).is_due(after)
        )


if __name__ == "__main__":
    unittest.main()
