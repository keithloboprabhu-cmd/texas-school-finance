"""Run the whole pipeline: download -> clean -> Parquet -> DuckDB SQL -> marts -> checks.

Usage: python -m pipeline.build   (or `make data`)

Stages are added phase by phase. Each stage is idempotent: cached raw downloads are reused.
"""

from __future__ import annotations

import sys

from pipeline.ingest import fetch


def main() -> int:
    print("== 1. ingest ==")
    if fetch.main([]) != 0:
        print(
            "\nStopping: some sources are not in data/raw/ yet. "
            "See data/raw/MANUAL_DOWNLOADS.md, download them, then rerun `make data`."
        )
        return 1
    print("\nAll raw sources present. Clean/stage/mart stages are not implemented yet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
