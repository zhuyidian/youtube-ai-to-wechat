# YouTube AI To WeChat 模型与环境变量说明

本文档说明 `youtube-ai-to-wechat` skill 当前实现里完整流程实际使用到的模型、环境变量、脚本入口和推荐命令。

口径说明：

- 本文优先以当前 Python 脚本和 `assets/examples/environments/live_config.*.example.json` 为准。
- 如果文档、旧 `.ps1` 示例、通用 fallback 默认值之间有冲突，以“完整流程实际运行时会读取什么”为准。
- 当前默认完整流程的主链路是 MiniMax 文本 + MiniMax 图片，不是 OpenAI fallback。

适用时间点：当前仓库状态，基于 2026-03-23 本地代码读取结果整理。

## 1. 先说结论

当前默认主链路不是单模型，而是分段执行：

1. YouTube 检索：YouTube Data API
2. 候选排序：本地启发式打分
3. 转录：当前实现仅做 metadata fallback，不调用 ASR
4. 研究补充：本地规则生成 claims 和官方来源候选
5. 大纲、信息稿、微信改写：LLM
6. 封面图、配图、信息图：图片模型
7. 标题、排版、素材注入：本地脚本
8. 微信草稿上传：微信公众号接口

当前默认推荐配置是 MiniMax 路线：

- 正文 LLM：`MiniMax-M2.7`
- 图片模型：`image-01`
- 图片和正文默认共用：`MINIMAX_API_KEY`
- 微信发布：`WECHAT_ACCESS_TOKEN` 或 `WECHAT_APP_ID` + `WECHAT_APP_SECRET`

?????????????????

- `YOUTUBE_API_KEY`
- `MINIMAX_API_KEY`
- `WECHAT_ACCESS_TOKEN`
- ?? `WECHAT_APP_ID` + `WECHAT_APP_SECRET`

## 2. 完整流程阶段表

| 阶段 | 脚本 | 是否调用模型 | 默认模型/服务 | 需要的环境变量 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 搜索候选视频 | `scripts/search_youtube.py` | 否 | YouTube Data API | `YOUTUBE_API_KEY` | 也可用 `--fixtures-dir` 离线运行 |
| 候选排序 | `scripts/rank_candidates.py` | 否 | 本地规则 | 无 | 纯本地打分 |
| 转录收集 | `scripts/fetch_transcript.py` | 否 | 无 | 无 | 当前只拼接标题和描述，`transcript_mode=metadata_fallback` |
| 研究补充 | `scripts/collect_research.py` | 否 | 本地规则 | 无 | 生成 claims、官方来源候选、写作角度 |
| 大纲生成 | `scripts/build_outline.py` | 是 | `llm.model` | `llm.api_key_env` 指向的变量 | 默认是 `MiniMax-M2.7` |
| 信息稿写作 | `scripts/write_article.py` | 是 | `llm.model` | 同上 | 默认是 `MiniMax-M2.7` |
| 微信风格改写 | `scripts/rewrite_wechat_style.py` | 是 | `llm.model` | 同上 | 默认是 `MiniMax-M2.7` |
| 标题包生成 | `scripts/generate_headlines.py` | 否 | 本地规则 | 无 | 不走 LLM |
| 图片生成 | `scripts/generate_images_nanobanana.py` | 是 | `nanobanana.model` | `nanobanana.api_key_env` 指向的变量 | 默认是 `image-01` |
| 信息图规划 | `scripts/build_infographic.py` | 否 | 本地规则 | 无 | 不走模型 |
| 微信排版 | `scripts/format_wechat_article.py` | 否 | 本地渲染 | 无 | 不走模型 |
| 品牌素材注入 | `scripts/inject_assets.py` | 否 | 本地渲染 | 无 | 使用 `brand` 配置 |
| 微信草稿上传 | `scripts/publish_wechat_draft.py` | 否 | 微信公众号接口 | `WECHAT_ACCESS_TOKEN` 或 `WECHAT_APP_ID` + `WECHAT_APP_SECRET` | 可只生成 payload，不实际上传 |

## 3. 当前默认模型配置

默认合并配置文件是：

- `assets/examples/live_config.example.json`
- `assets/examples/environments/live_config.dev.example.json`
- `assets/examples/environments/live_config.staging.example.json`
- `assets/examples/environments/live_config.prod.example.json`

这些模板当前都以 MiniMax 为正文和图片的默认提供方。

### 3.1 正文 LLM

默认字段：

```json
{
  "api_format": "openai",
  "base_url": "https://api.minimaxi.com/v1",
  "api_key_env": "MINIMAX_API_KEY",
  "model": "MiniMax-M2.7"
}
```

用途：

- `build_outline.py`
- `write_article.py`
- `rewrite_wechat_style.py`

