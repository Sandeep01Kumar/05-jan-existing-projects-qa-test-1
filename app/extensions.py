"""Flask extensions and application-level singletons.

This module is loaded by :func:`app.create_app` to bind the
application's shared, thread-safe clients to the Flask app instance.
The two principal singletons are:

* ``storage_client`` -- a ``google.cloud.storage.Client`` used by
  ``AdminStorageService`` and any other GCS-dependent service.
* ``publisher`` -- a ``google.cloud.pubsub_v1.PublisherClient`` used
  by ``Notifier`` for IN_PROGRESS / DONE / ERROR notifications and
  by ``publish_notification`` for downstream-job propagation.

Both clients are constructed once per Flask process (they are
thread-safe, per the Google Cloud client library documentation) and
stored on ``app.extensions`` for retrieval by service-layer code via
``current_app.extensions[...]``.

In the original ``main.py`` these singletons were created at module
import time::

    from google.cloud import storage, pubsub_v1
    ...
    storage_client = storage.Client()      # main.py line 64
    publisher = pubsub_v1.PublisherClient()  # main.py line 65

In the Flask migration the singletons are deferred to
:func:`init_extensions` so that:

1. Importing the module has no side effects (so
   ``from app.extensions import init_extensions`` is fast and safe
   in environments without GCP credentials, including unit tests).
2. Tests can patch the GCP libraries before instantiation.
3. Different Flask app instances (e.g. test fixtures vs. production)
   can use different mock clients.

The CORS extension instance is created at module level using
Flask-CORS's standard deferred-initialization pattern; the actual
binding to the Flask app happens inside :func:`init_extensions` via
``cors.init_app(app)``.

Usage from the application factory (``app/__init__.py``)::

    from app.extensions import init_extensions
    ...
    def create_app(config_name=None):
        app = Flask(__name__)
        ...
        init_extensions(app)
        ...
        return app

Usage from service-layer code::

    from flask import current_app
    from app.extensions import get_storage_client, get_pubsub_publisher

    storage_client = get_storage_client(current_app._get_current_object())
    publisher = get_pubsub_publisher(current_app._get_current_object())
"""

from typing import Any

from flask import Flask
from flask_cors import CORS
from google.cloud import pubsub_v1, storage

# --------------------------------------------------------------------- #
# Module-level extension instances
# --------------------------------------------------------------------- #
# Flask-CORS extension instance.  Initialized inside
# :func:`init_extensions` via ``cors.init_app(app)``.  Constructing the
# CORS object with no ``app`` argument follows the standard Flask-CORS
# deferred-initialization pattern: it does NOT connect to any external
# service at module-load time, so importing this module remains
# side-effect-free.
cors = CORS()


# --------------------------------------------------------------------- #
# Type aliases
# --------------------------------------------------------------------- #
#: Type alias for values stored in ``app.extensions``.  The Flask
#: ``extensions`` dictionary holds heterogeneous extension instances
#: (Flask-CORS, ``google.cloud.storage.Client``,
#: ``google.cloud.pubsub_v1.PublisherClient``, and any future
#: extensions registered here), so :data:`~typing.Any` is the
#: appropriate static type for the generic case.  Typed convenience
#: accessors -- :func:`get_storage_client` and
#: :func:`get_pubsub_publisher` -- narrow the return type for specific
#: extensions used by the service layer.
ExtensionInstance = Any


# --------------------------------------------------------------------- #
# Extension-storage keys
# --------------------------------------------------------------------- #
# These constants are the canonical keys under which each shared
# singleton is stored on ``app.extensions``.  Service-layer modules
# should prefer the typed accessors below to direct dictionary lookups,
# but the keys are exported here for completeness and for any caller
# that needs to introspect ``app.extensions`` directly.
_STORAGE_CLIENT_KEY = "storage_client"
_PUBSUB_PUBLISHER_KEY = "pubsub_publisher"


