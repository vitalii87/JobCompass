"""Command-line interface for the local JobCompass prototype."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from app.core.matcher import JobMatcher
from app.core.models import ApplicationStatus, CandidateProfile
from app.sources import JsonFileSource, SearchQuery
from app.storage import LocalJsonStore


DEFAULT_DATA_PATH = Path("data/jobcompass.json")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jobcompass",
        description="Local job search and application tracker",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help=f"path to local storage (default: {DEFAULT_DATA_PATH})",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("init", help="initialize empty local storage")

    import_parser = commands.add_parser(
        "import-jobs", help="import normalized vacancies from JSON"
    )
    import_parser.add_argument("file", type=Path)

    commands.add_parser("list-jobs", help="list stored vacancies")

    match_parser = commands.add_parser(
        "match", help="score stored vacancies against a candidate profile"
    )
    match_parser.add_argument("profile", type=Path)
    match_parser.add_argument("--minimum-score", type=int, default=0)

    status_parser = commands.add_parser(
        "set-status", help="set the application status for a vacancy"
    )
    status_parser.add_argument("job_id")
    status_parser.add_argument(
        "status", choices=[status.value for status in ApplicationStatus]
    )
    status_parser.add_argument("--notes")

    commands.add_parser("list-applications", help="list tracked applications")
    return parser


def _load_profile(path: Path) -> CandidateProfile:
    try:
        with path.open("r", encoding="utf-8") as stream:
            payload: Any = json.load(stream)
    except json.JSONDecodeError as error:
        raise ValueError(f"Profile is not valid JSON: {path}") from error
    if not isinstance(payload, dict):
        raise ValueError("Profile JSON must be an object")
    return CandidateProfile.from_dict(payload)


def _print_jobs(store: LocalJsonStore) -> None:
    jobs = store.list_jobs()
    if not jobs:
        print("No vacancies stored.")
        return
    for job in jobs:
        place = job.location or "location unknown"
        print(
            f"{job.job_id} | {job.title} | {job.company} | "
            f"{job.work_mode.value} | {place}"
        )


def _print_matches(
    store: LocalJsonStore, profile: CandidateProfile, minimum_score: int
) -> None:
    if not 0 <= minimum_score <= 100:
        raise ValueError("minimum-score must be between 0 and 100")
    matcher = JobMatcher()
    results = [
        (matcher.match(profile, job), job) for job in store.list_jobs()
    ]
    results.sort(key=lambda item: item[0].score, reverse=True)

    visible = [item for item in results if item[0].score >= minimum_score]
    if not visible:
        print("No matching vacancies found.")
        return
    for result, job in visible:
        print(
            f"{result.score:3d}% [{result.level.value}] "
            f"{job.title} — {job.company} ({job.job_id})"
        )
        if result.matched_skills:
            print("  Matched skills: " + ", ".join(result.matched_skills))
        if result.risks:
            for risk in result.risks:
                print(f"  Risk: {risk}")


def _print_applications(store: LocalJsonStore) -> None:
    applications = store.list_applications()
    if not applications:
        print("No applications tracked.")
        return
    for item in applications:
        notes = f" | {item.notes}" if item.notes else ""
        print(f"{item.job_id} | {item.status.value}{notes}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    store = LocalJsonStore(args.data)

    try:
        if args.command == "init":
            store.initialize()
            print(f"Storage ready: {store.path}")
        elif args.command == "import-jobs":
            jobs = JsonFileSource(args.file).search(SearchQuery())
            added = store.save_jobs(jobs)
            print(f"Imported {added} new vacancies ({len(jobs)} read).")
        elif args.command == "list-jobs":
            _print_jobs(store)
        elif args.command == "match":
            _print_matches(
                store,
                _load_profile(args.profile),
                args.minimum_score,
            )
        elif args.command == "set-status":
            record = store.set_application_status(
                args.job_id,
                ApplicationStatus(args.status),
                args.notes,
            )
            print(f"{record.job_id}: {record.status.value}")
        elif args.command == "list-applications":
            _print_applications(store)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
