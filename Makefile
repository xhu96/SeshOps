# ─────────────────────────────────────────────────────────────────────────────
# SeshOps — IT Operations Copilot
# ─────────────────────────────────────────────────────────────────────────────

install:
	pip install uv
	uv sync

DOCKER_COMPOSE ?= docker-compose

# ── Environment management ──────────────────────────────────────────────────

set-env:
	@if [ -z "$(ENV)" ]; then \
		echo "Usage: make set-env ENV=development|staging|production|test"; \
		exit 1; \
	fi
	@if [ "$(ENV)" != "development" ] && [ "$(ENV)" != "staging" ] && [ "$(ENV)" != "production" ] && [ "$(ENV)" != "test" ]; then \
		echo "ENV must be one of: development, staging, production, test"; \
		exit 1; \
	fi
	@echo "Setting SeshOps environment to $(ENV)"
	@bash -c "source scripts/set_env.sh $(ENV)"

# ── Local development ──────────────────────────────────────────────────────

dev:
	@echo "Starting SeshOps in development mode"
	@bash -c "source scripts/set_env.sh development && uv run uvicorn app.main:app --reload --port 8000 --loop uvloop"

prod:
	@echo "Starting SeshOps in production mode"
	@bash -c "source scripts/set_env.sh production && ./.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --loop uvloop"

staging:
	@echo "Starting SeshOps in staging mode"
	@bash -c "source scripts/set_env.sh staging && ./.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --loop uvloop"

# ── Testing ─────────────────────────────────────────────────────────────────

test:
	@echo "Running SeshOps test suite"
	@APP_ENV=test JWT_SECRET_KEY=test-secret OPENAI_API_KEY=sk-test uv run pytest tests/ -v

# ── Evaluation ──────────────────────────────────────────────────────────────

eval:
	@echo "Running SeshOps evaluation (interactive)"
	@bash -c "source scripts/set_env.sh $${ENV:-development} && python -m evals.main --interactive"

eval-quick:
	@echo "Running SeshOps evaluation (quick)"
	@bash -c "source scripts/set_env.sh $${ENV:-development} && python -m evals.main --quick"

# ── Linting & formatting ───────────────────────────────────────────────────

lint:
	ruff check .

format:
	ruff format .

clean:
	rm -rf .venv __pycache__ .pytest_cache seshops.db

# ── Docker ──────────────────────────────────────────────────────────────────

docker-build:
	docker build -t seshops .

docker-build-env:
	@if [ -z "$(ENV)" ]; then \
		echo "Usage: make docker-build-env ENV=development|staging|production"; \
		exit 1; \
	fi
	@./scripts/build-docker.sh $(ENV)

docker-run:
	@ENV_FILE=.env.development; \
	if [ ! -f $$ENV_FILE ]; then \
		echo "$$ENV_FILE not found — create it first."; \
		exit 1; \
	fi; \
	APP_ENV=development $(DOCKER_COMPOSE) --env-file $$ENV_FILE up -d --build db app

docker-run-env:
	@if [ -z "$(ENV)" ]; then \
		echo "Usage: make docker-run-env ENV=development|staging|production"; \
		exit 1; \
	fi
	@ENV_FILE=.env.$(ENV); \
	if [ ! -f $$ENV_FILE ]; then \
		echo "$$ENV_FILE not found — create it first."; \
		exit 1; \
	fi; \
	APP_ENV=$(ENV) $(DOCKER_COMPOSE) --env-file $$ENV_FILE up -d --build db app

docker-logs:
	@if [ -z "$(ENV)" ]; then \
		echo "Usage: make docker-logs ENV=development|staging|production"; \
		exit 1; \
	fi
	@ENV_FILE=.env.$(ENV); \
	APP_ENV=$(ENV) $(DOCKER_COMPOSE) --env-file $$ENV_FILE logs -f app db

docker-stop:
	@if [ -z "$(ENV)" ]; then \
		echo "Usage: make docker-stop ENV=development|staging|production"; \
		exit 1; \
	fi
	@ENV_FILE=.env.$(ENV); \
	APP_ENV=$(ENV) $(DOCKER_COMPOSE) --env-file $$ENV_FILE down

# ── Docker Compose full stack ───────────────────────────────────────────────

docker-compose-up:
	@if [ -z "$(ENV)" ]; then \
		echo "Usage: make docker-compose-up ENV=development|staging|production"; \
		exit 1; \
	fi
	@ENV_FILE=.env.$(ENV); \
	APP_ENV=$(ENV) $(DOCKER_COMPOSE) --env-file $$ENV_FILE up -d

docker-compose-down:
	@if [ -z "$(ENV)" ]; then \
		echo "Usage: make docker-compose-down ENV=development|staging|production"; \
		exit 1; \
	fi
	@ENV_FILE=.env.$(ENV); \
	APP_ENV=$(ENV) $(DOCKER_COMPOSE) --env-file $$ENV_FILE down

docker-compose-logs:
	@if [ -z "$(ENV)" ]; then \
		echo "Usage: make docker-compose-logs ENV=development|staging|production"; \
		exit 1; \
	fi
	@ENV_FILE=.env.$(ENV); \
	APP_ENV=$(ENV) $(DOCKER_COMPOSE) --env-file $$ENV_FILE logs -f

# ── Help ────────────────────────────────────────────────────────────────────

help:
	@echo "SeshOps — IT Operations Copilot"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Development:"
	@echo "  install        Install dependencies via uv"
	@echo "  dev            Start SeshOps in development mode (hot-reload)"
	@echo "  prod           Start SeshOps in production mode"
	@echo "  staging        Start SeshOps in staging mode"
	@echo "  test           Run the test suite"
	@echo ""
	@echo "Quality:"
	@echo "  lint           Run ruff linter"
	@echo "  format         Auto-format with ruff"
	@echo "  clean          Remove caches and local DB"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build                Build the SeshOps image"
	@echo "  docker-build-env ENV=...    Build for a specific environment"
	@echo "  docker-run                  Start SeshOps + DB (development)"
	@echo "  docker-run-env ENV=...      Start SeshOps + DB for environment"
	@echo "  docker-logs ENV=...         Tail container logs"
	@echo "  docker-stop ENV=...         Stop containers"
	@echo "  docker-compose-up ENV=...   Start full stack (API, Prometheus, Grafana)"
	@echo "  docker-compose-down ENV=... Stop full stack"
	@echo "  docker-compose-logs ENV=... Tail full stack logs"