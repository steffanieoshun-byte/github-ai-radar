import json

import requests

from app.analyzer import LLMAnalyzer, LLMProfile, MockAnalyzer, get_analyzer, load_llm_profiles
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
    assert "AI agent workflow" not in analysis["problem_solved"]
    assert "工作流" in analysis["problem_solved"]


def test_mock_analyzer_produces_repo_specific_text() -> None:
    intent = SearchIntent(keyword="ai agent", scan_count=2, scan_mode="quick")
    crew = RepoMetadata(
        full_name="crewAIInc/crewAI",
        html_url="https://github.com/crewAIInc/crewAI",
        description="Framework for orchestrating role-playing autonomous AI agents.",
        stars=10,
        forks=2,
        language="Python",
        topics=["agents", "ai-agents"],
        updated_at="2026-01-01T00:00:00Z",
        default_branch="main",
    )
    workflow = RepoMetadata(
        full_name="activepieces/activepieces",
        html_url="https://github.com/activepieces/activepieces",
        description="AI workflow automation with tools and integrations.",
        stars=10,
        forks=2,
        language="TypeScript",
        topics=["workflow", "automation", "mcp"],
        updated_at="2026-01-01T00:00:00Z",
        default_branch="main",
    )

    crew_analysis = MockAnalyzer().analyze(
        crew,
        intent,
        "Role-playing autonomous agents and task orchestration.",
        ["README.md", "examples/demo.py"],
        [SelectedFile("examples/demo.py", "example", "agent crew task process")],
    )
    workflow_analysis = MockAnalyzer().analyze(
        workflow,
        intent,
        "Workflow automation and integration examples.",
        ["README.md", "package.json", "docs/README.md"],
        [SelectedFile("docs/README.md", "docs", "workflow automation connector")],
    )

    assert crew_analysis["problem_solved"] != workflow_analysis["problem_solved"]
    assert crew_analysis["replicable_mvp"] != workflow_analysis["replicable_mvp"]
    assert "多智能体" in crew_analysis["problem_solved"]
    assert "自动化" in workflow_analysis["problem_solved"]


def test_mock_analyzer_has_quant_specific_profiles() -> None:
    intent = SearchIntent(keyword="量化", scan_count=2, scan_mode="deep")
    qlib = RepoMetadata(
        full_name="microsoft/qlib",
        html_url="https://github.com/microsoft/qlib",
        description="AI-oriented Quant investment platform for Quant Research, models, datasets, and backtesting.",
        stars=10,
        forks=2,
        language="Python",
        topics=["quantitative-trading", "stock-data", "research", "machine-learning"],
        updated_at="2026-01-01T00:00:00Z",
        default_branch="main",
    )
    akshare = RepoMetadata(
        full_name="akfamily/akshare",
        html_url="https://github.com/akfamily/akshare",
        description="Open source financial data interface library for stocks, futures, options, and economics.",
        stars=10,
        forks=2,
        language="Python",
        topics=["financial-data", "finance-api", "stock", "quant"],
        updated_at="2026-01-01T00:00:00Z",
        default_branch="main",
    )
    llm = RepoMetadata(
        full_name="owner/llm-quantization",
        html_url="https://github.com/owner/llm-quantization",
        description="Large language model quantization and inference notes.",
        stars=10,
        forks=2,
        language="Python",
        topics=["llm", "quantization"],
        updated_at="2026-01-01T00:00:00Z",
        default_branch="main",
    )

    qlib_analysis = MockAnalyzer().analyze(
        qlib,
        intent,
        "Quant research platform with datasets, models, portfolio and backtesting examples.",
        ["README.md", "examples/README.md"],
        [SelectedFile("examples/README.md", "example", "quant research backtesting stock model")],
    )
    akshare_analysis = MockAnalyzer().analyze(
        akshare,
        intent,
        "Financial data API examples for stock and futures data.",
        ["README.md", "docs/demo.md"],
        [SelectedFile("docs/demo.md", "docs", "financial data stock futures API")],
    )
    llm_analysis = MockAnalyzer().analyze(
        llm,
        intent,
        "LLM quantization and inference.",
        ["README.md"],
        [SelectedFile("README.md", "docs", "LLM quantization inference")],
    )

    assert "量化研究平台" in qlib_analysis["problem_solved"]
    assert "财经数据入口" in akshare_analysis["problem_solved"]
    assert "不是交易量化" in llm_analysis["problem_solved"]
    assert qlib_analysis["problem_solved"] != akshare_analysis["problem_solved"]


