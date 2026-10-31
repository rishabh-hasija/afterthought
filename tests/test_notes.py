import json
from datetime import datetime, timedelta

import pytest
from sqlalchemy import event, select

from app import main
from app.models import Note, NoteStatus
from app.search.provider import MockSearchProvider
from app.services import research


def save_note(session_factory, **values):
    with session_factory() as session:
        note = Note(title="Solar panels", body="How do they work?", **values)
        session.add(note)
        session.commit()
        return note.id


def test_create_persists_before_background_task(client, test_database, monkeypatch):
    committed_statuses = []
    task_note_ids = []

    def record_commit(session):
        with test_database() as observer:
            committed_statuses.extend(observer.scalars(select(Note.status)).all())

    def inspect_background_note(note_id):
        with test_database() as session:
            note = session.get(Note, note_id)
            assert note.status == NoteStatus.researching
            assert note.body == "How do they work?"
            assert note.context == "For my roof"
            task_note_ids.append(note.id)

    event.listen(test_database, "after_commit", record_commit)
    monkeypatch.setattr(main, "research_note", inspect_background_note)
    response = client.post(
        "/notes",
        data={"title": " Solar panels ", "body": "How do they work?", "context": "For my roof"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert committed_statuses == [NoteStatus.saved, NoteStatus.researching]
    assert len(task_note_ids) == 1
    assert response.headers["location"] == f"/notes/{task_note_ids[0]}"
    with test_database() as session:
        note = session.get(Note, task_note_ids[0])
        assert note.title == "Solar panels"


def test_successful_research(test_database):
    note_id = save_note(test_database, context="For my roof")
    research.research_note(note_id)
    with test_database() as session:
        note = session.get(Note, note_id)
        assert note.status == NoteStatus.complete
        assert "Solar panels" in note.research_summary
        assert "How do they work?" in note.research_summary
        assert "For my roof" in note.research_summary
        sources = json.loads(note.sources_json)
        assert len(sources) == 3
        assert all(set(source) == {"title", "url", "snippet"} for source in sources)
        assert note.researched_at is not None
        assert note.error_message is None


def test_failed_research_preserves_note(test_database, monkeypatch):
    note_id = save_note(test_database, context="Keep this context")

    def fail_search(self, query):
        raise RuntimeError("Sample source lookup failed")

    monkeypatch.setattr(MockSearchProvider, "search", fail_search)
    research.research_note(note_id)
    with test_database() as session:
        note = session.get(Note, note_id)
        assert note.title == "Solar panels"
        assert note.body == "How do they work?"
        assert note.context == "Keep this context"
        assert note.status == NoteStatus.failed
        assert "Sample source lookup failed" in note.error_message
        assert note.researched_at is None


def test_post_runs_background_research_and_displays_result(client, test_database):
    response = client.post("/notes", data={"title": "Solar panels", "body": "How do they work?"})
    assert response.status_code == 200
    assert "Mock research for &#39;Solar panels&#39;" in response.text
    assert "Sample overview: Solar panels" in response.text
    assert 'href="https://example.com/overview?q=Solar+panels"' in response.text
    assert "Researched" in response.text
    assert 'http-equiv="refresh"' not in response.text
    with test_database() as session:
        assert session.scalar(select(Note)).status == NoteStatus.complete


def test_home_lists_newest_notes_first(client, test_database):
    first_id = save_note(test_database, created_at=datetime(2026, 1, 1))
    second_id = save_note(test_database, created_at=datetime(2026, 1, 1) + timedelta(days=1))
    response = client.get("/")
    assert response.status_code == 200
    assert "Save thought" in response.text
    assert "How do they work?" in response.text
    assert response.text.index(f'/notes/{second_id}') < response.text.index(f'/notes/{first_id}')
    assert "saved" in response.text
    assert "2026-01-02" in response.text


@pytest.mark.parametrize("data", [
    {},
    {"title": " ", "body": "Body"},
    {"title": "Title", "body": "\n "},
    {"title": "x" * 201, "body": "Body"},
])
def test_invalid_form_does_not_create_note(client, test_database, data):
    response = client.post("/notes", data=data)
    assert response.status_code == 422
    assert "Please check your thought" in response.text
    with test_database() as session:
        assert session.scalar(select(Note)) is None


@pytest.mark.parametrize("status,message,refresh", [
    (NoteStatus.saved, "Saved. Research will start shortly.", False),
    (NoteStatus.researching, "Researching your thought...", True),
    (NoteStatus.failed, "Research failed.", False),
])
def test_detail_status_states(client, test_database, status, message, refresh):
    note_id = save_note(test_database, status=status, error_message="Stored failure message")
    response = client.get(f"/notes/{note_id}")
    assert message in response.text
    assert ('http-equiv="refresh" content="2"' in response.text) == refresh
    if status == NoteStatus.failed:
        assert "Stored failure message" in response.text


def test_missing_note_returns_404(client):
    assert client.get("/notes/9999").status_code == 404


def test_mock_results_are_deterministic():
    provider = MockSearchProvider()
    assert provider.search("Solar panels") == provider.search("Solar panels")
    assert provider.search("Solar panels") != provider.search("Insulation")


def test_research_does_not_repeat_completed_work(test_database, monkeypatch):
    note_id = save_note(test_database)
    research.research_note(note_id)

    def unexpected_search(self, query):
        raise AssertionError("Completed notes should not be researched again")

    monkeypatch.setattr(MockSearchProvider, "search", unexpected_search)
    research.research_note(note_id)
    research.research_note(9999)
    with test_database() as session:
        assert session.get(Note, note_id).status == NoteStatus.complete


def test_note_text_is_escaped(client):
    response = client.post("/notes", data={"title": "<script>alert(1)</script>", "body": "<b>Body</b>"})
    assert "<script>alert(1)</script>" not in response.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in response.text
    assert "&lt;b&gt;Body&lt;/b&gt;" in response.text
