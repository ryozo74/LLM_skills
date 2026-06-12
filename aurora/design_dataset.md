# Aurora design dataset

The reusable design knowledge Aurora encodes. Hand this to any LLM (local or hosted) and
it can produce deliberate, non-amateur dashboards. The renderer already bakes most of this
in; this file is the *why*, so edits stay principled. Companion: `DESIGN.md` (the concrete
tokens/components).

## 1. Refactoring UI — the "amateur" tells, and their fixes
- Hierarchy via **color/weight, not font size**. De-emphasize with a lighter gray, not smaller text.
- **Whitespace is a feature**, not a gap. Start generous, remove as needed.
- **Separate with shadow/background/spacing, not borders everywhere.** Hairline borders only.
- One **single locked accent**; never a second decorative hue. Semantic state colors
  (done/wip/wait) are separate and encode meaning, not decoration.
- Don't put plain gray text on a colored background — tint the gray toward the bg hue.

## 2. Gestalt / cognitive
- **Proximity**: related items close, unrelated apart. (Heading sits closer to its content
  than to the previous section — Aurora uses a 2:1 gap ratio.)
- **F/Z reading pattern**: most important content top-left / top. Aurora puts highlights +
  AI insights at the very top (the "act first" zone).
- **Hick** (fewer choices), **Fitts** (bigger/closer targets), **Miller** (~7±2 at once).

## 3. Tailwind = numeric design data
- **8pt spacing grid**: all spacing/radii on multiples of 4 (4/8/12/16/24/32/40/48). Misaligned
  modules read as messy.
- **Color scales 50→950**: pick shades from a scale, never eyeball a hex. Accent = Tailwind
  indigo; state palette = emerald / amber / rose.
- Two typefaces, two jobs: a sans for prose, a mono for numbers/IDs/timestamps.

## 4. Apple HIG / Google Material
- **Tap targets ≥ 44×44pt (Apple) / 48×48dp (Material).** Aurora summaries are 48px min.
- **Dark mode is not pure black** (Aurora bg ≈ #0a0c11) and text is **not pure white**
  (off-white), to avoid harsh vibration. WCAG AA body contrast ≥ 4.5:1.
- Dark-mode data viz: a dedicated palette, slightly **lower saturation** than light mode.

## 5. 2026 dashboard practice (researched)
- **Decision-first, not a data dump.** Ask "what decision does this support?" before charts.
- **3–5 key metrics read first**, then progressive disclosure (collapsibles / drilldown).
- **~7–8 elements visible at once** to manage cognitive load. (Aurora's example is a *showcase*
  of all components — real dashboards should pick a subset; consider a "lite" preset.)
- **Proactive, not passive**: 2026 dashboards predict / prioritize / recommend → Aurora's
  `insights` component (AI writes the recommendation; the renderer styles it).
- **Glassmorphism needs a contrast safety net**: pair blur with a semi-transparent solid
  tint (10–30%) and keep strong text/icon separation; it's an accessibility requirement.
- **Don't overdesign**: gradients/glow/animation only where they carry meaning. Aurora limits
  glow + gradients to the single accent (+ its same-family partner).

## Content style (mixed language, JP audience)
Short labels / technical terms stay in English (`Features`, `Tests`, `API v2`, `Plan → GA`);
explanatory prose is Japanese (overall summary, to-do/issue detail, insights, settings).

Sources (2026 practice): UXPin Dashboard Design Principles; think.design Do's & Don'ts 2026;
Qodequay Dark-Mode Data Dashboards; "Dark Glassmorphism" (Medium); UX Pilot Glassmorphism;
Ananya Deka, Dark Mode for Data Visualizations.
