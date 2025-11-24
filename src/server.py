"""
Argus MCP Server - Brave Search API with HTTP Streamable transport
"""

from mcp.server.fastmcp import FastMCP, Context
from starlette.requests import Request
from starlette.responses import JSONResponse
from src.config.settings import get_settings
from src.services.brave_service import BraveService
from src.services.usage_tracker import get_tracker
from src import __version__
from typing import Optional, Annotated
from contextvars import ContextVar
import logging

# Context variables for request-scoped API keys
request_api_key_search: ContextVar[Optional[str]] = ContextVar('request_api_key_search', default=None)
request_api_key_ai: ContextVar[Optional[str]] = ContextVar('request_api_key_ai', default=None)
request_api_key_autosuggest: ContextVar[Optional[str]] = ContextVar('request_api_key_autosuggest', default=None)
request_api_key_spellcheck: ContextVar[Optional[str]] = ContextVar('request_api_key_spellcheck', default=None)

# Initialize settings
settings = get_settings()
logging.basicConfig(
    level=settings.log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Suppress known ClosedResourceError in stateless HTTP mode
# This is a normal cleanup error that occurs after successful request completion
logging.getLogger('mcp.server.streamable_http').setLevel(logging.CRITICAL)

# Initialize FastMCP with stateless HTTP and JSON response (no SSE)
mcp = FastMCP("Argus", stateless_http=True, json_response=True)


# ============================================================================
# Custom HTTP Routes
# ============================================================================

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """
    Health check endpoint (liveness probe).
    Returns basic service status.
    """
    return JSONResponse({
        "status": "alive",
        "service": "Argus",
        "version": __version__
    })


@mcp.custom_route("/ready", methods=["GET"])
async def readiness_check(request: Request) -> JSONResponse:
    """
    Readiness check endpoint (readiness probe).
    Returns service status with capabilities and usage information.
    """
    tracker = get_tracker()
    usage_summary = tracker.get_usage_summary()

    return JSONResponse({
        "status": "ready",
        "service": "Argus",
        "version": __version__,
        "capabilities": {
            "search_web": True,
            "search_web_extra_snippets_for_ai": True,
            "search_images": True,
            "search_videos": True,
            "search_news": True,
            "suggest": True,
            "spellcheck": True
        },
        "usage": usage_summary
    })


@mcp.custom_route("/test/set-usage", methods=["POST"])
async def test_set_usage(request: Request) -> JSONResponse:
    """
    Testing endpoint to temporarily set usage values for policy testing.

    Body: {"data_for_search": <used>, "data_for_ai": <used>}
    """
    try:
        body = await request.json()
        tracker = get_tracker()

        if "data_for_search" in body:
            tracker.set_usage_for_testing("data_for_search", body["data_for_search"])

        if "data_for_ai" in body:
            tracker.set_usage_for_testing("data_for_ai", body["data_for_ai"])

        return JSONResponse({
            "status": "success",
            "usage": tracker.get_usage_summary()
        })
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=400)


# ============================================================================
# MCP Tools
# ============================================================================

