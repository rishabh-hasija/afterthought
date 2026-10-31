# Current State: Compact Research Controls

Completed on 2026-10-31. UI-only refinement; product behavior is unchanged.

- Completed research shows only circular-arrow and download SVG icon actions
  beside Research. Both have exact title/aria-label text, hover/keyboard tooltips,
  visible focus outlines and 44x44px targets. No icon library or visible labels.
- Refresh appears only while research is actively researching. Failed research
  retains its existing text retry button; completed research has no Refresh.
- Replaced radios with the compact Include earlier answers switch, default OFF.
  OFF submits research; ON submits conversation. JavaScript updates the helper
  and enables the matching successful form control. Error rendering preserves
  the selected mode. Space toggles the native checkbox switch; its description
  is associated through aria-describedby and its focus ring is visible.
- Helper text is Uses saved research only. / Includes earlier follow-ups.
  Usage text is now simply N of 4 follow-ups used. No panel or new functionality.
- Backend, database schema, limits, saved records, PDF contents, research services,
  sidebar and deletion are unchanged.

## Files Changed

- app/templates/note.html
- app/static/styles.css
- app/static/app.js
- tests/test_ui.py
- tests/test_followups.py
- docs/STATUS.md
- docs/HANDOFF.md

## Verification and Commands

- Read AGENTS.md, STATUS.md, HANDOFF.md and affected template/styles/script/tests.
  Initial working tree was clean on main.
- Baseline `rtk proxy .venv\Scripts\python -m pytest -q`: 90 passed.
  Final: 92 passed; same upstream Starlette/httpx warning. Updated state-specific
  Refresh coverage, added icon accessibility/default-switch markup checks, and
  updated the existing failure-retains-context test. Existing follow-up, PDF,
  research and deletion tests all pass without live APIs.
- `rtk proxy .venv\Scripts\python .venv/ui_preview.py`: temporary isolated SQLite
  database, mock follow-up answers and forced mock search. An initial attempt to
  launch this as a relative module failed; launched the script directly instead.
  Script was removed and server stopped after verification. No user database,
  credentials, Brave calls, Gemini calls or remaining real follow-up slot used.
- Browser submitted OFF and ON questions successfully: mock responses confirmed
  no history for OFF and one earlier follow-up for ON. Switch changed helper text
  both ways with Space. Research icon activated with Enter and completed mock
  research while retaining follow-ups. PDF icon activated with Enter and produced
  a download (prototype-review.pdf in the browser Downloads folder).
- At 375x812: icon targets were 44x44px, switch label target was 44px high,
  document width 360px excluding scrollbar, viewport 375px: no horizontal overflow.
  Reviewed form, helper, question and count with three saved follow-ups. At
  1280x900 verified secondary icon layout and keyboard PDF focus: solid outline,
  tooltip opacity 1 with Download PDF text. Reset viewport and closed preview tab.
- Previews outside repository:
  C:/Users/risha.RISHABH/.codex/visualizations/2026/10/31/01a1923b-7461-7912-8a42-7e03864e182b/refined-actions-desktop.png
  and refined-controls-mobile.png in the same directory.
- Inspected `rtk git diff -- ...`, `rtk git status --short` and
  `rtk git diff --check`. Used `rtk git fetch origin main` before push; remote
  had no divergent commits. The requested push includes the two preceding local
  checkpoints (footer cleanup and follow-ups/PDF export) plus this refinement.
- Commit message: Refine research actions and follow-up controls.
  Push target: origin/main. Check `git log -1 --oneline` for the hash.

## Known Problems and Exact Next Task

No new known problems. Existing Starlette/httpx warning and single-process
follow-up/research limitations still apply. Requested UI refinement is complete.
Next, only when requested, run the older-German-house-insulation final-demo review
with configured Brave/Gemma. The existing Gemma item still has one follow-up slot;
do not consume it during routine checks.

# Previous Checkpoint: Follow-ups and PDF Export

