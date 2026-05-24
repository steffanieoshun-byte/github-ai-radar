# GitHub 上架检查清单

这个文件用于登记 v0.1 上架 GitHub 前后的边界，避免把本地数据、密钥或临时文件带到公开仓库。

## 发布前必须确认

- `.env` 不进入 Git。
- `data/radar.sqlite3` 不进入 Git。
- `.venv/`、缓存、日志、临时文件不进入 Git。
- `.env.example` 只包含空模板，不包含真实 key。
- README 说明 GitHub token、模型 API、mock 模式和本地数据库位置。
- 测试命令 `.\.venv\Scripts\python -m pytest -q` 通过。
- 本地首页 `http://127.0.0.1:8765/` 可以打开。

## 用户下载后的配置方式

1. 复制 `.env.example` 为 `.env`。
2. 可选填写 `GITHUB_TOKEN`，提高 GitHub API 额度。
3. 默认保持 `ANALYZER_MODE=mock`，无需模型 key 也能运行。
4. 如需真实模型分析，改为 `ANALYZER_MODE=llm`，并填写：
   - `LLM_API_KEY`
   - `LLM_BASE_URL`
   - `LLM_MODEL`
5. 如果主模型额度不足，填写 `LLM_FALLBACK_1_*`、`LLM_FALLBACK_2_*` 或 `LLM_FALLBACK_3_*`。

## 发布动作

- 如果本地没有 GitHub remote，先创建远程仓库。
- 推荐仓库名：`github-ai-radar`。
- 推送默认分支。
- 打 tag：`v0.1.0`。
- GitHub 描述建议：`本地运行的 GitHub AI 项目灵感雷达，支持中文界面、SQLite 历史、多模型分析接口。`

## v0.1 不承诺

- 不承诺云端部署。
- 不承诺账号系统。
- 不承诺排行榜。
- 不承诺全自动抓取大量仓库。
- 不承诺所有模型服务都 100% 兼容，只要求支持 OpenAI-compatible `/chat/completions` 的服务。
