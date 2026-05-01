"""AdminStorageService construction and upload helpers.

This module wraps the
:class:`blitzy_platform_shared.common.storage.AdminStorageService`
class with two pieces of API:

* :func:`build_storage_service` -- a factory that constructs an
  ``AdminStorageService`` configured for a given pipeline run,
  preserving the keyword-argument signature from the original
  ``main.py`` lines 148-153.

* Convenience wrappers (:func:`upload_repo_mapping`,
  :func:`upload_short_repo_structure`, :func:`upload_file_schemas`,
  :func:`download_tech_spec`) that delegate to the corresponding
  ``AdminStorageService`` methods.

All calls preserve the keyword-argument names from the original
``main.py`` (lines 155-160 and 208-220) verbatim.  Behavior is
unchanged from the source code: this module performs no retries,
no error swallowing, no logging, and no bucket-name resolution of
its own.  The underlying ``AdminStorageService`` is responsible for
all GCS interactions, including credential resolution, retry
policies, and authentication.

Design rationale
================

* **Decoupled from Flask.**  This module imports nothing from
  ``flask.*``.  The caller (typically
  :class:`app.services.pipeline_service.PipelineService`) is
  responsible for reading the ``PRIVATE_BLOB_NAME`` configuration
  value out of ``current_app.config`` and passing it explicitly to
  :func:`build_storage_service`.  Keeping the helpers Flask-agnostic
  makes them trivially unit-testable without a Flask application
  context and lets them be reused from background workers,
  command-line utilities, or future non-HTTP entry points.

* **No side effects at import time.**  Importing this module does
  not read environment variables, construct GCP clients, configure
  logging, or perform any network I/O.  The first network operation
  occurs only when the caller invokes one of the wrapper functions
  on a constructed :class:`AdminStorageService`.

* **Faithful preservation of the source-of-truth keyword names.**
  Every keyword-argument used in the original ``main.py`` is
  preserved verbatim.  In particular, the original code passes the
  same value for both ``project_id`` and ``task_id`` to the
  ``AdminStorageService`` constructor (``main.py`` line 150:
  ``task_id=project_id``).  This is preserved here for behavioral
  fidelity.  See :func:`build_storage_service` for details.

* **Convenience wrappers are optional.**  Callers may use the wrapper
  functions defined in this module
  (e.g. :func:`upload_repo_mapping`) or call the underlying
  ``AdminStorageService`` instance methods directly with identical
  semantics.  The wrappers exist as a forward-compatibility hook so
  that cross-cutting concerns such as logging, retries, or metrics
  can be added in a single place without modifying every call site.
  The current :class:`PipelineService` agent prompt elects to call
  the underlying methods directly (matching ``main.py`` lines
  208-220 verbatim), so the wrappers are primarily exercised by
  unit tests and by future call sites.
"""

# ---------------------------------------------------------------------------
# Standard-library imports
# ---------------------------------------------------------------------------
# ``typing`` provides the static type annotations on the public function
# signatures.  ``Any`` is used for the wrapper return types because the
# underlying ``AdminStorageService`` methods do not advertise concrete return
# types (they return ``None`` for uploads and ``str`` for downloads, but the
# ``Any`` annotation keeps this module forward-compatible should the
# upstream API evolve).  ``Dict`` types the JSON-serialisable payload
# dictionaries (``mapping_data``, ``structure_data``, ``schemas_data``) that
# the wrappers forward to the ``AdminStorageService`` instance.
from typing import Any, Dict

