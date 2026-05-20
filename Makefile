.PHONY: help install lint fmt typecheck test up down logs migrate seed worker api

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n",$$1,$$2}'

install: ## Install Python deps
	pip install -r requirements.txt

lint: ## Ruff lint
	ruff check backend ml workers tests

fmt: ## Ruff format
	ruff format backend ml workers tests

typecheck: ## mypy
	mypy backend ml workers

test: ## Run tests
	pytest -q

up: ## Start full local stack
	docker compose up -d

down: ## Stop stack
	docker compose down

logs: ## Tail api + worker logs
	docker compose logs -f api worker

migrate: ## Apply DB migrations
	alembic upgrade head

seed: ## Seed an initial admin user
	python -m backend.scripts.seed

api: ## Run API locally (reload)
	uvicorn backend.app.main:app --reload --port 8000

worker: ## Run a Celery worker locally
	celery -A workers.celery_app.celery_app worker -l info -Q inference,export,active_learning
