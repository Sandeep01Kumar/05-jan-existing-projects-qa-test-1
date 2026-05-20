"""Configuration classes for the hao-backprop-test Flask service.

Implements the twelve-factor configuration pattern (AAP §0.3.3 Design Pattern
Applications). Configuration values are sourced from ``os.environ`` after
``python-dotenv`` populates the process environment from a ``.env`` file (when
present). The active configuration class is selected by ``wsgi.py`` via the
``FLASK_CONFIG`` environment variable (a dotted import path resolved with
``importlib``) and applied to the Flask app instance through
``app.config.from_object(...)`` inside ``create_app()`` (see
``app/__init__.py``).

Default values preserve byte-level network-surface parity with the retired
Node.js implementation per AAP rule R-2 (§0.7.4):

* ``HOST`` defaults to ``"127.0.0.1"`` — mirrors ``server.js:L3``
  (``const hostname = '127.0.0.1';``).
* ``PORT`` defaults to ``3000`` — mirrors ``server.js:L4``
  (``const port = 3000;``).

The module exposes four configuration classes:

* ``BaseConfig`` — shared defaults; never selected directly in deployment, but
  may be loaded for ad-hoc inspection.
* ``DevConfig`` — local development profile (``DEBUG = True``).
* ``ProdConfig`` — production profile (``DEBUG = False``, ``TESTING = False``).
* ``TestConfig`` — pytest profile (``TESTING = True``, deterministic
  ``SECRET_KEY``); used by ``tests/conftest.py`` via
  ``create_app("app.config.TestConfig")``.

This module is framework-agnostic: it does NOT import ``flask``. Flask reads the
attributes off these classes via :py:meth:`flask.Config.from_object`, so the
classes work equally well with any consumer that introspects class attributes.

References:

* AAP §0.2.1 (rule-mandated CREATE), §0.3.1 (Role Specification), §0.3.3
  (Twelve-Factor Configuration), §0.4.1 (Transformation table row
  ``app/config.py``), §0.4.2 (Configuration Transformations),
  §0.5.4 (Import Refactoring), §0.6.4 (Express → Flask mapping —
  ``require('dotenv').config()`` → ``load_dotenv()``), §0.7.3 (Rule clause
  "environment config"), §0.7.4 R-2 (network surface preservation defaults).
"""

import os

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Bootstrap python-dotenv at module-import time.
#
# Why at module level (and not inside a function): the configuration class
# bodies below evaluate ``os.environ.get(...)`` at class-definition time, which
# happens exactly once — when this module is first imported. If ``load_dotenv``
# were deferred (e.g. invoked inside ``create_app()``), the class attributes
# would already be bound to whatever ``os.environ`` looked like at import time,
# making the ``.env`` file ineffective.
#
# By default ``load_dotenv()`` searches for a ``.env`` file in the current
# working directory and walks upward toward the filesystem root. It is a
# no-op (returns ``False``) when no ``.env`` is found, which is the correct
# behavior for production deployments that inject environment variables via
# the platform (systemd, Docker, Heroku, Kubernetes, etc.) rather than via a
# committed ``.env`` file.
#
# This call is the Python / Flask equivalent of placing
# ``require('dotenv').config()`` at the top of an Express application — see
# AAP §0.6.4 Express → Flask mapping for the full translation table.
# ---------------------------------------------------------------------------
load_dotenv()


