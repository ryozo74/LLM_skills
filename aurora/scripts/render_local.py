#!/usr/bin/env python3
"""
render_local.py — Render the dashboard to a single self-contained LOCAL HTML page.
NO Notion. NO network calls (except the Mermaid CDN for the flow chart; see --no-cdn).

Same STATE as notion_sync.py drives it, so the two targets stay in sync:
  - notion_sync.py  -> hero image + native Notion blocks (uses Notion API)
  - render_local.py -> one local HTML file you open in a browser (uses nothing)

This is the "design unification" path from DESIGN.md: the whole page is rendered with
one CSS / one accent, so there is no Notion-vs-hero visual seam.

STATE resolution (shared with notion_sync.py):
  --state PATH | $DASHBOARD_STATE | dashboard_state.json next to scripts | EXAMPLE_STATE

Usage:
  python3 render_local.py [--state STATE.json] [--out dashboard_local.html] [--serve [PORT]] [--no-cdn]
"""
import html as _html
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import notion_sync as ns  # reuse STATE loader + EXAMPLE_STATE


# Notion color name -> (bg rgba, border rgba, text hex) on the dark taste-skill surface
COLORS = {
    "green_background":  ("rgba(52,211,153,.13)", "rgba(52,211,153,.34)", "#7ff0c4"),
    "yellow_background": ("rgba(251,191,36,.14)", "rgba(251,191,36,.34)", "#fcd770"),
    "orange_background": ("rgba(251,146,60,.14)", "rgba(251,146,60,.34)", "#fdba74"),
    "red_background":    ("rgba(251,113,133,.13)", "rgba(251,113,133,.34)", "#ffa9b6"),
    "blue_background":   ("rgba(129,140,248,.14)", "rgba(129,140,248,.34)", "#c7cdfb"),
    "purple_background": ("rgba(192,132,252,.14)", "rgba(192,132,252,.34)", "#dcc5fd"),
    "gray_background":   ("rgba(255,255,255,.05)", "rgba(255,255,255,.12)", "#aab2c0"),
    "default":           ("rgba(255,255,255,.05)", "rgba(255,255,255,.12)", "#aab2c0"),
}
# state-bar accent for issues / flow legend
BAR = {"red_background": "var(--wait)", "yellow_background": "var(--wip)",
       "orange_background": "var(--wip)", "green_background": "var(--done)",
       "blue_background": "var(--accent)", "gray_background": "var(--ink3)",
       "default": "var(--ink3)"}


def esc(s):
    return _html.escape(str(s))


def md(s):
    """escape + **bold** -> <strong> + \\n -> <br>."""
    out, i, buf = [], 0, ""
    s = str(s)
    while i < len(s):
        if s.startswith("**", i):
            j = s.find("**", i + 2)
            if j != -1:
                out.append(esc(buf)); buf = ""
                out.append("<strong>" + esc(s[i + 2:j]) + "</strong>")
                i = j + 2
                continue
        buf += s[i]; i += 1
    out.append(esc(buf))
    return "".join(out).replace("\n", "<br>")


def color_of(name):
    return COLORS.get(name, COLORS["default"])


# ---- chart helpers (pure, offline; no JS/CDN) ----
_BARCOL = {"green_background": "var(--done)", "yellow_background": "var(--wip)",
           "orange_background": "var(--wip)", "red_background": "var(--wait)",
           "blue_background": "var(--accent)", "purple_background": "var(--accent2)"}


def _num(x):
    x = float(x)
    return str(int(x)) if x.is_integer() else f"{x:g}"


def _barcol(name):
    return _BARCOL.get(name, "var(--accent)")


def svg_line(pts, W=600, H=150, pad=18):
    """SVG line chart (area + line + dots) from a list of numbers. Scales to width."""
    n = len(pts)
    mn, mx = min(pts), max(pts)
    rng = (mx - mn) or 1.0
    def X(i):
        return pad + (W - 2 * pad) * (i / ((n - 1) or 1))
    def Y(v):
        return pad + (H - 2 * pad) * (1 - (v - mn) / rng)
    poly = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(pts))
    area = (f"M{X(0):.1f},{H - pad:.1f} L"
            + " L".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(pts))
            + f" L{X(n - 1):.1f},{H - pad:.1f} Z")
    dots = "".join(f'<circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="3" class="lc-dot"/>'
                   for i, v in enumerate(pts))
    last = f'<circle cx="{X(n - 1):.1f}" cy="{Y(pts[-1]):.1f}" r="4.5" class="lc-last"/>'
    return (f'<svg class="linechart" viewBox="0 0 {W} {H}" width="100%" height="{H}">'
            '<defs><linearGradient id="lcg" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0" stop-color="var(--accent)" stop-opacity=".35"/>'
            '<stop offset="1" stop-color="var(--accent)" stop-opacity="0"/></linearGradient></defs>'
            f'<path d="{area}" fill="url(#lcg)"/>'
            f'<polyline points="{poly}" fill="none" stroke="var(--accent)" stroke-width="2.5" '
            'stroke-linecap="round" stroke-linejoin="round"/>'
            f'{dots}{last}</svg>')


