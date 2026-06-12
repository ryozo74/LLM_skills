---
name: dashboard_notion
description: |
  Render a graphical project dashboard and mirror-sync it into a Notion page.
  Zero-dependency Python (stdlib only); the runtime is LLM-free and deterministic.
  Produces a taste-skill hero image (HTML -> PNG via headless browser, CJK-safe) plus
  native Notion blocks (status cards, Mermaid flow, to-do list, issue callouts,
  collapsible milestones) from a single STATE dict. Mirror sync = page rebuilt each run.
  Use when: "Notion dashboard", "sync progress to Notion", "ダッシュボード Notion 同期",
  "プロジェクト進捗を Notion に", "notion_sync", "dashboard_notion".
  Do NOT use for: generic Notion CRUD, non-dashboard pages.
argument-hint: "[--dry-run | --no-image | --state STATE.json]"
allowed-tools: Bash, Read, Edit, Write
---

# dashboard_notion — graphical Notion dashboard sync

A portable addon. Full docs in `README.md`; design system in `DESIGN.md`.

## North Star
A project's status is legible **at a glance** and **durably recorded** in Notion, so
upstream chat history can be cleared without losing the record. The look is deliberate
(taste-skill), not AI-default.

## How it works (two channels, one source of truth)
`STATE` (data) →
- **hero image**: `scripts/dashboard.html` rendered to PNG by a headless browser
  (Windows Chrome/Edge preferred on WSL for CJK fonts), posted as the page's top image.
- **native blocks**: banner / status cards / Mermaid flow / to-do / issue callouts /
  collapsible milestone+settings+ref toggles, built by `scripts/notion_sync.py`.

Mirror sync: every run DELETEs old blocks and appends fresh ones.

## Run
```bash
# 1. one-time: cp notion.env.example notion.env  (fill token + page id)
python3 scripts/notion_sync.py --dry-run            # build only, no Notion call
python3 scripts/notion_sync.py                       # render + upload + sync
python3 scripts/notion_sync.py --state mystate.json  # custom data
python3 scripts/notion_sync.py --no-image            # native blocks only
```

## Customize
Edit **data, not engine**: copy `examples/example_state.json` → `dashboard_state.json`
and edit. For the hero look, edit `scripts/dashboard.html` (change only `--accent` to
re-skin) — read `DESIGN.md` first.

## Auth
`notion.env` (next to script / repo root / CWD) or env: `NOTION_API_TOKEN`,
`NOTION_DASHBOARD_PAGE_ID`. The integration MUST be added to the page via
••• → Connections, or the API returns 401/404.

## Notes
- Standard library only — no `pip install`.
- LLM-free at runtime. A local/hosted LLM is only useful upstream to author STATE
  (see README "Driving updates with a local LLM").
- `--dry-run` is the safe preflight; it never touches Notion.
