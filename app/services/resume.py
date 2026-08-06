"""Local resume loading with conservative, user-reviewable extraction."""

from __future__ import annotations

import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from app.core.models import CandidateProfile
from app.core.taxonomy import (
    canonical_skill,
    canonicalize_values,
    extract_skill_mentions,
)


_EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_PHONE_PATTERN = re.compile(r"(?<!\w)(?:\+?\d[\d ()/.-]{7,}\d)(?!\w)")
_GERMAN_POSTAL_LOCATION_PATTERN = re.compile(
    r"\b\d{5}\s+(?P<city>[A-ZÄÖÜ][A-Za-zÄÖÜäöüß.-]+)\b"
)
_YEARS_PATTERN = re.compile(
    r"(?P<years>\d+(?:[.,]\d+)?)\s*(?:years?|yrs?|jahr(?:e|en)?|рок(?:и|ів)?|р\.)\b",
    re.I,
)
_UNLABELED_EXPERIENCE_PATTERN = re.compile(
    r"(?P<years>\d+(?:[.,]\d+)?)\s*"
    r"(?:years?|yrs?|jahr(?:e|en)?|рок(?:и|ів)?|р\.)\s*"
    r"(?:of\s+)?(?:relevant\s+|professional\s+)?"
    r"(?:experience|berufserfahrung|erfahrung|досвіду)",
    re.I,
)
_LANGUAGE_MENTION_PATTERN = re.compile(
    r"\b(?P<language>Deutsch|German|Englisch|English|Ukrainisch|Ukrainian)\b"
    r"(?:\s*[-:,(]?\s*(?P<level>[ABC][12]|Muttersprache|native|fließend|fluent))?",
    re.I,
)
_LABEL_PATTERN = re.compile(r"^\s*([^:]{2,40})\s*:\s*(.*)$")

_LABELS = {
    "name": "full_name",
    "full name": "full_name",
    "ім'я": "full_name",
    "ім’я": "full_name",
    "піб": "full_name",
    "email": "email",
    "e-mail": "email",
    "електронна пошта": "email",
    "phone": "phone",
    "телефон": "phone",
    "summary": "summary",
    "profile": "summary",
    "profil": "summary",
    "про себе": "summary",
    "профіль": "summary",
    "desired role": "desired_roles",
    "desired roles": "desired_roles",
    "position": "desired_roles",
    "wunschposition": "desired_roles",
    "gewünschte position": "desired_roles",
    "бажана посада": "desired_roles",
    "посада": "desired_roles",
    "skills": "skills",
    "technical skills": "skills",
    "kenntnisse": "skills",
    "fähigkeiten": "skills",
    "technische kenntnisse": "skills",
    "навички": "skills",
    "технічні навички": "skills",
    "languages": "languages",
    "sprachen": "languages",
    "мови": "languages",
    "location": "preferred_locations",
    "preferred location": "preferred_locations",
    "wohnort": "preferred_locations",
    "standort": "preferred_locations",
    "локація": "preferred_locations",
    "бажана локація": "preferred_locations",
    "experience": "experience",
    "years of experience": "experience",
    "berufserfahrung": "experience",
    "досвід": "experience",
}
_LIST_FIELDS = {"desired_roles", "skills", "languages", "preferred_locations"}


@dataclass(frozen=True, slots=True)
class ResumeLoadResult:
    profile: CandidateProfile
    raw_text: str
    warnings: tuple[str, ...] = ()


def _split_values(value: str) -> list[str]:
    cleaned = value.strip().lstrip("-•·* ")
    return [item.strip() for item in re.split(r"[,;|]", cleaned) if item.strip()]


