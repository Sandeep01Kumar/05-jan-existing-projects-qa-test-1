"""Routes package for the hao-backprop-test Flask service.

Aggregates the Flask :class:`~flask.Blueprint` definitions for this
application and re-exports them so the application factory
(:mod:`app.__init__`) can use the canonical short-form import::

    from .routes import main_bp

This package is the structural replacement for the inline
``http.createServer((req, res) => {...})`` callback of the retired
Node.js implementation (see ``server.js:L6-L10``). The retired callback
was a single anonymous function bound directly to the HTTP server; the
Flask refactor replaces it with the
:class:`~flask.Blueprint`-based modular routing pattern recommended by
the official Flask documentation and adopted in AAP §0.3.3 (Design
Pattern Applications — Blueprint).

The actual request handler — including the catch-all routes that mirror
the Node implementation's method-agnostic and path-agnostic dispatch per
AAP rules R-3 and R-4 (§0.7.4) — lives in :mod:`app.routes.main`. This
package marker is purely structural; it does **not** reproduce or
shadow any of that behavior. It exists exclusively to:

1. Mark ``app/routes/`` as a Python package (the ``__init__.py``
   filename does that automatically per PEP 328).
2. Re-export :data:`main_bp` so the parent application factory can
   import the blueprint via the package name rather than reaching into
   :mod:`app.routes.main` directly.

Public API
----------

The explicit :data:`__all__` list pins this package's public surface to
the single re-exported blueprint :data:`main_bp`. This makes
``from app.routes import *`` deterministic (used by ad-hoc shells and
tests, not by production code) and prevents future additions to
``main.py`` (such as the module-level ``ALL_METHODS`` constant) from
accidentally leaking through this package boundary. Any new blueprints
added in future modules (e.g. ``auth_bp`` from ``app/routes/auth.py``)
must be aggregated here by extending the import block and
:data:`__all__` list, matching the existing pattern.

Scope discipline
----------------

Per AAP §0.7.4 R-8 ("No Node residue") and the broader principle of
keeping the migration surgical, this file contains no conditional
logic, no try/except blocks, no version checks, and no debug prints.
The two-line implementation below is the complete file by design.

References
----------

* AAP §0.2.1 — rule-mandated ``CREATE`` entry for
  ``app/routes/__init__.py``.
* AAP §0.3.1 — Role Specification table row (role: "exports main_bp").
* AAP §0.3.3 — Design Pattern Applications: Blueprint.
* AAP §0.4.1 — Transformation table row ("CREATE — new package marker
  — ``from .main import main_bp``").
* AAP §0.5.4 — Import Refactoring table specifying the
  ``from .routes import main_bp`` consumer pattern used by
  :mod:`app.__init__`.
* AAP §0.7.3 — Rule clause "add routing" honored.
* AAP §0.7.4 R-8 — No Node residue.
* AAP §0.8.5 — Citation discipline (this docstring references
  ``server.js:L6-L10`` for traceability to the retired Node source).
* :mod:`app.routes.main` — the module that defines :data:`main_bp` and
  the catch-all view function it wraps.
"""

# Relative import from the sibling ``main`` module — PEP 328 explicit
# relative form. The leading dot guarantees that ``main_bp`` resolves to
# the :class:`~flask.Blueprint` instance declared in
# ``app/routes/main.py`` regardless of the caller's working directory or
# ``sys.path`` ordering (the absolute form
# ``from app.routes.main import main_bp`` would couple this file to the
# top-level package name and would fail inside test rigs that mount the
# package under an alternate name).
from .main import main_bp

# Explicit public API surface for this package. Limiting ``__all__`` to
# the single re-exported blueprint name ensures that
# ``from app.routes import *`` exposes exactly :data:`main_bp` and
# nothing else — keeping the package marker deterministic and aligned
# with the AAP §0.5.4 import contract consumed by :mod:`app.__init__`.
__all__ = ["main_bp"]
