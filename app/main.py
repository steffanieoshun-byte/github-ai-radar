from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import db
from .github_client import GitHubClient
from .models import RepoMetadata
from .scanner import RadarScanner, make_intent


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

app = FastAPI(title="GitHub AI Radar", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/prototypes", StaticFiles(directory=str(PROJECT_DIR / "prototypes")), name="prototypes")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

ACTION_LABELS = {
    "direct_try": "直接试用",
    "deep_dive": "深挖",
    "codex_experiment": "本地实验",
    "watch": "观察",
    "skip": "略过",
}

DECISION_LABELS = {
    "PASS": "已过滤",
    "LIGHT": "轻量记录",
    "ANALYZE": "进入分析",
    "DEEP": "深度分析",
}

STATUS_LABELS = {
    "running": "运行中",
    "completed": "已完成",
    "failed": "失败",
}

PROJECT_TYPE_LABELS = {
    "Agent": "智能体",
    "RAG": "知识检索",
    "Workflow": "工作流",
    "Browser": "浏览器",
    "Coding": "代码助手",
    "Eval": "评测治理",
    "KnowledgeBase": "知识库",
    "Other": "其他",
}

MODE_LABELS = {
    "quick": "快速",
    "standard": "标准",
    "deep": "深入",
}


@app.on_event("startup")
def startup() -> None:
    with db.connection() as conn:
        db.init_db(conn)


def _score_width(value: Any) -> int:
    try:
        return max(0, min(100, int(value) * 20))
    except Exception:
        return 0


def _looks_like_raw_english(value: str) -> bool:
    letters = [ch for ch in value if ch.isalpha()]
    if len(letters) < 18:
        return False
    ascii_letters = sum(1 for ch in letters if ord(ch) < 128)
    return ascii_letters / max(len(letters), 1) > 0.72


def _cn_text(value: Any, repo_full_name: str = "") -> Any:
    if not isinstance(value, str):
        return value
    fixed = {
        "AI builders, automation users, and local workflow experimenters": "AI 应用构建者、自动化用户、本地工作流实验者",
        "Repository docs, examples, prompts, workflows, or source files": "仓库文档、示例、prompt、workflow 或源码文件",
        "Reusable project intelligence and experiment ideas": "可复用的项目情报和实验灵感",
        "Useful if its structure can improve local Codex workflows or project governance.": "如果它的结构能改进本地 Codex 工作流或项目治理，就有直接价值。",
        "Look for evals, guardrails, logs, permissions, and failure recovery patterns.": "重点观察 eval、guardrail、日志、权限、成本和失败恢复机制。",
        "Review docs, examples, templates, prompts, and setup files before reading source deeply.": "先看 docs、examples、templates、prompts 和安装配置，再决定是否读源码。",
        "Can inspire a small local experiment even if the whole project is too large to adopt.": "即使整个项目不适合采用，也可能拆出一个小技巧或小实验。",
        "Extract one workflow, prompt pattern, evaluation rule, or starter template and test it locally.": "抽取一个 workflow、prompt 模式、评测规则或 starter template，在本地做小实验。",
        "No strong docs/examples/prompts/evals directory signal found in the scanned tree.": "目录树里没有发现明显的 docs/examples/prompts/evals 等强证据信号。",
        "Evidence is thin; read more files before making a strong decision.": "证据偏薄，做强判断前需要读取更多文件。",
        "Low for this search intent.": "对当前搜索意图价值较低。",
        "Low evidence for current intent.": "当前意图下证据不足，灵感价值较低。",
        "UNKNOWN": "未知",
    }
    if value in fixed:
        return fixed[value]
    if repo_full_name and value == f"{repo_full_name} may provide reusable AI workflow or governance inspiration.":
        return f"{repo_full_name} 可能包含可复用的智能工作流、治理经验或灵感线索。"
    if repo_full_name and value == f"{repo_full_name} was filtered out for this scan.":
        return f"{repo_full_name} 在本次扫描中被过滤。"
    if repo_full_name and value == f"{repo_full_name} 可能包含可复用的 AI 工作流、治理经验或灵感线索。":
        return f"{repo_full_name} 可能包含可复用的智能工作流、治理经验或灵感线索。"
    if _looks_like_raw_english(value):
        return "原始仓库描述是英文，已保留在后台证据中；前台只展示中文判断。"
    replacements = {
        "AI 工作流": "智能工作流",
        "AI 应用": "智能应用",
        "AI ": "智能",
        "agent orchestration": "智能体编排",
        "workflow automation": "工作流自动化",
        "prompt management": "提示词管理",
        "evaluation": "评测",
        "agent": "智能体",
        "workflow": "工作流",
        "prompt": "提示词",
        "prompts": "提示词",
        "starter template": "启动模板",
        "templates": "模板",
        "examples": "示例",
        "docs": "文档",
        "eval": "评测",
        "guardrail": "防护规则",
        "guardrails": "防护规则",
    }
    translated = value
    for source, target in replacements.items():
        translated = translated.replace(source, target)
    return translated


def _display_analysis(analysis: dict[str, Any], repo_full_name: str) -> dict[str, Any]:
    display = dict(analysis)
    for key, value in list(display.items()):
        if isinstance(value, str):
            display[key] = _cn_text(value, repo_full_name)
        elif isinstance(value, list):
            display[key] = [_cn_text(item, repo_full_name) for item in value]
    return display


def _library_item(row: Any) -> dict[str, Any]:
    analysis = json.loads(row["analysis_json"])
    scores = json.loads(row["scores_json"])
    return {
        "id": int(row["id"]),
        "repo_full_name": row["repo_full_name"],
        "repo_url": row["repo_url"],
        "description": row["description"] or "No description provided.",
        "language": row["language"] or "Unknown",
        "stars": row["stars"],
        "status": row["status"],
        "final_action": row["final_action"],
        "final_action_label": ACTION_LABELS.get(row["final_action"], row["final_action"]),
        "initial_decision": row["initial_decision"],
        "initial_decision_label": DECISION_LABELS.get(row["initial_decision"], row["initial_decision"]),
        "analyzed_at": row["analyzed_at"],
        "total_score": analysis.get("total_score", 0),
        "one_line_judgment": analysis.get("one_line_judgment", ""),
        "project_type": analysis.get("project_type", "Other"),
        "project_type_label": PROJECT_TYPE_LABELS.get(analysis.get("project_type", "Other"), analysis.get("project_type", "Other")),
        "scores": scores,
    }


def _detail_view(detail: dict[str, Any] | None) -> dict[str, Any] | None:
    if not detail:
        return None
    project = detail["project"]
    analysis = detail["analysis"]
    analysis_json = _display_analysis(detail["analysis_json"], project["repo_full_name"])
    scores = detail["scores"]
    topics = []
    try:
        topics = json.loads(project.get("topics_json") or "[]")
    except Exception:
        topics = []
    metrics = [
        ("灵感强度", scores.get("inspiration", 0)),
        ("可复刻性", scores.get("replicability", 0)),
        ("治理启发", scores.get("governance_value", 0)),
        ("知识密度", scores.get("knowledge_density", 0)),
        ("自动化价值", scores.get("automation_value", 0)),
        ("直接价值", scores.get("direct_value", 0)),
        ("证据质量", scores.get("evidence_quality", 0)),
        ("试用难度", scores.get("trial_difficulty", 0)),
        ("隐藏成本", scores.get("hidden_cost", 0)),
    ]
    worth_tags = [
        f"可学：{PROJECT_TYPE_LABELS.get(analysis_json.get('project_type', 'Other'), '其他')}",
        "可能拆出小实验" if scores.get("replicability", 0) >= 3 else "先观察再决定",
    ]
    if scores.get("governance_value", 0) >= 3:
        worth_tags.append("有治理启发")
    if scores.get("knowledge_density", 0) >= 3:
        worth_tags.append("知识密度较高")
    if scores.get("automation_value", 0) >= 3:
        worth_tags.append("有自动化线索")
    worth_tags.append(ACTION_LABELS.get(analysis["final_action"], analysis["final_action"]))
    problem = analysis_json.get("problem_solved", "未知")
    if problem == "原始仓库描述是英文，已保留在后台证据中；前台只展示中文判断。":
        problem = "这个仓库的原始简介不足以直接判断价值，前台改按仓库结构、文档线索、主题和评分来判断它是否值得留下。"
    problem = str(problem).rstrip("。！？.!?")
    ai_pattern = analysis_json.get("ai_pattern", "未知")
    ai_pattern = str(ai_pattern).rstrip("。！？.!?")
    direct_value = analysis_json.get("direct_value_for_me", "未知")
    governance_value = analysis_json.get("governance_value", "未知")
    knowledge_tips = analysis_json.get("knowledge_tips", "未知")
    inspiration_value = analysis_json.get("inspiration_value", "未知")
    replicable_mvp = analysis_json.get("replicable_mvp", "未知")
    hidden_costs = analysis_json.get("hidden_costs", "未知")
    worth_intro = (
        f"这条进入前台，不是因为热度，而是因为它可能提供“{PROJECT_TYPE_LABELS.get(analysis_json.get('project_type', 'Other'), '其他')}”方向的灵感。"
        f"当前看到的核心玩法是：{ai_pattern}。"
    )
    return {
        "project": project,
        "analysis": analysis,
        "analysis_json": analysis_json,
        "mode_labels": MODE_LABELS,
        "scores": scores,
        "topics": topics,
        "selected_files": detail["selected_files"],
        "not_read_files": detail["not_read_files"],
        "evidence_files": detail["evidence_files"],
        "metrics": [{"name": name, "value": value, "width": _score_width(value)} for name, value in metrics],
        "raw_json": json.dumps(analysis_json, ensure_ascii=False, indent=2),
        "final_action_label": ACTION_LABELS.get(analysis["final_action"], analysis["final_action"]),
        "initial_decision_label": DECISION_LABELS.get(analysis["initial_decision"], analysis["initial_decision"]),
        "project_type_label": PROJECT_TYPE_LABELS.get(analysis_json.get("project_type", "Other"), analysis_json.get("project_type", "Other")),
        "worth_intro": worth_intro,
        "worth_tags": worth_tags,
        "inspiration_paragraphs": [
            f"它大概在做什么：{problem}。我关心的不是这个仓库本身有多大，而是它有没有把一个智能工作流、治理方法、知识技巧或自动化动作讲清楚。",
            f"可能带来的灵感：{inspiration_value} {direct_value} 如果它能展示新的组织方式、流程拆法、边界控制或小技巧，就值得留下。",
            f"最小可复刻动作：{replicable_mvp} 这个动作应该足够小，可以在本地先做一个实验，而不是一上来复刻整个项目。",
            f"继续阅读的判断：{knowledge_tips} {governance_value} 成本侧要注意：{hidden_costs}。",
        ],
    }


def _workspace_context(
    request: Request,
    filter_name: str,
    project_id: int | None,
    run_id: int | None,
    message: str = "",
) -> dict[str, Any]:
    with db.connection() as conn:
        db.init_db(conn)
        library = [_library_item(row) for row in db.list_library(conn, filter_name)]
        selected_id = project_id or (library[0]["id"] if library else None)
        detail = _detail_view(db.get_project_detail(conn, selected_id))
        runs = [dict(row) for row in db.list_runs(conn)]
        active_run = dict(db.get_run(conn, run_id)) if run_id else None
    return {
        "request": request,
        "library": library,
        "detail": detail,
        "runs": runs,
        "active_run": active_run,
        "status_labels": STATUS_LABELS,
        "mode_labels": MODE_LABELS,
        "filter_name": filter_name,
        "message": message,
    }


@app.get("/")
def index(
    request: Request,
    filter: str = "all",
    project_id: int | None = None,
    run_id: int | None = None,
    message: str = "",
) -> Any:
    return templates.TemplateResponse(
        "index.html",
        _workspace_context(request, filter, project_id, run_id, message),
    )


@app.post("/scan")
def scan(
    scan_title: str = Form(""),
    keyword: str = Form(...),
    scan_count: int = Form(10),
    scan_mode: str = Form("quick"),
) -> RedirectResponse:
    with db.connection() as conn:
        db.init_db(conn)
        run_id = RadarScanner().run(conn, scan_title, keyword, scan_count, scan_mode)
    return RedirectResponse(f"/?run_id={run_id}", status_code=303)


@app.post("/projects/{project_id}/mark")
def mark_project(project_id: int, status: str = Form(...)) -> RedirectResponse:
    allowed = {
        "watch": "watch",
        "experiment": "experiment_candidate",
        "seen": "seen",
    }
    with db.connection() as conn:
        db.init_db(conn)
        if status in allowed:
            db.update_project_status(conn, project_id, allowed[status])
    return RedirectResponse(f"/?project_id={project_id}&message=项目状态已更新", status_code=303)


@app.post("/projects/{project_id}/hide")
def hide_project(project_id: int) -> RedirectResponse:
    with db.connection() as conn:
        db.init_db(conn)
        db.update_project_status(conn, project_id, "hidden")
    return RedirectResponse("/?message=已从前台移除，后台仍保留记录", status_code=303)


@app.post("/projects/{project_id}/reanalyze")
def reanalyze_project(project_id: int, scan_mode: str = Form("quick")) -> RedirectResponse:
    with db.connection() as conn:
        db.init_db(conn)
        project = db.get_project(conn, project_id)
        if not project:
            return RedirectResponse("/?message=项目不存在", status_code=303)
        topics = json.loads(project["topics_json"] or "[]")
        repo = RepoMetadata(
            full_name=project["repo_full_name"],
            html_url=project["repo_url"],
            description=project["description"] or "",
            stars=int(project["stars"] or 0),
            forks=int(project["forks"] or 0),
            language=project["language"] or "",
            topics=topics,
            updated_at=project["updated_at"] or "",
            default_branch=project["default_branch"] or "main",
        )
        intent = make_intent(repo.full_name, 1, scan_mode, f"Re-analyze {repo.full_name}")
        run_id = db.create_run(conn, intent.title, intent.keyword, 1, intent.scan_mode)
        try:
            result = RadarScanner(client=GitHubClient())._process_repo(conn, run_id, repo, intent, force=True)
            analyzed = 0 if result["final_action"] == "skip" else 1
            passed = 1 if result["final_action"] == "skip" else 0
            recommended = 0 if result["final_action"] == "skip" else 1
            db.complete_run(conn, run_id, "completed", 1, analyzed, passed, recommended)
        except Exception as exc:
            db.complete_run(conn, run_id, "failed", 1, 0, 0, 0, str(exc))
    return RedirectResponse(f"/?project_id={project_id}&run_id={run_id}", status_code=303)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/internal/passes")
def internal_passes(limit: int = 50) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 200))
    with db.connection() as conn:
        db.init_db(conn)
        rows = conn.execute(
            """
            SELECT p.repo_full_name, p.repo_url, a.pass_stage, a.pass_reason, a.created_at
            FROM project_analyses a
            JOIN projects p ON p.id = a.project_id
            WHERE a.final_action = 'skip'
            ORDER BY a.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