Completed on 2026-10-31. This section supersedes the historical next tasks below.

- Completed research supports up to four saved follow-ups, each with a trimmed,
  nonempty question of at most 500 characters. Research only is the default;
  conversation mode sends earlier questions/answers chronologically. The Gemma
  service receives original thought, optional context, structured saved research,
  saved sources and current question. Research-only prompts omit history entirely.
  Neither mode calls search. Gemma 4 remains the only AI model.
- Added FollowUp with a foreign key to Note, UTC creation time, stored context
  mode, ordered relationship and ORM delete cascade. create_all adds the table
  without replacing existing notes. Failures create no incomplete records and
  display a generic useful error without exposing SDK exceptions or credentials.
- One process-wide nonblocking lock covers follow-up validation, generation and
  commit. Overlapping follow-ups return 409. Deletion and research-again requests
  also return 409 during generation to prevent orphan/stale writes. Form submission
  disables the button while waiting; the server also guards requests across tabs.
- Added POST /notes/{note_id}/followups, GET /notes/{note_id}/export.pdf, and
  POST /notes/{note_id}/research. Research again uses the existing background
  pipeline, retains saved follow-ups and their four-question limit, and disallows
  duplicate pending research. Existing deletion confirmation remains required.
- Follow-up controls and document-style records appear before Sources. Research
  again, Download PDF and Refresh sit beside Research. Delete thought remains
  the only footer action; the sidebar remains primary navigation.
- PDF includes title, original thought, optional context, four research sections,
  all follow-ups, all source titles/full URLs and created/researched/exported UTC
  timestamps. Safe ASCII attachment filename; application/pdf response; escaped
  literal text, wrapping, multi-page splitting and page numbers. No database IDs,
  internal statuses or credentials are added to the document.
- ReportLab is the only new requirements.txt package. PDF embeds ReportLab's
  bundled Vera fonts plus an OFL-licensed Noto Emoji fallback because an existing
  source title contains a rocket. Font and license downloaded from
  https://raw.githubusercontent.com/google/fonts/main/ofl/notoemoji/.
  A focused TTFont subclass repairs ReportLab 4's astral-character CMap targets
  into UTF-16 surrogate pairs so emoji render and extract correctly.

## Files Changed in This Checkpoint

- app/main.py
- app/models.py
- app/services/gemma.py
- app/services/pdf_export.py (new)
- app/static/app.js
- app/static/styles.css
- app/static/fonts/NotoEmoji.ttf (new)
- app/static/fonts/OFL.txt (new)
- app/templates/note.html
- requirements.txt
- tests/test_followups.py (new)
- tests/test_pdf_export.py (new)
- docs/STATUS.md
- docs/HANDOFF.md

## Verification and Commands

- Read pasted task, AGENTS.md, RTK.md, STATUS.md, HANDOFF.md, current model,
  schema, database, routes, services, templates, styles, script and tests.
  Initial git status was clean. The initial instruction-reading command used
  PowerShell directly before RTK.md was read; subsequent shell commands use rtk.
- Baseline `rtk proxy .venv\Scripts\python -m pytest -q`: 64 passed.
  Final: 90 passed, one existing Starlette/httpx deprecation warning.
  New tests cover both modes, history omission/inclusion, chronological persistence,
  validation/boundaries, four-item limit, incomplete/missing notes, failures,
  escaping, concurrent follow-up/delete/research requests, cascade deletion,
  additive initialization, Gemma prompt/model, PDF content/headers/long content,
  safe filename, Unicode CMap, and research-again retention. Tests forbid live APIs.
  Two intermediate PDF literal-markup assertions failed because XML escaping
  produces adjacent PDF text runs; joined literal runs fixed the test correctly.
- `rtk proxy .venv\Scripts\python -m pip install "reportlab>=4,<5"` installed
  ReportLab 4.5.1 and its Pillow dependency into the project venv.
