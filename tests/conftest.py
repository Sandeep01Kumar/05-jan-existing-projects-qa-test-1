"""Pytest fixtures for the behavioral-parity test suite.

This module provides the two pytest fixtures consumed by every test in the
``tests/`` directory tree:

* :func:`app` — A fully configured :class:`flask.Flask` application built via
  ``create_app("app.config.TestConfig")``. Selecting :class:`app.config.TestConfig`
  sets ``TESTING = True`` (see ``app/config.py``), which causes Flask to
  propagate handler exceptions into the test client (so failing assertions
  inside view functions surface as test failures rather than HTTP 500
  responses) and enables :meth:`flask.Flask.test_client` for in-process
  request simulation.
* :func:`client` — A Werkzeug-backed :class:`flask.testing.FlaskClient` bound
  to the freshly-built :func:`app` instance, used by tests to issue
  in-process HTTP requests. The returned response object exposes
  ``response.status_code`` (int), ``response.headers`` (dict-like), and
  ``response.data`` (bytes) — the three attributes that the behavioral-parity
  test suite needs in order to assert the byte-level equivalence requirements
  enumerated in AAP §0.6.1 (status ``200``, header ``Content-Type:
  text/plain``, body ``b"Hello, World!\\n"``).

Auto-discovery rationale
------------------------

pytest automatically loads ``conftest.py`` files for every test in the same
directory tree without explicit imports in the test modules. This makes the
:func:`app` and :func:`client` fixtures available to ``tests/test_app.py``
(and to any future test modules added to ``tests/``) simply by declaring them
as arguments on test functions::

    def test_get_root_returns_hello_world(client):
        response = client.get("/")
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "text/plain"
        assert response.data == b"Hello, World!\\n"

The fixture names ``app`` and ``client`` also match the conventions used by
the optional ``pytest-flask`` plugin (declared in ``requirements.txt`` per
AAP §0.5.2), so the test suite works whether or not that plugin is loaded —
defining ``app`` and ``client`` explicitly here preserves portability and
guarantees deterministic semantics regardless of plugin discovery order.

Fixture-scope rationale
-----------------------

Both fixtures use pytest's default *function* scope (i.e., a fresh app +
client are constructed for every individual test). This gives perfect test
isolation: any mutation a test makes to ``app.config``, ``app.url_map``, or
any module-level state inside the application package cannot leak into a
sibling test. The factory call ``create_app("app.config.TestConfig")`` is
cheap (no database connection, no external resource acquisition, no network
I/O) so the per-test cost is negligible — typically <10ms per fixture
instantiation on commodity hardware. Adopting ``scope="module"`` or
``scope="session"`` would couple tests, making failures harder to diagnose,
without delivering any measurable speedup for this stateless service.

References
----------

* AAP §0.2.1 (Test Suite — CREATE row ``tests/conftest.py``).
* AAP §0.3.1 (Role Specification — ``tests/conftest.py`` provides "pytest
  fixtures (``app``, ``client``) using ``create_app('app.config.TestConfig')``").
* AAP §0.4.1 (transformation row ``tests/conftest.py``).
* AAP §0.5.2 (external dependency — ``pytest==9.0.3``; upgraded at
  Checkpoint 7 final from the AAP-pinned 8.4.2 to remediate
  CVE-2025-71176 / GHSA-6w46-j5rx-g56g, following the same
  defense-in-depth precedent established for Werkzeug and python-dotenv
  at Checkpoint 3 final review).
* AAP §0.5.4 (Import Refactoring table — ``tests/**.py`` imports
  ``pytest`` and ``from app import create_app``).
* AAP §0.6.1 (Behavioral-Parity Strategy — response attributes asserted by
  consumers of the :func:`client` fixture).
* AAP §0.7.4 R-1 / R-3 / R-4 (parity rules verified by tests built on
  these fixtures).
* AAP §0.8.5 (Citation Discipline).
"""

