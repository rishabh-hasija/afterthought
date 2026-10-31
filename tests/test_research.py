import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest

from app.models import Note, NoteStatus
from app.schemas import ResearchSummary
from app.search import provider
from app.search.base import SearchResult
from app.search.brave import BraveSearchProvider
from app.search.queries import generate_queries, unique_sources
from app.services import gemma, research
from tests.test_notes import save_note


def source(url="https://sources.test/insulation", title="Insulation"):
    return SearchResult(title, url, "Moisture needs careful assessment.")


def test_queries_include_trimmed_thought_and_context():
    assert generate_queries(" Older house ", "  insulation\n risks ", " practical options ") == [
        "Older house insulation risks", "Older house practical options"
    ]
    queries = generate_queries("T" * 200, "B" * 10000, "C" * 10000)
    assert len(queries) == 2
    assert all(len(query) <= 240 for query in queries)


def test_duplicate_queries_and_missing_context():
    assert generate_queries("House", "Insulation risks?", "insulation  risks") == [
        "House Insulation risks?"
    ]
    assert generate_queries("House", "Insulation", None) == ["House Insulation"]
    assert generate_queries("House", "", " ") == ["House"]


def brave_response(monkeypatch, payload, status=200):
    calls = []

    def get(url, **kwargs):
        calls.append((url, kwargs))
        return httpx.Response(status, json=payload, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", get)
    return calls


def test_brave_maps_results_and_request(monkeypatch):
    calls = brave_response(monkeypatch, {"web": {"results": [
        {"title": "House &amp; roof", "url": "https://sources.test/roof",
         "description": "Avoid <strong>moisture</strong>."},
        {"title": "No snippet", "url": "https://sources.test/empty"},
    ]}})
    assert BraveSearchProvider("test-key").search("old house") == [
        SearchResult("House & roof", "https://sources.test/roof", "Avoid moisture.")
    ]
    url, kwargs = calls[0]
    assert url == "https://api.search.brave.com/res/v1/web/search"
    assert kwargs["headers"]["X-Subscription-Token"] == "test-key"
    assert kwargs["params"] == {"q": "old house", "count": 5, "result_filter": "web"}
    assert kwargs["timeout"] == 15.0


@pytest.mark.parametrize("payload", [[], {}, {"web": None}, {"web": {"results": {}}},
    {"web": {"results": [None]}}, {"web": {"results": [{"title": 42}]}},
    {"web": {"results": [{"title": "Bad", "url": "javascript:alert(1)", "description": "Bad"}]}}])
def test_brave_malformed_response(monkeypatch, payload):
    brave_response(monkeypatch, payload)
    with pytest.raises(ValueError, match="malformed"):
        BraveSearchProvider("test-key").search("query")


def test_brave_invalid_json(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: httpx.Response(
        200, text="not JSON", request=httpx.Request("GET", "https://search.test")))
    with pytest.raises(ValueError, match="malformed"):
        BraveSearchProvider("test-key").search("query")


@pytest.mark.parametrize("payload", [{"query": {"original": "query"}}, {"web": {"results": []}}])
def test_brave_no_results(monkeypatch, payload):
    brave_response(monkeypatch, payload)
    assert BraveSearchProvider("test-key").search("query") == []


@pytest.mark.parametrize("status", [401, 429, 500])
def test_brave_http_error_hides_response_body(monkeypatch, status):
    brave_response(monkeypatch, {"error": "secret-key"}, status)
    with pytest.raises(RuntimeError, match=f"HTTP {status}") as error:
        BraveSearchProvider("secret-key").search("query")
    assert "secret-key" not in str(error.value)


def test_brave_timeout(monkeypatch):
    def timeout(*args, **kwargs):
        raise httpx.ReadTimeout("secret-key")
    monkeypatch.setattr(httpx, "get", timeout)
    with pytest.raises(RuntimeError, match="could not be reached"):
        BraveSearchProvider("secret-key").search("query")


def test_missing_brave_key_and_unsupported_provider(monkeypatch):
    monkeypatch.setattr(provider, "SEARCH_PROVIDER", "brave")
    monkeypatch.setattr(provider, "SEARCH_API_KEY", " ")
    with pytest.raises(ValueError, match="Set SEARCH_API_KEY"):
        provider.get_search_provider()
    monkeypatch.setattr(provider, "SEARCH_PROVIDER", "unknown")
    with pytest.raises(ValueError, match="Unsupported search provider"):
        provider.get_search_provider()


def test_url_deduplication_preserves_first_source_and_limits_total():
    first = source("https://SOURCES.test:443/path/?b=2&a=1&utm_source=feed#top")
    results = [first, source("https://sources.test/path?a=1&b=2"),
               source("javascript:alert(1)"), SearchResult("Empty", "https://empty.test", " ")]
    results += [source(f"https://sources.test/{index}") for index in range(10)]
    unique = unique_sources(results)
    assert len(unique) == 8
    assert unique[0] == first
    assert unique[1:] == results[4:11]
    # Meaningful query parameters and path case must remain distinct.
    assert len(unique_sources([source("https://s.test/P?a=1"), source("https://s.test/p?a=2")])) == 2


def use_brave(monkeypatch):
    monkeypatch.setattr(provider, "SEARCH_PROVIDER", "brave")
    monkeypatch.setattr(provider, "SEARCH_API_KEY", "test-key")


def test_real_pipeline_combines_queries_and_displays_sources(client, test_database, monkeypatch):
    use_brave(monkeypatch)
    queries = []
    supplied = []

    def search(self, query):
        queries.append(query)
        return [source(), source(f"https://sources.test/{len(queries)}")]

    def summarize(note, context, results):
        assert "Solar panels" in note and "How do they work?" in note
        assert context == "For my roof"
        supplied.extend(results)
        return ResearchSummary(summary="Overview\nA grounded brief.")

    monkeypatch.setattr(BraveSearchProvider, "search", search)
    monkeypatch.setattr(research, "summarize_research", summarize)
    response = client.post("/notes", data={
        "title": "Solar panels", "body": "How do they work?", "context": "For my roof"})
    assert queries == ["Solar panels How do they work?", "Solar panels For my roof"]
    assert len(supplied) == 3
    assert "A grounded brief." in response.text
    assert 'href="https://sources.test/insulation"' in response.text
    assert "mock results" not in response.text and "example.com" not in response.text
    assert client.get(response.url).text == response.text
    with test_database() as session:
        note = session.get(Note, 1)
        assert note.status == NoteStatus.complete
        assert len(json.loads(note.sources_json)) == 3
        assert note.researched_at and note.error_message is None


@pytest.mark.parametrize("failure", ["brave", "gemma", "empty", "key"])
def test_real_pipeline_failures_preserve_note(test_database, monkeypatch, failure):
    use_brave(monkeypatch)
    note_id = save_note(test_database, context="Keep context")

    def fail(*args, **kwargs):
        raise RuntimeError("Service unavailable")

    monkeypatch.setattr(BraveSearchProvider, "search", lambda *a: [source()])
    if failure == "brave":
        monkeypatch.setattr(BraveSearchProvider, "search", fail)
    elif failure == "gemma":
        monkeypatch.setattr(research, "summarize_research", fail)
    elif failure == "empty":
        monkeypatch.setattr(BraveSearchProvider, "search", lambda *a: [])
    else:
        monkeypatch.setattr(provider, "SEARCH_API_KEY", "")
    research.research_note(note_id)
    with test_database() as session:
        note = session.get(Note, note_id)
        assert (note.title, note.body, note.context) == ("Solar panels", "How do they work?", "Keep context")
        assert note.status == NoteStatus.failed
        expected = {"key": "Set SEARCH_API_KEY", "empty": "no useful sources"}.get(failure, "Service unavailable")
        assert expected in note.error_message
        assert note.researched_at is None and json.loads(note.sources_json) == []


def fake_gemma(monkeypatch, text):
    monkeypatch.setattr(gemma, "GEMINI_API_KEY", "test-secret")
    client = MagicMock()
    client.__enter__.return_value = client
    client.models.generate_content.return_value = SimpleNamespace(text=text)
    monkeypatch.setattr(gemma.genai, "Client", lambda **kwargs: client)
    return client


def test_gemma_model_prompt_and_json(monkeypatch):
    client = fake_gemma(monkeypatch, '```json\n{"summary":" Overview\\nGrounded findings. "}\n```')
    assert gemma.summarize_research("Thought", "Context", [source()]).summary == "Overview\nGrounded findings."
    kwargs = client.models.generate_content.call_args.kwargs
    assert kwargs["model"] == "gemma-4-26b-a4b-it"
    assert "Uncertainties" in kwargs["contents"]
    material = json.loads(kwargs["contents"].split("\n", 1)[1])
    assert material["note"] == "Thought"
    assert material["context"] == "Context"
    assert material["search_results"][0]["url"] == source().url


@pytest.mark.parametrize("text", [None, "", "not JSON", '{"summary":" "}', '{}'])
def test_gemma_rejects_invalid_summary(monkeypatch, text):
    fake_gemma(monkeypatch, text)
    with pytest.raises(ValueError, match="summary"):
        gemma.summarize_research("Thought", None, [source()])


def test_gemma_errors_do_not_expose_keys(monkeypatch):
    client = fake_gemma(monkeypatch, "")
    client.models.generate_content.side_effect = RuntimeError("test-secret request failed")
    with pytest.raises(RuntimeError, match="Gemma request failed") as error:
        gemma.summarize_research("Thought", None, [source()])
    assert "test-secret" not in str(error.value)
    monkeypatch.setattr(gemma, "GEMINI_API_KEY", "")
    with pytest.raises(ValueError, match="Set GEMINI_API_KEY"):
        gemma.summarize_research("Thought", None, [source()])


def test_failure_state_redacts_configured_keys(test_database, monkeypatch):
    use_brave(monkeypatch)
    note_id = save_note(test_database)
    monkeypatch.setattr(research, "GEMINI_API_KEY", "gemma-secret")
    monkeypatch.setattr(research, "SEARCH_API_KEY", "brave-secret")

    def fail(*args):
        raise RuntimeError("gemma-secret brave-secret failed")

    monkeypatch.setattr(BraveSearchProvider, "search", fail)
    research.research_note(note_id)
    with test_database() as session:
        note = session.get(Note, note_id)
        assert note.status == NoteStatus.failed
        assert "secret" not in note.error_message
        assert note.error_message.count("[redacted]") == 2
