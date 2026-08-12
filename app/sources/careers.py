"""Public ATS and schema.org career-page connectors."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree

from app.core.models import JobPosting, WorkMode
from app.parsing import enrich_job_posting
from app.sources.base import JobSource, SearchQuery, SourceAccess, SourceCapabilities
from app.sources.filtering import matches_query
from app.sources.http import JsonHttpClient, SourceError
from app.sources.jsonld import (
    company_hint_from_url,
    extract_job_postings,
    extract_page_links,
)
from app.sources.utils import html_to_text, parse_published_at, text_value


ATS_CAPABILITIES = SourceCapabilities(
    access=SourceAccess.OFFICIAL_API,
    supports_locations=True,
    supports_remote=True,
    provides_full_description=True,
    provides_published_at=True,
)

PUBLIC_FEED_CAPABILITIES = SourceCapabilities(
    access=SourceAccess.PUBLIC_FEED,
    supports_locations=True,
    supports_remote=True,
    provides_full_description=True,
    provides_published_at=True,
)

CAREER_PAGE_CAPABILITIES = SourceCapabilities(
    access=SourceAccess.PUBLIC_CAREER_PAGE,
    supports_locations=True,
    supports_remote=True,
    provides_full_description=True,
    provides_published_at=True,
)


def _payload(client: object, url: str, params: dict[str, object] | None = None) -> object:
    method = getattr(client, "get_json_value", None)
    if callable(method):
        return method(url, params)
    return client.get_json(url, params)  # type: ignore[attr-defined]


class GreenhouseCareerSource:
    name = "Greenhouse careers"
    capabilities = ATS_CAPABILITIES

    def __init__(self, boards: tuple[str, ...], client: JsonHttpClient | None = None) -> None:
        self.boards = tuple(dict.fromkeys(boards))
        self.client = client or JsonHttpClient()
        self.last_partial_error = ""
        self.last_target_status: dict[str, str] = {}

    def search(self, query: SearchQuery) -> list[JobPosting]:
        jobs: list[JobPosting] = []
        errors: list[str] = []
        self.last_target_status = {}
        for board in self.boards:
            if query.expired:
                break
            try:
                payload = self.client.get_json(
                    f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs",
                    {"content": "true"},
                )
                rows = payload.get("jobs")
                if not isinstance(rows, list):
                    raise SourceError("Greenhouse не повернув список вакансій")
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    job = self._normalize(board, row)
                    if job is not None and matches_query(job, query):
                        jobs.append(job)
                self.last_target_status[board] = ""
            except Exception as error:
                self.last_target_status[board] = str(error)
                errors.append(f"{board}: {error}")
        self.last_partial_error = "; ".join(errors)
        if errors and not jobs:
            raise SourceError(self.last_partial_error)
        return jobs

    @classmethod
    def _normalize(cls, board: str, row: dict[str, object]) -> JobPosting | None:
        identifier = str(row.get("id") or "").strip()
        title = text_value(row.get("title"))
        if not identifier or not title:
            return None
        location = row.get("location")
        location_name = text_value(location.get("name")) if isinstance(location, dict) else ""
        return enrich_job_posting(
            JobPosting(
                source=cls.name,
                external_id=f"{board}:{identifier}",
                title=title,
                company=board.replace("-", " ").title(),
                location=location_name,
                url=text_value(row.get("absolute_url")),
                description=html_to_text(row.get("content")),
                published_at=parse_published_at(
                    row.get("first_published") or row.get("updated_at")
                ),
            )
        )


class LeverCareerSource:
    name = "Lever careers"
    capabilities = ATS_CAPABILITIES

    def __init__(
        self,
        sites: tuple[tuple[str, bool], ...],
        client: JsonHttpClient | None = None,
    ) -> None:
        self.sites = tuple(dict.fromkeys(sites))
        self.client = client or JsonHttpClient()
        self.last_partial_error = ""
        self.last_target_status: dict[str, str] = {}

    def search(self, query: SearchQuery) -> list[JobPosting]:
        jobs: list[JobPosting] = []
        errors: list[str] = []
        self.last_target_status = {}
        for site, eu in self.sites:
            if query.expired:
                break
            host = "api.eu.lever.co" if eu else "api.lever.co"
            try:
                rows = _payload(
                    self.client,
                    f"https://{host}/v0/postings/{site}",
                    {"mode": "json"},
                )
                if not isinstance(rows, list):
                    raise SourceError("Lever не повернув список вакансій")
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    job = self._normalize(site, row)
                    if job is not None and matches_query(job, query):
                        jobs.append(job)
                self.last_target_status[
                    f"{'api.eu.lever.co' if eu else 'api.lever.co'}:{site}"
                ] = ""
            except Exception as error:
                self.last_target_status[
                    f"{'api.eu.lever.co' if eu else 'api.lever.co'}:{site}"
                ] = str(error)
                errors.append(f"{site}: {error}")
        self.last_partial_error = "; ".join(errors)
        if errors and not jobs:
            raise SourceError(self.last_partial_error)
        return jobs

    @classmethod
    def _normalize(cls, site: str, row: dict[str, object]) -> JobPosting | None:
        identifier = str(row.get("id") or "").strip()
        title = text_value(row.get("text"))
        if not identifier or not title:
            return None
        categories = row.get("categories")
        category = categories if isinstance(categories, dict) else {}
        workplace = text_value(row.get("workplaceType")).casefold()
        remote = workplace == "remote"
        work_mode = {
            "remote": WorkMode.REMOTE,
            "hybrid": WorkMode.HYBRID,
            "on-site": WorkMode.OFFICE,
            "onsite": WorkMode.OFFICE,
        }.get(workplace, WorkMode.UNKNOWN)
        description_parts = [text_value(row.get("descriptionPlain"))]
        lists = row.get("lists")
        if isinstance(lists, list):
            for item in lists:
                if isinstance(item, dict):
                    description_parts.extend(
                        (text_value(item.get("text")), html_to_text(item.get("content")))
                    )
        return enrich_job_posting(
            JobPosting(
                source=cls.name,
                external_id=f"{site}:{identifier}",
                title=title,
                company=site.replace("-", " ").title(),
                location=text_value(category.get("location")) or ("Remote" if remote else ""),
                url=text_value(row.get("hostedUrl")) or text_value(row.get("applyUrl")),
                description="\n".join(part for part in description_parts if part),
                remote=remote,
                work_mode=work_mode,
                employment_type=text_value(category.get("commitment")) or None,
                published_at=parse_published_at(row.get("createdAt")),
            )
        )


class AshbyCareerSource:
    name = "Ashby careers"
    capabilities = ATS_CAPABILITIES

    def __init__(self, boards: tuple[str, ...], client: JsonHttpClient | None = None) -> None:
        self.boards = tuple(dict.fromkeys(boards))
        self.client = client or JsonHttpClient()
        self.last_partial_error = ""
        self.last_target_status: dict[str, str] = {}

    def search(self, query: SearchQuery) -> list[JobPosting]:
        jobs: list[JobPosting] = []
        errors: list[str] = []
        self.last_target_status = {}
        for board in self.boards:
            if query.expired:
                break
            try:
                payload = self.client.get_json(
                    f"https://api.ashbyhq.com/posting-api/job-board/{board}"
                )
                rows = payload.get("jobs")
                if not isinstance(rows, list):
                    raise SourceError("Ashby не повернув список вакансій")
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    job = self._normalize(board, row)
                    if job is not None and matches_query(job, query):
                        jobs.append(job)
                self.last_target_status[board] = ""
            except Exception as error:
                self.last_target_status[board] = str(error)
                errors.append(f"{board}: {error}")
        self.last_partial_error = "; ".join(errors)
        if errors and not jobs:
            raise SourceError(self.last_partial_error)
        return jobs

    @classmethod
    def _normalize(cls, board: str, row: dict[str, object]) -> JobPosting | None:
        title = text_value(row.get("title"))
        job_url = text_value(row.get("jobUrl")) or text_value(row.get("applyUrl"))
        identifier = str(row.get("id") or job_url).strip()
        if not identifier and title:
            identifier = hashlib.sha256(f"{board}\x1f{title}".encode()).hexdigest()[:24]
        if not identifier or not title:
            return None
        workplace = text_value(row.get("workplaceType")).casefold()
        remote = row.get("isRemote") is True or workplace == "remote"
        work_mode = {
            "remote": WorkMode.REMOTE,
            "hybrid": WorkMode.HYBRID,
            "onsite": WorkMode.OFFICE,
            "on-site": WorkMode.OFFICE,
        }.get(workplace, WorkMode.REMOTE if remote else WorkMode.UNKNOWN)
        return enrich_job_posting(
            JobPosting(
                source=cls.name,
                external_id=f"{board}:{identifier}",
                title=title,
                company=board.replace("-", " ").title(),
                location=text_value(row.get("location")) or ("Remote" if remote else ""),
                url=job_url,
                description=html_to_text(row.get("descriptionHtml")) or text_value(row.get("descriptionPlain")),
                remote=remote,
                work_mode=work_mode,
                employment_type=text_value(row.get("employmentType")) or None,
                published_at=parse_published_at(row.get("publishedAt")),
            )
        )


class PersonioCareerSource:
    name = "Personio careers"
    capabilities = PUBLIC_FEED_CAPABILITIES

    def __init__(self, hosts: tuple[str, ...], client: JsonHttpClient | None = None) -> None:
        self.hosts = tuple(dict.fromkeys(hosts))
        self.client = client or JsonHttpClient()
        self.last_partial_error = ""
        self.last_target_status: dict[str, str] = {}

    def search(self, query: SearchQuery) -> list[JobPosting]:
        jobs: list[JobPosting] = []
        errors: list[str] = []
        self.last_target_status = {}
        for host in self.hosts:
            if query.expired:
                break
            try:
                xml = self.client.get_text(
                    f"https://{host}/xml?language=de",
                    {"Accept": "application/xml,text/xml"},
                )
                for row in ElementTree.fromstring(xml).findall(".//position"):
                    job = self._normalize(host, row)
                    if job is not None and matches_query(job, query):
                        jobs.append(job)
                self.last_target_status[host] = ""
            except Exception as error:
                self.last_target_status[host] = str(error)
                errors.append(f"{host}: {error}")
        self.last_partial_error = "; ".join(errors)
        if errors and not jobs:
            raise SourceError(self.last_partial_error)
        return jobs

    @classmethod
    def _normalize(
        cls, host: str, row: ElementTree.Element
    ) -> JobPosting | None:
        identifier = (row.findtext("id") or "").strip()
        title = (row.findtext("name") or "").strip()
        if not identifier or not title:
            return None
        description_parts: list[str] = []
        for block in row.findall("./jobDescriptions/jobDescription"):
            heading = (block.findtext("name") or "").strip()
            content = html_to_text(block.findtext("value"))
            description_parts.append("\n".join(part for part in (heading, content) if part))
        employment = " / ".join(
            part
            for part in (
                (row.findtext("employmentType") or "").strip(),
                (row.findtext("schedule") or "").strip(),
            )
            if part
        )
        account = host.split(".jobs.personio.", 1)[0]
        company = (row.findtext("subcompany") or "").strip() or account.replace("-", " ").title()
        return enrich_job_posting(
            JobPosting(
                source=cls.name,
                external_id=f"{host}:{identifier}",
                title=title,
                company=company,
                location=(row.findtext("office") or "").strip(),
                url=f"https://{host}/job/{identifier}",
                description="\n\n".join(part for part in description_parts if part),
                employment_type=employment or None,
                published_at=parse_published_at(row.findtext("createdAt")),
            )
        )


@dataclass(frozen=True, slots=True)
class _PageTarget:
    root_url: str


class GenericCareerPageSource:
    name = "Company career pages"
    capabilities = CAREER_PAGE_CAPABILITIES
    _blocked_hosts = ("indeed.com", "linkedin.com", "stepstone.de")
    _link_markers = ("job", "career", "stelle", "vacanc", "position", "karriere")

    def __init__(
        self,
        urls: tuple[str, ...],
        client: JsonHttpClient | None = None,
        max_pages_per_site: int = 15,
    ) -> None:
        self.targets = tuple(_PageTarget(url) for url in dict.fromkeys(urls))
        self.client = client or JsonHttpClient()
        self.max_pages_per_site = max(1, max_pages_per_site)
        self.last_partial_error = ""
        self.last_target_status: dict[str, str] = {}
        self._robots_cache: dict[str, RobotFileParser | None] = {}

    def search(self, query: SearchQuery) -> list[JobPosting]:
        jobs: dict[str, JobPosting] = {}
        errors: list[str] = []
        self.last_target_status = {}
        for target in self.targets:
            if query.expired:
                break
            try:
                for job in self._crawl(target.root_url, query):
                    if matches_query(job, query):
                        jobs[job.job_id] = job
                self.last_target_status[target.root_url.rstrip("/")] = ""
            except Exception as error:
                self.last_target_status[target.root_url.rstrip("/")] = str(error)
                errors.append(f"{target.root_url}: {error}")
        self.last_partial_error = "; ".join(errors)
        if errors and not jobs:
            raise SourceError(self.last_partial_error)
        return list(jobs.values())

    def _crawl(self, root_url: str, query: SearchQuery) -> list[JobPosting]:
        parsed_root = urlsplit(root_url)
        host = (parsed_root.hostname or "").casefold()
        if parsed_root.scheme not in {"http", "https"} or not host:
            raise SourceError("Career URL має використовувати http або https")
        if any(host == blocked or host.endswith(f".{blocked}") for blocked in self._blocked_hosts):
            raise SourceError("Автоматичне читання цього job board вимкнене політикою JobCompass")
        if not self._robots_allows(root_url):
            raise SourceError("robots.txt не дозволяє автоматичне читання сторінки")

        pending = [root_url]
        visited: set[str] = set()
        jobs: list[JobPosting] = []
        while pending and len(visited) < self.max_pages_per_site:
            if query.expired:
                break
            url = pending.pop(0)
            if url in visited:
                continue
            visited.add(url)
            if not self._robots_allows(url):
                continue
            html = self.client.get_text(url)
            jobs.extend(
                extract_job_postings(
                    html,
                    url,
                    source=self.name,
                    company_hint=company_hint_from_url(root_url),
                )
            )
            if len(visited) == 1:
                discovered_links = list(extract_page_links(html, url))
                if "<loc" in html.casefold():
                    try:
                        sitemap_root = ElementTree.fromstring(html)
                    except ElementTree.ParseError:
                        sitemap_root = None
                    if sitemap_root is not None:
                        discovered_links.extend(
                            element.text.strip()
                            for element in sitemap_root.iter()
                            if element.tag.rsplit("}", 1)[-1].casefold() == "loc"
                            and element.text
                            and element.text.strip()
                        )
                for link in dict.fromkeys(discovered_links):
                    parsed = urlsplit(link)
                    if parsed.hostname == parsed_root.hostname and any(
                        marker in parsed.path.casefold() for marker in self._link_markers
                    ):
                        pending.append(link)
        return jobs

    def _robots_allows(self, url: str) -> bool:
        parsed = urlsplit(url)
        cache_key = parsed.netloc.casefold()
        if cache_key in self._robots_cache:
            parser = self._robots_cache[cache_key]
            return parser is None or parser.can_fetch(self.client.user_agent, url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        try:
            content = self.client.get_text(robots_url)
        except SourceError:
            self._robots_cache[cache_key] = None
            return True
        parser = RobotFileParser(robots_url)
        parser.parse(content.splitlines())
        self._robots_cache[cache_key] = parser
        return parser.can_fetch(self.client.user_agent, url)


class WorkdayCareerSource(GenericCareerPageSource):
    """Policy-aware Workday reader using public HTML/JSON-LD when exposed."""

    name = "Workday careers"


def build_career_sources(urls: tuple[str, ...]) -> dict[str, JobSource]:
    greenhouse: list[str] = []
    lever: list[tuple[str, bool]] = []
    ashby: list[str] = []
    personio: list[str] = []
    workday: list[str] = []
    generic: list[str] = []
    for url in dict.fromkeys(item.strip() for item in urls if item.strip()):
        parsed = urlsplit(url)
        host = (parsed.hostname or "").casefold()
        parts = [part for part in parsed.path.split("/") if part]
        if host in {"boards.greenhouse.io", "job-boards.greenhouse.io"} and parts:
            greenhouse.append(parts[0])
        elif host in {"jobs.lever.co", "jobs.eu.lever.co"} and parts:
            lever.append((parts[0], host == "jobs.eu.lever.co"))
        elif host == "jobs.ashbyhq.com" and parts:
            ashby.append(parts[0])
        elif host.endswith((".jobs.personio.de", ".jobs.personio.com")):
            personio.append(host)
        elif host.endswith("myworkdayjobs.com"):
            workday.append(url)
        else:
            generic.append(url)
    sources: dict[str, JobSource] = {}
    for source in (
        GreenhouseCareerSource(tuple(greenhouse)) if greenhouse else None,
        LeverCareerSource(tuple(lever)) if lever else None,
        AshbyCareerSource(tuple(ashby)) if ashby else None,
        PersonioCareerSource(tuple(personio)) if personio else None,
        WorkdayCareerSource(tuple(workday)) if workday else None,
        GenericCareerPageSource(tuple(generic)) if generic else None,
    ):
        if source is not None:
            sources[source.name] = source
    return sources
