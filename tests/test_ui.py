import json
from datetime import datetime
from html.parser import HTMLParser

import pytest

from app.models import Note, NoteStatus
from app.services import research
from app.services.presentation import research_sections
from tests.test_notes import save_note


class SidebarLinks(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.links = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and "sidebar-note" in attrs.get("class", ""):
            self.links.append(attrs)


def test_shared_sidebar_order_current_and_product_header(client, test_database):
    older = save_note(test_database, created_at=datetime(2026, 1, 1), status=NoteStatus.complete)
    newer = save_note(test_database, created_at=datetime(2026, 1, 2), status=NoteStatus.researching)
    for path in ("/", f"/notes/{older}"):
        html = client.get(path).text
        assert "AFTERTHOUGHT" in html
        assert "+ New thought" in html
        assert 'aria-controls="thought-sidebar"' in html
        assert '/static/app.js' in html
        links = SidebarLinks(html).links
        assert [link["href"].split("/")[-1] for link in links] == [str(newer), str(older)]
        assert 'aria-current' not in links[0]
        assert links[1].get("aria-current") == ("page" if path != "/" else None)
        assert ">Researching</span>" in html
        assert ">Complete</span>" in html


@pytest.mark.parametrize("status", list(NoteStatus))
def test_refresh_is_visible_for_every_research_state(client, test_database, status):
    note_id = save_note(test_database, status=status)
    html = client.get(f"/notes/{note_id}").text
    assert f'href="http://testserver/notes/{note_id}">Refresh</a>' in html
    assert f'>{status.value.capitalize()}</span>' in html


def test_brief_sections_lists_and_escaping(client, test_database):
    note_id = save_note(
        test_database, status=NoteStatus.complete,
        research_summary=(
            "## **Overview**\nA **useful** brief.\n\n"
            "**Use Cases**\n- **First** finding\n* Second finding\n"
            "### Next steps:\n1. Check `details`\n2) Ask an expert\n"
            "__Uncertainties__\n<script>alert(1)</script>\n"
        ),
        sources_json=json.dumps([{"title": "Original source", "url": "https://example.org/original"}]),
    )
    html = client.get(f"/notes/{note_id}").text
    for title in ("Overview", "Important findings", "Next steps", "Uncertainties"):
        assert f'>{title}</h3>' in html
    assert "<li>First finding</li><li>Second finding</li>" in html
    assert "<li>Check details</li><li>Ask an expert</li>" in html
    assert "**" not in html and "__Uncertainties__" not in html
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert 'href="https://example.org/original"' in html
    with test_database() as session:
        assert "**Overview**" in session.get(Note, note_id).research_summary


def test_legacy_brief_and_missing_sections_preserve_text():
    sections = research_sections("A legacy brief.\n\nSample findings:\nSome evidence.")
    assert sections[0]["blocks"] == [{"kind": "paragraph", "items": ["A legacy brief."]}]
    assert sections[1]["blocks"] == [{"kind": "paragraph", "items": ["Some evidence."]}]
    assert sections[2]["blocks"] == sections[3]["blocks"] == []


def test_additional_markdown_markers_become_plain_text():
    sections = research_sections("### **Benefits**\n_Useful_ [reading](https://example.org).\n---")
    assert sections[0]["blocks"] == [
        {"kind": "paragraph", "items": ["Benefits"]},
        {"kind": "paragraph", "items": ["Useful reading."]},
    ]


def test_delete_confirmation_does_not_modify_note(client, test_database):
    note_id = save_note(test_database, research_summary="Keep research", sources_json='[{"url":"https://example.org"}]')
    html = client.get(f"/notes/{note_id}/delete").text
    assert "Delete this thought?" in html and "Keep thought" in html
    assert 'name="confirmed" value="true" required' in html
    for data in ({}, {"confirmed": "false"}):
        assert client.post(f"/notes/{note_id}/delete", data=data).status_code == 400
    with test_database() as session:
        assert session.get(Note, note_id).research_summary == "Keep research"


@pytest.mark.parametrize("status", list(NoteStatus))
def test_confirmed_delete_removes_note_and_research_redirects_home(client, test_database, status):
    note_id = save_note(test_database, status=status, research_summary="Research to delete", sources_json='[{"url":"https://example.org"}]')
    other_id = save_note(test_database)
    response = client.post(f"/notes/{note_id}/delete", data={"confirmed": "true"}, follow_redirects=False)
    assert response.status_code == 303 and response.headers["location"] == "/"
    assert client.get(f"/notes/{note_id}").status_code == 404
    assert client.get("/").status_code == 200
    with test_database() as session:
        assert session.get(Note, note_id) is None
        assert session.get(Note, other_id) is not None


def test_delete_missing_thought(client):
    assert client.get("/notes/999/delete").status_code == 404
    assert client.post("/notes/999/delete", data={"confirmed": "true"}).status_code == 404


def test_deleting_during_research_does_not_recreate_note(client, test_database, monkeypatch):
    note_id = save_note(test_database)

    def delete_while_searching(self, query):
        response = client.post(f"/notes/{note_id}/delete", data={"confirmed": "true"})
        assert response.status_code == 200
        return []

    monkeypatch.setattr(research.MockSearchProvider, "search", delete_while_searching)
    research.research_note(note_id)
    with test_database() as session:
        assert session.get(Note, note_id) is None
