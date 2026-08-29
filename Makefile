.PHONY: install up down seed api test catalog-validate osint-validate identify-validate batch2-validate validate-all validate-all-live generate-validate generate-scale generate-slow defend-fit defend-gtest defend-gdev defend-loop-m defend-remediate defend-validate stage4-saml-d

PYTHONPATH ?= $(CURDIR)
export PYTHONPATH
export PYTHONUNBUFFERED ?= 1

ifneq (,$(wildcard $(CURDIR)/.venv/Scripts/python.exe))
PY := $(CURDIR)/.venv/Scripts/python.exe
else ifneq (,$(wildcard $(CURDIR)/.venv/bin/python))
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
	$(PY) -c "from packages.osint.fixtures import load_fixture_documents; d=load_fixture_documents(); print(f'fixtures={len(d)}'); assert len(d)>=3"
	$(PY) -c "from packages.osint.collect import collect_candidate_urls; u=collect_candidate_urls(); print(f'airplane_urls={len(u)}'); assert len(u)>=2"

identify-validate:
	$(VALIDATE_ENV) $(PY) -c "from apps.api.db import init_db; from packages.agents.identify_graph import run_identify_graph; init_db(); r=run_identify_graph('make-validate'); print(r['run_id'], len(r.get('proposed_specs') or [])); assert r['run_id']=='make-validate'"

batch2-validate: osint-validate identify-validate test

batch3-validate:
	$(VALIDATE_ENV) $(PY) -c 'from apps.api.db import init_db; from packages.agents.identify_graph import run_identify_graph; init_db(); r=run_identify_graph("make-b3"); print("proposed", len(r.get("proposed_specs") or [])); assert len(r.get("proposed_specs") or [])>=1'

generate-validate:
	$(PY) -c "from pathlib import Path; from apps.api.env import load_project_env; load_project_env(); from apps.api.db import SessionLocal, init_db; from apps.api.seed import seed_catalog; from packages.sim.runner import run_population; init_db(); seed_catalog(reset=True); db=SessionLocal(); r=run_population(db, vector_id='t13-upi-impersonation-app', n_customers=16, n_merchants=8, sim_days=40, world_seed=42, pin=True, runs_dir=Path('data/runs')); db.close(); assert r['event_count']>1 and 'simulatable_signals' not in r and r['counts_by_label_family'].get('app_fraud',0)>=3; assert r['fidelity']['pass'] is True, r['fidelity']; print(r['parquet_path'], r.get('split_path'), r['counts_by_label_family'], r['fidelity']['pass'])"

# Phase 4 scale reference target (full mix, no vector_id pin)
# Expected scale: 2400 customers x 120 merchants x 90 sim_days (~50k-70k events, ~1-2 min wall clock)
generate-scale:
	$(PY) -c "from pathlib import Path; from apps.api.env import load_project_env; load_project_env(); from apps.api.db import SessionLocal, init_db; from apps.api.seed import seed_catalog; from packages.sim.runner import run_population; init_db(); seed_catalog(reset=True); db=SessionLocal(); r=run_population(db, run_id='make-scale-fullmix', n_customers=2400, n_merchants=120, sim_days=90, world_seed=42, pin=True, runs_dir=Path('data/runs')); db.close(); assert r['event_count']>50000, r['event_count']; assert 'simulatable_signals' not in r; assert r['fidelity']['pass'] is True, r['fidelity']; print('scale OK', r['event_count'], r['parquet_path'], r['fidelity']['pass'])"

defend-fit:
	PYTHONUNBUFFERED=1 $(PY) -c "from packages.eval.fit import fit_champion; r=fit_champion('make-scale-fullmix', world_seed=42); print('fit OK', r['run_id'], r['metrics']['recipe_hash'])"

defend-gtest:
	PYTHONUNBUFFERED=1 $(PY) -c "import json; from pathlib import Path; from apps.api.env import load_project_env; load_project_env(); from apps.api.db import SessionLocal, init_db; from apps.api.seed import seed_catalog; from packages.sim.runner import run_population; from packages.eval.fit import score_run; init_db(); seed_catalog(reset=True); db=SessionLocal(); sidecar = json.loads(Path('data/runs/make-scale-fullmix/sidecar.json').read_text()) if Path('data/runs/make-scale-fullmix/sidecar.json').is_file() else {}; nc = sidecar.get('n_customers', 2400); nm = sidecar.get('n_merchants', 120); sd = sidecar.get('sim_days', 90); r=run_population(db, run_id='make-gtest', world_seed=43, n_customers=nc, n_merchants=nm, sim_days=sd, pin=True, runs_dir=Path('data/runs')); db.close(); s=score_run('make-gtest', model_run_id='make-scale-fullmix', all_rows=True); print('gtest OK', s['run_id'], s.get('model_freeze_id'), s['metrics'].get('binary_ap'), s['metrics']['ap_by_family'])"

