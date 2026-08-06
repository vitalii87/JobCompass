"""Connector for Arbeitnow's public, keyless European job API."""

from __future__ import annotations

from time import monotonic

from app.core.models import JobPosting, WorkMode
from app.parsing import enrich_job_posting
from app.sources.base import SearchQuery
from app.sources.filtering import matches_query
from app.sources.http import JsonHttpClient, SourceError
from app.sources.utils import html_to_text, parse_published_at, text_value


class ArbeitnowSource:
    name = "Arbeitnow"
    endpoint = "https://www.arbeitnow.com/api/job-board-api"

    def __init__(
        self,
        client: JsonHttpClient | None = None,
        max_pages: int = 8,
        cache_ttl_seconds: float = 15 * 60,
    ) -> None:
        self.client = client or JsonHttpClient()
        self.max_pages = max(1, max_pages)
        self.cache_ttl_seconds = max(0.0, cache_ttl_seconds)
        self._page_cache: dict[int, tuple[float, dict[str, object]]] = {}
        self.last_partial_error = ""

    def search(self, query: SearchQuery) -> list[JobPosting]:
        jobs: dict[str, JobPosting] = {}
        loaded_pages = 0
        self.last_partial_error = ""
        for page in range(1, self.max_pages + 1):
            try:
                payload = self._load_page(page)
            except SourceError as error:
                if loaded_pages:
                    self.last_partial_error = str(error)
                    break
                raise
            loaded_pages += 1
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

    def _load_page(self, page: int) -> dict[str, object]:
        cached = self._page_cache.get(page)
        now = monotonic()
        if cached is not None and now - cached[0] <= self.cache_ttl_seconds:
            return cached[1]
        payload = self.client.get_json(self.endpoint, {"page": page})
        self._page_cache[page] = (now, payload)
        return payload

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
