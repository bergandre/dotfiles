#!/usr/bin/env python3
"""Generate professions/<prof>/recipes.md (full recipe catalogue) and print the leveling note's dynamic tables.

usage:
  recipes_catalogue.py Blacksmithing                 # rewrite recipes.md (generated - never edit by hand)
  recipes_catalogue.py Blacksmithing --useful arms   # level-band upgrade tables for leveling.md (also: prot)
  recipes_catalogue.py Blacksmithing --get           # "Recipes to get" candidates (unknown: gear / profit)
  recipes_catalogue.py Blacksmithing --points "Imperial Plate Belt" --skill 222   # Learn/Yellow/Green/Grey table
  recipes_catalogue.py Cooking --food warrior        # buff food by eat level (also: priest; --level N)
  recipes_catalogue.py Blacksmithing --shop "Mithril Spurs=5,Heavy Mithril Shoulder=3"   # Need / Have / Buy table

Data (data/<prof>/, cached from Wowhead Forever through Claude in Chrome - see SKILL.md "Recipe catalogue"):
  spells.txt     id|name|learnedat|orange/yellow/green/grey|item/min/max|reagents|source codes|training cost|quality|status
  plans.txt      id|name|required skill||source codes|type~id~name~zone~zone2;...|quality
  overrides.tsv  regex<TAB>source|note<TAB>text  (hand-kept remarks; survive regeneration)
Prices / stock / known recipes: the repo's TSM data (tsm-analyze.py). Item names, icons, slots: Wowhead tooltips
(cheatsheet.py cache). Cards for every crafted item and mat are made with notes/gen_cards.py.
"""
import argparse
import datetime
import difflib
import importlib.util
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).parent
SKILLS = HERE.parent
ROOT = Path(os.environ.get("WOW_REPO", "~/repositories/wow-forever-addon-settings")).expanduser()
VAULT = Path("~/Documents/obsidian/gaming/Wow_FOREVER").expanduser()
CHAR = "Karums Warrior"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


t = load("t", ROOT / "tsm-analyze.py")
pp = load("pp", HERE / "profession-plan.py")
cs = load("cheatsheet", SKILLS / "dungeon-cheatsheet/cheatsheet.py")
ln = load("loot_note", SKILLS / "dungeon-cheatsheet/loot_note.py")
cards = load("gen_cards", SKILLS / "notes/gen_cards.py")

ZONES = {3: "Badlands", 8: "Swamp of Sorrows", 10: "Duskwood", 11: "Wetlands", 15: "Dustwallow Marsh", 16: "Azshara",
         28: "Western Plaguelands", 33: "Stranglethorn Vale", 36: "Alterac Mountains", 44: "Redridge", 45: "Arathi Highlands",
         47: "Hinterlands", 51: "Searing Gorge", 139: "Eastern Plaguelands", 215: "Mulgore", 267: "Hillsbrad",
         331: "Ashenvale", 357: "Feralas", 361: "Felwood", 400: "Thousand Needles", 405: "Desolace", 440: "Tanaris",
         616: "Mount Hyjal", 618: "Winterspring", 721: "Gnomeregan", 1377: "Silithus", 1581: "Deadmines",
         1583: "Blackrock Spire", 1584: "Blackrock Depths", 1637: "Orgrimmar", 2017: "Stratholme", 2557: "Dire Maul",
         2717: "Molten Core", 3428: "Ahn'Qiraj", 3429: "Ruins of Ahn'Qiraj", 16544: "Dalaran", 16554: "Blackmaw Hold",
         16591: "Riverglades", 16593: "Zephras Isle", 1: "Dun Morogh", 14: "Durotar", 17: "Barrens", 38: "Loch Modan",
         41: "Deadwind Pass", 85: "Tirisfal Glades", 130: "Silverpine Forest", 148: "Darkshore", 406: "Stonetalon Mountains",
         490: "Un'Goro Crater", 718: "Wailing Caverns", 1497: "Undercity", 1519: "Stormwind", 1638: "Thunder Bluff"}
# vendor-only mats: never price from the AH (copper)
VENDOR = {2880: 100, 3466: 2000, 3857: 500, 2605: 100, 4399: 200, 2678: 10, 2692: 40, 3713: 160, 159: 25, 1179: 125}
ARMOR_SLOTS = ["Head", "Shoulder", "Chest", "Wrist", "Hands", "Waist", "Legs", "Feet"]


