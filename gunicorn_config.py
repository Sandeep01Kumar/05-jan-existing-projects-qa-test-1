"""Gunicorn configuration for the hao-backprop-test Flask service.

This file is the Python equivalent of a PM2 ``ecosystem.config.js``. It is
consumed via ``gunicorn -c gunicorn_config.py wsgi:app`` (see ``Procfile``).

Background
----------
The hao-backprop-test project was originally a Node.js HTTP server
(``server.js``) that bound to ``127.0.0.1:3000``. Per the Agent Action Plan
§0.7.4 R-8 the Node implementation has been retired and replaced with a
Python 3.12 + Flask 3.1.3 application. PM2 (a Node.js process manager)
was named in the user-supplied rule ``QA-20-may-custom-rules`` as the
production-deployment tool; per AAP §0.6.5 PM2 is translated to its
idiomatic Python equivalents:

* PM2 ``instances: "max"`` (cluster mode) → ``workers = <N>``
* PM2 ``error_file`` / ``out_file``       → ``errorlog`` / ``accesslog``
* PM2 process name                        → ``proc_name = "hello_world"``
* PM2 ``ecosystem.config.js``             → this file (``gunicorn_config.py``)

Parity defaults
---------------
Defaults preserve byte-level parity with the retired Node.js
implementation: the service binds to ``127.0.0.1:3000``, matching the
literals at ``server.js:L3`` (``const hostname = '127.0.0.1';``) and
``server.js:L4`` (``const port = 3000;``). Environment variables —
loaded from ``.env`` by ``python-dotenv`` in ``app/config.py`` — may
override these defaults at runtime, but the defaults themselves remain
``127.0.0.1:3000`` per AAP rule R-2 (Network surface preservation).

Why module-level assignments
----------------------------
Gunicorn reads its Python configuration file as a module and inspects
the module namespace directly for recognised setting names. This means
**all settings below are bare module-level assignments** — there are
no functions, no classes, and no ``__all__`` list. Gunicorn's official
documentation (`Settings <https://docs.gunicorn.org/en/stable/settings.html>`_)
enumerates the valid setting names; only the names defined below are
exported by this module.
"""

import logging
import multiprocessing
import os

# ---------------------------------------------------------------------------
# Bind address
#
# Translates the Node call ``server.listen(3000, '127.0.0.1', ...)``
# (``server.js:L12``) into gunicorn's ``host:port`` notation. ``HOST`` and
# ``PORT`` environment variables (typically set in ``.env``) override the
# defaults; absent env vars yield the parity defaults of ``127.0.0.1`` and
# ``3000`` respectively. The two values are joined via an f-string into the
# single ``bind`` setting that gunicorn expects.
# ---------------------------------------------------------------------------
_host = os.environ.get("HOST", "127.0.0.1")
_port = os.environ.get("PORT", "3000")
bind = f"{_host}:{_port}"

# ---------------------------------------------------------------------------
# Worker processes
#
# AAP §0.3.1 specifies ``workers = 2`` as the documented default — a
# conservative choice appropriate for the simple Hello-World workload. An
# env-driven override (``GUNICORN_WORKERS``) is honoured for tuning:
#
#   * ``GUNICORN_WORKERS=<positive integer>`` — explicit worker count
#   * ``GUNICORN_WORKERS=auto``               — adaptive ``(2 * CPU) + 1`` heuristic
#
# The "auto" branch invokes :func:`multiprocessing.cpu_count` which returns
# the number of logical CPUs visible to the host; this is the canonical
# gunicorn worker-count recommendation for sync workers on multi-core
# production hosts.
#
# Robustness: invalid values (non-integers, zero, negative numbers) fall
# back **safely** to the documented default of ``2`` rather than raising
# ``ValueError`` and aborting gunicorn startup. The fallback is announced
# via a warning so operators are informed but the process keeps running.
# This satisfies the Checkpoint 1 deployment-robustness requirement:
# "integer parsing of GUNICORN_WORKERS with safe fallback when value is
# invalid."
# ---------------------------------------------------------------------------
_DEFAULT_WORKERS = 2
_workers_env = os.environ.get("GUNICORN_WORKERS", str(_DEFAULT_WORKERS))


