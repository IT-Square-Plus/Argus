# 👁️ Argus - Brave Search MCP Server

Argus is a Model Context Protocol (MCP) server that provides comprehensive access to Brave Search API through HTTP Streamable transport. Designed for AI assistants like Claude Code, Argus enables web searching, image search, video search, news search, autocomplete suggestions, and spell checking.

The name originates from Greek mythology.

Argus Panoptes ("All-Seeing Argus") was a giant in Greek mythology with a hundred eyes scattered across his body, some always awake while others slept, making him the perfect watchman. This name perfectly mirrors Brave Search's core functionality: continuously gathering and aggregating information from multiple independent sources across the web. Like Argus with his independently vigilant eyes, Brave Search operates on its own independent index, observing and cataloging the internet from countless perspectives simultaneously. The name embodies surveillance, reliability, and omnipresence-qualities that define both the mythical guardian and a modern search engine.

## Features

- **Web Search** - Full-featured web search with customizable result filters
- **Enhanced Web Search** - Get 6x more context with extra snippets (Data for AI plan)
- **Image Search** - Search and retrieve images with metadata
- **Video Search** - Find videos with duration, views, and publisher info
- **News Search** - Get latest news articles with breaking news flags
- **Autocomplete** - Query suggestions and autocomplete
- **Spell Checking** - Query correction and spell checking
- **Real-time Usage Tracking** - Monitor API quota usage across all plans
- **Health Monitoring** - Liveness and readiness probes for container orchestration

## Quick Start

### Prerequisites

