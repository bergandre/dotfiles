#!/usr/bin/env python3
"""Write dungeons/<Dungeon>/notes/<Dungeon> loot.md: per boss a heading + one tooltip banner per drop.

usage: python3 -I loot_note.py "<Dungeon>"

Generated - never edit the note by hand. Sources:
  - drops per boss: AtlasLoot data-forever.lua (path order); Forever-only dungeons without an AtlasLoot trash
    table get their trash drops from ForeverDungeonJournal
  - map numbers, levels, the W/P upgrade lines and `## Quest rewards`: map/<Dungeon> map data.md
      - [ ] W — ![[icon|inline]] [[Item]] — why        <- under the boss's section / `## Trash`, judged by hand
  - portraits: art/<Boss>.webp (foreverchanges) or art/method/ (method.gg render)
Embedded in the main note under `## Loot` (added above `## Notes` if missing), so no title of its own.
Layout: `## <map nr>. <Boss> — <level>` heading per boss, then one banner per item = the full item tooltip,
always visible (scroll, no hover). Upgrades first with a W/P header + the reason, then the other gear,
then quest items / recipes (dimmed). `## Quest rewards` from the map data the same way.
Item cards are made for every drop (notes/gen_cards.py -> Wow_FOREVER/items/).
Styles: .wowloot / .wm-item in gaming/.obsidian/snippets/wow.css.
"""
import argparse
import html
import importlib.util
import re
from pathlib import Path

HERE = Path(__file__).parent
VAULT = Path("~/Documents/obsidian/gaming/Wow_FOREVER").expanduser()


def load(name, path):  # sibling scripts, loaded by path (no package; -I ignores cwd)
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cs = load("cheatsheet", HERE / "cheatsheet.py")
cards = load("gen_cards", HERE.parent / "notes/gen_cards.py")
im = load("interactive_map", HERE / "interactive_map.py")

ITEM = r"!\[\[([^|\]]+)\|inline\]\] \[\[([^\]|]+)(?:\|[^\]]+)?\]\]"


def key(name):
    return re.sub(r"[^a-z]", "", name.lower())


def fdj_trash(dungeon):
    """Trash drop IDs from ForeverDungeonJournal (Forever-only dungeons have no AtlasLoot trash table)."""
    s = (cs.REPO / "Interface/AddOns/ForeverDungeonJournal/Data/Dungeons.lua").read_text(errors="replace")
    for m in re.finditer(r'FDJ\.DB\["([^"]+)"\] = \{', s):
        if key(m.group(1)) == key(dungeon):
            body = s[m.end(): s.find('FDJ.DB["', m.end())]
            t = body.find('name = "Trash Drops"')
            if t >= 0:
                return [int(i) for i in re.findall(r'\{(\d+), "', body[t: body.find("\n        }", t)])]  # to the entry's end
    return []


class Icons:
    """Item icon data URIs (36px), cached per run."""
    def __init__(self):
        self.c = {}

    def __call__(self, icon):
        if icon not in self.c:
            f = VAULT / "items" / "icons" / icon
            self.c[icon] = im.data_uri(f.read_bytes(), "jpeg", 85, "36x36") if f.exists() else ""
        return self.c[icon]


