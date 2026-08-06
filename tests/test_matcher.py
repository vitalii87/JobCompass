from __future__ import annotations

import unittest

from app.core.matcher import JobMatcher
from app.core.models import CandidateProfile, JobPosting, MatchLevel


class JobMatcherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.matcher = JobMatcher()
        self.profile = CandidateProfile(
            desired_roles=("Python Developer",),
            skills=("Python", "SQL", "Git"),
            languages=("English",),
            years_experience=3,
            preferred_locations=("Berlin",),
        )

    def test_match_is_weighted_and_explained(self) -> None:
        job = JobPosting(
            source="test",
            external_id="1",
            title="Senior Python Developer",
            company="ACME",
            location="Berlin",
            required_skills=("Python", "Docker"),
            preferred_skills=("Git",),
            required_languages=("English",),
            minimum_years_experience=2,
            remote=False,
        )

        result = self.matcher.match(self.profile, job)

        self.assertEqual(result.score, 81)
        self.assertEqual(result.level, MatchLevel.PARTIAL)
        self.assertEqual(result.component_scores["skills"], 62)
        self.assertEqual(result.matched_skills, ("Python", "Git"))
        self.assertEqual(result.missing_required_skills, ("Docker",))
        self.assertTrue(any("Docker" in risk for risk in result.risks))

    def test_high_score_without_critical_gaps_is_a_full_match(self) -> None:
        job = JobPosting(
            source="test",
            external_id="full",
            title="Python Developer",
            company="ACME",
            location="Berlin",
            required_skills=("Python", "SQL"),
            required_languages=("English",),
            minimum_years_experience=2,
        )

        result = self.matcher.match(self.profile, job)

        self.assertEqual(result.score, 100)
        self.assertEqual(result.level, MatchLevel.FULL)

    def test_mismatches_produce_a_weak_result(self) -> None:
        job = JobPosting(
            source="test",
            external_id="2",
            title="Data Scientist",
            company="ACME",
            required_skills=("R",),
        )

        result = self.matcher.match(self.profile, job)

        self.assertEqual(result.score, 0)
        self.assertEqual(result.level, MatchLevel.WEAK)
        self.assertEqual(result.missing_required_skills, ("R",))

    def test_missing_structured_data_does_not_invent_a_match(self) -> None:
        profile = CandidateProfile()
        job = JobPosting(
            source="test", external_id="3", title="Unknown", company="ACME"
        )

        result = self.matcher.match(profile, job)

        self.assertEqual(result.score, 0)
        self.assertTrue(any("Not enough" in risk for risk in result.risks))

    def test_role_only_match_is_capped_by_low_evidence_coverage(self) -> None:
        profile = CandidateProfile(desired_roles=("Office Manager",))
        job = JobPosting(
            source="test",
            external_id="role-only",
            title="Office Manager",
            company="ACME",
        )

        result = self.matcher.match(profile, job)

        self.assertEqual(result.component_scores["role"], 100)
        self.assertEqual(result.evidence_coverage, 25)
        self.assertEqual(result.score, 62)
        self.assertEqual(result.level, MatchLevel.PARTIAL)
        self.assertTrue(any("Low evidence coverage" in risk for risk in result.risks))


if __name__ == "__main__":
    unittest.main()
