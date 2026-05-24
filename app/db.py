from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def database_path() -> Path:
    raw = os.getenv("DATABASE_PATH", "data/radar.sqlite3")
    path = Path(raw)
    if not path.is_absolute():
        path = Path.cwd() / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def connect(path: Path | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or database_path())
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def connection(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    conn = connect(path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            keyword TEXT NOT NULL,
            scan_count INTEGER NOT NULL,
            scan_mode TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            discovered_count INTEGER DEFAULT 0,
            analyzed_count INTEGER DEFAULT 0,
            passed_count INTEGER DEFAULT 0,
            recommended_count INTEGER DEFAULT 0,
            error_message TEXT
        );

        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo_full_name TEXT NOT NULL UNIQUE,
            repo_url TEXT NOT NULL,
            description TEXT,
            stars INTEGER DEFAULT 0,
            forks INTEGER DEFAULT 0,
            language TEXT,
            topics_json TEXT,
            updated_at TEXT,
            default_branch TEXT,
            created_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            last_analyzed_at TEXT,
            status TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS project_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            project_id INTEGER NOT NULL,
            search_intent_json TEXT NOT NULL,
            initial_decision TEXT NOT NULL,
            pass_stage TEXT,
            pass_reason TEXT,
            final_action TEXT NOT NULL,
            analysis_json TEXT NOT NULL,
            evidence_files_json TEXT NOT NULL,
            selected_files_json TEXT NOT NULL,
            not_read_files_json TEXT NOT NULL,
            scores_json TEXT NOT NULL,
            scan_mode TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(run_id) REFERENCES runs(id),
            FOREIGN KEY(project_id) REFERENCES projects(id)
        );

        CREATE TABLE IF NOT EXISTS experiment_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            analysis_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            replicable_mvp TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id),
            FOREIGN KEY(analysis_id) REFERENCES project_analyses(id)
        );
        """
    )


def create_run(conn: sqlite3.Connection, title: str, keyword: str, scan_count: int, scan_mode: str) -> int:
    cur = conn.execute(
        """
        INSERT INTO runs (title, keyword, scan_count, scan_mode, status, created_at)
        VALUES (?, ?, ?, ?, 'running', ?)
        """,
        (title, keyword, scan_count, scan_mode, utc_now()),
    )
    return int(cur.lastrowid)


def complete_run(
    conn: sqlite3.Connection,
    run_id: int,
    status: str,
    discovered_count: int,
    analyzed_count: int,
    passed_count: int,
    recommended_count: int,
    error_message: str = "",
) -> None:
    conn.execute(
        """
        UPDATE runs
        SET status = ?, completed_at = ?, discovered_count = ?, analyzed_count = ?,
            passed_count = ?, recommended_count = ?, error_message = ?
        WHERE id = ?
        """,
        (
            status,
            utc_now(),
            discovered_count,
            analyzed_count,
            passed_count,
            recommended_count,
            error_message,
            run_id,
        ),
    )


def upsert_project(conn: sqlite3.Connection, repo: dict[str, Any]) -> int:
    now = utc_now()
    topics_json = json.dumps(repo.get("topics", []), ensure_ascii=False)
    existing = conn.execute(
        "SELECT id FROM projects WHERE repo_full_name = ?", (repo["repo_full_name"],)
    ).fetchone()
    if existing:
        conn.execute(
            """
            UPDATE projects
            SET repo_url = ?, description = ?, stars = ?, forks = ?, language = ?,
                topics_json = ?, updated_at = ?, default_branch = ?, last_seen_at = ?
            WHERE id = ?
            """,
            (
                repo["repo_url"],
                repo.get("description", ""),
                repo.get("stars", 0),
                repo.get("forks", 0),
                repo.get("language", ""),
                topics_json,
                repo.get("updated_at", ""),
                repo.get("default_branch", "main"),
                now,
                int(existing["id"]),
            ),
        )
        return int(existing["id"])
    cur = conn.execute(
        """
        INSERT INTO projects (
            repo_full_name, repo_url, description, stars, forks, language,
            topics_json, updated_at, default_branch, created_at, last_seen_at, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'seen')
        """,
        (
            repo["repo_full_name"],
            repo["repo_url"],
            repo.get("description", ""),
            repo.get("stars", 0),
            repo.get("forks", 0),
            repo.get("language", ""),
            topics_json,
            repo.get("updated_at", ""),
            repo.get("default_branch", "main"),
            now,
            now,
        ),
    )
    return int(cur.lastrowid)


def latest_analysis(conn: sqlite3.Connection, project_id: int) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT * FROM project_analyses
        WHERE project_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (project_id,),
    ).fetchone()


def insert_analysis(
    conn: sqlite3.Connection,
    run_id: int,
    project_id: int,
    search_intent: dict[str, Any],
    initial_decision: str,
    final_action: str,
    analysis: dict[str, Any],
    evidence_files: list[str],
    selected_files: list[dict[str, Any]],
    not_read_files: list[dict[str, Any]],
    scan_mode: str,
    pass_stage: str = "",
    pass_reason: str = "",
) -> int:
    scores = analysis.get("scores", {})
    cur = conn.execute(
        """
        INSERT INTO project_analyses (
            run_id, project_id, search_intent_json, initial_decision, pass_stage,
            pass_reason, final_action, analysis_json, evidence_files_json,
            selected_files_json, not_read_files_json, scores_json, scan_mode, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            project_id,
            json.dumps(search_intent, ensure_ascii=False),
            initial_decision,
            pass_stage,
            pass_reason,
            final_action,
            json.dumps(analysis, ensure_ascii=False),
            json.dumps(evidence_files, ensure_ascii=False),
            json.dumps(selected_files, ensure_ascii=False),
            json.dumps(not_read_files, ensure_ascii=False),
            json.dumps(scores, ensure_ascii=False),
            scan_mode,
            utc_now(),
        ),
    )
    current = conn.execute("SELECT status FROM projects WHERE id = ?", (project_id,)).fetchone()
    current_status = current["status"] if current else ""
    status = current_status
    if current_status != "hidden":
        status = "passed" if final_action == "skip" else "analyzed"
        if final_action == "watch":
            status = "watch"
        if final_action == "codex_experiment":
            status = "experiment_candidate"
    conn.execute(
        "UPDATE projects SET status = ?, last_analyzed_at = ? WHERE id = ?",
        (status, utc_now(), project_id),
    )
    if final_action == "codex_experiment":
        conn.execute(
            """
            INSERT INTO experiment_candidates (project_id, analysis_id, title, replicable_mvp, status, created_at)
            VALUES (?, ?, ?, ?, 'candidate', ?)
            """,
            (
                project_id,
                int(cur.lastrowid),
                analysis.get("one_line_judgment", "Codex experiment candidate")[:160],
                analysis.get("replicable_mvp", ""),
                utc_now(),
            ),
        )
    return int(cur.lastrowid)


