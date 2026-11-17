# Ticking off finished work

## 1. Notice the moment

A task is finished when the user and Claude agree on it, not when Claude thinks it might be:
- the user says it is done, moves on to the next thing after confirming the result, or answers what the task asked;
- or Claude completed exactly what the task describes and the user accepted the result.

Work that is half done, waiting on the user, or only drafted is not finished.

## 2. Find the task

Search open tasks by keywords from the work; if nothing, fetch the undone tasks of the list the work belongs to (see `map.md`). Match by meaning, not exact words.
- One clear match -> continue.
- Several candidates -> ask once, naming them.
- No match -> do nothing and don't mention it. Never create a task just to complete it.

## 3. Tick it off

- Whole task finished -> complete the task (needs `projectId` from the task).
- Only some checklist items finished -> complete those checklist items; leave the task open.
- All items done -> complete the task itself.

Do not edit titles, dates or content while completing.

## 4. Report

One line, at the end of the reply: `ticked off: <title> (<list>)` or `ticked: <item> in <title>`.
If unsure whether the user considers it finished, ask in one line instead of completing - a wrongly closed task disappears from their view.
