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
