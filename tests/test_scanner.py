import sqlite3

from app import db
from app.analyzer import MockAnalyzer
from app.models import RepoMetadata
from app.scanner import RadarScanner, build_queries, make_intent, search_keyword, select_files


class FakeGitHubClient:
    def __init__(self) -> None:
        self.good = RepoMetadata(
            full_name="owner/good-agent",
            html_url="https://github.com/owner/good-agent",
            description="AI agent workflow eval guardrail prompt automation knowledge assistant",
            stars=50,
            forks=3,
            language="Python",
            topics=["agent", "eval", "automation"],
            updated_at="2026-01-01T00:00:00Z",
            default_branch="main",
        )
        self.bad = RepoMetadata(
            full_name="owner/weather",
            html_url="https://github.com/owner/weather",
            description="Small weather widget",
            stars=1,
            forks=0,
            language="JavaScript",
            topics=[],
            updated_at="2026-01-01T00:00:00Z",
            default_branch="main",
        )

    def search_repositories(self, query: str, per_page: int = 10) -> list[RepoMetadata]:
        return [self.good, self.bad]

    def get_readme(self, full_name: str) -> str:
        if full_name == self.good.full_name:
            return "AI agent workflow with prompts, evals, guardrails, examples, docs, and automation."
        return ""

    def get_tree(self, full_name: str, branch: str) -> list[str]:
        if full_name == self.good.full_name:
            return [
                "README.md",
                "docs/quickstart.md",
                "examples/demo.py",
                "evals/checks.py",
                "node_modules/ignored.js",
                "package-lock.json",
            ]
        return []

    def get_file_text(self, full_name: str, path: str, branch: str) -> str:
        return f"{path} contains agent eval workflow guardrail example"


def make_conn(tmp_path):
    conn = sqlite3.connect(tmp_path / "radar.sqlite3")
    conn.row_factory = sqlite3.Row
    db.init_db(conn)
    return conn


def test_select_files_respects_quick_budget() -> None:
    selected, not_read = select_files(
        ["README.md", "docs/guide.md", "examples/demo.py", "evals/check.py"],
        "quick",
    )

    assert len(selected) == 2
    assert selected[0].path == "README.md"
    assert not_read


def test_chinese_keyword_options_search_with_english_query_terms() -> None:
    intent = make_intent("智能体治理", 3, "quick")
    queries = build_queries(intent)

    assert search_keyword("智能体治理") == "ai agent governance"
    assert "ai agent governance" in queries[0]


def test_scanner_persists_passes_and_reuses_similar_intent(tmp_path) -> None:
    conn = make_conn(tmp_path)
    scanner = RadarScanner(client=FakeGitHubClient(), analyzer=MockAnalyzer())

    first_run = scanner.run(conn, "Test", "ai agent governance", 2, "quick")
    second_run = scanner.run(conn, "Test again", "ai agent governance", 2, "quick")
    conn.commit()

    first = db.get_run(conn, first_run)
    second = db.get_run(conn, second_run)
    analysis_count = conn.execute("SELECT COUNT(*) AS c FROM project_analyses").fetchone()["c"]
    pass_rows = conn.execute(
        "SELECT pass_stage, pass_reason FROM project_analyses WHERE final_action = 'skip' ORDER BY id"
    ).fetchall()

    assert first["status"] == "completed"
    assert second["status"] == "completed"
    assert analysis_count == 4
    assert pass_rows[0]["pass_stage"] == "shell"
    assert pass_rows[-1]["pass_stage"] == "reuse"
    conn.close()
