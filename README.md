# youtube-ai-to-wechat

`youtube-ai-to-wechat` 是一个面向 Codex / 本地脚本运行的内容生产 skill，用来把 YouTube 上的 AI 主题视频与补充研究，整理成适合微信公众号草稿箱的中文文章包。

当前仓库状态对应公开发布版本 `v0.2.1`。默认定位是“半自动生产”：自动完成选题发现、素材整理、写作、图片规划、排版和草稿上传准备，再由人工审核后决定是否发布。

## 能力范围

- 基于主题词或关键词搜索 YouTube AI 内容候选
- 对候选视频做去重、启发式打分和优先级排序
- 生成 transcript / source pack，并补充官方资料线索
- 生成信息稿、微信风格改写稿、标题包和摘要
- 生成封面图、配图规划和信息图规划
- 输出微信公众号可用的 HTML、Markdown 预览和草稿 payload
- 支持按阶段重试、断点续跑、失败归因和运行状态落盘

## 当前边界

- 默认产出目标是 `draft_only`，不建议把“直接发布”作为默认流程
- 当前 transcript 阶段以 metadata fallback 为主，不是完整 ASR 管线
- 仓库没有内置依赖锁定文件，运行前需要自行准备 Python 环境
- 生产模板默认按官方来源优先抓图，找不到时才回退 `Wikimedia`，不再默认使用模型生图

## 版本与变更

### 当前版本

- 仓库当前公开版本: `0.2.1`
- Git 标签: `v0.2.1`
- 发布时间: `2026-03-25`

### 变更记录

#### [0.2.1] - 2026-03-25

本次修复:

- 修复 `README.md` 中文文本编码异常，恢复正常可读内容
- 保留 `v0.2.0` 引入的仓库内 prompt / runner 入口说明，并以正确 UTF-8 文本重写相关章节

#### [0.2.0] - 2026-03-25

本次新增:

- 新增仓库内可直接维护的公开入口 `prompts/youtube-ai-to-wechat.prompt.md` 和 `scripts/run-youtube-ai-to-wechat.ps1`
- 明确 prompt 模板和运行脚本的 canonical 维护位置在当前 skill 仓库内，便于独立发布与版本追踪
- 补充 README 使用说明，增加仓库内 prompt / runner 入口和文档导航

#### [0.1.1] - 2026-03-24

本次修复:

- 研究阶段把 `topic` 和 `keywords` 纳入实体识别，补齐 `wechat`、`tencent`、`n8n` 的官方资源映射，避免“相关资源”段落为空
- 调整图片抓取策略为官方来源优先，并按章节语义、来源实体和页面元信息排序，提高正文配图与内容的相关性
- 修正封面图、内图和信息图的正文挂载规则，避免把文章标题误当成首个配图章节

#### [0.1.0] - 2026-03-24

首个公开版本。

本次新增:

- 完成 `youtube-ai-to-wechat` 独立仓库的公开发布整理
- 补齐顶层说明文档，覆盖能力范围、运行前准备、快速开始、产物说明和文档导航
- 纳入当前实现对应的配置、运行、Schema、模型与环境变量说明文档

本版本包含:

- 从 YouTube 搜索、候选排序到 `source pack` 生成的主题驱动发现链路
- 带重试、恢复、阶段日志和机器可读运行状态的 live pipeline 编排能力
- 面向微信公众号草稿的写作、改写、排版、素材注入和草稿 payload 生成能力
- 按当前配置接入的 Nanobanana 兼容图片规划与生成链路
- 用于预览、分环境执行和 OneIT 风格流程的 PowerShell 运行脚本示例

## 仓库结构

```text
.
|-- SKILL.md
|-- CONFIG.md
|-- MODEL_ENV_GUIDE.zh-CN.md
|-- OPERATIONS.md
|-- SCHEMA.md
|-- VERSIONING.md
|-- prompts/
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

## Skill快速使用

### 触发方式一：直接跑仓库包装脚本 `run-youtube-ai-to-wechat.ps1`

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File xxx\.youtube-ai-to-wechat\scripts\run-youtube-ai-to-wechat.ps1 `
    -Topic "微信生态里的 AI 创业机会" `
    -Keywords "微信 AI 创业","微信生态 AI 商业机会","WeChat AI startup opportunity","WeChat AI business opportunity","AI workflow in WeChat" `
    -ArticleType deep_analysis `
    -TimeRange "30d" `
    -Language "zh","en" `
    -MaxCandidates 20 `
    -MaxSelectedVideos 3 `
    -Preview
```

### 触发方式二：在 Codex 对话里直接调用本地 skill

仓库里直接提 `$youtube-ai-to-wechat` 或 `youtube-ai-to-wechat`，就会按本地 skill 处理。

```md
[$youtube-ai-to-wechat](xxx\.youtube-ai-to-wechat\SKILL.md)
Generate a WeChat article draft for topic "微信生态里的 AI 创业机会".
Keywords: 微信 AI 创业,微信生态 AI 商业机会,WeChat AI startup opportunity,WeChat AI business opportunity,AI workflow in WeChat
Time range: 30d
Language: zh,en
Article type: deep_analysis
Publish mode: draft_only
Max candidates: 20
Max selected videos: 3
```

### 触发方式三：直接进 skill 内部跑 OneIT 入口 `run_oneit_topic.ps1`

```powershell
powershell -ExecutionPolicy Bypass -File xxx\.\youtube-ai-to-wechat\assets\examples\environments\run_oneit_topic.ps1 `
    -Topic "OpenAI Agents" `
    -Keywords "OpenAI Agents","AI agents" `
    -ArticleType commentary `
    -Preview
```

## 文档导航

- [`SKILL.md`](./SKILL.md): skill 输入契约与工作流
- [`CONFIG.md`](./CONFIG.md): 合并配置结构说明
- [`MODEL_ENV_GUIDE.zh-CN.md`](./MODEL_ENV_GUIDE.zh-CN.md): 当前实现对应的模型与环境变量速查
- [`OPERATIONS.md`](./OPERATIONS.md): 运行、重试、恢复和日常 SOP
- [`SCHEMA.md`](./SCHEMA.md): 产物结构与兼容字段
- [`VERSIONING.md`](./VERSIONING.md): 版本号与 tag 规则
- `README.md`: 当前版本号与变更记录





