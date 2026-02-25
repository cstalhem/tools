# SVG Icon Converter — Code Walkthrough

*2026-02-25T23:44:11Z by Showboat 0.6.1*
<!-- showboat-id: be18c4e9-48ff-484f-9b73-e0192dc5ba1b -->

## Overview

`svg-converter.html` is a self-contained, single-file tool — no build step, no server, no dependencies. Drop it in a browser and it works. The tool accepts an SVG via URL fetch or file upload, strips away everything except raw geometry (paths, circles, rects, etc.), rescales the coordinate system to a 24×24 viewBox, sets `fill="currentColor"`, and outputs a clean icon-ready SVG. A side-by-side comparison lets you verify the original against the converted result before copying or downloading.

The file is divided into three layers that correspond to the three sections of an HTML document:

| Layer | Section | Responsibility |
|---|---|---|
| Structure | `<body>` HTML | Declares inputs, previews, output area |
| Presentation | `<style>` CSS | Controls layout and visibility |
| Behaviour | `<script>` JS | All logic: parsing, converting, rendering |

## 1. HTML Structure

The page body contains four top-level blocks. Here they are in document order:

```bash
sed -n '168,203p' svg-converter.html
```

```output
<body>
    <h1>SVG Icon Converter</h1>
    <p class="description">Convert any SVG into a clean, monochrome 24&times;24 icon with <code>fill="currentColor"</code>.</p>

    <label for="url-input" style="font-size:0.9rem;font-weight:500;">Paste an SVG URL</label>
    <div style="display:flex;gap:0.5rem;margin-top:0.35rem;">
        <input type="url" id="url-input" placeholder="https://example.com/icon.svg">
        <button id="fetch-btn">Fetch</button>
    </div>

    <div class="separator">or</div>

    <div class="drop-zone" id="drop-zone">
        <div>Drop an SVG file here or <strong>click to browse</strong></div>
        <input type="file" id="file-input" accept=".svg,image/svg+xml">
    </div>

    <div id="output" class="output">
        <div class="preview-row">
            <div class="preview-item">
                <div class="preview-box" id="preview-original"></div>
                <div class="preview-label">Original</div>
            </div>
            <div class="preview-item">
                <div class="preview-box" id="preview-converted"></div>
                <div class="preview-label">Converted</div>
            </div>
        </div>
        <textarea class="code-block" id="code-output" readonly></textarea>
        <div class="btn-row">
            <button id="download-btn">Download SVG</button>
            <button id="copy-btn" class="btn-secondary">Copy code</button>
        </div>
    </div>

    <div id="error" class="error"></div>
```

The four top-level blocks are:

1. **URL input row** — an `<input type="url">` paired with a Fetch button, wrapped in a flex container.
2. **Drop zone** — a `<div class="drop-zone">` that acts as both the visible drag target and the click trigger. The real `<input type="file">` is hidden inside it (`display:none`).
3. **Output panel** (`#output`) — hidden by default, revealed by adding the class `visible`. Contains the two preview boxes side by side, then the code `<textarea>`, then the action buttons.
4. **Error bar** (`#error`) — also hidden by default, shown via the `visible` class when something goes wrong.

The visibility trick — toggling a `visible` class instead of setting `display` inline — keeps all show/hide logic in CSS and makes it easy to animate or restyle later.

## 2. CSS — Layout and Visibility

The stylesheet has two distinct jobs: layout and state. The layout classes establish the visual structure; the state classes control what is shown.

**State classes — the visibility pattern:**

```bash
sed -n '95,99p' svg-converter.html
```

```output
        .output {
            display: none;
            margin-top: 1.25rem;
        }
        .output.visible { display: block; }
```

The same pattern applies to . Both elements start hidden () and are revealed by JavaScript adding the  class. This means CSS owns the definition of what 'visible' means — JavaScript only toggles a semantic class name.

The same pattern applies to `.error.visible`. Both elements start hidden (`display:none`) and are revealed by JavaScript adding the `visible` class. This means CSS owns the definition of what "visible" means — JavaScript only toggles a semantic class name.

**Preview layout — side-by-side comparison:**

