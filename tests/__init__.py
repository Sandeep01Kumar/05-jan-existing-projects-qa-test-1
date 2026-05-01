"""Pytest test suite for the archie-job-reverse-file-mapper Flask application.

This package contains automated tests for the Flask migration of the
reverse file mapping pipeline.  It replaces the manual trigger
scripts (``main.test.py`` and ``retry.test.py``) that were deleted
during the Flask migration.

Subpackages:

* :mod:`tests.test_routes` -- Tests for HTTP route Blueprints in
  ``app.routes`` (``/api/generate``, ``/api/update``, ``/health``,
  ``/ready``, ``/api/traces/<run_id>``).  These tests use the
  ``client`` fixture from ``pytest-flask`` to issue HTTP requests
  against the Flask test client.
* :mod:`tests.test_services` -- Unit tests for service-layer modules
  in ``app.services`` (most importantly :class:`PipelineService`).
  These tests mock all external services (Neo4j, GCS, PubSub, LLM
  APIs) and verify the orchestration logic in isolation.

Shared fixtures (the ``app`` fixture, mock factories, sample
payloads) are defined in :mod:`tests.conftest`.  Pytest discovers
``conftest.py`` files automatically; tests do NOT need to import
fixtures explicitly.

Run the test suite with::

    pytest tests/

Or with coverage::

    pytest --cov=app --cov-report=html tests/
"""
