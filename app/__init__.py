"""Application package and factory for the hao-backprop-test Flask service.

This package is the **structural replacement** for the retired Node.js entry
pattern of ``http.createServer((req, res) => {...})`` declared in
``server.js`` (lines 1-14)::

    const http = require('http');

    const hostname = '127.0.0.1';
    const port = 3000;

    const server = http.createServer((req, res) => {
      res.statusCode = 200;
      res.setHeader('Content-Type', 'text/plain');
      res.end('Hello, World!\\n');
    });

    server.listen(port, hostname, () => {
      console.log(`Server running at http://${hostname}:${port}/`);
    });

The migration replaces the single-file Node entry with the Flask
**application-factory + blueprint** pattern (AAP §0.3.3 Design Pattern
Applications). The actual request handler (the ``Hello, World!\\n`` view
that mirrors ``server.js:L7-L9``) lives in :mod:`app.routes.main`; this
module's role is purely orchestration:

1. Mark ``app/`` as a Python package (the ``__init__.py`` filename does
   that automatically per PEP 328).
2. Expose the :func:`create_app` factory that instantiates and configures
   a fresh :class:`flask.Flask` application per call.
3. Dynamically resolve the configuration class from a dotted-path string
   so that :mod:`wsgi` can select profiles at runtime via the
   ``FLASK_CONFIG`` environment variable (AAP §0.3.1).
4. Wire up structured logging via :func:`app.logging_config.configure_logging`,
   replacing the retired ``console.log`` call from ``server.js:L13``.
5. Install the Express-equivalent request lifecycle hooks via
   :func:`app.middleware.register_hooks`.
6. Register the catch-all :data:`~app.routes.main_bp` blueprint so every
   URL path and every HTTP method reaches the Hello-World view (AAP
   rules R-3 and R-4 in §0.7.4).
7. Emit a startup banner that is semantically equivalent to the retired
   Node banner ``Server running at http://127.0.0.1:3000/`` (AAP rule
   R-5 in §0.7.4 — mirrors ``server.js:L13``).

Public API
----------

This package exposes exactly one public symbol:

* :func:`create_app` — the application factory described above.

The single-symbol :data:`__all__` declaration at the bottom of this module
pins that public API so that ``from app import *`` is deterministic.

Conflict-resolution context
---------------------------

Per AAP §0.1.2 and §0.7.3, the user-supplied rule
``QA-20-may-custom-rules`` names Node-specific tools (Express.js, PM2)
that cannot coexist with the primary directive to rewrite the service in
Python/Flask. The factory implemented here honors the *spirit* of the
rule by translating each named Node concept to its Flask equivalent:

* "Express.js framework" → :class:`flask.Flask` via ``Flask(__name__)``.
* "add routing" → :class:`flask.Blueprint` registration (see
  :func:`create_app` body and :mod:`app.routes`).
* "middleware" → :func:`app.middleware.register_hooks` installing
  ``before_request`` / ``after_request`` / ``errorhandler`` callbacks.
* "environment config" → :class:`app.config.BaseConfig` and its
  subclasses, populated from ``os.environ`` via ``python-dotenv``.
* "logging" → Python ``logging`` module wired via
  :func:`app.logging_config.configure_logging`.

References
----------

* AAP §0.2.1 (rule-mandated CREATE entry for ``app/__init__.py``).
* AAP §0.3.1 (Role Specification — application factory description).
* AAP §0.3.3 (Design Pattern Applications — Application Factory,
  Blueprint, Twelve-Factor Configuration, Decorator-based Middleware,
  Structured Logging).
* AAP §0.4.1 (Transformation table row ``app/__init__.py``).
* AAP §0.5.4 (Import Refactoring table — imports list verbatim).
* AAP §0.6.3 (Node.js → Python idiom translations).
* AAP §0.6.4 (Express → Flask mapping table).
* AAP §0.7.3 (Rule resolution — rule clauses honored by Flask
  equivalents).
* AAP §0.7.4 R-1 / R-2 / R-3 / R-4 / R-5 (parity rules).
* AAP §0.8.5 (Citation Discipline — bracketed references to
  ``server.js`` line ranges).
"""

