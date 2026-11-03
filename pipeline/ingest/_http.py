"""Polite, cached, retrying downloader shared by every ingest module."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
CHECKSUM_LOG = RAW / "checksums.jsonl"
USER_AGENT = (
    "LoneStarLedger/0.1 (Texas school finance research project; "
    "https://github.com/keithloboprabhu-cmd/texas-school-finance)"
)


class DownloadBlocked(RuntimeError):
    """The source could not be reached from this environment after all retries."""


@dataclass
class Downloaded:
    path: Path
    sha256: str
    from_cache: bool


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(
    url: str,
    dest: Path,
    *,
    params: dict | None = None,
    retries: int = 4,
    timeout: float = 120,
    refresh: bool = False,
) -> Downloaded:
    """Download `url` to `dest` unless it is already cached. Retries with exponential backoff."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0 and not refresh:
        return Downloaded(dest, _sha256(dest), from_cache=True)

    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            with requests.get(
                url,
                params=params,
                headers={"User-Agent": USER_AGENT},
                timeout=timeout,
                stream=True,
            ) as r:
                r.raise_for_status()
                tmp = dest.with_suffix(dest.suffix + ".part")
                with tmp.open("wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
                tmp.replace(dest)
            break
        except requests.RequestException as exc:
            last_err = exc
            if attempt < retries - 1:
                time.sleep(2 ** (attempt + 1))
    else:
        raise DownloadBlocked(f"{url}: {last_err}")

    digest = _sha256(dest)
    with CHECKSUM_LOG.open("a", encoding="utf-8") as log:
        log.write(
            json.dumps(
                {
                    "file": dest.relative_to(ROOT).as_posix(),
                    "url": url,
                    "sha256": digest,
                    "bytes": dest.stat().st_size,
                    "downloaded_at": datetime.now(UTC).isoformat(),
                }
            )
            + "\n"
        )
    return Downloaded(dest, digest, from_cache=False)