- **Docker & Docker Compose** - [Install Docker](https://docs.docker.com/get-docker/)
- **Brave Search API Key** - [Get your free API key](https://api-dashboard.search.brave.com/app/keys)
  - Required: **Data for Search** plan (2000 requests/month free)<sup>[1](#footnote-brave-api-guide)</sup>
  - Optional: **Data for AI**, **Autosuggest**, **Spellcheck** plans<sup>[1](#footnote-brave-api-guide)</sup>

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/IT-Square-Plus/Argus
   cd Argus
   ```

2. **Configure environment variables**

   ```bash
   cp .env.example .env
   # Edit .env and add your Brave Search API key for startup usage tracking
   ```

   > Don't have API keys yet? See the [Brave Search API Guide](docs/BRAVE_SEARCH_API_GUIDE.md)<sup>[1](#footnote-brave-api-guide)</sup> for step-by-step instructions.

3. **Configure MCP client (Claude Code)**

   ```bash
   cp .mcp.json.example .mcp.json
   # Edit .mcp.json and replace placeholder API keys with your actual keys
   ```

   > Don't have API keys yet? See the [Brave Search API Guide](docs/BRAVE_SEARCH_API_GUIDE.md)<sup>[1](#footnote-brave-api-guide)</sup> for step-by-step instructions.

4. **Start Argus container**

   ```bash
   docker-compose up -d
   ```

5. **Verify service is ready**

   ```bash
   curl http://localhost:8081/ready
   ```

6. **Restart Claude Code** to load the MCP server

## Configuration

### Environment Variables (.env)

The `.env` file configures the Docker container startup behavior:

```bash
# MCP Server Configuration
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8081
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Free Plan Limits (for usage tracking)
DATA_FOR_SEARCH_FREE_PLAN_MAX_USAGE=2000
DATA_FOR_AI_FREE_PLAN_MAX_USAGE=2000
DATA_FOR_SPELLCHECK_FREE_PLAN_MAX_USAGE=5000
DATA_FOR_AUTOSUGGEST_FREE_PLAN_MAX_USAGE=5000

# Optional: API Key for startup usage check
# This displays accurate quota info in startup logs
# Runtime tools use keys from .mcp.json (HTTP headers)
X_BRAVE_API_KEY_SEARCH=your_api_key_here
```

### MCP Client Configuration (.mcp.json)

The `.mcp.json` file configures Claude Code to connect to Argus:

```json
{
  "mcpServers": {
    "Argus": {
      "type": "http",
      "url": "http://localhost:8081/mcp",
      "headers": {
        "X-Brave-API-Key-Search": "your_data_for_search_api_key_here",
        "X-Brave-API-Key-AI": "your_data_for_ai_api_key_here",
        "X-Brave-API-Key-Autosuggest": "your_autosuggest_api_key_here",
        "X-Brave-API-Key-Spellcheck": "your_spellcheck_api_key_here"
      }
    }
  }
}
```

**Important Notes:**

- Only `X-Brave-API-Key-Search` is **required** for core functionality
- Other API keys are **optional** and enable additional features
- You can use the same API key for multiple headers if you have multiple plans
- API keys are provided via HTTP headers (per-request, not stored in container)

## 🔧 Available Tools

### search_web

Full-featured web search with Brave Search API.

**Key Parameters:**

- `query` - Search query (required)
- `count` - Number of results (default: 10, max: 20)
- `result_filter` - Filter results by type:
  - `"web"` (default, ~3k tokens) - Web results only ✅ Recommended
  - `""` (all clusters, ~10k tokens) - All result types
  - `"news"` - News articles only
  - `"videos"` - Videos only
  - `"discussions"` - Forum discussions only
  - `"faq"` - Q&A results only
  - `"infobox"` - Knowledge graph entities only
  - `"locations"` - Places of interest only
  - Combinations: `"web,news"`, `"web,videos"`, etc.
- `country`, `search_lang` - Localization options
- `freshness` - Time filter: "pd", "pw", "pm", "py"

**Token Cost:**

- `result_filter="web"`: ~3,000 tokens (web results only) ✅ **Recommended**
- `result_filter=""`: ~10,000 tokens (all clusters: web + news + videos + discussions)

**Tip:** Use specialized tools (`search_news`, `search_videos`, `search_images`) for better performance.

### search_web_extra_snippets_for_ai

Enhanced web search with up to 5 additional excerpts per result (6x more context).

**Requirements:** Data for AI plan

### search_images

Search for images with thumbnails and metadata.

**Returns:** Image URLs, thumbnails, source information, dimensions

### search_videos

Search for videos with duration, views, and publisher info.

**Returns:** Video URLs, thumbnails, duration, views, creator, publisher

### search_news

Search for news articles with breaking news flags.

**Returns:** News articles, age, breaking news indicators, thumbnails

### suggest

Get query autocomplete suggestions.

**Requirements:** Autosuggest plan (optional)

### spellcheck

Check and correct query spelling.

**Requirements:** Spellcheck plan (optional)

## Health Endpoints

### GET /health

**Liveness probe** - Quick check if service is alive.

```bash
curl http://localhost:8081/health
```

**Response:**

```json
{
  "status": "alive",
  "service": "Argus",
  "version": "1.0.1"
}
```

**Use case:** Basic monitoring, container restart decisions

### GET /ready

**Readiness probe** - Check if service is ready to accept requests.

```bash
curl http://localhost:8081/ready
```

**Response:**

```json
{
  "status": "ready",
  "service": "Argus",
  "version": "1.0.1",
  "capabilities": {
    "search_web": true,
    "search_web_extra_snippets_for_ai": true,
    "search_images": true,
    "search_videos": true,
    "search_news": true,
    "suggest": true,
    "spellcheck": true
  },
  "usage": {
    "data_for_search": {
      "used": 141,
      "limit": 2000,
      "remaining": 1859,
      "percentage": 7.0
    },
    "data_for_ai": {
      /* ... */
    },
    "spellcheck": {
      /* ... */
    },
    "autosuggest": {
      /* ... */
    }
  }
}
```

> **Note:** Usage statistics are calculated only when you provide a valid Search API key in `.env`. Without it, you'll see `0/2000` for all quotas, but MCP tools will still work correctly using keys from `.mcp.json`.

**Use case:** Deployment validation, load balancer health checks, detailed monitoring ✅ **Recommended**

## Project Structure

```
Argus/
├── src/
│   ├── __init__.py           # Version management (importlib.metadata)
│   ├── server.py             # MCP server and tool implementations
│   ├── config/
│   │   └── settings.py       # Configuration (pydantic-settings)
│   ├── services/
│   │   ├── brave_service.py  # Brave Search API client
│   │   └── usage_tracker.py  # API usage tracking
│   └── utils/
│       └── response_formatter.py  # Response formatting
├── Dockerfile                # Multi-stage Docker build
├── docker-compose.yml        # Container orchestration
├── pyproject.toml            # Package metadata and dependencies
├── .env.example              # Environment variables template
├── .mcp.json.example         # MCP client configuration template
└── README.md                 # This file
```

## API Key Architecture

Argus uses a dual-key architecture for optimal security and functionality:

### Startup Key (.env)

- **Purpose:** Display accurate API usage in startup logs
- **Scope:** Container startup only
- **Optional:** Tools work without this key (shows 0/2000 if missing)
- **Location:** `X_BRAVE_API_KEY_SEARCH` in `.env`

### Runtime Keys (.mcp.json)

- **Purpose:** Actual API calls from MCP tools
- **Scope:** Per-request via HTTP headers
- **Required:** `X-Brave-API-Key-Search` (minimum)
- **Location:** `.mcp.json` headers section

**Why separate?**

- Docker container starts **before** any HTTP requests arrive
- Startup usage check needs a key (no `.mcp.json` headers available yet)
- Runtime tools use per-request keys from `.mcp.json` headers
- Keys are never stored in the container (stateless design)

## API Plans and Limits

| Plan                | Free Tier                 | Tools                                                         |
| ------------------- | ------------------------- | ------------------------------------------------------------- |
| **Data for Search** | 2000 req/month, 1 req/sec | `search_web`, `search_images`, `search_videos`, `search_news` |
| **Data for AI**     | 2000 req/month, 1 req/sec | `search_web_extra_snippets_for_ai`                            |
| **Autosuggest**     | 5000 req/month, 5 req/sec | `suggest`                                                     |
| **Spellcheck**      | 5000 req/month, 5 req/sec | `spellcheck`                                                  |

[Get your API keys - See setup guide](docs/BRAVE_SEARCH_API_GUIDE.md)<sup>[1](#footnote-brave-api-guide)</sup>

## FAQ

<details>
<summary><strong>Why not official Brave Search MCP?</strong></summary>

Because it doesn't fit my needs.

- I want to rely only on Free plans and Official [Brave Search MCP Server](https://github.com/brave/brave-search-mcp-server) supports all of the plans.
- Official Brave Search provides curated and trimmed API response. Already filtered out. I prefer to have a full JSON response from API. Claude Code is smart enough to understand it and as a matter of fact - he likes it 😊

</details>

<details>
<summary><strong>No NPX?</strong></summary>

Nope.

I don't know Node.js at all and therefore I don't develop in languages I don't know. Plus MCP Docker Container provides great visibility of how your tool is working.

</details>

<details>
<summary><strong>Why do I need to provide a credit card for free plans?</strong></summary>

Brave requires credit card verification for all API subscriptions, including free tiers. This is a standard practice to prevent abuse. The free tier quotas (2,000-5,000 requests/month) are generous enough for typical usage, so you shouldn't incur charges unless you exceed these limits.

</details>

<details>
<summary><strong>Can I use the same API key for multiple tools?</strong></summary>

No. Each Brave Search API subscription (Data for Search, Data for AI, Spellcheck, Autosuggest) requires its own separate API key. However, you only need the "Data for Search" key for Argus to work - other keys are optional and enable additional features.

</details>

<details>
<summary><strong>Why are usage stats showing 0/2000 in startup logs?</strong></summary>

This happens when you don't provide a valid Search API key in `.env`. The startup key is optional and only used for displaying accurate quota information in logs. Your MCP tools will still work correctly using keys from `.mcp.json`.

</details>

<details>
<summary><strong>What "🧠 AI-Saving Policy" log line means?</strong></summary>

Argus has two main tools that you probably going to work with:

- `search_web`
- `search_web_extra_snippets_for_ai`

These tools are mainly used for searchning the web for plain websites. They can of course search for images, videos, news but you need to explicitly tell Claude to use those tools. For example:

`Search for an image of sad puppy dog using search_web_extra_snippets_for_ai`

In this case you've told Claude to use `search_web_extra_snippets_for_ai` Tool and you've burned a request from `Data for AI` pool.

However, usually you will tell Claude this:

`Search for an image of sad puppy dog`

In this case Claude will use a Tool called `search_images` cause it has a proper Tool Description and this tool is dedicated and optimised for searching images. But!
But which type of request its gonna burn? Here's the problem. Both plans (Data for Search and Data for AI) can search for images. But you might want to save those precious Data for AI requests, eh?

That's why AI-Saving Policy was introduced. And here's how it works:

1. **AI has > 50% remaining?**

   - _Save AI and use Search pool_

2. **Search has ≥ 10% remaining?**

   - _Keep using Search pool and save AI_

3. **Search < 10% remaining?**
   - _Search is getting dangerously low. Leave it for `search_web` and use AI pool for `search_images`_

**AI-Saving Policy Decision Tree:**

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI-Saving Policy Logic                       │
└─────────────────────────────────────────────────────────────────┘

                    ┌─────────────────┐
                    │ search_images   │
                    │    called       │
                    └────────┬────────┘
                             │
                             ▼
                ┌────────────────────────┐
                │   AI remaining > 50%?  │
                └────────┬───────────────┘
                         │
            ┌────────────┴────────────┐
            │ YES                     │ NO
            ▼                         ▼
     ┌─────────────┐      ┌───────────────────────┐
     │ Use SEARCH  │      │ Search remaining ≥10%?│
     │  (save AI)  │      └──────────┬────────────┘
     └─────────────┘                 │
                          ┌──────────┴──────────┐
                          │ YES                 │ NO
                          ▼                     ▼
                   ┌─────────────┐      ┌─────────────┐
                   │ Use SEARCH  │      │   Use AI    │
                   │  (save AI)  │      │ (Search low)│
                   └─────────────┘      └─────────────┘
```

You will notice logs like this:

```bash
INFO - 🖼️  search_images called: query='sad puppy dog', count=1
INFO - 🧠 AI-Saving Policy: AI has 92.8% remaining (>50%) → Using Search to save AI
INFO - 🔑 Using Data For Search key
INFO - 🖼️  Image search: query='sad puppy dog', count=1, country=US
INFO - HTTP Request: GET https://api.search.brave.com/res/v1/images/search?q=sad+puppy+dog&count=1&country=US&search_lang=en&safesearch=strict&spellcheck=true⁠ "HTTP/1.1 200 OK"
INFO - ✅ Image search successful: 1 images returned
INFO - 📊 Used 1 request from Data For Search quota
INFO - 📊 Current Data For Search usage: [██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░]  144/2000 (  7.2%) - 1856 remaining
```

This image_search query has saved you a request from `Data for AI` pool.

> **NOTE:** AI-Saving Policy works for:
>
> - `search_images`
> - `search_videos`
> - `search_news`

</details>

<details>
<summary><strong>Does Argus work with other AI tools than Claude Desktop?</strong></summary>

Argus is designed and tested with Claude Code. It hasn't been tested on anything else but it should work since it's MCP HTTP Streamable protocol.

If you tried it on anything else than Claude Code - please let me know. I can't do this cause I don't have enough spare time for these tests.

</details>

<details>
<summary><strong>What are the next plans?</strong></summary>

- Introduce hard limit for API Usage quotas. So when you reach 2000 free requests - it will block any further attempts saving your money.
- CI/CD tests

</details>

## Footnotes

### <a name="footnote-brave-api-guide">[1]</a> Brave Search API Guide

For complete setup guide with step-by-step instructions on how to subscribe to free plans and generate API keys, see: [`docs/BRAVE_SEARCH_API_GUIDE.md`](docs/BRAVE_SEARCH_API_GUIDE.md)
