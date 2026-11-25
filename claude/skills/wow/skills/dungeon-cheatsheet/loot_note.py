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
always visible (scroll, no hover). Header: approx % change for W / P vs the item they wear in that slot
(BagBrother; rough stat weights in score(); rings/trinkets vs the weaker one, 2H vs main + off hand), "empty slot",
or "? random stats". Sorted by the best upgrade; quest items / recipes dimmed. `## Quest rewards` from the map data.
Item cards are made for every drop (notes/gen_cards.py -> Wow_FOREVER/items/). The upgrades (>= 5% or empty slot)
also go to map/<Dungeon> upgrades.json - the interactive map's boss cards show those (run this before interactive_map.py).
Styles: .wowloot / .wm-item in gaming/.obsidian/snippets/wow.css.
"""
import argparse
import html
import json
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


# ---------- approx upgrade % vs what each char wears (BagBrother) ----------
CHARS = {"W": "Karums Warrior", "P": "Karums Priest"}
NUM = r"([\d.]+)"


def stats(item_id, bonus=None):
    """Rough stat dict from the Wowhead tooltip lines; random suffix without bonus ID -> {"random": 1}."""
    L = cs.tooltip(item_id, bonus)["lines"]
    st = {}
    add = lambda k, v: st.__setitem__(k, st.get(k, 0) + float(v))
    for l in L:
        if l.startswith("(") and "Set" in l:
            continue  # set bonuses
        if "<Random enchantment>" in l or "Random enchantment" in l:
            st["random"] = 1
        for k, pat in (("armor", rf"^\+?{NUM} Armor$"), ("str", rf"^\+{NUM} Strength"), ("agi", rf"^\+{NUM} Agility"),
                       ("sta", rf"^\+{NUM} Stamina"), ("int", rf"^\+{NUM} Intellect"), ("spi", rf"^\+{NUM} Spirit"),
                       ("dps", rf"\({NUM} damage per second\)"), ("speed", rf"^Speed {NUM}$"), ("mp5", rf"Restores \+?{NUM} mana per 5"),
                       ("ap", rf"\+{NUM} Attack Power\.?$"), ("hit", rf"chance to hit by {NUM}%"),
                       ("crit", rf"critical strike by {NUM}%"), ("def", rf"Increased Defense \+{NUM}"),
                       ("heal", rf"healing done by (?:magical spells and effects )?(?:by )?up to {NUM}")):
            m = re.search(pat, l)
            if m:
                add(k, m.group(1))
        m = re.match(r"^(\d+) - (\d+) Damage$", l)  # main hit only, not "+ 5 - 10 Fire Damage"
        if m and "avg" not in st:
            st["avg"] = (int(m.group(1)) + int(m.group(2))) / 2
        if l.startswith("Chance on hit:") and "proc" not in st:
            st["proc"] = proc_damage(l, st.get("avg", 0))
    return st


# Weapon procs: rate unknown on Forever -> guess PROC_PPM procs/min. Ravager-style AoE whirlwinds count
# AOE_TARGETS mobs (the duo pulls several at once).
PROC_PPM = 1
AOE_TARGETS = 2


def proc_damage(line, avg):
    """Expected damage of one proc from its 'Chance on hit:' line (0 = no direct damage, e.g. stun/armor)."""
    m = re.search(r"weapon damage plus (\d+) every (\d+) sec for (\d+) sec", line)
    if m:
        ticks = int(m.group(3)) // int(m.group(2))
        return ticks * (avg + int(m.group(1))) * (AOE_TARGETS if "all nearby" in line else 1)
    m = re.search(r"(\d+) to (\d+) (?:\w+ )?damage", line)
    if m:
        return (int(m.group(1)) + int(m.group(2))) / 2
    m = re.search(r"(\d+) (?:\w+ )?damage", line)
    return float(m.group(1)) if m else 0


# Arms 2H: white swings scale with DPS, Mortal Strike / Overpower / Whirlwind / Slam with one swing's damage
# (avg hit), so slow hard-hitting weapons win at equal DPS. Per 10 s: 10*DPS white + ABIL_HITS*avg from
# abilities. 1 Str = 2 AP = 2/14 DPS on every white second + ability (3.3 = normalized 2H speed, guess).
ABIL_HITS = 2
STR_DMG = 2 / 14 * (10 + ABIL_HITS * 3.3)


def weapon_term(st):
    if not st.get("dps"):
        return 0
    proc = PROC_PPM / 6 * st.get("proc", 0)  # damage per 10 s
    if not st.get("avg"):
        return 7 * st["dps"] + proc / STR_DMG
    return (10 * st["dps"] + ABIL_HITS * st["avg"] + proc) / STR_DMG


def score(c, st, slot=None):
    if c == "W":
        s = (st.get("str", 0) + .5 * st.get("agi", 0) + .8 * st.get("sta", 0) + .5 * st.get("ap", 0) + .03 * st.get("armor", 0)
             + 8 * st.get("hit", 0) + 8 * st.get("crit", 0) + .6 * st.get("def", 0) + .05 * st.get("spi", 0))
        return s + (weapon_term(st) if slot == "Two-Hand" else 0)
    s = st.get("heal", 0) + 2 * st.get("mp5", 0) + .5 * st.get("int", 0) + .6 * st.get("spi", 0) + .25 * st.get("sta", 0)
    return s + (.5 * st.get("dps", 0) if slot == "Ranged" else 0)


RECIPE = re.compile(r"^(Schematic|Plans|Pattern|Recipe|Formula|Design|Manual)[:\s-]")
SKIP = {"W": {"One-Hand", "Main Hand", "Off Hand", "Held In Off-hand"}, "P": {"Off Hand"}}


def upgrade(c, gear, item_id):
    """Approx % vs the worn item(s) in that slot: number, "new" (empty slot), "?" (random stats) or None (not for c)."""
    g = gear.get(CHARS[c])
    tt = cs.tooltip(item_id)
    if RECIPE.match(tt["name"]):
        return None  # recipe tooltips embed the crafted item, slot line included
    slot, typ, req, _ = cs.describe(tt)
    if not g or not slot or slot in SKIP[c] or not cs.can_equip(g["class"], slot, typ):
        return None
    if c == "W" and (typ in ("Shield", "Wand", "Dagger", "Fist Weapon", "Cloth", "Leather")):
        return None  # Arms 2H in mail (plate at 40): cloth/leather never beats it
    new = stats(item_id)
    if new.get("random"):
        return "?"
    sid = cs.SLOT_IDS[slot]
    worn = [(i, g["gear"].get(i)) for i in sid]
    if slot == "Two-Hand":  # replaces main + off hand
        worn = [(i, g["gear"].get(i)) for i in (16, 17)]
        cur = sum(score(c, stats(w, g["bonus"].get(i)), cs.describe(cs.tooltip(w))[0]) for i, w in worn if w)
        if any(w and stats(w, g["bonus"].get(i)).get("random") for i, w in worn):
            return "?"
    else:
        if all(w is None for _, w in worn):
            return "new"
        olds = []
        for i, w in worn:
            if w is None:
                return "new"
            ws = stats(w, g["bonus"].get(i))
            if ws.get("random"):
                return "?"
            olds.append(score(c, ws, cs.describe(cs.tooltip(w))[0]))
        cur = min(olds)  # rings / trinkets: replace the weaker one
    nw = score(c, new, slot)
    if cur <= 0:
        return "new" if nw > 0 else None
    return round(100 * (nw - cur) / cur)


# ---------- who else rolls Need on it (for "Big drops": pick the group around them) ----------
CLASSES = ("Warrior", "Paladin", "Hunter", "Rogue", "Priest", "Shaman", "Mage", "Warlock", "Druid")
WEARS = {  # who wants this armor / weapon type (Classic rules: hunter/shaman wear leather until 40)
    "Cloth": {"Priest", "Mage", "Warlock"}, "Leather": {"Rogue", "Druid", "Hunter", "Shaman"},
    "Mail": {"Warrior", "Paladin", "Hunter", "Shaman"}, "Plate": {"Warrior", "Paladin"},
    "Wand": {"Priest", "Mage", "Warlock"}, "Shield": {"Warrior", "Paladin", "Shaman"},
    "Bow": {"Hunter", "Warrior", "Rogue"}, "Crossbow": {"Hunter", "Warrior", "Rogue"}, "Gun": {"Hunter", "Warrior", "Rogue"},
    "Thrown": {"Warrior", "Rogue"}, "Polearm": {"Warrior", "Paladin", "Hunter"},
    "Staff": {"Priest", "Mage", "Warlock", "Druid", "Shaman", "Hunter", "Warrior"},
    "Dagger": {"Rogue", "Mage", "Warlock", "Priest", "Hunter", "Warrior", "Druid", "Shaman"},
    "Held In Off-hand": {"Priest", "Mage", "Warlock", "Druid", "Shaman", "Paladin"},
}
WEAPON_SLOTS = {"Two-Hand", "One-Hand", "Main Hand", "Off Hand", "Ranged", "Thrown"}
HEALERS = {"Priest", "Paladin", "Druid", "Shaman"}
CASTERS = {"Priest", "Mage", "Warlock", "Druid", "Shaman", "Paladin"}


def rivals(item_id, own=("Warrior", "Priest")):
    """Classes besides ours that would Need it: armor/weapon type ∩ stats (rough; random suffix -> type only)."""
    tt = cs.tooltip(item_id)
    slot, typ, _, _ = cs.describe(tt)
    by_type = WEARS.get(typ) or WEARS.get(slot) or set(CLASSES)
    if typ in ("Axe", "Sword", "Mace", "Fist Weapon"):
        by_type = set(CLASSES) - {"Priest", "Mage", "Warlock"}
        by_type |= {"Priest"} if typ == "Mace" else set()
        by_type |= {"Mage", "Warlock"} if typ == "Sword" and slot != "Two-Hand" else set()
    st, text = stats(item_id), " ".join(tt["lines"])
    want = set()
    if "healing done" in text and "damage and healing" not in text:
        want |= HEALERS
    if re.search(r"damage (?:and healing )?done by (?:\w+ )?(?:magical )?spells|spell power|Your spells", text, re.I):
        want |= CASTERS
    if st.get("int") or st.get("mp5") or (st.get("spi") and not st.get("str") and not st.get("agi")):
        want |= CASTERS
    if st.get("str"):
        want |= {"Warrior", "Paladin", "Shaman", "Druid"}
    if st.get("agi"):
        want |= {"Rogue", "Hunter", "Druid", "Shaman"}
    if st.get("ap") or st.get("crit") or st.get("hit"):
        want |= {"Warrior", "Rogue", "Hunter", "Paladin", "Shaman"}
    if st.get("def"):
        want |= {"Warrior", "Paladin", "Druid"}
    if st.get("random") or not want:
        want = set(CLASSES)  # unknown stats: anyone who wears it
    return [c for c in CLASSES if c in by_type and c in want and c not in own]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dungeon")
    a = ap.parse_args()
    # "Scarlet Monastery/Graveyard" = a wing: folder dungeons/Scarlet Monastery/Graveyard/, files "Graveyard ...";
    # lookups (AtlasLoot, FDJ, site slugs) use the full name
    full, base = a.dungeon.replace("/", " "), Path(a.dungeon).name
    d = VAULT / "dungeons" / a.dungeon
    note = d / "notes" / f"{base} loot.md"
    data = next((p for p in (d / "map" / f"{base} map data.md", d / f"{base} tactics.md") if p.exists()), None)
    text = data.read_text() if data else ""

    nums, lvls = {}, {}  # map numbers + levels from the map data headings
    for h in re.findall(r"(?m)^## (.+)$", text):
        m = re.match(r"(\d+)\.\s*(.+?)(?:\s+—\s+(\d+))?(?:\s+\(.*\))?\s*$", h)
        if m:
            nums[key(m.group(2))], lvls[key(m.group(2))] = m.group(1), m.group(3)
    qr = re.search(r"\n## Quest rewards[^\n]*\n(.*?)(?=\n## |\Z)", text, re.S)

    _, bosses = cs.atlasloot_bosses(full)
    if not any(b["name"].lower() == "trash" for b in bosses) and (tr := fdj_trash(full)):
        bosses.append({"name": "Trash", "level": None, "items": tr})
    # map-number order; bosses without a number after them, trash last
    bosses.sort(key=lambda b: (b["name"].lower() == "trash", int(nums.get(key(b["name"]), 999))))

    icons = Icons()

    gear = cs.equipped(list(CHARS.values()))

    def card_id(name):
        f = VAULT / "items" / f"{name}.md"
        m = re.search(r"^id: (\d+)", f.read_text(), re.M) if f.exists() else None
        return int(m.group(1)) if m else None

    def badges(iid):
        """[(char, pct)] for chars who can use it; pct = int | "new" | "?"."""
        return [(c, u) for c in CHARS if iid and (u := upgrade(c, gear, iid)) is not None]

    def rank(b):  # sort key: best upgrade first, unknown in the middle, misc last
        nums = [100 if u == "new" else u for _, u in b if u != "?"]
        return -(max(nums) if nums else (0 if b else -999))

    found = {}  # boss key -> computed upgrades, for the map's boss cards (map/<Dungeon> upgrades.json)

    def banner(name, icon, head="", dim=False, boss=None):
        """One item = one banner: the full tooltip, always visible; a header with W/P approx % vs worn gear."""
        iid = card_id(name)
        tip = im.item_tip(name, icons(icon)).replace('<span class="wm-tip">', '<span class="wm-itip">', 1)
        if not tip:  # no card (shouldn't happen): name only
            tip = f'<span class="wm-itip"><span class="wm-q-{im.item_quality(name)} wm-tip-name">{html.escape(name)}</span></span>'
        b = badges(iid) if not dim else []
        up = any((u == "new" or (isinstance(u, int) and u >= 5)) for _, u in b)
        parts = [f'<b class="wm-upg-q">{html.escape(head)}</b>'] if head else []
        for c, u in b:
            txt = "empty slot" if u == "new" else ("? random stats" if u == "?" else f"{u:+d}%")
            cls = "up" if (u == "new" or (isinstance(u, int) and u >= 5)) else ("unk" if u == "?" else "down")
            parts.append(f'<span class="wm-pct wm-pct-{cls}"><b class="wm-who wm-{c}">{c}</b>{txt}</span>')
        top = f'<span class="wm-upg">{"".join(parts)}</span>' if parts else ""
        cls = "wm-item" + (" wm-item-up" if up else "") + (" wm-item-dim" if dim else "")
        if boss:
            for c, u in b:
                if u == "new" or (isinstance(u, int) and u >= 5):
                    found.setdefault(boss, []).append(dict(who=c, item=name, icon=icon,
                                                           why="empty slot" if u == "new" else f"{u:+d}%",
                                                           pct=999 if u == "new" else u, rivals=rivals(iid),
                                                           weapon=cs.describe(cs.tooltip(iid))[0] in WEAPON_SLOTS))
        return rank(b), f'<div class="{cls}">{top}{tip}</div>'

    out = []  # no title / intro: the note is embedded under `## Loot` of the main note
    for b in bosses:
        trash = b["name"].lower() == "trash"
        k = "trash" if trash else key(b["name"])
        num, lvl = nums.get(k), lvls.get(k) or b["level"]
        out.append("## Trash (BoE, random)" if trash else
                   f"## {num + '. ' if num else ''}{b['name']}{f' — {lvl}' if lvl else ''}")
        gear_b, misc, seen = [], [], set()
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
            (gear_b if slot else misc).append(banner(name, card_icon(name), dim=not slot, boss=k if slot else None))
        rows = [h for _, h in sorted(gear_b, key=lambda x: x[0])] + [h for _, h in misc]
        out += ['<div class="wowloot"><div class="wm-items">' + "".join(rows) + "</div></div>", ""]
    if qr:
        out.append("## Quest rewards")
        items = []
        for l in (l.strip() for l in qr.group(1).splitlines() if l.strip().startswith("- ")):
            rest = re.sub(r"^- (?:\[[ x]\] )?(?:[WP] — )?", "", l)
            quest = re.split(r"\s+—\s+", rest)[0] if not rest.startswith("![[") else ""
            for icon, name in re.findall(ITEM, rest):
                items.append(banner(name, icon, head=quest))
        out += ['<div class="wowloot"><div class="wm-items">' + "".join(h for _, h in sorted(items, key=lambda x: x[0]))
                + "</div></div>", ""]

    note.parent.mkdir(parents=True, exist_ok=True)
    for v in found.values():
        v.sort(key=lambda u: -u["pct"])
    (d / "map").mkdir(exist_ok=True)
    (d / "map" / f"{base} upgrades.json").write_text(json.dumps(found, indent=1, ensure_ascii=False))
    note.write_text("\n".join(out).rstrip() + "\n")

    # main note: `## Loot` embeds this note, right above `## Notes` (the links block at the end)
    main = d / f"{base}.md"
    embed = f"![[{note.stem}]]"
    if main.exists() and embed not in (mt := main.read_text()):
        block = f"## Loot\n{embed}\n\n"
        mt = mt.replace("## Notes\n", block + "## Notes\n", 1) if "## Notes\n" in mt else mt.rstrip() + "\n\n" + block
        main.write_text(mt)
        print(f"{main.name}: ## Loot embeds {embed}")
    print(f"{note}  ({len(bosses)} sections"
          f"{', quest rewards' if qr else ''})")


if __name__ == "__main__":
    main()
