---
name: gather-zones
description: Build a WoW Forever gathering-profession note (Herbalism, Mining) in the Obsidian vault for any Horde character, level 1-60 / skill 1-300 - clickable zone index, skill Targets by character level, per-zone sections along the RestedXP Forever Horde route (questing + dungeon guide) with a node-dot map and a table of every herb/ore there (share of nodes, orange/yellow/green/grey skill), plus colour lines on the item cards. Use when the user asks which herbs/ores grow where, what skill they need for a zone, or wants such a note for a gathering profession.
---

# Gathering zone note (WoW Forever)

Output: `~/Documents/obsidian/gaming/Wow_FOREVER/professions/<prof>.md`, maps in `professions/maps/<Zone> <herbs|ore>.png`,
`Requires <Prof> N` + colour line on each item card in `items/`. Reference results: `professions/herbalism.md`, `professions/mining.md`.
Every run also rewrites `professions/profession-benchmarks.md`: skill to have at every level 1-60 for **every**
profession (alts have other profs), header links to `professions/<prof>.md`. Columns = `BENCH_GROUPS` in the script
(user's order: Mining/Blacksmithing/Engineering | Cooking/Fishing | Herbalism/Alchemy | Skinning/Leatherworking |
Tailoring/Enchanting/First Aid):
Herbalism/Mining = Targets from config interpolated between levels; Skinning = skill to skin mobs of your level
(Classic: <=10 -> 1, 11-20 -> (L-10)*10, 21+ -> L*5); crafting + Cooking/First Aid/Fishing = 5 x level (rule of thumb).
A new route-based profession: add its config and switch its `BENCH_GROUPS` entry to "route".
Styled by `cssclasses: [prof-bench]`; the script regenerates the `prof-bench:start`…`end` block in wow.css from
`BENCH_GROUPS` (themed colour per profession, gold line before each group, sticky header + level column).
Top of that note: contents list, then a section per played character from `config/chars.json`
({char: [profession note names]}) - its professions every 5 levels, values coloured by rank range (Apprentice white, Journeyman
green, Expert blue, Artisan purple; legend under the contents). Static on purpose (user's choice): no live
skill/Δ that would need regenerating after every session. Refresh only this note: `gather_zones.py benchmarks`.
Colour CSS targets only the wide table (`table:has(th:nth-child(13))`).
Every herb/ore name carries a tier label `(Tn)` = rank of its skill among route nodes (same skill -> same tier),
so the user can learn the progression order.
Notes are character-independent (reused by alts) - current skill per char comes from `profession-plan`.

Script: `python3 -I ~/.claude/skills/wow/skills/gather-zones/gather_zones.py <prof> [--stats] [--shift N]`
(`<prof>` = `herbalism` | `mining` | `benchmarks`). Re-running regenerates everything - never hand-edit the note.

## 1. New profession
1. Item cards must exist for every node's item. The script stops and prints the `gen_cards.py` command
   with the missing ids - run it, check the printed names match (notes skill rule).
2. `--stats` - per route zone: skill for half the nodes, skill for every common node, share per node.
3. Write `config/<prof>.json` (copy `herbalism.json`): `ranks`, `have` per zone (every ROUTE zone), `targets`.
   - `have` = skill on arrival = the "half" value (user rule: pick at least half the nodes on arrival),
     raised for hard checkpoints - zones that are almost one high node (Tanaris/Searing Gorge Firebloom,
     Swamp of Sorrows Blindweed) and the Artisan train at 35.
   - `targets` = skill 1 -> 300: first level a new node tier appears on the route:
     `{level, skill, nodes: [names], zones: [names]}`; rank trains use `note` (`"train Journeyman"` 10,
     Expert 20, Artisan 35). Node names exactly as in GatherRadar.
4. Generate, then look at 2-3 maps (Read) before telling the user it's done.

## Data
- Nodes: GatherRadar `Core/Nodes.lua` (`Add("herb"|"ore", ...)`: node id, name, item id, skill) +
  `Data/Import<Kind>.lua` (Forever node coords from Wowhead, GatherMate2 encoding) in the addon repo.
- Forever-only nodes (ids 90xxx) have no item and no coords yet - shown as plain text if they ever appear.
- Ore: several nodes share one item (Ooze Covered *, Small/Rich Thorium) - rows link the item note with
  the node name as alias; the card gets the lowest skill.
- Skinning/Fishing: no node data - not supported.
- Zone list/order = `ROUTE` in the script: level 1 starting zones (Durotar, Mulgore, Tirisfal, Zephras Isle)
  to 60, union of RestedXP Forever Guide (H) and Dungeon Guide (H) chapters (Guide column: both / questing /
  dungeon), revisits merged into one section. Map ids are RestedXP's `DB/forever/db.lua` zone table.
- Zephras Isle (Forever-only) has no Wowhead map image -> dots on plain parchment.
- Rank level requirements (10 / 20 / 35) are Classic values, not confirmed for Forever.

## Colours
- Classic formula, **uncalibrated for Forever**: yellow +25, green +50, grey +100 ("—" past 300).
  If the user reports in-game tooltip colours that disagree, regenerate with `--shift N`.
- CSS in `gaming/.obsidian/snippets/wow.css`: `.sk-o/.sk-y/.sk-g/.sk-x` (skill colours),
  `.lv-poor/common/uncommon/rare/epic` (character level coloured like item quality: <5, <10, <25, <45, ≤60).

## Obsidian gotchas (cost time already)
- Inside tables write `![[icon.jpg\|inline]]` and `[[#heading\|alias]]` - a bare `|` splits the cell.
- Links hover-preview without Ctrl only inside tables (Live Preview), so lists the user hovers are tables.
- Tables can't hold task checkboxes; the user doesn't need tick state kept across regenerations.

## Finish
One line: note path, number of zone maps, cards stamped; remind that colours are uncalibrated.