```bash
sed -n '100,131p' svg-converter.html
```

```output
        .preview-row {
            display: flex;
            gap: 2rem;
            justify-content: center;
            margin-bottom: 1.25rem;
        }
        .preview-item {
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .preview-box {
            width: 120px;
            height: 120px;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #fff;
            overflow: hidden;
        }
        .preview-box svg {
            width: 80px;
            height: 80px;
        }
        .preview-label {
            font-size: 0.8rem;
            color: #6b7280;
            text-align: center;
            margin-top: 0.35rem;
        }
```

`.preview-row` is a flex container centred horizontally. Each `.preview-item` is itself a column-flex that stacks the box above its label. The `.preview-box` is a fixed 120×120 container; any SVG injected into it is constrained to 80×80 by the `.preview-box svg` rule (or via inline style for the original). `overflow: hidden` clips any SVG that ignores those dimensions.

## 3. JavaScript — DOM References and State

The script opens by grabbing every interactive element by ID and declaring the single piece of mutable state:

```bash
sed -n '205,218p' svg-converter.html
```

```output
    <script type="module">
        const urlInput = document.getElementById('url-input');
        const fetchBtn = document.getElementById('fetch-btn');
        const dropZone = document.getElementById('drop-zone');
        const fileInput = document.getElementById('file-input');
        const output = document.getElementById('output');
        const previewOriginal = document.getElementById('preview-original');
        const previewConverted = document.getElementById('preview-converted');
        const codeOutput = document.getElementById('code-output');
        const downloadBtn = document.getElementById('download-btn');
        const copyBtn = document.getElementById('copy-btn');
        const errorEl = document.getElementById('error');

        let convertedSvg = '';
```

`type="module"` gives the script its own scope (no global leaks) and allows top-level `await`. All DOM lookups happen once at startup and are stored in `const`s — no repeated `getElementById` calls inside event handlers.

`convertedSvg` is the only piece of shared mutable state. It holds the most recently produced SVG string so the download and copy handlers can reference it without re-running the conversion.

## 4. Error Handling — showError / hideError

```bash
sed -n '220,228p' svg-converter.html
```

```output
        function showError(msg) {
            errorEl.textContent = msg;
            errorEl.classList.add('visible');
            output.classList.remove('visible');
        }

        function hideError() {
            errorEl.classList.remove('visible');
        }
```

`showError` does three things atomically: sets the message text, reveals the error bar, and hides the output panel. This prevents a state where both are visible at once. `hideError` is called at the top of `convertSvg` so a new attempt always starts with a clean slate.

## 5. convertSvg — Parse and Validate

This is the core function. It receives the raw SVG string and returns a clean SVG string, or throws if anything is wrong.

```bash
sed -n '232,248p' svg-converter.html
```

```output
        function convertSvg(raw) {
            hideError();
            const parser = new DOMParser();
            const doc = parser.parseFromString(raw, 'image/svg+xml');
            const parseError = doc.querySelector('parsererror');
            if (parseError) throw new Error('Invalid SVG: could not parse the file.');

            const srcSvg = doc.documentElement;
            if (srcSvg.tagName !== 'svg') throw new Error('Invalid SVG: root element is not <svg>.');

            // Determine the source viewBox so we can remap coordinates
            const srcViewBox = resolveViewBox(srcSvg);

            // Collect every visible shape, flattening groups
            const paths = [];
            collectPaths(srcSvg, paths);
            if (paths.length === 0) throw new Error('No drawable paths found in SVG.');
```

`DOMParser` with `image/svg+xml` parses the string into a real DOM tree. A `<parsererror>` element in the result is the browser's signal that XML parsing failed — querying for it is the standard way to detect parse errors in SVG/XML.

After parsing, two things are validated before any work is done:
- The root element must be `<svg>` (not just any XML).
- At least one drawable shape must exist — failing early with a clear message beats producing an empty output file.

`resolveViewBox` and `collectPaths` are called here to gather the inputs for the rebuild phase.

## 6. resolveViewBox — Coordinate Space Detection

```bash
sed -n '293,305p' svg-converter.html
```

