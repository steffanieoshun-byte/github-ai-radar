from app.analyzer import MockAnalyzer
from app.models import RepoMetadata, SearchIntent, SelectedFile


def test_mock_analyzer_scores_inspiration_and_evidence() -> None:
    repo = RepoMetadata(
        full_name="owner/agent-eval-kit",
        html_url="https://github.com/owner/agent-eval-kit",
        description="AI agent workflow eval guardrail prompt automation toolkit",
        stars=10,
        forks=2,
        language="Python",
        topics=["agent", "eval", "guardrails"],
        updated_at="2026-01-01T00:00:00Z",
        default_branch="main",
    )
    intent = SearchIntent(keyword="ai agent governance", scan_count=1, scan_mode="quick")
    files = [SelectedFile("docs/quickstart.md", "documentation", "agent eval guardrail workflow")]

    analysis = MockAnalyzer().analyze(
        repo,
        intent,
        "AI agent workflow with evals, prompts, examples, docs, and guardrails.",
        ["docs/quickstart.md", "examples/demo.py"],
        files,
    )

    assert analysis["scores"]["inspiration"] >= 4
    assert analysis["scores"]["evidence_quality"] >= 3
    assert analysis["evidence_files"] == ["docs/quickstart.md"]
    assert analysis["final_action"] in {"watch", "deep_dive", "codex_experiment"}
