"""Automatic, policy-aware discovery of public company vacancy sources."""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from time import monotonic
from typing import Protocol
from urllib.parse import parse_qs, urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree

from app.core.models import JobPosting
from app.core.source_registry import AtsType, SourceRegistryEntry
from app.sources.base import SearchQuery
from app.sources.http import JsonHttpClient, SourceError
from app.sources.jsonld import extract_job_postings


_CAREER_MARKERS = (
    "career",
    "careers",
    "karriere",
    "jobs",
    "stellen",
    "stellenangebote",
    "vacancies",
    "vacancy",
    "positions",
)
_ACTION_MARKERS = (
    "apply",
    "bewerben",
    "bewerbung",
    "karriere",
    "career",
    "jobs",
    "stellen",
    "company website",
    "unternehmenswebsite",
)
_NON_EMPLOYER_HOSTS = (
    "arbeitsagentur.de",
    "arbeitnow.com",
    "remotive.com",
    "indeed.com",
    "linkedin.com",
    "stepstone.de",
    "xing.com",
)


@dataclass(frozen=True, slots=True)
class WebDiscoveryResult:
    url: str
    company: str = ""


class WebDiscoveryProvider(Protocol):
    """Optional legal web-search channel; no provider is required by the UI."""

    name: str

    def discover(self, query: SearchQuery) -> list[WebDiscoveryResult]: ...


@dataclass(frozen=True, slots=True)
class DiscoveryReport:
    entries: tuple[SourceRegistryEntry, ...] = ()
    pages_checked: int = 0
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _Link:
    url: str
    text: str


class _LinkParser(HTMLParser):
    def __init__(self, page_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self._href = ""
        self._parts: list[str] = []
        self.links: list[_Link] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag.casefold() != "a":
            return
        values = {key.casefold(): value or "" for key, value in attrs}
        self._href = values.get("href", "")
        self._parts = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() == "a" and self._href:
            self.links.append(
                _Link(
                    url=urljoin(self.page_url, self._href),
                    text=" ".join("".join(self._parts).split()),
                )
            )
            self._href = ""
            self._parts = []


def _host_is(host: str, suffix: str) -> bool:
    return host == suffix or host.endswith(f".{suffix}")


def _is_non_employer_host(host: str) -> bool:
    return any(_host_is(host, suffix) for suffix in _NON_EMPLOYER_HOSTS)


def _root_url(value: str) -> str:
    parts = urlsplit(value)
    return urlunsplit((parts.scheme, parts.netloc, "/", "", ""))


def _career_parent(value: str) -> str:
    parts = urlsplit(value)
    segments = [segment for segment in parts.path.split("/") if segment]
    marker_index = next(
        (
            index
            for index, segment in enumerate(segments)
            if any(marker in segment.casefold() for marker in _CAREER_MARKERS)
        ),
        None,
    )
    if marker_index is None:
        return value
    kept = segments[: marker_index + 1]
    return urlunsplit((parts.scheme, parts.netloc, "/" + "/".join(kept), "", ""))


def detect_source_url(
    url: str,
    *,
    company: str = "",
    country: str = "",
    region: str = "",
    allow_generic: bool = True,
    discovered_from: str = "automatic",
) -> SourceRegistryEntry | None:
    """Identify an ATS and reduce deep vacancy links to a reusable board URL."""

    parts = urlsplit(url.strip())
    host = (parts.hostname or "").casefold()
    if parts.scheme not in {"http", "https"} or not host:
        return None
    segments = [segment for segment in parts.path.split("/") if segment]
    ats_type: AtsType
    source_url: str
    if host in {"boards.greenhouse.io", "job-boards.greenhouse.io"}:
        board = segments[0] if segments and segments[0] != "embed" else ""
        if not board:
            board = parse_qs(parts.query).get("for", [""])[0]
        if not board:
            return None
        ats_type = AtsType.GREENHOUSE
        source_url = f"https://{host}/{board}"
    elif host in {"jobs.lever.co", "jobs.eu.lever.co"} and segments:
        ats_type = AtsType.LEVER
        source_url = f"https://{host}/{segments[0]}"
    elif host == "jobs.ashbyhq.com" and segments:
        ats_type = AtsType.ASHBY
        source_url = f"https://{host}/{segments[0]}"
    elif host.endswith((".jobs.personio.de", ".jobs.personio.com")):
        ats_type = AtsType.PERSONIO
        source_url = f"https://{host}/"
    elif host.endswith("myworkdayjobs.com"):
        ats_type = AtsType.WORKDAY
        kept = (
            segments[:2]
            if segments and re.fullmatch(r"[a-z]{2}-[A-Z]{2}", segments[0])
            else segments[:1]
        )
        source_url = f"https://{host}/" + "/".join(kept)
    elif allow_generic and not _is_non_employer_host(host) and any(
        marker in parts.path.casefold() for marker in _CAREER_MARKERS
    ):
        ats_type = AtsType.GENERIC_HTML
        source_url = _career_parent(url)
    else:
        return None
    return SourceRegistryEntry(
        company=company,
        career_url=source_url,
        ats_type=ats_type,
        country=country,
        region=region,
        discovered_from=discovered_from,
    )


def extract_sitemap_links(xml: str) -> tuple[str, ...]:
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        return tuple(
            dict.fromkeys(
                match.strip()
                for match in re.findall(r"<loc[^>]*>(.*?)</loc>", xml, re.I | re.S)
                if match.strip()
            )
        )
    result: list[str] = []
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1].casefold() == "loc" and element.text:
            result.append(element.text.strip())
    return tuple(dict.fromkeys(item for item in result if item))


