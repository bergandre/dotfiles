---
name: notes
description: Record WoW Forever progression (class leveling, talents, rotations, gear and profession progression) into the gaming Obsidian vault, with tooltip-style item cards and checklists.
disable-model-invocation: true
argument-hint: [what to record / note to modernize — e.g. "priest leveling", "modernize mining"]
---

Record into `~/Documents/obsidian/gaming/Wow_FOREVER/` what the user asks: $ARGUMENTS
(if empty — the non-obvious WoW results of this session; list them and confirm first).

Reference notes (copy their format): `warrior leveling.md`, `warrior weapons.md`,
`professions/cooking.md`, `items/Corpsemaker.md`.

## Layout
- `<class> leveling.md` — talents, rotation, group/duo, Forever changes; links to gear notes
- `<class> <slot>.md` — gear progression, e.g. `warrior weapons.md`
- `professions/<profession>.md` — profession progression
- `items/` — one card note per item (any type), icons in `items/icons/`
- Item notes are shared — reuse if it exists, never duplicate
- `wow forever.md` — todo list; tick + link the note if this completes a todo

## Style — cheatsheet, not a report
- `#` title with who/what (e.g. "Horde Arms duo", "Cooking — Karums Warrior (Horde)")
- `##` sections, one-line bullets, `level — what`; chains with `→`
- No sources, no "unverified", no prose, no why-explanations
- Only what was established in the conversation — don't fill gaps
- "Modernize" a note = keep every fact and checkbox state, only change formatting

## Items in text — inline icon + link (hover shows the card)
`![[<icon>|inline]] [[<Note Name>]]` — icon from the item note's `icon:` field
- Caption must be exactly `inline` (theme opt-out from image gallery/centering); size comes from wow.css
- Alias when shorter/plural reads better: `[[Bristle Whisker Catfish|Catfish]]`
- Recipes: note is `Recipe - X.md` (Obsidian forbids `:`)

## Gear progression note
```
# <Class> <slot> — <faction> <type>
- <one-line pick rule>

## <level> — <source: quest / boss, dungeon / craft>
- [ ] got it

![[<Item Name>#^card]]
```
- Alternatives at the same level → several embeds under one heading
- Levels from the research, not the tooltip (quest rewards have no req level)
- Blank line between `- [ ] got it` and the embed

## Profession note
- `## Progress` — checklist: `- [ ] <from> → <to> — <inline items> ×N (notes)`
- Trainer/book steps as their own checklist line (e.g. `125 — Expert Cookbook — <vendor>`)
- `## Recipes to get` — checklist line = where to buy, card under it:
  ```
  - [ ] Tari'qa, Crossroads
    ![[Recipe - Strider Stew#^card]]
  ```
- Shopping / Mats / tips sections — bullets with inline items

## Item cards
1. Get Wowhead Forever item IDs
   - Local data: `python3 tsm-analyze.py --item "<name>"` in the addon-settings repo → `(id N)`
   - Gear guides with item links: timesaver.gg leveling-gear, method.gg weapon lists
2. Generate — prints `id, note name, icon, quality`; skips existing notes, `--force` regenerates:
   `python3 -I ~/.claude/skills/wow/skills/notes/gen_cards.py ~/Documents/obsidian/gaming/Wow_FOREVER/items <id> …`
3. Check every printed name matches the item — local TSM data has wrong name→ID pairs.
   Wrong/missing → try the Classic ID and check the printed name; never use an unchecked ID
4. No ID found → stub card in `items/`, tell the user which:
   ```
   ---
   id:
   tags: [wow/item]
   ---
   > [!wow] <Item Name>
   > <type · stats known from research>
   > <span class="extra"><source></span>
   > [Wowhead search](https://www.wowhead.com/forever/search?q=<Item+Name>)

   ^card
   ```

## Styling
- Cards = `> [!wow|<quality>]` callouts, inline icons = `|inline` embeds; both styled by
  `gaming/.obsidian/snippets/wow.css` (must stay in `appearance.json` → `enabledCssSnippets`)
- New tooltip parts → add a class to `wow.css`, don't inline styles

## Known blocks — don't work around
- mobalytics.gg (Kargoz guides) and Wowhead search return 403 to fetch/curl → offer Claude in Chrome
- `nether.wowhead.com/forever/tooltip/item/<id>` works — that's what the script uses

## Finish
One line per file: what was added, where. List stub items.
