from __future__ import annotations

import unittest

from app.core.models import CandidateProfile, JobPosting, WorkMode
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
        self.assertEqual(results[0].match.score, 88)

    def test_exclusions_remove_jobs(self) -> None:
        results = search_jobs(
            self.profile,
            self.jobs,
            SearchFilters(excluded_companies=("Good",), excluded_keywords=("Java",)),
        )

        self.assertEqual(results, [])

    def test_keyword_list_uses_and_logic(self) -> None:
        results = search_jobs(
            self.profile,
            self.jobs,
            SearchFilters(keywords=("Python", "missing phrase")),
        )

        self.assertEqual(results, [])

    def test_desired_role_list_uses_or_logic(self) -> None:
        results = search_jobs(
            self.profile,
            self.jobs,
            SearchFilters(roles=("Office Manager", "Python Developer")),
        )

        self.assertEqual([item.job.job_id for item in results], ["board-a:1"])

    def test_slider_radius_keeps_city_filter_for_local_json(self) -> None:
        filters = SearchFilters(locations=("Berlin",), location_radius_km=50)
        results = search_jobs(
            self.profile,
            self.jobs,
            filters,
        )

        self.assertEqual([item.job.job_id for item in results], ["board-a:1"])
        self.assertEqual(filters.location_queries[0].radius_km, 50)

    def test_invalid_slider_radius_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "between 0 and 500"):
            SearchFilters(locations=("Berlin",), location_radius_km=700)

    def test_server_radius_results_are_not_filtered_again_by_city_name(self) -> None:
        nearby_job = JobPosting(
            source="online",
            external_id="nearby",
            title="Python Developer",
            company="Nearby GmbH",
            location="Stuttgart",
            required_skills=("Python",),
        )
        filters = SearchFilters(locations=("Köngen",), location_radius_km=50)

        without_server_context = search_jobs(self.profile, [nearby_job], filters)
        with_server_context = search_jobs(
            self.profile,
            [nearby_job],
            filters,
            location_prefiltered_job_ids=frozenset({nearby_job.job_id}),
        )

        self.assertEqual(without_server_context, [])
        self.assertEqual(
            [item.job.job_id for item in with_server_context], [nearby_job.job_id]
        )

    def test_without_remote_only_all_work_modes_are_included(self) -> None:
        jobs = [
            JobPosting(
                source="modes",
                external_id=mode.value,
                title="Python Developer",
                company=mode.value,
                required_skills=("Python",),
                work_mode=mode,
            )
            for mode in (WorkMode.REMOTE, WorkMode.HYBRID, WorkMode.OFFICE)
        ]

        results = search_jobs(self.profile, jobs, SearchFilters(remote_only=False))

        self.assertEqual(len(results), 3)

    def test_remote_and_hybrid_filter_excludes_office_jobs(self) -> None:
        jobs = [
            JobPosting(
                source="modes",
                external_id=mode.value,
                title="Python Developer",
                company=mode.value,
                required_skills=("Python",),
                work_mode=mode,
            )
            for mode in (WorkMode.REMOTE, WorkMode.HYBRID, WorkMode.OFFICE)
        ]

        results = search_jobs(
            self.profile,
            jobs,
            SearchFilters(work_modes=(WorkMode.REMOTE, WorkMode.HYBRID)),
        )

        self.assertEqual(
            {item.job.work_mode for item in results},
            {WorkMode.REMOTE, WorkMode.HYBRID},
        )


if __name__ == "__main__":
    unittest.main()
