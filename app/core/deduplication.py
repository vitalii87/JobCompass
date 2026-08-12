"""Conservative duplicate detection for normalized vacancies."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from urllib.parse import urlsplit, urlunsplit

from app.core.models import JobPosting


_NON_WORDS = re.compile(r"[^\w]+", re.UNICODE)


def _normalize_text(value: str) -> str:
    return " ".join(_NON_WORDS.sub(" ", value.casefold()).split())


def _normalize_url(value: str) -> str:
    if not value:
        return ""
    parts = urlsplit(value)
    return urlunsplit(
        (parts.scheme.casefold(), parts.netloc.casefold(), parts.path.rstrip("/"), "", "")
    )


def job_fingerprint(job: JobPosting) -> str:
    """Build a stable key from title, company, and location."""

    identity = "\x1f".join(
        (
            _normalize_text(job.title),
            _normalize_text(job.company),
            _normalize_text(job.location),
        )
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]


def deduplicate_jobs(jobs: Iterable[JobPosting]) -> list[JobPosting]:
    """Merge repeats while preferring the richest direct-company record."""

    unique, _ = deduplicate_jobs_with_aliases(jobs)
    return unique


def deduplicate_jobs_with_aliases(
    jobs: Iterable[JobPosting],
) -> tuple[list[JobPosting], dict[str, str]]:
    """Return canonical records and old-to-canonical job-id aliases.

    The aliases let persistent stores retain favorites, viewed dates, cover
    letters, and application history when a richer direct-company record
    replaces the same vacancy previously found through an aggregator.
    """

    items = list(jobs)
    if not items:
        return [], {}

    parents = list(range(len(items)))

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parents[max(left_root, right_root)] = min(left_root, right_root)

    identity_indexes: dict[tuple[str, str], int] = {}
    for index, job in enumerate(items):
        identities = [("id", job.job_id), ("fingerprint", job_fingerprint(job))]
        normalized_url = _normalize_url(job.url)
        if normalized_url:
            identities.append(("url", normalized_url))
        for identity in identities:
            previous = identity_indexes.get(identity)
            if previous is None:
                identity_indexes[identity] = index
            else:
                union(index, previous)

    groups: dict[int, list[int]] = {}
    for index in range(len(items)):
        groups.setdefault(find(index), []).append(index)

    unique: list[JobPosting] = []
    aliases: dict[str, str] = {}
    for indexes in sorted(groups.values(), key=min):
        selected_index = max(indexes, key=lambda item: _record_quality(items[item]))
        selected = items[selected_index]
        unique.append(selected)
        for index in indexes:
            aliases[items[index].job_id] = selected.job_id
    return unique, aliases


def _record_quality(job: JobPosting) -> tuple[int, int, int, int]:
    """Rank duplicate records without changing their match score."""

    direct_sources = {
        "Company career pages",
        "Greenhouse careers",
        "Lever careers",
        "Ashby careers",
        "Personio careers",
        "Workday careers",
    }
    return (
        int(job.source in direct_sources),
        int(bool(job.description)),
        int(job.published_at is not None),
        len(job.description),
    )
