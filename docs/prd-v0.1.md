# 本地 GitHub AI 项目雷达 PRD v0.1

## 1. 产品定位

本项目是一个本地运行的 GitHub AI 项目雷达。

它不是 GitHub 热榜、测评网站、爬虫系统或周报系统，而是一个带记忆、带判断标准、由 Codex/API 驱动的本地灵感发现工具。

用户在本地程序中输入搜索命令后，系统自动从 GitHub 获取候选项目，逐层判断是否值得继续读取，并将有价值的项目沉淀为结构化情报卡。

最终目标不是数量多，而是持续获得高质量灵感源泉。

这里的灵感包括：

- 一个可以直接借鉴的 AI 工具玩法
- 一个小而有效的自动化技巧
- 一个 AI 治理、评估、权限、失败处理或成本控制方法
- 一个 prompt、workflow、agent、skills、docs、examples 的组织方式
- 一个可以复刻成本地 Codex 实验的小项目
- 一个能启发个人知识库、数据采集、AI 协作流程的工程模式

## 2. 用户目标

核心用户是 AI 应用架构师 / 业务型产品经理。

用户不追求从零读源码，也不追求收集最多项目，而是希望系统帮自己：

- 找到值得看的 GitHub AI 项目
- 自动过滤空泛、无关、低价值项目
- 看清一个项目为什么值得继续看
- 从项目中提炼 AI 应用、AI 治理、知识技巧和实验灵感
- 保存历史判断，避免重复扫描和重复消耗 token
- 在本地 Web 页面里回看历史扫描和项目情报卡

## 3. v0.1 核心闭环

v0.1 先跑通一个本地可用闭环：

1. 用户启动本地程序
2. 程序打开本地 Web 页面
3. 用户输入搜索关键词、扫描数量、扫描模式
4. 系统调用 GitHub API 搜索候选项目
5. 系统读取 repo metadata、topics、README 等壳信息
6. 系统执行第一道判断：壳信息是否值得看
7. 对值得看的项目读取目录树
8. 系统执行第二道判断：目录结构是否匹配当前搜索意图
9. 对继续保留的项目选择关键文件
10. 系统执行第三道判断：证据是否足够分析
11. 调用 Codex/OpenAI Analyzer 或 MockAnalyzer 生成情报卡
12. 将 PASS、分析结果、证据文件、评分和历史记录写入 SQLite
13. 用户在本地 Web 页面查看历史灵感库、项目评分和项目详情

## 4. 产品形态

参考本地 exe 程序的使用感觉：

- 用户不需要理解服务端和前端
- 双击启动脚本或程序
- 自动启动本地服务
- 自动打开浏览器
- 在本地 Web 页面操作
- 结果保存在本地

v0.1 采用轻量方式：

- 提供 `start_radar.bat` 或 `start_radar.ps1`
- 启动 FastAPI 本地服务
- 自动打开浏览器
- 暂不打包 exe

v0.2 再考虑 PyInstaller 打包成单个可执行程序。

## 5. 搜索命令标准

用户输入的 keyword 不能直接等同于 GitHub 搜索词。

系统需要先把用户输入理解成结构化搜索命令。

搜索命令至少包含：

- 原始关键词
- 搜索意图
- 扫描数量
- 扫描模式
- 搜索方向权重
- 排除规则
- 优先证据类型

v0.1 默认采用均衡扫描，而不是固定单一下拉分类。

默认搜索方向：

- AI 应用 / Agent
- 自动化 / Workflow
- AI 治理 / Eval / Guardrail
- AI 知识技巧 / Docs / Examples / Templates
- 可复刻实验 / Demo / Starter / Boilerplate

如果用户输入 scan_count=10，则系统尽量在多个方向之间均衡分配候选项目。

后续版本可以允许用户调整权重，例如提高 AI 治理方向的比例。

## 6. 带脑子的三道门

### 6.1 第一道门：壳信息判断

输入：

- repo metadata
- README
- topics
- stars / forks / language / updated_at

判断：

