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
ANALYZER_MODE=mock
DATABASE_PATH=data/radar.sqlite3

LLM_PROVIDER=openai_compatible
LLM_API_KEY=
LLM_BASE_URL=
LLM_MODEL=

LLM_FALLBACK_1_API_KEY=
LLM_FALLBACK_1_BASE_URL=
LLM_FALLBACK_1_MODEL=

OPENAI_API_KEY=
```

建议配置 `GITHUB_TOKEN`，用于提高 GitHub API rate limit。没有任何模型 key 时，默认 `MockAnalyzer` 也可以跑通完整本地闭环。

## 模型 API 配置

v0.1 不绑定 Codex key。模型分析统一走 OpenAI-compatible 接口，用户可以配置 OpenAI、OpenRouter、DeepSeek、Gemini 兼容代理或其他兼容 `/chat/completions` 的服务。

默认模式：

```text
ANALYZER_MODE=mock
```

启用真实模型：

```text
ANALYZER_MODE=llm
LLM_PROVIDER=openai_compatible
LLM_API_KEY=你的模型key
LLM_BASE_URL=https://你的服务地址/v1
LLM_MODEL=你的模型名
```

如果使用 OpenAI 官方接口，也可以：

```text
ANALYZER_MODE=llm
OPENAI_API_KEY=你的OpenAI key
LLM_MODEL=你的模型名
```

如果主 key 额度用完，可以配置备用接口：

```text
LLM_FALLBACK_1_API_KEY=备用key
LLM_FALLBACK_1_BASE_URL=https://备用服务地址/v1
LLM_FALLBACK_1_MODEL=备用模型名
```

扫描时会先尝试主模型，再尝试备用模型。全部失败时会回退到本地 `MockAnalyzer`，并在原始分析 JSON 里记录失败原因。所有 key 只读取本地 `.env`，不要提交到 Git。

## 启动

```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
```

然后打开：

```text
http://127.0.0.1:8765/
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
5. 在本地灵感库里查看评分、灵感结论和可复刻实验方向。

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
- `ANALYZER_MODE=llm` 时支持 OpenAI-compatible 模型接口和最多 3 组备用接口。
- 不做云端部署、账号系统和权限系统。
- 被过滤项目会入库用于去重，但 v0.1 不展示独立 PASS 库入口。

## 发布安全

这个项目面向本地运行。发布或 fork 前请确认：

- `.env` 没有提交。
- `data/radar.sqlite3` 没有提交。
- GitHub token 和模型 API key 只保存在本地。
- 不要把个人扫描历史、日志或缓存上传到公开仓库。

## 验证

```powershell
.\.venv\Scripts\python -m pytest -q
```

验收标准记录在：

```text
docs/acceptance-v0.1.md
```
