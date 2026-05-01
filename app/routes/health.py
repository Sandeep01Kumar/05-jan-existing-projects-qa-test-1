"""Flask Blueprint for Cloud Run health and readiness probes.

Exposes two endpoints:

* ``GET /health`` -- Liveness probe.  Returns ``200 OK`` whenever
  the Flask process is responsive.  Cheap (no I/O); used by Cloud
  Run to detect crashed instances.

* ``GET /ready`` -- Readiness probe.  Returns ``200 OK`` when the
  application has fully initialized (Flask extensions populated,
  required config present) or ``503 Service Unavailable`` with
  diagnostic detail otherwise.  Used by Cloud Run to gate traffic
  routing.

These endpoints are NEW to the Flask migration.  The original
``main.py`` Cloud Run **Job** had no equivalent because batch jobs
do not require health probes.  Cloud Run **Services** require both
liveness and readiness probes to manage container lifecycle.

Per the assigned-folder requirements: the readiness endpoint MUST
NOT trigger any pipeline execution.  It only checks that required
Flask extensions and configuration values are present in the
application.

Design constraints
------------------

* **Foundational module.**  This file imports ONLY from Flask and
  the Python standard library.  It does NOT depend on
  ``app.services.*``, ``app.utils.*``, ``lib.reverse_document.*``,
  ``blitzy_platform_shared.*``, or ``blitzy_utils.*``.  This means
  the ``/health`` endpoint continues to work even if other parts
  of the application fail to import (e.g., due to a missing
  optional dependency or a degraded private package registry).

* **No expensive I/O on ``/ready``.**  The readiness probe is
  polled frequently by Cloud Run.  Calling
  ``storage_client.list_buckets()`` or ``publisher.get_topic(...)``
  on every poll would add latency, risk false-negatives during
  transient network blips, consume API quota, and create
  circular dependencies.  Instead we verify only the in-process
  state populated by :func:`app.extensions.init_extensions` and
  the config keys declared in :attr:`app.config.Config.REQUIRED_VARS`.

* **No Neo4j check.**  Neo4j credentials are looked up per-request
  via ``get_company_neo4j_instance_credentials(company_id)``;
  there is no global Neo4j connection at the application level,
  so a global readiness probe cannot meaningfully verify Neo4j
  connectivity.

* **JSON-only responses.**  All responses are JSON to match the
  application's JSON-only error handlers (see ``app/__init__.py``)
  and to make the endpoints machine-parsable for any monitoring
  system that consumes them.
"""

from __future__ import annotations

from typing import Any, List, Tuple

from flask import Blueprint, current_app, jsonify

# ---------------------------------------------------------------------- #
# Blueprint instance
# ---------------------------------------------------------------------- #
# Mounted at the root URL prefix so the routes are ``/health`` and
# ``/ready`` (matching standard Cloud Run probe path conventions and
# Kubernetes pod-probe conventions).  The Blueprint name ``"health"``
# is unique within the application; ``url_prefix`` is intentionally
# unset so the routes appear at the root of the application.
health_bp = Blueprint("health", __name__)


# ---------------------------------------------------------------------- #
# Liveness probe
# ---------------------------------------------------------------------- #
@health_bp.route("/health", methods=["GET"])
def health() -> Any:
    """Liveness probe -- returns 200 OK whenever the Flask process is up.

    Cloud Run uses this endpoint to detect crashed instances.  The
    handler is intentionally minimal: it performs no I/O, no
    dependency checks, and no logging.  If the Flask process is
    responsive enough to return this response, the instance is
    considered healthy.

    The ``/health`` probe is fundamentally distinct from ``/ready``:

    * **Liveness** -- "Should the container be restarted?"  Returns
      200 if the process is responsive.  MUST be cheap and
      unconditional so it can be polled at high frequency without
      imposing load on the instance.
    * **Readiness** -- "Should this instance receive traffic?"
      Returns 200 if the instance has finished initializing.  MAY
      check in-process state but MUST NOT perform expensive I/O on
      every poll (see :func:`ready` below).

    Returns:
        Tuple of ``(jsonify({"status": "healthy"}), 200)``.
    """
    return jsonify({"status": "healthy"}), 200


