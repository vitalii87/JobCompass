"""Connector for Arbeitnow's public, keyless European job API."""

from __future__ import annotations

from app.core.models import JobPosting, WorkMode
from app.parsing import enrich_job_posting
from app.sources.base import SearchQuery
from app.sources.filtering import matches_query
from app.sources.http import JsonHttpClient, SourceError
from app.sources.utils import html_to_text, parse_published_at, text_value


class ArbeitnowSource:
    name = "Arbeitnow"
    endpoint = "https://www.arbeitnow.com/api/job-board-api"

    def __init__(self, client: JsonHttpClient | None = None, max_pages: int = 2) -> None:
        self.client = client or JsonHttpClient()
        self.max_pages = max(1, max_pages)

    def search(self, query: SearchQuery) -> list[JobPosting]:
        jobs: dict[str, JobPosting] = {}
        for page in range(1, self.max_pages + 1):
            payload = self.client.get_json(self.endpoint, {"page": page})
            rows = payload.get("data")
            if not isinstance(rows, list):
                raise SourceError("Arbeitnow не повернув список вакансій")
            for row in rows:
                if not isinstance(row, dict):
                    continue
                job = self._normalize(row)
                if job is not None and matches_query(job, query):
                    jobs[job.job_id] = job
            meta = payload.get("meta")
            if not rows or (
                isinstance(meta, dict)
                and isinstance(meta.get("last_page"), int)
                and page >= meta["last_page"]
            ):
                break
        return list(jobs.values())

    @classmethod
    def _normalize(cls, row: dict[str, object]) -> JobPosting | None:
        slug = text_value(row.get("slug"))
        title = text_value(row.get("title"))
        company = text_value(row.get("company_name"), "Невідомий роботодавець")
        if not slug or not title:
            return None
        remote = row.get("remote") is True
        job_types = row.get("job_types")
        employment_type = (
            ", ".join(str(item) for item in job_types if str(item).strip())
            if isinstance(job_types, list)
            else None
        )
        return enrich_job_posting(
            JobPosting(
                source=cls.name,
                external_id=slug,
                title=title,
                company=company,
                location=text_value(row.get("location")),
                url=text_value(row.get("url")),
                description=html_to_text(row.get("description")),
                remote=remote,
                work_mode=WorkMode.REMOTE if remote else WorkMode.UNKNOWN,
                employment_type=employment_type,
                published_at=parse_published_at(row.get("created_at")),
            )
        )
