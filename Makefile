SHELL := /bin/bash

.PHONY: fmt lint test green up down logs ps migrate reset-db seed

fmt:
	ruff format .

lint:
	ruff check .

test:
	pytest -q

# ---------- Docker ----------
ps:
	docker compose ps

logs:
	docker compose logs --tail=200

down:
	docker compose down

# WARNING: wipes DB + redis volumes (clean slate)
reset-db:
	docker compose down -v
	docker compose up -d postgres
	docker compose run --rm migrate
	docker compose up -d

migrate:
	docker compose up -d postgres
	docker compose run --rm migrate

up:
	docker compose up -d

green:
	python scripts/wait_health.py