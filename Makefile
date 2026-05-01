PORT ?= 8080
BUILD_IMAGE_VERSION_TAG ?= latest
ARTIFACTORY_REGION ?= us-east1
PROJECT_ID_DEV ?= blitzy-platform-stage
REPOSITORY ?= gcf-artifacts
IMAGE_NAME ?= archie-job-reverse-file-mapper
ENV ?= qa

# Full image path
IMAGE_PATH := $(ARTIFACTORY_REGION)-docker.pkg.dev/$(PROJECT_ID_DEV)/$(REPOSITORY)/$(IMAGE_NAME):$(BUILD_IMAGE_VERSION_TAG)

all: build

install-deployment-utils:
	python -m pip install --upgrade pip keyrings.google-artifactregistry-auth toml
	@echo "Installing deployment utils"
	pip install --extra-index-url https://us-east1-python.pkg.dev/$(PROJECT_ID_DEV)/python-us-east1/simple deployment-utils


init:
	pip install -r requirements.txt

build:
	@if [ "$(GITHUB_ACTIONS)" = "true" ]; then \
         DOCKER_BUILDKIT=1 docker build \
            --secret id=google_credentials,src=$$GOOGLE_APPLICATION_CREDENTIALS \
            -t $(IMAGE_PATH) .; \
    else \
        DOCKER_BUILDKIT=1 docker build \
            --secret id=google_credentials,src=$$SERVICE_ACCOUNT_KEY_PATH \
            -t $(IMAGE_PATH) .; \
    fi
	@echo "Building docker image with tag $(IMAGE_PATH)"

clean:
	docker rmi -f $(docker images -f "dangling=true" -q)

# Deploy the container image as a Cloud Run *Service* (NOT a Job).
# Under the Flask migration the deployment target is a long-running HTTP
# service that receives requests at /api/generate, /api/update, /health,
# and /api/traces/<run_id>. The internal `deploy-to-cloud-run` utility
# accepts `--type service` to drive `gcloud run services deploy` with
# the YAML manifest and per-environment variable overrides.
deploy:
	@if [ -n "$(tag)" ]; then \
		echo "Deploying with tag from command line: $(tag)"; \
		deploy-to-cloud-run --type service --image-tag=$(tag) --yaml-file=$(YAML_FILE) --vars-file=env_config/env-$(ENV).yaml --skip-confirmation; \
	else \
		echo "Deploying with IMAGE_PATH: $(IMAGE_PATH)"; \
		deploy-to-cloud-run --type service --image-tag=$(IMAGE_PATH) --yaml-file=$(YAML_FILE) --vars-file=env_config/env-$(ENV).yaml --skip-confirmation; \
	fi

# Local Flask development server. Uses run.py which calls
# `app.run(debug=True, port=8080)` for hot reloading and verbose
# error pages. Suitable for iterating on routes, services, and
# pipeline orchestration outside of Docker.
run-dev:
	python run.py

# Local Gunicorn production server. Mirrors the Cloud Run container
# command (--workers 2, --timeout 3600) so developers can validate
# WSGI compatibility, async view dispatch, and long-running pipeline
# behavior in a production-like configuration before deploying.
run-prod:
	gunicorn --bind 0.0.0.0:$(PORT) --workers 2 --timeout 3600 wsgi:app

# Run the full pytest suite under tests/ with verbose output. Tests
# cover route handlers (generate, update, health, traces) and the
# pipeline_service orchestration layer with mocked external services.
test:
	pytest tests/ -v

# Run pytest with coverage measurement against the `app` package.
# Emits both an HTML report (htmlcov/) for browser inspection and a
# terminal summary, enabling local coverage gates before CI runs.
test-cov:
	pytest --cov=app --cov-report=html --cov-report=term tests/


.PHONY: init deploy build clean run-dev run-prod test test-cov install-deployment-utils
