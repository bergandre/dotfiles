#!/usr/bin/env python3
"""Collect data for a WoW Forever dungeon cheatsheet.

usage: python3 -I cheatsheet.py "<Dungeon>" [--slug SLUG] [--chars "Karums Warrior,Karums Priest"]
                                [--map-out FILE.png] [--no-map]

1. Map: foreverchanges.pro map image + boss pins (drawn as numbered markers);
   fallback = local InstanceAtlas TGA without markers.
2. Bosses in path order + Forever loot IDs from local AtlasLoot (data-forever.lua).
3. Item stats from Wowhead Forever tooltips (cached), and what each char wears in that slot
   (BagBrother.lua), with a simple can-equip flag. Judging upgrades is left to the caller.
"""
import argparse
import html
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO = Path(os.environ.get("WOW_REPO", "~/repositories/wow-forever-addon-settings")).expanduser()
ATLASLOOT = REPO / "Interface/AddOns/AtlasLootContinued_DungeonsAndRaids/data-forever.lua"
IA_MAPS = REPO / "Interface/AddOns/InstanceAtlas/Maps"
SITE = "https://foreverchanges.pro"
TOOLTIP = "https://nether.wowhead.com/forever/tooltip/item/{}"
CACHE = Path("~/.cache/wow-tooltips").expanduser()
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) wow-cheatsheet"}

SLOT_IDS = {  # tooltip slot text -> inventory slot ids (BagBrother equip index)
    "Head": [1], "Neck": [2], "Shoulder": [3], "Chest": [5], "Robe": [5], "Waist": [6],
    "Legs": [7], "Feet": [8], "Wrist": [9], "Hands": [10], "Finger": [11, 12],
    "Trinket": [13, 14], "Back": [15], "Main Hand": [16], "One-Hand": [16, 17],
    "Two-Hand": [16], "Off Hand": [17], "Held In Off-hand": [17], "Ranged": [18],
    "Thrown": [18], "Relic": [18],
}
SLOT_NAMES = {1: "head", 2: "neck", 3: "shoulder", 5: "chest", 6: "waist", 7: "legs", 8: "feet",
              9: "wrist", 10: "hands", 11: "ring1", 12: "ring2", 13: "trinket1", 14: "trinket2",
              15: "back", 16: "main hand", 17: "off hand", 18: "ranged"}
# What each class can equip (Classic rules; warrior mail/plate at 40 -> plate needs 40).
CAN = {
    "WARRIOR": {"armor": {"Cloth", "Leather", "Mail", "Plate"},
                "weapon": {"Axe", "Sword", "Mace", "Dagger", "Fist Weapon", "Polearm", "Staff",
                           "Bow", "Crossbow", "Gun", "Thrown", "Shield"}},
    "PRIEST": {"armor": {"Cloth"}, "weapon": {"Mace", "Dagger", "Staff", "Wand"}},
}


def get(url, binary=False):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        data = r.read()
    return data if binary else data.decode("utf-8", "replace")


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower().replace("'", "")).strip("-")


# ---------- tooltips ----------
def tooltip(item_id):
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{item_id}.json"
    if not f.exists():
        try:
            f.write_text(get(TOOLTIP.format(item_id)))
        except Exception as e:  # noqa: BLE001 - report and keep going
            return {"id": item_id, "name": f"?{item_id}", "err": str(e), "lines": []}
    d = json.loads(f.read_text())
    t = re.sub(r"<!--.*?-->", "", d.get("tooltip", ""), flags=re.S)
    t = re.sub(r"<br\s*/?>|</tr>|</th>|</td>|<table[^>]*>", "\n", t)
    lines = [l.strip() for l in html.unescape(re.sub(r"<[^>]+>", "", t)).split("\n") if l.strip()]
    return {"id": item_id, "name": d.get("name", f"?{item_id}"), "q": d.get("quality"), "lines": lines}