def money(c):
    """In-game coin colours: <span class="mg">1g</span> <span class="ms">24s</span> (wow.css .mg/.ms/.mc)."""
    if not c:
        return "—"
    c = int(round(abs(c)))
    g, s = c // 10000, c // 100 % 100
    if g:
        return f'<span class="mg">{g}g</span>' + (f' <span class="ms">{s}s</span>' if s else "")
    return f'<span class="ms">{s}s</span>' if s else f'<span class="mc">{c}c</span>'


MONEY = re.compile(r"(?<![\w.\[])(\d+(?:\.\d+)?)g(\d\d)?(?![\w\]])|(?<![\w.\[])(\d+)([sc])(?![\w\]])")


def style_money(text):
    """Wrap plain amounts (17g, 3g50, 0.8g, 12s, 55c) of a hand-written note in the coin-colour spans.
    Skips wiki links, embeds, code spans, URLs and text that is already styled."""
    def coin(m):
        if m.group(1):
            return f'<span class="mg">{m.group(1)}g</span>' + (f' <span class="ms">{m.group(2)}s</span>' if m.group(2) else "")
        return f'<span class="m{m.group(4)}">{m.group(3)}{m.group(4)}</span>'
    keep = re.compile(r"(!?\[\[[^\]]*\]\]|`[^`]*`|https?://\S+|<span class=\"m[gsc]\">[^<]*</span>)")
    return "".join(part if i % 2 else MONEY.sub(coin, part) for i, part in enumerate(keep.split(text)))


def key(name):
    return re.sub(r"[^a-z]", "", name.lower()).rstrip("s")


