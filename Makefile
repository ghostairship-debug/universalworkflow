.PHONY: dev migrate reset-db smoke logs-tail

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