- `rtk proxy .venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1
  --port 8766` for browser review. Restarted after PDF font changes, stopped
  afterward. No Brave calls or new original-research requests in manual review.
- As explicitly requested, used the existing completed Gemma 4 research item and
  configured Gemini credentials for THREE live follow-ups. These are saved in the
  user's ignored local database: research, conversation, research modes in order.
  First question was the requested solo-developer prototype question; answer chose
  an offline study assistant from saved material. The requested second question
  explained that option using the earlier answer. Third question asked which
  hardware performance metrics to measure; answer gave TTFT, throughput, peak
  RAM/VRAM and stability from saved research. Refresh preserved all three in order.
  Exactly one follow-up slot remains. Credentials were never printed or changed.
- Browser verified default context, both selectors, submission, reload, document
  layout and Download PDF action. One browser snapshot timed out after the second
  submission; database and a fresh snapshot confirmed success, with no duplicate
  submission. Automated spies verify the exact history provided to Gemma.
- Downloaded a three-page PDF through the route. Used bundled pypdf for independent
  extraction: original thought, every saved follow-up question/answer and every
  source title/full URL match after normalizing wrapping whitespace. Rendered all
  three pages with bundled Poppler and inspected PNGs. Fixed the missing rocket
  glyph and invalid astral CMap discovered during this verification; re-rendered
  and re-extracted the corrected export successfully. Bundled pypdf/Poppler are
  verification tools only, not new project dependencies.
- Artifact-operation marker ran successfully before PDF creation. Export and
  screenshots are outside the repository under
  C:/Users/risha.RISHABH/.codex/visualizations/2026/10/31/01a1923b-7461-7912-8a42-7e03864e182b/.
  Files: gemma-4-for-local-ai-applications.pdf, research-page-1.png through
  research-page-3.png, afterthought-followups.png.
- Inspected `rtk git diff --stat`, `rtk git status --short` and source diff;
  `rtk git diff --check` passed. Committed locally, no push requested.
  The staged check found upstream trailing whitespace in the new font license;
  removed that whitespace and verified `rtk proxy git show --check` afterward.
- Read one DEV session-lifecycle article and its empty discussion through DevRelay;
  checked available challenge/event listings. No external publishing or messages.

## Known Problems and Limits

- Existing Starlette TestClient/httpx warning remains; all tests pass.
- Follow-up exclusion assumes the existing single-process server; do not run
  multiple Uvicorn workers without implementing shared exclusion first.
- Research-again keeps previous follow-ups even when the brief changes; the saved
  answers remain historical and are not recomputed or reset.
- Gemma grounding is prompt-based, not a deterministic fact validator. The three
  manual answers were consistent with saved material; this does not validate the
  factual accuracy of the older research itself.
- PDF fonts cover Latin research text and emoji; full CJK/other-script coverage
  is not implemented. In-process research tasks remain non-durable on restart.

## Exact Next Task

Both requested features are complete. Next, when the user requests it, perform
the existing final-demo review of the older-German-house-insulation use case with
configured Brave/Gemma, checking source links and factual grounding. Do not spend
the remaining follow-up slot on the existing Gemma item without a new request.

Checkpoint message: `Add saved research follow-ups and PDF export`.
Use `git log -1 --oneline` for its hash. No push requested.

# Historical UI Checkpoints

UI polish is complete. Afterthought has a shared product header, collapsible
thought navigation, responsive drawer, readable research sections, visible
Refresh action, and confirmed deletion. Existing Brave/Gemma research and
deterministic default mock mode remain intact. No dependency was added.

The product header is now sticky and contains only the menu toggle and brand.
Desktop navigation and the mobile drawer begin below the persistent header.
The home form now carries "Save the thought. Let AI research the rest."
The header tagline has been removed from every page.

The home page now ends with the new-thought form. The sidebar is the only
saved-thought browsing list; duplicate Recent thoughts cards are removed.

Research detail pages now end with only Delete thought. The redundant Back to
home link is removed; footer spacing is reduced and the action stays right aligned.

