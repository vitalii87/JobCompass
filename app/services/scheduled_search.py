"""Headless scheduled vacancy search for one saved candidate profile."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone

from app.core.deduplication import deduplicate_jobs
from app.core.models import JobPosting
from app.core.search import SearchFilters, search_jobs
from app.sources import ONLINE_SOURCE_TYPES, SearchQuery
from app.storage import LocalJsonStore


@dataclass(frozen=True, slots=True)
class ScheduledSearchReport:
    profile_id: str
    matched_count: int
    new_count: int
    source_counts: dict[str, int]
    errors: dict[str, str]
    skipped: bool = False


def fresh_scheduled_jobs(
    jobs: list[JobPosting],
    last_run_at: datetime | None,
    *,
    now: datetime | None = None,
) -> list[JobPosting]:
    """Return reliably dated jobs published since the last scheduled run.

    Some sources expose only a calendar date. Comparing local calendar dates
    prevents those vacancies from being lost because their time is represented
    as midnight. Jobs with no valid publication date remain available in normal
    search, but are not labelled as fresh scheduled discoveries.
    """
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    baseline = last_run_at or (current - timedelta(hours=24))
    if baseline.tzinfo is None:
        baseline = baseline.replace(tzinfo=timezone.utc)
    earliest_date = baseline.astimezone().date()
    latest_date = current.astimezone().date()

    fresh: list[JobPosting] = []
    for job in jobs:
        published_at = job.published_at
        if published_at is None:
            continue
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=timezone.utc)
        if earliest_date <= published_at.astimezone().date() <= latest_date:
            fresh.append(job)
    return fresh


def run_scheduled_search(
    store: LocalJsonStore,
    profile_id: str,
    *,
    force: bool = False,
) -> ScheduledSearchReport:
    """Run a saved search without displaying the GUI."""
    original_profile_id = store.active_profile_id
    store.set_profile_context(profile_id)
    try:
        schedule = store.load_schedule()
        if not force and not schedule.is_due():
            return ScheduledSearchReport(profile_id, 0, 0, {}, {}, skipped=True)
        profile = store.load_profile()
        if profile is None:
            raise ValueError("Candidate profile is empty")
        preferences = store.load_search_preferences()
        source_instances = {
            source_type.name: source_type() for source_type in ONLINE_SOURCE_TYPES
        }
        source_names = preferences.sources or tuple(source_instances)
        online_names = tuple(
            name for name in source_names if name in source_instances
        )
        if not online_names:
            raise ValueError("Scheduled search has no online sources")
        roles = preferences.roles or profile.desired_roles
        if not roles and not preferences.keywords:
            raise ValueError("Scheduled search requires at least one desired role")
        if not preferences.locations:
            raise ValueError("Scheduled search requires at least one saved city")

        filters = SearchFilters(
            sources=source_names,
            roles=roles,
            keywords=preferences.keywords,
            locations=tuple(item.name for item in preferences.locations),
            location_selections=preferences.locations,
            location_radius_km=preferences.radius_km,
            excluded_keywords=preferences.excluded_keywords,
            excluded_companies=preferences.excluded_companies,
            remote_only=preferences.remote_only,
            minimum_score=preferences.minimum_score,
        )
        query = SearchQuery(
            roles=filters.roles,
            locations=filters.locations,
            location_selections=filters.location_selections,
            location_radius_km=filters.location_radius_km,
            remote_only=filters.remote_only,
        )
        query = replace(query, keywords=())
        online_jobs: list[JobPosting] = []
        counts: dict[str, int] = {}
        errors: dict[str, str] = {}
        for name in online_names:
            source = source_instances[name]
            try:
                found = source.search(query)
            except Exception as error:
                errors[name] = str(error)
                continue
            online_jobs.extend(found)
            counts[name] = len(found)
            partial_error = getattr(source, "last_partial_error", "")
            if partial_error:
                errors[name] = f"Partial results: {partial_error}"

        if online_jobs:
            store.save_jobs(online_jobs)
        selected_online_sources = set(online_names)
        current_jobs = deduplicate_jobs(
            [
                *online_jobs,
                *(
                    job
                    for job in store.list_jobs()
                    if job.source not in selected_online_sources
                    and job.source in filters.sources
                ),
            ]
        )
        ranked = search_jobs(
            profile,
            current_jobs,
            filters,
            location_prefiltered_job_ids=frozenset(
                job.job_id for job in online_jobs
            ),
        )
        result_ids = [item.job.job_id for item in ranked]
        store.save_last_result_job_ids(result_ids)
        fresh_ids = [
            job.job_id
            for job in fresh_scheduled_jobs(
                [item.job for item in ranked], schedule.last_run_at
            )
        ]
        new_count = store.record_job_discoveries(fresh_ids)
        successful_sources = {
            name for name in online_names if name not in errors or counts.get(name, 0)
        }
        if successful_sources:
            store.mark_schedule_run()
        return ScheduledSearchReport(
            profile_id=profile_id,
            matched_count=len(ranked),
            new_count=new_count,
            source_counts=counts,
            errors=errors,
        )
    finally:
        store.set_profile_context(original_profile_id)
