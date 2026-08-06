from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from app.interfaces.cli import main


class CliWorkflowTests(unittest.TestCase):
    def test_import_match_and_status_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data_path = root / "jobcompass.json"
            jobs_path = root / "jobs.json"
            profile_path = root / "profile.json"
            jobs_path.write_text(
                json.dumps(
                    [
                        {
                            "source": "fixture",
                            "external_id": "1",
                            "title": "Python Developer",
                            "company": "ACME",
                            "required_skills": ["Python"],
                        }
                    ]
                ),
                encoding="utf-8",
            )
            profile_path.write_text(
                json.dumps(
                    {
                        "desired_roles": ["Python Developer"],
                        "skills": ["Python"],
                    }
                ),
                encoding="utf-8",
            )

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "--data",
                            str(data_path),
                            "import-jobs",
                            str(jobs_path),
                        ]
                    ),
                    0,
                )
                self.assertEqual(
                    main(["--data", str(data_path), "match", str(profile_path)]),
                    0,
                )
                self.assertEqual(
                    main(
                        [
                            "--data",
                            str(data_path),
                            "set-status",
                            "fixture:1",
                            "Interesting",
                        ]
                    ),
                    0,
                )

        rendered = output.getvalue()
        self.assertIn("Imported 1 new vacancies", rendered)
        self.assertIn("88% [full] Python Developer", rendered)
        self.assertIn("fixture:1: Interesting", rendered)


if __name__ == "__main__":
    unittest.main()
