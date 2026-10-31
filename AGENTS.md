# Afterthought agent instructions

This is the authoritative shared instruction file for Codex and Claude Code.

## Goal and scope

Build a simple second-brain research tool: save a note immediately, research it
in the background, and attach a useful summary and source URLs for later reading.
The current slice creates and lists notes, runs deterministic local mock research
in a background task, and displays its summary and sample sources. Do not connect
live AI or web search until the user requests the next task.

## Architecture

Python 3.12, FastAPI, SQLite, SQLAlchemy, Jinja2, vanilla HTML/CSS/JavaScript,
Google GenAI SDK, Gemma 4 through the Gemini API, and pytest.
Routes call the database and research service. Research uses the SearchProvider
interface and the Gemma wrapper. Search returns title, URL, and snippet.
Gemma only summarizes note text, context, and search material; it does not access
the database or perform search. Gemma 4 is the only AI model.

The note flow is: commit the note as saved, mark it researching, start a
FastAPI background task, gather sources, summarize, store results, mark complete.
On failure, preserve the note, mark failed, and store a useful error message.
Each background task must open its own database session. These tasks run in the
web process and are not durable across a restart.

## Keep the scope small

Do not add authentication, user accounts, vector databases, embeddings, RAG or
agent frameworks, multi-agent systems, chat interfaces, external task queues,
Docker, complicated frontend frameworks, or unnecessary design patterns without
a clear reason and an explicit scope decision from the user.

## Coding rules

- Prefer readability over abstraction.
- Keep functions small and modules focused.
- Avoid duplicated logic and unnecessary classes.
- Use descriptive names and minimal dependencies.
- Comments explain why, rather than obvious code.
- Never put secrets in source control.
- Tests cover important behavior and avoid live API calls.
- Keep source URLs from search results rather than inventing them in summaries.
- Store timestamps in UTC; SQLite reads naive datetimes, interpreted as UTC.

## Before starting

1. Read AGENTS.md.
2. Read docs/STATUS.md.
3. Read docs/HANDOFF.md.
4. Run existing tests.

Only one coding agent actively modifies this project at a time.

## Before stopping

1. Run tests.
2. Update docs/STATUS.md.
3. Record exactly what was completed and the files changed.
4. Record known problems and commands run.
5. Record the exact next task.
6. Commit the checkpoint.
