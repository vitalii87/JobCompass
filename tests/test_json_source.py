from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.sources import JsonFileSource, SearchQuery


class JsonFileSourceTests(unittest.TestCase):
    def test_source_loads_and_filters_normalized_jobs(self) -> None:
        payload = {
            "jobs": [
                {
                    "source": "fixture",
                    "external_id": "1",
                    "title": "Python Developer",
                    "company": "ACME",
                    "location": "Berlin",
                    "remote": True,
                },
                {
                    "source": "fixture",
                    "external_id": "2",
                    "title": "Java Developer",
                    "company": "ACME",
                    "location": "Munich",
                    "remote": False,
                },
            ]
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jobs.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            jobs = JsonFileSource(path).search(
                SearchQuery(keywords=("Python",), remote_only=True)
            )

        self.assertEqual([job.job_id for job in jobs], ["fixture:1"])

    def test_invalid_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jobs.json"
            path.write_text("{}", encoding="utf-8")

            with self.assertRaises(ValueError):
                JsonFileSource(path).search(SearchQuery())

    def test_german_raw_description_is_enriched_during_import(self) -> None:
        payload = [
            {
                "source": "german-board",
                "external_id": "de-1",
                "title": "Python-Entwickler",
                "company": "Beispiel GmbH",
                "description": (
                    "Ihr Profil\n"
                    "Fundierte Kenntnisse in Python sind erforderlich.\n"
                    "Docker ist von Vorteil."
                ),
            }
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "german-jobs.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            job = JsonFileSource(path).search(SearchQuery())[0]

        self.assertEqual(job.required_skills, ("Python",))
        self.assertEqual(job.preferred_skills, ("Docker",))
        self.assertTrue(job.requirement_evidence)


if __name__ == "__main__":
    unittest.main()