### 3.2 图片模型

默认字段：

```json
{
  "base_url": "https://api.minimaxi.com/v1",
  "model": "image-01",
  "api_key_env": "MINIMAX_API_KEY"
}
```

用途：

- `generate_images_nanobanana.py`

### 3.3 微信发布

默认字段：

```json
{
  "access_token_env": "WECHAT_ACCESS_TOKEN",
  "app_id_env": "WECHAT_APP_ID",
  "app_secret_env": "WECHAT_APP_SECRET"
}
```

用途：

- `publish_wechat_draft.py`

认证规则：

- 优先直接使用 `WECHAT_ACCESS_TOKEN`
- 如果没有 token，则退回到 `WECHAT_APP_ID` + `WECHAT_APP_SECRET`

## 4. dev / staging / prod 环境变量

### 4.1 dev

对应配置：

- `assets/examples/environments/live_config.dev.example.json`

当前模板使用：

- `MINIMAX_API_KEY_DEV`
- `WECHAT_ACCESS_TOKEN_DEV`
- 可选：`WECHAT_APP_ID_DEV`
- 可选：`WECHAT_APP_SECRET_DEV`

额外注意：

- YouTube 搜索脚本仍然固定读取 `YOUTUBE_API_KEY`
- 它没有 dev 后缀版本配置位

### 4.2 staging

对应配置：

- `assets/examples/environments/live_config.staging.example.json`

当前模板使用：

- `MINIMAX_API_KEY_STAGING`
- `WECHAT_ACCESS_TOKEN_STAGING`
- 可选：`WECHAT_APP_ID_STAGING`
- 可选：`WECHAT_APP_SECRET_STAGING`

额外注意：

- YouTube 搜索脚本仍然固定读取 `YOUTUBE_API_KEY`

### 4.3 prod

对应配置：

- `assets/examples/environments/live_config.prod.example.json`

当前模板使用：

- `MINIMAX_API_KEY`
- `WECHAT_ACCESS_TOKEN`
- 可选：`WECHAT_APP_ID`
- 可选：`WECHAT_APP_SECRET`

额外注意：

- YouTube 搜索脚本仍然固定读取 `YOUTUBE_API_KEY`

## 5. 一条可直接执行的完整命令链

以下命令从 skill 根目录执行：

```powershell
python ./scripts/search_youtube.py `
  ./task.json `
  --output ./.runs/2026-03-23-topic/search_output.json

python ./scripts/rank_candidates.py `
  ./.runs/2026-03-23-topic/search_output.json `
  --output ./.runs/2026-03-23-topic/ranked_candidates.json

python ./scripts/fetch_transcript.py `
  ./.runs/2026-03-23-topic/ranked_candidates.json `
  --output ./.runs/2026-03-23-topic/transcript_pack.json

python ./scripts/collect_research.py `
  ./.runs/2026-03-23-topic/transcript_pack.json `
  --output ./.runs/2026-03-23-topic/source_pack.json

python ./scripts/run_live_pipeline.py `
  ./.runs/2026-03-23-topic/source_pack.json `
  --output-dir ./.runs/2026-03-23-topic `
  --live-config ./assets/examples/environments/live_config.prod.example.json `
  --execute-llm `
  --execute-images
```

如果要实际上传微信草稿，再加：

```powershell
python ./scripts/run_live_pipeline.py `
  ./.runs/2026-03-23-topic/source_pack.json `
  --output-dir ./.runs/2026-03-23-topic `
  --live-config ./assets/examples/environments/live_config.prod.example.json `
  --execute-llm `
  --execute-images `
  --execute-publish
