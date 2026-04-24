.PHONY: dev migrate reset-db smoke logs-tail offline-validation check-doc-links export-source pre-m8-gates test test-full test-coverage

PYTHON ?= python
DB_PATH ?= state/workflow.db

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
	$(PYTHON) -m infra.scripts.offline_validation --skip-offline-probe

check-doc-links:
	$(PYTHON) -m infra.scripts.check_doc_links

export-source:
	$(PYTHON) -m infra.scripts.export_source_package --dry-run

pre-m8-gates:
	$(PYTHON) -m infra.scripts.pre_m8_gates

test:
	pytest -q

test-full:
	pytest -q --run-slow

test-coverage:
	pytest -q --run-slow --cov=packages --cov=apps --cov-report=term-missing --cov-fail-under=70
