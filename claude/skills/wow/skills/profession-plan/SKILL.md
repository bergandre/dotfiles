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
- **Catch-up price (always):** for every profession in the plan, one total in gold from the current skill to the
  target (benchmark for the char's level, or the next milestone): AH mats still to buy + vendor mats + plans/recipes +
  training fees if known. Owned mats count as 0; say what the total leaves out or guesses (e.g. "≈ 8g, 40 bars bought,
  rest owned"). Goes in the answer and on the first line under the note's `## Mats to get`.
- Shopping list: what to buy (qty, ~price), noting vendor-only mats (flux, spices, dyes, water) - never price those from the AH (AH can be 10x vendor).
- Gaps in the user's own mats: explain *why* they lack something (e.g. gathering skill too low for that node tier).
- Recipes: trainer vs vendor/AH plans; only recommend buying plans that are cheaper per point or useful to the character.
- Respect [profession priorities] in memory (must-keep vs postponed profs) when suggesting smelting/using shared mats.

Gathering professions (Herbalism, Mining): which node grows in which zone along the route -> `gather-zones` skill.

## Recipe catalogue + leveling note (crafting professions)
Vault layout per crafting profession (Blacksmithing 2026-11-24, Cooking 2026-11-25; Cooking has no materials.md): `professions/<prof>/leveling.md`
(rewritten on demand at each catch-up), `recipes.md` (fully generated, never hand-edited), `materials.md`; shared
`professions/merchants-favor.md` (mechanics + crate inventory). Names repeat across folders -> link by full vault path
with an alias (`[[Wow_FOREVER/professions/blacksmithing/leveling|blacksmithing]]`). Mining/Herbalism keep `<prof>/<prof>.md`.
- `recipes_catalogue.py <Prof>` writes recipes.md: every recipe grouped by item type (crafting-window order), sorted by
  skill; columns item, skill, mats (one per line), recipe source, sold / day, sale rate. Cooking groups by buff
  (Strength ... Healing and spell power, Other buffs, No buff, Other) and adds an Effect column (buff, restore, eat level).
- **Skill numbers (user, 2026-11-24):** recipes.md shows ONLY the minimum skill to learn the recipe. The four colour
  points live in leveling.md's `## Skill points` table (`--points "extra,names" --skill N`: Item | Learn | Yellow | Green |
  Grey | Recipe source, the gathering notes' `sk-o/y/g/x` spans) - known + trainer recipes that still give points, plus
  the route's plans named in `extra`. Wowhead's orange start can differ from the learn skill or be 0: show learn.
- Cooking's "Useful for ..." equivalent = `--food warrior|priest`: buff food in bands by eat level (now / 45 / 55),
  strongest first, two per buff. Section order: Progress, Recipes to get, Mats to get, Skill points, Food for the
  warrior, Food for the priest, Merchant's Favor, Profit estimates, Status and links, Notes for future sessions.
- Recipe vendors (`data/<prof>/vendors.tsv`, Horde-friendly only): item page `g_listviews['sold-by']`, keep rows with
  `react[1] == 1`. One page per navigation in browser_batch; the bot check still appeared after ~40 pages in a row
  (2026-11-25) - read at most ~30 per session. Neutral goblin vendors can be missing from that filter (plans.txt has them).
- Data = `data/<prof>/spells.txt` + `plans.txt`, cached from **Wowhead Forever** through Claude in Chrome (real Forever
  skill colours, reagents, plan sources): open `wowhead.com/forever/spells/professions/<prof>` and
  `/forever/items/recipes/<prof>`, map `g_listviews` rows to the pipe format in the script's docstring, put them in a
  `<pre>` and read with get_page_text (the JS tool truncates; the transcript jsonl holds the full text). **Never fetch
  item pages in a loop from inside the page** - ~100 quick fetches trip Wowhead's "confirm you are human" check
  (2026-11-24); vendor names for multi-vendor plans are therefore still missing (`vendor` / `?` in the Source column).
- `data/<prof>/trainers.tsv` = which trainer teaches which spell (Wowhead `npc=<id>` page, `teaches-recipe` listview: two
  page loads cover a profession; specialization trainers via the spell page's `taught-by-npc`). The Source cell always
  names the city (`trainer — Orgrimmar, Booty Bay` / `Booty Bay only` / `Armorsmith trainer (...), Orgrimmar`).
  Blacksmithing: Truesilver Gauntlets + Breastplate are **Armorsmith-only**, Blight (and by Classic inference Phantom
  Blade, The Shatterer, Truesilver Champion) **Weaponsmith-only**.
- The column is called **Recipe source** everywhere (where the plans/training come from). NPCs, objects, world drops and
  unnamed vendors in it are Wowhead Forever links; a drop also shows its chance in bold from `data/<prof>/droprates.tsv`
  (item page `dropped-by`: count/outof of the best source, read with browser_batch = navigate + JS per item, ~15 per
  call - that pace did not trip the bot check). Raid/level-60 dungeon plans have no rate cached yet.
- Profit tables: Skill | Item | Recipe source | Mats | Sold / day | Rate | Profit | Score - sorted by Score = profit (g) ×
  sale rate × min(1, sold per day / 5); rows under a 20% sale rate are dropped (agreed with the user 2026-11-24: plain
  profit × rate put Lionheart Helm, 0.4 sold a day, on top).
- Recipes show their real card: a Recipe source cell of a plans recipe starts with the plans' icon link
  (`[[Plans - X|plans]]`, hover = Wowhead tooltip incl. drop chance and the crafted item); no embedded cards in leveling.md.
- **Mats = the actual materials, always** (hard rule, user said it twice, 2026-11-24): any column or cell called Mats lists
  the real reagents with icons, one per line (`mats_cell`). A gold figure never stands in for them; a cost, if wanted,
  is its own explicitly named column.
- No sell-price column: tables show `Sold / day` (TSM `regionSoldPerDay`, region average) next to Rate (region sale rate).
- **Specialization colours (user rule, 2026-11-24):** a recipe exclusive to Armorsmith is brown, to Weaponsmith (and the
  Master Sword/Axe/Hammersmith sub-specs) red - the item link and its plans link alike. Put the empty marker
  `<span class="spec-armor"></span>` / `spec-weapon` at the start of the row or list line; wow.css colours every link in
  that row/line (wiki links inside an HTML span don't render, hence the marker). `spec()` decides: spec trainer in
  trainers.tsv, or "Requires Armorsmith/Weaponsmith" in the plans or item tooltip.
- The column that shows the crafted item is called **Item** (not Recipe); the recipe itself (plans card) is in Recipe source.
- No known-tick (✓) column anywhere in recipes.md or leveling.md (user removed it everywhere, 2026-11-24).
- **NEW IN FOREVER tag (hard rule, user 2026-11-24):** every recipe/item that Wowhead marks new in Forever (spells.txt
  status `new`; on a page: `envChange.status`) carries `<span class="wf-new">NEW IN FOREVER</span>` right after its
  link - in every table and list, generated or hand-written.
- A quest named as a source is always a link to Wowhead Forever (`[Name](https://www.wowhead.com/forever/quest=<id>)`),
  in generated and hand-written lines alike (user, 2026-11-24).
- `data/<prof>/overrides.tsv` = hand-kept per-recipe source/notes (regex on the name); the only place for remarks that
  must survive regeneration.
- **Profit is not trusted by the user** (2026-11-24): never in the main tables or next to a recipe. recipes.md keeps
  Sells + Rate columns and one `## Profit estimates` table at the very end; leveling.md ends with
  `## Profit estimates — not verified`. Both are tables sorted by profit × sale rate ("how good it is"). No "profit" reason in Recipes to get.
- leveling.md frontmatter `cssclasses: [prof-leveling]` (recipes.md: `prof-recipes`) - wow.css keeps one-mat-per-line
  cells unwrapped for those classes.
- leveling.md section order ends: … Merchant's Favor → Profit estimates → Status and links → `Notes for future sessions`
  (always the very last thing in the file: it exists only for AI context).
- Under the leveling.md title there is ONLY the section list; the status line (level, skill, target) and the links
  line (recipes, materials, Favor) live in a last section `## Status and links` (user, 2026-11-24).
- Obsidian re-pads a table's source when the user touches it in Live Preview (`| Skill | Recipe      |`): find tables in an
  existing note by regex (`^\| Skill`), never by an exact header string.
- A table needs a blank line above it: right under a bullet list Obsidian shows the raw `| … |` text (2026-11-24).
- Both notes start with a `## Contents` list: one clickable line per section (`- [[#Progress]]`), plain sub-sections
  nested under it (`  - [[#Useful for Arms#44–47 — now|44–47 — now]]`) - a real list, never one dotted line; keep headings plain
  (no HTML, dates or amounts) so those links work - range, total and date go on the first line under `## Mats to get`.
- leveling.md sections, in order: Progress (full ticked history kept, then the road to 300, far steps marked `guide`) ->
  Recipes to get (unknown recipes that are on the leveling route or an upgrade for the MAIN spec (Arms) only - no off-spec (Prot)
  recipes unless asked; each line says why in words and labels the number (`skill 210`), the user asked "why do I need
  205 Heavy Mithril Breastplate" when it was a bare number + "Prot";
  one table, sorted by skill: Skill | Item | Why | Recipe source | Cost - the user tried tick-box lines with embedded
  cards and went back to a plain table, 2026-11-24) -> `Mats to get` (first line: `<from> → <to> — ≈ Ng (date)`; next step only; Need/Have/Buy) ->
  Useful for Arms -> Useful for Prot (4-level bands from the char's level, all slots in one table, upgrades over worn
  gear only, best 2 per slot, sorted by gain; consumables separate); columns Skill | Item | Slot | Gain vs worn | Replaces | Recipe | Mats
  (real mats with icons, one per line - no cost, no known-tick column) -> Merchant's Favor (ranked spending list, one
  "next" line) -> `Notes for future sessions` (free text for AI context - the one allowed exception to "no AI notes in
  the vault"). Helpers print the tables: `--useful arms|prot`, `--get`, `--shop "<Recipe>=N,..."`.

## 5. "Anything useful for my character?"
Check char level + equipped gear (BagBrother), then: Forever-only plans that fill empty/weak slots, self-buff consumables, campsite objects, currency-gated plans (Merchant's Favor from Waylaid Crates - don't sell crates), and long-term milestones. Custom Forever items (IDs > ~200000) have no local stats - say "unknown, compare tooltips".

## Output
Terse (user preference): one route table, one shopping list with the catch-up price total per profession, 2-3 bullets of caveats, sources as markdown links. Don't claim certainty on Forever ranges/stats you couldn't verify.
