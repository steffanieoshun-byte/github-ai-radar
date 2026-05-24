# File Management Registry

This registry defines the expected responsibility of each committed path so the project stays GitHub-ready and easy to maintain.

## Product Docs

- `docs/prd-v0.1.md`: Product definition, constraints, scope, and UX decisions.
- `docs/acceptance-v0.1.md`: Acceptance scope, success boundary, failure boundary, and required verification.
- `docs/file-management.md`: This file. It registers file responsibilities and keeps future changes inside clear zones.

## Application

- `app/main.py`: FastAPI routes, startup initialization, form handling, and page rendering.
- `app/db.py`: SQLite schema, connection helpers, run/project/analysis persistence.
- `app/github_client.py`: GitHub API access through REST endpoints. No cloning.
- `app/analyzer.py`: `AgentAdapter`, `MockAnalyzer`, and optional LLM/Codex adapter boundary.
- `app/scanner.py`: Scan orchestration, search intent expansion, three-gate decision flow, dedupe, file budgets.
- `app/models.py`: Dataclasses and typed structures shared by scanner, analyzer, and templates.
- `app/templates/index.html`: English one-screen workspace UI.
- `app/static/styles.css`: UI styling for the local workspace.

## Local Data

- `data/.gitkeep`: Keeps the data folder in git.
- `data/radar.sqlite3`: Local runtime database. Must not be committed.

## GitHub Publishing

- `README.md`: English public project overview and run instructions.
- `LICENSE`: Project license.
- `.gitignore`: Keeps local data, keys, caches, and virtual environments out of git.
- `.env.example`: Safe environment variable template only.
- `requirements.txt`: Runtime and test dependencies.
- `start_radar.bat`: Windows local startup helper.

## Tests

- `tests/test_analyzer.py`: Analyzer and scoring behavior.
- `tests/test_db.py`: SQLite persistence and non-overwrite history.
- `tests/test_scanner.py`: Search intent, file budget, pass/dedupe behavior with mocked GitHub data.

## Prototypes

- `prototypes/prototype-v0.1.html`: Static UI prototype used for design review. It is not the production UI.

## Boundaries

- Do not commit `.env`, `data/radar.sqlite3`, caches, virtual environments, or temporary screenshots.
- Do not add unrelated experiments at repo root.
- Put future product docs under `docs/`.
- Put runtime code under `app/`.
- Put verification code under `tests/`.
