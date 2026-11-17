#!/usr/bin/env python3
"""Build the hover map for a dungeon note.

usage: python3 -I interactive_map.py "<Dungeon>" [--slug SLUG]

Reads Wow_FOREVER/dungeons/<Dungeon>/<Dungeon> tactics.md (boss cards: Run line, ability icons, loot;
falls back to `## Bosses` of the main note) and <Dungeon>.md: `### Inside` under `## Quests`
(quest pin text) and frontmatter `pins:` (extra/override pins). Boss pins + portraits + clean map
come from foreverchanges.pro. Writes <Dungeon> (interactive).md next to it (one HTML
block, images inlined as data: URIs) and makes the main note's `## Map` embed it.
Styles: .wowmap rules in gaming/.obsidian/snippets/wow.css.

frontmatter pins (x/y = % of the map image):
  pins:
    - {kind: quest, name: Blueleaf Tubers, match: Blueleaf Tuber, x: 43, y: 54, guess: true}
    - {kind: boss, name: Aggem Thorncurse, x: 70, y: 50, guess: true}   # adds/moves a boss pin
`match` = text that picks the quest's lines from `### Inside` (default: name).
`guess: true` -> dashed ring + "approx. position" in the card.
frontmatter `map: <file in the dungeon folder>` (multi-floor dungeons: floors stitched into one image)
-> used instead of the site's first floor; site boss pins are then dropped, give every boss a `kind: boss` pin.
frontmatter `route:` = the run path, entrance first, then every turn / boss in kill order (x/y = % of the map):
  route:
    - [50, 95]                          # entrance (green "Start" dot)
    - [48, 70]
    - {x: 30, y: 52, label: drop down}   # optional short label at that point
    - [22, 40]                          # last point = arrow end
Drawn as a dashed red line with direction arrows under the pins. `--preview PNG` writes the map with
route + pin dots burnt in (to Read and check positions).
"""
import argparse
import base64
import html
import re
import subprocess
import urllib.request

import yaml
from pathlib import Path

VAULT = Path("~/Documents/obsidian/gaming/Wow_FOREVER").expanduser()
SITE = "https://foreverchanges.pro"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) wow-cheatsheet"}
CACHE = Path("~/.cache/wow-bosses").expanduser()


def get(url, binary=False):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
        d = r.read()
    return d if binary else d.decode("utf-8", "replace")


def data_uri(raw: bytes, conv: str, quality=80, resize=None):
    """Convert any image bytes to a compact jpg/webp data URI via ImageMagick."""
    cmd = ["magick", "-", "-strip"] + (["-resize", resize] if resize else []) + ["-quality", str(quality), f"{conv}:-"]
    out = subprocess.run(cmd, input=raw, capture_output=True, check=True).stdout
    return f"data:image/{conv};base64,{base64.b64encode(out).decode()}"


def parse_bosses(note: str):
    """Boss sections of `<Dungeon> tactics.md` (`## N. Name — lvl (tag)`, `> **Run:**` line,
    `- ![[icon|inline]] [[Ability]]` lines, loot checkboxes); old notes: `### ` under `## Bosses`."""
    if "[!boss]" in note:
        blocks = [b for b in re.split(r"\n## ", "\n" + note)[1:] if "[!boss]" in b or b.startswith("Trash")]
    else:
        sec = note.split("## Bosses", 1)[1].split("\n## ", 1)[0]
        blocks = re.split(r"\n### ", "\n" + sec)[1:]
    bosses = []
    for blk in blocks:
        head, *lines = blk.strip().splitlines()
        m = re.match(r"(?:(\d+)\.\s*)?(.+?)(?:\s+—\s+(\d+))?(\s*\(.*\))?\s*$", head)
        num, name, lvl, tag = m.group(1), m.group(2).strip(), m.group(3), (m.group(4) or "").strip()
        mech, loot, abil = [], [], []
        for l in lines:
            l = l.strip()
            lm = re.match(r"- \[[ x]\] ([WP]) — !\[\[([^|\]]+)\|inline\]\] \[\[([^\]|]+)(?:\|[^\]]+)?\]\](?: — (.*))?", l)
            am = re.match(r"- !\[\[([^|\]]+)\|inline\]\] \[\[([^\]|]+)\]\]", l)
            if lm:
                loot.append(dict(who=lm.group(1), icon=lm.group(2), item=lm.group(3), why=lm.group(4) or ""))
            elif l.startswith("> **Run:**"):
                mech.append(l[len("> **Run:**"):].strip())
            elif am and "[!boss]" in blk:
                abil.append(dict(icon=am.group(1), name=am.group(2)))
            elif l.startswith("- ") and "[!boss]" not in blk:
                mech.append(re.sub(r"!\[\[[^\]]+\]\]\s*|\[\[|\]\]|\*\*", "", l[2:]))
        bosses.append(dict(num=num, name=name, lvl=lvl, tag=tag, mech=mech, loot=loot, abil=abil))
    return bosses


