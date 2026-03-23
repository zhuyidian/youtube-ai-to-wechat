#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

STAGE_ORDER = [
    "outline",
    "draft",
    "rewrite",
    "headline",
    "images",
    "infographic",
    "format",
    "inject",
    "publish",
]

SKILL_NAME = "youtube-ai-to-wechat"
SCHEMA_VERSION = "1.0"

WINDOWS_CRASH_RETURN_CODES = {3221225477, -1073741819}


FAILURE_RULES = [
    {
        "code": "auth_error",
        "category": "auth",
        "retryable": False,
        "patterns": [
            r"unauthorized",
            r"forbidden",
            r"http error\s*401",
            r"http error\s*403",
            r"status code\s*401",
            r"status code\s*403",
            r"\b401\b",
            r"\b403\b",
        ],
    },
    {
        "code": "upstream_rate_limit",
        "category": "upstream",
        "retryable": True,
        "patterns": [
            r"rate limit",
            r"too many requests",
            r"http\s*429",
            r"status code\s*429",
            r"429",
        ],
    },
    {
        "code": "upstream_timeout",
        "category": "upstream",
        "retryable": True,
        "patterns": [
            r"timed out",
            r"timeouterror",
            r"read timeout",
            r"connect timeout",
            r"gateway timeout",
        ],
    },
    {
        "code": "upstream_network_error",
        "category": "upstream",
        "retryable": True,
        "patterns": [
            r"connection reset",
            r"connection aborted",
            r"connection refused",
            r"temporar",
            r"temporary failure",
            r"try again",
            r"network is unreachable",
            r"name or service not known",
            r"dns",
        ],
    },
    {
        "code": "upstream_server_error",
        "category": "upstream",
        "retryable": True,
        "patterns": [
            r"http\s*5\d\d",
            r"status code\s*5\d\d",
            r"service unavailable",
            r"bad gateway",
        ],
    },
    {
        "code": "config_error",
        "category": "config",
        "retryable": False,
        "patterns": [
            r"missing env var",
            r"cover media_id",
            r"api key",
            r"permission denied",
        ],
    },
    {
        "code": "input_error",
        "category": "input",
        "retryable": False,
        "patterns": [
            r"filenotfounderror",
            r"jsondecodeerror",
            r"no such file or directory",
            r"cannot resume because required earlier artifacts are missing",
            r"argument",
            r"invalid",
        ],
    },
    {
        "code": "missing_output",
        "category": "output",
        "retryable": False,
        "patterns": [
            r"expected output missing",
        ],
    },
    {
        "code": "internal_error",
        "category": "internal",
        "retryable": False,
        "patterns": [
            r"valueerror",
            r"keyerror",
            r"typeerror",
            r"syntaxerror",
            r"modulenotfounderror",
        ],
    },
]
@dataclass

class StageSpec:

    label: str

    command: list[str]

    output_path: Path





def utc_now() -> str:

    return datetime.now(timezone.utc).isoformat()





def classify_failure(returncode: int, stdout_text: str, stderr_text: str, artifact_exists: bool) -> tuple[str, str, bool, str]:

    combined = "\n".join(part for part in [stdout_text, stderr_text] if part).strip()

    lower_combined = combined.lower()



    if returncode == 0 and not artifact_exists:

        return "missing_output", "output", False, "stage exited successfully but did not produce its expected artifact"



    if returncode in WINDOWS_CRASH_RETURN_CODES:

        return "subprocess_crash", "runtime", True, f"stage process crashed with Windows return code {returncode}"



    for rule in FAILURE_RULES:

        for pattern in rule["patterns"]:

            if re.search(pattern, lower_combined, re.IGNORECASE):

                return rule["code"], rule["category"], rule["retryable"], f"matched failure pattern: {pattern}"



    if returncode != 0 and not combined:

        return "unknown_error", "unknown", False, "stage failed without stderr/stdout details"



    return "unknown_error", "unknown", False, "failure did not match a known standardized error code"





def should_retry_failure(failure_code: str, is_retryable: bool, retry_policy: str) -> bool:

    if retry_policy == "never":

        return False

    if retry_policy == "always":

        return True

    return is_retryable





def write_json(path: Path, payload: dict) -> None:

    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8-sig")





