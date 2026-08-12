"""One-button search coordinator with automatic source learning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlsplit

from app.core.deduplication import deduplicate_jobs
from app.core.models import JobPosting
from app.core.source_registry import (
    AtsType,
    SOURCE_NAME_BY_ATS,
    SourceRegistryEntry,
    SourceRegistryStatus,
    normalize_registry_url,
)
from app.sources import JobSource, SearchOrchestrator, SearchQuery, build_online_sources
from app.sources.discovery import AutomaticSourceDiscoverer
from app.storage import LocalJsonStore


@dataclass(frozen=True, slots=True)
class SearchProgress:
    checked_sources: int
    total_sources: int
    discovered_sources: int
    collected_jobs: int
    stage: str = "search"


@dataclass(frozen=True, slots=True)
class DiscoverySearchReport:
    jobs: tuple[JobPosting, ...]
    counts: dict[str, int]
    errors: dict[str, str]
    checked_sources: int
    discovered_sources: int
    discovery_pages_checked: int
    collected_jobs: int


class DiscoverySearchCoordinator:
    def __init__(
        self,
        store: LocalJsonStore,
        *,
        orchestrator: SearchOrchestrator | None = None,
        discoverer: AutomaticSourceDiscoverer | None = None,
        source_builder: (
            Callable[[tuple[str, ...]], dict[str, JobSource]] | None
        ) = None,
    ) -> None:
        self.store = store
        self.orchestrator = orchestrator or SearchOrchestrator()
        self.discoverer = discoverer or AutomaticSourceDiscoverer()
        self.source_builder = source_builder or build_online_sources

    def search(
        self,
        query: SearchQuery,
        *,
        selected_source_names: tuple[str, ...] = (),
        on_progress: Callable[[SearchProgress], None] | None = None,
    ) -> DiscoverySearchReport:
        registry_before = self.store.list_source_registry()
        blocked_urls = {
            entry.career_url
            for entry in registry_before
            if entry.status
            in {SourceRegistryStatus.BLOCKED, SourceRegistryStatus.DISABLED}
        }
        registry_urls = tuple(
            entry.career_url
            for entry in registry_before
            if entry.status not in {
                SourceRegistryStatus.BLOCKED,
                SourceRegistryStatus.DISABLED,
            }
        )
        manual_urls = tuple(
            url
            for url in self.store.load_career_urls()
            if normalize_registry_url(url) not in blocked_urls
        )
        self._register_manual_urls(manual_urls)
        registry_current = self.store.list_source_registry()
        all_known_urls = tuple(dict.fromkeys((*registry_urls, *manual_urls)))
        source_instances = dict(self.source_builder(all_known_urls))
        if selected_source_names:
            selected = tuple(
                source
                for name, source in source_instances.items()
                if name in selected_source_names
            )
        else:
            selected = tuple(source_instances.values())

        discovered_count = 0
        initial_weights = self._source_weights(registry_current, selected)
        initial_total = sum(initial_weights.values())
        initial_checked = 0

        def initial_progress(_diagnostic, checked, total, collected) -> None:
            nonlocal initial_checked
            initial_checked += initial_weights.get(_diagnostic.source, 1)
            if on_progress is not None:
                on_progress(
                    SearchProgress(
                        checked_sources=initial_checked,
                        total_sources=initial_total,
                        discovered_sources=discovered_count,
                        collected_jobs=collected,
                    )
                )

        initial = self.orchestrator.search_sync(selected, query, initial_progress)
        discovery = self.discoverer.discover(
            list(initial.jobs),
            query,
            known_urls=all_known_urls,
        )
        discovered_count = self.store.upsert_source_registry(list(discovery.entries))

        new_sources = dict(
            self.source_builder(
                tuple(entry.career_url for entry in discovery.entries)
            )
        )
        for standard_name in tuple(self.source_builder(())):
            new_sources.pop(standard_name, None)
        secondary_weights = self._source_weights(
            list(discovery.entries), tuple(new_sources.values())
        )
        secondary_total = sum(secondary_weights.values())

        if on_progress is not None:
            on_progress(
                SearchProgress(
                    checked_sources=initial_total,
                    total_sources=initial_total + secondary_total,
                    discovered_sources=discovered_count,
                    collected_jobs=len(initial.jobs),
                    stage="discovery",
                )
            )

        secondary_jobs: tuple[JobPosting, ...] = ()
        secondary_counts: dict[str, int] = {}
        secondary_errors: dict[str, str] = {}
        if new_sources:
            initial_collected = len(initial.jobs)
            secondary_checked = 0

            def secondary_progress(_diagnostic, checked, total, collected) -> None:
                nonlocal secondary_checked
                secondary_checked += secondary_weights.get(_diagnostic.source, 1)
                if on_progress is not None:
                    on_progress(
                        SearchProgress(
                            checked_sources=initial_total + secondary_checked,
                            total_sources=initial_total + secondary_total,
                            discovered_sources=discovered_count,
                            collected_jobs=initial_collected + collected,
                        )
                    )

            secondary = self.orchestrator.search_sync(
                tuple(new_sources.values()), query, secondary_progress
            )
            secondary_jobs = secondary.jobs
            secondary_counts = secondary.counts
            secondary_errors = secondary.errors

        counts = dict(initial.counts)
        for name, count in secondary_counts.items():
            counts[name] = counts.get(name, 0) + count
        errors = dict(initial.errors)
        for name, error in secondary_errors.items():
            errors[name] = "; ".join(
                part for part in (errors.get(name, ""), error) if part
            )
        jobs = tuple(deduplicate_jobs((*initial.jobs, *secondary_jobs)))
        self._mark_registry_checks(
            counts,
            errors,
            (*selected, *new_sources.values()),
        )
        checked_sources = initial_total + secondary_total
        return DiscoverySearchReport(
            jobs=jobs,
            counts=counts,
            errors=errors,
            checked_sources=checked_sources,
            discovered_sources=discovered_count,
            discovery_pages_checked=discovery.pages_checked,
            collected_jobs=len(initial.jobs) + len(secondary_jobs),
        )

    @staticmethod
    def _source_weights(
        entries: list[SourceRegistryEntry],
        sources: tuple[JobSource, ...],
    ) -> dict[str, int]:
        registered: dict[str, int] = {}
        for entry in entries:
            name = SOURCE_NAME_BY_ATS[entry.ats_type]
            registered[name] = registered.get(name, 0) + 1
        return {
            source.name: max(1, registered.get(source.name, 0))
            for source in sources
        }

    def _register_manual_urls(self, urls: tuple[str, ...]) -> None:
        entries: list[SourceRegistryEntry] = []
        from app.sources.discovery import detect_source_url

        for url in urls:
            detected = detect_source_url(
                url,
                allow_generic=True,
                discovered_from="manual",
            )
            entries.append(
                detected
                or SourceRegistryEntry(
                    company="",
                    career_url=url,
                    ats_type=AtsType.GENERIC_HTML,
                    discovered_from="manual",
                )
            )
        if entries:
            self.store.upsert_source_registry(entries)

    def _mark_registry_checks(
        self,
        counts: dict[str, int],
        errors: dict[str, str],
        sources: tuple[JobSource, ...],
    ) -> None:
        target_status: dict[tuple[str, str], str] = {}
        sources_with_target_status: set[str] = set()
        for source in sources:
            raw = getattr(source, "last_target_status", None)
            if not isinstance(raw, dict):
                continue
            sources_with_target_status.add(source.name)
            for key, error in raw.items():
                if isinstance(key, str) and isinstance(error, str):
                    target_status[(source.name, key.casefold())] = error

        updated: list[SourceRegistryEntry] = []
        for entry in self.store.list_source_registry():
            source_name = SOURCE_NAME_BY_ATS[entry.ats_type]
            target_key = self._registry_target_key(entry)
            target_error = target_status.get((source_name, target_key.casefold()))
            if target_error is not None:
                error = target_error
            elif source_name in sources_with_target_status:
                # A timed-out connector may not reach every target. Mark only
                # those as failed instead of applying another board's result.
                error = errors.get(source_name, "Source target was not checked")
            elif source_name in counts or source_name in errors:
                error = errors.get(source_name, "")
            else:
                updated.append(entry)
                continue
            succeeded = not error
            blocked = "robots.txt" in error or "policy" in error.casefold()
            updated.append(entry.checked(succeeded=succeeded, blocked=blocked))
        self.store.save_source_registry(updated)

    @staticmethod
    def _registry_target_key(entry: SourceRegistryEntry) -> str:
        parsed = urlsplit(entry.career_url)
        path_parts = [part for part in parsed.path.split("/") if part]
        if entry.ats_type in {AtsType.GREENHOUSE, AtsType.ASHBY} and path_parts:
            return path_parts[0]
        if entry.ats_type is AtsType.LEVER and path_parts:
            api_host = (
                "api.eu.lever.co"
                if parsed.hostname == "jobs.eu.lever.co"
                else "api.lever.co"
            )
            return f"{api_host}:{path_parts[0]}"
        if entry.ats_type is AtsType.PERSONIO:
            return parsed.netloc.casefold()
        return entry.career_url.rstrip("/")
