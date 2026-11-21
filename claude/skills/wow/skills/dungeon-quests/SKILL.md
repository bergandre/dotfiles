---
name: dungeon-quests
description: Build or update the quests note (notes/<Dungeon> quests.md) for a WoW Forever dungeon (Razorfen Kraul, SM, Uldaman...) - every quest to pick up before going in, prerequisites, where to turn in, class quests the in-game guide skips - from the local Zygor guide cross-checked with Forever web guides and YouTube. Use when the user asks which quests a dungeon has, what they missed, or wants to prepare for a dungeon run.
---

# Dungeon quest notes (WoW Forever)

Output: `~/Documents/obsidian/gaming/Wow_FOREVER/dungeons/<Dungeon Name>/notes/<Dungeon Name> quests.md`
(the main note `<Dungeon Name>.md` belongs to `dungeon-cheatsheet` and only links here from `## Notes`; its
frontmatter holds the quest pins). Folder layout: see dungeon-cheatsheet SKILL.md.
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
pre-quests started far away. Second local source (best for Forever): `<repo>/Interface/AddOns/ForeverDungeonJournal/Data/Dungeons.lua`
(`FDJ.DB["<Dungeon>"].quests`: faction, giver, levels, rewards, warnings) + `QuestChains.lua` (prereqs).
RXPGuides (`<repo>/Interface/AddOns/RXPGuides`) is the third.

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
# <Dungeon> — quests
- [[<Dungeon>]] · objectives inside are the yellow ! pins on the map
- <level / faction notes, e.g. "Gear drops → [[warrior weapons - arms|arms]] · [[warrior weapons - prot|prot]] weapons">

## Pick up
### <Town>
- [ ] <Quest> - <giver> (<coords>) - <what to grab / pre-quest> [→ <item to get inside, if no pin shows it>]
## Turn in
- [ ] <Town> - <NPC> - <Quest> -> ![[icon|inline]] [[<reward>]] (W / P) / <follow-up unlocked>
## Check in game
<the /run macro from step 1>
```
No `## Inside` list: in the dungeon the user only looks at the interactive map. Each
in-dungeon quest becomes a quest pin on it (`dungeon-cheatsheet`, main note frontmatter `pins:`) whose
`text:` lines hold the objective, the turn-in NPC + coords and the rewards that matter:
```
  - {kind: quest, name: <Quest>, x: <%>, y: <%>, guess: true, text: [
      "<objective> (<mobs / spot>)",
      "→ <NPC>, <town> (<coords>): W <reward> · P <reward>"]}
```
Class quests for the user's classes go in their own `### <Class> only` block under `## Pick up`.
Research sources stay in chat (the vault notes have no sources); mention level conflicts in chat.
Todos live in TickTick, not the vault: a matching open task (gaming / wow) gets ticked via `ticktick:done`
once the user agrees it's finished. When the user reports quest status (macro output), tick `[x]` the lines in
`## Pick up` / `## Turn in` of the quests note.