# ---------------------------------------------------------------------------
# Third-party imports
# ---------------------------------------------------------------------------
# ``AdminStorageService`` is the primary GCS-backed document persistence
# class shipped by ``blitzy-platform-shared`` (pinned at 0.0.720 in
# requirements.txt).  It exposes ``download_tech_spec``,
# ``upload_repo_mapping``, ``upload_short_repo_structure``, and
# ``upload_file_schemas`` methods that this module delegates to.  The
# constructor signature is::
#
#     AdminStorageService(
#         project_id: str,
#         task_id: str,
#         tech_spec_id: str,
#         blob_name: str = 'private-src',
#         upload_to_new_folder: bool = True,
#     )
#
# Only the first four arguments are exercised from this module; the
# ``upload_to_new_folder`` argument is left at its default value, matching
# the original ``main.py`` lines 148-153.
from blitzy_platform_shared.common.storage import AdminStorageService

# ---------------------------------------------------------------------------
# Public API surface
# ---------------------------------------------------------------------------
# Explicitly listing the public symbols here both documents the module's
# API and limits what ``from app.services.storage_service import *`` would
# expose -- although star imports are discouraged, the ``__all__``
# declaration also helps tooling such as Sphinx autodoc and IDE
# auto-completion identify the supported entry points.
__all__ = [
    "build_storage_service",
    "upload_repo_mapping",
    "upload_short_repo_structure",
    "upload_file_schemas",
    "download_tech_spec",
]


# ---------------------------------------------------------------------------
# Factory: construct a configured AdminStorageService
# ---------------------------------------------------------------------------
def build_storage_service(
    project_id: str,
    tech_spec_id: str,
    private_blob_name: str,
) -> AdminStorageService:
    """Construct a configured :class:`AdminStorageService`.

    Direct port of the inline construction from ``main.py`` lines
    148-153.  Every keyword argument is preserved verbatim.

    Note that ``main.py`` passes the same value for both
    ``project_id`` and ``task_id`` (line 150: ``task_id=project_id``).
    This is preserved here for behavioral fidelity -- it is NOT a
    typo in the original code; it is the actual behavior the system
    relies on for tenant scoping inside the GCS bucket.  Per AAP
    Section 0.7.1 ("Preserve all multi-tenant isolation"), this
    quirk is propagated unchanged.

    Args:
        project_id: The pipeline run's project ID.  Used for both
            ``project_id`` and ``task_id`` of the storage service
            (matching the original ``main.py`` line 150 behavior).
        tech_spec_id: The technical specification ID associated with
            this run.  The ``AdminStorageService`` uses this to
            namespace the GCS object keys for the spec's private
            artifacts.
        private_blob_name: The GCS blob name for private storage.
            Typically read from
            ``current_app.config["PRIVATE_BLOB_NAME"]`` by the
            caller.  Maps to the ``blob_name`` constructor argument
            of :class:`AdminStorageService`.

    Returns:
        A new :class:`AdminStorageService` instance ready to perform
        ``download_tech_spec``, ``upload_repo_mapping``,
        ``upload_short_repo_structure``, and ``upload_file_schemas``
        operations against the configured GCS bucket.

    Example:
        >>> from flask import current_app
        >>> svc = build_storage_service(
        ...     project_id="proj-123",
        ...     tech_spec_id="ts-456",
        ...     private_blob_name=current_app.config["PRIVATE_BLOB_NAME"],
        ... )
        >>> isinstance(svc, AdminStorageService)
        True
    """
    return AdminStorageService(
        project_id=project_id,
        task_id=project_id,
        tech_spec_id=tech_spec_id,
        blob_name=private_blob_name,
    )


# ---------------------------------------------------------------------------
# Wrapper: upload the repository file mapping JSON to GCS
# ---------------------------------------------------------------------------
def upload_repo_mapping(
    storage_service: AdminStorageService,
    code_gen_id: str,
    mapping_data: Dict[str, Any],
) -> Any:
    """Upload the repository file mapping JSON to GCS.

    Direct delegation to ``AdminStorageService.upload_repo_mapping``
    with keyword-argument names preserved from ``main.py`` lines
    208-211.

    Args:
        storage_service: The :class:`AdminStorageService` instance
            (typically produced by :func:`build_storage_service`).
        code_gen_id: The code-generation run ID; used as the GCS
            object key prefix for the uploaded mapping document.
        mapping_data: The file-mapping payload, typically
            ``result["file_mapping"]`` from the LangGraph pipeline.

    Returns:
        Whatever the underlying
        ``AdminStorageService.upload_repo_mapping`` returns
        (typically ``None`` or the GCS object URI).
    """
    return storage_service.upload_repo_mapping(
        code_gen_id=code_gen_id,
        mapping_data=mapping_data,
    )


