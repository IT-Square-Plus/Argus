"""
Response formatting utilities for Argus MCP Server

Placeholder module for future response formatting functionality.
Currently, responses are returned directly from the Brave API.
"""

from typing import Any, Dict


def format_search_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format Brave Search API response.

    Currently a pass-through function. Can be extended to:
    - Extract specific fields
    - Transform data structure
    - Add additional metadata
    - Filter or clean results

    Args:
        data: Raw response from Brave API

    Returns:
        Formatted response dictionary
    """
    return data


def format_error_response(error: Exception) -> Dict[str, Any]:
    """
    Format error response.

    Args:
        error: Exception that occurred

    Returns:
        Error response dictionary
    """
    return {
        "success": False,
        "error": str(error),
        "error_type": type(error).__name__
    }