def render_command(command: list[str]) -> str:

    return " ".join(command)





def append_attempt_log(path: Path, attempt: int, stdout_text: str, stderr_text: str) -> None:

    with path.open("a", encoding="utf-8-sig") as handle:

        handle.write(f"=== Attempt {attempt} ===\n")

        if stdout_text:

            handle.write("[stdout]\n")

            handle.write(stdout_text)

            if not stdout_text.endswith("\n"):

                handle.write("\n")

        if stderr_text:

            handle.write("[stderr]\n")

            handle.write(stderr_text)

            if not stderr_text.endswith("\n"):

                handle.write("\n")





def print_captured(stdout_text: str, stderr_text: str) -> None:

    if stdout_text:

        print(stdout_text, end="" if stdout_text.endswith("\n") else "\n")

    if stderr_text:

        print(stderr_text, end="" if stderr_text.endswith("\n") else "\n", file=sys.stderr)





def read_stage_status(stage_logs_dir: Path, stage_index: int, label: str) -> str | None:

    stage_log_path = stage_logs_dir / f"{stage_index:02d}_{label}.json"

    if not stage_log_path.exists():

        return None

    try:

        payload = json.loads(stage_log_path.read_text(encoding="utf-8-sig"))

    except json.JSONDecodeError:

        return "invalid"

    return payload.get("status")





def resolve_resume_index(

    stage_specs: list[StageSpec],

    stage_logs_dir: Path,

    resume_from: str | None,

    auto_resume: bool,

) -> tuple[int, str | None, str | None]:

    if resume_from and auto_resume:

        raise ValueError("--resume-from and --auto-resume cannot be used together")



    if resume_from:

        labels = [stage.label for stage in stage_specs]

        if resume_from not in labels:

            raise ValueError(f"Unknown resume stage: {resume_from}")

        resume_index = labels.index(resume_from)

        missing = [str(stage.output_path) for stage in stage_specs[:resume_index] if not stage.output_path.exists()]

        if missing:

            missing_list = "\n".join(missing)

            raise FileNotFoundError(

                "Cannot resume because required earlier artifacts are missing:\n" + missing_list

            )

        return resume_index, resume_from, f"manual resume_from={resume_from}"



    if not auto_resume:

        return 0, None, None



    if all(stage.output_path.exists() for stage in stage_specs):

        return len(stage_specs), None, "auto-resume found a fully completed run; nothing to execute"



    for index, stage in enumerate(stage_specs):

        if not stage.output_path.exists():

            return index, stage.label, f"auto-resume selected {stage.label} because output is missing"

        stage_status = read_stage_status(stage_logs_dir, index, stage.label)

        if stage_status and stage_status not in {"completed", "skipped"}:

            return index, stage.label, f"auto-resume selected {stage.label} because stage log status is {stage_status}"



    return len(stage_specs), None, "auto-resume found no missing outputs and no failed stages; nothing to execute"





def derive_run_outcome(pipeline_status: str, stage_results: list[dict]) -> str:

    if pipeline_status != "completed":

        return "failed"

    statuses = [stage.get("status") for stage in stage_results]

    if not statuses:

        return "noop"

    if all(status == "skipped" for status in statuses):

        return "noop"

    if any(status == "skipped" for status in statuses):

        return "partial"

    return "success"





def derive_status_badge(run_outcome: str) -> str:

    if run_outcome == "success":

        return "ok"

    if run_outcome == "partial":

        return "warn"

    if run_outcome == "failed":

        return "error"

    return "idle"





def derive_exit_reason(

    run_outcome: str,

    failure_code: str | None,

    auto_resume: bool,

    resolved_resume_from: str | None,

) -> str:

    if run_outcome == "success":

        return "completed_full_run"

    if run_outcome == "partial":

        return "completed_with_resume"

    if run_outcome == "noop":

        if auto_resume:

            return "auto_resume_noop"

        return "no_work_performed"

    if failure_code:

        return f"failed_{failure_code}"

    if resolved_resume_from:

        return f"failed_after_resume_{resolved_resume_from}"

    return "failed_unknown_error"





