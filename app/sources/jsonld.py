"""Extract schema.org JobPosting records from public career-page HTML."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlsplit

from app.core.models import JobPosting, WorkMode
from app.parsing import enrich_job_posting
from app.sources.utils import html_to_text, parse_published_at, text_value


class _StructuredDataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._capturing = False
        self._parts: list[str] = []
        self.scripts: list[str] = []
        self.links: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        values = {key.casefold(): value or "" for key, value in attrs}
        if tag.casefold() == "script" and "ld+json" in values.get("type", "").casefold():
            self._capturing = True
            self._parts = []
        elif tag.casefold() == "a" and values.get("href"):
            self.links.append(values["href"])

    def handle_data(self, data: str) -> None:
        if self._capturing:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() == "script" and self._capturing:
            self.scripts.append("".join(self._parts).strip())
            self._capturing = False
            self._parts = []


def extract_page_links(html: str, page_url: str) -> tuple[str, ...]:
    parser = _StructuredDataParser()
    parser.feed(html)
    return tuple(dict.fromkeys(urljoin(page_url, href) for href in parser.links))


def _types(value: object) -> set[str]:
    if isinstance(value, str):
        return {value.casefold()}
    if isinstance(value, list):
        return {str(item).casefold() for item in value}
    return set()


def _job_nodes(value: object) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        if "jobposting" in _types(value.get("@type")):
            yield value
        for child in value.values():
            yield from _job_nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from _job_nodes(child)


def _organization_name(value: object) -> str:
    if isinstance(value, Mapping):
        return text_value(value.get("name")) or text_value(value.get("legalName"))
    return text_value(value)


def _address(value: object) -> str:
    if not isinstance(value, Mapping):
        return text_value(value)
    address = value.get("address") if isinstance(value.get("address"), Mapping) else value
    if not isinstance(address, Mapping):
        return text_value(address)
    country = address.get("addressCountry")
    if isinstance(country, Mapping):
        country = country.get("name") or country.get("addressCountry")
    parts = (
        address.get("addressLocality"),
        address.get("addressRegion"),
        country,
    )
    return ", ".join(text_value(part) for part in parts if text_value(part))


def _location(node: Mapping[str, Any]) -> str:
    raw = node.get("jobLocation")
    locations = raw if isinstance(raw, list) else [raw]
    values = tuple(dict.fromkeys(_address(item) for item in locations if _address(item)))
    if values:
        return " / ".join(values)
    applicant = node.get("applicantLocationRequirements")
    applicants = applicant if isinstance(applicant, list) else [applicant]
    values = tuple(
        dict.fromkeys(
            text_value(item.get("name")) if isinstance(item, Mapping) else text_value(item)
            for item in applicants
            if (text_value(item.get("name")) if isinstance(item, Mapping) else text_value(item))
        )
    )
    return " / ".join(values)


def _external_id(node: Mapping[str, Any], url: str, title: str, company: str) -> str:
    identifier = node.get("identifier")
    if isinstance(identifier, Mapping):
        value = text_value(identifier.get("value")) or text_value(identifier.get("name"))
    else:
        value = text_value(identifier)
    if value:
        return value
    raw = "\x1f".join((url, title, company))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def extract_job_postings(
    html: str,
    page_url: str,
    *,
    source: str,
    company_hint: str = "",
) -> list[JobPosting]:
    parser = _StructuredDataParser()
    parser.feed(html)
    jobs: list[JobPosting] = []
    for script in parser.scripts:
        try:
            payload = json.loads(script)
        except (TypeError, json.JSONDecodeError):
            continue
        for node in _job_nodes(payload):
            title = text_value(node.get("title")) or text_value(node.get("name"))
            company = _organization_name(node.get("hiringOrganization")) or company_hint
            if not title or not company:
                continue
            url = urljoin(page_url, text_value(node.get("url"), page_url))
            location_type = " ".join(
                str(item) for item in (
                    node.get("jobLocationType")
                    if isinstance(node.get("jobLocationType"), list)
                    else [node.get("jobLocationType")]
                )
            ).casefold()
            remote = "telecommute" in location_type or "remote" in location_type
            employment = node.get("employmentType")
            employment_type = (
                ", ".join(str(item) for item in employment)
                if isinstance(employment, list)
                else text_value(employment) or None
            )
            jobs.append(
                enrich_job_posting(
                    JobPosting(
                        source=source,
                        external_id=_external_id(node, url, title, company),
                        title=title,
                        company=company,
                        location=_location(node) or ("Remote" if remote else ""),
                        url=url,
                        description=html_to_text(node.get("description")),
                        remote=remote,
                        work_mode=WorkMode.REMOTE if remote else WorkMode.UNKNOWN,
                        employment_type=employment_type,
                        published_at=parse_published_at(node.get("datePosted")),
                    )
                )
            )
    return jobs


def company_hint_from_url(url: str) -> str:
    host = urlsplit(url).hostname or ""
    label = host.removeprefix("www.").split(".")[0]
    return label.replace("-", " ").replace("_", " ").title()
