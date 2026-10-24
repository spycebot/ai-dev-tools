# Card Catalog: one command each to run, test and stop the app.
#
#   make up          the full system (Postgres + migrations + app) in Docker → http://localhost:8000
#                    first run: asks for a login password and writes .env
#   make test        every test (backend unit + integration on PostgreSQL 17, frontend, lint) in Docker
#   make down        stop the stack (data is kept; `make clean` deletes it)
#
# Only Docker (with the Compose plugin) is needed for those. Native
# development, with hot reload, needs uv, Node.js 22 and, for the
# integration tests, PostgreSQL 17's binaries (see docs/testing.md):
#
#   make dev         backend on :8000 + Vite on :5173 (needs backend/.env)
#   make test-local  the same tests as `make test`, natively

SHELL := /bin/bash
COMPOSE := docker compose
UID_GID := $(shell id -u):$(shell id -g)

.PHONY: help up down logs clean test test-backend test-frontend dev test-local

help:
	@sed -n '3,14p' Makefile | sed 's/^# \{0,1\}//'

# --- Docker: what reviewers need --------------------------------------------

up: .env
	$(COMPOSE) up --build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f app

clean:
	$(COMPOSE) down -v

# First run only: build the image, prompt for a password inside it (nothing
# is echoed or printed), and write the hash and a fresh session key into .env.
# Written to a temp file first, so an aborted prompt leaves no half-made .env.
.env:
	docker build -q -t card-catalog:local . >/dev/null
	cp .env.example .env.tmp
	docker run --rm -it --user $(UID_GID) -v "$(CURDIR)/.env.tmp:/tmp/app.env" \
		card-catalog:local python scripts/set_password.py --env-file /tmp/app.env \
		|| { rm -f .env.tmp; exit 1; }
	mv .env.tmp .env

test: test-backend test-frontend
	@echo "All tests passed."

test-backend:
	docker build -q -f Dockerfile.test --target backend-test -t card-catalog-test:backend . >/dev/null
	docker run --rm card-catalog-test:backend

test-frontend:
	docker build -q -f Dockerfile.test --target frontend-test -t card-catalog-test:frontend . >/dev/null
	docker run --rm card-catalog-test:frontend

# --- Native development --------------------------------------------------------

dev:
	@test -f backend/.env || { echo "backend/.env is missing: see README → Authentication"; exit 1; }
	cd backend && uv sync -q
	cd frontend && npm install --no-fund --no-audit
	trap 'kill 0' EXIT; \
		(cd backend && uv run uvicorn app.main:app --reload) & \
		(cd frontend && npm run dev) & \
		wait

test-local:
	cd backend && uv run pytest
	cd frontend && npm test && npm run lint