class Data:
    def __init__(self, prof):
        self.prof = prof
        d = HERE / "data" / prof.lower()
        self.prices, self.inv = t.load_prices(), t.load_inventory()
        self.known = {sid for sid, (_, who) in pp.known_recipes(prof).items() if CHAR in who}
        self.vendor = dict(VENDOR)
        self.overrides = []
        f = d / "overrides.tsv"
        for line in f.read_text().splitlines() if f.exists() else []:
            if line.strip() and not line.startswith("#"):
                rx, field, text = line.split("\t")
                self.overrides.append((re.compile(rx), field, text))
        self.trainers = {}  # spell -> [(trainer, place)]
        f = d / "trainers.tsv"
        for line in f.read_text().splitlines() if f.exists() else []:
            if line.strip() and not line.startswith("#"):
                who, place, ids = line.split("\t")
                for i in ids.split(","):
                    self.trainers.setdefault(int(i), []).append((who, place))
        self.drops = {}  # plans item id -> (npc id, npc, drops, kills)
        f = d / "droprates.tsv"
        for line in f.read_text().splitlines() if f.exists() else []:
            if line.strip() and not line.startswith("#"):
                pid, nid, npc, c, n = line.split("\t")
                self.drops[int(pid)] = (int(nid), npc, int(c), int(n))
        self.vendors = {}  # recipe item id -> [(npc id, npc, zone id)], Horde-friendly vendors
        f = d / "vendors.tsv"
        for line in f.read_text().splitlines() if f.exists() else []:
            if line.strip() and not line.startswith("#"):
                pid, npcs = line.split("\t")
                self.vendors[int(pid)] = [(int(a), b, int(c)) for a, b, c in (n.split("~") for n in npcs.split(";"))]
        self.plans = {}
        for line in (d / "plans.txt").read_text().splitlines():
            p = line.split("|")
            name = re.sub(r"^(Plans|Blueprint|Recipe|Pattern|Schematic|Formula): ", "", p[1])
            more = [m.split("~") for m in p[5].split(";") if m]
            self.plans[key(name)] = {"id": int(p[0]), "skill": int(p[2] or 0), "src": [int(x) for x in p[4].split("/") if x],
                                     "more": more}
        self.recipes = []
        for line in (d / "spells.txt").read_text().splitlines():
            p = line.split("|")
            sid = int(p[0])
            if not p[4] or p[8] == "-1" or 400000 <= sid < 1000000:  # ranks, specs, other game versions' leftovers
                continue
            item, lo, _ = (int(x) for x in p[4].split("/"))
            colors = [int(x) for x in p[3].split("/")] if p[3] else [0, 0, 0, 0]
            plan = self.plans.get(key(p[1]))
            if not plan and "6" not in p[6].split("/"):  # spelling drift: spell "Mithril Headed Trout", recipe "... Head Trout"
                near = difflib.get_close_matches(key(p[1]), list(self.plans), 1, .92)
                plan = self.plans[near[0]] if near else None
            self.recipes.append({
                "spell": sid, "name": p[1], "item": item, "n": lo, "colors": colors,
                "learn": (plan["skill"] if plan and plan["skill"] else 0) or int(p[2]),
                "mats": [tuple(int(x) for x in r.split("x")) for r in p[5].split(",") if r],
                "src": [int(x) for x in p[6].split("/") if x], "cost": int(p[7] or 0), "plan": plan,
                "new": p[9] == "new", "known": sid in self.known})

    # ---- prices
    def mkt(self, i):
        p = self.prices.get(i, {})
        return p.get("marketValueRecent") or p.get("marketValue") or p.get("regionMarketValue") or 0

    def rate(self, i):
        return self.prices.get(i, {}).get("regionSalePercent")

    def mat_price(self, i):
        return self.vendor.get(i) or self.mkt(i)

    def mats_cost(self, r):
        """Total at vendor/AH prices; None when a mat has no price."""
        tot = 0
        for i, n in r["mats"]:
            p = self.mat_price(i)
            if not p:
                return None
            tot += p * n
        return tot

    # ---- items
    def info(self, item_id):
        tt = cs.tooltip(item_id)
        f = cs.CACHE / f"{item_id}.json"
        raw = json.loads(f.read_text()) if f.exists() else {}
        slot, typ, req, _ = cs.describe(tt)
        return {"name": raw.get("name") or tt["name"], "icon": raw.get("icon", ""), "slot": slot, "type": typ, "req": req}

    def link(self, item_id, table=True, alias=None):
        i = self.info(item_id)
        note = cards.note_name(i["name"])
        if not (VAULT / "items" / f"{note}.md").exists():
            cards.build(item_id, VAULT / "items", False)
        bar = "\\|" if table else "|"
        return f"![[{i['icon']}.jpg{bar}inline]] [[{note}{bar + alias if alias else ''}]]"

    def card(self, r):
        """Note name of the recipe's card: the plans item (Wowhead-style tooltip: skill, drop chance, crafted item,
        reagents) or, for trainer recipes, the crafted item."""
        i = self.info(r["plan"]["id"] if r["plan"] else r["item"])
        self.link(r["plan"]["id"] if r["plan"] else r["item"])
        return cards.note_name(i["name"])

    # ---- source cell
    def source(self, r, table=True):
        src = None
        note = [text for rx, field, text in self.overrides if field == "note" and rx.search(r["name"])]
        for rx, field, text in self.overrides:
            if field == "source" and rx.search(r["name"]):
                src = text
        plan = r["plan"]
        if src is None and 6 in r["src"] and not plan:
            tr = self.trainers.get(r["spell"], [])
            spec = [w for w, _ in tr if "smith trainer" in w]
            places = list(dict.fromkeys(pl for _, pl in tr))
            if spec:      # Armorsmith / Weaponsmith only
                src = f"{spec[0]}, {places[0]}"
            elif places:  # which city: every trainer vs one place only
                src = "trainer — " + (f"{places[0]} only" if len(places) == 1 else ", ".join(sorted(places, key=lambda x: x != "Orgrimmar")))
            else:
                src = "trainer — ?" if self.trainers else f"trainer — any {self.prof} trainer"
            src += f" · {money(r['cost'])}" if r["cost"] else ""
        elif src is None and plan:
            bits = []
            wh = "https://www.wowhead.com/forever/"
            vendor = 5 in plan["src"]
            for m in plan["more"]:
                typ, name = m[0], m[2] if len(m) > 2 else ""
                zone = ZONES.get(int(m[3])) if len(m) > 3 and m[3].lstrip("-").isdigit() else None
                if typ == "5" and name:
                    bits.append(f"quest — [{name}]({wh}quest={m[1]})")  # always a link
                elif typ in ("1", "2") and name:
                    link = f"[{name}]({wh}{'npc' if typ == '1' else 'object'}={m[1]})"
                    bits.append(f"{'vendor' if vendor else 'drop'} — {link}" + (f", {zone}" if zone else ""))
                elif zone:
                    bits.append(("vendor" if vendor else "drop") + f" — {zone}")
            vs = self.vendors.get(plan["id"])
            if vs:  # Horde vendors read from the item page: main cities first, three at most
                vs = sorted(vs, key=lambda v: ZONES.get(v[2]) not in ("Orgrimmar", "Thunder Bluff", "Undercity"))[:3]
                bits = [b for b in bits if not b.startswith("vendor")]
                bits += [f"vendor — [{n}]({wh}npc={i})" + (f", {ZONES[z]}" if z in ZONES else "") for i, n, z in vs]
            dr = self.drops.get(plan["id"])
            if dr and not vendor:  # how hard it is to get: the best source's drop chance
                zone = next((ZONES.get(int(m[3])) for m in plan["more"] if len(m) > 3 and m[1] == str(dr[0]) and m[3].isdigit()), None)
                pct = 100 * dr[2] / dr[3]
                bits = [b for b in bits if not b.startswith("drop")]
                bits.insert(0, f"drop — [{dr[1]}]({wh}npc={dr[0]})" + (f", {zone}" if zone else "")
                            + f" · **{pct:.1f}%**" + (" (few kills)" if dr[3] < 200 else ""))
            if not bits:
                names = {2: f"[world drop]({wh}item={plan['id']})", 4: "quest", 5: f"[vendor]({wh}item={plan['id']})", 1: "crafted"}
                bits = [names[c] for c in plan["src"] if c in names] or ["?"]
            src = " / ".join(dict.fromkeys(bits))
        elif src is None:
            src = {2: "drop ?", 4: "quest ?", 5: "vendor ?"}.get(r["src"][0] if r["src"] else 0, "?")
        if plan:  # the plans' own card first: hover = the Wowhead tooltip
            src = f"{self.link(plan['id'], table, 'plans')} · {src}"
        if plan and self.mkt(plan["id"]):
            src += f" · AH {money(self.mkt(plan['id']))}"
        return src + "".join(f" · *{n}*" for n in note)

    # ---- grouping
    def effect(self, r):
        """Food / drink: (buff key, buff text, what it restores) from the item tooltip."""
        txt = " ".join(cs.tooltip(r["item"])["lines"])
        m = re.search(r"gain (.+?) for 15 min", txt)
        buff = m.group(1).replace(" chance", "") if m else ""
        m = re.search(r"Restores ([\d.]+) (health|mana)", txt)
        heal = f"{float(m.group(1)):.0f} {m.group(2)}" if m else ""
        k = next((k for k in ("Strength", "Attack Power", "Agility", "Stamina", "Intellect", "Spirit") if k in buff), None)
        k = k or ("Healing and spell power" if re.search("Healing|Spell", buff) else "Other buffs" if buff else None)
        return k, buff, heal

    def group(self, r):
        if self.prof == "Cooking":
            k, _, heal = self.effect(r)
            order = ["Strength", "Attack Power", "Agility", "Stamina", "Intellect", "Spirit", "Healing and spell power", "Other buffs"]
            if k:
                return (100 + order.index(k), 0, k)
            return (120, 0, "No buff") if heal else (130, 0, "Other")
        i = self.info(r["item"])
        slot, typ, name = i["slot"], i["type"] or "", r["name"]
        if typ == "Shield":
            return (30, 0, "Shields")
        if slot in ("Two-Hand", "One-Hand", "Main Hand", "Off Hand") and typ:
            hand = "Two-Hand" if slot == "Two-Hand" else "One-Hand"
            if typ in ("Polearm", "Staff", "Fist Weapon", "Dagger"):
                return (5 if hand == "Two-Hand" else 12, 0, {"Staff": "Staves"}.get(typ, typ + "s"))
            return (0 if hand == "Two-Hand" else 10, 0, f"{hand} {typ}s")
        if slot in ARMOR_SLOTS and typ in ("Plate", "Mail", "Leather", "Cloth"):
            return (20 + ["Plate", "Mail", "Leather", "Cloth"].index(typ), ARMOR_SLOTS.index(slot), f"{typ} — {slot}")
        if re.search(r"Sharpening Stone|Weightstone|Spike|Chain$|Counterweight|Spurs|Skeleton Key", name):
            return (-1, 0, "Consumables")  # first section: what gets used up on gear (user, 2026-11-24)
        if re.search(r"Grinding Stone|Rod$|Buckle", name):
            return (41, 0, "Parts and rods")
        return (43, 0, "Other")


