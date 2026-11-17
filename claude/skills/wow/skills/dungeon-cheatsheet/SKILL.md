---
name: dungeon-cheatsheet
description: Make a WoW Forever dungeon cheatsheet in the Obsidian vault - 1) interactive dungeon map with boss/quest pins and the run route drawn on it, 2) a Dungeon-Journal-style tactics note (boss abilities as in-game spell cards, Tank/Healer/Damage tips) with the loot that is an upgrade for the user's current characters (default Karums Warrior Arms + Karums Priest healer duo), based on their equipped gear. Use when the user wants to prepare for a dungeon, asks what bosses do, or what loot to look for.
---

# Dungeon cheatsheet (WoW Forever)

**Required: the map shows the run route** (entrance -> every boss in kill order -> exit/last boss),
see section 5. A cheatsheet without a route on the map is not done.

Output, one folder per dungeon `~/Documents/obsidian/gaming/Wow_FOREVER/dungeons/<Dungeon>/`
(keep file names unique - Obsidian links by name):
- `<Dungeon>.md` - main note: `## Map` (embed) -> `## Bosses` (link to tactics) -> `## Quests` (owned by `dungeon-quests`, keep it)
- `<Dungeon> tactics.md` - per boss: journal header, abilities, role tips, loot (section 4)
- `<Dungeon> (interactive).md` (generated), `<Dungeon> map.png` (static fallback), `art/` (portraits, sketches)
Shared: `abilities/<Spell>.md` ability cards (+ `abilities/icons/`, incl. `ej-<flag>.png`), `items/<Item>.md`.
Game data repo: `~/repositories/wow-forever-addon-settings` (CLAUDE.md there: accounts, chars).

## 1. Collect data (one command)
```
python3 -I ~/.claude/skills/wow/skills/dungeon-cheatsheet/cheatsheet.py "<Dungeon>" [--slug <foreverchanges-slug>] [--chars "Karums Warrior,Karums Priest"]
```
- **Map**: downloads `foreverchanges.pro/dungeons/<slug>` map + boss pins, draws numbered red
  markers (numbers = boss path order) -> `dungeons/<Dungeon>/<Dungeon> map.png`. Prints which bosses have no pin.
  Slug default = lowercased name with dashes; SM wings etc. may need `--slug` (check the site's URL).
  No web map -> falls back to local `InstanceAtlas/Maps/*.tga` (no markers). Always look at the PNG (Read) before using it.
  **Multi-floor** (script prints "N map images"; the site pins bosses on floor 1 only): download
  `<slug>-1..N.webp`, label each "Floor n" (`magick -annotate`, font via `fc-match`), stitch with
  `magick montage -tile 2x2 -geometry +0+0` over `<Dungeon> map.png`, set `map: <Dungeon> map.png` in the
  main note's frontmatter and give every boss a `kind: boss` pin (floor-local % -> grid: x=(col*100+x)/2,
  y=(row*100+y)/2). Draw the pins on a copy and Read it to check. Reference: `dungeons/Gnomeregan/`.
  **Forever-only dungeon** (foreverchanges 404, e.g. Excavation Site): in-game map from the ForeverDungeonJournal
  addon `<repo>/Interface/AddOns/ForeverDungeonJournal/Media/<Name>Map.tga` (1024² with a black bottom ->
  `magick ... -crop 1024x690+0+0 -fuzz 8% -trim`) -> `<Dungeon> map.png` + `map:` + a `kind: boss` pin per boss
  (no portraits). method.gg's map is the mirror image of it (both fan recreations) - ask the user which matches the game. Reference: `dungeons/Excavation Site - Wetlands/`.
  Names with `:` -> folder/notes use ` - ` (Obsidian forbids `:` in file names); scripts match AtlasLoot by letters only.
- **Bosses + loot**: Forever loot IDs from local AtlasLoot `data-forever.lua` (path order), item stats
  from Wowhead Forever tooltips (cached in `~/.cache/wow-tooltips`), and what each char wears in the
  matching slot from `BagBrother.lua` (refreshed on `/reload` or logout - ask the user to `/reload`
  if gear looks stale). Only items the class can equip are compared.

