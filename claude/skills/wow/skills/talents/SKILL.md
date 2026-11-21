---
name: talents
description: Build WoW Forever talent tree notes in the Obsidian vault - the three trees on their in-game backgrounds, every talent icon with rank badge, hover card per talent (rank, levels you take it, effect), one section per build (e.g. level 40 cut + level 60 end). Builds come from method.gg Forever guides (Forever reworked the trees - Classic calculators are wrong). Use when the user wants talent notes, a talent build, or "what to take at level X" for a character.
---

# Talent tree notes (WoW Forever)

Output: `~/Documents/obsidian/gaming/Wow_FOREVER/characters/<Char>/<class> talents - <spec>.md`
(reference: `characters/Karums Warrior/warrior talents - arms.md`, `- prot.md`). Link them from the
character hub (`<Char>.md` "Talents —" line).

```
python3 -I ~/.claude/skills/wow/skills/talents/talents.py <class> "<out.md>" "<Title>" <build>[:<points>] ...
```
`build:31` = the first 31 points of that build (level 40: first point at level 10, one per level, 51 at 60).
Styles: `.wowtal` block (`wowtal:start`…`end`) in `gaming/.obsidian/snippets/wow.css`.

## Data: config/<class>.json (scrape once per class, Claude in Chrome)
Forever trees have 7 tiers × 4 columns and Forever-only talents - only method.gg's embeds are right.
1. Open a method.gg Forever page with that class's talent embed (`/wow-forever/class-guides/<spec>-<class>/talents`,
   or the leveling guide). Builds sit in `.forever-talents[data-talent]` = `<loadout>;<order>`; the order string
   has one letter per point, letter = index (alphabet `A-Za-z0-9+/`) into the class's talents sorted by
   Method's `.talent[data-id]`. Hidden tab panes render only after clicking their `ul.nav li a`.
2. Grid: per `.talent` - `data-id`, spell id from `a.ability[data-wowhead]` (`spell=N`), max rank from
   `.rank` ("x/y"), tree = index of `.talent-holder`, row/col from its position in `.talent-tree-body`
   (unique sorted values → tier 0-6 / col 0-3). Output with `=`, `&`, `?` replaced - the browser tool blocks
   query-string-looking results.
3. Check: decoded counts must never exceed a talent's max rank, total 51.
4. Tree backgrounds: `wow.zamimg.com/images/wow/talents/backgrounds/classic/<treeId>.jpg` (warrior 161/164/163;
   other classes: the Classic talent tree ids). Spell text/icons: nether.wowhead.com/forever (cached).

## Build choice
- A guide's order string is the author's click order, not always a priority (Method's Prot dungeon order spends
  15 Fury points first). For a "level N" cut of an end build, check the cut makes sense (reaches the spec's
  key talent); otherwise add a hand-made build to the config (`prot_dungeon_40`: Prot tree only, tier order).
- Tooltips are rank-1 text from Wowhead; some rank values are unresolved there ("0%" dropped by the script,
  some numbers odd) - the card says "rank 1 shown".
- Preview without Obsidian: put the `.wowtal` CSS + the HTML block in an .html file and
  `chromium --headless=new --screenshot=out.png --window-size=800,760 file://…` (Claude in Chrome can't open file://).
