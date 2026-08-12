"""Transparent offline query expansion for German and English job titles."""

from __future__ import annotations

from app.core.taxonomy import normalize_term, role_query_variants


def generate_role_queries(
    roles: tuple[str, ...],
    *,
    max_variants_per_role: int = 6,
    max_total: int = 12,
) -> tuple[str, ...]:
    """Expand roles without an external AI call or invented candidate facts."""
    result: list[str] = []
    seen: set[str] = set()

    # Expansion is supplemental: every explicit OR choice must be retained even
    # when earlier roles have many aliases.
    for role in roles:
        normalized = normalize_term(role)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(role.strip())

    limit = max(max(1, max_total), len(result))
    for role in roles:
        for variant in role_query_variants(role)[1 : max(1, max_variants_per_role)]:
            normalized = normalize_term(variant)
            if normalized and normalized not in seen:
                seen.add(normalized)
                result.append(variant)
                if len(result) >= limit:
                    return tuple(result)
    return tuple(result)
