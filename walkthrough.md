# Code Walkthrough: tools.stalhem.se

*2026-02-25T23:23:22Z by Showboat 0.6.1*
<!-- showboat-id: aadf5b0c-19f4-420d-b252-fba28cba514c -->

This is a linear walkthrough of the **tools.stalhem.se** codebase — a static site generator that hosts single-file, browser-based tools. The site is built by Carl Stålhem and deployed on GitHub Pages.

The architecture is elegant: each tool is a standalone HTML file with inline CSS and JavaScript. A Python-based build system mines Git history for metadata and generates index pages, a monthly archive, and a detailed colophon with full commit history. A small JavaScript footer is injected into every tool page at build time to provide navigation.

We will follow the data through the system from configuration to deployment:

1. **Site configuration** — `site.json`
2. **The tool template and an example tool** — `.templates/tool.html` and `word-count.html`
3. **Build orchestrator** — `build.sh`
4. **Metadata extraction from Git** — `gather_links.py`
5. **Date mapping** — `build_dates.py`
6. **Homepage generation** — `build_index.py`
7. **Monthly archive** — `build_by_month.py`
8. **Colophon (commit history docs)** — `build_colophon.py`
9. **Runtime footer** — `footer.js`
10. **CI/CD deployment** — `.github/workflows/deploy.yml`

## 1. Site Configuration — `site.json`

Everything starts with `site.json`, a small configuration file that defines the site's identity. It is read by `build_index.py` and `build_colophon.py` to generate page titles, navigation links, and GitHub URLs.

```bash
cat site.json
```

```output
{
  "title": "Tools",
  "description": "A collection of useful browser-based tools",
  "base_url": "",
  "github_repo": "cstalhem/tools",
  "author": "Carl Stålhem"
}
```

Five fields: `title` and `description` become the page `<title>` and meta description. `base_url` is left empty because the site lives at the domain root. `github_repo` is used to build links to source code and individual commits in the colophon. `author` appears in the HTML meta tags.

## 2. The Tool Template and an Example Tool

### The starter template — `.templates/tool.html`

New tools are created by copying this starter template. It establishes the design system: system fonts, a constrained `max-width: 640px` layout, and a consistent color palette. Let's look at the CSS variables and structural skeleton:

```bash
sed -n '1,15p' .templates/tool.html
```

```output
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tool Name</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
            line-height: 1.6;
            max-width: 640px;
            margin: 2rem auto;
            padding: 0 1.5rem;
            color: #111827;
```

The template sets the design tokens inline: `#111827` for primary text, system fonts for clean rendering, and a centered single-column layout. It also defines styles for focus states, error displays, and a responsive breakpoint at 600px.

```bash
sed -n '40,78p' .templates/tool.html
```

```output
        }
        textarea:focus, input:focus, select:focus {
            outline: none;
            border-color: #2563eb;
            box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
        }
        button {
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 6px;
            font-size: 0.9rem;
            font-family: inherit;
            cursor: pointer;
            background: #2563eb;
            color: #fff;
        }
        button:hover { background: #1d4ed8; }
        button:disabled { background: #d1d5db; cursor: not-allowed; }
        .output {
            display: none;
            margin-top: 1rem;
        }
        .output.visible { display: block; }
        .error {
            display: none;
            margin-top: 0.75rem;
            padding: 0.75rem;
            border-radius: 6px;
            font-size: 0.9rem;
            color: #991b1b;
            background: #fef2f2;
        }
        .error.visible { display: block; }
        @media (max-width: 600px) {
            body { padding: 0 1rem; margin: 1rem auto; }
            h1 { font-size: 1.1rem; }
        }
    </style>
</head>
```

The template's JavaScript skeleton provides error handling infrastructure and a placeholder for tool logic. The key pattern: a `try/catch` wrapper around an `update()` function that shows/hides an error banner:

```bash
sed -n '79,/^<\/html>/p' .templates/tool.html
```

