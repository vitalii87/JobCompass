from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app.core.profiles import SearchSchedule
from app.services import windows_scheduler


class WindowsSchedulerTests(unittest.TestCase):
    def test_enabled_schedule_registers_profile_specific_headless_command(self) -> None:
        completed = SimpleNamespace(returncode=0, stdout="", stderr="")
        with (
            patch.object(windows_scheduler.os, "name", "nt"),
            patch.object(windows_scheduler.sys, "frozen", True, create=True),
            patch.object(
                windows_scheduler.sys, "executable", r"C:\JobCompass\JobCompass.exe"
            ),
            patch.object(
                windows_scheduler.subprocess, "run", return_value=completed
            ) as run,
        ):
            message = windows_scheduler.sync_windows_search_task(
                "profile-1",
                SearchSchedule(enabled=True, daily_time="08:30"),
                Path(r"C:\Data\jobcompass.json"),
            )

        command = run.call_args.args[0]
        self.assertEqual(command[0:3], ["schtasks", "/Create", "/TN"])
        self.assertIn("JobCompass-profile-1", command)
        self.assertIn("scheduled-search", command[5])
        self.assertIn("--profile-id", command[5])
        self.assertIn("08:30", command)
        self.assertIn("оновлено", message)


if __name__ == "__main__":
    unittest.main()
