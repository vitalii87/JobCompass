from __future__ import annotations

import unittest

from app.core.models import (
    ApplicationEvent,
    ApplicationRecord,
    ApplicationStatus,
    CandidateProfile,
    JobPosting,
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

if __name__ == "__main__":
    unittest.main()
