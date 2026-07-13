.PHONY: bootstrap test lint audit build up down smoke e2e

bootstrap:
	cd backend && uv sync --locked --extra dev --python 3.12
	cd frontend && npm ci

test:
	cd backend && uv run --locked --extra dev pytest -q
	cd frontend && npm test

lint:
	cd backend && uv run --locked --extra dev ruff check app tests
	cd frontend && npm run build -- --emptyOutDir=false

audit:
	cd backend && uv run --locked --extra dev pip-audit
	cd frontend && npm audit --audit-level=high

build:
	cd frontend && npm run build
	docker compose build

up:
	docker compose up -d --build

down:
	docker compose down

smoke:
	@i=0; until curl --fail --silent http://127.0.0.1:8000/healthz; do i=$$((i+1)); test $$i -lt 30; sleep 1; done
	@i=0; until curl --fail --silent http://127.0.0.1:8000/readyz; do i=$$((i+1)); test $$i -lt 30; sleep 1; done
	@i=0; until curl --fail --silent http://127.0.0.1:5173/ | grep -q "硫衡证据台"; do i=$$((i+1)); test $$i -lt 30; sleep 1; done
	curl --fail --silent http://127.0.0.1:8000/openapi.json | grep -q 'certificates'

e2e:
	cd frontend && npx playwright install chromium && npm run e2e