## 2. Abilities, role tactics, art (one command)
```
python3 -I ~/.claude/skills/wow/skills/dungeon-cheatsheet/tactics.py "<Dungeon>" [--slug <slug>] [--force]
```
- method.gg Forever guide: every boss + important trash mob -> spell IDs -> ability cards in `abilities/`
  (`notes/gen_abilities.py`: Wowhead Forever spell tooltip, dispel type, "Used by: <mob> (<Dungeon>)").
  Prints each mob's guide lines and method's flags (e.g. `important`).
- warcrafttavern (Classic; Forever kept Classic boss kits): intro + Tank / Healer / Damage Dealers text.
- art: foreverchanges portraits -> `art/<Boss>.webp`; DungeonJournal addon pencil sketch (only a few
  bosses have one) -> `art/<Boss> sketch.png`; journal flag icons -> `abilities/icons/ej-<flag>.png`.
Wowhead's site 403s curl, the `nether.wowhead.com` tooltip API works. icy-veins 403s.
Rewrite the guide text for the duo (W tanks + deals damage, P heals); don't copy CC/kick advice that
needs other classes. Spell tooltips beat guide prose (e.g. Dominate Mind tooltip caps at level 25).

## 3. Judge loot
From the script output pick only real upgrades per char; skip side-grades. Rules:
- Warrior = Arms 2H, levels as the duo's tank in Def/Battle stance: Str, 2H DPS, Sta, armor. No 1H/shields.
- Priest = healer: +healing, Int, Spirit, Sta. Cloth only. Note empty slots (free upgrades).
- Random-suffix gear (`<Random enchantment>`) - stats unknown, say so.
- Check `warrior weapons.md` / `<class> <slot>.md` notes - tick or link if the item is already planned there.
Item cards: `python3 -I ~/.claude/skills/wow/skills/notes/gen_cards.py ~/Documents/obsidian/gaming/Wow_FOREVER/items <ids>`,
then inline them as `![[<icon>|inline]] [[<Item>]]` (icon from the card's `icon:` field).

## 4. Note format (style of the `notes` skill: cheatsheet, no prose, no sources)
Main note:
```
# <Dungeon> — Horde, Karums duo (<level>)
- <level range> — <where>
- W = Karums Warrior (Arms 2H), P = Karums Priest (heals)

## Map
![[<Dungeon> (interactive)]]   <- set by interactive_map.py (static PNG only as fallback)

## Bosses
- [[<Dungeon> tactics|Tactics]] — abilities, roles, loot per boss

## Quests
<kept from dungeon-quests, headings demoted one level>
```
`<Dungeon> tactics.md` (reference: `dungeons/Razorfen Kraul/Razorfen Kraul tactics.md`) starts with
`## Pulls — kill order` (before the bosses; the map parser ignores it):
```
Any trash pack, top first. You have no CC, so the kill order does the job of CC:
1. <inline icon> [[<totem/ability>]] or **<Mob>** — <why first>          <- totems, stunners, healers, mana burners, summoners, melee last
- **Casters:** LoS-pull ... / **Interrupts:** Pummel = Berserker Stance only / **<danger mob>:** <follow rule>
- **Boss packs:** kill order = that boss's **Run:** line
```
Guides list only the mob types, not what's in each pack (method.gg "Important Trash", warcrafttavern, Wowhead
Classic); the priority list comes from those. Don't make up pack compositions; add one only when the user
reports it. Then per boss in map order:
```
## <map nr>. <Boss> — <level> [(rare)] [(no map marker)]
> [!boss] <creature type> · <where / adds>
> ![[<Boss>.webp]]
> [![[<Boss> sketch.png]]]
> <one-line overview>
> **Run:** <kill order / key move>          <- the interactive map card shows this line

- ![[<spell icon>|inline]] [[<Ability>]] ![[ej-<flag>.png|inline]] — <cast time, what it does>

> [!roles]
> > [!tank] Tank · W
> > - ...
>
> > [!healer] Healer · P
> > - ...
>
> > [!dps] Damage · W
> > - ...

- [ ] W — <inline item> — <why, vs what is worn>
(nothing useful -> "- nothing for either of you")
```
Then `## Trash (BoE, random)`: `- [ej-important] **<Mob>** — <inline abilities> → <what to do>`, then BoE loot lines.
Flags (journal icons, only when they matter): interrupt, magic/curse/poison/disease (dispel type from the
card), enrage, important, tank/healer/dps (who must react), nonphys/physical.
Priest dispels Magic (Dispel Magic) and Disease; no poison/curse removal -> "heal through".
Header line 2 of the note is the flag legend. Back up existing notes to the scratchpad before rewriting.

