# Agent handoff

Only one coding agent should actively modify the project at a time.

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
