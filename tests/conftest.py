from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
MARTS = ROOT / "data" / "marts"


def needs(path: Path):
    """Skip pipeline tests when the (gitignored) processed data is not present, e.g. in CI."""
    return pytest.mark.skipif(not path.exists(), reason=f"{path.relative_to(ROOT)} not built")


@pytest.fixture
def ref_con():
    con = duckdb.connect()
    for name in ["function_groups", "object_groups", "fund_groups"]:
        con.execute((ROOT / "sql" / "ref" / f"{name}.sql").read_text())
    yield con
    con.close()
