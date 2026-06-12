# LLM Skills

A collection of portable, **drop-in addons** for LLM-driven agent setups. Each addon is
self-contained — download the folder, follow its `README.md`, and use it immediately.
No framework lock-in; the runtime code is plain and dependency-light.

## Addons

| Addon | What it does | Runtime deps |
|-------|--------------|--------------|
| [`aurora`](./aurora) | Turn one compact `STATE` into a stylish project dashboard — rendered to a self-contained **local HTML** page and/or a **Notion** page. Rich component library (KPI ring, AI insights, highlights, bar/line charts, sliders, a styled clickable pipeline, milestones…) plus a bundled **design dataset** so any LLM produces deliberate, non-amateur output. | Python stdlib only (+ a headless Chrome/Edge for the Notion hero image) |

## How to use an addon

```bash
git clone https://github.com/ryozo74/LLM_skills.git
cd LLM_skills/aurora
cat README.md   # each addon documents its own setup
```

Each addon ships with:
- `SKILL.md` — a manifest so agent runtimes (e.g. Claude Code) can discover/trigger it
- `README.md` — quick start + customization
- the engine/scripts, an example config, and the design knowledge it relies on

## Design philosophy

- **Portable**: copy the folder into any project; no central install.
- **LLM-free at runtime where possible**: the LLM authors the *data/config*; the addon's
  engine is deterministic code. This keeps cost down and behavior reproducible — the LLM
  only writes the small data delta, while the renderer (the "下地") owns all markup,
  styling, charts, and interactivity.
- **Knowledge included, not just code**: where an addon depends on design/domain taste,
  that knowledge is written down (e.g. `aurora/design_dataset.md`) so any model — local or
  hosted — can reproduce the result.
