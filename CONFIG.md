# Config Guide



This skill now uses a single merged config file by default.

For a Chinese quick reference covering the full pipeline's actual models, required environment variables, config choices, and recommended commands, see [`MODEL_ENV_GUIDE.zh-CN.md`](./MODEL_ENV_GUIDE.zh-CN.md).




Default example:

- [`assets/examples/live_config.example.json`](./assets/examples/live_config.example.json)



Deprecated split examples:

- [`assets/examples/deprecated`](./assets/examples/deprecated)



Environment templates:

- [`assets/examples/environments/live_config.dev.example.json`](./assets/examples/environments/live_config.dev.example.json)

- [`assets/examples/environments/live_config.staging.example.json`](./assets/examples/environments/live_config.staging.example.json)

- [`assets/examples/environments/live_config.prod.example.json`](./assets/examples/environments/live_config.prod.example.json)

- [`assets/examples/environments/run_live_pipeline.dev.example.ps1`](./assets/examples/environments/run_live_pipeline.dev.example.ps1)

- [`assets/examples/environments/run_live_pipeline.staging.example.ps1`](./assets/examples/environments/run_live_pipeline.staging.example.ps1)

- [`assets/examples/environments/run_live_pipeline.prod.example.ps1`](./assets/examples/environments/run_live_pipeline.prod.example.ps1)



## Structure



```json

{

  "llm": {

    "api_format": "openai",
    "base_url": "https://api.minimaxi.com/v1",

    "api_key_env": "MINIMAX_API_KEY",

    "model": "MiniMax-M2.7",

    "temperature": 0.7,

    "timeout": 120,

    "json_mode": false,

    "headers": {}

  },

  "nanobanana": {

    "base_url": "https://api.minimaxi.com/v1",

    "model": "image-01",

    "api_key_env": "MINIMAX_API_KEY",

    "image_size": "1K"

  },

  "brand": {

    "author_name": "AI鎯呮姤灞€",

    "author_bio": "涓撴敞璺熻釜 AI 浜у搧銆佹ā鍨嬩笌宸ヤ綔娴佸彉鍖栵紝杈撳嚭閫傚悎涓枃璇昏€呭揩閫熺悊瑙ｇ殑涓€绾挎媶瑙ｃ€?,

    "qrcode_url": "E:\project\CodexProject\SkillsDemo\.agents\skills\youtube-ai-to-wechat\assets\公众号二维码.png",

    "follow_text": "持续分享 AI 技术与编程工具干货，觉得有用就点个关注，不错过每一篇实用内容。"

  },

  "publish": {

    "author": "AI鎯呮姤灞€",

    "content_source_url": "",

    "need_open_comment": 0,

    "only_fans_can_comment": 0,

    "publish_mode": "draft_only",

    "cover_media_id": "TODO_UPLOAD_COVER",

    "base_url": "https://api.weixin.qq.com",

    "access_token_env": "WECHAT_ACCESS_TOKEN",

    "app_id_env": "WECHAT_APP_ID",

    "app_secret_env": "WECHAT_APP_SECRET"

  }

}

```



## Section Map



- `llm`: used by outline, drafting, and rewrite stages.

- `nanobanana`: used by image generation. In this repo the default image route is also MiniMax, using `image-01`.

- `brand`: used when appending author CTA and QR code into markdown before rendering HTML.

- `publish`: used when building or executing the WeChat draft payload.



## LLM Section



Fields:

- `base_url`: OpenAI-compatible API base URL.

- `api_key_env`: environment variable name that stores the API key.

- `model`: model name sent to the chat completions endpoint.

- `temperature`: generation temperature.

- `timeout`: request timeout in seconds.

- `json_mode`: whether to request structured JSON output mode when supported.

- `headers`: optional extra HTTP headers.



Used by:

- [`scripts/build_outline.py`](./scripts/build_outline.py)

- [`scripts/write_article.py`](./scripts/write_article.py)

- [`scripts/rewrite_wechat_style.py`](./scripts/rewrite_wechat_style.py)



CLI behavior:

- These scripts accept `--config`.

- `--config` can point to either a dedicated LLM config file or the merged live config file.

- When the merged file is used, the scripts read the `llm` section.



## Nanobanana Section



Fields:

- `base_url`: Nanobanana API base URL.

- `model`: image generation model name.

- `api_key_env`: environment variable name that stores the API key.

- `image_size`: image generation size hint sent to the API.