# Latest Follow-up: Simplify Research Footer

Completed on 2026-10-31:

- Removed Back to home without adding a replacement. Kept Delete thought.
- Simplified footer CSS to a single right-aligned action, reducing margin-top
  from 3rem to 2rem and padding-top from 1.5rem to 1rem.
- Files changed: app/templates/note.html, app/static/styles.css, docs/STATUS.md.
- Read AGENTS.md, STATUS.md, HANDOFF.md and affected template/styles.
  Initial working tree was clean.
- Baseline and final `rtk proxy .venv\Scripts\python -m pytest -q`: 64 passed,
  same upstream Starlette/httpx warning. Existing tests verify confirmation,
  deletion in every state, research removal, and redirection home.
- `rtk git diff --check`: passed. Inspected `rtk git diff --stat` and
  `rtk git status --short`; committed locally.
- Ran `rtk proxy .venv\Scripts\python .venv\ui_preview.py` with separate
  temporary SQLite database, mock mode, and one sample completed thought.
  At 1280x900 and 375x812, verified only Delete thought in footer. Desktop
  footer height was approximately 39px with 32px top margin. Mobile document
  width matched viewport width (360 CSS px). Delete thought opened its
  confirmation page, Keep thought returned to detail, and the mobile sidebar's
  + New thought opened the home form. No live APIs or user data touched.
- An optional final screenshot pass timed out in browser automation after
  these checks; recovering that tab also timed out. Viewport override was
  successfully reset. No screenshot artifact saved for this follow-up.
  Temporary browser tab remains unmarked and will close at turn end.
- Stopped preview server and removed temporary script. No new application
  issues found; existing limitations below remain. Exact next task remains
  the live final-demo review below, when requested/configured.

Checkpoint message: `Remove redundant home link from research footer`.
Use `git log -1 --oneline` for its hash. No push requested.

# Previous Follow-up: Remove Duplicate Home List

Completed on 2026-10-31:

- Removed the Recent thoughts heading, saved-thought cards, and their empty
  state from home. Preserved the product message, form, sticky header, and
  sidebar. Removed CSS used only by the deleted cards.
- Updated the existing home test to verify newest-first links appear once
  per thought and no duplicate heading, cards, or body snippets appear.
- Files changed: app/templates/index.html, app/static/styles.css,
  tests/test_notes.py, docs/STATUS.md.
- Read AGENTS.md, STATUS.md, HANDOFF.md, home template, and existing tests.
  Initial working tree was clean.
- Baseline and final `rtk proxy .venv\Scripts\python -m pytest -q`:
  64 passed, same upstream Starlette/httpx warning. `rtk git diff --check`
  passed. Inspected `rtk git status --short` and `rtk git diff --stat`.
- Ran `rtk proxy .venv\Scripts\python .venv\ui_preview.py` with an isolated
  temporary SQLite database, mock mode, and two sample notes. Checked home
  at 1280x900 and 375x812: main ends with FORM, no article cards; desktop
  sidebar lists both notes and opens the chosen detail page. Mobile form
  submission saved a third thought and completed mock research. Mobile
  drawer then listed all three newest first and opened another selected note.
  Mobile home document/viewport widths matched at 360 CSS px. Browser viewport
  reset, tab closed, preview server stopped, and temporary script removed.
  No user's notes/credentials were changed; no live APIs called.
- Desktop preview saved outside the repository:
  C:/Users/risha.RISHABH/.codex/visualizations/2026/10/31/01a19204-ce04-7543-b213-2be87a8c4e32/afterthought-home.png.
- No new known issues. Exact next task remains the live final-demo review
  below, when requested/configured.

Checkpoint message: `Remove duplicate thoughts list from home`.
Use `git log -1 --oneline` for its hash. No push requested.

# Previous Follow-up: Sticky Header and Home Message

Completed on 2026-10-31:

- Kept the header at its existing 4.5rem height, sticky at top: 0 with opaque
  white background and z-index above navigation/content.
