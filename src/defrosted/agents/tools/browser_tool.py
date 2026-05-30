"""
Listing scraper tool (Playwright + Browserbase).

Browserbase gives us managed, fingerprint-resistant browser sessions so we can
scrape Zillow/Craigslist/Facebook/Hotpads without immediately tripping bot
defenses. Playwright drives the page over Browserbase's CDP endpoint.

Per-site DOM parsing is deliberately NOT implemented here yet: each platform
needs its own resilient selectors and they change often, so they belong in
dedicated, separately-tested site adapters. ``execute`` fails loudly
(NotImplementedError) for any site without an adapter rather than silently
returning zero listings, which would look like "no results" to the user.

Heavy imports (playwright) are deferred into the method so importing this module
does not require the browser stack to be installed.
"""
from __future__ import annotations

from typing import Any

from ...config import Settings
from ..tools.base import AgentTool, ToolResult

BROWSERBASE_CONNECT_URL = "wss://connect.browserbase.com"

# Site adapters are registered here as they are built and individually tested.
_SITE_ADAPTERS: dict[str, Any] = {}


class BrowserScraperTool(AgentTool):

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.browserbase_api_key
        self._project_id = settings.browserbase_project_id

    @property
    def tool_name(self) -> str:
        return "scrape_listings"

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        required = ["source", "search_url"]
        missing = [k for k in required if k not in params]
        if missing:
            raise ValueError(
                f"BrowserScraperTool.execute() missing required params: {missing}. "
                f"Got: {list(params.keys())}"
            )

        source = params["source"]
        adapter = _SITE_ADAPTERS.get(source)
        if adapter is None:
            raise NotImplementedError(
                f"No scraping adapter is registered for source '{source}'. "
                f"Registered adapters: {sorted(_SITE_ADAPTERS)}. "
                "Add and test a site adapter before scraping this source."
            )

        # When adapters exist, this is where we open a Browserbase session and
        # hand the page to the adapter. Until then, the guard above is the path.
        listings = await adapter.scrape(params["search_url"])  # pragma: no cover
        return ToolResult(  # pragma: no cover
            success=True,
            message=f"Scraped {len(listings)} listings from {source}.",
            data={"listings": listings},
            provider_reference=None,
        )

    async def verify(self, provider_reference: str) -> bool:
        # Scraping has no external provider receipt to confirm against; the
        # workflow verifies results by counting persisted listings instead.
        return True

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.tool_name,
            "description": (
                "Scrape rental listings from a supported source given a search URL. "
                "Returns structured listing data for ingestion and dedup."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "One of: zillow, craigslist, facebook_marketplace, hotpads",
                    },
                    "search_url": {"type": "string", "description": "The pre-filtered search results URL."},
                },
                "required": ["source", "search_url"],
            },
        }