# ---------------------------------------------------------------------------
# Module-level imports
# ---------------------------------------------------------------------------
#
# Per AAP §0.5.4 Import Refactoring table row ``tests/**.py``, this module
# imports exactly two symbols:
#
#   * :mod:`pytest`            — provides the ``@pytest.fixture`` decorator
#                                used to declare the fixtures below
#                                (``pytest==9.0.3``; upgraded at Checkpoint
#                                7 final from the AAP §0.5.2 baseline of
#                                8.4.2 to remediate CVE-2025-71176 /
#                                GHSA-6w46-j5rx-g56g).
#   * :func:`app.create_app`   — the Flask application factory exposed by
#                                ``app/__init__.py``'s ``__all__``
#                                (AAP §0.5.4 internal import).
#
# Intentionally NOT imported here:
#
#   * :mod:`flask` (the class :class:`flask.Flask` and the
#     :class:`flask.testing.FlaskClient` type) — fixtures don't need direct
#     access to the Flask classes; :func:`create_app` already returns a
#     concrete :class:`flask.Flask` instance and ``app.test_client()``
#     returns a :class:`flask.testing.FlaskClient`. Importing them would
#     create a redundant dependency and clutter the module surface.
#   * :mod:`os` — environment-variable access is concentrated in
#     :mod:`app.config` per AAP §0.5.4. Keeping this module env-free makes
#     the fixtures deterministic across CI runners and developer machines.
#   * :class:`app.config.TestConfig` (or any concrete config class) — the
#     factory accepts a dotted-path *string* (``"app.config.TestConfig"``)
#     and uses :func:`importlib.import_module` to load the class lazily
#     (see ``app/__init__.py``). Passing the string avoids a direct import
#     here, which keeps the conftest decoupled from ``app.config`` and
#     side-steps any potential circular-import scenarios that could arise
#     if ``app.config`` were ever to need test-time helpers.
# ---------------------------------------------------------------------------
import pytest

from app import create_app