```output
        function resolveViewBox(svg) {
            const vb = svg.getAttribute('viewBox');
            if (vb) {
                const parts = vb.trim().split(/[\s,]+/).map(Number);
                if (parts.length === 4 && parts.every(n => isFinite(n))) {
                    return { x: parts[0], y: parts[1], w: parts[2], h: parts[3] };
                }
            }
            // Fall back to width/height attributes
            const w = parseFloat(svg.getAttribute('width')) || 24;
            const h = parseFloat(svg.getAttribute('height')) || 24;
            return { x: 0, y: 0, w, h };
        }
```

The `viewBox` attribute is the canonical way to declare an SVG's internal coordinate space. It is a string like `"0 0 512 512"` (or comma-separated). The regex `/[\s,]+/` splits on any mix of spaces and commas, which covers all valid SVG viewBox formats.

If no `viewBox` exists, the function falls back to the `width` and `height` attributes (e.g. `width="512" height="512"`) and assumes the origin is at 0,0. If those are missing too, it defaults to 24×24 — meaning the source is already icon-sized and no scaling is needed.

The returned object `{ x, y, w, h }` is used by `convertSvg` to compute the rescaling transform.

## 7. KEEP_ATTRS and SHAPE_TAGS — The Allowlist

These two constants define exactly which element types and attributes survive the conversion.

```bash
sed -n '307,318p' svg-converter.html
```

```output
        // Geometry attributes we want to keep per element type
        const KEEP_ATTRS = {
            path: ['d', 'fill-rule', 'clip-rule'],
            circle: ['cx', 'cy', 'r'],
            ellipse: ['cx', 'cy', 'rx', 'ry'],
            rect: ['x', 'y', 'width', 'height', 'rx', 'ry'],
            line: ['x1', 'y1', 'x2', 'y2'],
            polyline: ['points'],
            polygon: ['points'],
        };

        const SHAPE_TAGS = new Set(Object.keys(KEEP_ATTRS));
```

`KEEP_ATTRS` is a whitelist that covers every drawable SVG primitive. For each element type it lists only the geometry attributes — position, size, shape data. Everything else (fill colours, stroke widths, opacity, class names, IDs, event handlers, filters, gradients) is silently dropped. This is what makes the output "clean".

`fill-rule` and `clip-rule` are kept on `path` because they directly affect which pixels are filled (e.g. the even-odd rule for donut shapes). No colour attributes are kept — colour comes from `fill="currentColor"` on the root `<svg>`, letting the icon inherit whatever colour the surrounding CSS sets.

`SHAPE_TAGS` is derived automatically from `KEEP_ATTRS`'s keys via a `Set`, so it always stays in sync — no risk of the tag list and attribute list diverging.

## 8. collectPaths — Recursive Tree Walk

This function traverses the SVG DOM tree and collects every drawable shape into a flat list.

```bash
sed -n '320,358p' svg-converter.html
```

```output
        function collectPaths(node, out, parentTransform) {
            for (const child of node.children) {
                const tag = child.tagName.toLowerCase();

                // Skip non-visual / style elements
                if (['style', 'defs', 'clippath', 'mask', 'metadata', 'title', 'desc', 'symbol'].includes(tag)) continue;

                // Accumulate transforms from groups
                let transform = parentTransform || '';
                const t = child.getAttribute('transform');
                if (t) transform = transform ? `${transform} ${t}` : t;

                if (tag === 'g' || tag === 'a' || tag === 'svg') {
                    collectPaths(child, out, transform);
                    continue;
                }

                if (tag === 'use') {
                    const refId = (child.getAttribute('href') || child.getAttributeNS('http://www.w3.org/1999/xlink', 'href') || '').replace('#', '');
                    if (refId) {
                        const target = child.ownerDocument.getElementById(refId);
                        if (target) collectPaths(target, out, transform);
                    }
                    continue;
                }

                if (!SHAPE_TAGS.has(tag)) continue;

                const attrs = {};
                const allowed = KEEP_ATTRS[tag] || [];
                for (const a of allowed) {
                    const v = child.getAttribute(a);
                    if (v != null) attrs[a] = v;
                }
                if (transform) attrs.transform = transform;

                out.push({ tag, attrs });
            }
        }
```

