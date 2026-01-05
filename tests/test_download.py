"""The verified download, without Internet: `read_url`, the only function that touches the
network, is replaced by monkeypatch."""

import hashlib
import urllib.error
from collections.abc import Callable
from pathlib import Path

import pytest
from typer.testing import CliRunner

from baac_digest import download as downloads
from baac_digest.cli import app

runner = CliRunner()
PAYLOAD = b'"Num_Acc";"jour"\n"202300000001";"7"\n'
GOOD_SHA256 = hashlib.sha256(PAYLOAD).hexdigest()
URL = "https://example.org/caract.csv"

Serve = Callable[..., None]


@pytest.fixture
def served(monkeypatch: pytest.MonkeyPatch) -> Serve:
    """served(error=None): read_url returns PAYLOAD, or raises `error`."""

    def serve(error: BaseException | None = None) -> None:
        def fake_read_url(url: str) -> bytes:
            if error is not None:
                raise error
            return PAYLOAD

        monkeypatch.setattr(downloads, "read_url", fake_read_url)

    return serve


def download(out: Path, *options: str) -> int:
    return runner.invoke(app, ["download", "--out", str(out), *options]).exit_code


def test_good_sha256_writes_the_file(served: Serve, tmp_path: Path) -> None:
    served()
    out = tmp_path / "data" / "2023" / "caract.csv"
    assert download(out, "--url", URL, "--sha256", GOOD_SHA256) == 0
    assert out.read_bytes() == PAYLOAD


def test_wrong_sha256_keeps_the_existing_file(served: Serve, tmp_path: Path) -> None:
    served()
    out = tmp_path / "caract.csv"
    out.write_bytes(b"previous")
    assert download(out, "--url", URL, "--sha256", "0" * 64) == 1
    assert out.read_bytes() == b"previous"


def test_wrong_sha256_writes_nothing(served: Serve, tmp_path: Path) -> None:
    served()
    out = tmp_path / "caract.csv"
    assert download(out, "--url", URL, "--sha256", "0" * 64) == 1
    assert not out.exists()


@pytest.mark.parametrize(
    "error",
    [
        urllib.error.HTTPError(URL, 404, "Not Found", None, None),  # type: ignore[arg-type]
        urllib.error.URLError("connection refused"),
    ],
    ids=["http-404", "unreachable"],
)
def test_http_or_network_error(served: Serve, tmp_path: Path, error: BaseException) -> None:
    served(error)
    out = tmp_path / "caract.csv"
    assert download(out, "--url", URL, "--sha256", GOOD_SHA256) == 1
    assert not out.exists()


def test_year_of_the_registry(served: Serve, tmp_path: Path) -> None:
    served()
    out = tmp_path / "caract.csv"
    assert download(out, "--year", "2023") == 1  # the fake payload is not the 2023 file
    assert not out.exists()


def test_unknown_year(tmp_path: Path) -> None:
    out = tmp_path / "caract.csv"
    assert download(out, "--year", "1999") == 2
    assert not out.exists()


@pytest.mark.parametrize("options", [["--url", URL], ["--sha256", GOOD_SHA256]])
def test_url_and_sha256_go_together(tmp_path: Path, options: list[str]) -> None:
    assert download(tmp_path / "caract.csv", *options) == 2


def test_only_http_urls(tmp_path: Path) -> None:
    assert download(tmp_path / "x.csv", "--url", "file:///etc/passwd", "--sha256", "0" * 64) == 2
