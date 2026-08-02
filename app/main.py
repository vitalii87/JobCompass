"""Application launcher: GUI by default, CLI when arguments are supplied."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from app.interfaces.cli import main as cli_main
from app.core.paths import default_data_path


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments:
        from app.interfaces.gui import launch_gui

        return launch_gui()
    if arguments[0] == "gui":
        parser = argparse.ArgumentParser(prog="jobcompass gui")
        parser.add_argument("--data", type=Path, default=default_data_path())
        gui_args = parser.parse_args(arguments[1:])
        from app.interfaces.gui import launch_gui

        return launch_gui(gui_args.data)
    return cli_main(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