# --------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------- #
def init_extensions(app: Flask) -> None:
    """Initialize all Flask extensions and shared singletons.

    Called once by :func:`app.create_app` during application factory
    setup.  This function:

    1. Initializes ``flask-cors`` so the API endpoints accept
       cross-origin requests from the Blitzy platform UI.
    2. Constructs a thread-safe ``google.cloud.storage.Client`` and
       binds it to ``app.extensions["storage_client"]``.
    3. Constructs a thread-safe
       ``google.cloud.pubsub_v1.PublisherClient`` and binds it to
       ``app.extensions["pubsub_publisher"]``.

    The two GCP singletons replace the module-level singletons that
    existed in the original ``main.py``::

        storage_client = storage.Client()
        publisher = pubsub_v1.PublisherClient()

    They are constructed lazily here (rather than at module-import
    time) so that importing the ``app`` package has no side effects
    and so that tests can patch the GCP libraries before instantiation.

    Both GCP clients are documented as thread-safe and intended to be
    reused across requests, so a single instance per Flask process
    (i.e. per Gunicorn worker) is the correct pattern.

    Args:
        app: The Flask application instance returned by
            :func:`flask.Flask` inside :func:`app.create_app`.

    Returns:
        ``None``.  Side effects:
            * ``app.extensions["storage_client"]`` is set to a
              ``google.cloud.storage.Client``.
            * ``app.extensions["pubsub_publisher"]`` is set to a
              ``google.cloud.pubsub_v1.PublisherClient``.
            * Flask-CORS is bound to ``app``.
    """
    # 1. CORS -- allow cross-origin requests.  The default
    #    configuration permits any origin; tighten via
    #    ``app.config["CORS_ORIGINS"]`` if the deployment requires
    #    more restrictive headers.
    cors.init_app(app)
    app.logger.info("Initialized flask-cors extension.")

    # 2. GCP Cloud Storage client (replaces ``storage_client`` from
    #    main.py line 64).  This client is thread-safe and meant to
    #    be reused across requests; one instance per worker is the
    #    correct pattern.
    storage_client = storage.Client()
    app.extensions[_STORAGE_CLIENT_KEY] = storage_client
    app.logger.info("Initialized google-cloud-storage client.")

    # 3. GCP PubSub publisher client (replaces ``publisher`` from
    #    main.py line 65).  This client is thread-safe and is shared
    #    across all PubSub publication paths -- Notifier IN_PROGRESS
    #    / DONE / ERROR notifications and downstream-job propagation.
    publisher = pubsub_v1.PublisherClient()
    app.extensions[_PUBSUB_PUBLISHER_KEY] = publisher
    app.logger.info("Initialized google-cloud-pubsub publisher client.")


def get_storage_client(app: Flask) -> storage.Client:
    """Return the application-bound ``google.cloud.storage.Client``.

    Service-layer code should prefer this typed accessor over a raw
    ``current_app.extensions["storage_client"]`` lookup so that
    callers receive a properly-typed client and a clear error message
    if extensions were never initialized.

    Args:
        app: The Flask application instance.  When called from a
            request context, pass ``current_app._get_current_object()``
            rather than the proxy, so that the function operates on
            the underlying ``Flask`` instance and not the wrapper.

    Returns:
        The shared ``google.cloud.storage.Client`` created in
        :func:`init_extensions` and stored under
        ``app.extensions["storage_client"]``.

    Raises:
        RuntimeError: If :func:`init_extensions` has not yet been
            called for ``app`` (i.e. the key
            ``"storage_client"`` is missing from ``app.extensions``).
    """
    # ``app.extensions.get(...)`` returns :data:`~typing.Any`; the
    # local annotation makes the heterogeneous-container nature of
    # ``app.extensions`` explicit and is narrowed to ``storage.Client``
    # at the return statement (which matches the function's annotated
    # return type).
    client: ExtensionInstance = app.extensions.get(_STORAGE_CLIENT_KEY)
    if client is None:
        raise RuntimeError(
            "storage_client is not initialized; call init_extensions(app) first."
        )
    return client


def get_pubsub_publisher(app: Flask) -> pubsub_v1.PublisherClient:
    """Return the application-bound PubSub ``PublisherClient``.

    Service-layer code should prefer this typed accessor over a raw
    ``current_app.extensions["pubsub_publisher"]`` lookup so that
    callers receive a properly-typed client and a clear error message
    if extensions were never initialized.

    Args:
        app: The Flask application instance.  When called from a
            request context, pass ``current_app._get_current_object()``
            rather than the proxy, so that the function operates on
            the underlying ``Flask`` instance and not the wrapper.

    Returns:
        The shared ``google.cloud.pubsub_v1.PublisherClient`` created
        in :func:`init_extensions` and stored under
        ``app.extensions["pubsub_publisher"]``.

    Raises:
        RuntimeError: If :func:`init_extensions` has not yet been
            called for ``app`` (i.e. the key
            ``"pubsub_publisher"`` is missing from ``app.extensions``).
    """
    # ``app.extensions.get(...)`` returns :data:`~typing.Any`; the
    # local annotation makes the heterogeneous-container nature of
    # ``app.extensions`` explicit and is narrowed to
    # ``pubsub_v1.PublisherClient`` at the return statement.
    publisher: ExtensionInstance = app.extensions.get(_PUBSUB_PUBLISHER_KEY)
    if publisher is None:
        raise RuntimeError(
            "pubsub_publisher is not initialized; call init_extensions(app) first."
        )
    return publisher


__all__ = [
    "init_extensions",
    "get_storage_client",
    "get_pubsub_publisher",
    "cors",
]
