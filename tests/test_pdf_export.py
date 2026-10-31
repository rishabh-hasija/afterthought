import base64
import re
import zlib
from datetime import datetime, timezone
import json

from app.models import Note
from app.services.pdf_export import pdf_filename
from tests.test_followups import answers, ask, completed


def decoded_streams(pdf, include_fonts=False):
    """Decode PDF page streams without adding a PDF reader dependency to the app."""
    streams = []
    for match in re.finditer(rb"<<(.*?)>>\s*stream\r?\n(.*?)endstream", pdf, re.S):
        header, stream = match.groups()
        if b"/ASCII85Decode" in header:
            stream = base64.a85decode(stream.strip().removesuffix(b"~>"))
        if b"/FlateDecode" in header:
            stream = zlib.decompress(stream)
        if include_fonts or b"BT" in stream:
            streams.append(stream)
    return streams


def page_streams(pdf, include_fonts=False):
    return b"\n".join(decoded_streams(pdf, include_fonts))


def test_pdf_without_followups(client, completed):
    response = client.get(f"/notes/{completed}/export.pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == 'attachment; filename="solo-developer.pdf"'
    assert response.content.startswith(b"%PDF-")
    text = page_streams(response.content)
    for value in [b"AFTERTHOUGHT", b"Solo developer", b"Which prototype?", b"One weekend",
                  b"Research", b"Overview", b"A small local tool.", b"A CLI is simplest.",
                  b"Build a CLI.", b"Cost unknown.", b"CLI guide", b"https://sources.test/cli",
                  b"Created:", b"Research completed:", b"sources.test"]:
        assert value in text
    assert b"Follow-up discussion" not in text
    assert b"UTC" not in text and b"Exported" not in text
    assert b"note_id" not in text
    assert b"/URI (https://sources.test/cli)" in response.content


def test_pdf_dates_are_human_readable(client, test_database, completed):
    with test_database() as session:
        note = session.get(Note, completed)
        note.created_at = datetime(2026, 10, 31, 12, 39, 4, tzinfo=timezone.utc)
        note.researched_at = datetime(2026, 10, 31, 12, 39, 50, tzinfo=timezone.utc)
        session.commit()
    text = page_streams(client.get(f"/notes/{completed}/export.pdf").content)
    assert b"Created: October 31, 2026" in text
    assert b"Research completed: October 31, 2026" in text
    for removed in (b"UTC", b"Exported", b"12:39", b"2026-10-31"):
        assert removed not in text


def test_pdf_source_titles_link_to_exact_saved_urls(client, test_database, completed):
    url = 'https://sources.test/full/path?first=1&second=2#detail'
    with test_database() as session:
        session.get(Note, completed).sources_json = json.dumps([
            {"title": "A source & its evidence", "url": url},
            {"title": "Unsafe link", "url": "javascript:alert(1)"},
        ])
        session.commit()
    pdf = client.get(f"/notes/{completed}/export.pdf").content
    text = page_streams(pdf)
    assert b"1. A source" in text
    assert b"sources.test" in text
    assert f"/URI ({url})".encode() in pdf
    assert b"/URI (javascript:" not in pdf


def test_pdf_long_followup_question_and_answer(client, completed, answers, monkeypatch):
    monkeypatch.setattr('app.main.answer_follow_up', lambda **kwargs: "A practical answer. " * 600)
    ask(client, completed, "A long question with wrapping. " * 16)
    response = client.get(f"/notes/{completed}/export.pdf")
    assert response.status_code == 200
    assert len(re.findall(rb"/Type /Page\b", response.content)) > 2
    text = page_streams(response.content)
    assert b"Question" in text and b"Answer" in text and b"A practical answer." in text
    assert any(b"A long question with wrapping." in page and b"A practical answer." in page
               for page in decoded_streams(response.content))


def test_pdf_includes_discussion_in_order(client, completed, answers):
    ask(client, completed, "First question?")
    ask(client, completed, "Second question?", "conversation")
    text = page_streams(client.get(f"/notes/{completed}/export.pdf").content)
    assert b"Follow-up discussion" in text
    assert b"Follow-up 1" in text and b"Follow-up 2" in text
    assert text.index(b"First question?") < text.index(b"Saved answer 1") < text.index(b"Second question?") < text.index(b"Saved answer 2") < text.index(b"Sources")


def test_pdf_long_content_and_safe_markup(client, test_database, completed):
    with test_database() as session:
        note = session.get(Note, completed)
        note.body = "<b>Original & unchanged</b> " + "Long paragraph. " * 1200
        note.research_summary += "\n" + "- A finding that wraps over lines. " * 400
        note.sources_json = '[{"title":"Source <test>","url":"https://sources.test/' + 'a' * 2000 + '"}]'
        session.commit()
    response = client.get(f"/notes/{completed}/export.pdf")
    assert response.status_code == 200
    assert len(re.findall(rb"/Type /Page\b", response.content)) > 2
    text = page_streams(response.content)
    # PDF stores escaped XML as adjacent text runs; join the literal strings.
    literals = b"".join(re.findall(rb"\(((?:\\.|[^\\)])*)\)\s*Tj", text))
    assert b"<b>Original & unchanged</b>" in literals
    assert b"Source <test>" in literals


def test_safe_pdf_filename():
    assert pdf_filename('Gemma 4 for local AI applications') == 'gemma-4-for-local-ai-applications.pdf'
    assert pdf_filename('../Title"\r\nInjected: ä') == 'title-injected-a.pdf'
    assert pdf_filename('???') == 'afterthought-research.pdf'
    assert len(pdf_filename('x' * 300)) == 104


def test_pdf_emoji_has_valid_unicode_mapping(client, test_database, completed):
    with test_database() as session:
        session.get(Note, completed).title = "A prototype 🚀"
        session.commit()
    pdf = client.get(f"/notes/{completed}/export.pdf").content
    assert b"<D83DDE80>" in page_streams(pdf, include_fonts=True)


def test_research_again_keeps_followups(client, test_database, completed, answers):
    ask(client, completed)
    response = client.post(f"/notes/{completed}/research")
    assert response.status_code == 200
    with test_database() as session:
        note = session.get(Note, completed)
        assert note.status.value == 'complete'
        assert len(note.followups) == 1
