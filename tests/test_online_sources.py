from __future__ import annotations

import unittest
from typing import Any

from app.core.location import LocationSelection
from app.sources import ArbeitnowSource, BundesagenturSource, RemotiveSource, SearchQuery
from app.sources.http import SourceError


class FakeClient:
    def __init__(self, responses: dict[str, dict[str, Any]]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, dict[str, object]]] = []

    def get_json(
        self,
        url: str,
        params: dict[str, object] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        self.calls.append((url, dict(params or {})))
        for marker, response in self.responses.items():
            if marker in url:
                return response
        raise AssertionError(f"Unexpected URL: {url}")


class OnlineSourceTests(unittest.TestCase):
    def test_arbeitnow_normalizes_html_and_uses_role_or_logic(self) -> None:
        client = FakeClient(
            {
                "job-board-api": {
                    "data": [
                        {
                            "slug": "office-1",
                            "company_name": "Beispiel GmbH",
                            "title": "Office Manager (m/w/d)",
                            "description": (
                                "&lt;p&gt;Ihr Profil: MS Office und Terminkoordination "
                                "sind erforderlich.&lt;/p&gt;"
                            ),
                            "remote": False,
                            "url": "https://example.test/office-1",
                            "tags": [],
                            "job_types": ["Vollzeit"],
                            "location": "Stuttgart",
                            "created_at": 1_700_000_000,
                        }
                    ],
                    "meta": {"last_page": 1},
                }
            }
        )
        source = ArbeitnowSource(client=client, max_pages=1)

        jobs = source.search(
            SearchQuery(roles=("PMO Assistant", "Office Manager"))
        )

        self.assertEqual(len(jobs), 1)
        self.assertNotIn("&lt;", jobs[0].description)
        self.assertIn("Microsoft Office", jobs[0].required_skills)

    def test_arbeitnow_caches_pages_and_keeps_partial_results_on_rate_limit(self) -> None:
        class RateLimitClient:
            def __init__(self) -> None:
                self.calls: list[int] = []

            def get_json(
                self,
                _url: str,
                params: dict[str, object] | None = None,
                _headers: dict[str, str] | None = None,
            ) -> dict[str, Any]:
                page = int((params or {}).get("page", 1))
                self.calls.append(page)
                if page > 1:
                    raise SourceError("Сервер повернув HTTP 429: Too Many Requests")
                return {
                    "data": [
                        {
                            "slug": "cached-office",
                            "company_name": "Example GmbH",
                            "title": "Office Manager",
                            "description": "Office administration",
                            "remote": True,
                            "url": "https://example.test/cached-office",
                            "location": "Remote",
                        }
                    ]
                }

        client = RateLimitClient()
        source = ArbeitnowSource(client=client, max_pages=3)
        query = SearchQuery(roles=("Office Manager",))

        first = source.search(query)
        second = source.search(query)

        self.assertEqual(len(first), 1)
        self.assertEqual(len(second), 1)
        self.assertIn("429", source.last_partial_error)
        self.assertEqual(client.calls.count(1), 1)

    def test_bundesagentur_uses_each_role_and_radius(self) -> None:
        search_response = {
            "ergebnisliste": [
                {
                    "stellenangebotsTitel": "Kaufmännische Assistenz (m/w/d)",
                    "referenznummer": "REF-1",
                    "stellenlokationen": [
                        {
                            "adresse": {
                                "ort": "Stuttgart",
                                "region": "BADEN_WUERTTEMBERG",
                            }
                        }
                    ],
                    "firma": "Beispiel GmbH",
                    "datumErsteVeroeffentlichung": "2026-08-01",
                }
            ],
            "maxErgebnisse": 1,
        }
        detail_response = {
            "stellenangebotsTitel": "Kaufmännische Assistenz (m/w/d)",
            "stellenangebotsBeschreibung": (
                "Ihr Profil: MS Office und Terminkoordination sind erforderlich."
            ),
            "firma": "Beispiel GmbH",
            "referenznummer": "REF-1",
        }
        client = FakeClient(
            {"jobdetails": detail_response, "/jobs": search_response}
        )
        source = BundesagenturSource(
            client=client, max_results=10, detail_workers=1
        )

        jobs = source.search(
            SearchQuery(
                roles=("Kaufmännische Assistenz", "Office Manager"),
                locations=("Stuttgart",),
                location_radius_km=50,
            )
        )

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].location, "Stuttgart, Baden-Württemberg")
        search_calls = [call for call in client.calls if call[0].endswith("/jobs")]
        self.assertEqual(len(search_calls), 2)
        self.assertTrue(search_calls[0][0].endswith("/pc/v6/jobs"))
        self.assertEqual(search_calls[0][1]["umkreis"], 50)
        self.assertEqual(
            {call[1]["was"] for call in search_calls},
            {"Kaufmännische Assistenz", "Office Manager"},
        )

    def test_bundesagentur_keeps_other_roles_when_one_role_has_no_results(self) -> None:
        search_response = {
            "stellenangebote": [
                {
                    "titel": "Kaufmännische Assistenz (m/w/d)",
                    "refnr": "REF-2",
                    "arbeitsort": {"ort": "Stuttgart"},
                    "arbeitgeber": "Beispiel GmbH",
                }
            ],
            "maxErgebnisse": 1,
        }
        detail_response = {
            "stellenangebotsTitel": "Kaufmännische Assistenz (m/w/d)",
            "stellenangebotsBeschreibung": "Kaufmännische Assistenz gesucht.",
            "firma": "Beispiel GmbH",
        }

        class PartialResultClient(FakeClient):
            def get_json(
                self,
                url: str,
                params: dict[str, object] | None = None,
                headers: dict[str, str] | None = None,
            ) -> dict[str, Any]:
                self.calls.append((url, dict(params or {})))
                if "jobdetails" in url:
                    return detail_response
                if params and params.get("was") == "PMO Assistant":
                    return {"maxErgebnisse": 0, "page": 1, "size": 5}
                return search_response

        client = PartialResultClient({})
        source = BundesagenturSource(
            client=client, max_results=10, detail_workers=1
        )

        jobs = source.search(
            SearchQuery(
                roles=("PMO Assistant", "Kaufmännische Assistenz"),
                locations=("Stuttgart",),
                location_radius_km=37,
            )
        )

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].title, "Kaufmännische Assistenz (m/w/d)")

    def test_bundesagentur_keeps_nearby_city_returned_by_server_radius(self) -> None:
        search_response = {
            "stellenangebote": [
                {
                    "titel": "Office Manager (m/w/d)",
                    "refnr": "RADIUS-1",
                    "arbeitsort": {
                        "ort": "Stuttgart",
                        "region": "Baden-Württemberg",
                    },
                    "arbeitgeber": "Nearby GmbH",
                }
            ],
            "maxErgebnisse": 1,
        }
        detail_response = {
            "stellenangebotsTitel": "Office Manager (m/w/d)",
            "stellenangebotsBeschreibung": "Office Management und MS Office.",
            "firma": "Nearby GmbH",
        }
        client = FakeClient(
            {"jobdetails": detail_response, "/jobs": search_response}
        )
        location = LocationSelection(
            name="Köngen",
            geonames_id=2890248,
            admin1="Baden-Württemberg",
            admin3="Landkreis Esslingen",
            country="Deutschland",
            country_code="DE",
            latitude=48.68333,
            longitude=9.36667,
        )

        jobs = BundesagenturSource(
            client=client, max_results=10, detail_workers=1
        ).search(
            SearchQuery(
                roles=("Office Manager",),
                locations=("Köngen",),
                location_selections=(location,),
                location_radius_km=50,
            )
        )

        self.assertEqual([job.location for job in jobs], ["Stuttgart, Baden-Württemberg"])
        search_call = next(call for call in client.calls if call[0].endswith("/jobs"))
        self.assertEqual(search_call[1]["wo"], "Köngen, Baden-Württemberg")
        self.assertEqual(search_call[1]["umkreis"], 50)

    def test_remotive_keeps_germany_compatible_remote_job(self) -> None:
        client = FakeClient(
            {
                "remote-jobs": {
                    "jobs": [
                        {
                            "id": 10,
                            "url": "https://remotive.test/jobs/10",
                            "title": "Project Coordinator",
                            "company_name": "Remote GmbH",
                            "candidate_required_location": "Europe",
                            "description": "<p>Project coordination</p>",
                            "job_type": "full_time",
                            "publication_date": "2026-08-01T10:00:00Z",
                            "tags": [],
                        }
                    ]
                }
            }
        )

        jobs = RemotiveSource(client=client).search(
            SearchQuery(
                roles=("Project Coordinator",), locations=("Stuttgart",)
            )
        )

        self.assertEqual(len(jobs), 1)
        self.assertTrue(jobs[0].is_remote)


if __name__ == "__main__":
    unittest.main()
