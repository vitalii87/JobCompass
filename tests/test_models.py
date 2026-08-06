from __future__ import annotations

import unittest

from app.core.models import (
    ApplicationEvent,
    ApplicationRecord,
    ApplicationSubmission,
    ApplicationStatus,
    CandidateProfile,
    JobPosting,
    SubmissionMode,
    WorkMode,
)


class CandidateProfileTests(unittest.TestCase):
    def test_values_are_trimmed_and_deduplicated(self) -> None:
        profile = CandidateProfile(
            skills=(" Python ", "python", "Git"),
            desired_roles=("Developer",),
        )

        self.assertEqual(profile.skills, ("Python", "Git"))
        self.assertEqual(profile.desired_roles, ("Developer",))

    def test_negative_experience_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CandidateProfile(years_experience=-1)

    def test_invalid_json_field_type_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CandidateProfile.from_dict({"full_name": ["not", "text"]})


class JobPostingTests(unittest.TestCase):
    def test_required_identity_fields_are_validated(self) -> None:
        with self.assertRaises(ValueError):
            JobPosting(source="", external_id="1", title="Developer", company="ACME")

    def test_job_id_combines_source_and_external_id(self) -> None:
        job = JobPosting(
            source="board", external_id="42", title="Developer", company="ACME"
        )

        self.assertEqual(job.job_id, "board:42")

    def test_all_application_statuses_are_available(self) -> None:
        self.assertEqual(
            {status.value for status in ApplicationStatus},
            {
                "Found",
                "Interesting",
                "Draft",
                "Applied",
                "Rejected",
                "Interview",
                "Offer",
                "Archived",
            },
        )

    def test_work_mode_is_backward_compatible_with_remote(self) -> None:
        remote_job = JobPosting(
            source="board", external_id="remote", title="Developer", company="ACME",
            remote=True,
        )
        hybrid_job = JobPosting(
            source="board", external_id="hybrid", title="Developer", company="ACME",
            work_mode=WorkMode.HYBRID,
        )

        self.assertEqual(remote_job.work_mode, WorkMode.REMOTE)
        self.assertTrue(remote_job.is_remote)
        self.assertEqual(hybrid_job.remote, False)
        self.assertFalse(hybrid_job.is_remote)


class ApplicationRecordTests(unittest.TestCase):
    def test_submission_history_survives_later_statuses(self) -> None:
        record = ApplicationRecord(
            job_id="source:1",
            status=ApplicationStatus.ARCHIVED,
            history=(ApplicationEvent(status=ApplicationStatus.APPLIED),),
        )

        self.assertTrue(record.has_submission_history)
        self.assertEqual(
            ApplicationRecord.from_dict(record.to_dict()).history[0].status,
            ApplicationStatus.APPLIED,
        )

    def test_structured_submission_survives_round_trip(self) -> None:
        submission = ApplicationSubmission(
            mode=SubmissionMode.ASSISTED,
            destination_url="https://example.test/job/1",
            resume_path="C:/Documents/resume.pdf",
            resume_name="resume.pdf",
            resume_sha256="a" * 64,
            cover_letter_text="Sehr geehrte Damen und Herren,",
            contact_email="candidate@example.test",
        )
        record = ApplicationRecord(job_id="source:1", submissions=(submission,))

        restored = ApplicationRecord.from_dict(record.to_dict())

        self.assertEqual(restored.submissions, (submission,))
        self.assertTrue(restored.has_submission_history)

if __name__ == "__main__":
    unittest.main()
