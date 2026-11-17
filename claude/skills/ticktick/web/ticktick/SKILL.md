---
name: ticktick
description: File TickTick tasks into the right list and tag using the user's map of areas, sort the Inbox, and tick off tasks once work is finished. Use whenever a TickTick task is about to be created or moved ("add a task", "remind me to", "make a todo for", a dictated batch, "sort my Inbox"), and whenever a piece of work that has a TickTick task behind it gets wrapped up in the conversation - the user says "done", "ok, next", "moving on", "that's finished", or asks to complete or close a task.
---

# TickTick

Works through the TickTick connector. If it is not connected, say so in one line: when adding, stop (do not fall back to a note or a file); when completing, carry on with the conversation.

`map.md` (next to this file) says what each folder, list and tag is for and holds the user's tie-break rules. TickTick decides what exists; the map only stores meaning. Never rely on IDs from the map - take them from live calls.

- Adding, moving or sorting tasks -> follow `add.md`.
- Ticking off finished work -> follow `done.md`.

The map in this skill is read-only. When it is out of date (a list was added, renamed or removed), do not try to save changes - tell the user the exact line to change in their map so they can update it locally and re-upload the skill.
