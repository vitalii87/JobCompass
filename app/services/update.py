"""Secure, standard-library update checks backed by GitHub Releases."""

from __future__ import annotations

import hashlib
from http.client import IncompleteRead
import json
import re
import socket
import ssl
import sys
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import BinaryIO
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app import __version__
from app.core.paths import PORTABLE_MARKER


LATEST_RELEASE_API = (
    "https://api.github.com/repos/vitalii87/JobCompass/releases/latest"
)
_VERSION_PATTERN = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$")


class UpdateError(RuntimeError):
    """A user-facing failure while checking or downloading an update."""


@dataclass(frozen=True, slots=True)
class ReleaseAsset:
    name: str
    download_url: str
    api_url: str = ""
    size: int = 0
    sha256: str = ""


@dataclass(frozen=True, slots=True)
class ReleaseInfo:
    version: str
    page_url: str
    notes: str
    assets: tuple[ReleaseAsset, ...]

    def asset_for(self, runtime_mode: str) -> ReleaseAsset | None:
        suffix = "-Portable.zip" if runtime_mode == "portable" else "-Setup.exe"
        return next(
            (asset for asset in self.assets if asset.name.endswith(suffix)), None
        )


def runtime_mode(
    *, executable: str | Path | None = None, frozen: bool | None = None
) -> str:
    """Return ``installed``, ``portable`` or ``source`` for the current process."""

    is_frozen = bool(getattr(sys, "frozen", False)) if frozen is None else frozen
    if not is_frozen:
        return "source"
    executable_directory = Path(executable or sys.executable).resolve().parent
    return (
        "portable"
        if (executable_directory / PORTABLE_MARKER).is_file()
        else "installed"
    )


def is_newer_version(candidate: str, current: str = __version__) -> bool:
    """Compare the stable numeric versions used by JobCompass releases."""

    def parts(value: str) -> tuple[int, int, int]:
        match = _VERSION_PATTERN.fullmatch(value.strip())
        if match is None:
            raise UpdateError(f"Некоректний номер версії: {value}")
        return tuple(int(part) for part in match.groups())  # type: ignore[return-value]

    return parts(candidate) > parts(current)