The function walks `node.children` (element children only, no text nodes) and handles four categories:

**Skip** — `style`, `defs`, `clipPath`, `mask`, `metadata`, `title`, `desc`, `symbol` are non-visual containers or metadata. Skipping them means referenced symbols and clip paths are ignored; the tool is intentionally lossy for complex SVGs.

**Recurse** — `<g>`, `<a>`, and nested `<svg>` are transparent containers. The function recurses into them, threading the accumulated `transform` string downward. Each group's transform is concatenated to the parent's so nested transforms compose correctly: `"translate(10,10) scale(2,2)"`.

**Use** — `<use>` is SVG's symbol-reference element. It points to another element via `href` (or the older XLink `xlink:href`). The function resolves the reference with `getElementById` and recurses into the target, effectively inlining the referenced shape.

**Shape** — If the tag is in `SHAPE_TAGS`, only the geometry attributes from `KEEP_ATTRS` are copied. The accumulated transform string (if any) is written as the shape's own `transform` attribute so it carries through to the rebuilt SVG.

The result `out` is a flat array of `{ tag, attrs }` objects — a normalized, hierarchy-free representation of all the geometry.

## 9. Building the Clean SVG — Rescaling and Assembly

```bash
sed -n '250,282p' svg-converter.html
```

```output
            // Build the clean SVG
            const ns = 'http://www.w3.org/2000/svg';
            const svg = document.createElementNS(ns, 'svg');
            svg.setAttribute('xmlns', ns);
            svg.setAttribute('viewBox', '0 0 24 24');
            svg.setAttribute('fill', 'currentColor');

            // If source viewBox is already 0 0 24 24, just copy paths.
            // Otherwise wrap in a <g> with a transform to rescale.
            const needsTransform = !(
                srcViewBox.x === 0 && srcViewBox.y === 0 &&
                srcViewBox.w === 24 && srcViewBox.h === 24
            );

            let container = svg;
            if (needsTransform) {
                const g = document.createElementNS(ns, 'g');
                const sx = 24 / srcViewBox.w;
                const sy = 24 / srcViewBox.h;
                const tx = -srcViewBox.x;
                const ty = -srcViewBox.y;
                g.setAttribute('transform', `translate(${fmt(tx * sx)},${fmt(ty * sy)}) scale(${fmt(sx)},${fmt(sy)})`);
                svg.appendChild(g);
                container = g;
            }

            for (const p of paths) {
                const el = document.createElementNS(ns, p.tag);
                for (const [k, v] of Object.entries(p.attrs)) {
                    el.setAttribute(k, v);
                }
                container.appendChild(el);
            }
```

A new `<svg>` element is created via the DOM API (not string concatenation) to guarantee well-formed XML output. Three attributes are set unconditionally:
- `xmlns` — required for the SVG to be valid as a standalone file.
- `viewBox="0 0 24 24"` — the target coordinate space.
- `fill="currentColor"` — the whole point of the conversion; the icon inherits its colour from CSS.

**Conditional rescaling:** If the source viewBox is already `0 0 24 24` the shapes can be copied directly. Otherwise a `<g>` wrapper is inserted with a compound transform:

```
translate(tx*sx, ty*sy) scale(sx, sy)
```

Where `sx = 24/w` and `sy = 24/h` scale the coordinates down (or up) to 24 units, and the translate corrects for a non-zero origin (e.g. a viewBox starting at `"100 100 512 512"`). The translate is applied *after* scaling in SVG transform order (transforms compose right-to-left in SVG), so `tx` and `ty` are the raw offsets from `resolveViewBox`, multiplied by the scale factor.

Finally the flat `paths` array is iterated and each shape is appended to `container` (either the root `<svg>` or the `<g>`).

## 10. Serialization and Namespace Cleanup

```bash
sed -n '284,291p' svg-converter.html
```

```output
            // Serialize
            const serializer = new XMLSerializer();
            let code = serializer.serializeToString(svg);
            // Tidy up namespace noise the serializer may add to children
            code = code.replace(/ xmlns="[^"]*"/g, (m, offset) => offset === code.indexOf(m) ? m : '');

            return code;
        }
```

