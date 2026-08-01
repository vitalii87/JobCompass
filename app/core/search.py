"""Filtering and ranking of locally normalized vacancies."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.location import LocationQuery, build_location_queries
from app.core.matcher import JobMatcher
from app.core.models import CandidateProfile, JobPosting, MatchResult
from app.core.taxonomy import text_matches_keyword


def _clean(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(value.strip() for value in values if value.strip())


@dataclass(frozen=True, slots=True)
class SearchFilters:
    sources: tuple[str, ...] = ()
    roles: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    locations: tuple[str, ...] = ()
    location_radius_km: float | None = None
    excluded_keywords: tuple[str, ...] = ()
    excluded_companies: tuple[str, ...] = ()
    remote_only: bool = False
    minimum_score: int = 0

    def __post_init__(self) -> None:
        for field_name in (
            "sources",
            "roles",
            "keywords",
            "locations",
            "excluded_keywords",
            "excluded_companies",
        ):
            object.__setattr__(self, field_name, _clean(getattr(self, field_name)))
        if not 0 <= self.minimum_score <= 100:
            raise ValueError("minimum_score must be between 0 and 100")
        if self.location_radius_km is not None:
            if isinstance(self.location_radius_km, bool):
                raise ValueError("location_radius_km must be a number or null")
            radius = float(self.location_radius_km)
            if not 0 < radius <= 500:
                raise ValueError("location_radius_km must be between 0 and 500")
            object.__setattr__(self, "location_radius_km", radius)

    @property
    def location_queries(self) -> tuple[LocationQuery, ...]:
        return build_location_queries(self.locations, self.location_radius_km)


@dataclass(frozen=True, slots=True)
class RankedJob:
    job: JobPosting
    match: MatchResult


def search_jobs(
    profile: CandidateProfile,
    jobs: list[JobPosting],
    filters: SearchFilters,
    matcher: JobMatcher | None = None,
) -> list[RankedJob]:
    scorer = matcher or JobMatcher()
    source_keys = {value.casefold() for value in filters.sources}
    location_keys = tuple(query.name.casefold() for query in filters.location_queries)
    excluded_keys = tuple(value.casefold() for value in filters.excluded_keywords)
    excluded_companies = tuple(
        value.casefold() for value in filters.excluded_companies
    )

    ranked: list[RankedJob] = []
    for job in jobs:
        if source_keys and job.source.casefold() not in source_keys:
            continue
        if filters.remote_only and not job.is_remote:
            continue
        if location_keys and not job.is_remote:
            location = job.location.casefold()
            if not any(value in location for value in location_keys):
                continue
        if excluded_companies and any(
            value in job.company.casefold() for value in excluded_companies
        ):
            continue

        searchable = " ".join(
            (
                job.title,
                job.company,
                job.description,
                " ".join(job.required_skills),
                " ".join(job.preferred_skills),
            )
        ).casefold()
        if filters.roles and not any(
            text_matches_keyword(job.title, role) for role in filters.roles
        ):
            continue
        if filters.keywords and not all(
            text_matches_keyword(searchable, value) for value in filters.keywords
        ):
            continue
        if excluded_keys and any(
            text_matches_keyword(searchable, value)
            for value in filters.excluded_keywords
        ):
            continue

        result = scorer.match(profile, job)
        if result.score >= filters.minimum_score:
            ranked.append(RankedJob(job=job, match=result))

    ranked.sort(key=lambda item: (-item.match.score, item.job.title.casefold()))
    return ranked