def frontmatter(note: str):
    m = re.match(r"---\n(.*?)\n---\n", note, re.S)
    return (yaml.safe_load(m.group(1)) or {}) if m else {}


def inside_lines(note: str):
    """Bullets of the `### Inside` subsection of `## Quests` (checkbox prefix removed)."""
    m = re.search(r"\n### Inside[^\n]*\n(.*?)(?=\n#{1,3} |\Z)", note, re.S)
    return [re.sub(r"^- (\[[ x]\] )?", "", l.strip()) for l in (m.group(1).splitlines() if m else [])
            if l.strip().startswith("- ")]


def quest_card(pin, lines):
    h = [f'<span class="wm-title wm-qtitle">{html.escape(pin["name"])}</span>',
         f'<span class="wm-sub">Quest{" · approx. position" if pin.get("guess") else ""}</span>']
    key = str(pin.get("match") or pin["name"]).lower()
    hits = [l for l in lines if key in l.lower()] or [str(pin.get("text", ""))]
    h += [f'<span class="wm-mech">{html.escape(l)}</span>' for l in hits if l]
    return "".join(h)


def item_quality(item, folder="items"):
    f = VAULT / folder / f"{item}.md"
    m = re.search(r"\[!wow\|(\w+)\]", f.read_text()) if f.exists() else None
    return m.group(1) if m else "rare"


def item_tip(item, icon_uri, folder="items"):
    """Tooltip HTML from an item/ability card note (callout lines -> <br> lines)."""
    f = VAULT / folder / f"{item}.md"
    if not f.exists():
        return ""
    q = item_quality(item, folder)
    lines = [l[2:] if l.startswith("> ") else l[1:] for l in f.read_text().splitlines() if l.startswith(">")]
    body = [l for l in lines[1:] if not l.startswith("![[") and not l.startswith("[Wowhead]")]
    return (f'<span class="wm-tip"><img class="wm-tip-icon" src="{icon_uri}">'
            f'<span class="wm-q-{q} wm-tip-name">{html.escape(item)}</span><br>' + "<br>".join(body) + "</span>")


def route_points(fm):
    """frontmatter `route:` -> [(x, y, label)] in % of the map image."""
    pts = []
    for r in fm.get("route") or []:
        if isinstance(r, dict):
            pts.append((float(r["x"]), float(r["y"]), str(r.get("label") or "")))
        else:
            pts.append((float(r[0]), float(r[1]), ""))
    return pts


def route_svg(pts, w, h):
    """Route overlay in map pixel coords (viewBox = image size, so arrows keep their shape)."""
    xy = [(x * w / 100, y * h / 100, lab) for x, y, lab in pts]
    s = max(w, h) / 1000  # line/arrow size relative to the map
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in xy)
    out = [f'<svg class="wm-route" viewBox="0 0 {w} {h}" preserveAspectRatio="none">',
           f'<defs><marker id="wm-arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="3.2" markerHeight="3.2" '
           f'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#e01b1b"/></marker></defs>',
           f'<polyline points="{poly}" fill="none" stroke="#000" stroke-opacity=".55" stroke-width="{7 * s:.1f}" '
           f'stroke-linejoin="round" stroke-linecap="round"/>',
           f'<polyline points="{poly}" fill="none" stroke="#e01b1b" stroke-width="{3.5 * s:.1f}" '
           f'stroke-dasharray="{12 * s:.1f} {7 * s:.1f}" stroke-linejoin="round" stroke-linecap="round" '
           f'marker-mid="url(#wm-arrow)" marker-end="url(#wm-arrow)"/>',
           f'<circle cx="{xy[0][0]:.1f}" cy="{xy[0][1]:.1f}" r="{9 * s:.1f}" fill="#1eff00" stroke="#000" '
           f'stroke-width="{2 * s:.1f}"/>',
           f'<text class="wm-route-label" x="{xy[0][0]:.1f}" y="{xy[0][1] - 14 * s:.1f}" font-size="{20 * s:.1f}" '
           f'text-anchor="middle">Start</text>']
    for x, y, lab in xy[1:]:
        if lab:
            out.append(f'<text class="wm-route-label" x="{x:.1f}" y="{y - 12 * s:.1f}" font-size="{18 * s:.1f}" '
                       f'text-anchor="middle">{html.escape(lab)}</text>')
    out.append("</svg>")
    return "".join(out)


