"""Environment-based Flask configuration classes.

Each subclass of :class:`Config` represents a deployment environment
(development, staging, QA, production, testing).  The factory
function :func:`get_config` selects a class based on the
``FLASK_ENV`` environment variable (or an explicit argument) and
returns it for use with ``app.config.from_object(...)``.

All 22+ environment variables consumed by the original ``main.py``
are preserved as class attributes so service-layer code can access
them via ``current_app.config[...]``.  Required variables (those
without defaults) will raise ``RuntimeError`` from
:func:`Config.validate` if missing at startup; optional variables
fall back to sensible defaults.

Beyond the variables consumed by the original ``main.py``, the
:class:`Config` class also exposes a :attr:`Config.CORS_ORIGINS`
attribute that is consumed by :func:`app.extensions.init_extensions`
to harden the Flask-CORS extension against CWE-942 (Permissive
Cross-domain Policy with Untrusted Domains) by populating an explicit
allow-list rather than relying on the permissive default of
reflecting any origin.

Usage:
    >>> from app.config import get_config
    >>> ConfigClass = get_config("production")
    >>> app.config.from_object(ConfigClass)
    >>> ConfigClass.validate()  # raises RuntimeError if vars missing

Environment names recognized by :func:`get_config`:
    - ``"development"`` / ``"dev"``        -> :class:`DevelopmentConfig`
    - ``"staging"``     / ``"stage"``      -> :class:`StagingConfig`
    - ``"qa"``                             -> :class:`QAConfig`
    - ``"production"``  / ``"prod"``       -> :class:`ProductionConfig`
    - ``"testing"``     / ``"test"``       -> :class:`TestingConfig`

This module is foundational: it MUST NOT import anything from
``app.__init__`` or other ``app.*`` modules, only from the Python
standard library.  This avoids circular imports during Flask
application factory initialization.
"""

import os
from typing import List, Optional, Type


def _parse_cors_origins(raw: str) -> List[str]:
    """Parse a comma-separated CORS allow-list from an env-var string.

    Splits ``raw`` on commas, strips whitespace from each entry, and
    drops empty entries.  Returns an empty list when ``raw`` is empty
    or contains only whitespace and commas, which is the safe
    fail-closed default for production-class deployments (see
    :class:`Config.CORS_ORIGINS`).

    Args:
        raw: The raw value of the ``CORS_ORIGINS`` environment
            variable (or any equivalent comma-separated string).

    Returns:
        The parsed list of origin URLs.  May be empty.

    Examples:
        >>> _parse_cors_origins("")
        []
        >>> _parse_cors_origins("https://app.blitzy.com")
        ['https://app.blitzy.com']
        >>> _parse_cors_origins("https://a.example.com, https://b.example.com")
        ['https://a.example.com', 'https://b.example.com']
        >>> _parse_cors_origins("*")
        ['*']
    """
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


