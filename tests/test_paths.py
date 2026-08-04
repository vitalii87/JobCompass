from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.core.paths import default_data_path


class RuntimePathTests(unittest.TestCase):
    def test_source_mode_keeps_project_local_data(self) -> None:
        project = Path("C:/Projects/JobCompass")

        path = default_data_path(
            environment={}, frozen=False, current_directory=project
        )

        self.assertEqual(path, project / "data" / "jobcompass.json")

    def test_installed_app_uses_local_app_data(self) -> None:
        path = default_data_path(
            environment={"LOCALAPPDATA": "C:/Users/Test/AppData/Local"},
            executable="C:/Users/Test/AppData/Local/Programs/JobCompass/JobCompass.exe",
            frozen=True,
        )

        self.assertEqual(
            path,
            Path("C:/Users/Test/AppData/Local/JobCompass/data/jobcompass.json"),
        )

    def test_portable_marker_keeps_data_beside_executable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            app_directory = Path(directory)
            (app_directory / "portable.flag").touch()

            path = default_data_path(
                environment={"LOCALAPPDATA": "C:/ignored"},
                executable=app_directory / "JobCompass.exe",
                frozen=True,
            )

            self.assertEqual(path, app_directory / "data" / "jobcompass.json")

    def test_environment_override_has_highest_priority(self) -> None:
        path = default_data_path(
            environment={"JOBCOMPASS_DATA_PATH": "D:/Private/profile.json"},
            executable="C:/JobCompass/JobCompass.exe",
            frozen=True,
        )

        self.assertEqual(path, Path("D:/Private/profile.json"))


if __name__ == "__main__":
    unittest.main()
