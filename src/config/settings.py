"""
Configuration settings for Argus MCP Server
"""

from pydantic import Field
from pydantic_settings import BaseSettings
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Application settings with environment variable support.

    API keys are now provided via .mcp.json headers (X-Brave-API-Key-Search, X-Brave-API-Key-AI).
    This configuration manages MCP server settings and free plan usage limits.
    """

    # MCP Server Configuration
    mcp_server_host: str = Field(
        default="0.0.0.0",
        description="MCP server host"
    )

    mcp_server_port: int = Field(
        default=8081,
        description="MCP server port"
    )

    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )

    # Brave Search API - Free Plan Limits (monthly)
    data_for_search_free_plan_max_usage: int = Field(
        default=2000,
        description="Data for Search free plan monthly limit (1 req/sec, 2000 req/month)"
    )

    data_for_ai_free_plan_max_usage: int = Field(
        default=2000,
        description="Data for AI free plan monthly limit (1 req/sec, 2000 req/month)"
    )

    data_for_spellcheck_free_plan_max_usage: int = Field(
        default=5000,
        description="Spellcheck free plan monthly limit (5 req/sec, 5000 req/month)"
    )

    data_for_autosuggest_free_plan_max_usage: int = Field(
        default=5000,
        description="Autosuggest free plan monthly limit (5 req/sec, 5000 req/month)"
    )

    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Get settings singleton instance.
    Uses lru_cache to ensure only one instance is created.
    """
    return Settings()