def card(b, icons):
    h = [f'<span class="wm-title">{html.escape(b["name"])}</span>']
    sub = " ".join(x for x in (f'Level {b["lvl"]}' if b["lvl"] else "", b["tag"]) if x)
    if sub:
        h.append(f'<span class="wm-sub">{html.escape(sub)}</span>')
    if b.get("abil"):
        h.append('<span class="wm-abil">' + "".join(
            f'<span class="wm-ab" tabindex="0"><img src="{icons.get(a["icon"], "")}">'
            f'{item_tip(a["name"], icons.get(a["icon"], ""), "abilities")}</span>' for a in b["abil"]) + "</span>")
    for m in b["mech"]:
        h.append(f'<span class="wm-mech">{html.escape(m)}</span>')
    for it in b["loot"]:
        ic = icons.get(it["icon"], "")
        h.append(f'<span class="wm-loot"><b class="wm-who wm-{it["who"]}">{it["who"]}</b>'
                 f'<img src="{ic}"><span class="wm-q-{item_quality(it["item"])}">{html.escape(it["item"])}</span>'
                 f'<span class="wm-why">{html.escape(it["why"])}</span>{item_tip(it["item"], ic)}</span>')
    return "".join(h)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dungeon")
    ap.add_argument("--slug")
    ap.add_argument("--preview", help="also write a PNG with the route and pin dots burnt in (for checking)")
    a = ap.parse_args()
    slug = a.slug or re.sub(r"[^a-z0-9]+", "-", a.dungeon.lower().replace("'", "")).strip("-")
    main_note = VAULT / "dungeons" / a.dungeon / f"{a.dungeon}.md"  # one folder per dungeon
    note = main_note.read_text()
    tactics = main_note.with_name(f"{a.dungeon} tactics.md")
    bosses = parse_bosses(tactics.read_text() if tactics.exists() else note)
    fm = frontmatter(note)
    extra = fm.get("pins") or []
    local_map = main_note.parent / fm["map"] if fm.get("map") else None  # e.g. stitched floors

    try:
        page = get(f"{SITE}/dungeons/{slug}")
    except Exception as e:  # Forever-only dungeons may have no page: needs frontmatter `map:` + boss pins
        if not local_map:
            raise SystemExit(f"{SITE}/dungeons/{slug}: {e} - set `map:` in the main note's frontmatter")
        print(f"{SITE}/dungeons/{slug}: {e} (no portraits)")
        page = ""
    pins = {} if local_map else {n: (float(x), float(y)) for x, y, n in re.findall(
        r'class="dgx-pin[^"]*" style="left:([\d.]+)%;top:([\d.]+)%" aria-label="([^"]+)"', page)}
    faces = {n: f for f, n in re.findall(r'/wow-ui/bosses/(\d+)\.webp\)[^>]*></span><span[^>]*>([^<]+)</span>', page)}
    guess = set()
    for p in extra:
        if p.get("kind", "quest") == "boss":
            pins[p["name"]] = (float(p["x"]), float(p["y"]))
            if p.get("guess"):
                guess.add(p["name"])
    map_url = None if local_map else SITE + re.search(r'(/dungeons/maps/[^"\')\s]+\.(?:webp|png|jpg))', page).group(1)

    CACHE.mkdir(parents=True, exist_ok=True)

    def face(name):
        fid = faces.get(name)
        if not fid:
            return ""
        f = CACHE / f"{fid}.webp"
        if not f.exists():
            f.write_bytes(get(f"{SITE}/wow-ui/bosses/{fid}.webp", binary=True))
        return data_uri(f.read_bytes(), "webp", 85, "64x64")

    icons = {}
    for b in bosses:
        for it in b["loot"] + b["abil"]:
            p = next((d / "icons" / it["icon"] for d in (VAULT / "items", VAULT / "abilities")
                      if (d / "icons" / it["icon"]).exists()), None)
            if p and it["icon"] not in icons:
                icons[it["icon"]] = data_uri(p.read_bytes(), "jpeg", 85, "36x36")

    map_raw = local_map.read_bytes() if local_map else get(map_url, binary=True)
    out = ['<div class="wowmap">', f'<img class="wm-map" src="{data_uri(map_raw, "jpeg", 78)}">']
    route = route_points(fm)
    svg = ""
    if len(route) >= 2:
        w, h = map(int, subprocess.run(["magick", "identify", "-format", "%w %h", "-"], input=map_raw,
                                       capture_output=True, check=True).stdout.split()[:2])
        svg = route_svg(route, w, h)
        out.append(svg)
    else:
        print("WARNING: no `route:` in the main note's frontmatter - the map has no run path")
    def pin_cls(x, y, *more):
        return " ".join(["wm-pin"] + (["wm-left"] if x > 50 else []) + (["wm-up"] if y > 55 else []) + [m for m in more if m])

    strip = []
    for b in bosses:
        if b["name"] in pins:
            x, y = pins[b["name"]]
            cls = pin_cls(x, y, "wm-rare" if "rare" in b["tag"] else "", "wm-guess" if b["name"] in guess else "")
            c = card(b, icons)
            if b["name"] in guess:
                c = c.replace('</span>', ' <i>(approx. position)</i></span>', 1) if "wm-sub" not in c else c.replace(
                    '<span class="wm-sub">', '<span class="wm-sub">approx. position · ', 1)
            fc = face(b["name"])  # no portrait on the site (some rares) -> number badge only
            img = f'<img class="wm-face" src="{fc}">' if fc else ""
            out.append(f'<div class="{cls}" tabindex="0" style="left:{x}%;top:{y}%">{img}'
                       f'<b class="wm-num">{b["num"] or ""}</b><div class="wm-card">{c}</div></div>')
        else:
            strip.append(b)
    lines = inside_lines(note)
    for p in extra:
        if p.get("kind", "quest") != "quest":
            continue
        x, y = float(p["x"]), float(p["y"])
        out.append(f'<div class="{pin_cls(x, y, "wm-quest", "wm-guess" if p.get("guess") else "")}" tabindex="0" '
                   f'style="left:{x}%;top:{y}%"><b class="wm-qmark">!</b>'
                   f'<div class="wm-card">{quest_card(p, lines)}</div></div>')
    out.append("</div>")
    if strip:
        out.append('<div class="wowmap-strip">')
        for b in strip:
            fc = face(b["name"])
            inner = f'<img class="wm-face" src="{fc}">' if fc else f'<b class="wm-num">{html.escape(b["name"][:1])}</b>'
            out.append(f'<div class="wm-pin wm-inline" tabindex="0">{inner}<span class="wm-label">{html.escape(b["name"])}</span>'
                       f'<div class="wm-card">{card(b, icons)}</div></div>')
        out.append("</div>")

    if a.preview:  # route + boss (red) / quest (yellow) dots on a PNG, to Read and check positions
        dots = [(*pins[b["name"]], "#e00") for b in bosses if b["name"] in pins]
        dots += [(float(p["x"]), float(p["y"]), "#fc0") for p in extra if p.get("kind", "quest") == "quest"]
        w, h = map(int, subprocess.run(["magick", "identify", "-format", "%w %h", "-"], input=map_raw,
                                       capture_output=True, check=True).stdout.split()[:2])
        r = max(w, h) / 100
        dot_svg = "".join(f'<circle cx="{x * w / 100:.1f}" cy="{y * h / 100:.1f}" r="{r:.1f}" fill="{c}" '
                          f'stroke="#000" stroke-width="{r / 4:.1f}"/>' for x, y, c in dots)
        over = (svg or f'<svg class="wm-route" viewBox="0 0 {w} {h}"></svg>').replace(
            '<svg class="wm-route"', f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}"', 1)
        over = over.replace("</svg>", dot_svg + "</svg>").replace(
            'class="wm-route-label"', 'fill="#fff" stroke="#000" stroke-width="1" font-family="sans-serif" font-weight="bold"')
        tmp = Path(a.preview).with_suffix(".svg")
        tmp.write_text(over)
        subprocess.run(["magick", "-", "-background", "none", str(tmp), "-composite", a.preview],
                       input=map_raw, check=True)
        tmp.unlink()
        print(f"preview: {a.preview}")

    target = main_note.parent / f"{a.dungeon} (interactive).md"
    target.write_text("".join(out) + "\n")  # no title: the note is embedded at the top of the main note
    print(f"{target}  ({target.stat().st_size // 1024} KB, {len(bosses)} bosses, {len(strip)} without pin, "
          f"{sum(1 for p in extra if p.get('kind', 'quest') == 'quest')} quest pins)")

    # main note: `## Map` embeds the interactive note (replaces the old static PNG embed)
    embed = f"![[{target.stem}]]"
    if embed not in note:
        new = re.sub(r"(## Map\n)!\[\[[^\]]+ map\.png\]\]", lambda m: m.group(1) + embed, note, count=1)
        if new == note:
            new = re.sub(r"(\n## Bosses)", f"\n## Map\n{embed}\n\\1", note, count=1)
        main_note.write_text(new)
        print(f"{main_note.name}: ## Map now embeds {embed}")


if __name__ == "__main__":
    main()
