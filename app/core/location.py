"""Structured and disambiguated location filters for job-source connectors."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LocationSelection:
    """A city selected from geocoding results, independent from search radius."""

    name: str
    geonames_id: int | None = None
    country_code: str = ""
    country: str = ""
    admin1: str = ""
    admin2: str = ""
    admin3: str = ""
    latitude: float | None = None
    longitude: float | None = None
    postcodes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in (
            "name",
            "country_code",
            "country",
            "admin1",
            "admin2",
            "admin3",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str):
                raise ValueError(f"{field_name} must be a string")
            object.__setattr__(self, field_name, value.strip())
        if not self.name:
            raise ValueError("Location name cannot be empty")
        if self.geonames_id is not None and not isinstance(self.geonames_id, int):
            raise ValueError("geonames_id must be an integer or null")
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Latitude and longitude must be provided together")
        if self.latitude is not None:
            latitude = float(self.latitude)
            longitude = float(self.longitude)
            if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
                raise ValueError("Location coordinates are invalid")
            object.__setattr__(self, "latitude", latitude)
            object.__setattr__(self, "longitude", longitude)
        cleaned_postcodes = tuple(
            dict.fromkeys(
                str(postcode).strip()
                for postcode in self.postcodes
                if str(postcode).strip()
            )
        )
        object.__setattr__(self, "postcodes", cleaned_postcodes)

    @property
    def display_name(self) -> str:
        details: list[str] = []
        if self.postcodes:
            details.append("/".join(self.postcodes[:3]))
        for value in (self.admin3, self.admin2, self.admin1, self.country):
            if value and value.casefold() not in {
                item.casefold() for item in details
            } and value.casefold() != self.name.casefold():
                details.append(value)
        return self.name + (" — " + ", ".join(details) if details else "")

    @property
    def source_query(self) -> str:
        """Return a human-readable query that disambiguates same-named cities."""

        if self.postcodes:
            return f"{self.postcodes[0]} {self.name}"
        if self.admin1 and self.admin1.casefold() != self.name.casefold():
            return f"{self.name}, {self.admin1}"
        return self.name


@dataclass(frozen=True, slots=True)
class LocationQuery:
    name: str
    radius_km: float | None = None
    selection: LocationSelection | None = None

    def __post_init__(self) -> None:
        cleaned = self.name.strip()
        if not cleaned:
            raise ValueError("Location name cannot be empty")
        object.__setattr__(self, "name", cleaned)
        if self.radius_km is not None and not 0 < self.radius_km <= 500:
            raise ValueError("Location radius must be between 0 and 500 km")
        if self.selection is not None and not isinstance(
            self.selection, LocationSelection
        ):
            raise ValueError("selection must be a LocationSelection or null")

    @property
    def source_query(self) -> str:
        return self.selection.source_query if self.selection is not None else self.name


def build_location_queries(
    names: tuple[str, ...],
    radius_km: float | None = None,
    selections: tuple[LocationSelection, ...] = (),
) -> tuple[LocationQuery, ...]:
    """Apply the selected radius to each location name."""

    if selections:
        return tuple(
            LocationQuery(
                name=selection.name,
                radius_km=radius_km,
                selection=selection,
            )
            for selection in selections
        )
    return tuple(
        LocationQuery(name=name, radius_km=radius_km)
        for name in names
        if name.strip()
    )
