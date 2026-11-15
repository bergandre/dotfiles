#!/usr/bin/env python3
"""Build the hover map for a dungeon note.

usage: python3 -I interactive_map.py "<Dungeon>" [--slug SLUG]

Reads Wow_FOREVER/dungeons/<Dungeon>/<Dungeon>.md: `## Bosses` (cards), `### Inside` under `## Quests`
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
    sec = note.split("## Bosses", 1)[1].split("\n## ", 1)[0]
    bosses = []
    for blk in re.split(r"\n### ", "\n" + sec)[1:]:
        head, *lines = blk.strip().splitlines()
        m = re.match(r"(?:(\d+)\.\s*)?(.+?)(?:\s+—\s+(\d+))?(\s*\(.*\))?\s*$", head)
        num, name, lvl, tag = m.group(1), m.group(2).strip(), m.group(3), (m.group(4) or "").strip()
        mech, loot = [], []
        for l in lines:
            l = l.strip()
            lm = re.match(r"- \[[ x]\] ([WP]) — !\[\[([^|\]]+)\|inline\]\] \[\[([^\]|]+)(?:\|[^\]]+)?\]\](?: — (.*))?", l)
            if lm:
                loot.append(dict(who=lm.group(1), icon=lm.group(2), item=lm.group(3), why=lm.group(4) or ""))
            elif l.startswith("- "):
                mech.append(l[2:])
        bosses.append(dict(num=num, name=name, lvl=lvl, tag=tag, mech=mech, loot=loot))
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


def item_quality(item):
    f = VAULT / "items" / f"{item}.md"
    m = re.search(r"\[!wow\|(\w+)\]", f.read_text()) if f.exists() else None
    return m.group(1) if m else "rare"


def item_tip(item, icon_uri):
    """Item tooltip HTML from the item's card note (callout lines -> <br> lines)."""
    f = VAULT / "items" / f"{item}.md"
    if not f.exists():
        return ""
    q = item_quality(item)
    lines = [l[2:] if l.startswith("> ") else l[1:] for l in f.read_text().splitlines() if l.startswith(">")]
    body = [l for l in lines[1:] if not l.startswith("![[") and not l.startswith("[Wowhead]")]
    return (f'<span class="wm-tip"><img class="wm-tip-icon" src="{icon_uri}">'
            f'<span class="wm-q-{q} wm-tip-name">{html.escape(item)}</span><br>' + "<br>".join(body) + "</span>")


def card(b, icons):
    h = [f'<span class="wm-title">{html.escape(b["name"])}</span>']
    sub = " ".join(x for x in (f'Level {b["lvl"]}' if b["lvl"] else "", b["tag"]) if x)
    if sub:
        h.append(f'<span class="wm-sub">{html.escape(sub)}</span>')
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
    a = ap.parse_args()
    slug = a.slug or re.sub(r"[^a-z0-9]+", "-", a.dungeon.lower().replace("'", "")).strip("-")
    main_note = VAULT / "dungeons" / a.dungeon / f"{a.dungeon}.md"  # one folder per dungeon
    note = main_note.read_text()
    bosses = parse_bosses(note)
    extra = frontmatter(note).get("pins") or []

    page = get(f"{SITE}/dungeons/{slug}")
    pins = {n: (float(x), float(y)) for x, y, n in re.findall(
        r'class="dgx-pin[^"]*" style="left:([\d.]+)%;top:([\d.]+)%" aria-label="([^"]+)"', page)}
    faces = {n: f for f, n in re.findall(r'/wow-ui/bosses/(\d+)\.webp\)[^>]*></span><span[^>]*>([^<]+)</span>', page)}
    guess = set()
    for p in extra:
        if p.get("kind", "quest") == "boss":
            pins[p["name"]] = (float(p["x"]), float(p["y"]))
            if p.get("guess"):
                guess.add(p["name"])
    map_url = SITE + re.search(r'(/dungeons/maps/[^"\')\s]+\.(?:webp|png|jpg))', page).group(1)

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
        for it in b["loot"]:
            p = VAULT / "items" / "icons" / it["icon"]
            if p.exists() and it["icon"] not in icons:
                icons[it["icon"]] = data_uri(p.read_bytes(), "jpeg", 85, "36x36")

    out = ['<div class="wowmap">', f'<img class="wm-map" src="{data_uri(get(map_url, binary=True), "jpeg", 78)}">']
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
            out.append(f'<div class="{cls}" tabindex="0" style="left:{x}%;top:{y}%">'
                       f'<img class="wm-face" src="{face(b["name"])}"><b class="wm-num">{b["num"] or ""}</b>'
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
            inner = f'<img class="wm-face" src="{fc}">' if fc else f'<b class="wm-num">{html.escape(b["name"][:1])}</b>'
            out.append(f'<div class="wm-pin wm-inline" tabindex="0">{inner}<span class="wm-label">{html.escape(b["name"])}</span>'
                       f'<div class="wm-card">{card(b, icons)}</div></div>')
        out.append("</div>")

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
