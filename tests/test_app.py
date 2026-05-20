"""Behavioral-parity tests for the hao-backprop-test Flask service.

Asserts byte-level HTTP-response parity between the new Python/Flask service
and the retired Node.js implementation (``server.js:L1-L14``). The Node
handler returned the same response to every caller — it never inspected
``req.method`` and never inspected ``req.url`` (``server.js:L6-L10``):

  * **Status**: ``200`` — mirrors ``res.statusCode = 200`` from
    ``server.js:L7`` (AAP §0.6.1 row 1).
  * **Content-Type**: ``text/plain`` (bare token, **no** ``; charset=utf-8``
    suffix) — mirrors ``res.setHeader('Content-Type', 'text/plain')`` from
    ``server.js:L8`` (AAP §0.6.1 row 2 and caveat).
  * **Body**: ``b"Hello, World!\\n"`` — mirrors ``res.end('Hello, World!\\n')``
    from ``server.js:L9``; the trailing newline (``\\n``, ASCII ``0x0A``) is
    mandatory per AAP rule R-1.
  * **Method coverage**: every HTTP method must reach the handler — AAP
    rule R-3 (the Node handler did not inspect ``req.method``).
  * **Path coverage**: every URL path must reach the handler — AAP rule
    R-4 (the Node handler did not inspect ``req.url``).

This module is the single authoritative source of behavioral-parity
verification per AAP §0.2.1 (Test Suite — CREATE), §0.3.1 (Role
Specification table row ``tests/test_app.py``), §0.4.1 (transformation
row ``tests/test_app.py``), §0.6.1 (Response Byte-Equivalence
Requirements table), §0.6.2 (Catch-All Routing Strategy in Flask), and
the parity rules R-1, R-3, R-4 from §0.7.4.

Fixture provenance
------------------

The ``client`` parameter on every test function is the
:class:`flask.testing.FlaskClient` produced by the ``client`` fixture in
``tests/conftest.py``. That fixture builds a fresh app via
``create_app("app.config.TestConfig")`` for each test (function-scope) and
calls ``app.test_client()`` on it — the test client dispatches requests
in-process (bypassing real sockets), so the suite runs fast and does not
require TCP port ``3000`` to be free. pytest auto-discovers
``conftest.py`` and injects the fixture by parameter name; no explicit
Python ``import`` of ``client`` is required (or possible).

Per AAP §0.5.4 Import Refactoring table row ``tests/**.py``:
:mod:`pytest` is the only third-party import this module needs (it
provides the ``@pytest.mark.parametrize`` decorator used to drive the
method- and path-parametrized tests).
"""

# ---------------------------------------------------------------------------
# Module-level imports
# ---------------------------------------------------------------------------
#
# Per AAP §0.5.4 Import Refactoring table row ``tests/**.py``, this module
# imports exactly one third-party symbol:
#
#   * :mod:`pytest` — provides ``@pytest.mark.parametrize`` for the
#     method-parametrized ``test_all_methods_return_same_body`` (AAP rule
#     R-3) and the path-parametrized ``test_arbitrary_paths_return_same_body``
#     (AAP rule R-4). pytest is also the test runner that auto-discovers
#     ``tests/conftest.py`` and injects the ``client`` fixture by parameter
#     name.
#
# Intentionally NOT imported here:
#
#   * :mod:`flask`, :func:`app.create_app`, :class:`app.config.TestConfig`
#     — these are used only by the conftest fixture builder, not by tests.
#     Tests interact with the application exclusively through the
#     ``client`` fixture's HTTP-style API (``.get``, ``.post``, ``.open``,
#     etc.) and the response object's ``.status_code``, ``.headers``,
#     and ``.data`` attributes.
#   * :mod:`os` — no environment-variable access is needed; the
#     deterministic ``TestConfig`` selected by the conftest fixture makes
#     this module independent of ``.env`` files and OS-level environment.
#   * Any HTTP client library (``requests``, ``httpx``, etc.) — the
#     in-process Flask test client supersedes them and avoids the
#     operational cost of binding a real socket on port ``3000``.
# ---------------------------------------------------------------------------
import pytest


