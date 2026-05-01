"""Pytest tests for the ``app.services`` business-logic modules.

This subpackage contains unit tests for the service-layer modules in
:mod:`app.services`:

* :mod:`tests.test_services.test_pipeline_service` -- Unit tests for
  :class:`app.services.pipeline_service.PipelineService`.  Verifies
  the orchestration logic that wraps the LangGraph reverse file
  mapping pipeline.  All external dependencies (Neo4j, GCS, PubSub,
  LLM APIs, LangGraph, LangSmith, MCP servers, Figma) are mocked via
  the ``mock_pipeline_internals`` fixture from
  :mod:`tests.conftest`.

The corresponding HTTP-level tests (which exercise the Flask routes
end-to-end with ``PipelineService`` mocked) live in
:mod:`tests.test_routes`.  Together, the two subpackages provide
balanced coverage:

* ``test_routes`` -- HTTP request/response behaviour, validation,
  status codes, background-thread dispatch.
* ``test_services`` -- Business-logic orchestration, pipeline
  invocation, resource lifecycle, error propagation.

Shared pytest fixtures (the ``app`` fixture, mock factories, sample
payloads, the ``wait_for_call`` helper) are defined in
:mod:`tests.conftest`.  Pytest discovers ``conftest.py`` files
automatically; tests do NOT need to import fixtures explicitly.
"""
