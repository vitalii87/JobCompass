from __future__ import annotations

import unittest

from app.core.matcher import JobMatcher
from app.core.models import CandidateProfile, JobPosting
from app.services.cover_letter import build_ai_prompt, build_cover_letter_draft


class CoverLetterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = CandidateProfile(
            full_name="Vitalii",
            skills=("Python",),
            years_experience=3,
        )
        self.job = JobPosting(
            source="test",
            external_id="1",
            title="Python Developer",
            company="ACME",
            required_skills=("Python", "Docker"),
        )
        self.result = JobMatcher().match(self.profile, self.job)

    def test_draft_uses_matched_but_not_missing_skills(self) -> None:
        draft = build_cover_letter_draft(self.profile, self.job, self.result)

        self.assertIn("Python", draft)
        self.assertNotIn("Docker", draft)
        self.assertIn("3 years", draft)

    def test_prompt_contains_evidence_and_anti_fabrication_rule(self) -> None:
        prompt = build_ai_prompt(self.profile, self.job, self.result)

        self.assertIn("Do not invent", prompt)
        self.assertIn('"missing_required_skills": [', prompt)
        self.assertIn('"Docker"', prompt)


if __name__ == "__main__":
    unittest.main()
