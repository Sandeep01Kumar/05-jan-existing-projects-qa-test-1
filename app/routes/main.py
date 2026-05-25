"""Main Flask blueprint for the hao-backprop-test service.

Encapsulates the single catch-all "Hello, World!" route that replaces the
retired Node.js ``http.createServer((req, res) => {...})`` callback from
``server.js:L6-L10``. Two route decorators (``/`` and ``/<path:subpath>``)
share one handler so every URL path reaches the same code, matching the
Node implementation's disregard for ``req.url`` (AAP rule R-4).

The handler returns a :class:`flask.Response` with status ``200``, header
``Content-Type: text/plain`` (no charset suffix — AAP §0.6.1 caveat),
and body ``b"Hello, World!\\n"`` (with trailing newline — AAP rule R-1),
byte-for-byte equivalent to what ``server.js:L7-L9`` emitted::

    res.statusCode = 200;                             // server.js:L7
    res.setHeader('Content-Type', 'text/plain');      // server.js:L8
    res.end('Hello, World!\\n');                       // server.js:L9

The list of accepted HTTP methods is enumerated explicitly via
:data:`ALL_METHODS` to satisfy AAP rule R-3 (the Node handler accepted all
methods because it never inspected ``req.method``; Flask requires explicit
enumeration since the default route allows only ``GET``).

Express analogue (AAP §0.6.4 — Express → Flask mapping)::

    const router = express.Router();
    router.all('/*', (req, res) =>
        res.type('text/plain').send('Hello, World!\\n'));

References
----------
* AAP §0.2.1 (rule-mandated CREATE), §0.3.1 (Role Specification table row
  ``app/routes/main.py``), §0.3.3 (Design Pattern Applications — Blueprint),
  §0.4.1 (transformation row ``app/routes/main.py``), §0.5.4 (Import
  Refactoring), §0.6.1 (Behavioral-Parity Strategy), §0.6.2 (Catch-All
  Routing Strategy in Flask), §0.6.4 (Express → Flask mapping table —
  Router and Route registration rows), §0.6.6 (Cross-Cutting Risk
  Inventory), §0.7.4 rules R-1, R-3, R-4.
"""

from flask import Blueprint, Response


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------
#
# Mirrors the retired Node implementation's method-agnostic dispatch
# (``server.js:L6-L10`` — ``http.createServer`` ignores ``req.method``). Per
# AAP rule R-3 (§0.7.4), every HTTP method must reach the handler. Flask's
# default route registration only accepts ``GET``, so explicit enumeration is
# required — otherwise non-``GET`` requests would receive a ``405 Method Not
# Allowed`` response, violating parity with the Node implementation.
#
# The order mirrors AAP §0.6.2 verbatim. ``TRACE`` and ``CONNECT`` are
# intentionally omitted: the Node ``http.createServer`` callback would also
# accept them (it never filters), but they are exceedingly rare in practice
# and not enumerated by the AAP — including them would expand scope beyond
# what the user requested.
ALL_METHODS: list[str] = [
    "GET",
    "POST",
    "PUT",
    "DELETE",
    "PATCH",
    "HEAD",
    "OPTIONS",
]


# ---------------------------------------------------------------------------
# Blueprint definition
# ---------------------------------------------------------------------------
#
# Express analogue (AAP §0.6.4):
#     const router = express.Router();
#
# Constructor arguments:
#   * ``"main"`` — the blueprint *name*. Flask prefixes view-function
#     endpoints with this name (so the registered endpoint is
#     ``main.hello_world``). It must match the string consumed by any caller
#     using ``url_for("main.hello_world")``.
#   * ``__name__`` — the *import name*; the standard Flask idiom that allows
#     Flask to resolve resources (templates, static files) relative to this
#     package. AAP §0.3.4 confirms there are no templates or static assets,
#     so the import name serves only its endpoint-naming role here.
#
# No ``url_prefix=`` is passed: the routes register at the application root
# (paths ``/`` and ``/<path:subpath>``) so the catch-all covers every URL.
# No ``static_folder``, ``template_folder``, or ``static_url_path`` is passed
# either — none is needed (AAP §0.3.4: the service has no UI surface).
main_bp: Blueprint = Blueprint("main", __name__)


