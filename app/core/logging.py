import logging
import sys


def setup_logging(debug: bool = False) -> None:
    """Configure structured logging for the application."""
    level = logging.DEBUG if debug else logging.INFO
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S"))

    root = logging.getLogger()
    root.setLevel(level)
    # Avoid duplicate handlers on reload
    root.handlers = [handler]

    # Silence noisy third-party loggers
    for name in ("httpcore", "httpx", "uvicorn.access"):
        logging.getLogger(name).setLevel(logging.WARNING)
