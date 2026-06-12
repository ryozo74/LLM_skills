# LLM Skills

A collection of portable, **drop-in addons** for LLM-driven agent setups. Each addon is
self-contained — download the folder, follow its `README.md`, and use it immediately.
No framework lock-in; the runtime code is plain and dependency-light.

## Addons

| Addon | What it does | Runtime deps |
|-------|--------------|--------------|
| [`dashboard_notion`](./dashboard_notion) | Render a graphical project dashboard (taste-skill hero image + native Notion blocks) and mirror-sync it into a Notion page. | Python stdlib only + a headless Chrome/Edge |

## How to use an addon

```bash
# grab just one addon folder (sparse checkout), or clone the whole repo
git clone https://github.com/ryozo74/LLM_slills.git
cd LLM_slills/dashboard_notion
cat README.md   # each addon documents its own setup
```

Each addon ships with:
- `SKILL.md` — a manifest so agent runtimes (e.g. Claude Code) can discover/trigger it
- `README.md` — quick start + customization
- the engine/scripts, an example config, and any design knowledge it relies on

## Design philosophy

- **Portable**: copy the folder into any project; no central install.
- **LLM-free at runtime where possible**: the LLM authors the *data/config*; the addon's
  engine is deterministic code. This keeps cost down and behavior reproducible.
- **Knowledge included, not just code**: where an addon depends on design/domain taste
  (e.g. `dashboard_notion/DESIGN.md`), that knowledge is written down so any model —
  local or hosted — can reproduce the result.
