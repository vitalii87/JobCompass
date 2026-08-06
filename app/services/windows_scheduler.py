"""Optional Windows Task Scheduler integration for installed JobCompass builds."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from app.core.profiles import SearchSchedule


def sync_windows_search_task(
    profile_id: str,
    schedule: SearchSchedule,
    data_path: str | Path,
) -> str:
    """Create, update, or remove a per-profile daily background task."""
    if os.name != "nt":
        return "Фонове завдання підтримується лише у Windows."
    if not getattr(sys, "frozen", False):
        return (
            "У режимі вихідного коду пошук виконається при відкритті програми; "
            "Windows-завдання створюється встановленою або portable версією."
        )

    task_name = f"JobCompass-{profile_id}"
    if not schedule.enabled:
        subprocess.run(
            ["schtasks", "/Delete", "/TN", task_name, "/F"],
            capture_output=True,
            text=True,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return "Фонове завдання Windows вимкнено."

    executable = str(Path(sys.executable).resolve())
    storage = str(Path(data_path).resolve())
    task_command = (
        f'"{executable}" --data "{storage}" scheduled-search '
        f'--profile-id "{profile_id}"'
    )
    result = subprocess.run(
        [
            "schtasks",
            "/Create",
            "/TN",
            task_name,
            "/TR",
            task_command,
            "/SC",
            "DAILY",
            "/ST",
            schedule.daily_time,
            "/F",
        ],
        capture_output=True,
        text=True,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise OSError(detail or "Windows Task Scheduler rejected the task")
    message = "Щоденне фонове завдання Windows оновлено."
    if (Path(executable).parent / "portable.flag").exists():
        message += (
            " Portable-папка повинна залишатися доступною за тим самим шляхом."
        )
    return message
