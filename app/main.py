import json
from contextlib import asynccontextmanager, contextmanager
from threading import Lock
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import database
from app.config import PROJECT_ROOT
from app.models import FollowUp, Note, NoteStatus
from app.schemas import NoteCreate
from app.services.research import research_note
from app.services.presentation import research_sections
from app.services.gemma import answer_follow_up
from app.services.pdf_export import export_research, pdf_filename


# This application runs in one web process. Serialize follow-ups across tabs,
# including the count check and commit; reject overlapping mutations promptly.
followup_lock = Lock()


@contextmanager
def exclusive_note_action():
    if not followup_lock.acquire(blocking=False):
        raise HTTPException(409, "A follow-up is processing. Please wait and try again.")
    try:
        yield
    finally:
        followup_lock.release()


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_database()
    try:
        yield
    finally:
        database.engine.dispose()


app = FastAPI(title="Afterthought", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=PROJECT_ROOT / "app/static"), name="static")
templates = Jinja2Templates(directory=PROJECT_ROOT / "app/templates")
DatabaseSession = Annotated[Session, Depends(database.get_session)]


def saved_notes(session: Session):
    return session.scalars(
        select(Note).order_by(Note.created_at.desc(), Note.id.desc())
    ).all()


def home_response(
    request: Request,
    session: Session,
    values: dict[str, str] | None = None,
    errors: list[str] | None = None,
    status_code: int = 200,
):
    notes = saved_notes(session)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"notes": notes, "values": values or {}, "errors": errors or []},
        status_code=status_code,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request, session: DatabaseSession):
    return home_response(request, session)


@app.post("/notes")
def create_note(
    request: Request,
    background_tasks: BackgroundTasks,
    session: DatabaseSession,
    title: Annotated[str, Form()] = "",
    body: Annotated[str, Form()] = "",
    context: Annotated[str, Form()] = "",
):
    values = {"title": title, "body": body, "context": context}
    try:
        data = NoteCreate(**values)
    except ValidationError as exc:
        errors = [f"{error['loc'][0].capitalize()}: {error['msg']}" for error in exc.errors()]
        return home_response(
            request, session, values=values, errors=errors, status_code=422
        )

    note = Note(**data.model_dump(), status=NoteStatus.saved)
    session.add(note)
    session.commit()
    note.status = NoteStatus.researching
    session.commit()
    background_tasks.add_task(research_note, note.id)
    return RedirectResponse(url=f"/notes/{note.id}", status_code=303)


@app.get("/notes/{note_id}", response_class=HTMLResponse)
def note_detail(note_id: int, request: Request, session: DatabaseSession):
    note = session.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Thought not found")
    return note_response(note, request, session)


def note_response(note, request, session, error=None, status_code=200,
                  question="", context_mode="research"):
    sources = json.loads(note.sources_json)
    return templates.TemplateResponse(
        request=request, name="note.html", context={
            "note": note, "notes": saved_notes(session), "sources": sources,
            "sections": research_sections(note.research_summary or ""),
            "followups": note.followups, "followup_error": error,
            "question": question, "context_mode": context_mode,
        }, status_code=status_code,
    )


@app.post("/notes/{note_id}/followups")
def create_followup(
    note_id: int, request: Request, session: DatabaseSession,
    question: Annotated[str, Form()] = "",
    context_mode: Annotated[str, Form()] = "research",
):
    with exclusive_note_action():
        note = session.get(Note, note_id)
        if note is None:
            raise HTTPException(404, "Thought not found")
        question = question.strip()
        error = None
        if note.status != NoteStatus.complete:
            error = "Follow-ups are available only for completed research."
        elif not question or len(question) > 500:
            error = "Enter a question between 1 and 500 characters."
        elif context_mode not in ("research", "conversation"):
            error = "Choose a valid follow-up context."
        elif session.scalar(select(func.count()).select_from(FollowUp).where(
            FollowUp.note_id == note_id
        )) >= 4:
            error = "You've reached the follow-up limit for this research."
        if error:
            return note_response(note, request, session, error, 422, question, context_mode)
        history = None
        if context_mode == "conversation":
            history = [{"question": item.question, "answer": item.answer}
                       for item in note.followups]
        try:
            answer = answer_follow_up(
                thought=f"{note.title}\n\n{note.body}", context=note.context,
                research_summary=note.research_summary or "",
                sources=json.loads(note.sources_json), question=question,
                previous_followups=history,
            )
            if not answer or not answer.strip():
                raise ValueError("Empty answer")
        except Exception:
            # Never display SDK exceptions: they can contain credentials or payloads.
            return note_response(
                note, request, session,
                "Could not answer the follow-up. Check Gemini configuration, model access, "
                "quota, and service availability, then try again. Your research is saved.",
                502, question, context_mode,
            )
        session.add(FollowUp(note_id=note.id, question=question, answer=answer.strip(),
                             context_mode=context_mode))
        session.commit()
    return RedirectResponse(f"/notes/{note_id}", status_code=303)


@app.get("/notes/{note_id}/export.pdf")
def download_pdf(note_id: int, session: DatabaseSession):
    note = session.get(Note, note_id)
    if note is None:
        raise HTTPException(404, "Thought not found")
    if note.status != NoteStatus.complete:
        raise HTTPException(409, "PDF export is available only for completed research.")
    return Response(
        export_research(note, json.loads(note.sources_json)), media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{pdf_filename(note.title)}"'},
    )


@app.post("/notes/{note_id}/research")
def research_again(note_id: int, background_tasks: BackgroundTasks, session: DatabaseSession):
    with exclusive_note_action():
        note = session.get(Note, note_id)
        if note is None:
            raise HTTPException(404, "Thought not found")
        if note.status not in (NoteStatus.complete, NoteStatus.failed):
            raise HTTPException(409, "Research is already pending.")
        note.status = NoteStatus.researching
        note.error_message = None
        session.commit()
        background_tasks.add_task(research_note, note.id)
    return RedirectResponse(f"/notes/{note_id}", status_code=303)


@app.get("/notes/{note_id}/delete", response_class=HTMLResponse)
def confirm_delete(note_id: int, request: Request, session: DatabaseSession):
    note = session.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Thought not found")
    return templates.TemplateResponse(
        request=request, name="delete.html",
        context={"note": note, "notes": saved_notes(session)},
    )


@app.post("/notes/{note_id}/delete")
def delete_note(
    note_id: int, session: DatabaseSession,
    confirmed: Annotated[bool, Form()] = False,
):
    with exclusive_note_action():
        note = session.get(Note, note_id)
        if note is None:
            raise HTTPException(status_code=404, detail="Thought not found")
        if not confirmed:
            raise HTTPException(status_code=400, detail="Confirm deletion first")
        session.delete(note)
        session.commit()
    return RedirectResponse(url="/", status_code=303)