- 是否和当前搜索命令相关
- README 是否说明输入、输出、使用场景
- 是否只是概念宣传或空壳项目
- 是否存在继续读取目录的价值
- 是否可能带来灵感、技巧、治理启发或可复刻实验

输出：

- `PASS`
- `LIGHT`
- `ANALYZE`
- `DEEP`

若判断为 `PASS`，必须记录 pass 原因。

### 6.2 第二道门：目录匹配判断

仅对 `ANALYZE` / `DEEP` 项目读取目录树。

优先关注：

- docs/
- examples/
- example/
- src/
- app/
- apps/
- packages/
- agents/
- workflows/
- prompts/
- skills/
- evals/
- tests/
- templates/
- notebooks/
- issues / discussions 相关信息

判断：

- 当前目录结构是否匹配搜索命令
- 是否存在值得读取的关键文件
- 是否只是普通 CRUD、UI demo、无关工程

如果目录和当前搜索命令不符，记录 `PASS`，不继续读取文件。

### 6.3 第三道门：证据充分性判断

对通过第二道门的项目，按预算选择关键文件。

判断：

- 证据是否足够生成情报卡
- 证据是否能支撑 AI 玩法、治理启发、知识技巧或实验价值
- 是否需要标记为证据不足

如果证据不足，可以：

- 记录为 `LIGHT`
- 降低 evidence_quality
- 标记 unknowns
- 不编造项目能力

## 7. 文件读取预算

按 scan_mode 控制读取范围：

quick：

- metadata + README + 简单目录树
- 每个 repo 最多读取 0-2 个关键文件

standard：

- metadata + README + 完整目录树
- 每个 repo 最多读取 5-10 个关键文件

deep：

- metadata + README + 完整目录树
- 每个 repo 最多读取 15-30 个关键文件

默认跳过：

- node_modules/
- dist/
- build/
- vendor/
- .git/
- lock 文件
- 图片
- 大型数据文件
- 自动生成文件
- 超大文件

项目详情页必须显示：

- 实际读取了哪些文件
- 为什么选择这些文件
- 有哪些关键文件没有读取
- 未读取原因

## 8. PASS 留痕与去重

所有被扫到的 repo 都要进入本地记录。

即使项目被 pass，也必须记录：

- repo full_name
- GitHub URL
- 搜索关键词
- 搜索方向
- pass 阶段
- pass 原因
- README 摘要或壳信息摘要
- repo updated_at
- 本次 run_id

去重规则：

- 同一个 repo 再次出现时，不直接重复分析
- 如果 repo updated_at 未变化，且搜索意图相近，则复用旧判断
- 如果 repo 有更新，允许重新轻量判断
- 如果搜索意图明显不同，允许重新判断，但不覆盖旧分析
- 同一个项目可以有多次分析历史

项目状态建议：

- `seen`：扫到过
- `passed`：曾经判断不值得继续
- `analyzed`：已经生成过情报卡
- `watch`：值得后续观察
- `experiment_candidate`：适合转成 Codex 实验

v0.1 前端原则：

- PASS 库只做数据沉淀，不做独立页面
- 不提供后台管理入口
- 不在主界面展示三道门、请求日志、文件读取过程
- 项目详情页底部可以保留 `判断依据` 折叠区，用于后续查看 pass 原因、读取文件和去重信息
- 后续预留 `/passes` 或 `/admin/passes` 接口，但 v0.1 不暴露导航入口

## 9. 评分标准

评分不是为了排行榜，而是为了帮助用户判断项目是否能带来灵感。

建议 v0.1 使用 1-5 分。

核心评分维度：

- `direct_value`：对当前 AI 工作流是否有直接价值
- `governance_value`：是否有 AI 治理、评估、权限、审计、成本、失败处理启发
- `knowledge_density`：是否包含高密度知识技巧、模板、文档或示例
- `automation_value`：自动化流程、workflow、agent 编排是否值得学习
- `replicability`：是否能拆成本地可复刻实验
- `inspiration`：是否带来新想法、小技巧或可迁移模式
- `evidence_quality`：证据是否足够支撑判断
- `trial_difficulty`：试用难度，分数越高表示越难
- `hidden_cost`：隐藏成本，分数越高表示成本越高

