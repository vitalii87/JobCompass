from __future__ import annotations

import unittest

from app.core.models import JobPosting
from app.core.source_registry import AtsType
from app.sources import SearchQuery
from app.sources.discovery import AutomaticSourceDiscoverer, detect_source_url
from app.sources.http import SourceError


class _DiscoveryClient:
    user_agent = "JobCompass/Test"

    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages

    def get_text(self, url: str, _headers: object = None) -> str:
        try:
            return self.pages[url]
        except KeyError as error:
            raise SourceError("not found") from error


class SourceDiscoveryTests(unittest.TestCase):
    def test_detects_and_normalizes_supported_ats(self) -> None:
        cases = {
            "https://boards.greenhouse.io/acme/jobs/123": AtsType.GREENHOUSE,
            "https://jobs.eu.lever.co/acme/abc": AtsType.LEVER,
            "https://jobs.ashbyhq.com/acme/abc": AtsType.ASHBY,
            "https://acme.jobs.personio.de/job/123": AtsType.PERSONIO,
            "https://acme.wd3.myworkdayjobs.com/de-DE/External/job/123": AtsType.WORKDAY,
            "https://acme.example/karriere/offene-stellen": AtsType.GENERIC_HTML,
        }

        for url, expected in cases.items():
            with self.subTest(url=url):
                entry = detect_source_url(url)
                self.assertIsNotNone(entry)
                self.assertEqual(entry.ats_type, expected)  # type: ignore[union-attr]

    def test_learns_direct_ats_link_from_an_aggregator_job(self) -> None:
        job_url = "https://www.arbeitsagentur.de/jobsuche/jobdetail/123"
        pages = {
            "https://www.arbeitsagentur.de/robots.txt": "User-agent: *\nAllow: /",
            job_url: (
                '<a href="https://jobs.lever.co/acme/position-1">'
                "Auf Unternehmenswebsite bewerben</a>"
            ),
        }
        discoverer = AutomaticSourceDiscoverer(
            _DiscoveryClient(pages), max_job_pages=5, max_site_probes=5
        )

        report = discoverer.discover(
            [
                JobPosting(
                    "Bundesagentur für Arbeit",
                    "123",
                    "QA Engineer",
                    "Acme GmbH",
                    location="Stuttgart, Baden-Württemberg, Deutschland",
                    url=job_url,
                )
            ],
            SearchQuery(roles=("QA Engineer",)),
        )

        self.assertEqual(len(report.entries), 1)
        self.assertEqual(report.entries[0].ats_type, AtsType.LEVER)
        self.assertEqual(report.entries[0].career_url, "https://jobs.lever.co/acme")
        self.assertEqual(report.entries[0].country, "DE")

    def test_company_job_page_leads_to_its_declared_sitemap(self) -> None:
        job_url = "https://acme.example/openings/123"
        pages = {
            "https://acme.example/robots.txt": (
                "User-agent: *\nAllow: /\n"
                "Sitemap: https://acme.example/jobs-sitemap.xml"
            ),
            job_url: "<html><body>QA Engineer</body></html>",
            "https://acme.example/jobs-sitemap.xml": (
                "<urlset><url><loc>https://acme.example/careers/qa</loc>"
                "</url></urlset>"
            ),
        }
        report = AutomaticSourceDiscoverer(
            _DiscoveryClient(pages), max_site_probes=20
        ).discover(
            [JobPosting("Direct", "123", "QA Engineer", "Acme", url=job_url)],
            SearchQuery(roles=("QA Engineer",)),
        )

        sitemap_entries = [
            entry
            for entry in report.entries
            if entry.career_url == "https://acme.example/jobs-sitemap.xml"
        ]
        self.assertEqual(len(sitemap_entries), 1)
        self.assertEqual(sitemap_entries[0].ats_type, AtsType.GENERIC_HTML)


if __name__ == "__main__":
    unittest.main()
