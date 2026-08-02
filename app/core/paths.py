"""Runtime paths for source, installed, and portable JobCompass modes."""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path


APP_DIRECTORY_NAME = "JobCompass"
DATA_FILE_NAME = "jobcompass.json"
PORTABLE_MARKER = "portable.flag"
DATA_PATH_ENVIRONMENT_VARIABLE = "JOBCOMPASS_DATA_PATH"


def default_data_path(
    *,
    environment: Mapping[str, str] | None = None,
    executable: str | Path | None = None,
    frozen: bool | None = None,
    current_directory: str | Path | None = None,
) -> Path:
    """Resolve a writable data path without mixing installed and portable data."""

    active_environment = os.environ if environment is None else environment
    override = active_environment.get(DATA_PATH_ENVIRONMENT_VARIABLE, "").strip()
    if override:
        return Path(os.path.expandvars(override)).expanduser()

    is_frozen = bool(getattr(sys, "frozen", False)) if frozen is None else frozen
    executable_path = Path(executable or sys.executable).resolve()
    executable_directory = executable_path.parent

    if is_frozen and (executable_directory / PORTABLE_MARKER).is_file():
        return executable_directory / "data" / DATA_FILE_NAME

    if is_frozen:
        local_app_data = active_environment.get("LOCALAPPDATA", "").strip()
        if local_app_data:
            return Path(local_app_data) / APP_DIRECTORY_NAME / "data" / DATA_FILE_NAME
        return (
            Path.home()
            / "AppData"
            / "Local"
            / APP_DIRECTORY_NAME
            / "data"
            / DATA_FILE_NAME
        )

    source_directory = Path(current_directory or Path.cwd())
    return source_directory / "data" / DATA_FILE_NAME
