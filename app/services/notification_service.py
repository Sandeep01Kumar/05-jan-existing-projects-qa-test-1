"""Notifier construction helpers for the Flask application.

This module owns the construction of the
:class:`blitzy_platform_shared.notifier.Notifier` and its supporting
:class:`NotificationData` and :class:`BaseMetadata` value objects.

The original ``main.py`` (lines 254-281) constructed the Notifier
inline at the start of the ``__main__`` block.  In the Flask
migration, the construction is extracted here so :class:`PipelineService`
can stay focused on orchestration, the notifier can be unit-tested in
isolation, and other code paths can reuse the same construction
pattern.

The :func:`build_notifier` factory preserves every keyword argument
of the original construction calls verbatim, including
``phase=ProjectPhase.FILE_MAPPING``.  This is required by the AAP's
rule (Section 0.7.1: "Preserve all PubSub notification schemas") to
preserve the exact message schema with ``project_id``, ``job_id``,
``tech_spec_id``, ``code_gen_id``, ``org_name``, ``repo_id``,
``branch_name``, ``user_id``, and ``git_project_repo_id`` fields.

Design rationale
================

* **Pure helper function.**  This module exposes only a single
  factory function with no module-level state.  It is fully
  decoupled from Flask, GCP environment variables, and the rest of
  the application -- the caller passes everything in.  This makes
  it trivially testable from unit tests, standalone scripts, and
  background worker contexts that do not have a Flask application
  context.

* **Decoupled from Flask.**  This module imports nothing from
  ``flask.*``.  The caller (typically
  :class:`app.services.pipeline_service.PipelineService`) is
  responsible for reading the ``PROJECT_ID`` and
  ``PLATFORM_EVENTS_TOPIC`` configuration values out of
  ``current_app.config`` and the shared
  :class:`pubsub_v1.PublisherClient` singleton out of
  ``current_app.extensions["pubsub_publisher"]`` before invoking
  this factory.  Keeping the helper Flask-agnostic mirrors the
  pattern established by :mod:`app.services.storage_service` and
  :mod:`app.services.trace_service`.

* **No side effects at import time.**  Importing this module does
  not read environment variables, construct GCP clients, configure
  logging, or perform any network I/O.  The first network operation
  occurs only when the caller invokes a method on the constructed
  :class:`Notifier` (``notify_started``, ``notify_completion``, or
  ``notify_failure``).

* **Faithful preservation of the source-of-truth keyword names.**
  Every keyword argument used in the original ``main.py`` is
  preserved verbatim.  In particular, ``phase=ProjectPhase.FILE_MAPPING``
  is hard-coded -- the AAP rule "Preserve all PubSub notification
  schemas" requires this enum value because downstream PubSub
  consumers identify the pipeline phase from this field.  The
  ``.get()`` defaults exactly match the values used in
  ``main.py`` lines 237-252.  This guarantees that absent fields in
  the request payload are filled with the same defaults the
  original code used (e.g. ``"default"`` for ``repo_id`` and
  ``user_id``, ``"main"`` for ``branch_name``, and ``True`` for
  ``propagate``).

* **Thread safety.**  The :class:`Notifier` constructor is
  thread-safe (it just stores its arguments).  The :class:`Notifier`
  itself is NOT thread-safe in the sense that concurrent
  ``notify_*`` calls on the same instance could race, but every
  request constructs its own :class:`Notifier` via this factory so
  there is no cross-request sharing.

Example
=======

The following example illustrates how :class:`PipelineService` will
typically use this factory inside a Flask request handler::

    from flask import current_app
    from app.services.notification_service import build_notifier
    from app.extensions import get_pubsub_publisher

    def handle_request(payload):
        publisher = get_pubsub_publisher(current_app._get_current_object())
        notifier = build_notifier(
            payload=payload,
            publisher=publisher,
            project_id=current_app.config["PROJECT_ID"],
            platform_events_topic=current_app.config["PLATFORM_EVENTS_TOPIC"],
        )
        notifier.notify_started()
        try:
            ...  # run pipeline
            notifier.notify_completion()
        except Exception as exc:
            notifier.notify_failure(str(exc))
            raise
"""

