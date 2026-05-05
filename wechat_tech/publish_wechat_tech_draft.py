#!/usr/bin/env python3
"""Publish wechat tech daily markdown draft to WeChat Official Account drafts."""
from __future__ import annotations

import json
import logging
import os
import re
import sys
from html import escape as html_escape
from pathlib import Path
from urllib.parse import quote
from urllib.error import HTTPError
from urllib.request import Request, urlopen

LOGGER = logging.getLogger("publish_wechat_tech_draft")
USER_AGENT = "Mozilla/5.0 (compatible; auto-video/1.0; +https://github.com/)"

WECHAT_ACCESS_TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
WECHAT_ADD_DRAFT_URL = "https://api.weixin.qq.com/cgi-bin/draft/add"


def parse_args() -> dict:
    import argparse
    parser = argparse.ArgumentParser(description="Publish wechat tech draft to WeChat drafts.")
    parser.add_argument("--input-md", type=Path, required=True, help="Generated markdown draft file.")
    parser.add_argument("--app-id", default=os.getenv("AppID", ""), help="WeChat AppID.")
    parser.add_argument("--app-secret", default=os.getenv("AppSecret", ""), help="WeChat AppSecret.")
    parser.add_argument("--author", default=os.getenv("WECHAT_AUTHOR", "科技日报"), help="Article author.")
    parser.add_argument("--thumb-media-id", default=os.getenv("WECHAT_THUMB_MEDIA_ID", ""), help="WeChat thumb media ID for cover.")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    return parser.parse_args()


def setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def get_access_token(app_id: str, app_secret: str) -> str:
    url = f"{WECHAT_ACCESS_TOKEN_URL}?grant_type=client_credential&appid={quote(app_id)}&secret={quote(app_secret)}"
    request = Request(url, headers={"User-Agent": USER_AGENT}, method="GET")
    with urlopen(request, timeout=20) as response:
        data = json.loads(response.read().decode("utf-8"))
    if "access_token" not in data:
        raise RuntimeError(f"Failed to get access token: {data}")
    return data["access_token"]


