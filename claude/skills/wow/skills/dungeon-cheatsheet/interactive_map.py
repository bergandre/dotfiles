#!/usr/bin/env python3
"""Build the hover map for a dungeon note.

usage: python3 -I interactive_map.py "<Dungeon>" [--slug SLUG]

Dungeon folder layout: <Dungeon>/<Dungeon>.md (main note: TLDR, map embed, frontmatter pins/route/map),
map/ (<Dungeon> map data.md = boss/trash source, map image, the generated (interactive).md), notes/
(<Dungeon> quests.md, <Dungeon> loot.md), art/.
Reads map/<Dungeon> map data.md (boss sections: TLDR line, ability icons - red border = ej-important,
role badges; `## Pulls` kill order; `## Trash` mob lines; legacy name <Dungeon> tactics.md), the W/P upgrade
lines in it (boss cards: loot) and the main note's frontmatter `pins:` (quest pins with
their text, extra/override boss pins). Boss pins + portraits + clean map come from foreverchanges.pro.
Writes map/<Dungeon> (interactive).md (one HTML block, images inlined as data: URIs) and makes the main
note's `## Map` embed it.
Styles: .wowmap rules in gaming/.obsidian/snippets/wow.css.

frontmatter pins (x/y = % of the map image):
  pins:
    - {kind: quest, name: Blueleaf Tubers, x: 43, y: 54, guess: true,
       text: ["Dig 6 Blueleaf Tubers (snuffling snout)", "→ Mebok Mizzyrix, Ratchet: Rogue's Pants"]}
    - {kind: boss, name: Aggem Thorncurse, x: 70, y: 50, guess: true}   # adds/moves a boss pin
`text` = the quest pin card lines (string or list): objective, turn-in, reward. Without it,
older notes: `match` (default: name) picks the quest's lines from `### Inside`.
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
    """Boss sections of the map data (`## N. Name — lvl (tag)`, `> **TLDR:**` line,
    `- ![[icon|inline]] [[Ability]]` lines, loot checkboxes); old notes: `### ` under `## Bosses`."""
    if "[!boss]" in note:
        blocks = [b for b in re.split(r"\n## ", "\n" + note)[1:] if "[!boss]" in b or b.startswith("Trash")]
    else:
        sec = note.split("## Bosses", 1)[1].split("\n## ", 1)[0]
        blocks = re.split(r"\n### ", "\n" + sec)[1:]
    bosses = []
    for blk in blocks:
        head, *lines = blk.strip().splitlines()
        if head.startswith("Trash") and "[!boss]" in note:
            bosses += parse_trash(lines)
            continue
        m = re.match(r"(?:(\d+)\.\s*)?(.+?)(?:\s+—\s+(\d+))?(\s*\(.*\))?\s*$", head)
        num, name, lvl, tag = m.group(1), m.group(2).strip(), m.group(3), (m.group(4) or "").strip()
        mech, loot, abil, roles, sub, role = [], [], [], [], "", None
        for l in lines:
            l = l.strip()
            rm = re.match(r"> > \[!(tank|healer|dps)\]", l)
            if rm:
                role = rm.group(1)
            elif role and l.startswith("> > - "):
                roles.append((role, l[6:]))
            elif l.startswith("> [!boss]"):
                sub = l[len("> [!boss]"):].strip()
            lm = re.match(r"- \[[ x]\] ([WP]) — !\[\[([^|\]]+)\|inline\]\] \[\[([^\]|]+)(?:\|[^\]]+)?\]\](?: — (.*))?", l)
            am = re.match(r"- !\[\[([^|\]]+)\|inline\]\] \[\[([^\]|]+)\]\]", l)
            if lm:
                loot.append(dict(who=lm.group(1), icon=lm.group(2), item=lm.group(3), why=lm.group(4) or ""))
            elif l.startswith("> **TLDR:**"):
                mech.append(l[len("> **TLDR:**"):].strip())
            elif am and "[!boss]" in blk:
                abil.append(dict(icon=am.group(1), name=am.group(2), imp="ej-important" in l,
                                 roles=[r for r in ROLES if f"ej-{r}.png" in l], raw=l[2:]))
            elif l.startswith("- ") and "[!boss]" not in blk:
                mech.append(re.sub(r"!\[\[[^\]]+\]\]\s*|\[\[|\]\]|\*\*", "", l[2:]))
        bosses.append(dict(num=num, name=name, lvl=lvl, tag=tag, mech=mech, loot=loot, abil=abil, roles=roles, sub=sub))
    return bosses


ROLES = ("tank", "healer", "dps")  # ej-<role> flag on an ability line = who must react (journal convention)


ABIL = r"!\[\[([^|\]]+)\|inline\]\] \[\[([^\]|]+)\]\]"


def parse_trash(lines):
    """`## Trash` of the map data -> one banner per mob line (`- [ej-important] **Mob** — point, point → do`),
    dangerous ones (ej-important) first, plus a "Trash loot" chip for the W/P loot lines."""
    mobs, loot, rest = [], [], []
    for l in (l.strip() for l in lines):
        mm = re.match(r"- (.*?)\*\*([^*]+)\*\*\s*—\s*(.*)", l)
        lm = re.match(r"- (?:\[[ x]\] )?([WP]) — !\[\[([^|\]]+)\|inline\]\] \[\[([^\]|]+)(?:\|[^\]]+)?\]\](?: — (.*))?", l)
        if mm:
            imp = "ej-important" in mm.group(1)
            abil = [dict(icon=i, name=n) for i, n in re.findall(ABIL, mm.group(3)) if not i.startswith("ej-")]
            text = re.sub(r"\s*!\[\[[^\]]+\]\]\s*", " ", mm.group(3)).replace("[[", "").replace("]]", "")
            mobs.append(dict(num=None, name=mm.group(2).strip(), lvl=None, tag="dangerous trash" if imp else "trash", raw=mm.group(3),
                             mech=[re.sub(r"\s+([,.])", r"\1", re.sub(r"\s+", " ", text)).strip()], loot=[], abil=abil, trash=True, imp=imp))
        elif lm:
            loot.append(dict(who=lm.group(1), icon=lm.group(2), item=lm.group(3), why=lm.group(4) or ""))
    mobs.sort(key=lambda m: not m["imp"])
    if loot:
        mobs.append(dict(num=None, name="Trash loot", lvl=None, tag="BoE, random", mech=rest, loot=loot, abil=[]))
    return mobs


def method_art(folder, name):
    """art/method/<tile>.jpg (tactics.py) for a mob/boss name: the tile sharing the most words
    ("Dragonmaw Warder" -> "Dragonmaw Saboteur and Dragonmaw Warder"; plural s ignored)."""
    words = lambda t: {w.rstrip("s") for w in re.findall(r"[a-z']+", t.lower())} - {"and", "the", "of"}
    want, best, top = words(name), None, 0
    for f in (folder / "art" / "method").glob("*.jpg"):
        n = len(want & words(f.stem))
        if n > top:
            best, top = f, n
    return best if best and top >= min(2, len(want)) else None


def md_inline(t, icons, flags):
    """Note text -> HTML: `![[ej-x.png|inline]]` -> flag icon, `![[icon|inline]] [[Ability]]` -> hover icon + name
    (role flags right after it -> corner badges); the text between is escaped (names like Death's stay raw)."""
    out = []
    for tok in re.split(r"(!\[\[[^\]]+\]\](?: \[\[[^\]]+\]\])?)", t):
        fm, am = re.fullmatch(r"!\[\[ej-([a-z]+)\.png\|inline\]\]", tok), re.fullmatch(ABIL, tok)
        if fm:
            out.append(f'<img class="wm-flag" src="{flags.get(fm.group(1), "")}">')
        elif am:
            ic = icons.get(am.group(1), "")
            out.append(f'<span class="wm-ab" tabindex="0"><img src="{ic}">'
                       f'{item_tip(am.group(2), ic, "abilities")}</span> {html.escape(am.group(2))}')
        else:
            out.append(html.escape(tok))
    return "".join(out)


def mob_points(raw, icons, flags):
    """Mob line text -> ([point html], [(role, action html)]): points split on ", " before the "→", actions
    on ";" after it (leading ej-<role> flag = the role's icon), abilities as hover icons."""
    fmt = lambda t: md_inline(t, icons, flags)
    what, _, do = raw.partition("→")
    pts = [fmt(x.strip()) for x in re.split(r",\s+|;\s+", what) if x.strip()]
    acts = []  # [(role or "", html)] - "→ ![[ej-tank.png|inline]] pull one at a time; ![[ej-healer.png|inline]] ..."
    for x in (x.strip() for x in do.split(";") if x.strip()):
        m = re.match(r"!\[\[ej-(tank|healer|dps)\.png\|inline\]\]\s*(.*)", x)
        acts.append((m.group(1), fmt(m.group(2))) if m else ("", fmt(x)))
    return pts, acts


LOOT = re.compile(r"- (?:\[[ x]\] )?([WP]) — !\[\[([^|\]]+)\|inline\]\] \[\[([^\]|]+)(?:\|[^\]]+)?\]\](?: — (.*))?")


def lkey(name):
    return re.sub(r"[^a-z]", "", name.lower())


def parse_loot(path):
    """W/P upgrade lines per `## ` section of the map data -> {boss key | "trash": [loot dicts]}."""
    out, cur = {}, None
    for l in (path.read_text().splitlines() if path.exists() else []):
        if l.startswith("## "):
            h = re.sub(r"^\d+\.\s*", "", l[3:])
            cur = "trash" if h.startswith("Trash") else lkey(re.split(r"\s+—\s+|\s+\(", h)[0])
        elif cur and (m := LOOT.match(l.strip())):
            out.setdefault(cur, []).append(dict(who=m.group(1), icon=m.group(2), item=m.group(3), why=m.group(4) or ""))
    return out


def kill_order(text):
    """Numbered lines of `## Pulls — kill order` (bold markers stripped)."""
    m = re.search(r"\n## Pulls[^\n]*\n(.*?)(?=\n## |\Z)", text, re.S)
    return [re.sub(r"\*\*", "", x) for x in re.findall(r"^\d+\.\s+(.*)$", m.group(1), re.M)] if m else []


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
    text = pin.get("text")
    if text:  # objective / turn-in / reward lines written on the pin itself
        hits = [str(t) for t in (text if isinstance(text, list) else [text])]
    else:     # older notes: lines from `### Inside`
        key = str(pin.get("match") or pin["name"]).lower()
        hits = [l for l in lines if key in l.lower()]
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


def role_badges(roles, icons):
    """Shield / cross / sword in the icon's corner (like method.gg and the Dungeon Journal)."""
    return "".join(f'<img class="wm-role wm-role-{r}" src="{icons.get("ej-" + r, "")}">' for r in roles or [])


def card(b, icons):
    h = [f'<span class="wm-title">{html.escape(b["name"])}</span>']
    sub = " ".join(x for x in (f'Level {b["lvl"]}' if b["lvl"] else "", b["tag"]) if x)
    if sub:
        h.append(f'<span class="wm-sub">{html.escape(sub)}</span>')
    if b.get("abil"):
        h.append('<span class="wm-abil">' + "".join(
            f'<span class="wm-ab{" wm-imp" if a.get("imp") else ""}" tabindex="0"><span class="wm-abi">'
            f'<img src="{icons.get(a["icon"], "")}">{role_badges(a.get("roles"), icons)}</span>'
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
    ddir = VAULT / "dungeons" / a.dungeon                     # one folder per dungeon
    main_note = ddir / f"{a.dungeon}.md"
    note = main_note.read_text()
    data = next((f for f in (ddir / "map" / f"{a.dungeon} map data.md", ddir / f"{a.dungeon} tactics.md")
                 if f.exists()), None)
    data_text = data.read_text() if data else note
    bosses = parse_bosses(data_text)
    trash = [b for b in bosses if b.get("trash")]
    bosses = [b for b in bosses if not b.get("trash") and b["name"] != "Trash loot"]
    loot = parse_loot(data) if data else {}  # W/P upgrade lines under each boss / `## Trash` of the map data
    for b in bosses:
        b["loot"] = loot.get(lkey(b["name"]), b["loot"])
    if loot.get("trash"):
        bosses.append(dict(num=None, name="Trash loot", lvl=None, tag="BoE, random", mech=[], loot=loot["trash"], abil=[]))
    order = kill_order(data_text)
    fm = frontmatter(note)
    extra = fm.get("pins") or []
    local_map = next((f for f in (ddir / str(fm["map"]), ddir / "map" / str(fm["map"])) if f.exists()),
                     None) if fm.get("map") else None  # e.g. stitched floors

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
        if not fid:  # no site portrait (Forever-only dungeon) -> method.gg render, if tactics.py saved one
            f = method_art(main_note.parent, name)
            return data_uri(f.read_bytes(), "jpeg", 85, "96x96") if f else ""
        f = CACHE / f"{fid}.webp"
        if not f.exists():
            f.write_bytes(get(f"{SITE}/wow-ui/bosses/{fid}.webp", binary=True))
        return data_uri(f.read_bytes(), "webp", 85, "64x64")

    icons = {}
    inline = [dict(icon=i) for i, _ in re.findall(ABIL, data_text)]  # icons used in any text (kill order, role lines)
    for b in bosses + trash + [dict(loot=[], abil=inline)]:
        for it in b["loot"] + b["abil"]:
            p = next((d / "icons" / it["icon"] for d in (VAULT / "items", VAULT / "abilities")
                      if (d / "icons" / it["icon"]).exists()), None)
            if p and it["icon"] not in icons:
                icons[it["icon"]] = data_uri(p.read_bytes(), "jpeg", 85, "36x36")

    for r in ROLES:
        f = VAULT / "abilities" / "icons" / f"ej-{r}.png"
        if f.exists():
            icons["ej-" + r] = data_uri(f.read_bytes(), "png", 85, "28x28")

    map_raw = local_map.read_bytes() if local_map else get(map_url, binary=True)
    # click a boss pin -> jump to its banner: data-wm-jump / data-wm-id, handled by the vault plugin
    # .obsidian/plugins/wowmap-jump (notes can't run scripts; Obsidian eats plain #id clicks on images)
    anchor = lambda name: f"wm-{slug}-{re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')}"
    has_banner = {b["name"] for b in bosses if b.get("roles") or b.get("abil")}
    out = [f'<div class="wowmap" id="wm-{slug}-map" data-wm-id="wm-{slug}-map">', f'<img class="wm-map" src="{data_uri(map_raw, "jpeg", 78)}">']
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
            mark = f'{img}<b class="wm-num">{b["num"] or ""}</b>'
            if b["name"] in has_banner:
                mark = f'<a class="wm-jump" href="#{anchor(b["name"])}" data-wm-jump="{anchor(b["name"])}">{mark}</a>'
            out.append(f'<div class="{cls}" tabindex="0" style="left:{x}%;top:{y}%">{mark}'
                       f'<div class="wm-card">{c}</div></div>')
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
            badge = "!" if b.get("imp") else b["name"][:1]
            inner = f'<img class="wm-face" src="{fc}">' if fc else f'<b class="wm-num">{html.escape(badge)}</b>'
            kind = (" wm-trash" if b.get("trash") else "") + (" wm-danger" if b.get("imp") else "")
            out.append(f'<div class="wm-pin wm-inline{kind}" tabindex="0">{inner}<span class="wm-label">{html.escape(b["name"])}</span>'
                       f'<div class="wm-card">{card(b, icons)}</div></div>')
        out.append("</div>")

    flags = {f.stem[3:]: data_uri(f.read_bytes(), "png", 85, "28x28")
             for f in (VAULT / "abilities" / "icons").glob("ej-*.png")}
    if any(b.get("roles") or b.get("abil") for b in bosses):  # boss banners: same look as the trash ones
        out.append('<div class="wm-sect">Bosses</div><div class="wm-mobs wm-bosses">')
        for b in bosses:
            if not (b.get("roles") or b.get("abil")):
                continue
            f = method_art(main_note.parent, b["name"])
            src = data_uri(f.read_bytes(), "jpeg", 82, "112x112") if f else face(b["name"])
            img = (f'<span class="wm-mob-facebox">{f'<img class="wm-mob-face" src="{src}">' if src else ""}'
                   f'<b class="wm-num">{b["num"] or ""}</b></span>')
            lvl = f' <span class="wm-mob-lvl">{b["lvl"]}</span>' if b["lvl"] else ""
            tag = f' <span class="wm-mob-lvl">{html.escape(b["tag"])}</span>' if b["tag"] else ""
            body = [f'<span class="wm-mob-name">{html.escape(b["name"])}{lvl}{tag}</span>']
            if b.get("sub"):
                body.append(f'<span class="wm-mob-sub">{md_inline(b["sub"], icons, flags)}</span>')
            body += [f'<span class="wm-run"><b>TLDR:</b> {html.escape(m)}</span>' for m in b["mech"][:1]]
            for ab in b["abil"]:
                ic = icons.get(ab["icon"], "")
                name, _, eff = re.sub(ABIL, "", ab["raw"], count=1).partition("—")
                body.append(f'<span class="wm-pt wm-abl"><span class="wm-ab{" wm-imp" if ab["imp"] else ""}" tabindex="0"><span class="wm-abi"><img src="{ic}">'
                            f'{role_badges(ab["roles"], icons)}</span>{item_tip(ab["name"], ic, "abilities")}</span> '
                            f'<b>{html.escape(re.sub(r" [(]\d+[)]$", "", ab["name"]))}</b>'
                            f'{md_inline(re.sub(r"!\[\[ej-(tank|healer|dps)\.png\|inline\]\]", "", name), icons, flags)}'
                            f'{" — " + md_inline(eff.strip(), icons, flags) if eff.strip() else ""}</span>')
            body += [f'<span class="wm-do wm-do-{r}"><img class="wm-roleb" src="{flags.get(r, "")}">'
                     f'{md_inline(t, icons, flags)}</span>' for r, t in b["roles"]]
            out.append(f'<div class="wm-mob wm-boss" id="{anchor(b["name"])}" data-wm-id="{anchor(b["name"])}">{img}<div class="wm-mob-body">{"".join(body)}'
                       f'</div><a class="wm-up-map" href="#wm-{slug}-map" data-wm-jump="wm-{slug}-map" title="back to the map">↑ map</a></div>')
        out.append("</div>")
    if trash:  # trash banners: portrait, name, danger points, what to do
        out.append('<div class="wm-sect">Trash</div>')
        if order:  # `## Pulls — kill order` of the map data: one numbered row above the banners
            out.append('<div class="wm-order"><b>Kill order</b>' + "".join(
                f'<span class="wm-ord"><i>{i}</i>{md_inline(t, icons, flags)}</span>' for i, t in enumerate(order, 1)) + "</div>")
        out.append('<div class="wm-mobs">')
        for m in trash:
            f = method_art(main_note.parent, m["name"])
            img = f'<img class="wm-mob-face" src="{data_uri(f.read_bytes(), "jpeg", 82, "112x112")}">' if f else ""
            pts, acts = mob_points(m["raw"], icons, flags)
            # plain spans, not <ul>: Obsidian restyles lists (markers, indents) inside notes
            lis = "".join(f'<span class="wm-pt">{p}</span>' for p in pts) + "".join(
                f'<span class="wm-do wm-do-{r}"><img class="wm-roleb" src="{flags.get(r, "")}">{t}</span>' if r
                else f'<span class="wm-do">{t}</span>' for r, t in acts)
            out.append(f'<div class="wm-mob{" wm-danger" if m["imp"] else ""}">{img}<div class="wm-mob-body">'
                       f'<span class="wm-mob-name">{html.escape(m["name"])}</span>{lis}</div></div>')
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

    target = ddir / "map" / f"{a.dungeon} (interactive).md"
    target.parent.mkdir(exist_ok=True)
    target.write_text("".join(out) + "\n")  # no title: the note is embedded at the top of the main note
    print(f"{target}  ({target.stat().st_size // 1024} KB, {len(bosses)} bosses, {len(strip)} without pin, "
          f"{sum(1 for p in extra if p.get('kind', 'quest') == 'quest')} quest pins)")

    # main note: `## Map` embeds the interactive note (replaces the old static PNG embed)
    embed = f"![[{target.stem}]]"
    if embed not in note:
        new = re.sub(r"(## Map\n)!\[\[[^\]]+ map\.png\]\]", lambda m: m.group(1) + embed, note, count=1)
        if new == note:  # no `## Map` yet: put it before `## Loot` / `## Notes`, else at the end
            head = next((h for h in ("\n## Loot", "\n## Notes", "\n## Bosses") if h in note), None)
            new = note.replace(head, f"\n## Map\n{embed}\n{head}", 1) if head else note.rstrip() + f"\n\n## Map\n{embed}\n"
        main_note.write_text(new)
        print(f"{main_note.name}: ## Map now embeds {embed}")


if __name__ == "__main__":
    main()
