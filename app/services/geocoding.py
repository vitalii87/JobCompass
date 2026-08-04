"""Keyless city suggestions backed by Open-Meteo's GeoNames search."""

from __future__ import annotations

from typing import Any

from app.core.location import LocationSelection
from app.sources.http import JsonHttpClient, SourceError


class LocationGeocoder:
    endpoint = "https://geocoding-api.open-meteo.com/v1/search"

    def __init__(self, client: JsonHttpClient | None = None) -> None:
        self.client = client or JsonHttpClient(timeout=10.0)
        self._cache: dict[
            tuple[str, str, str, int], tuple[LocationSelection, ...]
        ] = {}

    def search(
        self,
        text: str,
        *,
        country_code: str = "DE",
        language: str = "de",
        count: int = 10,
    ) -> list[LocationSelection]:
        query = text.strip()
        if len(query) < 2:
            return []
        normalized_country = country_code.strip().upper()
        cache_key = (
            query.casefold(),
            normalized_country,
            language.casefold(),
            count,
        )
        cached = self._cache.get(cache_key)
        if cached is not None:
            return list(cached)

        payload = self.client.get_json(
            self.endpoint,
            {
                "name": query,
                "count": max(1, min(count, 20)),
                "language": language.strip().lower() or "de",
                "countryCode": normalized_country or None,
                "format": "json",
            },
        )
        rows = payload.get("results", [])
        if not isinstance(rows, list):
            raise SourceError("Сервіс підказок міст повернув некоректні дані")

        suggestions: list[LocationSelection] = []
        seen_ids: set[int] = set()
        for row in rows:
            if not isinstance(row, dict):
                continue
            suggestion = self._normalize(row)
            if suggestion is None:
                continue
            if (
                suggestion.geonames_id is not None
                and suggestion.geonames_id in seen_ids
            ):
                continue
            if suggestion.geonames_id is not None:
                seen_ids.add(suggestion.geonames_id)
            suggestions.append(suggestion)
        self._cache[cache_key] = tuple(suggestions)
        return suggestions

    @staticmethod
    def _normalize(row: dict[str, Any]) -> LocationSelection | None:
        name = row.get("name")
        latitude = row.get("latitude")
        longitude = row.get("longitude")
        if not isinstance(name, str) or not name.strip():
            return None
        if not isinstance(latitude, (int, float)) or not isinstance(
            longitude, (int, float)
        ):
            return None
        raw_id = row.get("id")
        geonames_id = raw_id if isinstance(raw_id, int) else None
        raw_postcodes = row.get("postcodes")
        postcodes = (
            tuple(str(item) for item in raw_postcodes)
            if isinstance(raw_postcodes, list)
            else ()
        )
        return LocationSelection(
            name=name,
            geonames_id=geonames_id,
            country_code=str(row.get("country_code", "")),
            country=str(row.get("country", "")),
            admin1=str(row.get("admin1", "")),
            admin2=str(row.get("admin2", "")),
            admin3=str(row.get("admin3", "")),
            latitude=float(latitude),
            longitude=float(longitude),
            postcodes=postcodes,
        )