defend-gdev:
	PYTHONUNBUFFERED=1 $(PY) -c "import json; from pathlib import Path; from apps.api.env import load_project_env; load_project_env(); from apps.api.db import SessionLocal, init_db; from apps.api.seed import seed_catalog; from packages.sim.runner import run_population; from packages.eval.fit import score_run; init_db(); seed_catalog(reset=True); db=SessionLocal(); sidecar = json.loads(Path('data/runs/make-scale-fullmix/sidecar.json').read_text()) if Path('data/runs/make-scale-fullmix/sidecar.json').is_file() else {}; nc = sidecar.get('n_customers', 2400); nm = sidecar.get('n_merchants', 120); sd = sidecar.get('sim_days', 90); r=run_population(db, run_id='make-gdev', world_seed=44, n_customers=nc, n_merchants=nm, sim_days=sd, pin=True, runs_dir=Path('data/runs')); db.close(); s=score_run('make-gdev', model_run_id='make-scale-fullmix', all_rows=True); print('gdev OK', s['run_id'], s['metrics']['ap_by_family'])"

defend-loop-m:
	@echo "Loop M requires POST /defend/loop-m with body:"
	@echo '{"run_id":"v1-train-46","miss_family":"<family>","gtest_seed":48,"family_chosen_from_slice":"gdev44","n_customers":2400,"n_merchants":120,"sim_days":90,"pin":true}'

generate-v1-train-46:
	$(PY) -c "from pathlib import Path; from apps.api.env import load_project_env; load_project_env(); from apps.api.db import SessionLocal, init_db; from apps.api.seed import seed_catalog; from packages.sim.runner import run_population; init_db(); seed_catalog(reset=True); db=SessionLocal(); r=run_population(db, run_id='v1-train-46', n_customers=2400, n_merchants=120, sim_days=90, world_seed=46, pin=True, runs_dir=Path('data/runs')); db.close(); print('v1 train 46 OK', r['event_count'])"

generate-v1-gdev-47:
	$(PY) -c "from pathlib import Path; from apps.api.env import load_project_env; load_project_env(); from apps.api.db import SessionLocal, init_db; from apps.api.seed import seed_catalog; from packages.sim.runner import run_population; init_db(); seed_catalog(reset=True); db=SessionLocal(); r=run_population(db, run_id='v1-gdev-47', n_customers=2400, n_merchants=120, sim_days=90, world_seed=47, pin=True, runs_dir=Path('data/runs')); db.close(); print('v1 gdev 47 OK', r['event_count'])"

generate-v1-gtest-48:
	$(PY) -c "from pathlib import Path; from apps.api.env import load_project_env; load_project_env(); from apps.api.db import SessionLocal, init_db; from apps.api.seed import seed_catalog; from packages.sim.runner import run_population; init_db(); seed_catalog(reset=True); db=SessionLocal(); r=run_population(db, run_id='v1-gtest-48', n_customers=2400, n_merchants=120, sim_days=90, world_seed=48, pin=True, runs_dir=Path('data/runs')); db.close(); print('v1 gtest 48 OK', r['event_count'])"

stage4-saml-d:
	OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONUNBUFFERED=1 nice -n 15 $(PY) -c "from packages.eval.saml_d import score_saml_d, write_stage4_artifacts; b=score_saml_d(); p=write_stage4_artifacts(b); print(b.get('status'), p, b.get('tpr_at_fpr'))"

defend-remediate:
	@echo "Phase 8 Loop T remediation cycle requires a configured LLM provider (AEGIS_LLM_*) and G-dev + train runs."
	@echo "Run: $(PY) -c \"from apps.api.env import load_project_env; load_project_env(); from packages.agents.llm.config import build_provider, load_provider_config; from packages.eval.loop_t_orchestrator import run_remediation_cycle; p=build_provider(load_provider_config()); print(run_remediation_cycle(gdev_run_id='make-gdev', train_run_id='make-scale-fullmix', provider=p))\""
	@echo "Kill switch: remediation.orchestrator_enabled in models/features.json (off = no-op)."

generate-slow:
	$(PY) -m pytest tests/test_sim_calibrator.py tests/test_sim_slow.py -q --tb=short

defend-validate:
	$(PY) -c "from apps.api.env import load_project_env; load_project_env(); from apps.api.db import SessionLocal, init_db; from apps.api.seed import seed_catalog; from packages.policy.coverage import build_coverage_map; init_db(); seed_catalog(reset=True); db=SessionLocal(); m=build_coverage_map(db); db.close(); assert m['technique_count']==24"

handoff-validate: generate-validate defend-validate

validate-all:
	@echo "=== [1/6] catalog ===" && $(MAKE) catalog-validate
	@echo "=== [2/6] osint (airplane) ===" && $(MAKE) osint-validate
	@echo "=== [3/6] postgres + seed ===" && $(MAKE) up seed
	@echo "=== [4/6] generate + defend handoff ===" && $(MAKE) handoff-validate
	@echo "=== [5/6] identify graph (offline, real librarian) ===" && $(VALIDATE_ENV) $(PY) -c 'from apps.api.db import init_db; from packages.agents.identify_graph import run_identify_graph; init_db(); r=run_identify_graph("validate-all"); assert len(r.get("candidate_urls") or [])>=1; assert len(r.get("proposed_specs") or [])>=1; print("identify OK", r["run_id"], "proposed", len(r["proposed_specs"]))'
	@echo "=== [6/6] pytest ===" && $(VALIDATE_ENV) $(PY) -m pytest tests/ -q -m "not live_llm and not live_identify"
	@echo "=== ALL GATES PASSED ==="

# Unix: ./run.sh --check. Windows PowerShell: pwsh -File scripts/run.ps1 --check
ifeq ($(OS),Windows_NT)
validate-all-live:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run.ps1 --check
else
validate-all-live:
	./run.sh --check
endif

demo: up seed api
