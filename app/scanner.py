from __future__ import annotations

import json
from collections import OrderedDict
from typing import Any

from . import db
from .analyzer import AI_TERMS, MockAnalyzer, get_analyzer
from .github_client import GitHubClient
from .models import RepoMetadata, SearchIntent, SelectedFile


DIRECTIONS = [
    "agent workflow",
    "automation workflow",
    "eval guardrails",
    "prompts examples templates",
    "starter demo boilerplate",
]

PRIORITY_PREFIXES = (
    "docs/",
    "examples/",
    "example/",
    "agents/",
    "workflows/",
    "prompts/",
    "skills/",
    "evals/",
    "templates/",
    "notebooks/",
    "src/",
    "app/",
)

PRIORITY_FILES = {
    "README.md",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "docker-compose.yml",
    "Dockerfile",
}

SKIP_PARTS = {
    "node_modules",
    "dist",
    "build",
    "vendor",
    ".git",
    "__pycache__",
    ".pytest_cache",
}

SKIP_SUFFIXES = (
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".lock",
)

MODE_BUDGETS = {"quick": 2, "standard": 8, "deep": 20}


def make_intent(keyword: str, scan_count: int, scan_mode: str, title: str = "") -> SearchIntent:
    mode = scan_mode if scan_mode in MODE_BUDGETS else "quick"
    count = max(1, min(int(scan_count), 30))
    return SearchIntent(keyword=keyword.strip(), scan_count=count, scan_mode=mode, title=title.strip(), directions=DIRECTIONS)


def build_queries(intent: SearchIntent) -> list[str]:
    base = f"{intent.keyword} in:name,description,readme fork:false archived:false"
    queries = [base]
    for direction in intent.directions:
        queries.append(f"{intent.keyword} {direction} in:name,description,readme fork:false archived:false")
    return queries[: max(1, min(len(queries), intent.scan_count + 1))]


def shell_decision(repo: RepoMetadata, readme: str, intent: SearchIntent) -> tuple[str, str]:
    shell_blob = " ".join([repo.full_name, repo.description, " ".join(repo.topics), readme[:4000]]).lower()
    ai_hits = sum(1 for term in AI_TERMS if term in shell_blob)
    keyword_terms = {term for term in intent.keyword.lower().replace("-", " ").split() if len(term) >= 3}
    keyword_hits = sum(1 for term in keyword_terms if term in shell_blob)
    evidence_terms = {"example", "examples", "template", "demo", "docs", "quickstart", "workflow", "eval", "guardrail"}
    evidence_hits = sum(1 for term in evidence_terms if term in shell_blob)
    if not readme.strip() and ai_hits == 0 and keyword_hits == 0:
        return "PASS", "没有 README 信号，且 AI/自动化相关性较弱。"
    if ai_hits >= 5 or (keyword_hits >= 2 and evidence_hits >= 2):
        return "DEEP", ""
    if ai_hits >= 2 or keyword_hits >= 2 or (keyword_hits >= 1 and evidence_hits >= 1):
        return "ANALYZE", ""
    if ai_hits >= 1 or keyword_hits >= 1:
        return "LIGHT", ""
    return "PASS", "壳信息与当前 AI 灵感搜索意图不匹配。"


def tree_matches(tree_paths: list[str]) -> tuple[bool, str]:
    interesting = [
        path
        for path in tree_paths
        if path.startswith(PRIORITY_PREFIXES) or path.split("/")[-1] in PRIORITY_FILES
    ]
    if interesting:
        return True, ""
    return False, "目录树缺少 docs、examples、prompts、workflows、evals、skills 或 starter 证据。"


def eligible_path(path: str) -> bool:
    parts = set(path.split("/"))
    if parts & SKIP_PARTS:
        return False
    lowered = path.lower()
    return not lowered.endswith(SKIP_SUFFIXES)


