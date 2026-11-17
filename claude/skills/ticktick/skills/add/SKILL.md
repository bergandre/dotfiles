---
name: add
description: File TickTick tasks into the right list and tag using the user's map of areas. Use whenever a TickTick task is about to be created or moved - on request ("add a task", "remind me to", "make a todo for"), in passing during other work, for a dictated batch (/ticktick:add), or when the user asks to sort or triage their TickTick Inbox.
argument-hint: "[todos in free text]"
---

# TickTick routing

The map `~/Documents/obsidian/glava7/ticktick/map.md` says what each folder, list and tag is for and holds the user's tie-break rules. TickTick decides what exists; the map only stores meaning. Never put IDs in the map - take them from the live calls.

Tools are `mcp__ticktick__*` (load with ToolSearch). If the server is not connected, say so and stop - do not fall back to a note or a file.

## 1. Sync the map - once per conversation

Before the first write, read the map and call `list_projects`, `list_project_groups`, `list_tags`. Skip lists with `closed: true`. Compare by name:

- In the map, gone from TickTick -> delete the line, tell the user in one line.
- New in TickTick -> if the name explains itself, write the line and say so; otherwise ask "what goes in X?" and save the answer.
- One gone and one new in the same folder -> ask whether it is a rename before dropping the old description.

Do not repeat this for later tasks in the same conversation. Re-sync only when a write fails because a list is missing.

## 2. Route

Read the map's `Rules` section first, then pick one list per todo from the descriptions.

- Clear fit -> file it there, no question.
- Two plausible lists -> ask once, naming both. In a batch, file the clear ones and put all unclear ones into a single question.
- No fit -> Inbox (omit `projectId`). Never create a list. If the same kind of homeless todo keeps coming up, suggest one.
- A line marked `(guess)` in the map is unconfirmed: route by it, but when a todo lands there, ask the user to confirm the description and remove the marker.

Tags are situational hints for how a task gets solved (a place, a method), independent of the list. Add an existing tag only when the todo plainly matches its line in the map. In doubt, no tag. Never create a tag.

## 3. Write

- Title: the user's own wording and language. Do not translate, expand or tidy it.
- Several items of one kind (a shopping list) -> one task with `kind: "CHECKLIST"` and `items`.
- Date only when the user gave one. All-day unless they gave a time. Pass `client_timezone` from `get_user_preference`.
- More than one task -> `batch_add_tasks`.

Report one line per task: `title -> folder / list #tag`.

## 4. Sort the Inbox - only when asked

Never run this unprompted; these are tasks the user filed themselves.

1. Sync (step 1), then `get_project_with_undone_tasks` for the Inbox.
2. Route every task by step 2.
3. Show one table: task | goes to | tag. Use "stays" for tasks with no home and "A or B?" for ties.
4. Move nothing until the user approves. Then `move_task` (`fromProjectId` = the task's own `projectId`) and `update_task` for tags, and report what moved.