```output
<body>
    <h1>Tool Name</h1>
    <p class="description">Brief description of what the tool does.</p>

    <!-- Input area — adjust to suit the tool -->
    <textarea id="input" placeholder="Paste or type here..." autofocus></textarea>

    <!-- Output area — hidden until there are results -->
    <div id="output" class="output"></div>

    <!-- Error display -->
    <div id="error" class="error"></div>

    <script>
        const input = document.getElementById('input');
        const output = document.getElementById('output');
        const error = document.getElementById('error');

        function showError(message) {
            error.textContent = message;
            error.classList.add('visible');
        }

        function hideError() {
            error.classList.remove('visible');
        }

        function update() {
            hideError();
            const text = input.value;
            if (!text.trim()) {
                output.classList.remove('visible');
                return;
            }
            // Process input and display results
            output.classList.add('visible');
        }

        input.addEventListener('input', update);
    </script>
</body>
</html>
```

### A real tool — `word-count.html`

Now let's see how an actual tool fills in this skeleton. The Word Count tool is a real-time word, character, and line counter:

```bash
cat word-count.html
```

```output
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Word Count</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
            line-height: 1.6;
            max-width: 640px;
            margin: 2rem auto;
            padding: 0 1.5rem;
            color: #111827;
        }
        h1 {
            font-size: 1.25rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
        }
        textarea {
            width: 100%;
            min-height: 200px;
            padding: 0.75rem;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            font-family: inherit;
            font-size: 0.95rem;
            resize: vertical;
            line-height: 1.6;
        }
        textarea:focus {
            outline: none;
            border-color: #2563eb;
            box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
        }
        .stats {
            display: flex;
            gap: 1.5rem;
            margin-top: 0.75rem;
            color: #6b7280;
            font-size: 0.9rem;
        }
        .stat-value {
            font-weight: 600;
            color: #111827;
        }
    </style>
</head>
<body>
    <h1>Word Count</h1>
    <textarea id="input" placeholder="Paste or type text here..." autofocus></textarea>
    <div class="stats">
        <div>Words: <span class="stat-value" id="words">0</span></div>
        <div>Characters: <span class="stat-value" id="chars">0</span></div>
        <div>Lines: <span class="stat-value" id="lines">0</span></div>
    </div>
    <script>
        const input = document.getElementById('input');
        const words = document.getElementById('words');
        const chars = document.getElementById('chars');
        const lines = document.getElementById('lines');

        function update() {
            const text = input.value;
            chars.textContent = text.length;
            words.textContent = text.trim() ? text.trim().split(/\s+/).length : 0;
            lines.textContent = text ? text.split('\n').length : 0;
        }

        input.addEventListener('input', update);
    </script>
</body>
</html>
```

The tool follows the template pattern exactly — same fonts, same layout, same focus styling. The `update()` function fires on every keystroke via `input.addEventListener('input', update)`. The counting logic is minimal: `split(/\s+/)` for words, `.length` for characters, and `split('\n')` for lines. No frameworks, no build step — just one file.

## 3. The Build Orchestrator — `build.sh`

Now we enter the build system. `build.sh` is the single entry point that orchestrates the entire site generation. It runs from the repository root and calls the Python scripts in the correct dependency order.

```bash
cat build.sh
```

```output
#!/bin/bash
set -e

# Ensure full git history is available for date extraction
if [ -f .git/shallow ]; then
    git fetch --unshallow
fi

echo "=== Building site ==="

echo "Gathering links and metadata..."
python3 gather_links.py

echo "Building colophon page..."
python3 build_colophon.py

echo "Building dates.json..."
python3 build_dates.py

echo "Building index page..."
python3 build_index.py

echo "Building by-month page..."
python3 build_by_month.py

echo "Injecting footer.js into HTML files..."
FOOTER_HASH=$(git log -1 --format="%H" -- footer.js 2>/dev/null || echo "dev")
FOOTER_SHORT_HASH=$(echo "$FOOTER_HASH" | cut -c1-8)

for file in *.html; do
    if [ -f "$file" ] && [ "$file" != "index.html" ] && [ "$file" != "colophon.html" ] && [ "$file" != "by-month.html" ]; then
        # Only inject if not already present
        if ! grep -q 'src="footer.js' "$file"; then
            awk -v script="<script type=\"module\" src=\"footer.js?${FOOTER_SHORT_HASH}\"></script>" '
                { lines[NR] = $0 }
                /<\/body>/ { last_body = NR }
                END {
                    for (i = 1; i <= NR; i++) {
                        if (i == last_body) {
                            sub(/<\/body>/, script "\n</body>", lines[i])
                        }
                        print lines[i]
                    }
                }
            ' "$file" > "$file.tmp" && mv "$file.tmp" "$file"
        fi
    fi
done

echo "=== Build complete! ==="
```

