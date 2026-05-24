from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import requests

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


@dataclass(frozen=True)
class LLMProfile:
    name: str
    api_key: str
    base_url: str
    model: str


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
            "one_line_judgment": f"{repo.full_name} 可能包含可复用的智能工作流、治理经验或灵感线索。",
            "project_type": project_type,
            "problem_solved": "根据仓库描述、文档和目录结构判断它是否提供可复用的智能工作流、治理方法、知识技巧或自动化动作。",
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
    def __init__(self, profiles: list[LLMProfile], timeout: int = 60) -> None:
        self.profiles = profiles
        self.timeout = timeout
        self.mock = MockAnalyzer()

    def analyze(
        self,
        repo: RepoMetadata,
        intent: SearchIntent,
        readme: str,
        tree_paths: list[str],
        selected_files: list[SelectedFile],
    ) -> dict[str, Any]:
        failures: list[str] = []
        for profile in self.profiles:
            try:
                analysis = self._call_profile(profile, repo, intent, readme, tree_paths, selected_files)
                analysis = self._complete_schema(analysis, repo, intent, readme, tree_paths, selected_files)
                analysis["analysis_source"] = f"llm:{profile.name}"
                return analysis
            except Exception as exc:
                failures.append(f"{profile.name}: {exc}")
        analysis = self.mock.analyze(repo, intent, readme, tree_paths, selected_files)
        analysis["analysis_source"] = "mock_after_llm_failure"
        analysis.setdefault("unknowns", [])
        analysis["unknowns"].append("模型接口不可用，已回退到本地规则分析；失败信息保存在原始 JSON。")
        analysis["llm_failures"] = failures
        return analysis

    def _call_profile(
        self,
        profile: LLMProfile,
        repo: RepoMetadata,
        intent: SearchIntent,
        readme: str,
        tree_paths: list[str],
        selected_files: list[SelectedFile],
    ) -> dict[str, Any]:
        response = requests.post(
            profile.base_url.rstrip("/") + "/chat/completions",
            headers={
                "Authorization": f"Bearer {profile.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": profile.model,
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": "你是本地 GitHub AI 项目雷达的中文分析器。只输出合法 JSON，不要输出 Markdown。不确定写未知，不要编造项目能力。",
                    },
                    {
                        "role": "user",
                        "content": self._prompt(repo, intent, readme, tree_paths, selected_files),
                    },
                ],
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)

    def _prompt(
        self,
        repo: RepoMetadata,
        intent: SearchIntent,
        readme: str,
        tree_paths: list[str],
        selected_files: list[SelectedFile],
    ) -> str:
        payload = {
            "search_intent": intent.as_dict(),
            "repo": repo.as_dict(),
            "readme_excerpt": readme[:6000],
            "tree_paths": tree_paths[:300],
            "selected_files": [
                {"path": item.path, "reason": item.reason, "content": item.content[:2000]}
                for item in selected_files
            ],
            "required_schema": {
                "one_line_judgment": "中文一句话判断",
                "project_type": "Agent/RAG/Workflow/Browser/Coding/Eval/KnowledgeBase/Other",
                "problem_solved": "中文",
                "target_users": "中文",
                "input": "中文",
                "output": "中文",
                "ai_pattern": "中文",
                "direct_value_for_me": "中文",
                "governance_value": "中文",
                "knowledge_tips": "中文",
                "inspiration_value": "中文",
                "replicable_mvp": "中文",
                "hidden_costs": "中文",
                "key_directory_observations": "中文",
                "evidence_files": [],
                "scores": {
                    "direct_value": "1-5",
                    "governance_value": "1-5",
                    "knowledge_density": "1-5",
                    "automation_value": "1-5",
                    "replicability": "1-5",
                    "inspiration": "1-5",
                    "evidence_quality": "1-5",
                    "trial_difficulty": "1-5",
                    "hidden_cost": "1-5",
                },
                "final_action": "direct_try/deep_dive/codex_experiment/watch/skip",
                "unknowns": [],
            },
        }
        return json.dumps(payload, ensure_ascii=False)

    def _complete_schema(
        self,
        analysis: dict[str, Any],
        repo: RepoMetadata,
        intent: SearchIntent,
        readme: str,
        tree_paths: list[str],
        selected_files: list[SelectedFile],
    ) -> dict[str, Any]:
        fallback = self.mock.analyze(repo, intent, readme, tree_paths, selected_files)
        merged = {**fallback, **analysis}
        scores = {**fallback.get("scores", {}), **analysis.get("scores", {})}
        merged["scores"] = {key: _score_value(value) for key, value in scores.items()}
        merged["total_score"] = score_average(merged["scores"])
        merged["analysis_version"] = "0.1"
        merged["evidence_files"] = list(merged.get("evidence_files") or fallback.get("evidence_files") or [])
        merged["selected_files"] = [file.as_dict() for file in selected_files]
        merged["not_read_files"] = []
        if merged.get("final_action") not in {"direct_try", "deep_dive", "codex_experiment", "watch", "skip"}:
            merged["final_action"] = fallback["final_action"]
        return merged


def _score_value(value: Any) -> int:
    try:
        return max(1, min(5, int(value)))
    except Exception:
        return 1


def _profile_from_env(prefix: str, name: str, allow_openai_defaults: bool = False) -> LLMProfile | None:
    api_key = os.getenv(f"{prefix}API_KEY", "")
    base_url = os.getenv(f"{prefix}BASE_URL", "")
    model = os.getenv(f"{prefix}MODEL", "")
    if allow_openai_defaults and not api_key:
        api_key = os.getenv("OPENAI_API_KEY", "")
    if allow_openai_defaults and not base_url:
        base_url = "https://api.openai.com/v1"
    if not api_key or not base_url or not model:
        return None
    return LLMProfile(name=name, api_key=api_key, base_url=base_url, model=model)


def load_llm_profiles() -> list[LLMProfile]:
    profiles: list[LLMProfile] = []
    primary = _profile_from_env("LLM_", "primary", allow_openai_defaults=True)
    if primary:
        profiles.append(primary)
    for index in range(1, 4):
        profile = _profile_from_env(f"LLM_FALLBACK_{index}_", f"fallback_{index}")
        if profile:
            profiles.append(profile)
    return profiles


def get_analyzer() -> AgentAdapter:
    mode = os.getenv("ANALYZER_MODE", "mock").lower()
    if mode in {"llm", "openai", "openai_compatible"}:
        profiles = load_llm_profiles()
        if profiles:
            return LLMAnalyzer(profiles)
    return MockAnalyzer()
