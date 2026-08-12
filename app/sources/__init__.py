"""Job source connectors for local files and public online job APIs."""

from app.sources.arbeitnow import ArbeitnowSource
from app.sources.base import (
    JobSource,
    SearchQuery,
    SourceAccess,
    SourceBatch,
    SourceCapabilities,
    SourceDiagnostic,
)
from app.sources.bundesagentur import BundesagenturSource
from app.sources.careers import (
    AshbyCareerSource,
    GenericCareerPageSource,
    GreenhouseCareerSource,
    LeverCareerSource,
    PersonioCareerSource,
    WorkdayCareerSource,
    build_career_sources,
)
from app.sources.http import SourceError
from app.sources.json_file import JsonFileSource
from app.sources.remotive import RemotiveSource
from app.sources.orchestrator import SearchOrchestrator
from app.sources.discovery import (
    AutomaticSourceDiscoverer,
    DiscoveryReport,
    WebDiscoveryProvider,
    WebDiscoveryResult,
    detect_source_url,
)

ONLINE_SOURCE_TYPES = (BundesagenturSource, ArbeitnowSource, RemotiveSource)


def build_online_sources(career_urls: tuple[str, ...] = ()) -> dict[str, JobSource]:
    sources: dict[str, JobSource] = {
        source_type.name: source_type() for source_type in ONLINE_SOURCE_TYPES
    }
    sources.update(build_career_sources(career_urls))
    return sources

__all__ = [
    "ArbeitnowSource",
    "AutomaticSourceDiscoverer",
    "BundesagenturSource",
    "AshbyCareerSource",
    "GenericCareerPageSource",
    "DiscoveryReport",
    "GreenhouseCareerSource",
    "JobSource",
    "JsonFileSource",
    "ONLINE_SOURCE_TYPES",
    "LeverCareerSource",
    "PersonioCareerSource",
    "WorkdayCareerSource",
    "WebDiscoveryProvider",
    "WebDiscoveryResult",
    "RemotiveSource",
    "SearchQuery",
    "SearchOrchestrator",
    "SourceAccess",
    "SourceBatch",
    "SourceCapabilities",
    "SourceDiagnostic",
    "SourceError",
    "build_career_sources",
    "build_online_sources",
    "detect_source_url",
]
