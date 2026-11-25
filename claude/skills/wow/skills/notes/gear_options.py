"""Every obtainable gear option for one slot of a character, scored - the source list for <Spec>/Weapons.md.

usage: python3 -I gear_options.py --char "Karums Warrior" --role W --slot 2h
                                  [--min 35 --max 50] [--faction Horde] [--note "<vault-relative Weapons.md>"]

Sources (all local, tooltips from the Wowhead Forever cache/API):
  - ForeverDungeonJournal Dungeons.lua: boss + trash loot, dungeon quests' rewardItems (+ follow-ups such as
    A Tale Spun Around the Fire) with the quest's faction; SharedLoot.lua (items many bosses drop)
  - AtlasLoot data-forever.lua: every dungeon/raid loot table (catches items FDJ lacks)
Not covered (check by hand): zone/class quest rewards (Whirlwind Axe), world drops, vendors, crafted
(own Blacksmithing - professions/blacksmithing).

Score = loot_note.score() (W: 7*2H DPS + Str + .5 AP + .8 Sta ...; P: healing, mp5, Int, Spi).
Lists everything that beats what the char wears now. With --note: every candidate missing from the
note that scores >= the median option the note lists for that level band is printed as MISSING -
add it or reject it on purpose.
"""
import argparse
import concurrent.futures as cf
import importlib.util
import re
import statistics
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
VAULT = Path("~/Documents/obsidian/gaming/Wow_FOREVER").expanduser()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ln = load("loot_note", HERE.parent / "dungeon-cheatsheet/loot_note.py")
cs = ln.cs
FDJ = cs.REPO / "Interface/AddOns/ForeverDungeonJournal/Data"

# Dungeons.lua expects the addon namespace (FDJ.Constants...); stub it and dump rows as TSV.
LUA = r"""
local any; any = setmetatable({}, {__index=function() return any end, __call=function() return "" end})
FDJ = {Constants=any, RareLabelText=function() return "" end}; _G.ForeverDungeonJournal_NS = FDJ
assert(loadfile(DIR .. "/Dungeons.lua"))("FDJ", FDJ)
assert(loadfile(DIR .. "/SharedLoot.lua"))("FDJ", FDJ)
local function row(...) local t = {...} for i = 1, #t do t[i] = tostring(t[i] or "") end print(table.concat(t, "\t")) end
for dname, d in pairs(FDJ.DB) do
  for _, q in ipairs(d.quests or {}) do
    for _, it in ipairs(q.rewardItems or {}) do
      row("quest", dname, d.level, q.name, q.faction, q.level, it[1], it[2], "") end
  end
  for _, b in ipairs(d.bosses or {}) do
    if type(b) == "table" then for _, it in ipairs(b.loot or {}) do
      row(b.trash and "trash" or "boss", dname, d.level, b.name, "", "", it[1], it[2], it[3]) end end
  end
end
for dname, bosses in pairs(FDJ.SHARED_BY_BOSS) do
  for bname, list in pairs(bosses) do for _, it in ipairs(list) do
    row("shared", dname, (FDJ.DB[dname] or {}).level, bname, "", "", it[1], it[2], it[3]) end end
end
"""

SLOTS = {"2h": {"Two-Hand"}, "1h": {"One-Hand", "Main Hand"}, "shield": {"Off Hand"}}


def fdj_rows():
    res = subprocess.run(["lua", "-e", f"DIR={str(FDJ)!r}" + LUA], capture_output=True, text=True)
    if res.returncode:
        sys.exit("FDJ load failed:\n" + res.stderr)
    out = []
    for l in res.stdout.splitlines():
        kind, dg, dlv, src, fac, qlv, iid, name, typ = l.split("\t")
        lo = re.match(r"(\d+)", dlv)
        out.append(dict(kind=kind, dungeon=dg, dlvl=int(lo[1]) if lo else None, src=src, faction=fac,
                        qlvl=int(qlv) if qlv.isdigit() else None, id=int(iid), name=name, typ=typ))
    return out


