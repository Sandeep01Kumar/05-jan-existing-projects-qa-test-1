"""Service-layer modules for the archie-job-reverse-file-mapper Flask application.

The service layer encapsulates the business logic that was previously
embedded in ``main.py``'s ``generate_reverse_file_map()`` function and
``__main__`` block of the original Cloud Run Job implementation.  By
separating these concerns from the HTTP route handlers (in
:mod:`app.routes`), the routes stay thin (request parsing, validation,
response shaping) while the heavyweight orchestration logic lives in
re-usable, testable service classes that can be invoked from multiple
endpoints and from background workers alike.

Submodules
----------

* :mod:`app.services.pipeline_service` -- :class:`PipelineService`
  owning the eight-node LangGraph reverse document/file-mapping
  pipeline orchestration (the structural heart of the migration).
  This wraps :class:`lib.reverse_document.helper.ReverseDocumentHelper`
  and is responsible for ``CodeGraphBuilder`` / ``RunnerSession``
  lifecycle, ``AdminStorageService`` interaction, and PubSub
  notification publishing.

* :mod:`app.services.notification_service` -- helpers for building
  PubSub notifier instances that publish ``IN_PROGRESS`` / ``DONE`` /
  ``ERROR`` events to the ``platform-events`` topic with the exact
  same message schema (``project_id``, ``tech_spec_id``, ``status``,
  ``tech_spec_url``) emitted by the original Cloud Run Job.

* :mod:`app.services.storage_service` -- helpers for building and
  using ``AdminStorageService`` instances for GCS document upload
  / download operations.  Centralises bucket-name resolution and
  ``tech_spec_url`` generation.

* :mod:`app.services.trace_service` -- :class:`TraceService` for
  LangSmith cross-project trace correlation, adapted from the
  original ``find_trace_runs.py`` utility into an HTTP-callable
  service.

Design rationale
----------------

This package is intentionally minimal -- it contains no eager imports
and exposes no aggregated API.  Consumers must import the specific
submodule they need, for example::

    from app.services.pipeline_service import PipelineService
    from app.services.notification_service import build_notifier
    from app.services.storage_service import build_storage_service
    from app.services.trace_service import TraceService, build_trace_service

Re-exporting submodule symbols from this ``__init__`` would force the
entire LangGraph / LangChain / blitzy-platform-shared dependency tree
to be loaded at application startup time -- even for lightweight
requests such as ``/health``, ``/ready``, and ``/api/traces/<id>``
that do not touch the pipeline.  Keeping the package initializer
empty also avoids the circular-import hazards that arise when a
submodule reaches back into its containing package, and it preserves
a single canonical import path for every public symbol.

Importing :mod:`app.services` itself is a side-effect-free no-op:
it does not read environment variables, construct GCP clients,
configure logging, perform network I/O, or pull in any heavyweight
machine-learning libraries.  This guarantee keeps the package safe
to import in unit tests, in environments lacking GCP credentials,
and during Flask application startup before configuration has been
finalised.
"""

# Explicit empty ``__all__`` documents that this package re-exports no
# names of its own.  All public symbols live in the submodules and must
# be imported from there directly (see the docstring above).  This
# mirrors the pattern used by :mod:`app.utils` for symmetry across the
# ``app`` namespace.
__all__: tuple[str, ...] = ()
