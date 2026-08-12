"""Atomic multi-profile JSON storage for JobCompass."""

from __future__ import annotations

import copy
import json
import os
import tempfile
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, ParamSpec, TypeVar
from urllib.parse import urlsplit

from app.core.deduplication import deduplicate_jobs_with_aliases
from app.core.source_registry import SourceRegistryEntry
from app.core.models import (
    ApplicationEvent,
    ApplicationRecord,
    ApplicationSubmission,
    ApplicationStatus,
    CandidateProfile,
    CoverLetterPreparation,
    JobPosting,
    utc_now,
)
from app.core.profiles import ProfileSummary, SavedSearchPreferences, SearchSchedule
from app.i18n import DEFAULT_LANGUAGE, normalize_language


_P = ParamSpec("_P")
_R = TypeVar("_R")
_PROCESS_LOCKS: dict[str, threading.RLock] = {}
_PROCESS_LOCKS_GUARD = threading.Lock()


def _process_lock_for(path: Path) -> threading.RLock:
    key = str(path.resolve()).casefold()
    with _PROCESS_LOCKS_GUARD:
        return _PROCESS_LOCKS.setdefault(key, threading.RLock())


def _locked_mutation(
    method: Callable[_P, _R],
) -> Callable[_P, _R]:
    """Keep every read-modify-write operation atomic across store instances."""

    @wraps(method)
    def wrapped(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        store = args[0]
        with store._mutation_lock():
            return method(*args, **kwargs)

    return wrapped


class LocalJsonStore:
    """Store shared vacancies and isolate every candidate's private workspace."""

    SCHEMA_VERSION = 2

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock_path = self.path.with_name(f".{self.path.name}.lock")
        self._process_lock = _process_lock_for(self.path)
        self._lock_state = threading.local()
        self._active_profile_id: str | None = None
        self._guest_data = self._empty_profile_data("guest", "Гостьовий режим")
        if self.path.exists():
            data = self._read()
            active = data.get("active_profile_id")
            self._active_profile_id = active if isinstance(active, str) else None

    @property
    def active_profile_id(self) -> str | None:
        return self._active_profile_id

    def load_app_language(self) -> str:
        settings = self._read().get("settings", {})
        value = settings.get("language") if isinstance(settings, Mapping) else None
        return normalize_language(value if isinstance(value, str) else None)

    @_locked_mutation
    def save_app_language(self, language: str) -> None:
        data = self._read()
        settings = data.setdefault("settings", {})
        if not isinstance(settings, dict):
            settings = {}
            data["settings"] = settings
        settings["language"] = normalize_language(language)
        self._write(data)

    def load_career_urls(self) -> tuple[str, ...]:
        settings = self._read().get("settings", {})
        raw = settings.get("career_urls", []) if isinstance(settings, Mapping) else []
        if not isinstance(raw, list):
            return ()
        return tuple(
            dict.fromkeys(
                value.strip()
                for value in raw
                if isinstance(value, str) and value.strip()
            )
        )

    @_locked_mutation
    def save_career_urls(self, urls: tuple[str, ...]) -> None:
        cleaned = tuple(
            dict.fromkeys(value.strip() for value in urls if value.strip())
        )
        if any(
            urlsplit(value).scheme.casefold() not in {"http", "https"}
            or not urlsplit(value).netloc
            for value in cleaned
        ):
            raise ValueError("Career URL має починатися з https:// або http://")
        data = self._read()
        settings = data.setdefault("settings", {})
        if not isinstance(settings, dict):
            settings = {}
            data["settings"] = settings
        settings["career_urls"] = list(cleaned)
        self._write(data)

    def list_source_registry(self) -> list[SourceRegistryEntry]:
        raw = self._read().get("source_registry", [])
        if not isinstance(raw, list):
            return []
        result: list[SourceRegistryEntry] = []
        for item in raw:
            if not isinstance(item, Mapping):
                continue
            try:
                result.append(SourceRegistryEntry.from_dict(item))
            except (TypeError, ValueError):
                continue
        return result

    @_locked_mutation
    def save_source_registry(self, entries: list[SourceRegistryEntry]) -> None:
        unique = {entry.source_id: entry for entry in entries}
        data = self._read()
        data["source_registry"] = [
            entry.to_dict()
            for entry in sorted(
                unique.values(),
                key=lambda item: (item.company.casefold(), item.career_url),
            )
        ]
        self._write(data)

    @_locked_mutation
    def upsert_source_registry(
        self, entries: list[SourceRegistryEntry]
    ) -> int:
        existing = {entry.source_id: entry for entry in self.list_source_registry()}
        added = 0
        for entry in entries:
            previous = existing.get(entry.source_id)
            if previous is None:
                existing[entry.source_id] = entry
                added += 1
                continue
            existing[entry.source_id] = replace(
                previous,
                company=entry.company or previous.company,
                ats_type=(
                    entry.ats_type
                    if entry.ats_type.value not in {"generic_html", "json_ld"}
                    or previous.ats_type.value in {"generic_html", "json_ld"}
                    else previous.ats_type
                ),
                country=entry.country or previous.country,
                region=entry.region or previous.region,
                discovered_from=previous.discovered_from or entry.discovered_from,
            )
        self.save_source_registry(list(existing.values()))
        return added

    @property
    def is_guest(self) -> bool:
        return self._active_profile_id is None

    @_locked_mutation
    def initialize(self) -> None:
        if not self.path.exists():
            self._write(self._empty_data())
        data = self._read()
        active = data.get("active_profile_id")
        self._active_profile_id = active if isinstance(active, str) else None

    def list_profiles(self) -> list[ProfileSummary]:
        data = self._read()
        profiles = [self._profile_summary(item) for item in data["profiles"].values()]
        return sorted(profiles, key=lambda item: item.name.casefold())

    def get_profile_summary(self, profile_id: str) -> ProfileSummary | None:
        raw = self._read()["profiles"].get(profile_id)
        return self._profile_summary(raw) if isinstance(raw, dict) else None

    @_locked_mutation
    def create_profile(
        self,
        name: str,
        candidate: CandidateProfile | None = None,
        *,
        make_active: bool = True,
    ) -> ProfileSummary:
        cleaned_name = self._validated_profile_name(name)
        data = self._read()
        self._ensure_unique_profile_name(data, cleaned_name)
        profile_id = uuid.uuid4().hex
        profile_data = self._empty_profile_data(profile_id, cleaned_name)
        profile_data["candidate"] = (candidate or CandidateProfile()).to_dict()
        data["profiles"][profile_id] = profile_data
        if make_active:
            data["active_profile_id"] = profile_id
            self._active_profile_id = profile_id
            profile_data["last_opened_at"] = utc_now().isoformat()
        self._write(data)
        return self._profile_summary(profile_data)

    @_locked_mutation
    def activate_profile(self, profile_id: str | None) -> datetime | None:
        data = self._read()
        if profile_id is None:
            self._active_profile_id = None
            return None
        profile = data["profiles"].get(profile_id)
        if not isinstance(profile, dict):
            raise ValueError(f"Unknown profile: {profile_id}")
        previous_opened = self._optional_datetime(profile.get("last_opened_at"))
        now = utc_now().isoformat()
        profile["last_opened_at"] = now
        profile["updated_at"] = now
        data["active_profile_id"] = profile_id
        self._active_profile_id = profile_id
        self._write(data)
        return previous_opened

    def set_profile_context(self, profile_id: str | None) -> None:
        """Select a profile for a background process without changing startup state."""
        if profile_id is not None and profile_id not in self._read()["profiles"]:
            raise ValueError(f"Unknown profile: {profile_id}")
        self._active_profile_id = profile_id

    @_locked_mutation
    def rename_profile(self, profile_id: str, name: str) -> ProfileSummary:
        cleaned_name = self._validated_profile_name(name)
        data = self._read()
        profile = data["profiles"].get(profile_id)
        if not isinstance(profile, dict):
            raise ValueError(f"Unknown profile: {profile_id}")
        self._ensure_unique_profile_name(data, cleaned_name, except_id=profile_id)
        profile["name"] = cleaned_name
        profile["updated_at"] = utc_now().isoformat()
        self._write(data)
        return self._profile_summary(profile)

    @_locked_mutation
    def duplicate_profile(self, profile_id: str, name: str) -> ProfileSummary:
        cleaned_name = self._validated_profile_name(name)
        data = self._read()
        source = data["profiles"].get(profile_id)
        if not isinstance(source, dict):
            raise ValueError(f"Unknown profile: {profile_id}")
        self._ensure_unique_profile_name(data, cleaned_name)
        new_id = uuid.uuid4().hex
        duplicated = copy.deepcopy(source)
        now = utc_now().isoformat()
        duplicated.update(
            {
                "id": new_id,
                "name": cleaned_name,
                "created_at": now,
                "updated_at": now,
                "last_opened_at": now,
                "applications": [],
                "cover_letters": [],
                "job_states": {},
                "last_result_job_ids": [],
                "schedule": SearchSchedule().to_dict(),
            }
        )
        data["profiles"][new_id] = duplicated
        data["active_profile_id"] = new_id
        self._active_profile_id = new_id
        self._write(data)
        return self._profile_summary(duplicated)

    @_locked_mutation
    def delete_profile(self, profile_id: str) -> None:
        data = self._read()
        if profile_id not in data["profiles"]:
            raise ValueError(f"Unknown profile: {profile_id}")
        del data["profiles"][profile_id]
        if data.get("active_profile_id") == profile_id:
            data["active_profile_id"] = None
            self._active_profile_id = None
        self._write(data)

    def load_profile(self) -> CandidateProfile | None:
        profile = self._active_profile_data(self._read())
        raw_candidate = profile.get("candidate")
        if raw_candidate is None:
            return None
        if not isinstance(raw_candidate, Mapping):
            raise ValueError("Stored candidate must be a JSON object or null")
        return CandidateProfile.from_dict(raw_candidate)

    def set_guest_profile(self, profile: CandidateProfile) -> None:
        if not self.is_guest:
            raise ValueError("Guest profile can only be set in guest mode")
        self._guest_data["candidate"] = profile.to_dict()

    @_locked_mutation
    def save_profile(self, profile: CandidateProfile) -> None:
        if self.is_guest:
            self.create_profile(profile.full_name or "Основний профіль", profile)
            return
        data = self._read()
        profile_data = self._persistent_active_profile(data)
        profile_data["candidate"] = profile.to_dict()
        profile_data["updated_at"] = utc_now().isoformat()
        self._write(data)

    def load_search_preferences(self) -> SavedSearchPreferences:
        profile = self._active_profile_data(self._read())
        raw = profile.get("search_preferences") or {}
        if not isinstance(raw, Mapping):
            raise ValueError("Search preferences must be a JSON object")
        return SavedSearchPreferences.from_dict(raw)

    @_locked_mutation
    def save_search_preferences(self, preferences: SavedSearchPreferences) -> None:
        self._update_active_profile_value(
            "search_preferences", preferences.to_dict()
        )

    def load_schedule(self) -> SearchSchedule:
        profile = self._active_profile_data(self._read())
        raw = profile.get("schedule") or {}
        if not isinstance(raw, Mapping):
            raise ValueError("Schedule must be a JSON object")
        return SearchSchedule.from_dict(raw)

    @_locked_mutation
    def save_schedule(self, schedule: SearchSchedule) -> None:
        self._update_active_profile_value("schedule", schedule.to_dict())

    @_locked_mutation
    def mark_schedule_run(self, occurred_at: datetime | None = None) -> None:
        schedule = self.load_schedule()
        self.save_schedule(
            SearchSchedule(
                enabled=schedule.enabled,
                daily_time=schedule.daily_time,
                last_run_at=occurred_at or utc_now(),
            )
        )

    @_locked_mutation
    def save_resume_info(self, path: str, raw_text: str) -> None:
        self._update_active_profile_value(
            "resume", {"path": path.strip(), "raw_text": raw_text}
        )

    def load_resume_info(self) -> tuple[str, str]:
        profile = self._active_profile_data(self._read())
        raw = profile.get("resume") or {}
        if not isinstance(raw, Mapping):
            return "", ""
        path = raw.get("path") if isinstance(raw.get("path"), str) else ""
        text = raw.get("raw_text") if isinstance(raw.get("raw_text"), str) else ""
        return path, text

    @_locked_mutation
    def save_last_result_job_ids(self, job_ids: list[str]) -> None:
        cleaned = list(dict.fromkeys(item.strip() for item in job_ids if item.strip()))
        self._update_active_profile_value("last_result_job_ids", cleaned)

    def snapshot_activity(self) -> dict[str, Any]:
        """Copy profile-scoped history for guest-to-profile conversion."""
        profile = self._active_profile_data(self._read())
        return copy.deepcopy(
            {
                key: profile.get(key)
                for key in (
                    "applications",
                    "cover_letters",
                    "job_states",
                    "last_result_job_ids",
                )
            }
        )

    @_locked_mutation
    def restore_activity(self, snapshot: Mapping[str, Any]) -> None:
        profile = self._active_profile_data(self._read())
        for key in (
            "applications",
            "cover_letters",
            "job_states",
            "last_result_job_ids",
        ):
            if key in snapshot:
                profile[key] = copy.deepcopy(snapshot[key])
        self._save_active_profile_data(profile)

    def load_last_result_job_ids(self) -> list[str]:
        profile = self._active_profile_data(self._read())
        raw = profile.get("last_result_job_ids") or []
        return [item for item in raw if isinstance(item, str)]

    def list_jobs(self) -> list[JobPosting]:
        return [JobPosting.from_dict(item) for item in self._read()["jobs"]]

    def get_job(self, job_id: str) -> JobPosting | None:
        return next((job for job in self.list_jobs() if job.job_id == job_id), None)

    @_locked_mutation
    def save_jobs(self, jobs: list[JobPosting]) -> int:
        data = self._read()
        existing = [JobPosting.from_dict(item) for item in data["jobs"]]
        existing_ids = {job.job_id for job in existing}
        combined_by_id = {job.job_id: job for job in existing}
        for job in jobs:
            combined_by_id[job.job_id] = job
        unique, aliases = deduplicate_jobs_with_aliases(combined_by_id.values())
        self._remap_profile_job_references(data, aliases)
        data["jobs"] = [job.to_dict() for job in unique]
        self._write(data)
        canonical_existing_ids = {
            aliases.get(job_id, job_id) for job_id in existing_ids
        }
        return len({job.job_id for job in unique} - canonical_existing_ids)

    @_locked_mutation
    def record_job_discoveries(
        self,
        job_ids: list[str],
        *,
        occurred_at: datetime | None = None,
        scheduled: bool = True,
    ) -> int:
        profile = self._active_profile_data(self._read())
        states = profile.setdefault("job_states", {})
        now = (occurred_at or utc_now()).isoformat()
        new_count = 0
        for job_id in dict.fromkeys(job_ids):
            state = states.get(job_id)
            if not isinstance(state, dict):
                state = {
                    "first_seen_at": now,
                    "seen_at": None,
                    "favorite": False,
                    "scheduled": scheduled,
                }
                states[job_id] = state
                new_count += 1
            elif scheduled:
                state["scheduled"] = True
            state["last_seen_at"] = now
        self._save_active_profile_data(profile)
        return new_count

    @_locked_mutation
    def mark_job_seen(self, job_id: str, seen: bool = True) -> None:
        profile = self._active_profile_data(self._read())
        states = profile.setdefault("job_states", {})
        state = states.setdefault(
            job_id,
            {
                "first_seen_at": utc_now().isoformat(),
                "last_seen_at": utc_now().isoformat(),
                "favorite": False,
            },
        )
        state["seen_at"] = utc_now().isoformat() if seen else None
        self._save_active_profile_data(profile)

    @_locked_mutation
    def mark_all_jobs_seen(self) -> None:
        profile = self._active_profile_data(self._read())
        now = utc_now().isoformat()
        for state in profile.setdefault("job_states", {}).values():
            if isinstance(state, dict):
                state["seen_at"] = now
        self._save_active_profile_data(profile)

    @_locked_mutation
    def set_job_favorite(self, job_id: str, favorite: bool = True) -> None:
        profile = self._active_profile_data(self._read())
        states = profile.setdefault("job_states", {})
        now = utc_now().isoformat()
        state = states.setdefault(
            job_id,
            {"first_seen_at": now, "last_seen_at": now, "seen_at": None},
        )
        state["favorite"] = bool(favorite)
        self._save_active_profile_data(profile)

    def get_job_state(self, job_id: str) -> dict[str, Any]:
        profile = self._active_profile_data(self._read())
        state = profile.setdefault("job_states", {}).get(job_id, {})
        return copy.deepcopy(state) if isinstance(state, dict) else {}

    def list_unseen_jobs(self) -> list[JobPosting]:
        return [
            job
            for job, state in self.list_scheduled_jobs()
            if not state.get("seen_at")
        ]

    def list_scheduled_jobs(self) -> list[tuple[JobPosting, dict[str, Any]]]:
        """Return scheduled discoveries; missing flags preserve legacy data."""
        return [
            (job, state)
            for job, state in self.list_discovered_jobs()
            if state.get("scheduled", True)
        ]

    def list_discovered_jobs(self) -> list[tuple[JobPosting, dict[str, Any]]]:
        """Return all profile discoveries, including jobs already opened."""

        profile = self._active_profile_data(self._read())
        states = profile.setdefault("job_states", {})
        jobs = {job.job_id: job for job in self.list_jobs()}
        discovered = [
            (state.get("first_seen_at", ""), jobs[job_id], copy.deepcopy(state))
            for job_id, state in states.items()
            if job_id in jobs and isinstance(state, dict)
        ]
        discovered.sort(key=lambda item: item[0], reverse=True)
        return [(job, state) for _, job, state in discovered]

    def list_favorite_job_ids(self) -> set[str]:
        profile = self._active_profile_data(self._read())
        return {
            job_id
            for job_id, state in profile.setdefault("job_states", {}).items()
            if isinstance(state, dict) and state.get("favorite") is True
        }

    def list_cover_letter_preparations(self) -> list[CoverLetterPreparation]:
        profile = self._active_profile_data(self._read())
        return [
            CoverLetterPreparation.from_dict(item)
            for item in profile["cover_letters"]
        ]

    def get_cover_letter_preparation(
        self, job_id: str
    ) -> CoverLetterPreparation | None:
        return next(
            (
                item
                for item in self.list_cover_letter_preparations()
                if item.job_id == job_id
            ),
            None,
        )

    @_locked_mutation
    def save_cover_letter_preparation(
        self, preparation: CoverLetterPreparation
    ) -> None:
        if self.get_job(preparation.job_id) is None:
            raise ValueError(f"Unknown job: {preparation.job_id}")
        profile = self._active_profile_data(self._read())
        items = [
            CoverLetterPreparation.from_dict(item)
            for item in profile["cover_letters"]
        ]
        items = [
            preparation if item.job_id == preparation.job_id else item
            for item in items
        ]
        if not any(item.job_id == preparation.job_id for item in items):
            items.append(preparation)
        profile["cover_letters"] = [item.to_dict() for item in items]
        self._save_active_profile_data(profile)

    def list_applications(self) -> list[ApplicationRecord]:
        profile = self._active_profile_data(self._read())
        return [ApplicationRecord.from_dict(item) for item in profile["applications"]]

    def get_application(self, job_id: str) -> ApplicationRecord | None:
        return next(
            (item for item in self.list_applications() if item.job_id == job_id),
            None,
        )

    @_locked_mutation
    def set_application_status(
        self,
        job_id: str,
        status: ApplicationStatus,
        notes: str | None = None,
    ) -> ApplicationRecord:
        if self.get_job(job_id) is None:
            raise ValueError(f"Unknown job: {job_id}")
        profile = self._active_profile_data(self._read())
        applications = [
            ApplicationRecord.from_dict(item) for item in profile["applications"]
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
        profile["applications"] = [item.to_dict() for item in applications]
        self._save_active_profile_data(profile)
        return updated

    @_locked_mutation
    def record_application_submission(
        self,
        job_id: str,
        submission: ApplicationSubmission,
        *,
        allow_duplicate: bool = False,
    ) -> ApplicationRecord:
        """Atomically record a user-confirmed submission and its material snapshot."""

        if self.get_job(job_id) is None:
            raise ValueError(f"Unknown job: {job_id}")
        profile = self._active_profile_data(self._read())
        applications = [
            ApplicationRecord.from_dict(item) for item in profile["applications"]
        ]
        current = next((item for item in applications if item.job_id == job_id), None)
        if current is not None and current.has_submission_history and not allow_duplicate:
            raise ValueError(
                "Заявку на цю вакансію вже позначено як відправлену."
            )

        mode_label = {
            "manual": "ручний",
            "assisted": "з допомогою JobCompass",
            "automatic": "автоматичний",
        }[submission.mode.value]
        material_note = (
            f"Відправлення підтверджено; режим: {mode_label}; "
            f"резюме: {submission.resume_name or 'не вказано'}; "
            f"супровідний лист: {'так' if submission.cover_letter_text else 'ні'}"
        )
        event = ApplicationEvent(
            status=ApplicationStatus.APPLIED,
            occurred_at=submission.submitted_at,
            notes=material_note,
        )
        if current is None:
            updated = ApplicationRecord(
                job_id=job_id,
                status=ApplicationStatus.APPLIED,
                notes=material_note,
                created_at=submission.submitted_at,
                updated_at=submission.submitted_at,
                history=(event,),
                submissions=(submission,),
            )
            applications.append(updated)
        else:
            updated = replace(
                current,
                status=ApplicationStatus.APPLIED,
                notes=material_note,
                updated_at=submission.submitted_at,
                history=current.history + (event,),
                submissions=current.submissions + (submission,),
            )
            applications = [
                updated if item.job_id == job_id else item for item in applications
            ]
        profile["applications"] = [item.to_dict() for item in applications]
        self._save_active_profile_data(profile)
        return updated

    def export_profile(self, profile_id: str, path: str | Path) -> None:
        data = self._read()
        profile = data["profiles"].get(profile_id)
        if not isinstance(profile, dict):
            raise ValueError(f"Unknown profile: {profile_id}")
        referenced_ids = set(profile.get("job_states", {}))
        referenced_ids.update(profile.get("last_result_job_ids", []))
        referenced_ids.update(
            item.get("job_id")
            for item in profile.get("applications", [])
            if isinstance(item, dict)
        )
        jobs = [
            item
            for item in data["jobs"]
            if isinstance(item, dict)
            and f"{item.get('source')}:{item.get('external_id')}" in referenced_ids
        ]
        payload = {
            "format": "jobcompass-profile",
            "version": 1,
            "profile": profile,
            "jobs": jobs,
        }
        Path(path).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    @_locked_mutation
    def import_profile(self, path: str | Path) -> ProfileSummary:
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError("Profile export is not valid JSON") from error
        if not isinstance(payload, dict) or payload.get("format") != "jobcompass-profile":
            raise ValueError("File is not a JobCompass profile export")
        source = payload.get("profile")
        if not isinstance(source, dict):
            raise ValueError("Profile export does not contain a profile")
        candidate_raw = source.get("candidate")
        if not isinstance(candidate_raw, Mapping):
            raise ValueError("Exported candidate is invalid")
        CandidateProfile.from_dict(candidate_raw)
        SavedSearchPreferences.from_dict(source.get("search_preferences") or {})
        SearchSchedule.from_dict(source.get("schedule") or {})

        data = self._read()
        base_name = self._validated_profile_name(str(source.get("name") or "Імпорт"))
        name = base_name
        number = 2
        existing = {
            str(item.get("name", "")).casefold()
            for item in data["profiles"].values()
            if isinstance(item, dict)
        }
        while name.casefold() in existing:
            name = f"{base_name} ({number})"
            number += 1
        new_id = uuid.uuid4().hex
        imported = copy.deepcopy(source)
        now = utc_now().isoformat()
        imported.update(
            {
                "id": new_id,
                "name": name,
                "created_at": now,
                "updated_at": now,
                "last_opened_at": now,
            }
        )
        data["profiles"][new_id] = imported
        imported_jobs = [
            JobPosting.from_dict(item)
            for item in payload.get("jobs", [])
            if isinstance(item, Mapping)
        ]
        existing_jobs = [JobPosting.from_dict(item) for item in data["jobs"]]
        combined = {item.job_id: item for item in [*existing_jobs, *imported_jobs]}
        unique, aliases = deduplicate_jobs_with_aliases(combined.values())
        self._remap_profile_job_references(data, aliases)
        data["jobs"] = [item.to_dict() for item in unique]
        data["active_profile_id"] = new_id
        self._active_profile_id = new_id
        self._write(data)
        return self._profile_summary(imported)

    def _active_profile_data(self, data: dict[str, Any]) -> dict[str, Any]:
        if self.is_guest:
            return self._guest_data
        return self._persistent_active_profile(data)

    def _persistent_active_profile(self, data: dict[str, Any]) -> dict[str, Any]:
        profile = data["profiles"].get(self._active_profile_id)
        if not isinstance(profile, dict):
            raise ValueError("Active profile no longer exists")
        return profile

    def _save_active_profile_data(self, profile: dict[str, Any]) -> None:
        if self.is_guest:
            self._guest_data = profile
            return
        data = self._read()
        profile["updated_at"] = utc_now().isoformat()
        data["profiles"][self._active_profile_id] = profile
        self._write(data)

    def _update_active_profile_value(self, key: str, value: Any) -> None:
        profile = self._active_profile_data(self._read())
        profile[key] = value
        self._save_active_profile_data(profile)

    @classmethod
    def _remap_profile_job_references(
        cls,
        data: dict[str, Any],
        aliases: Mapping[str, str],
    ) -> None:
        changed = {
            old_id: new_id
            for old_id, new_id in aliases.items()
            if old_id != new_id
        }
        if not changed:
            return
        for profile in data.get("profiles", {}).values():
            if isinstance(profile, dict):
                cls._remap_one_profile(profile, changed)

    @classmethod
    def _remap_one_profile(
        cls,
        profile: dict[str, Any],
        aliases: Mapping[str, str],
    ) -> None:
        raw_states = profile.get("job_states", {})
        states: dict[str, dict[str, Any]] = {}
        if isinstance(raw_states, Mapping):
            for old_id, raw_state in raw_states.items():
                if not isinstance(old_id, str) or not isinstance(raw_state, Mapping):
                    continue
                new_id = aliases.get(old_id, old_id)
                state = copy.deepcopy(dict(raw_state))
                previous = states.get(new_id)
                states[new_id] = (
                    cls._merge_job_states(previous, state)
                    if previous is not None
                    else state
                )
        profile["job_states"] = states

        raw_result_ids = profile.get("last_result_job_ids", [])
        if isinstance(raw_result_ids, list):
            profile["last_result_job_ids"] = list(
                dict.fromkeys(
                    aliases.get(job_id, job_id)
                    for job_id in raw_result_ids
                    if isinstance(job_id, str)
                )
            )

        applications: dict[str, ApplicationRecord] = {}
        for raw in profile.get("applications", []):
            if not isinstance(raw, Mapping):
                continue
            try:
                item = ApplicationRecord.from_dict(raw)
            except (TypeError, ValueError):
                continue
            item = replace(item, job_id=aliases.get(item.job_id, item.job_id))
            previous = applications.get(item.job_id)
            applications[item.job_id] = (
                cls._merge_applications(previous, item)
                if previous is not None
                else item
            )
        profile["applications"] = [item.to_dict() for item in applications.values()]

        preparations: dict[str, CoverLetterPreparation] = {}
        for raw in profile.get("cover_letters", []):
            if not isinstance(raw, Mapping):
                continue
            try:
                item = CoverLetterPreparation.from_dict(raw)
            except (TypeError, ValueError):
                continue
            item = replace(item, job_id=aliases.get(item.job_id, item.job_id))
            previous = preparations.get(item.job_id)
            if previous is None or item.updated_at >= previous.updated_at:
                preparations[item.job_id] = item
        profile["cover_letters"] = [
            item.to_dict() for item in preparations.values()
        ]

    @staticmethod
    def _merge_job_states(
        left: Mapping[str, Any],
        right: Mapping[str, Any],
    ) -> dict[str, Any]:
        merged = {**left, **right}
        for key in ("favorite", "scheduled"):
            merged[key] = bool(left.get(key)) or bool(right.get(key))
        for key, choose in (
            ("first_seen_at", min),
            ("last_seen_at", max),
            ("seen_at", max),
        ):
            values = [
                value
                for value in (left.get(key), right.get(key))
                if isinstance(value, str) and value
            ]
            merged[key] = choose(values) if values else None
        return merged

    @staticmethod
    def _merge_applications(
        left: ApplicationRecord,
        right: ApplicationRecord,
    ) -> ApplicationRecord:
        latest = right if right.updated_at >= left.updated_at else left
        history = tuple(
            sorted(
                {*left.history, *right.history},
                key=lambda event: event.occurred_at,
            )
        )
        submissions = tuple(
            sorted(
                {*left.submissions, *right.submissions},
                key=lambda submission: submission.submitted_at,
            )
        )
        return replace(
            latest,
            created_at=min(left.created_at, right.created_at),
            updated_at=max(left.updated_at, right.updated_at),
            history=history,
            submissions=submissions,
        )

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
        if data.get("schema_version") == 1:
            data = self._migrate_v1(data)
            self._write(data)
        if data.get("schema_version") != self.SCHEMA_VERSION:
            raise ValueError("Unsupported storage schema version")
        if not isinstance(data.get("jobs"), list):
            raise ValueError("Storage must contain a job list")
        if not isinstance(data.get("profiles"), dict):
            raise ValueError("Storage must contain a profile object")
        settings = data.setdefault(
            "settings", {"language": DEFAULT_LANGUAGE, "career_urls": []}
        )
        if not isinstance(settings, dict):
            raise ValueError("Storage settings must be an object")
        settings["language"] = normalize_language(settings.get("language"))
        if not isinstance(settings.get("career_urls", []), list):
            settings["career_urls"] = []
        if not isinstance(data.get("source_registry", []), list):
            data["source_registry"] = []
        active = data.get("active_profile_id")
        if active is not None and active not in data["profiles"]:
            data["active_profile_id"] = None
        return data

    def _write(self, data: dict[str, Any]) -> None:
        with self._mutation_lock():
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

    @contextmanager
    def _mutation_lock(self, timeout_seconds: float = 15.0) -> Iterator[None]:
        """Serialize mutations in this process and across JobCompass processes."""

        with self._process_lock:
            depth = int(getattr(self._lock_state, "depth", 0))
            if depth:
                self._lock_state.depth = depth + 1
                try:
                    yield
                finally:
                    self._lock_state.depth = depth
                return

            self.path.parent.mkdir(parents=True, exist_ok=True)
            deadline = time.monotonic() + timeout_seconds
            while True:
                try:
                    descriptor = os.open(
                        self._lock_path,
                        os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    )
                except FileExistsError:
                    try:
                        age = time.time() - self._lock_path.stat().st_mtime
                        if age > 30.0:
                            self._lock_path.unlink()
                            continue
                    except FileNotFoundError:
                        continue
                    if time.monotonic() >= deadline:
                        raise TimeoutError(
                            "JobCompass storage is busy in another process"
                        )
                    time.sleep(0.05)
                    continue
                else:
                    with os.fdopen(descriptor, "w", encoding="ascii") as stream:
                        stream.write(f"{os.getpid()}\n")
                    break

            self._lock_state.depth = 1
            try:
                yield
            finally:
                self._lock_state.depth = 0
                try:
                    self._lock_path.unlink()
                except FileNotFoundError:
                    pass

    @classmethod
    def _migrate_v1(cls, data: dict[str, Any]) -> dict[str, Any]:
        migrated = cls._empty_data()
        migrated["jobs"] = data.get("jobs", [])
        raw_candidate = data.get("profile")
        applications = data.get("applications", [])
        letters = data.get("cover_letters", [])
        if raw_candidate is None and not applications and not letters:
            return migrated
        candidate = raw_candidate if isinstance(raw_candidate, dict) else {}
        profile_id = uuid.uuid4().hex
        name = str(candidate.get("full_name") or "Основний профіль").strip()
        profile = cls._empty_profile_data(profile_id, name)
        profile["candidate"] = candidate
        profile["applications"] = applications if isinstance(applications, list) else []
        profile["cover_letters"] = letters if isinstance(letters, list) else []
        profile["search_preferences"] = SavedSearchPreferences(
            roles=tuple(candidate.get("desired_roles") or ()),
            remote_only=bool(candidate.get("remote_only", False)),
        ).to_dict()
        migrated["profiles"][profile_id] = profile
        migrated["active_profile_id"] = profile_id
        return migrated

    @classmethod
    def _empty_data(cls) -> dict[str, Any]:
        return {
            "schema_version": cls.SCHEMA_VERSION,
            "active_profile_id": None,
            "settings": {"language": DEFAULT_LANGUAGE, "career_urls": []},
            "profiles": {},
            "jobs": [],
            "source_registry": [],
        }

    @staticmethod
    def _empty_profile_data(profile_id: str, name: str) -> dict[str, Any]:
        now = utc_now().isoformat()
        return {
            "id": profile_id,
            "name": name,
            "candidate": CandidateProfile().to_dict(),
            "resume": {"path": "", "raw_text": ""},
            "search_preferences": SavedSearchPreferences().to_dict(),
            "schedule": SearchSchedule().to_dict(),
            "applications": [],
            "cover_letters": [],
            "job_states": {},
            "last_result_job_ids": [],
            "created_at": now,
            "updated_at": now,
            "last_opened_at": None,
        }

    @staticmethod
    def _optional_datetime(value: object) -> datetime | None:
        if not isinstance(value, str) or not value:
            return None
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None else parsed.astimezone()

    @classmethod
    def _profile_summary(cls, data: Mapping[str, Any]) -> ProfileSummary:
        created = cls._optional_datetime(data.get("created_at")) or utc_now()
        updated = cls._optional_datetime(data.get("updated_at")) or created
        return ProfileSummary(
            profile_id=str(data.get("id") or ""),
            name=str(data.get("name") or "").strip(),
            created_at=created,
            updated_at=updated,
            last_opened_at=cls._optional_datetime(data.get("last_opened_at")),
        )

    @staticmethod
    def _validated_profile_name(name: str) -> str:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Profile name cannot be empty")
        cleaned = name.strip()
        if len(cleaned) > 80:
            raise ValueError("Profile name cannot exceed 80 characters")
        return cleaned

    @staticmethod
    def _ensure_unique_profile_name(
        data: Mapping[str, Any], name: str, except_id: str | None = None
    ) -> None:
        for profile_id, profile in data["profiles"].items():
            if profile_id == except_id or not isinstance(profile, Mapping):
                continue
            if str(profile.get("name", "")).casefold() == name.casefold():
                raise ValueError("A profile with this name already exists")
