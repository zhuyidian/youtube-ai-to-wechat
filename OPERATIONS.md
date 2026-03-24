# Operations Guide



This document is the production runbook for the `youtube-ai-to-wechat` skill.



It focuses on four things:

- retry strategy

- log capture

- resume from intermediate artifacts

- daily operating SOP



Important boundary:

- the current implementation writes pipeline artifacts to `.runs/...`

- it now writes built-in per-stage logs under `stage-logs/`, a top-level `pipeline_summary.json`, a minimal `run_status.json`, and a fixed `.runs/latest-run.json` index

- it supports configurable stage retries through `--max-retries`, `--retry-delay-seconds`, and `--retry-policy`

- it supports explicit stage resume through `--resume-from`

- it supports artifact-based automatic resume through `--auto-resume`

- it now classifies failures into standardized error codes and uses them in `smart` retry mode



## Recommended Run Modes



Use one of these modes:

- `dev`: local validation, test-oriented settings, no real publish

- `staging`: real APIs for article and image generation, but no final draft publish unless needed for validation

- `prod`: full draft creation to the real WeChat draft workflow



Recommended inputs:

- use a dedicated run directory per execution

- use the environment-specific config templates under [`assets/examples/environments`](./assets/examples/environments)

- keep `publish_mode` as `draft_only`



## Recommended Run Directory Layout



Use one directory per run under `.runs/`.



Example:



```text

.runs/

-- 2026-03-19-openai-agents-prod/

    |-- run.log

    |-- outline_live.json

    |-- article_draft_live.json

    |-- wechat_article_live.json

    |-- headline_bundle_live.json

    |-- image_package_live.json

    |-- infographic_plan_live.json

    |-- formatted_article_live.json

    |-- final_article_package_live.json

    |-- article_preview.md

    |-- article_preview.html

    |-- draft_payload_live.json

    |-- run_live_manifest.json

    |-- pipeline_summary.json

    |-- run_status.json

    |-- stage-logs/

    `-- ...



.runs/

|-- latest-run.json

`-- 2026-03-19-openai-agents-prod/

    `-- generated-images/

```



Run naming recommendation:

- `YYYY-MM-DD-topic-env`

- example: `2026-03-19-openai-agents-prod`



## Log Capture



Current state:

- the pipeline prints stage execution to stdout

- stage scripts print `Wrote ...` on successful output

- the pipeline writes one JSON log and one text log per stage under `stage-logs/`

- the pipeline writes a top-level `pipeline_summary.json`

- the pipeline writes a compact `run_status.json` for monitoring and external schedulers

- the pipeline updates a fixed `.runs/latest-run.json` index that points to the most recent run



Recommended practice:

- still capture stdout and stderr into a run log for operator review

- keep the run log inside the same run directory as the artifacts

- use `.runs/latest-run.json` when an external system wants one stable path that always points to the newest run

- use `run_status.json` when an external system only needs the final outcome, badge, exit reason, and main failure code for a known run directory

- use `pipeline_summary.json` for run status, `run_outcome`, `status_badge`, `exit_reason`, top-level failure code, and final failure summary

- use `stage-logs/` for stage-by-stage inspection



PowerShell example:



```powershell

New-Item -ItemType Directory -Force ./.runs/2026-03-19-openai-agents-prod | Out-Null

python ./scripts/run_live_pipeline.py `

  ./.runs/example/source_pack_v2.json `

  --output-dir ./.runs/2026-03-19-openai-agents-prod `

  --live-config ./assets/examples/environments/live_config.prod.example.json `

  --execute-llm `

  --execute-images `

  --execute-publish `

  --max-retries 2 `

  --retry-delay-seconds 3 `

  --retry-policy smart *>&1 | Tee-Object ./.runs/2026-03-19-openai-agents-prod/run.log

```



Minimum fields to inspect in the log:

- which stage started last

- the exact command line used for the failed stage

- the last successfully written artifact

- any missing env var or HTTP error details



Minimum top-level fields to inspect in `.runs/latest-run.json`:

- `skill_name`

- `schema_version`

- `latest_updated_at`

- `status_badge`

- `exit_reason`

- `failure_code`

- `output_dir`

- `run_status_path`

- `pipeline_summary_path`



Minimum top-level fields to inspect in `run_status.json`:

- `skill_name`

- `schema_version`

- `run_outcome`

- `status_badge`

- `exit_reason`

- `failure_code`

- `failure_summary`



Minimum top-level summary fields to inspect in `pipeline_summary.json`:

- `skill_name`

- `schema_version`

- `run_outcome`

- `status_badge`

- `exit_reason`

- `failed_stage`

- `failure_code`

- `failure_category`

- `failure_reason`

- `failure_summary`



`run_outcome` meanings:

