$env:NANOBANANA_API_KEY="your_llm_key"
$env:APICORE_IMAGE_API_KEY="your_image_key"
$env:WECHAT_ACCESS_TOKEN="your_prod_token"

python ./scripts/run_live_pipeline.py `
  ./.runs/example/source_pack_v2.json `
  --output-dir ./.runs/prod-run `
  --live-config ./assets/examples/environments/live_config.prod.example.json `
  --execute-llm `
  --execute-images `
  --execute-publish
