"""Logging configuration helpers for ngpb4py."""

import logging

_LOGGER = logging.getLogger("ngpb4py")
_VERBOSITY_LEVELS = {0: logging.WARNING, 1: logging.INFO, 2: logging.DEBUG, 3: logging.DEBUG}


def _configure_logging(verbosity: int) -> None:
    """Configure package logging for the requested verbosity level."""
    level = _VERBOSITY_LEVELS.get(verbosity, logging.DEBUG)
    _LOGGER.setLevel(level)

    if not _LOGGER.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        _LOGGER.addHandler(handler)
        _LOGGER.propagate = False

    for handler in _LOGGER.handlers:
        handler.setLevel(level)
