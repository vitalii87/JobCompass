"""Domain models used by JobCompass.

The first version deliberately keeps the models independent from databases,
web frameworks, and third-party validation libraries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Mapping


def _clean_strings(values: object, field_name: str) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, str) or not isinstance(values, (list, tuple, set)):
        raise ValueError(f"{field_name} must be a list of strings")

    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            raise ValueError(f"{field_name} must contain only strings")
        cleaned = value.strip()
        key = cleaned.casefold()
        if cleaned and key not in seen:
            result.append(cleaned)
            seen.add(key)
    return tuple(result)


def _optional_text(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string or null")
    cleaned = value.strip()
    return cleaned or None


def _text(value: object, field_name: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    return value.strip()


def _optional_float(value: object, field_name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a number or null")
    number = float(value)
    if number < 0:
        raise ValueError(f"{field_name} cannot be negative")
    return number


def _optional_bool(value: object, field_name: str) -> bool | None:
    if value is None or isinstance(value, bool):
        return value
    raise ValueError(f"{field_name} must be true, false, or null")


def _parse_datetime(value: object, field_name: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be an ISO 8601 string or null")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{field_name} must be a valid ISO 8601 string") from error
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def utc_now() -> datetime:
    """Return an aware UTC timestamp."""

    return datetime.now(timezone.utc)


class ApplicationStatus(StrEnum):
    FOUND = "Found"
    INTERESTING = "Interesting"
    DRAFT = "Draft"
    APPLIED = "Applied"
    REJECTED = "Rejected"
    INTERVIEW = "Interview"
    OFFER = "Offer"
    ARCHIVED = "Archived"


class MatchLevel(StrEnum):
    FULL = "full"
    PARTIAL = "partial"
    WEAK = "weak"


class WorkMode(StrEnum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    OFFICE = "office"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class RequirementEvidence:
    field: str
    value: str
    classification: str
    excerpt: str
    confidence: str = "high"

    def __post_init__(self) -> None:
        for field_name in ("field", "value", "classification", "excerpt", "confidence"):
            cleaned = _text(getattr(self, field_name), field_name)
            if not cleaned:
                raise ValueError(f"{field_name} is required")
            object.__setattr__(self, field_name, cleaned)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RequirementEvidence:
        return cls(
            field=_text(data.get("field"), "field"),
            value=_text(data.get("value"), "value"),
            classification=_text(data.get("classification"), "classification"),
            excerpt=_text(data.get("excerpt"), "excerpt"),
            confidence=_text(data.get("confidence", "high"), "confidence"),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "field": self.field,
            "value": self.value,
            "classification": self.classification,
            "excerpt": self.excerpt,
            "confidence": self.confidence,
        }


@dataclass(frozen=True, slots=True)
class CandidateProfile:
    full_name: str = ""
    email: str = ""
    phone: str = ""
    summary: str = ""
    desired_roles: tuple[str, ...] = ()
    skills: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    years_experience: float | None = None
    preferred_locations: tuple[str, ...] = ()
    remote_only: bool = False

    def __post_init__(self) -> None:
        for field_name in ("full_name", "email", "phone", "summary"):
            object.__setattr__(
                self, field_name, _text(getattr(self, field_name), field_name)
            )
        object.__setattr__(
            self, "desired_roles", _clean_strings(self.desired_roles, "desired_roles")
        )
        object.__setattr__(self, "skills", _clean_strings(self.skills, "skills"))
        object.__setattr__(
            self, "languages", _clean_strings(self.languages, "languages")
        )
        object.__setattr__(
            self,
            "preferred_locations",
            _clean_strings(self.preferred_locations, "preferred_locations"),
        )
        object.__setattr__(
            self,
            "years_experience",
            _optional_float(self.years_experience, "years_experience"),
        )
        if not isinstance(self.remote_only, bool):
            raise ValueError("remote_only must be true or false")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CandidateProfile:
        return cls(
            full_name=_text(data.get("full_name"), "full_name"),
            email=_text(data.get("email"), "email"),
            phone=_text(data.get("phone"), "phone"),
            summary=_text(data.get("summary"), "summary"),
            desired_roles=_clean_strings(data.get("desired_roles"), "desired_roles"),
            skills=_clean_strings(data.get("skills"), "skills"),
            languages=_clean_strings(data.get("languages"), "languages"),
            years_experience=_optional_float(
                data.get("years_experience"), "years_experience"
            ),
            preferred_locations=_clean_strings(
                data.get("preferred_locations"), "preferred_locations"
            ),
            remote_only=data.get("remote_only", False),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "summary": self.summary,
            "desired_roles": list(self.desired_roles),
            "skills": list(self.skills),
            "languages": list(self.languages),
            "years_experience": self.years_experience,
            "preferred_locations": list(self.preferred_locations),
            "remote_only": self.remote_only,
        }


@dataclass(frozen=True, slots=True)
class JobPosting:
    source: str
    external_id: str
    title: str
    company: str
    location: str = ""
    url: str = ""
    description: str = ""
    required_skills: tuple[str, ...] = ()
    preferred_skills: tuple[str, ...] = ()
    required_languages: tuple[str, ...] = ()
    minimum_years_experience: float | None = None
    remote: bool | None = None
    work_mode: WorkMode = WorkMode.UNKNOWN
    employment_type: str | None = None
    published_at: datetime | None = None
    requirement_evidence: tuple[RequirementEvidence, ...] = ()

    def __post_init__(self) -> None:
        for field_name in ("source", "external_id", "title", "company"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} is required")
            object.__setattr__(self, field_name, value.strip())

        for field_name in ("location", "url", "description"):
            value = getattr(self, field_name)
            if not isinstance(value, str):
                raise ValueError(f"{field_name} must be a string")
            object.__setattr__(self, field_name, value.strip())

        object.__setattr__(
            self,
            "required_skills",
            _clean_strings(self.required_skills, "required_skills"),
        )
        object.__setattr__(
            self,
            "preferred_skills",
            _clean_strings(self.preferred_skills, "preferred_skills"),
        )
        object.__setattr__(
            self,
            "required_languages",
            _clean_strings(self.required_languages, "required_languages"),
        )
        object.__setattr__(
            self,
            "minimum_years_experience",
            _optional_float(
                self.minimum_years_experience, "minimum_years_experience"
            ),
        )
        object.__setattr__(self, "remote", _optional_bool(self.remote, "remote"))
        if not isinstance(self.work_mode, WorkMode):
            try:
                object.__setattr__(self, "work_mode", WorkMode(self.work_mode))
            except ValueError as error:
                raise ValueError(
                    "work_mode must be remote, hybrid, office, or unknown"
                ) from error
        if self.work_mode is WorkMode.UNKNOWN and self.remote is True:
            object.__setattr__(self, "work_mode", WorkMode.REMOTE)
        elif self.work_mode is not WorkMode.UNKNOWN and self.remote is None:
            object.__setattr__(
                self, "remote", self.work_mode is WorkMode.REMOTE
            )
        object.__setattr__(
            self,
            "employment_type",
            _optional_text(self.employment_type, "employment_type"),
        )
        if self.published_at is not None and not isinstance(self.published_at, datetime):
            raise ValueError("published_at must be a datetime or null")
        evidence = tuple(self.requirement_evidence)
        if any(not isinstance(item, RequirementEvidence) for item in evidence):
            raise ValueError("requirement_evidence must contain evidence objects")
        object.__setattr__(self, "requirement_evidence", evidence)

    @property
    def job_id(self) -> str:
        return f"{self.source}:{self.external_id}"

    @property
    def is_remote(self) -> bool:
        return self.work_mode is WorkMode.REMOTE or self.remote is True

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> JobPosting:
        return cls(
            source=_text(data.get("source"), "source"),
            external_id=_text(data.get("external_id"), "external_id"),
            title=_text(data.get("title"), "title"),
            company=_text(data.get("company"), "company"),
            location=_text(data.get("location"), "location"),
            url=_text(data.get("url"), "url"),
            description=_text(data.get("description"), "description"),
            required_skills=_clean_strings(
                data.get("required_skills"), "required_skills"
            ),
            preferred_skills=_clean_strings(
                data.get("preferred_skills"), "preferred_skills"
            ),
            required_languages=_clean_strings(
                data.get("required_languages"), "required_languages"
            ),
            minimum_years_experience=_optional_float(
                data.get("minimum_years_experience"),
                "minimum_years_experience",
            ),
            remote=_optional_bool(data.get("remote"), "remote"),
            work_mode=WorkMode(
                _text(data.get("work_mode", WorkMode.UNKNOWN.value), "work_mode")
            ),
            employment_type=_optional_text(
                data.get("employment_type"), "employment_type"
            ),
            published_at=_parse_datetime(data.get("published_at"), "published_at"),
            requirement_evidence=tuple(
                RequirementEvidence.from_dict(item)
                for item in data.get("requirement_evidence", ())
                if isinstance(item, Mapping)
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "external_id": self.external_id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "url": self.url,
            "description": self.description,
            "required_skills": list(self.required_skills),
            "preferred_skills": list(self.preferred_skills),
            "required_languages": list(self.required_languages),
            "minimum_years_experience": self.minimum_years_experience,
            "remote": self.remote,
            "work_mode": self.work_mode.value,
            "employment_type": self.employment_type,
            "published_at": (
                self.published_at.isoformat() if self.published_at is not None else None
            ),
            "requirement_evidence": [
                item.to_dict() for item in self.requirement_evidence
            ],
        }


@dataclass(frozen=True, slots=True)
class MatchResult:
    job_id: str
    score: int
    level: MatchLevel
    component_scores: dict[str, int] = field(default_factory=dict)
    matched_skills: tuple[str, ...] = ()
    missing_required_skills: tuple[str, ...] = ()
    matched_roles: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0 <= self.score <= 100:
            raise ValueError("score must be between 0 and 100")
        if any(not 0 <= score <= 100 for score in self.component_scores.values()):
            raise ValueError("component scores must be between 0 and 100")


@dataclass(frozen=True, slots=True)
class ApplicationEvent:
    status: ApplicationStatus
    occurred_at: datetime = field(default_factory=utc_now)
    notes: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.status, ApplicationStatus):
            object.__setattr__(self, "status", ApplicationStatus(self.status))
        object.__setattr__(self, "notes", _text(self.notes, "notes"))
        if self.occurred_at.tzinfo is None:
            object.__setattr__(
                self, "occurred_at", self.occurred_at.replace(tzinfo=timezone.utc)
            )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ApplicationEvent:
        return cls(
            status=ApplicationStatus(_text(data.get("status"), "status")),
            occurred_at=_parse_datetime(data.get("occurred_at"), "occurred_at")
            or utc_now(),
            notes=_text(data.get("notes"), "notes"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "occurred_at": self.occurred_at.isoformat(),
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class ApplicationRecord:
    job_id: str
    status: ApplicationStatus = ApplicationStatus.FOUND
    notes: str = ""
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    history: tuple[ApplicationEvent, ...] = ()

    def __post_init__(self) -> None:
        if not self.job_id.strip():
            raise ValueError("job_id is required")
        object.__setattr__(self, "job_id", self.job_id.strip())
        object.__setattr__(self, "notes", self.notes.strip())
        if not isinstance(self.status, ApplicationStatus):
            object.__setattr__(self, "status", ApplicationStatus(self.status))
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot be earlier than created_at")
        history = tuple(self.history)
        if any(not isinstance(event, ApplicationEvent) for event in history):
            raise ValueError("history must contain application events")
        object.__setattr__(self, "history", history)

    @property
    def has_submission_history(self) -> bool:
        submitted_statuses = {
            ApplicationStatus.APPLIED,
            ApplicationStatus.REJECTED,
            ApplicationStatus.INTERVIEW,
            ApplicationStatus.OFFER,
        }
        return self.status in submitted_statuses or any(
            event.status in submitted_statuses for event in self.history
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ApplicationRecord:
        created_at = _parse_datetime(data.get("created_at"), "created_at")
        updated_at = _parse_datetime(data.get("updated_at"), "updated_at")
        raw_history = data.get("history")
        if raw_history is None:
            history: tuple[ApplicationEvent, ...] = ()
        elif isinstance(raw_history, list) and all(
            isinstance(item, dict) for item in raw_history
        ):
            history = tuple(ApplicationEvent.from_dict(item) for item in raw_history)
        else:
            raise ValueError("history must be a list of application events")
        return cls(
            job_id=_text(data.get("job_id"), "job_id"),
            status=ApplicationStatus(
                _text(data.get("status", ApplicationStatus.FOUND.value), "status")
            ),
            notes=_text(data.get("notes"), "notes"),
            created_at=created_at or utc_now(),
            updated_at=updated_at or created_at or utc_now(),
            history=history,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "history": [event.to_dict() for event in self.history],
        }
