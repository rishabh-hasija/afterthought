# Architecture

- **UI:** Jinja2 templates with plain HTML, CSS, and JavaScript. The home page
  works; the note template is a placeholder without a route.
- **API:** FastAPI serves `/` and `/health`. Its lifespan creates database tables
  at startup and disposes the engine on shutdown. `POST /notes` is not built yet.
- **Database:** SQLAlchemy connects to a project-local SQLite file. The Note table
  stores text, context, status, summary, source JSON, errors, and UTC timestamps.
- **Research service:** The reserved `research_note` entry point accepts a note ID
  and SearchProvider. It currently raises NotImplementedError. The next slice
  will give it its own database session and connect the background workflow.
- **Search provider:** A small interface returns title, URL, and snippet. The
  provider factory currently supports only a mock returning an empty list.
- **Gemma service:** A standalone wrapper uses Google GenAI and only Gemma 4.
  It sends note text, context, and supplied results, then validates a JSON summary.
  It has no database or search logic and is not called by current routes.

The intended call direction is UI -> API -> database / research service.
Research calls search first, then Gemma, then saves the summary and original
source URLs to SQLite. Search is replaceable without changing the Gemma service.
The first slice will use mocked research before connecting live API calls.

FastAPI background tasks run in the web process. A restart can interrupt them;
durable job handling and recovery are outside this foundation.
