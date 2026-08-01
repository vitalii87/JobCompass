"""Atomic local JSON storage for jobs and application history."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any

from app.core.deduplication import deduplicate_jobs
from app.core.models import (
    ApplicationEvent,
    ApplicationRecord,
    ApplicationStatus,
    CandidateProfile,
    JobPosting,
    utc_now,
)


class LocalJsonStore:
    SCHEMA_VERSION = 1

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def initialize(self) -> None:
        if not self.path.exists():
            self._write(self._empty_data())

    def list_jobs(self) -> list[JobPosting]:
        return [JobPosting.from_dict(item) for item in self._read()["jobs"]]

    def get_job(self, job_id: str) -> JobPosting | None:
        return next((job for job in self.list_jobs() if job.job_id == job_id), None)

    def load_profile(self) -> CandidateProfile | None:
        profile = self._read().get("profile")
        if profile is None:
            return None
        if not isinstance(profile, dict):
            raise ValueError("Stored profile must be a JSON object or null")
        return CandidateProfile.from_dict(profile)

    def save_profile(self, profile: CandidateProfile) -> None:
        data = self._read()
        data["profile"] = profile.to_dict()
        self._write(data)

    def save_jobs(self, jobs: list[JobPosting]) -> int:
        data = self._read()
        existing = [JobPosting.from_dict(item) for item in data["jobs"]]
        existing_ids = {job.job_id for job in existing}

        combined_by_id = {job.job_id: job for job in existing}
        for job in jobs:
            combined_by_id[job.job_id] = job
        unique = deduplicate_jobs(combined_by_id.values())

        data["jobs"] = [job.to_dict() for job in unique]
        self._write(data)
        return len({job.job_id for job in unique} - existing_ids)

    def list_applications(self) -> list[ApplicationRecord]:
        return [
            ApplicationRecord.from_dict(item) for item in self._read()["applications"]
        ]

    def get_application(self, job_id: str) -> ApplicationRecord | None:
        return next(
            (
                application
                for application in self.list_applications()
                if application.job_id == job_id
            ),
            None,
        )

    def set_application_status(
        self,
        job_id: str,
        status: ApplicationStatus,
        notes: str | None = None,
    ) -> ApplicationRecord:
        if self.get_job(job_id) is None:
            raise ValueError(f"Unknown job: {job_id}")

        data = self._read()
        applications = [
            ApplicationRecord.from_dict(item) for item in data["applications"]
        ]
        current = next((item for item in applications if item.job_id == job_id), None)
        now = utc_now()
        if current is None:
            event = ApplicationEvent(status=status, occurred_at=now, notes=notes or "")
            updated = ApplicationRecord(
                job_id=job_id,
                status=status,
                notes=notes or "",
                created_at=now,
                updated_at=now,
                history=(event,),
            )
            applications.append(updated)
        else:
            event = ApplicationEvent(
                status=status,
                occurred_at=now,
                notes=current.notes if notes is None else notes,
            )
            updated = replace(
                current,
                status=status,
                notes=current.notes if notes is None else notes,
                updated_at=now,
                history=current.history + (event,),
            )
            applications = [
                updated if item.job_id == job_id else item for item in applications
            ]

        data["applications"] = [item.to_dict() for item in applications]
        self._write(data)
        return updated

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._empty_data()
        try:
            with self.path.open("r", encoding="utf-8") as stream:
                data: Any = json.load(stream)
        except json.JSONDecodeError as error:
            raise ValueError(f"Storage file is not valid JSON: {self.path}") from error

        if not isinstance(data, dict):
            raise ValueError("Storage root must be a JSON object")
        if data.get("schema_version") != self.SCHEMA_VERSION:
            raise ValueError("Unsupported storage schema version")
        if not isinstance(data.get("jobs"), list) or not isinstance(
            data.get("applications"), list
        ):
            raise ValueError("Storage must contain job and application lists")
        data.setdefault("profile", None)
        return data

    def _write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as stream:
                json.dump(data, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                temporary_path = Path(stream.name)
            os.replace(temporary_path, self.path)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

    @classmethod
    def _empty_data(cls) -> dict[str, Any]:
        return {
            "schema_version": cls.SCHEMA_VERSION,
            "profile": None,
            "jobs": [],
            "applications": [],
        }