def update_project_status(conn: sqlite3.Connection, project_id: int, status: str) -> None:
    conn.execute("UPDATE projects SET status = ? WHERE id = ?", (status, project_id))


def list_library(conn: sqlite3.Connection, filter_name: str = "all") -> list[sqlite3.Row]:
    conditions = ["p.status != 'hidden'", "a.initial_decision != 'PASS'", "a.final_action != 'skip'"]
    params: list[Any] = []
    if filter_name == "watch":
        conditions.append("p.status = 'watch'")
    elif filter_name == "experiment":
        conditions.append("p.status = 'experiment_candidate'")
    elif filter_name == "high":
        conditions.append("CAST(json_extract(a.scores_json, '$.inspiration') AS INTEGER) >= 4")
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return list(
        conn.execute(
            f"""
            SELECT p.*, a.id AS analysis_id, a.final_action, a.initial_decision,
                   a.analysis_json, a.scores_json, a.created_at AS analyzed_at
            FROM projects p
            JOIN project_analyses a ON a.id = (
                SELECT id FROM project_analyses
                WHERE project_id = p.id
                ORDER BY id DESC
                LIMIT 1
            )
            {where}
            ORDER BY a.id DESC
            """,
            params,
        )
    )


def list_runs(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 20"))


def get_run(conn: sqlite3.Connection, run_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()


def get_project(conn: sqlite3.Connection, project_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()


def get_project_detail(conn: sqlite3.Connection, project_id: int | None) -> dict[str, Any] | None:
    if project_id is None:
        row = conn.execute(
            """
            SELECT p.id
            FROM projects p
            JOIN project_analyses a ON a.project_id = p.id
            WHERE p.status != 'hidden' AND a.final_action != 'skip'
            ORDER BY a.id DESC
            LIMIT 1
            """
        ).fetchone()
        if not row:
            return None
        project_id = int(row["id"])
    project = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not project or project["status"] == "hidden":
        return None
    analysis = latest_analysis(conn, project_id)
    if not analysis:
        return None
    return {
        "project": dict(project),
        "analysis": dict(analysis),
        "analysis_json": json.loads(analysis["analysis_json"]),
        "scores": json.loads(analysis["scores_json"]),
        "selected_files": json.loads(analysis["selected_files_json"]),
        "not_read_files": json.loads(analysis["not_read_files_json"]),
        "evidence_files": json.loads(analysis["evidence_files_json"]),
    }
