from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.search.base import SearchResult


def generate_queries(title: str, thought: str, context: str | None) -> list[str]:
    """Keep the title and a short opening excerpt; never send an entire long note."""
    title = " ".join(title.split())[:100]
    queries = []
    seen = set()
    for text in (thought, context):
        if not text or not text.strip():
            continue
        excerpt = " ".join(text.split())[:180]
        query = " ".join(f"{title} {excerpt}".split()[:40])[:240].rstrip()
        identity = " ".join(query.casefold().split()).rstrip(".?!")
        if identity not in seen:
            queries.append(query)
            seen.add(identity)
    return queries or [title]


def normalized_url(url: str) -> str:
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    port = parts.port
    if port and (parts.scheme.lower(), port) not in (("http", 80), ("https", 443)):
        host += f":{port}"
    query = urlencode(sorted(
        (key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in ("fbclid", "gclid")
    ))
    return urlunsplit((parts.scheme.lower(), host, parts.path.rstrip("/"), query, ""))


def unique_sources(results: list[SearchResult]) -> list[SearchResult]:
    sources = []
    seen = set()
    for result in results:
        parts = urlsplit(result.url)
        if (parts.scheme not in ("http", "https") or not parts.hostname
                or not result.title.strip() or not result.snippet.strip()):
            continue
        identity = normalized_url(result.url)
        if identity not in seen:
            seen.add(identity)
            sources.append(result)
            if len(sources) == 8:
                break
    return sources
