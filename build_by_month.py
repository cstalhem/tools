#!/usr/bin/env python3
"""Generate by-month.html listing all tools grouped by creation month."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

GATHERED_LINKS_PATH = Path("gathered_links.json")
SITE_CONFIG_PATH = Path("site.json")
OUTPUT_PATH = Path("by-month.html")


def _load_config() -> dict:
    if SITE_CONFIG_PATH.exists():
        with SITE_CONFIG_PATH.open("r", encoding="utf-8") as fp:
            return json.load(fp)
    return {"title": "Tools", "github_repo": "", "author": ""}


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _first_n_words(text: str, n: int = 30) -> tuple[str, bool]:
    words = text.split()
    if len(words) <= n:
        return text, False
    return " ".join(words[:n]), True


def _extract_summary(docs_path: Path, word_limit: int = 30) -> tuple[str, bool]:
    if not docs_path.exists():
        return "", False
    try:
        content = docs_path.read_text("utf-8").strip()
    except OSError:
        return "", False

    if "<!--" in content:
        content = content.split("<!--", 1)[0]

    content_lines = [
        line for line in content.splitlines()
        if not line.lstrip().startswith("#")
    ]

    lines = []
    for line in content_lines:
        stripped = line.strip()
        if not stripped:
            if lines:
                break
            continue
        lines.append(stripped)

    paragraph = " ".join(lines)
    return _first_n_words(paragraph, word_limit)


def build_by_month():
    config = _load_config()
    site_title = config.get("title", "Tools")
    github_repo = config.get("github_repo", "")

    data = {}
    if GATHERED_LINKS_PATH.exists():
        with GATHERED_LINKS_PATH.open("r", encoding="utf-8") as fp:
            data = json.load(fp)

    pages = data.get("pages", {})
    if not pages:
        print("No pages found in gathered_links.json")
        return

    tools_by_month: dict[str, list[dict]] = defaultdict(list)

    for page_name, page_data in pages.items():
        commits = page_data.get("commits", [])
        if not commits:
            continue

        oldest_commit = commits[-1]
        created_date = _parse_iso(oldest_commit.get("date"))
        if created_date is None:
            continue

        month_key = created_date.strftime("%Y-%m")
        slug = page_name.replace(".html", "")
        docs_path = Path(f"{slug}.docs.md")
        summary, truncated = _extract_summary(docs_path)

        tools_by_month[month_key].append({
            "filename": page_name,
            "slug": slug,
            "created": created_date,
            "summary": summary,
            "truncated": truncated,
        })

    sorted_months = sorted(tools_by_month.keys(), reverse=True)
    for key in sorted_months:
        tools_by_month[key].sort(key=lambda t: t["created"], reverse=True)

    tool_count = sum(len(t) for t in tools_by_month.values())
    github_link = f'<a href="https://github.com/{github_repo}">Source</a>' if github_repo else ""

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>By month &mdash; {site_title}</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 0;
            color: #111827;
            background: #fff;
        }}
        nav.site-nav {{
            background: #111827;
            color: #f9fafb;
        }}
        nav.site-nav .nav-inner {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            max-width: 720px;
            margin: 0 auto;
            padding: 10px 2rem;
        }}
        nav.site-nav a {{
            color: #f9fafb;
            text-decoration: none;
            font-size: 0.875rem;
        }}
        nav.site-nav a:hover {{
            color: #d1d5db;
        }}
        nav.site-nav .site-name {{
            font-weight: 600;
            font-size: 1rem;
            letter-spacing: -0.01em;
        }}
        nav.site-nav .nav-links {{
            display: flex;
            gap: 1.5rem;
        }}
        section.body {{
            max-width: 720px;
            margin: 0 auto;
            padding: 1.5rem 2rem 3rem;
        }}
        h1 {{
            font-size: 1.5rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            margin-bottom: 0.25rem;
        }}
        h2 {{
            margin-top: 2rem;
            font-size: 1.125rem;
            font-weight: 600;
        }}
        a {{
            color: #2563eb;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        a.hashref {{
            color: #d1d5db;
            margin-right: 0.25rem;
        }}
        a.hashref:hover {{
            color: #9ca3af;
            text-decoration: none;
        }}
        .tool-list {{
            list-style: none;
            margin: 0;
            padding: 0;
        }}
        .tool-item {{
            margin-bottom: 0.75rem;
            padding-bottom: 0.75rem;
            border-bottom: 1px solid #f3f4f6;
        }}
        .tool-item:last-child {{
            border-bottom: none;
        }}
        .tool-name {{
            font-weight: 500;
        }}
        .tool-links {{
            font-size: 0.85rem;
            color: #9ca3af;
        }}
        .tool-summary {{
            margin-top: 0.15rem;
            color: #6b7280;
            font-size: 0.9rem;
        }}
        @media (max-width: 600px) {{
            section.body {{
                padding: 1rem;
            }}
            nav.site-nav .nav-inner {{
                padding: 10px 1rem;
            }}
        }}
    </style>
</head>
<body>
<nav class="site-nav">
    <div class="nav-inner">
        <a href="/" class="site-name">{site_title}</a>
        <div class="nav-links">
            <a href="/by-month">By month</a>
            <a href="/colophon">Colophon</a>
            {github_link}
        </div>
    </div>
</nav>
<section class="body">
    <h1>By month</h1>
    <p>{tool_count} tool{"s" if tool_count != 1 else ""}, grouped by creation month.</p>
"""

    for month_key in sorted_months:
        tools = tools_by_month[month_key]
        month_date = datetime.strptime(month_key, "%Y-%m")
        month_display = month_date.strftime("%B %Y")
        tool_word = "tool" if len(tools) == 1 else "tools"

        html_content += f'\n    <h2 id="{month_key}"><a class="hashref" href="#{month_key}">#</a>{month_display} ({len(tools)} {tool_word})</h2>\n'
        html_content += '    <ul class="tool-list">\n'

        for tool in tools:
            slug = tool["slug"]
            filename = tool["filename"]
            summary = tool["summary"]
            truncated = tool["truncated"]
            tool_url = f"/{slug}"
            colophon_url = f"/colophon#{filename}"

            html_content += f'        <li class="tool-item">\n'
            html_content += f'            <span class="tool-name"><a href="{tool_url}">{slug}</a></span>\n'
            html_content += f'            <span class="tool-links">(<a href="{colophon_url}">about</a>)</span>\n'
            if summary:
                if truncated:
                    html_content += f'            <div class="tool-summary">{summary} <a href="{colophon_url}">...</a></div>\n'
                else:
                    html_content += f'            <div class="tool-summary">{summary}</div>\n'
            html_content += '        </li>\n'

        html_content += '    </ul>\n'

    html_content += """</section>
</body>
</html>
"""

    OUTPUT_PATH.write_text(html_content, "utf-8")
    print(f"by-month.html created successfully ({tool_count} tools)")


if __name__ == "__main__":
    build_by_month()
