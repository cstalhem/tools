#!/usr/bin/env python3
"""Generate colophon.html showing all tools with their full commit history."""

from __future__ import annotations

import html
import json
import re
from datetime import datetime
from pathlib import Path

import markdown

SITE_CONFIG_PATH = Path("site.json")


def _load_config() -> dict:
    if SITE_CONFIG_PATH.exists():
        with SITE_CONFIG_PATH.open("r", encoding="utf-8") as fp:
            return json.load(fp)
    return {"title": "Tools", "github_repo": "", "author": ""}


def format_commit_message(message, github_repo):
    """Format commit message with linkified URLs and issue references."""
    escaped = html.escape(message)
    escaped = re.sub(r"(https?://[^\s]+)", r'<a href="\1">\1</a>', escaped)
    if github_repo:
        escaped = re.sub(
            r"#(\d+)",
            rf'<a href="https://github.com/{github_repo}/issues/\1">#\1</a>',
            escaped,
        )
    return escaped.replace("\n", "<br>")


def build_colophon():
    config = _load_config()
    site_title = config.get("title", "Tools")
    github_repo = config.get("github_repo", "")

    try:
        with open("gathered_links.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Error: gathered_links.json not found. Run gather_links.py first.")
        return

    pages = data.get("pages", {})
    if not pages:
        print("No pages found in gathered_links.json")
        return

    def get_most_recent_date(page_data):
        commits = page_data.get("commits", [])
        if not commits:
            return "0000-00-00T00:00:00"
        dates = [c.get("date", "0000-00-00T00:00:00") for c in commits]
        return max(dates) if dates else "0000-00-00T00:00:00"

    sorted_pages = sorted(
        pages.items(), key=lambda x: get_most_recent_date(x[1]), reverse=True
    )

    tool_count = len(sorted_pages)
    github_link = f'<a href="https://github.com/{github_repo}">Source</a>' if github_repo else ""

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Colophon &mdash; {site_title}</title>
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
        a {{
            color: #2563eb;
            text-decoration: none;
            overflow-wrap: break-word;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        .tool {{
            margin-bottom: 2rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid #e5e7eb;
        }}
        .heading {{
            display: flex;
            align-items: baseline;
            gap: 0.5rem;
            margin: 0;
            font-size: 1.125rem;
        }}
        .hash-text a {{
            color: #d1d5db;
            font-weight: 400;
        }}
        .hash-text a:hover {{
            color: #9ca3af;
            text-decoration: none;
        }}
        .code-text {{
            font-size: 0.8rem;
        }}
        .code-text a {{
            color: #9ca3af;
        }}
        .docs {{
            margin-top: 0.5rem;
            color: #374151;
            font-size: 0.95rem;
        }}
        details {{
            margin-top: 0.75rem;
        }}
        summary {{
            cursor: pointer;
            padding: 0.25rem 0;
            color: #6b7280;
            font-size: 0.85rem;
            font-weight: 500;
        }}
        summary:hover {{
            color: #2563eb;
        }}
        .commit {{
            background: #f9fafb;
            padding: 0.75rem 1rem;
            margin: 0.5rem 0;
            border-radius: 6px;
            border-left: 3px solid #e5e7eb;
            font-size: 0.9rem;
        }}
        .commit-hash {{
            font-family: "SF Mono", "Fira Code", monospace;
            color: #9ca3af;
            font-size: 0.8rem;
        }}
        .commit-date {{
            color: #9ca3af;
            font-size: 0.8rem;
            margin-left: 0.5rem;
        }}
        .commit-message {{
            margin-top: 0.25rem;
            color: #374151;
        }}
        blockquote {{
            margin: 0.75rem 0;
            border-left: 3px solid #e5e7eb;
            padding-left: 0.75rem;
            color: #6b7280;
        }}
        @media (max-width: 600px) {{
            section.body {{
                padding: 1rem;
            }}
            nav.site-nav .nav-inner {{
                padding: 10px 1rem;
            }}
            .commit {{
                padding: 0.5rem 0.75rem;
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
    <h1>Colophon</h1>
    <p>{tool_count} tool{"s" if tool_count != 1 else ""} and their development history.</p>
"""

    for page_name, page_data in sorted_pages:
        slug = page_name.replace(".html", "")
        tool_url = f"/{slug}"
        github_url = f"https://github.com/{github_repo}/blob/main/{page_name}" if github_repo else "#"
        commits = list(reversed(page_data.get("commits", [])))
        commit_count = len(commits)

        html_content += f"""
    <div class="tool" id="{page_name}">
        <h2 class="heading">
            <span class="hash-text"><a href="#{page_name}">#</a></span>
            <a href="{tool_url}">{slug}</a>
            <span class="code-text"><a href="{github_url}">code</a></span>
        </h2>
"""
        docs_file = page_name.replace(".html", ".docs.md")
        if Path(docs_file).exists():
            try:
                with open(docs_file, "r") as f:
                    docs_content = f.read()
                docs_lines = [
                    line for line in docs_content.splitlines()
                    if not line.lstrip().startswith("#")
                ]
                docs_content = "\n".join(docs_lines)
                docs_html = markdown.markdown(docs_content)
                html_content += f'        <div class="docs">{docs_html}</div>\n'
            except Exception as e:
                print(f"Error reading {docs_file}: {e}")

        html_content += f"""
        <details>
            <summary>{commit_count} commit{"s" if commit_count != 1 else ""}</summary>
"""
        for commit in commits:
            commit_hash = commit.get("hash", "")
            short_hash = commit_hash[:7] if commit_hash else "unknown"
            commit_date = commit.get("date", "")

            formatted_date = ""
            if commit_date:
                try:
                    dt = datetime.fromisoformat(commit_date)
                    formatted_date = dt.strftime("%B %d, %Y %H:%M")
                except ValueError:
                    formatted_date = commit_date

            commit_message = commit.get("message", "")
            formatted_message = format_commit_message(commit_message, github_repo)
            commit_url = f"https://github.com/{github_repo}/commit/{commit_hash}" if github_repo else "#"

            html_content += f"""
            <div class="commit" id="commit-{short_hash}">
                <div>
                    <a href="{commit_url}" class="commit-hash">{short_hash}</a>
                    <span class="commit-date">{formatted_date}</span>
                </div>
                <div class="commit-message">{formatted_message}</div>
            </div>
"""
        html_content += """
        </details>
    </div>
"""

    html_content += """
    <script>
    document.addEventListener('DOMContentLoaded', () => {
        const hash = window.location.hash.slice(1);
        if (hash) {
            const el = document.getElementById(hash);
            if (el) {
                const details = el.querySelector('details');
                if (details) details.open = true;
            }
        }
    });
    </script>
</section>
</body>
</html>
"""

    with open("colophon.html", "w") as f:
        f.write(html_content)
    print("colophon.html built successfully")


if __name__ == "__main__":
    build_colophon()
