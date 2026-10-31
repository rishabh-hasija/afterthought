from app.config import SEARCH_PROVIDER
from app.search.base import SearchProvider, SearchResult


class MockSearchProvider:
    """Return no sources until a real provider or test fixtures are supplied."""

    def search(self, query: str) -> list[SearchResult]:
        return []


def get_search_provider() -> SearchProvider:
    if SEARCH_PROVIDER == "mock":
        return MockSearchProvider()
    raise ValueError(f"Unsupported search provider: {SEARCH_PROVIDER}")
