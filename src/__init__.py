"""Argus - Brave Search MCP Server"""

from importlib.metadata import PackageNotFoundError, version

try:
    # Read version from pyproject.toml (single source of truth)
    __version__ = version("argus")
except PackageNotFoundError:
    # Fallback during development before package is installed
    __version__ = "dev"
