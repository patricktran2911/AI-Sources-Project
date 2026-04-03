"""Application logging configuration.

Call ``setup_logging(debug=True/False)`` once during application startup.
All noisy third-party loggers are silenced to INFO/WARNING so that only
application-level messages appear at DEBUG level during development.
"""

import logging
import sys

# Third-party loggers that produce too much output even at INFO level.
_NOISY_LOGGERS = (
    "httpcore",
    "httpx",
    "uvicorn.access",
    "openai._base_client",
    "anthropic._base_client",
)


def setup_logging(debug: bool = False) -> None:
    """Configure structured logging for the application.

    Args:
        debug: When True, sets the root logger to DEBUG.  At INFO level
               (production) all third-party noise is suppressed.
    """
    level = logging.DEBUG if debug else logging.INFO
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S"))

    root = logging.getLogger()
    root.setLevel(level)
    # Replace handlers to avoid duplicates on hot-reload
    root.handlers = [handler]

    # Keep noisy third-party loggers quiet regardless of debug flag
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