def extract_failure_summary(stage_results: list[dict], failed_stage: str | None) -> dict[str, object]:

    if not failed_stage:

        return {

            "failure_code": None,

            "failure_category": None,

            "failure_reason": None,

            "failure_retryable": None,

            "failure_attempt": None,

            "failure_summary": None,

        }



    for stage in reversed(stage_results):

        if stage.get("label") != failed_stage:

            continue

        for attempt in reversed(stage.get("attempts", [])):

            if attempt.get("status") != "failed":

                continue

            failure_code = attempt.get("failure_code")

            failure_reason = attempt.get("failure_reason")

            return {

                "failure_code": failure_code,

                "failure_category": attempt.get("failure_category"),

                "failure_reason": failure_reason,

                "failure_retryable": attempt.get("retryable"),

                "failure_attempt": attempt.get("attempt"),

                "failure_summary": f"{failed_stage}:{failure_code}:{failure_reason}" if failure_code and failure_reason else None,

            }

        return {

            "failure_code": None,

            "failure_category": None,

            "failure_reason": None,

            "failure_retryable": None,

            "failure_attempt": None,

            "failure_summary": f"{failed_stage}:failed_without_attempt_details",

        }



    return {

        "failure_code": None,

        "failure_category": None,

        "failure_reason": None,

        "failure_retryable": None,

        "failure_attempt": None,

        "failure_summary": f"{failed_stage}:failed_stage_not_found_in_stage_results",

    }





def run_stage(

    stage: StageSpec,

    stage_index: int,

    stage_logs_dir: Path,

    max_retries: int,

    retry_delay_seconds: float,

    retry_policy: str,

) -> dict:

    stage_log_path = stage_logs_dir / f"{stage_index:02d}_{stage.label}.json"

    text_log_path = stage_logs_dir / f"{stage_index:02d}_{stage.label}.log"

    command_text = render_command(stage.command)

    total_attempts = max_retries + 1

    attempts: list[dict] = []

    overall_start = utc_now()



    print(f"[{stage.label}] {command_text}")



    for attempt in range(1, total_attempts + 1):

        attempt_start_epoch = time.time()

        attempt_start = utc_now()

        completed = subprocess.run(

            stage.command,

            capture_output=True,

            text=True,

            encoding="utf-8-sig",

            errors="replace",

        )

        attempt_end = utc_now()

        duration_seconds = round(time.time() - attempt_start_epoch, 3)

        stdout_text = completed.stdout or ""

        stderr_text = completed.stderr or ""

        print_captured(stdout_text, stderr_text)

        append_attempt_log(text_log_path, attempt, stdout_text, stderr_text)



        artifact_exists = stage.output_path.exists()

        success = completed.returncode == 0 and artifact_exists

        if completed.returncode == 0 and not artifact_exists:

            stderr_text = (stderr_text + ("\n" if stderr_text else "") + f"Expected output missing: {stage.output_path}").strip()

            append_attempt_log(text_log_path, attempt, "", f"Expected output missing: {stage.output_path}")



        failure_code, failure_category, retryable, failure_reason = classify_failure(

            returncode=completed.returncode,

            stdout_text=stdout_text,

            stderr_text=stderr_text,

            artifact_exists=artifact_exists,

        )

        retry_allowed = should_retry_failure(failure_code, retryable, retry_policy)

        will_retry = (not success) and attempt < total_attempts and retry_allowed



        attempt_payload = {

            "attempt": attempt,

            "started_at": attempt_start,

            "ended_at": attempt_end,

            "duration_seconds": duration_seconds,

            "returncode": completed.returncode,

            "artifact_exists": artifact_exists,

            "status": "completed" if success else "failed",

            "failure_code": None if success else failure_code,

            "failure_category": None if success else failure_category,

            "failure_reason": None if success else failure_reason,

            "retryable": False if success else retryable,

            "retry_policy": retry_policy,

            "will_retry": will_retry,

            "stdout_log_path": str(text_log_path.resolve()),

            "stderr_log_path": str(text_log_path.resolve()),

            "stdout_preview": stdout_text[-1000:],

            "stderr_preview": stderr_text[-1000:],

        }

        attempts.append(attempt_payload)



        if success:

            stage_payload = {

                "label": stage.label,

                "command": command_text,

                "output_path": str(stage.output_path.resolve()),

                "status": "completed",

                "started_at": overall_start,

                "ended_at": attempt_end,

                "attempt_count": attempt,

                "max_retries": max_retries,

                "retry_policy": retry_policy,

                "log_path": str(text_log_path.resolve()),

                "attempts": attempts,

            }

            write_json(stage_log_path, stage_payload)

            return stage_payload



        if will_retry:

            print(

                f"[{stage.label}] attempt {attempt} failed with code={failure_code}; retrying in {retry_delay_seconds} seconds...",

                file=sys.stderr,

            )

            time.sleep(retry_delay_seconds)

            continue



        if not success:

            print(

                f"[{stage.label}] stopping retries after attempt {attempt}; code={failure_code}, retryable={retryable}, policy={retry_policy}",

                file=sys.stderr,

            )

            break



    failure_payload = {

        "label": stage.label,

        "command": command_text,

        "output_path": str(stage.output_path.resolve()),

        "status": "failed",

        "started_at": overall_start,

        "ended_at": utc_now(),

        "attempt_count": len(attempts),

        "max_retries": max_retries,

        "retry_policy": retry_policy,

        "log_path": str(text_log_path.resolve()),

        "attempts": attempts,

    }

    write_json(stage_log_path, failure_payload)

    raise subprocess.CalledProcessError(

        returncode=attempts[-1]["returncode"],

        cmd=stage.command,

        output=attempts[-1]["stdout_preview"],

        stderr=attempts[-1]["stderr_preview"],

    )