`XMLSerializer.serializeToString` turns the DOM tree back into a string. However browsers often re-declare the SVG namespace (`xmlns="http://www.w3.org/2000/svg"`) on child elements that were created with `createElementNS` — producing noisy output like `<path xmlns="http://www.w3.org/2000/svg" d="..."/>`.

The regex `/ xmlns="[^"]*"/g` finds every `xmlns="..."` attribute. The callback keeps only the *first* occurrence (the one on the root `<svg>`) by checking `offset === code.indexOf(m)` — i.e. is this match at the position of the first match in the string? All subsequent ones are replaced with an empty string.

## 11. fmt — Floating Point Tidying

```bash
sed -n '360,362p' svg-converter.html
```

```output
        function fmt(n) {
            return +n.toFixed(6);
        }
```

`toFixed(6)` caps the decimal places to avoid transform strings like `translate(0.000000476837158,0)` from floating point arithmetic. The unary `+` converts the string that `toFixed` returns back to a number, which removes trailing zeros: `+("0.500000")` → `0.5`.

## 12. process — Orchestrating Input to Output

 is the glue between all input paths (file upload, URL fetch) and the conversion + rendering pipeline.

## 12. process — Orchestrating Input to Output

`process` is the glue between all input paths (file upload, URL fetch) and the conversion + rendering pipeline.

```bash
sed -n '366,387p' svg-converter.html
```

```output
        function process(raw) {
            try {
                convertedSvg = convertSvg(raw);
                codeOutput.value = convertedSvg;

                // Show original SVG scaled to fit the preview box
                const parser = new DOMParser();
                const origDoc = parser.parseFromString(raw, 'image/svg+xml');
                const origSvg = origDoc.documentElement;
                if (origSvg.tagName === 'svg') {
                    previewOriginal.innerHTML = new XMLSerializer().serializeToString(origSvg);
                    const el = previewOriginal.querySelector('svg');
                    if (el) { el.style.width = '80px'; el.style.height = '80px'; }
                }

                previewConverted.innerHTML = convertedSvg;
                output.classList.add('visible');
                hideError();
            } catch (e) {
                showError(e.message);
            }
        }
```

Everything is wrapped in a try/catch — any throw from `convertSvg` is caught and handed to `showError`.

On success, five things happen in order:
1. `convertedSvg` is updated with the new string (making it available to download/copy).
2. The code textarea is filled.
3. The original SVG is parsed again and injected into `previewOriginal` via `innerHTML`. Inline `width`/`height` styles are set to 80×80 so the original renders within the box regardless of its natural dimensions.
4. The converted SVG is injected into `previewConverted` via `innerHTML`. The CSS rule `.preview-box svg { width:80px; height:80px }` handles scaling for it.
5. The output panel is shown and any previous error is cleared.

Note that the original SVG is re-parsed here rather than using the DOM tree from `convertSvg`, because `convertSvg` only returns a string. The second parse is lightweight since `DOMParser` is very fast.

## 13. File Input — Click-to-Browse and Drag-and-Drop

```bash
sed -n '389,418p' svg-converter.html
```

```output
        // File upload
        dropZone.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', () => {
            const file = fileInput.files[0];
            if (file) readFile(file);
        });

        // Drag and drop
        dropZone.addEventListener('dragover', e => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });
        dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
        dropZone.addEventListener('drop', e => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            const file = e.dataTransfer.files[0];
            if (file) readFile(file);
        });

        function readFile(file) {
            if (!file.name.endsWith('.svg') && file.type !== 'image/svg+xml') {
                showError('Please upload an SVG file.');
                return;
            }
            const reader = new FileReader();
            reader.onload = () => process(reader.result);
            reader.onerror = () => showError('Could not read the file.');
            reader.readAsText(file);
        }
```

The drop zone is a styled `<div>` that delegates file selection to the hidden `<input type="file">`. Clicking the div programmatically clicks the input, which opens the OS file picker.

