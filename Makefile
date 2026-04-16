.PHONY: up down build migrate makemigrations seed test shell logs restart

# ── Docker ────────────────────────────────────────────────
up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

setup: build up
	sleep 3
	docker compose exec backend python manage.py makemigrations users tracking
	docker compose exec backend python manage.py migrate
	@echo "✅ Orbi7rack prêt sur http://localhost:8000"

restart:
	docker compose restart backend

logs:
	docker compose logs -f backend

# ── Django ────────────────────────────────────────────────
migrate:
	docker compose exec backend python manage.py migrate

makemigrations:
	docker compose exec backend python manage.py makemigrations

shell:
	docker compose exec backend python manage.py shell

createsuperuser:
	docker compose exec backend python manage.py createsuperuser

# ── Tests ─────────────────────────────────────────────────
test:
	docker compose exec backend pytest -v

test-cov:
	docker compose exec backend pytest --cov=apps --cov-report=term-missing

# ── Utilitaires ───────────────────────────────────────────

seed:
	bash scripts/seed.sh

reset-db:
	bash scripts/reset_db.sh

backup-db:
	bash scripts/backup_db.sh