- `success`: all stages ran in this invocation with no skipped stages

- `partial`: the run completed, but some earlier stages were skipped because of manual or automatic resume

- `failed`: the run did not complete successfully

- `noop`: the run completed without executing any stages, usually because `--auto-resume` found a fully complete output directory



`status_badge` meanings:

- `ok`: successful full run

- `warn`: successful run with resume or partial execution

- `error`: failed run

- `idle`: no-op run



Typical `exit_reason` values:

- `completed_full_run`

- `completed_with_resume`

- `auto_resume_noop`

- `failed_input_error`

- `failed_auth_error`

- `failed_upstream_rate_limit`



## Retry Strategy



The pipeline now supports three retry policies:

- `smart`: retry only failures classified as transient or retryable

- `always`: retry any failed stage until the retry budget is exhausted

- `never`: do not retry, even when `--max-retries` is greater than zero



Recommended default:

- use `smart` in staging and production

- use `always` only when you are debugging flaky upstream services

- use `never` when you want fast fail behavior for operator debugging



Retry by failure type, not blindly.



Standardized error codes currently used by the pipeline:

- `input_error`: missing files, invalid arguments, malformed input payloads

- `config_error`: missing env vars, API key issues, publish config gaps

- `auth_error`: 401, 403, unauthorized, forbidden

- `missing_output`: stage exited successfully but did not emit its expected artifact

- `upstream_rate_limit`: 429 and rate-limit style failures

- `upstream_timeout`: timeout and gateway-timeout style failures

- `upstream_network_error`: DNS and connection failures

- `upstream_server_error`: 5xx and service-unavailable style failures

- `internal_error`: local code/runtime issues such as `ValueError`, `KeyError`, `TypeError`

- `unknown_error`: unmatched failures



Smart retry behavior:

- retries: `upstream_rate_limit`, `upstream_timeout`, `upstream_network_error`, `upstream_server_error`

- does not retry: `input_error`, `config_error`, `auth_error`, `missing_output`, `internal_error`, `unknown_error`



### Search and Ranking



Symptoms:

- weak candidates

- off-topic candidates

- empty candidate pool



Retry actions:

- narrow the topic keywords

- reduce time range noise

- run search and ranking again only

- do not rerun article generation until candidate quality is fixed



Commands:

- [`scripts/search_youtube.py`](./scripts/search_youtube.py)

- [`scripts/rank_candidates.py`](./scripts/rank_candidates.py)



### Transcript and Research



Symptoms:

- missing transcript

- low-quality transcript

- weak claim extraction



Retry actions:

- retry transcript collection first

- if transcript remains weak, proceed with stronger external research and explicitly lower confidence

- do not over-claim from partial captions



Commands:

- [`scripts/fetch_transcript.py`](./scripts/fetch_transcript.py)

- [`scripts/collect_research.py`](./scripts/collect_research.py)



### LLM Writing



Symptoms:

- bad outline

- weak article structure

- unsatisfactory rewrite tone

- factual overreach in prose



Retry actions:

- rerun only the failed writing stage when possible

- if the outline is weak, restart from outline

- if only style is weak, rerun rewrite without regenerating everything else

- lower temperature for stability in production



Commands:

- [`scripts/build_outline.py`](./scripts/build_outline.py)

- [`scripts/write_article.py`](./scripts/write_article.py)

- [`scripts/rewrite_wechat_style.py`](./scripts/rewrite_wechat_style.py)



### Image Generation



Symptoms:

- API failure

- poor image quality

- wrong aspect ratio or weak style match



Retry actions:

- rerun image generation only

- preserve article artifacts

- if cover fails repeatedly, continue the draft and mark cover handling as a manual follow-up



Commands:

- [`scripts/generate_images_nanobanana.py`](./scripts/generate_images_nanobanana.py)

- [`scripts/build_infographic.py`](./scripts/build_infographic.py)



### WeChat Draft Upload



Symptoms:

- missing `cover_media_id`

- token failure

- `uploadimg` failure

- draft add failure



Retry actions:

- fix credentials first

- rerun publish only

- do not regenerate article or images unless the payload itself is wrong

- if publish still fails, keep the final HTML package and image assets for manual import



Command:

- [`scripts/publish_wechat_draft.py`](./scripts/publish_wechat_draft.py)



## Resume Strategy



Current state:

- [`scripts/run_live_pipeline.py`](./scripts/run_live_pipeline.py) supports explicit stage resume through `--resume-from`

- [`scripts/run_live_pipeline.py`](./scripts/run_live_pipeline.py) also supports artifact-based resume through `--auto-resume`

- earlier stages are marked as `skipped` in the stage logs when resume is used

- `--auto-resume` picks the earliest stage with a missing artifact or a non-completed stage log

- if all artifacts already exist, `--auto-resume` turns the run into a no-op and records that outcome in the summary



