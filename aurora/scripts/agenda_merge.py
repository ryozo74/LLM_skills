#!/usr/bin/env python3
"""agenda_merge.py — Stitch several self-contained HTML pages into ONE navigable deck.

Adds a **sticky agenda (table of contents)** at the top; clicking an item
**smooth-scrolls** to its section; every section gets a **"▲ Top"** link back up.
Use it to combine multiple `render_local.py` outputs (Status / Brain / Persona ...)
into a single page that works even over file:// (in-page anchors, no cross-file links).

Why a separate step (not inside render_local.py):
  render_local.py owns ONE STATE -> one page. This *composes* N already-rendered
  pages, so each keeps its own STATE/design. Clean separation of concerns.

Usage:
  python3 agenda_merge.py --out deck.html \
      "📊 Status=status.html" "🧠 Brain=brain.html" "🎭 Persona=persona.html"
  # each arg = "<agenda label>=<html file>"  (label first; split on first '=')
  # --title "..."     page <title>
  # --first-title     also show a heading for the 1st section (default: omit,
  #                   since the first page usually carries its own banner)

Gotchas handled (learned the hard way):
  1. Every <style> block is hoisted into the merged <head> (deduped) so no CSS
     leaks into the body as raw text.
  2. <body> is extracted AFTER stripping <style> — a CSS *comment* may contain the
     literal text "<body>" (e.g. "...direct child of <body>..."), which would
     otherwise mis-anchor the body regex and drag head CSS into the page body.
"""
import re
import sys

CSS = """<style>
html{scroll-behavior:smooth}
.agenda{position:sticky;top:0;z-index:99;display:flex;flex-wrap:wrap;gap:8px;align-items:center;
  padding:11px 18px;background:rgba(8,12,20,.86);-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px);
  border-bottom:1px solid rgba(255,255,255,.12)}
.agenda b{color:#8b97a8;font:12px system-ui,sans-serif;margin-right:4px}
.agenda a{padding:6px 14px;border-radius:999px;text-decoration:none;font:14px/1.2 system-ui,sans-serif;
  background:rgba(56,189,248,.13);color:#bae6fd;border:1px solid rgba(56,189,248,.35)}
.agenda a:hover{background:#38bdf8;color:#06121f}
.am-sec{border-top:1px dashed rgba(255,255,255,.08);scroll-margin-top:64px}
.am-ttl{max-width:900px;margin:34px auto 4px;padding:0 20px 0 12px;font:700 22px/1.3 system-ui,sans-serif;
  color:#e5e7eb;border-left:4px solid #38bdf8}
.am-top{display:inline-block;font:13px system-ui,sans-serif;color:#8b97a8;text-decoration:none;
  padding:6px 12px;border-radius:8px;border:1px solid rgba(255,255,255,.18);margin:6px 0 48px}
.am-top:hover{color:#fff;border-color:#38bdf8}
</style>"""


def _styles(h):
    return re.findall(r"<style[^>]*>.*?</style>", h, flags=re.S)


def _body(h):
    h = re.sub(r"<style[^>]*>.*?</style>", "", h, flags=re.S)   # strip styles FIRST (see gotcha #2)
    m = re.search(r"<body[^>]*>(.*?)</body>", h, flags=re.S)
    return (m.group(1).strip() if m else h)


def merge(items, title="Dashboard", first_title=False):
    """items: list of (label, html_path). Returns the combined HTML string."""
    seen, styles = set(), []
    htmls = []
    for label, path in items:
        h = open(path, encoding="utf-8").read()
        htmls.append(h)
        for s in _styles(h):
            if s not in seen:
                seen.add(s)
                styles.append(s)
    head = "".join(styles) + CSS
    agenda = ('<div class="agenda"><b>目次:</b>'
              + "".join(f'<a href="#am-{i}">{lbl}</a>' for i, (lbl, _) in enumerate(items))
              + "</div>")
    back = '<div style="text-align:right"><a href="#am-top" class="am-top">▲ Top</a></div>'
    secs = ""
    for i, ((label, _), h) in enumerate(zip(items, htmls)):
        ttl = "" if (i == 0 and not first_title) else f'<h2 class="am-ttl">{label}</h2>'
        secs += f'<section id="am-{i}" class="am-sec">{ttl}{_body(h)}{back}</section>'
    return ('<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{title}</title>{head}</head>\n'
            f'<body><div id="am-top"></div>\n{agenda}\n{secs}\n</body></html>')


def main(argv):
    out, title, first_title, items = "deck.html", "Dashboard", False, []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--out":
            out = argv[i + 1]; i += 2; continue
        if a == "--title":
            title = argv[i + 1]; i += 2; continue
        if a == "--first-title":
            first_title = True; i += 1; continue
        if "=" in a:
            lbl, p = a.split("=", 1)
            items.append((lbl.strip(), p.strip()))
        i += 1
    if not items:
        print("usage: agenda_merge.py --out deck.html [--title T] [--first-title] 'ラベル=file.html' ...")
        return 1
    open(out, "w", encoding="utf-8").write(merge(items, title=title, first_title=first_title))
    print(f"merged -> {out}  ({len(items)} sections, agenda+smooth-scroll+back-to-top)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
