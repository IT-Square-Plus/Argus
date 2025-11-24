"""
Brave Search API service client
"""

import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class BraveService:
    """
    Service client for Brave Search API.

    Handles both basic search (Data for Search) and advanced search (Data for AI with extra_snippets).
    """

    BASE_URL = "https://api.search.brave.com/res/v1"

    def __init__(self, api_key: str):
        """
        Initialize Brave service client.

        Args:
            api_key: Brave API key for authentication
        """
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": api_key
            },
            timeout=30.0
        )

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

    async def search_web(
        self,
        query: str,
        count: int = 10,
        country: str = "US",
        search_lang: str = "en",
        ui_lang: str = "en-US",
        offset: int = 0,
        safesearch: str = "off",
        freshness: Optional[str] = None,
        text_decorations: bool = True,
        spellcheck: bool = True,
        result_filter: Optional[str] = None,
        goggles: Optional[list[str]] = None,
        units: Optional[str] = None,
        summary: Optional[bool] = None,
        operators: bool = True
    ) -> dict:
        """
        Perform web search using Brave Web Search API.

        Args:
            query: Search query string (max 400 chars, 50 words)
            count: Number of results to return (default: 10, max: 20)
            country: Search query country code (default: "US"). 2-character country codes
            search_lang: Search language code (default: "en"). 2 or more character language code
            ui_lang: UI language preference (default: "en-US"). Format: <language_code>-<country_code>
            offset: Pagination offset (default: 0, max: 9). Zero-based offset for pagination
            safesearch: Content filtering: "off", "moderate", "strict" (default: "off")
            freshness: Time filter: "pd" (past day), "pw" (past week), "pm" (past month), "py" (past year), or date range
            text_decorations: Include decoration markers (default: True)
            spellcheck: Enable spell checking (default: True)
            result_filter: Comma-delimited result types to include (e.g., "discussions,faq,news")
            goggles: Custom re-ranking definitions (list of Goggles IDs)
            units: Measurement units: "metric" or "imperial"
            summary: Enable summary key generation for AI
            operators: Apply search operators (default: True)

        Returns:
            dict: WebSearchApiResponse from Brave API containing web results, videos, news, discussions, FAQ, infobox, locations, etc.

        Raises:
            httpx.HTTPError: If the API request fails
        """
        logger.info(f"🔍 Web search: query='{query}', count={count}, country={country}, result_filter={result_filter}")

        params = {
            "q": query,
            "count": count,
            "country": country,
            "search_lang": search_lang,
            "ui_lang": ui_lang,
            "offset": offset,
            "safesearch": safesearch,
            "text_decorations": text_decorations,
            "spellcheck": spellcheck,
            "operators": operators
        }

        # Add optional parameters
        if freshness:
            params["freshness"] = freshness
        if result_filter:
            params["result_filter"] = result_filter
        if goggles:
            params["goggles"] = goggles
        if units:
            params["units"] = units
        if summary is not None:
            params["summary"] = summary

        try:
            response = await self.client.get("/web/search", params=params)
            response.raise_for_status()
            data = response.json()

            logger.info(
                f"✅ Web search success: "
                f"got {len(data.get('web', {}).get('results', []))} web results"
            )

            return data

        except httpx.HTTPError as e:
            logger.error(f"❌ Web search failed: {e}")
            raise

    async def search_web_extra_snippets_for_ai(
        self,
        query: str,
        count: int = 10,
        country: str = "US",
        search_lang: str = "en",
        ui_lang: str = "en-US",
        offset: int = 0,
        safesearch: str = "off",
        freshness: Optional[str] = None,
        text_decorations: bool = True,
        spellcheck: bool = True,
        result_filter: Optional[str] = None,
        goggles: Optional[list[str]] = None,
        units: Optional[str] = None,
        summary: Optional[bool] = None,
        operators: bool = True,
        use_extra_snippets: bool = True
    ) -> dict:
        """
        Perform web search with extra_snippets for AI/LLM (Data for AI key).

        This method provides up to 5 additional excerpts per result, ideal for AI/LLM context.
        Falls back to regular search without extra_snippets if AI key fails.

        Args:
            query: Search query string (max 400 chars, 50 words)
            count: Number of results to return (default: 10, max: 20)
            country: Search query country code (default: "US"). 2-character country codes
            search_lang: Search language code (default: "en"). 2 or more character language code
            ui_lang: UI language preference (default: "en-US"). Format: <language_code>-<country_code>
            offset: Pagination offset (default: 0, max: 9). Zero-based offset for pagination
            safesearch: Content filtering: "off", "moderate", "strict" (default: "off")
            freshness: Time filter: "pd" (past day), "pw" (past week), "pm" (past month), "py" (past year), or date range
            text_decorations: Include decoration markers (default: True)
            spellcheck: Enable spell checking (default: True)
            result_filter: Comma-delimited result types to include (e.g., "discussions,faq,news")
            goggles: Custom re-ranking definitions (list of Goggles IDs)
            units: Measurement units: "metric" or "imperial"
            summary: Enable summary key generation for AI
            operators: Apply search operators (default: True)
            use_extra_snippets: Whether to enable extra_snippets (requires Data for AI key)

        Returns:
            dict: WebSearchApiResponse from Brave API with extra_snippets field containing 4-5 additional alternative excerpts per result

        Raises:
            httpx.HTTPError: If the API request fails
        """
        extra_info = " with extra_snippets" if use_extra_snippets else " (fallback mode)"
        logger.info(f"🔍✨ Web search for AI{extra_info}: query='{query}', count={count}, country={country}")

        params = {
            "q": query,
            "count": count,
            "country": country,
            "search_lang": search_lang,
            "ui_lang": ui_lang,
            "offset": offset,
            "safesearch": safesearch,
            "text_decorations": text_decorations,
            "spellcheck": spellcheck,
            "operators": operators
        }

        # Add optional parameters
        if freshness:
            params["freshness"] = freshness
        if result_filter:
            params["result_filter"] = result_filter
        if goggles:
            params["goggles"] = goggles
        if units:
            params["units"] = units
        if summary is not None:
            params["summary"] = summary

        # Add extra_snippets if available
        if use_extra_snippets:
            params["extra_snippets"] = True

        try:
            response = await self.client.get("/web/search", params=params)
            response.raise_for_status()
            data = response.json()

            web_results = data.get('web', {}).get('results', [])
            logger.info(
                f"✅ Web search for AI success: got {len(web_results)} web results"
            )

            # Log snippet length for first result (debugging)
            if web_results and use_extra_snippets:
                first_snippet = web_results[0].get('extra_snippets', [])
                if first_snippet:
                    logger.info(f"ℹ️  Extra snippets enabled: {len(first_snippet)} snippets in first result")
                else:
                    logger.warning("⚠️  Extra snippets requested but not present in response")

            return data

        except httpx.HTTPError as e:
            logger.error(f"❌ Web search for AI failed: {e}")
            raise

    async def search_images(
        self,
        query: str,
        count: int = 50,
        country: str = "US",
        search_lang: str = "en",
        safesearch: str = "strict",
        spellcheck: bool = True
    ) -> dict:
        """
        Perform image search using Brave Image Search API.

        Args:
            query: Search query string (max 400 chars, 50 words)
            count: Number of results to return (default: 50, max: 200)
            country: Search query country code (default: "US"). 2-character country codes
            search_lang: Search language code (default: "en"). 2 or more character language code
            safesearch: Content filtering: "off", "strict" (default: "strict")
            spellcheck: Enable spell checking (default: True)

        Returns:
            dict: ImageSearchApiResponse containing:
                - type: Always "images"
                - query: Query information (original, altered, spellcheck_off, show_strict_warning)
                - results: List of ImageResult objects with title, url, source, thumbnail, properties
                - extra: Additional info (might_be_offensive flag)

        Raises:
            httpx.HTTPError: If the API request fails
        """
        logger.info(f"🖼️  Image search: query='{query}', count={count}, country={country}")

        params = {
            "q": query,
            "count": count,
            "country": country,
            "search_lang": search_lang,
            "safesearch": safesearch,
            "spellcheck": spellcheck
        }

        try:
            response = await self.client.get("/images/search", params=params)
            response.raise_for_status()
            data = response.json()

            result_count = len(data.get("results", []))
            logger.info(f"✅ Image search successful: {result_count} images returned")

            return data

        except httpx.HTTPError as e:
            logger.error(f"❌ Image search failed: {e}")
            raise

    async def search_videos(
        self,
        query: str,
        count: int = 20,
        country: str = "US",
        search_lang: str = "en",
        ui_lang: str = "en-US",
        offset: int = 0,
        safesearch: str = "moderate",
        freshness: str = None,
        spellcheck: bool = True,
        operators: bool = True
    ) -> dict:
        """
        Perform video search using Brave Video Search API.

        Args:
            query: Search query string (max 400 chars, 50 words)
            count: Number of results to return (default: 20, max: 50)
            country: Search query country code (default: "US"). 2-character country code
            search_lang: Search language code (default: "en"). 2 or more character language code
            ui_lang: UI language preference (default: "en-US"). Format: <language_code>-<country_code>
            offset: Pagination offset (default: 0, max: 9)
            safesearch: Content filtering: "off", "moderate" (default), "strict"
            freshness: Time filter: "pd" (past day), "pw" (past week), "pm" (past month), "py" (past year), or date range
            spellcheck: Enable spell checking (default: True)
            operators: Apply search operators (default: True)

        Returns:
            dict: VideoSearchApiResponse containing:
                - type: Always "videos"
                - query: Query information (original, altered, spellcheck_off, show_strict_warning)
                - results: List of VideoResult objects with title, url, description, duration, views, etc.
                - extra: Additional info (might_be_offensive flag)

        Raises:
            httpx.HTTPError: If the API request fails
        """
        logger.info(f"🎬 Video search: query='{query}', count={count}, country={country}")

        params = {
            "q": query,
            "count": count,
            "country": country,
            "search_lang": search_lang,
            "ui_lang": ui_lang,
            "offset": offset,
            "safesearch": safesearch,
            "spellcheck": spellcheck,
            "operators": operators
        }

        # Add optional freshness filter
        if freshness:
            params["freshness"] = freshness

        try:
            response = await self.client.get("/videos/search", params=params)
            response.raise_for_status()
            data = response.json()

            result_count = len(data.get("results", []))
            logger.info(f"✅ Video search successful: {result_count} videos returned")

            return data

        except httpx.HTTPError as e:
            logger.error(f"❌ Video search failed: {e}")
            raise

    async def search_news(
        self,
        query: str,
        count: int = 20,
        country: str = "US",
        search_lang: str = "en",
        ui_lang: str = "en-US",
        offset: int = 0,
        safesearch: str = "moderate",
        freshness: str = None,
        spellcheck: bool = True,
        extra_snippets: bool = False,
        goggles: list = None,
        operators: bool = True
    ) -> dict:
        """
        Perform news search using Brave News Search API.

        Args:
            query: Search query (max 400 chars, 50 words)
            count: Number of results (default 20, max 50)
            country: Country code (default "US")
            search_lang: Language code (default "en")
            ui_lang: UI language (default "en-US")
            offset: Pagination offset (default 0, max 9)
            safesearch: Content filter - "off", "moderate", "strict" (default "moderate")
            freshness: Time filter - "pd", "pw", "pm", "py" or date range
            spellcheck: Enable spellcheck (default True)
            extra_snippets: Get up to 5 additional excerpts (Data for AI plan only)
            goggles: Custom re-ranking definitions
            operators: Apply search operators (default True)

        Returns:
            dict: NewsSearchApiResponse with type="news", query info, and list of NewsResult objects
        """
        logger.info(f"📰 News search: query='{query}', count={count}, country={country}")

        params = {
            "q": query,
            "count": count,
            "country": country,
            "search_lang": search_lang,
            "ui_lang": ui_lang,
            "offset": offset,
            "safesearch": safesearch,
            "spellcheck": spellcheck,
            "operators": operators
        }

        if freshness:
            params["freshness"] = freshness

        if extra_snippets:
            params["extra_snippets"] = extra_snippets

        if goggles:
            params["goggles"] = goggles

        try:
            response = await self.client.get("/news/search", params=params)
            response.raise_for_status()
            data = response.json()

            result_count = len(data.get("results", []))
            logger.info(f"✅ News search successful: {result_count} news articles returned")

            return data

        except httpx.HTTPError as e:
            logger.error(f"❌ News search failed: {e}")
            raise

    async def suggest(
        self,
        query: str,
        count: int = 5,
        country: str = "US",
        lang: str = "en",
        rich: bool = False
    ) -> dict:
        """
        Get search suggestions using Brave Suggest API.

        Args:
            query: Suggest search query (max 400 chars, 50 words)
            count: Number of suggestions (default 5, min 1, max 20)
            country: Country code (default "US")
            lang: Language code (default "en")
            rich: Enhance suggestions with rich results (requires paid subscription)

        Returns:
            dict: SuggestSearchApiResponse with type="suggest", query info, and list of SuggestResult objects
        """
        logger.info(f"💡 Suggest search: query='{query}', count={count}, country={country}")

        params = {
            "q": query,
            "count": count,
            "country": country,
            "lang": lang
        }

        # Only include rich parameter if True (requires paid subscription)
        if rich:
            params["rich"] = "true"

        try:
            response = await self.client.get("/suggest/search", params=params)
            response.raise_for_status()
            data = response.json()

            result_count = len(data.get("results", []))
            logger.info(f"✅ Suggest search successful: {result_count} suggestions returned")

            return data

        except httpx.HTTPError as e:
            logger.error(f"❌ Suggest search failed: {e}")
            raise

    async def spellcheck(
        self,
        query: str,
        country: str = "US",
        lang: str = "en"
    ) -> dict:
        """
        Spellcheck a query using Brave Spellcheck API.

        Args:
            query: Query to spellcheck (max 400 chars, 50 words)
            country: Country code (default "US")
            lang: Language code (default "en")

        Returns:
            dict: SpellCheckSearchApiResponse with type="spellcheck", query info, and list of SpellCheckResult objects
        """
        logger.info(f"✍️  Spellcheck search: query='{query}', country={country}, lang={lang}")

        params = {
            "q": query,
            "country": country,
            "lang": lang
        }

        try:
            response = await self.client.get("/spellcheck/search", params=params)
            response.raise_for_status()
            data = response.json()

            result_count = len(data.get("results", []))
            logger.info(f"✅ Spellcheck successful: {result_count} corrections returned")

            return data

        except httpx.HTTPError as e:
            logger.error(f"❌ Spellcheck failed: {e}")
            raise
