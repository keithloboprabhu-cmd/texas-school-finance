"""Methodology & Data: sources, definitions, exclusions, caveats and as-of dates."""

from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

from ui.components import page_header, rule

ROOT = Path(__file__).resolve().parent.parent

page_header(
    "Methodology & Data",
    "Sources, definitions and caveats",
    "Every number in this atlas comes from the pipeline in this repository. "
    "This page lists where the data comes from and what has been verified.",
)

sources = yaml.safe_load((ROOT / "config" / "sources.yaml").read_text(encoding="utf-8"))
st.subheader("Sources", anchor=False)
st.dataframe(
    pd.DataFrame(
        [
            {
                "Source": s["name"],
                "Publisher": s["publisher"],
                "Link": s["landing"],
                "Status": s.get("status", ""),
            }
            for s in sources.values()
        ]
    ),
    hide_index=True,
    width="stretch",
    column_config={"Link": st.column_config.LinkColumn()},
)

rule()
st.subheader("Glossary", anchor=False)
glossary = yaml.safe_load((ROOT / "config" / "glossary.yaml").read_text(encoding="utf-8"))
for entry in glossary.values():
    st.markdown(f"**{entry['label']}**: {entry['definition']}")

rule()
st.subheader("Unit of analysis and universe", anchor=False)
st.markdown(
    "- **Unit:** Texas school district by school year. The fiscal/school-year convention will be "
    "stated here once confirmed against the TEA files.\n"
    "- **Universe:** independent and common school districts with geographic boundaries. "
    "Open-enrollment charters have no boundaries and no local property tax base, so they are "
    "excluded from the map and from the wealth-vs-spending analysis and reported separately.\n"
    "- **Identifiers:** TEA's 6-digit County-District Number (CDN), always kept as a zero-padded "
    "string; NCES/Census 7-digit LEAID/GEOID (Texas FIPS 48 + 5 digits)."
)
