set dotenv-load := false
IS_PROD := env_var_or_default("IS_PROD", "")
COMPOSE_FILE := if IS_PROD == "true" {"-f docker-compose-prod.yml "} else {""}
DC := "docker-compose " + COMPOSE_FILE
RUN := "run --rm cli"

# Build the containers
build:
	{{ DC }} build

# Spin up all (or one) service
up service="":
	{{ DC }} up -d {{ service }}

# Tear down containers
down:
	{{ DC }} down

# Verify all numbers
verify:
	{{ DC }} {{ RUN }} signal-scanner-bot-verify

# Register a new number
register:
	{{ DC }} {{ RUN }} ./register-number.sh

# Static checks
static:
	pre-commit run --all-files