Principle:

- restart from the earliest corrupted or missing artifact

- keep all earlier good artifacts

- do not rerun expensive stages unless needed



### Stage Artifact Map



- outline stage output: `outline_live.json`

- draft stage output: `article_draft_live.json`

- rewrite stage output: `wechat_article_live.json`

- headline stage output: `headline_bundle_live.json`

- image stage output: `image_package_live.json`

- infographic stage output: `infographic_plan_live.json`

- format stage output: `formatted_article_live.json`

- inject stage output: `final_article_package_live.json`

- inject stage companion preview markdown: `article_preview.md`

- inject stage companion preview html: `article_preview.html`

- publish stage output: `draft_payload_live.json`



### Auto Resume Example



Use auto-resume when you want the pipeline to inspect the existing run directory and continue from the earliest incomplete stage:



```powershell

python ./scripts/run_live_pipeline.py `

  ./.runs/example/source_pack_v2.json `

  --output-dir ./.runs/2026-03-19-openai-agents-prod `

  --live-config ./assets/examples/environments/live_config.prod.example.json `

  --auto-resume

```



Typical behavior:

- if `formatted_article_live.json` is missing, the pipeline resumes from `format`

- if all stage artifacts are present, the pipeline writes a no-op summary and does not rerun stages



### Manual Resume Examples



Resume from rewrite onward when outline and draft are already valid:



```powershell

python ./scripts/rewrite_wechat_style.py `

  ./.runs/2026-03-19-openai-agents-prod/article_draft_live.json `

  --output ./.runs/2026-03-19-openai-agents-prod/wechat_article_live.json `

  --config ./assets/examples/environments/live_config.prod.example.json `

  --execute

```



Resume publish only:



```powershell

python ./scripts/publish_wechat_draft.py `

  ./.runs/2026-03-19-openai-agents-prod/final_article_package_live.json `

  --image-package ./.runs/2026-03-19-openai-agents-prod/image_package_live.json `

  --infographic-plan ./.runs/2026-03-19-openai-agents-prod/infographic_plan_live.json `

  --publish-config ./assets/examples/environments/live_config.prod.example.json `

  --output ./.runs/2026-03-19-openai-agents-prod/draft_payload_live.json `

  --execute

```



Resume image generation only:



```powershell

python ./scripts/generate_images_nanobanana.py `

  ./.runs/2026-03-19-openai-agents-prod/wechat_article_live.json `

  --output ./.runs/2026-03-19-openai-agents-prod/image_package_live.json `

  --asset-dir ./.runs/2026-03-19-openai-agents-prod/generated-images `

  --config ./assets/examples/environments/live_config.prod.example.json `

  --execute

```



## Daily Operating SOP



### 1. Preflight



Before the first run of the day:

- verify the chosen environment config file

- verify all required env vars are loaded

- verify the run directory name for the day

- verify the WeChat target account is the intended one

- verify the selected model and image generation mode



Recommended checks:

- `OPENAI_API_KEY` or environment-specific equivalent

- `NANOBANANA_API_KEY` or environment-specific equivalent

- `WECHAT_ACCESS_TOKEN` or app credentials

- chosen retry settings: `--max-retries`, `--retry-delay-seconds`, and `--retry-policy`



### 2. Start Run



For each topic:

- create a unique run directory

- capture logs to `run.log`

- start the pipeline with the environment-specific config

- do not overwrite a previous run directory



### 3. Inspect Artifacts



After a successful run, inspect at minimum:

- `wechat_article_live.json`

- `headline_bundle_live.json`

- `image_package_live.json`

- `final_article_package_live.json`

- `article_preview.md`

- `article_preview.html`

- `draft_payload_live.json`



Review points:

- title quality

- factual caution

- paragraph rhythm and readability

- image relevance and cover quality

- draft payload author and digest fields



### 4. Human Review Gate



Before any downstream publish action:

- open the WeChat draft

- verify cover image, title, digest, and body rendering

- verify QR code and follow CTA block

- verify links and inline images

- verify no obvious hallucinated claims remain



### 5. Close Run



At the end of the run:

- keep the output directory intact

- keep the log file with the artifacts

- note any manual corrections applied after draft creation

- record whether the run is reusable as a template for similar topics



## Incident Handling



When a production incident happens:

- stop launching new prod runs from the same config until the cause is known

- downgrade to `staging` if you need safe reproduction

- keep the failed run directory unchanged

- copy the exact failing command from the log before retrying

- document whether the issue was credentials, upstream API failure, prompt quality, payload shape, or operator error



## Recommended Future Improvements



These are not implemented yet, but they are the next production hardening steps:

- richer stage logs with provider-specific error details and upstream response metadata

- daily archive and cleanup policy for `.runs/`




