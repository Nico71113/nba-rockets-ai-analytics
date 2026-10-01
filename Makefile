.PHONY: data-download data-normalize data-validate data test lint

data-download:
	python -m ingestion.download

data-normalize:
	python -m ingestion.normalize

data-validate:
	python -m ingestion.validate

data: data-download data-normalize data-validate

test:
	pytest

lint:
	ruff check .
