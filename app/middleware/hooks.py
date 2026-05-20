"""Flask request lifecycle hooks — Express middleware equivalent.

Provides :func:`register_hooks`, the single public entry point that attaches
three decorator-based hooks to a Flask application instance:

* ``@app.before_request`` — request logging (side-effect only).
* ``@app.after_request``  — response logging; returns ``response`` unchanged.
* ``@app.errorhandler(Exception)`` — uniform 500 ``text/plain`` response for
  uncaught exceptions.

Role in the refactor
--------------------

This module is the Flask incarnation of the Express ``app.use(fn)`` middleware
concept from the user-supplied rule ``QA-20-may-custom-rules``. The retired
Node implementation in ``server.js`` (lines 1-14) declares no middleware at
all — the request handler is a single anonymous callback that immediately
writes the response and ends the stream::

    const server = http.createServer((req, res) => {
      res.statusCode = 200;
      res.setHeader('Content-Type', 'text/plain');
      res.end('Hello, World!\\n');
    });

The hooks registered here are therefore a **rule-mandated enhancement** added
purely to honor the rule clause "middleware". Per AAP §0.6.4 Behavioral-Parity
Caveat and §0.6.6 Risk Inventory rows 1-3, the hooks MUST be additive only:
they MUST NOT alter the wire-format response that the Hello-World view emits.

Behavioral-parity constraints (CRITICAL)
----------------------------------------

The implementation below enforces three non-negotiable invariants. Each row
maps to a row in the AAP §0.6.6 Risk Inventory:

* ``before_request`` is side-effect-only — it never returns a non-``None``
  value, because returning anything from a ``before_request`` callback causes
  Flask to short-circuit the route and use the returned object as the
  response (breaking parity per AAP rules R-1 and R-3 in §0.7.4).

* ``after_request`` returns the ``response`` argument **unchanged** — no
  status mutation, no header mutation, no body mutation. Forgetting to
  ``return response`` would cause Flask to receive ``None`` and raise
  ``TypeError`` at the WSGI boundary (per AAP §0.6.6).

* The 500 errorhandler builds its :class:`flask.Response` with an explicit
  ``headers={"Content-Type": "text/plain"}`` mapping rather than the
  ``mimetype="text/plain"`` shortcut. The shortcut causes Werkzeug to append
  ``; charset=utf-8`` to the header value; the explicit mapping preserves the
  exact ``text/plain`` byte string emitted by Node's ``res.setHeader(...)`` on
  the success path (per AAP §0.6.1 caveat and §0.6.6 Risk Inventory row 1).

Scope discipline
----------------

Per AAP §0.7.3, only the three named middleware concerns (request log,
response log, errorhandler) are in scope. The implementation deliberately
does NOT add CORS handling, request-ID injection, rate limiting, timing
metrics, or any other cross-cutting concern — those would be additive
beyond the rule's wording and outside the AAP's enumerated requirements.

References
----------

* AAP §0.2.1 (rule-mandated CREATE entry for ``app/middleware/hooks.py``).
* AAP §0.3.1 (Role Specification — three decorator hooks).
* AAP §0.3.3 (Design Pattern — Decorator-based Middleware).
* AAP §0.4.1 (Transformation table row ``app/middleware/hooks.py``).
* AAP §0.5.4 (Import Refactoring — ``current_app``, ``request``, ``Response``).
* AAP §0.6.1 (Response byte-equivalence — exact ``Content-Type: text/plain``).
* AAP §0.6.3 (Idiom Translations — ``console.log`` → ``app.logger.info``).
* AAP §0.6.4 (Express → Flask mapping — ``app.use`` → ``before/after_request``).
* AAP §0.6.6 (Risk Inventory rows 1-3 — wire-format preservation).
* AAP §0.7.3 (Rule clause "middleware" honored).
* AAP §0.7.4 R-1, R-2, R-3, R-4 (parity rules).
* ``server.js`` lines 1-14 (the retired Node source of truth).
"""

from flask import Response, current_app, request


