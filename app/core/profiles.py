"""Candidate workspace settings shared by storage, GUI, and scheduling."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import Any, Mapping

from app.core.location import LocationSelection


def _text(value: object, field_name: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    return value.strip()


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
        if cleaned and cleaned.casefold() not in seen:
            result.append(cleaned)
            seen.add(cleaned.casefold())
    return tuple(result)


def _parse_datetime(value: object, field_name: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be an ISO timestamp or null")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{field_name} must be an ISO timestamp") from error
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def _location_to_dict(location: LocationSelection) -> dict[str, Any]:
    return {
        "name": location.name,
        "geonames_id": location.geonames_id,
        "country_code": location.country_code,
        "country": location.country,
        "admin1": location.admin1,
        "admin2": location.admin2,
        "admin3": location.admin3,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "postcodes": list(location.postcodes),
    }


def _location_from_dict(data: Mapping[str, Any]) -> LocationSelection:
    return LocationSelection(
        name=_text(data.get("name"), "name"),
        geonames_id=data.get("geonames_id"),
        country_code=_text(data.get("country_code"), "country_code"),
        country=_text(data.get("country"), "country"),
        admin1=_text(data.get("admin1"), "admin1"),
        admin2=_text(data.get("admin2"), "admin2"),
        admin3=_text(data.get("admin3"), "admin3"),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        postcodes=tuple(data.get("postcodes") or ()),
    )


@dataclass(frozen=True, slots=True)
class ProfileSummary:
    profile_id: str
    name: str
    created_at: datetime
    updated_at: datetime
    last_opened_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class SavedSearchPreferences:
    sources: tuple[str, ...] = ()
    roles: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    locations: tuple[LocationSelection, ...] = ()
    radius_km: float | None = None
    excluded_keywords: tuple[str, ...] = ()
    excluded_companies: tuple[str, ...] = ()
    remote_only: bool = False
    work_modes: tuple[str, ...] = ()
    minimum_score: int = 0
    result_sort: str = "За релевантністю"

    def __post_init__(self) -> None:
        for field_name in (
            "sources",
            "roles",
            "keywords",
            "excluded_keywords",
            "excluded_companies",
        ):
            object.__setattr__(
                self,
                field_name,
                _clean_strings(getattr(self, field_name), field_name),
            )
        locations = tuple(self.locations)
        if any(not isinstance(item, LocationSelection) for item in locations):
            raise ValueError("locations must contain LocationSelection objects")
        object.__setattr__(self, "locations", locations)
        if self.radius_km is not None:
            radius = float(self.radius_km)
            if not 0 < radius <= 500:
                raise ValueError("radius_km must be between 0 and 500")
            object.__setattr__(self, "radius_km", radius)
        if not isinstance(self.remote_only, bool):
            raise ValueError("remote_only must be true or false")
        allowed_modes = {"remote", "hybrid", "office", "unknown"}
        modes = _clean_strings(self.work_modes, "work_modes")
        if any(mode not in allowed_modes for mode in modes):
            raise ValueError("work_modes contains an unsupported work mode")
        object.__setattr__(self, "work_modes", modes)
        if not 0 <= int(self.minimum_score) <= 100:
            raise ValueError("minimum_score must be between 0 and 100")
        object.__setattr__(self, "minimum_score", int(self.minimum_score))
        object.__setattr__(self, "result_sort", self.result_sort.strip())

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> SavedSearchPreferences:
        raw_locations = data.get("locations", [])
        if raw_locations is None:
            raw_locations = []
        if not isinstance(raw_locations, list):
            raise ValueError("locations must be a list")
        return cls(
            sources=tuple(data.get("sources") or ()),
            roles=tuple(data.get("roles") or ()),
            keywords=tuple(data.get("keywords") or ()),
            locations=tuple(
                _location_from_dict(item)
                for item in raw_locations
                if isinstance(item, Mapping)
            ),
            radius_km=data.get("radius_km"),
            excluded_keywords=tuple(data.get("excluded_keywords") or ()),
            excluded_companies=tuple(data.get("excluded_companies") or ()),
            remote_only=data.get("remote_only", False),
            work_modes=tuple(data.get("work_modes") or ()),
            minimum_score=data.get("minimum_score", 0),
            result_sort=_text(
                data.get("result_sort", "За релевантністю"), "result_sort"
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "sources": list(self.sources),
            "roles": list(self.roles),
            "keywords": list(self.keywords),
            "locations": [_location_to_dict(item) for item in self.locations],
            "radius_km": self.radius_km,
            "excluded_keywords": list(self.excluded_keywords),
            "excluded_companies": list(self.excluded_companies),
            "remote_only": self.remote_only,
            "work_modes": list(self.work_modes),
            "minimum_score": self.minimum_score,
            "result_sort": self.result_sort,
        }


@dataclass(frozen=True, slots=True)
class SearchSchedule:
    enabled: bool = False
    daily_time: str = "09:00"
    last_run_at: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise ValueError("enabled must be true or false")
        try:
            parsed_time = time.fromisoformat(self.daily_time)
        except (TypeError, ValueError) as error:
            raise ValueError("daily_time must use HH:MM format") from error
        object.__setattr__(
            self, "daily_time", f"{parsed_time.hour:02d}:{parsed_time.minute:02d}"
        )
        if self.last_run_at is not None and self.last_run_at.tzinfo is None:
            object.__setattr__(
                self,
                "last_run_at",
                self.last_run_at.replace(tzinfo=timezone.utc),
            )

    def is_due(self, now: datetime | None = None) -> bool:
        if not self.enabled:
            return False
        current = (now or datetime.now().astimezone()).astimezone()
        scheduled_time = time.fromisoformat(self.daily_time)
        if current.timetz().replace(tzinfo=None) < scheduled_time:
            return False
        if self.last_run_at is None:
            return True
        return self.last_run_at.astimezone().date() < current.date()

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> SearchSchedule:
        return cls(
            enabled=data.get("enabled", False),
            daily_time=_text(data.get("daily_time", "09:00"), "daily_time"),
            last_run_at=_parse_datetime(data.get("last_run_at"), "last_run_at"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "daily_time": self.daily_time,
            "last_run_at": (
                self.last_run_at.isoformat() if self.last_run_at is not None else None
            ),
        }
