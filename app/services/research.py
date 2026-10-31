import json
from dataclasses import asdict

from app import database
from app.models import Note, NoteStatus, utc_now
from app.search.base import SearchResult
from app.search.provider import get_search_provider


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

            results = get_search_provider().search(note.title)
            note.research_summary = mock_summary(note, results)
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
                note.error_message = f"Mock research failed: {str(exc) or type(exc).__name__}"
                session.commit()
