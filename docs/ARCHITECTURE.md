# Architecture

- **UI:** Jinja2 templates with plain HTML and CSS. The home page has a creation
  form and newest-first list. Note pages display text, status, summary, and sources.
  Only researching pages refresh, using a two-second HTML meta refresh.
- **API:** FastAPI serves `/`, `/health`, `POST /notes`, and `/notes/{note_id}`.
  Input is checked with NoteCreate; invalid forms retain entered values. The API
  commits saved and researching states before scheduling research by note ID,
  then returns a 303 redirect. Its lifespan creates tables and disposes the engine.
- **Database:** SQLAlchemy connects to a project-local SQLite file. The Note table
  stores text, context, status, summary, source JSON, errors, and UTC timestamps.
- **Research service:** `research_note(note_id)` opens its own database session,
  loads the note, and uses the provider factory through the SearchProvider
  interface. It creates a deterministic summary from the note and results, stores
  summary, source JSON, and researched time, then commits complete. On exceptions
  it rolls back, reloads the original note, and commits failed with an error.
- **Search provider:** A small interface returns title, URL, and snippet. The
  provider factory supports only a local mock returning three query-based sample
  sources. These example.com links are clearly labelled mock data in the UI.
- **Gemma service:** A standalone wrapper uses Google GenAI and only Gemma 4.
  It sends note text, context, and supplied results, then validates a JSON summary.
  It has no database or search logic and is not called by the local workflow.

The current call direction is UI -> API -> database / research service.
Research calls mock search, creates a mock summary, and saves results to SQLite.
The next pipeline will replace the mock summary with Gemma and connect a real
search provider. Source URLs remain stored separately from summary text.

FastAPI background tasks run in the web process. A restart can interrupt them;
durable job handling and recovery are outside the current scope.
