# Current State

Real web research is implemented: save a thought, search with Brave, synthesize
the supplied source snippets with Gemma 4, and display the brief and original
source links. Default mock mode remains deterministic and requires no keys.

# Completed

- BraveSearchProvider implements SearchProvider using httpx, the standard web
  search endpoint, X-Subscription-Token, five results, and a 15-second timeout.
  It maps only title/URL/snippet, removes snippet markup, and reports missing
  credentials, HTTP/network errors, and malformed responses clearly.
- Provider selection supports mock and brave, with mock still the safe default.
  Brave mode never silently falls back to sample research.
- Deterministic query generation uses title, thought, and optional context:
  at most two queries, capped at 240 characters/40 words, with duplicate avoidance.
- Combined results retain the first occurrence of each normalized URL and at
  most eight useful sources. Stored URLs remain exactly those returned by search.
  No page scraping was added.
- Research opens its own database session, commits researching, requires useful
  sources, calls Gemma, and stores summary/source JSON/time/complete. Failures
  preserve the original note and commit failed with credential-safe messages.
- Gemma's only model remains gemma-4-26b-a4b-it. Its prompt asks for overview,
  findings, next steps, and uncertainties, grounded only in supplied material.
  It validates a small JSON summary, accepts a JSON fence, rejects blank or invalid
  output, and uses a 60-second request timeout. No database or search logic is
  present in the wrapper. Mock mode keeps local synthesis and title-only search.
- Removed the blanket mock disclaimer from completed note pages; actual mock
  summaries and sample sources still identify themselves. Existing visual style
  and status refresh behavior remain intact.
- Updated README and architecture, preserving the visual map and MIT license.
- Added isolated tests for query generation, duplicate avoidance, Brave request
  and response mapping, HTTP/network/malformed/empty results, URL normalization,
  combined sources, real-mode success and failures, Gemma model/prompt/validation,
  source rendering and refresh persistence, and secret redaction. No automated
  test makes a live Brave or Gemini call.

# Files Changed

- .env.example
- README.md
- app/schemas.py
- app/search/brave.py (new)
- app/search/provider.py
- app/search/queries.py (new)
- app/services/gemma.py
- app/services/research.py
- app/templates/note.html
- docs/ARCHITECTURE.md
- docs/STATUS.md
- tests/conftest.py
- tests/test_research.py (new)

# Verification

Verified on 2026-10-31 using Python 3.12. Shell commands used the required rtk
prefix (rtk proxy for Python commands).

- Baseline: `.venv\Scripts\python -m pytest -q`: 17 passed, one upstream warning.
- Final: `.venv\Scripts\python -m pytest -q`: 49 passed, one upstream warning.
- `.venv\Scripts\python -m pip check`: no broken requirements.
- `git diff --check`: passed.
- `.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8766`:
  application startup completed. urllib requests confirmed `/health` returned
  200 with status ok and `/` returned 200 with the Save thought form. Stopped
  the verification server afterward; no manual note was inserted.
- `.env` presence check reported both GEMINI_API_KEY and SEARCH_API_KEY absent
  or empty, without printing credentials. Live verification was skipped.
  Neither Brave nor Gemma was actually called live. The model call asserted by
  the mocked SDK test is exactly `gemma-4-26b-a4b-it`.
- Read repository instructions, status, handoff, source and tests; inspected
  Git status/diff/log/branch/remotes. Reviewed official Brave and Gemma API docs.
- Generated the requested insulation example queries locally:
  1. Home insulation for an older German house What insulation approaches are commonly recommended for older houses, and what problems should I watch for?
  2. Home insulation for an older German house I want practical options and risks rather than a general explanation.
- An initial credential-presence command had a shell quoting error and was
  corrected; no credential contents were printed.

# Known Issues

- Live API access and real output quality remain unverified because both keys
  are missing. Configure both keys and SEARCH_PROVIDER=brave, then restart and
  run the requested insulation note before the final demo.
- Briefs use search snippets only. Prompt constraints reduce unsupported claims
  but do not independently fact-check model output; no full-page extraction is
  included in this iteration.
- Background tasks run in the web process and are not durable. A restart can
  leave a note researching; retries/recovery remain outside this slice.
- Starlette TestClient emits its existing upstream httpx deprecation warning.
  Tests pass and the warning is not suppressed.

# Exact Next Task

Polish the research experience for the final demo: improve research output readability, loading/status feedback, empty/error states, and run a final end-to-end review.

This next task has not been started.

# Checkpoint

Commit message: `Connect real web research and Gemma 4`.
Destination: origin/main at https://github.com/rishabh-hasija/afterthought.git.
Use `git log -1 --oneline` for this checkpoint's hash.
