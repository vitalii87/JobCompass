"""Application services shared by command-line and graphical interfaces."""

from app.services.cover_letter import (
    build_ai_prompt,
    build_cover_letter_draft,
    build_evidence_summary,
    build_prompt_evidence,
    suggested_letter_language,
)
from app.services.geocoding import LocationGeocoder
from app.services.resume import ResumeLoadResult, load_resume
from app.services.windows_scheduler import sync_windows_search_task
from app.services.update import (
    ReleaseAsset,
    ReleaseInfo,
    UpdateError,
    check_latest_release,
    download_release_asset,
    is_newer_version,
    runtime_mode,
)
from app.services.submission import (
    SubmissionPreparationError,
    prepare_submission,
    resume_sha256,
)

__all__ = [
    "ResumeLoadResult",
    "LocationGeocoder",
    "build_ai_prompt",
    "build_cover_letter_draft",
    "build_evidence_summary",
    "build_prompt_evidence",
    "suggested_letter_language",
    "load_resume",
    "sync_windows_search_task",
    "ReleaseAsset",
    "ReleaseInfo",
    "UpdateError",
    "check_latest_release",
    "download_release_asset",
    "is_newer_version",
    "runtime_mode",
    "SubmissionPreparationError",
    "prepare_submission",
    "resume_sha256",
]
