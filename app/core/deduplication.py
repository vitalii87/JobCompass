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
    """Keep the first vacancy when IDs, canonical URLs, or fingerprints repeat."""

    result: list[JobPosting] = []
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    seen_fingerprints: set[str] = set()

    for job in jobs:
        normalized_url = _normalize_url(job.url)
        fingerprint = job_fingerprint(job)
        if job.job_id in seen_ids:
            continue
        if normalized_url and normalized_url in seen_urls:
            continue
        if fingerprint in seen_fingerprints:
            continue

        result.append(job)
        seen_ids.add(job.job_id)
        if normalized_url:
            seen_urls.add(normalized_url)
        seen_fingerprints.add(fingerprint)

    return result