# ---------------------------------------------------------------------------
# Catch-all "Hello, World!" handler
# ---------------------------------------------------------------------------
#
# The function is stacked with TWO ``@main_bp.route(...)`` decorators so that
# a single function body services both the root path ``/`` and every other
# URL via ``/<path:subpath>``. This matches the Node ``http.createServer``
# callback's behavior of ignoring ``req.url`` entirely (AAP rule R-4).
#
# Critical converter choice: ``<path:subpath>`` (NOT ``<string:subpath>``).
# Flask's default ``<variable>`` converter is ``string``, which matches any
# text up to (but not including) the next ``/``. The ``path`` converter
# matches text INCLUDING slashes, which is exactly what we need to capture
# nested URLs such as ``/a/b/c/d``. Without ``path:``, the request
# ``GET /a/b/c`` would reach Flask's default 404 handler instead of this
# view, violating AAP rule R-4.
@main_bp.route("/", methods=ALL_METHODS)
@main_bp.route("/<path:subpath>", methods=ALL_METHODS)
def hello_world(subpath: str = "") -> Response:
    """Return the parity-preserving 'Hello, World!' response.

    Mirrors the retired Node.js handler from ``server.js:L6-L10``
    byte-for-byte:

    * **Status code**: ``200`` — matches ``res.statusCode = 200;``
      (``server.js:L7``).
    * **Content-Type**: ``text/plain`` (no ``charset`` suffix) — matches
      ``res.setHeader('Content-Type', 'text/plain');`` (``server.js:L8``).
      Built via the explicit ``headers={"Content-Type": "text/plain"}``
      mapping rather than ``mimetype="text/plain"`` because Flask appends
      ``; charset=utf-8`` to text mimetypes by default, which would diverge
      from the Node header bytes (AAP §0.6.1 caveat, AAP §0.6.6 risk #1).
    * **Body**: ``b"Hello, World!\\n"`` — matches ``res.end('Hello, World!\\n');``
      (``server.js:L9``). The trailing newline is a parity requirement per
      AAP rule R-1 (§0.7.4) — omitting it would change the response bytes.

    The handler is intentionally method- and path-agnostic per AAP rules
    R-3 and R-4 (§0.7.4), mirroring the retired ``http.createServer``
    callback's disregard for ``req.method`` and ``req.url``. The
    ``subpath`` argument is captured by the catch-all route but never
    inspected, logged, or branched upon — doing so would diverge from the
    Node handler's stateless, content-agnostic behavior.

    Args:
        subpath: Captured by the ``<path:subpath>`` converter on the
            catch-all route. Ignored by design — parity with the Node
            handler that ignored ``req.url`` (AAP §0.6.2). Defaults to the
            empty string so the same function can also service the root
            route ``/`` (which does not supply a ``subpath`` argument).

    Returns:
        A :class:`flask.Response` with HTTP status ``200``, the header
        ``Content-Type: text/plain`` (no ``charset`` suffix), and the body
        bytes ``b"Hello, World!\\n"`` (note the trailing newline). The
        response is identical for every HTTP method and every URL path.
    """
    # The ``subpath`` argument is deliberately unused (see the docstring
    # above and AAP §0.6.2: "The ``subpath`` argument is intentionally
    # ignored, mirroring the Node handler's disregard for ``req.url``").
    # No ``del subpath`` is needed — Python permits unused arguments
    # silently, and removing it from scope would not change behavior.
    #
    # CRITICAL: ``headers={"Content-Type": "text/plain"}`` is intentionally
    # used here INSTEAD of ``mimetype="text/plain"`` or
    # ``content_type="text/plain"``. The mimetype/content_type shortcuts
    # cause Werkzeug to append ``; charset=utf-8`` to the header, which
    # would diverge from the Node ``res.setHeader('Content-Type',
    # 'text/plain')`` call (server.js:L8) that emits the bare token.
    # See AAP §0.6.1 caveat and AAP §0.6.6 risk #1.
    return Response(
        "Hello, World!\n",
        status=200,
        headers={"Content-Type": "text/plain"},
    )


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------
#
# ``main_bp`` is consumed by ``app/routes/__init__.py`` (re-export) and
# ultimately by ``app/__init__.py`` (which calls
# ``app.register_blueprint(main_bp)`` inside the ``create_app()`` factory).
#
# ``ALL_METHODS`` is exported so the parity test suite in
# ``tests/test_app.py`` can iterate over the same canonical method list
# when asserting AAP rule R-3 (method-agnostic dispatch).
__all__ = ["main_bp", "ALL_METHODS"]
