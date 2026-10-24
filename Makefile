.PHONY: test lint build validate

PYTHON ?= python
NPM ?= npm

test:
	$(MAKE) backend-test frontend-test

backend-test:
	cd backend && $(PYTHON) -m pytest -q

frontend-test:
	cd frontend && $(NPM) test -- --run

lint:
	cd frontend && $(NPM) run lint

build:
	cd frontend && $(NPM) run build

validate:
	$(MAKE) lint test build
