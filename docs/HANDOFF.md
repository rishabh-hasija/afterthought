# Agent handoff

Only one coding agent should actively modify the project at a time.

Latest checkpoint refines completed research into SVG icon actions and a compact
Include earlier answers switch. Backend context modes remain research/conversation;
Refresh appears only during active research. This UI-only commit was requested
for origin/main. Read the TOP section of STATUS.md for verification and next task.

The preceding checkpoint adds saved follow-ups and PDF export. Read the TOP section of
STATUS.md; its next task supersedes the older UI checkpoint tasks. The local
Gemma research item now has three requested live follow-ups (research,
conversation, research); one slot remains. Do not consume it during routine tests.
Run the server with one process: follow-up exclusion currently uses an in-process
lock. Install requirements.txt, which now includes ReportLab. Font assets and
their license must remain available for PDF export.

## Incoming agent

1. Read AGENTS.md.
2. Read docs/STATUS.md.
3. Pull latest changes if needed, after checking for local changes.
4. Run `.venv\Scripts\python -m pytest -q`.
5. Continue from the exact Next Task in STATUS.md.

## Outgoing agent

1. Finish or stop at a clean checkpoint.
2. Run tests.
3. Update docs/STATUS.md.
4. Record completed work, current state, files changed, commands run, known
   issues, and the exact next task.
5. Commit changes.

Keep the next task specific enough that the incoming agent can begin without
reconstructing the previous conversation. Do not record secrets.
