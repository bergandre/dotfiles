# Adding and routing tasks

## 1. Sync the map - once per conversation

Before the first write, read `map.md` and list the user's projects, project groups and tags from TickTick. Skip lists with `closed: true`. Compare by name:

- In the map, gone from TickTick -> ignore that line and tell the user in one line it can be removed from the map.
- New in TickTick -> if the name explains itself, route by the name and suggest a map line; otherwise ask "what goes in X?" and give the line to add.
- One gone and one new in the same folder -> ask whether it is a rename.

Do not repeat this for later tasks in the same conversation. Re-sync only when a write fails because a list is missing.

## 2. Route

Read the map's `Rules` section first, then pick one list per todo from the descriptions.

- Clear fit -> file it there, no question.
- Two plausible lists -> ask once, naming both. In a batch, file the clear ones and put all unclear ones into a single question.
- No fit -> Inbox (omit `projectId`). Never create a list. If the same kind of homeless todo keeps coming up, suggest one.
- A line marked `(guess)` in the map is unconfirmed: route by it, but when a todo lands there, ask the user to confirm the description.

Tags are situational hints for how a task gets solved (a place, a method), independent of the list. Add an existing tag only when the todo plainly matches its line in the map. In doubt, no tag. Never create a tag.

## 3. Write

- Title: the user's own wording and language. Do not translate, expand or tidy it.
- Several items of one kind (a shopping list) -> one task with `kind: "CHECKLIST"` and `items`.
- Date only when the user gave one. All-day unless they gave a time. Pass `client_timezone` from the user preference call.
- More than one task -> batch add.

Report one line per task: `title -> folder / list #tag`.

## 4. Sort the Inbox - only when asked

Never run this unprompted; these are tasks the user filed themselves.

1. Sync (step 1), then fetch the Inbox with its undone tasks.
2. Route every task by step 2.
3. Show one table: task | goes to | tag. Use "stays" for tasks with no home and "A or B?" for ties.
4. Move nothing until the user approves. Then move each task (`fromProjectId` = the task's own `projectId`), update tags, and report what moved.
