---
name: done
description: Tick off TickTick tasks (or single checklist items) once the user and Claude agree the work is finished. Use whenever a piece of work that has a TickTick task behind it gets wrapped up in the conversation - the user says "done", "ok, next", "moving on", "that's finished", answers the questions a task was about, or Claude finishes work the user asked for that matches an open task - and when the user asks to complete or close a task (/ticktick:done).
argument-hint: "[task or what was finished]"
---

# TickTick: tick off finished work

Tools are `mcp__ticktick__*` (load with ToolSearch). If the server is not connected, say so in one line and carry on with the conversation.

## 1. Notice the moment
A task is finished when the user and Claude agree on it, not when Claude thinks it might be:
- the user says it is done, moves on to the next thing after confirming the result, or answers what the task asked;
- or Claude completed exactly what the task describes and the user accepted the result.
Work that is half done, waiting on the user, or only drafted is not finished.

## 2. Find the task
Search open tasks (`search_task` by keywords from the work; if nothing, `get_project_with_undone_tasks` for the list the work belongs to - see the map `~/Documents/obsidian/glava7/_claude/ticktick/map.md`). Match by meaning, not exact words.
- One clear match -> continue.
- Several candidates -> ask once, naming them.
- No match -> do nothing and don't mention it. Never create a task just to complete it.

## 3. Tick it off
- Whole task finished -> `complete_task` (needs `projectId` from the task).
- Only some checklist items finished -> `complete_checklist_item` for those items; leave the task open.
- All items done -> complete the task itself.
Do not edit titles, dates or content while completing.

## 4. Report
One line, at the end of the reply: `ticked off: <title> (<list>)` or `ticked: <item> in <title>`.
If unsure whether the user considers it finished, ask in one line instead of completing - a wrongly closed task disappears from their view.
