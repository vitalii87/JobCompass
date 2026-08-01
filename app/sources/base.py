"""Contracts shared by job source connectors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.core.models import JobPosting


@dataclass(frozen=True, slots=True)
class SearchQuery:
    roles: tuple[str, ...] = ()
    locations: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    remote_only: bool = False


class JobSource(Protocol):
    """A connector that returns normalized vacancies."""

    name: str

    def search(self, query: SearchQuery) -> list[JobPosting]: ...
