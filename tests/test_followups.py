import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from sqlalchemy import func, select

from app import database, main
from app.models import FollowUp, Note, NoteStatus, utc_now
from app.services import gemma
from tests.test_research import fake_gemma


@pytest.fixture
def completed(test_database):
    with test_database() as session:
        note = Note(title="Solo developer", body="Which prototype?", context="One weekend",
                    status=NoteStatus.complete, researched_at=utc_now(),
                    research_summary="Overview\nA small local tool.\nImportant findings\n- A CLI is simplest.\nNext steps\nBuild a CLI.\nUncertainties\nCost unknown.",
                    sources_json=json.dumps([{"title": "CLI guide", "url": "https://sources.test/cli", "snippet": "Start small."}]))
        session.add(note)
        session.commit()
        return note.id


@pytest.fixture
def answers(monkeypatch):
    calls = []

    def answer(**kwargs):
        calls.append(kwargs)
        return f"Saved answer {len(calls)}"

    monkeypatch.setattr(main, "answer_follow_up", answer)
    return calls


def ask(client, note_id, question="Which is easiest?", mode="research", **kwargs):
    return client.post(f"/notes/{note_id}/followups",
                       data={"question": question, "context_mode": mode}, **kwargs)


def test_followups_persist_in_order_and_context_is_explicit(client, test_database, completed, answers):
    first = ask(client, completed, "First question?", follow_redirects=False)
    assert first.status_code == 303
    assert answers[0]["previous_followups"] is None
    assert answers[0]["context"] == "One weekend"
    assert "Which prototype?" in answers[0]["thought"]
    assert "A CLI is simplest" in answers[0]["research_summary"]
    assert answers[0]["sources"][0]["url"] == "https://sources.test/cli"
    ask(client, completed, "Second question?", "conversation")
    assert answers[1]["previous_followups"] == [
        {"question": "First question?", "answer": "Saved answer 1"}]
    ask(client, completed, "Third question?", "research")
    assert answers[2]["previous_followups"] is None
    ask(client, completed, "Fourth question?", "conversation")
    assert len(answers[3]["previous_followups"]) == 3
    with test_database() as session:
        records = session.get(Note, completed).followups
        assert [f.context_mode for f in records] == ["research", "conversation", "research", "conversation"]
        assert all(f.created_at for f in records)
    page = client.get(f"/notes/{completed}").text
    assert page.index("First question?") < page.index("Second question?") < page.index("Third question?")
    assert page.index("Ask a follow-up") < page.index("First question?") < page.index('id="sources-title"')
    assert "You've reached the follow-up limit" in page
    assert 'id="followup-form"' not in page
    assert ask(client, completed).status_code == 422
    assert len(answers) == 4


@pytest.mark.parametrize("question,mode", [("", "research"), ("  ", "research"), ("x" * 501, "research"), ("Valid?", "invalid")])
def test_invalid_followup(client, completed, answers, question, mode):
    assert ask(client, completed, question, mode).status_code == 422
    assert answers == []


def test_question_boundary_and_escaping(client, completed, answers):
    assert ask(client, completed, "x" * 500).status_code == 200
    page = ask(client, completed, "<script>alert(1)</script>").text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page
    assert "<script>alert(1)</script>" not in page


@pytest.mark.parametrize("status", [NoteStatus.saved, NoteStatus.researching, NoteStatus.failed])
def test_incomplete_research(client, test_database, completed, answers, status):
    with test_database() as session:
        session.get(Note, completed).status = status
        session.commit()
    assert ask(client, completed).status_code == 422
    assert 'id="followup-form"' not in client.get(f"/notes/{completed}").text
    assert client.get(f"/notes/{completed}/export.pdf").status_code == 409
    assert not answers


def test_missing_note(client, answers):
    assert ask(client, 99999).status_code == 404
    assert client.get("/notes/99999/export.pdf").status_code == 404
    assert not answers