最终推荐分可以采用加权平均。

默认权重暂定：

- direct_value：20%
- inspiration：20%
- replicability：15%
- governance_value：15%
- knowledge_density：10%
- automation_value：10%
- evidence_quality：10%

trial_difficulty 和 hidden_cost 作为风险项单独展示，不直接提高推荐分。

后续版本允许在本地配置中调整权重。

## 10. 分析输出格式

Analyzer 输出必须是结构化 JSON。

字段：

```json
{
  "one_line_judgment": "",
  "project_type": "",
  "problem_solved": "",
  "target_users": "",
  "input": "",
  "output": "",
  "ai_pattern": "",
  "direct_value_for_me": "",
  "governance_value": "",
  "knowledge_tips": "",
  "inspiration_value": "",
  "replicable_mvp": "",
  "hidden_costs": "",
  "key_directory_observations": "",
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
    "hidden_cost": 1
  },
  "final_action": "direct_try | deep_dive | codex_experiment | watch | skip",
  "pass_reason": "",
  "unknowns": []
}
```

规则：

- 不确定的地方写 `UNKNOWN`
- 不编造项目能力
- 每个关键结论尽量关联证据文件
- README 空泛但目录有启发时，不直接否定，可标记为需要深挖
- 热度高但对用户无用，也可以 `skip` 或 `watch`

## 11. 核心界面

v0.1 前端收敛为一个一屏工作台，而不是多个页面。

主界面路径：`/`

布局：

- 左侧：灵感库列表和扫描入口
- 右侧上半区：当前选中项目的评分摘要
- 右侧下半区：当前选中项目的情报详情

用户进入页面后，默认看到历史沉淀，而不是扫描过程。

### 11.1 左侧：灵感库

左侧是用户长期维护的唯一入口。

展示：

- 新建扫描按钮
- 当前扫描参数摘要：关键词、数量、模式
- 历史灵感列表
- 每条项目的名称、总评分、最终动作、分析时间
- 轻量筛选：全部 / Watch / Codex Experiment / 高灵感 / 最近扫描

新建扫描交互：

- 点击 `新建扫描`
- 展开或弹出轻量表单
- 字段包括 keyword、scan_count、scan_mode、scan_title
- 扫描完成后，列表刷新并选中本次最值得看的项目

左侧不展示：

- GitHub 请求日志
- 三道门过程
- 文件读取过程
- PASS 项目大表

### 11.2 右侧上半区：评分摘要

右侧上半区展示当前选中项目的核心判断。

展示：

- 项目名
- GitHub 链接
- 一句话判断
- 总评分
- 最终动作
- 灵感强度
- 可复刻性
- 治理启发
- 知识技巧密度
- 直接价值
- 试用难度
- 隐藏成本

评分区只展示结论，不展示系统如何扫描。

### 11.3 右侧下半区：项目详情

右侧下半区展示完整情报卡。

默认展示：

- 为什么值得看
- 灵感点
- 可复刻小实验
- AI 治理 / 技巧启发
- 隐藏成本
- 适合下一步怎么处理

折叠展示：

- 关键证据文件
- 读取了哪些文件
- 为什么读取这些文件
- 未读取文件
- pass / dedupe / analysis 原始判断依据
- 原始分析 JSON

按钮：

- Mark as Watch
- Mark as Codex Experiment
- Re-analyze

v0.1 中按钮可以先实现为状态标记。

### 11.4 后台与 PASS 库

v0.1 不做后台入口。

PASS 库只作为后端能力存在：

- 数据要保存
- 不能覆盖旧记录
- 允许后续通过接口查询
- 前端不提供显性入口

若需要提示用户，左侧底部只放一行弱提示：

`已过滤项目记录已保存，可在后续版本查看`

## 12. 技术方案

优先简单稳定：

- Python
- FastAPI
- SQLite
- Jinja2
- requests 或 httpx
- python-dotenv

