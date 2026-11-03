"""Download every file listed in config/sources.yaml into data/raw/<source>/.

Sources that cannot be reached are written to data/raw/MANUAL_DOWNLOADS.md with exact URLs
and target file names, so the owner can download them by hand and rerun the pipeline.

Usage: python -m pipeline.ingest.fetch [source ...]
"""

from __future__ import annotations

import sys

import yaml

from pipeline.ingest._http import RAW, ROOT, DownloadBlocked, fetch

SOURCES = ROOT / "config" / "sources.yaml"
MANUAL = RAW / "MANUAL_DOWNLOADS.md"


def load_sources() -> dict:
    return yaml.safe_load(SOURCES.read_text(encoding="utf-8"))


def write_manual_list(blocked: list[tuple[str, dict, str, str]], unlisted: list[tuple[str, dict]]):
    lines = [
        "# Manual downloads needed",
        "",
        "These sources could not be downloaded automatically from the build environment.",
        "Download each file to the path shown (relative to the repo root), then rerun `make data`.",
        "",
    ]
    if blocked:
        lines += ["## Direct files", "", "| Source | Save as | URL |", "|---|---|---|"]
        for key, src, name, url in blocked:
            lines.append(f"| {src['name']} | `data/raw/{key}/{name}` | {url} |")
        lines.append("")
    if unlisted:
        lines += ["## Files to pick from a landing page", ""]
        for key, src in unlisted:
            lines.append(f"- **{src['name']}**: {src['landing']}. Save into `data/raw/{key}/`.")
            if src.get("notes"):
                lines.append(f"  {src['notes']}")
        lines.append("")
    MANUAL.write_text("\n".join(lines), encoding="utf-8")


def main(selected: list[str]) -> int:
    sources = load_sources()
    keys = selected or list(sources)
    blocked, unlisted = [], []
    for key in keys:
        src = sources[key]
        files = src.get("files") or []
        if not files:
            if not any((RAW / key).glob("*")):
                unlisted.append((key, src))
            continue
        for f in files:
            try:
                got = fetch(f["url"], RAW / key / f["name"])
                print(f"ok      {key}/{f['name']}  {'cached' if got.from_cache else 'downloaded'}")
            except DownloadBlocked as exc:
                print(f"BLOCKED {key}/{f['name']}  {exc}")
                blocked.append((key, src, f["name"], f["url"]))
    if blocked or unlisted:
        write_manual_list(blocked, unlisted)
        print(f"\n{len(blocked) + len(unlisted)} source(s) need manual download: {MANUAL}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
