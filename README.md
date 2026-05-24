# GitHub AI 项目雷达

这是一个本地运行的 GitHub AI 项目雷达，用来发现和沉淀真正有启发的 AI 项目。

它不是排行榜、测评站，也不是爬虫。它会搜索 GitHub，读取轻量证据，判断哪些项目值得继续看，把每次扫描和判断结果保存到本地 SQLite，并在本地 Web 页面里展示灵感库、评分和项目详情。

## 它关注什么

- AI 应用和 Agent 玩法
- 自动化和 workflow 思路
- AI 治理、eval、guardrail、权限、审计、失败处理
- 知识技巧、prompt、模板、examples、docs
- 可以本地复刻的小实验

stars 只作为背景信息，不是核心判断标准。核心问题是：这个项目能不能提供灵感源泉。

## 技术栈

- Python
- FastAPI
- SQLite
- Jinja2
- requests
- python-dotenv

## 安装

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

可选 `.env` 配置：

```text
GITHUB_TOKEN=
OPENAI_API_KEY=
CODEX_API_KEY=
ANALYZER_MODE=mock
DATABASE_PATH=data/radar.sqlite3
```

建议配置 `GITHUB_TOKEN`，用于提高 GitHub API rate limit。OpenAI/Codex key 不是 v0.1 必需项，默认 `MockAnalyzer` 可以跑通本地闭环。

## 启动

```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

然后打开：

```text
http://127.0.0.1:8000/
```

Windows 也可以直接运行：

```powershell
.\start_radar.bat
```

## 使用

1. 输入关键词，例如 `ai agent`。
2. 输入扫描数量，例如 `10`。
3. 选择 `quick`、`standard` 或 `deep`。
4. 点击“开始扫描”。
5. 在本地灵感库里查看评分、证据文件、AI 玩法和可复刻实验。

## 扫描模式

- `quick`：metadata、README、目录树，每个相关仓库最多读取 2 个关键文件。
- `standard`：metadata、README、目录树，每个相关仓库最多读取 8 个关键文件。
- `deep`：metadata、README、目录树，每个相关仓库最多读取 20 个关键文件。

系统使用 GitHub API 的 tree 接口读取目录，不 clone 仓库。

## 本地数据

运行数据保存在：

```text
data/radar.sqlite3
```

这个数据库不会提交到 git。

## 当前限制

- v0.1 同步执行扫描，不做后台队列。
- 默认分析器是规则化 `MockAnalyzer`。
- Codex/OpenAI 分析器接口已保留，但真实调用尚未实现。
- 不做云端部署、账号系统和权限系统。
- 被过滤项目会入库用于去重，但 v0.1 不展示独立 PASS 库入口。

## 验证

```powershell
.\.venv\Scripts\python -m pytest -q
```

验收标准记录在：

```text
docs/acceptance-v0.1.md
```
