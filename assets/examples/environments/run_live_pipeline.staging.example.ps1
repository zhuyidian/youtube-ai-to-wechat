$env:OPENAI_API_KEY_STAGING="your_staging_key"
$env:NANOBANANA_API_KEY_STAGING="your_staging_key"
$env:WECHAT_ACCESS_TOKEN_STAGING="your_staging_token"

python ./scripts/run_live_pipeline.py `
  ./.runs/example/source_pack_v2.json `
  --output-dir ./.runs/staging-run `
  --live-config ./assets/examples/environments/live_config.staging.example.json `
  --execute-llm `
  --execute-images