def parse_pipeline(src):
    """Parse a stage flow into ordered nodes (by definition order). None for graphs
    that aren't a simple stage sequence (subgraphs / explicit branch syntax)."""
    if "subgraph" in src or "-.->" in src or "==>" in src:
        return None
    seen, order = set(), []
    for nid, lab in re.findall(r'(\w+)\["([^"]*)"\]', src):
        if nid not in seen:
            seen.add(nid); order.append((nid, lab))
    if len(order) < 2:
        return None
    states = dict(re.findall(r'(\w+)\["[^"]*"\]:::(\w+)', src))
    out = []
    for nid, lab in order:
        lab = lab.replace("<br/>", " ").strip()
        head, _, rest = lab.partition(" ")
        icon, name = (head, rest) if (rest and not head[:1].isalnum()) else ("", lab)
        out.append({"id": nid, "icon": icon, "name": name, "state": states.get(nid, "done")})
    return out


def build_pipeline(nodes, clickable):
    chips = []
    for nd in nodes:
        click = f' onclick="nodeClick(\'{nd["id"]}\')"' if clickable else ""
        chips.append(
            f'<div class="pl-node {esc(nd["state"])}"{click}>'
            f'<div class="pl-ic">{esc(nd["icon"])}</div>'
            f'<div class="pl-nm">{esc(nd["name"])}</div></div>')
    return '<div class="pl">' + "".join(chips) + '</div>'