def card_icon(name):
    f = VAULT / "items" / f"{name}.md"
    m = re.search(r"^icon: (.+)$", f.read_text(), re.M) if f.exists() else None
    return m.group(1).strip() if m else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dungeon")
    a = ap.parse_args()
    d = VAULT / "dungeons" / a.dungeon
    note = d / "notes" / f"{a.dungeon} loot.md"
    data = next((p for p in (d / "map" / f"{a.dungeon} map data.md", d / f"{a.dungeon} tactics.md") if p.exists()), None)
    text = data.read_text() if data else ""

    nums, lvls = {}, {}  # map numbers + levels from the map data headings
    for h in re.findall(r"(?m)^## (.+)$", text):
        m = re.match(r"(\d+)\.\s*(.+?)(?:\s+—\s+(\d+))?(?:\s+\(.*\))?\s*$", h)
        if m:
            nums[key(m.group(2))], lvls[key(m.group(2))] = m.group(1), m.group(3)
    ups = im.parse_loot(data) if data else {}
    qr = re.search(r"\n## Quest rewards[^\n]*\n(.*?)(?=\n## |\Z)", text, re.S)

    _, bosses = cs.atlasloot_bosses(a.dungeon)
    if not any(b["name"].lower() == "trash" for b in bosses) and (tr := fdj_trash(a.dungeon)):
        bosses.append({"name": "Trash", "level": None, "items": tr})

    icons = Icons()

    def banner(name, icon, who="", head="", why="", dim=False):
        """One item = one banner: the full tooltip, always visible; upgrades get a W/P header with the reason."""
        tip = im.item_tip(name, icons(icon)).replace('<span class="wm-tip">', '<span class="wm-itip">', 1)
        if not tip:  # no card (shouldn't happen): name only
            tip = f'<span class="wm-itip"><span class="wm-q-{im.item_quality(name)} wm-tip-name">{html.escape(name)}</span></span>'
        top = ""
        if who or head or why:
            top = ('<span class="wm-upg">' + (f'<b class="wm-who wm-{who}">{who}</b>' if who else "")
                   + (f'<b class="wm-upg-q">{html.escape(head)}</b>' if head else "")
                   + (f'<span>{html.escape(why)}</span>' if why else "") + "</span>")
        cls = "wm-item" + (" wm-item-up" if who else "") + (" wm-item-dim" if dim else "")
        return f'<div class="{cls}">{top}{tip}</div>'

    out = []  # no title / intro: the note is embedded under `## Loot` of the main note
    for b in bosses:
        trash = b["name"].lower() == "trash"
        k = "trash" if trash else key(b["name"])
        num, lvl = nums.get(k), lvls.get(k) or b["level"]
        out.append("## Trash (BoE, random)" if trash else
                   f"## {num + '. ' if num else ''}{b['name']}{f' — {lvl}' if lvl else ''}")
        items, seen = [], set()
        for u in ups.get(k, []):
            items.append(banner(u["item"], u["icon"], u["who"], why=u["why"]))
            seen.add(u["item"])
        gear, misc = [], []
        for iid in dict.fromkeys(b["items"]):
            tt = cs.tooltip(iid)
            if tt.get("err"):
                continue  # AtlasLoot spacer, not an item
            name = cards.note_name(tt["name"])
            if name in seen:
                continue
            seen.add(name)
            if not (VAULT / "items" / f"{name}.md").exists():
                cards.build(iid, VAULT / "items", False)
            slot = cs.describe(tt)[0]
            (gear if slot else misc).append(banner(name, card_icon(name), dim=not slot))
        out += ['<div class="wowloot"><div class="wm-items">' + "".join(items + gear + misc) + "</div></div>", ""]
    if qr:
        out.append("## Quest rewards")
        items = []
        for l in (l.strip() for l in qr.group(1).splitlines() if l.strip().startswith("- ")):
            m = re.match(r"- (?:\[[ x]\] )?(?:([WP]) — )?(.*)", l)
            who, rest = (m.group(1) or "", m.group(2)) if m else ("", l[2:])
            quest = re.split(r"\s+—\s+", rest)[0] if not rest.startswith("![[") else ""
            why = rest.rsplit(" — ", 1)[1] if rest.count(" — ") >= (2 if quest else 1) else ""
            for icon, name in re.findall(ITEM, rest):
                items.append(banner(name, icon, who, head=quest, why=why))
        out += ['<div class="wowloot"><div class="wm-items">' + "".join(items) + "</div></div>", ""]

    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text("\n".join(out).rstrip() + "\n")

    # main note: `## Loot` embeds this note, right above `## Notes` (the links block at the end)
    main = d / f"{a.dungeon}.md"
    embed = f"![[{note.stem}]]"
    if main.exists() and embed not in (mt := main.read_text()):
        block = f"## Loot\n{embed}\n\n"
        mt = mt.replace("## Notes\n", block + "## Notes\n", 1) if "## Notes\n" in mt else mt.rstrip() + "\n\n" + block
        main.write_text(mt)
        print(f"{main.name}: ## Loot embeds {embed}")
    print(f"{note}  ({len(bosses)} sections, {sum(len(v) for v in ups.values())} upgrades"
          f"{', quest rewards' if qr else ''})")


if __name__ == "__main__":
    main()
