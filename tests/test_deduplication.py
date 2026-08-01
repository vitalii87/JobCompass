from __future__ import annotations

import unittest

from app.core.deduplication import deduplicate_jobs, job_fingerprint
from app.core.models import JobPosting


class DeduplicationTests(unittest.TestCase):
    def test_same_job_from_different_sources_is_deduplicated(self) -> None:
        first = JobPosting(
            source="source-a",
            external_id="1",
            title="Python Developer",
            company="Example GmbH",
            location="Berlin",
        )
        second = JobPosting(
            source="source-b",
            external_id="99",
            title=" python  developer ",
            company="EXAMPLE GMBH",
            location="Berlin,",
        )

        self.assertEqual(job_fingerprint(first), job_fingerprint(second))
        self.assertEqual(deduplicate_jobs([first, second]), [first])

    def test_tracking_parameters_do_not_make_urls_unique(self) -> None:
        first = JobPosting(
            source="source-a",
            external_id="1",
            title="Developer",
            company="One",
            url="https://example.test/job/1?utm_source=a",
        )
        second = JobPosting(
            source="source-b",
            external_id="2",
            title="Engineer",
            company="Two",
            url="https://example.test/job/1?utm_source=b",
        )

        self.assertEqual(deduplicate_jobs([first, second]), [first])


if __name__ == "__main__":
    unittest.main()