SPEC_RX = re.compile(r"Requires (Armorsmith|Weaponsmith|Master (?:Sword|Axe|Hammer)smith)")


def spec(d, r):
    """'armor' / 'weapon' when the recipe is exclusive to that specialization (spec trainer, or the plans / item
    tooltip says "Requires Armorsmith" etc.), else None."""
    who = " ".join(w for w, _ in d.trainers.get(r["spell"], []))
    for i in ([r["plan"]["id"]] if r["plan"] else []) + [r["item"]]:
        m = next((m for l in cs.tooltip(i)["lines"] if (m := SPEC_RX.search(l))), None)
        if m:
            who += " " + m.group(1)
    return "armor" if "Armorsmith" in who else "weapon" if "smith" in who else None


def spec_mark(d, r):
    """Empty marker; wow.css colours every link of the row / line that holds it (brown = Armorsmith, red = Weaponsmith)."""
    sp = spec(d, r)
    return f'<span class="spec-{sp}"></span>' if sp else ""


NEW = ' <span class="wf-new">NEW IN FOREVER</span>'  # Wowhead's badge; rule: every Forever-new recipe/item carries it


def new_tag(r):
    return NEW if r["new"] else ""


def skill_cell(r):
    """Catalogue: only the minimum skill to learn it. The colour points live in the leveling note (points())."""
    return str(r["learn"])