- Shared --header-height between header, desktop sidebar, mobile drawer,
  backdrop, and scroll-padding. Sidebar scrolling is constrained to the space
  below the header; anchor targets clear the header as well.
- Removed the top-right tagline and its CSS. Placed the exact requested
  product message directly above the new-thought form on home only.
- Files changed in this follow-up: app/static/styles.css,
  app/templates/base.html, app/templates/index.html, docs/STATUS.md.
- Read AGENTS.md, STATUS.md, HANDOFF.md and affected templates/styles/script.
  Initial working tree was clean.
- Baseline and final `rtk proxy .venv\Scripts\python -m pytest -q`:
  64 passed, the same upstream Starlette/httpx warning.
- `rtk git diff --check`: passed. Inspected `rtk git status --short` and
  `rtk git diff --stat`; committed the checkpoint locally.
- Browser verification used `rtk proxy .venv\Scripts\python .venv\ui_preview.py`
  with a separate temporary SQLite database, mock mode, and a 30-item research
  brief. No user notes or credentials were read/changed; no live APIs called.
  Removed the preview script and stopped its server afterward.
- At 1280x900, after scrolling 1143 CSS px, header top remained 0, header bottom
  and sidebar top both remained 72px. Main content initially began at 72px.
  Header contained only the toggle and brand.
- At 375x812, scrolled research retained header top 0. Opening the drawer gave
  drawer top/header bottom 72px and drawer bottom 812px. Document/viewport
  widths matched (360 CSS px excluding scrollbar). Selecting New thought
  closed the drawer and its input anchor landed below the header (about 88px).
  Verified the exact home message and no message on the research page.
  Reset browser viewport and closed the temporary tab.
- Scrolled desktop preview saved outside the repo as
  C:/Users/risha.RISHABH/.codex/visualizations/2026/10/31/01a19204-ce04-7543-b213-2be87a8c4e32/afterthought-sticky-header.png.
- No new known issues. Existing limitations below remain. Exact next task
  remains the live final-demo review recorded below, when requested/configured.

Follow-up checkpoint message: `Keep product header visible and move home message`.
Use `git log -1 --oneline` for its hash. No push requested.

# Previous UI Polish Checkpoint

- Added a shared AFTERTHOUGHT header and sidebar on home, detail, validation,
  and delete confirmation pages. All saved thoughts appear newest first,
  including an ID tie-breaker, with titles and compact capitalized status.
  The open thought is highlighted and marked aria-current. Links open thoughts;
  + New thought opens the home form.
- Added a simple menu button, desktop collapse preference in localStorage
  (with storage-error fallback), and a phone drawer. Drawer supports close
  button, backdrop, Escape, focus containment/restoration, background inertness,
  and resize handling. Without JavaScript, navigation stays visible and usable.
  Uses 61 lines of vanilla JavaScript, no animation or frontend framework.
- Added visible Refresh links on every research state; researching pages retain
  their existing automatic two-second refresh. Refresh reloads stored results,
  without starting another research task.
- Added a delete confirmation page with required checkbox and Keep thought
  action. POST also requires a true confirmation value. Deleting removes the
  note, its summary, and saved sources together, then redirects home (303).
  Unknown IDs return 404; GET confirmation never deletes.
- Rendered Overview, Important findings, Next steps, and Uncertainties as HTML
  sections, with proper lists. A small presentation helper handles expected
  plain/Markdown headings, emphasis, backticks, links, bullet and numbered lines,
  legacy Sample findings, and Use Cases. Templates autoescape all model text;
  original saved summaries and source URLs are preserved. Missing sections say
  they were not provided rather than inventing findings. Gemma still returns
  one JSON summary string; prompt now explicitly requests headings on own lines.
- Refined typography, spacing, form, original-thought block, statuses, sources,
  empty/error states, and keyboard focus styles in calm green/neutral colors.
  Removed the obsolete blanket mock-mode message from the home page.
