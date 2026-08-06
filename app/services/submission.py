"""Application submission preparation and local audit helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.core.models import ApplicationSubmission, CandidateProfile, SubmissionMode


class SubmissionPreparationError(ValueError):
    """Raised when selected application materials cannot be prepared safely."""


def resume_sha256(path: str | Path) -> str:
    resume = Path(path)
    if not resume.is_file():
        raise SubmissionPreparationError(
            "Оригінальний файл резюме не знайдено. Оберіть актуальний PDF або DOCX."
        )
    digest = hashlib.sha256()
    try:
        with resume.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
    except OSError as error:
        raise SubmissionPreparationError(
            f"Не вдалося прочитати оригінальний файл резюме: {error}"
        ) from error
    return digest.hexdigest()


def prepare_submission(
    *,
    mode: SubmissionMode,
    destination_url: str,
    resume_path: str = "",
    cover_letter_text: str = "",
    profile: CandidateProfile,
) -> ApplicationSubmission:
    """Snapshot exactly what the user intends to submit."""

    normalized_path = str(Path(resume_path).resolve()) if resume_path.strip() else ""
    digest = resume_sha256(normalized_path) if normalized_path else ""
    return ApplicationSubmission(
        mode=mode,
        destination_url=destination_url,
        resume_path=normalized_path,
        resume_name=Path(normalized_path).name if normalized_path else "",
        resume_sha256=digest,
        cover_letter_text=cover_letter_text,
        contact_full_name=profile.full_name,
        contact_email=profile.email,
        contact_phone=profile.phone,
    )