def test_failure_preserves_record_and_question(client, test_database, completed, answers, monkeypatch):
    ask(client, completed, "Keep this question")

    def fail(**kwargs):
        raise RuntimeError("secret-api-key")

    monkeypatch.setattr(main, "answer_follow_up", fail)
    response = ask(client, completed, "Retry this question", "conversation")
    assert response.status_code == 502
    assert "secret-api-key" not in response.text
    assert "Retry this question" in response.text
    assert 'value="conversation" checked' in response.text
    with test_database() as session:
        note = session.get(Note, completed)
        assert note.status == NoteStatus.complete
        assert "A small local tool." in note.research_summary
        assert "CLI guide" in note.sources_json
        assert len(note.followups) == 1
        assert note.followups[0].answer == "Saved answer 1"


def test_concurrent_requests_are_rejected_until_commit(client, test_database, completed, monkeypatch):
    entered, release = Event(), Event()

    def slow(**kwargs):
        entered.set()
        assert release.wait(10)
        return "Only one answer"

    monkeypatch.setattr(main, "answer_follow_up", slow)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(ask, client, completed)
        try:
            assert entered.wait(10)
            assert ask(client, completed).status_code == 409
            assert client.post(f"/notes/{completed}/research").status_code == 409
            assert client.post(f"/notes/{completed}/delete", data={"confirmed": "true"}).status_code == 409
        finally:
            release.set()
        assert pending.result().status_code == 200
    with test_database() as session:
        assert session.scalar(select(func.count()).select_from(FollowUp)) == 1


def test_delete_removes_followups(client, test_database, completed, answers):
    ask(client, completed)
    assert client.post(f"/notes/{completed}/delete", data={"confirmed": "true"}).status_code == 200
    with test_database() as session:
        assert session.get(Note, completed) is None
        assert session.scalars(select(FollowUp)).all() == []


def test_initialization_keeps_notes_and_adds_followups(test_database, completed):
    FollowUp.__table__.drop(database.engine)
    database.init_database()
    with test_database() as session:
        assert session.get(Note, completed).title == "Solo developer"
        assert session.scalars(select(FollowUp)).all() == []


@pytest.mark.parametrize("history", [None, [{"question": "Prior?", "answer": "Prior answer"}]])
def test_gemma_followup_prompt_and_model(monkeypatch, history):
    fake = fake_gemma(monkeypatch, " A concise answer. ")
    assert gemma.answer_follow_up("Thought", "Context", "Overview\nBrief", [], "Question?", history) == "A concise answer."
    kwargs = fake.models.generate_content.call_args.kwargs
    assert kwargs["model"] == "gemma-4-26b-a4b-it"
    prompt = kwargs["contents"]
    assert "The saved research does not contain enough information to answer this confidently." in prompt
    material = json.loads(prompt.split("\n", 1)[1])
    assert material["research"][0]["blocks"][0]["items"] == ["Brief"]
    assert ("previous_followups" in material) == (history is not None)
    if history:
        assert material["previous_followups"] == history


@pytest.mark.parametrize("text", [None, "", "  "])
def test_gemma_followup_rejects_empty(monkeypatch, text):
    fake_gemma(monkeypatch, text)
    with pytest.raises(ValueError, match="empty"):
        gemma.answer_follow_up("Thought", None, "Brief", [], "Question?")


def test_gemma_followup_failure_hides_credentials(monkeypatch):
    fake = fake_gemma(monkeypatch, "")
    fake.models.generate_content.side_effect = RuntimeError("test-secret")
    with pytest.raises(RuntimeError) as error:
        gemma.answer_follow_up("Thought", None, "Brief", [], "Question?")
    assert "test-secret" not in str(error.value)
    monkeypatch.setattr(gemma, "GEMINI_API_KEY", "")
    with pytest.raises(ValueError, match="Set GEMINI_API_KEY"):
        gemma.answer_follow_up("Thought", None, "Brief", [], "Question?")