```

如果你已经有 `source_pack.json`，就可以跳过前四步，直接从 `run_live_pipeline.py` 开始。

## 6. 最小环境变量集合

### 6.1 默认 MiniMax 主链路

最低要求：

```powershell
$env:YOUTUBE_API_KEY="..."
$env:MINIMAX_API_KEY="..."
$env:WECHAT_ACCESS_TOKEN="..."
```

如果不用直接 token：

```powershell
$env:YOUTUBE_API_KEY="..."
$env:MINIMAX_API_KEY="..."
$env:WECHAT_APP_ID="..."
$env:WECHAT_APP_SECRET="..."
```

### 6.2 dev 版本

```powershell
$env:YOUTUBE_API_KEY="..."
$env:MINIMAX_API_KEY_DEV="..."
$env:WECHAT_ACCESS_TOKEN_DEV="..."
```

### 6.3 staging 版本

```powershell
$env:YOUTUBE_API_KEY="..."
$env:MINIMAX_API_KEY_STAGING="..."
$env:WECHAT_ACCESS_TOKEN_STAGING="..."
```

## 7. 可替换模型链路

仓库里还提供了一个 GLM 示例：

- 配置文件：`assets/examples/live_config.glm.example.json`

它的含义是：

- 正文模型：`glm-4.7`
- 正文密钥：`GLM_API_KEY`
- 图片模型：`gemini-3-pro-image-preview`
- 图片密钥：`NANOBANANA_API_KEY`
- 微信发布：仍然是 `WECHAT_ACCESS_TOKEN` 或 `WECHAT_APP_ID` + `WECHAT_APP_SECRET`

这个示例更适合你明确要走：

- 智谱 GLM 做正文
- Nanobanana / Gemini 风格图片接口做配图

最低变量集合：

```powershell
$env:YOUTUBE_API_KEY="..."
$env:GLM_API_KEY="..."
$env:NANOBANANA_API_KEY="..."
$env:WECHAT_ACCESS_TOKEN="..."
```

## 8. 当前实现里的几个重要偏差

### 8.1 `run_live_pipeline.py` 不是全流程入口

它只覆盖从 `source_pack` 到微信草稿 payload 的后半段：

- `outline`
- `draft`
- `rewrite`
- `headline`
- `images`
- `infographic`
- `format`
- `inject`
- `publish`

前面的 YouTube 搜索、排序、转录、研究需要你单独调用对应脚本。

### 8.2 `fetch_transcript.py` 目前不是真转录

当前输出是：

- `transcript_mode = metadata_fallback`
- `transcript_text = 标题 + 描述`

所以它不需要额外模型和密钥，但信息质量明显受限。

### 8.3 图片文字质检默认并不会真正启用

默认 MiniMax profile 下，代码会因为 reviewer 仍指向 MiniMax 文本兼容接口而主动禁用图片质检。

另外，当前代码库里 `OpenAICompatibleClient` 也没有实现 `chat_with_image`，所以即使未来你接入了独立 reviewer，现有 reviewer 调用链也还需要补实现后才能真正工作稳定。

实际含义：

- 当前默认链路是“生成图片”
- 不是“生成图片 + 视觉模型复检”

### 8.4 几个 `.ps1` 示例脚本已落后于当前 JSON 模板

当前应优先相信：

- `CONFIG.md`
- `assets/examples/environments/live_config.*.example.json`
- 实际 Python 脚本中的 `load_*_config` 和 `os.getenv(...)`

不要直接把以下旧示例当成权威：

- `run_live_pipeline.dev.example.ps1`
- `run_live_pipeline.staging.example.ps1`
- `run_live_pipeline.prod.example.ps1`

这些旧示例里还出现了：

- `OPENAI_API_KEY_DEV`
- `OPENAI_API_KEY_STAGING`
- `NANOBANANA_API_KEY`
- `APICORE_IMAGE_API_KEY`

而当前默认环境模板已经统一为 MiniMax 主链路。

## 9. 推荐你实际怎么用

如果你现在要稳定跑通完整流程，建议按下面的优先级：

1. 检索阶段统一使用 `YOUTUBE_API_KEY`
2. 正文和图片都先走 MiniMax 模板
3. 先跑到 `draft_only`
4. 人工检查标题、事实边界、图片和排版
5. 最后才加 `--execute-publish`

如果你只是验证流程，不要直接打开 `--execute-publish`。

## 10. 最终推荐记忆版

默认主链路只记这四个变量就够：

```text
YOUTUBE_API_KEY
MINIMAX_API_KEY
WECHAT_ACCESS_TOKEN
WECHAT_APP_ID / WECHAT_APP_SECRET
```

如果换 GLM 示例，再把正文和图片变量改成：

```text
GLM_API_KEY
NANOBANANA_API_KEY
```

## 11. 当前最终口径

如果你只想记“完整流程现在到底用什么”，只看这一段：

- 搜索：YouTube Data API，读取 `YOUTUBE_API_KEY`
- 排序：本地规则，无模型
- transcript：当前是 metadata fallback，无模型
- research/source pack：本地规则，无模型
- outline / draft / rewrite：`MiniMax-M2.7`，读取 `MINIMAX_API_KEY`
- headlines：本地规则，无模型
- images：`image-01`，读取 `MINIMAX_API_KEY`
- image text review：配置上仍写 `MiniMax-M2.7`，但当前默认 MiniMax profile 下实际禁用
- format / inject / article_preview.html：本地处理，无模型
- publish：微信公众号接口，读取 `WECHAT_ACCESS_TOKEN`，没有则回退到 `WECHAT_APP_ID` + `WECHAT_APP_SECRET`

需要特别排除的误解：

- `llm_client.py` 里的 `gpt-4.1-mini + OPENAI_API_KEY` 是通用 fallback，不是这个 skill 当前默认完整流程
- 旧的 `run_live_pipeline.*.ps1` 不能作为默认链路的权威说明