def select_files(tree_paths: list[str], mode: str) -> tuple[list[SelectedFile], list[dict[str, str]]]:
    budget = MODE_BUDGETS.get(mode, 2)
    candidates: list[tuple[int, str, str]] = []
    for path in tree_paths:
        if not eligible_path(path):
            continue
        name = path.split("/")[-1]
        if name in PRIORITY_FILES:
            candidates.append((0, path, "standard project metadata or setup file"))
        elif path.startswith(("docs/", "examples/", "example/")):
            candidates.append((1, path, "documentation or runnable example"))
        elif path.startswith(("agents/", "workflows/", "prompts/", "skills/", "evals/")):
            candidates.append((2, path, "agent, prompt, workflow, skill, or evaluation evidence"))
        elif path.startswith(("src/", "app/")) and len(path.split("/")) <= 4:
            candidates.append((3, path, "small source entry point"))
    ordered = sorted(candidates, key=lambda item: (item[0], len(item[1]), item[1]))
    selected = [SelectedFile(path=path, reason=reason) for _, path, reason in ordered[:budget]]
    selected_paths = {item.path for item in selected}
    not_read = [
        {"path": path, "reason": "outside scan mode budget"}
        for _, path, _ in ordered[budget : budget + 20]
        if path not in selected_paths
    ]
    return selected, not_read


def similar_intent(previous_json: str, intent: SearchIntent) -> bool:
    return intent.keyword.lower() in previous_json.lower() or previous_json.lower() in intent.keyword.lower()