def _request(url: str, *, binary: bool = False) -> Request:
    return Request(
        url,
        headers={
            "Accept": (
                "application/octet-stream"
                if binary
                else "application/vnd.github+json"
            ),
            "Accept-Encoding": "identity",
            "User-Agent": f"JobCompass/{__version__} (Windows updater)",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="GET",
    )


def _open(
    request: Request,
    timeout: float,
    *,
    attempts: int = 3,
) -> BinaryIO:
    """Open a GitHub request with bounded retries for transient disconnects."""

    last_error: BaseException | None = None
    retryable_http_codes = {408, 429, 500, 502, 503, 504}
    for attempt in range(max(1, attempts)):
        try:
            return urlopen(request, timeout=timeout)  # type: ignore[return-value]
        except HTTPError as error:
            if error.code not in retryable_http_codes:
                raise UpdateError(
                    f"GitHub повернув HTTP {error.code}: {error.reason}"
                ) from error
            last_error = error
        except (
            URLError,
            TimeoutError,
            socket.timeout,
            ConnectionError,
            ssl.SSLError,
        ) as error:
            last_error = error
        if attempt + 1 < max(1, attempts):
            time.sleep(0.4 * (2**attempt))
    raise UpdateError(
        f"Не вдалося підключитися до GitHub після повторних спроб: {last_error}"
    ) from last_error


def _read_checksums(asset: ReleaseAsset, timeout: float) -> dict[str, str]:
    try:
        with _open(_request(asset.download_url), timeout) as response:
            text = response.read().decode("utf-8-sig")
    except (UnicodeDecodeError, OSError) as error:
        raise UpdateError("Не вдалося прочитати SHA256SUMS.txt") from error
    checksums: dict[str, str] = {}
    for line in text.splitlines():
        pieces = line.strip().split(maxsplit=1)
        if len(pieces) == 2 and re.fullmatch(r"[0-9a-fA-F]{64}", pieces[0]):
            checksums[pieces[1].lstrip("* ")] = pieces[0].lower()
    return checksums


def check_latest_release(timeout: float = 20.0) -> ReleaseInfo:
    """Fetch and validate the newest stable GitHub release metadata."""

    try:
        with _open(_request(LATEST_RELEASE_API), timeout) as response:
            payload = json.load(response)
    except (UnicodeDecodeError, json.JSONDecodeError, OSError) as error:
        raise UpdateError("GitHub повернув некоректні дані про оновлення") from error
    if not isinstance(payload, dict):
        raise UpdateError("GitHub повернув неочікуваний формат оновлення")

    tag = str(payload.get("tag_name", "")).strip()
    match = _VERSION_PATTERN.fullmatch(tag)
    if match is None:
        raise UpdateError("Останній GitHub Release не має коректного номера версії")
    version = ".".join(match.groups())
    raw_assets = payload.get("assets", [])
    assets: list[ReleaseAsset] = []
    if isinstance(raw_assets, list):
        for item in raw_assets:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            url = str(item.get("browser_download_url", "")).strip()
            api_url = str(item.get("url", "")).strip()
            if not name or not url.startswith("https://github.com/"):
                continue
            if not api_url.startswith(
                "https://api.github.com/repos/vitalii87/JobCompass/releases/assets/"
            ):
                api_url = ""
            digest = str(item.get("digest") or "")
            sha256 = digest.removeprefix("sha256:").lower()
            if not re.fullmatch(r"[0-9a-f]{64}", sha256):
                sha256 = ""
            assets.append(
                ReleaseAsset(
                    name=name,
                    download_url=url,
                    api_url=api_url,
                    size=int(item.get("size") or 0),
                    sha256=sha256,
                )
            )

    checksum_asset = next(
        (asset for asset in assets if asset.name == "SHA256SUMS.txt"), None
    )
    assets_missing_digest = [
        asset
        for asset in assets
        if asset.name != "SHA256SUMS.txt" and not asset.sha256
    ]
    if checksum_asset is not None and assets_missing_digest:
        checksums = _read_checksums(checksum_asset, timeout)
        assets = [
            replace(asset, sha256=asset.sha256 or checksums.get(asset.name, ""))
            for asset in assets
        ]

    return ReleaseInfo(
        version=version,
        page_url=str(payload.get("html_url", "")).strip(),
        notes=str(payload.get("body") or "").strip(),
        assets=tuple(assets),
    )


def download_release_asset(
    asset: ReleaseAsset,
    destination: str | Path,
    timeout: float = 60.0,
    attempts: int = 3,
) -> Path:
    """Download an asset atomically and reject it if SHA-256 does not match."""

    if not asset.sha256:
        raise UpdateError(
            "Оновлення не має контрольної суми SHA-256, тому його не буде запущено."
        )
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".part")
    requests = [
        *(
            [_request(asset.api_url, binary=True)]
            if asset.api_url
            else []
        ),
        _request(asset.download_url, binary=True),
    ]
    last_error: BaseException | None = None
    for attempt in range(max(1, attempts)):
        partial.unlink(missing_ok=True)
        request = requests[attempt % len(requests)]
        digest = hashlib.sha256()
        received = 0
        try:
            with _open(request, timeout, attempts=2) as response, partial.open(
                "wb"
            ) as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
                    digest.update(chunk)
                    received += len(chunk)
            if asset.size and received != asset.size:
                raise IncompleteRead(b"", abs(asset.size - received))
            if digest.hexdigest() != asset.sha256:
                raise UpdateError(
                    "Контрольна сума завантаженого оновлення не збігається. Файл видалено."
                )
            partial.replace(target)
            return target
        except UpdateError as error:
            last_error = error
            if "Контрольна сума" in str(error):
                partial.unlink(missing_ok=True)
                raise
        except (
            URLError,
            TimeoutError,
            socket.timeout,
            ConnectionError,
            ssl.SSLError,
            IncompleteRead,
        ) as error:
            last_error = error
        finally:
            partial.unlink(missing_ok=True)
        if attempt + 1 < max(1, attempts):
            time.sleep(0.5 * (2**attempt))
    raise UpdateError(
        "Не вдалося завантажити файл оновлення після повторних спроб. "
        f"Перевірте інтернет-з’єднання або відкрийте сторінку релізу. {last_error}"
    ) from last_error
