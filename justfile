set dotenv-load := false
IS_PROD := env_var_or_default("IS_PROD", "")
COMPOSE_FILE := "--file=docker-compose.yml" + (
    if IS_PROD != "true" {" --file=docker-compose.override.yml"} else {""}
)
DC := "docker-compose " + COMPOSE_FILE
RUN := "run --rm cli"
# Force just to hand down positional arguments so quoted arguments with spaces are
# handled appropriately
set positional-arguments


# Show all available recipes
default:
  @just --list --unsorted

# Create a .env file if it doesn't exist
env:
    @([ ! -f .env ] && touch .env) || true

# Build the containers
build: env
	{{ DC }} build

# Spin up all (or one) service
up service="":
	{{ DC }} up -d {{ service }}

# Tear down containers
down:
	{{ DC }} down

# Pull all docker images
pull:
    {{ DC }} pull

# Attach logs to all (or the specified) services
logs *args:
	{{ DC }} logs -f {{ args }}

# Run a command on a provided service
run *args:
	{{ DC }} {{ RUN }} "$@"

# Verify all numbers
verify:
	{{ DC }} {{ RUN }} signal-scanner-bot-verify

# Register a new number
register:
	{{ DC }} {{ RUN }} ./register-number.sh

# Static checks
lint:
	pre-commit run --all-files
