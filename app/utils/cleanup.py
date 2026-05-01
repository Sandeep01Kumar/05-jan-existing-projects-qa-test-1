"""Per-request resource cleanup teardown handlers.

In the original ``main.py`` (lines 308-330), the LangGraph pipeline
invocation was wrapped in a top-level ``try``/``finally`` block that
closed the ``CodeGraphBuilder`` and stopped the ``RunnerSession``
(if any) before the script exited::

    finally:
        graph_builder.close()
        if runner_session:
            runner_session.stop()

In the Flask migration, this cleanup must run at the end of EVERY
request rather than at the end of the process.  This module provides
the Flask-idiomatic equivalent: a teardown handler bound to
:meth:`flask.Flask.teardown_appcontext`.

The :class:`PipelineService` (in :mod:`app.services.pipeline_service`)
populates ``g.graph_builder`` and ``g.runner_session`` at the start of
each request that triggers a pipeline run.  At the end of every
request, regardless of success or failure, the teardown handler
registered by :func:`register_teardown_handlers` retrieves those
references from ``g``, calls ``close()`` / ``stop()`` on them, and
removes them from ``g``.

Per the Flask teardown contract, the teardown function MUST NOT
raise: any cleanup errors are logged via the application logger and
swallowed.

Design notes
============

* ``@app.teardown_appcontext`` (NOT ``@app.teardown_request``) is the
  correct decorator because the application context is torn down
  AFTER the request context, so cleanup runs even when the request
  context has been destroyed by an exception during response
  generation.
* :meth:`flask.g.pop` (rather than direct attribute access) is used
  to retrieve the per-request resources, so the cleanup is idempotent
  and the references are removed in a single atomic operation.
* This module imports ONLY from Flask and the standard library.  It
  intentionally does NOT import :class:`CodeGraphBuilder` from
  ``blitzy_platform_shared`` or :class:`RunnerSession` from
  ``blitzy_utils``: it treats ``g.graph_builder`` and
  ``g.runner_session`` as opaque objects exposing ``close()`` /
  ``stop()`` methods.  This keeps :mod:`app.utils.cleanup`
  side-effect-free at import time and safe to use in unit tests.
* Health-check requests (``/health``, ``/ready``) and any other
  request that does not initialize a pipeline never set
  ``g.graph_builder`` or ``g.runner_session``; the teardown handler
  gracefully no-ops in that case.
"""

from typing import Optional

from flask import Flask, current_app, g

# --------------------------------------------------------------------- #
# Names of the per-request resource attributes on Flask's ``g`` object.
# --------------------------------------------------------------------- #
# These constants are the canonical keys under which
# :class:`PipelineService` stores its per-request resources.  They are
# referenced both here (for popping during teardown) and in the
# pipeline-service module (for assignment at request start).  Defining
# them as module-level constants avoids "magic string" duplication and
# keeps the contract explicit.
_GRAPH_BUILDER_KEY = "graph_builder"
_RUNNER_SESSION_KEY = "runner_session"


def register_teardown_handlers(app: Flask) -> None:
    """Bind the per-request resource cleanup function to the Flask app.

    Registers :func:`_cleanup_request_resources` as the application's
    ``@app.teardown_appcontext`` handler.  The handler runs at the end
    of every request (regardless of success or failure) and releases
    any per-request resources that the request placed on Flask's ``g``
    object.

    The Flask-idiomatic ``@app.teardown_appcontext`` decorator is used
    (NOT ``@app.teardown_request``) because the application context is
    torn down AFTER the request context, ensuring cleanup runs even
    when the request context is destroyed by an exception during
    response generation.

    This function is invoked exactly once during application startup,
    from :func:`app.create_app` immediately after blueprint
    registration.

    Args:
        app: The Flask application instance (typically the one returned
            by :func:`app.create_app`).

    Returns:
        ``None``.  Side effects: appends
        :func:`_cleanup_request_resources` to
        ``app.teardown_appcontext_funcs``.
    """
    # ``Flask.teardown_appcontext`` accepts a callable taking a single
    # ``Optional[BaseException]`` argument and returns the same callable
    # unchanged (so it can also be used as a decorator).  We invoke it
    # directly here because we want to register an existing function,
    # not declare a new one inline.
    app.teardown_appcontext(_cleanup_request_resources)


