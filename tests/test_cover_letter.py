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

        self.assertIn("Python Developer", draft)
        self.assertIn("ACME", draft)
        self.assertIn("Python", draft)
        self.assertNotIn("Docker", draft)
        self.assertIn("3 years", draft)

    def test_prompt_contains_evidence_and_anti_fabrication_rule(self) -> None:
        prompt = build_ai_prompt(self.profile, self.job, self.result)

        self.assertIn("Do not invent", prompt)
        self.assertIn('"title": "Python Developer"', prompt)
        self.assertIn('"company": "ACME"', prompt)
        self.assertIn('"missing_required_skills": [', prompt)
        self.assertIn('"Docker"', prompt)

    def test_german_job_produces_german_draft_and_prompt(self) -> None:
        german_job = JobPosting(
            source="test",
            external_id="de",
            title="Python-Entwickler",
            company="Beispiel GmbH",
            description=(
                "Ihr Profil: Fundierte Kenntnisse und Berufserfahrung. "
                "Sehr gute Deutschkenntnisse sind erforderlich."
            ),
            required_skills=("Python",),
        )
        result = JobMatcher().match(self.profile, german_job)

        draft = build_cover_letter_draft(self.profile, german_job, result)
        prompt = build_ai_prompt(self.profile, german_job, result)

        self.assertIn("Sehr geehrtes Recruiting-Team", draft)
        self.assertIn("Mit freundlichen Grüßen", draft)
        self.assertIn("Verfasse ein prägnantes", prompt)
        self.assertIn("Erfinde keine Fähigkeiten", prompt)


if __name__ == "__main__":
    unittest.main()