def describe(tt):
    """slot, type, req level, compact stat string."""
    L = tt["lines"]
    slot = next((l for l in L if l in SLOT_IDS), None)
    typ = None
    if slot:
        i = L.index(slot)
        if i + 1 < len(L) and not re.match(r"^[\d+-]", L[i + 1]):
            typ = L[i + 1]
    req = next((int(m.group(1)) for l in L if (m := re.match(r"Requires Level (\d+)", l))), None)
    skip = re.compile(r"^(Item Level|Binds|Unique|Durability|Requires|Sell Price|Dropped by|Classes)")
    stats = [l for l in L[1:] if not skip.match(l) and l not in (slot, typ)]
    stats = [re.sub(r"Sell Price.*", "", s) for s in stats]
    return slot, typ, req, "; ".join(s for s in stats if s)


def can_equip(cls, slot, typ):
    if slot is None:
        return False
    c = CAN.get(cls)
    if not c:
        return True
    if typ in c["armor"] or typ in c["weapon"]:
        return True
    if slot in ("Neck", "Finger", "Trinket", "Back") or typ is None:
        return True
    return False


# ---------- local data ----------
def atlasloot_bosses(dungeon):
    s = ATLASLOOT.read_text(errors="replace")
    keys = re.findall(r'data\["([^"]+)"\]\s*=\s*\{', s)
    want = re.sub(r"[^a-z]", "", dungeon.lower())
    key = next((k for k in keys if want in k.lower()), None)
    if not key:
        sys.exit(f"No AtlasLoot Forever entry matching '{dungeon}'. Keys: {', '.join(keys)}")
    start = s.index(f'data["{key}"]')
    nxt = re.search(r'\ndata\["', s[start + 10:])
    body = s[start: start + 10 + nxt.start()] if nxt else s[start:]
    bosses = []
    for blk in re.split(r"\n\t\t\{\s*--", body)[1:]:
        name = re.search(r'name\s*=\s*AL\["([^"]+)"\]', blk) or re.search(r'name\s*=\s*"([^"]+)"', blk)
        if not name:
            continue
        lvl = re.search(r"Level\s*=\s*(?:GetForVersion\()?(\d+)", blk)
        items = [int(i) for i in re.findall(r"\{\s*\d+,\s*(\d+)\s*\}", blk)]
        bosses.append({"name": name.group(1), "level": lvl and int(lvl.group(1)), "items": items})
    return key, bosses


def equipped(chars):
    out = {}
    for f in (REPO / "WTF/Account").glob("*/SavedVariables/BagBrother.lua"):
        lua = ("dofile(%r) for r,cs in pairs(BrotherBags) do for c,d in pairs(cs) do "
               "if type(d)=='table' and d.equip then local t={} for i=1,19 do local e=d.equip[i] "
               "if e then t[#t+1]=i..'='..tostring(type(e)=='table' and (e.link or e[1]) or e) end end "
               "print(c..'|'..tostring(d.class)..'|'..tostring(d.level)..'|'..table.concat(t,' ')) end end end") % str(f)
        res = subprocess.run(["lua", "-e", lua], capture_output=True, text=True)
        for line in res.stdout.splitlines():
            c, cls, lvl, gear = line.split("|", 3)
            if c in chars:
                g = {}
                for kv in gear.split():
                    i, link = kv.split("=", 1)
                    g[int(i)] = int(link.split(":")[0])
                out[c] = {"class": cls, "level": lvl, "gear": g, "file": str(f)}
    return out


