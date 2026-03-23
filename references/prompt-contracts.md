# Prompt Contracts

## Task JSON

The pipeline expects a JSON task object. Required: `topic` or `keywords`.

## Stage Boundaries

- `search_youtube.py`: input task, output candidate list
- `rank_candidates.py`: input candidates, output ranked candidates
- `fetch_transcript.py`: input selected candidates, output transcript pack
- `collect_research.py`: input transcript pack, output source pack
- `build_outline.py`: input source pack, output outline
- `write_article.py`: input outline, output information-pass article
- `rewrite_wechat_style.py`: input article, output WeChat-style article
- `generate_headlines.py`: input article, output title set and summary
- `generate_images_nanobanana.py`: input article and prompts, output image request set
- `build_infographic.py`: input article structure, output infographic plan
- `format_wechat_article.py`: input article plus image slots, output HTML
- `inject_assets.py`: input HTML, output final HTML with fixed blocks
- `publish_wechat_draft.py`: input final HTML bundle, output draft metadata

## Prompt Hygiene

1. Separate fact extraction from style rewriting.
2. Pass explicit article type into every writing stage.
3. Tell the model whether it may infer or must only state verified information.
4. Keep publishing credentials out of prompts.