class AutomaticSourceDiscoverer:
    """Learn reusable career sources from jobs, outbound links, and sitemaps."""

    def __init__(
        self,
        client: JsonHttpClient | None = None,
        *,
        web_providers: tuple[WebDiscoveryProvider, ...] = (),
        max_job_pages: int = 10,
        max_site_probes: int = 24,
        max_elapsed_seconds: float = 30.0,
    ) -> None:
        self.client = client or JsonHttpClient(timeout=12.0)
        self.web_providers = web_providers
        self.max_job_pages = max(0, max_job_pages)
        self.max_site_probes = max(1, max_site_probes)
        self.max_elapsed_seconds = max(1.0, max_elapsed_seconds)
        self._robots: dict[str, RobotFileParser | None] = {}
        self._checked_urls: set[str] = set()
        self._deadline = 0.0

    def discover(
        self,
        jobs: list[JobPosting],
        query: SearchQuery,
        *,
        known_urls: tuple[str, ...] = (),
    ) -> DiscoveryReport:
        self._checked_urls = set()
        self._deadline = monotonic() + self.max_elapsed_seconds
        entries: dict[str, SourceRegistryEntry] = {}
        warnings: list[str] = []
        known = {url.rstrip("/").casefold() for url in known_urls}

        for job in jobs:
            country, region = _job_geo(job)
            direct = detect_source_url(
                job.url,
                company=job.company,
                country=country,
                region=region,
            )
            if direct is not None:
                entries[direct.source_id] = direct

        page_jobs = [
            job
            for job in jobs
            if job.url and detect_source_url(job.url, allow_generic=False) is None
        ][: self.max_job_pages]
        for job in page_jobs:
            if self._expired:
                warnings.append("Automatic source discovery reached its time limit")
                break
            try:
                for entry in self._discover_from_job_page(job):
                    entries[entry.source_id] = entry
            except Exception as error:
                warnings.append(f"{job.url}: {error}")

        for provider in self.web_providers:
            if self._expired:
                warnings.append("Automatic source discovery reached its time limit")
                break
            try:
                found = provider.discover(query)
            except Exception as error:
                warnings.append(f"{provider.name}: {error}")
                continue
            for item in found:
                entry = detect_source_url(
                    item.url,
                    company=item.company,
                    discovered_from=f"web:{provider.name}",
                )
                if entry is not None:
                    entries[entry.source_id] = entry
                    continue
                for probed in self._probe_employer_site(item.url, item.company):
                    entries[probed.source_id] = probed

        fresh = tuple(
            entry
            for entry in entries.values()
            if entry.career_url.rstrip("/").casefold() not in known
        )
        return DiscoveryReport(
            entries=fresh,
            pages_checked=len(self._checked_urls),
            warnings=tuple(warnings),
        )

    def _discover_from_job_page(
        self, job: JobPosting
    ) -> list[SourceRegistryEntry]:
        parsed = urlsplit(job.url)
        host = (parsed.hostname or "").casefold()
        if not host or not self._allows(job.url):
            return []
        html = self._get_text(job.url)
        entries: dict[str, SourceRegistryEntry] = {}
        country, region = _job_geo(job)
        if not _is_non_employer_host(host) and extract_job_postings(
            html,
            job.url,
            source="discovery",
            company_hint=job.company,
        ):
            entry = SourceRegistryEntry(
                company=job.company,
                career_url=_career_parent(job.url),
                ats_type=AtsType.JSON_LD,
                country=country,
                region=region,
                discovered_from=job.source,
            )
            entries[entry.source_id] = entry

        parser = _LinkParser(job.url)
        parser.feed(html)
        employer_roots: dict[str, str] = {}
        for link in parser.links:
            detected = detect_source_url(
                link.url,
                company=job.company,
                country=country,
                region=region,
                discovered_from=job.source,
            )
            if detected is not None:
                entries[detected.source_id] = detected
                continue
            link_host = (urlsplit(link.url).hostname or "").casefold()
            if (
                link_host
                and link_host != host
                and not _is_non_employer_host(link_host)
                and any(marker in link.text.casefold() for marker in _ACTION_MARKERS)
            ):
                employer_roots[link_host] = _root_url(link.url)

        for root in tuple(employer_roots.values())[:3]:
            for entry in self._probe_employer_site(root, job.company):
                entries[entry.source_id] = entry
        if not _is_non_employer_host(host):
            for entry in self._probe_employer_site(_root_url(job.url), job.company):
                entries[entry.source_id] = entry
        return list(entries.values())

    def _probe_employer_site(
        self, url: str, company: str
    ) -> list[SourceRegistryEntry]:
        direct = detect_source_url(url, company=company)
        if direct is not None:
            return [direct]
        root = _root_url(url)
        candidates = (
            url,
            urljoin(root, "/karriere"),
            urljoin(root, "/jobs"),
            urljoin(root, "/careers"),
        )
        entries: dict[str, SourceRegistryEntry] = {}
        for candidate in dict.fromkeys(candidates):
            if self._expired:
                break
            if (
                len(self._checked_urls) >= self.max_site_probes
                or not self._allows(candidate)
            ):
                continue
            try:
                html = self._get_text(candidate)
            except SourceError:
                continue
            if extract_job_postings(
                html,
                candidate,
                source="discovery",
                company_hint=company,
            ):
                entry = SourceRegistryEntry(
                    company=company,
                    career_url=_career_parent(candidate),
                    ats_type=AtsType.JSON_LD,
                )
                entries[entry.source_id] = entry
            parser = _LinkParser(candidate)
            parser.feed(html)
            for link in parser.links:
                detected = detect_source_url(link.url, company=company)
                if detected is not None:
                    entries[detected.source_id] = detected

        for sitemap_url in self._sitemaps(root):
            if self._expired:
                break
            if (
                len(self._checked_urls) >= self.max_site_probes
                or not self._allows(sitemap_url)
            ):
                continue
            try:
                xml = self._get_text(sitemap_url)
            except SourceError:
                continue
            links = extract_sitemap_links(xml)
            if any(
                any(marker in urlsplit(link).path.casefold() for marker in _CAREER_MARKERS)
                for link in links[:500]
            ):
                entry = SourceRegistryEntry(
                    company=company,
                    career_url=sitemap_url,
                    ats_type=AtsType.GENERIC_HTML,
                )
                entries[entry.source_id] = entry
        return list(entries.values())

    def _sitemaps(self, root_url: str) -> tuple[str, ...]:
        parsed = urlsplit(root_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        values = [urljoin(root_url, "/sitemap.xml")]
        try:
            robots = self._get_text(robots_url)
        except SourceError:
            return tuple(values)
        for line in robots.splitlines():
            if line.casefold().startswith("sitemap:"):
                value = line.split(":", 1)[1].strip()
                if value:
                    values.append(value)
        return tuple(dict.fromkeys(values))

    def _get_text(self, url: str) -> str:
        if self._expired:
            raise SourceError("Automatic source discovery reached its time limit")
        self._checked_urls.add(url)
        return self.client.get_text(url)

    def _allows(self, url: str) -> bool:
        if self._expired:
            return False
        parsed = urlsplit(url)
        host = (parsed.hostname or "").casefold()
        if not host or _is_non_employer_host(host) and host not in {
            "www.arbeitsagentur.de",
            "www.arbeitnow.com",
            "remotive.com",
        }:
            return False
        key = parsed.netloc.casefold()
        if key not in self._robots:
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            try:
                content = self.client.get_text(robots_url)
            except SourceError:
                self._robots[key] = None
            else:
                parser = RobotFileParser(robots_url)
                parser.parse(content.splitlines())
                self._robots[key] = parser
        parser = self._robots[key]
        return parser is None or parser.can_fetch(self.client.user_agent, url)

    @property
    def _expired(self) -> bool:
        return self._deadline > 0 and monotonic() >= self._deadline


def _job_geo(job: JobPosting) -> tuple[str, str]:
    """Preserve useful coarse geography without pretending to geocode a job."""

    location = job.location.strip()
    folded = location.casefold()
    country = (
        "DE"
        if job.source == "Bundesagentur für Arbeit"
        or any(value in folded for value in ("deutschland", "germany"))
        else ""
    )
    parts = [part.strip() for part in location.split(",") if part.strip()]
    named_country = bool(
        parts and parts[-1].casefold() in {"deutschland", "germany"}
    )
    region = (
        parts[-2]
        if country and named_country and len(parts) >= 2
        else parts[-1]
        if country and len(parts) >= 2
        else ""
    )
    return country, region
