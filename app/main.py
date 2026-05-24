from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import db
from .github_client import GitHubClient
from .models import RepoMetadata
from .scanner import RadarScanner, make_intent


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="GitHub AI Radar", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.on_event("startup")
def startup() -> None:
    with db.connection() as conn:
        db.init_db(conn)


def _score_width(value: Any) -> int:
    try:
        return max(0, min(100, int(value) * 20))
    except Exception:
        return 0


def _library_item(row: Any) -> dict[str, Any]:
    analysis = json.loads(row["analysis_json"])
    scores = json.loads(row["scores_json"])
    return {
        "id": int(row["id"]),
        "repo_full_name": row["repo_full_name"],
        "repo_url": row["repo_url"],
        "description": row["description"] or "No description provided.",
        "language": row["language"] or "Unknown",
        "stars": row["stars"],
        "status": row["status"],
        "final_action": row["final_action"],
        "initial_decision": row["initial_decision"],
        "analyzed_at": row["analyzed_at"],
        "total_score": analysis.get("total_score", 0),
        "one_line_judgment": analysis.get("one_line_judgment", ""),
        "project_type": analysis.get("project_type", "Other"),
        "scores": scores,
    }


def _detail_view(detail: dict[str, Any] | None) -> dict[str, Any] | None:
    if not detail:
        return None
    project = detail["project"]
    analysis = detail["analysis"]
    analysis_json = detail["analysis_json"]
    scores = detail["scores"]
    topics = []
    try:
        topics = json.loads(project.get("topics_json") or "[]")
    except Exception:
        topics = []
    metrics = [
        ("Inspiration", scores.get("inspiration", 0)),
        ("Replicability", scores.get("replicability", 0)),
        ("Governance", scores.get("governance_value", 0)),
        ("Knowledge", scores.get("knowledge_density", 0)),
        ("Automation", scores.get("automation_value", 0)),
        ("Direct Value", scores.get("direct_value", 0)),
        ("Evidence", scores.get("evidence_quality", 0)),
        ("Trial Difficulty", scores.get("trial_difficulty", 0)),
        ("Hidden Cost", scores.get("hidden_cost", 0)),
    ]
    return {
        "project": project,
        "analysis": analysis,
        "analysis_json": analysis_json,
        "scores": scores,
        "topics": topics,
        "selected_files": detail["selected_files"],
        "not_read_files": detail["not_read_files"],
        "evidence_files": detail["evidence_files"],
        "metrics": [{"name": name, "value": value, "width": _score_width(value)} for name, value in metrics],
        "raw_json": json.dumps(analysis_json, ensure_ascii=False, indent=2),
    }


def _workspace_context(
    request: Request,
    filter_name: str,
    project_id: int | None,
    run_id: int | None,
    message: str = "",
) -> dict[str, Any]:
    with db.connection() as conn:
        db.init_db(conn)
        library = [_library_item(row) for row in db.list_library(conn, filter_name)]
        selected_id = project_id or (library[0]["id"] if library else None)
        detail = _detail_view(db.get_project_detail(conn, selected_id))
        runs = [dict(row) for row in db.list_runs(conn)]
        active_run = dict(db.get_run(conn, run_id)) if run_id else None
    return {
        "request": request,
        "library": library,
        "detail": detail,
        "runs": runs,
        "active_run": active_run,
        "filter_name": filter_name,
        "message": message,
    }


@app.get("/")
def index(
    request: Request,
    filter: str = "all",
    project_id: int | None = None,
    run_id: int | None = None,
    message: str = "",
) -> Any:
    return templates.TemplateResponse(
        "index.html",
        _workspace_context(request, filter, project_id, run_id, message),
    )


@app.post("/scan")
def scan(
    scan_title: str = Form(""),
    keyword: str = Form(...),
    scan_count: int = Form(10),
    scan_mode: str = Form("quick"),
) -> RedirectResponse:
    with db.connection() as conn:
        db.init_db(conn)
        run_id = RadarScanner().run(conn, scan_title, keyword, scan_count, scan_mode)
    return RedirectResponse(f"/?run_id={run_id}", status_code=303)


@app.post("/projects/{project_id}/mark")
def mark_project(project_id: int, status: str = Form(...)) -> RedirectResponse:
    allowed = {
        "watch": "watch",
        "experiment": "experiment_candidate",
        "seen": "seen",
    }
    with db.connection() as conn:
        db.init_db(conn)
        if status in allowed:
            db.update_project_status(conn, project_id, allowed[status])
    return RedirectResponse(f"/?project_id={project_id}&message=Project updated", status_code=303)


@app.post("/projects/{project_id}/reanalyze")
def reanalyze_project(project_id: int, scan_mode: str = Form("quick")) -> RedirectResponse:
    with db.connection() as conn:
        db.init_db(conn)
        project = db.get_project(conn, project_id)
        if not project:
            return RedirectResponse("/?message=Project not found", status_code=303)
        topics = json.loads(project["topics_json"] or "[]")
        repo = RepoMetadata(
            full_name=project["repo_full_name"],
            html_url=project["repo_url"],
            description=project["description"] or "",
            stars=int(project["stars"] or 0),
            forks=int(project["forks"] or 0),
            language=project["language"] or "",
            topics=topics,
            updated_at=project["updated_at"] or "",
            default_branch=project["default_branch"] or "main",
        )
        intent = make_intent(repo.full_name, 1, scan_mode, f"Re-analyze {repo.full_name}")
        run_id = db.create_run(conn, intent.title, intent.keyword, 1, intent.scan_mode)
        try:
            result = RadarScanner(client=GitHubClient())._process_repo(conn, run_id, repo, intent, force=True)
            analyzed = 0 if result["final_action"] == "skip" else 1
            passed = 1 if result["final_action"] == "skip" else 0
            recommended = 0 if result["final_action"] == "skip" else 1
            db.complete_run(conn, run_id, "completed", 1, analyzed, passed, recommended)
        except Exception as exc:
            db.complete_run(conn, run_id, "failed", 1, 0, 0, 0, str(exc))
    return RedirectResponse(f"/?project_id={project_id}&run_id={run_id}", status_code=303)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/internal/passes")
def internal_passes(limit: int = 50) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 200))
    with db.connection() as conn:
        db.init_db(conn)
        rows = conn.execute(
            """
            SELECT p.repo_full_name, p.repo_url, a.pass_stage, a.pass_reason, a.created_at
            FROM project_analyses a
            JOIN projects p ON p.id = a.project_id
            WHERE a.final_action = 'skip'
            ORDER BY a.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
