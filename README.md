# Afterthought

Save the thought. Let AI research the rest.

You write something you want to remember or investigate. Afterthought saves it.
While you move on with your day, it researches the topic. When you come back,
the useful information is waiting beside your note.

**Current version:** save a thought with optional context, then open its research
and sources. Your thoughts appear newest first on the home page. Choose Brave
Search and Gemma 4 for real web research, or use the default local mock mode
without API keys.

## Architecture map

```text
User
  |
  v
Web Page
  |
  v
FastAPI
  |
  +------------------+
  |                  |
  v                  v
SQLite            Research Service
                     |
                     +-------------+
                     |             |
                     v             v
               Brave Search     Gemma 4
                     |             |
                     +------v------+
                            |
                            v
                     Research Result
                            |
                            v
                          SQLite
```

- **User:** Writes and reads thoughts.
- **Web Page:** Shows notes and research results.
- **FastAPI:** Connects the page, database, and research system.
- **SQLite:** Stores thoughts and research results.
- **Research Service:** Coordinates the research process.
- **Brave Search:** Finds current information from the web.
- **Gemma 4:** Turns the gathered information into a useful research brief.
- **Research Result:** Contains the summary and source URLs saved with a note.

The research service generates up to two focused queries, gathers up to eight
unique sources, and sends their titles and snippets to Gemma. Source pages are
not scraped; links come directly from search results. Background tasks run in
the web process and do not survive a restart.

## Project structure

```text
app/
  main.py, config.py       Web routes and settings
  database.py, models.py   SQLite connection and Note table
  schemas.py              Input and summary formats
  services/               Research pipeline and Gemma wrapper
  search/                 Query generation, Brave and mock providers
  templates/, static/     Simple web pages, CSS, and JavaScript
tests/                    Automated checks
docs/                     Architecture, current state, and handoff
AGENTS.md, CLAUDE.md       Instructions for coding agents
```

## Setup and run

Use Python 3.12. From the project directory on Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
.venv\Scripts\python -m uvicorn app.main:app --reload
```

On macOS or Linux, use `python3.12` to create the environment,
`.venv/bin/python` for the commands above, and `cp .env.example .env`.

Open [the home page](http://127.0.0.1:8000).
The app creates `afterthought.db` in the project directory when it starts.

## Environment variables

Edit `.env`; keep it private. For real research, set `SEARCH_PROVIDER=brave`
and supply both API keys, then restart the app. Leave the provider as `mock`
for deterministic sample research without network calls. Brave failures are
displayed on the saved note; they never silently switch to mock results.

| Variable | Purpose |
| --- | --- |
| `GEMINI_API_KEY` | Gemini API key for Gemma synthesis; unused in mock mode. |
| `SEARCH_PROVIDER` | `mock` (default) or `brave`. |
| `SEARCH_API_KEY` | Brave Search API key; required in Brave mode. |

Gemma 4 is the only AI model; the wrapper uses `gemma-4-26b-a4b-it`.

## Test

```powershell
.venv\Scripts\python -m pytest -q
```

See `docs/STATUS.md` for the exact next task. Licensed under MIT.
