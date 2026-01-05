"""Download the file of a year, check its sha256 in memory, and only then write it."""

import hashlib
import http.client
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from baac_digest.errors import DownloadError

logger = logging.getLogger(__name__)

TIMEOUT_S = 60.0


@dataclass(frozen=True)
class Source:
    url: str
    sha256: str
    updated: str = ""  # date of the file on data.gouv.fr, quoted by the README (licence)


_BASE = "https://static.data.gouv.fr/resources/bases-de-donnees-annuelles-des-accidents-corporels-"
REGISTRY: dict[int, Source] = {
    2023: Source(
        _BASE + "de-la-circulation-routiere-annees-de-2005-a-2023/20241028-103125/caract-2023.csv",
        "e6cb8685b7e144e56365bed7c542bd90a95c3512431b9ba0e62a01cfd4a87ac0",
        "2024-10-28",
    ),
    2024: Source(
        _BASE + "de-la-circulation-routiere-annees-de-2005-a-2024/20251021-115900/caract-2024.csv",
        "45a69360aeb566f9065e079c5e9840fb1068e71cd4e6fcc34cb9fdcaff04b391",
        "2025-10-21",
    ),
}


def read_url(url: str) -> bytes:
    """The only function that touches the network: the tests replace it."""
    with urllib.request.urlopen(url, timeout=TIMEOUT_S) as response:
        data: bytes = response.read()
    return data


def fetch(source: Source, out: Path) -> None:
    """Downloads `source` in memory (6.6 MB fit easily), checks its sha256, then writes `out`.

    On any failure nothing is written (`out` stays absent, or intact) and DownloadError is
    raised."""
    logger.info("downloading %s", source.url)
    try:
        data = read_url(source.url)
    except (urllib.error.URLError, http.client.HTTPException, OSError) as error:
        raise DownloadError(f"{source.url}: {error}") from error
    digest = hashlib.sha256(data).hexdigest()
    if digest != source.sha256.lower():
        raise DownloadError(
            f"sha256 mismatch for {source.url}: expected {source.sha256}, got {digest}"
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    logger.info("sha256 verified, wrote %s (%d bytes)", out, len(data))