class Config:
    """Base configuration class.

    Reads all environment variables consumed by the application.
    Subclasses override the ``ENV`` attribute and may override any
    other attribute as needed.

    Flask reads UPPERCASE attributes from this class via
    ``app.config.from_object(Config)`` and copies them into the
    ``app.config`` mapping.  Lowercase attributes are ignored by
    Flask, which is why every configuration field declared here is
    in UPPERCASE.

    Environment variables are read at module load time (when the
    class body is evaluated by the Python interpreter), which
    matches the behavior of the original ``main.py``.  Tests that
    need to inject custom values must set ``os.environ`` *before*
    importing this module, or use :class:`TestingConfig` which
    provides safe placeholder values.
    """

    # ------------------------------------------------------------------
    # Flask built-ins
    # ------------------------------------------------------------------
    ENV: str = "production"
    DEBUG: bool = False
    TESTING: bool = False
    JSON_SORT_KEYS: bool = False  # Preserve JSON field ordering in responses

    # ------------------------------------------------------------------
    # CORS allow-list (security hardening — see ``app/extensions.py``)
    # ------------------------------------------------------------------
    # ``CORS_ORIGINS`` is a list of origin URLs that the API will
    # accept cross-origin requests from.  It is consumed by
    # :func:`app.extensions.init_extensions`, which forwards the value
    # to ``flask_cors.CORS.init_app(app, origins=...)``.
    #
    # The default is an EMPTY LIST (``[]``), which is fail-closed: no
    # browser cross-origin reflection occurs unless an operator
    # explicitly opts in by either (a) setting the ``CORS_ORIGINS``
    # environment variable to a comma-separated allow-list, or
    # (b) overriding ``CORS_ORIGINS`` in a subclass (see
    # :class:`DevelopmentConfig` which uses ``["*"]`` for local dev).
    #
    # This protects against CWE-942 (Permissive Cross-domain Policy
    # with Untrusted Domains).  Without this attribute,
    # ``flask-cors`` reflects any value of the request ``Origin``
    # header into ``Access-Control-Allow-Origin`` -- an unsafe
    # default for a Cloud Run Service exposed on the public internet.
    #
    # Typical production values come from the env-config YAML files,
    # for example::
    #
    #     CORS_ORIGINS=https://app.blitzy.com,https://staging.blitzy.com
    #
    # which is parsed by :func:`_parse_cors_origins` into
    # ``["https://app.blitzy.com", "https://staging.blitzy.com"]``.
    CORS_ORIGINS: List[str] = _parse_cors_origins(os.environ.get("CORS_ORIGINS", ""))

    # ------------------------------------------------------------------
    # Project / GCP identifiers (REQUIRED)
    # ------------------------------------------------------------------
    # ``PROJECT_ID`` is the GCP project ID where Cloud Run, GCS, and
    # PubSub resources live.  Read by Notifier and AdminStorageService.
    PROJECT_ID: Optional[str] = os.environ.get("PROJECT_ID")
    # ``SERVICE_NAME`` is the Cloud Run service identifier; preserved
    # from the GitHub Actions workflow (``SERVICE_NAME`` env var).
    SERVICE_NAME: Optional[str] = os.environ.get(
        "SERVICE_NAME", "archie-job-reverse-file-mapper"
    )

    # ------------------------------------------------------------------
    # GCS storage configuration (REQUIRED)
    # ------------------------------------------------------------------
    GCS_BUCKET_NAME: Optional[str] = os.environ.get("GCS_BUCKET_NAME")
    PRIVATE_BLOB_NAME: Optional[str] = os.environ.get("PRIVATE_BLOB_NAME")

    # ------------------------------------------------------------------
    # PubSub topics (REQUIRED)
    # ------------------------------------------------------------------
    # The ``PLATFORM_EVENTS_TOPIC`` is where Notifier publishes
    # IN_PROGRESS / DONE / ERROR events.
    PLATFORM_EVENTS_TOPIC: Optional[str] = os.environ.get("PLATFORM_EVENTS_TOPIC")
    # The ``GENERATE_REVERSE_THINKING_TOPIC`` is where main.py
    # publishes the next-stage trigger via publish_notification.
    GENERATE_REVERSE_THINKING_TOPIC: Optional[str] = os.environ.get(
        "GENERATE_REVERSE_THINKING_TOPIC"
    )

    # ------------------------------------------------------------------
    # Service URLs (REQUIRED)
    # ------------------------------------------------------------------
    GITHUB_SECRET_SERVER: Optional[str] = os.environ.get("GITHUB_SECRET_SERVER")
    SERVICE_URL_GITHUB: Optional[str] = os.environ.get("SERVICE_URL_GITHUB")
    SERVICE_URL_RELAY: Optional[str] = os.environ.get("SERVICE_URL_RELAY")
    SERVICE_URL_ADMIN: Optional[str] = os.environ.get("SERVICE_URL_ADMIN")

    # ------------------------------------------------------------------
    # LLM Provider API keys (REQUIRED)
    # ------------------------------------------------------------------
    ANTHROPIC_API_KEY: Optional[str] = os.environ.get("ANTHROPIC_API_KEY")
    OPENAI_API_KEY: Optional[str] = os.environ.get("OPENAI_API_KEY")
    VOYAGE_API_KEY: Optional[str] = os.environ.get("VOYAGE_API_KEY")
    GOOGLE_API_KEY: Optional[str] = os.environ.get("GOOGLE_API_KEY")

    # ------------------------------------------------------------------
    # Neo4j credentials (used by underlying libraries)
    # ------------------------------------------------------------------
    # NOTE: The application no longer reads Neo4j creds from env vars
    # directly; they are looked up per-request via
    # ``get_company_neo4j_instance_credentials(company_id)``.  These
    # values are still exposed for any code path that may consult them.
    NEO4J_SERVER: Optional[str] = os.environ.get("NEO4J_SERVER")
    NEO4J_USERNAME: Optional[str] = os.environ.get("NEO4J_USERNAME")
    NEO4J_PASSWORD: Optional[str] = os.environ.get("NEO4J_PASSWORD")

    # ------------------------------------------------------------------
    # LangSmith observability (REQUIRED in production)
    # ------------------------------------------------------------------
    LANGSMITH_TRACING: Optional[str] = os.environ.get("LANGSMITH_TRACING")
    LANGSMITH_ENDPOINT: Optional[str] = os.environ.get("LANGSMITH_ENDPOINT")
    LANGSMITH_API_KEY: Optional[str] = os.environ.get("LANGSMITH_API_KEY")
    LANGSMITH_PROJECT: Optional[str] = os.environ.get("LANGSMITH_PROJECT")

    # ------------------------------------------------------------------
    # Misc tuning (OPTIONAL with defaults)
    # ------------------------------------------------------------------
    # ``USE_RUNNER`` is consumed by ``blitzy_platform_shared`` /
    # ``blitzy_utils`` (e.g., ``should_use_runner()``) to decide
    # whether to delegate execution to a remote runner.
    USE_RUNNER: Optional[str] = os.environ.get("USE_RUNNER")
    # ``TOKENIZERS_PARALLELISM`` is read by HuggingFace / tokenizers
    # to silence the parallelism warning when forking workers.
    TOKENIZERS_PARALLELISM: Optional[str] = os.environ.get(
        "TOKENIZERS_PARALLELISM", "false"
    )
    # ``IN_PROGRESS_EVENT_FREQUENCY`` controls how often "in progress"
    # PubSub events are emitted (every N folders).  Defaults to 1 so
    # every progress update is published.  Stored as ``int`` (the
    # original ``main.py`` cast it via ``int(os.environ.get(...))``).
    IN_PROGRESS_EVENT_FREQUENCY: int = int(
        os.environ.get("IN_PROGRESS_EVENT_FREQUENCY", "1")
    )

    # ------------------------------------------------------------------
    # List of required variable names (for validate)
    # ------------------------------------------------------------------
    # These are the env vars that the original ``main.py`` reads with
    # ``os.environ["..."]`` (subscript form, which raises ``KeyError``
    # if missing).  Optional vars use ``os.environ.get(...)`` and are
    # NOT included here.  The ``validate()`` classmethod iterates this
    # tuple to determine which attributes must be set.
    REQUIRED_VARS: tuple = (
        "PROJECT_ID",
        "GCS_BUCKET_NAME",
        "PRIVATE_BLOB_NAME",
        "PLATFORM_EVENTS_TOPIC",
        "GENERATE_REVERSE_THINKING_TOPIC",
        "GITHUB_SECRET_SERVER",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "VOYAGE_API_KEY",
        "GOOGLE_API_KEY",
        "LANGSMITH_TRACING",
        "LANGSMITH_ENDPOINT",
        "LANGSMITH_API_KEY",
        "LANGSMITH_PROJECT",
    )

    @classmethod
    def validate(cls) -> None:
        """Verify that all required environment variables are set.

        Iterates :attr:`REQUIRED_VARS` and checks that every named
        attribute on this class evaluates as truthy.  Raises a clear
        ``RuntimeError`` listing the missing variables when any are
        absent so operators can quickly diagnose deployment-time
        configuration errors.

        Raises:
            RuntimeError: If any required variable is missing or
                evaluates as falsy (``None``, empty string, etc.).
        """
        missing = [name for name in cls.REQUIRED_VARS if not getattr(cls, name, None)]
        if missing:
            raise RuntimeError(
                "Missing required environment variables: " + ", ".join(sorted(missing))
            )