The script does three things:

**First**, it ensures full git history is available. GitHub Actions performs a shallow clone by default, but the build system needs every commit to generate accurate creation dates and change history. If `.git/shallow` exists, it fetches the full history.

**Second**, it runs the five Python build scripts in dependency order:
1. `gather_links.py` — must run first, produces `tools.json` and `gathered_links.json`
2. `build_colophon.py` — reads `gathered_links.json`
3. `build_dates.py` — reads `gathered_links.json`
4. `build_index.py` — reads `tools.json`
5. `build_by_month.py` — reads `gathered_links.json`

**Third**, it injects `footer.js` into every tool HTML file (skipping the generated pages: `index.html`, `colophon.html`, `by-month.html`). The injection uses `awk` to insert a `<script>` tag just before the last `</body>` tag in each file. The script URL includes a short git hash for cache busting (`footer.js?a1b2c3d4`). It also checks whether the script tag is already present, so the build is idempotent.

## 4. Metadata Extraction — `gather_links.py`

This is the foundation of the build system. It scans every `.html` file in the repository root, queries Git for its full commit history, and produces two JSON files that all other build scripts depend on.

Let's start with the imports and the core function that queries git:

```bash
sed -n '1,44p' gather_links.py
```

```output
#!/usr/bin/env python3
"""Scan HTML tool files and extract metadata from git history."""

import html
import json
import re
import subprocess
from pathlib import Path


def get_file_commit_details(file_path):
    """Get commit details for a file from git log."""
    try:
        result = subprocess.run(
            ["git", "log", "--format=%H|%aI|%B%x00", "--", file_path],
            capture_output=True,
            text=True,
            check=True,
        )

        commits = []
        for raw_commit in result.stdout.strip().split("\0"):
            if not raw_commit.strip():
                continue

            first_pipe = raw_commit.find("|")
            if first_pipe == -1:
                continue

            second_pipe = raw_commit.find("|", first_pipe + 1)
            if second_pipe == -1:
                continue

            commits.append({
                "hash": raw_commit[:first_pipe],
                "date": raw_commit[first_pipe + 1 : second_pipe],
                "message": raw_commit[second_pipe + 1 :],
            })

        return commits
    except subprocess.CalledProcessError as e:
        print(f"Error getting commit history for {file_path}: {e}")
        return []

```

`get_file_commit_details()` is the heart of the metadata system. It runs `git log` with a custom format that uses pipe delimiters (`|`) between the commit hash, ISO 8601 date, and full commit message body. The `%x00` at the end emits a null byte as a record separator — this is crucial because commit messages can contain newlines, so you can't split on newlines alone. The parser manually finds pipes by position rather than splitting (because the message body may itself contain pipes).

Next come the helper functions for extracting URLs, descriptions, and titles from files:

```bash
sed -n '47,77p' gather_links.py
```

```output
    """Extract URLs from text."""
    return re.findall(r"(https?://[^\s]+)", text)


def extract_description(docs_path):
    """Extract the first paragraph from a .docs.md file."""
    if not docs_path.exists():
        return ""

    try:
        content = docs_path.read_text("utf-8").strip()
    except OSError:
        return ""

    if "<!--" in content:
        content = content.split("<!--", 1)[0]

    lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            if lines:
                break
            continue
        lines.append(stripped)

    return " ".join(lines)


def extract_title(html_path):
    """Extract the <title> from an HTML file."""
```

```bash
sed -n '78,93p' gather_links.py
```

```output
    try:
        content = html_path.read_text("utf-8", errors="ignore")
    except OSError:
        return html_path.stem

    match = re.search(r"<title>(.*?)</title>", content, re.IGNORECASE | re.DOTALL)
    if match:
        return html.unescape(match.group(1).strip())

    return html_path.stem


def main():
    current_dir = Path.cwd()
    html_files = sorted(current_dir.glob("*.html"))

```

