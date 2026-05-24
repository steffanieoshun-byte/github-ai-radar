# GitHub AI Radar

GitHub AI Radar is a local web app for finding AI project inspiration on GitHub.

It is not a ranking site, benchmark, or crawler. It searches GitHub, reads lightweight repository evidence, decides what is worth deeper analysis, stores every run in SQLite, and shows a local inspiration library with scores and evidence.

## What It Looks For

- AI application and agent patterns
- Automation and workflow ideas
- AI governance, eval, guardrail, audit, and failure-handling patterns
- Knowledge, prompt, template, and example-heavy repositories
- Small experiments that can be replicated locally

Stars are background context only. The core question is whether a project can become a useful inspiration source.

## Tech Stack

- Python
- FastAPI
- SQLite
- Jinja2
- requests
- python-dotenv

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Optional `.env` values:

```text
GITHUB_TOKEN=
OPENAI_API_KEY=
CODEX_API_KEY=
ANALYZER_MODE=mock
DATABASE_PATH=data/radar.sqlite3
```

`GITHUB_TOKEN` is recommended for the GitHub API rate limit. OpenAI/Codex keys are not required for v0.1 because `MockAnalyzer` runs the full local loop.

## Run

```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000/
```

On Windows, you can also run:

```powershell
.\start_radar.bat
```

## Use

1. Enter a keyword such as `ai agent`.
2. Set a scan count such as `10`.
3. Choose `quick`, `standard`, or `deep`.
4. Click `Start Scan`.
5. Review the local inspiration library, scores, evidence files, and replicable experiment ideas.

## Scan Modes

- `quick`: metadata, README, tree, and up to 2 key files per relevant repository.
- `standard`: metadata, README, tree, and up to 8 key files.
- `deep`: metadata, README, tree, and up to 20 key files.

The app uses the GitHub API tree endpoint. It does not clone repositories.

## Data

Runtime data is stored locally in SQLite:

```text
data/radar.sqlite3
```

The database is ignored by git.

## Current Limits

- v0.1 runs scans synchronously.
- The default analyzer is rule-based mock analysis.
- The Codex/OpenAI analyzer boundary is reserved but not implemented.
- No cloud deployment, user accounts, or background job queue.
- Filtered-out projects are stored for dedupe, but no separate review UI is exposed in v0.1.

## Verification

```powershell
.\.venv\Scripts\python -m pytest -q
```

The acceptance standard is registered in:

```text
docs/acceptance-v0.1.md
```
