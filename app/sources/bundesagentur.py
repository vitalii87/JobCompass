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
        "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v6/jobs"
    )
    fallback_search_endpoint = (
        "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/app/jobs"
    )
    detail_endpoint = (
        "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobdetails"
    )
    headers = {"X-API-Key": "jobboerse-jobsuche"}
    _REGION_LABELS = {
        "BADEN_WUERTTEMBERG": "Baden-Württemberg",
        "BAYERN": "Bayern",
        "BERLIN": "Berlin",
        "BRANDENBURG": "Brandenburg",
        "BREMEN": "Bremen",
        "HAMBURG": "Hamburg",
        "HESSEN": "Hessen",
        "NIEDERSACHSEN": "Niedersachsen",
        "NORDRHEIN_WESTFALEN": "Nordrhein-Westfalen",
        "RHEINLAND_PFALZ": "Rheinland-Pfalz",
        "SAARLAND": "Saarland",
        "SACHSEN": "Sachsen",
        "SACHSEN_ANHALT": "Sachsen-Anhalt",
        "SCHLESWIG_HOLSTEIN": "Schleswig-Holstein",
        "THUERINGEN": "Thüringen",
    }

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
        locations = query.location_queries or (None,)
        combination_count = max(1, len(roles) * len(locations))
        page_size = min(25, max(5, self.max_results // combination_count + 3))
        rows_by_reference: dict[str, dict[str, Any]] = {}

        for role in roles:
            for location_query in locations:
                location = (
                    location_query.source_query if location_query is not None else ""
                )
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
                payload = self._get_search_payload(params)
                if (
                    payload.get("maxErgebnisse") == 0
                    and location_query is not None
                    and location_query.source_query != location_query.name
                ):
                    params["wo"] = location_query.name
                    payload = self._get_search_payload(params)
                rows = payload.get("ergebnisliste")
                if rows is None:
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
                    reference = self._reference(row)
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
            if job is not None and matches_query(
                job, query, location_prefiltered=True
            ):
                jobs.append(job)
        return jobs

    def _get_search_payload(self, params: dict[str, object]) -> dict[str, Any]:
        errors: list[SourceError] = []
        for endpoint in (self.search_endpoint, self.fallback_search_endpoint):
            try:
                return self.client.get_json(endpoint, params, self.headers)
            except SourceError as error:
                errors.append(error)
                if "HTTP 404" not in str(error):
                    raise
        raise SourceError(
            "Jobsuche Bundesagentur тимчасово недоступна: обидва пошукові "
            "endpoint-и повернули HTTP 404"
        ) from errors[-1]

    def _load_detail_safely(self, row: dict[str, Any]) -> dict[str, Any]:
        reference = self._reference(row)
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

    @staticmethod
    def _reference(row: dict[str, Any]) -> str:
        return text_value(row.get("referenznummer"), text_value(row.get("refnr")))

    @classmethod
    def _normalize(
        cls, row: dict[str, Any], detail: dict[str, Any]
    ) -> JobPosting | None:
        reference = cls._reference(row)
        title = text_value(
            detail.get("stellenangebotsTitel"),
            text_value(row.get("stellenangebotsTitel"), text_value(row.get("titel"))),
        )
        company = text_value(
            detail.get("firma"),
            text_value(
                row.get("firma"),
                text_value(row.get("arbeitgeber"), "Невідомий роботодавець"),
            ),
        )
        if not reference or not title:
            return None

        raw_location = row.get("arbeitsort")
        if not isinstance(raw_location, dict):
            raw_locations = row.get("stellenlokationen")
            if isinstance(raw_locations, list) and raw_locations:
                first_location = raw_locations[0]
                if isinstance(first_location, dict):
                    raw_address = first_location.get("adresse")
                    if isinstance(raw_address, dict):
                        raw_location = raw_address
        if isinstance(raw_location, dict):
            location_parts = [
                text_value(raw_location.get("ort")),
                cls._region_label(raw_location.get("region")),
            ]
            location = ", ".join(part for part in location_parts if part)
        else:
            location = ""

        external_url = text_value(
            detail.get("externeURL"),
            text_value(row.get("externeURL"), text_value(row.get("externeUrl"))),
        )
        url = external_url or (
            "https://www.arbeitsagentur.de/jobsuche/jobdetail/" + quote(reference)
        )
        employment_types: list[str] = []
        if detail.get("arbeitszeitVollzeit") is True:
            employment_types.append("Vollzeit")
        elif row.get("arbeitszeitVollzeit") is True:
            employment_types.append("Vollzeit")
        if any(
            detail.get(field) is True or row.get(field) is True
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
                    or row.get("datumErsteVeroeffentlichung")
                    or row.get("aktuelleVeroeffentlichungsdatum")
                ),
            )
        )
        if (
            job.work_mode is WorkMode.UNKNOWN
            and (
                detail.get("homeofficemoeglich") is True
                or row.get("homeofficemoeglich") is True
            )
        ):
            job = replace(job, work_mode=WorkMode.HYBRID, remote=False)
        return job

    @classmethod
    def _region_label(cls, value: object) -> str:
        raw = text_value(value)
        return cls._REGION_LABELS.get(raw, raw.replace("_", " ").title())
