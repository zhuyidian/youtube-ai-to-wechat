from __future__ import annotations

from typing import Iterable


def dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def choose_primary_item(research_items: list[dict]) -> dict:
    return research_items[0] if research_items else {}


def route_article_type(task: dict, research_items: list[dict]) -> str:
    requested = task.get("article_type", "auto")
    if requested and requested != "auto":
        return requested

    total_claims = sum(len(item.get("claims_to_verify", [])) for item in research_items)
    if len(research_items) >= 2 or total_claims >= 3:
        return "deep_analysis"

    primary = choose_primary_item(research_items)
    title = primary.get("title", "").lower()
    if any(token in title for token in ("launch", "release", "update", "announces", "new")):
        return "ai_news_brief"
    return "video_summary"


def build_title_candidates(topic: str, primary: dict, article_type: str) -> list[str]:
    primary_title = primary.get("title", topic).strip() or topic
    if article_type == "deep_analysis":
        return [
            f"{topic}，真正值得关注的不是模型，而是工作流变化",
            f"{primary_title}：这次 AI Agents 为什么值得认真看",
            f"从 {topic} 到真正可落地的智能体，中间到底变了什么？",
        ]
    if article_type == "ai_news_brief":
        return [
            f"{primary_title}：今天最值得看的一个 AI 更新",
            f"{topic} 有新进展了，重点只有这 3 个",
            f"{primary_title}：发生了什么，为什么重要",
        ]
    return [
        f"{primary_title}：一篇看懂这条 AI 视频到底讲了什么",
        f"{topic} 到底值不值得关注，这篇帮你拆开",
        f"{primary_title}，关键信息我替你提炼好了",
    ]


def build_outline_payload(source_pack: dict) -> dict:
    task = source_pack.get("task", {})
    research_items = source_pack.get("research_items", [])
    primary = choose_primary_item(research_items)
    article_type = route_article_type(task, research_items)
    topic = task.get("topic") or (task.get("keywords") or ["AI Topic"])[0]
    title_candidates = build_title_candidates(topic, primary, article_type)

    primary_claims = primary.get("claims_to_verify", [])[:3]
    context_claims = []
    for item in research_items[1:]:
        context_claims.extend(item.get("claims_to_verify", [])[:2])

    outline_sections = [
        {
            "heading": "这次更新，真正值得看的是什么",
            "purpose": "开头先给判断，不先铺很长背景。",
            "bullets": [
                primary.get("article_angle_hint", f"解释 {topic} 为什么值得关注。"),
                "先告诉读者最重要的判断，再进入拆解。",
            ],
            "source_video_ids": [primary.get("video_id")],
        },
        {
            "heading": "先把发生了什么讲清楚",
            "purpose": "用最少篇幅复原事件本身。",
            "bullets": primary_claims or ["整理主视频中的核心变化和关键信息。"],
            "source_video_ids": [primary.get("video_id")],
        },
        {
            "heading": "为什么这件事比表面上更重要",
            "purpose": "把产品变化、工作流变化、行业影响拆开。",
            "bullets": [
                "区分模型能力变化和产品工作流变化。",
                "说明它对开发者、普通读者和创业者分别意味着什么。",
                *context_claims[:2],
            ],
            "source_video_ids": [item.get("video_id") for item in research_items if item.get("video_id")],
        },
        {
            "heading": "哪些说法还需要继续核验",
            "purpose": "保留审慎感，避免公众号写法把不确定性抹掉。",
            "bullets": dedupe(
                claim for item in research_items for claim in item.get("claims_to_verify", [])
            )[:4],
            "source_video_ids": [item.get("video_id") for item in research_items if item.get("video_id")],
        },
        {
            "heading": "最后给读者一个判断",
            "purpose": "收束全文，输出明确立场和行动建议。",
            "bullets": [
                f"总结 {topic} 对 AI 从业者、开发者和普通读者的实际意义。",
                "给出后续最值得继续跟踪的方向。",
            ],
            "source_video_ids": [primary.get("video_id")],
        },
    ]

    return {
        "task": task,
        "article_type": article_type,
        "title_candidates": title_candidates,
        "selected_title": title_candidates[0],
        "summary_angle": primary.get("article_angle_hint", f"解释 {topic} 的核心变化与实际影响。"),
        "primary_item": primary,
        "research_items": research_items,
        "sections": outline_sections,
        "open_questions": dedupe(
            claim for item in research_items for claim in item.get("claims_to_verify", [])
        )[:5],
    }


def render_information_article(outline: dict) -> dict:
    primary = outline.get("primary_item", {})
    topic = outline.get("task", {}).get("topic") or primary.get("title", "AI topic")
    sections_md: list[str] = []

    intro = [
        "## 导语",
        outline.get("summary_angle", ""),
        f"这篇先不急着下判断，而是把 {topic} 里真正重要的变化、影响和待核验点拆开。",
    ]
    sections_md.append("\n".join(intro))

    for section in outline.get("sections", []):
        body_lines = [f"## {section['heading']}", section.get("purpose", "")]
        for bullet in section.get("bullets", []):
            if bullet:
                body_lines.append(f"- {bullet}")
        sections_md.append("\n".join(body_lines))

    source_notes = []
    for item in outline.get("research_items", []):
        source_notes.append(
            {
                "video_id": item.get("video_id"),
                "title": item.get("title"),
                "url": item.get("url"),
                "channel_id": item.get("channel_id"),
                "channel_title": item.get("channel_title"),
                "published_at": item.get("published_at"),
                "sources": item.get("sources", []),
            }
        )

    return {
        "task": outline.get("task", {}),
        "article_type": outline.get("article_type"),
        "title_candidates": outline.get("title_candidates", []),
        "selected_title": outline.get("selected_title"),
        "body_markdown": "\n\n".join(sections_md),
        "source_notes": source_notes,
        "review_flags": outline.get("open_questions", []),
    }


def rewrite_wechat_article(article: dict) -> dict:
    title = article.get("selected_title") or (article.get("title_candidates") or ["AI 内容草稿"])[0]
    digest = "这篇文章把 YouTube 里的信息拆成了事件、影响和待核验点，适合公众号读者快速读懂。"

    lines = [
        f"# {title}",
        "",
        "很多 AI 内容的问题，不是信息不够，而是重点不清。",
        "",
        "这次真正值得看的，不只是某个模型又变强了，而是工作流、产品化路径和落地门槛一起在变。",
        "",
    ]

    for block in article.get("body_markdown", "").split("## "):
        stripped = block.strip()
        if not stripped:
            continue
        section_lines = stripped.splitlines()
        heading = section_lines[0].strip()
        body_lines = [line.strip() for line in section_lines[1:] if line.strip()]
        lines.append(f"## {heading}")
        for line in body_lines:
            lines.append(line)
        lines.append("")

    lines.extend(
        [
            "## 最后",
            "如果你关心的是 AI 真正怎么落地，而不是只看热闹，那么最该跟踪的永远是三件事：工作流有没有变、门槛有没有降、结果能不能复用。",
            "",
            "这也是这类选题最适合公众号深度拆解的原因。",
        ]
    )

    return {
        "task": article.get("task", {}),
        "article_type": article.get("article_type"),
        "final_title": title,
        "digest": digest,
        "cover_copy": title,
        "body_markdown": "\n".join(lines).strip(),
        "source_notes": article.get("source_notes", []),
        "review_flags": article.get("review_flags", []),
    }

