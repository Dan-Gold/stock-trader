# Makefile for Stock Trader application

COMPOSE_DEV_FILEPATH := ./docker/docker-compose.yml
# ENV_FILE_DEV := ./docker/dev.env
DOCKER_COMPOSE_COMMAND := docker compose -f $(COMPOSE_DEV_FILEPATH)

.DEFAULT_GOAL := help

# ----------------------------
# Help
# ----------------------------

.PHONY: help
help: ## Show available commands
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ \
		{printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ----------------------------
# Global setup
# ----------------------------

.PHONY: setup-docker-network
setup-docker-network: ## Create app_network if it doesn't exist
	@docker network ls | grep -q app_network || docker network create app_network

.PHONY: setup-pgadmin-volume
setup-pgadmin-volume: ## Create pgadmin-data volume if it doesn't exist
	@docker volume ls | grep -q pgadmin-data || docker volume create pgadmin-data


# ----------------------------
# Stock Trader Services
# ----------------------------

.PHONY: stock-trader-build
stock-trader-build: setup-docker-network ## Build stock-trader base image
	$(DOCKER_COMPOSE_COMMAND) build stock_trader_base


.PHONY: stock-trader-generate-migration
stock-trader-generate-migration: stock-trader-build stock-trader-migrate ## Generate a new alembic migration based on model changes
	$(DOCKER_COMPOSE_COMMAND) run --name temp_migration --rm=false stock_trader_db_migration \
		alembic -c /app/stock_trader/db/migrations/alembic.ini revision --autogenerate -m "$(MSG)"
	docker cp temp_migration:/app/stock_trader/db/migrations/versions/. ./src/stock_trader/db/migrations/versions/
	docker rm temp_migration


.PHONY: stock-trader-migrate
stock-trader-migrate: stock-trader-build ## Run database alembic migrations
	$(DOCKER_COMPOSE_COMMAND) run --rm stock_trader_db_init


.PHONY: stock-trader-up
stock-trader-up: stock-trader-build ## Start stock-trader service
	$(DOCKER_COMPOSE_COMMAND) up -d stock_trader_api


# ----------------------------
# Stock Trader Tests
# ----------------------------

.PHONY: stock-trader-tests-build
stock-trader-tests-build: setup-docker-network ## Build stock-trader test image
	$(DOCKER_COMPOSE_COMMAND) build stock_trader_tests


.PHONY: stock-trader-mypy
stock-trader-mypy: stock-trader-tests-build ## Run mypy type checks
	$(DOCKER_COMPOSE_COMMAND) run --rm stock_trader_tests mypy --config mypy.ini -p stock_trader -p tests


# ----------------------------
# Redis (delegation only)
# ----------------------------

.PHONY: redis-up
redis-up: ## Start redis
	$(MAKE) -C infra/redis up

.PHONY: redis-down
redis-down: ## Stop redis
	$(MAKE) -C infra/redis down

.PHONY: redis-restart
redis-restart: ## Restart redis
	$(MAKE) -C infra/redis restart

.PHONY: redis-logs
redis-logs: ## Tail redis logs
	$(MAKE) -C infra/redis logs

.PHONY: redis-pull
redis-pull: ## Pull redis images
	$(MAKE) -C infra/redis pull

.PHONY: redis-ui-up
redis-ui-up: ## Start redis insight UI
	$(MAKE) -C infra/redis ui-up

.PHONY: redis-ui-down
redis-ui-down: ## Stop redis insight UI
	$(MAKE) -C infra/redis ui-down

# ----------------------------
# PostgreSQL (delegation only)
# ----------------------------

.PHONY: postgres-up
postgres-up: setup-docker-network setup-pgadmin-volume ## Start postgres and pgadmin
	$(MAKE) -C infra/postgres up

.PHONY: postgres-down
postgres-down: ## Stop postgres and pgadmin
	$(MAKE) -C infra/postgres down

.PHONY: postgres-restart
postgres-restart: ## Restart postgres and pgadmin
	$(MAKE) -C infra/postgres restart

.PHONY: postgres-logs
postgres-logs: ## Tail postgres logs
	$(MAKE) -C infra/postgres logs

.PHONY: postgres-pull
postgres-pull: ## Pull postgres and pgadmin images
	$(MAKE) -C infra/postgres pull
