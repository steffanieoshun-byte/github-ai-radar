# GitHub AI Radar v0.1 Acceptance Standard

## Scope

v0.1 is accepted only if it runs as a local, English-language web app that can scan GitHub repositories, preserve local history, and show inspiration-focused project intelligence.

The user-facing product is one workspace:

- Left side: inspiration library, scan entry, filters, historical project list.
- Right side: selected project score summary and detailed intelligence card.

Scanning internals, pass decisions, file selection, and request logs are backend evidence. They are not primary UI surfaces in v0.1.

## Must Pass

- The repository is ready to publish on GitHub with `README.md`, `LICENSE`, `.gitignore`, `.env.example`, `requirements.txt`, app code, tests, and docs.
- All user-facing UI copy is English.
- The app starts locally with `uvicorn app.main:app --reload`.
- `start_radar.bat` starts the app and opens the local browser.
- The homepage loads at `/`.
- The homepage shows an inspiration library, a new scan action, project scores, and project detail.
- A scan form accepts `keyword`, `scan_count`, `scan_mode`, and optional `scan_title`.
- `quick`, `standard`, and `deep` modes have different file-read budgets.
- GitHub token is read only from `.env` or environment variables.
- No real API keys are committed.
- Without OpenAI/Codex keys, `MockAnalyzer` runs the full loop.
- Each scan creates a `runs` row in SQLite.
- Each discovered repository creates or updates a `projects` row.
- Each analyzed or passed repository creates a `project_analyses` row.
- PASS decisions are stored with `pass_stage` and `pass_reason`.
- Duplicate repositories are not overwritten; new analyses are appended.
- If a repo has not changed and intent is similar, prior judgment can be reused.
- The UI does not expose a separate PASS library page.
- The UI does not expose an admin/backend page.
- Reserved backend routes or functions may exist for future PASS review.
- Errors are recorded in the run and shown in a user-readable way.
- Automated tests pass.

## Self-Test Commands

Run these before asking for human acceptance:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Manual/browser checks:

- Open `http://127.0.0.1:8765/`.
- Confirm English UI.
- Confirm the inspiration library layout.
- Run `keyword=ai agent`, `scan_count=3`, `scan_mode=quick`.
- Confirm SQLite data is written under `data/radar.sqlite3`.
- Confirm a project row can be selected and its score/detail appears.
- Confirm no PASS/admin navigation is visible.

## Success Boundary

The release is successful if the app can complete one local scan loop and persist the results, even when analysis uses `MockAnalyzer`.

GitHub API rate limits, no optional OpenAI/Codex key, or weak GitHub search results do not fail v0.1 if the app records the status clearly and the mock loop works.

## Failure Boundary

Mark the release as failed if any of these happen:

- The app cannot start locally.
- The homepage does not load.
- A scan crashes the app process.
- SQLite is not created or written.
- The UI is not English.
- API keys are hardcoded or committed.
- PASS decisions are not persisted.
- Duplicate analyses overwrite prior history.
- Tests fail after implementation.
- The app exposes a PASS library or admin page as a visible v0.1 navigation item.

## Deferred

- Packaged `.exe`.
- Cloud deployment.
- User accounts.
- Background job queue.
- Full PASS library UI.
- Admin dashboard.
- LangChain orchestration.
- Large-scale crawling.
- Repository cloning.
