"""District Profile: a one-page report card for any district (?district=<CDN>)."""

from ui.components import page_header, require_marts

page_header("District profile", "District Profile", "A report card for any Texas school district.")
require_marts("mart_district_year")
