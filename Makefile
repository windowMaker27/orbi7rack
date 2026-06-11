.PHONY: up up-mobile down build migrate makemigrations seed seed-demo test shell logs restart re re-mobile

# ── Docker ────────────────────────────────────────────────
up:
	docker compose up -d

up-mobile:
	docker compose -f docker-compose.yml -f docker-compose.mobile.yml up -d

down:
	docker compose down

re:
	docker compose down
	docker compose up -d

re-mobile:
	docker compose down
	docker compose -f docker-compose.yml -f docker-compose.mobile.yml up -d

build:
	docker compose build

setup: build up
	sleep 3
	docker compose exec backend python manage.py makemigrations users tracking
	docker compose exec backend python manage.py migrate
	@echo "✅ Orbi7rack prêt sur http://localhost:3000"

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

seed-demo:
	docker compose exec backend python scripts/seed_demo.py

reset-db:
	bash scripts/reset_db.sh

backup-db:
	bash scripts/backup_db.sh