- Added 15 isolated test cases covering shared navigation order/current state,
  Refresh/status labels, sections/lists/escaping/legacy briefs, confirmation,
  deletion in every state, missing notes, keeping other notes, and deletion
  during active research without resurrection. No live API calls in tests.

# Files Changed

- app/main.py
- app/services/gemma.py
- app/services/presentation.py (new)
- app/static/app.js
- app/static/styles.css
- app/templates/base.html (new)
- app/templates/delete.html (new)
- app/templates/index.html
- app/templates/note.html
- tests/test_ui.py (new)
- docs/STATUS.md

# Verification and Commands Run

Verified on 2026-10-31 with Python 3.12. Shell commands used the required rtk
prefix after reading RTK.md; PowerShell builtins were run through
`rtk proxy powershell -NoProfile -Command`.

- Read RTK.md, AGENTS.md, STATUS.md, HANDOFF.md, source, existing tests,
  config, requirements, and ignore rules. Initial working tree was clean.
- `rtk proxy .venv\Scripts\python -m pytest -q`: baseline 49 passed;
  intermediate 63 passed; final 64 passed, one existing upstream warning.
- `rtk git status --short`, `rtk rg --files app tests`,
  `rtk git diff --stat`, `rtk git diff -- app/main.py app/services/gemma.py`,
  and `rtk git diff --check` for inspection and whitespace verification.
- `rtk proxy .venv\Scripts\python -c "import importlib.util; print('playwright', bool(importlib.util.find_spec('playwright')))"`:
  Python Playwright unavailable; no package installed. Node runtime import also
  failed; used the supported in-app browser instead.
- An initial `rtk proxy Get-Content` failed because Get-Content is a PowerShell
  builtin; corrected by invoking PowerShell through rtk proxy.
- `rtk proxy .venv\Scripts\python .venv\ui_preview.py`: temporary preview
  server on 127.0.0.1:8766, separate temporary SQLite DB and forced mock mode,
  with two disposable sample thoughts. Preview script was removed afterward
  and the server stopped. The user's database was not used or modified.
- In-app browser checks at default narrow size, 1280x900, and 375x812:
  home, note, and confirmation pages; desktop sidebar collapse/expand and
  persistence after reload; current item highlight; drawer open/close,
  Shift+Tab wrap, Escape and restored menu focus; thought selection;
  clean headings/lists; visible Refresh; confirmation and Keep thought.
  Phone DOM width equaled viewport width (360 CSS px after scrollbar).
  Viewport override reset and temporary browser tab closed afterward.
- Saved a full-page desktop preview outside the repository at
  C:/Users/risha.RISHABH/.codex/visualizations/2026/10/31/01a19204-ce04-7543-b213-2be87a8c4e32/afterthought-ui.png.
- Read Community Wisdom references on drawer focus management through
  DevRelay; both inspected discussions had no comments. No external content
  was posted and no live Brave/Gemini request was made.

# Known Issues

- Starlette TestClient emits the existing upstream httpx deprecation warning.
  All tests pass; the warning remains unsuppressed.
- Presentation supports the brief's small text convention rather than full
  Markdown. Existing unstructured briefs fall back to Overview; unavailable
  sections are marked as not provided. No schema/database migration is needed.
- Live Brave/Gemma output quality remains unverified in this checkpoint.
  The preceding checkpoint reported missing credentials; this task did not
  inspect or change credentials. Research still uses snippets, not full pages.
- Background tasks remain in-process and non-durable across restarts.

# Exact Next Task

With the user's configured Brave and Gemini credentials and SEARCH_PROVIDER=brave,
run a live end-to-end final-demo review using the older German house insulation
thought. Verify source links and the four rendered sections, and record actual
live success/failure without exposing credentials. No live request has been
made as part of this UI task.

# Checkpoint

Commit message: `Polish thought navigation and research presentation`.
Use `git log -1 --oneline` for this checkpoint's hash. Commit locally; no push
was requested.
