"""Config files parse, glossary entries are complete, and law-change markers cite a source."""

from pathlib import Path

import yaml

CONFIG = Path(__file__).resolve().parent.parent / "config"


def test_all_config_parses():
    for f in CONFIG.glob("*.yaml"):
        assert yaml.safe_load(f.read_text()) is not None, f.name


def test_events_have_primary_sources():
    for e in yaml.safe_load((CONFIG / "events.yaml").read_text())["events"]:
        assert e["source"].startswith("https://capitol.texas.gov/"), e
        assert {"date", "school_year", "label", "checked"} <= set(e)


def test_glossary_entries_complete():
    for k, v in yaml.safe_load((CONFIG / "glossary.yaml").read_text()).items():
        assert v.get("label") and v.get("definition"), k


def test_metric_layers_complete():
    for k, v in yaml.safe_load((CONFIG / "metrics.yaml").read_text())["layers"].items():
        assert {"theme", "label", "column", "fmt", "palette", "read"} <= set(v), k
