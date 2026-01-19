ENV_FILE := database.env
COMPOSE := docker compose --env-file $(ENV_FILE)
COMPOSE_FILE := docker-compose.yml

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show available postgres commands
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ \
		{printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ----------------------------
# Postgres + pgAdmin
# ----------------------------

.PHONY: up
up: ## Start postgres and pgAdmin
	$(COMPOSE) -f $(COMPOSE_FILE) up -d

.PHONY: down
down: ## Stop postgres and pgAdmin
	$(COMPOSE) -f $(COMPOSE_FILE) down

.PHONY: restart
restart: down up ## Restart postgres and pgAdmin

.PHONY: logs
logs: ## Tail postgres logs
	$(COMPOSE) -f $(COMPOSE_FILE) logs -f postgres

.PHONY: pull
pull: ## Pull postgres and pgAdmin images
	$(COMPOSE) -f $(COMPOSE_FILE) pull
