from __future__ import annotations

import threading
import time
import unittest

from app.core.models import JobPosting
from app.sources import (
    SearchOrchestrator,
    SearchQuery,
    SourceAccess,
    SourceCapabilities,
)


class _ConcurrentSource:
    capabilities = SourceCapabilities(access=SourceAccess.OFFICIAL_API)

    def __init__(self, name: str, barrier: threading.Barrier) -> None:
        self.name = name
        self.barrier = barrier

    def search(self, _query: SearchQuery) -> list[JobPosting]:
        self.barrier.wait(timeout=2)
        return [JobPosting(self.name, "1", f"{self.name} job", "ACME")]


class _BrokenSource:
    name = "Broken"
    capabilities = SourceCapabilities(access=SourceAccess.PUBLIC_FEED)

    def search(self, _query: SearchQuery) -> list[JobPosting]:
        raise ValueError("temporary failure")


class _SlowSource:
    name = "Slow"
    capabilities = SourceCapabilities(access=SourceAccess.PUBLIC_FEED)

    def search(self, _query: SearchQuery) -> list[JobPosting]:
        time.sleep(2.0)
        return []


class SearchOrchestratorTests(unittest.TestCase):
    def test_sources_run_concurrently_and_one_failure_keeps_other_results(self) -> None:
        barrier = threading.Barrier(2)
        sources = (
            _ConcurrentSource("One", barrier),
            _ConcurrentSource("Two", barrier),
            _BrokenSource(),
        )

        batch = SearchOrchestrator(max_concurrency=3).search_sync(
            sources, SearchQuery()
        )

        self.assertEqual({job.source for job in batch.jobs}, {"One", "Two"})
        self.assertEqual(batch.counts, {"One": 1, "Two": 1, "Broken": 0})
        self.assertIn("temporary failure", batch.errors["Broken"])

    def test_progress_callback_cannot_break_a_search(self) -> None:
        barrier = threading.Barrier(1)

        batch = SearchOrchestrator().search_sync(
            (_ConcurrentSource("One", barrier),),
            SearchQuery(),
            lambda *_args: (_ for _ in ()).throw(RuntimeError("UI closed")),
        )

        self.assertEqual(len(batch.jobs), 1)

    def test_timeout_returns_without_waiting_for_blocking_worker_shutdown(self) -> None:
        started = time.monotonic()

        batch = SearchOrchestrator(source_timeout_seconds=1.0).search_sync(
            (_SlowSource(),), SearchQuery()
        )

        self.assertLess(time.monotonic() - started, 1.5)
        self.assertIn("Slow", batch.errors)


if __name__ == "__main__":
    unittest.main()