def effect_cell(d, r):
    _, buff, heal = d.effect(r)
    req = d.info(r["item"])["req"]
    return "<br>".join(x for x in (f"**{buff}**" if buff else "", heal, f"lvl {req}" if req else "") if x) or "—"


def points(d, skill, extra):
    """Leveling note's "Skill points" table (same four colours as the gathering notes): recipes that still give points at
    `skill` and are known or trainer-taught, plus the ones named in `extra` (the route's plans / quest recipes)."""
    names = {key(n) for n in extra}
    rows = [r for r in d.recipes if key(r["name"]) in names
            or (r["colors"][3] > skill and (r["known"] or (6 in r["src"] and not r["plan"])))]
    print("| Item | Learn | Yellow | Green | Grey | Recipe source |\n|---|---|---|---|---|---|")
    for r in sorted(rows, key=lambda r: (r["learn"], r["name"])):
        _, y, g, x = r["colors"]
        cells = " | ".join(f'<span class="sk-{c}">{v or "—"}</span>' for c, v in (("o", r["learn"]), ("y", y), ("g", g), ("x", x)))
        print(f"| {spec_mark(d, r)}{d.link(r['item'])}{new_tag(r)} | {cells} | {'known' if r['known'] else d.source(r)} |")


FOOD = {"warrior": ("Strength", "Attack Power", "Agility", "Stamina", "Other buffs"),
        "priest": ("Intellect", "Spirit", "Healing and spell power")}


def food(d, who, lvl):
    lvl = lvl or int(cs.equipped([f"Karums {who.title()}"])[f"Karums {who.title()}"].get("level") or 1)
    """Cooking's "Useful for ..." tables: buff food by the level it can be eaten at, strongest first, two per buff."""
    rows = []
    for r in d.recipes:
        k, buff, heal = d.effect(r)
        req = d.info(r["item"])["req"] or 0
        if k in FOOD[who] and not re.search("Fishing|Herbalism|movement", buff):
            n = float(re.search(r"[\d.]+", buff).group())
            rows.append((req, k, n, f"| {r['learn']} | {d.link(r['item'])}{new_tag(r)} | **{buff}**<br>{heal} | {req or '—'} | "
                         f"{'known' if r['known'] else d.source(r)} | {mats_cell(d, r)} |"))
    print(f"## Food for the {who}\n")
    for title, sel in ((f"Now — level {lvl}", lambda q: q <= lvl), ("Level 45", lambda q: lvl < q <= 45), ("Level 55", lambda q: q > max(45, lvl))):
        band = sorted((x for x in rows if sel(x[0])), key=lambda x: (FOOD[who].index(x[1]), -x[2]))
        seen, kept = {}, []
        for x in band:
            seen[x[1]] = seen.get(x[1], 0) + 1
            if seen[x[1]] <= 2:
                kept.append(x)
        if kept:
            print(f"### {title}\n\n| Skill | Food | Buff | Level | Recipe source | Mats |\n|---|---|---|---|---|---|")
            print("\n".join(x[3] for x in kept) + "\n")


