# dashboard_notion

A drop-in **addon** that renders a graphical project dashboard and mirror-syncs it
into a Notion page. Zero Python dependencies (standard library only). The runtime is
**LLM-free and deterministic** — any LLM (local or hosted) is only useful *upstream*,
to author/update the data.

```
dashboard_notion/
├── SKILL.md                  # skill manifest (Claude Code / agent entry point)
├── DESIGN.md                 # the taste-skill design knowledge (the reusable "look")
├── README.md                 # this file
├── notion.env.example        # copy -> notion.env, fill token + page id
├── scripts/
│   ├── notion_sync.py        # the engine: STATE -> hero PNG + Notion blocks -> mirror sync
│   └── dashboard.html        # hero poster template (taste-skill applied)
└── examples/
    └── example_state.json     # a filled STATE to learn from (generic demo)
```

## What it produces

1. A **hero image** — `dashboard.html` rendered to PNG by a headless browser, posted
   as the page's top image (full design control; see `DESIGN.md`).
2. **Native Notion blocks** below it — banner, status cards, a Mermaid flow chart,
   a to-do work list, colored issue callouts, and collapsible milestone/settings/ref
   sections — all built from the same `STATE`.

Every run rebuilds the page (mirror sync), so it is the durable record and any
upstream chat log can be cleared freely.

## Install (download from anywhere → use)

1. Copy this whole `dashboard_notion/` folder into any project (or clone it standalone).
2. `cp notion.env.example notion.env` and fill in `NOTION_API_TOKEN` +
   `NOTION_DASHBOARD_PAGE_ID` (instructions are in the file).
3. Verify the build without touching Notion:
   ```bash
   python3 scripts/notion_sync.py --dry-run
   ```
4. Push it for real:
   ```bash
   python3 scripts/notion_sync.py
   ```

### Prerequisites
- `python3` (3.8+). No `pip install` needed.
- A headless **Chrome or Edge** for the hero image (auto-detected: Windows Chrome/Edge
  on WSL — best for CJK; Chrome/Chromium on Linux/macOS). Without one, it falls back to
  native blocks only (`--no-image` to skip on purpose).
- A Notion integration connected to the target page.

## Customize for your project

Edit the **data**, not the engine:

- **Quick**: copy `examples/example_state.json` to `dashboard_state.json` (next to the
  script, or point `--state`/`$DASHBOARD_STATE` at it) and edit the values.
- **Hero look**: edit `scripts/dashboard.html` content; to re-skin, change only the
  `--accent` CSS variable. Read `DESIGN.md` first — it encodes the rules that keep it
  looking deliberate.

```bash
python3 scripts/notion_sync.py --state dashboard_state.json
python3 scripts/notion_sync.py --no-image          # native blocks only
python3 scripts/notion_sync.py --html my_hero.html  # custom hero
```

## STATE shape (cheat sheet)

```jsonc
{
  "title_banner": ["text", "blue_background"],      // Notion color name
  "overall":      ["🟢 label", "sentence", "green_background"],
  "progress_pct": 85,
  "cards":  [["emoji","title","line1\nline2","green_background"], ...],   // 4 recommended
  "flow":   "flowchart TD ...",                      // raw Mermaid (done/wip/wait classes)
  "todos":  [["**task** — detail", false], ...],
  "issues": [["🔴","**title** — detail","red_background"], ...],
  "milestones": [["col","headers",".."], ["row",...], ...],   // optional, -> table in a toggle
  "settings":   ["**Policy**: ...", ...],            // optional, -> bullets in a toggle
  "refs":       ["Repo: `path`", ...]                // optional, -> bullets in a toggle
}
```
Tuples in Python become arrays in JSON — both work.

## Driving updates with a local LLM

The engine never calls an LLM. To automate "read progress → write `dashboard_state.json`",
point any OpenAI-compatible endpoint (Ollama / llama.cpp / LM Studio) at your progress
source and have it emit the STATE JSON, then run `notion_sync.py`. Small models handle
the JSON fine; the *design taste* lives in `dashboard.html` + `DESIGN.md`, so the look
holds regardless of which model writes the data.
