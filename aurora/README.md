# Aurora

A drop-in **addon** that turns one compact `STATE` dict into a stylish project dashboard,
rendered to **two targets**:

- **Local HTML** (`render_local.py`) — a single self-contained, premium dark-glass page you
  open in a browser. No Notion, no network beyond web fonts (+ a Mermaid CDN only as a
  branching-graph fallback).
- **Notion** (`notion_sync.py`) — a hero image (HTML→PNG, CJK-safe) plus native Notion
  blocks, mirror-synced (the page is rebuilt every run).

Zero Python dependencies (standard library only). The runtime is **LLM-free and
deterministic** — an LLM (local or hosted) is only useful *upstream*, to author `STATE`.
All markup, styling, charts, and interactivity live in the renderer (the "下地"), so each
update costs the LLM only the small `STATE` delta.

```
aurora/
├── SKILL.md                # skill manifest (agent entry point)
├── DESIGN.md               # the design system (taste-skill + how the renderer encodes it)
├── design_dataset.md       # bundled design knowledge (Refactoring UI / Gestalt / Tailwind / Material + 2026 dashboard practice)
├── README.md               # this file
├── notion.env.example      # copy -> notion.env (Notion target only)
├── scripts/
│   ├── render_local.py     # STATE -> one self-contained local HTML page (no Notion)
│   ├── notion_sync.py      # STATE -> hero PNG + Notion blocks -> mirror sync
│   └── dashboard.html      # Notion hero poster template
└── examples/
    └── example_state.json  # a rich, filled STATE showcasing every component
```

## Components

Each section renders only if its `STATE` key is present:

| Key | Component |
|-----|-----------|
| `title_banner`, `overall`, `progress_pct` | banner + KPI ring |
| `highlights` | featured metric tiles (with ▲/▼ delta) |
| `insights` | **AI insights** — proactive recommendations |
| `cards` | status cards |
| `bars` | horizontal bar chart |
| `trend` | SVG line chart |
| `meters` | sliders / gauges |
| `flow` + `flow_notes` | styled stage **pipeline** (top icon strip); hover a node → its note fills the **sticky** `#flowDetail` panel + the node gets a persistent "current" marker; click → scrolls to the matching detail card |
| `flow_cards` + `flow_cards_layout` | **flow summary cards** — vertical DETAIL: phase-by-phase cards with text/image/images/videos samples; layout `"vertical"` (default, timeline) or `"horizontal"` (wrap grid) |
| `flow_cards2` (+`flow_cards2_layout`) | **flow overview** — horizontal OVERVIEW companion to `flow_cards` (compact, sampleless) |
| `todos` / `issues` | work list / colored issue callouts |
| `milestones` / `settings` / `refs` | cards + collapsibles |

> **Flow / pipeline chart — standard pattern.** To present any multi-step process, use the
> four cooperating keys together — `flow` (top icon strip) + `flow_notes` (sticky hover
> panel) + `flow_cards` (vertical detail cards) + `flow_cards2` (horizontal overview). Each
> card's `step` must equal its `flow` node id (`P1…`) so they share a scroll anchor: hover a
> strip icon → its note sticks in the panel and the icon gets a persistent "current" marker;
> click → scrolls to that detail card. Full schema + interaction contract + information order
> live in **`DESIGN.md` → "Flow / pipeline chart (standard pattern)"**;
> `examples/example_state.json` is a runnable generic demo.

## Quick start

**Local HTML (no Notion):**
```bash
python3 scripts/render_local.py --state examples/example_state.json --serve 8088
#   open http://127.0.0.1:8088/dashboard_local.html
# or, just write a file:
python3 scripts/render_local.py --state examples/example_state.json --out dash.html
python3 scripts/render_local.py --no-cdn     # fully offline (raw flow source instead of Mermaid fallback)
```

**Notion:**
```bash
cp notion.env.example notion.env     # fill NOTION_API_TOKEN + NOTION_DASHBOARD_PAGE_ID
python3 scripts/notion_sync.py --dry-run     # build only, no Notion call
python3 scripts/notion_sync.py               # render + upload + mirror sync
```

