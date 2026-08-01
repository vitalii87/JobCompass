"""Connector for the German Federal Employment Agency Jobsuche service."""

from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from typing import Any
from urllib.parse import quote

from app.core.models import JobPosting, WorkMode
from app.parsing import enrich_job_posting
from app.sources.base import SearchQuery
from app.sources.filtering import matches_query
from app.sources.http import JsonHttpClient, SourceError
from app.sources.utils import parse_published_at, text_value


class BundesagenturSource:
    name = "Bundesagentur für Arbeit"
    search_endpoint = (
        "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs"
    )
    detail_endpoint = (
        "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobdetails"
    )
    headers = {"X-API-Key": "jobboerse-jobsuche"}

    def __init__(
        self,
        client: JsonHttpClient | None = None,
        max_results: int = 80,
        detail_workers: int = 6,
    ) -> None:
        self.client = client or JsonHttpClient()
        self.max_results = max(1, max_results)
        self.detail_workers = max(1, detail_workers)

    def search(self, query: SearchQuery) -> list[JobPosting]:
        roles = query.roles or query.keywords or ("",)
        locations = tuple(item.name for item in query.location_queries) or ("",)
        combination_count = max(1, len(roles) * len(locations))
        page_size = min(25, max(5, self.max_results // combination_count + 3))
        rows_by_reference: dict[str, dict[str, Any]] = {}

        for role in roles:
            for location in locations:
                params: dict[str, object] = {
                    "angebotsart": 1,
                    "page": 1,
                    "size": page_size,
                    "pav": "false",
                    "was": role,
                    "wo": location,
                    "umkreis": (
                        round(query.location_radius_km)
                        if location and query.location_radius_km is not None
                        else None
                    ),
                    "arbeitszeit": "ho" if query.remote_only else None,
                }
                payload = self.client.get_json(
                    self.search_endpoint, params, self.headers
                )
                rows = payload.get("stellenangebote")
                if rows is None and payload.get("maxErgebnisse") == 0:
                    continue
                if not isinstance(rows, list):
                    raise SourceError(
                        "Jobsuche Bundesagentur не повернула список вакансій"
                    )
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    reference = text_value(row.get("refnr"))
                    if reference:
                        rows_by_reference[reference] = row
                    if len(rows_by_reference) >= self.max_results:
                        break
                if len(rows_by_reference) >= self.max_results:
                    break
            if len(rows_by_reference) >= self.max_results:
                break

        rows = list(rows_by_reference.values())
        with ThreadPoolExecutor(max_workers=self.detail_workers) as executor:
            details = list(executor.map(self._load_detail_safely, rows))

        jobs: list[JobPosting] = []
        for row, detail in zip(rows, details, strict=True):
            job = self._normalize(row, detail)
            if job is not None and matches_query(job, query):
                jobs.append(job)
        return jobs

    def _load_detail_safely(self, row: dict[str, Any]) -> dict[str, Any]:
        reference = text_value(row.get("refnr"))
        if not reference:
            return {}
        encoded = base64.b64encode(reference.encode("utf-8")).decode("ascii")
        try:
            return self.client.get_json(
                f"{self.detail_endpoint}/{quote(encoded, safe='')}",
                headers=self.headers,
            )
        except SourceError:
            return {}

    @classmethod
    def _normalize(
        cls, row: dict[str, Any], detail: dict[str, Any]
    ) -> JobPosting | None:
        reference = text_value(row.get("refnr"))
        title = text_value(
            detail.get("stellenangebotsTitel"), text_value(row.get("titel"))
        )
        company = text_value(
            detail.get("firma"),
            text_value(row.get("arbeitgeber"), "Невідомий роботодавець"),
        )
        if not reference or not title:
            return None

        raw_location = row.get("arbeitsort")
        if isinstance(raw_location, dict):
            location_parts = [
                text_value(raw_location.get("ort")),
                text_value(raw_location.get("region")),
            ]
            location = ", ".join(part for part in location_parts if part)
        else:
            location = ""

        external_url = text_value(
            detail.get("externeURL"), text_value(row.get("externeUrl"))
        )
        url = external_url or (
            "https://www.arbeitsagentur.de/jobsuche/jobdetail/" + quote(reference)
        )
        employment_types: list[str] = []
        if detail.get("arbeitszeitVollzeit") is True:
            employment_types.append("Vollzeit")
        if any(
            detail.get(field) is True
            for field in (
                "arbeitszeitTeilzeitAbend",
                "arbeitszeitTeilzeitNachmittag",
                "arbeitszeitTeilzeitVormittag",
                "arbeitszeitTeilzeitFlexibel",
            )
        ):
            employment_types.append("Teilzeit")

        job = enrich_job_posting(
            JobPosting(
                source=cls.name,
                external_id=reference,
                title=title,
                company=company,
                location=location,
                url=url,
                description=text_value(detail.get("stellenangebotsBeschreibung")),
                employment_type=", ".join(employment_types) or None,
                published_at=parse_published_at(
                    detail.get("datumErsteVeroeffentlichung")
                    or row.get("aktuelleVeroeffentlichungsdatum")
                ),
            )
        )
        if (
            job.work_mode is WorkMode.UNKNOWN
            and detail.get("homeofficemoeglich") is True
        ):
            job = replace(job, work_mode=WorkMode.HYBRID, remote=False)
        return job
