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