class BaseConfig:
    """Base configuration shared by every environment profile.

    Subclasses override only the attributes that change between environments
    (``DEBUG``, ``TESTING``, ``FLASK_ENV``, and — in the test profile — a fixed
    ``SECRET_KEY``). All other attributes are inherited unchanged so that the
    network-surface defaults (HOST/PORT) and the logging defaults remain
    consistent across profiles.

    Attribute defaults preserve byte-level parity with the retired Node.js
    implementation per AAP rule R-2 (§0.7.4):

    * ``HOST`` defaults to ``"127.0.0.1"`` (mirrors ``server.js:L3``).
    * ``PORT`` defaults to ``3000`` (mirrors ``server.js:L4``).

    All values are env-driven via ``os.environ``; the second argument to
    ``os.environ.get(...)`` is the fallback used when the variable is absent.
    """

    # ------------------------------------------------------------------
    # Network binding
    # ------------------------------------------------------------------
    # Mirrors retired ``server.js:L3`` — ``const hostname = '127.0.0.1';``.
    # Consumed by ``wsgi.py`` (dev runner) and ``gunicorn_config.py``
    # (production bind directive) per AAP §0.4.2.
    HOST: str = os.environ.get("HOST", "127.0.0.1")

    # Mirrors retired ``server.js:L4`` — ``const port = 3000;``.
    # ``os.environ.get`` always returns a string, so the explicit ``int(...)``
    # cast is required: Flask's ``app.run(port=...)`` and gunicorn's
    # ``bind = "host:port"`` directive both expect an integer port, and at
    # least some Flask versions raise ``TypeError`` when given a string.
    PORT: int = int(os.environ.get("PORT", "3000"))

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    # Consumed by ``app/logging_config.py::configure_logging(app)`` to set the
    # level on ``app.logger``. Must be one of the standard ``logging`` module
    # level names (DEBUG, INFO, WARNING, ERROR, CRITICAL). Defaulting to INFO
    # matches the ``.env.example`` template.
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")

    # ------------------------------------------------------------------
    # Flask runtime profile
    # ------------------------------------------------------------------
    # Free-form string identifying the runtime environment. Mirrors the
    # ``NODE_ENV`` concept referenced by rule QA-20-may-custom-rules and the
    # PM2 ``env`` block (AAP §0.6.5). The value is informational — the active
    # config class is selected separately via the ``FLASK_CONFIG`` env var.
    FLASK_ENV: str = os.environ.get("FLASK_ENV", "development")

    # ------------------------------------------------------------------
    # Security
    # ------------------------------------------------------------------
    # Flask requires ``SECRET_KEY`` for session signing, flash messages, and
    # any future feature that calls ``itsdangerous`` on the user's behalf. The
    # current Hello-World route does not exercise the secret key, but Flask
    # warns at startup when it is unset, so we always provide a value.
    #
    # IMPORTANT: the ``"change-me"`` default is an obvious placeholder and is
    # safe only for a freshly-cloned development checkout. Production
    # deployments MUST override this via the ``SECRET_KEY`` environment
    # variable (or via the platform's secret-management system). The
    # twelve-factor pattern (AAP §0.3.3) keeps secrets out of source control.
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "change-me")

    # ------------------------------------------------------------------
    # Flask flags (overridden by subclasses where appropriate)
    # ------------------------------------------------------------------
    # ``DEBUG`` enables Flask's interactive debugger and code-reloader. Must
    # be ``False`` in production because the debugger exposes a remote code
    # execution surface. Subclasses override as needed.
    DEBUG: bool = False

    # ``TESTING`` disables Flask's error-catching so that exceptions propagate
    # into the pytest test runner. Set to ``True`` only by ``TestConfig``.
    TESTING: bool = False


class DevConfig(BaseConfig):
    """Local development profile.

    Selected when ``FLASK_CONFIG=app.config.DevConfig`` (the default value
    documented in ``.env.example``). Enables Flask's debugger and reloader so
    that source edits trigger an automatic restart, mirroring the developer
    ergonomics that PM2's ``--watch`` flag provides on the Node side.
    """

    DEBUG = True
    TESTING = False
    FLASK_ENV = "development"


class ProdConfig(BaseConfig):
    """Production profile.

    Selected when ``FLASK_CONFIG=app.config.ProdConfig``. Strictly disables
    both the Flask debugger (``DEBUG = False``) and the test-mode
    error-bypassing (``TESTING = False``) so that the application behaves
    exactly as it will under real traffic. Used by the gunicorn process
    declared in ``Procfile`` (``web: gunicorn -c gunicorn_config.py wsgi:app``).
    """

    DEBUG = False
    TESTING = False
    FLASK_ENV = "production"


class TestConfig(BaseConfig):
    """pytest profile used by ``tests/conftest.py``.

    Selected by passing the dotted path ``"app.config.TestConfig"`` to
    ``create_app(...)`` from a pytest fixture. Enables Flask's ``TESTING`` mode
    (which disables the default error-catching behavior so exceptions surface
    as test failures and unlocks ``app.test_client()`` ergonomics) and pins
    a deterministic ``SECRET_KEY`` so test runs are insulated from any drift
    in the developer's local ``.env`` file.
    """

    DEBUG = False
    TESTING = True
    FLASK_ENV = "testing"
    # Deterministic fixed secret — tests must not depend on environment state.
    SECRET_KEY = "test-secret-key"


__all__ = ["BaseConfig", "DevConfig", "ProdConfig", "TestConfig"]
