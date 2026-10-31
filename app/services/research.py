import json
from dataclasses import asdict

from app import database
from app.config import GEMINI_API_KEY, SEARCH_API_KEY
from app.models import Note, NoteStatus, utc_now
from app.search.base import SearchResult
from app.search.provider import MockSearchProvider, get_search_provider
from app.search.queries import generate_queries, unique_sources
from app.services.gemma import summarize_research


def mock_summary(note: Note, results: list[SearchResult]) -> str:
    summary = (
        f"Mock research for '{note.title}' found {len(results)} sample sources. "
        f"The thought focuses on: {note.body}"
    )
    if note.context:
        summary += f"\n\nContext: {note.context}"
    if results:
        summary += "\n\nSample findings:\n" + "\n".join(result.snippet for result in results)
    return summary


def research_note(note_id: int) -> None:
    with database.SessionLocal() as session:
        try:
            note = session.get(Note, note_id)
            if note is None or note.status not in (NoteStatus.saved, NoteStatus.researching):
                return
            note.status = NoteStatus.researching
            session.commit()

            provider = get_search_provider()
            if isinstance(provider, MockSearchProvider):
                results = provider.search(note.title)
                summary = mock_summary(note, results)
            else:
                results = unique_sources([
                    result
                    for query in generate_queries(note.title, note.body, note.context)
                    for result in provider.search(query)
                ])
                if not results:
                    raise ValueError("Search found no useful sources for this thought.")
                summary = summarize_research(
                    f"{note.title}\n\n{note.body}", note.context, results
                ).summary
            note.research_summary = summary
            note.sources_json = json.dumps([asdict(result) for result in results])
            note.researched_at = utc_now()
            note.error_message = None
            note.status = NoteStatus.complete
            session.commit()
        except Exception as exc:
            session.rollback()
            note = session.get(Note, note_id)
            if note is not None:
                note.status = NoteStatus.failed
                message = str(exc) or type(exc).__name__
                for secret in (GEMINI_API_KEY, SEARCH_API_KEY):
                    if secret:
                        message = message.replace(secret, "[redacted]")
                note.error_message = f"Research failed: {message[:500]}"
                session.commit()
