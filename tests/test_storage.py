from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path

from app.core.models import (
    ApplicationStatus,
    ApplicationSubmission,
    CandidateProfile,
    CoverLetterPreparation,
    JobPosting,
    SubmissionMode,
)
from app.storage import LocalJsonStore


class LocalJsonStoreTests(unittest.TestCase):
    def test_global_interface_language_survives_reload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jobcompass.json"
            store = LocalJsonStore(path)
            store.initialize()

            store.save_app_language("en")

            self.assertEqual(LocalJsonStore(path).load_app_language(), "en")

    def test_german_interface_language_survives_reload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "store.json"
            store = LocalJsonStore(path)
            store.initialize()

            store.save_app_language("de")

            self.assertEqual(LocalJsonStore(path).load_app_language(), "de")

    def test_global_career_sites_survive_reload_and_are_deduplicated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "store.json"
            store = LocalJsonStore(path)
            store.initialize()

            store.save_career_urls(
                (
                    "https://jobs.example.test/careers",
                    "https://jobs.example.test/careers",
                    " https://jobs.lever.co/example ",
                )
            )

            self.assertEqual(
                LocalJsonStore(path).load_career_urls(),
                (
                    "https://jobs.example.test/careers",
                    "https://jobs.lever.co/example",
                ),
            )

    def test_career_site_rejects_non_http_url(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = LocalJsonStore(Path(directory) / "store.json")
            store.initialize()

            with self.assertRaises(ValueError):
                store.save_career_urls(("file:///private/jobs.html",))
            with self.assertRaises(ValueError):
                store.save_career_urls(("https://",))

    def test_jobs_and_application_status_survive_reload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jobcompass.json"
            store = LocalJsonStore(path)
            store.create_profile("Vitalii")
            job = JobPosting(
                source="test",
                external_id="1",
                title="Python Developer",
                company="ACME",
            )

            self.assertEqual(store.save_jobs([job]), 1)
            record = store.set_application_status(
                job.job_id, ApplicationStatus.INTERESTING, "Review tomorrow"
            )
            reloaded = LocalJsonStore(path)

            self.assertEqual(reloaded.list_jobs(), [job])
            self.assertEqual(record.status, ApplicationStatus.INTERESTING)
            self.assertEqual(reloaded.list_applications()[0].notes, "Review tomorrow")
            self.assertEqual(len(reloaded.list_applications()[0].history), 1)

    def test_profile_and_full_status_history_are_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = LocalJsonStore(Path(directory) / "jobcompass.json")
            profile = CandidateProfile(
                full_name="Vitalii", skills=("Python",), email="v@example.test"
            )
            job = JobPosting(
                source="test", external_id="2", title="Developer", company="ACME"
            )
            store.save_profile(profile)
            store.save_jobs([job])
            store.set_application_status(job.job_id, ApplicationStatus.APPLIED)
            store.set_application_status(job.job_id, ApplicationStatus.INTERVIEW)

            application = store.get_application(job.job_id)

            self.assertEqual(store.load_profile(), profile)
            self.assertIsNotNone(application)
            assert application is not None
            self.assertEqual(
                [event.status for event in application.history],
                [ApplicationStatus.APPLIED, ApplicationStatus.INTERVIEW],
            )
            self.assertTrue(application.has_submission_history)

    def test_unknown_job_cannot_receive_an_application_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = LocalJsonStore(Path(directory) / "jobcompass.json")

            with self.assertRaises(ValueError):
                store.set_application_status("missing:1", ApplicationStatus.APPLIED)

    def test_cover_letter_material_is_saved_per_vacancy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jobcompass.json"
            store = LocalJsonStore(path)
            store.create_profile("Vitalii")
            job = JobPosting(
                source="test", external_id="letter", title="PMO", company="ACME"
            )
            store.save_jobs([job])
            preparation = CoverLetterPreparation(
                job_id=job.job_id,
                draft="Editable draft",
                prompt="Grounded prompt",
                evidence_summary="Confirmed facts",
                language="de",
                tone="warm",
                length="standard",
                focus="Relocation confirmed",
            )

            store.save_cover_letter_preparation(preparation)
            reloaded = LocalJsonStore(path).get_cover_letter_preparation(job.job_id)

            self.assertEqual(reloaded, preparation)

    def test_confirmed_submission_records_materials_and_blocks_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jobcompass.json"
            store = LocalJsonStore(path)
            store.create_profile("Vitalii")
            job = JobPosting(
                source="test", external_id="submit", title="PMO", company="ACME"
            )
            store.save_jobs([job])
            submission = ApplicationSubmission(
                mode=SubmissionMode.ASSISTED,
                destination_url="https://example.test/job",
                resume_name="resume.pdf",
                resume_sha256="b" * 64,
                cover_letter_text="Letter",
            )

            record = store.record_application_submission(job.job_id, submission)

            self.assertEqual(record.status, ApplicationStatus.APPLIED)
            self.assertEqual(record.submissions, (submission,))
            with self.assertRaises(ValueError):
                store.record_application_submission(job.job_id, submission)
            duplicate = store.record_application_submission(
                job.job_id, submission, allow_duplicate=True
            )
            self.assertEqual(len(duplicate.submissions), 2)

    def test_parallel_store_instances_do_not_lose_jobs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jobcompass.json"
            LocalJsonStore(path).initialize()
            start = threading.Barrier(3)
            failures: list[Exception] = []

            def save(external_id: str) -> None:
                try:
                    store = LocalJsonStore(path)
                    start.wait()
                    store.save_jobs(
                        [
                            JobPosting(
                                source="parallel",
                                external_id=external_id,
                                title=f"Role {external_id}",
                                company="ACME",
                            )
                        ]
                    )
                except Exception as error:  # pragma: no cover - assertion below
                    failures.append(error)

            threads = [
                threading.Thread(target=save, args=(external_id,))
                for external_id in ("one", "two")
            ]
            for thread in threads:
                thread.start()
            start.wait()
            for thread in threads:
                thread.join()

            self.assertEqual(failures, [])
            self.assertEqual(
                {job.external_id for job in LocalJsonStore(path).list_jobs()},
                {"one", "two"},
            )

    def test_direct_duplicate_keeps_profile_history_under_canonical_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = LocalJsonStore(Path(directory) / "jobcompass.json")
            store.create_profile("Candidate")
            aggregator = JobPosting(
                source="aggregator",
                external_id="old",
                title="QA Engineer",
                company="Example GmbH",
                location="Stuttgart",
                description="Summary",
            )
            direct = JobPosting(
                source="Company career pages",
                external_id="direct",
                title="QA Engineer",
                company="Example GmbH",
                location="Stuttgart",
                url="https://example.test/careers/qa",
                description="A substantially richer direct vacancy description.",
            )
            store.save_jobs([aggregator])
            store.record_job_discoveries([aggregator.job_id])
            store.mark_job_seen(aggregator.job_id)
            store.set_job_favorite(aggregator.job_id)
            store.set_application_status(
                aggregator.job_id, ApplicationStatus.INTERESTING
            )
            store.save_cover_letter_preparation(
                CoverLetterPreparation(
                    job_id=aggregator.job_id,
                    draft="Draft",
                    prompt="Prompt",
                )
            )
            store.save_last_result_job_ids([aggregator.job_id])

            self.assertEqual(store.save_jobs([direct]), 0)

            self.assertEqual(store.list_jobs(), [direct])
            self.assertTrue(store.get_job_state(direct.job_id)["favorite"])
            self.assertIsNotNone(store.get_job_state(direct.job_id)["seen_at"])
            self.assertIsNotNone(store.get_application(direct.job_id))
            self.assertIsNotNone(store.get_cover_letter_preparation(direct.job_id))
            self.assertEqual(store.load_last_result_job_ids(), [direct.job_id])


if __name__ == "__main__":
    unittest.main()