### Prerequisites
- `python3` (3.8+). No `pip install`.
- For the **Notion hero image**: a headless Chrome/Edge (auto-detected — Windows
  Chrome/Edge on WSL is best for CJK; Chrome/Chromium on Linux/macOS). The local HTML
  needs no browser to *build* (only to view).
- For the **Notion target**: an integration connected to the page (••• → Connections).

## Customize

Edit the **data, not the engine**: copy `examples/example_state.json` →
`dashboard_state.json` (or point `--state` / `$DASHBOARD_STATE` at it) and edit. To
re-skin, change only the `--accent` CSS variable in `render_local.py` / `dashboard.html`.
Read `DESIGN.md` + `design_dataset.md` first — they hold the rules that keep it deliberate.

## STATE cheat sheet

```jsonc
{
  "title_banner": ["text", "blue_background"],
  "overall":      ["🟢 label", "sentence", "green_background"],
  "progress_pct": 72,
  "highlights": [["📈","Active users","12,480","▲ 18%"], ...],
  "insights":   [["🚀","recommendation text", "blue_background"], ...],
  "cards":      [["🟢","Title","line1\nline2","green_background"], ...],
  "bars":       [["Label", 88, 100, "green_background"], ...],          // value, max, color
  "trend":      {"points":[12,18,16,24], "labels":["W1","W2","W3","W4"]},
  "meters":     [["CPU", 42, 0, 100, "%"], ...],                        // value, min, max, unit
  "flow":       "flowchart LR\n A[\"📋 Plan\"]:::done --> B[\"🚀 Beta\"]:::wip ...",
  "flow_notes": {"A":"…click-to-show explanation…", "B":"…"},
  // flow_cards: フェーズ要約カード (standard component)
  // layout: "vertical"(default, タイムライン) | "horizontal"(wrap グリッド)
  "flow_cards_heading": "🗺️ Pipeline",
  "flow_cards_layout": "vertical",
  "flow_cards": [
    {
      "step": "P1",           // mono 表示される工程 ID (任意)
      "icon": "✍",            // 絵文字 1 字 (任意)
      "title": "Story",       // 必須相当
      "state": "done",        // "done"|"wip"|"wait" (任意・既定 "done")
      "roles": ["Writer"],    // 役職タグ (任意)
      "desc": "説明テキスト (Markdown **bold** 対応)",
      "sample": {             // (任意) フェーズの実例
        // text 形式:
        "type": "text", "label": "出力例ラベル", "body": "本文テキスト"
        // image 形式 (path 推奨 — STATE ファイルのディレクトリ基準で base64 埋込):
        // "type": "image", "label": "画像ラベル", "path": "assets/sample.jpg", "alt": "alt text"
        // または inline data-URI:
        // "type": "image", "label": "...", "src": "data:image/png;base64,..."
      }
    }
  ],
  // 移植性メモ: 画像は path 形式推奨(STATE 基準でレンダラが build 時 base64 化)。
  // skill example は docs/ 画像を参照せず examples/assets/ に同梱のこと。
  "todos":      [["**task** — detail", false], ...],
  "issues":     [["🔴","**title** — detail","red_background"], ...],
  "milestones": [["col","headers",".."], ["v0.1","Theme","summary"], ...],
  "settings":   ["**Policy**: …", ...],
  "refs":       ["Repo: `path`", ...]
}
```
Convention: short labels/terms in English, explanatory prose in Japanese (see `DESIGN.md`).
Pipeline icons = an emoji at the start of a node label; the renderer draws them. No SVG.

## Driving updates with a local LLM

The engine never calls an LLM. To automate "read progress → write `dashboard_state.json`",
point any OpenAI-compatible endpoint (Ollama / llama.cpp / LM Studio) at your progress
source and have it emit the STATE JSON, then run a renderer. Small models handle the JSON
fine; the *design taste* lives in the renderer + `DESIGN.md` + `design_dataset.md`, so the
look holds regardless of which model writes the data.