def _cleanup_request_resources(exception: Optional[BaseException]) -> None:
    """Release per-request pipeline resources.

    Bound to ``@app.teardown_appcontext`` by
    :func:`register_teardown_handlers`.  Runs at the end of every
    request, regardless of whether an exception occurred during
    request processing.

    Cleanup steps (matching the original ``main.py`` ``finally`` block
    at lines 327-330):

    1. Pop ``g.graph_builder`` (a ``CodeGraphBuilder`` placed on ``g``
       by :class:`PipelineService`) and call its ``close()`` method to
       release the Neo4j connection.
    2. Pop ``g.runner_session`` (an optional ``RunnerSession``) and
       call its ``stop()`` method to terminate the remote runner.

    Each cleanup step is wrapped in its own ``try``/``except`` block
    so a failure cleaning up one resource does not prevent the other
    from being cleaned up.  All exceptions are logged via the
    application logger and swallowed; per the Flask teardown contract,
    teardown handlers MUST NOT propagate exceptions.

    The cleanup order -- ``graph_builder.close()`` BEFORE
    ``runner_session.stop()`` -- preserves the order from the original
    ``main.py`` ``finally`` block.  Closing the Neo4j connection
    first ensures any final code-graph queries pending on the runner
    can complete before the runner is terminated.

    Args:
        exception: The exception (if any) that triggered the teardown.
            Cleanup runs regardless of whether ``exception`` is
            ``None``; the argument is accepted purely to comply with
            Flask's teardown-handler signature.

    Returns:
        ``None``.  Side effects: ``graph_builder.close()`` and
        ``runner_session.stop()`` are invoked on the per-request
        resources (if present) and those references are removed
        from ``g``.
    """
    # ------------------------------------------------------------------
    # Step 1: Close the CodeGraphBuilder (Neo4j connection).
    # ------------------------------------------------------------------
    # Pop with a default of ``None`` so we never raise ``AttributeError``
    # for requests (e.g. ``/health``, ``/ready``) that did not
    # initialize a pipeline.  ``g.pop`` removes the attribute from ``g``
    # in a single atomic operation, so subsequent teardown handlers (or
    # mistaken re-entry into this function) will not see a stale
    # reference.
    graph_builder = g.pop(_GRAPH_BUILDER_KEY, None)
    if graph_builder is not None:
        try:
            graph_builder.close()
        except Exception:
            # Per the Flask teardown contract, never propagate cleanup
            # errors -- doing so causes undefined behavior in the
            # framework's request-handling pipeline.  Log with full
            # traceback (``logger.exception``) so the failure is still
            # diagnosable in the structured JSON logs emitted by
            # ``blitzy_utils.logger``.
            current_app.logger.exception(
                "Error while closing graph_builder during teardown."
            )

    # ------------------------------------------------------------------
    # Step 2: Stop the RunnerSession (remote runner) if one was started.
    # ------------------------------------------------------------------
    # The original ``main.py`` only called ``runner_session.stop()`` if
    # ``runner_session`` was not ``None``; preserve that semantic by
    # checking for ``None`` after the pop.  Note that the absence of
    # the attribute and an explicit ``None`` value both result in
    # skipping the ``stop()`` call -- this matches the semantics of
    # ``if runner_session:`` in the original code (modulo truthiness
    # of falsy-but-non-None objects, which the original loop did not
    # need to handle because ``RunnerSession`` instances are always
    # truthy).
    runner_session = g.pop(_RUNNER_SESSION_KEY, None)
    if runner_session is not None:
        try:
            runner_session.stop()
        except Exception:
            current_app.logger.exception(
                "Error while stopping runner_session during teardown."
            )


# --------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------- #
# Only :func:`register_teardown_handlers` is exposed; the actual cleanup
# function ``_cleanup_request_resources`` is intentionally private and
# called only by Flask's teardown machinery.
__all__ = ["register_teardown_handlers"]
