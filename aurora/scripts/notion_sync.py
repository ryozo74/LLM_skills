#!/usr/bin/env python3
"""
notion_sync.py — Render a graphical project dashboard and mirror it into a Notion page.

PART OF THE `aurora` ADDON. Vendor- and project-agnostic.

Design principles:
  - Zero dependencies (Python standard library / urllib only). Runs anywhere
    `python3` exists. No `pip install`, no notion-client.
  - Single source of truth = a STATE dict (data only). The SAME STATE feeds:
      ① a graphical "hero" image (HTML rendered to PNG by a headless browser)
      ② native Notion blocks (callouts / columns / mermaid / to-do / table / toggles)
  - Mirror sync: the page body is rebuilt every run (old blocks DELETE -> new append),
    so any upstream chat history (Discord etc.) can be cleared freely — the dashboard
    is the durable record.
  - LLM-free at runtime. An LLM (local or hosted) is only useful UPSTREAM, to author
    or update STATE / the HTML. The pipeline itself is deterministic code.

STATE resolution (first hit wins):
  1. --state PATH        (explicit JSON file)
  2. $DASHBOARD_STATE    (env var path to a JSON file)
  3. dashboard_state.json next to this script
  4. EXAMPLE_STATE       (built-in demo, bottom of file)

Hero HTML resolution:
  --html PATH | $DASHBOARD_HTML | dashboard.html next to this script

Auth (env or `notion.env` discovered next to script / parent / CWD):
  NOTION_API_TOKEN, NOTION_DASHBOARD_PAGE_ID

Usage:
  python3 notion_sync.py [--dry-run] [--no-image] [--state STATE.json] [--html HERO.html]
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

NOTION_VERSION = "2022-06-28"
API = "https://api.notion.com/v1"
HERE = os.path.dirname(os.path.abspath(__file__))


# ============================================================ env / HTTP infra
def load_env():
    for base in (HERE, os.path.dirname(HERE), os.getcwd()):
        path = os.path.join(base, "notion.env")
        if os.path.isfile(path):
            for raw in open(path, encoding="utf-8"):
                line = raw.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            break
    token = os.environ.get("NOTION_API_TOKEN")
    page = os.environ.get("NOTION_DASHBOARD_PAGE_ID")
    if not token or not page:
        sys.exit("ERROR: NOTION_API_TOKEN / NOTION_DASHBOARD_PAGE_ID not set "
                 "(env or notion.env).")
    return token, page.replace("-", "")


class NotionError(Exception):
    pass


def api(method, path, token, body=None):
    url = path if path.startswith("http") else API + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Notion-Version", NOTION_VERSION)
    req.add_header("Content-Type", "application/json")
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = resp.read().decode("utf-8")
                return json.loads(payload) if payload else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            if exc.code == 429 and attempt < 3:
                time.sleep(float(exc.headers.get("Retry-After", "1")) + 0.5)
                continue
            raise NotionError(f"{method} {path} -> HTTP {exc.code}\n{detail}") from None
        except urllib.error.URLError as exc:
            if attempt < 3:
                time.sleep(1.0 + attempt)
                continue
            raise NotionError(f"{method} {path} -> network error: {exc.reason}") from None
    raise NotionError(f"{method} {path} -> retries exhausted")


# ============================================================ rich text
def _chunks(text):
    text = str(text).replace("\r", "")
    while len(text) > 1900:
        yield text[:1900]
        text = text[1900:]
    yield text


def raw_rich(text):
    """Plain rich_text with no markdown parsing (mermaid / code)."""
    return [{"type": "text", "text": {"content": c}} for c in _chunks(text)] or \
           [{"type": "text", "text": {"content": ""}}]


def rich(text):
    """Lightweight rich_text: converts `**bold**` to bold runs."""
    out, buf, i = [], "", 0
    def flush(s, bold):
        for c in _chunks(s):
            out.append({"type": "text", "text": {"content": c},
                        "annotations": {"bold": bold}})
    text = str(text)
    while i < len(text):
        if text.startswith("**", i):
            j = text.find("**", i + 2)
            if j != -1:
                if buf:
                    flush(buf, False); buf = ""
                flush(text[i + 2:j], True)
                i = j + 2
                continue
        buf += text[i]; i += 1
    if buf:
        flush(buf, False)
    return out or [{"type": "text", "text": {"content": ""}}]


# ============================================================ block builders
def paragraph(text, color="default"):
    return {"type": "paragraph", "paragraph": {"rich_text": rich(text), "color": color}}


def heading(level, text, color="default", toggle=False, children=None):
    key = f"heading_{level}"
    blk = {"type": key, key: {"rich_text": rich(text), "color": color,
                              "is_toggleable": toggle}}
    if children:
        blk["_children"] = children
    return blk


def callout(text, emoji="💡", color="gray_background"):
    return {"type": "callout", "callout": {
        "rich_text": rich(text),
        "icon": {"type": "emoji", "emoji": emoji},
        "color": color}}


def todo(text, checked=False, color="default"):
    return {"type": "to_do", "to_do": {"rich_text": rich(text),
                                       "checked": checked, "color": color}}


def bullet(text, color="default"):
    return {"type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": rich(text), "color": color}}


def divider():
    return {"type": "divider", "divider": {}}


def code(text, language="plain text"):
    return {"type": "code", "code": {"rich_text": raw_rich(text), "language": language}}


def columns(col_block_lists):
    """[[blocks...], [blocks...], ...] -> column_list. Inline children per column."""
    cols = [{"type": "column", "column": {"children": blocks}}
            for blocks in col_block_lists]
    return {"type": "column_list", "column_list": {"children": cols}}


def table(rows, has_header=True):
    width = max(len(r) for r in rows)
    children = []
    for r in rows:
        cells = list(r) + [""] * (width - len(r))
        children.append({"type": "table_row",
                         "table_row": {"cells": [rich(c) for c in cells]}})
    return {"type": "table", "table": {"table_width": width,
            "has_column_header": has_header, "has_row_header": False,
            "children": children}}


def progress_bar(pct, width=12):
    filled = round(pct / 100 * width)
    return "█" * filled + "░" * (width - filled) + f"  {pct}%"


# ============================================================ push to Notion
def clear_page(page_id, token):
    removed, cursor = 0, None
    while True:
        q = f"/blocks/{page_id}/children?page_size=100" + (f"&start_cursor={cursor}" if cursor else "")
        res = api("GET", q, token)
        for blk in res.get("results", []):
            api("DELETE", f"/blocks/{blk['id']}", token)
            removed += 1
        if res.get("has_more"):
            cursor = res.get("next_cursor")
        else:
            return removed


def append_children(parent_id, blocks, token):
    """_children appended via a separate PATCH (avoids deep-nesting limits).
    table / column_list native children stay inline."""
    if not blocks:
        return
    deferred, payload = [], []
    for blk in blocks:
        kids = blk.pop("_children", None)
        if kids:
            deferred.append((len(payload), kids))
        payload.append(dict(blk))
    created = []
    for start in range(0, len(payload), 100):
        res = api("PATCH", f"/blocks/{parent_id}/children", token,
                  {"children": payload[start:start + 100]})
        created.extend(res.get("results", []))
    for idx, kids in deferred:
        if idx < len(created):
            append_children(created[idx]["id"], kids, token)


# ============================================================ graphical hero image
CHROME_CANDIDATES = [
    "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe",
    "/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    "/mnt/c/Program Files/Microsoft/Edge/Application/msedge.exe",
    "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


def _wsl_to_win(path):
    parts = path.split("/")            # /mnt/h/foo -> H:\foo
    if len(parts) > 3 and parts[1] == "mnt":
        return f"{parts[2].upper()}:\\" + "\\".join(parts[3:])
    return path


def render_png(html_path, png_path):
    """Render the hero HTML to PNG via a headless Chrome/Edge.
    On WSL, a Windows Chrome/Edge is preferred (native CJK fonts -> no tofu).
    Returns png_path on success, else existing png_path, else None."""
    import subprocess
    chrome = next((c for c in CHROME_CANDIDATES if os.path.isfile(c)), None)
    if not (os.path.isfile(html_path) and chrome):
        return png_path if os.path.isfile(png_path) else None
    is_win = chrome.endswith(".exe")
    if is_win:
        url = "file:///" + _wsl_to_win(html_path).replace("\\", "/")
        out = _wsl_to_win(png_path)
    else:
        url = "file://" + html_path
        out = png_path
    try:
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
                        "--no-first-run", "--hide-scrollbars",
                        "--force-device-scale-factor=2", "--window-size=1200,1422",
                        "--virtual-time-budget=5000",
                        f"--screenshot={out}", url],
                       timeout=90, capture_output=True)
    except Exception as exc:
        print(f"  (render skipped: {exc})")
    return png_path if os.path.isfile(png_path) else None


def upload_image(path, token):
    """Notion File Upload API (3-step) -> returns file_upload id."""
    import uuid
    up = api("POST", "/file_uploads", token, {})
    fb = open(path, "rb").read()
    boundary = "----nsync" + uuid.uuid4().hex
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
            f"filename=\"dashboard.png\"\r\nContent-Type: image/png\r\n\r\n").encode() + fb + \
           f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(up["upload_url"], data=body, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Notion-Version", NOTION_VERSION)
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    with urllib.request.urlopen(req, timeout=60) as resp:
        res = json.loads(resp.read())
    if res.get("status") != "uploaded":
        raise NotionError(f"file upload status={res.get('status')}")
    return up["id"]


def image_block(file_upload_id, caption=""):
    img = {"type": "file_upload", "file_upload": {"id": file_upload_id}}
    if caption:
        img["caption"] = rich(caption)
    return {"type": "image", "image": img}


# ============================================================ build native blocks
def build_blocks(state):
    blocks = []
    # ─ ① banner + sync time + progress bar
    banner, bcolor = state["title_banner"]
    blocks.append(callout(banner, "🎯", bcolor))
    blocks.append(paragraph(f"🔄 last sync: {time.strftime('%Y-%m-%d %H:%M:%S')}", "gray"))
    ov_label, ov_text, ov_color = state["overall"]
    blocks.append(callout(f"**{ov_label}** — {ov_text}", "📊", ov_color))
    blocks.append(callout(f"progress  {progress_bar(state['progress_pct'])}", "📈", "blue_background"))

    # ─ ② status cards (4-col)
    blocks.append(heading(2, state.get("cards_heading", "📌 Status"), "blue"))
    blocks.append(columns([[callout(f"**{title}**\n{body}", emoji, color)]
                           for emoji, title, body, color in state["cards"]]))

    # ─ ③ flow chart (mermaid)
    blocks.append(heading(2, state.get("flow_heading", "🗺️ Flow"), "blue"))
    blocks.append(code(state["flow"], "mermaid"))

    # ─ ④ work list
    blocks.append(heading(2, state.get("todos_heading", "📝 Work list"), "blue"))
    for text, checked in state["todos"]:
        blocks.append(todo(text, checked))

    # ─ ⑤ issues / blockers
    blocks.append(heading(2, state.get("issues_heading", "🚨 Issues / blockers"), "blue"))
    for emoji, text, color in state["issues"]:
        blocks.append(callout(text, emoji, color))

    blocks.append(divider())

    # ─ ⑥ collapsibles (details)
    if state.get("milestones"):
        blocks.append(heading(2, state.get("milestones_heading", "✅ Milestones"), "green",
                              toggle=True, children=[table(state["milestones"])]))
    if state.get("settings"):
        blocks.append(heading(2, state.get("settings_heading", "⚙️ Settings"), "default",
                              toggle=True, children=[bullet(s) for s in state["settings"]]))
    if state.get("refs"):
        blocks.append(heading(2, state.get("refs_heading", "📁 References"), "default",
                              toggle=True, children=[bullet(s) for s in state["refs"]]))
    return blocks


# ============================================================ state loading
def load_state(argv):
    path = None
    if "--state" in argv:
        path = argv[argv.index("--state") + 1]
    elif os.environ.get("DASHBOARD_STATE"):
        path = os.environ["DASHBOARD_STATE"]
    elif os.path.isfile(os.path.join(HERE, "dashboard_state.json")):
        path = os.path.join(HERE, "dashboard_state.json")
    if path:
        with open(path, encoding="utf-8") as f:
            print(f"state <- {path}")
            return json.load(f)
    print("state <- built-in EXAMPLE_STATE")
    return EXAMPLE_STATE


def resolve_html(argv):
    if "--html" in argv:
        return argv[argv.index("--html") + 1]
    return os.environ.get("DASHBOARD_HTML") or os.path.join(HERE, "dashboard.html")


def main():
    argv = sys.argv
    dry = "--dry-run" in argv
    state = load_state(argv)
    blocks = build_blocks(state)

    def count(bs):
        n = 0
        for b in bs:
            n += 1
            n += count(b.get("_children", []))
            if b.get("type") == "table":
                n += len(b["table"]["children"])
            if b.get("type") == "column_list":
                for col in b["column_list"]["children"]:
                    n += 1 + len(col["column"]["children"])
        return n

    print(f"built dashboard -> {len(blocks)} top-level, {count(blocks)} blocks total")
    if dry:
        print("--dry-run: not sending to Notion.")
        return

    token, page_id = load_env()
    try:
        if "--no-image" not in argv:
            html = resolve_html(argv)
            png = os.path.join(HERE, "dashboard.png")
            print(f"rendering hero (headless browser) <- {html}")
            png = render_png(html, png)
            if png:
                print(f"  uploading {os.path.basename(png)} ({os.path.getsize(png)//1024} KB) ...")
                fid = upload_image(png, token)
                blocks = [image_block(fid, state.get("hero_caption", "Project dashboard (auto-generated)")),
                          divider()] + blocks
                print("  ✅ hero image ready")
            else:
                print("  (no image: HTML/browser absent -> native blocks only)")
        print("clearing existing page content ...")
        print(f"  removed {clear_page(page_id, token)} old block(s)")
        print("appending content ...")
        append_children(page_id, blocks, token)
        print("✅ Notion sync complete")
        print(f"   page: https://www.notion.so/{page_id}")
    except NotionError as exc:
        print("❌ Notion API error:\n" + str(exc), file=sys.stderr)
        sys.exit(1)


# ============================================================ EXAMPLE STATE (demo)
# Replace via --state STATE.json / $DASHBOARD_STATE / dashboard_state.json.
# See examples/example_state.json for a filled example.
EXAMPLE_STATE = {
    "title_banner": ["🎯 My Project — phase / status one-liner", "blue_background"],
    "overall": ["🟢 On track", "One sentence describing the overall state.", "green_background"],
    "progress_pct": 60,
    "hero_caption": "Project dashboard (auto-generated)",
    "cards_heading": "📌 Status at a glance",
    "cards": [
        ["🟢", "Build", "done\nv1.0", "green_background"],
        ["✅", "Tests", "120 / 0\nGREEN", "green_background"],
        ["🟡", "In progress", "feature-x\nwiring", "yellow_background"],
        ["⏸️", "Server", "stopped\n(offline)", "orange_background"],
    ],
    "flow_heading": "🗺️ Project flow",
    "flow": """flowchart TD
  A[\"Mock\"]:::done --> B[\"Design\"]:::done
  B --> C[\"Build\"]:::done --> D[\"Ship\"]:::wip
  D --> E[\"Prod connect\"]:::wait
  classDef done fill:#a7f3d0,stroke:#059669,color:#064e3b;
  classDef wip fill:#fde68a,stroke:#f59e0b,color:#78350f;
  classDef wait fill:#fecdd3,stroke:#e11d48,color:#881337;""",
    "todos_heading": "📝 Work list",
    "todos": [
        ["**feature-x** — finish wiring", False],
        ["Docs pass", False],
        ["Fix edge-case fallback", False],
    ],
    "issues_heading": "🚨 Issues / blockers",
    "issues": [
        ["🔴", "**External dependency** — waiting on partner team", "red_background"],
        ["🟡", "**Manual QA** — 3 flows to confirm", "yellow_background"],
    ],
    "milestones_heading": "✅ Milestones",
    "milestones": [
        ["Range", "Theme", "Summary"],
        ["v0.1", "Prototype", "first working slice"],
        ["v0.5", "Hardening", "auth / tests / CI"],
        ["v1.0", "Ship", "production cutover"],
    ],
    "settings_heading": "⚙️ Settings",
    "settings": [
        "**Policy 1**: describe an operating policy here.",
        "**Policy 2**: another one.",
    ],
    "refs_heading": "📁 References",
    "refs": [
        "Repo: `path/to/readme.md`",
        "Spec: `docs/spec.md`",
    ],
}


if __name__ == "__main__":
    main()