def sold_cell(d, r):
    """Region average sold per day (TSM regionSoldPerDay) - how much of it actually moves."""
    v = d.prices.get(r["item"], {}).get("regionSoldPerDay")
    return "—" if v is None else (f"{v:.0f}" if v >= 10 else f"{v:.1f}")


def mats_cell(d, r):
    """Mats are always the real materials with icons, one per line - never a gold figure (user rule)."""
    nb = "\u00a0"  # non-breaking: "20× icon Heavy Thorium Bar" must never wrap inside a mat line
    return "<br>".join(f"{n}×{nb}" + d.link(i, alias=d.info(i)["name"].replace(" ", nb)).replace("]] [[", f"]]{nb}[[")
                       for i, n in r["mats"])


def profit_cells(d, r):
    sells, cost = d.mkt(r["item"]) * r["n"], d.mats_cost(r)
    rate = d.rate(r["item"])
    if not sells:
        return "—", "—", "—", None
    if cost is None:
        return "—", money(sells), f"{rate:.0%}" if rate is not None else "—", None
    p = sells - cost
    cls = "pf-pos" if p >= 0 else "pf-neg"
    return (f'<span class="{cls}">{"+" if p >= 0 else "−"}</span>{money(p)}', money(sells),
            f"{rate:.0%}" if rate is not None else "—", p)


def catalogue(d):
    groups = {}
    for r in d.recipes:
        g = d.group(r)
        groups.setdefault(g, []).append(r)
    appdata = datetime.date.fromtimestamp(t.APPDATA.stat().st_mtime)
    prof = d.prof
    out = ["---", "cssclasses: [prof-recipes]", "---", f"# {prof} recipes — {CHAR} (Horde)",
           f"- {len(d.recipes)} recipes, {sum(r['known'] for r in d.recipes)} known · prices {appdata} · "
           + ('<span class="spec-armor-key">brown = Armorsmith only</span> · <span class="spec-weapon-key">red = Weaponsmith only</span> · '
              if prof == "Blacksmithing" else "") +
           f"[[Wow_FOREVER/professions/{prof.lower()}/leveling|leveling]]",
           "", "## Contents"]
    seen = set()
    for g in sorted(groups):  # one line per section, grouped: Weapons / Plate / Mail
        parent = "Weapons" if g[0] < 20 and g[0] >= 0 else g[2].split(" — ")[0] if " — " in g[2] else None
        if parent and parent not in seen:
            seen.add(parent)
            out.append(f"- {parent}")
        out.append(("  " if parent else "") + f"- [[#{g[2]}|{g[2].split(' — ')[-1]}]]")
    out += ["- [[#Profit estimates]]", ""]
    for g in sorted(groups):
        eff = prof == "Cooking"  # food: what it gives and from which level
        out += [f"## {g[2]}", "", "| Item | Skill | " + ("Effect | " if eff else "") + "Mats | Recipe source | Sold / day | Rate |",
                "|---|---|---|---|---|---|" + ("---|" if eff else "")]
        for r in sorted(groups[g], key=lambda r: (r["learn"], r["name"])):
            mats = mats_cell(d, r)
            _, _, rate, _ = profit_cells(d, r)
            sells = sold_cell(d, r)
            out.append(f"| {spec_mark(d, r)}{d.link(r['item'])}{new_tag(r)} | {skill_cell(r)} | {(effect_cell(d, r) + ' | ') if eff else ''}{mats} | {d.source(r)} "
                       f"| {sells} | {rate} |")
        out.append("")
    # the user doesn't trust the profit estimate (2026-11-24): kept out of the tables, one list at the very end
    out += ["## Profit estimates", "- AH value − mats at today's AH/vendor prices; no AH cut, no deposits — not verified",
            "- Score = profit in gold × sale rate × demand (sold / day, capped at 5 a day); rows under a 20% sale rate left out", ""]  # blank line or the table won't render
    out += profit_table(d, d.recipes, False)  # no known-tick column here: it was an empty column for almost every row
    out.append("")
    dst = VAULT / "professions" / prof.lower() / "recipes.md"
    dst.write_text("\n".join(out))
    print(f"{dst}: {len(d.recipes)} recipes in {len(groups)} sections")


