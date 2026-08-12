from __future__ import annotations

import unittest

from app.sources.jsonld import extract_job_postings


class JsonLdJobPostingTests(unittest.TestCase):
    def test_extracts_normalized_german_job_with_evidence(self) -> None:
        html = """
        <html><head><script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "JobPosting",
          "identifier": {"value": "REQ-42"},
          "title": "Test Automation Engineer (m/w/d)",
          "hiringOrganization": {"name": "Beispiel GmbH"},
          "datePosted": "2026-08-11",
          "employmentType": ["FULL_TIME"],
          "jobLocation": {"address": {
            "addressLocality": "Stuttgart",
            "addressRegion": "Baden-Württemberg",
            "addressCountry": "DE"
          }},
          "description": "<p>Ihr Profil: Python und Deutsch B2 sind erforderlich.</p>",
          "url": "/career/req-42"
        }
        </script></head></html>
        """

        jobs = extract_job_postings(
            html,
            "https://example.test/jobs",
            source="Company career pages",
        )

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].external_id, "REQ-42")
        self.assertEqual(jobs[0].company, "Beispiel GmbH")
        self.assertEqual(jobs[0].location, "Stuttgart, Baden-Württemberg, DE")
        self.assertEqual(jobs[0].url, "https://example.test/career/req-42")
        self.assertIn("Python", jobs[0].required_skills)
        self.assertEqual(jobs[0].published_at.date().isoformat(), "2026-08-11")

    def test_extracts_graph_and_remote_location(self) -> None:
        html = """
        <script type="application/ld+json">
        {"@graph": [{"@type": ["Thing", "JobPosting"], "name": "SDET",
        "hiringOrganization": {"name": "Remote GmbH"},
        "jobLocationType": "TELECOMMUTE",
        "applicantLocationRequirements": {"name": "Germany"},
        "description": "Automation testing"}]}
        </script>
        """
        job = extract_job_postings(
            html, "https://remote.test/job", source="Company career pages"
        )[0]

        self.assertTrue(job.is_remote)
        self.assertEqual(job.location, "Germany")


if __name__ == "__main__":
    unittest.main()
