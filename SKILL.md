---

name: youtube-ai-to-wechat

description: Search YouTube for AI topics, select strong source videos, extract subtitles or transcripts, add supplemental research, draft Chinese WeChat articles, generate Nanobanana images, format polished WeChat HTML, and upload the result to the WeChat draft box. Use when Codex needs to turn a topic keyword set or AI theme into a reviewed WeChat-ready draft rather than directly publishing.

---



# YouTube AI To WeChat



## Overview



Turn an AI topic or keyword list into a Chinese WeChat article draft with research, structure, images, formatted HTML, and draft-box-safe output. Default to a half-automatic workflow: automate from discovery to draft creation, then stop for human review before final publish.



## Input Contract



Accept a task with these fields:



```json

{

  "topic": "OpenAI Agents",

  "keywords": ["OpenAI Agents", "AI agents"],

  "time_range": "7d",

  "language": ["zh", "en"],

  "article_type": "auto",

  "publish_mode": "draft_only",

  "max_candidates": 20,

  "max_selected_videos": 3,

  "cost_budget": "low"

}

```



Treat `topic` or `keywords` as required. Default to `publish_mode=draft_only` unless the user explicitly asks for a separate publish step.



## Operating Rules



1. Search broadly, but score sources aggressively.

2. Never write from a single YouTube video alone.

3. Separate verified facts from commentary and synthesis.

4. Prefer AI news briefs, video summaries, and deep analysis over tutorials or tool lists unless the input clearly asks for them.

5. Default output language to Chinese.

6. Generate the WeChat draft, not a direct publish action.

7. Keep costs low by capping candidate count, selected videos, and image count before reducing article quality.



## Workflow



### 1. Discover



Use [`references/content-strategy.md`](./references/content-strategy.md) and [`references/source-scoring.md`](./references/source-scoring.md) to expand the topic into bilingual search queries and a scoring rubric.



Run these stages in order:



1. Search YouTube for AI-related candidates.

2. De-duplicate near-identical videos and reposts.

3. Score each candidate for topic fit, novelty, information density, channel quality, and writing potential.

4. Pick one primary video plus supporting videos or research sources.



### 2. Collect



Use the chosen videos to obtain subtitles or transcripts. When captions are weak or missing, note that transcription quality is uncertain and compensate with outside research.



Build a source pack containing:



1. Video metadata

2. Transcript excerpts with timestamps

3. Supplemental official sources

4. Key claims that require verification



### 3. Write



Structure the article in two passes:



1. Information pass: build outline, summarize facts, list implications, note missing evidence.

2. WeChat pass: rewrite for pacing, hooks, title quality, and readability.



Use [`references/article-structures.md`](./references/article-structures.md) for article frames and [`references/wechat-style-guide.md`](./references/wechat-style-guide.md) for tone, rhythm, and formatting rules.



### 4. Illustrate



Generate:



1. One 2.35:1 cover image

2. Two to four inline illustrations

3. One infographic when the topic contains a flow, comparison, or timeline



Use Nanobanana prompts from [`assets/templates`](./assets/templates) and the guardrails in [`references/image-guidelines.md`](./references/image-guidelines.md).



### 5. Format



Build the final article from one markdown source of truth. First append fixed sections such as `淇℃伅鏉ユ簮`, `鐩稿叧璧勬簮`, `缁撴潫璇璥 and generated image markdown into the article markdown, then render WeChat-friendly HTML from that same markdown. Preserve a clean reading rhythm with short paragraphs, highlighted conclusions, and obvious subheadings.



### 6. Deliver



Produce a review package containing:



1. Final HTML draft

2. Title candidates

3. Summary and cover copy

4. Image assets

5. Source list

6. Open questions for human review



Upload only to the draft box. If the user later asks to publish, treat that as a separate confirmed action.



## Failure Handling



When a step fails, degrade gracefully instead of aborting:



1. If YouTube search is noisy, narrow the query and raise source thresholds.

2. If transcript quality is poor, cite that explicitly and lean more on official materials.

3. If research sources conflict, surface the conflict in the draft rather than forcing certainty.

4. If image generation fails, ship the article draft first and mark image placeholders.

5. If WeChat upload fails, persist the final HTML package locally for manual import.



Read [`references/failure-handling.md`](./references/failure-handling.md) when a stage fails or quality is borderline.



## Scripts



Run [`scripts/run_pipeline.py`](./scripts/run_pipeline.py) to generate a structured run manifest and stage plan from a task JSON file. Use the stage scripts only when you need deterministic scaffolding for a specific step.



For live execution, prefer [`scripts/run_live_pipeline.py`](./scripts/run_live_pipeline.py) with a single merged config file such as [`assets/examples/live_config.example.json`](./assets/examples/live_config.example.json). The older split config examples have been moved under [`assets/examples/deprecated`](./assets/examples/deprecated) and are kept only for backward compatibility.



See [`CONFIG.md`](./CONFIG.md) for the merged config structure, field meanings, environment variables, and recommended runtime command.

See [`MODEL_ENV_GUIDE.zh-CN.md`](./MODEL_ENV_GUIDE.zh-CN.md) for the current authoritative Chinese quick reference covering the full pipeline's actual models, required environment variables, and recommended commands by environment.




See [`OPERATIONS.md`](./OPERATIONS.md) for production run procedures, log capture, retry guidance, resume strategy, and daily SOP.



## References



Load only what is relevant:



1. [`references/workflow.md`](./references/workflow.md): End-to-end SOP

2. [`references/content-strategy.md`](./references/content-strategy.md): Topic positioning and routing

3. [`references/source-scoring.md`](./references/source-scoring.md): Candidate ranking

4. [`references/wechat-style-guide.md`](./references/wechat-style-guide.md): Writing and formatting rules

5. [`references/article-structures.md`](./references/article-structures.md): Reusable article frames

6. [`references/prompt-contracts.md`](./references/prompt-contracts.md): Script I/O and prompt boundaries

7. [`references/image-guidelines.md`](./references/image-guidelines.md): Cover and inline image guidance

8. [`references/wechat-publish-spec.md`](./references/wechat-publish-spec.md): Draft upload expectations

9. [`references/failure-handling.md`](./references/failure-handling.md): Fallback paths





