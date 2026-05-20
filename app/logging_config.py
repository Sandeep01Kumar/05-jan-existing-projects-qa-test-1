"""Logging configuration for the hao-backprop-test Flask service.

Provides ``configure_logging(app)`` — the single entry point that wires up
``app.logger`` with a deterministic format and the level configured by
``app.config["LOG_LEVEL"]``.

Replaces the retired Node implementation's lone ``console.log`` call
(see ``server.js:L13`` — ``console.log(`Server running at http://${hostname}:${port}/`)``)
with a structured Python ``logging`` setup per AAP §0.3.3 (Structured Logging
pattern), §0.6.3 (Idiom Translations — ``console.log`` → ``app.logger.info``),
§0.6.5 (PM2 → gunicorn mapping — log capture via stdout/stderr complements
``accesslog``/``errorlog`` directives), and §0.7.3 (Rule clause "logging"
honored by Python ``logging`` module).

Design notes
------------

* **Framework decoupling** — this module deliberately does not import
  :py:mod:`flask`.  ``configure_logging`` accepts the Flask application as a
  parameter (duck-typed: any object with a ``config`` mapping and a ``logger``
  attribute satisfies the contract), which lets the function be unit-tested in
  isolation with a lightweight stub.  See AAP §0.3.3 Application Factory.

* **stdout, not stderr** — the configured :py:class:`logging.StreamHandler`
  targets :py:data:`sys.stdout` so that in-process log lines interleave
  cleanly with gunicorn's ``accesslog = "-"`` directive (see
  ``gunicorn_config.py``).  Critical errors will still surface on stderr via
  gunicorn's ``errorlog = "-"`` directive at the process supervisor layer per
  AAP §0.6.5.

* **Idempotency** — pytest fixtures call :py:func:`app.create_app` once per
  test (the Application Factory pattern, AAP §0.3.3).  Without an explicit
  duplicate-handler guard, every test would attach an additional
  ``StreamHandler`` to ``app.logger`` and emit each log line N times.  The
  implementation below removes any previously-attached ``StreamHandler``
  instances before adding the new one.

* **propagate = False** — Flask installs a default handler on
  ``app.logger``'s parent chain (and Werkzeug installs its own root handler
  for request-line traffic).  Leaving propagation enabled would cause every
  call to ``app.logger.info(...)`` to emit twice — once via our handler and
  once via the root handler.  Disabling propagation contains every log line
  to the single handler this module attaches.

* **No file-based logging** — by design.  Per AAP §0.6.5, file rotation /
  aggregation is delegated to the deployment layer (gunicorn's ``accesslog``
  / ``errorlog`` directives, or the host's systemd / Docker / Kubernetes log
  driver).  This module keeps the in-process side of logging strictly
  concerned with formatting and level filtering on stdout.

References
----------

* AAP §0.2.1 (rule-mandated CREATE)
* AAP §0.3.1 (Role Specification — ``configure_logging(app)`` builds a
  ``StreamHandler`` and ``Formatter``, attaches to ``app.logger`` at the
  configured ``LOG_LEVEL``)
* AAP §0.3.3 (Design Pattern — Structured Logging)
* AAP §0.4.1 (Transformation row ``app/logging_config.py``)
* AAP §0.5.4 (Import Refactoring — ``import logging``)
* AAP §0.6.3 (Idiom Translations — ``console.log(msg)`` → ``app.logger.info(msg)``)
* AAP §0.6.5 (PM2 → gunicorn mapping — ``errorlog``/``accesslog`` directives)
* AAP §0.7.3 (Rule clause "logging" → Python ``logging`` module)
"""

import logging
import sys


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------
# Single-line structured format string applied to every emitted record.  The
# fields are deliberately ordered (timestamp first, then level, then logger
# name in brackets, then the message) so that grep / cut / awk pipelines can
# slice on whitespace-separated columns without ambiguity.
#
# Field reference (Python ``logging`` LogRecord attributes):
#
#   * ``%(asctime)s``   — formatted timestamp (see ``_DATE_FORMAT`` below)
#   * ``%(levelname)s`` — severity, e.g. ``INFO``, ``WARNING``
#   * ``%(name)s``      — logger name, e.g. ``"app"`` for Flask's app.logger
#                         (``Flask(__name__)`` sets the logger name to the
#                         app's import name — ``"app"`` here because
#                         ``app/__init__.py`` invokes ``Flask(__name__)``)
#   * ``%(message)s``   — the rendered log message
#
# Kept as a module-level constant so that downstream tests can import and
# assert against it without re-deriving the literal string.
_LOG_FORMAT: str = "%(asctime)s %(levelname)s [%(name)s] %(message)s"

