# Dashboard design knowledge (taste-skill, distilled)

This is the design system behind the `aurora` hero poster. It is the
*reusable* part — the reason the output looks deliberate instead of "AI-default".
Hand this file to any LLM (local or hosted) and it can reproduce the look.

Origin: the **taste-skill** discipline (github.com/leonxlnx/taste-skill).
The three dials below are its core; the rules are its guardrails.

## The three dials

| Dial | Range | Dashboard setting | What it controls |
|------|-------|-------------------|------------------|
| `DESIGN_VARIANCE` | 0–10 | **5** | How far layout deviates from a plain stack. 5 = bento KPI + pipeline + 2-col, still legible. |
| `MOTION_INTENSITY` | 0–10 | **1** | Animation/energy. 1 because the output is a static PNG — motion would be wasted. |
| `VISUAL_DENSITY` | 0–10 | **6** | Information per area. 6 = rich but not cramped; every card earns its space. |

## Locked rules (do not break)

1. **Single accent, locked.** One brand color only (`--accent`, here indigo `#818cf8`).
   To re-skin a project, change *only* `--accent`. Never introduce a second decorative hue.
2. **Semantic state palette is separate from the accent.** `done`=emerald, `wip`=amber,
   `wait`=rose. These encode *meaning*, never decoration. Don't recolor them per project.
3. **No pure black, no pure white.** Background is `#0e0f14`, ink is `#e8eaf0`.
   Pure `#000`/`#fff` read as cheap and harsh; always offset.
4. **No em-dash as decoration.** (taste-skill signature rule.) Use real structure —
   columns, cards, dividers — not punctuation, to separate ideas.
5. **No filled "progress bar" clichés in the hero.** Use a conic-gradient ring for the
   headline percentage. (The Notion native side keeps a unicode █░ bar — that's the
   plain-text channel, where a bar is the honest primitive.)
6. **Generous radius + hairline borders.** `--r:18px`, borders at 8–14% white.
   Surfaces sit on the bg via subtle elevation, not heavy strokes.
7. **Two typefaces, two jobs.** `Outfit` for prose, `JetBrains Mono` for numbers/IDs/timestamps.
   Numbers in mono read as data; never set KPI figures in the prose font.
8. **Width is locked to 1200px** to match `notion_sync.py --window-size=1200,1422`.
   Design within that frame; don't make it fluid.

## Why a headless *Windows/native* browser (CJK note)

On WSL2 the Linux side often lacks Japanese fonts → tofu (□□□) in the PNG.
`notion_sync.py` therefore prefers a **Windows Chrome/Edge** (native CJK fonts) when
on WSL, falling back to a local Chrome/Chromium elsewhere. This is the root fix for
the font-tofu class of bug — nothing needs installing on WSL itself.

## The two-channel model (why it looks unified)

One `STATE` dict drives **both**:
- the **hero image** (this HTML → PNG), full design control, and
- the **native Notion blocks** (callouts/columns/mermaid/toggles), Notion's own styling.

The hero is where taste-skill lives. The native blocks below it are constrained by
Notion's ~10 background colors and fixed chrome — so they will always look a little
more "default". If you want a single unified design with no visual seam, drop the
Notion native channel and render everything from `STATE` into one self-hosted HTML
page (the block builders map 1:1 to HTML/CSS: callout→div, column_list→flex,
mermaid→Mermaid.js, toggle→`<details>`, table→`<table>`). That is the documented
"next step" for full design unification.

## Content style (mixed language)

When the audience is Japanese: **short labels / technical terms stay in English**
(card titles, flow node names, status tags, milestone themes — e.g. `Features`,
`Tests`, `API v2`, `Plan → GA`), but **explanatory prose is written in Japanese**
(the overall summary, to-do detail after the `—`, issue descriptions, settings).
This keeps scannable labels compact and universal while sentences read naturally.

Icons in the flow chart are just emoji inside the Mermaid node label
(`A["🔨 Build"]`) — the LLM adds one character, the renderer draws it. No SVG,
no extra tokens. The same applies to cards/issues, which already lead with an emoji.

Clickable node explanations (local render): add a `flow_notes` map to STATE keyed by
the Mermaid node id (`{"A": "…説明…"}`). `render_local.py` wires each node's click to
an **inline detail panel under the flow** (`#flowDetail`) — NOT a modal. Modals block
the screen and force a close action; prefer non-modal inline/drawer/tooltip reveals.
The LLM only writes short note text per node; interactivity is the renderer's job.

## Flow / pipeline chart (standard pattern)

This is the **canonical way to present a flow / pipeline / process** in Aurora. Any LLM
authoring a `STATE` that describes a multi-step process MUST reproduce this pattern
deliberately (schema + interaction + information order below). `render_local.py` already
implements all of it generically — the LLM only writes the data.

