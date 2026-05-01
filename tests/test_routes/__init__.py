"""Pytest tests for the ``app.routes`` HTTP route Blueprints.

This subpackage contains pytest-based tests for each Flask Blueprint
registered under :mod:`app.routes`:

* :mod:`tests.test_routes.test_generate` -- Tests for the
  ``POST /api/generate`` endpoint.  Verifies request validation
  (``company_id`` required), the ``mode="generate"`` response, the
  background-thread pipeline dispatch, and that
  :meth:`PipelineService.run_generate` is invoked (NOT ``run_update``).

* :mod:`tests.test_routes.test_update` -- Tests for the
  ``POST /api/update`` endpoint.  Verifies the structural symmetry
  with ``/api/generate`` plus the ``mode="update"`` response and that
  :meth:`PipelineService.run_update` is invoked (NOT ``run_generate``).

* :mod:`tests.test_routes.test_health` -- Tests for the ``GET /health``
  (liveness) and ``GET /ready`` (readiness) probes used by Cloud Run
  for container lifecycle management.  Verifies the readiness check
  reports 503 when extensions or required configuration are missing.

The corresponding service-layer unit tests (which exercise
:class:`PipelineService` directly with all external dependencies
mocked) live in :mod:`tests.test_services`.  Together, the two
subpackages provide balanced coverage:

* ``test_routes`` -- HTTP request/response behaviour, validation,
  status codes, background-thread dispatch.
* ``test_services`` -- Business-logic orchestration, pipeline
  invocation, resource lifecycle, error propagation.

Shared pytest fixtures (the ``app`` fixture, ``client`` fixture from
``pytest-flask``, ``mock_pipeline_service``, ``mock_trace_service``,
``valid_generate_payload``, ``valid_update_payload``,
``minimal_valid_payload``, ``wait_for_call``) are defined in
:mod:`tests.conftest`.  Pytest discovers ``conftest.py`` files
automatically; tests do NOT need to import fixtures explicitly.

Source origin: this subpackage is conceptually derived from the
original ``retry.test.py`` (DELETED) -- a manual PubSub trigger that
fired off a hardcoded notification to the
``generate-reverse-file-map`` topic.  The new HTTP endpoints
(``/api/generate``, ``/api/update``) replace that PubSub trigger;
these route tests exercise the equivalent paths via the Flask test
client.
"""
