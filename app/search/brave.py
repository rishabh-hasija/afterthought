from html import unescape
import re
from urllib.parse import urlsplit

import httpx

from app.search.base import SearchResult


class BraveSearchProvider:
    """Map Brave web results to the application's small search interface."""

    def __init__(self, api_key: str):
        if not api_key.strip():
            raise ValueError("Set SEARCH_API_KEY in .env before using Brave Search.")
        self.api_key = api_key.strip()

    def search(self, query: str) -> list[SearchResult]:
        try:
            response = httpx.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"X-Subscription-Token": self.api_key, "Accept": "application/json"},
                params={"q": query, "count": 5, "result_filter": "web"},
                timeout=15.0,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Brave Search returned HTTP {exc.response.status_code}. "
                "Check SEARCH_API_KEY, quota, and service availability."
            ) from None
        except httpx.RequestError:
            raise RuntimeError("Brave Search could not be reached. Try again later.") from None

        try:
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError
            if "web" not in payload and not isinstance(payload.get("query"), dict):
                raise ValueError
            # Brave can omit the web section when no web results were found.
            web = payload.get("web", {"results": []})
            rows = web["results"]
            if not isinstance(rows, list):
                raise ValueError
            results = []
            for row in rows[:5]:
                title, url = row["title"], row["url"]
                snippet = row.get("description") or ""
                if not all(isinstance(value, str) for value in (title, url, snippet)):
                    raise ValueError
                parsed = urlsplit(url)
                if parsed.scheme not in ("http", "https") or not parsed.hostname:
                    raise ValueError
                # Brave snippets can contain emphasis markup, not page content.
                title = unescape(re.sub(r"<[^>]+>", "", title)).strip()
                snippet = unescape(re.sub(r"<[^>]+>", "", snippet)).strip()
                if title and snippet:
                    results.append(SearchResult(title=title, url=url, snippet=snippet))
            return results
        except (ValueError, KeyError, TypeError):
            raise ValueError("Brave Search returned a malformed response.") from None