# ---------------------------------------------------------------------------
# Parity-expectation constants — sourced from server.js:L7-L9 byte-for-byte.
# ---------------------------------------------------------------------------
#
# These constants are the SINGLE SOURCE OF TRUTH for behavioral parity in
# this test module. Each constant maps to a specific line of the retired
# Node implementation and to a specific row of AAP §0.6.1 Response
# Byte-Equivalence Requirements. A mismatch between any constant and the
# corresponding response attribute returned by the Flask app indicates a
# parity break (AAP rule R-1).
# ---------------------------------------------------------------------------

# Mirrors ``res.statusCode = 200;`` from ``server.js:L7``.
# Per AAP §0.6.1 row 1: the Flask service must respond with HTTP status
# ``200`` for every request. Flask's default is also ``200``, but
# ``app/routes/main.py`` constructs the :class:`flask.Response` with
# ``status=200`` explicitly so the value is independent of framework
# defaults.
EXPECTED_STATUS: int = 200

# Mirrors ``res.setHeader('Content-Type', 'text/plain');`` from
# ``server.js:L8``.
#
# CRITICAL: this is the BARE token ``text/plain`` with NO
# ``; charset=utf-8`` suffix. Per AAP §0.6.1 caveat and AAP §0.6.6 risk
# #1, Flask's default behavior when ``mimetype="text/plain"`` (or
# ``content_type="text/plain"``) is passed to :class:`flask.Response` is
# to append ``; charset=utf-8`` to the header value. That suffix is
# semantically equivalent for ASCII payloads but is a literal-byte
# divergence from the Node ``res.setHeader('Content-Type', 'text/plain')``
# emission. The route in ``app/routes/main.py`` explicitly uses
# ``headers={"Content-Type": "text/plain"}`` to bypass Werkzeug's mimetype
# auto-extension, preserving the bare token; this test asserts the bare
# token to lock that behavior in regression-test form.
EXPECTED_CONTENT_TYPE: str = "text/plain"

# Mirrors ``res.end('Hello, World!\n');`` from ``server.js:L9``.
#
# CRITICAL: includes the trailing newline (``\n``, ASCII ``0x0A``) — per
# AAP rule R-1 (§0.7.4), the trailing newline is mandatory. Total length
# is 14 bytes: ``H e l l o , [space] W o r l d ! [\n]``. Returning
# ``b"Hello, World!"`` (no newline) or ``b"Hello, World!\r\n"`` (CRLF)
# would both violate parity.
EXPECTED_BODY: bytes = b"Hello, World!\n"

# AAP rule R-3 (§0.7.4) — every HTTP method must reach the handler.
#
# The Node ``http.createServer`` callback never filtered on ``req.method``
# (``server.js:L6-L10``), so every method received the identical response.
# Flask requires explicit enumeration because the default route accepts
# only ``GET`` (non-``GET`` requests would otherwise yield ``405 Method
# Not Allowed``, violating parity).
#
# The list mirrors ``ALL_METHODS`` in ``app/routes/main.py`` exactly,
# both in contents and in order. Maintaining the order makes parametrized
# test IDs deterministic across runs and aids diff comparisons.
#
# ``TRACE`` and ``CONNECT`` are intentionally excluded — they are
# exceedingly rare in practice and are not enumerated by AAP §0.6.2;
# including them would expand scope beyond the documented contract.
ALL_METHODS: list[str] = [
    "GET",
    "POST",
    "PUT",
    "DELETE",
    "PATCH",
    "HEAD",
    "OPTIONS",
]

