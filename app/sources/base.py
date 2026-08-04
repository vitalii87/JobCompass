"""Contracts shared by job source connectors."""

from __future__ import annotations

from dataclasses import dataclass
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

    @property
    def location_queries(self) -> tuple[LocationQuery, ...]:
        return build_location_queries(
            self.locations,
            self.location_radius_km,
            self.location_selections,
        )


class JobSource(Protocol):
    """A connector that returns normalized vacancies."""

    name: str

    def search(self, query: SearchQuery) -> list[JobPosting]: ...