# ---------- map ----------
def build_map(slug, out, dungeon, order):
    pins, maps = [], []
    try:
        page = get(f"{SITE}/dungeons/{slug}")
        pins = [(n, float(x), float(y)) for x, y, n in re.findall(
            r'class="dgx-pin[^"]*" style="left:([\d.]+)%;top:([\d.]+)%" aria-label="([^"]+)"', page)]
        maps = list(dict.fromkeys(re.findall(r'(/dungeons/maps/[^"\')\s]+\.(?:webp|png|jpg))', page)))
    except Exception as e:  # noqa: BLE001
        print(f"[map] {SITE} failed: {e}")
    rank = {n: i for i, n in enumerate(order)}
    pins.sort(key=lambda p: rank.get(p[0], 99))
    src = None
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".src")
    if maps:
        tmp.write_bytes(get(SITE + maps[0], binary=True))
        src = f"{SITE}{maps[0]}"
        if len(maps) > 1:
            print(f"[map] {len(maps)} map images on page, used the first: {maps}")
    else:
        local = [p for p in IA_MAPS.glob("*.tga") if re.sub(r"[^a-z]", "", dungeon.lower())
                 in re.sub(r"[^a-z]", "", p.stem.lower())]
        if not local:
            print("[map] no map found - search the web manually")
            return None
        tmp.write_bytes(local[0].read_bytes())
        src = str(local[0])
        pins = []
    size = subprocess.run(["magick", "identify", "-format", "%w %h", str(tmp)],
                          capture_output=True, text=True).stdout.split()
    w, h = int(size[0]), int(size[1])
    r = max(11, w // 70)
    cmd = ["magick", str(tmp), "-strokewidth", "3"]
    for n, (name, x, y) in enumerate(pins, 1):
        cx, cy = round(w * x / 100), round(h * y / 100)
        cmd += ["-fill", "#b3261e", "-stroke", "white", "-draw", f"circle {cx},{cy} {cx + r},{cy}",
                "-stroke", "none", "-fill", "white", "-pointsize", str(int(r * 1.3)), "-gravity", "NorthWest",
                "-annotate", f"+{cx - r // 2 - (r // 3 if n > 9 else 0)}+{cy - int(r * 0.8)}", str(n)]
    cmd.append(str(out))
    subprocess.run(cmd, check=True)
    tmp.unlink()
    print(f"[map] {out}  (source: {src}; {len(pins)} pins)")
    for n, (name, x, y) in enumerate(pins, 1):
        print(f"  {n}. {name}")
    missing = [b for b in order if b not in {p[0] for p in pins} and b != "Trash"]
    if missing:
        print(f"  no pin on the source map: {', '.join(missing)}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dungeon")
    ap.add_argument("--slug", help="foreverchanges.pro slug (default: from name)")
    ap.add_argument("--chars", default="Karums Warrior,Karums Priest")
    ap.add_argument("--map-out", type=Path)
    ap.add_argument("--no-map", action="store_true")
    a = ap.parse_args()
    chars = [c.strip() for c in a.chars.split(",")]

    key, bosses = atlasloot_bosses(a.dungeon)
    if not a.no_map:
        out = a.map_out or Path(f"~/Documents/obsidian/gaming/Wow_FOREVER/dungeons/maps/{a.dungeon}.png").expanduser()
        build_map(a.slug or slugify(a.dungeon), out, a.dungeon, [b["name"] for b in bosses])
    gear = equipped(chars)
    print(f"\n# Bosses + loot (AtlasLoot {key}, path order)")
    for c in chars:
        g = gear.get(c)
        print(f"- {c}: " + (f"{g['class']} lvl {g['level']}" if g else "NOT FOUND in BagBrother"))

    for b in bosses:
        print(f"\n## {b['name']} (lvl {b['level']})")
        for iid in b["items"]:
            tt = tooltip(iid)
            slot, typ, req, stats = describe(tt)
            if tt.get("err"):
                continue  # not a real item id (AtlasLoot spacer/level entry)
            if slot is None:
                print(f"- {tt['name']} [{iid}] (not gear)")
                continue
            print(f"- {tt['name']} [{iid}] q{tt.get('q')} {slot}/{typ or '-'} req{req}: {stats}")
            for c in chars:
                g = gear.get(c)
                if not g or not can_equip(g["class"], slot, typ):
                    continue
                worn = []
                for sid in SLOT_IDS[slot]:
                    w = g["gear"].get(sid)
                    if w:
                        wt = tooltip(w)
                        worn.append(f"{SLOT_NAMES[sid]}: {wt['name']} [{w}] {describe(wt)[3]}")
                    else:
                        worn.append(f"{SLOT_NAMES[sid]}: EMPTY")
                print(f"    {c} wears -> " + " | ".join(worn))


if __name__ == "__main__":
    main()
