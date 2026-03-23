# Schema Guide



This document defines the machine-readable output contract for the `youtube-ai-to-wechat` skill.



## Current Version



Current identifiers:

- `skill_name`: `youtube-ai-to-wechat`

- `schema_version`: `1.0`



These two fields are written to the top level of the main run metadata files and should be treated as the first compatibility check for external systems.



## Contract Scope



The current schema contract covers these files:

- `.runs/latest-run.json`

- `<run>/run_status.json`

- `<run>/pipeline_summary.json`

- `<run>/run_live_manifest.json`

The run directory also contains content artifacts such as:

- `<run>/final_article_package_live.json`

- `<run>/article_preview.md`

- `<run>/article_preview.html`



Purpose by file:

- `.runs/latest-run.json`: fixed-path pointer to the newest run and its top-level status.

- `run_status.json`: minimal per-run status file for schedulers, monitors, and dashboards.

- `pipeline_summary.json`: richer per-run status summary with outcome and failure aggregation.

- `run_live_manifest.json`: full execution manifest with stage records, artifacts, and run metadata.



## Stable Top-Level Fields



The following fields are intended to stay stable across `1.x` versions unless explicitly noted.



Shared identity fields:

- `skill_name`

- `schema_version`



Shared lifecycle fields:

- `started_at`

- `ended_at`

- `output_dir`



Shared outcome fields:

- `status`

- `run_outcome`

- `status_badge`

- `exit_reason`



Shared failure fields:

- `failed_stage`

- `failure_code`

- `failure_category`

- `failure_reason`

- `failure_summary`



## File Contracts



### `.runs/latest-run.json`



Use this file when an external system wants one stable path that always points to the newest run.



Expected top-level fields:

- `skill_name`

- `schema_version`

- `latest_updated_at`

- `status`

- `run_outcome`

- `status_badge`

- `exit_reason`

- `failed_stage`

- `failure_code`

- `failure_category`

- `failure_reason`

- `failure_summary`

- `output_dir`

- `run_status_path`

- `pipeline_summary_path`



Notes:

- `output_dir` points to the newest run directory.

- `run_status_path` and `pipeline_summary_path` are the preferred drill-down paths.

- This file is intentionally small and suitable for polling.



### `run_status.json`



Use this file when an external system knows the run directory and only needs a small status payload.



Expected top-level fields:

- `skill_name`

- `schema_version`

- `status`

- `run_outcome`

- `status_badge`

- `exit_reason`

- `failed_stage`

- `failure_code`

- `failure_category`

- `failure_reason`

- `failure_summary`

- `started_at`

- `ended_at`

- `source_pack`

- `output_dir`



Notes:

- This is the preferred file for alert routing and dashboard badges.

- It intentionally excludes full stage detail.



### `pipeline_summary.json`



Use this file when an operator or orchestrator needs the main run result plus summarized failure context.



Expected top-level fields:

- `skill_name`

- `schema_version`

- `status`

- `run_outcome`

- `status_badge`

- `exit_reason`

- `started_at`

- `ended_at`

- `source_pack`

- `output_dir`

- `failed_stage`

- `failure_code`

- `failure_category`

- `failure_reason`

- `failure_retryable`

- `failure_attempt`

- `failure_summary`

- `resolved_resume_from`

- `resume_reason`

- `stage_results`



Notes:

- `stage_results` is a summary structure, not a full replacement for `stage-logs/`.

- This file should be the first place a human operator checks after a failed run.



### `run_live_manifest.json`



Use this file when you need the full execution record for auditing or deeper automation.



Expected top-level fields:

- `skill_name`

- `schema_version`

- `status`

- `run_outcome`

- `status_badge`

- `exit_reason`

- `started_at`

- `ended_at`

- `source_pack`

- `output_dir`

- `resolved_resume_from`

- `resume_reason`

- `artifacts`

- `stages`



Notes:

- `stages` contains per-stage execution records.

- `artifacts` is the most complete machine-readable artifact index for a run.

- `artifacts.preview_md` points to the local markdown preview generated from `body_markdown`.

- `artifacts.preview_html` points to the local HTML preview rendered from that same markdown.



## Field Semantics



### `run_outcome`



Allowed values:

- `success`: all stages executed in the current invocation.

- `partial`: the run completed, but one or more earlier stages were skipped because of resume.

- `failed`: the run did not complete successfully.

- `noop`: the run finished without executing stages, usually because `--auto-resume` found a complete run.



### `status_badge`



Allowed values:

- `ok`: successful full run.

- `warn`: successful resumed or partial run.

- `error`: failed run.

- `idle`: no-op run.



### `exit_reason`



Current values include:

- `completed_full_run`

- `completed_with_resume`

- `auto_resume_noop`

- `failed_input_error`

- `failed_auth_error`

- `failed_upstream_rate_limit`



External systems should treat `exit_reason` as stable within the current schema family and use it for routing, not prose parsing.



### `failure_code`



Current standardized values:

- `input_error`

- `config_error`

- `auth_error`

- `missing_output`

- `upstream_rate_limit`

- `upstream_timeout`

- `upstream_network_error`

- `upstream_server_error`

- `internal_error`

- `unknown_error`



These codes are the canonical machine-readable failure classification.



## Conventions



- Timestamps should be treated as ISO 8601 strings.

- Paths should be treated as local filesystem paths produced by the current environment.

- Missing failure fields may be `null` on successful or no-op runs.

- Additive fields may appear in future `1.x` releases; consumers should ignore unknown fields.



## Compatibility Policy



The schema stays at `1.0` when changes are additive and non-breaking, for example:

- adding a new optional field

- adding a new artifact path

- adding a new informational summary field



The schema must be version-bumped when a breaking change happens, for example:

- removing a documented field

- renaming a documented field

- changing the meaning of a documented field

- changing a field type in a way that breaks existing consumers

- changing the expected allowed values of a documented enum without backward compatibility



Recommended consumer behavior:

1. Check `skill_name` first.

2. Check `schema_version` second.

3. Ignore unknown fields.

4. Fail closed only when a required documented field is missing or semantically incompatible.



## Related Documents



- [`SKILL.md`](./SKILL.md): high-level skill contract and workflow

- [`CONFIG.md`](./CONFIG.md): merged config structure and environment usage

- [`OPERATIONS.md`](./OPERATIONS.md): runtime SOP, retries, resume, and incident handling