不引入复杂前端框架。

不引入 LangChain 作为 v0.1 依赖。

Analyzer 设计：

- `AgentAdapter` 抽象接口
- `CodexAnalyzer` / `LLMAnalyzer`：主分析器，占位或按可用 API 实现
- `MockAnalyzer`：无 API key 时兜底跑通闭环

环境变量：

```text
GITHUB_TOKEN=
OPENAI_API_KEY=
CODEX_API_KEY=
```

规则：

- GitHub token 可选，但有 token 时优先使用
- API key 只从本地 `.env` 读取
- 不要求用户把真实 key 贴到聊天窗口
- 如果 Codex API 调用方式不确定，不编造，保留接口和 TODO

## 13. 数据库设计

SQLite 表：

### runs

- id
- title
- keyword
- scan_count
- scan_mode
- status
- created_at
- completed_at
- discovered_count
- analyzed_count
- passed_count
- recommended_count
- error_message

### projects

- id
- repo_full_name
- repo_url
- description
- stars
- forks
- language
- topics_json
- updated_at
- default_branch
- created_at
- last_seen_at
- last_analyzed_at
- status

### project_analyses

- id
- run_id
- project_id
- search_intent_json
- initial_decision
- pass_stage
- pass_reason
- final_action
- analysis_json
- evidence_files_json
- selected_files_json
- not_read_files_json
- scores_json
- scan_mode
- created_at

### experiment_candidates

- id
- project_id
- analysis_id
- title
- replicable_mvp
- status
- created_at

## 14. 项目目录建议

```text
E:\codex\github_ai_radar\
  app\
    main.py
    db.py
    github_client.py
    analyzer.py
    scanner.py
    models.py
    templates\
      index.html
      runs.html
      run_detail.html
      project_detail.html
    static\
  data\
    radar.sqlite3
  docs\
    prd-v0.1.md
  .env.example
  .gitignore
  requirements.txt
  README.md
  start_radar.bat
```

## 15. 非目标

v0.1 不做：

- 热榜
- 排行榜
- 云端部署
- 桌面 App
- 大规模抓取
- 自动 clone 大量仓库
- 真实账户登录
- 自动发邮件
- 多用户系统
- 复杂任务队列
- LangChain 工作流编排
- 重型前端框架

## 16. 验收标准

v0.1 完成后应满足：

- 本地服务可以启动
- 首页可以打开
- 可以输入 keyword、scan_count、scan_mode
- 可以用 `ai agent` 和 scan_count=3 跑 quick 模式
- GitHub token 存在时优先使用 token
- 无 API key 时 MockAnalyzer 也能跑通
- 扫描结果写入 SQLite
- 首页是一屏灵感库工作台
- 左侧能看到历史灵感列表和新建扫描入口
- 每条历史项目有名称、总评分、最终动作、分析时间
- 选中项目后，右侧能看到评分摘要和项目详情
- 项目详情不只展示 README 和 stars
- 项目详情展示目录观察、关键证据文件、AI 玩法、治理启发、知识技巧、灵感点、可复刻实验
- 系统在折叠区说明读取了哪些文件，以及为什么读取
- PASS 项目也记录原因
- v0.1 前端不展示 PASS 库独立入口
- v0.1 前端不展示后台管理入口
- 同一项目再次分析不会覆盖旧记录
- 运行失败有错误提示和日志，不静默失败

## 17. 已知限制

- v0.1 以同步扫描为主，扫描过程中页面可能等待
- MockAnalyzer 只能做规则化分析，不能替代真实 Codex 判断
- Codex API 调用方式如果不确定，先保留接口，不编造实现
- GitHub Search API 的结果质量受关键词影响
- Issues / Discussions 的读取可先轻量实现，避免消耗过多请求
- 初版评分权重需要通过真实扫描结果继续校准

## 18. 下一步

1. 基于本 PRD 做一版 Figma 页面原型
2. 原型确认后创建实现计划
3. 初始化项目代码
4. 跑通 v0.1 本地闭环
5. 自测并记录结果
