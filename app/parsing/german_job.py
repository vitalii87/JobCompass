"""Conservative German-first extraction from raw vacancy descriptions."""

from __future__ import annotations

import re
from dataclasses import replace

from app.core.models import JobPosting, RequirementEvidence, WorkMode
from app.core.taxonomy import (
    canonicalize_values,
    canonical_language,
    canonical_skill,
    extract_skill_mentions,
    normalize_term,
)


_REQUIRED_HEADINGS = {
    "anforderungen",
    "ihr profil",
    "dein profil",
    "das bringen sie mit",
    "das bringst du mit",
    "qualifikationen",
    "was wir erwarten",
    "was sie mitbringen",
    "was du mitbringst",
}
_PREFERRED_HEADINGS = {
    "wuenschenswert",
    "von vorteil",
    "idealerweise",
    "nice to have",
}
_OTHER_HEADINGS = {
    "ihre aufgaben",
    "deine aufgaben",
    "aufgaben",
    "wir bieten",
    "was wir bieten",
    "benefits",
    "ueber uns",
}
_REQUIRED_MARKERS = (
    "erforderlich",
    "zwingend",
    "voraussetzung",
    "setzen wir voraus",
    "fundierte kenntnisse",
    "sehr gute kenntnisse",
    "mehrjaehrige erfahrung",
    "bringen sie mit",
    "bringst du mit",
    "must have",
    "required",
)
_PREFERRED_MARKERS = (
    "wuenschenswert",
    "von vorteil",
    "idealerweise",
    "nice to have",
    "optional",
    "pluspunkt",
    "preferred",
)
_NEGATIVE_MARKERS = (
    "keine voraussetzung",
    "nicht erforderlich",
    "nicht zwingend",
    "kein muss",
    "kann erlernt werden",
)
_GERMAN_SIGNALS = {
    "anforderungen",
    "aufgaben",
    "berufserfahrung",
    "deutschkenntnisse",
    "kenntnisse",
    "mitbringen",
    "unternehmen",
    "wir bieten",
    "wuenschenswert",
}
_ENGLISH_SIGNALS = {
    "requirements",
    "responsibilities",
    "experience",
    "skills",
    "we offer",
    "preferred",
    "candidate",
}
_NUMBER_WORDS = {
    "ein": 1,
    "eine": 1,
    "einem": 1,
    "zwei": 2,
    "drei": 3,
    "vier": 4,
    "fuenf": 5,
    "sechs": 6,
    "sieben": 7,
    "acht": 8,
    "neun": 9,
    "zehn": 10,
}
_EXPERIENCE_PATTERN = re.compile(
    r"(?:mindestens|min\.?|ab)?\s*"
    r"(?P<years>\d+(?:[.,]\d+)?|ein(?:e|em)?|zwei|drei|vier|fuenf|sechs|sieben|acht|neun|zehn)"
    r"\s*\+?\s*jahr(?:e|en)?",
    re.IGNORECASE,
)


def detect_text_language(text: str) -> str:
    """Return ``de`` or ``en`` using transparent local signals."""

    normalized = normalize_term(text)
    german_score = sum(signal in normalized for signal in _GERMAN_SIGNALS)
    english_score = sum(signal in normalized for signal in _ENGLISH_SIGNALS)
    if german_score > english_score or any(
        token in normalized
        for token in ("deutsch", "entwickler", "berufserfahrung", "kenntnisse")
    ):
        return "de"
    return "en"


def _section_for_heading(normalized: str) -> str | None:
    if normalized in _REQUIRED_HEADINGS:
        return "required"
    if normalized in _PREFERRED_HEADINGS:
        return "preferred"
    if normalized in _OTHER_HEADINGS:
        return "other"
    return None


def _classification(normalized: str, section: str | None) -> str | None:
    if any(marker in normalized for marker in _NEGATIVE_MARKERS):
        return None
    if any(marker in normalized for marker in _PREFERRED_MARKERS):
        return "preferred"
    if any(marker in normalized for marker in _REQUIRED_MARKERS):
        return "required"
    if section in {"required", "preferred"}:
        return section
    return None


def _sentences(line: str) -> list[str]:
    return [
        part.strip(" \t-•●")
        for part in re.split(r"(?<=[.!?;])\s+|[•●]", line)
        if part.strip(" \t-•●")
    ]


