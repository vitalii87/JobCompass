"""Grounded cover-letter drafts and prompts without an AI dependency."""

from __future__ import annotations

import json

from app.core.models import CandidateProfile, JobPosting, MatchResult


def build_cover_letter_draft(
    profile: CandidateProfile,
    job: JobPosting,
    result: MatchResult,
) -> str:
    """Create an editable English draft using only confirmed candidate facts."""

    greeting = f"Dear {job.company} hiring team,"
    paragraphs = [
        greeting,
        f"I am writing to apply for the {job.title} position at {job.company}.",
    ]
    if profile.summary:
        paragraphs.append(profile.summary)
    if result.matched_skills:
        paragraphs.append(
            "My relevant skills for this role include "
            + ", ".join(result.matched_skills)
            + "."
        )
    if profile.years_experience is not None:
        paragraphs.append(
            f"I have {profile.years_experience:g} years of relevant professional "
            "experience."
        )
    paragraphs.append(
        "I would welcome the opportunity to discuss how my confirmed experience "
        "could contribute to your team."
    )
    closing = "Best regards"
    if profile.full_name:
        closing += f",\n{profile.full_name}"
    paragraphs.append(closing)
    return "\n\n".join(paragraphs)


def build_ai_prompt(
    profile: CandidateProfile,
    job: JobPosting,
    result: MatchResult,
    language: str = "English",
) -> str:
    """Create a portable prompt; this function never calls an AI service."""

    evidence = {
        "candidate": profile.to_dict(),
        "vacancy": job.to_dict(),
        "match": {
            "score": result.score,
            "matched_skills": list(result.matched_skills),
            "missing_required_skills": list(result.missing_required_skills),
            "risks": list(result.risks),
        },
    }
    return (
        f"Write a concise professional cover letter in {language}.\n"
        "Use only facts explicitly present in the evidence below. "
        "Do not invent skills, experience, education, achievements, employers, "
        "or personal details. Do not claim missing required skills. "
        "Keep the result under 300 words and return only the letter.\n\n"
        "EVIDENCE:\n"
        + json.dumps(evidence, ensure_ascii=False, indent=2)
    )