def _docx_text(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as archive:
            document = archive.read("word/document.xml")
    except (FileNotFoundError, KeyError, zipfile.BadZipFile) as error:
        raise ValueError(f"Cannot read DOCX resume: {path}") from error

    try:
        root = ElementTree.fromstring(document)
    except ElementTree.ParseError as error:
        raise ValueError(f"DOCX document XML is invalid: {path}") from error

    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    paragraphs: list[str] = []
    for paragraph in root.iter(f"{namespace}p"):
        text = "".join(
            node.text or "" for node in paragraph.iter(f"{namespace}t")
        ).strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def _pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise ValueError(
            "Для читання PDF потрібен локальний пакет pypdf. "
            "Встановіть залежності командою: py -3 -m pip install -r requirements.txt"
        ) from error

    try:
        reader = PdfReader(str(path))
        if reader.is_encrypted and not reader.decrypt(""):
            raise ValueError(
                "PDF захищений паролем. Збережіть незахищену копію та спробуйте ще раз."
            )
        pages = [page.extract_text() or "" for page in reader.pages]
    except ValueError:
        raise
    except Exception as error:
        raise ValueError(f"Не вдалося прочитати PDF-резюме: {path}") from error

    text = "\n\n".join(page.strip() for page in pages if page.strip()).strip()
    if not text:
        raise ValueError(
            "У PDF не знайдено текстового шару. Ймовірно, це скан або зображення; "
            "для такого файла потрібне OCR."
        )
    return _normalize_spaced_pdf_text(text)


def _normalize_spaced_pdf_text(text: str) -> str:
    """Repair PDFs that expose every glyph as a separately spaced token.

    Some layout-oriented PDF generators encode ``Köngen`` as ``K ö n g e n``
    while retaining two or more spaces between real words.  Only segments
    dominated by one-character tokens are compacted, so ordinary extracted
    text is left unchanged.
    """

    normalized_lines: list[str] = []
    for line in text.splitlines():
        segments = re.split(r"\s{2,}", line.strip())
        normalized_segments: list[str] = []
        for segment in segments:
            tokens = segment.split()
            single_character_ratio = (
                sum(len(token) == 1 for token in tokens) / len(tokens)
                if tokens
                else 0.0
            )
            if len(tokens) >= 2 and single_character_ratio >= 0.75:
                segment = "".join(tokens)
            if segment:
                normalized_segments.append(segment)
        normalized_lines.append(" ".join(normalized_segments))
    return "\n".join(normalized_lines)


def _extract_language_mentions(text: str) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    canonical_names = {
        "deutsch": "German",
        "german": "German",
        "englisch": "English",
        "english": "English",
        "ukrainisch": "Ukrainian",
        "ukrainian": "Ukrainian",
    }
    for match in _LANGUAGE_MENTION_PATTERN.finditer(text):
        canonical = canonical_names[match.group("language").casefold()]
        level = match.group("level") or ""
        value = f"{canonical} {level.upper() if len(level) == 2 else level}".strip()
        key = canonical.casefold()
        if key not in seen:
            result.append(value)
            seen.add(key)
    return result


def _infer_name_before_personal_data(text: str) -> str:
    """Conservatively read a name placed directly above a personal-data heading."""

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    marker_index = next(
        (
            index
            for index, line in enumerate(lines[:6])
            if line.casefold()
            in {"persönliche daten", "personal data", "personal details"}
        ),
        None,
    )
    if marker_index is None or not 1 <= marker_index <= 2:
        return ""
    candidates = lines[:marker_index]
    if not all(
        re.fullmatch(r"[A-Za-zÄÖÜäöüß'’-]{2,40}", value)
        for value in candidates
    ):
        return ""
    return " ".join(candidates)


def _extract_phone(text: str) -> str:
    candidates: list[tuple[bool, str]] = []
    for match in _PHONE_PATTERN.finditer(text):
        value = " ".join(match.group(0).split())
        if re.search(r"\b\d{1,2}/\d{4}\b", value):
            continue
        digit_count = sum(character.isdigit() for character in value)
        if 8 <= digit_count <= 15:
            candidates.append((value.startswith("+"), value))
    if not candidates:
        return ""
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def _profile_from_text(text: str) -> ResumeLoadResult:
    scalar: dict[str, str] = {}
    lists: dict[str, list[str]] = {field: [] for field in _LIST_FIELDS}
    experience: float | None = None
    active_field: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            active_field = None
            continue

        label_match = _LABEL_PATTERN.match(line)
        inline_value = ""
        if label_match:
            label = " ".join(label_match.group(1).casefold().split())
            field_name = _LABELS.get(label)
            inline_value = label_match.group(2).strip()
        else:
            field_name = _LABELS.get(" ".join(line.casefold().split()))

        if field_name is not None:
            active_field = field_name
            if not inline_value:
                continue
            value = inline_value
        elif active_field is not None:
            value = line
            field_name = active_field
        else:
            continue

        if field_name in _LIST_FIELDS:
            lists[field_name].extend(_split_values(value))
            if inline_value:
                active_field = None
        elif field_name == "experience":
            match = _YEARS_PATTERN.search(value)
            if match:
                experience = float(match.group("years").replace(",", "."))
        elif field_name == "summary":
            scalar[field_name] = " ".join(
                part for part in (scalar.get(field_name), value) if part
            )
        else:
            scalar.setdefault(field_name, value)

    lists["skills"] = list(
        canonicalize_values(
            (*lists["skills"], *extract_skill_mentions(text)), canonical_skill
        )
    )
    if not lists["languages"]:
        lists["languages"].extend(_extract_language_mentions(text))
    if experience is None:
        match = _UNLABELED_EXPERIENCE_PATTERN.search(text)
        if match:
            experience = float(match.group("years").replace(",", "."))

    if "email" not in scalar:
        email_match = _EMAIL_PATTERN.search(text)
        if email_match:
            scalar["email"] = email_match.group(0)
    if "phone" not in scalar:
        inferred_phone = _extract_phone(text)
        if inferred_phone:
            scalar["phone"] = inferred_phone
    if "full_name" not in scalar:
        inferred_name = _infer_name_before_personal_data(text)
        if inferred_name:
            scalar["full_name"] = inferred_name
    if not lists["preferred_locations"]:
        location_match = _GERMAN_POSTAL_LOCATION_PATTERN.search(text)
        if location_match:
            lists["preferred_locations"].append(location_match.group("city"))

    profile = CandidateProfile(
        full_name=scalar.get("full_name", ""),
        email=scalar.get("email", ""),
        phone=scalar.get("phone", ""),
        summary=scalar.get("summary", ""),
        desired_roles=tuple(lists["desired_roles"]),
        skills=tuple(lists["skills"]),
        languages=tuple(lists["languages"]),
        years_experience=experience,
        preferred_locations=tuple(lists["preferred_locations"]),
    )
    extracted_fields = sum(
        bool(value)
        for value in (
            profile.full_name,
            profile.email,
            profile.phone,
            profile.summary,
            profile.desired_roles,
            profile.skills,
            profile.languages,
            profile.years_experience is not None,
            profile.preferred_locations,
        )
    )
    warnings: list[str] = [
        "Перевірте автоматично витягнуті дані; за потреби їх можна відредагувати."
    ]
    if extracted_fields <= 1:
        warnings.append(
            "Структурованих полів майже не знайдено, тому оцінювання може бути "
            "менш точним. Ручне заповнення полів залишається необов’язковим."
        )
    return ResumeLoadResult(profile=profile, raw_text=text, warnings=tuple(warnings))


def load_resume(path: str | Path) -> ResumeLoadResult:
    """Load JSON, TXT, DOCX, or text-based PDF entirely locally."""

    resume_path = Path(path)
    suffix = resume_path.suffix.casefold()
    if suffix == ".json":
        try:
            with resume_path.open("r", encoding="utf-8") as stream:
                payload: Any = json.load(stream)
        except json.JSONDecodeError as error:
            raise ValueError(f"Resume JSON is invalid: {resume_path}") from error
        if not isinstance(payload, dict):
            raise ValueError("Resume JSON must be an object")
        return ResumeLoadResult(
            profile=CandidateProfile.from_dict(payload),
            raw_text=json.dumps(payload, ensure_ascii=False, indent=2),
        )
    if suffix == ".txt":
        text = resume_path.read_text(encoding="utf-8-sig")
        return _profile_from_text(text)
    if suffix == ".docx":
        return _profile_from_text(_docx_text(resume_path))
    if suffix == ".pdf":
        return _profile_from_text(_pdf_text(resume_path))
    raise ValueError("Supported resume formats: JSON, TXT, DOCX, PDF")