def _experience_years(normalized: str) -> float | None:
    if "erfahrung" not in normalized and "experience" not in normalized:
        return None
    match = _EXPERIENCE_PATTERN.search(normalized)
    if match is None:
        return None
    raw = match.group("years")
    if raw in _NUMBER_WORDS:
        return float(_NUMBER_WORDS[raw])
    return float(raw.replace(",", "."))


def _detect_work_mode(text: str) -> tuple[WorkMode, str | None]:
    for raw_line in text.splitlines():
        normalized = normalize_term(raw_line)
        if any(
            marker in normalized
            for marker in (
                "hybrid",
                "hybrides arbeiten",
                "homeoffice tage",
                "tage homeoffice",
                "mobiles arbeiten",
            )
        ):
            return WorkMode.HYBRID, raw_line.strip()
        if any(
            marker in normalized
            for marker in ("100 remote", "full remote", "remote first", "vollstaendig remote")
        ):
            return WorkMode.REMOTE, raw_line.strip()
        if any(
            marker in normalized
            for marker in ("vor ort", "praesenzarbeit", "onsite", "office based")
        ):
            return WorkMode.OFFICE, raw_line.strip()
    return WorkMode.UNKNOWN, None


def enrich_job_posting(job: JobPosting) -> JobPosting:
    """Add only evidence-backed fields missing from a normalized job."""

    if not job.description.strip():
        return job

    required: list[str] = list(job.required_skills)
    preferred: list[str] = list(job.preferred_skills)
    required_languages: list[str] = list(job.required_languages)
    evidence: list[RequirementEvidence] = list(job.requirement_evidence)
    minimum_years = job.minimum_years_experience
    section: str | None = None

    for raw_line in job.description.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if ":" in line:
            possible_heading, remaining = line.split(":", 1)
            inline_section = _section_for_heading(normalize_term(possible_heading))
            if inline_section is not None:
                section = inline_section
                line = remaining.strip()
                if not line:
                    continue
        normalized_line = normalize_term(line.rstrip(":"))
        heading_section = _section_for_heading(normalized_line)
        if heading_section is not None:
            section = heading_section
            continue

        for sentence in _sentences(line):
            normalized = normalize_term(sentence)
            classification = _classification(normalized, section)
            if classification is None:
                continue

            skills = extract_skill_mentions(sentence)
            target = required if classification == "required" else preferred
            for skill in skills:
                if skill not in target:
                    target.append(skill)
                    evidence.append(
                        RequirementEvidence(
                            field="skill",
                            value=skill,
                            classification=classification,
                            excerpt=sentence,
                        )
                    )

            if classification == "required":
                for signal, language in (
                    ("deutsch", "German"),
                    ("englisch", "English"),
                    ("english", "English"),
                    ("german", "German"),
                ):
                    if signal in normalized and language not in required_languages:
                        required_languages.append(language)
                        evidence.append(
                            RequirementEvidence(
                                field="language",
                                value=language,
                                classification="required",
                                excerpt=sentence,
                            )
                        )

                years = _experience_years(normalized)
                if years is not None and minimum_years is None:
                    minimum_years = years
                    evidence.append(
                        RequirementEvidence(
                            field="experience",
                            value=f"{years:g} years",
                            classification="required",
                            excerpt=sentence,
                        )
                    )

    normalized_required = canonicalize_values(required, canonical_skill)
    required_keys = {normalize_term(value) for value in normalized_required}
    normalized_preferred = tuple(
        value
        for value in canonicalize_values(preferred, canonical_skill)
        if normalize_term(value) not in required_keys
    )
    normalized_languages = canonicalize_values(
        required_languages, canonical_language
    )
    work_mode = job.work_mode
    remote = job.remote
    detected_mode, mode_excerpt = _detect_work_mode(job.description)
    if work_mode is WorkMode.UNKNOWN and detected_mode is not WorkMode.UNKNOWN:
        work_mode = detected_mode
        remote = detected_mode is WorkMode.REMOTE
        if mode_excerpt:
            evidence.append(
                RequirementEvidence(
                    field="work_mode",
                    value=detected_mode.value,
                    classification="detected",
                    excerpt=mode_excerpt,
                )
            )

    return replace(
        job,
        required_skills=normalized_required,
        preferred_skills=normalized_preferred,
        required_languages=normalized_languages,
        minimum_years_experience=minimum_years,
        work_mode=work_mode,
        remote=remote,
        requirement_evidence=tuple(evidence),
    )