class DevelopmentConfig(Config):
    """Local development configuration.

    Enables debug mode and verbose logging.  Uses default env-var
    values where available so developers can run the app without
    populating every secret.
    """

    ENV: str = "development"
    DEBUG: bool = True

    # ------------------------------------------------------------------
    # CORS allow-list — permissive for local development convenience.
    # ------------------------------------------------------------------
    # In local development we accept any origin so a developer can
    # easily exercise the API from a localhost UI on any port (e.g.,
    # ``http://localhost:3000``, ``http://localhost:5173``).  An
    # explicit ``CORS_ORIGINS`` env-var value still wins over this
    # default because the base class reads it at import time and
    # subclass body assignment runs later in the MRO.  To force the
    # operator-provided env value through, an explicit override is
    # used: if ``CORS_ORIGINS`` env var is set, parse it; otherwise
    # default to ``["*"]``.
    CORS_ORIGINS: List[str] = _parse_cors_origins(os.environ.get("CORS_ORIGINS", "*"))


class StagingConfig(Config):
    """Staging configuration.

    Used for the ``stage`` deployment environment per the
    GitHub Actions workflow.  No debug mode; production-like settings.

    ``CORS_ORIGINS`` inherits the fail-closed default of ``[]`` from
    :class:`Config`.  Operators MUST set ``CORS_ORIGINS`` in
    ``env_config/env-stage.yaml`` to an explicit allow-list of
    origins (e.g., ``https://staging.blitzy.com``) for browser
    cross-origin requests to be accepted.
    """

    ENV: str = "staging"
    DEBUG: bool = False