# ISO-8601-style date format (no microseconds; ``%z`` appends the UTC offset
# in the form ``+0000``).  This format is sortable as plain text, parseable
# by most log-aggregation tooling (Splunk, Loki, ELK), and stable across
# locales.  We deliberately avoid ``%(msecs)d`` here: stdlib's default
# millisecond resolution requires a separate ``msecs`` field, which would
# break the single-format-string contract.
_DATE_FORMAT: str = "%Y-%m-%dT%H:%M:%S%z"

# Default level applied when ``app.config["LOG_LEVEL"]`` is missing, empty,
# or names a logging level that does not exist on the :py:mod:`logging`
# module (e.g. a typo like ``"INF"``).  Defaulting to ``INFO`` matches the
# ``.env.example`` template and the ``BaseConfig`` default in
# ``app/config.py``.
_DEFAULT_LEVEL: int = logging.INFO


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def configure_logging(app):
    """Configure structured logging on a Flask application's logger.

    Attaches a single :py:class:`logging.StreamHandler` (writing to
    :py:data:`sys.stdout`) to ``app.logger`` with a deterministic format
    string.  The handler's level is taken from ``app.config["LOG_LEVEL"]``
    (default ``"INFO"`` per :class:`app.config.BaseConfig`).

    This replaces the retired Node implementation's lone ``console.log``
    call (see ``server.js:L13``) with a single configurable logging surface
    per AAP §0.3.3 (Structured Logging pattern) and §0.6.3 (Idiom
    Translations — ``console.log`` → ``app.logger.info``).

    The function is **idempotent**: calling it multiple times on the same
    application instance results in exactly one ``StreamHandler`` attached
    to ``app.logger``.  This property is essential for the pytest fixture
    pattern (AAP §0.3.3 Application Factory) where ``create_app()`` may be
    invoked once per test — without idempotency, each call would attach an
    additional handler and every log line would multiply across runs.

    Args:
        app: A Flask application instance (or any object exposing a
            ``config`` mapping and a ``logger`` attribute that quacks like
            :py:class:`logging.Logger`).  ``app.config["LOG_LEVEL"]`` must
            be set before this call — the :func:`app.create_app` factory
            applies the config class via ``app.config.from_object(...)``
            *before* invoking ``configure_logging(app)``.

    Returns:
        ``None``.  The function mutates ``app.logger`` in place.

    Side effects:
        * Removes any previously-attached ``StreamHandler`` instances from
          ``app.logger.handlers`` (idempotency guard).
        * Adds exactly one new ``StreamHandler`` writing to
          :py:data:`sys.stdout`, formatted with :data:`_LOG_FORMAT` /
          :data:`_DATE_FORMAT`, at the level resolved from
          ``app.config["LOG_LEVEL"]``.
        * Sets ``app.logger.level`` to the same resolved level.
        * Sets ``app.logger.propagate`` to ``False`` so records do not
          bubble up to the root logger (which would cause double emission
          alongside Werkzeug's own root-level handler).

    Example:
        Wiring the helper from the application factory::

            from flask import Flask
            from app.config import DevConfig
            from app.logging_config import configure_logging

            app = Flask(__name__)
            app.config.from_object(DevConfig)
            configure_logging(app)
            app.logger.info("Server running at http://%s:%d/",
                            app.config["HOST"], app.config["PORT"])

        Produces a single line on stdout resembling::

            2025-01-15T12:00:00+0000 INFO [app] Server running at http://127.0.0.1:3000/
    """
    # ------------------------------------------------------------------
    # Step 1 — Resolve the configured LOG_LEVEL string to a numeric
    # logging constant.
    #
    # ``app.config.get("LOG_LEVEL", "INFO")`` returns the configured value
    # (typically a string like ``"INFO"`` or ``"DEBUG"``) or ``"INFO"`` if
    # the key is absent.  We coerce to ``str`` defensively in case a caller
    # passed a non-string (e.g. an int from a customized config class) and
    # uppercase the result so that ``"info"``, ``"Info"``, and ``"INFO"``
    # all resolve identically.
    #
    # ``getattr(logging, level_name, _DEFAULT_LEVEL)`` performs the
    # string → constant lookup safely: if the level name does not exist on
    # the :py:mod:`logging` module (e.g. ``"VERBOSE"`` or a typo), the
    # fallback :data:`_DEFAULT_LEVEL` (``logging.INFO``) is used instead of
    # raising :py:class:`AttributeError`.
    #
    # We additionally guard against the getattr returning a non-integer
    # attribute (e.g. ``logging.getLogger`` if ``LOG_LEVEL`` were
    # somehow set to ``"getLogger"``).  In that case we fall back to the
    # default so that the StreamHandler always receives a valid level.
    # ------------------------------------------------------------------
    level_name = str(app.config.get("LOG_LEVEL", "INFO")).upper()
    resolved = getattr(logging, level_name, _DEFAULT_LEVEL)
    level: int = resolved if isinstance(resolved, int) else _DEFAULT_LEVEL

    # ------------------------------------------------------------------
    # Step 2 — Build the formatter.
    #
    # The formatter is constructed fresh on every call so that callers who
    # mutate the module-level constants between calls (e.g. test fixtures
    # that temporarily monkeypatch ``_LOG_FORMAT``) see their changes take
    # effect.  Formatter instances are cheap to allocate — there is no
    # performance reason to cache one.
    # ------------------------------------------------------------------
    formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # ------------------------------------------------------------------
    # Step 3 — Build the handler.
    #
    # ``StreamHandler(stream=sys.stdout)`` writes to standard output.  This
    # choice is deliberate (AAP §0.6.5):
    #
    #   * In development (``python wsgi.py``), the developer sees log
    #     output directly in the terminal alongside any ``print`` calls.
    #   * In production (``gunicorn -c gunicorn_config.py wsgi:app``),
    #     gunicorn's ``accesslog = "-"`` directive also targets stdout,
    #     keeping all server output on a single stream that the host's
    #     process supervisor (systemd / Docker / Kubernetes) can capture.
    #
    # The handler's level is set explicitly so that records below the
    # configured threshold are filtered out *before* the formatter runs —
    # a minor optimization, but more importantly it documents intent.
    # ------------------------------------------------------------------
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(formatter)

    # ------------------------------------------------------------------
    # Step 4 — Idempotency guard.
    #
    # Remove any previously-attached ``StreamHandler`` instances from
    # ``app.logger`` before adding the new one.  Iterating over a copy
    # (``list(...)``) is mandatory: mutating the underlying list during
    # iteration would skip elements or raise ``RuntimeError`` depending on
    # the Python version.
    #
    # We deliberately filter on ``isinstance(existing, logging.StreamHandler)``
    # rather than removing every handler:
    #
    #   * ``FileHandler`` inherits from ``StreamHandler``, so any file
    #     handler attached by an integrator (e.g. a future enhancement to
    #     route audit logs to a file) would also be removed.  This is the
    #     intended behavior — ``configure_logging`` owns the stream-handler
    #     surface end-to-end and must clear it before re-wiring.
    #   * Non-stream handlers (e.g. an external ``SysLogHandler``) are
    #     preserved across calls — they were not attached by this module
    #     and should outlive a re-configuration.
    # ------------------------------------------------------------------
    for existing in list(app.logger.handlers):
        if isinstance(existing, logging.StreamHandler):
            app.logger.removeHandler(existing)

    # ------------------------------------------------------------------
    # Step 5 — Attach the handler and set the logger level.
    #
    # Setting the level on BOTH the handler (Step 3) and the logger here
    # is required: the handler-level filter runs only after the logger
    # has decided to dispatch the record.  If the logger's level is higher
    # than the handler's, low-severity records would be dropped before the
    # handler ever sees them.
    # ------------------------------------------------------------------
    app.logger.addHandler(handler)
    app.logger.setLevel(level)

    # ------------------------------------------------------------------
    # Step 6 — Disable propagation.
    #
    # Flask's ``app.logger`` is a child of the root logger.  Without
    # ``propagate = False``, every record this handler emits would also
    # bubble up to the root logger — and Werkzeug installs its own root
    # handler for request-line traffic, which would duplicate every line.
    # Setting propagate to False contains every record to the single
    # StreamHandler we just attached.
    #
    # This is a one-time mutation: subsequent calls (per the idempotency
    # contract above) re-assert the same value, which is a no-op.
    # ------------------------------------------------------------------
    app.logger.propagate = False


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------
# Explicit ``__all__`` declaration so that ``from app.logging_config import *``
# (e.g. from an integration test or interactive shell) imports only the public
# API.  Module-private helpers (``_LOG_FORMAT``, ``_DATE_FORMAT``,
# ``_DEFAULT_LEVEL``) remain accessible by qualified name for advanced
# introspection without polluting the wildcard-import surface.
__all__ = ["configure_logging"]
