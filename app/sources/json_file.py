"""Offline connector for importing normalized vacancies from JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.models import JobPosting
from app.sources.base import SearchQuery


class JsonFileSource:
    name = "json-file"

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def search(self, query: SearchQuery) -> list[JobPosting]:
        jobs = self._load()
        return [job for job in jobs if self._matches(job, query)]

    def _load(self) -> list[JobPosting]:
        try:
            with self.path.open("r", encoding="utf-8") as stream:
                payload: Any = json.load(stream)
        except FileNotFoundError as error:
            raise ValueError(f"Job file does not exist: {self.path}") from error
        except json.JSONDecodeError as error:
            raise ValueError(f"Job file is not valid JSON: {self.path}") from error

        if isinstance(payload, dict):
            payload = payload.get("jobs")
        if not isinstance(payload, list):
            raise ValueError("Job JSON must be a list or an object with a 'jobs' list")

        jobs: list[JobPosting] = []
        for index, item in enumerate(payload):
            if not isinstance(item, dict):
                raise ValueError(f"Job at index {index} must be an object")
            try:
                jobs.append(JobPosting.from_dict(item))
            except (TypeError, ValueError) as error:
                raise ValueError(f"Invalid job at index {index}: {error}") from error
        return jobs

    @staticmethod
    def _matches(job: JobPosting, query: SearchQuery) -> bool:
        searchable = f"{job.title} {job.description}".casefold()
        if query.roles and not any(role.casefold() in searchable for role in query.roles):
            return False
        if query.keywords and not all(
            keyword.casefold() in searchable for keyword in query.keywords
        ):
            return False
        if query.remote_only and job.remote is not True:
            return False
        if query.locations and job.remote is not True:
            location = job.location.casefold()
            if not any(value.casefold() in location for value in query.locations):
                return False
        return True
