---
name: aurora
description: |
  Aurora — build a stylish project dashboard from a compact STATE dict, to TWO targets:
  a self-contained local HTML page (no Notion, no network beyond fonts) and/or a Notion
  page (mirror-synced). Zero-dependency Python (stdlib only); LLM-free and deterministic
  at runtime. Rich component library: KPI ring, status cards, AI insights, highlights,
  bar chart, SVG line chart, sliders/meters, a styled stage pipeline with clickable
  per-node notes, work list, issue callouts, milestones, collapsibles. Ships a design
  dataset (Refactoring UI / Gestalt / Tailwind / Material) so any LLM produces deliberate,
  non-amateur output. Use when: "dashboard", "Aurora", "進捗ダッシュボード", "project dashboard",
  "Notion dashboard", "ダッシュボード作成", "render_local", "notion_sync".
  Do NOT use for: generic Notion CRUD, non-dashboard pages.
argument-hint: "[--state STATE.json] [--serve PORT] | notion_sync [--dry-run|--no-image]"
allowed-tools: Bash, Read, Edit, Write
---

# Aurora — stylish dashboards from one STATE

A portable addon. Full docs in `README.md`; design system in `DESIGN.md`; the bundled
design knowledge in `design_dataset.md`.

## North Star
A project's status is legible **at a glance**, looks **deliberate** (not AI-default), and
costs the LLM almost nothing per update — because the LLM only writes a compact `STATE`,
while the renderer (the "下地") owns all markup, styling, charts, and interactivity.

## Two render targets, one source of truth (`STATE`)
- **Local HTML** — `scripts/render_local.py` → one self-contained page (premium dark glass,
  fully offline except web fonts + Mermaid fallback). No Notion.
- **Notion** — `scripts/notion_sync.py` → hero image (HTML→PNG, CJK-safe) + native blocks,
  mirror-synced (page rebuilt each run).

## Components (render from STATE; each section appears only if its key is present)
banner · overall · KPI ring (`progress_pct`) · `highlights` · `insights` (AI) · `cards` ·
`bars` (bar chart) · `trend` (SVG line) · `meters` (sliders) · `flow`+`flow_notes`
(styled pipeline, click a node → inline detail panel) · `todos` · `issues` · `milestones` ·
`settings` · `refs`.

## Run
```bash
# Local HTML (no Notion):
python3 scripts/render_local.py --state examples/example_state.json --serve 8088
#   open http://127.0.0.1:8088/dashboard_local.html   (or omit --serve for a file)

# Notion (one-time: cp notion.env.example notion.env, fill token + page id):
python3 scripts/notion_sync.py --dry-run     # build only
python3 scripts/notion_sync.py               # render + upload + mirror sync
```

## Customize
Edit **data, not engine**: copy `examples/example_state.json` → `dashboard_state.json`
and edit. To re-skin, change only `--accent` in the CSS. Read `DESIGN.md` +
`design_dataset.md` first — they encode the rules that keep it looking deliberate.

## Notes
- Standard library only — no `pip install`. A headless Chrome/Edge is used for the Notion
  hero image (auto-detected; Windows Chrome/Edge on WSL for CJK).
- LLM-free at runtime. A local or hosted LLM is only useful upstream, to author `STATE`.
- `notion_sync.py --dry-run` is the safe preflight; it never touches Notion.
