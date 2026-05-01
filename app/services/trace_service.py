"""LangSmith trace correlation service.

Exposes :class:`TraceService` and :func:`build_trace_service` for
cross-project LangSmith trace correlation.  Given a ``run_id``,
the service queries LangSmith via the ``langsmith.Client`` to find
correlated trace URLs across all LangSmith projects accessible to
the configured API key.

This module is consumed by :mod:`app.routes.traces`, which exposes
a ``GET /api/traces/<run_id>`` endpoint that returns the correlated
URLs as JSON.

The service is decoupled from Flask -- the caller is responsible for
reading any LangSmith config values from ``current_app.config[...]``
before invocation.  This makes the service trivially unit-testable
without a Flask app context.

Design rationale
================

* **No Flask dependency.**  The :class:`TraceService` constructor
  accepts an optional pre-built :class:`langsmith.Client`.  When no
  client is supplied, a default :class:`Client` is constructed and
  reads ``LANGSMITH_API_KEY``, ``LANGSMITH_ENDPOINT``,
  ``LANGSMITH_PROJECT``, and ``LANGSMITH_TRACING`` from the process
  environment using the SDK's own resolution rules.  Tests inject
  ``MagicMock`` instances via the ``client`` argument.

* **Defensive serialization.**  The :func:`_run_to_dict` helper uses
  :func:`getattr` with ``None`` defaults for every field access so
  the conversion never raises ``AttributeError`` even when the
  underlying ``langsmith`` SDK reorganises its ``Run`` model between
  releases.  Both ``session_name`` (older SDKs) and ``project_name``
  (newer SDKs) are checked for the project identifier.

* **JSON-safe results.**  Every value in the returned dict is either
  a string or :data:`None`, making :meth:`find_correlated_traces`
  output trivially compatible with :func:`flask.jsonify` in the
  ``/api/traces/<run_id>`` route handler.

* **No additional retry logic.**  The :class:`langsmith.Client`
  ships with its own retry/backoff policy for transient HTTP
  failures.  This service intentionally does not layer additional
  retries on top, in keeping with the AAP's directive to avoid
  introducing new error-handling layers during the Flask migration.

* **Thread safety.**  The :class:`langsmith.Client` is documented as
  safe to share across threads; each :class:`TraceService` therefore
  owns a single client instance for the lifetime of the service so
  the underlying HTTP session can be reused across multiple calls.
"""

# ---------------------------------------------------------------------------
# Standard-library imports
# ---------------------------------------------------------------------------
# ``typing`` is used purely for static annotations on the public API of this
# module.  ``Iterable`` types the generator returned by
# :meth:`langsmith.Client.list_runs`; ``Optional`` types the constructor's
# ``client`` argument that admits dependency-injected mocks during testing.
from typing import Any, Dict, Iterable, List, Optional

# ---------------------------------------------------------------------------
# Third-party imports
# ---------------------------------------------------------------------------
# ``langsmith.Client`` is the SDK entry point.  It is a transitive dependency
# of ``blitzy-platform-shared`` (pinned in requirements.txt at version
# 0.0.781), so no direct entry in requirements.txt is required for this
# import to succeed at runtime.  The ``Client`` class accepts no required
# constructor arguments -- when called with no parameters, it reads its
# configuration (``LANGSMITH_API_KEY``, ``LANGSMITH_ENDPOINT``,
# ``LANGSMITH_PROJECT``, ``LANGSMITH_TRACING``) from environment variables.
from langsmith import Client

__all__ = ["TraceService", "build_trace_service"]


