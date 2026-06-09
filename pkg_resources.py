"""Minimal compatibility shim for older packages that import pkg_resources.

This project runs in environments where setuptools' legacy pkg_resources module
may not be available, but some pinned third-party packages still import it at
startup. We provide only the small surface area currently needed by those
imports.
"""

from importlib import metadata


class DistributionNotFound(metadata.PackageNotFoundError):
    """Raised when a requested distribution is not installed."""


def get_distribution(dist):
    """Return distribution metadata for an installed package."""

    return metadata.distribution(dist)
