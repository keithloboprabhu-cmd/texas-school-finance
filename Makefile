PY ?= python

.PHONY: install data app test lint check

install:
	$(PY) -m pip install -r requirements-dev.txt

data:            ## Download, clean, build the DuckDB warehouse and marts, run data-quality checks
	$(PY) -m pipeline.build

app:
	streamlit run app.py

test:
	$(PY) -m pytest -q

lint:
	ruff check .
	ruff format --check .

check: lint test