# ---------------------------------------------------------------------------
# The ``app`` fixture — produces a fresh, fully-configured Flask app per test.
# ---------------------------------------------------------------------------
#
# Per AAP §0.3.1 Role Specification:
#   ``app`` (``create_app("app.config.TestConfig")``)
#
# Decorator choice — ``@pytest.fixture`` (NOT ``@pytest.fixture(scope=...)``):
#   The bare decorator is equivalent to ``@pytest.fixture(scope="function")``
#   which is the correct scope for this fixture per the module docstring's
#   "Fixture-scope rationale" section. Setting ``scope="module"`` or
#   ``scope="session"`` would couple tests by sharing the same app across
#   them — undesirable for parity tests that may need to verify config
#   isolation, register transient blueprints, or assert idempotency.
#
# Generator pattern — ``yield app`` (NOT ``return app``):
#   pytest interprets the presence of ``yield`` as a generator-style fixture
#   so that any code placed after the ``yield`` runs as teardown. The
#   current Hello-World service has no teardown to perform (the test client
#   automatically releases its resources when garbage-collected, and the
#   :class:`flask.Flask` instance holds no open files, sockets, or DB
#   handles), but using ``yield`` here leaves room for future teardown
#   (e.g., closing a database pool) without changing the fixture signature
#   and breaking every test that depends on it. The ergonomic cost of
#   ``yield`` vs. ``return`` is zero in modern pytest.
#
# Dotted-path argument — ``"app.config.TestConfig"`` (NOT a direct class
# reference like ``from app.config import TestConfig; create_app(TestConfig)``):
#   The factory in ``app/__init__.py`` accepts a string and resolves it via
#   :func:`importlib.import_module` + :func:`getattr`. This indirection
#   matches the production code path (where ``wsgi.py`` reads
#   ``FLASK_CONFIG`` from the environment as a string), making the fixture
#   exercise the same loading mechanism that production uses. It also
#   avoids importing :class:`app.config.TestConfig` directly into this
#   module, keeping the dependency graph minimal.
# ---------------------------------------------------------------------------
@pytest.fixture
def app():
    """Provide a Flask application built with TestConfig for testing.

    Constructs a fresh :class:`flask.Flask` instance for each test by
    invoking the application factory with the dotted-path identifier
    ``"app.config.TestConfig"``. The factory (see ``app/__init__.py``) uses
    :func:`importlib.import_module` to load :class:`app.config.TestConfig`
    and applies it via :meth:`flask.Config.from_object`, which sets
    ``TESTING = True`` on the resulting ``app.config`` mapping.

    Effects of ``TESTING = True``:

    * Exceptions raised inside view functions propagate to the test client
      so failing assertions surface as test failures (rather than being
      caught and converted to HTTP 500 responses by Flask's default error
      handler).
    * :meth:`flask.Flask.test_client` returns an in-process test client
      that bypasses the network stack — no real socket binding, no port
      ``3000`` contention, no network roundtrips. This makes the test
      suite fast (typically <100 ms for the full parity suite) and
      CI-friendly.

    Each test receives a completely independent app instance — there is
    no shared state between fixture invocations. The
    ``yield app`` pattern leaves room for future teardown logic (e.g.,
    closing database connections, removing temporary files) to be added
    after the ``yield`` without changing the fixture's public signature.

    The fixture is intentionally function-scoped (pytest's default scope
    when no ``scope=`` argument is passed to ``@pytest.fixture``). Per-test
    isolation is the correct default for parity tests because it prevents
    accidental cross-test state leakage and matches the stateless behavior
    of the retired Node.js service (``server.js:L6-L10``).

    Yields:
        flask.Flask: A fully configured Flask application instance with
        ``TESTING = True``, the :data:`app.routes.main.main_bp` catch-all
        blueprint registered, logging configured, and middleware hooks
        installed — ready for use with :meth:`flask.Flask.test_client`.
    """
    # ----------------------------------------------------------------------
    # Build the Flask app via the application factory.
    #
    # The dotted-path string ``"app.config.TestConfig"`` is the contract
    # documented in:
    #
    #   * AAP §0.3.1 Role Specification — verbatim value
    #     ``create_app("app.config.TestConfig")``.
    #   * AAP §0.4.1 transformation row ``tests/conftest.py`` —
    #     "Set up pytest fixtures (``app``, ``client``) using
    #     ``create_app('app.config.TestConfig')``".
    #   * ``app/config.py`` — defines :class:`TestConfig` with
    #     ``TESTING = True`` and a deterministic ``SECRET_KEY``.
    #   * ``app/__init__.py`` — defines :func:`create_app` whose
    #     ``config_object`` parameter accepts dotted-path strings.
    #
    # ``create_app`` triggers:
    #
    #   1. ``Flask(__name__, static_folder=None)`` — fresh Flask instance.
    #   2. ``importlib.import_module("app.config")`` + ``getattr(...,
    #      "TestConfig")`` + ``app.config.from_object(TestConfig)`` —
    #      populates the config mapping with ``TESTING = True`` and the
    #      ``HOST=127.0.0.1`` / ``PORT=3000`` parity defaults.
    #   3. :func:`app.logging_config.configure_logging` — attaches the
    #      structured StreamHandler to ``app.logger``.
    #   4. :func:`app.middleware.register_hooks` — installs the
    #      ``before_request`` / ``after_request`` / ``errorhandler``
    #      decorator-based middleware.
    #   5. :meth:`flask.Flask.register_blueprint` for
    #      :data:`app.routes.main.main_bp` — wires up the catch-all
    #      Hello-World routes that the parity tests will exercise.
    #   6. A startup-banner ``app.logger.info(...)`` call — semantically
    #      equivalent to the retired ``console.log`` from ``server.js:L13``.
    #
    # All six steps complete synchronously and return the fully-wired
    # :class:`flask.Flask` instance before this fixture yields. Tests can
    # immediately call :meth:`flask.Flask.test_client` via the ``client``
    # fixture below.
    # ----------------------------------------------------------------------
    app = create_app("app.config.TestConfig")

    # ----------------------------------------------------------------------
    # Hand the freshly-built app off to the requesting test.
    #
    # Using ``yield`` (not ``return``) lets future teardown logic be added
    # below this line without changing this fixture's external behavior.
    # Current teardown requirements: NONE. The :class:`flask.Flask`
    # instance holds no open file handles, no live network sockets, and no
    # background threads — Python's garbage collector will reclaim it
    # automatically when the last reference (the test function and the
    # ``client`` fixture below) goes out of scope at the end of the test.
    #
    # No ``app.app_context()`` or ``app.test_request_context()`` push is
    # performed here — the test client (see the ``client`` fixture below)
    # manages those contexts automatically for each request it dispatches.
    # Pre-pushing a context here would unnecessarily widen the scope and
    # could mask context-handling bugs in the application code.
    # ----------------------------------------------------------------------
    yield app


