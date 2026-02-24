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


def extract_urls(text):
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
    main()
