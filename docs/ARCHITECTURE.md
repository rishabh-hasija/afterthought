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
  interface. In Brave mode it generates at most two deterministic queries (240
  characters and 40 words each), combines five results per query, and retains at
  most eight useful sources in search order. URL comparison normalizes host case,
  default ports, trailing slashes, query order, fragments, and tracking parameters;
  stored URLs remain the originals. Gemma summarizes supplied titles and snippets.
  Mock mode retains title-only sample search and deterministic local synthesis.
  The service stores
  summary, source JSON, and researched time, then commits complete. On exceptions
  it rolls back, reloads the original note, and commits failed with an error.
- **Search provider:** A small interface returns title, URL, and snippet. The
  provider factory supports `mock` (the safe default) and `brave`. Mock returns
  three query-based sample sources and labels its summary as mock research.
  Brave calls the standard web search endpoint with a 15-second timeout and
  maps titles, URLs, and descriptions; it never accesses the database or scrapes
  pages. Missing keys, HTTP/network errors, and malformed responses fail clearly.
  No useful sources also fails; there is no automatic mock fallback.
- **Gemma service:** A standalone wrapper uses Google GenAI and only Gemma 4.
  It sends note text, context, and supplied results, then validates a JSON summary.
  The brief asks for overview, findings, next steps, and uncertainties using only
  supplied material. The schema remains one nonempty summary string; URLs are
  controlled separately by the application. Requests time out after 60 seconds;
  SDK errors are replaced with credential-safe messages. It has no database or
  search logic and is not called in mock mode.

The current call direction is UI -> API -> database / research service.
Research calls search, synthesizes a brief, and saves results to SQLite.
Source URLs remain stored separately from summary text. Automated tests replace
both external service boundaries and use temporary SQLite databases.

FastAPI background tasks run in the web process. A restart can interrupt them;
durable job handling and recovery are outside the current scope.