# ---------------------------------------------------------------------------
# Module-level imports
# ---------------------------------------------------------------------------
# Per AAP §0.5.4 Import Refactoring table, this module imports:
#
#   * ``importlib`` (standard library) — used by :func:`create_app` to
#     dynamically resolve the configuration class from the dotted-path
#     string passed in ``config_object`` (e.g., ``"app.config.DevConfig"``
#     → ``importlib.import_module("app.config")`` then
#     ``getattr(module, "DevConfig")``). This indirection lets
#     :mod:`wsgi` select a config profile via the ``FLASK_CONFIG``
#     environment variable at runtime without this module needing to
#     import every possible profile up-front (AAP §0.3.1 Role
#     Specification).
#
#   * :class:`flask.Flask` — the web framework class that replaces the
#     retired Node ``http.createServer`` from ``server.js:L1`` (AAP
#     §0.6.4 Express → Flask mapping: ``express()`` → ``Flask(__name__)``).
#
#   * :func:`.logging_config.configure_logging` — centralized logging
#     setup that replaces the retired ``console.log`` from
#     ``server.js:L13`` (AAP §0.6.3, §0.7.3).
#
#   * :func:`.middleware.register_hooks` — Express-equivalent middleware
#     installation (AAP §0.6.4, §0.7.3).
#
#   * :data:`.routes.main_bp` — the catch-all blueprint that hosts the
#     Hello-World view (AAP §0.3.3 Blueprint pattern, §0.7.3 "add
#     routing").
#
# Intentionally NOT imported here:
#
#   * ``os`` / ``os.environ`` — per AAP §0.5.4, environment-variable
#     access is concentrated in :mod:`app.config`. Keeping this module
#     env-free makes the factory unit-testable without ``.env`` loading.
#   * :class:`flask.Blueprint` / :class:`flask.Response` — these belong
#     in :mod:`app.routes.main`. This module only registers the
#     pre-built blueprint; it does not declare routes.
#   * :mod:`dotenv` — ``load_dotenv()`` is invoked at import-time inside
#     :mod:`app.config`, so it is reachable transitively through the
#     ``importlib.import_module("app.config")`` call below.
# ---------------------------------------------------------------------------
import importlib

from flask import Flask

from .logging_config import configure_logging
from .middleware import register_hooks
from .routes import main_bp


# ---------------------------------------------------------------------------
# Default configuration profile
# ---------------------------------------------------------------------------
# When :func:`create_app` is invoked without arguments, it uses
# ``"app.config.DevConfig"`` as the dotted-path target. This default is
# documented in :mod:`app.config` and in ``.env.example`` and is the
# profile most useful during local development (``DEBUG = True`` enables
# Flask's interactive debugger and reloader).
#
# Defining the default as a module-level constant (rather than burying it
# in the function signature) lets tests and integration scripts reference
# it by name when they need to switch profiles explicitly — e.g.,
# ``create_app("app.config.TestConfig")`` from a pytest fixture. The
# constant is intentionally private to discourage external mutation;
# consumers who need to change the profile should pass ``config_object``
# explicitly rather than reach in and monkeypatch this name.
_DEFAULT_CONFIG_OBJECT: str = "app.config.DevConfig"


