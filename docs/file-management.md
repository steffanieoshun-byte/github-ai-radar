# 文件管理注册表

这个文件定义各类文件的职责边界，避免后续把原型、运行数据、测试输出和正式代码混在一起。

## 产品文档

- `docs/prd-v0.1.md`：产品定位、边界、核心流程和 UX 决策。
- `docs/acceptance-v0.1.md`：验收范围、成功边界、失败边界和自测要求。
- `docs/file-management.md`：本文件，登记文件职责与后续维护规则。
- `docs/github-release-checklist.md`：GitHub 上架前检查项和发布边界。

## 应用代码

- `app/main.py`：FastAPI 路由、启动初始化、表单处理、页面渲染。
- `app/db.py`：SQLite 表结构、连接工具、扫描/项目/分析结果持久化。
- `app/github_client.py`：GitHub REST API 访问，只读接口，不 clone 仓库。
- `app/analyzer.py`：`AgentAdapter`、`MockAnalyzer`、OpenAI-compatible `LLMAnalyzer` 和备用模型接口读取。
- `app/scanner.py`：扫描编排、搜索意图扩展、三道判断门、去重、文件读取预算。
- `app/models.py`：扫描器、分析器、模板共享的数据结构。
- `app/templates/index.html`：中文一屏工作台 UI。
- `app/static/styles.css`：本地工作台样式。

## 本地数据

- `data/.gitkeep`：保留数据目录。
- `data/radar.sqlite3`：本地运行数据库，不提交 git。

## GitHub 上架文件

- `README.md`：项目说明、安装、启动、使用、限制。
- `LICENSE`：项目许可证。
- `.gitignore`：排除密钥、本地数据库、缓存、虚拟环境和临时文件。
- `.env.example`：安全的环境变量模板，不放真实 key。
- `requirements.txt`：运行和测试依赖。
- `start_radar.bat`：Windows 本地启动脚本。

## 测试

- `tests/test_analyzer.py`：分析器和评分行为。
- `tests/test_db.py`：SQLite 持久化和历史不覆盖。
- `tests/test_scanner.py`：搜索意图、文件预算、PASS/去重逻辑。

## 原型

- `prototypes/prototype-v0.1.html`：设计评审用中文静态原型，不是生产 UI。

## 边界

- 不提交 `.env`、`data/radar.sqlite3`、缓存、虚拟环境、临时截图。
- 不在仓库根目录放无关实验。
- 产品文档放 `docs/`。
- 正式应用代码放 `app/`。
- 验证代码放 `tests/`。
