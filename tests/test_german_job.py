from __future__ import annotations

import unittest

from app.core.matcher import JobMatcher
from app.core.models import CandidateProfile, JobPosting, WorkMode
from app.core.taxonomy import canonical_role, canonical_skill, text_matches_keyword
from app.parsing.german_job import detect_text_language, enrich_job_posting


GERMAN_DESCRIPTION = """Ihr Profil
Fundierte Kenntnisse in Python und SQL sind erforderlich.
Erfahrung mit Docker ist von Vorteil.
Mindestens 2 Jahre Berufserfahrung.
Sehr gute Deutschkenntnisse.
Wir bieten
Hybrides Arbeiten mit zwei Tagen Homeoffice.
"""


class GermanJobParserTests(unittest.TestCase):
    def test_german_requirements_are_structured_with_evidence(self) -> None:
        job = enrich_job_posting(
            JobPosting(
                source="test",
                external_id="de-1",
                title="Python Softwareentwickler (m/w/d)",
                company="Beispiel GmbH",
                description=GERMAN_DESCRIPTION,
            )
        )

        self.assertEqual(job.required_skills, ("Python", "SQL"))
        self.assertEqual(job.preferred_skills, ("Docker",))
        self.assertEqual(job.minimum_years_experience, 2)
        self.assertEqual(job.required_languages, ("German",))
        self.assertEqual(job.work_mode, WorkMode.HYBRID)
        self.assertTrue(
            any("Fundierte Kenntnisse" in item.excerpt for item in job.requirement_evidence)
        )
        self.assertEqual(JobPosting.from_dict(job.to_dict()), job)

    def test_inline_german_heading_is_supported(self) -> None:
        job = enrich_job_posting(
            JobPosting(
                source="test",
                external_id="inline",
                title="Entwickler",
                company="Beispiel GmbH",
                description="Ihr Profil: Fundierte Kenntnisse in Python sind erforderlich.",
            )
        )

        self.assertEqual(job.required_skills, ("Python",))

    def test_negative_requirement_is_not_extracted(self) -> None:
        job = enrich_job_posting(
            JobPosting(
                source="test",
                external_id="de-2",
                title="Softwareentwickler",
                company="Beispiel GmbH",
                description="Docker ist keine Voraussetzung und kann erlernt werden.",
            )
        )

        self.assertNotIn("Docker", job.required_skills)
        self.assertNotIn("Docker", job.preferred_skills)

    def test_de_en_taxonomy_supports_matching_and_search(self) -> None:
        profile = CandidateProfile(
            desired_roles=("Python Developer",),
            skills=("Python-Entwicklung", "SQL"),
            languages=("Deutsch B2",),
            years_experience=3,
        )
        job = enrich_job_posting(
            JobPosting(
                source="test",
                external_id="de-3",
                title="Python-Entwickler",
                company="Beispiel GmbH",
                description=GERMAN_DESCRIPTION,
            )
        )

        result = JobMatcher().match(profile, job)

        self.assertEqual(canonical_skill("Python-Entwicklung"), "Python")
        self.assertEqual(canonical_role("Senior Softwareentwickler"), "Software Developer")
        self.assertTrue(text_matches_keyword(job.title, "Python Developer"))
        self.assertGreaterEqual(result.score, 85)
        self.assertFalse(any("languages" in risk for risk in result.risks))

    def test_language_detection_prefers_german_signals(self) -> None:
        self.assertEqual(detect_text_language(GERMAN_DESCRIPTION), "de")
        self.assertEqual(detect_text_language("Requirements and responsibilities"), "en")


if __name__ == "__main__":
    unittest.main()