def create_app(config_object: str = _DEFAULT_CONFIG_OBJECT) -> Flask:
    """Construct and return a fully configured Flask application.

    Mirrors the role of ``http.createServer`` from the retired Node.js
    implementation at ``server.js:L6`` but uses the Flask
    application-factory pattern (AAP §0.3.3) instead of returning a raw
    server object. Each call produces a freshly instantiated
    :class:`flask.Flask` object with config loaded, structured logging
    configured, request lifecycle hooks installed, and the main blueprint
    registered. Callers are responsible for either running the returned
    instance (``app.run(...)`` for dev) or handing it to a WSGI server
    (``gunicorn -c gunicorn_config.py wsgi:app`` for production).

    The factory is intentionally idempotent in the sense that two
    consecutive calls return two independent ``Flask`` instances with
    identical configuration — there is no shared mutable state between
    calls. This property is essential for pytest fixtures (AAP §0.3.3
    Application Factory pattern) that may need to spin up many isolated
    app instances per test session.

    Initialization order (CRITICAL — DO NOT REORDER):

    1. **Instantiate the Flask app.** ``Flask(__name__)`` produces the
       WSGI application object; the import-name argument is the standard
       Flask idiom that lets the framework resolve resources relative to
       this package. Plays the role of Express's ``express()`` call per
       AAP §0.6.4.

    2. **Load configuration.** The dotted-path ``config_object`` string
       is split into ``(module_path, class_name)``, the module is
       imported via :func:`importlib.import_module`, and the named class
       is fetched via :func:`getattr`. The class is then applied to
       ``app.config`` via :meth:`flask.Config.from_object`. Importing
       :mod:`app.config` here also triggers its module-level
       ``load_dotenv()`` call, populating ``os.environ`` from ``.env``
       (AAP §0.6.4 — ``require('dotenv').config()`` equivalent).

    3. **Configure logging.** Must happen *after* config is loaded
       because :func:`.logging_config.configure_logging` reads
       ``app.config["LOG_LEVEL"]`` to set the handler level. Reordering
       this step before step 2 would cause the logger to fall back to
       its default level regardless of what ``LOG_LEVEL`` says.

    4. **Register middleware.** Must happen *after* logging is set up
       because the registered hooks emit log lines via
       ``current_app.logger`` (per-request, not at registration time —
       but it is cleanest to keep the logger ready before any hook code
       runs). Plays the role of Express ``app.use(fn)`` per AAP §0.6.4.

    5. **Register the main blueprint.** ``main_bp`` carries the
       catch-all ``"/"`` and ``"/<path:subpath>"`` routes that satisfy
       AAP rules R-3 (method-agnostic dispatch) and R-4 (path-agnostic
       dispatch) in §0.7.4.

    6. **Emit the startup banner.** Logged *after* blueprint
       registration so the banner acts as the "ready" signal, matching
       the semantics of ``server.js:L13`` (the original ``console.log``
       fires only after ``server.listen`` succeeds). Per AAP rule R-5 in
       §0.7.4, the banner is semantically equivalent to
       ``Server running at http://${hostname}:${port}/`` with the
       hostname and port sourced from the loaded config — preserving
       the ``127.0.0.1:3000`` defaults from ``server.js:L3-L4`` per
       rule R-2.

    Args:
        config_object: Dotted import path to a configuration class. Must
            resolve to one of the four classes exposed by
            :mod:`app.config` — :class:`~app.config.BaseConfig`,
            :class:`~app.config.DevConfig`, :class:`~app.config.ProdConfig`,
            or :class:`~app.config.TestConfig`. Defaults to
            ``"app.config.DevConfig"`` so a bare ``create_app()`` call
            yields a development-profile app. The :mod:`wsgi` entry
            point overrides this with the value of the ``FLASK_CONFIG``
            environment variable (defaulting to
            ``"app.config.ProdConfig"`` for production deployments).

    Returns:
        A fully wired :class:`flask.Flask` instance. The returned app
        has the chosen configuration class applied to ``app.config``, a
        structured ``StreamHandler`` attached to ``app.logger``, the
        Express-equivalent ``before_request`` / ``after_request`` /
        ``errorhandler`` hooks registered, and the
        :data:`app.routes.main_bp` catch-all blueprint registered so
        every URL path and every HTTP method enumerated in
        :data:`app.routes.main.ALL_METHODS` returns the byte-for-byte
        parity response from ``server.js:L7-L9``.

    Raises:
        ModuleNotFoundError: If ``config_object`` references a Python
            module that cannot be imported (e.g., a typo like
            ``"app.confg.DevConfig"``). Propagated unchanged from
            :func:`importlib.import_module`.
        AttributeError: If ``config_object`` references a class name
            that does not exist on the resolved module (e.g.,
            ``"app.config.NoSuchConfig"``). Propagated unchanged from
            :func:`getattr`.

    Example:
        Build a development-profile app and exercise the Hello-World
        route via the Flask test client::

            from app import create_app

            app = create_app()  # uses DevConfig by default
            assert app.config["HOST"] == "127.0.0.1"
            assert app.config["PORT"] == 3000

            with app.test_client() as client:
                response = client.get("/")
                assert response.status_code == 200
                assert response.headers["Content-Type"] == "text/plain"
                assert response.data == b"Hello, World!\\n"

        Build a test-profile app from a pytest fixture::

            @pytest.fixture
            def app():
                from app import create_app
                return create_app("app.config.TestConfig")
    """

    # ------------------------------------------------------------------
    # Step 1: Instantiate the Flask application.
    # ------------------------------------------------------------------
    # ``Flask(__name__)`` is the canonical idiom recommended by the
    # official Flask documentation: the import-name argument lets the
    # framework resolve resources (templates, static files, instance
    # folder) relative to this package. The hao-backprop-test service
    # uses none of those features (AAP §0.3.4 — no UI surface), but
    # passing ``__name__`` keeps the signature aligned with community
    # conventions and with documentation examples that future
    # maintainers will look up.
    #
    # ``__name__`` evaluates to ``"app"`` here because this module is
    # ``app/__init__.py`` and the package is named ``app``. This is the
    # same string that Flask uses as the default ``app.logger`` name,
    # which is what the formatter in :mod:`app.logging_config` renders
    # in the ``%(name)s`` field.
    #
    # Express analogue (per AAP §0.6.4): ``const app = express();``.
    # ------------------------------------------------------------------
    app: Flask = Flask(__name__)

    # ------------------------------------------------------------------
    # Step 2: Resolve the dotted-path config string and load the class.
    # ------------------------------------------------------------------
    # The ``config_object`` parameter is a dotted import path — for
    # example, ``"app.config.DevConfig"``. The factory must:
    #
    #   1. Split the string into ``(module_path, class_name)`` so that
    #      ``importlib.import_module`` can be given the module portion
    #      alone (it cannot import a class directly — Python's import
    #      machinery operates on modules).
    #   2. Import the module via :func:`importlib.import_module`. This
    #      side-effects the import of :mod:`app.config`, which in turn
    #      triggers that module's top-level ``load_dotenv()`` call —
    #      populating ``os.environ`` from ``.env`` (per AAP §0.6.4
    #      Express → Flask mapping: ``require('dotenv').config()``
    #      equivalent).
    #   3. Pluck the named class off the imported module via
    #      :func:`getattr`.
    #   4. Apply the class to ``app.config`` via
    #      :meth:`flask.Config.from_object`, which copies every
    #      ``ALL_CAPS`` attribute off the class into the config mapping.
    #
    # ``str.rpartition(".")`` is used (rather than ``str.rsplit(".", 1)``
    # then indexing into a list) because it always returns a 3-tuple,
    # which is friendlier to unpacking. The middle element (``_``) is
    # the separator dot itself, which we discard.
    #
    # Why the dotted-string indirection (instead of accepting a class
    # object)? Because :mod:`wsgi` reads ``FLASK_CONFIG`` from the
    # environment as a string and passes it straight through without
    # needing import knowledge of the choice. This keeps the WSGI
    # entry-point file free of per-profile import branches.
    # ------------------------------------------------------------------
    module_path, _, class_name = config_object.rpartition(".")
    config_module = importlib.import_module(module_path)
    config_class = getattr(config_module, class_name)
    app.config.from_object(config_class)

    # ------------------------------------------------------------------
    # Step 3: Configure structured logging.
    # ------------------------------------------------------------------
    # :func:`configure_logging` reads ``app.config["LOG_LEVEL"]`` to set
    # the level on a freshly-built :class:`logging.StreamHandler`
    # targeting ``sys.stdout``. Idempotent — calling it again on the
    # same app instance does NOT result in duplicate handlers (the
    # implementation strips any existing ``StreamHandler`` before
    # adding the new one).
    #
    # This call MUST come after Step 2 (config load) because
    # :func:`configure_logging` reads from ``app.config``. Reordering
    # would cause the logger to fall back to its default level
    # regardless of what ``LOG_LEVEL`` says — silently breaking the
    # operator's ability to crank verbosity for diagnostics.
    #
    # This call replaces the retired ``console.log`` from
    # ``server.js:L13`` per AAP §0.6.3 (Idiom Translations) and §0.7.3
    # (Rule clause "logging" honored by Python ``logging`` module).
    # ------------------------------------------------------------------
    configure_logging(app)

    # ------------------------------------------------------------------
    # Step 4: Install Express-equivalent request lifecycle hooks.
    # ------------------------------------------------------------------
    # :func:`register_hooks` attaches three decorator-based callbacks to
    # the Flask app:
    #
    #   * ``before_request`` — logs the incoming method and path.
    #   * ``after_request``  — logs the outgoing status code; returns
    #                          the response unchanged (parity-critical
    #                          per AAP §0.6.6 Risk Inventory).
    #   * ``errorhandler(Exception)`` — uniform 500 ``text/plain``
    #                                  response for uncaught exceptions.
    #
    # These hooks are the **rule-mandated** Flask incarnation of the
    # Express ``app.use(fn)`` middleware concept (per AAP §0.6.4 and
    # §0.7.3). They are additive only — they MUST NOT alter the
    # wire-format response that the Hello-World view emits on the
    # success path.
    #
    # Calling this AFTER Step 3 (logging) is best practice: the hooks
    # invoke ``current_app.logger`` at request time, so it is cleanest
    # to have the logger fully wired before any hook code can fire.
    # ------------------------------------------------------------------
    register_hooks(app)

    # ------------------------------------------------------------------
    # Step 5: Register the main blueprint (the catch-all router).
    # ------------------------------------------------------------------
    # :data:`main_bp` carries the two route decorators that satisfy AAP
    # rules R-3 (method-agnostic dispatch) and R-4 (path-agnostic
    # dispatch) in §0.7.4:
    #
    #   * ``@main_bp.route("/", methods=ALL_METHODS)``
    #   * ``@main_bp.route("/<path:subpath>", methods=ALL_METHODS)``
    #
    # Both decorators wrap the same ``hello_world`` view function, so
    # every URL path × every HTTP method in
    # :data:`app.routes.main.ALL_METHODS` reaches the byte-for-byte
    # parity response from ``server.js:L7-L9``.
    #
    # No ``url_prefix=`` is passed to ``register_blueprint`` because
    # :data:`main_bp` is intentionally mounted at the application root.
    # Adding a prefix would push the catch-all under a sub-URL and
    # break parity with the retired Node implementation (which serves
    # ``Hello, World!\n`` at every path, including ``/``).
    #
    # Express analogue (per AAP §0.6.4):
    #     app.use('/', router);   // where ``router`` is ``main_bp``.
    # ------------------------------------------------------------------
    app.register_blueprint(main_bp)

    # ------------------------------------------------------------------
    # Step 6: Emit the startup banner (parity with ``server.js:L13``).
    # ------------------------------------------------------------------
    # The retired Node implementation logged the following line on
    # successful ``listen``::
    #
    #     console.log(`Server running at http://${hostname}:${port}/`);
    #
    # The Python equivalent uses ``app.logger.info`` with %-style
    # placeholders rather than an f-string so that the logging
    # framework can defer the actual string interpolation when the
    # configured level filters this record out — the recommended
    # pattern from the Python ``logging`` module documentation.
    #
    # The host and port are sourced from the loaded ``app.config``
    # rather than from hard-coded constants. This preserves the
    # ``127.0.0.1:3000`` defaults from ``server.js:L3-L4`` (per AAP
    # rule R-2 in §0.7.4) while letting operators override them via
    # the ``HOST`` and ``PORT`` environment variables at deployment
    # time.
    #
    # The explicit ``int(...)`` coercion on ``app.config["PORT"]`` is
    # defensive: most code paths populate ``PORT`` as an int (see
    # :class:`app.config.BaseConfig`), but if a caller-supplied
    # configuration class stores it as a string the ``%d`` format
    # specifier would raise ``TypeError`` without this guard.
    #
    # This call MUST come AFTER Step 5 (blueprint registration) so that
    # the banner acts as the "ready" signal, matching the semantic of
    # ``server.js:L13`` (the Node ``console.log`` fires only after
    # ``server.listen`` succeeds).
    # ------------------------------------------------------------------
    app.logger.info(
        "Server running at http://%s:%d/",
        app.config["HOST"],
        int(app.config["PORT"]),
    )

    # ------------------------------------------------------------------
    # Step 7: Return the fully wired Flask app.
    # ------------------------------------------------------------------
    # Callers receive a :class:`flask.Flask` instance with:
    #   * Config loaded (HOST=127.0.0.1, PORT=3000 by default — AAP R-2)
    #   * Logging configured (StreamHandler on stdout — AAP §0.3.3)
    #   * Middleware hooks registered (before/after/error — AAP §0.7.3)
    #   * Main blueprint registered (catch-all routes — AAP R-3, R-4)
    #
    # The factory has no return-value-side-effect: the returned app is
    # the only externally-visible result of the call. There is no
    # global state mutation, no module-level cache, and no idempotency
    # marker. Two consecutive calls produce two fully independent app
    # instances — essential for pytest fixtures that build per-test
    # apps via ``create_app("app.config.TestConfig")``.
    # ------------------------------------------------------------------
    return app


# ---------------------------------------------------------------------------
# Module-level exports
# ---------------------------------------------------------------------------
# Explicit ``__all__`` declaration so that ``from app import *`` and
# tooling that inspects ``__all__`` (e.g., Sphinx's ``automodule``,
# certain linters, IDE auto-completers) see exactly one public symbol —
# :func:`create_app`. Module-private helpers
# (``_DEFAULT_CONFIG_OBJECT``) remain accessible by qualified name for
# advanced introspection without polluting the wildcard-import surface.
#
# Per the AAP §0.3.1 Role Specification and the file's ``exports`` schema
# row, the single exported symbol is :func:`create_app` (kind=function,
# is_default=False).
__all__ = ["create_app"]
