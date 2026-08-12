from __future__ import annotations

import unittest

from app.sources import SearchQuery
from app.sources.careers import (
    AshbyCareerSource,
    GenericCareerPageSource,
    GreenhouseCareerSource,
    LeverCareerSource,
    PersonioCareerSource,
    build_career_sources,
)
from app.sources.http import SourceError


class _CareerClient:
    user_agent = "JobCompass/Test"

    def __init__(self, payload: object) -> None:
        self.payload = payload

    def get_json(self, _url: str, _params: object = None) -> dict:
        if not isinstance(self.payload, dict):
            raise AssertionError("Expected mapping")
        return self.payload

    def get_json_value(self, _url: str, _params: object = None) -> object:
        return self.payload


class CareerSourceTests(unittest.TestCase):
    def test_greenhouse_normalizes_public_board(self) -> None:
        source = GreenhouseCareerSource(
            ("acme",),
            client=_CareerClient(
                {"jobs": [{
                    "id": 7,
                    "title": "QA Engineer",
                    "location": {"name": "Stuttgart"},
                    "absolute_url": "https://boards.greenhouse.io/acme/jobs/7",
                    "content": "<p>Python testing</p>",
                    "updated_at": "2026-08-11T08:00:00Z"
                }]}
            ),
        )

        jobs = source.search(SearchQuery(roles=("QA Engineer",)))

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].external_id, "acme:7")

    def test_lever_and_ashby_normalize_public_boards(self) -> None:
        lever = LeverCareerSource(
            (("acme", True),),
            client=_CareerClient([{
                "id": "L1", "text": "Software Tester",
                "categories": {"location": "Berlin", "commitment": "Full-time"},
                "descriptionPlain": "Test automation", "hostedUrl": "https://jobs.eu.lever.co/acme/L1",
                "createdAt": 1786435200000
            }]),
        )
        ashby = AshbyCareerSource(
            ("acme",),
            client=_CareerClient({"jobs": [{
                "title": "QA Engineer", "location": "Remote",
                "isRemote": True, "descriptionHtml": "<p>Python</p>",
                "jobUrl": "https://jobs.ashbyhq.com/acme/A1"
            }]}),
        )

        self.assertEqual(len(lever.search(SearchQuery(roles=("Software Tester",)))), 1)
        self.assertTrue(ashby.search(SearchQuery(roles=("QA Engineer",)))[0].is_remote)

    def test_personio_normalizes_public_xml_feed(self) -> None:
        class _XmlClient:
            def get_text(self, _url: str, _headers: object = None) -> str:
                return """<workzag-jobs><position><id>4103</id>
                    <subcompany>Acme GmbH</subcompany><office>Stuttgart</office>
                    <name>Office Manager</name><jobDescriptions><jobDescription>
                    <name>Dein Profil</name><value>Deutsch und MS Office</value>
                    </jobDescription></jobDescriptions><employmentType>permanent</employmentType>
                    <schedule>full-time</schedule><createdAt>2026-08-11T08:00:00+0200</createdAt>
                    </position></workzag-jobs>"""

        source = PersonioCareerSource(
            ("acme.jobs.personio.de",), client=_XmlClient()  # type: ignore[arg-type]
        )

        jobs = source.search(SearchQuery(roles=("Office Manager",)))

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].company, "Acme GmbH")
        self.assertEqual(jobs[0].location, "Stuttgart")

    def test_factory_groups_known_ats_and_generic_urls(self) -> None:
        sources = build_career_sources((
            "https://boards.greenhouse.io/acme",
            "https://jobs.eu.lever.co/example",
            "https://jobs.ashbyhq.com/demo",
            "https://acme.jobs.personio.de",
            "https://acme.wd3.myworkdayjobs.com/de-DE/External",
            "https://company.example/careers",
        ))

        self.assertEqual(
            set(sources),
            {"Greenhouse careers", "Lever careers", "Ashby careers", "Personio careers", "Workday careers", "Company career pages"},
        )

    def test_generic_reader_honors_robots_for_linked_job_pages(self) -> None:
        class _TextClient:
            user_agent = "JobCompass/Test"

            def __init__(self) -> None:
                self.read_urls: list[str] = []

            def get_text(self, url: str) -> str:
                self.read_urls.append(url)
                pages = {
                    "https://company.example/robots.txt": (
                        "User-agent: *\nAllow: /careers\nAllow: /jobs/public\n"
                        "Disallow: /jobs/private"
                    ),
                    "https://company.example/careers": (
                        '<a href="/jobs/public">Public</a>'
                        '<a href="/jobs/private">Private</a>'
                    ),
                    "https://company.example/jobs/public": (
                        '<script type="application/ld+json">'
                        '{"@type":"JobPosting","title":"QA Engineer",'
                        '"hiringOrganization":{"name":"Acme GmbH"},'
                        '"url":"https://company.example/jobs/public"}'
                        "</script>"
                    ),
                }
                if url not in pages:
                    raise AssertionError(f"Unexpected read: {url}")
                return pages[url]

        client = _TextClient()
        source = GenericCareerPageSource(
            ("https://company.example/careers",),
            client=client,  # type: ignore[arg-type]
        )

        jobs = source.search(SearchQuery(roles=("QA Engineer",)))

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].url, "https://company.example/jobs/public")
        self.assertNotIn("https://company.example/jobs/private", client.read_urls)

    def test_generic_reader_refuses_blocked_job_boards(self) -> None:
        source = GenericCareerPageSource(("https://www.indeed.com/jobs",))

        with self.assertRaises(SourceError):
            source.search(SearchQuery())


if __name__ == "__main__":
    unittest.main()
