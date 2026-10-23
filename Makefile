.PHONY: install build test lint app docs all

install:
	pip install -r requirements-dev.txt

build:
	mkdir -p warehouse && cd dbt && dbt build --profiles-dir .

test:
	python -m pytest -q

lint:
	ruff check app src tests

app:
	streamlit run app/streamlit_app.py

docs:
	cd dbt && dbt docs generate --profiles-dir . && dbt docs serve --profiles-dir .

all: lint build test