def render(state, use_cdn=True):
    banner_text, banner_color = state["title_banner"]
    ov_label, ov_text, ov_color = state["overall"]
    pct = int(state.get("progress_pct", 0))
    # derive a short title + brand mark from the banner (best effort)
    raw = banner_text
    for ch in "🎯📊📈🟢🟡🔴⏸️✅⚪ ":
        raw = raw.lstrip(ch)
    title = raw.split("—")[0].split("/")[0].strip() or "Dashboard"
    mark = title[0].upper() if title else "D"

    P = []  # parts
    A = P.append

    # ---- status cards
    cards = "".join(
        f'<div class="card stat" style="--edge:{BAR.get(c,"var(--ink3)")}">'
        f'<div class="lab">{esc(t)}</div><div class="big">{md(b)}</div></div>'
        for e, t, b, c in state.get("cards", [])
    )

    # ---- flow: custom CSS pipeline (preferred) / Mermaid (branching fallback)
    notes = state.get("flow_notes") or {}
    note_map, use_mermaid, flow = {}, False, ""
    flow_legend = ""
    if state.get("flow"):
        flow_src = state["flow"]
        labels = dict(re.findall(r'(\w+)\["([^"]*)"\]', flow_src))
        for nid, txt in notes.items():
            note_map[nid] = {"label": labels.get(nid, nid).replace("<br/>", " ").strip(), "text": txt}
        pipeline = parse_pipeline(flow_src)
        flow_legend = ('<div class="legend">'
                       '<span><i class="lg" style="background:var(--done)"></i>done</span>'
                       '<span><i class="lg" style="background:var(--wip)"></i>in progress</span>'
                       '<span><i class="lg" style="background:var(--wait)"></i>waiting</span></div>')
        if pipeline:
            flow = build_pipeline(pipeline, clickable=bool(note_map))
        elif use_cdn:
            use_mermaid = True
            clicks = [f'click {nid} nodeClick "{re.sub(chr(92)+"s+", " ", str(t))[:48].replace(chr(34), chr(39))}"'
                      for nid, t in notes.items()]
            if clicks:
                flow_src = flow_src + "\n  " + "\n  ".join(clicks)
            flow = f'<pre class="mermaid">{esc(flow_src)}</pre>'
        else:
            flow = '<pre class="codeflow">' + esc(state["flow"]) + '</pre>'
            flow_legend = '<p class="hint">(--no-cdn: raw flow source)</p>'

    # ---- todos
    todos = "".join(
        f'<div class="row"><div class="chk{" on" if chk else ""}"></div>'
        f'<div class="body"><div class="t">{md(txt)}</div></div></div>'
        for txt, chk in state.get("todos", [])
    )
    # ---- issues
    issues = "".join(
        f'<div class="iss"><div class="bar" style="background:{BAR.get(c,"var(--ink3)")}"></div>'
        f'<div><div class="t">{md(txt)}</div></div></div>'
        for e, txt, c in state.get("issues", [])
    )

    # ---- highlights (featured metric tiles, with delta)
    hi = ""
    for item in state.get("highlights", []):
        icon, label, value = item[0], item[1], item[2]
        delta = str(item[3]) if len(item) > 3 else ""
        dcls = "up" if delta[:1] in "▲+↑" else ("down" if delta[:1] in "▼-↓" else "")
        dh = f'<span class="hl-d {dcls}">{esc(delta)}</span>' if delta else ""
        hi += (f'<div class="hl"><div class="hl-top"><span class="hl-i">{esc(icon)}</span>'
               f'<span class="hl-l">{esc(label)}</span></div>'
               f'<div class="hl-v">{esc(value)}{dh}</div></div>')

    # ---- insights (AI proactive recommendations: [icon, text, tone?])
    insights = ""
    for item in state.get("insights", []):
        icon, text = item[0], item[1]
        bg, bd, tx = color_of(item[2] if len(item) > 2 else "blue_background")
        insights += (f'<div class="ins"><div class="ins-ic" style="background:{bg};'
                     f'border-color:{bd};color:{tx}">{esc(icon)}</div>'
                     f'<div class="ins-t">{md(text)}</div></div>')

    # ---- bars (horizontal bar chart: [label, val] or [label, val, max, color])
    bars = ""
    for row in state.get("bars", []):
        label, val = row[0], float(row[1])
        mx = float(row[2]) if len(row) > 2 else 100.0
        w = max(0.0, min(100.0, val / mx * 100 if mx else 0))
        bars += (f'<div class="bar-row"><div class="bar-h"><span>{esc(label)}</span>'
                 f'<b>{esc(_num(val))}</b></div><div class="bar-tr">'
                 f'<div class="bar-fl" style="width:{w:.1f}%;background:{_barcol(row[3] if len(row)>3 else "blue_background")}"></div></div></div>')

    # ---- trend (SVG line chart) {"points":[...], "labels":[...]}
    trend = ""
    td = state.get("trend") or {}
    pts = [float(x) for x in td.get("points", [])]
    if pts:
        trend = svg_line(pts)

    # ---- meters / sliders: [label, val, min, max, unit?]
    meters = ""
    for row in state.get("meters", []):
        label, val = row[0], float(row[1])
        lo = float(row[2]) if len(row) > 2 else 0.0
        up = float(row[3]) if len(row) > 3 else 100.0
        unit = row[4] if len(row) > 4 else ""
        p = max(0.0, min(100.0, (val - lo) / (up - lo) * 100)) if up > lo else 0.0
        meters += (f'<div class="mt"><div class="mt-h"><span>{esc(label)}</span>'
                   f'<b>{esc(_num(val))}{esc(unit)}</b></div>'
                   f'<div class="mt-tr"><div class="mt-fl" style="width:{p:.1f}%"></div>'
                   f'<div class="mt-knob" style="left:{p:.1f}%"></div></div>'
                   f'<div class="mt-mm"><span>{esc(_num(lo))}{esc(unit)}</span>'
                   f'<span>{esc(_num(up))}{esc(unit)}</span></div></div>')

    # ---- milestones (skip header row)
    mrows = state.get("milestones", [])
    ms = ""
    if mrows:
        body = mrows[1:] if len(mrows) > 1 else mrows
        ms = "".join(
            f'<div class="ms"><div class="rg">{esc(r[0])}</div>'
            f'<div class="tt">{esc(r[1]) if len(r)>1 else ""}</div>'
            f'<div class="ds">{esc(r[2]) if len(r)>2 else ""}</div></div>'
            for r in body
        )

    def details(title_txt, items):
        if not items:
            return ""
        lis = "".join(f"<li>{md(s)}</li>" for s in items)
        return (f'<details class="det"><summary>{esc(title_txt)}</summary>'
                f'<ul>{lis}</ul></details>')

    bbg, bbd, btx = color_of(banner_color)
    obg, obd, otx = color_of(ov_color)

    A(f'''<div class="poster">
  <div class="top">
    <div class="brand"><div class="mark">{esc(mark)}</div>
      <div><h1>{esc(title)}</h1><p>Local Dashboard</p></div></div>
    <div class="topright">
      <span class="pill" style="background:{obg};border-color:{obd};color:{otx}">
        <span class="dot"></span>{esc(ov_label)}</span>
      <div class="synced">RENDERED {esc(time.strftime("%Y-%m-%d %H:%M:%S"))}</div>
    </div>
  </div>

  <div class="banner" style="background:{bbg};border-color:{bbd};color:{btx}">{md(banner_text)}</div>
  <div class="overall">{md(ov_text)}</div>

  <div class="kpi">
    <div class="card ring-card">
      <div class="ring" style="--p:{pct}"><b>{pct}%</b></div>
      <div class="meta"><h3>Overall progress</h3><p>{md(ov_label)}</p></div>
    </div>
    <div class="stats">{cards}</div>
  </div>''')

    if hi:
        A(f'<div class="h"><i></i>{esc(state.get("highlights_heading","Highlights"))}</div>'
          f'<div class="highlights">{hi}</div>')

    if insights:
        A(f'<div class="h"><i></i>{esc(state.get("insights_heading","Insights"))}'
          f'<span class="ai-badge">AI</span></div>'
          f'<div class="panel insights-p">{insights}</div>')

    mcols = []
    if bars:
        mcols.append(f'<div><div class="h"><i></i>{esc(state.get("bars_heading","Breakdown"))}</div>'
                     f'<div class="panel bars">{bars}</div></div>')
    if trend:
        lbls = td.get("labels", [])
        lab = ('<div class="lc-labels">' + "".join(f"<span>{esc(l)}</span>" for l in lbls)
               + '</div>') if lbls else ""
        mcols.append(f'<div><div class="h"><i></i>{esc(state.get("trend_heading","Trend"))}</div>'
                     f'<div class="panel chartp">{trend}{lab}</div></div>')
    if mcols:
        A(f'<div class="cols">{"".join(mcols)}</div>')

    if meters:
        A(f'<div class="h"><i></i>{esc(state.get("meters_heading","Metrics"))}</div>'
          f'<div class="panel meters-p">{meters}</div>')

    if flow:
        detail = ('<div class="flowdetail" id="flowDetail"><span class="fd-hint">'
                  '👆 ノードをクリックすると、ここに説明が表示されます</span></div>') if note_map else ""
        A(f'<div class="h"><i></i>{esc(state.get("flow_heading","Project flow"))}</div>'
          f'<div class="flowbox">{flow}</div>{flow_legend}{detail}')

    A(f'''<div class="cols">
    <div><div class="h"><i></i>{esc(state.get("todos_heading","Work list"))}</div>
      <div class="panel">{todos}</div></div>
    <div><div class="h"><i></i>{esc(state.get("issues_heading","Issues / blockers"))}</div>
      <div class="panel">{issues}</div></div>
  </div>''')

    if ms:
        A(f'<div class="h"><i></i>{esc(state.get("milestones_heading","Milestones"))}</div>'
          f'<div class="mile">{ms}</div>')

    extra = (details(state.get("settings_heading", "Settings"), state.get("settings"))
             + details(state.get("refs_heading", "References"), state.get("refs")))
    if extra:
        A(f'<div class="extra">{extra}</div>')

    A(f'<div class="foot"><span>{esc(title)} / local render</span>'
      f'<span class="mono">source: STATE (no Notion)</span></div></div>')

    tail = ""
    if note_map:                       # inline detail panel (works for pipeline AND mermaid)
        tail += ('<script>'
                 f'const FLOW_NOTES={json.dumps(note_map, ensure_ascii=False)};'
                 'window.nodeClick=function(id){var n=FLOW_NOTES[id];if(!n)return;'
                 'var el=document.getElementById("flowDetail");if(!el)return;'
                 'el.classList.add("active");el.innerHTML="";'
                 'var h=document.createElement("h5");h.textContent=n.label||id;'
                 'var p=document.createElement("p");p.textContent=n.text||"";'
                 'el.appendChild(h);el.appendChild(p);};</script>')
    if use_mermaid:
        tail += ('<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>'
                 '<script>mermaid.initialize({startOnLoad:true,securityLevel:"loose",theme:"dark",'
                 'themeVariables:{fontFamily:"Outfit,sans-serif"}});</script>')

    return PAGE.format(accent="#818cf8", body="\n".join(P), mermaid=tail,
                       caption=esc(state.get("hero_caption", "Project dashboard")))


