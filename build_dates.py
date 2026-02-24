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