def _resolve_workers(raw_value: str, default: int = _DEFAULT_WORKERS) -> int:
    """Resolve the ``GUNICORN_WORKERS`` env value to a positive integer.

    Parameters
    ----------
    raw_value : str
        The raw string read from ``os.environ['GUNICORN_WORKERS']`` (or
        the default substituted by the caller if the env var is unset).
    default : int, optional
        The integer to fall back to when ``raw_value`` is invalid. The
        default mirrors AAP §0.3.1's documented ``workers = 2``.

    Returns
    -------
    int
        ``(2 * cpu_count) + 1`` for the literal ``"auto"`` (case-insensitive,
        surrounding whitespace tolerated); the parsed positive integer for
        any other valid value; ``default`` for anything else.

    Notes
    -----
    Invalid inputs trigger a single ``logging`` warning ("falling back
    to default workers=N") so operators see the substitution in
    gunicorn's error log without the process aborting. The function is
    pure — it never raises — which is what allows gunicorn's
    configuration import to complete even in the presence of operator
    typos in ``.env`` or shell-export commands.
    """
    # Normalise: strip surrounding whitespace and lowercase so that
    # "Auto", " auto ", and "AUTO" are all treated the same as "auto".
    value = (raw_value or "").strip()

    # The literal "auto" (any case) uses gunicorn's canonical
    # (2 * cpu_count) + 1 heuristic for sync workers.
    if value.lower() == "auto":
        return (multiprocessing.cpu_count() * 2) + 1

    # Anything else must parse as a positive integer. We use a guarded
    # try/except + positivity check rather than ``int(value)`` directly
    # so that ValueError, empty strings, floats like "2.5", and
    # non-positive integers all funnel into the same fallback branch.
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        logging.warning(
            "GUNICORN_WORKERS=%r is not an integer or 'auto'; "
            "falling back to default workers=%d",
            raw_value,
            default,
        )
        return default

    if parsed <= 0:
        logging.warning(
            "GUNICORN_WORKERS=%r must be a positive integer; "
            "falling back to default workers=%d",
            raw_value,
            default,
        )
        return default

    return parsed


# Module-level assignment — gunicorn discovers settings by name in this
# module's globals (see the file-level docstring), so ``workers`` must
# be a plain int at import time.
workers = _resolve_workers(_workers_env)

# ---------------------------------------------------------------------------
# Logging — analogue of PM2's out_file / error_file
#
# Both access and error logs stream to standard streams (``"-"`` is the
# gunicorn idiom for stdout/stderr). Production deployments typically run
# gunicorn under a process supervisor (systemd, supervisord, Docker, etc.)
# that captures these streams to persistent storage; in development the
# operator sees them inline.
#
# ``loglevel`` defaults to ``"info"`` (AAP §0.3.1). It is forced to
# lowercase to satisfy gunicorn's enum validator which accepts only
# ``debug``, ``info``, ``warning``, ``error``, or ``critical``.
# ---------------------------------------------------------------------------
loglevel = os.environ.get("LOG_LEVEL", "info").lower()
accesslog = "-"   # write access log to stdout
errorlog = "-"    # write error log to stderr

# ---------------------------------------------------------------------------
# Process name
#
# Mirrors the retired ``package.json`` ``"name": "hello_world"`` field
# (the npm manifest declared the project name as ``hello_world`` — see
# AAP §0.6.5 mapping table). Setting ``proc_name`` causes the gunicorn
# master and worker processes to advertise this name in ``ps`` /
# ``setproctitle`` output, easing identification on shared hosts.
# ---------------------------------------------------------------------------
proc_name = "hello_world"

# ---------------------------------------------------------------------------
# Worker class
#
# The default synchronous worker is appropriate for the simple
# request/response pattern this service exhibits — every request returns
# a constant 14-byte body (``Hello, World!\n``) with no I/O fan-out and no
# blocking operations. Async workers (``gevent``, ``eventlet``, ``uvicorn``)
# would add complexity without measurable benefit for this workload.
# ---------------------------------------------------------------------------
worker_class = "sync"

# ---------------------------------------------------------------------------
# Graceful shutdown / restart timeouts (seconds)
#
# * ``timeout``          — workers silent for this many seconds are killed
#                          and restarted (gunicorn default: 30).
# * ``graceful_timeout`` — seconds to wait for workers to finish in-flight
#                          requests during a restart before forcing exit
#                          (gunicorn default: 30).
# * ``keepalive``        — seconds to hold an idle keep-alive connection
#                          open after a response (gunicorn default: 2).
#
# These values intentionally match gunicorn's documented defaults and are
# declared explicitly so the configuration is self-documenting.
# ---------------------------------------------------------------------------
timeout = 30
graceful_timeout = 30
keepalive = 2
