.PHONY: up down logs migrate-check test lint typecheck audit check

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=100 backend frontend

migrate-check:
	docker compose exec -T backend alembic check

test:
	docker compose exec -T backend python -m pytest app/tests -q

lint:
	docker compose exec -T backend python -m ruff check app
	docker compose exec -T backend python -m compileall -q alembic
	docker compose exec -T frontend pnpm lint

typecheck:
	docker compose exec -T backend python -m mypy app
	docker compose exec -T frontend pnpm typecheck

audit:
	docker compose exec -T backend python -m pip_audit --skip-editable
	docker compose exec -T frontend pnpm audit --prod

check: migrate-check test lint typecheck
