from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any

from .models import RepoMetadata, SearchIntent, SelectedFile


AI_TERMS = {
    "agent",
    "agents",
    "ai",
    "llm",
    "rag",
    "prompt",
    "workflow",
    "automation",
    "eval",
    "evaluation",
    "guardrail",
    "codex",
    "copilot",
    "assistant",
    "knowledge",
}

GOVERNANCE_TERMS = {"eval", "evaluation", "guardrail", "policy", "audit", "permission", "cost", "trace", "logging"}
REPLICABLE_TERMS = {"example", "examples", "demo", "starter", "template", "quickstart", "notebook", "docker"}


class AgentAdapter(ABC):
    @abstractmethod
    def analyze(
        self,
        repo: RepoMetadata,
        intent: SearchIntent,
        readme: str,
        tree_paths: list[str],
        selected_files: list[SelectedFile],
    ) -> dict[str, Any]:
        raise NotImplementedError


def text_score(blob: str, terms: set[str]) -> int:
    lowered = blob.lower()
    hits = sum(1 for term in terms if term in lowered)
    if hits >= 7:
        return 5
    if hits >= 5:
        return 4
    if hits >= 3:
        return 3
    if hits >= 1:
        return 2
    return 1


def score_average(scores: dict[str, int]) -> float:
    weights = {
        "direct_value": 0.20,
        "inspiration": 0.20,
        "replicability": 0.15,
        "governance_value": 0.15,
        "knowledge_density": 0.10,
        "automation_value": 0.10,
        "evidence_quality": 0.10,
    }
    return round(sum(scores.get(k, 1) * w for k, w in weights.items()), 2)


class MockAnalyzer(AgentAdapter):
    def analyze(
        self,
        repo: RepoMetadata,
        intent: SearchIntent,
        readme: str,
        tree_paths: list[str],
        selected_files: list[SelectedFile],
    ) -> dict[str, Any]:
        corpus = " ".join(
            [
                repo.full_name,
                repo.description,
                " ".join(repo.topics),
                readme[:8000],
                " ".join(tree_paths[:300]),
                " ".join(file.content[:1600] for file in selected_files),
            ]
        )
        direct = text_score(corpus, AI_TERMS)
        governance = text_score(corpus, GOVERNANCE_TERMS)
        replicability = text_score(corpus, REPLICABLE_TERMS)
        knowledge = 4 if any(path.startswith(("docs/", "examples/", "notebooks/")) for path in tree_paths) else 2
        automation = 4 if any(term in corpus.lower() for term in ["workflow", "automation", "agent"]) else 2
        evidence = min(5, 2 + len(selected_files) + (1 if readme.strip() else 0))
        inspiration = max(direct, governance, replicability, knowledge)
        trial_difficulty = 4 if any(path in tree_paths for path in ["docker-compose.yml", "dockerfile"]) else 2
        hidden_cost = 4 if any(term in corpus.lower() for term in ["api key", "cloud", "paid", "kubernetes"]) else 2
        scores = {
            "direct_value": direct,
            "governance_value": governance,
            "knowledge_density": knowledge,
            "automation_value": automation,
            "replicability": replicability,
            "inspiration": inspiration,
            "evidence_quality": evidence,
            "trial_difficulty": trial_difficulty,
            "hidden_cost": hidden_cost,
        }
        total = score_average(scores)
        final_action = "skip"
        if total >= 4.2:
            final_action = "codex_experiment"
        elif total >= 3.7:
            final_action = "deep_dive"
        elif total >= 3.0:
            final_action = "watch"
        evidence_files = [file.path for file in selected_files]
        project_type = "Other"
        lowered = corpus.lower()
        if "agent" in lowered:
            project_type = "Agent"
        elif "rag" in lowered or "knowledge" in lowered:
            project_type = "KnowledgeBase"
        elif "workflow" in lowered or "automation" in lowered:
            project_type = "Workflow"
        elif "eval" in lowered or "guardrail" in lowered:
            project_type = "Eval"
        return {
            "analysis_version": "0.1",
            "one_line_judgment": f"{repo.full_name} 可能包含可复用的 AI 工作流、治理经验或灵感线索。",
            "project_type": project_type,
            "problem_solved": repo.description or "未知",
            "target_users": "智能应用构建者、自动化用户、本地工作流实验者",
            "input": "仓库文档、示例、提示词、工作流或源码文件",
            "output": "可复用的项目情报和实验灵感",
            "ai_pattern": self._ai_pattern(lowered),
            "direct_value_for_me": "如果它的结构能改进本地智能工作流或项目治理，就有直接价值。",
            "governance_value": "重点观察评测、防护规则、日志、权限、成本和失败恢复机制。",
            "knowledge_tips": "先看文档、示例、模板、提示词和安装配置，再决定是否读源码。",
            "inspiration_value": "即使整个项目不适合采用，也可能拆出一个小技巧或小实验。",
            "replicable_mvp": "抽取一个工作流、提示词模式、评测规则或启动模板，在本地做小实验。",
            "hidden_costs": "未知" if hidden_cost <= 2 else "可能依赖外部服务、托管 API 或较重部署环境。",
            "key_directory_observations": self._directory_observations(tree_paths),
            "evidence_files": evidence_files,
            "selected_files": [file.as_dict() for file in selected_files],
            "not_read_files": [],
            "scores": scores,
            "total_score": total,
            "final_action": final_action,
            "pass_reason": "",
            "unknowns": [] if evidence >= 3 else ["证据偏薄，做强判断前需要读取更多文件。"],
        }

    def _ai_pattern(self, lowered: str) -> str:
        patterns = []
        if "agent" in lowered:
            patterns.append("agent 编排")
        if "workflow" in lowered:
            patterns.append("workflow 自动化")
        if "eval" in lowered:
            patterns.append("评测")
        if "prompt" in lowered:
            patterns.append("prompt 管理")
        return "、".join(patterns) or "未知"

    def _directory_observations(self, tree_paths: list[str]) -> str:
        interesting = [p for p in tree_paths if p.startswith(("docs/", "examples/", "agents/", "prompts/", "evals/", "workflows/", "skills/"))]
        if not interesting:
            return "目录树里没有发现明显的 docs/examples/prompts/evals 等强证据信号。"
        return "值得关注的路径：" + ", ".join(interesting[:10])


class LLMAnalyzer(AgentAdapter):
    def analyze(
        self,
        repo: RepoMetadata,
        intent: SearchIntent,
        readme: str,
        tree_paths: list[str],
        selected_files: list[SelectedFile],
    ) -> dict[str, Any]:
        raise RuntimeError("LLMAnalyzer is reserved for future Codex/OpenAI API integration.")


def get_analyzer() -> AgentAdapter:
    mode = os.getenv("ANALYZER_MODE", "mock").lower()
    if mode in {"llm", "codex", "openai"}:
        if os.getenv("OPENAI_API_KEY") or os.getenv("CODEX_API_KEY"):
            return LLMAnalyzer()
    return MockAnalyzer()