# ---------------------------------------------------------------- leveling-note helpers (printed, pasted on demand)
PROT_W = {"str": .4, "agi": .3, "sta": 1, "armor": .08, "def": 1.5, "hit": 4, "crit": 2, "ap": .2}
SHOW = [("str", "Str"), ("agi", "Agi"), ("sta", "Sta"), ("ap", "AP"), ("armor", "armor"), ("def", "Def"), ("hit", "% hit"),
        ("crit", "% crit"), ("dps", "dps")]


def prot_score(st, slot):
    s = sum(w * st.get(k, 0) for k, w in PROT_W.items())
    return s + (3 * st.get("dps", 0) if slot in ("One-Hand", "Main Hand") else 0)


def useful(d, mode):
    gear = cs.equipped([CHAR])
    g = gear[CHAR]
    lvl = int(g.get("level") or 1)
    rows = []
    for r in d.recipes:
        i = d.info(r["item"])
        slot, typ, req = i["slot"], i["type"], i["req"] or 0
        if not slot or req > 60 or not cs.can_equip(g["class"], slot, typ):
            continue
        new = ln.stats(r["item"])
        if mode == "arms":
            up = ln.upgrade("W", gear, r["item"])
            if not isinstance(up, (int, float)) and up != "new":
                continue
            worn = [g["gear"].get(s) for s in ((16, 17) if slot == "Two-Hand" else cs.SLOT_IDS[slot])]
        else:
            if slot == "Two-Hand" or typ in ("Cloth", "Leather", "Dagger", "Fist Weapon"):
                continue
            ids = (16,) if slot in ("One-Hand", "Main Hand") else cs.SLOT_IDS[slot]
            worn = [g["gear"].get(s) for s in ids]
            cur = min((prot_score(ln.stats(w), cs.describe(cs.tooltip(w))[0]) for w in worn if w), default=0)
            if slot in ("One-Hand", "Main Hand", "Off Hand") and worn and worn[0] and cs.describe(cs.tooltip(worn[0]))[0] == "Two-Hand":
                cur = 0  # wearing the 2H: any 1H / shield is "new" for the tank set
            nw = prot_score(new, slot)
            up = "new" if cur <= 0 else round(100 * (nw - cur) / cur)
        if up != "new" and up <= 0:
            continue
        old = ln.stats(worn[0]) if worn and worn[0] and up != "new" else {}  # "new": the item's own stats
        diff = " · ".join(f"{new.get(k, 0) - old.get(k, 0):+g}\u00a0{lab}".replace("-", "−")
                          for k, lab in SHOW if round(new.get(k, 0) - old.get(k, 0), 1))
        if up == "new":
            diff = diff.replace("+", "")
        mats = mats_cell(d, r)
        rows.append({"req": req, "up": up, "slot": slot, "row": f"| {r['learn']} | {spec_mark(d, r)}{d.link(r['item'])}{new_tag(r)} | "
                     f"{slot}{' ' + typ if typ else ''} | **{'new' if up == 'new' else f'+{up}%'}**<br>{diff} | "
                     f"{d.link(worn[0]) if worn and worn[0] else '—'} | {d.source(r)} | {mats} |"})
    print(f"## Useful for {mode.title()}\n")
    lo = lvl
    while lo <= 60:
        hi = min(lo + 3, 60)
        band = [x for x in rows if (x["req"] <= hi if lo == lvl else lo <= x["req"] <= hi)]
        if band:
            print(f"### {lo}–{hi}".replace("60–60", "60") + (" — now" if lo == lvl else ""))
            print("| Skill | Item | Slot | Gain vs worn | Replaces | Recipe source | Mats |\n|---|---|---|---|---|---|---|")
            band.sort(key=lambda x: -(10 ** 6 if x["up"] == "new" else x["up"]))
            per_slot, kept = {}, []
            for x in band:  # reading aid: best 2 per slot, 10 rows per band
                per_slot[x["slot"]] = per_slot.get(x["slot"], 0) + 1
                if per_slot[x["slot"]] <= 2 and len(kept) < 10:
                    kept.append(x)
            for x in kept:
                print(x["row"])
            print()
        lo = hi + 1