def build_stage_specs(

    python: str,

    script_dir: Path,

    source_pack: str,

    paths: dict[str, Path],

    llm_config: str | None,

    nanobanana_config: str | None,

    brand_config: str | None,

    publish_config: str | None,

    execute_llm: bool,

    execute_images: bool,

    execute_publish: bool,

    asset_dir: Path,

) -> list[StageSpec]:

    build_outline_cmd = [python, str(script_dir / "build_outline.py"), source_pack, "--output", str(paths["outline"])]

    if execute_llm:

        build_outline_cmd.append("--execute")

    if llm_config:

        build_outline_cmd.extend(["--config", llm_config])



    write_article_cmd = [python, str(script_dir / "write_article.py"), str(paths["outline"]), "--output", str(paths["article"])]

    if execute_llm:

        write_article_cmd.append("--execute")

    if llm_config:

        write_article_cmd.extend(["--config", llm_config])



    rewrite_cmd = [python, str(script_dir / "rewrite_wechat_style.py"), str(paths["article"]), "--output", str(paths["wechat"])]

    if execute_llm:

        rewrite_cmd.append("--execute")

    if llm_config:

        rewrite_cmd.extend(["--config", llm_config])



    headline_cmd = [python, str(script_dir / "generate_headlines.py"), str(paths["wechat"]), "--output", str(paths["headline"])]



    image_cmd = [python, str(script_dir / "generate_images_nanobanana.py"), str(paths["wechat"]), "--output", str(paths["image"]), "--asset-dir", str(asset_dir)]

    if execute_images:

        image_cmd.append("--execute")

    if nanobanana_config:

        image_cmd.extend(["--config", nanobanana_config])



    infographic_cmd = [python, str(script_dir / "build_infographic.py"), str(paths["wechat"]), "--output", str(paths["infographic"])]



    format_cmd = [python, str(script_dir / "format_wechat_article.py"), str(paths["headline"]), "--image-package", str(paths["image"]), "--output", str(paths["formatted"])]



    inject_cmd = [python, str(script_dir / "inject_assets.py"), str(paths["formatted"]), "--output", str(paths["final"])]

    if brand_config:

        inject_cmd.extend(["--brand-config", brand_config])



    publish_cmd = [python, str(script_dir / "publish_wechat_draft.py"), str(paths["final"]), "--image-package", str(paths["image"]), "--infographic-plan", str(paths["infographic"]), "--output", str(paths["draft"])]

    if publish_config:

        publish_cmd.extend(["--publish-config", publish_config])

    if execute_publish:

        publish_cmd.append("--execute")



    return [

        StageSpec("outline", build_outline_cmd, paths["outline"]),

        StageSpec("draft", write_article_cmd, paths["article"]),

        StageSpec("rewrite", rewrite_cmd, paths["wechat"]),

        StageSpec("headline", headline_cmd, paths["headline"]),

        StageSpec("images", image_cmd, paths["image"]),

        StageSpec("infographic", infographic_cmd, paths["infographic"]),

        StageSpec("format", format_cmd, paths["formatted"]),

        StageSpec("inject", inject_cmd, paths["final"]),

        StageSpec("publish", publish_cmd, paths["draft"]),

    ]





