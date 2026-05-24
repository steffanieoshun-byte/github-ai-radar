import sqlite3

from app import db


def test_db_appends_analysis_history_without_overwrite(tmp_path) -> None:
    conn = sqlite3.connect(tmp_path / "radar.sqlite3")
    conn.row_factory = sqlite3.Row
    db.init_db(conn)
    run_id = db.create_run(conn, "Test", "ai agent", 1, "quick")
    project_id = db.upsert_project(
        conn,
        {
            "repo_full_name": "owner/repo",
            "repo_url": "https://github.com/owner/repo",
            "description": "AI agent repo",
            "stars": 1,
            "forks": 0,
            "language": "Python",
            "topics": ["agent"],
            "updated_at": "2026-01-01T00:00:00Z",
            "default_branch": "main",
        },
    )
    analysis = {
        "one_line_judgment": "Useful",
        "scores": {"inspiration": 4},
        "final_action": "watch",
    }

    db.insert_analysis(conn, run_id, project_id, {"keyword": "ai agent"}, "ANALYZE", "watch", analysis, [], [], [], "quick")
    db.insert_analysis(conn, run_id, project_id, {"keyword": "ai agent"}, "ANALYZE", "watch", analysis, [], [], [], "quick")
    conn.commit()

    count = conn.execute("SELECT COUNT(*) AS c FROM project_analyses WHERE project_id = ?", (project_id,)).fetchone()["c"]
    project = db.get_project(conn, project_id)

    assert count == 2
    assert project["status"] == "watch"
    conn.close()


def test_hidden_project_stays_recorded_but_leaves_front_library(tmp_path) -> None:
    conn = sqlite3.connect(tmp_path / "radar.sqlite3")
    conn.row_factory = sqlite3.Row
    db.init_db(conn)
    run_id = db.create_run(conn, "Test", "ai agent", 1, "quick")
    project_id = db.upsert_project(
        conn,
        {
            "repo_full_name": "owner/hidden-repo",
            "repo_url": "https://github.com/owner/hidden-repo",
            "description": "AI agent repo",
            "stars": 1,
            "forks": 0,
            "language": "Python",
            "topics": ["agent"],
            "updated_at": "2026-01-01T00:00:00Z",
            "default_branch": "main",
        },
    )
    analysis = {
        "one_line_judgment": "Useful",
        "scores": {"inspiration": 4},
        "total_score": 4,
        "final_action": "watch",
    }

    db.insert_analysis(conn, run_id, project_id, {"keyword": "ai agent"}, "ANALYZE", "watch", analysis, [], [], [], "quick")
    db.update_project_status(conn, project_id, "hidden")
    db.insert_analysis(conn, run_id, project_id, {"keyword": "ai agent"}, "ANALYZE", "watch", analysis, [], [], [], "quick")
    conn.commit()

    project = db.get_project(conn, project_id)
    analysis_count = conn.execute("SELECT COUNT(*) AS c FROM project_analyses WHERE project_id = ?", (project_id,)).fetchone()["c"]

    assert project["status"] == "hidden"
    assert analysis_count == 2
    assert db.list_library(conn) == []
    assert db.get_project_detail(conn, project_id) is None
    conn.close()