# ---------------------------------------------------------------------- #
# Private helpers for the readiness probe
# ---------------------------------------------------------------------- #
def _check_extensions_initialized() -> List[str]:
    """Return a list of missing Flask extension names.

    Verifies that the application-level singletons populated by
    :func:`app.extensions.init_extensions` are present in
    ``current_app.extensions``.  Returns the names of any missing
    singletons (empty list if all are present).

    The two extensions checked are:

    * ``storage_client`` -- ``google.cloud.storage.Client`` used by
      ``AdminStorageService`` and any GCS-dependent service.
    * ``pubsub_publisher`` -- ``google.cloud.pubsub_v1.PublisherClient``
      used by ``Notifier`` for IN_PROGRESS / DONE / ERROR
      notifications and by ``publish_notification`` for
      downstream-job propagation.

    A value of ``None`` for either extension is treated as
    "missing" (Flask's ``app.extensions`` mapping may legitimately
    contain ``None`` placeholders when a feature is disabled).

    Returns:
        A list of extension names that are absent or set to
        ``None`` (empty if all required extensions are populated).
    """
    missing: List[str] = []
    # ``current_app.extensions`` is normally a dict, but defend
    # against the (theoretical) case where it is ``None`` or
    # otherwise falsy on a partially-initialized application.
    extensions = current_app.extensions or {}
    for ext_name in ("storage_client", "pubsub_publisher"):
        if extensions.get(ext_name) is None:
            missing.append(ext_name)
    return missing


def _check_required_config() -> List[str]:
    """Return a list of required config keys that are unset or empty.

    Reads ``current_app.config`` and verifies that every key in the
    application's ``REQUIRED_VARS`` (defined on the active
    :class:`app.config.Config` subclass) maps to a non-empty value.

    If the active config does not define ``REQUIRED_VARS`` (e.g. a
    minimal third-party config object passed to ``create_app``), all
    configured keys are considered present and the function returns
    an empty list.

    The check is intentionally a *truthiness* check (``value is None
    or value == ""``) rather than a stricter ``bool(value)`` check.
    This matches the semantics of :meth:`app.config.Config.validate`,
    which considers any falsy value (``None``, empty string) as
    missing.  Importantly, it allows Flask boolean-config values
    (e.g. ``DEBUG = False``) to remain present even though
    ``bool(False)`` is falsy -- but those keys are not in
    ``REQUIRED_VARS`` so this is moot for the actual contract.

    Returns:
        A list of missing-or-empty config key names (empty if all
        required keys are populated).
    """
    cfg = current_app.config
    # ``REQUIRED_VARS`` is declared on :class:`app.config.Config` as
    # a ``tuple`` of strings.  Default to an empty tuple if it is
    # not present (e.g. tests with minimal config dicts).  The
    # ``Tuple[str, ...]`` annotation documents the expected shape
    # without requiring it at runtime.
    required_vars: Tuple[str, ...] = tuple(cfg.get("REQUIRED_VARS", ()))
    missing: List[str] = []
    for var_name in required_vars:
        value = cfg.get(var_name)
        if value is None or value == "":
            missing.append(var_name)
    return missing


# ---------------------------------------------------------------------- #
# Readiness probe
# ---------------------------------------------------------------------- #
@health_bp.route("/ready", methods=["GET"])
def ready() -> Any:
    """Readiness probe -- returns 200 OK when the app is fully initialized.

    Verifies that:

    1. The application-level Flask extensions
       (``storage_client``, ``pubsub_publisher``) populated by
       :func:`app.extensions.init_extensions` are present.
    2. The required configuration variables (per
       :attr:`app.config.Config.REQUIRED_VARS`) are non-empty.

    The endpoint does NOT verify Neo4j connectivity (which requires
    per-company credential lookup) and does NOT trigger any pipeline
    execution.  It also does NOT perform any expensive I/O against
    GCS, PubSub, or any external service -- it only inspects the
    application's in-process state.  This keeps the probe fast,
    deterministic, quota-free, and free from circular dependencies
    on the very services it is meant to gate traffic into.

    Returns:
        ``200 OK`` with body ``{"status": "ready"}`` when all
        checks pass.

        ``503 Service Unavailable`` with body
        ``{"status": "unavailable", "missing_extensions": [...],
        "missing_config": [...]}`` when any check fails.  Each
        list contains the names of the missing items so operators
        can quickly diagnose deployment problems.
    """
    missing_extensions = _check_extensions_initialized()
    missing_config = _check_required_config()

    if missing_extensions or missing_config:
        return (
            jsonify(
                {
                    "status": "unavailable",
                    "missing_extensions": missing_extensions,
                    "missing_config": missing_config,
                }
            ),
            503,
        )

    return jsonify({"status": "ready"}), 200


# ---------------------------------------------------------------------- #
# Public API
# ---------------------------------------------------------------------- #
__all__ = ["health_bp"]