# AAP rule R-4 (§0.7.4) — every URL path must reach the handler.
#
# The Node ``http.createServer`` callback never inspected ``req.url``
# (``server.js:L6-L10``), so every path received the identical response.
# Flask routes match path patterns explicitly; the catch-all blueprint in
# ``app/routes/main.py`` registers TWO routes — ``"/"`` and
# ``"/<path:subpath>"`` — to cover every reachable URL. The
# ``<path:subpath>`` converter (NOT the default ``<string:subpath>``)
# matches text including forward slashes, so deeply-nested paths like
# ``/a/b/c/d`` resolve to the same handler.
#
# Path depths covered:
#   * ``"/"``        — depth 0; exercises the root route registration.
#   * ``"/foo"``     — depth 1; exercises ``<path:subpath>`` with one segment.
#   * ``"/any/path"``— depth 2; exercises slash matching inside ``<path:>``.
#   * ``"/a/b/c"``   — depth 3; further validates nested slash matching.
#   * ``"/x/y/z/w"`` — depth 4; deeper nesting to ensure no depth limit.
#
# AAP §0.6.2 documents the rationale for the two-route registration; this
# list ensures the parametrized test exercises BOTH the root route AND
# the ``<path:subpath>`` converter at varying depths.
ALL_PATHS: list[str] = [
    "/",
    "/foo",
    "/any/path",
    "/a/b/c",
    "/x/y/z/w",
]


# ---------------------------------------------------------------------------
# Test 1 — Status code parity (AAP §0.6.1 row 1, rule R-1)
# ---------------------------------------------------------------------------
def test_status_is_200(client) -> None:
    """``GET /`` returns status code ``200``.

    Mirrors ``res.statusCode = 200;`` from ``server.js:L7``. Per AAP
    §0.6.1 row 1 and rule R-1 (§0.7.4): the HTTP status of the response
    must be exactly the integer ``200`` — neither ``201``, ``204``, nor
    a redirect or error status is acceptable.

    The ``client`` fixture is auto-injected by pytest from
    ``tests/conftest.py``. It is a :class:`flask.testing.FlaskClient`
    backed by ``app.test_client()`` on a fresh Flask app built via
    ``create_app("app.config.TestConfig")``. The ``.get("/")`` call
    issues an in-process HTTP request — no real socket binding is
    performed, so this test runs without requiring port ``3000`` to be
    free.

    Args:
        client: Flask test client fixture from
            ``tests/conftest.py::client``. Pytest matches the parameter
            name ``client`` to the fixture function of the same name.
    """
    response = client.get("/")
    assert response.status_code == EXPECTED_STATUS, (
        f"Expected status {EXPECTED_STATUS}, got {response.status_code}"
    )


# ---------------------------------------------------------------------------
# Test 2 — Content-Type header parity (AAP §0.6.1 row 2, rule R-1)
# ---------------------------------------------------------------------------
def test_content_type_is_text_plain(client) -> None:
    """Response ``Content-Type`` header is exactly ``text/plain`` (no charset).

    Mirrors ``res.setHeader('Content-Type', 'text/plain');`` from
    ``server.js:L8``. Per AAP §0.6.1 row 2 and the caveat noted there
    (AAP §0.6.6 risk #1), the header must NOT include the
    ``; charset=utf-8`` suffix that Flask appends by default when
    ``mimetype="text/plain"`` or ``content_type="text/plain"`` is used.

    The route in ``app/routes/main.py`` constructs the
    :class:`flask.Response` with ``headers={"Content-Type": "text/plain"}``
    explicitly to bypass Werkzeug's mimetype auto-extension and preserve
    the bare-token byte form emitted by Node's
    ``res.setHeader('Content-Type', 'text/plain')``. This test pins that
    behavior so any regression that switches the route back to
    ``mimetype=`` / ``content_type=`` is detected immediately.

    Args:
        client: Flask test client fixture from
            ``tests/conftest.py::client``.
    """
    response = client.get("/")
    assert response.headers["Content-Type"] == EXPECTED_CONTENT_TYPE, (
        f"Expected Content-Type {EXPECTED_CONTENT_TYPE!r}, "
        f"got {response.headers['Content-Type']!r}"
    )


