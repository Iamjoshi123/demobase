.PHONY: dev backend frontend seed seed-acceptance test test-backend test-frontend test-integration test-e2e test-acceptance test-all coverage coverage-backend coverage-frontend lint docker-up docker-down install typecheck sanity livekit-up livekit-down

PYTHON ?= C:/Python313/python.exe

install:
	cd backend && $(PYTHON) -m pip install -r requirements.txt
	cd frontend && npm install

dev:
	$(MAKE) backend &
	$(MAKE) frontend &
	wait

backend:
	cd backend && $(PYTHON) run.py

frontend:
	cd frontend && npm run dev

seed:
	cd backend && $(PYTHON) -m app.seed

seed-acceptance:
	cd backend && $(PYTHON) -m app.seed

test:
	cd backend && $(PYTHON) -m pytest
	cd frontend && npm run test:unit

test-integration:
	cd backend && $(PYTHON) -m pytest tests/test_integration_api_flows.py tests/test_browser_integration.py tests/test_live_session_api.py tests/test_voice_contract.py
	cd frontend && npm run test:integration

test-e2e:
	cd frontend && npm run test:e2e

test-acceptance:
	cd frontend && npm run test:acceptance

test-all:
	$(MAKE) sanity
	$(MAKE) test
	$(MAKE) test-integration
	$(MAKE) test-e2e

test-backend:
	cd backend && $(PYTHON) -m pytest

test-frontend:
	cd frontend && npm run test:unit

coverage:
	cd backend && $(PYTHON) -m pytest
	cd frontend && npm run test:coverage

coverage-backend:
	cd backend && $(PYTHON) -m pytest

coverage-frontend:
	cd frontend && npm run test:coverage

typecheck:
	cd frontend && npm run typecheck

sanity:
	cd backend && $(PYTHON) -c "import app.main, app.seed, app.services.planner, app.browser.executor, app.voice.session"
	cd frontend && npm run lint
	cd frontend && npm run typecheck
	cd frontend && npm run build

lint:
	cd backend && $(PYTHON) -m ruff check app/
	cd frontend && npm run lint

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

livekit-up:
	docker compose up -d livekit

livekit-down:
	docker compose stop livekit

db-reset:
	cd backend && rm -f agentic_demo_brain.db && $(PYTHON) -m app.seed
