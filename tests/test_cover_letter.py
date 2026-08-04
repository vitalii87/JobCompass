from __future__ import annotations

import unittest

from app.core.matcher import JobMatcher
from app.core.models import CandidateProfile, JobPosting
from app.services.cover_letter import (
    build_ai_prompt,
    build_cover_letter_draft,
    build_evidence_summary,
    build_prompt_evidence,
)


class CoverLetterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = CandidateProfile(
            full_name="Vitalii",
            email="private@example.test",
            summary="I coordinate technical projects and improve team processes.",
            desired_roles=("Python Developer",),
            skills=("Python",),
            languages=("German B2", "English B2"),
            years_experience=3,
        )
        self.job = JobPosting(
            source="test",
            external_id="1",
            title="Python Developer",
            company="ACME",
            location="Stuttgart",
            description=(
                "Develop internal Python tools, collaborate with stakeholders, "
                "and maintain Docker-based services."
            ),
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
        self.assertIn('"missing_or_unconfirmed_required_skills": [', prompt)
        self.assertIn('"Docker"', prompt)
        self.assertIn("processed data from the CV and selected vacancy", prompt)
        self.assertNotIn("private@example.test", prompt)

    def test_prompt_honors_tone_length_and_candidate_focus(self) -> None:
        prompt = build_ai_prompt(
            self.profile,
            self.job,
            self.result,
            "en",
            tone="warm",
            length="short",
            focus="I am relocating to Stuttgart in October.",
        )

        self.assertIn("professional, personable, and warm", prompt)
        self.assertIn("140 to 180 words", prompt)
        self.assertIn("I am relocating to Stuttgart in October.", prompt)
        self.assertIn("two to four of the strongest evidenced overlaps", prompt)

    def test_processed_evidence_separates_confirmed_and_missing_skills(self) -> None:
        evidence = build_prompt_evidence(self.profile, self.job, self.result)

        candidate = evidence["candidate_confirmed_facts"]
        match = evidence["jobcompass_match_analysis"]
        self.assertEqual(candidate["confirmed_skills"], ["Python"])
        self.assertEqual(match["confirmed_matching_skills"], ["Python"])
        self.assertEqual(
            match["missing_or_unconfirmed_required_skills"], ["Docker"]
        )
        self.assertNotIn("email", candidate)

    def test_evidence_summary_explains_gaps_before_copying_prompt(self) -> None:
        summary = build_evidence_summary(self.profile, self.job, self.result)

        self.assertIn("ПІДТВЕРДЖЕНІ ДАНІ КАНДИДАТА", summary)
        self.assertIn("Не підтверджені вимоги: Docker", summary)
        self.assertIn("Email і телефон навмисно не додаються", summary)

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

        self.assertIn("Sehr geehrte Damen und Herren", draft)
        self.assertIn("Mit freundlichen Grüßen", draft)
        self.assertIn("Verfasse ein individuelles, professionelles Anschreiben", prompt)
        self.assertIn("Erfinde keine Fähigkeiten", prompt)
        self.assertIn("professionelles, idiomatisches Deutsch", prompt)


if __name__ == "__main__":
    unittest.main()
