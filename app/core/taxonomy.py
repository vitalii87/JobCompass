"""Small bilingual taxonomy for deterministic DE/EN normalization."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Iterable


def normalize_term(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).casefold()
    text = text.replace("c++", " cpp ").replace("c#", " csharp ")
    text = text.replace(".net", " dotnet ")
    text = (
        text.replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )
    return " ".join(re.sub(r"[^\w]+", " ", text, flags=re.UNICODE).split())


_SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "Python": ("python", "python-entwicklung", "python entwicklung"),
    "SQL": ("sql", "sql-kenntnisse", "datenbankabfragen"),
    "Git": ("git", "git-kenntnisse", "versionsverwaltung mit git"),
    "Docker": ("docker", "docker-container"),
    "Kubernetes": ("kubernetes", "k8s"),
    "PostgreSQL": ("postgresql", "postgres"),
    "MySQL": ("mysql",),
    "Java": ("java", "java-entwicklung"),
    "Spring Boot": ("spring boot", "spring-boot"),
    "FastAPI": ("fastapi",),
    "Django": ("django",),
    "Flask": ("flask",),
    "REST API": ("rest api", "rest-api", "restful api", "rest-schnittstellen"),
    "AWS": ("aws", "amazon web services"),
    "Azure": ("azure", "microsoft azure"),
    "Google Cloud": ("google cloud", "gcp"),
    "Linux": ("linux",),
    "CI/CD": ("ci/cd", "ci-cd", "continuous integration", "continuous delivery"),
    "Terraform": ("terraform",),
    "Ansible": ("ansible",),
    "JavaScript": ("javascript",),
    "TypeScript": ("typescript",),
    "React": ("react", "reactjs", "react.js"),
    "Angular": ("angular",),
    "Vue.js": ("vue", "vuejs", "vue.js"),
    "C#": ("c#", "c sharp", "csharp"),
    ".NET": (".net", "dotnet", "asp.net"),
    "C++": ("c++", "cpp"),
    "SAP": ("sap",),
    "Microsoft Office": (
        "microsoft office",
        "ms office",
        "office 365",
        "microsoft 365",
        "ms-office-kenntnisse",
    ),
    "Microsoft Excel": ("microsoft excel", "ms excel", "excel"),
    "Microsoft Word": ("microsoft word", "ms word"),
    "Microsoft PowerPoint": ("microsoft powerpoint", "powerpoint"),
    "Microsoft Outlook": ("microsoft outlook", "outlook"),
    "CRM": ("crm", "customer relationship management", "kundenmanagementsystem"),
    "Project Coordination": (
        "project coordination",
        "projektkoordination",
        "projektorganisation",
        "projektunterstuetzung",
        "projektunterstützung",
    ),
    "Office Administration": (
        "office administration",
        "bueroorganisation",
        "büroorganisation",
        "office-organisation",
        "allgemeine verwaltung",
    ),
    "Calendar Management": (
        "calendar management",
        "terminkoordination",
        "terminmanagement",
    ),
    "Business Correspondence": (
        "business correspondence",
        "geschaeftskorrespondenz",
        "geschäftskorrespondenz",
        "korrespondenz",
    ),
    "Invoice Processing": (
        "invoice processing",
        "rechnungspruefung",
        "rechnungsprüfung",
        "rechnungsbearbeitung",
    ),
    "Jenkins": ("jenkins",),
    "GitLab CI": ("gitlab ci", "gitlab-ci"),
    "Bash": ("bash", "shell scripting", "shell-skripting"),
    "PowerShell": ("powershell",),
    "Agile": ("agile", "agile softwareentwicklung"),
    "Scrum": ("scrum",),
}

_ROLE_ALIASES: dict[str, tuple[str, ...]] = {
    "Python Developer": (
        "python developer",
        "python entwickler",
        "python-entwickler",
        "python softwareentwickler",
    ),
    "Backend Developer": (
        "backend developer",
        "backend engineer",
        "backend entwickler",
        "backend-entwickler",
        "backend softwareentwickler",
    ),
    "Software Developer": (
        "software developer",
        "software engineer",
        "softwareentwickler",
        "software-entwickler",
        "anwendungsentwickler",
    ),
    "Full Stack Developer": (
        "full stack developer",
        "full-stack developer",
        "fullstack entwickler",
        "full-stack-entwickler",
    ),
    "Frontend Developer": (
        "frontend developer",
        "front-end developer",
        "frontend entwickler",
        "frontend-entwickler",
    ),
    "DevOps Engineer": (
        "devops engineer",
        "devops entwickler",
        "devops-engineer",
    ),
    "Data Engineer": ("data engineer", "dateningenieur", "daten engineer"),
    "Data Scientist": ("data scientist", "datenwissenschaftler"),
    "QA Engineer": (
        "qa engineer",
        "qa automation",
        "test engineer",
        "test automation engineer",
        "software test engineer",
        "sdet",
        "python qa",
        "softwaretester",
        "testingenieur",
        "testautomatisierer",
        "automatisierungstester",
    ),
    "System Administrator": (
        "system administrator",
        "systemadministrator",
        "system admin",
    ),
    "Commercial Assistant": (
        "commercial assistant",
        "kaufmaennische assistenz",
        "kaufmännische assistenz",
        "kfm assistenz",
        "kfm. assistenz",
        "kfmännische assistenz",
        "kfm. kaufmännische assistenz",
        "kaufmaennischer assistent",
        "kaufmännischer assistent",
    ),
    "Office Manager": (
        "office manager",
        "office-manager",
        "office management",
        "buero manager",
        "büro manager",
    ),
    "Administrative Specialist": (
        "administrative specialist",
        "sachbearbeiter verwaltung",
        "sachbearbeiterin verwaltung",
        "sachbearbeiter in verwaltung",
        "verwaltungssachbearbeiter",
        "kaufmaennischer sachbearbeiter",
        "kaufmännischer sachbearbeiter",
        "kaufmaennische sachbearbeitung",
        "kaufmännische sachbearbeitung",
        "sachbearbeitung verwaltung",
    ),
    "Project Coordinator": (
        "project coordinator",
        "projektkoordinator",
        "projektkoordinatorin",
        "projektkoordination",
        "projektassistenz",
    ),
    "PMO Assistant": (
        "pmo assistant",
        "pmo assistenz",
        "project management office assistant",
    ),
    "Management Assistant": (
        "management assistant",
        "management assistenz",
        "managementassistenz",
        "assistenz management",
    ),
    "Executive Assistant": (
        "executive assistant",
        "assistenz der geschaeftsfuehrung",
        "assistenz der geschäftsführung",
        "geschaeftsfuehrungsassistenz",
        "geschäftsführungsassistenz",
    ),
    "Team Assistant": (
        "team assistant",
        "team assistenz",
        "teamassistenz",
    ),
}


def role_query_variants(value: str) -> tuple[str, ...]:
    """Return deterministic DE/EN search variants for one requested role."""
    key = normalize_term(value)
    for canonical, aliases in _ROLE_ALIASES.items():
        normalized = {normalize_term(canonical), *(normalize_term(item) for item in aliases)}
        if key in normalized:
            return tuple(dict.fromkeys((value.strip(), canonical, *aliases)))
    return (value.strip(),) if value.strip() else ()

_LANGUAGE_ALIASES: dict[str, tuple[str, ...]] = {
    "German": ("german", "deutsch", "deutsche sprache", "deutschkenntnisse"),
    "English": ("english", "englisch", "englischkenntnisse"),
    "Ukrainian": ("ukrainian", "ukrainisch", "ukrainischkenntnisse"),
}


def _alias_index(groups: dict[str, tuple[str, ...]]) -> dict[str, str]:
    return {
        normalize_term(alias): canonical
        for canonical, aliases in groups.items()
        for alias in aliases
    }


_SKILL_INDEX = _alias_index(_SKILL_ALIASES)
_ROLE_INDEX = _alias_index(_ROLE_ALIASES)
_LANGUAGE_INDEX = _alias_index(_LANGUAGE_ALIASES)


def _canonical_exact_or_contained(value: str, index: dict[str, str]) -> str | None:
    normalized = normalize_term(value)
    if normalized in index:
        return index[normalized]
    for alias in sorted(index, key=len, reverse=True):
        if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", normalized):
            return index[alias]
    return None


def canonical_skill(value: str) -> str:
    return _canonical_exact_or_contained(value, _SKILL_INDEX) or value.strip()


def canonical_role(value: str) -> str:
    return _canonical_exact_or_contained(value, _ROLE_INDEX) or value.strip()


def canonical_language(value: str) -> str:
    return _canonical_exact_or_contained(value, _LANGUAGE_INDEX) or value.strip()


def extract_skill_mentions(text: str) -> tuple[str, ...]:
    normalized = normalize_term(text)
    found: list[str] = []
    for alias in sorted(_SKILL_INDEX, key=len, reverse=True):
        canonical = _SKILL_INDEX[alias]
        if canonical in found:
            continue
        if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", normalized):
            found.append(canonical)
    return tuple(found)


def canonicalize_values(
    values: Iterable[str], normalizer: Callable[[str], str]
) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        canonical = normalizer(value)
        key = normalize_term(canonical)
        if key and key not in seen:
            result.append(canonical)
            seen.add(key)
    return tuple(result)


def text_matches_keyword(text: str, keyword: str) -> bool:
    normalized_text = normalize_term(text)
    normalized_keyword = normalize_term(keyword)
    if normalized_keyword and normalized_keyword in normalized_text:
        return True
    skill = canonical_skill(keyword)
    if skill in extract_skill_mentions(text):
        return True
    role = canonical_role(keyword)
    return normalize_term(canonical_role(text)) == normalize_term(role)
