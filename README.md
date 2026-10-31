# Afterthought

Save the thought. Let AI research the rest.

You write something you want to remember or investigate. Afterthought saves it.
While you move on with your day, it researches the topic. When you come back,
the useful information is waiting beside your note.

**Current version:** save a thought with optional context, then open its research
and sources. Your thoughts appear newest first on the home page. Research uses
deterministic local mock results and three sample links; no AI or search API is
called yet.

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
                Web Search      Gemma 4
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
- **Web Search:** Supplies source material through a replaceable provider.
- **Gemma 4:** Turns the gathered information into a useful summary.
- **Research Result:** Contains the summary and source URLs saved with a note.

The local flow works today; web search and Gemma 4 will replace the mock results later.

## Project structure

```text
app/
  main.py, config.py       Web routes and settings
  database.py, models.py   SQLite connection and Note table
  schemas.py              Input and summary formats
  services/               Local mock research and unused Gemma wrapper
  search/                 Search interface and mock provider
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

Edit `.env`; keep it private. No API key is needed for the current local workflow.

| Variable | Purpose |
| --- | --- |
| `GEMINI_API_KEY` | Reserved for the Gemma wrapper; unused by mock research. |
| `SEARCH_PROVIDER` | Leave blank or set to `mock`; no other provider exists yet. |
| `SEARCH_API_KEY` | Reserved for a future search provider. |

Gemma 4 is the only AI model; the wrapper uses `gemma-4-26b-a4b-it`.

## Test

```powershell
.venv\Scripts\python -m pytest -q
```

See `docs/STATUS.md` for the exact next task. Licensed under MIT.