# ---------------------------------------------------------------------------
# Standard-library imports
# ---------------------------------------------------------------------------
# ``typing`` is used purely for static type annotations on the public
# :func:`build_notifier` signature.  ``Dict[str, Any]`` types the parsed
# JSON request body that the caller forwards from the HTTP layer (the
# Flask migration replaces the ``EVENT_DATA`` environment-variable parse
# in the original ``main.py`` with a ``request.get_json()`` call); ``Any``
# permits arbitrary value types in that mapping (the original payload
# carries strings, booleans, lists, and nested dicts).
from typing import Any, Dict

# ---------------------------------------------------------------------------
# Third-party imports (listed in alphabetical order expected by isort/black)
# ---------------------------------------------------------------------------
# Each third-party import below is annotated in this header block rather
# than between the import statements themselves: keeping the imports
# adjacent (no inline comments and no blank lines between them) is what
# the project's default isort + black configuration requires, mirroring
# the convention in :mod:`app.extensions`.
#
# * ``Notifier`` -- the canonical PubSub notification publisher shipped by
#   ``blitzy-platform-shared`` (private package, GCP Artifact Registry,
#   pinned at 0.0.720 per the AAP).  It is constructed with a
#   :class:`NotificationData` value object (request-specific identifiers
#   such as ``project_id`` and ``tech_spec_id``) and a :class:`BaseMetadata`
#   value object (cross-cutting flags such as ``propagate``).  All three
#   classes ride together as the source-of-truth for the PubSub message
#   schema, so they are imported as a single statement.
# * ``ProjectPhase`` -- the canonical enum identifying which Blitzy pipeline
#   phase emitted a notification.  ``ProjectPhase.FILE_MAPPING`` is the
#   value used by the original ``main.py`` (line 278) and MUST be preserved
#   verbatim per AAP Section 0.7.1 ("Preserve all PubSub notification
#   schemas") so that downstream PubSub consumers can route events
#   correctly.  ``blitzy-utils`` is a private internal package served from
#   the GCP Artifact Registry (pinned at 0.0.542 per the AAP; the setup
#   log records 0.0.582 installed -- both versions expose the same
#   ``ProjectPhase.FILE_MAPPING`` enum member).
# * ``google.cloud.pubsub_v1`` -- imported solely for the
#   ``pubsub_v1.PublisherClient`` type annotation on the ``publisher``
#   parameter of :func:`build_notifier`.  The actual client instance is
#   constructed once per Flask process in
#   :func:`app.extensions.init_extensions` (where it replaces the
#   module-level singleton from the original ``main.py`` line 65) and is
#   passed in by the caller -- this module does not construct or hold any
#   GCP client of its own.  ``google-cloud-pubsub`` is pinned at 2.36.0 in
#   ``requirements.txt`` (the installed version is 2.37.0 per the setup
#   log; both are API-compatible for the ``pubsub_v1`` namespace).
from blitzy_platform_shared.notifier import (
    BaseMetadata,
    NotificationData,
    Notifier,
)
from blitzy_utils.enums import ProjectPhase
from google.cloud import pubsub_v1

# ---------------------------------------------------------------------------
# Public API surface
# ---------------------------------------------------------------------------
# Only :func:`build_notifier` is part of the module's public API.  The
# imported helper classes are re-exported only via their original
# fully-qualified import paths (``blitzy_platform_shared.notifier.*``);
# duplicating them in ``__all__`` here would introduce two canonical
# import paths for the same symbol and invite confusion.
__all__ = ["build_notifier"]