The pattern is built from **four cooperating STATE keys** that point at the same phases:

| Key | Role on the page | Shape |
|-----|------------------|-------|
| `flow` | **top strip** of icon nodes (the quick-scan ribbon) | a `flowchart LR` mermaid string |
| `flow_notes` | per-node description, shown in the **sticky panel** on hover | `{ nodeId -> text }` |
| `flow_cards` | **vertical DETAIL list** (one rich card per phase) | list of dicts |
| `flow_cards2` | **horizontal OVERVIEW list** (compact, one row of cards) | list of dicts |

### Schema

**`flow`** — `parse_pipeline` reads the nodes **in definition order** and turns them into
the top strip. Node ids should be `P1`, `P2`, … (the anchor key); the `:::state` classDef
suffix on each node maps to a state (`done` / `wip` / `wait` / `new` / `plan` / `crit`).
The first emoji in the label becomes the node icon, the rest becomes its name.
Branching graphs (`subgraph`, `-.->`, `==>`) fall back to Mermaid and are NOT a strip — keep
the standard flow a **simple linear sequence** so the strip renders.

```jsonc
"flow": "flowchart LR\n P1[\"📋 Brief\"]:::done --> P2[\"✍ Draft\"]:::done --> P3[\"🚀 Publish\"]:::wait\n classDef done ...; classDef wip ...; classDef wait ...;"
```

**`flow_notes`** — keyed by the SAME node ids (`P1`…). The text is what appears in the
sticky `#flowDetail` panel when that node is hovered. The panel header shows the node label.

```jsonc
"flow_notes": { "P1": "依頼の受領と要件確定 …", "P2": "下書きの執筆 …" }
```

**`flow_cards`** (vertical detail) / **`flow_cards2`** (horizontal overview) — each item is a
**dict** (not a tuple — fields are optional, so named keys stay robust):

```jsonc
{
  "step":  "P1",                 // MUST match a flow node id -> shares the scroll anchor
  "icon":  "📋",                 // one emoji
  "title": "Brief",
  "state": "done",               // done | wip | wait | new  (semantic color; default done)
  "roles": ["Editor", "Client"], // tag chips
  "desc":  "説明 (Markdown **bold** 可)",
  "sample": { ... }              // optional, one representative artifact (see below)
}
```

`flow_cards` carries the `sample`; `flow_cards2` is the compact overview and needs **no
sample**. The FIRST `flow_cards` set rendered owns the canonical phase anchors
(`emaki-phase-{step}`) and the per-card "back to flowchart" button; the overview only links
*into* those anchors.

**`sample` types** (one per card, all degrade gracefully):