class TraceService:
    """Service for querying LangSmith traces by run ID.

    Wraps a :class:`langsmith.Client` to provide a typed, testable
    interface for trace correlation.  Each :class:`TraceService`
    instance owns its own ``Client`` so the underlying HTTP session
    can be reused across multiple ``find_correlated_traces`` calls.

    The default behavior (``Client()`` with no arguments) reads the
    ``LANGSMITH_API_KEY``, ``LANGSMITH_ENDPOINT``, and other env vars
    via the LangSmith SDK's standard environment-variable resolution.
    For testing or for using a non-default endpoint, callers may
    supply a pre-built ``Client`` via the ``client`` constructor
    argument.

    Args:
        client: Optional pre-built :class:`langsmith.Client`.  If
            ``None``, a default ``Client()`` is constructed (which
            reads ``LANGSMITH_API_KEY``, ``LANGSMITH_ENDPOINT``, etc.
            from the environment).

    Example:
        Production use (reads ``LANGSMITH_API_KEY`` from env):

        >>> svc = TraceService()
        >>> results = svc.find_correlated_traces("run-id-here")

        Test use (with an injected mock):

        >>> from unittest.mock import MagicMock
        >>> mock = MagicMock()
        >>> mock.list_runs.return_value = []
        >>> svc = TraceService(client=mock)
        >>> svc.find_correlated_traces("nope")
        []
    """

    def __init__(self, client: Optional[Client] = None) -> None:
        # Store the supplied client, or construct a default :class:`Client`
        # whose configuration is resolved from the LangSmith SDK's standard
        # environment-variable lookup (LANGSMITH_API_KEY, LANGSMITH_ENDPOINT,
        # LANGSMITH_PROJECT, LANGSMITH_TRACING).  Using a dependency-injected
        # client keeps the service unit-testable without a network connection
        # or valid LangSmith credentials.
        self._client = client if client is not None else Client()

    def find_correlated_traces(
        self,
        run_id: str,
        *,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Find all LangSmith runs correlated with the given run ID.

        Queries LangSmith via ``Client.list_runs(...)`` filtering by
        the ``run_id`` and returns a list of dicts containing the
        correlated URL, ID, project name, start time, status, and
        run type for each match.

        Args:
            run_id: The LangSmith run ID to search for.  Typically
                the trace ID emitted by the LangGraph pipeline (also
                visible in PubSub IN_PROGRESS notifications).
            limit: Maximum number of correlated runs to return
                (defaults to 100).

        Returns:
            A list of dicts.  Each dict has these keys:

            * ``run_id`` (str): The LangSmith run ID.
            * ``url`` (str | None): The fully-qualified LangSmith UI URL
              for the run (returned by ``run.url`` on the LangSmith
              SDK's ``Run`` model).
            * ``project_name`` (str | None): The LangSmith project
              name the run belongs to.
            * ``start_time`` (str | None): ISO-8601 string for the
              run's start time, or ``None`` if not set.
            * ``status`` (str | None): The run status (``"success"``,
              ``"error"``, etc.).
            * ``run_type`` (str | None): The run type (``"chain"``,
              ``"llm"``, ``"tool"``, etc.).

            If no correlated runs are found, the returned list is
            empty.  No exceptions are raised for empty results.
        """
        # ``Client.list_runs`` is a generator: by typing it as an Iterable we
        # stay agnostic of the concrete generator/iterator type the SDK
        # returns.  Passing ``id`` as a single-element list rather than a bare
        # string ensures consistent behaviour across LangSmith SDK versions
        # (the SDK's own docstring example uses ``client.list_runs(id=run_ids)``
        # where ``run_ids`` is a list).  The ``id`` keyword is forwarded into
        # the underlying ``/runs/query`` body via the SDK's ``**kwargs``
        # passthrough.
        runs: Iterable[Any] = self._client.list_runs(
            id=[run_id],
            limit=limit,
        )

        # Eagerly materialise the iterator into a list so the caller does not
        # need to worry about consuming it during request handling -- the
        # generator backed by an HTTP cursor would otherwise be invalidated
        # once the request context tears down.  ``_run_to_dict`` produces a
        # JSON-safe representation suitable for direct ``flask.jsonify``
        # serialization in the route handler.
        results: List[Dict[str, Any]] = []
        for run in runs:
            results.append(_run_to_dict(run))

        return results


def _run_to_dict(run: Any) -> Dict[str, Any]:
    """Serialize a LangSmith ``Run`` SDK object into a JSON-safe dict.

    Uses ``getattr`` defensively so the conversion is robust against
    minor LangSmith SDK changes.

    Args:
        run: A LangSmith ``Run`` model instance returned by
            ``Client.list_runs(...)``.

    Returns:
        A dict with the run's id, url, project_name, start_time,
        status, and run_type.  Missing attributes default to
        ``None``; the resulting dict is JSON-serializable as long
        as the ``start_time`` value (if present) supports
        ``.isoformat()``.
    """
    # Pull the start time out first so we can normalise it into an ISO-8601
    # string.  The SDK exposes ``start_time`` as a ``datetime.datetime`` on
    # real ``Run`` instances, but tests may set it to a plain string or
    # ``None`` -- we accept all three shapes and degrade gracefully.
    start_time = getattr(run, "start_time", None)
    start_time_str: Optional[str]
    if start_time is None:
        start_time_str = None
    else:
        try:
            # ``datetime.datetime`` and ``datetime.date`` both expose
            # ``.isoformat()``.  Pydantic-coerced datetimes from the LangSmith
            # SDK also satisfy this contract.
            start_time_str = start_time.isoformat()
        except AttributeError:
            # Caller supplied something that is neither ``None`` nor a
            # ``datetime``-like object (most likely already a string).  Fall
            # back to ``str()`` so we still produce a JSON-safe value.
            start_time_str = str(start_time)

    # Use ``getattr`` with explicit ``None`` defaults for every field so the
    # helper never raises ``AttributeError`` if the LangSmith SDK reshapes
    # its ``Run`` model.  ``id`` is wrapped in ``str(...)`` because the SDK
    # represents it as a UUID object whose JSON serialization would otherwise
    # be implementation-specific.  Project identification falls back from
    # ``session_name`` (older SDK versions and older LangSmith server
    # responses) to ``project_name`` (newer SDK versions) so the helper
    # remains forward- and backward-compatible.
    return {
        "run_id": str(getattr(run, "id", "")),
        "url": getattr(run, "url", None),
        "project_name": getattr(run, "session_name", None)
        or getattr(run, "project_name", None),
        "start_time": start_time_str,
        "status": getattr(run, "status", None),
        "run_type": getattr(run, "run_type", None),
    }


def build_trace_service(client: Optional[Client] = None) -> TraceService:
    """Construct a :class:`TraceService`.

    Convenience factory matching the pattern used by
    :func:`app.services.notification_service.build_notifier` and
    :func:`app.services.storage_service.build_storage_service`.

    Args:
        client: Optional pre-built ``langsmith.Client``.  If ``None``,
            a default ``Client()`` is constructed.  Tests should
            supply a ``MagicMock`` here.

    Returns:
        A new :class:`TraceService` instance.
    """
    # Delegating to the constructor (rather than returning ``TraceService()``
    # directly with a positional argument) ensures the keyword-only contract
    # of ``__init__`` is preserved across signature changes.
    return TraceService(client=client)
