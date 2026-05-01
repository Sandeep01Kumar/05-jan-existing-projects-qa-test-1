# archie-job-reverse-file-mapper — Flask Application

**Reverse File Mapper — AI-Powered Technical Specification Service**

`archie-job-reverse-file-mapper` is a Flask-based, AI-powered backend service in
the Blitzy platform that performs reverse file mapping for technical
specifications using a LangGraph multi-agent pipeline. It analyzes a source
repository's code graph (Neo4j), gathers contextual evidence through a multi-tool
agent pipeline, and produces a structured technical specification artifact
persisted to Google Cloud Storage with progress events streamed over Pub/Sub.

> **Refactoring note** — This service was refactored from a Cloud Run **Job**
> (PubSub-triggered, single-shot batch container that consumed the `EVENT_DATA`
> environment variable and exited) into a Cloud Run **Service**
> (HTTP-triggered, long-running Flask web application). The refactor is
> structural only — every feature, agent role, prompt, state field, external
> integration, multi-tenant isolation guarantee, error-handling layer, and
> Pub/Sub notification schema from the original implementation is preserved
> exactly. The only differences are the trigger mechanism (HTTP request body
> instead of `EVENT_DATA`), the deployment model (persistent service instead of
> one-shot job), and the code organization (modular Flask blueprints/services
> instead of a single `main.py` script).

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [API Endpoints](#api-endpoints)
3. [Local Development](#local-development)
4. [Testing](#testing)
5. [Deployment](#deployment)
6. [Environment Variables](#environment-variables)

---

## Architecture Overview

The application follows the standard Flask **application-factory** pattern with
**Blueprints** for modular route organization and a dedicated **service layer**
that isolates business logic from HTTP concerns. The original LangGraph
multi-agent pipeline is preserved in-place under `lib/reverse_mapper/`.

### Application factory — `app/__init__.py`

The factory function `create_app(config_name=None)` constructs and configures
the Flask application instance. It is responsible for:

- Loading environment-specific configuration (development, staging, QA,
  production) from `app/config.py`.
- Initializing Flask extensions through `app/extensions.py`
  (CORS, shared singletons such as the Pub/Sub publisher client and the
  `AdminStorageService`).
- Registering all route Blueprints declared in `app/routes/`.
- Wiring application-level error handlers and request lifecycle hooks
  (including resource cleanup via `@app.teardown_appcontext`).

The factory pattern enables environment-specific configuration, isolated test
clients, and clean startup/shutdown semantics.

### Blueprint-based routes — `app/routes/`

HTTP endpoints are organized into discrete Flask Blueprints, each owning a
single concern:

| Blueprint                     | Module                  | Concern                                                            |
| ----------------------------- | ----------------------- | ------------------------------------------------------------------ |
| `generate_bp`                 | `app/routes/generate.py`| `POST /api/generate` — full reverse-mapping pipeline trigger       |
| `update_bp`                   | `app/routes/update.py`  | `POST /api/update`   — incremental specification update trigger    |
| `health_bp`                   | `app/routes/health.py`  | `GET /health`, `GET /ready` — Cloud Run liveness/readiness probes  |
| `traces_bp`                   | `app/routes/traces.py`  | `GET /api/traces/<run_id>` — LangSmith cross-project trace lookup  |

### Service layer — `app/services/`

All business logic lives in the service layer so route handlers stay thin.
Services encapsulate the orchestration patterns previously embedded in
`main.py`:

| Service                | Module                                | Responsibility                                                                                              |
| ---------------------- | ------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `PipelineService`      | `app/services/pipeline_service.py`    | Constructs the LangGraph state graph, instantiates `ReverseMapperHelper`, and drives `app.astream(...)`     |
| `NotificationService`  | `app/services/notification_service.py`| Publishes `IN_PROGRESS`, `DONE`, and `ERROR` Pub/Sub events to the platform-events topic                    |
| `StorageService`       | `app/services/storage_service.py`     | Uploads generated specifications to GCS via `AdminStorageService` and computes the returned `tech_spec_url` |
| `TraceService`         | `app/services/trace_service.py`       | Cross-project LangSmith trace correlation (formerly `find_trace_runs.py`)                                   |

### Preserved core pipeline library — `lib/reverse_mapper/`

The LangGraph multi-agent pipeline is **preserved unchanged** under
`lib/reverse_mapper/`:

- `helper.py`  — `ReverseMapperHelper` class: builds the LangGraph
  `StateGraph`, defines all pipeline nodes, registers tools, configures the LLM
  models, and wires MCP tool servers.
- `state.py`   — `ReverseMapperState` `TypedDict`: the typed state object
  threaded through every node of the pipeline.
- `prompts.py` — Agent personas, system/user prompts for each agent role
  (Search, Author, Summarizer, Architect, Update), and document-mode
  definitions.

No business logic, agent configuration, prompt content, or state shape is
changed by the refactor.

### High-level request flow

```
HTTP POST /api/generate
        │
        ▼
 app/routes/generate.py            ──▶  validate JSON body (22 event fields)
        │
        ▼
 app/services/pipeline_service.py  ──▶  build helper, run app.astream(...)
        │
        ├──▶ NotificationService       (IN_PROGRESS / DONE / ERROR Pub/Sub events)
        ├──▶ StorageService            (GCS upload, tech_spec_url generation)
        └──▶ TraceService              (LangSmith trace correlation)
        │
        ▼
 lib/reverse_mapper/helper.py      ──▶  LangGraph multi-agent execution
```

---

## API Endpoints

All endpoints are mounted at the application root and accept/produce
`application/json`.

### `POST /api/generate`

Trigger reverse file mapping for a repository. This endpoint replaces the
original PubSub-triggered batch flow — it accepts the **same payload** that
was previously delivered through the `EVENT_DATA` environment variable.

- **Request body** — JSON object containing all event fields:
  `repo_name`, `repo_id`, `branch_id`, `branch_name`, `head_commit_hash`,
  `tech_spec_id`, `code_gen_id`, `company_id`, `team_id`, `user_id`,
  `org_name`, `project_id`, `job_id`, `dest_repo_name`, `dest_repo_id`,
  `dest_branch_id`, `dest_branch_name`, `is_new_dest_repo`, `change_mode`,
  `propagate`, `git_project_repo_id`, `resume`.
- **Response** — `202 Accepted` with the job tracking ID.

Example:

```bash
curl -X POST http://localhost:8080/api/generate \
     -H "Content-Type: application/json" \
     -d '{
           "repo_name": "example-repo",
           "repo_id": "repo-123",
           "branch_id": "branch-456",
           "branch_name": "main",
           "head_commit_hash": "abc1234",
           "tech_spec_id": "spec-789",
           "code_gen_id": "cg-001",
           "company_id": "company-1",
           "team_id": "team-1",
           "user_id": "user-1",
           "org_name": "example-org",
           "project_id": "project-1",
           "job_id": "job-001",
           "dest_repo_name": "example-repo",
           "dest_repo_id": "repo-123",
           "dest_branch_id": "branch-456",
           "dest_branch_name": "main",
           "is_new_dest_repo": false,
           "change_mode": "GENERATE",
           "propagate": false,
           "git_project_repo_id": "git-001",
           "resume": false
         }'
```

### `POST /api/update`

Trigger an **incremental specification update**. Accepts the same JSON payload
schema as `/api/generate` with `change_mode` set to the appropriate
update value. Returns `202 Accepted` with the job tracking ID.

### `GET /health`

Cloud Run **liveness** probe. Returns `200 OK` immediately without exercising
external dependencies, indicating the process is up.

```json
{ "status": "healthy" }
```

### `GET /ready`

Cloud Run **readiness** probe. Returns `200 OK` only after verifying that
critical external dependencies (Neo4j, GCS, Pub/Sub) are reachable. Returns a
non-2xx status when the service is not yet ready to accept traffic.

```json
{ "status": "ready" }
```

### `GET /api/traces/<run_id>`

Cross-project LangSmith trace correlation lookup. Given a `run_id`, returns the
correlated trace URLs across the related LangSmith projects (e.g. agent project
↔ pipeline project) by fingerprint matching — preserving the behavior of the
former standalone `find_trace_runs.py` utility as an HTTP endpoint.

---

## Local Development

### Prerequisites

- **Python 3.12.3** (matching the Dockerfile runtime).
- **pip** and a virtual environment tool of your choice (`venv`, `virtualenv`,
  etc.).
- **Google Cloud Service Account key** with access to the Blitzy platform
  artifact registry, Pub/Sub topics, GCS buckets, and Secret Manager. The path
  to this JSON key file is exported as `GOOGLE_APPLICATION_CREDENTIALS`.

### Authentication — `GOOGLE_APPLICATION_CREDENTIALS`

Export the appropriate credentials for the environment you are targeting:

**Dev:**
```bash
export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/service-key-dev.json"
```

**Stage:**
```bash
export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/service-key-stage.json"
```

**Prod:**
```bash
export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/service-key-prod.json"
```

These keys are also used during dependency installation to authenticate
against the private GCP Artifact Registry that hosts `blitzy-platform-shared`
(via the pre-installed `keyrings.google-artifactregistry-auth` backend).

### Install dependencies

```bash
pip install -r requirements.txt
```

This installs Flask, Gunicorn, `flask-cors`, the `blitzy-platform-shared`
internal package (which transitively pulls in LangGraph, LangChain, the LLM
provider SDKs, the GCP client libraries, Neo4j, LangSmith, MCP, etc.), and
the test framework (`pytest`, `pytest-flask`, `pytest-asyncio`,
`pytest-cov`).

### Run the Flask development server

For an iterative development loop with auto-reload and verbose error pages:

```bash
python run.py
```

`run.py` invokes `create_app()` and calls `app.run(debug=True, port=8080)`,
binding the server to `0.0.0.0:8080`.

You can also use the equivalent Makefile target:

```bash
make run-dev
```

### Run with Gunicorn (production-like)

To exercise the actual production WSGI configuration locally — useful for
validating long-running pipeline behavior, async view dispatch, and worker
concurrency — start Gunicorn directly:

```bash
gunicorn --bind 0.0.0.0:8080 --workers 2 --timeout 3600 wsgi:app
```

Or via Make:

```bash
make run-prod
```

The `--timeout 3600` mirrors the Cloud Run request timeout configured for
long-running pipeline executions.

---

## Testing

The test suite lives under `tests/` and is organized to mirror the
application package layout.

### Directory layout

```
tests/
├── __init__.py
├── conftest.py                 # shared fixtures: Flask test client, mocks
├── test_routes/                # HTTP-level tests for each Blueprint
│   ├── __init__.py
│   ├── test_generate.py        # POST /api/generate
│   ├── test_update.py          # POST /api/update
│   └── test_health.py          # GET /health, GET /ready
└── test_services/              # service-layer unit tests with mocked dependencies
    ├── __init__.py
    └── test_pipeline_service.py
```

### Run the full test suite

```bash
pytest tests/
```

Or via Make:

```bash
make test
```

### Run with coverage measurement

```bash
pytest --cov=app tests/
```

Or via Make (also emits an HTML report under `htmlcov/`):

```bash
make test-cov
```

`tests/conftest.py` provides a `client` fixture built from
`create_app(config_name="testing")` along with mock factories for
`CodeGraphBuilder`, `AdminStorageService`, the Pub/Sub publisher, and the
LangGraph pipeline so that route and service tests run in complete isolation
from external services.

---

## Deployment

### CI/CD workflow

Continuous deployment is handled by the GitHub Actions workflow at
`.github/workflows/deploy-service.yml` (renamed from the previous
`deploy-job.yml`). On a push to a deploy branch, the workflow:

1. Authenticates to GCP using the service-account key stored in the GitHub
   secret `GOOGLE_APPLICATION_CREDENTIALS`.
2. Builds the Docker image defined by `Dockerfile` and pushes it to the GCP
   Artifact Registry repository configured in the `Makefile`
   (`archie-job-reverse-file-mapper:<tag>`).
3. Deploys the image to Cloud Run as a **Service** using
   `gcloud run services deploy` (replacing the previous
   `gcloud run jobs deploy` command used by the batch-job deployment model).

### Container entry point

The Docker image launches the application via Gunicorn, bound to port `8080`
with the WSGI entry point `wsgi:app`:

```dockerfile
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "3600", "wsgi:app"]
```

The `--timeout 3600` (one hour) accommodates the long-running document
generation pipeline and matches the Cloud Run Service request timeout. The
single image preserves the multi-runtime stack required by the original
container — Python 3.12.3 for the application, Node.js 22 LTS for the
Chrome DevTools and Figma MCP tool servers spawned via `npx`, and Google
Chrome for headless browser automation.

### Manual deployment (developer workflow)

For ad-hoc deploys outside the CI pipeline, the `Makefile` provides a
convenience target backed by the internal `deploy-to-cloud-run --type service`
utility:

```bash
ENV=qa make deploy
```

---

## Environment Variables

The application reads its configuration from environment variables in
`app/config.py`. All variables documented below are preserved verbatim from
the original Cloud Run Job implementation — they are populated at deploy time
by the GitHub Actions workflow / Cloud Run service definition. No new
environment variables are introduced by the Flask refactor.

### GCP / Project

| Variable             | Purpose                                                                |
| -------------------- | ---------------------------------------------------------------------- |
| `PROJECT_ID`         | GCP project ID hosting the Cloud Run service, Pub/Sub topics, and GCS  |
| `GCS_BUCKET_NAME`    | GCS bucket name used by `StorageService` for specification persistence |
| `PRIVATE_BLOB_NAME`  | Path prefix / blob name used for private (per-tenant) document objects |
| `SERVICE_NAME`       | Logical service identifier used in logs and trace metadata             |

### Pub/Sub

| Variable                          | Purpose                                                              |
| --------------------------------- | -------------------------------------------------------------------- |
| `PLATFORM_EVENTS_TOPIC`           | Topic that receives `IN_PROGRESS`, `DONE`, and `ERROR` events        |
| `GENERATE_REVERSE_THINKING_TOPIC` | Topic used to trigger downstream reverse-thinking generation jobs    |

### AI Providers

| Variable             | Purpose                                                            |
| -------------------- | ------------------------------------------------------------------ |
| `ANTHROPIC_API_KEY`  | Claude (Anthropic) API key for deep-analytical agents              |
| `OPENAI_API_KEY`     | OpenAI API key for structured-output extraction agents             |
| `VOYAGE_API_KEY`     | Voyage AI API key for embeddings used in semantic search           |
| `GOOGLE_API_KEY`     | Google AI / Gemini API key for fallback model invocations          |

### Neo4j

| Variable          | Purpose                                                       |
| ----------------- | ------------------------------------------------------------- |
| `NEO4J_SERVER`    | Bolt URI of the Neo4j instance hosting the code graph         |
| `NEO4J_USERNAME`  | Username for the read-only Neo4j account                      |
| `NEO4J_PASSWORD`  | Password for the read-only Neo4j account                      |

### LangSmith

| Variable             | Purpose                                                            |
| -------------------- | ------------------------------------------------------------------ |
| `LANGSMITH_TRACING`  | Toggle (`true`/`false`) to enable LangSmith trace collection       |
| `LANGSMITH_ENDPOINT` | LangSmith API endpoint URL                                         |
| `LANGSMITH_API_KEY`  | LangSmith API key for authenticated trace ingestion                |
| `LANGSMITH_PROJECT`  | LangSmith project name to which traces are tagged                  |

### Service URLs

| Variable                | Purpose                                                          |
| ----------------------- | ---------------------------------------------------------------- |
| `GITHUB_SECRET_SERVER`  | URL of the internal GitHub Secret Server for token retrieval     |
| `SERVICE_URL_GITHUB`    | URL of the GitHub integration service                            |
| `SERVICE_URL_RELAY`     | URL of the Relay service for cross-service messaging             |
| `SERVICE_URL_ADMIN`     | URL of the Admin service backing `AdminStorageService` operations|

### Miscellaneous

| Variable                       | Purpose                                                                                  |
| ------------------------------ | ---------------------------------------------------------------------------------------- |
| `USE_RUNNER`                   | Toggle (`true`/`false`) controlling whether `RunnerSession` is used for agent execution  |
| `TOKENIZERS_PARALLELISM`       | Standard HuggingFace tokenizer parallelism flag (`true`/`false`); set to silence warnings|
| `IN_PROGRESS_EVENT_FREQUENCY`  | Frequency (in seconds or pipeline steps) at which `IN_PROGRESS` events are published     |