# ---------------------------------------------------------------------------
# The ``client`` fixture — produces a Flask test client bound to the ``app``.
# ---------------------------------------------------------------------------
#
# Per AAP §0.3.1 Role Specification:
#   ``client`` (``app.test_client()``)
#
# Fixture dependency — ``def client(app):``:
#   pytest injects fixtures by argument name. Declaring ``app`` as a
#   parameter triggers the ``app`` fixture above and binds the resulting
#   :class:`flask.Flask` instance to the local variable. The dependency
#   arrow is ``client -> app``, so every test that requests ``client``
#   transitively gets a fresh ``app`` too — preserving the per-test
#   isolation guarantee documented in the module docstring.
#
# Function scope — implicit via ``@pytest.fixture``:
#   Matches the ``app`` fixture's scope. Setting a wider scope here would
#   be meaningless because the wider-scoped client would reference the
#   narrower-scoped (function-scope) ``app`` and pytest would refuse to
#   resolve the dependency. The default scope is the right choice.
#
# Plain ``return`` (not a context-manager ``with`` block):
#   In Flask 3.x, :meth:`flask.Flask.test_client` returns a
#   :class:`flask.testing.FlaskClient` that does NOT require an explicit
#   cleanup phase under normal usage. The ``with`` form is reserved for
#   scenarios where a test needs to manipulate the session cookie via
#   ``client.session_transaction()``; parity tests do not exercise
#   sessions (the Hello-World handler returns no cookies and reads no
#   session state), so the plain ``return`` form is sufficient and
#   slightly more ergonomic. Each request the test issues automatically
#   pushes its own request context for the duration of that request.
# ---------------------------------------------------------------------------
@pytest.fixture
def client(app):
    """Provide a Flask test client for issuing in-process HTTP requests.

    Returns a :class:`flask.testing.FlaskClient` bound to the
    ``app`` fixture. The test client dispatches requests directly to the
    Flask WSGI application in-process — no real socket binding, no port
    contention, and no network roundtrips. This makes test execution fast
    and removes the operational coupling between the test suite and the
    host's TCP port availability (the retired Node.js server bound to
    ``127.0.0.1:3000`` per ``server.js:L3-L4``, but the test client does
    not require port ``3000`` to be free).

    Common request methods supported:

    * ``client.get(url)``, ``client.post(url)``, ``client.put(url)``,
      ``client.delete(url)``, ``client.patch(url)``, ``client.head(url)``,
      ``client.options(url)`` — method-specific convenience helpers that
      issue a request and return the :class:`werkzeug.test.TestResponse`.
    * ``client.open(url, method=...)`` — generic dispatcher used by
      parametrized tests (e.g., the method-agnostic dispatch verification
      that satisfies AAP rule R-3).

    Each response object exposes the three attributes that the
    behavioral-parity assertions in :mod:`tests.test_app` rely on:

    * ``response.status_code`` (int) — verifies the HTTP status. Parity
      tests assert ``response.status_code == 200`` per AAP §0.6.1 row 1
      and AAP rule R-1 (mirrors ``server.js:L7`` — ``res.statusCode = 200;``).
    * ``response.headers`` (:class:`werkzeug.datastructures.Headers`,
      dict-like) — verifies the response headers. Parity tests assert
      ``response.headers["Content-Type"] == "text/plain"`` (no
      ``charset`` suffix) per AAP §0.6.1 row 2 and the caveat noted there
      (Flask appends ``; charset=utf-8`` to text mimetypes by default;
      the handler in ``app/routes/main.py`` deliberately uses an explicit
      ``headers={"Content-Type": "text/plain"}`` mapping to avoid that
      suffix and preserve byte parity with ``server.js:L8`` —
      ``res.setHeader('Content-Type', 'text/plain');``).
    * ``response.data`` (bytes) — verifies the response body. Parity
      tests assert ``response.data == b"Hello, World!\\n"`` per AAP §0.6.1
      row 3 and AAP rule R-1 (mirrors ``server.js:L9`` —
      ``res.end('Hello, World!\\n');``).

    Args:
        app (flask.Flask): Injected by pytest from the :func:`app`
            fixture above. Each test gets a fresh, isolated Flask
            instance with ``TESTING = True``.

    Returns:
        flask.testing.FlaskClient: A test client bound to the ``app``
        fixture, ready for tests to issue in-process HTTP requests
        against the catch-all Hello-World blueprint.
    """
    # ----------------------------------------------------------------------
    # Construct the test client.
    #
    # :meth:`flask.Flask.test_client` returns a new
    # :class:`flask.testing.FlaskClient` each time it is called. The
    # client is bound to the ``app`` argument's WSGI callable: every
    # request the client dispatches passes through the same routing,
    # middleware, and view stack that gunicorn would invoke for a real
    # HTTP request in production. This makes the test suite a faithful
    # parity check for the production code path.
    #
    # Returning the client directly (instead of yielding it) is the
    # idiomatic pytest pattern when no teardown is required. The Flask
    # test client in 3.x cleans up after itself when the last reference
    # is released — no explicit close, no context-manager exit handler
    # required.
    # ----------------------------------------------------------------------
    return app.test_client()
