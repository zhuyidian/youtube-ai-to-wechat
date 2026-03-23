# OneIT Runtime Guide

This folder contains the `一点IT+` production-oriented wrappers for the `youtube-ai-to-wechat` skill.

## Files

- `run_oneit.ps1`: single entrypoint for preview, full run, resume, publish, and preview refresh
- `run_live_pipeline.prod.oneit.ps1`: production run wrapper around `scripts/run_live_pipeline.py`
- `render_article_preview.oneit.ps1`: regenerate `article_preview.md` and `article_preview.html` from the same final package for an existing run
- `live_config.prod.example.json`: current merged config, including `一点IT+` branding
- `set_minimax_env.local.ps1`: local MiniMax key loader used by the example wrappers

## Required Env Vars

Preview / full run:
- `MINIMAX_API_KEY`

Real draft upload:
- `WECHAT_ACCESS_TOKEN`

Note:
- current MiniMax OpenAI-compatible text APIs can drive article generation
- current MiniMax image generation uses `POST /v1/image_generation`
- current MiniMax documented text APIs do not accept image input, so image text-review is disabled in the MiniMax profile unless you wire a separate vision endpoint

## Common Commands

Run preview mode:

```powershell
cd E:\project\CodexProject\SkillsDemo\.agents\skills\youtube-ai-to-wechat
.\assets\examples\environments\run_oneit.ps1 -Preview
```

Run full pipeline:

```powershell
.\assets\examples\environments\run_oneit.ps1
```

Resume from images stage:

```powershell
.\assets\examples\environments\run_oneit.ps1 -RunName 2026-03-21-e2e-brand-full -ResumeFrom images
```

Refresh markdown preview only:

```powershell
.\assets\examples\environments\run_oneit.ps1 -RunName 2026-03-21-e2e-brand-full -RenderOnly
```

Upload to WeChat draft box:

```powershell
.\assets\examples\environments\run_oneit.ps1 -Publish
```

## Output

Each run writes into `.runs/<run-name>/`.

Key files:
- `final_article_package_live.json`
- `article_preview.html`
- `draft_payload_live.json`
- `image_package_live.json`
- `article_preview.md`
- `run.log`