| `type` | fields | render |
|--------|--------|--------|
| `text`   | `label`, `body` | blockquote (Markdown bold supported) |
| `image`  | `label`, `path` (or `src`), `alt` | base64-embedded `<img>` (`path` is relative to the STATE file's dir) |
| `images` | `label`, `paths[]` | base64-embedded 3-col grid |
| `videos` | `label`, `paths[]`, optional `posters[]` (parallel to `paths`) | relative `<video controls preload=none>` per clip |

Asset rules: **small images** → base64-embed via `path` (self-contained HTML). **Large
videos** → relative `<video>` src with a per-clip `poster` (do NOT base64 a video). A missing
image renders a `(画像未検出: …)` caption instead of crashing.

### Interaction model (must hold exactly)

**Top-strip icon — on HOVER** (`mouseover`/`focusin`):
- Its description appears in the sticky `#flowDetail` panel below the strip (header = phase
  label, body = `flow_notes[id]`).
- The panel is **STICKY**: on mouse-leave it does NOT revert — it keeps the last-hovered
  node's content until a **different** node is hovered.
- The hovered node gets a **persistent `.is-current` marker** (accent ring/glow on the icon +
  accent name + accent connector dot) so the reader can always tell which icon the panel text
  belongs to. **Exactly one node is `.is-current` at a time.** A transient `.is-hot` lift is
  added only while the cursor is actually on the node.

**Top-strip icon — on CLICK / Enter**: smooth-scrolls to that phase's DETAIL card
(`emaki-phase-{step}`) and flashes it.

**Each DETAIL card**: shows step / icon / title / state / roles / desc + the one sample, plus
a **"フローチャートへ戻る" button** that scrolls back to the flow section. The card icon also
has a body-level hover tooltip (`#emaki-tip`, the card's `desc`) — immune to card
overflow/stacking context (a CSS `:hover` child span failed in real browsers, so the tooltip
is a single `position:fixed` body element driven by JS).

**State display**: muted **tinted border + a small colored dot** (done = emerald, wip =
amber, wait = rose, new = indigo). The **single `--accent`** is reserved for the active/hover
highlight — no clashing palette; state encodes meaning, the accent encodes focus.

### Information organization (the order to author in)

```
目的   →  banner + overall summary (+ KPI ring / highlights)
フロー  →  top strip (flow) + sticky panel (flow_notes)
          + vertical DETAIL cards (flow_cards) + horizontal OVERVIEW (flow_cards2)
その他  →  roles / issues + references
```

Per phase, keep it to: **state + roles + a concise desc + one representative sample.** Don't
overload a card; the strip is for scanning, the detail card is for the single best artifact.

### Design rules to note

Dark-glass, **single accent**; small images base64-embedded; large videos via relative
`<video>` + per-clip `posters`; the whole page is **one self-contained HTML file**.

---

## Flow summary card (component reference)

`flow_cards` is a **first-class built-in component** — the detailed companion to `flow`
(which is a quick-scan ribbon). Where `flow` gives a 1-line per-phase status at a glance,
`flow_cards` gives each phase its own card with roles, description, and a sample artifact.

### When to use which

| Component | Use case |
|-----------|----------|
| `flow` + `flow_notes` | Quick pipeline scan; clickable detail popover; Notion-compatible |
| `flow_cards` | Phase-by-phase details + real sample output (text / image); local HTML only |

Combine both in one STATE to get both views — use `flow` for the Notion-compatible strip
and `flow_cards` for the full phase-by-phase walkthrough.

### Layouts

- **`"vertical"` (default)** — single-column timeline with border-left spine and per-card
  node dot. Sample artifacts display full-width (物語本文 / storyboard 画像など). Best for
  sequential pipelines where reading order matters.
- **`"horizontal"`** — CSS grid `repeat(auto-fit, minmax(220px,1fr))` with auto-wrap.
  9 cards sit in 3–4 columns on 1200px; single-row forcing is avoided (unreadable). Sample
  images thumbnail (max-height), sample text line-clamped. Collapses to 1 column at 760px.

### Design decisions (locked rules compliance)

- **Glass surface inherited via shared selector** — `.fc-card` is added to the existing
  multi-target rule (`.card,.panel,.flowbox,…`) so it inherits `background:var(--card)`,
  `border`, `box-shadow`, and `backdrop-filter` automatically. DRY, no duplicated properties.
- **State color = semantic meaning** — `.fc-card.done/wip/wait` reuse `--done/--wip/--wait`
  on the left accent border, identical to `pl-node`. State encodes meaning, never decoration
  (locked rule 2).
- **Single accent** — `.fc-step` uses `var(--accent)` for mono ID display (locked rule 7:
  numbers/IDs in mono). No second decorative hue introduced (locked rule 1).
- **Radius + hairline border** — `var(--r)`, border at `var(--line)` weight (locked rule 6).
- **No pure black/white** — ink tokens used throughout (locked rule 3).

### Sample embedding rules (portability)

- `"path"`: relative to the **STATE file's directory**. `render_local.py` resolves
  `os.path.join(base_dir, path)` at build time and embeds as `data:{mime};base64,…`. The
  output HTML is fully self-contained regardless of where it is opened.
- `"src"`: inline `data:…` URI written directly into STATE. Portable but bloats the JSON
  (avoid for images > ~10KB; prefer `path`).
- Missing file: renderer outputs `<figcaption>(画像未検出: path)</figcaption>` and
  continues rendering — never crashes (graceful degradation).
- **Skill examples must not reference `docs/` images** — `examples/` is a drop-in addon
  subdirectory. Use `examples/assets/` for demo images.

### Icon hover (rollover) — built-in, both layouts

Each flow-card **icon** carries a CSS-only hover/focus affordance (no JS, non-modal):

- **Highlight** — on `:hover`/`:focus-visible` the icon glows (`drop-shadow` in `--accent`)
  and scales up slightly. The icon is `tabindex="0"` so keyboard focus reveals it too (a11y).
- **Tooltip** — a `.fc-ic-tip` bubble (the card's `desc`) appears below the icon, anchored
  with an arrow. It is a pure CSS reveal (`opacity`/`visibility` on `:hover`), so it works
  identically in **vertical** and **horizontal** layouts and adds zero tokens to the STATE.

The LLM does nothing extra: any card that has a `desc` automatically gets the icon tooltip.
Modals are still avoided per the non-modal rule — this is an inline tooltip, not a dialog.

### dict schema (not tuple)

`flow_cards` uses `dict` for each card, unlike tuple-based components (`cards`, `issues`,
`bars`). Reason: flow cards have many optional fields (`step`, `icon`, `roles`, `desc`,
`sample`). Position-dependent tuples become fragile when fields are optional; named dicts
stay readable and extendable. This asymmetry is intentional and is documented here.
