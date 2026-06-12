# Dashboard design knowledge (taste-skill, distilled)

This is the design system behind the `dashboard_notion` hero poster. It is the
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