# ---------------------------------------------------------------------------
# Test 3 — Response body parity (AAP §0.6.1 row 3, rule R-1)
# ---------------------------------------------------------------------------
def test_body_bytes_match(client) -> None:
    """Response body is byte-exact ``b'Hello, World!\\n'`` (with trailing newline).

    Mirrors ``res.end('Hello, World!\\n');`` from ``server.js:L9``. Per
    AAP §0.6.1 row 3 and rule R-1 (§0.7.4), the body bytes must be
    exactly ``b"Hello, World!\\n"`` — 14 bytes total, including the
    trailing newline (``\\n``, ASCII ``0x0A``). Omitting the newline,
    using CRLF (``\\r\\n``), or any character-encoding alteration would
    constitute a parity break.

    The comparison is performed on ``response.data`` (raw bytes) rather
    than ``response.get_data(as_text=True)`` (decoded string) to ensure
    a byte-exact match irrespective of how the framework spells the
    response payload internally. This catches encoding drift, BOM
    insertion, or trailing-whitespace mutations that a string comparison
    might silently tolerate.

    Args:
        client: Flask test client fixture from
            ``tests/conftest.py::client``.
    """
    response = client.get("/")
    assert response.data == EXPECTED_BODY, (
        f"Expected body {EXPECTED_BODY!r}, got {response.data!r}"
    )


# ---------------------------------------------------------------------------
# Test 4 — Method-agnostic dispatch (AAP §0.6.1 row 4, rule R-3)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("method", ALL_METHODS)
def test_all_methods_return_same_body(client, method: str) -> None:
    """Every HTTP method receives the parity-preserving response.

    Per AAP rule R-3 (§0.7.4 — method-agnostic dispatch) and §0.6.2
    (Catch-All Routing Strategy in Flask): the retired Node handler did
    not inspect ``req.method`` (``server.js:L6-L10``), so every HTTP
    method must produce identical wire-format responses (status ``200``,
    ``Content-Type: text/plain``).

    The list of methods exercised — ``GET``, ``POST``, ``PUT``,
    ``DELETE``, ``PATCH``, ``HEAD``, ``OPTIONS`` — mirrors ``ALL_METHODS``
    in ``app/routes/main.py`` verbatim; both decorators on the
    ``hello_world`` view function pass ``methods=ALL_METHODS`` to
    register the same handler under each method.

    HEAD-method nuance (RFC 7231 §4.3.2): the HEAD method requests the
    same headers as a corresponding GET but mandates that the server
    "MUST NOT send a message body in the response." Flask honors this
    by automatically stripping the body from HEAD responses (it
    dispatches HEAD to the GET handler and then discards the body
    before transmission). Consequently, ``response.data`` for a HEAD
    request is ``b""`` (empty), NOT ``b"Hello, World!\\n"``. This is
    correct, standards-compliant behavior — not a parity break — and
    the test branches accordingly to assert the expected empty body for
    HEAD while preserving the strict byte-exact body assertion for all
    other methods.

    Args:
        client: Flask test client fixture from
            ``tests/conftest.py::client``.
        method: HTTP method name (uppercase) injected by
            :func:`pytest.mark.parametrize` from :data:`ALL_METHODS`.
            One test instance is generated per method, yielding
            parametrized test IDs of the form
            ``test_all_methods_return_same_body[GET]``,
            ``test_all_methods_return_same_body[POST]``, etc.
    """
    # Use the generic ``client.open(url, method=method)`` dispatcher
    # instead of the method-specific helpers (``client.get``,
    # ``client.post``, …) because ``method`` is a runtime variable.
    # ``open`` accepts any method string and routes it through the same
    # WSGI call path the helpers use, so behavior is identical.
    response = client.open("/", method=method)

    # Status parity — every method returns ``200``.
    assert response.status_code == EXPECTED_STATUS, (
        f"{method} /: expected status {EXPECTED_STATUS}, "
        f"got {response.status_code}"
    )

    # Content-Type parity — every method returns the bare ``text/plain``
    # token. (HEAD responses have headers identical to GET per RFC 7231
    # §4.3.2; only the body is stripped.)
    assert response.headers["Content-Type"] == EXPECTED_CONTENT_TYPE, (
        f"{method} /: expected Content-Type {EXPECTED_CONTENT_TYPE!r}, "
        f"got {response.headers['Content-Type']!r}"
    )

    # Body parity — every method except HEAD returns
    # ``b"Hello, World!\n"``. HEAD's body is stripped to ``b""`` by Flask
    # per HTTP spec (RFC 7231 §4.3.2: "The HEAD method is identical to
    # GET except that the server MUST NOT send a message body in the
    # response."). This branch acknowledges the spec-mandated behavior
    # rather than treating it as a failure.
    if method == "HEAD":
        assert response.data == b"", (
            f"HEAD /: expected empty body per HTTP spec (RFC 7231 §4.3.2), "
            f"got {response.data!r}"
        )
    else:
        assert response.data == EXPECTED_BODY, (
            f"{method} /: expected body {EXPECTED_BODY!r}, "
            f"got {response.data!r}"
        )


