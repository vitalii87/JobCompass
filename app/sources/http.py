"""Small standard-library HTTP client for public job source APIs."""

from __future__ import annotations

import json
import socket
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class SourceError(ValueError):
    """A user-facing error raised by an online job source."""


@dataclass(frozen=True, slots=True)
class JsonHttpClient:
    timeout: float = 20.0
    user_agent: str = "JobCompass/0.10.3 (local desktop job search)"

    def get_json(
        self,
        url: str,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        if params:
            query = urlencode(
                {key: value for key, value in params.items() if value not in (None, "")},
                doseq=True,
            )
            url = f"{url}?{query}"
        request_headers = {"Accept": "application/json", "User-Agent": self.user_agent}
        request_headers.update(headers or {})
        request = Request(url, headers=request_headers, method="GET")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload: Any = json.load(response)
        except HTTPError as error:
            raise SourceError(
                f"Сервер повернув HTTP {error.code}: {error.reason}"
            ) from error
        except (URLError, TimeoutError, socket.timeout) as error:
            raise SourceError(f"Не вдалося підключитися до джерела: {error}") from error
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise SourceError("Джерело повернуло некоректну JSON-відповідь") from error
        if not isinstance(payload, dict):
            raise SourceError("Джерело повернуло неочікуваний формат даних")
        return payload
