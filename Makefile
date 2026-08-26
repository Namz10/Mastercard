.PHONY: install up down seed api test catalog-validate

PYTHONPATH ?= $(CURDIR)
export PYTHONPATH

install:
	pip install -e ".[dev]"

up:
	docker compose up -d postgres
	@echo "Waiting for Postgres..."
	@sleep 3

down:
	docker compose down

seed:
	python apps/api/seed.py --reset

api:
	uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -q

catalog-validate:
	python -c "from packages.catalog.loader import load_catalog_yaml, catalog_summary; s=catalog_summary(load_catalog_yaml()); print(s); assert s['count']>=28 and not s['missing_techniques']"

demo: up seed api