**Drag events:** `dragover` must call `e.preventDefault()` to signal that this element accepts drops (otherwise the browser's default action — navigating to the file — fires). The `dragover`/`dragleave` pair toggles a `.dragover` class for the dashed-border highlight. The `drop` handler also prevents the default, removes the highlight, and extracts the file from `e.dataTransfer.files`.

**readFile** is the shared handler for both paths. It validates the file type by checking both the extension and the MIME type (since browsers may report either), then uses `FileReader.readAsText` to read the file contents as a UTF-8 string, which is handed to `process` in the `onload` callback.

## 14. URL Fetch

```bash
sed -n '420,444p' svg-converter.html
```

```output
        // URL fetch
        fetchBtn.addEventListener('click', async () => {
            const url = urlInput.value.trim();
            if (!url) { showError('Enter a URL first.'); return; }

            fetchBtn.disabled = true;
            fetchBtn.textContent = 'Fetching…';
            hideError();

            try {
                const res = await fetch(url);
                if (!res.ok) throw new Error(`Fetch failed (${res.status}).`);
                const text = await res.text();
                process(text);
            } catch (e) {
                showError(e.message || 'Could not fetch the SVG.');
            } finally {
                fetchBtn.disabled = false;
                fetchBtn.textContent = 'Fetch';
            }
        });

        urlInput.addEventListener('keydown', e => {
            if (e.key === 'Enter') fetchBtn.click();
        });
```

The fetch handler is `async` so it can `await` the network request inline. While fetching, the button is disabled and its label changed to "Fetching…" — simple but effective feedback that something is happening. The `finally` block restores the button unconditionally whether the fetch succeeded or failed.

`res.ok` covers HTTP 2xx codes; any non-2xx response (404, 403, 500…) is treated as an error. The response body is read as plain text with `res.text()` — no JSON parsing needed since SVG is XML text.

The Enter key shortcut on the URL input just programmatically clicks the fetch button, reusing all its logic including the disabled state and error handling.

> **CORS note:** Browser `fetch` is subject to the same-origin policy. Fetching SVGs from servers that don't include CORS headers will fail with a network error. This is a browser security constraint, not a bug in the tool.

## 15. Download and Copy

```bash
sed -n '446,461p' svg-converter.html
```

```output
        // Download
        downloadBtn.addEventListener('click', () => {
            const blob = new Blob([convertedSvg], { type: 'image/svg+xml' });
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'icon.svg';
            a.click();
            URL.revokeObjectURL(a.href);
        });

        // Copy
        copyBtn.addEventListener('click', async () => {
            await navigator.clipboard.writeText(convertedSvg);
            copyBtn.textContent = 'Copied!';
            setTimeout(() => { copyBtn.textContent = 'Copy code'; }, 1500);
        });
```

**Download** uses the Blob URL trick: wrap the SVG string in a `Blob` with the correct MIME type, create an object URL pointing to it, attach it to a temporary `<a>` element with a `download` attribute, click it programmatically, then immediately revoke the object URL to release memory. The `<a>` element is never appended to the DOM — it only needs to exist transiently in memory for `.click()` to work.

**Copy** uses the modern `navigator.clipboard.writeText` API (requires HTTPS or localhost). The button text swaps to "Copied!" for 1.5 seconds as confirmation, then resets. No error handling here — clipboard failures silently no-op, which is acceptable for a convenience feature.

## Summary — Data Flow

Here is the complete data flow from user action to rendered output:

```
User action
    │
    ├─ File upload / drag-drop ──► readFile() ──► FileReader.readAsText()
    │                                                       │
    └─ URL fetch ────────────────► fetch() ────► res.text() │
                                                            ▼
                                                       process(raw)
                                                            │
                                          ┌─────────────────┤
                                          │                 │
                                    convertSvg(raw)    re-parse raw
                                          │            for original preview
                                  ┌───────┤                 │
                           resolveViewBox  collectPaths   inject into
                                  │            │        #preview-original
                              needsTransform?  │
                                  │            │
                              build <svg>  flatten shapes
                                  │            │
                              serialize & clean namespace
                                          │
                                   convertedSvg string
                                          │
                          ┌──────────────┬┴──────────────┐
                          │              │                │
                    textarea          #preview-converted  convertedSvg var
                    (code view)       (rendered SVG)      (for download/copy)
```
