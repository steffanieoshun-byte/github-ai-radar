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


def _has_any(blob: str, terms: tuple[str, ...]) -> bool:
    return any(term in blob for term in terms)


def _path_hint(paths: list[str]) -> str:
    cleaned = [path for path in paths if path][:4]
    if not cleaned:
        return "README 和目录结构"
    return "、".join(cleaned)


def infer_focus_profile(
    repo_full_name: str,
    description: str = "",
    topics: list[str] | None = None,
    tree_paths: list[str] | None = None,
    selected_paths: list[str] | None = None,
    content_snippets: list[str] | None = None,
    project_type: str = "Other",
) -> dict[str, str]:
    topics = topics or []
    tree_paths = tree_paths or []
    selected_paths = selected_paths or []
    content_snippets = content_snippets or []
    summary_blob = " ".join(
        [
            repo_full_name,
            description,
            " ".join(topics),
            " ".join(tree_paths[:300]),
            " ".join(selected_paths),
        ]
    ).lower()
    blob = " ".join(
        [
            repo_full_name,
            description,
            " ".join(topics),
            " ".join(tree_paths[:300]),
            " ".join(selected_paths),
            " ".join(snippet[:1200] for snippet in content_snippets),
        ]
    ).lower()
    files = _path_hint(selected_paths or tree_paths[:4])
    hidden_costs = "未知"
    if _has_any(blob, ("api key", "cloud", "paid", "hosted", "kubernetes", "docker-compose")):
        hidden_costs = "可能有外部服务、托管接口、账号额度或较重部署环境，需要先做小范围验证。"
    strong_workflow = _has_any(
        summary_blob,
        ("workflow", "automation", "connector", "integration", "no-code", "n8n", "activepieces"),
    )
    strong_learning = _has_any(
        summary_blob,
        ("tutorial", "course", "courses/", "notebook", "cookbook", "learn", "learning", "ai-engineering-hub"),
    )
    explicit_multi_agent = _has_any(
        summary_blob,
        ("agency", "role-playing", "role playing", "crew", "multi-agent", "multiagent", "autonomous ai agents", "autonomous agents"),
    )

    if strong_workflow and not explicit_multi_agent:
        return {
            "category": "工作流自动化",
            "learn_label": "流程连接",
            "experiment_label": "自动化小动作",
            "audience_label": "流程改造",
            "core_play": "把触发器、步骤、工具和外部服务串成可运行流程",
            "problem_solved": f"{repo_full_name} 更像一个工作流自动化样本，重点是看它如何连接工具、触发动作、处理状态和复用流程。",
            "target_users": "想把日常任务、资料处理或智能体动作自动化的人",
            "output": "可拆成小步骤的自动化流程、连接器思路和运行入口",
            "direct_value_for_me": "它可能直接启发本地扫描、整理、归档或智能体协作流程。",
            "governance_value": "重点看它如何处理权限、失败重试、日志、成本和外部服务边界。",
            "knowledge_tips": f"先看 {files}，确认有没有清晰的流程入口、连接器示例和部署方式。",
            "inspiration_value": "灵感来自流程拆法和连接器设计，哪怕只复用一个触发动作也有价值。",
            "replicable_mvp": "挑一个触发器加一个动作，做成本地小自动化，而不是复刻整套平台。",
            "hidden_costs": hidden_costs,
        }

    if strong_learning and not explicit_multi_agent:
        return {
            "category": "知识技巧和案例教程",
            "learn_label": "案例拆解",
            "experiment_label": "摘一个练习",
            "audience_label": "学习和复盘",
            "core_play": "把知识点、案例和实验路径整理成可以逐步复现的材料",
            "problem_solved": f"{repo_full_name} 更像一个知识和案例库，价值不在工具本身，而在它把学习路径、示例和实验线索集中到一起。",
            "target_users": "想系统补充智能应用知识、案例和实验素材的人",
            "output": "可拆解的学习条目、案例路径和本地小练习",
            "direct_value_for_me": "它适合作为知识补给源，帮助快速找到可继续深挖的主题和案例。",
            "governance_value": "如果里面有评测、防护、权限或失败处理内容，就可以补成治理清单。",
            "knowledge_tips": f"先看 {files}，判断它是教程目录、案例集合还是单点资料。",
            "inspiration_value": "灵感主要来自案例组织方式、主题分组和可复现练习，而不是直接采用整个仓库。",
            "replicable_mvp": "挑一个最小教程或案例，改写成自己的本地实验记录，再决定是否继续扩展。",
            "hidden_costs": hidden_costs,
        }

    if explicit_multi_agent:
        return {
            "category": "多智能体协作",
            "learn_label": "角色分工",
            "experiment_label": "角色协作小实验",
            "audience_label": "智能体编排",
            "core_play": "把角色、任务、工具和执行边界组织成可复用流程",
            "problem_solved": f"{repo_full_name} 更像一个多智能体协作样本，重点是观察它如何拆角色、分任务、传递上下文和收束结果。",
            "target_users": "想改进本地智能体协作、任务分工和交付流程的人",
            "output": "角色分工模板、任务编排方式和可复刻的协作流程",
            "direct_value_for_me": "它能帮助拆出本地 Codex 协作里的角色、检查点和交付物边界。",
            "governance_value": "重点看它有没有定义角色权限、任务终止条件、失败恢复和人工介入点。",
            "knowledge_tips": f"先看 {files}，确认角色定义、任务入口和示例流程是否清楚。",
            "inspiration_value": "灵感来自角色拆分、协作顺序和边界控制，小技巧也值得留下。",
            "replicable_mvp": "抽一个两到三个角色的协作流程，在本地做一次小任务编排实验。",
            "hidden_costs": hidden_costs,
        }

    if _has_any(blob, ("mcp", "tool server", "tool-server", "server tools")):
        return {
            "category": "工具协议接入",
            "learn_label": "工具接入",
            "experiment_label": "接一个工具",
            "audience_label": "本地工具化",
            "core_play": "把外部能力包装成智能体可调用的工具接口",
            "problem_solved": f"{repo_full_name} 更像一个工具接入样本，重点是看它如何把外部服务、命令或数据源变成可调用能力。",
            "target_users": "想给本地智能体补工具、数据源或自动化接口的人",
            "output": "工具接口设计、调用边界和可复用的接入方式",
            "direct_value_for_me": "它可能启发把本地脚本、文件治理或扫描能力接进智能体工作台。",
            "governance_value": "重点看调用权限、输入校验、日志和失败兜底。",
            "knowledge_tips": f"先看 {files}，确认接口定义、调用样例和安全边界。",
            "inspiration_value": "灵感来自工具包装方式和调用边界，适合拆成一个本地工具接入实验。",
            "replicable_mvp": "选一个最小工具接口，接入本地脚本并让智能体调用一次。",
            "hidden_costs": hidden_costs,
        }

    if _has_any(blob, ("eval", "evaluation", "guardrail", "policy", "audit", "permission", "trace", "logging")):
        return {
            "category": "治理和评测",
            "learn_label": "规则设计",
            "experiment_label": "加一条规则",
            "audience_label": "质量控制",
            "core_play": "用规则、评测、日志或权限边界约束智能系统",
            "problem_solved": f"{repo_full_name} 更像一个治理或评测样本，重点是看它如何判断输出质量、约束行为和保留过程记录。",
            "target_users": "想给智能体流程增加质量检查、权限边界和失败记录的人",
            "output": "评测规则、防护边界、日志字段和异常处理思路",
            "direct_value_for_me": "它可以直接补进本地项目门禁、复盘或自动化执行前后的检查。",
            "governance_value": "重点看规则是否可解释、是否有记录、是否能失败后恢复。",
            "knowledge_tips": f"先看 {files}，确认规则、评测用例和日志结构。",
            "inspiration_value": "灵感来自治理动作本身：一条小规则、一个检查点或一份日志结构都值得留下。",
            "replicable_mvp": "抽一条评测或防护规则，接到本地扫描后的判断流程里。",
            "hidden_costs": hidden_costs,
        }

    if _has_any(blob, ("rag", "knowledge", "retrieval", "memory", "document")) or project_type == "KnowledgeBase":
        return {
            "category": "知识库和检索",
            "learn_label": "知识组织",
            "experiment_label": "建一条检索链路",
            "audience_label": "知识沉淀",
            "core_play": "把资料整理、检索和回答链路连接起来",
            "problem_solved": f"{repo_full_name} 更像一个知识组织样本，重点是看它如何切分资料、检索信息和形成可复用回答。",
            "target_users": "想积累智能应用知识、项目资料和可查询经验的人",
            "output": "知识结构、检索链路和可复用资料组织方式",
            "direct_value_for_me": "它可能启发本地知识库、经验库或扫描结果复盘方式。",
            "governance_value": "重点看来源记录、更新机制、权限边界和回答证据。",
            "knowledge_tips": f"先看 {files}，确认资料入口、索引方式和示例问题。",
            "inspiration_value": "灵感来自知识组织结构和检索路径，适合拆出一个小型资料库实验。",
            "replicable_mvp": "用少量本地文档做一个最小检索链路，验证资料组织方式。",
            "hidden_costs": hidden_costs,
        }

    return {
        "category": "可观察项目样本",
        "learn_label": "结构观察",
        "experiment_label": "保留线索",
        "audience_label": "灵感筛选",
        "core_play": "从文档、目录和示例里判断是否有可复用做法",
        "problem_solved": f"{repo_full_name} 目前更适合先作为观察对象，重点是判断它是否藏着可复用流程、知识技巧或治理经验。",
        "target_users": "想从开源项目里筛出灵感线索的人",
        "output": "待确认的结构线索、阅读方向和小实验假设",
        "direct_value_for_me": "直接价值还不确定，但可以用来训练筛选标准。",
        "governance_value": "如果后续发现评测、权限、日志或失败处理，再提高治理价值。",
        "knowledge_tips": f"先看 {files}，不要急着读源码。",
        "inspiration_value": "灵感仍需继续确认，先看是否有新组织方式、小技巧或边界控制。",
        "replicable_mvp": "先只记录一个可验证假设，等读到明确示例再做本地实验。",
        "hidden_costs": hidden_costs,
    }


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
        focus = infer_focus_profile(
            repo_full_name=repo.full_name,
            description=repo.description,
            topics=repo.topics,
            tree_paths=tree_paths,
            selected_paths=[file.path for file in selected_files],
            content_snippets=[file.content for file in selected_files],
            project_type=project_type,
        )
        project_type = {
            "多智能体协作": "Agent",
            "工作流自动化": "Workflow",
            "工具协议接入": "Workflow",
            "治理和评测": "Eval",
            "知识库和检索": "KnowledgeBase",
            "知识技巧和案例教程": "KnowledgeBase",
        }.get(focus["category"], project_type)
        return {
            "analysis_version": "0.1",
            "one_line_judgment": f"{repo.full_name} 更像一个{focus['category']}，适合观察{focus['learn_label']}。",
            "project_type": project_type,
            "problem_solved": focus["problem_solved"],
            "target_users": focus["target_users"],
            "input": "仓库文档、示例、提示词、工作流或源码文件",
            "output": focus["output"],
            "ai_pattern": self._ai_pattern(lowered),
            "direct_value_for_me": focus["direct_value_for_me"],
            "governance_value": focus["governance_value"],
            "knowledge_tips": focus["knowledge_tips"],
            "inspiration_value": focus["inspiration_value"],
            "replicable_mvp": focus["replicable_mvp"],
            "hidden_costs": "未知" if hidden_cost <= 2 else focus["hidden_costs"],
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
        if "mcp" in lowered:
            patterns.append("工具协议接入")
        if "agent" in lowered:
            patterns.append("智能体编排")
        if "workflow" in lowered:
            patterns.append("工作流自动化")
        if "eval" in lowered:
            patterns.append("评测治理")
        if "prompt" in lowered:
            patterns.append("提示词管理")
        if "rag" in lowered:
            patterns.append("知识检索")
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