## 5. Interactive map (top of the note = the "run view")
After the note is written: `python3 -I ~/.claude/skills/wow/skills/dungeon-cheatsheet/interactive_map.py "<Dungeon>" [--slug ...]`
-> `dungeons/<Dungeon>/<Dungeon> (interactive).md` (generated, never edit by hand) and `## Map` in the main
note embeds it. Boss portraits (rares = silver ring), hover = boss card (from the tactics note: Run line, hover an ability icon = spell tooltip from `abilities/<Spell>.md`,
ability icon row, loot; old notes without tactics: `## Bosses`), hover a loot
line = full item tooltip (from `items/<Item>.md`). Images are inlined as data URIs.
Quest pins come from the main note's frontmatter (x/y = % of the map image):
```
pins:
  - {kind: quest, name: Blueleaf Tubers, match: Blueleaf Tuber, x: 43, y: 54, guess: true}
  - {kind: boss, name: Aggem Thorncurse, x: 70, y: 50, guess: true}   # add/move a boss pin
```
**Route (required)** - the main note's frontmatter also gets `route:`, drawn as a dashed red line with
direction arrows under the pins (green "Start" dot at the entrance):
```
route:
  - [50, 95]                          # entrance
  - [48, 70]                          # a point at every corridor bend - the line must not cut through walls
  - {x: 30, y: 52, label: drop down}  # short label where something happens (jump, skip, shortcut, quest item)
  - [22, 40]                          # ... through every boss pin in **Run** / map-number order
```
- Order = boss numbers on the map (path order from the guides: foreverchanges/method.gg route, "clear order"
  text; optional/rare bosses only as a short detour). Pass through quest-objective pins on the way.
- Run with `--preview <scratchpad>/<slug>-route.png` and **Read the PNG**: line stays inside corridors,
  hits every boss/quest dot in order, no backtracking that isn't needed. Fix points and re-run until it does.
- Multi-floor (stitched map): one route through all floors; label the floor change (`label: stairs → Floor 2`).
- Route from guide text, not seen in-game -> tell the user it's a first draft; adjust when they report the real path.
  The script prints a WARNING when `route:` is missing.

`match` picks the quest's lines from `### Inside`; `guess: true` = dashed ring + "approx. position".
Add a pin for every in-dungeon quest objective (guess from guide text, mark `guess: true`); when the
user confirms/corrects a spot, fix x/y and drop `guess`. Regenerate after editing the note.
Styles: `.wowmap` / `.wm-*` (route: `.wm-route`) in `gaming/.obsidian/snippets/wow.css` (cards scale with map width via
container queries; pins right of center open left).
Tactics styles: `[!boss]` (parchment from the DungeonJournal addon), `[!roles]` grid of
`[!tank]`/`[!healer]`/`[!dps]` (role icons are data URIs in the css), `[!wow|spell]` cards.
Quirks: Live Preview wraps HTML blocks in widgets with `contain: paint`, and note embeds get
`overflow: auto` + max height - both clip popups; wow.css lifts them for anything `:has(.wowmap)`.
