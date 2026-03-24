# youtube-ai-to-wechat

`youtube-ai-to-wechat` 是一个面向 Codex / 本地脚本运行的内容生产 skill，用来把 YouTube 上的 AI 主题视频与补充研究，整理成适合微信公众号草稿箱的中文文章包。

当前仓库状态对应首个公开发布版本 `v0.1.0`，默认定位是“半自动生产”: 自动完成选题发现、素材整理、写作、图片规划、排版和草稿上传准备，人再审核后决定是否发布。

## 能力范围

- 基于主题词或关键词搜索 YouTube AI 内容候选
- 对候选视频做去重、启发式打分和优先级排序
- 生成 transcript/source pack，并补充官方资料线索
- 生成信息稿、微信风格改写稿、标题包和摘要
- 生成封面图、配图规划和信息图规划
- 输出微信公众号可用的 HTML、Markdown 预览和草稿 payload
- 支持按阶段重试、断点续跑、失败归因和运行状态落盘

## 当前边界

- 默认产出目标是 `draft_only`，不建议把“直接发布”作为默认流程
- 当前 transcript 阶段以 metadata fallback 为主，不是完整 ASR 管线
- 仓库没有内置依赖锁定文件，运行前需要自行准备 Python 环境
- 图片与正文链路当前默认是 MiniMax 配置，不是 OpenAI fallback

## 版本与变更

### 当前版本

- 仓库当前公开版本: `0.1.0`
- Git tag: `v0.1.0`
- 发布日期: `2026-03-24`

### Changelog

#### [0.1.0] - 2026-03-24

Initial public release.

Added:

- Published the standalone GitHub-ready repository structure for the `youtube-ai-to-wechat` skill.
- Added top-level release documentation covering scope, prerequisites, quick start, outputs, and release rules.
- Included operation, schema, config, and model/environment reference documents for the current pipeline implementation.

Included in this release:

- Topic-driven discovery flow from YouTube search to ranked candidates and source pack generation.
- Live pipeline orchestration with retry, resume, stage logs, and machine-readable run metadata.
- WeChat-oriented drafting, rewrite, formatting, asset injection, and draft payload generation.
- Image planning and generation integration via the configured Nanobanana-compatible path.
- PowerShell runner examples for preview, environment-specific execution, and OneIT-oriented workflows.

## 仓库结构

```text
.
|-- SKILL.md
|-- CONFIG.md
|-- MODEL_ENV_GUIDE.zh-CN.md
|-- OPERATIONS.md
|-- SCHEMA.md
|-- VERSIONING.md
|-- assets/
|   |-- examples/
|   |-- templates/
|   `-- blocks/
|-- references/
|-- scripts/
`-- agents/
```

## 运行前准备

最低建议环境:

- Windows PowerShell 5.1+ 或 PowerShell 7+
- Python 3.10+
- 可直接调用的 `python`
- 第三方 Python 依赖: `Pillow`

所需外部能力:

- `YOUTUBE_API_KEY`
- `MINIMAX_API_KEY`
- `WECHAT_ACCESS_TOKEN`
- 或者 `WECHAT_APP_ID` + `WECHAT_APP_SECRET`

建议先阅读:

- [`MODEL_ENV_GUIDE.zh-CN.md`](./MODEL_ENV_GUIDE.zh-CN.md)
- [`CONFIG.md`](./CONFIG.md)
- [`OPERATIONS.md`](./OPERATIONS.md)

安装最小依赖示例:

```powershell
python -m pip install Pillow
```

## 快速开始

### 1. 复制配置模板

从以下模板开始二选一:

- 通用模板: [`assets/examples/live_config.example.json`](./assets/examples/live_config.example.json)
- 生产模板: [`assets/examples/environments/live_config.prod.example.json`](./assets/examples/environments/live_config.prod.example.json)

如果你需要本地私有环境脚本，建议把真实密钥放到未纳入版本控制的本地文件中，不要直接改示例文件后提交。

### 2. 预览模式跑通一条主题链路

仓库内最直接的 PowerShell 入口:

```powershell
powershell -ExecutionPolicy Bypass -File .\assets\examples\environments\run_oneit_topic.ps1 `
  -Topic "OpenAI Agents" `
  -Keywords "OpenAI Agents","AI agents" `
  -Preview
```

这个入口会先生成:

- `search_candidates.auto.json`
- `ranked_candidates.auto.json`
- `transcript_pack.auto.json`
- `source_pack.auto.json`

再继续跑文章与排版链路，并在 `.runs/<run-name>/` 下输出预览文件和发布包。

### 3. 直接使用 Python 主入口

如果你已经有 `source_pack.json`，可以直接调用完整 live pipeline:

```powershell
python .\scripts\run_live_pipeline.py .\.runs\example\source_pack_v2.json `
  --output-dir .\.runs\2026-03-24-openai-agents-preview `
  --live-config .\assets\examples\environments\live_config.prod.example.json `
  --execute-llm `
  --max-retries 2 `
  --retry-policy smart
```

需要真的调用图片或草稿上传时，再显式加入:

- `--execute-images`
- `--execute-publish`

## 主要产物

典型运行目录位于 `.runs/<run-name>/`，常见文件包括:

- `run_live_manifest.json`
- `pipeline_summary.json`
- `run_status.json`
- `article_preview.md`
- `article_preview.html`
- `formatted_article_live.json`
- `final_article_package_live.json`
- `draft_payload_live.json`
- `stage-logs/`

更完整的字段定义见 [`SCHEMA.md`](./SCHEMA.md)。

## 作为 Codex Skill 使用

如果你把这个仓库作为 skill 直接挂载给 Codex，主入口说明在 [`SKILL.md`](./SKILL.md)。

在 `SkillsDemo` 主仓库里，也可以通过仓库级包装脚本调用:

```powershell
.\scripts\run-youtube-ai-to-wechat.ps1 -Topic "OpenAI Agents" -Preview
```

## 文档导航

- [`SKILL.md`](./SKILL.md): skill 输入契约与工作流
- [`CONFIG.md`](./CONFIG.md): 合并配置结构说明
- [`MODEL_ENV_GUIDE.zh-CN.md`](./MODEL_ENV_GUIDE.zh-CN.md): 当前实现对应的模型与环境变量速查
- [`OPERATIONS.md`](./OPERATIONS.md): 运行、重试、恢复和日常 SOP
- [`SCHEMA.md`](./SCHEMA.md): 产物结构与兼容字段
- [`VERSIONING.md`](./VERSIONING.md): 版本号与 tag 规则
- `README.md`: 当前版本号与变更记录

## 版本发布

当前版本号和变更记录统一维护在本 README 中。

发布约定:

- 使用语义化版本号 `MAJOR.MINOR.PATCH`
- Git tag 格式固定为 `vMAJOR.MINOR.PATCH`
- 每次发布前同步更新 README 中的“当前版本”和 “Changelog”