PAGE = """<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{caption}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
<style>
  /* Premium dark glass. Principles kept: 8pt grid, single accent(+gradient pair),
     AA contrast, no pure black, 48px tap targets. */
  :root{{
    --bg:#0a0c11; --bg2:#0e1118;
    --line:rgba(255,255,255,.08); --line2:rgba(255,255,255,.15);
    --ink:#eef0f7; --ink2:#b0b8c8; --ink3:#8b93a3;
    --accent:{accent}; --accent2:#a78bfa; --glow:rgba(129,140,248,.5);
    --done:#34d399; --wip:#fbbf24; --wait:#fb7185; --r:18px;
    --card:linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.018));
    --elev:0 1px 0 rgba(255,255,255,.07) inset, 0 24px 50px -28px rgba(0,0,0,.92);
    --blur:saturate(1.2) blur(16px);
    --font:'Outfit','Yu Gothic UI','Yu Gothic','Meiryo',sans-serif;
    --mono:'JetBrains Mono','Outfit',monospace;
  }}
  *{{box-sizing:border-box;margin:0;padding:0}}
  html,body{{min-height:100vh;color:var(--ink);font-family:var(--font);
    background:
      radial-gradient(960px 560px at 88% -12%, rgba(129,140,248,.26), transparent 56%),
      radial-gradient(760px 520px at -10% 4%, rgba(167,139,250,.16), transparent 52%),
      radial-gradient(920px 640px at 50% 124%, rgba(52,211,153,.11), transparent 56%),
      linear-gradient(180deg,var(--bg),var(--bg2)) fixed}}
  .poster{{position:relative;max-width:1200px;margin:0 auto;padding:48px 28px 56px}}
  .poster::before{{content:"";position:fixed;inset:0;z-index:-1;pointer-events:none;opacity:.45;
    background-image:radial-gradient(rgba(255,255,255,.05) 1px, transparent 1px);background-size:34px 34px;
    -webkit-mask-image:radial-gradient(1200px 760px at 50% 0%, #000, transparent 78%);
    mask-image:radial-gradient(1200px 760px at 50% 0%, #000, transparent 78%)}}
  .card,.panel,.flowbox,.ms,.flowdetail,.det{{background:var(--card);border:1px solid var(--line);
    box-shadow:var(--elev);-webkit-backdrop-filter:var(--blur);backdrop-filter:var(--blur)}}
  .stat,.ms{{transition:transform .16s ease, box-shadow .16s ease}}
  .stat:hover,.ms:hover{{transform:translateY(-3px);box-shadow:0 1px 0 rgba(255,255,255,.1) inset,0 28px 56px -26px rgba(0,0,0,.95)}}
  .top{{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;flex-wrap:wrap;padding-bottom:24px;border-bottom:1px solid var(--line)}}
  .brand{{display:flex;align-items:center;gap:16px}}
  .mark{{width:56px;height:56px;border-radius:18px;background:linear-gradient(145deg,var(--accent),var(--accent2));
    display:grid;place-items:center;font-weight:800;font-size:27px;color:#0b0c10;
    box-shadow:0 12px 32px -6px var(--glow), 0 1px 0 rgba(255,255,255,.35) inset}}
  .brand h1{{font-size:33px;font-weight:800;letter-spacing:-.025em;line-height:1;
    background:linear-gradient(180deg,#fff,#bfc5df);-webkit-background-clip:text;background-clip:text;color:transparent}}
  .brand p{{font-size:11px;color:var(--ink3);margin-top:8px;letter-spacing:.2em;text-transform:uppercase}}
  .topright{{text-align:right}}
  .pill{{display:inline-flex;align-items:center;gap:8px;padding:9px 16px;border-radius:999px;border:1px solid;font-weight:600;font-size:14px}}
  .dot{{width:8px;height:8px;border-radius:50%;background:currentColor;box-shadow:0 0 10px currentColor}}
  .synced{{font-size:12px;color:var(--ink3);margin-top:10px;font-family:var(--mono);letter-spacing:.03em}}
  .banner{{margin-top:26px;padding:18px 22px;border:1px solid;border-radius:14px;font-size:19px;font-weight:700;letter-spacing:-.01em}}
  .overall{{margin-top:14px;color:var(--ink2);font-size:14px;line-height:1.7;max-width:82ch}}
  .kpi{{display:grid;grid-template-columns:340px 1fr;gap:18px;margin-top:26px}}
  .card{{border-radius:var(--r)}}
  .ring-card{{padding:28px;display:flex;align-items:center;gap:26px}}
  .ring{{width:132px;height:132px;border-radius:50%;flex:none;position:relative;
    background:conic-gradient(from -90deg, var(--accent), var(--accent2) calc(var(--p)*1%), rgba(255,255,255,.06) 0);
    filter:drop-shadow(0 0 22px var(--glow));display:grid;place-items:center}}
  .ring::after{{content:"";position:absolute;inset:13px;border-radius:50%;background:#11141c}}
  .ring b{{position:relative;z-index:1;font-size:36px;font-weight:800;font-family:var(--mono);letter-spacing:-.02em}}
  .ring-card .meta h3{{font-size:11px;color:var(--ink3);font-weight:700;letter-spacing:.12em;text-transform:uppercase}}
  .ring-card .meta p{{font-size:19px;font-weight:700;margin-top:10px;line-height:1.4}}
  .stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px}}
  .stat{{padding:22px;position:relative;overflow:hidden;border-radius:var(--r)}}
  .stat::before{{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:linear-gradient(180deg,var(--edge),transparent)}}
  .stat::after{{content:"";position:absolute;right:-30px;top:-30px;width:90px;height:90px;border-radius:50%;background:radial-gradient(circle,var(--edge),transparent 70%);opacity:.12}}
  .stat .lab{{font-size:11px;color:var(--ink3);font-weight:700;text-transform:uppercase;letter-spacing:.07em}}
  .stat .big{{font-size:26px;font-weight:800;margin-top:10px;line-height:1.2}}
  .h{{display:flex;align-items:center;gap:12px;margin:38px 0 16px;font-size:14px;font-weight:700;color:var(--ink2);letter-spacing:.01em}}
  .h i{{width:20px;height:3px;border-radius:3px;background:linear-gradient(90deg,var(--accent),var(--accent2))}}
  .flowbox{{border-radius:var(--r);padding:30px 26px;overflow:auto}}
  .flowbox .mermaid{{display:flex;justify-content:center;background:none}}
  /* custom pipeline */
  .pl{{display:flex;align-items:flex-start;min-width:560px}}
  .pl-node{{flex:1;position:relative;display:flex;flex-direction:column;align-items:center;text-align:center;cursor:pointer;padding:0 4px;transition:transform .15s ease}}
  .pl-node:hover{{transform:translateY(-3px)}}
  .pl-ic{{width:54px;height:54px;border-radius:16px;display:grid;place-items:center;font-size:23px;border:1.5px solid;margin-bottom:11px;position:relative;z-index:1;background:var(--card)}}
  .pl-nm{{font-size:12.5px;color:var(--ink2);font-weight:600;line-height:1.3;max-width:120px}}
  .pl-node:not(:last-child)::after{{content:"";position:absolute;top:27px;left:calc(50% + 35px);right:calc(-50% + 35px);height:2px;background:var(--line2);border-radius:2px;z-index:0}}
  .pl-node.done .pl-ic{{border-color:var(--done);color:#7ff0c4;box-shadow:0 0 18px -4px rgba(52,211,153,.55)}}
  .pl-node.done:not(:last-child)::after{{background:linear-gradient(90deg,var(--done),var(--done))}}
  .pl-node.wip .pl-ic{{border-color:var(--wip);color:#fcd770;box-shadow:0 0 0 5px rgba(251,191,36,.12),0 0 22px -2px rgba(251,191,36,.6)}}
  .pl-node.wip:not(:last-child)::after{{background:linear-gradient(90deg,var(--wip),var(--wait))}}
  .pl-node.wait .pl-ic{{border-color:var(--wait);color:#ffa9b6;border-style:dashed;opacity:.92}}
  .pl-node.wait .pl-nm{{color:var(--ink3)}}
  .flowbox .clickable,.flowbox .node{{cursor:pointer}}
  .flowbox .clickable:hover{{filter:brightness(1.16)}}
  .flowdetail{{margin-top:16px;border-left:3px solid var(--accent);border-radius:14px;padding:16px 20px;min-height:56px;transition:.15s}}
  .flowdetail .fd-hint{{color:var(--ink3);font-size:13px}}
  .flowdetail h5{{font-size:16px;font-weight:700;margin-bottom:8px}}
  .flowdetail p{{color:var(--ink2);font-size:14px;line-height:1.7}}
  .codeflow{{font-family:var(--mono);font-size:12px;color:var(--ink2);white-space:pre-wrap}}
  .legend{{display:flex;gap:20px;margin:16px 4px 0;font-size:12px;color:var(--ink3)}}
  .legend span{{display:inline-flex;align-items:center;gap:8px}}
  .lg{{width:10px;height:10px;border-radius:3px}}
  .hint{{font-size:12px;color:var(--ink3);margin:8px 2px}}
  .cols{{display:grid;grid-template-columns:1fr 1fr;gap:16px;align-items:start}}
  @media(max-width:760px){{.cols,.kpi{{grid-template-columns:1fr}}}}
  .panel{{border-radius:var(--r);padding:8px 22px 16px}}
  .row,.iss{{display:flex;gap:12px;padding:16px 0;border-bottom:1px solid var(--line)}}
  .row:last-child,.iss:last-child{{border-bottom:0}}
  .chk{{width:20px;height:20px;border-radius:7px;border:1.5px solid var(--line2);flex:none;margin-top:1px}}
  .chk.on{{background:linear-gradient(145deg,var(--done),#10b981);border-color:transparent;box-shadow:0 0 12px rgba(52,211,153,.5)}}
  .row .t{{font-size:15px;font-weight:600;line-height:1.45}}
  .iss .bar{{width:4px;border-radius:3px;flex:none;box-shadow:0 0 10px currentColor}}
  .iss .t{{font-size:14px;font-weight:600;line-height:1.45}}
  .mile{{display:grid;grid-template-columns:repeat(auto-fit,minmax(168px,1fr));gap:16px}}
  .ms{{border-radius:16px;padding:18px;position:relative;overflow:hidden}}
  .ms::before{{content:"";position:absolute;left:0;right:0;top:0;height:2px;background:linear-gradient(90deg,var(--accent),transparent)}}
  .ms .rg{{font-family:var(--mono);font-size:12px;color:var(--accent);font-weight:700;letter-spacing:.02em}}
  .ms .tt{{font-size:14px;font-weight:700;margin-top:8px}}
  .ms .ds{{font-size:12px;color:var(--ink3);margin-top:4px;line-height:1.45}}
  .extra{{margin-top:32px;display:flex;flex-direction:column;gap:12px}}
  .det{{border-radius:14px;padding:0 22px}}
  .det summary{{display:flex;align-items:center;min-height:48px;cursor:pointer;font-weight:700;color:var(--ink2);font-size:15px;list-style:none}}
  .det summary::-webkit-details-marker{{display:none}}
  .det summary::before{{content:"▸";margin-right:10px;color:var(--accent);transition:transform .15s}}
  .det[open] summary::before{{transform:rotate(90deg)}}
  .det ul{{margin:0 0 16px 22px;color:var(--ink2);font-size:14px;line-height:1.8}}
  .foot{{display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-top:36px;padding-top:20px;border-top:1px solid var(--line);font-size:12px;color:var(--ink3)}}
  .foot .mono{{font-family:var(--mono)}}
  /* insights (AI) */
  .ai-badge{{font-size:9.5px;font-weight:800;letter-spacing:.09em;color:#0b0c10;background:linear-gradient(90deg,var(--accent),var(--accent2));padding:3px 8px;border-radius:6px;box-shadow:0 0 14px -2px var(--glow)}}
  .insights-p{{padding:6px 22px 8px;position:relative;overflow:hidden}}
  .insights-p::before{{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:linear-gradient(180deg,var(--accent),var(--accent2))}}
  .ins{{display:flex;gap:14px;align-items:flex-start;padding:15px 0;border-bottom:1px solid var(--line)}}
  .ins:last-child{{border-bottom:0}}
  .ins-ic{{width:36px;height:36px;border-radius:11px;display:grid;place-items:center;font-size:17px;border:1px solid;flex:none}}
  .ins-t{{font-size:14px;color:var(--ink);line-height:1.6;font-weight:500;padding-top:7px}}
  /* highlights */
  .highlights{{display:grid;grid-template-columns:repeat(auto-fit,minmax(196px,1fr));gap:16px}}
  .hl{{background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:20px 22px;box-shadow:var(--elev);position:relative;overflow:hidden;transition:transform .16s ease}}
  .hl:hover{{transform:translateY(-3px)}}
  .hl::after{{content:"";position:absolute;right:-26px;top:-26px;width:84px;height:84px;border-radius:50%;background:radial-gradient(circle,var(--glow),transparent 70%);opacity:.55}}
  .hl-top{{display:flex;align-items:center;gap:9px}}
  .hl-i{{font-size:18px}}
  .hl-l{{font-size:11px;color:var(--ink3);font-weight:700;text-transform:uppercase;letter-spacing:.07em}}
  .hl-v{{font-size:30px;font-weight:800;margin-top:12px;font-family:var(--mono);letter-spacing:-.02em;display:flex;align-items:baseline;gap:10px}}
  .hl-d{{font-size:13px;font-weight:700;font-family:var(--font)}}
  .hl-d.up{{color:var(--done)}} .hl-d.down{{color:var(--wait)}}
  /* bars */
  .bars,.meters-p,.chartp{{padding:18px 22px}}
  .bar-row{{margin:15px 0}} .bar-row:first-child{{margin-top:6px}}
  .bar-h{{display:flex;justify-content:space-between;font-size:13px;color:var(--ink2);margin-bottom:7px}}
  .bar-h b{{font-family:var(--mono);color:var(--ink)}}
  .bar-tr{{height:9px;background:rgba(255,255,255,.06);border-radius:99px;overflow:hidden}}
  .bar-fl{{height:100%;border-radius:99px;box-shadow:0 0 10px rgba(129,140,248,.45)}}
  /* line chart */
  .linechart{{display:block;width:100%;height:auto}}
  .lc-dot{{fill:var(--accent);opacity:.5}}
  .lc-last{{fill:#fff;stroke:var(--accent);stroke-width:2}}
  .lc-labels{{display:flex;justify-content:space-between;margin-top:10px;font-size:11px;color:var(--ink3);font-family:var(--mono)}}
  /* meters / sliders */
  .mt{{margin:18px 0}} .mt:first-child{{margin-top:6px}}
  .mt-h{{display:flex;justify-content:space-between;font-size:13px;color:var(--ink2);margin-bottom:11px}}
  .mt-h b{{font-family:var(--mono);color:var(--ink)}}
  .mt-tr{{position:relative;height:6px;background:rgba(255,255,255,.08);border-radius:99px}}
  .mt-fl{{position:absolute;left:0;top:0;height:100%;border-radius:99px;background:linear-gradient(90deg,var(--accent),var(--accent2))}}
  .mt-knob{{position:absolute;top:50%;width:16px;height:16px;border-radius:50%;background:#fff;border:3px solid var(--accent);transform:translate(-50%,-50%);box-shadow:0 0 12px var(--glow)}}
  .mt-mm{{display:flex;justify-content:space-between;margin-top:8px;font-size:11px;color:var(--ink3);font-family:var(--mono)}}
</style></head>
<body>
{body}
{mermaid}
</body></html>
"""


def main():
    argv = sys.argv
    state = ns.load_state(argv)
    out = argv[argv.index("--out") + 1] if "--out" in argv else os.path.join(HERE, "dashboard_local.html")
    use_cdn = "--no-cdn" not in argv
    doc = render(state, use_cdn=use_cdn)
    with open(out, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"✅ local dashboard -> {out}  ({len(doc)//1024} KB)")
    print(f"   open: file://{os.path.abspath(out)}")

    if "--serve" in argv:
        import http.server, socketserver, functools
        i = argv.index("--serve")
        port = int(argv[i + 1]) if i + 1 < len(argv) and argv[i + 1].isdigit() else 8088
        root = os.path.dirname(os.path.abspath(out))
        name = os.path.basename(out)
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=root)
        with socketserver.TCPServer(("127.0.0.1", port), handler) as httpd:
            print(f"   serving at http://127.0.0.1:{port}/{name}  (Ctrl-C to stop)")
            httpd.serve_forever()


if __name__ == "__main__":
    main()