`extract_description()` reads companion `.docs.md` files (e.g., `word-count.docs.md`) and extracts the first paragraph, stripping HTML comments. This becomes the tool's description on the index page. `extract_title()` uses a regex to pull the `<title>` tag from each HTML file, with `html.unescape()` to handle any encoded characters. The filename stem is the fallback if no title is found.

Now let's see the `main()` function that ties it all together:

```bash
sed -n '90,140p' gather_links.py
```

```output
def main():
    current_dir = Path.cwd()
    html_files = sorted(current_dir.glob("*.html"))

    results = {"pages": {}}
    tools_summary = []

    for html_file in html_files:
        file_name = html_file.name
        print(f"Processing {file_name}...")

        commits = get_file_commit_details(html_file)
        if not commits:
            continue

        all_urls = []
        for commit in commits:
            for url in extract_urls(commit["message"]):
                if url not in all_urls:
                    all_urls.append(url)

        results["pages"][file_name] = {"commits": commits, "urls": all_urls}

        docs_path = html_file.with_suffix(".docs.md")
        description = extract_description(docs_path)

        slug = html_file.stem
        tools_summary.append({
            "filename": file_name,
            "slug": slug,
            "title": extract_title(html_file),
            "description": description,
            "created": commits[-1]["date"] if commits else None,
            "updated": commits[0]["date"] if commits else None,
            "url": f"/{slug}" if slug != "index" else "/",
        })

    with open("gathered_links.json", "w") as f:
        json.dump(results, f, indent=2)

    tools_summary.sort(key=lambda t: t["title"].lower())

    with open("tools.json", "w", encoding="utf-8") as f:
        json.dump(tools_summary, f, indent=2, ensure_ascii=False)

    print(f"Processed {len(html_files)} files")
    print(f"Found details for {len(results['pages'])} files")
    print(f"Generated metadata for {len(tools_summary)} tools in tools.json")


if __name__ == "__main__":
```

The `main()` function iterates every `.html` file in the repo root. For each file it:

1. **Queries git** for the full commit history
2. **Extracts URLs** from all commit messages (de-duplicated, order-preserved)
3. **Stores raw data** in `gathered_links.json` — a dictionary keyed by filename, each containing the full commit list and extracted URLs
4. **Builds a summary** for `tools.json` — with title, description, creation date (`commits[-1]`, the oldest), update date (`commits[0]`, the newest), and a URL slug

The creation date trick is clever: since `git log` returns commits in reverse chronological order, `commits[-1]` is always the first commit that introduced the file, and `commits[0]` is the most recent change. The tools summary is sorted alphabetically by title for stable ordering.

## 5. Date Mapping — `build_dates.py`

This is the simplest build script. It reads `gathered_links.json` and produces a flat mapping from filename to most-recent-update date (YYYY-MM-DD). This is consumed at runtime by `footer.js` to display "Updated 2025-01-15" in each tool's footer.

```bash
cat build_dates.py
```

```output
#!/usr/bin/env python3
"""Generate dates.json mapping HTML files to their most recent commit dates."""

import json


def build_dates():
    try:
        with open("gathered_links.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Error: gathered_links.json not found. Run gather_links.py first.")
        return

    pages = data.get("pages", {})
    dates = {}

    for page_name, page_data in pages.items():
        commits = page_data.get("commits", [])
        if commits:
            most_recent = max(
                commits, key=lambda c: c.get("date", "0000-00-00T00:00:00")
            )
            date_str = most_recent.get("date", "")
            if date_str:
                dates[page_name] = date_str[:10]

    with open("dates.json", "w") as f:
        json.dump(dates, f)

    print(f"Generated dates.json with {len(dates)} entries")


if __name__ == "__main__":
    build_dates()
```

It finds the most recent commit using `max()` with a key function on the ISO date string (lexicographic comparison works correctly for ISO 8601). The date is then truncated to just the first 10 characters (`YYYY-MM-DD`) with `date_str[:10]`. The output is a minimal JSON object like `{"word-count.html": "2025-01-15"}` — small enough to fetch quickly in the browser.

## 6. Homepage Generation — `build_index.py`

This is the largest and most complex build script. It generates `index.html` — the landing page of the site — by converting `README.md` to HTML and injecting two dynamic sections: recently added/updated tools, and a complete directory of all tools.

Let's look at it in sections, starting with the configuration and date utilities:

