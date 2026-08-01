"""Grounded cover-letter drafts and prompts without an AI dependency."""

from __future__ import annotations

import json

from app.core.models import CandidateProfile, JobPosting, MatchResult
from app.parsing import detect_text_language


def suggested_letter_language(job: JobPosting) -> str:
    return "de" if detect_text_language(f"{job.title}\n{job.description}") == "de" else "en"


def _resolve_language(job: JobPosting, language: str) -> str:
    normalized = language.strip().casefold()
    if normalized in {"auto", "automatic", "автоматично", ""}:
        return suggested_letter_language(job)
    if normalized in {"de", "deutsch", "german", "німецька"}:
        return "de"
    return "en"


def build_cover_letter_draft(
    profile: CandidateProfile,
    job: JobPosting,
    result: MatchResult,
    language: str = "auto",
) -> str:
    """Create an editable DE/EN draft using only confirmed candidate facts."""

    resolved_language = _resolve_language(job, language)
    if resolved_language == "de":
        paragraphs = [
            f"Sehr geehrtes Recruiting-Team von {job.company},",
            (
                f"mit großem Interesse bewerbe ich mich auf die Position "
                f"{job.title} bei {job.company}."
            ),
        ]
        if profile.summary:
            paragraphs.append(profile.summary)
        if result.matched_skills:
            paragraphs.append(
                "Für diese Position bringe ich bestätigte Kenntnisse in "
                + ", ".join(result.matched_skills)
                + " mit."
            )
        if profile.years_experience is not None:
            paragraphs.append(
                f"Ich verfüge über {profile.years_experience:g} Jahre relevante "
                "Berufserfahrung."
            )
        paragraphs.append(
            "Gerne erläutere ich Ihnen in einem persönlichen Gespräch, wie ich "
            "Ihr Team mit meiner bestätigten Erfahrung unterstützen kann."
        )
        closing = "Mit freundlichen Grüßen"
        if profile.full_name:
            closing += f"\n{profile.full_name}"
        paragraphs.append(closing)
        return "\n\n".join(paragraphs)

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
    language: str = "auto",
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
    resolved_language = _resolve_language(job, language)
    target_language = "Deutsch" if resolved_language == "de" else "English"
    instruction = (
        f"Verfasse ein prägnantes professionelles Anschreiben auf {target_language}.\n"
        "Verwende ausschließlich Fakten aus den folgenden Nachweisen. Erfinde "
        "keine Fähigkeiten, Erfahrungen, Ausbildung, Erfolge, Arbeitgeber oder "
        "persönlichen Angaben. Behaupte nicht, dass fehlende Pflichtkenntnisse "
        "vorhanden sind. Der Text darf höchstens 300 Wörter enthalten. Gib nur "
        "das Anschreiben aus.\n\nNACHWEISE:\n"
        if resolved_language == "de"
        else f"Write a concise professional cover letter in {target_language}.\n"
        "Use only facts explicitly present in the evidence below. "
        "Do not invent skills, experience, education, achievements, employers, "
        "or personal details. Do not claim missing required skills. "
        "Keep the result under 300 words and return only the letter.\n\n"
        "EVIDENCE:\n"
    )
    return instruction + json.dumps(evidence, ensure_ascii=False, indent=2)
