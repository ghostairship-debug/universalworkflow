.PHONY: dev migrate reset-db smoke logs-tail offline-validation check-doc-links doc-command-smoke doctor-strict export-source pre-m8-gates test test-unit test-fast test-core test-integration test-full test-coverage

PYTHON ?= python
DB_PATH ?= state/workflow.db
WORKSPACE_ROOT ?= $(CURDIR)
PYTEST_BASETEMP ?= $(shell $(PYTHON) -c "from pathlib import Path; import tempfile; root=Path('state/.pytest-tmp-workflow'); root.mkdir(parents=True, exist_ok=True); print(tempfile.mkdtemp(prefix='run-', dir=root).replace('\\\\','/'))")

dev:
	$(PYTHON) -m infra.scripts.manage --db-path $(DB_PATH) dev

migrate:
	$(PYTHON) -m infra.scripts.manage --db-path $(DB_PATH) migrate

reset-db:
	$(PYTHON) -m infra.scripts.manage --db-path $(DB_PATH) reset-db

smoke:
	$(PYTHON) -m infra.scripts.manage --db-path $(DB_PATH) smoke

logs-tail:
	$(PYTHON) -m infra.scripts.manage --db-path $(DB_PATH) logs-tail

offline-validation:
	$(PYTHON) -m infra.scripts.offline_validation --suite quick --skip-offline-probe

check-doc-links:
	$(PYTHON) -m infra.scripts.check_doc_links

doc-command-smoke:
	$(PYTHON) -m infra.scripts.check_doc_links
	$(PYTHON) -m infra.scripts.offline_validation --suite quick --skip-offline-probe

doctor-strict:
	$(PYTHON) -c "from pathlib import Path; Path('state').mkdir(exist_ok=True)"
	workflowctl --db-path $(DB_PATH) --workspace-root "$(WORKSPACE_ROOT)" doctor --strict

export-source:
	$(PYTHON) -m infra.scripts.export_source_package --dry-run

pre-m8-gates:
	$(PYTHON) -m infra.scripts.pre_m8_gates

test:
	pytest -q --basetemp=$(PYTEST_BASETEMP)

test-unit:
	pytest -q tests/test_contracts.py tests/test_repositories.py tests/test_operator_action_receipt.py tests/test_repo_mutation_atomicity.py tests/test_workspace_root.py tests/test_service_decomposition.py tests/test_scheduler_flag_off_isolation.py --tb=short --durations=20 --basetemp=$(PYTEST_BASETEMP)

test-fast:
	pytest -q --tb=short --durations=20 --basetemp=$(PYTEST_BASETEMP)

test-core:
	pytest -q tests/test_contracts.py tests/test_repositories.py tests/test_doctor.py tests/test_api_startup.py tests/test_scheduler_flag_off_isolation.py tests/test_service_decomposition.py tests/test_runtime_boundary.py tests/test_m41_capabilities.py --tb=short --durations=20 --basetemp=$(PYTEST_BASETEMP)

test-integration:
	pytest -q tests/test_api.py tests/test_cli.py tests/test_remote_worker_api.py tests/test_scheduler_authority_api.py tests/test_web_ui.py --tb=short --durations=20 --basetemp=$(PYTEST_BASETEMP)

test-full:
	pytest -q --run-slow --basetemp=$(PYTEST_BASETEMP)

test-coverage:
	pytest -q --run-slow --cov=packages --cov=apps --cov-report=term-missing --cov-fail-under=70 --basetemp=$(PYTEST_BASETEMP)
