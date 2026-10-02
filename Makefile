PYTHON ?= .venv/bin/python

.PHONY: install data-download data-normalize data-validate migrate data-load data \
	test lint frontend-install frontend-test frontend-build frontend-audit verify up down

install:
	python3 -m venv .venv
	$(PYTHON) -m pip install -e '.[dev]'
	cd frontend && npm ci

data-download:
	$(PYTHON) -m ingestion.download

data-normalize:
	$(PYTHON) -m ingestion.normalize

data-validate:
	$(PYTHON) -m ingestion.validate

migrate:
	docker compose up -d db
	docker compose run --rm migrate

data-load: migrate
	docker compose run --rm backend python -m ingestion.load_postgres --replace

data: data-download data-normalize data-validate

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check .

frontend-install:
	cd frontend && npm ci

frontend-test:
	cd frontend && npm test

frontend-build:
	cd frontend && npm run build

frontend-audit:
	cd frontend && npm audit --audit-level=moderate

verify: test lint frontend-test frontend-build frontend-audit

up:
	docker compose up --build -d

down:
	docker compose down