def register_hooks(app):
    """Register Flask request lifecycle hooks on ``app``.

    Plays the role of Express ``app.use(fn)`` middleware (per AAP §0.6.4
    Express → Flask mapping) by attaching three decorator-based hooks to the
    passed-in Flask application instance:

    * ``before_request`` — logs the incoming HTTP method and URL path; the
      callback is side-effect-only and MUST NOT return a value (returning a
      non-``None`` value would short-circuit the route and break wire-format
      parity, per AAP §0.6.6 Risk Inventory).
    * ``after_request``  — logs the outgoing response status code and MUST
      return the ``response`` argument unchanged to preserve parity with the
      retired Node implementation's exact response bytes (per AAP §0.6.1 and
      rules R-1 / R-2 in §0.7.4).
    * ``errorhandler(Exception)`` — catches uncaught exceptions and returns a
      uniform 500 ``text/plain`` response. The Hello-World view never raises,
      so this hook is effectively never invoked in normal operation; its
      presence satisfies the rule clause "middleware" comprehensively per
      AAP §0.7.3.

    The function has no return value — it mutates ``app`` in place by
    registering callbacks. It is intended to be called exactly once during
    application factory wiring (see ``app/__init__.py``).

    Args:
        app: A :class:`flask.Flask` application instance whose request
            lifecycle will be augmented with the three hooks above.

    Returns:
        ``None``. Side-effect only — hooks are registered on ``app``.
    """

    # ------------------------------------------------------------------
    # Hook 1: before_request — request logging (side-effect only).
    # ------------------------------------------------------------------
    # Express analogue (per AAP §0.6.4):
    #     app.use((req, res, next) => { logger.info(req.method, req.url);
    #                                    next(); });
    # The Flask analogue is much simpler because ``next()`` is implicit:
    # Flask invokes the next handler in the chain unless this callback
    # returns a non-``None`` value (in which case Flask treats the return
    # value as the response and skips the view). To preserve wire-format
    # parity we MUST NOT return anything — see AAP §0.6.6 Risk Inventory.
    @app.before_request
    def _log_request():
        """Log the incoming request method and path.

        Side-effect only — explicitly returns ``None`` (via the implicit
        end-of-function return). Returning a :class:`flask.Response` here
        would cause Flask to bypass the registered view entirely, breaking
        parity with the retired Node handler per AAP §0.6.6 Risk Inventory
        and §0.7.4 rules R-1 / R-3.
        """

        # ``current_app`` resolves to ``app`` (the closure-captured instance
        # passed to ``register_hooks``) whenever this callback fires, because
        # Flask pushes the application context before dispatching the
        # request. Using ``current_app.logger`` rather than capturing
        # ``app.logger`` directly keeps the hook decoupled from any specific
        # app reference and makes the logger lookup consistent with the rest
        # of the codebase (per AAP §0.6.3 Idiom Translations).
        #
        # The %-style format args (rather than an f-string) defer the string
        # interpolation to the logging framework, which skips it entirely
        # when the configured level filters this record out — the
        # recommended pattern from the Python ``logging`` documentation.
        current_app.logger.info(
            "Request: %s %s",
            request.method,
            request.path,
        )

        # Explicit absence of ``return`` — Python implicitly returns
        # ``None`` here, which is exactly what Flask requires for a
        # non-short-circuiting ``before_request`` callback.

    # ------------------------------------------------------------------
    # Hook 2: after_request — response logging (response passthrough).
    # ------------------------------------------------------------------
    # Express analogue (per AAP §0.6.4):
    #     app.use((req, res, next) => { res.on('finish', () => {
    #         logger.info(req.method, req.url, res.statusCode); });
    #         next(); });
    # The Flask analogue is more direct: the ``after_request`` decorator
    # registers a callback that receives the outgoing :class:`Response` and
    # MUST return it (possibly modified) so that the WSGI layer can
    # serialize it. The contract requires the return value to be a
    # :class:`Response` — returning ``None`` would raise ``TypeError`` at
    # the WSGI boundary. We pass the response through unchanged.
    @app.after_request
    def _log_response(response):
        """Log the outgoing response status; return ``response`` unchanged.

        CRITICAL: this callback MUST return the ``response`` argument
        unchanged. Modifying status, headers, or body would break parity
        with the retired Node implementation per AAP §0.6.6 Risk Inventory
        and §0.7.4 rules R-1 / R-2 (the Hello-World view emits status 200
        / ``Content-Type: text/plain`` / body ``Hello, World!\\n`` and the
        whole point of this refactor is to preserve those bytes verbatim).

        Args:
            response: The outgoing :class:`flask.Response` produced by the
                registered view (or, on the error path, by the
                :func:`_handle_uncaught` errorhandler below).

        Returns:
            The same ``response`` object, unchanged.
        """

        # Log the status code alongside the method and path so that an
        # operator scanning the log stream can correlate each
        # "Request: METHOD PATH" line with the corresponding
        # "Response: METHOD PATH -> STATUS" line that follows it.
        current_app.logger.info(
            "Response: %s %s -> %d",
            request.method,
            request.path,
            response.status_code,
        )

        # CRITICAL: return the response object UNCHANGED. Any mutation
        # would break wire-format parity. Specifically:
        #   - Do NOT touch response.status_code (would break rule R-1).
        #   - Do NOT touch response.headers (would break the exact
        #     ``Content-Type: text/plain`` byte string per §0.6.1).
        #   - Do NOT touch response.data (would break the ``Hello, World!\n``
        #     body per §0.6.1).
        return response

    # ------------------------------------------------------------------
    # Hook 3: errorhandler(Exception) — uniform 500 text/plain response.
    # ------------------------------------------------------------------
    # Express analogue (per AAP §0.6.4):
    #     app.use((err, req, res, next) => {
    #         logger.error(err);
    #         res.status(500).type('text/plain').send('Internal Server Error\\n');
    #     });
    # The Flask analogue uses ``@app.errorhandler(Exception)``, which
    # catches every uncaught exception (including subclasses of
    # ``HTTPException``, except those registered against more specific
    # handlers). Because the Hello-World view never raises, this handler
    # is effectively a no-op for normal operation — its presence exists
    # solely to satisfy the rule QA-20-may-custom-rules "middleware"
    # clause comprehensively per AAP §0.7.3.
    @app.errorhandler(Exception)
    def _handle_uncaught(exc):
        """Return a uniform 500 ``text/plain`` response for uncaught errors.

        The wire-format of this 500 response matches the success path's
        wire-format on the two attributes the AAP cares about
        (``Content-Type`` header byte string, trailing-newline body
        convention) so that operators see a consistent shape across both
        paths.

        Implementation note — :py:meth:`logging.Logger.exception` is used
        rather than :py:meth:`~logging.Logger.error` because
        :py:meth:`exception` automatically attaches the current
        ``sys.exc_info()`` traceback to the emitted record, which is the
        idiomatic Python way to log an unhandled exception from inside an
        ``except`` (or, here, an errorhandler) block.

        Args:
            exc: The exception instance that Flask caught and routed to
                this handler. Logged for diagnostic visibility; not
                propagated to the caller.

        Returns:
            A :class:`flask.Response` with status ``500``, header
            ``Content-Type: text/plain`` (no charset suffix, matching the
            success-path convention per AAP §0.6.1), and body
            ``"Internal Server Error\\n"`` (terminating newline mirrors
            the main view's ``Hello, World!\\n`` convention).
        """

        # ``logger.exception`` automatically attaches the current traceback
        # via ``sys.exc_info()`` — no need to format it manually. The first
        # positional argument is the message template; subsequent
        # positional args are interpolated lazily by the logging framework.
        current_app.logger.exception("Unhandled exception: %s", exc)

        # Construct the 500 response with an explicit ``Content-Type``
        # header rather than relying on Flask's ``mimetype`` shortcut.
        # Rationale (per AAP §0.6.1 caveat and §0.6.6 Risk Inventory row 1):
        # ``Response(body, mimetype="text/plain")`` causes Werkzeug to emit
        # ``Content-Type: text/plain; charset=utf-8``, whereas the retired
        # Node implementation's ``res.setHeader('Content-Type', 'text/plain')``
        # call emits the bare string ``text/plain``. Setting the header via
        # the ``headers`` mapping bypasses Werkzeug's charset-suffix logic
        # and preserves the exact byte string used by the main success path
        # in ``app/routes/main.py``.
        #
        # The body terminates with ``\n`` to mirror the convention from
        # ``server.js:L9`` (``res.end('Hello, World!\n');``) — operators see
        # a consistent body-shape convention across both success and error
        # paths even though the literal bytes differ.
        return Response(
            "Internal Server Error\n",
            status=500,
            headers={"Content-Type": "text/plain"},
        )


# Explicit module-level export list. Limiting ``__all__`` to the single public
# entry point (``register_hooks``) hides the inner ``_log_request``,
# ``_log_response``, and ``_handle_uncaught`` closures from ``from ... import *``
# consumers — they are implementation details of ``register_hooks`` and never
# referenced from outside this module.
__all__ = ["register_hooks"]
