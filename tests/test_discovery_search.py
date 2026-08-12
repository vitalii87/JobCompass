from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.core.models import JobPosting
from app.core.source_registry import AtsType, SourceRegistryEntry, SourceRegistryStatus
from app.services.discovery_search import DiscoverySearchCoordinator, SearchProgress
from app.sources import (
    LeverCareerSource,
    SearchQuery,
    SourceAccess,
    SourceCapabilities,
)
from app.sources.discovery import DiscoveryReport
from app.storage import LocalJsonStore


class _StaticSource:
    capabilities = SourceCapabilities(access=SourceAccess.PUBLIC_CAREER_PAGE)

    def __init__(self, name: str, job: JobPosting) -> None:
        self.name = name
        self.job = job

    def search(self, _query: SearchQuery) -> list[JobPosting]:
        return [self.job]


class _Discoverer:
    def discover(
        self,
        _jobs: list[JobPosting],
        _query: SearchQuery,
        *,
        known_urls: tuple[str, ...] = (),
    ) -> DiscoveryReport:
        entry = SourceRegistryEntry(
            company="Acme",
            career_url="https://jobs.lever.co/acme",
            ats_type=AtsType.LEVER,
            country="DE",
        )
        return DiscoveryReport(
            entries=() if entry.career_url in known_urls else (entry,),
            pages_checked=1,
        )


class _TwoLeverBoardsClient:
    def get_json_value(
        self,
        url: str,
        _params: dict[str, object] | None = None,
    ) -> object:
        if url.endswith("/working"):
            return [
                {
                    "id": "1",
                    "text": "QA Engineer",
                    "categories": {"location": "Stuttgart"},
                }
            ]
        raise ValueError("board unavailable")


class DiscoverySearchCoordinatorTests(unittest.TestCase):
    def test_new_source_is_saved_and_queried_in_the_same_search(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = LocalJsonStore(Path(directory) / "store.json")
            store.initialize()
            aggregator_job = JobPosting(
                "Aggregator", "a", "QA Engineer", "Acme", url="https://a.test/a"
            )
            direct_job = JobPosting(
                "Lever careers",
                "d",
                "QA Engineer",
                "Acme",
                url="https://jobs.lever.co/acme/d",
            )

            def build(urls: tuple[str, ...] = ()) -> dict[str, _StaticSource]:
                sources = {
                    "Aggregator": _StaticSource("Aggregator", aggregator_job)
                }
                if "https://jobs.lever.co/acme" in urls:
                    sources["Lever careers"] = _StaticSource(
                        "Lever careers", direct_job
                    )
                return sources

            progress: list[SearchProgress] = []
            report = DiscoverySearchCoordinator(
                store,
                discoverer=_Discoverer(),  # type: ignore[arg-type]
                source_builder=build,  # type: ignore[arg-type]
            ).search(SearchQuery(roles=("QA Engineer",)), on_progress=progress.append)

            self.assertEqual([job.external_id for job in report.jobs], ["d"])
            self.assertEqual(report.collected_jobs, 2)
            self.assertEqual(report.discovered_sources, 1)
            self.assertTrue(progress)
            registry = store.list_source_registry()
            self.assertEqual(len(registry), 1)
            self.assertEqual(registry[0].status, SourceRegistryStatus.ACTIVE)

    def test_registry_health_is_recorded_per_board_not_per_ats_group(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = LocalJsonStore(Path(directory) / "store.json")
            store.initialize()
            store.save_source_registry(
                [
                    SourceRegistryEntry(
                        company="Working",
                        career_url="https://jobs.lever.co/working",
                        ats_type=AtsType.LEVER,
                    ),
                    SourceRegistryEntry(
                        company="Broken",
                        career_url="https://jobs.lever.co/broken",
                        ats_type=AtsType.LEVER,
                    ),
                ]
            )
            source = LeverCareerSource(
                (("working", False), ("broken", False)),
                client=_TwoLeverBoardsClient(),  # type: ignore[arg-type]
            )
            jobs = source.search(SearchQuery())
            coordinator = DiscoverySearchCoordinator(store)

            coordinator._mark_registry_checks(
                {source.name: len(jobs)},
                {source.name: source.last_partial_error},
                (source,),
            )

            statuses = {
                entry.company: entry.status for entry in store.list_source_registry()
            }
            self.assertEqual(statuses["Working"], SourceRegistryStatus.ACTIVE)
            self.assertEqual(statuses["Broken"], SourceRegistryStatus.ERROR)


if __name__ == "__main__":
    unittest.main()
