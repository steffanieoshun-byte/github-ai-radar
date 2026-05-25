from app.main import _detail_view


def _detail(repo_full_name: str, description: str, topics: list[str], selected_paths: list[str]) -> dict:
    return {
        "project": {
            "id": 1,
            "repo_full_name": repo_full_name,
            "repo_url": f"https://github.com/{repo_full_name}",
            "description": description,
            "stars": 100,
            "updated_at": "2026-01-01T00:00:00Z",
            "topics_json": __import__("json").dumps(topics, ensure_ascii=False),
        },
        "analysis": {
            "final_action": "deep_dive",
            "initial_decision": "ANALYZE",
        },
        "analysis_json": {
            "project_type": "Agent",
            "one_line_judgment": f"{repo_full_name} 可能包含可复用的智能工作流、治理经验或灵感线索。",
            "problem_solved": "根据仓库描述、文档和目录结构判断它是否提供可复用的智能工作流、治理方法、知识技巧或自动化动作。",
            "ai_pattern": "智能体编排、工作流自动化",
            "direct_value_for_me": "如果它的结构能改进本地智能工作流或项目治理，就有直接价值。",
            "governance_value": "重点观察评测、防护规则、日志、权限、成本和失败恢复机制。",
            "knowledge_tips": "先看文档、示例、模板、提示词和安装配置，再决定是否读源码。",
            "inspiration_value": "即使整个项目不适合采用，也可能拆出一个小技巧或小实验。",
            "replicable_mvp": "抽取一个工作流、提示词模式、评测规则或启动模板，在本地做小实验。",
            "hidden_costs": "未知",
            "total_score": 4.1,
        },
        "scores": {
            "inspiration": 5,
            "replicability": 4,
            "governance_value": 3,
            "knowledge_density": 4,
            "automation_value": 4,
            "direct_value": 5,
            "evidence_quality": 5,
            "trial_difficulty": 2,
            "hidden_cost": 2,
        },
        "selected_files": [{"path": path, "reason": "test"} for path in selected_paths],
        "not_read_files": [],
        "evidence_files": selected_paths,
    }


def test_detail_view_uses_repo_specific_focus_for_generic_mock_records() -> None:
    crew = _detail_view(
        _detail(
            "crewAIInc/crewAI",
            "Framework for orchestrating role-playing autonomous AI agents.",
            ["agents", "ai-agents"],
            ["README.md", "lib/crewai/README.md"],
        )
    )
    activepieces = _detail_view(
        _detail(
            "activepieces/activepieces",
            "AI Agents and workflow automation with many MCP servers.",
            ["workflow", "workflow-automation", "mcp"],
            ["README.md", "package.json", "docs/README.md"],
        )
    )

    assert crew is not None
    assert activepieces is not None
    assert crew["inspiration_paragraphs"] != activepieces["inspiration_paragraphs"]
    assert "多智能体" in " ".join(crew["inspiration_paragraphs"])
    assert "自动化" in " ".join(activepieces["inspiration_paragraphs"])
