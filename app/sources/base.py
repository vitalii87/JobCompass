"""Contracts shared by job source connectors."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from time import monotonic
from typing import Protocol

from app.core.location import (
    LocationQuery,
    LocationSelection,
    build_location_queries,
)
from app.core.models import JobPosting


@dataclass(frozen=True, slots=True)
class SearchQuery:
    roles: tuple[str, ...] = ()
    locations: tuple[str, ...] = ()
    location_radius_km: float | None = None
    location_selections: tuple[LocationSelection, ...] = ()
    keywords: tuple[str, ...] = ()
    remote_only: bool = False
    deadline_monotonic: float | None = field(
        default=None,
        compare=False,
        repr=False,
    )

    @property
    def location_queries(self) -> tuple[LocationQuery, ...]:
        return build_location_queries(
            self.locations,
            self.location_radius_km,
            self.location_selections,
        )

    @property
    def expired(self) -> bool:
        return (
            self.deadline_monotonic is not None
            and monotonic() >= self.deadline_monotonic
        )


class SourceAccess(StrEnum):
    """How JobCompass is allowed to obtain vacancies from a source."""

    OFFICIAL_API = "official_api"
    PUBLIC_FEED = "public_feed"
    PUBLIC_CAREER_PAGE = "public_career_page"
    LOCAL_FILE = "local_file"


@dataclass(frozen=True, slots=True)
class SourceCapabilities:
    """Machine-readable behavior used by the search orchestrator and GUI."""

    access: SourceAccess
    supports_locations: bool = False
    supports_radius: bool = False
    supports_remote: bool = False
    supports_pagination: bool = False
    provides_full_description: bool = False
    provides_published_at: bool = False
    requires_api_key: bool = False


@dataclass(frozen=True, slots=True)
class SourceDiagnostic:
    source: str
    job_count: int
    elapsed_seconds: float
    error: str = ""
    partial: bool = False


@dataclass(frozen=True, slots=True)
class SourceBatch:
    """Normalized output from a parallel multi-source search."""

    jobs: tuple[JobPosting, ...] = ()
    diagnostics: tuple[SourceDiagnostic, ...] = ()
    counts: dict[str, int] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)


class JobSource(Protocol):
    """A connector that returns normalized vacancies."""

    name: str
    capabilities: SourceCapabilities

    def search(self, query: SearchQuery) -> list[JobPosting]: ...
