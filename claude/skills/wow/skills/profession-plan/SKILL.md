---
name: profession-plan
description: Plan leveling a WoW Forever profession (Blacksmithing, Cooking, Engineering, ...) from the user's real data - skill, known recipes, owned mats, AH prices - cross-checked with Forever web guides, plus what the profession offers the character (gear, Forever-only plans, currency). Use when the user asks how to level a profession, what to buy/craft next, or whether a profession has anything useful for their character.
---

# Profession leveling plan (WoW Forever)

Repo with the game data: `~/repositories/wow-forever-addon-settings` (paths below are relative to it; `WOW_REPO` env overrides).

Goal: a short, costed route from the current skill to the next real milestone, built from the user's own data and verified against **Forever** guides (not Classic Era).

## 1. Make sure data is fresh
Saved variables only update on `/reload` or logout. If skill/inventory looks off vs. what the user says, ask them to `/reload` the relevant characters first.

## 2. Local snapshot (one command)
```
python3 ~/.claude/skills/wow/skills/profession-plan/profession-plan.py <Profession> [--skill N] [--window 75]
```
Prints current skill per char, char levels, known recipes, every recipe still giving skill-ups with cost/craft, owned mats per recipe, and source (trainer vs plan item + AH price).
For single items use `python3 tsm-analyze.py --item "<name>"` (holders, price, uses).

Other sources if needed:
- Zygor route: `Interface/AddOns/ZygorGuidesViewerForever/Guides-Forever/Professions/ZygorProfessions{Horde,Common}CLASSIC.lua` -> `RegisterGuide("Profession Guides\\<Prof>\\...")`, steps after `label "Begin_Profession_Leveling"` (Train/learn/collect lines).
- Equipped gear: `WTF/Account/*/SavedVariables/BagBrother.lua` `equip` array (1-based slot ids: 1 head, 3 shoulder, 5 chest, 10 hands, 16 MH). **Syndicator.lua is stale - don't use it.**
- Currencies (Merchant's Favor): `TitanCurrenciesMulti.lua` -> `TITAN_FOREVER_MERCHANTSFAVOR`.

## 3. Cross-check on the web (required)
AtlasLoot and Zygor carry **Classic Era** skill ranges; Forever changed many (often grey ~25 earlier, some learn levels lower). Always WebFetch at least two Forever guides and prefer them for ranges:
- `https://www.wow-professions.com/forever/<prof>-leveling-guide`
- `https://www.method.gg/wow-forever/` (search "<prof> in wow forever leveling guide")
- `https://warcraft.wiki.gg/wiki/Forever_<prof>_plans` (Forever-only recipes, sources) / `..._recipes`
- Vendor pages on wow-professions.com/forever/npc/<name> (Merchant's Favor plans)
icy-veins and wowvendor return 403 to WebFetch - skip them. Guides disagree on ranges: say so and tell the user to check recipe color in-game.

## 4. Build the plan
- Route table: skill range | recipe | crafts | mats | source. Merge the guides; pick the cheapest per skill point using local prices and what the user already owns.
- Shopping list: what to buy (qty, ~price), noting vendor-only mats (flux, spices, dyes, water) - never price those from the AH (AH can be 10x vendor).
- Gaps in the user's own mats: explain *why* they lack something (e.g. gathering skill too low for that node tier).
- Recipes: trainer vs vendor/AH plans; only recommend buying plans that are cheaper per point or useful to the character.
- Respect [profession priorities] in memory (must-keep vs postponed profs) when suggesting smelting/using shared mats.

## 5. "Anything useful for my character?"
Check char level + equipped gear (BagBrother), then: Forever-only plans that fill empty/weak slots, self-buff consumables, campsite objects, currency-gated plans (Merchant's Favor from Waylaid Crates - don't sell crates), and long-term milestones. Custom Forever items (IDs > ~200000) have no local stats - say "unknown, compare tooltips".

## Output
Terse (user preference): one route table, one shopping list, 2-3 bullets of caveats, sources as markdown links. Don't claim certainty on Forever ranges/stats you couldn't verify.
