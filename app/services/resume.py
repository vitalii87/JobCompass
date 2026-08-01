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


_EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_YEARS_PATTERN = re.compile(
    r"(?P<years>\d+(?:[.,]\d+)?)\s*(?:years?|yrs?|рок(?:и|ів)?|р\.)\b",
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
    "про себе": "summary",
    "профіль": "summary",
    "desired role": "desired_roles",
    "desired roles": "desired_roles",
    "position": "desired_roles",
    "бажана посада": "desired_roles",
    "посада": "desired_roles",
    "skills": "skills",
    "technical skills": "skills",
    "навички": "skills",
    "технічні навички": "skills",
    "languages": "languages",
    "мови": "languages",
    "location": "preferred_locations",
    "preferred location": "preferred_locations",
    "локація": "preferred_locations",
    "бажана локація": "preferred_locations",
    "experience": "experience",
    "years of experience": "experience",
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

    if "email" not in scalar:
        email_match = _EMAIL_PATTERN.search(text)
        if email_match:
            scalar["email"] = email_match.group(0)

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
        "Перевірте всі витягнуті дані перед збереженням профілю."
    ]
    if extracted_fields <= 1:
        warnings.append(
            "Структурованих полів майже не знайдено; заповніть профіль вручну."
        )
    return ResumeLoadResult(profile=profile, raw_text=text, warnings=tuple(warnings))


def load_resume(path: str | Path) -> ResumeLoadResult:
    """Load JSON, TXT, or DOCX without sending resume data anywhere."""

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
        raise ValueError(
            "PDF parsing is not available yet. Use JSON, TXT, or DOCX for now."
        )
    raise ValueError("Supported resume formats: JSON, TXT, DOCX")
