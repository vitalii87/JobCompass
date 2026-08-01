"""Structured location filters shared with future source connectors."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LocationQuery:
    name: str
    radius_km: float | None = None

    def __post_init__(self) -> None:
        cleaned = self.name.strip()
        if not cleaned:
            raise ValueError("Location name cannot be empty")
        object.__setattr__(self, "name", cleaned)
        if self.radius_km is not None and not 0 < self.radius_km <= 500:
            raise ValueError("Location radius must be between 0 and 500 km")

def build_location_queries(
    names: tuple[str, ...], radius_km: float | None = None
) -> tuple[LocationQuery, ...]:
    """Apply the selected radius to each location name."""

    return tuple(
        LocationQuery(name=name, radius_km=radius_km)
        for name in names
        if name.strip()
    )
