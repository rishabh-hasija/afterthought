import json
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import database
from app.config import PROJECT_ROOT
from app.models import Note, NoteStatus
from app.schemas import NoteCreate
from app.services.research import research_note


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


def home_response(
    request: Request,
    session: Session,
    values: dict[str, str] | None = None,
    errors: list[str] | None = None,
    status_code: int = 200,
):
    notes = session.scalars(
        select(Note).order_by(Note.created_at.desc(), Note.id.desc())
    ).all()
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
    sources = json.loads(note.sources_json)
    return templates.TemplateResponse(
        request=request, name="note.html", context={"note": note, "sources": sources}
    )
