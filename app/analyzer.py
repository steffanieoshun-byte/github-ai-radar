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
            "one_line_judgment": f"{repo.full_name} may provide reusable AI workflow or governance inspiration.",
            "project_type": project_type,
            "problem_solved": repo.description or "UNKNOWN",
            "target_users": "AI builders, automation users, and local workflow experimenters",
            "input": "Repository docs, examples, prompts, workflows, or source files",
            "output": "Reusable project intelligence and experiment ideas",
            "ai_pattern": self._ai_pattern(lowered),
            "direct_value_for_me": "Useful if its structure can improve local Codex workflows or project governance.",
            "governance_value": "Look for evals, guardrails, logs, permissions, and failure recovery patterns.",
            "knowledge_tips": "Review docs, examples, templates, prompts, and setup files before reading source deeply.",
            "inspiration_value": "Can inspire a small local experiment even if the whole project is too large to adopt.",
            "replicable_mvp": "Extract one workflow, prompt pattern, evaluation rule, or starter template and test it locally.",
            "hidden_costs": "UNKNOWN" if hidden_cost <= 2 else "May require external services, hosted APIs, or heavier setup.",
            "key_directory_observations": self._directory_observations(tree_paths),
            "evidence_files": evidence_files,
            "selected_files": [file.as_dict() for file in selected_files],
            "not_read_files": [],
            "scores": scores,
            "total_score": total,
            "final_action": final_action,
            "pass_reason": "",
            "unknowns": [] if evidence >= 3 else ["Evidence is thin; read more files before making a strong decision."],
        }

    def _ai_pattern(self, lowered: str) -> str:
        patterns = []
        if "agent" in lowered:
            patterns.append("agent orchestration")
        if "workflow" in lowered:
            patterns.append("workflow automation")
        if "eval" in lowered:
            patterns.append("evaluation")
        if "prompt" in lowered:
            patterns.append("prompt management")
        return ", ".join(patterns) or "UNKNOWN"

    def _directory_observations(self, tree_paths: list[str]) -> str:
        interesting = [p for p in tree_paths if p.startswith(("docs/", "examples/", "agents/", "prompts/", "evals/", "workflows/", "skills/"))]
        if not interesting:
            return "No strong docs/examples/prompts/evals directory signal found in the scanned tree."
        return "Interesting paths: " + ", ".join(interesting[:10])


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
