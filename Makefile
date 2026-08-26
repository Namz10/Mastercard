.PHONY: install up down seed api test catalog-validate osint-validate identify-validate batch2-validate

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

osint-validate:
	python -c "from packages.osint.fixtures import load_fixture_documents; d=load_fixture_documents(); print(f'fixtures={len(d)}'); assert len(d)>=2"
	python -c "from packages.osint.collect import collect_candidate_urls; u=collect_candidate_urls(); print(f'airplane_urls={len(u)}'); assert len(u)>=2"

identify-validate:
	python -c "from packages.agents.identify_graph import run_identify_graph; r=run_identify_graph('make-validate'); print(r['run_id']); assert r['run_id']=='make-validate'"

batch2-validate: osint-validate identify-validate test

batch3-validate:
	IDENTIFY_LIVE_SEARCH=false QDRANT_DISABLED=true EMBEDDINGS_DISABLED=true python -c 'from unittest.mock import patch; from packages.agents.identify_graph import run_identify_graph; patch("packages.agents.nodes.librarian.merge_proposed_spec").start(); r=run_identify_graph("make-b3"); print("proposed", len(r.get("proposed_specs") or [])); assert len(r.get("proposed_specs") or [])>=1'

demo: up seed api
