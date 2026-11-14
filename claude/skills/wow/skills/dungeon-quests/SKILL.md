---
name: dungeon-quests
description: Build or update a quest-chain note for a WoW Forever dungeon (Razorfen Kraul, SM, Uldaman...) - every quest to pick up before going in, prerequisites, where to turn in, class quests the in-game guide skips - from the local Zygor guide cross-checked with Forever web guides and YouTube. Use when the user asks which quests a dungeon has, what they missed, or wants to prepare for a dungeon run.
---

# Dungeon quest notes (WoW Forever)

Output: `~/Documents/obsidian/gaming/Wow_FOREVER/dungeons/<Dungeon Name>.md` (Obsidian vault). Update it if it exists.
Game data repo: `~/repositories/wow-forever-addon-settings` (its CLAUDE.md has accounts/chars).
Default context: Horde, Karums-Warrior (Arms) + Karums-Priest duo.

## 1. Local guide (baseline)
```
python3 ~/.claude/skills/wow/skills/dungeon-quests/dungeon-quests.py "<Dungeon>" [--faction Alliance]
```
Prints the Zygor "<Dungeon> Quests" guide steps (accept/collect/turnin, quest IDs, coords) and a
`/run` macro the user pastes in-game to see which quests are `done` / in `log` / `-` (not taken).
Completed quests are NOT in SavedVariables (RXP `questObjectivesCache` is only a cache), so the
macro is the only reliable "what did I miss" check. Ask the user to run it and paste the output.

Zygor known gaps: skips **class quests** (e.g. warrior Brutal Armor / Fire Hardened Mail) and
pre-quests started far away. RXPGuides (`<repo>/Interface/AddOns/RXPGuides`) is the second local source.

## 2. Web cross-check (required)
WebFetch, prefer Forever pages over Classic:
- `https://www.warcrafttavern.com/forever/guides/<dungeon-slug>-quests/` - most complete (objectives, chains, class quests)
- `https://www.method.gg/wow-forever/dungeons/<dungeon-slug>` - levels, givers
- `https://www.wowhead.com/classic/quest=<id>` - details, pitfalls, comments (Classic data; Forever may differ)
icy-veins and mobalytics return 403 to WebFetch - offer Claude in Chrome if needed.
Sources disagree on min levels (beta vs live): say so, don't pick silently.

## 3. YouTube (optional, best-effort)
```
yt-dlp "ytsearch5:wow forever <dungeon> quests" --print "%(id)s | %(title)s | %(upload_date)s"
yt-dlp --no-simulate --skip-download --write-auto-subs --sub-langs en --sub-format vtt -o "%(id)s" <id>
```
Run in the scratchpad. Subtitle downloads often hit HTTP 429 - try once, then move on; never loop.
Strip VTT timing lines/tags before reading. Use transcripts only for tips (routes, pitfalls).

## 4. Note format
Follow the `notes` skill style (cheatsheet: one-line bullets, `->` chains, checklists, no prose).
Items: inline icon + link like `notes` does, reuse `items/` cards, make new ones with its `gen_cards.py`.
```
# <Dungeon> - <faction> quests
- <level range> - <where it is>

## Before you go
### <Town>
- [ ] <Quest> - <giver> (<coords>) - <what to grab / pre-quest>
## Inside (in path order)
- [ ] <objective> - <boss / spot>
## After
- [ ] <town> - turn in <Quest> -> <follow-up unlocked>
## Check in game
<the /run macro from step 1>
```
Class quests for the user's classes go in their own `### <Class> only` block.
Research sources stay in chat (the vault notes have no sources); mention level conflicts in chat.
If `wow forever.md` (todo list) has a matching todo, tick it and link the note.