def build_notifier(
    payload: Dict[str, Any],
    publisher: pubsub_v1.PublisherClient,
    project_id: str,
    platform_events_topic: str,
) -> Notifier:
    """Construct a configured :class:`Notifier` for the given request.

    This is a direct port of the inline notifier construction from
    ``main.py`` lines 254-281.  Every keyword argument is preserved
    verbatim, including ``phase=ProjectPhase.FILE_MAPPING``.  The
    ``.get()`` default values mirror the per-field defaults used at
    ``main.py`` lines 237-252 so that absent fields in the HTTP
    request body are filled with the same defaults the original
    Cloud Run Job applied to absent ``EVENT_DATA`` fields.

    Args:
        payload: The HTTP request body parsed as a Python dict
            (equivalent to ``event_data`` in the original
            ``main.py``).  The function reads the following fields
            using ``.get()`` with sensible defaults:

            * ``project_id`` (default ``""``)
            * ``job_id`` (default ``""``)
            * ``tech_spec_id`` (default ``""``)
            * ``code_gen_id`` (default ``""``)
            * ``org_name`` (default ``""``)
            * ``repo_id`` (default ``"default"``)
            * ``branch_name`` (default ``"main"``)
            * ``user_id`` (default ``"default"``)
            * ``git_project_repo_id`` (default ``""``)
            * ``propagate`` (default ``True``)
            * ``repo_name`` (default ``None``)

            The function does not mutate ``payload``.

        publisher: Shared :class:`google.cloud.pubsub_v1.PublisherClient`
            singleton, fetched from
            ``current_app.extensions["pubsub_publisher"]`` by the
            caller (typically via
            :func:`app.extensions.get_pubsub_publisher`).  This client
            is thread-safe and is reused across requests -- one
            instance per Flask process is the correct pattern.

        project_id: GCP project ID where the PubSub topic resides,
            read from ``current_app.config["PROJECT_ID"]`` by the
            caller.  This is the GLOBAL ``PROJECT_ID`` (the GCP
            project hosting the platform-events PubSub topic), NOT
            the ``payload["project_id"]`` field which identifies the
            Blitzy *project* being processed -- the two values are
            independent and may differ.

        platform_events_topic: PubSub topic name for IN_PROGRESS /
            DONE / ERROR events, read from
            ``current_app.config["PLATFORM_EVENTS_TOPIC"]`` by the
            caller.  Forwarded as the ``topic_id`` argument to the
            :class:`Notifier` constructor.

    Returns:
        A fully configured :class:`Notifier` ready to emit
        ``notify_started``, ``notify_completion``, and
        ``notify_failure`` events.  The notifier's ``phase`` is set to
        :attr:`ProjectPhase.FILE_MAPPING`, matching the original
        ``main.py`` line 278.  No PubSub I/O is performed by this
        factory -- publication occurs only when the caller invokes a
        ``notify_*`` method on the returned instance.
    """
    # ---------------------------------------------------------------
    # 1. Build the per-request ``NotificationData`` value object.
    # ---------------------------------------------------------------
    # Every keyword argument below is preserved verbatim from
    # ``main.py`` lines 256-266 and the corresponding defaults at
    # ``main.py`` lines 237-252 (where the original code reads
    # ``event_data.get(<field>, <default>)``).  The function is
    # intentionally explicit about every field name so that any
    # future schema change to ``NotificationData`` will surface as a
    # type error here rather than silently dropping a field.
    notification_data = NotificationData(
        project_id=payload.get("project_id", ""),
        job_id=payload.get("job_id", ""),
        tech_spec_id=payload.get("tech_spec_id", ""),
        code_gen_id=payload.get("code_gen_id", ""),
        org_name=payload.get("org_name", ""),
        repo_id=payload.get("repo_id", "default"),
        branch_name=payload.get("branch_name", "main"),
        user_id=payload.get("user_id", "default"),
        git_project_repo_id=payload.get("git_project_repo_id", ""),
    )

    # ---------------------------------------------------------------
    # 2. Build the cross-cutting ``BaseMetadata`` value object.
    # ---------------------------------------------------------------
    # ``propagate`` defaults to ``True`` (matching ``main.py`` line
    # 251) so that downstream-job propagation is enabled by default.
    # ``repo_name`` defaults to ``None`` (matching ``main.py`` line
    # 252) -- the underlying ``BaseMetadata`` accepts ``str | None``
    # so passing ``None`` for an absent field is safe.
    base_metadata = BaseMetadata(
        propagate=payload.get("propagate", True),
        repo_name=payload.get("repo_name"),
    )

    # ---------------------------------------------------------------
    # 3. Construct and return the configured ``Notifier``.
    # ---------------------------------------------------------------
    # The ``phase=ProjectPhase.FILE_MAPPING`` argument is hard-coded
    # because every notification this service emits belongs to the
    # FILE_MAPPING phase (the reverse-document/file-mapping pipeline
    # is the only producer in this Cloud Run service).  Per AAP
    # Section 0.7.1 ("Preserve all PubSub notification schemas")
    # this enum value MUST be preserved verbatim from ``main.py``
    # line 278.  Downstream PubSub consumers route events based on
    # this field, so changing it would silently break the
    # observability pipeline.
    notifier = Notifier(
        publisher=publisher,
        gcp_project_id=project_id,
        topic_id=platform_events_topic,
        phase=ProjectPhase.FILE_MAPPING,
        notification_data=notification_data,
        base_metadata=base_metadata,
    )
    return notifier
