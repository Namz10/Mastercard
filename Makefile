.PHONY: install up down seed api test catalog-validate osint-validate identify-validate batch2-validate validate-all validate-all-live

PYTHONPATH ?= $(CURDIR)
export PYTHONPATH

ifneq (,$(wildcard $(CURDIR)/.venv/bin/python))
PY := $(CURDIR)/.venv/bin/python
else
PY := python3
endif

VALIDATE_ENV = IDENTIFY_LIVE_SEARCH=false AEGIS_EMBEDDINGS=hash

install:
	uv sync --extra dev

up:
	docker compose up -d postgres --wait

down:
	docker compose down

seed:
	$(PY) apps/api/seed.py --reset

api:
	uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

test:
	$(PY) -m pytest tests/ -q -m "not live_llm and not live_identify"

catalog-validate:
	$(PY) -c "from packages.catalog.loader import load_catalog_yaml, catalog_summary; s=catalog_summary(load_catalog_yaml()); print(s); assert s['count']>=28 and not s['missing_techniques']"

osint-validate:
	$(PY) -c "from packages.osint.fixtures import load_fixture_documents; d=load_fixture_documents(); print(f'fixtures={len(d)}'); assert len(d)>=2"
	$(PY) -c "from packages.osint.collect import collect_candidate_urls; u=collect_candidate_urls(); print(f'airplane_urls={len(u)}'); assert len(u)>=2"

identify-validate:
	$(VALIDATE_ENV) $(PY) -c "from apps.api.db import init_db; from packages.agents.identify_graph import run_identify_graph; init_db(); r=run_identify_graph('make-validate'); print(r['run_id'], len(r.get('proposed_specs') or [])); assert r['run_id']=='make-validate'"

batch2-validate: osint-validate identify-validate test

batch3-validate:
	$(VALIDATE_ENV) $(PY) -c 'from apps.api.db import init_db; from packages.agents.identify_graph import run_identify_graph; init_db(); r=run_identify_graph("make-b3"); print("proposed", len(r.get("proposed_specs") or [])); assert len(r.get("proposed_specs") or [])>=1'

generate-validate:
	$(PY) -c "from apps.api.db import SessionLocal, init_db; from apps.api.seed import seed_catalog; from packages.sim.runner import run_population; init_db(); seed_catalog(reset=True); db=SessionLocal(); r=run_population(db, vector_id='t13-upi-impersonation-app'); db.close(); assert r['injector_id']=='app_session'"

defend-validate:
	$(PY) -c "from apps.api.db import SessionLocal, init_db; from apps.api.seed import seed_catalog; from packages.policy.coverage import build_coverage_map; init_db(); seed_catalog(reset=True); db=SessionLocal(); m=build_coverage_map(db); db.close(); assert m['technique_count']==24"

handoff-validate: generate-validate defend-validate

validate-all:
	@echo "=== [1/6] catalog ===" && $(MAKE) catalog-validate
	@echo "=== [2/6] osint (airplane) ===" && $(MAKE) osint-validate
	@echo "=== [3/6] postgres + seed ===" && $(MAKE) up seed
	@echo "=== [4/6] generate + defend handoff ===" && $(MAKE) handoff-validate
	@echo "=== [5/6] identify graph (offline, real librarian) ===" && $(VALIDATE_ENV) $(PY) -c 'from apps.api.db import init_db; from packages.agents.identify_graph import run_identify_graph; init_db(); r=run_identify_graph("validate-all"); assert len(r.get("candidate_urls") or [])>=1; assert len(r.get("proposed_specs") or [])>=1; print("identify OK", r["run_id"], "proposed", len(r["proposed_specs"]))'
	@echo "=== [6/6] pytest ===" && $(VALIDATE_ENV) $(PY) -m pytest tests/ -q -m "not live_llm and not live_identify"
	@echo "=== ALL GATES PASSED ==="

validate-all-live:
	./run.sh --check

demo: up seed api
