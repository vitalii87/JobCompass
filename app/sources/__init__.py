"""Job source connector contracts and built-in offline sources."""

from app.sources.base import JobSource, SearchQuery
from app.sources.json_file import JsonFileSource

__all__ = ["JobSource", "JsonFileSource", "SearchQuery"]
