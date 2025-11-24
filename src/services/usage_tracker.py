"""
Usage tracking for Brave Search API free plan limits.

This module tracks API usage across container restarts by:
1. Checking current usage via API call on startup (costs 1 request)
2. Storing usage in memory
3. Incrementing after each request
4. Re-checking on container restart
"""

import httpx
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class UsageTracker:
    """
    Tracks API usage for Brave Search API plans.

    Maintains in-memory counters that are:
    - Initialized on container startup via API call
    - Incremented after each tool use
    - Reset on container restart (with fresh API check)
    """

    def __init__(self):
        self.usage: Dict[str, int] = {
            "data_for_search": 0,
            "data_for_ai": 0,
            "spellcheck": 0,
            "autosuggest": 0
        }
        self.limits: Dict[str, int] = {
            "data_for_search": 2000,
            "data_for_ai": 2000,
            "spellcheck": 5000,
            "autosuggest": 5000
        }
        # Flag to track if initial usage check failed
        self.initial_check_failed: bool = False
        # Flag to track if we already warned the user
        self.user_warned: bool = False

    async def check_initial_usage(
        self,
        api_key_search: str,
        api_key_ai: Optional[str] = None
    ) -> bool:
        """
        Check current API usage on startup.

        Makes API calls to check x-ratelimit-remaining headers.
        This costs 1 request per API key checked.

        Args:
            api_key_search: X-Brave-API-Key-Search from .mcp.json
            api_key_ai: X-Brave-API-Key-AI from .mcp.json (optional)

        Returns:
            bool: True if check succeeded, False if API key is invalid/expired
        """
        logger.info("📊 Checking initial API usage...")

        # Check Data for Search usage
        success = await self._check_plan_usage("data_for_search", api_key_search)

        if not success:
            self.initial_check_failed = True
            return False

        # Check Data for AI usage if different key provided
        if api_key_ai and api_key_ai != api_key_search:
            await self._check_plan_usage("data_for_ai", api_key_ai)
        else:
            # Same key = same usage
            self.usage["data_for_ai"] = self.usage["data_for_search"]
            logger.info("ℹ️  Data for AI uses same key as Data for Search")

        return True

    async def _check_plan_usage(self, plan_name: str, api_key: str) -> bool:
        """
        Check usage for a specific plan by making a minimal API call.

        Args:
            plan_name: Plan identifier ("data_for_search", "data_for_ai")
            api_key: API key for the plan

        Returns:
            bool: True if check succeeded, False if API key is invalid/expired
        """
        base_url = "https://api.search.brave.com/res/v1"

        async with httpx.AsyncClient(base_url=base_url) as client:
            try:
                # Minimal search query to check headers
                response = await client.get(
                    "/web/search",
                    params={"q": "test", "count": 1},
                    headers={
                        "Accept": "application/json",
                        "X-Subscription-Token": api_key
                    },
                    timeout=10.0
                )
                response.raise_for_status()

                # Parse x-ratelimit-remaining header
                # Format: "0, 1987" (per-second, per-month)
                remaining_header = response.headers.get("x-ratelimit-remaining", "0, 0")
                limit_header = response.headers.get("x-ratelimit-limit", "1, 2000")

                # Extract monthly values (second number)
                remaining_monthly = int(remaining_header.split(", ")[1])
                limit_monthly = int(limit_header.split(", ")[1])

                # Calculate used
                used = limit_monthly - remaining_monthly

                self.usage[plan_name] = used
                self.limits[plan_name] = limit_monthly

                percentage = (used / limit_monthly * 100) if limit_monthly > 0 else 0

                logger.info(
                    f"✅ {plan_name}: {used}/{limit_monthly} requests used ({percentage:.1f}%)"
                )
                return True

            except Exception as e:
                logger.error(f"❌ Failed to check {plan_name} usage: {e}")
                # Keep default values (0 used)
                return False

    def get_user_warning_if_needed(self) -> Optional[str]:
        """
        Get warning message for user if initial check failed and user hasn't been warned yet.

        Returns:
            Warning message string or None if no warning needed
        """
        if self.initial_check_failed and not self.user_warned:
            self.user_warned = True
            return (
                "⚠️ **API Usage Tracking Warning** ⚠️\n\n"
                "Argus was unable to check your initial API usage during startup because "
                "the `X_BRAVE_API_KEY_SEARCH` variable in `.env` file contains an invalid, expired, or missing API key.\n\n"
                "**Impact:**\n"
                "- Your MCP tools are working correctly (using keys from `.mcp.json`)\n"
                "- However, API usage statistics shown at startup are **incorrect** (showing 0/2000)\n"
                "- Usage tracking will work during runtime, but won't show accurate initial values\n\n"
                "**Solution:**\n"
                "Update the `X_BRAVE_API_KEY_SEARCH` variable in your `.env` file with a valid Brave Search API key, "
                "then rebuild the Docker container to see correct usage statistics at startup."
            )
        return None

    def increment_usage(self, plan_name: str, count: int = 1) -> None:
        """
        Increment usage counter after API request.

        Args:
            plan_name: Plan identifier ("data_for_search", "data_for_ai", etc.)
            count: Number of requests to add (default: 1)
        """
        if plan_name in self.usage:
            self.usage[plan_name] += count
            logger.debug(f"📈 {plan_name} usage: {self.usage[plan_name]}/{self.limits[plan_name]}")

    def get_usage_summary(self) -> Dict[str, Dict[str, int]]:
        """
        Get current usage summary for all plans.

        Returns:
            Dict with plan usage info: {plan_name: {"used": X, "limit": Y, "remaining": Z}}
        """
        summary = {}
        for plan_name in self.usage.keys():
            used = self.usage[plan_name]
            limit = self.limits[plan_name]
            remaining = limit - used
            percentage = (used / limit * 100) if limit > 0 else 0

            summary[plan_name] = {
                "used": used,
                "limit": limit,
                "remaining": remaining,
                "percentage": round(percentage, 1)
            }

        return summary

    def format_usage_for_startup(self) -> str:
        """
        Format usage information for startup logs.

        Returns:
            Formatted string with usage bars and percentages
        """
        lines = ["📊 API Usage (Free Plans):"]
        lines.append("=" * 80)

        summary = self.get_usage_summary()

        for plan_name, info in summary.items():
            # Create progress bar
            bar_width = 40
            filled = int(bar_width * info["percentage"] / 100)
            bar = "█" * filled + "░" * (bar_width - filled)

            # Format plan name
            display_name = plan_name.replace("_", " ").title()

            lines.append(
                f"   {display_name:20s} [{bar}] "
                f"{info['used']:4d}/{info['limit']:4d} ({info['percentage']:5.1f}%) "
                f"- {info['remaining']:4d} remaining"
            )

        lines.append("=" * 80)

        return "\n".join(lines)

    def format_single_plan_usage(self, plan_name: str) -> str:
        """
        Format usage information for a single plan (for per-request logging).

        Args:
            plan_name: Plan identifier ("data_for_search", "data_for_ai", etc.)

        Returns:
            Formatted string with usage bar and percentage for the plan
        """
        if plan_name not in self.usage:
            return f"Unknown plan: {plan_name}"

        used = self.usage[plan_name]
        limit = self.limits[plan_name]
        remaining = limit - used
        percentage = (used / limit * 100) if limit > 0 else 0

        # Create progress bar
        bar_width = 40
        filled = int(bar_width * percentage / 100)
        bar = "█" * filled + "░" * (bar_width - filled)

        # Format plan name
        display_name = plan_name.replace("_", " ").title()

        return (
            f"Current {display_name} usage: [{bar}] "
            f"{used:4d}/{limit:4d} ({percentage:5.1f}%) - {remaining:4d} remaining"
        )

    def set_usage_for_testing(self, plan_name: str, used: int) -> None:
        """
        Temporarily set usage for testing purposes.

        Args:
            plan_name: Plan identifier ("data_for_search", "data_for_ai", etc.)
            used: Number of used requests to set
        """
        if plan_name in self.usage:
            self.usage[plan_name] = used
            logger.info(f"🧪 Testing: Set {plan_name} usage to {used}/{self.limits[plan_name]}")

    def should_use_ai_key(self) -> tuple[bool, str]:
        """
        AI-Saving Policy: Determine whether to use AI key or Search key for tools
        that can work with both (search_images, search_videos, search_news).

        Policy Logic:
        1. If AI has > 50% remaining → Always use Search (save AI)
        2. If Search has ≥ 10% remaining → Use Search (save AI)
        3. If Search has < 10% remaining → Use AI (Search almost depleted)

        Returns:
            tuple[bool, str]: (should_use_ai, reason)
                - should_use_ai: True if should use AI key, False if should use Search key
                - reason: Human-readable explanation of the decision
        """
        search_used = self.usage.get("data_for_search", 0)
        search_limit = self.limits.get("data_for_search", 2000)
        search_remaining = search_limit - search_used
        search_remaining_pct = (search_remaining / search_limit * 100) if search_limit > 0 else 0

        ai_used = self.usage.get("data_for_ai", 0)
        ai_limit = self.limits.get("data_for_ai", 2000)
        ai_remaining = ai_limit - ai_used
        ai_remaining_pct = (ai_remaining / ai_limit * 100) if ai_limit > 0 else 0

        # Rule 1: If AI has > 50% remaining, always save it
        if ai_remaining_pct > 50:
            return (
                False,
                f"AI has {ai_remaining_pct:.1f}% remaining (>50%) → Using Search to save AI"
            )

        # Rule 2: If Search has ≥ 10% remaining, still use it (save AI)
        if search_remaining_pct >= 10:
            return (
                False,
                f"Search has {search_remaining_pct:.1f}% remaining (≥10%) → Using Search (save AI)"
            )

        # Rule 3: Search has < 10% remaining, switch to AI
        return (
            True,
            f"Search has {search_remaining_pct:.1f}% remaining (<10%) → Switching to AI"
        )


# Global singleton instance
_tracker: Optional[UsageTracker] = None


def get_tracker() -> UsageTracker:
    """
    Get global UsageTracker singleton.

    Returns:
        UsageTracker instance
    """
    global _tracker
    if _tracker is None:
        _tracker = UsageTracker()
    return _tracker
