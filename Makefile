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

green: fmt lint test
	@echo "Local checks passed ✅"
	@echo "Running docker green path..."
	docker compose down -v
	docker compose up -d postgres
	docker compose run --rm migrate
	docker compose up -d
	python - <<'PY'
import time, sys, urllib.request
urls=["http://127.0.0.1:8000/health","http://127.0.0.1:8004/health","http://127.0.0.1:8005/health"]
deadline=time.time()+60
last=None
while time.time()<deadline:
    ok=True
    for u in urls:
        try:
            r=urllib.request.urlopen(u,timeout=2)
            ok = ok and (r.status==200)
        except Exception as e:
            ok=False
            last=(u,repr(e))
    if ok:
        print("DOCKER GREEN ✅")
        sys.exit(0)
    time.sleep(2)
print("DOCKER NOT GREEN ❌", last)
sys.exit(1)
PY