def test_load_llm_profiles_supports_primary_and_fallbacks(monkeypatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "primary-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://primary.example/v1")
    monkeypatch.setenv("LLM_MODEL", "primary-model")
    monkeypatch.setenv("LLM_FALLBACK_1_API_KEY", "fallback-key")
    monkeypatch.setenv("LLM_FALLBACK_1_BASE_URL", "https://fallback.example/v1")
    monkeypatch.setenv("LLM_FALLBACK_1_MODEL", "fallback-model")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    profiles = load_llm_profiles()

    assert [profile.name for profile in profiles] == ["primary", "fallback_1"]
    assert profiles[0].base_url == "https://primary.example/v1"
    assert profiles[1].model == "fallback-model"


def test_load_llm_profiles_supports_deepseek_defaults(monkeypatch) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-key")

    profiles = load_llm_profiles()

    assert profiles[0].name == "deepseek"
    assert profiles[0].base_url == "https://api.deepseek.com"
    assert profiles[0].model == "deepseek-v4-pro"


def test_get_analyzer_uses_mock_without_complete_llm_config(monkeypatch) -> None:
    monkeypatch.setenv("ANALYZER_MODE", "llm")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    analyzer = get_analyzer()
    assert isinstance(analyzer, MockAnalyzer)
    assert analyzer.source == "mock_no_llm_config"


def test_llm_analyzer_falls_back_to_second_profile(monkeypatch) -> None:
    repo = RepoMetadata(
        full_name="owner/agent-eval-kit",
        html_url="https://github.com/owner/agent-eval-kit",
        description="AI agent workflow eval guardrail prompt automation toolkit",
        stars=10,
        forks=2,
        language="Python",
        topics=["agent", "eval"],
        updated_at="2026-01-01T00:00:00Z",
        default_branch="main",
    )
    intent = SearchIntent(keyword="ai agent governance", scan_count=1, scan_mode="quick")
    files = [SelectedFile("docs/quickstart.md", "documentation", "agent eval guardrail workflow")]
    calls = []

    class FakeResponse:
        def __init__(self, ok: bool) -> None:
            self.ok = ok

        def raise_for_status(self) -> None:
            if not self.ok:
                raise requests.HTTPError("quota exceeded")

        def json(self) -> dict:
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "one_line_judgment": "中文模型判断",
                                    "project_type": "Agent",
                                    "problem_solved": "用于观察智能体项目治理方式。",
                                    "scores": {"inspiration": 5, "direct_value": 4},
                                    "final_action": "watch",
                                    "unknowns": [],
                                },
                                ensure_ascii=False,
                            )
                        }
                    }
                ]
            }

    def fake_post(url, **kwargs):
        calls.append(url)
        return FakeResponse(ok=len(calls) > 1)

    monkeypatch.setattr("app.analyzer.requests.post", fake_post)
    analyzer = LLMAnalyzer(
        [
            LLMProfile("primary", "key1", "https://primary.example/v1", "model-a"),
            LLMProfile("fallback_1", "key2", "https://fallback.example/v1", "model-b"),
        ]
    )

    analysis = analyzer.analyze(repo, intent, "readme", ["docs/quickstart.md"], files)

    assert calls == ["https://primary.example/v1/chat/completions", "https://fallback.example/v1/chat/completions"]
    assert analysis["analysis_source"] == "llm:fallback_1"
    assert analysis["one_line_judgment"] == "中文模型判断"
    assert analysis["scores"]["inspiration"] == 5
