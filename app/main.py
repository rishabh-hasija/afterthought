from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import PROJECT_ROOT
from app.database import engine, init_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    try:
        yield
    finally:
        engine.dispose()


app = FastAPI(title="Afterthought", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=PROJECT_ROOT / "app/static"), name="static")
templates = Jinja2Templates(directory=PROJECT_ROOT / "app/templates")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")