def main() -> None:

    parser = argparse.ArgumentParser(description="Run the post-research live pipeline from source pack to WeChat draft payload.")

    parser.add_argument("source_pack", help="Path to source_pack JSON.")

    parser.add_argument("--output-dir", required=True, help="Directory for pipeline artifacts.")

    parser.add_argument("--live-config", help="Single merged config JSON path. Preferred over individual config flags.")

    parser.add_argument("--llm-config", help="Deprecated: optional LLM override path. Prefer --live-config; accepts a dedicated LLM config or a merged live config.")

    parser.add_argument("--nanobanana-config", help="Deprecated: optional image override path. Prefer --live-config; accepts a dedicated Nanobanana config or a merged live config.")

    parser.add_argument("--brand-config", help="Deprecated: optional brand override path. Prefer --live-config; accepts a dedicated brand config or a merged live config.")

    parser.add_argument("--publish-config", help="Deprecated: optional publish override path. Prefer --live-config; accepts a dedicated publish config or a merged live config.")

    parser.add_argument("--asset-dir", help="Directory for generated image assets.")

    parser.add_argument("--execute-llm", action="store_true", help="Use the real LLM for outline, draft, and rewrite stages.")

    parser.add_argument("--execute-images", action="store_true", help="Call the real Nanobanana API.")

    parser.add_argument("--execute-publish", action="store_true", help="Call the real WeChat draft API.")

    parser.add_argument("--max-retries", type=int, default=0, help="Number of retries per stage after the first failure.")

    parser.add_argument("--retry-delay-seconds", type=float, default=2.0, help="Delay between retry attempts in seconds.")

    parser.add_argument("--retry-policy", choices=["smart", "always", "never"], default="smart", help="Retry policy. smart retries only retryable failures; always retries any failure; never disables retries even if max-retries > 0.")

    parser.add_argument("--resume-from", choices=STAGE_ORDER, help="Resume the pipeline from a specific stage. Earlier stage artifacts must already exist.")

    parser.add_argument("--auto-resume", action="store_true", help="Automatically resume from the earliest incomplete stage in the output directory.")

    args = parser.parse_args()



    if args.max_retries < 0:

        raise ValueError("--max-retries must be >= 0")

    if args.retry_delay_seconds < 0:

        raise ValueError("--retry-delay-seconds must be >= 0")



    deprecated_args_used = any([

        args.llm_config,

        args.nanobanana_config,

        args.brand_config,

        args.publish_config,

    ])

    if deprecated_args_used:

        print("Warning: individual config flags are deprecated. Prefer --live-config with a merged JSON file.", file=sys.stderr)



    script_dir = Path(__file__).resolve().parent

    output_dir = Path(args.output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    asset_dir = Path(args.asset_dir) if args.asset_dir else (output_dir / "generated-images")

    stage_logs_dir = output_dir / "stage-logs"

    stage_logs_dir.mkdir(parents=True, exist_ok=True)



    llm_config = args.llm_config or args.live_config

    nanobanana_config = args.nanobanana_config or args.live_config

    brand_config = args.brand_config or args.live_config

    publish_config = args.publish_config or args.live_config



    python = sys.executable

    paths = {

        "outline": output_dir / "outline_live.json",

        "article": output_dir / "article_draft_live.json",

        "wechat": output_dir / "wechat_article_live.json",

        "headline": output_dir / "headline_bundle_live.json",

        "image": output_dir / "image_package_live.json",

        "infographic": output_dir / "infographic_plan_live.json",

        "formatted": output_dir / "formatted_article_live.json",

        "final": output_dir / "final_article_package_live.json",
        "preview_md": output_dir / "article_preview.md",
        "preview_html": output_dir / "article_preview.html",

        "draft": output_dir / "draft_payload_live.json",

        "manifest": output_dir / "run_live_manifest.json",

        "summary": output_dir / "pipeline_summary.json",

        "status": output_dir / "run_status.json",

        "latest": output_dir.parent / "latest-run.json",

    }



    stage_specs = build_stage_specs(

        python=python,

        script_dir=script_dir,

        source_pack=args.source_pack,

        paths=paths,

        llm_config=llm_config,

        nanobanana_config=nanobanana_config,

        brand_config=brand_config,

        publish_config=publish_config,

        execute_llm=args.execute_llm,

        execute_images=args.execute_images,

        execute_publish=args.execute_publish,

        asset_dir=asset_dir,

    )



    resume_index, resolved_resume_from, resume_reason = resolve_resume_index(

        stage_specs=stage_specs,

        stage_logs_dir=stage_logs_dir,

        resume_from=args.resume_from,

        auto_resume=args.auto_resume,

    )

    if resume_reason:

        print(resume_reason)

    pipeline_started_at = utc_now()

    stage_results: list[dict] = []

    pipeline_status = "completed"

    failed_stage: str | None = None

    current_stage_index: int | None = None



    try:

        for index, stage in enumerate(stage_specs):

            current_stage_index = index

            if index < resume_index:

                skipped_payload = {

                    "label": stage.label,

                    "command": render_command(stage.command),

                    "output_path": str(stage.output_path.resolve()),

                    "status": "skipped",

                    "reason": resume_reason or f"resume_from={resolved_resume_from}",

                    "log_path": None,

                    "attempt_count": 0,

                    "max_retries": args.max_retries,

                    "retry_policy": args.retry_policy,

                    "started_at": pipeline_started_at,

                    "ended_at": pipeline_started_at,

                    "attempts": [],

                }

                stage_results.append(skipped_payload)

                write_json(stage_logs_dir / f"{index:02d}_{stage.label}.json", skipped_payload)

                skip_reason = resume_reason or f"resume_from={resolved_resume_from}"

                print(f"[{stage.label}] skipped because {skip_reason}")

                continue

            result = run_stage(stage, index, stage_logs_dir, args.max_retries, args.retry_delay_seconds, args.retry_policy)

            stage_results.append(result)

    except subprocess.CalledProcessError as exc:

        pipeline_status = "failed"

        if current_stage_index is not None:

            failed_stage = stage_specs[current_stage_index].label

        elif resume_index < len(stage_specs):

            failed_stage = stage_specs[resume_index].label

        else:

            failed_stage = None

        if current_stage_index is not None and failed_stage is not None:

            failed_log_path = stage_logs_dir / f"{current_stage_index:02d}_{failed_stage}.json"

            if failed_log_path.exists():

                failed_payload = json.loads(failed_log_path.read_text(encoding="utf-8-sig"))

                if not stage_results or stage_results[-1].get("label") != failed_stage:

                    stage_results.append(failed_payload)

        print(f"Pipeline failed at stage: {failed_stage}", file=sys.stderr)

        print(f"Last error returncode: {exc.returncode}", file=sys.stderr)

    finally:

        run_outcome = derive_run_outcome(pipeline_status, stage_results)

        failure_summary = extract_failure_summary(stage_results, failed_stage)

        status_badge = derive_status_badge(run_outcome)

        exit_reason = derive_exit_reason(run_outcome, failure_summary["failure_code"], args.auto_resume, resolved_resume_from)

        manifest = {

            "skill_name": SKILL_NAME,

            "schema_version": SCHEMA_VERSION,

            "source_pack": str(Path(args.source_pack).resolve()),

            "output_dir": str(output_dir.resolve()),

            "asset_dir": str(asset_dir.resolve()),

            "stage_logs_dir": str(stage_logs_dir.resolve()),

            "live_config": str(Path(args.live_config).resolve()) if args.live_config else None,

            "llm_config": str(Path(args.llm_config).resolve()) if args.llm_config else None,

            "nanobanana_config": str(Path(args.nanobanana_config).resolve()) if args.nanobanana_config else None,

            "brand_config": str(Path(args.brand_config).resolve()) if args.brand_config else None,

            "publish_config": str(Path(args.publish_config).resolve()) if args.publish_config else None,

            "execute_llm": args.execute_llm,

            "execute_images": args.execute_images,

            "execute_publish": args.execute_publish,

            "max_retries": args.max_retries,

            "retry_delay_seconds": args.retry_delay_seconds,

            "retry_policy": args.retry_policy,

            "resume_from": args.resume_from,

            "auto_resume": args.auto_resume,

            "resolved_resume_from": resolved_resume_from,

            "resume_reason": resume_reason,

            "run_outcome": run_outcome,

            "status_badge": status_badge,

            "exit_reason": exit_reason,

            "artifacts": {name: str(path.resolve()) for name, path in paths.items()},

        }

        write_json(paths["manifest"], manifest)



        summary = {

            "skill_name": SKILL_NAME,

            "schema_version": SCHEMA_VERSION,

            "status": pipeline_status,

            "run_outcome": run_outcome,

            "status_badge": status_badge,

            "exit_reason": exit_reason,

            "failed_stage": failed_stage,

            "failure_code": failure_summary["failure_code"],

            "failure_category": failure_summary["failure_category"],

            "failure_reason": failure_summary["failure_reason"],

            "failure_retryable": failure_summary["failure_retryable"],

            "failure_attempt": failure_summary["failure_attempt"],

            "failure_summary": failure_summary["failure_summary"],

            "started_at": pipeline_started_at,

            "ended_at": utc_now(),

            "source_pack": str(Path(args.source_pack).resolve()),

            "output_dir": str(output_dir.resolve()),

            "stage_logs_dir": str(stage_logs_dir.resolve()),

            "resume_from": args.resume_from,

            "auto_resume": args.auto_resume,

            "resolved_resume_from": resolved_resume_from,

            "resume_reason": resume_reason,

            "max_retries": args.max_retries,

            "retry_delay_seconds": args.retry_delay_seconds,

            "retry_policy": args.retry_policy,

            "stages": stage_results,

        }

        write_json(paths["summary"], summary)



        run_status = {

            "skill_name": SKILL_NAME,

            "schema_version": SCHEMA_VERSION,

            "status": pipeline_status,

            "run_outcome": run_outcome,

            "status_badge": status_badge,

            "exit_reason": exit_reason,

            "failed_stage": failed_stage,

            "failure_code": failure_summary["failure_code"],

            "failure_category": failure_summary["failure_category"],

            "failure_reason": failure_summary["failure_reason"],

            "failure_summary": failure_summary["failure_summary"],

            "started_at": pipeline_started_at,

            "ended_at": summary["ended_at"],

            "source_pack": str(Path(args.source_pack).resolve()),

            "output_dir": str(output_dir.resolve()),

            "stage_logs_dir": str(stage_logs_dir.resolve()),

            "pipeline_summary_path": str(paths["summary"].resolve()),

            "run_live_manifest_path": str(paths["manifest"].resolve()),

        }

        write_json(paths["status"], run_status)



        latest_run = {

            "skill_name": SKILL_NAME,

            "schema_version": SCHEMA_VERSION,

            "latest_updated_at": run_status["ended_at"],

            "status": run_status["status"],

            "run_outcome": run_status["run_outcome"],

            "status_badge": run_status["status_badge"],

            "exit_reason": run_status["exit_reason"],

            "failed_stage": run_status["failed_stage"],

            "failure_code": run_status["failure_code"],

            "failure_category": run_status["failure_category"],

            "failure_reason": run_status["failure_reason"],

            "failure_summary": run_status["failure_summary"],

            "output_dir": run_status["output_dir"],

            "source_pack": run_status["source_pack"],

            "run_status_path": str(paths["status"].resolve()),

            "pipeline_summary_path": str(paths["summary"].resolve()),

            "run_live_manifest_path": str(paths["manifest"].resolve()),

            "stage_logs_dir": run_status["stage_logs_dir"],

        }

        write_json(paths["latest"], latest_run)

        print(f"Wrote {paths['manifest']}")

        print(f"Wrote {paths['summary']}")

        print(f"Wrote {paths['status']}")

        print(f"Wrote {paths['latest']}")



    if pipeline_status != "completed":

        raise SystemExit(1)





if __name__ == "__main__":

    main()