# ---------------------------------------------------------------------------
# Wrapper: upload the short repository structure JSON to GCS
# ---------------------------------------------------------------------------
def upload_short_repo_structure(
    storage_service: AdminStorageService,
    code_gen_id: str,
    structure_data: Dict[str, Any],
) -> Any:
    """Upload the short repository structure JSON to GCS.

    Direct delegation to
    ``AdminStorageService.upload_short_repo_structure`` with
    keyword-argument names preserved from ``main.py`` lines 213-216.

    Args:
        storage_service: The :class:`AdminStorageService` instance
            (typically produced by :func:`build_storage_service`).
        code_gen_id: The code-generation run ID; used as the GCS
            object key prefix for the uploaded structure document.
        structure_data: The short repo structure payload, typically
            ``result["short_repo_structure"]`` from the LangGraph
            pipeline.

    Returns:
        Whatever the underlying
        ``AdminStorageService.upload_short_repo_structure`` returns
        (typically ``None`` or the GCS object URI).
    """
    return storage_service.upload_short_repo_structure(
        code_gen_id=code_gen_id,
        structure_data=structure_data,
    )


# ---------------------------------------------------------------------------
# Wrapper: upload the per-file schemas JSON to GCS
# ---------------------------------------------------------------------------
def upload_file_schemas(
    storage_service: AdminStorageService,
    code_gen_id: str,
    schemas_data: Dict[str, Any],
) -> Any:
    """Upload the per-file schemas JSON to GCS.

    Direct delegation to ``AdminStorageService.upload_file_schemas``
    with keyword-argument names preserved from ``main.py`` lines
    218-220.

    Args:
        storage_service: The :class:`AdminStorageService` instance
            (typically produced by :func:`build_storage_service`).
        code_gen_id: The code-generation run ID; used as the GCS
            object key prefix for the uploaded schemas document.
        schemas_data: The file-schemas payload, typically
            ``result["file_schemas"]`` from the LangGraph pipeline.

    Returns:
        Whatever the underlying
        ``AdminStorageService.upload_file_schemas`` returns
        (typically ``None`` or the GCS object URI).
    """
    return storage_service.upload_file_schemas(
        code_gen_id=code_gen_id,
        schemas_data=schemas_data,
    )


# ---------------------------------------------------------------------------
# Wrapper: download the technical specification document from GCS
# ---------------------------------------------------------------------------
def download_tech_spec(
    storage_service: AdminStorageService,
    tech_spec_id: str,
    head_commit_hash: str,
) -> Any:
    """Download the technical specification document from GCS.

    Direct delegation to ``AdminStorageService.download_tech_spec``
    with keyword-argument names preserved from ``main.py`` lines
    155-160.  The returned document is typically passed to
    :func:`blitzy_platform_shared.document.utils.clean_document`
    before further processing by the LangGraph pipeline.

    Args:
        storage_service: The :class:`AdminStorageService` instance
            (typically produced by :func:`build_storage_service`).
        tech_spec_id: The technical specification ID to download.
        head_commit_hash: The commit hash for which the spec was
            generated; used by ``AdminStorageService`` to locate the
            correct version of the GCS object.

    Returns:
        The raw tech-spec document content (typically a string),
        unmodified from the underlying
        ``AdminStorageService.download_tech_spec`` return value.
    """
    return storage_service.download_tech_spec(
        tech_spec_id=tech_spec_id,
        head_commit_hash=head_commit_hash,
    )
