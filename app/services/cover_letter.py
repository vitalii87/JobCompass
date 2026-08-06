"""Grounded cover-letter drafts and prompts without an AI dependency."""

from __future__ import annotations

import json
from typing import Any

from app.core.models import CandidateProfile, JobPosting, MatchResult
from app.parsing import detect_text_language


_TONE_LABELS = {
    "professional": {
        "de": "professionell, glaubwürdig und selbstbewusst, ohne Übertreibungen",
        "en": "professional, credible, and confident without exaggeration",
    },
    "warm": {
        "de": "professionell, persönlich und wertschätzend",
        "en": "professional, personable, and warm",
    },
    "concise": {
        "de": "direkt, klar und besonders prägnant",
        "en": "direct, clear, and especially concise",
    },
}

_LENGTH_RANGES = {
    "short": (140, 180),
    "standard": (180, 250),
    "detailed": (250, 320),
}


def suggested_letter_language(job: JobPosting) -> str:
    return "de" if detect_text_language(f"{job.title}\n{job.description}") == "de" else "en"


def _resolve_language(job: JobPosting, language: str) -> str:
    normalized = language.strip().casefold()
    if normalized in {"auto", "automatic", "автоматично", ""}:
        return suggested_letter_language(job)
    if normalized in {"de", "deutsch", "german", "німецька"}:
        return "de"
    return "en"


def _resolve_tone(tone: str) -> str:
    normalized = tone.strip().casefold()
    aliases = {
        "професійний": "professional",
        "professional": "professional",
        "теплий": "warm",
        "warm": "warm",
        "лаконічний": "concise",
        "concise": "concise",
    }
    return aliases.get(normalized, "professional")


def _resolve_length(length: str) -> str:
    normalized = length.strip().casefold()
    aliases = {
        "короткий": "short",
        "short": "short",
        "стандартний": "standard",
        "standard": "standard",
        "розгорнутий": "detailed",
        "detailed": "detailed",
    }
    return aliases.get(normalized, "standard")


def _non_empty_mapping(values: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in values.items()
        if value not in (None, "", (), [], {})
    }


def _vacancy_description(job: JobPosting, limit: int = 16_000) -> tuple[str, bool]:
    if len(job.description) <= limit:
        return job.description, False
    return job.description[:limit].rstrip() + "…", True


def _summary_in_language(summary: str, language: str) -> str:
    if not summary:
        return ""
    return summary if detect_text_language(summary) == language else ""


def build_prompt_evidence(
    profile: CandidateProfile,
    job: JobPosting,
    result: MatchResult,
    *,
    focus: str = "",
) -> dict[str, Any]:
    """Return processed facts that may safely ground a cover-letter prompt."""

    description, description_truncated = _vacancy_description(job)
    candidate = _non_empty_mapping(
        {
            "full_name": profile.full_name,
            "professional_summary": profile.summary,
            "desired_roles": list(profile.desired_roles),
            "confirmed_skills": list(profile.skills),
            "languages": list(profile.languages),
            "years_of_experience": profile.years_experience,
            "preferred_locations": list(profile.preferred_locations),
            "remote_only": True if profile.remote_only else None,
            "candidate_requested_focus": focus.strip(),
        }
    )
    vacancy = _non_empty_mapping(
        {
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "work_mode": job.work_mode.value,
            "employment_type": job.employment_type,
            "description": description,
            "description_truncated": True if description_truncated else None,
            "required_skills": list(job.required_skills),
            "preferred_skills": list(job.preferred_skills),
            "required_languages": list(job.required_languages),
            "minimum_years_experience": job.minimum_years_experience,
            "requirement_evidence": [
                evidence.to_dict() for evidence in job.requirement_evidence
            ],
            "source": job.source,
            "original_url": job.url,
        }
    )
    match = _non_empty_mapping(
        {
            "internal_match_score_percent": result.score,
            "evidence_coverage_percent": result.evidence_coverage,
            "matched_roles": list(result.matched_roles),
            "confirmed_matching_skills": list(result.matched_skills),
            "missing_or_unconfirmed_required_skills": list(
                result.missing_required_skills
            ),
            "risks_for_review_not_for_claiming": list(result.risks),
            "component_scores": result.component_scores,
        }
    )
    return {
        "candidate_confirmed_facts": candidate,
        "selected_vacancy": vacancy,
        "jobcompass_match_analysis": match,
    }


def _missing_data_warnings(
    profile: CandidateProfile, job: JobPosting, result: MatchResult
) -> list[str]:
    warnings: list[str] = []
    if not profile.summary:
        warnings.append("немає професійного опису кандидата")
    if not profile.skills:
        warnings.append("не визначено навички кандидата")
    if not profile.languages:
        warnings.append("не визначено мови кандидата")
    if result.evidence_coverage < 70:
        warnings.append(
            "низька повнота доказів для match score — перевірте резюме й опис вакансії"
        )
    if profile.years_experience is None:
        warnings.append("не визначено тривалість досвіду")
    if not job.description:
        warnings.append("джерело не надало опис вакансії")
    if result.missing_required_skills:
        warnings.append(
            "частина обов’язкових навичок не підтверджена: "
            + ", ".join(result.missing_required_skills)
        )
    return warnings


