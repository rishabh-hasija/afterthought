from urllib.parse import urlencode

from app.config import SEARCH_PROVIDER
from app.search.base import SearchProvider, SearchResult


class MockSearchProvider:
    """Return clearly labelled sample sources without making network requests."""

    def search(self, query: str) -> list[SearchResult]:
        query_string = urlencode({"q": query})
        return [
            SearchResult(
                title=f"Sample {topic}: {query}",
                url=f"https://example.com/{path}?{query_string}",
                snippet=f"Mock {topic} material related to {query}.",
            )
            for topic, path in [
                ("overview", "overview"),
                ("background", "background"),
                ("reading", "reading"),
            ]
        ]


def get_search_provider() -> SearchProvider:
    if SEARCH_PROVIDER == "mock":
        return MockSearchProvider()
    raise ValueError(f"Unsupported search provider: {SEARCH_PROVIDER}")