@mcp.tool()
async def search_web(
    query: str,
    count: int = 10,
    country: str = "US",
    search_lang: str = "en",
    ui_lang: str = "en-US",
    offset: int = 0,
    safesearch: str = "off",
    freshness: str = "",
    text_decorations: bool = True,
    spellcheck: bool = True,
    result_filter: str = "web",
    goggles: list[str] = [],
    units: str = "",
    summary: str = "",
    operators: bool = True
) -> dict:
    """
    Web search using Brave Search API (Data for Search).

    Performs comprehensive web searches with rich result types and advanced filtering options.

    ⚠️ TOKEN COST OPTIMIZATION:
    - Default (result_filter="web"): ~3,000 tokens (web results only) ✅ RECOMMENDED
    - All clusters (result_filter=""): ~10,000 tokens (web + news + videos + more)

    💡 TIP: For specialized searches, consider using dedicated tools:
       - search_news() for news articles (optimized for news)
       - search_videos() for video content (optimized for videos)
       - search_images() for image search (optimized for images)

    Args:
        query: Search query string (max 400 chars, 50 words)
        count: Number of results to return (default: 10, max: 20)
        country: Search query country code (default: "US"). 2-character country code where the results come from
        search_lang: Search language code (default: "en"). 2 or more character language code for search results
        ui_lang: UI language preference (default: "en-US"). Format: <language_code>-<country_code>
        offset: Pagination offset (default: 0, max: 9). Zero-based offset indicating number of search results per page to skip
        safesearch: Content filtering: "off", "moderate", "strict" (default: "off"). Filters adult content
        freshness: Time filter: "pd" (past day), "pw" (past week), "pm" (past month), "py" (past year), or date range. Filters search results by when they were discovered
        text_decorations: Include decoration markers (default: True). Whether display strings should include decoration markers
        spellcheck: Enable spell checking (default: True). Whether to spellcheck the provided query
        result_filter: Filter to specific result types (controls token cost):
                      - "web" = ONLY web results (~3k tokens) ⭐ DEFAULT - best for general searches
                      - "" (empty) = ALL clusters: web, news, videos, discussions, faq, etc. (~10k tokens)
                      - "news" = ONLY news articles (~4k tokens) - consider using search_news() instead
                      - "videos" = ONLY videos (~3k tokens) - consider using search_videos() instead
                      - "discussions" = ONLY forum posts and discussions (~3k tokens)
                      - "faq" = ONLY Q&A and FAQ results (~2k tokens)
                      - "infobox" = ONLY knowledge graph entities (~1k tokens)
                      - "locations" = ONLY places of interest (~2k tokens)
                      - "web,news" = Combination: web + news (~7k tokens)
                      - "web,videos" = Combination: web + videos (~6k tokens)
                      Note: Comma-delimited combinations are supported (e.g., "web,news,discussions")
        goggles: Custom re-ranking definitions. List of Goggles IDs for custom re-ranking on top of Brave's search index
        units: Measurement units: "metric" or "imperial". Specifies preferred measurement units in results
        summary: Enable summary key generation for AI. Returns a summarizer key that can be used to fetch AI-generated summaries
        operators: Apply search operators (default: True). Whether to apply search operators in the query (see: https://search.brave.com/help/operators)

    Returns:
        dict: Search results with the following structure:
            - success (bool): Whether the request succeeded
            - data (dict): WebSearchApiResponse containing:
                - type: Always "search"
                - web: Collection of web search results (title, url, description, age, language, etc.)
                - query: Query information (original, altered, country, language, spellcheck info)
                - videos: Video results relevant to query (if result_filter includes "videos" or is empty)
                - news: News results relevant to query (if result_filter includes "news" or is empty)
                - discussions: Forum posts and discussions (if result_filter includes "discussions" or is empty)
                - faq: Frequently asked questions (if result_filter includes "faq" or is empty)
                - infobox: Knowledge graph entity information (if result_filter includes "infobox" or is empty)
                - locations: Places of interest for location-sensitive queries (if result_filter includes "locations" or is empty)
                - mixed: Preferred ranked order of results
    """
    logger.info(f"🛠️  Tool: search_web(query='{query}', count={count}, country={country})")

    # Check if user needs warning about invalid .env API key
    tracker = get_tracker()
    warning_message = tracker.get_user_warning_if_needed()

    # Get API key from context vars (headers) or fallback to settings (env)
    api_key = request_api_key_search.get() or settings.brave_api_key_data_for_search

    service = BraveService(api_key)

    try:
        # Convert empty strings to None for optional parameters
        result = await service.search_web(
            query=query,
            count=count,
            country=country,
            search_lang=search_lang,
            ui_lang=ui_lang,
            offset=offset,
            safesearch=safesearch,
            freshness=freshness or None,
            text_decorations=text_decorations,
            spellcheck=spellcheck,
            result_filter=result_filter or None,
            goggles=goggles if goggles else None,
            units=units or None,
            summary=True if summary == "true" else False if summary == "false" else None,
            operators=operators
        )

        # Track usage for data_for_search plan
        tracker.increment_usage("data_for_search", 1)
        logger.info("📊 Used 1 request from Data For Search quota")
        logger.info(f"📊 {tracker.format_single_plan_usage('data_for_search')}")

        response = {
            "success": True,
            "data": result
        }

        # Add warning message if needed (only first tool call)
        if warning_message:
            response["warning"] = warning_message

        return response

    except Exception as e:
        logger.error(f"❌ search_web failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }

    finally:
        await service.close()


@mcp.tool()
async def search_web_extra_snippets_for_ai(
    query: str,
    count: int = 10,
    country: str = "US",
    search_lang: str = "en",
    ui_lang: str = "en-US",
    offset: int = 0,
    safesearch: str = "off",
    freshness: str = "",
    text_decorations: bool = True,
    spellcheck: bool = True,
    result_filter: str = "",
    goggles: list[str] = [],
    units: str = "",
    summary: str = "",
    operators: bool = True
) -> dict:
    """
    Web search with extra_snippets for AI/LLM (Data for AI key required).

    Performs an enhanced web search with up to 5 additional excerpts per result,
    providing 6x more context ideal for AI/LLM applications. Falls back to regular
    search without extra_snippets if Data for AI key is not available or invalid.

    Args:
        query: Search query string (max 400 chars, 50 words)
        count: Number of results to return (default: 10, max: 20)
        country: Search query country code (default: "US"). 2-character country code where the results come from
        search_lang: Search language code (default: "en"). 2 or more character language code for search results
        ui_lang: UI language preference (default: "en-US"). Format: <language_code>-<country_code>
        offset: Pagination offset (default: 0, max: 9). Zero-based offset indicating number of search results per page to skip
        safesearch: Content filtering: "off", "moderate", "strict" (default: "off"). Filters adult content
        freshness: Time filter: "pd" (past day), "pw" (past week), "pm" (past month), "py" (past year), or date range. Filters search results by when they were discovered
        text_decorations: Include decoration markers (default: True). Whether display strings should include decoration markers
        spellcheck: Enable spell checking (default: True). Whether to spellcheck the provided query
        result_filter: Comma-delimited result types to include. Filter to specific types like "discussions", "faq", "infobox", "news", "query", "videos", "web", "locations"
        goggles: Custom re-ranking definitions. List of Goggles IDs for custom re-ranking on top of Brave's search index
        units: Measurement units: "metric" or "imperial". Specifies preferred measurement units in results
        summary: Enable summary key generation for AI. Returns a summarizer key that can be used to fetch AI-generated summaries
        operators: Apply search operators (default: True). Whether to apply search operators in the query (see: https://search.brave.com/help/operators)

    Returns:
        dict: Search results with extra context snippets and metadata. Structure includes:
            - success (bool): Whether the request succeeded
            - data (dict): WebSearchApiResponse containing the same fields as search_web, plus:
                - Each SearchResult includes extra_snippets field: list of 4-5 additional alternative excerpts from the page
                - NewsResult may include extra_snippets: list of extra snippets from news articles
            - metadata (dict): Information about the search execution:
                - has_extra_snippets (bool): True if extra snippets were included in results
                - fallback_used (bool): True if fallback to Search key was used
            - warning (str, optional): Present if fallback was used, explaining the limitation
    """
    logger.info(f"🛠️✨ Tool: search_web_extra_snippets_for_ai(query='{query}', count={count}, country={country})")

    # Get API keys from context vars (headers) or fallback to settings (env)
    api_key_search = request_api_key_search.get() or settings.brave_api_key_data_for_search
    api_key_ai = request_api_key_ai.get()

    # Try with AI key first if available
    if api_key_ai and api_key_ai != api_key_search:
        service = BraveService(api_key_ai)
        try:
            logger.info(f"🔑 Attempting search with AI key (extra_snippets enabled)")
            # Convert empty strings to None for optional parameters
            result = await service.search_web_extra_snippets_for_ai(
                query=query,
                count=count,
                country=country,
                search_lang=search_lang,
                ui_lang=ui_lang,
                offset=offset,
                safesearch=safesearch,
                freshness=freshness or None,
                text_decorations=text_decorations,
                spellcheck=spellcheck,
                result_filter=result_filter or None,
                goggles=goggles if goggles else None,
                units=units or None,
                summary=True if summary == "true" else False if summary == "false" else None,
                operators=operators,
                use_extra_snippets=True
            )

            # Track usage for data_for_ai plan
            tracker = get_tracker()
            tracker.increment_usage("data_for_ai", 1)
            logger.info("📊 Used 1 request from Data For AI quota")
            logger.info(f"📊 {tracker.format_single_plan_usage('data_for_ai')}")

            return {
                "success": True,
                "data": result,
                "metadata": {
                    "has_extra_snippets": True,
                    "fallback_used": False
                }
            }

        except Exception as e:
            logger.warning(f"⚠️  AI key failed ({e}), falling back to Search key")
            await service.close()
            # Fall through to fallback

    # Fallback to search key (no AI key, or AI key failed)
    service = BraveService(api_key_search)
    try:
        logger.info(f"🔑 Using Search key (extra_snippets disabled)")
        # Convert empty strings to None for optional parameters
        result = await service.search_web_extra_snippets_for_ai(
            query=query,
            count=count,
            country=country,
            search_lang=search_lang,
            ui_lang=ui_lang,
            offset=offset,
            safesearch=safesearch,
            freshness=freshness or None,
            text_decorations=text_decorations,
            spellcheck=spellcheck,
            result_filter=result_filter or None,
            goggles=goggles if goggles else None,
            units=units or None,
            summary=True if summary == "true" else False if summary == "false" else None,
            operators=operators,
            use_extra_snippets=False
        )

        # Track usage for data_for_search plan (fallback)
        tracker = get_tracker()
        tracker.increment_usage("data_for_search", 1)
        logger.info("📊 Used 1 request from Data For Search quota (fallback)")
        logger.info(f"📊 {tracker.format_single_plan_usage('data_for_search')}")

        response = {
            "success": True,
            "data": result,
            "metadata": {
                "has_extra_snippets": False,
                "fallback_used": True
            },
            "warning": (
                "Using fallback Search key without extra_snippets. "
                "AI key was not provided or is invalid."
            )
        }

        return response

    except Exception as e:
        logger.error(f"❌ search_web_extra_snippets_for_ai failed with fallback key: {e}")
        return {
            "success": False,
            "error": str(e)
        }

    finally:
        await service.close()


@mcp.tool()
async def search_images(
    query: str,
    count: int = 50,
    country: str = "US",
    search_lang: str = "en",
    safesearch: str = "strict",
    spellcheck: bool = True
) -> dict:
    """
    Search for images using Brave Image Search API.

    Returns image results relevant to the search query with thumbnails, source information,
    and metadata. Available on both "Data for Search" and "Data for AI" plans.

    Args:
        query: Search query string (max 400 chars, 50 words)
        count: Number of results to return (default: 50, max: 200)
        country: Search query country code (default: "US"). 2-character country code where the results come from
        search_lang: Search language code (default: "en"). 2 or more character language code for search results
        safesearch: Content filtering: "off", "strict" (default: "strict"). Filters adult content
        spellcheck: Enable spell checking (default: True). Whether to spellcheck the provided query

    Returns:
        dict: Response containing:
            - success (bool): Whether the request succeeded
            - data (dict): ImageSearchApiResponse with fields:
                - type: Always "images"
                - query: Query information (original, altered, spellcheck_off, show_strict_warning)
                - results: List of ImageResult objects with:
                    - title: Image title
                    - url: Original page URL where image was found
                    - source: Source domain of the image
                    - page_fetched: ISO datetime of last page fetch
                    - thumbnail: Image thumbnail details (src, width, height)
                    - properties: Image metadata (url, placeholder, width, height)
                    - meta_url: Aggregated URL information
                    - confidence: Result confidence level (low/medium/high)
                - extra: Additional info with might_be_offensive flag
    """
    logger.info(f"🖼️  search_images called: query='{query}', count={count}")

    # Apply AI-Saving Policy to determine which key to use
    tracker = get_tracker()
    use_ai_key, reason = tracker.should_use_ai_key()
    logger.info(f"🧠 AI-Saving Policy: {reason}")

    # Get API keys from context vars (headers)
    api_key_search = request_api_key_search.get()
    api_key_ai = request_api_key_ai.get()

    # Select key based on policy decision
    if use_ai_key and api_key_ai:
        api_key = api_key_ai
        plan_name = "data_for_ai"
        logger.info("🔑 Using Data For AI key")
    else:
        api_key = api_key_search
        plan_name = "data_for_search"
        logger.info("🔑 Using Data For Search key")

    service = BraveService(api_key)

    try:
        result = await service.search_images(
            query=query,
            count=count,
            country=country,
            search_lang=search_lang,
            safesearch=safesearch,
            spellcheck=spellcheck
        )

        # Track usage for the selected plan
        tracker.increment_usage(plan_name, 1)
        display_name = "Data For AI" if plan_name == "data_for_ai" else "Data For Search"
        logger.info(f"📊 Used 1 request from {display_name} quota")
        logger.info(f"📊 {tracker.format_single_plan_usage(plan_name)}")

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        logger.error(f"❌ search_images failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }

    finally:
        await service.close()


@mcp.tool()
async def search_videos(
    query: str,
    count: int = 20,
    country: str = "US",
    search_lang: str = "en",
    ui_lang: str = "en-US",
    offset: int = 0,
    safesearch: str = "moderate",
    freshness: str = "",
    spellcheck: bool = True,
    operators: bool = True
) -> dict:
    """
    Search for videos using Brave Video Search API.

    Returns video results relevant to the search query with thumbnails, duration,
    views, and metadata. Available on both "Data for Search" and "Data for AI" plans.
    Uses AI-Saving Policy to intelligently select the best API key.

    Args:
        query: Search query string (max 400 chars, 50 words)
        count: Number of results to return (default: 20, max: 50)
        country: Search query country code (default: "US"). 2-character country code where the results come from
        search_lang: Search language code (default: "en"). 2 or more character language code for search results
        ui_lang: UI language preference (default: "en-US"). Format: <language_code>-<country_code>
        offset: Pagination offset (default: 0, max: 9). Zero-based offset for pagination
        safesearch: Content filtering: "off", "moderate" (default), "strict". Filters adult content
        freshness: Time filter: "pd" (past day), "pw" (past week), "pm" (past month), "py" (past year), or date range (YYYY-MM-DDtoYYYY-MM-DD)
        spellcheck: Enable spell checking (default: True). Whether to spellcheck the provided query
        operators: Apply search operators (default: True). Whether to apply search operators in the query

    Returns:
        dict: Response containing:
            - success (bool): Whether the request succeeded
            - data (dict): VideoSearchApiResponse with fields:
                - type: Always "videos"
                - query: Query information (original, altered, spellcheck_off, show_strict_warning)
                - results: List of VideoResult objects with:
                    - type: "video_result"
                    - url: Source URL of the video
                    - title: Video title
                    - description: Video description text
                    - age: Human-readable content age
                    - page_age: Age data from source page
                    - page_fetched: ISO format timestamp
                    - thumbnail: {src, original}
                    - video: {duration, views, creator, publisher, requires_subscription, tags}
                    - meta_url: Aggregated URL information
                - extra: Additional info with might_be_offensive flag
    """
    logger.info(f"🎬 search_videos called: query='{query}', count={count}")

    # Apply AI-Saving Policy to determine which key to use
    tracker = get_tracker()
    use_ai_key, reason = tracker.should_use_ai_key()
    logger.info(f"🧠 AI-Saving Policy: {reason}")

    # Get API keys from context vars (headers)
    api_key_search = request_api_key_search.get()
    api_key_ai = request_api_key_ai.get()

    # Select key based on policy decision
    if use_ai_key and api_key_ai:
        api_key = api_key_ai
        plan_name = "data_for_ai"
        logger.info("🔑 Using Data For AI key")
    else:
        api_key = api_key_search
        plan_name = "data_for_search"
        logger.info("🔑 Using Data For Search key")

    service = BraveService(api_key)

    try:
        result = await service.search_videos(
            query=query,
            count=count,
            country=country,
            search_lang=search_lang,
            ui_lang=ui_lang,
            offset=offset,
            safesearch=safesearch,
            freshness=freshness or None,
            spellcheck=spellcheck,
            operators=operators
        )

        # Track usage for the selected plan
        tracker.increment_usage(plan_name, 1)
        display_name = "Data For AI" if plan_name == "data_for_ai" else "Data For Search"
        logger.info(f"📊 Used 1 request from {display_name} quota")
        logger.info(f"📊 {tracker.format_single_plan_usage(plan_name)}")

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        logger.error(f"❌ search_videos failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }

    finally:
        await service.close()


@mcp.tool()
async def search_news(
    query: str,
    count: int = 20,
    country: str = "US",
    search_lang: str = "en",
    ui_lang: str = "en-US",
    offset: int = 0,
    safesearch: str = "moderate",
    freshness: str = "",
    spellcheck: bool = True,
    extra_snippets: bool = False,
    goggles: str = "",
    operators: bool = True
) -> dict:
    """
    Search for news using Brave News Search API with AI-Saving Policy.

    Returns news articles relevant to the search query with breaking news flags,
    thumbnails, and metadata. Available on both "Data for Search" and "Data for AI" plans.
    Uses AI-Saving Policy to intelligently select the best API key.

    Args:
        query: Search query string (max 400 chars, 50 words)
        count: Number of results to return (default: 20, max: 50)
        country: Search query country code (default: "US"). 2-character country code where the results come from
        search_lang: Search language code (default: "en"). 2 or more character language code for search results
        ui_lang: UI language preference (default: "en-US"). Format: <language_code>-<country_code>
        offset: Pagination offset (default: 0, max: 9). Zero-based offset for pagination
        safesearch: Content filtering: "off", "moderate" (default), "strict". Filters adult content
        freshness: Time filter: "pd" (past day), "pw" (past week), "pm" (past month), "py" (past year), or date range (YYYY-MM-DDtoYYYY-MM-DD)
        spellcheck: Enable spell checking (default: True). Whether to spellcheck the provided query
        extra_snippets: Get up to 5 additional alternative excerpts (Data for AI plan only)
        goggles: Custom re-ranking definitions. List of Goggles IDs for custom re-ranking on top of Brave's search index
        operators: Apply search operators (default: True). Whether to apply search operators in the query

    Returns:
        dict: Response containing:
            - success (bool): Whether the request succeeded
            - data (dict): NewsSearchApiResponse with fields:
                - type: Always "news"
                - query: Query information (original, altered, spellcheck_off, show_strict_warning)
                - results: List of NewsResult objects with:
                    - title: News article title
                    - url: Source article URL
                    - description: Article description
                    - age: Human-readable content age
                    - page_age: Age data from source page
                    - page_fetched: ISO format timestamp
                    - breaking: Boolean indicating breaking news
                    - thumbnail: News thumbnail details (src, original)
                    - meta_url: Aggregated URL information
                    - extra_snippets: List of extra snippets (if extra_snippets=true)
    """
    logger.info(f"📰 search_news called: query='{query}', count={count}")

    # Apply AI-Saving Policy
    tracker = get_tracker()
    use_ai_key, reason = tracker.should_use_ai_key()
    logger.info(f"🧠 AI-Saving Policy: {reason}")

    # Select key based on policy
    api_key_search = request_api_key_search.get()
    api_key_ai = request_api_key_ai.get()

    if use_ai_key and api_key_ai:
        api_key = api_key_ai
        plan_name = "data_for_ai"
        display_name = "Data For AI"
        logger.info("🔑 Using Data For AI key")
    else:
        api_key = api_key_search
        plan_name = "data_for_search"
        display_name = "Data For Search"
        logger.info("🔑 Using Data For Search key")

    service = BraveService(api_key)

    try:
        # Convert empty strings to None for optional parameters
        freshness_param = freshness if freshness else None
        goggles_param = goggles.split(",") if goggles else None

        result = await service.search_news(
            query=query,
            count=count,
            country=country,
            search_lang=search_lang,
            ui_lang=ui_lang,
            offset=offset,
            safesearch=safesearch,
            freshness=freshness_param,
            spellcheck=spellcheck,
            extra_snippets=extra_snippets,
            goggles=goggles_param,
            operators=operators
        )

        # Track usage
        tracker.increment_usage(plan_name, 1)
        logger.info(f"📊 Used 1 request from {display_name} quota")
        logger.info(f"📊 {tracker.format_single_plan_usage(plan_name)}")

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        logger.error(f"❌ search_news failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }

    finally:
        await service.close()


@mcp.tool()
async def suggest(
    query: str,
    count: int = 5,
    country: str = "US",
    lang: str = "en",
    rich: bool = False
) -> dict:
    """
    Get search suggestions using Brave Suggest API.

    Returns potential query suggestions/autocomplete for a given search query.
    Uses the dedicated Autosuggest API key with its own quota (5000 requests/month).

    Args:
        query: Suggest search query (max 400 chars, 50 words)
        count: Number of suggestions to return (default: 5, min: 1, max: 20)
        country: Country code (default: "US"). 2-character country code
        lang: Language code (default: "en"). 2 or more character language code
        rich: Enhance suggestions with rich results (default: False). Requires paid subscription

    Returns:
        dict: Response containing:
            - success (bool): Whether the request succeeded
            - data (dict): SuggestSearchApiResponse with fields:
                - type: Always "suggest"
                - query: Query information (original)
                - results: List of SuggestResult objects with:
                    - query: Suggested query completion
                    - is_entity: Whether the suggestion is an entity (optional)
                    - title: Enriched title (optional, if rich=true)
                    - description: Enriched description (optional, if rich=true)
                    - img: Enriched image URL (optional, if rich=true)
    """
    logger.info(f"💡 suggest called: query='{query}', count={count}")

    # Autosuggest uses its own dedicated API key (no AI-Saving Policy)
    api_key_autosuggest = request_api_key_autosuggest.get()

    logger.info("🔑 Using Autosuggest key (dedicated pool)")

    service = BraveService(api_key_autosuggest)

    try:
        result = await service.suggest(
            query=query,
            count=count,
            country=country,
            lang=lang,
            rich=rich
        )

        # Track usage for autosuggest pool
        tracker = get_tracker()
        tracker.increment_usage("autosuggest", 1)
        logger.info(f"📊 Used 1 request from Autosuggest quota")
        logger.info(f"📊 {tracker.format_single_plan_usage('autosuggest')}")

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        logger.error(f"❌ suggest failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }

    finally:
        await service.close()


@mcp.tool()
async def spellcheck(
    query: str,
    country: str = "US",
    lang: str = "en"
) -> dict:
    """
    Spellcheck a query using Brave Spellcheck API.

    Checks spelling and provides corrected versions of the query.
    Uses the dedicated Spellcheck API key with its own quota (5000 requests/month).

    Args:
        query: Query to spellcheck (max 400 chars, 50 words)
        country: Country code (default: "US"). 2-character country code
        lang: Language code (default: "en"). 2 or more character language code

    Returns:
        dict: Response containing:
            - success (bool): Whether the request succeeded
            - data (dict): SpellCheckSearchApiResponse with fields:
                - type: Always "spellcheck"
                - query: Query information (original)
                - results: List of SpellCheckResult objects with:
                    - query: The spellcheck-corrected query
    """
    logger.info(f"✍️  spellcheck called: query='{query}', country={country}, lang={lang}")

    # Spellcheck uses its own dedicated API key
    api_key_spellcheck = request_api_key_spellcheck.get()

    logger.info("🔑 Using Spellcheck key (dedicated pool)")

    service = BraveService(api_key_spellcheck)

    try:
        result = await service.spellcheck(
            query=query,
            country=country,
            lang=lang
        )

        # Track usage for spellcheck pool
        tracker = get_tracker()
        tracker.increment_usage("spellcheck", 1)
        logger.info(f"📊 Used 1 request from Spellcheck quota")
        logger.info(f"📊 {tracker.format_single_plan_usage('spellcheck')}")

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        logger.error(f"❌ spellcheck failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }

    finally:
        await service.close()


# ============================================================================
# Server Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    import asyncio

    logger.info("=" * 80)
    logger.info(f"🏛️  Argus v{__version__}")
    logger.info("=" * 80)
    logger.info(f"📡 MCP Protocol: 2025-03-26 (Streamable HTTP)")
    logger.info(f"🌐 MCP Endpoint: http://{settings.mcp_server_host}:{settings.mcp_server_port}/mcp")
    logger.info(f"❤️  Health Check: http://{settings.mcp_server_host}:{settings.mcp_server_port}/health")
    logger.info(f"✅ Readiness Check: http://{settings.mcp_server_host}:{settings.mcp_server_port}/ready")
    logger.info("=" * 80)

    # Initialize usage tracker (costs 1 API request)
    tracker = get_tracker()

    # Check if API keys are available from environment (for initial check)
    # In production, these come from .mcp.json headers, but we need them for startup check
    import os
    api_key_search = os.getenv("X_BRAVE_API_KEY_SEARCH")
    api_key_ai = os.getenv("X_BRAVE_API_KEY_AI")

    if api_key_search:
        initial_check_success = asyncio.run(tracker.check_initial_usage(api_key_search, api_key_ai))

        if initial_check_success:
            logger.info(tracker.format_usage_for_startup())
        else:
            # Initial check failed - invalid/expired API key in .env
            logger.warning("⚠️⚠️⚠️ Variable 'X_BRAVE_API_KEY_SEARCH' in .env contains empty/bad/expired API key!")
            logger.warning("=" * 80)
            logger.warning("Argus is unable to check your current API Usage to track it.")
            logger.warning("Even if your API keys are correct in .mcp.json file,")
            logger.warning("the initial startup of Argus won't track your current API Usage correctly.")
            logger.warning("Set up 'X_BRAVE_API_KEY_SEARCH' to provide your Brave Search API Key")
            logger.warning("So your \"📊 API Usage (Free Plans):\" logs show correct initial Usage at startup")
            logger.warning("=" * 80)
            logger.info(tracker.format_usage_for_startup())
    else:
        logger.warning("⚠️  No API keys found in environment. Usage tracking will start after first request.")
        logger.info("=" * 80)

    logger.info(f"🔧 Available Tools:")
    logger.info(f"   • search_web - Web search with advanced parameters (Data for Search)")
    logger.info(f"   • search_web_extra_snippets_for_ai - Enhanced search with extra context (Data for AI)")
    logger.info(f"   • search_images - Image search with thumbnails and metadata (Data for Search & AI)")
    logger.info(f"   • search_videos - Video search with metadata (Data for Search & AI)")
    logger.info(f"   • search_news - News search with breaking news flags (Data for Search & AI)")
    logger.info(f"   • suggest - Query autocomplete suggestions (Autosuggest)")
    logger.info(f"   • spellcheck - Query spelling correction (Spellcheck)")
    logger.info("=" * 80)

    # Get the Starlette app and run with uvicorn for custom host/port
    app = mcp.streamable_http_app()

    # Add middleware to extract API keys from headers
    from starlette.middleware.base import BaseHTTPMiddleware

    class APIKeyMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            # Extract API keys from headers
            api_key_search = request.headers.get("X-Brave-API-Key-Search")
            api_key_ai = request.headers.get("X-Brave-API-Key-AI")
            api_key_autosuggest = request.headers.get("X-Brave-API-Key-Autosuggest")
            api_key_spellcheck = request.headers.get("X-Brave-API-Key-Spellcheck")

            # Set context variables for this request
            request_api_key_search.set(api_key_search)
            request_api_key_ai.set(api_key_ai)
            request_api_key_autosuggest.set(api_key_autosuggest)
            request_api_key_spellcheck.set(api_key_spellcheck)

            logger.debug(f"🔑 API Keys from headers: search={'✓' if api_key_search else '✗'}, ai={'✓' if api_key_ai else '✗'}, autosuggest={'✓' if api_key_autosuggest else '✗'}, spellcheck={'✓' if api_key_spellcheck else '✗'}")

            # Process request
            response = await call_next(request)

            return response

    app.add_middleware(APIKeyMiddleware)

    uvicorn.run(
        app,
        host=settings.mcp_server_host,
        port=settings.mcp_server_port,
        log_level=settings.log_level.lower()
    )
