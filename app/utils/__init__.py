"""Utility modules for the archie-job-reverse-file-mapper Flask application.

Currently provides:

* :mod:`app.utils.cleanup` -- Per-request resource teardown handlers
  that release ``CodeGraphBuilder`` and ``RunnerSession`` instances at
  the end of every Flask request.

This package is intentionally minimal -- it contains no eager imports
and exposes no aggregated API.  Consumers should import the specific
submodule they need, e.g.::

    from app.utils.cleanup import register_teardown_handlers

Importing :mod:`app.utils` itself is a side-effect-free no-op: it does
not read environment variables, construct GCP clients, configure
logging, or perform any other I/O.  This guarantee keeps the package
safe to import in unit tests, in environments lacking GCP credentials,
and during Flask application startup before configuration is finalised.
"""

# Explicit empty ``__all__`` documents that this package re-exports no
# names of its own.  All public symbols live in the submodules and must
# be imported from there directly.
__all__: tuple[str, ...] = ()
