---
name: quest-items
description: Judge leftover quest items in a WoW Forever character's bags - which quest each belongs to (local guides + Wowhead Forever), whether that quest is completed or still in the log, and which items are safe to delete. Use when the user asks about junk/leftover/unneeded quest items, "can I delete this quest item", or cleaning bags of quest leftovers.
---

# Leftover quest items (WoW Forever)

Game data repo: `~/repositories/wow-forever-addon-settings` (`WOW_REPO`); its CLAUDE.md has accounts/chars.
Default chars: Karums-Warrior, Karums-Priest. Never delete anything yourself - the user deletes in game.

## 0. Data: QuestLedger addon
`<repo>/Interface/AddOns/QuestLedger` (custom) saves per character, on logout / `/reload` / quest turn-in:
completed quest IDs, the quest log, every bag quest item (+ the quest it starts, from
`GetContainerItemQuestInfo`). Completed quests exist nowhere else on disk. If the script says
"no QuestLedger.lua yet" or the snapshot is old, ask the user to `/reload` that character (bags only,
not bank).

## 1. Local mapping + completion
```
python3 ~/.claude/skills/wow/skills/quest-items/quest-items.py [--char Karums-Priest]
```
Verdicts: `KEEP` (quest in log / not done), `SAFE?` (every quest it is for is done), `REWARD` (quest
reward, judge as a normal item), `WEB` (no local mapping). Local sources: Zygor Forever guides,
RXP guides + RXP Forever DB, ForeverDungeonJournal rewards - incomplete for Forever-only quests.

## 2. Wowhead Forever (required for WEB and SAFE? rows)
WebFetch/curl can't see the quest tabs (JS-rendered, bot check). Use Claude in Chrome: one tab,
for each item `navigate` to `https://www.wowhead.com/forever/item=<id>`, then `javascript_tool`:
```js
JSON.stringify({title: document.title, tabs: Object.fromEntries(Object.entries(window.g_listviews || {}).map(([k, v]) => [k, (v.data || []).map(d => [d.id, d.name])]))})
```
Relevant tabs: `objective-of`, `starts`, `provided-for`, `reward-from` (quests), `unlocks` (objects -
usually a quest object), `comments` (read them if non-empty: "keep for later quest" warnings).
Close the tab when done.

## 3. Check the web quests
```
python3 ~/.claude/skills/wow/skills/quest-items/quest-items.py --char <Char> --quests <id,id,...>
```
`done` / `log` / `-` (not taken) per quest.

## 4. Verdict table for the user
Safe to delete only if every quest from `objective-of`, `starts` and `provided-for` (local + web) is
`done`, none is in the log, and no comment warns about a follow-up. A `starts` quest that is `-`
means the item would start a quest you haven't done: keep (or say it's an optional quest).
Items with no quest anywhere: say "unknown", don't guess. Output: one table per character
(Item, Count, Quests + status, Verdict, Source), then the delete list.
