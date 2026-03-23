# Environment Templates

Use these merged config templates as starting points:
- `live_config.dev.example.json`: low-risk local development and offline or sandbox testing.
- `live_config.staging.example.json`: pre-production draft validation against staging publish credentials.
- `live_config.prod.example.json`: production draft workflow with real credentials and reviewed settings.

Matching PowerShell examples:
- `run_live_pipeline.dev.example.ps1`
- `run_live_pipeline.staging.example.ps1`
- `run_live_pipeline.prod.example.ps1`

Recommendation:
- use `MINIMAX_API_KEY` for both article generation and image generation in these MiniMax profiles
- keep `publish_mode` as `draft_only` in all environments
- only enable `--execute-publish` after manual review and credential verification
- if you need image text-review, wire a separate vision-capable reviewer because MiniMax's documented compatible text APIs do not currently accept image input