# ---------------------------------------------------------------------------
# Test 5 — Path-agnostic dispatch (AAP §0.6.1 row 5, rule R-4)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("path", ALL_PATHS)
def test_arbitrary_paths_return_same_body(client, path: str) -> None:
    """Every URL path receives the parity-preserving response.

    Per AAP rule R-4 (§0.7.4 — path-agnostic dispatch) and §0.6.2
    (Catch-All Routing Strategy in Flask): the retired Node handler did
    not inspect ``req.url`` (``server.js:L6-L10``), so every URL path —
    including deeply-nested ones like ``/a/b/c/d`` — must produce
    identical responses.

    The ``app/routes/main.py`` blueprint stacks TWO ``@main_bp.route``
    decorators on the same handler:

    * ``@main_bp.route("/", methods=ALL_METHODS)`` — for the root path.
    * ``@main_bp.route("/<path:subpath>", methods=ALL_METHODS)`` — for
      every other URL. The ``<path:subpath>`` converter (NOT
      ``<string:subpath>``) matches text INCLUDING slashes, so nested
      URLs of arbitrary depth all reach the same view function.

    Using ``<string:subpath>`` (Flask's default ``<variable>`` converter)
    would match only one path segment and would 404 on requests like
    ``GET /a/b/c``, breaking AAP rule R-4. The ``path:`` converter is a
    parity requirement, not a convenience choice.

    Path-depth coverage rationale:

    * ``"/"`` (depth 0)        — exercises the explicit root route.
    * ``"/foo"`` (depth 1)     — exercises ``<path:subpath>`` with one segment.
    * ``"/any/path"`` (depth 2)— exercises slash matching in ``<path:>``.
    * ``"/a/b/c"`` (depth 3)   — further validates nested slash matching.
    * ``"/x/y/z/w"`` (depth 4) — deeper nesting to ensure no depth limit.

    Args:
        client: Flask test client fixture from
            ``tests/conftest.py::client``.
        path: URL path injected by :func:`pytest.mark.parametrize` from
            :data:`ALL_PATHS`. One test instance is generated per path,
            yielding parametrized test IDs of the form
            ``test_arbitrary_paths_return_same_body[/]``,
            ``test_arbitrary_paths_return_same_body[/foo]``, etc.
    """
    response = client.get(path)

    # Status parity — every path returns ``200``.
    assert response.status_code == EXPECTED_STATUS, (
        f"GET {path}: expected status {EXPECTED_STATUS}, "
        f"got {response.status_code}"
    )

    # Content-Type parity — every path returns the bare ``text/plain`` token.
    assert response.headers["Content-Type"] == EXPECTED_CONTENT_TYPE, (
        f"GET {path}: expected Content-Type {EXPECTED_CONTENT_TYPE!r}, "
        f"got {response.headers['Content-Type']!r}"
    )

    # Body parity — every path returns ``b"Hello, World!\n"`` byte-exact.
    assert response.data == EXPECTED_BODY, (
        f"GET {path}: expected body {EXPECTED_BODY!r}, "
        f"got {response.data!r}"
    )