Used by:

- [`scripts/generate_images_nanobanana.py`](./scripts/generate_images_nanobanana.py)



CLI behavior:

- The script accepts `--config`.

- `--config` can point to either a dedicated Nanobanana config file or the merged live config file.

- When the merged file is used, the script reads the `nanobanana` section.



## Rendering Contract

The final package should treat `body_markdown` as the single source of truth. Generated images, `淇℃伅鏉ユ簮`, `鐩稿叧璧勬簮`, and `缁撴潫璇璥 are appended into markdown first, and `final_html` must be rendered from that exact markdown so both outputs stay aligned.

## Brand Section



Fields:

- `author_name`: author name shown in fixed blocks.

- `author_bio`: short account or author description.

- `qrcode_url`: QR image URL for the account block.

- `follow_text`: exact footer CTA text shown under `## 缁撴潫璇璥 before the QR code image.



Used by:

- [`scripts/inject_assets.py`](./scripts/inject_assets.py)



CLI behavior:

- The script accepts `--brand-config`.

- `--brand-config` can point to either a dedicated brand config file or the merged live config file.

- When the merged file is used, the script reads the `brand` section.



## Publish Section



Fields:

- `author`: WeChat draft article author field.

- `content_source_url`: optional source URL shown by WeChat.

- `need_open_comment`: `0` or `1`, whether comments are enabled.

- `only_fans_can_comment`: `0` or `1`, whether only followers can comment.

- `publish_mode`: default expected mode. Keep `draft_only` unless your workflow adds a reviewed publish step.

- `cover_media_id`: existing WeChat cover media id. If omitted or set to `TODO_UPLOAD_COVER`, the live publish step must upload a cover image first.

- `base_url`: WeChat API base URL.

- `access_token_env`: environment variable name for a direct access token.

- `app_id_env`: environment variable name for app id.

- `app_secret_env`: environment variable name for app secret.



Used by:

- [`scripts/publish_wechat_draft.py`](./scripts/publish_wechat_draft.py)



CLI behavior:

- The script accepts `--publish-config`.

- `--publish-config` can point to either a dedicated publish config file or the merged live config file.

- When the merged file is used, the script reads the `publish` section.



Authentication behavior:

- If `access_token_env` is set and available, the publish client uses it directly.

- Otherwise it attempts to resolve a token from `app_id_env` and `app_secret_env`.



## Environment Profiles



Use `dev` when you are validating prompts, payload shape, and offline artifacts. Point at test credentials.



Use `staging` when you want full end-to-end draft creation against real APIs, but still on isolated credentials or a staging public account.



Use `prod` when the pipeline is stable and the output is going to the real WeChat draft workflow. Keep `publish_mode` as `draft_only` and rely on manual review before any real publish action.



Recommended defaults:

- `dev`: cheapest safe model, relaxed temperature, isolated env vars with `_DEV` suffix

- `staging`: near-production settings, isolated env vars with `_STAGING` suffix

- `prod`: stable settings, production env vars without suffixes by default



## Recommended Runtime Env Vars



- `MINIMAX_API_KEY`

- `WECHAT_ACCESS_TOKEN`



Alternative WeChat auth vars:

- `WECHAT_APP_ID`

- `WECHAT_APP_SECRET`



## Recommended Commands



Run from the skill root directory.



Dev:



```powershell

python ./scripts/run_live_pipeline.py `

  ./.runs/example/source_pack_v2.json `

  --output-dir ./.runs/dev-run `

  --live-config ./assets/examples/environments/live_config.dev.example.json

```



Staging:



```powershell

python ./scripts/run_live_pipeline.py `

  ./.runs/example/source_pack_v2.json `

  --output-dir ./.runs/staging-run `

  --live-config ./assets/examples/environments/live_config.staging.example.json `

  --execute-llm `

  --execute-images

```



Prod:



```powershell

python ./scripts/run_live_pipeline.py `

  ./.runs/example/source_pack_v2.json `

  --output-dir ./.runs/prod-run `

  --live-config ./assets/examples/environments/live_config.prod.example.json `

  --execute-llm `

  --execute-images `

  --execute-publish

```



## Overrides



You can still override individual sections for debugging or migration:

- `--llm-config`

- `--nanobanana-config`

- `--brand-config`

- `--publish-config`



These flags are deprecated on the main pipeline entrypoint. Prefer `--live-config` unless you are testing one stage in isolation.





