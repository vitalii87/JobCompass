"""Connector for Remotive's public remote-jobs API."""

from __future__ import annotations

from app.core.models import JobPosting, WorkMode
from app.parsing import enrich_job_posting
from app.sources.base import SearchQuery
from app.sources.filtering import matches_query
from app.sources.http import JsonHttpClient, SourceError
from app.sources.utils import html_to_text, parse_published_at, text_value


class RemotiveSource:
    name = "Remotive"
    endpoint = "https://remotive.com/api/remote-jobs"

    def __init__(self, client: JsonHttpClient | None = None) -> None:
        self.client = client or JsonHttpClient()

    def search(self, query: SearchQuery) -> list[JobPosting]:
        terms = query.roles or query.keywords or ("",)
        jobs: dict[str, JobPosting] = {}
        for term in terms:
            payload = self.client.get_json(self.endpoint, {"search": term})
            rows = payload.get("jobs")
            if not isinstance(rows, list):
                raise SourceError("Remotive не повернув список вакансій")
            for row in rows:
                if not isinstance(row, dict):
                    continue
                job = self._normalize(row)
                if (
                    job is not None
                    and self._location_is_compatible(job.location, query)
                    and matches_query(job, query)
                ):
                    jobs[job.job_id] = job
        return list(jobs.values())

    @staticmethod
    def _location_is_compatible(location: str, query: SearchQuery) -> bool:
        if not query.locations:
            return True
        normalized = location.casefold()
        broad_regions = ("worldwide", "anywhere", "europe", "emea", "germany")
        return any(region in normalized for region in broad_regions) or any(
            item.name.casefold() in normalized for item in query.location_queries
        )
    @classmethod
    def _normalize(cls, row: dict[str, object]) -> JobPosting | None:
        external_id = str(row.get("id", "")).strip()
        title = text_value(row.get("title"))
        if not external_id or not title:
            return None
        tags = row.get("tags")
        tag_text = "\nTags: " + ", ".join(str(item) for item in tags) if isinstance(tags, list) else ""
        return enrich_job_posting(
            JobPosting(
                source=cls.name,
                external_id=external_id,
                title=title,
                company=text_value(row.get("company_name"), "Невідомий роботодавець"),
                location=text_value(row.get("candidate_required_location"), "Remote"),
                url=text_value(row.get("url")),
                description=html_to_text(row.get("description")) + tag_text,
                remote=True,
                work_mode=WorkMode.REMOTE,
                employment_type=text_value(row.get("job_type")) or None,
                published_at=parse_published_at(row.get("publication_date")),
            )
        )