def md_to_wechat_html(md_text: str) -> str:
    """Convert markdown draft to WeChat-compatible HTML.
    
    Handles: headings, bold, italic, blockquotes, lists, tables, horizontal rules,
    links, inline code, code blocks, and raw HTML blocks (div, img, etc.).
    """
    lines = md_text.split("\n")
    html_parts: list[str] = []
    in_code_block = False
    in_table = False
    table_rows: list[list[str]] = []
    list_items: list[str] = []
    in_list = False
    blockquote_lines: list[str] = []
    in_blockquote = False
    paragraph_lines: list[str] = []

    def flush_paragraph():
        nonlocal paragraph_lines
        if paragraph_lines:
            text = " ".join(paragraph_lines).strip()
            if text:
                text = process_inline(text)
                html_parts.append(f"<p>{text}</p>")
            paragraph_lines = []

    def flush_list():
        nonlocal list_items, in_list
        if list_items:
            items_html = "".join(f"<li>{process_inline(item)}</li>" for item in list_items)
            html_parts.append(f"<ul>{items_html}</ul>")
            list_items = []
        in_list = False

    def flush_blockquote():
        nonlocal blockquote_lines, in_blockquote
        if blockquote_lines:
            inner = " ".join(blockquote_lines).strip()
            inner = process_inline(inner)
            html_parts.append(f"<blockquote style=\"border-left:4px solid #ddd;padding-left:16px;color:#666;margin:12px 0;\">{inner}</blockquote>")
            blockquote_lines = []
        in_blockquote = False

    def flush_table():
        nonlocal table_rows, in_table
        if table_rows:
            rows_html = ""
            for i, row in enumerate(table_rows):
                if i == 0:
                    cells = "".join(f"<th style=\"border:1px solid #ddd;padding:8px;background:#f5f5f5;\">{process_inline(cell.strip())}</th>" for cell in row)
                    rows_html += f"<thead><tr>{cells}</tr></thead>"
                else:
                    cells = "".join(f"<td style=\"border:1px solid #ddd;padding:8px;\">{process_inline(cell.strip())}</td>" for cell in row)
                    rows_html += f"<tbody><tr>{cells}</tr></tbody>"
            html_parts.append(f"<table style=\"border-collapse:collapse;width:100%;margin:12px 0;\">{rows_html}</table>")
            table_rows = []
        in_table = False

    def process_inline(text: str) -> str:
        """Process inline markdown: **bold**, *italic*, `code`, [link](url)."""
        # Code (before bold/italic to avoid conflicts)
        text = re.sub(r"`([^`]+)`", r'<code style="background:#f5f5f5;padding:2px 6px;border-radius:4px;font-size:0.9em;">\1</code>', text)
        # Bold
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        # Italic
        text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
        # Links
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" style="color:#576b95;">\1</a>', text)
        return text

    for line in lines:
        # Raw HTML passthrough (div, img, table, etc.)
        if re.match(r"^\s*<(div|img|p|style|script|hr|section|article|blockquote|table|thead|tbody|tr|th|td)", line, re.IGNORECASE):
            flush_paragraph()
            flush_list()
            flush_blockquote()
            flush_table()
            html_parts.append(line)
            continue

        # End of raw HTML block
        if re.match(r"^\s*</(div|p|blockquote|section|article|table)", line, re.IGNORECASE):
            flush_paragraph()
            flush_list()
            flush_blockquote()
            flush_table()
            html_parts.append(line)
            continue

        # Code block
        if line.strip().startswith("```"):
            flush_paragraph()
            flush_list()
            flush_blockquote()
            flush_table()
            if in_code_block:
                html_parts.append("</pre>")
                in_code_block = False
            else:
                lang = line.strip()[3:].strip()
                html_parts.append(f'<pre style="background:#f5f5f5;padding:12px;border-radius:8px;overflow-x:auto;font-size:0.85em;"><code class="language-{lang}">')
                in_code_block = True
            continue

        if in_code_block:
            html_parts.append(html_escape(line))
            continue

        # Table row
        if re.match(r"^\s*\|", line):
            flush_paragraph()
            flush_list()
            flush_blockquote()
            # Skip separator row like |---|---|
            if re.match(r"^\s*\|[-:\s|]+\|\s*$", line):
                continue
            if not in_table:
                in_table = True
                table_rows = []
            cells = [c.strip() for c in line.strip().split("|")[1:-1]]
            table_rows.append(cells)
            continue
        elif in_table:
            flush_table()

        # Heading
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            flush_paragraph()
            flush_list()
            flush_blockquote()
            level = len(heading_match.group(1))
            text = process_inline(heading_match.group(2))
            # WeChat has specific heading styles
            if level <= 2:
                html_parts.append(f'<section style="margin:20px 0 10px;"><span style="display:inline-block;padding-left:12px;border-left:4px solid #1a73e8;font-size:1.2em;font-weight:bold;color:#333;">{text}</span></section>')
            elif level <= 3:
                html_parts.append(f'<section style="margin:16px 0 8px;"><span style="font-size:1.1em;font-weight:bold;color:#333;">{text}</span></section>')
            else:
                html_parts.append(f'<p style="font-size:1em;font-weight:bold;color:#555;margin:12px 0 6px;">{text}</span></p>')
            continue

        # Horizontal rule
        if re.match(r"^\s*---+\s*$", line) or re.match(r"^\s*\*\*\*\s*$", line):
            flush_paragraph()
            flush_list()
            flush_blockquote()
            flush_table()
            html_parts.append('<hr style="border:none;border-top:1px solid #e5e5e5;margin:20px 0;"/>')
            continue

        # Blockquote
        bq_match = re.match(r"^>\s*(.+)$", line)
        if bq_match:
            flush_paragraph()
            flush_list()
            flush_table()
            in_blockquote = True
            blockquote_lines.append(bq_match.group(1))
            continue
        elif in_blockquote:
            flush_blockquote()

        # List item
        list_match = re.match(r"^[\s]*[-*+]\s+(.+)$", line)
        if list_match:
            flush_paragraph()
            flush_blockquote()
            flush_table()
            in_list = True
            list_items.append(list_match.group(1))
            continue
        elif in_list:
            flush_list()

        # Empty line
        if not line.strip():
            flush_paragraph()
            flush_list()
            flush_blockquote()
            flush_table()
            continue

        # Regular text (paragraph)
        flush_list()
        flush_blockquote()
        flush_table()
        paragraph_lines.append(line)

    # Flush remaining
    flush_paragraph()
    flush_list()
    flush_blockquote()
    flush_table()
    if in_code_block:
        html_parts.append("</pre>")

    return "\n".join(html_parts)