def profit_table(d, rows, known_col):
    """Profit rows sorted by "how good it is": score = profit (gold) x sale rate x demand, where demand =
    region sold/day capped at 1 from 5 a day up. Rows under a 20% sale rate are left out (listings mostly expire)."""
    out = ["| Skill | Item | " + ("✓ | " if known_col else "") + "Recipe source | Mats | Sold / day | Rate | Profit | Score |",
           "|---|---|" + ("---|" if known_col else "") + "---|---|---|---|---|---|"]
    scored = []
    for r in rows:
        pf, _, rate, p = profit_cells(d, r)
        sr = d.rate(r["item"]) or 0
        sold = d.prices.get(r["item"], {}).get("regionSoldPerDay") or 0
        if p is not None and p > 0 and sr >= .20:
            scored.append((p / 10000 * sr * min(1, sold / 5), r, pf, rate))
    for score, r, pf, rate in sorted(scored, key=lambda x: -x[0]):
        out.append(f"| {r['learn']} | {spec_mark(d, r)}{d.link(r['item'])}{new_tag(r)} | " + (f"{'✓' if r['known'] else ''} | " if known_col else "")
                   + f"{d.source(r)} | {mats_cell(d, r)} | {sold_cell(d, r)} | {rate} | {pf} | {score:.2f} |")
    return out


def to_get(d):
    """Unknown recipes with profit >= 1g at >= 30% sale rate, for leveling.md's last section."""
    rows = [r for r in d.recipes if not r["known"] and (profit_cells(d, r)[3] or 0) >= 10000 and (d.rate(r["item"]) or 0) >= .30]
    print("\n".join(profit_table(d, rows, False)))


def shop(d, spec):
    by_name = {key(r["name"]): r for r in d.recipes}
    need = {}
    for part in spec.split(","):
        name, n = part.rsplit("=", 1)
        r = by_name[key(name)]
        for i, q in r["mats"]:
            need[i] = need.get(i, 0) + q * int(n)
    by_item = {r["item"]: r for r in d.recipes}
    for i in list(need):  # one level down: a crafted mat we lack is made from its own mats (grinding stones)
        have = d.inv.get(i, {}).get("total", 0)
        if i in by_item and have < need[i] and by_item[i]["known"]:
            short = need[i] - have
            need[i] = have
            for j, q in by_item[i]["mats"]:
                need[j] = need.get(j, 0) + q * -(-short // by_item[i]["n"])
    total = 0
    print("| Mat | Need | Have | Buy | ≈ Price | Where |\n|---|---|---|---|---|---|")
    for i, n in sorted(need.items(), key=lambda kv: -kv[1] * d.mat_price(kv[0])):
        if not n:
            continue
        own = d.inv.get(i, {})
        have, buy = own.get("total", 0), max(0, n - own.get("total", 0))
        price = d.mat_price(i)
        total += buy * price
        holders = ", ".join(f"{w.split('/')[0]} {q}" for w, q in own.get("where", {}).items() if not w.startswith(CHAR))
        where = (("vendor" if i in d.vendor else f"AH ({money(price)})") if buy else "") + (f" · mail: {holders}" if holders else "")
        print(f"| {d.link(i)} | {n} | {have} | {buy} | {money(buy * price) if buy else '—'} | {where.strip(' ·')} |")
    print(f"\ntotal ≈ {money(total)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prof")
    ap.add_argument("--useful", choices=["arms", "prot"])
    ap.add_argument("--get", action="store_true")
    ap.add_argument("--shop")
    ap.add_argument("--points", nargs="?", const="", metavar="NAMES", help="skill-colour table; extra recipe names, comma separated")
    ap.add_argument("--food", choices=["warrior", "priest"])
    ap.add_argument("--skill", type=int, default=0)
    ap.add_argument("--level", type=int, default=0)
    ap.add_argument("--money", metavar="NOTE", help="restyle plain money amounts in a hand-written note")
    a = ap.parse_args()
    if a.money:
        f = Path(a.money).expanduser()
        f.write_text(style_money(f.read_text()))
        return
    d = Data(a.prof.title())
    if a.useful:
        useful(d, a.useful)
    elif a.get:
        to_get(d)
    elif a.shop:
        shop(d, a.shop)
    elif a.points is not None:
        points(d, a.skill, [n for n in a.points.split(",") if n.strip()])
    elif a.food:
        food(d, a.food, a.level)
    else:
        catalogue(d)


if __name__ == "__main__":
    main()