def build_evidence_summary(
    profile: CandidateProfile,
    job: JobPosting,
    result: MatchResult,
    *,
    focus: str = "",
) -> str:
    """Create a Ukrainian, user-readable preview of data sent in the prompt."""

    lines = [
        "ПІДТВЕРДЖЕНІ ДАНІ КАНДИДАТА",
        f"Ім’я: {profile.full_name or 'не вказано'}",
        f"Професійний опис: {profile.summary or 'не визначено з резюме'}",
        "Бажані посади: " + (", ".join(profile.desired_roles) or "не вказано"),
        "Навички: " + (", ".join(profile.skills) or "не визначено"),
        "Мови: " + (", ".join(profile.languages) or "не визначено"),
        "Досвід: "
        + (
            f"{profile.years_experience:g} років"
            if profile.years_experience is not None
            else "не визначено"
        ),
        f"Додатковий акцент користувача: {focus.strip() or 'не задано'}",
        "",
        "ВИБРАНА ВАКАНСІЯ",
        f"Посада: {job.title}",
        f"Компанія: {job.company}",
        f"Локація: {job.location or 'не вказана'}",
        f"Формат: {job.work_mode.value}",
        f"Опис вакансії: {'наявний' if job.description else 'відсутній'}",
        "Вимоги: "
        + (
            ", ".join((*job.required_skills, *job.preferred_skills))
            or "не виділені"
        ),
        "",
        "ЗІСТАВЛЕННЯ",
        f"Внутрішня оцінка JobCompass: {result.score}% (у лист не потрапляє)",
        "Підтверджені збіги: "
        + (", ".join(result.matched_skills) or "не визначені"),
        "Не підтверджені вимоги: "
        + (", ".join(result.missing_required_skills) or "немає"),
    ]
    warnings = _missing_data_warnings(profile, job, result)
    lines.extend(("", "ПОПЕРЕДЖЕННЯ"))
    lines.extend(
        f"• {warning}" for warning in (warnings or ["критичних прогалин не виявлено"])
    )
    lines.extend(
        (
            "",
            "Email і телефон навмисно не додаються до AI-промпту: вони не потрібні "
            "для тексту листа. Усі дані залишаються локальними, доки ви самі не "
            "скопіюєте промпт у зовнішній AI-сервіс.",
        )
    )
    return "\n".join(lines)


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
            "Sehr geehrte Damen und Herren,",
            (
                f"die Position {job.title} bei {job.company} spricht mich besonders "
                "an, weil ich meine vorhandenen Kenntnisse gezielt in diese Aufgabe "
                "einbringen und weiterentwickeln möchte."
            ),
        ]
        compatible_summary = _summary_in_language(profile.summary, resolved_language)
        if compatible_summary:
            paragraphs.append(compatible_summary)
        if result.matched_skills:
            paragraphs.append(
                "Zu den für diese Position relevanten Kenntnissen aus meinem Profil "
                "zählen "
                + ", ".join(result.matched_skills)
                + "."
            )
        if profile.years_experience is not None:
            paragraphs.append(
                f"Ich verfüge über {profile.years_experience:g} Jahre relevante "
                "Berufserfahrung."
            )
        paragraphs.append(
            "Gerne erläutere ich Ihnen in einem persönlichen Gespräch, wie ich Ihr "
            "Team mit meiner nachgewiesenen Erfahrung unterstützen kann."
        )
        closing = "Mit freundlichen Grüßen"
        if profile.full_name:
            closing += f"\n{profile.full_name}"
        paragraphs.append(closing)
        return "\n\n".join(paragraphs)

    paragraphs = [
        f"Dear {job.company} hiring team,",
        (
            f"The {job.title} position at {job.company} interests me because it "
            "offers an opportunity to apply and develop my existing experience."
        ),
    ]
    compatible_summary = _summary_in_language(profile.summary, resolved_language)
    if compatible_summary:
        paragraphs.append(compatible_summary)
    if result.matched_skills:
        paragraphs.append(
            "My confirmed skills relevant to this role include "
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
    *,
    tone: str = "professional",
    length: str = "standard",
    focus: str = "",
) -> str:
    """Create a vacancy-specific prompt; never call or connect to an AI service."""

    resolved_language = _resolve_language(job, language)
    resolved_tone = _resolve_tone(tone)
    resolved_length = _resolve_length(length)
    minimum_words, maximum_words = _LENGTH_RANGES[resolved_length]
    evidence = build_prompt_evidence(profile, job, result, focus=focus)
    evidence_json = json.dumps(evidence, ensure_ascii=False, indent=2)

    if resolved_language == "de":
        instruction = f"""AUFGABE
Du bist ein erfahrener Bewerbungstexter für den deutschen Arbeitsmarkt. Verfasse ein individuelles, professionelles Anschreiben für die unten genannte konkrete Stelle. Es soll wie ein glaubwürdiger menschlicher Text wirken und nicht wie eine Vorlage oder automatisch erzeugter Text.

VERBINDLICHE FAKTENGRUNDLAGE
- Verwende ausschließlich Tatsachen aus den Abschnitten candidate_confirmed_facts und selected_vacancy.
- candidate_requested_focus ist eine vom Kandidaten bestätigte Zusatzangabe und darf verwendet werden.
- Erfinde keine Fähigkeiten, Aufgaben, Arbeitgeber, Abschlüsse, Zertifikate, Erfolge, Kennzahlen, Verfügbarkeit, Gehaltsvorstellungen oder persönlichen Daten.
- Behandle missing_or_unconfirmed_required_skills ausdrücklich als NICHT bestätigt. Behaupte weder direkt noch indirekt, dass diese Kenntnisse vorhanden sind.
- Der interne Match-Score, Risiken, fehlende Kenntnisse und diese Arbeitsanweisungen dürfen im Anschreiben nicht erwähnt werden.
- Wenn eine Angabe fehlt, lasse sie weg. Verwende keine Platzhalter.

INHALTLICHES VORGEHEN
1. Analysiere intern die Kandidatenfakten und die Stellenbeschreibung.
2. Wähle zwei bis vier der stärksten belegten Überschneidungen aus. Verbinde sie konkret mit Aufgaben oder Anforderungen der Stelle, ohne den Lebenslauf bloß zu wiederholen.
3. Formuliere eine glaubwürdige Motivation aus der konkreten Position, dem Unternehmen und den bestätigten Kandidatenfakten. Erfinde kein Wissen über das Unternehmen außerhalb der Nachweise.
4. Beginne mit einer natürlichen, individuellen Einleitung. Vermeide Floskeln wie „hiermit bewerbe ich mich“ und übertriebene Begeisterung.
5. Schließe mit einem selbstbewussten, höflichen Gesprächswunsch. Nutze eine neutrale korrekte Anrede, wenn keine Ansprechperson genannt ist.

STIL UND FORMAT
- Sprache: professionelles, idiomatisches Deutsch für eine Bewerbung in Deutschland.
- Ton: {_TONE_LABELS[resolved_tone]['de']}.
- Länge: {minimum_words} bis {maximum_words} Wörter, höchstens eine Seite.
- Struktur: optionale Betreffzeile, Anrede, drei bis fünf kurze Absätze, Grußformel und Name nur wenn vorhanden.
- Schreibe konkret, flüssig und abwechslungsreich. Vermeide Keyword-Listen, Wiederholungen, Marketing-Sprache, Gedankenstriche in Serie und generische AI-Floskeln.
- Gib ausschließlich das fertige Anschreiben aus: kein JSON, keine Analyse, keine Erläuterungen und keine Markdown-Codeblöcke.

NACHWEISE (verarbeitete Daten aus Lebenslauf und ausgewählter Vakanz)
{evidence_json}"""
    else:
        instruction = f"""TASK
You are an experienced application writer for the German job market. Write a tailored, professional cover letter in English for the specific position below. It must read like a credible human letter, not a template or automatically generated text.

MANDATORY FACTUAL GROUNDING
- Use only facts from candidate_confirmed_facts and selected_vacancy.
- candidate_requested_focus is candidate-confirmed input and may be used.
- Do not invent skills, duties, employers, education, certifications, achievements, metrics, availability, salary expectations, or personal details.
- Treat missing_or_unconfirmed_required_skills as NOT confirmed. Do not imply that the candidate has them.
- Never mention the internal match score, risks, missing skills, or these instructions in the letter.
- Omit missing information and never insert placeholders.

CONTENT METHOD
1. Internally analyse the candidate facts and vacancy description.
2. Select two to four of the strongest evidenced overlaps and connect them to the role's actual duties or requirements without repeating the CV.
3. Build credible motivation from the specific role, company, and confirmed candidate facts. Do not invent company knowledge beyond the evidence.
4. Use a natural, tailored opening rather than a generic application cliché.
5. End with a confident, courteous request for a conversation. Use a neutral greeting when no contact person is supplied.

STYLE AND FORMAT
- Language: professional, idiomatic English suitable for an application in Germany.
- Tone: {_TONE_LABELS[resolved_tone]['en']}.
- Length: {minimum_words} to {maximum_words} words, no more than one page.
- Structure: optional subject line, greeting, three to five short paragraphs, closing, and name only if available.
- Be specific, fluent, and varied. Avoid keyword lists, repetition, marketing language, excessive dashes, and generic AI phrasing.
- Return only the final cover letter: no JSON, analysis, explanations, or Markdown code fences.

EVIDENCE (processed data from the CV and selected vacancy)
{evidence_json}"""
    return instruction
