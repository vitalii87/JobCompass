from __future__ import annotations

import io
import json
import tempfile
import unittest
from hashlib import sha256
from http.client import RemoteDisconnected
from pathlib import Path
from unittest.mock import patch

from app.services.update import (
    ReleaseAsset,
    UpdateError,
    check_latest_release,
    download_release_asset,
    is_newer_version,
    runtime_mode,
)


class UpdateServiceTests(unittest.TestCase):
    def test_version_comparison_uses_numeric_components(self) -> None:
        self.assertTrue(is_newer_version("0.10.0", "0.9.9"))
        self.assertFalse(is_newer_version("v0.9.0", "0.9.0"))
        with self.assertRaises(UpdateError):
            is_newer_version("latest", "0.9.0")

    def test_runtime_mode_distinguishes_source_installed_and_portable(self) -> None:
        self.assertEqual(runtime_mode(frozen=False), "source")
        with tempfile.TemporaryDirectory() as directory:
            app_directory = Path(directory)
            executable = app_directory / "JobCompass.exe"
            self.assertEqual(
                runtime_mode(executable=executable, frozen=True), "installed"
            )
            (app_directory / "portable.flag").touch()
            self.assertEqual(
                runtime_mode(executable=executable, frozen=True), "portable"
            )

    def test_latest_release_uses_checksum_manifest(self) -> None:
        installer_name = "JobCompass-0.9.1-Setup.exe"
        expected_hash = "a" * 64
        payload = {
            "tag_name": "v0.9.1",
            "html_url": "https://github.com/vitalii87/JobCompass/releases/tag/v0.9.1",
            "body": "Changes",
            "assets": [
                {
                    "name": installer_name,
                    "browser_download_url": (
                        "https://github.com/vitalii87/JobCompass/releases/download/"
                        f"v0.9.1/{installer_name}"
                    ),
                    "size": 123,
                },
                {
                    "name": "SHA256SUMS.txt",
                    "browser_download_url": (
                        "https://github.com/vitalii87/JobCompass/releases/download/"
                        "v0.9.1/SHA256SUMS.txt"
                    ),
                    "size": 80,
                },
            ],
        }
        responses = [
            io.BytesIO(json.dumps(payload).encode("utf-8")),
            io.BytesIO(f"{expected_hash}  {installer_name}\n".encode("utf-8")),
        ]

        with patch("app.services.update._open", side_effect=responses):
            release = check_latest_release()

        self.assertEqual(release.version, "0.9.1")
        self.assertEqual(release.asset_for("installed").sha256, expected_hash)

    def test_latest_release_prefers_github_digest_without_extra_manifest_request(
        self,
    ) -> None:
        expected_hash = "b" * 64
        payload = {
            "tag_name": "v0.11.1",
            "html_url": "https://github.com/vitalii87/JobCompass/releases/tag/v0.11.1",
            "assets": [
                {
                    "name": "JobCompass-0.11.1-Setup.exe",
                    "url": "https://api.github.com/repos/vitalii87/JobCompass/releases/assets/1",
                    "browser_download_url": "https://github.com/vitalii87/JobCompass/releases/download/v0.11.1/JobCompass-0.11.1-Setup.exe",
                    "size": 123,
                    "digest": f"sha256:{expected_hash}",
                },
                {
                    "name": "SHA256SUMS.txt",
                    "url": "https://api.github.com/repos/vitalii87/JobCompass/releases/assets/2",
                    "browser_download_url": "https://github.com/vitalii87/JobCompass/releases/download/v0.11.1/SHA256SUMS.txt",
                    "size": 80,
                    "digest": f"sha256:{'c' * 64}",
                },
            ],
        }

        with patch(
            "app.services.update._open",
            return_value=io.BytesIO(json.dumps(payload).encode("utf-8")),
        ) as opened:
            release = check_latest_release()

        self.assertEqual(opened.call_count, 1)
        installer = release.asset_for("installed")
        assert installer is not None
        self.assertEqual(installer.sha256, expected_hash)
        self.assertTrue(installer.api_url.endswith("/assets/1"))

    def test_download_is_atomic_and_verifies_sha256(self) -> None:
        content = b"verified installer"
        asset = ReleaseAsset(
            name="JobCompass-0.9.1-Setup.exe",
            download_url="https://github.com/example/update.exe",
            sha256=sha256(content).hexdigest(),
        )
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / asset.name
            with patch(
                "app.services.update._open", return_value=io.BytesIO(content)
            ):
                result = download_release_asset(asset, destination)

            self.assertEqual(result.read_bytes(), content)
            self.assertFalse(destination.with_suffix(".exe.part").exists())

    def test_download_rejects_mismatched_hash(self) -> None:
        asset = ReleaseAsset(
            name="JobCompass-0.9.1-Setup.exe",
            download_url="https://github.com/example/update.exe",
            sha256="0" * 64,
        )
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / asset.name
            with patch(
                "app.services.update._open", return_value=io.BytesIO(b"tampered")
            ):
                with self.assertRaises(UpdateError):
                    download_release_asset(asset, destination)
            self.assertFalse(destination.exists())

    def test_download_falls_back_from_asset_api_to_browser_url(self) -> None:
        content = b"verified installer"
        asset = ReleaseAsset(
            name="JobCompass-0.11.1-Setup.exe",
            download_url="https://github.com/example/update.exe",
            api_url="https://api.github.com/repos/vitalii87/JobCompass/releases/assets/1",
            size=len(content),
            sha256=sha256(content).hexdigest(),
        )
        with tempfile.TemporaryDirectory() as directory, patch(
            "app.services.update._open",
            side_effect=(UpdateError("temporary disconnect"), io.BytesIO(content)),
        ) as opened, patch("app.services.update.time.sleep"):
            result = download_release_asset(
                asset,
                Path(directory) / asset.name,
            )
            self.assertEqual(result.read_bytes(), content)

        requested_urls = [call.args[0].full_url for call in opened.call_args_list]
        self.assertEqual(requested_urls, [asset.api_url, asset.download_url])

    def test_open_retries_remote_disconnect(self) -> None:
        from app.services.update import _open, _request

        response = io.BytesIO(b"ok")
        with patch(
            "app.services.update.urlopen",
            side_effect=(RemoteDisconnected("closed"), response),
        ) as opened, patch("app.services.update.time.sleep"):
            result = _open(_request("https://api.github.com/example"), 1.0)

        self.assertIs(result, response)
        self.assertEqual(opened.call_count, 2)


if __name__ == "__main__":
    unittest.main()
