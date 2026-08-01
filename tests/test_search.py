from __future__ import annotations

import unittest

from app.core.models import CandidateProfile, JobPosting
from app.core.search import SearchFilters, search_jobs


class SearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = CandidateProfile(
            desired_roles=("Python Developer",), skills=("Python",)
        )
        self.jobs = [
            JobPosting(
                source="board-a",
                external_id="1",
                title="Python Developer",
                company="Good GmbH",
                location="Berlin",
                required_skills=("Python",),
                remote=True,
            ),
            JobPosting(
                source="board-b",
                external_id="2",
                title="Java Developer",
                company="Skip GmbH",
                location="Munich",
                required_skills=("Java",),
                remote=False,
            ),
        ]

    def test_sources_keywords_remote_and_score_are_applied(self) -> None:
        results = search_jobs(
            self.profile,
            self.jobs,
            SearchFilters(
                sources=("board-a",),
                keywords=("Python",),
                remote_only=True,
                minimum_score=80,
            ),
        )

        self.assertEqual([item.job.job_id for item in results], ["board-a:1"])
        self.assertEqual(results[0].match.score, 100)

    def test_exclusions_remove_jobs(self) -> None:
        results = search_jobs(
            self.profile,
            self.jobs,
            SearchFilters(excluded_companies=("Good",), excluded_keywords=("Java",)),
        )

        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