def atlasloot_rows():
    s = cs.ATLASLOOT.read_text(errors="replace")
    out = []
    for m in re.finditer(r'\ndata\["([^"]+)"\]\s*=\s*\{', s):
        nxt = s.find('\ndata["', m.end())
        body = s[m.end(): nxt if nxt >= 0 else len(s)]
        for blk in re.split(r"\n\t\t\{\s*--", body)[1:]:
            name = re.search(r'name\s*=\s*AL\["([^"]+)"\]', blk) or re.search(r'name\s*=\s*"([^"]+)"', blk)
            for iid in re.findall(r"\{\s*\d+,\s*(\d+)\s*\}", blk):
                out.append(dict(kind="atlasloot", dungeon=m[1].removesuffix("Forever"), dlvl=None,
                                src=name[1] if name else "?", faction="", qlvl=None, id=int(iid), name="", typ=""))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--char", default="Karums Warrior")
    ap.add_argument("--role", default="W", choices=["W", "P"])
    ap.add_argument("--slot", default="2h", help="2h | 1h | shield | a tooltip slot text (Head, Finger, ...)")
    ap.add_argument("--min", type=int, default=0)
    ap.add_argument("--max", type=int, default=60)
    ap.add_argument("--faction", default="Horde")
    ap.add_argument("--note", help="vault-relative gear note to check, e.g. 'characters/Karums Warrior/Arms/Weapons.md'")
    a = ap.parse_args()
    slots = SLOTS.get(a.slot.lower(), {a.slot})

    gear = cs.equipped([a.char]).get(a.char)
    if not gear:
        sys.exit(f"{a.char} not in BagBrother")
    rows = [r for r in fdj_rows() if r["faction"] in ("", "Both", a.faction)] + atlasloot_rows()
    # FDJ boss loot carries the slot text ("Two-Hand, Mace") -> skip other slots without a tooltip fetch
    typs = {}
    for r in rows:
        if r["typ"]:
            typs.setdefault(r["id"], set()).add(r["typ"])
    need = {r["id"] for r in rows if r["id"] not in typs or any(s in t for t in typs[r["id"]] for s in slots)}
    with cf.ThreadPoolExecutor(8) as ex:
        tts = dict(zip(need, ex.map(cs.tooltip, need)))

    def item_score(iid, bonus=None):
        slot = cs.describe(cs.tooltip(iid, bonus))[0]
        return ln.score(a.role, ln.stats(iid, bonus), slot)

    worn = [gear["gear"].get(i) for s in slots for i in cs.SLOT_IDS.get(s, [])]
    worn = [w for w in dict.fromkeys(worn) if w]
    if "Two-Hand" in slots:
        worn = [gear["gear"].get(16)]
    cur = min((item_score(w) for w in worn if w), default=0)

    cands = {}
    for iid, tt in tts.items():
        if not tt["lines"] or ln.RECIPE.match(tt["name"]):
            continue  # recipe tooltips embed the crafted item, slot line included
        slot, typ, req, _ = cs.describe(tt)
        if slot not in slots or not cs.can_equip(gear["class"], slot, typ):
            continue
        if a.slot.lower() == "shield" and typ != "Shield":
            continue
        st = ln.stats(iid)
        if st.get("random"):
            continue
        srcs = [r for r in rows if r["id"] == iid]
        ilvl = next((int(m[1]) for l in tt["lines"] if (m := re.match(r"Item Level (\d+)", l))), None)
        lvl = req or next((r["qlvl"] for r in srcs if r["qlvl"]), None) or (ilvl - 5 if ilvl else None)
        if lvl is None or not a.min <= lvl <= a.max:
            continue
        sc = ln.score(a.role, st, slot)
        if sc <= cur:
            continue
        best = sorted(srcs, key=lambda r: r["kind"] == "atlasloot")[0]
        where = {"quest": f"quest {best['src']}", "trash": "trash", "shared": f"shared ({best['src']})"}
        src = f"{best['dungeon']} — {where.get(best['kind'], best['src'])}"
        cands[iid] = dict(name=tt["name"], lvl=lvl, req=req, score=sc, st=st, typ=typ, src=src)

    note_names, bands = set(), []
    if a.note:
        text = (VAULT / a.note).read_text(encoding="utf-8")
        note_names = set(re.findall(r"\[\[([^\]|\\]+)", text))
        for m in re.finditer(r"^## (\d+)[–-](\d+)(.*?)(?=^## |\Z)", text, re.M | re.S):
            ids = []
            for n in re.findall(r"\[\[([^\]|\\]+)", m[3]):
                card = VAULT / "items" / f"{n}.md"
                idm = card.exists() and re.search(r"^id:\s*(\d+)", card.read_text(encoding="utf-8"), re.M)
                if idm:
                    ids.append(item_score(int(idm[1])))
            bands.append((int(m[1]), int(m[2]), statistics.median(ids) if ids else None))

    print(f"{a.char} ({a.role}) {'/'.join(sorted(slots))}: now scores {cur:.0f}; {len(cands)} better options")
    missing = 0
    for iid, c in sorted(cands.items(), key=lambda kv: (kv[1]["lvl"], -kv[1]["score"])):
        flag = ""
        if a.note and c["name"] not in note_names:
            band = next((b for b in bands if c["lvl"] <= b[1]), None)  # below the first band = usable now
            if band and band[2] is not None and c["score"] >= band[2]:
                flag, missing = "MISSING ", missing + 1
            else:
                flag = "-       "
        elif a.note:
            flag = "in note "
        st = ", ".join(f"{v:g} {k}" for k, v in c["st"].items())
        print(f"{flag}L{c['lvl']:<3} {c['score']:5.0f}  {c['name'][:30]:30} {c['typ'] or '':8} {st[:46]:46} | {c['src']} ({iid})")
    if a.note:
        print(f"\n{missing} MISSING (score >= the median option of their band; lower bands count as the first). Not scanned: zone/class quests, "
              "world drops, vendors, crafted.")


if __name__ == "__main__":
    main()
