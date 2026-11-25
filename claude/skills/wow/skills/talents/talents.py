#!/usr/bin/env python3
"""Talent tree notes with hover cards (same idea as the dungeon interactive map).

usage: python3 -I talents.py <class> <out.md> <title> <build>[:<points>] [<build>[:<points>] ...]

config/<class>.json = the Forever talent grid scraped from method.gg's talent embeds (talent order letter
-> talent, see SKILL.md) + builds (`order` = Method's pick-order string, one letter per point, first point at
level 10). `build:31` renders the first 31 points of that build (level 40). Each build becomes a section with
one HTML block: the three trees on their Wowhead backgrounds, every talent icon with a rank badge, picked
talents in colour, hover card = name, rank, the levels its points are taken, rank-1 tooltip text.
Spell tooltips + icons come from nether.wowhead.com/forever (cached in ~/.cache/wow-talents).
Styles: .wowtal block in gaming/.obsidian/snippets/wow.css.
"""
import base64
import html
import json
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
CACHE = Path("~/.cache/wow-talents").expanduser()
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) wow-talents"}
ALPHA = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
FIRST_LEVEL = 10  # first talent point


def fetch(url, binary=False):
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / re.sub(r"[^\w.]+", "_", url.split("//", 1)[1])
    if not f.exists():
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
            f.write_bytes(r.read())
    return f.read_bytes() if binary else f.read_text(encoding="utf-8")


def data_uri(url, mime="image/jpeg"):
    return f"data:{mime};base64," + base64.b64encode(fetch(url, binary=True)).decode()


def spell(sp):
    j = json.loads(fetch(f"https://nether.wowhead.com/forever/tooltip/spell/{sp}"))
    t = re.sub(r"<!--.*?-->", "", j.get("tooltip", ""), flags=re.S)
    t = re.sub(r"<br\s*/?>|</(?:td|tr|table|div)>", "\n", t)
    lines = [re.sub(r"\s+", " ", l).strip() for l in html.unescape(re.sub(r"<[^>]+>", "", t)).split("\n")]
    keep = []
    for l in lines:
        # requirement lines glue onto the description ("Requires Melee WeaponA vicious strike ...")
        l = re.sub(r"^(Requires (?:Melee Weapon|[A-Z][a-z]+ Stance(?:, [A-Z][a-z]+ Stance)*))(?=[A-Z])", r"\1\n", l)
        for part in l.split("\n"):
            if not part or part.endswith("Talent") or part in ("Requires Warrior",) or part.startswith("Requires level") \
                    or part.startswith("Rank "):
                continue
            part = re.sub(r"(?<=[a-z])(?=Requires )", "\n", part.replace("Requires Warrior", ""))
            for q in part.split("\n"):
                q = re.sub(r"\b0(?:\.0)?% ", "", q.strip())  # unresolved rank values in Wowhead's rank-1 text
                if q:
                    keep.append(q)
    return {"name": j.get("name", str(sp)), "icon": j.get("icon", "inv_misc_questionmark"), "lines": keep}


ABILITIES = Path("~/Documents/obsidian/gaming/Wow_FOREVER/abilities").expanduser()


def card_names():
    """spell id -> ability card note name (gen_abilities.py writes `id:` in the frontmatter)"""
    out = {}
    for f in ABILITIES.glob("*.md"):
        m = re.search(r"^id:\s*(\d+)", f.read_text(encoding="utf-8"), re.M)
        if m:
            out[int(m.group(1))] = f.stem
    return out


def picks(cfg, key, points=None):
    by_did = sorted(cfg["talents"], key=lambda t: t["did"])
    order = cfg["builds"][key]["order"][:points] if points else cfg["builds"][key]["order"]
    seq = [by_did[ALPHA.index(ch)]["spell"] for ch in order]
    levels = {}
    for i, sp in enumerate(seq):
        levels.setdefault(sp, []).append(FIRST_LEVEL + i)
    return Counter(seq), levels, len(seq)


def lv_text(lv):
    """[10, 11, 12, 20] -> '10–12, 20'"""
    out, run = [], [lv[0]]
    for x in lv[1:]:
        if x == run[-1] + 1:
            run.append(x)
        else:
            out.append(run); run = [x]
    out.append(run)
    return ", ".join(f"{r[0]}–{r[-1]}" if len(r) > 1 else str(r[0]) for r in out)


def render(cfg, key, points=None):
    ranks, levels, n = picks(cfg, key, points)
    trees = cfg["trees"]
    spent = [sum(ranks.get(t["spell"], 0) for t in cfg["talents"] if t["tree"] == i) for i in range(len(trees))]
    cards = card_names()
    out = ['<div class="wowtal">']
    for ti, tree in enumerate(trees):
        bg = data_uri(f"https://wow.zamimg.com/images/wow/talents/backgrounds/classic/{tree['bg']}.jpg")
        out.append(f'<div class="wt-tree" style="background-image:url({bg})">'
                   f'<div class="wt-head">{html.escape(tree["name"])} <b>{spent[ti]}</b></div><div class="wt-grid">')
        for t in sorted((t for t in cfg["talents"] if t["tree"] == ti), key=lambda t: (t["tier"], t["col"])):
            s = spell(t["spell"])
            r = ranks.get(t["spell"], 0)
            state = "wt-max" if r == t["max"] else "wt-part" if r else "wt-none"
            side = " wt-left" if ti == len(trees) - 1 or (ti == 1 and t["col"] >= 2) else ""
            up = " wt-up" if t["tier"] >= 4 else ""
            icon = data_uri(f"https://wow.zamimg.com/images/wow/icons/medium/{s['icon']}.jpg")
            card = [f'<span class="wt-title">{html.escape(s["name"])}</span>',
                    f'<span class="wt-sub">Rank {r}/{t["max"]}'
                    + (f' · level {lv_text(levels[t["spell"]])}' if r else "") + "</span>"]
            card += [f'<span class="wt-line">{html.escape(l)}</span>' for l in s["lines"]]
            note = cards.get(t["spell"], s["name"])  # click opens the ability card (wowmap-jump plugin)
            out.append(f'<div class="wt-node {state}{side}{up}" tabindex="0" data-wm-open="{html.escape(note)}" '
                       f'style="grid-row:{t["tier"] + 1};grid-column:{t["col"] + 1}">'
                       f'<img src="{icon}"><b class="wt-rank">{r}/{t["max"]}</b>'
                       f'<div class="wt-card">{"".join(card)}</div></div>')
        out.append("</div></div>")
    out.append("</div>")
    split = "/".join(str(x) for x in spent)
    return n, split, "".join(out)


def main():
    cls, out, title, *builds = sys.argv[1:]
    cfg = json.loads((HERE / "config" / f"{cls}.json").read_text())
    md = [f"# {title}", ""]
    for b in builds:
        key, _, pts = b.partition(":")
        bd = cfg["builds"][key]
        n, split, block = render(cfg, key, int(pts) if pts else None)
        lvl = FIRST_LEVEL + n - 1
        md += [f"## Level {lvl} — {n} points ({split})",
               f"- [Method]({bd['url']})",
               "", block, ""]
    Path(out).write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