def extract_title_from_md(md_text: str) -> str:
    """Extract article title from markdown draft."""
    # Try emoji heading pattern: 🔥 keyword1 ｜ keyword2 ｜ keyword3
    match = re.search(r"🔥\s*(.+)$", md_text, re.MULTILINE)
    if match:
        return match.group(1).strip()

    # Try first h1 heading
    match = re.search(r"^#\s+(.+)$", md_text, re.MULTILINE)
    if match:
        return match.group(1).strip()

    return "科技日报"


def extract_digest_from_md(md_text: str) -> str:
    """Extract a short digest from the markdown draft."""
    # Try to find 今日导读 section
    match = re.search(r"【今日导读】\s*\n?\s*>\s*(.+?)(?:\n|$)", md_text)
    if match:
        text = match.group(1).strip()
        if len(text) <= 120:
            return text
        return text[:119] + "…"

    # Fallback: first 120 chars after removing markdown
    clean = re.sub(r"[#*>\[\]_|`~-]", "", md_text)
    clean = re.sub(r"\s+", " ", clean).strip()
    if len(clean) <= 120:
        return clean
    return clean[:119] + "…"


def create_draft(access_token: str, title: str, author: str, digest: str, content_html: str, thumb_media_id: str) -> str:
    """Create a draft in WeChat Official Account."""
    url = f"{WECHAT_ADD_DRAFT_URL}?access_token={quote(access_token)}"
    payload = {
        "articles": [
            {
                "title": title,
                "author": author,
                "digest": digest,
                "content": content_html,
                "content_source_url": "",
                "thumb_media_id": thumb_media_id,
                "need_open_comment": 0,
                "only_fans_can_comment": 0,
            }
        ]
    }

    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="ignore")
        except Exception:
            pass
        raise RuntimeError(f"WeChat API HTTP {exc.code}: {body}") from exc

    if "errcode" in data and data["errcode"] != 0:
        raise RuntimeError(f"WeChat draft creation failed: {data}")

    media_id = data.get("media_id")
    if not media_id:
        raise RuntimeError(f"WeChat response missing media_id: {data}")

    return media_id


def main() -> int:
    args = parse_args()
    setup_logging(args.verbose)

    # Read markdown draft
    md_path = args.input_md
    if not md_path.exists():
        LOGGER.error("draft file not found: %s", md_path)
        return 1

    md_text = md_path.read_text(encoding="utf-8")
    if not md_text.strip():
        LOGGER.error("draft file is empty: %s", md_path)
        return 1

    # Validate required credentials
    if not args.app_id or not args.app_secret:
        LOGGER.error("WeChat AppID and AppSecret are required. Set --app-id/--app-secret or AppID/AppSecret env vars.")
        return 1

    if not args.thumb_media_id:
        LOGGER.error("WeChat thumb_media_id is required. Set --thumb-media-id or WECHAT_THUMB_MEDIA_ID env var.")
        return 1

    # Convert markdown to HTML
    content_html = md_to_wechat_html(md_text)

    # Extract metadata
    title = extract_title_from_md(md_text)
    digest = extract_digest_from_md(md_text)

    LOGGER.info("title: %s", title)
    LOGGER.info("digest: %s", digest)
    LOGGER.info("content length: %d chars", len(content_html))

    # Get access token
    access_token = get_access_token(args.app_id, args.app_secret)
    LOGGER.info("access token obtained")

    # Create draft
    media_id = create_draft(
        access_token=access_token,
        title=title,
        author=args.author,
        digest=digest,
        content_html=content_html,
        thumb_media_id=args.thumb_media_id,
    )

    LOGGER.info("draft created successfully! media_id=%s", media_id)
    print(f"wechat_draft_media_id={media_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
