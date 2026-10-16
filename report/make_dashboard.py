"""Standalone results dashboard: one self-contained HTML file that opens in any
browser. The page layout lives in report/dashboard_page.html; this script
embeds the result CSVs into it, so re-running it after new experiments
refreshes every number and chart.

Usage: python -m report.make_dashboard   (run from project root)  ->  report/dashboard.html

Charts use d3 from cdnjs, so the first open needs an internet connection.
"""
import csv
import json
import os

HERE = os.path.dirname(__file__)
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "dashboard.html")
PAGE = os.path.join(HERE, "dashboard_page.html")
D3 = "https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"

# dataset id used by the page -> CSV it reads
DATASETS = {
    "summary": "results/final_summary.csv",
    "stats": "results/final_stats.csv",
    "cic": "results/cic_results.csv",
    "overhead": "results/overhead.csv",
    "ablation": "results/ablation.csv",
    "portscan": "data/processed/cic_PortScan.csv",
}

# ---- design tokens (light, then dark) ------------------------------------
TOKENS = """
:root {
  --font-anthropic-sans: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --font-anthropic-serif: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
  --cds-font-size-caption: 0.8125rem; --cds-font-size-body: 0.9375rem;
  --cds-font-size-heading: 1.0625rem; --cds-font-size-title: 1.75rem;
  --cds-font-weight-medium: 600;
  --cds-gap-xs: 4px; --cds-gap-sm: 8px; --cds-gap-md: 16px; --cds-gap-lg: 24px; --cds-gap-xl: 40px;
  --cds-pad-xs: 4px; --cds-pad-sm: 8px; --cds-pad-md: 12px; --cds-pad-lg: 20px;
  --cds-radius: 8px; --cds-dur-slow: 300ms;
  --color-bg: #f6f8f8; --color-panel: #ffffff; --color-fg: #1a2b30; --color-fg-muted: #5f6f73;
  --color-border-line: #dde3e3; --color-ok: #1f7a4d; --color-warn: #a35f00; --color-bad: #b3261e;
  --s1: #2e6e63; --s2: #5e7a99; --s3: #c77400; --s4: #7b5ea7; --s5: #3a8fb7; --s6: #a34e6f; --s7: #6b8e23; --s8: #8a6d3b;
  --cds-chart-muted: #b4bfc1; --cds-chart-grid: #e6eaea; --cds-chart-axis: #8a979b; --cds-chart-reference: #8a979b;
  --cds-surface-popover: #ffffff; --cds-border: #d3dada; --cds-text-secondary: #5f6f73;
  --cds-shadow-popover: 0 4px 16px rgba(20, 40, 45, 0.12);
}
@media (prefers-color-scheme: dark) {
  :root {
    --color-bg: #11191b; --color-panel: #182326; --color-fg: #e4eaeb; --color-fg-muted: #9aa9ad;
    --color-border-line: #2a383b; --color-ok: #5cc28c; --color-warn: #e0a040; --color-bad: #f07167;
    --s1: #5fb3a3; --s2: #8fa9c7; --s3: #e0a040; --s4: #b39ddb; --s5: #6cc0e5; --s6: #d98aa8; --s7: #9cc35a; --s8: #c9a26b;
    --cds-chart-muted: #4f5f63; --cds-chart-grid: #233033; --cds-chart-axis: #6f8085; --cds-chart-reference: #6f8085;
    --cds-surface-popover: #1e2b2e; --cds-border: #33454a; --cds-text-secondary: #9aa9ad;
    --cds-shadow-popover: 0 4px 16px rgba(0, 0, 0, 0.45);
    color-scheme: dark;
  }
}
html { background: var(--color-bg); }
body { margin: 0; background: var(--color-bg); color: var(--color-fg); font-family: var(--font-anthropic-sans); font-size: 14px; }
#dash-root { padding-block: 32px 48px; padding-left: max(16px, 4vw); padding-right: max(16px, 4vw); }
.dash-skeleton { color: transparent; background: var(--color-border-line); border-radius: 4px; }
"""

# ---- minimal stand-in for the claude.ai dashboard runtime -----------------
# Implements only what the page uses: dash.data, dash.calc, dash.onData, dash.colors.
RUNTIME = """
window.dash = (function () {
  const DATA = window.__DASH_DATA__, calcs = {}, cache = {}, subs = [];
  const data = (id) => {
    if (DATA[id]) return { status: 'ok', data: DATA[id], columns: Object.keys(DATA[id][0] || {}), meta: [] };
    if (calcs[id]) {
      if (!(id in cache)) cache[id] = calcs[id].fn(...calcs[id].inputs.map((i) => data(i).data));
      return { status: 'ok', data: cache[id], columns: Object.keys(cache[id][0] || {}), meta: [] };
    }
    return { status: 'missing', data: [], columns: [], meta: [] };
  };
  let t;
  window.addEventListener('resize', () => { clearTimeout(t); t = setTimeout(() => subs.forEach((f) => f()), 150); });
  return {
    data,
    calc: (id, spec) => { calcs[id] = spec; },
    onData: (fn) => { subs.push(fn); fn(); },
    colors: ['--s1', '--s2', '--s3', '--s4', '--s5', '--s6', '--s7', '--s8'].map((v) => `var(${v})`),
  };
})();
"""


def read_rows(path):
    with open(os.path.join(ROOT, path), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    data = {k: read_rows(p) for k, p in DATASETS.items()}
    with open(PAGE, encoding="utf-8") as f:
        page = f.read()
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Adaptive Network Traffic Anomaly Detection</title>
<style>{TOKENS}</style>
<script src="{D3}"></script>
</head>
<body>
<script>window.__DASH_DATA__ = {blob};</script>
<script>{RUNTIME}</script>
<div id="dash-root">
{page}
</div>
</body>
</html>
"""
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"wrote {os.path.relpath(OUT, ROOT)}  ({len(html) // 1024} KB)")


if __name__ == "__main__":
    main()
