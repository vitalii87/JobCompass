"""Local text parsers for resumes and vacancy descriptions."""

from app.parsing.german_job import detect_text_language, enrich_job_posting

__all__ = ["detect_text_language", "enrich_job_posting"]
