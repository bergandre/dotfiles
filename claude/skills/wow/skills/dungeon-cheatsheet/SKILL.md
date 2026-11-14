---
name: dungeon-cheatsheet
description: Make a WoW Forever dungeon cheatsheet in the Obsidian vault - 1) dungeon map with numbered boss markers, 2) every boss with 1-2 sentence mechanics and the loot that is an upgrade for the user's current characters (default Karums Warrior Arms + Karums Priest healer duo), based on their equipped gear. Use when the user wants to prepare for a dungeon, asks what bosses do, or what loot to look for.
---

# Dungeon cheatsheet (WoW Forever)

Output: `~/Documents/obsidian/gaming/Wow_FOREVER/dungeons/<Dungeon>.md`, sections in this order:
`## Map` -> `## Bosses` -> `## Quests` (the last one belongs to the `dungeon-quests` skill - keep it if present).
Game data repo: `~/repositories/wow-forever-addon-settings` (CLAUDE.md there: accounts, chars).

## 1. Collect data (one command)
```
python3 -I ~/.claude/skills/wow/skills/dungeon-cheatsheet/cheatsheet.py "<Dungeon>" [--slug <foreverchanges-slug>] [--chars "Karums Warrior,Karums Priest"]
```
- **Map**: downloads `foreverchanges.pro/dungeons/<slug>` map + boss pins, draws numbered red
  markers (numbers = boss path order) -> `dungeons/maps/<Dungeon>.png`. Prints which bosses have no pin.
  Slug default = lowercased name with dashes; SM wings etc. may need `--slug` (check the site's URL).
  No web map -> falls back to local `InstanceAtlas/Maps/*.tga` (no markers). Multi-floor dungeons:
  script uses the first image only - check the page and draw other floors by hand if needed.
  Always look at the PNG (Read) before using it.
- **Bosses + loot**: Forever loot IDs from local AtlasLoot `data-forever.lua` (path order), item stats
  from Wowhead Forever tooltips (cached in `~/.cache/wow-tooltips`), and what each char wears in the
  matching slot from `BagBrother.lua` (refreshed on `/reload` or logout - ask the user to `/reload`
  if gear looks stale). Only items the class can equip are compared.

## 2. Mechanics (web)
WebFetch two sources and merge into 1-2 short sentences per boss (what it does -> what to do):
- `https://www.method.gg/wow-forever/dungeons/<slug>`
- `https://warcrafttavern.com/wow-classic/guides/<slug>` (Classic, but Forever kept Classic boss kits)
foreverchanges.pro only has ability counts. icy-veins 403s.
Duo-relevant only: what the warrior must interrupt/taunt, what the priest must dispel/avoid.

## 3. Judge loot
From the script output pick only real upgrades per char; skip side-grades. Rules:
- Warrior = Arms 2H, levels as the duo's tank in Def/Battle stance: Str, 2H DPS, Sta, armor. No 1H/shields.
- Priest = healer: +healing, Int, Spirit, Sta. Cloth only. Note empty slots (free upgrades).
- Random-suffix gear (`<Random enchantment>`) - stats unknown, say so.
- Check `warrior weapons.md` / `<class> <slot>.md` notes - tick or link if the item is already planned there.
Item cards: `python3 -I ~/.claude/skills/wow/skills/notes/gen_cards.py ~/Documents/obsidian/gaming/Wow_FOREVER/items <ids>`,
then inline them as `![[<icon>|inline]] [[<Item>]]` (icon from the card's `icon:` field).

## 4. Note format (style of the `notes` skill: cheatsheet, no prose, no sources)
```
# <Dungeon> — Horde, Karums duo (<level>)
- <level range> — <where>
- W = Karums Warrior (Arms 2H), P = Karums Priest (heals)

## Map
![[maps/<Dungeon>.png]]

## Bosses
### <map nr>. <Boss> — <level> [(rare)] [(no map marker)]
- <mechanic> → <what to do>
- [ ] W — <inline item> — <why, vs what is worn>
- [ ] P — ...
(nothing useful -> "- nothing for either of you")
### Trash (BoE, random)

## Quests
<kept from dungeon-quests, headings demoted one level>
```
Back up an existing note to the scratchpad before rewriting it.
