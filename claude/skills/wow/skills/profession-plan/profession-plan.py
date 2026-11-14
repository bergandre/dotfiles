#!/usr/bin/env python3
"""Local-data snapshot for planning a profession level-up on WoW Forever.

Prints: character skill levels, known recipes, every recipe that still gives skill-ups
(AtlasLoot ranges -- these are CLASSIC ranges, verify against Forever web guides),
mat cost at realm market, what you already own of each mat, and the recipe source
(trainer vs plan item + its AH price).

Usage: profession-plan.py Cooking [--skill N] [--window 75]
"""
import os
import argparse, importlib.util, re, subprocess
from pathlib import Path

ROOT = Path(os.environ.get("WOW_REPO", "~/repositories/wow-forever-addon-settings")).expanduser()
spec = importlib.util.spec_from_file_location("t", ROOT / "tsm-analyze.py")
assert spec and spec.loader
t = importlib.util.module_from_spec(spec); spec.loader.exec_module(t)
PROF_IDS = {v: k for k, v in t.PROF_NAMES.items()}

KNOWN_LUA = r'''
local f = assert(io.open(arg[1], "rb")); local src = f:read("a"):gsub("\r", ""); f:close()
local env = {}; assert(load(src, "sv", "t", env))()
for key, crafts in pairs(env.TradeSkillMasterDB) do
  if key:match("@internalData@crafts$") and type(crafts) == "table" then
    for id, r in pairs(crafts) do
      if r.profession == arg[2] then
        for p in pairs(r.players or {}) do print(id:match("%d+") .. "\t" .. r.name .. "\t" .. p) end
      end
    end
  end
end'''


def known_recipes(prof):
    known = {}
    for sv in (ROOT / "WTF/Account").glob("*/SavedVariables/TradeSkillMaster.lua"):
        out = subprocess.run(["lua", "-", str(sv), prof], input=KNOWN_LUA, capture_output=True, text=True).stdout
        for line in out.splitlines():
            sid, name, who = line.split("\t")
            known.setdefault(int(sid), (name, set()))[1].add(who)
    return known


def char_levels():
    lv = {}
    for f in (ROOT / "WTF/Account").glob("*/SavedVariables/NovaInstanceTracker.lua"):
        txt = f.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r'\["level"\] = (\d+),', txt):
            pre = txt[max(0, m.start() - 4000):m.start()]
            names = re.findall(r'\n\["([A-Z][^"]+)"\] = \{', pre)
            if names:
                lv[names[-1]] = int(m.group(1))
    return lv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prof")
    ap.add_argument("--skill", type=int, help="override current skill (default: best char from TSM)")
    ap.add_argument("--window", type=int, default=75, help="show recipes learnable up to skill+window")
    a = ap.parse_args()
    prof = a.prof.title()
    pid = PROF_IDS[prof]

    t.CHAR_PROFS.update(t.load_char_professions())
    holders = t.CHAR_PROFS.get(prof, {})
    skill = a.skill if a.skill is not None else t.best_skill(prof)
    print(f"# {prof}: skill per char {dict(holders)} -> planning from {skill}")
    mine = set(t.load_char_classes())
    print(f"# your char levels (NovaInstanceTracker): {({c: l for c, l in char_levels().items() if c in mine})}")

    prices, names, inv = t.load_prices(), t.load_names(), t.load_inventory()
    spell_names = {int(s): re.sub(r'(\s*/\s*\d+)+$', '', n.strip())
                   for s, n in re.findall(r'\{\s*\d+,\s*(\d+)\s*\},\s*--(.+)', t.ATLAS_NAMES.read_text(encoding="utf-8"))}
    plans = {}
    for item, p, _, spell in re.findall(r'\[(\d+)\]\s*=\s*\{\s*(\d+),\s*(\d+),\s*(\d+)\s*\}',
                                            (t.ADDONS / "AtlasLootContinued/Data/Recipe.lua").read_text(encoding="utf-8")):
        if int(p) == pid:
            plans[int(spell)] = int(item)
    known = known_recipes(prof)

    def mkt(i):
        p = prices.get(i, {})
        return p.get("marketValueRecent") or p.get("marketValue") or p.get("regionMarketValue") or 0

    print(f"\n## Known recipes ({len(known)})")
    for sid, (name, who) in sorted(known.items(), key=lambda kv: kv[1][0]):
        print(f"- {name} [{sid}] ({', '.join(sorted(who))})")

    print(f"\n## Recipes with skill-ups (grey > {skill}, learn <= {skill + a.window}); ranges are CLASSIC (AtlasLoot)")
    print("| Recipe | learn/yellow/grey | Known | Cost/craft | Mats (have) | Source |")
    print("|---|---|---|---|---|---|")
    pat = re.compile(r'\[(\d+)\]\s*=\s*\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*\{([^}]*)\},\s*\{([^}]*)\}')
    rows = []
    for spell, _, p, learn, yel, grey, reag, cnt in pat.findall(t.ATLAS_RECIPES.read_text(encoding="utf-8")):
        spell, learn, yel, grey = int(spell), int(learn), int(yel), int(grey)
        if int(p) != pid or spell not in spell_names or grey <= skill or learn > skill + a.window:
            continue
        r = [int(x) for x in reag.split(",") if x.strip()]
        c = [int(x) for x in cnt.split(",") if x.strip()]
        cost = sum(mkt(i) * n for i, n in zip(r, c))
        mats = ", ".join(f"{n}x {names.get(i, i)} ({inv[i]['total'] if i in inv else 0})" for i, n in zip(r, c))
        pl = plans.get(spell)
        src = "trainer?" if not pl else f"plan {pl} {names.get(pl, '')} AH {t.money(mkt(pl)) if mkt(pl) else 'n/a'}"
        rows.append((learn, f"| {spell_names[spell]} | {learn}/{yel}/{grey} | {'yes' if spell in known else ''} | {t.money(cost)} | {mats} | {src} |"))
    for _, row in sorted(rows):
        print(row)
    unknown_known = [n for sid, (n, _) in known.items() if sid not in spell_names]
    if unknown_known:
        print(f"\nForever-custom known recipes (no AtlasLoot ranges, check in-game color): {', '.join(sorted(unknown_known))}")


if __name__ == "__main__":
    main()
