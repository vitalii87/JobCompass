"""Job source connectors for local files and public online job APIs."""

from app.sources.arbeitnow import ArbeitnowSource
from app.sources.base import JobSource, SearchQuery
from app.sources.bundesagentur import BundesagenturSource
from app.sources.http import SourceError
from app.sources.json_file import JsonFileSource
from app.sources.remotive import RemotiveSource

ONLINE_SOURCE_TYPES = (BundesagenturSource, ArbeitnowSource, RemotiveSource)

__all__ = [
    "ArbeitnowSource",
    "BundesagenturSource",
    "JobSource",
    "JsonFileSource",
    "ONLINE_SOURCE_TYPES",
    "RemotiveSource",
    "SearchQuery",
    "SourceError",
]
