#!/usr/bin/env python3
"""Generate index.html from README.md with recent additions/updates and all tools listing."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Sequence

try:
    import markdown
except ModuleNotFoundError as exc:
    raise SystemExit(
        "The 'markdown' package is required. Install with: pip install markdown"
    ) from exc

README_PATH = Path("README.md")
TOOLS_JSON_PATH = Path("tools.json")
SITE_CONFIG_PATH = Path("site.json")
OUTPUT_PATH = Path("index.html")


def _load_config() -> dict:
    if SITE_CONFIG_PATH.exists():
        with SITE_CONFIG_PATH.open("r", encoding="utf-8") as fp:
            return json.load(fp)
    return {"title": "Tools", "github_repo": "", "author": ""}


def _ordinal(value: int) -> str:
    if 10 <= value % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _has_distinct_update(tool: dict) -> bool:
    updated = _parse_iso(tool.get("updated"))
    if updated is None:
        return False
    created = _parse_iso(tool.get("created"))
    if created is None:
        return True
    return updated > created


def _format_date(dt: datetime) -> str:
    return f"{_ordinal(dt.day)} {dt.strftime('%B %Y')}"


def _load_tools() -> List[dict]:
    if not TOOLS_JSON_PATH.exists():
        return []
    with TOOLS_JSON_PATH.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def _select_recent(tools, *, key, limit, exclude_slugs=None):
    excluded = set(exclude_slugs or [])
    dated = [
        (t, _parse_iso(t.get(key)))
        for t in tools
        if t.get(key)
    ]
    dated = [(t, d) for t, d in dated if d is not None]
    dated.sort(key=lambda x: x[1], reverse=True)

    selected = []
    for tool, parsed in dated:
        if tool.get("slug") in excluded:
            continue
        entry = tool.copy()
        entry["parsed_date"] = parsed
        selected.append(entry)
        if len(selected) >= limit:
            break
    return selected


def _render_recent_section(recently_added, recently_updated):
    def render_list(tools):
        if not tools:
            return "<li>Nothing yet.</li>"
        items = []
        for tool in tools:
            slug = tool.get("slug", "")
            url = tool.get("url", "#")
            filename = tool.get("filename", "")
            parsed = tool.get("parsed_date")
            date_str = _format_date(parsed) if isinstance(parsed, datetime) else ""
            colophon_url = f"/colophon#{filename}" if filename else "#"
            date_html = (
                f'<span class="recent-date"> &mdash; <a href="{colophon_url}">{date_str}</a></span>'
                if date_str else ""
            )
            items.append(f'<li><a href="{url}">{slug}</a>{date_html}</li>')
        return "\n".join(items)

    return f"""
<div class="recent-container">
  <div class="recent-column">
    <h2>Recently added</h2>
    <ul class="recent-list">
      {render_list(recently_added)}
    </ul>
    <p class="browse-all"><a href="/by-month">Browse all by month</a></p>
  </div>
  <div class="recent-column">
    <h2>Recently updated</h2>
    <ul class="recent-list">
      {render_list(recently_updated)}
    </ul>
  </div>
</div>
"""


def _render_all_tools_section(tools):
    if not tools:
        return ""

    items = []
    for tool in tools:
        slug = tool.get("slug", "")
        url = tool.get("url", "#")
        title = tool.get("title", slug)
        desc = tool.get("description", "")
        desc_html = f'<span class="tool-desc"> &mdash; {desc}</span>' if desc else ""
        items.append(f'<li><a href="{url}">{title}</a>{desc_html}</li>')

    return f"""
<div class="all-tools">
  <h2>All tools</h2>
  <ul class="tools-list">
    {"".join(items)}
  </ul>
</div>
"""


def build_index():
    config = _load_config()
    site_title = config.get("title", "Tools")
    github_repo = config.get("github_repo", "")

    if not README_PATH.exists():
        raise FileNotFoundError("README.md not found")

    md_content = README_PATH.read_text("utf-8")
    md = markdown.Markdown(extensions=["extra"])
    body_html = md.convert(md_content)

    tools = _load_tools()
    recently_added = _select_recent(tools, key="created", limit=5)
    added_slugs = [t.get("slug") for t in recently_added]
    tools_with_updates = [t for t in tools if _has_distinct_update(t)]
    recently_updated = _select_recent(
        tools_with_updates, key="updated", limit=5, exclude_slugs=added_slugs
    )

    recent_html = _render_recent_section(recently_added, recently_updated)
    all_tools_html = _render_all_tools_section(tools)

    # Inject recent section between comment markers
    start_marker = "<!-- recently starts -->"
    end_marker = "<!-- recently stops -->"
    if start_marker in body_html and end_marker in body_html:
        si = body_html.find(start_marker)
        ei = body_html.find(end_marker)
        if si < ei:
            body_html = (
                body_html[: si + len(start_marker)]
                + "\n" + recent_html
                + body_html[ei:]
            )
    else:
        body_html = recent_html + body_html

    # Inject all-tools section between comment markers
    at_start = "<!-- all-tools starts -->"
    at_end = "<!-- all-tools stops -->"
    if at_start in body_html and at_end in body_html:
        si = body_html.find(at_start)
        ei = body_html.find(at_end)
        if si < ei:
            body_html = (
                body_html[: si + len(at_start)]
                + "\n" + all_tools_html
                + body_html[ei:]
            )
    else:
        body_html += all_tools_html

    github_link = f'<a href="https://github.com/{github_repo}">Source</a>' if github_repo else ""
    nav_right = github_link

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{site_title}</title>
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
            padding: 0;
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
            margin: 0 0 0.5rem;
            letter-spacing: -0.02em;
        }}
        h2 {{
            font-size: 1.125rem;
            font-weight: 600;
            margin-top: 2rem;
            margin-bottom: 0.5rem;
            letter-spacing: -0.01em;
        }}
        a {{
            color: #2563eb;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        .recent-container {{
            display: flex;
            gap: 2rem;
            flex-wrap: wrap;
            margin-bottom: 2rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid #e5e7eb;
        }}
        .recent-column {{
            flex: 1 1 280px;
        }}
        .recent-column h2 {{
            margin-top: 0;
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #6b7280;
        }}
        .recent-list {{
            list-style: none;
            margin: 0;
            padding: 0;
        }}
        .recent-list li {{
            margin-bottom: 0.4rem;
            font-size: 0.95rem;
        }}
        .recent-date {{
            color: #9ca3af;
            font-size: 0.8rem;
        }}
        .recent-date a {{
            color: #9ca3af;
        }}
        .recent-date a:hover {{
            color: #6b7280;
        }}
        .browse-all {{
            margin-top: 0.75rem;
            padding-top: 0.5rem;
            border-top: 1px solid #f3f4f6;
            font-size: 0.85rem;
        }}
        .all-tools {{
            margin-top: 2rem;
        }}
        .all-tools h2 {{
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #6b7280;
        }}
        .tools-list {{
            list-style: none;
            margin: 0;
            padding: 0;
        }}
        .tools-list li {{
            margin-bottom: 0.4rem;
            font-size: 0.95rem;
        }}
        .tool-desc {{
            color: #6b7280;
            font-size: 0.85rem;
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
            {nav_right}
        </div>
    </div>
</nav>
<section class="body">
{body_html}
</section>
</body>
</html>
"""

    OUTPUT_PATH.write_text(full_html, "utf-8")
    print("index.html created successfully")


if __name__ == "__main__":
    build_index()