```bash
sed -n '1,45p' build_index.py
```

```output
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
```

The script gracefully handles the `markdown` dependency — it's the only third-party package in the project. The `_ordinal()` function converts numbers to English ordinals (1st, 2nd, 3rd, 4th...) with correct handling of the 11th-13th exception. `_parse_iso()` normalizes ISO 8601 dates, replacing the `Z` suffix with `+00:00` for Python's `fromisoformat()`.

Next, the tool loading and filtering logic:

```bash
sed -n '48,97p' build_index.py
```

```output
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
```

`_has_distinct_update()` checks whether a tool has been meaningfully updated after its creation — it compares the `updated` timestamp against `created`. This prevents a brand-new tool from appearing in both the "Recently added" and "Recently updated" lists.

`_select_recent()` is the core filtering function. It takes a list of tools, a date key (either `created` or `updated`), a result limit, and an optional exclusion set. It parses dates, sorts reverse-chronologically, and picks the top N results while excluding any slugs in the exclusion set. This is how the homepage avoids showing the same tool in both "Recently added" and "Recently updated".

Now let's see how the HTML sections are rendered:

```bash
sed -n '97,155p' build_index.py
```

```output
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
```

The rendering functions build HTML using f-strings. Each tool entry in the "Recently added/updated" lists includes the slug name as a link to the tool and the date as a link to the colophon (so you can click the date to see the tool's full history). The "All tools" section shows the full title with the description pulled from `.docs.md` files.

Let's see the main `build_index()` function that puts it all together and shows how the README.md markers are used:

```bash
sed -n '155,215p' build_index.py
```

```output
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
```

Here's the assembly logic:

1. **Convert README** — `README.md` is parsed to HTML using the `markdown` library with the "extra" extension
2. **Select recent tools** — gets the 5 most recently created and 5 most recently updated (excluding tools that just appeared in "recently added")
3. **Inject via comment markers** — the README contains HTML comment markers like `<!-- recently starts -->` and `<!-- recently stops -->`. The build script finds these markers in the converted HTML and replaces everything between them with the generated content. If markers are missing, it falls back to prepending/appending
4. **Wrap in full HTML** — the body HTML is wrapped in a complete HTML document with inline CSS, a dark navigation bar, and responsive grid layouts

The rest of the file (which we'll skip showing) is a large HTML template string with embedded CSS for the nav bar, recent-tools grid, tool listing, and responsive breakpoints. It writes the final result to `index.html`.

## 7. Monthly Archive — `build_by_month.py`

This script generates `by-month.html`, which groups all tools by their creation month. Let's look at the key parts — the summary extraction and the grouping logic:

```bash
sed -n '1,58p' build_by_month.py
```

```output
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
```

```bash
sed -n '58,100p' build_by_month.py
```

```output
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
```

```bash
sed -n '100,120p' build_by_month.py
```

```output
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
```

`_extract_summary()` reads a tool's `.docs.md` companion file, strips markdown headings and HTML comments, takes the first paragraph, and truncates to 30 words. The truncation flag is preserved so the template can add an ellipsis indicator.

The grouping logic is straightforward: for each tool page in `gathered_links.json`, find the oldest commit (`commits[-1]`), extract its month as a `YYYY-MM` key, and group tools into a `defaultdict(list)`. Months are sorted in reverse chronological order, and within each month, tools are sorted newest-first.

The HTML output uses `<details>` elements for each tool, showing the summary with a link to the full colophon entry. Each month heading gets an anchor ID (like `#2025-02`) for deep linking.

## 8. Colophon — `build_colophon.py`

The colophon is the most detailed generated page. For every tool, it shows documentation from the `.docs.md` file and a full, expandable commit history with linkified URLs and GitHub issue references. Let's look at the commit message formatting first:

```bash
sed -n '1,60p' build_colophon.py
```

```output
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

```

`format_commit_message()` is a three-step text processor:
1. **HTML-escape** the raw message to prevent XSS
2. **Linkify URLs** using a regex that finds `http://` or `https://` patterns
3. **Linkify GitHub issue references** — `#123` becomes a link to `github.com/cstalhem/tools/issues/123`
4. **Convert newlines** to `<br>` tags for display

The order matters: HTML-escaping must happen first so that angle brackets in commit messages don't become valid HTML, and the link-insertion regex operates on the already-escaped text.

Now let's see how the colophon page builds each tool entry:

```bash
sed -n '60,115p' build_colophon.py
```

```output

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
```

```bash
sed -n '150,220p' build_colophon.py
```

```output
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
```

```bash
sed -n '220,280p' build_colophon.py
```

```output
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
```

```bash
sed -n '280,330p' build_colophon.py
```

```output
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
```

The colophon builds each tool entry with:

- **A heading** with three links: a `#` anchor for deep linking, the tool slug linking to the live tool, and a "code" link to the GitHub source
- **Documentation** from the `.docs.md` file, rendered from markdown to HTML (with heading lines stripped to avoid duplicate headings)
- **An expandable commit history** inside a `<details>` element — commits are reversed to chronological order (`list(reversed(...))`) so the earliest commit appears first, reading like a natural development narrative
- **Each commit card** shows the 7-character short hash (linked to the GitHub commit page), a formatted date, and the message with linkified URLs and issue references

The JavaScript at the bottom auto-expands the `<details>` element when the URL hash matches a tool (e.g., visiting `/colophon#word-count.html` will scroll to and expand Word Count's commit history). This is what makes the colophon links from other pages work seamlessly.

## 9. Runtime Footer — `footer.js`

This is the only JavaScript that runs in the browser (as opposed to during the build). It's injected into every tool page by `build.sh` and provides consistent navigation back to the homepage and colophon. It's also the most algorithmically interesting file in the project.

```bash
cat footer.js
```

```output
// footer.js — Injected into every tool page to provide consistent navigation.

let pathname = window.location.pathname;
let filename = pathname.split('/').pop() || 'index.html';
if (!filename.endsWith('.html')) {
    filename += '.html';
}
const pageName = filename.replace('.html', '');

// Detect background luminance for text color
function parseColor(str) {
    const m = str.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
    return m ? { r: +m[1], g: +m[2], b: +m[3] } : null;
}

function getLuminance(r, g, b) {
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255;
}

function getEffectiveBg() {
    for (const el of [document.body, document.documentElement]) {
        const bg = window.getComputedStyle(el).backgroundColor;
        const c = parseColor(bg);
        if (c && (c.r + c.g + c.b) < 760) return c;
    }
    return { r: 255, g: 255, b: 255 };
}

const bg = getEffectiveBg();
const isDark = getLuminance(bg.r, bg.g, bg.b) < 0.5;
const textColor = isDark ? 'rgb(200, 200, 200)' : 'rgb(107, 114, 128)';
const hrColor = isDark ? 'rgba(255,255,255,0.15)' : '#e5e7eb';

// Handle flex/grid body layouts
const bodyDisplay = window.getComputedStyle(document.body).display;
if (bodyDisplay === 'flex' || bodyDisplay === 'grid') {
    const wrapper = document.createElement('div');
    const bs = window.getComputedStyle(document.body);
    wrapper.style.cssText = `
        display: ${bodyDisplay};
        flex: 1 1 auto;
        flex-direction: ${bs.flexDirection};
        align-items: ${bs.alignItems};
        justify-content: ${bs.justifyContent};
        width: 100%;
        min-height: inherit;
    `;
    while (document.body.firstChild) wrapper.appendChild(document.body.firstChild);
    document.body.style.display = 'flex';
    document.body.style.flexDirection = 'column';
    document.body.appendChild(wrapper);
}

const footer = document.createElement('footer');
footer.style.cssText = 'flex-shrink: 0; width: 100%; box-sizing: border-box;';
footer.innerHTML = `
    <hr style="margin: 2rem 0 0.75rem; border: none; border-top: 1px solid ${hrColor};">
    <nav style="font-family: system-ui, -apple-system, sans-serif; font-size: 12px; text-align: center; padding-bottom: 1rem;">
        <a href="/" style="color: ${textColor}; text-decoration: underline; margin-right: 1.5rem;">Home</a>
        <a href="/colophon#${filename}" style="color: ${textColor}; text-decoration: underline; margin-right: 1.5rem;">About ${pageName}</a>
        <a href="/colophon#${filename}" style="color: ${textColor}; text-decoration: underline;" id="footer-updated-link">Changes</a>
    </nav>
`;
document.body.appendChild(footer);

// Show last-updated date in footer
fetch('/dates.json')
    .then(r => r.json())
    .then(dates => {
        const date = dates[filename];
        if (date) {
            const link = document.getElementById('footer-updated-link');
            if (link) link.textContent = `Updated ${date}`;
        }
    })
    .catch(() => {});
```

This file packs a surprising amount of intelligence into a small script:

**URL Detection** — It extracts the current page filename from the URL path, handling both `/word-count` (no extension) and `/word-count.html` forms.

**Dark Mode Adaptation** — Rather than relying on CSS media queries, it computes the actual background luminance using the WCAG relative luminance formula: `(0.299*R + 0.587*G + 0.114*B) / 255`. The `getEffectiveBg()` function walks up from `body` to `documentElement` looking for a non-white background, falling back to white. If luminance is below 0.5, it switches to light-on-dark text colors. This works with any tool regardless of its color scheme.

**Flex/Grid Layout Preservation** — This is the cleverest part. If the tool's `<body>` uses `display: flex` or `display: grid`, simply appending a footer would break the layout. So the script creates a wrapper `<div>`, moves all existing body children into it (preserving the original flex/grid properties), then sets the body to a vertical flex column with the wrapper as the main content and the footer pinned at the bottom. This ensures the footer never interferes with the tool's layout.

**Runtime Date Fetching** — The footer fetches `/dates.json` asynchronously and updates the "Changes" link text to "Updated YYYY-MM-DD" once the data arrives. The `.catch(() => {})` silently handles any fetch errors (e.g., during local development).

## 10. CI/CD Pipeline — `.github/workflows/deploy.yml`

The final piece: GitHub Actions builds and deploys the site on every push to `main`.

```bash
cat .github/workflows/deploy.yml
```

```output
name: Build and deploy

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # full history needed for commit dates

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - run: pip install markdown

      - run: bash build.sh

      - uses: actions/upload-pages-artifact@v3
        with:
          path: .

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

The pipeline has two jobs:

**Build** — Checks out the repo with `fetch-depth: 0` (full history, critical for the git-based metadata extraction), sets up Python 3.12, installs the one dependency (`markdown`), and runs `build.sh`. The entire directory is uploaded as a GitHub Pages artifact.

**Deploy** — Depends on the build job completing successfully. Uses the `deploy-pages` action to publish to GitHub Pages. The `concurrency` block with `cancel-in-progress: false` ensures that overlapping pushes don't result in partial deployments — each deploy runs to completion.

The `CNAME` file in the repo root (containing `tools.stalhem.se`) tells GitHub Pages to serve the site at that custom domain.

```bash
cat CNAME
```

```output
tools.stalhem.se
```

## Summary

The data flows through the system in a clear pipeline:

```
Git History + HTML files
        │
        ▼
  gather_links.py ──▶ tools.json + gathered_links.json
        │
        ├──▶ build_dates.py ──▶ dates.json (consumed at runtime by footer.js)
        ├──▶ build_index.py ──▶ index.html (homepage)
        ├──▶ build_by_month.py ──▶ by-month.html (monthly archive)
        └──▶ build_colophon.py ──▶ colophon.html (detailed docs + commit history)
        │
        ▼
  build.sh injects footer.js into every tool .html
        │
        ▼
  GitHub Actions deploys to tools.stalhem.se
```

The key design decisions:

1. **Git as the database** — No separate CMS or database. Creation dates, update dates, and development history all come from `git log`. This means the site's metadata is always perfectly in sync with the actual code history.
2. **Single-file tools** — Each tool is a self-contained HTML file. No webpack, no React, no build step for the tools themselves. This keeps each tool independent and instantly deployable.
3. **Build-time generation** — All index pages, archives, and documentation are generated at build time as static HTML. The only runtime JavaScript is the lightweight `footer.js` that fetches a small JSON file for dates.
4. **Companion .docs.md files** — Tool descriptions live in separate markdown files rather than being embedded in the HTML. This keeps documentation concerns separate from implementation.
5. **Adaptive footer** — The luminance detection and flex/grid wrapper logic ensures the footer works correctly with any tool's visual design, regardless of color scheme or layout approach.
