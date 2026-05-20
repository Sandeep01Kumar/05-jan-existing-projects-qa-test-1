"""Middleware package for the hao-backprop-test Flask service.

Exposes :func:`register_hooks`, which registers Flask request lifecycle
hooks (``before_request`` / ``after_request`` / ``errorhandler``) playing
the role of Express ``app.use(fn)`` middleware named in the user-supplied
rule ``QA-20-may-custom-rules``.

This package is a **rule-mandated enhancement** per AAP §0.7.3. The
retired Node implementation in ``server.js`` (lines 1-14) had no
middleware at all — its request handler is a single anonymous callback
that immediately writes the response and ends the stream (see AAP §0.6.4
"Express → Flask mapping" and the Behavioral-Parity Caveat documented in
``app/middleware/hooks.py``).

Purpose of this ``__init__`` module
-----------------------------------

The file's sole responsibility is to **re-export** :func:`register_hooks`
from the sibling :mod:`app.middleware.hooks` module so that the
application factory in :mod:`app.__init__` can perform the canonical
package-level import::

    from .middleware import register_hooks

This import path is specified verbatim in AAP §0.5.4 "Import
Refactoring" table. The naming and casing of the re-exported symbol MUST
match the function name defined in :mod:`app.middleware.hooks` exactly.

Public API
----------

The explicit :data:`__all__` list below pins this package's public API
surface to a single symbol — :func:`register_hooks`. This prevents
``from app.middleware import *`` from leaking the internal closures
declared inside ``hooks.py`` (``_log_request``, ``_log_response``,
``_handle_uncaught``) and gives tooling (IDEs, linters, documentation
generators) a deterministic enumeration of what consumers may import.

Scope discipline
----------------

Per AAP §0.7.3, only the three named middleware concerns from rule
``QA-20-may-custom-rules`` (request logging, response logging, generic
errorhandler) are mandated. This package therefore exposes only the
single :func:`register_hooks` aggregator — no CORS, no auth, no rate
limiting, no request-ID injection, and no additional middleware
re-exports. Any expansion of this public surface would exceed the AAP's
enumerated scope.

References
----------

* AAP §0.2.1 — rule-mandated CREATE entry for ``app/middleware/__init__.py``.
* AAP §0.3.1 — Role Specification table row for this file.
* AAP §0.4.1 — Transformation table row for this file.
* AAP §0.5.4 — Import Refactoring table mandating the
  ``from .middleware import register_hooks`` consumer pattern.
* AAP §0.6.4 — Express → Flask mapping (``app.use(fn)`` →
  ``@app.before_request`` / ``@app.after_request`` /
  ``@app.errorhandler``).
* AAP §0.7.3 — Rule clause "middleware" honored.
* ``app/middleware/hooks.py`` — the module that defines
  :func:`register_hooks` and the three private hook closures it
  registers.
"""

# Relative import from the sibling ``hooks`` module — PEP 328 explicit
# relative form. The leading dot guarantees that ``register_hooks``
# resolves to the function declared in ``app/middleware/hooks.py``
# regardless of the caller's working directory or ``sys.path`` ordering
# (the absolute form ``from app.middleware.hooks import register_hooks``
# would couple this file to the top-level package name and would fail
# inside test rigs that mount the package under an alternate name).
from .hooks import register_hooks

# Explicit public API surface for this package. Limiting ``__all__`` to
# the single re-exported function name ensures that
# ``from app.middleware import *`` exposes exactly :func:`register_hooks`
# and nothing else — keeping the package marker deterministic and aligned
# with the AAP §0.7.3 scope ("only the three named concerns ... no CORS,
# no auth, no rate-limiting").
__all__ = ["register_hooks"]