class RadarScanner:
    def __init__(self, client: GitHubClient | None = None, analyzer: Any | None = None) -> None:
        self.client = client or GitHubClient()
        self.analyzer = analyzer or get_analyzer()

    def run(self, conn: Any, title: str, keyword: str, scan_count: int, scan_mode: str) -> int:
        intent = make_intent(keyword, scan_count, scan_mode, title)
        run_id = db.create_run(conn, intent.title, intent.keyword, intent.scan_count, intent.scan_mode)
        discovered: OrderedDict[str, RepoMetadata] = OrderedDict()
        analyzed_count = 0
        passed_count = 0
        recommended_count = 0
        try:
            queries = build_queries(intent)
            per_query = max(1, min(10, intent.scan_count))
            for query in queries:
                for repo in self.client.search_repositories(query, per_page=per_query):
                    if repo.full_name not in discovered:
                        discovered[repo.full_name] = repo
                    if len(discovered) >= intent.scan_count:
                        break
                if len(discovered) >= intent.scan_count:
                    break
            for repo in list(discovered.values())[: intent.scan_count]:
                result = self._process_repo(conn, run_id, repo, intent)
                if result["initial_decision"] == "PASS":
                    passed_count += 1
                else:
                    analyzed_count += 1
                if result["final_action"] in {"direct_try", "deep_dive", "codex_experiment", "watch"}:
                    recommended_count += 1
            db.complete_run(
                conn,
                run_id,
                "completed",
                len(discovered),
                analyzed_count,
                passed_count,
                recommended_count,
            )
        except Exception as exc:
            db.complete_run(conn, run_id, "failed", len(discovered), analyzed_count, passed_count, recommended_count, str(exc))
        return run_id

    def _process_repo(
        self,
        conn: Any,
        run_id: int,
        repo: RepoMetadata,
        intent: SearchIntent,
        force: bool = False,
    ) -> dict[str, str]:
        project_id = db.upsert_project(conn, repo.as_dict())
        latest = db.latest_analysis(conn, project_id)
        if latest and not force and similar_intent(latest["search_intent_json"], intent):
            latest_analysis = json.loads(latest["analysis_json"])
            if latest_analysis.get("analysis_version") == "0.1":
                return self._reuse_previous_analysis(conn, run_id, project_id, intent, latest)
        readme = self.client.get_readme(repo.full_name)
        decision, reason = shell_decision(repo, readme, intent)
        if decision == "PASS":
            analysis = self._pass_analysis(repo, reason)
            db.insert_analysis(
                conn,
                run_id,
                project_id,
                intent.as_dict(),
                "PASS",
                "skip",
                analysis,
                [],
                [],
                [],
                intent.scan_mode,
                pass_stage="shell",
                pass_reason=reason,
            )
            return {"initial_decision": "PASS", "final_action": "skip"}
        tree_paths = self.client.get_tree(repo.full_name, repo.default_branch)
        if decision in {"ANALYZE", "DEEP"}:
            matched, tree_reason = tree_matches(tree_paths)
            if not matched:
                analysis = self._pass_analysis(repo, tree_reason)
                db.insert_analysis(
                    conn,
                    run_id,
                    project_id,
                    intent.as_dict(),
                    "PASS",
                    "skip",
                    analysis,
                    [],
                    [],
                    [],
                    intent.scan_mode,
                    pass_stage="tree",
                    pass_reason=tree_reason,
                )
                return {"initial_decision": "PASS", "final_action": "skip"}
        selected, not_read = select_files(tree_paths, intent.scan_mode)
        hydrated = []
        for item in selected:
            content = self.client.get_file_text(repo.full_name, item.path, repo.default_branch)
            hydrated.append(SelectedFile(path=item.path, reason=item.reason, content=content))
        analysis = self.analyzer.analyze(repo, intent, readme, tree_paths, hydrated)
        final_action = analysis.get("final_action", "watch")
        db.insert_analysis(
            conn,
            run_id,
            project_id,
            intent.as_dict(),
            decision,
            final_action,
            analysis,
            analysis.get("evidence_files", []),
            [file.as_dict() for file in hydrated],
            not_read,
            intent.scan_mode,
        )
        return {"initial_decision": decision, "final_action": final_action}

    def _reuse_previous_analysis(
        self,
        conn: Any,
        run_id: int,
        project_id: int,
        intent: SearchIntent,
        latest: Any,
    ) -> dict[str, str]:
        analysis = json.loads(latest["analysis_json"])
        evidence_files = json.loads(latest["evidence_files_json"])
        selected_files = json.loads(latest["selected_files_json"])
        not_read_files = json.loads(latest["not_read_files_json"])
        analysis["reused_from_analysis_id"] = int(latest["id"])
        analysis.setdefault("unknowns", [])
        db.insert_analysis(
            conn,
            run_id,
            project_id,
            intent.as_dict(),
            latest["initial_decision"],
            latest["final_action"],
            analysis,
            evidence_files,
            selected_files,
            not_read_files,
            intent.scan_mode,
            pass_stage="reuse" if latest["final_action"] == "skip" else (latest["pass_stage"] or ""),
            pass_reason=latest["pass_reason"] or "",
        )
        return {"initial_decision": latest["initial_decision"], "final_action": latest["final_action"]}

    def _pass_analysis(self, repo: RepoMetadata, reason: str) -> dict[str, Any]:
        return {
            "analysis_version": "0.1",
            "one_line_judgment": f"{repo.full_name} 在本次扫描中被过滤。",
            "project_type": "Other",
            "problem_solved": repo.description or "未知",
            "target_users": "未知",
            "input": "未知",
            "output": "未知",
            "ai_pattern": "未知",
            "direct_value_for_me": "对当前搜索意图价值较低。",
            "governance_value": "未知",
            "knowledge_tips": "未知",
            "inspiration_value": "当前意图下证据不足，灵感价值较低。",
            "replicable_mvp": "未知",
            "hidden_costs": "未知",
            "key_directory_observations": reason,
            "evidence_files": [],
            "selected_files": [],
            "not_read_files": [],
            "scores": {
                "direct_value": 1,
                "governance_value": 1,
                "knowledge_density": 1,
                "automation_value": 1,
                "replicability": 1,
                "inspiration": 1,
                "evidence_quality": 1,
                "trial_difficulty": 1,
                "hidden_cost": 1,
            },
            "total_score": 1.0,
            "final_action": "skip",
            "pass_reason": reason,
            "unknowns": [reason],
        }
