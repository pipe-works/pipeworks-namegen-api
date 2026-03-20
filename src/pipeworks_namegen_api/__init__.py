"""Pipeworks Namegen API."""

from .version import __version__

__all__ = ["__version__", "healthcheck"]


def healthcheck() -> str:
    """Return a stable package healthcheck string."""
    return "ok"
