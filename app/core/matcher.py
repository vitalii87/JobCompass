"""Deterministic and explainable matching of candidates to jobs."""

from __future__ import annotations

import re
from collections.abc import Iterable
from collections.abc import Callable

from app.core.models import CandidateProfile, JobPosting, MatchLevel, MatchResult
from app.core.taxonomy import (
    canonical_language,
    canonical_role,
    canonical_skill,
    normalize_term,
)


_TOKEN_PATTERN = re.compile(r"[^\W_]+(?:[+#.-][^\W_]+)*", re.UNICODE)


def _key(value: str) -> str:
    return " ".join(value.casefold().split())


def _tokens(value: str) -> set[str]:
    return {_key(token) for token in _TOKEN_PATTERN.findall(value)}


def _matching_values(
    candidate_values: Iterable[str],
    required_values: Iterable[str],
    normalizer: Callable[[str], str] = lambda value: value,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    candidate_keys = {normalize_term(normalizer(value)) for value in candidate_values}
    matched: list[str] = []
    missing: list[str] = []
    for value in required_values:
        key = normalize_term(normalizer(value))
        (matched if key in candidate_keys else missing).append(value)
    return tuple(matched), tuple(missing)


def _role_score(desired_roles: tuple[str, ...], title: str) -> tuple[float, tuple[str, ...]]:
    if not desired_roles:
        return 0.0, ()

    normalized_title = _key(title)
    title_tokens = _tokens(title)
    canonical_title = canonical_role(title)
    scored_roles: list[tuple[float, str]] = []
    for role in desired_roles:
        normalized_role = _key(role)
        role_tokens = _tokens(role)
        if normalize_term(canonical_role(role)) == normalize_term(canonical_title):
            score = 1.0
        elif normalized_role and normalized_role in normalized_title:
            score = 1.0
        elif role_tokens:
            score = len(role_tokens & title_tokens) / len(role_tokens)
        else:
            score = 0.0
        scored_roles.append((score, role))

    best_score = max(score for score, _ in scored_roles)
    matches = tuple(role for score, role in scored_roles if score >= 0.5)
    return best_score, matches


def _location_score(profile: CandidateProfile, job: JobPosting) -> float | None:
    if profile.remote_only:
        return 1.0 if job.is_remote else 0.0
    if not profile.preferred_locations:
        return None
    if job.is_remote:
        return 1.0

    location = _key(job.location)
    if not location:
        return 0.0
    return float(
        any(
            _key(preferred) in location or location in _key(preferred)
            for preferred in profile.preferred_locations
        )
    )


class JobMatcher:
    """Calculate an evidence-based score without inferred candidate skills."""

    _WEIGHTS = {
        "skills": 50,
        "role": 25,
        "experience": 10,
        "languages": 10,
        "location": 5,
    }

    def match(self, profile: CandidateProfile, job: JobPosting) -> MatchResult:
        raw_components: dict[str, float] = {}
        risks: list[str] = []
        has_critical_gap = False

        required_matches, missing_required = _matching_values(
            profile.skills, job.required_skills, canonical_skill
        )
        preferred_matches, _ = _matching_values(
            profile.skills, job.preferred_skills, canonical_skill
        )
        matched_skills = required_matches + preferred_matches

        if job.required_skills or job.preferred_skills:
            required_coverage = (
                len(required_matches) / len(job.required_skills)
                if job.required_skills
                else None
            )
            preferred_coverage = (
                len(preferred_matches) / len(job.preferred_skills)
                if job.preferred_skills
                else None
            )
            if required_coverage is not None and preferred_coverage is not None:
                raw_components["skills"] = (
                    required_coverage * 0.75 + preferred_coverage * 0.25
                )
            else:
                raw_components["skills"] = (
                    required_coverage
                    if required_coverage is not None
                    else preferred_coverage or 0.0
                )
        if missing_required:
            has_critical_gap = True
            risks.append(
                "Missing required skills: " + ", ".join(missing_required)
            )

        role_score, matched_roles = _role_score(profile.desired_roles, job.title)
        if profile.desired_roles:
            raw_components["role"] = role_score
            if role_score < 0.5:
                risks.append("Job title does not closely match the desired roles")

        if job.minimum_years_experience is not None:
            if profile.years_experience is None:
                has_critical_gap = True
                raw_components["experience"] = 0.0
                risks.append("Candidate experience is not specified")
            elif job.minimum_years_experience == 0:
                raw_components["experience"] = 1.0
            else:
                raw_components["experience"] = min(
                    profile.years_experience / job.minimum_years_experience, 1.0
                )
                if profile.years_experience < job.minimum_years_experience:
                    has_critical_gap = True
                    risks.append(
                        "Experience is below the stated minimum "
                        f"({profile.years_experience:g} of "
                        f"{job.minimum_years_experience:g} years)"
                    )

        if job.required_languages:
            language_matches, missing_languages = _matching_values(
                profile.languages, job.required_languages, canonical_language
            )
            raw_components["languages"] = (
                len(language_matches) / len(job.required_languages)
            )
            if missing_languages:
                has_critical_gap = True
                risks.append(
                    "Missing required languages: " + ", ".join(missing_languages)
                )

        location_score = _location_score(profile, job)
        if location_score is not None:
            raw_components["location"] = location_score
            if location_score == 0:
                has_critical_gap = True
                if profile.remote_only:
                    risks.append("The vacancy is not confirmed as remote")
                else:
                    risks.append("Location does not match the candidate preferences")

        active_weight = sum(self._WEIGHTS[name] for name in raw_components)
        if active_weight:
            weighted_score = sum(
                score * self._WEIGHTS[name]
                for name, score in raw_components.items()
            ) / active_weight
            score = round(weighted_score * 100)
        else:
            score = 0
            risks.append("Not enough structured data to calculate a match")

        if score >= 75 and not has_critical_gap:
            level = MatchLevel.FULL
        elif score >= 45:
            level = MatchLevel.PARTIAL
        else:
            level = MatchLevel.WEAK

        return MatchResult(
            job_id=job.job_id,
            score=score,
            level=level,
            component_scores={
                name: round(component * 100)
                for name, component in raw_components.items()
            },
            matched_skills=matched_skills,
            missing_required_skills=missing_required,
            matched_roles=matched_roles,
            risks=tuple(risks),
        )