class QAConfig(Config):
    """QA configuration.

    The ``qa`` GitHub Actions branch deploys to this environment
    (per ``Makefile`` ``ENV ?= qa`` and the ``qa`` workflow trigger).

    ``CORS_ORIGINS`` inherits the fail-closed default of ``[]`` from
    :class:`Config`.  Operators MUST set ``CORS_ORIGINS`` in
    ``env_config/env-qa.yaml`` to an explicit allow-list of origins
    (e.g., ``https://qa.blitzy.com``) for browser cross-origin
    requests to be accepted.
    """

    ENV: str = "qa"
    DEBUG: bool = False


class ProductionConfig(Config):
    """Production configuration.

    Strict configuration for the production Cloud Run Service.
    DEBUG is forced off and all required variables must be present
    (call :meth:`Config.validate` at application startup).

    ``CORS_ORIGINS`` inherits the fail-closed default of ``[]`` from
    :class:`Config`.  Operators MUST set ``CORS_ORIGINS`` in
    ``env_config/env-prod.yaml`` to an explicit allow-list of
    origins (e.g., ``https://app.blitzy.com``) for browser
    cross-origin requests to be accepted.  The default of ``[]``
    denies all browser cross-origin requests so misconfiguration
    fails closed (CWE-942 mitigation).
    """

    ENV: str = "production"
    DEBUG: bool = False


class TestingConfig(Config):
    """Pytest / unit-test configuration.

    Enables ``TESTING`` mode and provides safe defaults for all
    required variables so tests can run without GCP credentials.
    The :meth:`validate` check is skipped (overridden to no-op).

    Tests should never fail because of missing env vars.  Each
    required variable has a placeholder default that satisfies
    truthiness checks but does NOT correspond to a real GCP / API
    resource (test code is expected to mock the underlying clients).
    """

    ENV: str = "testing"
    DEBUG: bool = True
    TESTING: bool = True

    # ------------------------------------------------------------------
    # CORS allow-list — empty to verify request handling without
    # CORS reflection.
    # ------------------------------------------------------------------
    # Tests use an empty allow-list so they can verify that the API
    # behaves correctly regardless of CORS reflection (no
    # ``Access-Control-Allow-Origin`` header is added to responses
    # unless an explicit allow-list is provided).  Tests that
    # specifically need to verify CORS-allowed-origin behavior should
    # construct their own Flask app via :func:`app.create_app` with
    # an explicit ``CORS_ORIGINS`` override.
    CORS_ORIGINS: List[str] = []

    # ------------------------------------------------------------------
    # Safe placeholders so service code that reads config in tests
    # doesn't crash on ``None`` values.  These are NOT used to make
    # real GCP / API calls (tests mock the underlying clients).
    # ------------------------------------------------------------------
    PROJECT_ID: Optional[str] = os.environ.get("PROJECT_ID", "test-project")
    GCS_BUCKET_NAME: Optional[str] = os.environ.get("GCS_BUCKET_NAME", "test-bucket")
    PRIVATE_BLOB_NAME: Optional[str] = os.environ.get(
        "PRIVATE_BLOB_NAME", "private-src"
    )
    PLATFORM_EVENTS_TOPIC: Optional[str] = os.environ.get(
        "PLATFORM_EVENTS_TOPIC", "platform-events"
    )
    GENERATE_REVERSE_THINKING_TOPIC: Optional[str] = os.environ.get(
        "GENERATE_REVERSE_THINKING_TOPIC", "generate-reverse-thinking"
    )
    GITHUB_SECRET_SERVER: Optional[str] = os.environ.get(
        "GITHUB_SECRET_SERVER", "https://example.invalid"
    )
    SERVICE_URL_GITHUB: Optional[str] = os.environ.get(
        "SERVICE_URL_GITHUB", "https://example.invalid"
    )
    SERVICE_URL_RELAY: Optional[str] = os.environ.get(
        "SERVICE_URL_RELAY", "https://example.invalid"
    )
    SERVICE_URL_ADMIN: Optional[str] = os.environ.get(
        "SERVICE_URL_ADMIN", "https://example.invalid"
    )
    ANTHROPIC_API_KEY: Optional[str] = os.environ.get(
        "ANTHROPIC_API_KEY", "test-anthropic-key"
    )
    OPENAI_API_KEY: Optional[str] = os.environ.get("OPENAI_API_KEY", "test-openai-key")
    VOYAGE_API_KEY: Optional[str] = os.environ.get("VOYAGE_API_KEY", "test-voyage-key")
    GOOGLE_API_KEY: Optional[str] = os.environ.get("GOOGLE_API_KEY", "test-google-key")
    LANGSMITH_TRACING: Optional[str] = os.environ.get("LANGSMITH_TRACING", "false")
    LANGSMITH_ENDPOINT: Optional[str] = os.environ.get(
        "LANGSMITH_ENDPOINT", "https://example.invalid"
    )
    LANGSMITH_API_KEY: Optional[str] = os.environ.get(
        "LANGSMITH_API_KEY", "test-langsmith-key"
    )
    LANGSMITH_PROJECT: Optional[str] = os.environ.get(
        "LANGSMITH_PROJECT", "test-project"
    )

    @classmethod
    def validate(cls) -> None:  # type: ignore[override]
        """Skip required-variable validation for tests.

        Tests use :class:`TestingConfig` and provide safe placeholder
        values for every required variable, so the base
        :meth:`Config.validate` check is intentionally bypassed.  This
        also allows individual tests to clear placeholder values
        without triggering startup errors.
        """
        return None


