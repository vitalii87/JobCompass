"""Persistent metadata for automatically discovered vacancy sources."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Mapping
from urllib.parse import urlsplit, urlunsplit


class AtsType(StrEnum):
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    ASHBY = "ashby"
    PERSONIO = "personio"
    WORKDAY = "workday"
    JSON_LD = "json_ld"
    GENERIC_HTML = "generic_html"


class SourceRegistryStatus(StrEnum):
    DISCOVERED = "discovered"
    ACTIVE = "active"
    ERROR = "error"
    BLOCKED = "blocked"
    DISABLED = "disabled"


def normalize_registry_url(value: str) -> str:
    parts = urlsplit(value.strip())
    if parts.scheme.casefold() not in {"http", "https"} or not parts.netloc:
        raise ValueError("Source URL must use http or https")
    return urlunsplit(
        (
            parts.scheme.casefold(),
            parts.netloc.casefold(),
            parts.path.rstrip("/") or "/",
            parts.query,
            "",
        )
    )


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


@dataclass(frozen=True, slots=True)
class SourceRegistryEntry:
    company: str
    career_url: str
    ats_type: AtsType
    country: str = ""
    region: str = ""
    last_success: datetime | None = None
    last_checked: datetime | None = None
    status: SourceRegistryStatus = SourceRegistryStatus.DISCOVERED
    discovered_from: str = "automatic"

    def __post_init__(self) -> None:
        object.__setattr__(self, "company", self.company.strip())
        object.__setattr__(self, "career_url", normalize_registry_url(self.career_url))
        object.__setattr__(self, "country", self.country.strip())
        object.__setattr__(self, "region", self.region.strip())
        object.__setattr__(self, "discovered_from", self.discovered_from.strip())
        if not isinstance(self.ats_type, AtsType):
            object.__setattr__(self, "ats_type", AtsType(self.ats_type))
        if not isinstance(self.status, SourceRegistryStatus):
            object.__setattr__(self, "status", SourceRegistryStatus(self.status))

    @property
    def source_id(self) -> str:
        return hashlib.sha256(self.career_url.encode("utf-8")).hexdigest()[:24]

    def checked(
        self,
        *,
        succeeded: bool,
        blocked: bool = False,
        at: datetime | None = None,
    ) -> SourceRegistryEntry:
        checked_at = at or datetime.now(timezone.utc)
        return replace(
            self,
            last_checked=checked_at,
            last_success=checked_at if succeeded else self.last_success,
            status=(
                SourceRegistryStatus.ACTIVE
                if succeeded
                else SourceRegistryStatus.BLOCKED
                if blocked
                else SourceRegistryStatus.ERROR
            ),
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> SourceRegistryEntry:
        return cls(
            company=str(data.get("company", "")),
            career_url=str(data.get("career_url", "")),
            ats_type=AtsType(str(data.get("ats_type", AtsType.GENERIC_HTML.value))),
            country=str(data.get("country", "")),
            region=str(data.get("region", "")),
            last_success=_parse_datetime(data.get("last_success")),
            last_checked=_parse_datetime(data.get("last_checked")),
            status=SourceRegistryStatus(
                str(data.get("status", SourceRegistryStatus.DISCOVERED.value))
            ),
            discovered_from=str(data.get("discovered_from", "automatic")),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "company": self.company,
            "career_url": self.career_url,
            "ats_type": self.ats_type.value,
            "country": self.country,
            "region": self.region,
            "last_success": (
                self.last_success.isoformat() if self.last_success else None
            ),
            "last_checked": (
                self.last_checked.isoformat() if self.last_checked else None
            ),
            "status": self.status.value,
            "discovered_from": self.discovered_from,
        }


SOURCE_NAME_BY_ATS = {
    AtsType.GREENHOUSE: "Greenhouse careers",
    AtsType.LEVER: "Lever careers",
    AtsType.ASHBY: "Ashby careers",
    AtsType.PERSONIO: "Personio careers",
    AtsType.WORKDAY: "Workday careers",
    AtsType.JSON_LD: "Company career pages",
    AtsType.GENERIC_HTML: "Company career pages",
}
