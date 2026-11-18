---
name: cooking
description: Add or update a recipe note in the user's Obsidian cooking board (boards/ck) - from a photo of packaging, a link, a video or the user's own words - in Russian, with clear steps that say when every ingredient goes in. Use whenever the user wants to save, add, translate or fix a recipe, or asks how to cook something they want to keep.
argument-hint: [recipe source - photo, link, or "как я делал X"]
---

Make or update a recipe note: $ARGUMENTS

## Where
- Board: `~/Documents/obsidian/syncreborn/boards/ck/`
- Appliance recipes go in a subfolder named after the appliance (`Мультиварка/`, ...).
  Create a new subfolder only for a new appliance.
- File name: Russian dish name, plus the source if it matters
  (`Пельмени LAGE.md`, `Греческий салат от Сани.md`).
- Before writing, look at what is already in the board: update an existing note
  rather than making a duplicate.

## Note format
Plain text, no frontmatter, in Russian. Speak to the user with "ты" in the steps.

```
<Название> (<источник / порции>)

![[timer.svg|18]] **<главное время готовки>** · ![[fire.svg|18]] <подготовка/нагрев> · итого <всего>

Ингредиенты (<на сколько>):
- <продукт> — <количество>
- По желанию: ...

Приготовление:
1. <шаг>
...

Макросы на порцию: ...   (only if known or the user asks)
Хранение: ...            (only if relevant)
```

Optional components ("по желанию", "для остроты", substitutions) go at the end
of the ingredient list as a nested group, in the same format (stage icon, exact
amount, spoon icon + words, how to prep it, what it replaces):
```
- По желанию, для экзотики (количества мои, на упаковке их нет):
	- ![[boil.svg|18]] Соевый соус — 2–3 ![[tbsp.svg|18]] ст. ложки **вместо соли**
	- ![[boil.svg|18]] Чеснок — 2–3 зубчика, раздавить ножом
```
Mention them in the step where they go in, with one line on what each option
gives in taste. If the source names products without amounts, give your own and
say so in the group's line. No separate section after the steps.

Optional sections, only when there is data: cost per portion (the user tracks
prices in euros, like in `Греческий салат от Сани.md`), links, images.

## Time line (always, right under the title)
The user must see at a glance how long it cooks. The main time is bold and comes
first - the one that matters while cooking (after boiling, in the oven, the
multicooker mode). Then prep/heating, then the total.
`![[timer.svg|18]] **8–10 мин после закипания** · ![[fire.svg|18]] ~10 мин до кипения · итого ~20 мин`
Times from the source as given; your own estimates (water heating, chopping)
marked with `~`.

## Steps must be complete
- Every ingredient in the list appears in a step that says **when** it goes in
  (before boiling, with the food, N minutes before the end, at serving).
- Give times and heat/mode (`Режим Pasta, 30 мин`), and how to tell it is done.
- Briefly say why when the order matters (e.g. лавровый лист - не варить
  долго, горчит).
- Steps stay plain text, no icons - the icons are on the ingredients.

## Stage icons on ingredients
Like item icons in the WoW vault: every ingredient line starts with a small icon
saying **when** it goes in. Reference: `Пельмени LAGE.md`.

```
Ингредиенты (на 400 г пельменей):
- ![[fire.svg|18]] Вода — 1,2 л
- ![[boil.svg|18]] Лавровый лист — 1–2 шт.
- ![[serve.svg|18]] Зелень

![[fire.svg|18]] на огонь · ![[boil.svg|18]] когда закипело · ![[serve.svg|18]] при подаче
```

- Order the list by when things go in; under it, a legend of only the icons used.
- Always write `|18` (Obsidian's native size). Never `|inline` - that is the WoW
  vault's theme trick and renders full-size here.
- Icons: `~/Documents/obsidian/syncreborn/boards/ck/icons/`
  - `fire.svg` - нагрев: поставить на огонь, довести до кипения, разогреть сковороду
  - `boil.svg` - кидается в уже кипящую воду
  - `timer.svg` - по времени: "вари N мин", "за N мин до конца"
  - `serve.svg` - при подаче, в тарелку
- Spoon measures - the icon complements the words, never replaces them; put it
  between the number and the unit: `Соль — 1 ![[tsp.svg|18]] ч. ложка на 1 л воды`,
  `Масло — 2 ![[tbsp.svg|18]] ст. ложки`. The text already names them, so spoons
  do not go into the legend.
  - `tsp.svg` - чайная ложка (small spoon, green)
  - `tbsp.svg` - столовая ложка (big spoon, purple)
- New stage (духовка, сковорода, отдых, холодильник...): draw a 32x32 SVG in the
  same style (rounded square, dark tint background, simple bright shape), render
  it with `rsvg-convert -w 96` and look at it before use, then add it to this list.
- Styling: `syncreborn/.obsidian/snippets/cooking.css` (enabled, confirmed working
  2026-11-18) aligns icons to the text line and adds a WoW-style grey frame. It
  matches `img[src*="/ck/icons/"]`, so new icons must stay in that folder.
  Obsidian ignores edits to `appearance.json` made while it runs - if styling
  breaks, ask the user to toggle `cooking` in Settings (Ctrl+,) → Appearance →
  CSS snippets, instead of editing the config.

## Sources
- **Packaging photo**: transcribe the original text verbatim under
  `Оригинал (<язык>):` after a `---` at the end, then write the Russian recipe
  above it. Packaging usually lists only quantities and time - fill in the order
  from standard practice and tell the user which steps came from the package and
  which are yours.
- **Link / video**: put the URL on the first line, as the existing notes do.
- Unreadable or ambiguous text: say "не уверен" and how you read it - never
  invent quantities or times.

## After writing
Summarise in the chat: the file name, the key numbers (quantities, time), and
what you inferred vs. what the source said. Do not paste the whole note back.