# ----------------------------------------------------------------------
# Factory: select a config class by name
# ----------------------------------------------------------------------
# Mapping from environment names to config classes.  The names match
# the GitHub Actions environment names (``qa``, ``stage`` -> staging,
# ``prod`` -> production) plus the standard Python aliases.
_CONFIG_MAP: dict = {
    "development": DevelopmentConfig,
    "dev": DevelopmentConfig,
    "staging": StagingConfig,
    "stage": StagingConfig,
    "qa": QAConfig,
    "production": ProductionConfig,
    "prod": ProductionConfig,
    "testing": TestingConfig,
    "test": TestingConfig,
}


def get_config(name: Optional[str] = None) -> Type[Config]:
    """Return the configuration class for the requested environment.

    Args:
        name: Environment name -- one of ``"development"``,
            ``"staging"``, ``"qa"``, ``"production"``, ``"testing"``,
            or any of their short aliases (``"dev"``, ``"stage"``,
            ``"prod"``, ``"test"``).  Lookup is case-insensitive and
            tolerant of surrounding whitespace.  If ``None``, the
            value of the ``FLASK_ENV`` environment variable is used;
            if that is also unset, ``ProductionConfig`` is returned
            (production is the safe default for Cloud Run deployments).

    Returns:
        The matching configuration *class* (NOT an instance).  Use
        ``app.config.from_object(get_config(...))`` to load it.

    Raises:
        ValueError: If ``name`` is not a recognized environment.

    Examples:
        >>> get_config("production") is ProductionConfig
        True
        >>> get_config("test") is TestingConfig
        True
        >>> get_config("invalid")
        Traceback (most recent call last):
            ...
        ValueError: Unknown FLASK_ENV value 'invalid'; expected one of [...]
    """
    if name is None:
        name = os.environ.get("FLASK_ENV", "production")

    name = name.strip().lower()
    if name not in _CONFIG_MAP:
        raise ValueError(
            f"Unknown FLASK_ENV value {name!r}; expected one of "
            f"{sorted(_CONFIG_MAP.keys())}."
        )
    return _CONFIG_MAP[name]


__all__ = [
    "Config",
    "DevelopmentConfig",
    "StagingConfig",
    "QAConfig",
    "ProductionConfig",
    "TestingConfig",
    "get_config",
]
