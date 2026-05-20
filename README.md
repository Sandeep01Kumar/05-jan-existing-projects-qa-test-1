# hao-backprop-test

A Python 3 Flask "Hello, World!" HTTP server (migrated from a former Node.js implementation) bound to `127.0.0.1:3000` by default. The service returns the body `Hello, World!\n` with `Content-Type: text/plain` and status `200` to **every** HTTP method on **every** URL path — preserving the exact behavior of the retired implementation.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Setup](#setup)
3. [Run (Development)](#run-development)
4. [Run (Production)](#run-production)
5. [Test](#test)
6. [Project Layout](#project-layout)
7. [Environment Variables](#environment-variables)
8. [Behavioral Parity](#behavioral-parity)

---

## Prerequisites

- **Python 3.12 or higher** — the runtime is pinned in [`.python-version`](.python-version) for users of `pyenv` or `asdf`.
- **`pip`** — used to install dependencies from [`requirements.txt`](requirements.txt).
- **Virtual environment (recommended)** — use the built-in `python -m venv` to isolate project dependencies from the system interpreter.

Verify your installation:

```bash
python --version    # should report Python 3.12.x or newer
pip --version
```

---

## Setup

Run these commands once after cloning the repository:

```bash
# 1) Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate          # Linux/macOS
# .venv\Scripts\activate           # Windows (PowerShell or cmd.exe)

# 2) Install pinned dependencies
pip install -r requirements.txt

# 3) Copy the environment-variable template and edit values as needed
cp .env.example .env
```

The `.env` file is **gitignored** — only `.env.example` is tracked in version control. See [Environment Variables](#environment-variables) for the full list of variables and their defaults.

---

## Run (Development)

The development server is invoked in one of two equivalent ways. Both bind to `http://127.0.0.1:3000/` by default.

### Option A — run the WSGI entry directly

```bash
python wsgi.py
```

`wsgi.py` instantiates the Flask application via the `create_app()` factory and, when executed as a script, calls `app.run(host=cfg.HOST, port=cfg.PORT)`.

### Option B — use the Flask CLI

```bash
export FLASK_APP=wsgi:app
flask run --host=127.0.0.1 --port=3000
```

Once the server is running, every HTTP method (`GET`, `POST`, `PUT`, `DELETE`, `PATCH`, `HEAD`, `OPTIONS`) on every URL path returns:

- **Status**: `200`
- **Header**: `Content-Type: text/plain` (no `charset` suffix — exact parity with the retired implementation)
- **Body**: `Hello, World!\n` (with the trailing newline character)

Smoke-test the running server:

```bash
curl -i http://127.0.0.1:3000/
curl -i -X POST http://127.0.0.1:3000/any/path
```

---

## Run (Production)

Two production WSGI servers are pinned in [`requirements.txt`](requirements.txt):

- **`gunicorn`** — the primary pre-fork WSGI server for Linux/macOS.
- **`waitress`** — the cross-platform fallback, used on Windows (where `gunicorn` is not supported).

### Linux/macOS — gunicorn (primary)

```bash
gunicorn -c gunicorn_config.py wsgi:app
```

Configuration lives in [`gunicorn_config.py`](gunicorn_config.py) (binds to `127.0.0.1:3000`, sets worker count, log levels, access/error logs, and process name).

### Windows — waitress (fallback)

```bash
waitress-serve --listen=127.0.0.1:3000 wsgi:app
```

### PaaS / Procfile deployments

For platforms that consume a [`Procfile`](Procfile) (Heroku, Dokku, Railway, Fly.io, etc.), the declared process is:

```text
web: gunicorn -c gunicorn_config.py wsgi:app
```

### Process supervision

For production hosts, supervise the WSGI server with a dedicated process manager such as **systemd**, **supervisord**, or **Docker** (with a restart policy) rather than relying on the WSGI server itself. The `gunicorn --reload` flag exists for development convenience only and **must not** be used in production.

---

## Test

The test suite under [`tests/`](tests/) verifies behavioral parity with the retired implementation using `pytest` and `pytest-flask`.

```bash
pytest                              # run all parity tests
pytest -v                           # verbose output
pytest tests/test_app.py            # run a single module
pytest -k "test_body_bytes"         # filter by test name
```

The parity tests assert, for **every** HTTP method (`GET`, `POST`, `PUT`, `DELETE`, `PATCH`, `HEAD`, `OPTIONS`) and a variety of URL paths (`/`, `/any/path`, `/x/y/z`, etc.):

- Response status code is `200`.
- Response header `Content-Type` is exactly `text/plain` (no `charset=utf-8` suffix).
- Response body bytes are exactly `b"Hello, World!\n"` — including the trailing newline.

---

## Project Layout

```text
hao-backprop-test/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── logging_config.py
│   ├── routes/
│   │   ├── __init__.py
│   │   └── main.py
│   └── middleware/
│       ├── __init__.py
│       └── hooks.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── test_app.py
├── wsgi.py
├── requirements.txt
├── pyproject.toml
├── gunicorn_config.py
├── Procfile
├── .env.example
├── .python-version
└── .gitignore
```

### Module responsibilities

| Path | Responsibility |
|------|----------------|
| `app/__init__.py` | Application factory `create_app(config_object)` — instantiates `Flask(__name__)`, loads config, configures logging, registers middleware hooks, and registers `main_bp`. |
| `app/config.py` | Config classes (`BaseConfig`, `DevConfig`, `ProdConfig`, `TestConfig`) with values loaded from `os.environ` via `python-dotenv`. |
| `app/logging_config.py` | `configure_logging(app)` — attaches a stream handler and formatter to `app.logger` at the configured level. |
| `app/routes/main.py` | `main_bp` blueprint with the catch-all hello-world view (routes `/` and `/<path:subpath>`). |
| `app/middleware/hooks.py` | `register_hooks(app)` — registers `before_request`, `after_request`, and `errorhandler` callbacks. |
| `wsgi.py` | WSGI entry point — exposes `app = create_app(...)` for `gunicorn`/`waitress` and runs the dev server under `if __name__ == "__main__":`. |
| `tests/` | `pytest` suite verifying behavioral parity. |

---

## Environment Variables

All variables are documented in [`.env.example`](.env.example) and loaded into `os.environ` at startup by `python-dotenv`. Copy `.env.example` to `.env` and edit values as needed.

| Variable | Default | Purpose |
|----------|---------|---------|
| `FLASK_ENV` | `development` | Flask environment indicator — one of `development`, `production`, or `testing`. |
| `FLASK_CONFIG` | `app.config.DevConfig` | Dotted import path of the config class loaded by `create_app()`. Alternatives: `app.config.ProdConfig`, `app.config.TestConfig`. |
| `HOST` | `127.0.0.1` | Bind host for the WSGI server. The default preserves byte-level parity with the retired implementation. |
| `PORT` | `3000` | Bind port for the WSGI server. The default preserves byte-level parity with the retired implementation. |
| `LOG_LEVEL` | `INFO` | Python `logging` level — one of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |
| `SECRET_KEY` | `change-me` | Flask secret key used for session signing. Not consumed by the current Hello-World route, but recommended for any future feature that uses `flask.session` or `flask.flash`. |

> **Note**: `.env` is gitignored. Never commit production secrets to the repository.

---

## Behavioral Parity

This Python service is a **behavior-preserving rewrite** of an earlier Node.js implementation. Every HTTP request — regardless of method or URL path — receives an HTTP response that is byte-equivalent to the response the retired server would have returned:

- **Status code**: `200`
- **Response header**: `Content-Type: text/plain` (exact string — no `charset` suffix)
- **Response body**: `Hello, World!\n` (14 bytes; trailing newline included)

The `tests/` package asserts these properties exhaustively across the full HTTP method matrix and across a variety of URL paths (including nested paths such as `/a/b/c/d`). Run `pytest` to verify parity at any time.
