
COMPOSE := docker compose
COMPOSE_FILE := docker-compose.yml
.DEFAULT_GOAL := help

.PHONY: help
help:
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ \
		{printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ----------------------------
# Core Redis
# ----------------------------

.PHONY: up
up: ## Start redis only
	$(COMPOSE) -f $(COMPOSE_FILE) up -d redis

.PHONY: down
down: ## Stop all redis services
	$(COMPOSE) -f $(COMPOSE_FILE) down

.PHONY: restart
restart: down up # Restart redis

.PHONY: logs
logs: ## Tail redis logs
	$(COMPOSE) -f $(COMPOSE_FILE) logs -f redis

.PHONY: pull
pull: ## Pull redis images
	$(COMPOSE) -f $(COMPOSE_FILE) pull

# ----------------------------
# RedisInsight (UI)
# ----------------------------

.PHONY: ui-up
ui-up: ## Start redis + redisinsight
	$(COMPOSE) -f $(COMPOSE_FILE) --profile ui up -d

.PHONY: ui-down
ui-down: ## Stop redisinsight only
	$(COMPOSE) -f $(COMPOSE_FILE) stop redisinsight



