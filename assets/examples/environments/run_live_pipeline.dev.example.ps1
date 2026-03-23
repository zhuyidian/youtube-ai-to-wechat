$env:OPENAI_API_KEY_DEV="your_dev_key"
$env:NANOBANANA_API_KEY_DEV="your_dev_key"
$env:WECHAT_ACCESS_TOKEN_DEV="your_dev_token"

python ./scripts/run_live_pipeline.py `
  ./.runs/example/source_pack_v2.json `
  --output-dir ./.runs/dev-run `
  --live-config ./assets/examples/environments/live_config.dev.example.json
