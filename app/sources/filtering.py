"""Common local filtering used after an online source response."""

from __future__ import annotations

from app.core.models import JobPosting
from app.core.taxonomy import text_matches_keyword
from app.sources.base import SearchQuery


def matches_query(
    job: JobPosting,
    query: SearchQuery,
    *,
    location_prefiltered: bool = False,
) -> bool:
    if query.roles and not any(
        text_matches_keyword(job.title, role) for role in query.roles
    ):
        return False
    searchable = " ".join(
        (
            job.title,
            job.company,
            job.description,
            " ".join(job.required_skills),
            " ".join(job.preferred_skills),
        )
    )
    if query.keywords and not all(
        text_matches_keyword(searchable, keyword) for keyword in query.keywords
    ):
        return False
    if query.remote_only and not job.is_remote:
        return False
    if query.location_queries and not location_prefiltered and not job.is_remote:
        location = job.location.casefold()
        if not any(item.name.casefold() in location for item in query.location_queries):
            return False
    return True
