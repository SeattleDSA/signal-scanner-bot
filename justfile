set dotenv-load := false
DC := "docker-compose"
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

# Production deployment
deploy:
	{{ DC }} -f docker-compose-prod.yml up -d

# Verify all numbers
verify:
	{{ DC }} -f docker-compose-prod.yml {{ RUN }} signal-scanner-bot-verify

# Register a new number
register file="docker-compose.yml":
	{{ DC }} -f {{ file }} {{ RUN }} ./register-number.sh

# Static checks
static:
	pre-commit run --all-files