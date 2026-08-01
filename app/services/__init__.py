"""Application services shared by command-line and graphical interfaces."""

from app.services.cover_letter import (
    build_ai_prompt,
    build_cover_letter_draft,
    suggested_letter_language,
)
from app.services.resume import ResumeLoadResult, load_resume

__all__ = [
    "ResumeLoadResult",
    "build_ai_prompt",
    "build_cover_letter_draft",
    "suggested_letter_language",
    "load_resume",
]
