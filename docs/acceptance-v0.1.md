# GitHub AI 项目雷达 v0.1 验收标准

## 验收范围

v0.1 的目标是跑通一个本地 Web 工具：能扫描 GitHub 项目、保留本地历史、展示以“灵感价值”为核心的项目情报。

用户主界面是一屏工作台：

- 左侧：灵感库、新建扫描、筛选、历史项目列表。
- 右侧：当前项目评分摘要和项目详情。

扫描过程、PASS 判断、文件选择、请求日志属于后台证据，不是 v0.1 的主要前台入口。

## 必须通过

- 仓库具备可上架 GitHub 的基本结构：`README.md`、`LICENSE`、`.gitignore`、`.env.example`、`requirements.txt`、应用代码、测试、文档。
- 面向用户的产品界面使用中文。
- GitHub、API、README、LICENSE、FastAPI、SQLite 等通用技术名词可以保留英文。
- 应用可以通过 `uvicorn app.main:app --reload` 本地启动。
- `start_radar.bat` 可以启动应用并打开本地浏览器。
- 首页 `/` 可以打开。
- 首页展示灵感库、新建扫描、项目评分和项目详情。
- 扫描表单支持 `keyword`、`scan_count`、`scan_mode`、可选 `scan_title`。
- `quick`、`standard`、`deep` 三种模式有不同文件读取预算。
- `GITHUB_TOKEN` 只从 `.env` 或系统环境变量读取。
- 不提交真实 API key。
- 没有模型 API key 时，`MockAnalyzer` 也能跑通闭环。
- `ANALYZER_MODE=llm` 时可以使用 OpenAI-compatible 模型接口，且不绑定单一模型服务。
- 每次扫描都创建 `runs` 记录。
- 每个发现的仓库创建或更新 `projects` 记录。
- 每个分析或过滤过的仓库都创建 `project_analyses` 记录。
- PASS 判断必须保存 `pass_stage` 和 `pass_reason`。
- 同一个项目重复分析时追加历史，不覆盖旧记录。
- 如果仓库未变化且搜索意图相似，可以复用上一轮判断，但必须生成新的分析记录。
- 前台不展示独立 PASS 库入口。
- 前台不展示后台/Admin 页面入口。
- 可以保留后续 PASS 复查用的内部路由或函数。
- 扫描失败必须记录到 run，并在页面上可读展示。
- 自动化测试通过。

## 自测命令

验收前至少运行：

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

浏览器检查：

- 打开 `http://127.0.0.1:8765/`。
- 确认主界面为中文。
- 确认一屏灵感库布局存在。
- 使用 `keyword=ai agent`、`scan_count=3`、`scan_mode=quick` 跑一次扫描。
- 确认 SQLite 写入 `data/radar.sqlite3`。
- 确认项目可以点开并展示评分与详情。
- 确认没有可见 PASS/Admin 导航入口。

## 成功边界

只要应用能完成一次本地扫描闭环并持久化结果，即使分析器使用 `MockAnalyzer`，v0.1 也算成功。

GitHub API rate limit、缺少可选模型 API key、搜索结果质量不稳定，不构成 v0.1 失败；但应用必须清楚记录状态和错误。

## 失败边界

出现以下情况则判定失败：

- 应用无法本地启动。
- 首页无法打开。
- 扫描导致服务进程崩溃。
- SQLite 未创建或未写入。
- 面向用户的主界面不是中文。
- 代码中写死或提交真实 API key。
- PASS 判断没有持久化。
- 重复分析覆盖旧历史。
- 测试失败。
- v0.1 前台暴露独立 PASS 库或 Admin 页面入口。

## 暂不做

- 打包 `.exe`。
- 云端部署。
- 用户账号。
- 后台任务队列。
- 完整 PASS 库前台 UI。
- Admin 控制台。
- LangChain 编排。
- 大规模抓取。
- clone 仓库。
