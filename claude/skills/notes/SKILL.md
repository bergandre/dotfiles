---
name: notes
description: Record research results, fixes, decisions or keybinds into the Obsidian vault.
disable-model-invocation: true
argument-hint: [what to record / which note]
---

Record into the vault `~/Documents/obsidian/setup/` what the user asks: $ARGUMENTS
(if empty — the non-obvious results of this session; list them and confirm first).

## Where
- Note named by the user (e.g. "kd83a note") → find it with `find -iname`, use that.
- Keybinds → `hotkeys/<tool>.md` (nvim, arch, mac…); device-specific → `devices/<device>.md`
- Arch/system how-tos → `arch/`, shell → `shell/`, nvim config → `nvim/`, macOS → `macos/`
- Nothing fits → ask; don't invent folders.

## Style — short reminders, not a report
Notes are cheatsheets for future me: what a thing is for and how to use it.
Model: `hotkeys/nvim.md` — `#` title, `##`/`###` topic sections, one-line bullets.

- One bullet = one fact: `- \`key/command\` — what it does` or `- tool — what it's for`.
- Description ≤ ~8 words. No prose paragraphs, no intros, no explanations of why.
- Never write: problem descriptions, troubleshooting history, causes, diagnostics
  narrative, "next steps", "untested"/verification notes, sources, hardware IDs.
- Leave out anything that only mattered for this session's debugging.

Example (device note):
```
## Tools
- `sudo keyd monitor` — see which key is pressed
- `wev` — see what Hyprland receives

## Keybinds
- `Fn + W` — Win mode
- `Fn + M` — Mac mode
```

## How
- Read the target first; match its bullet format and language, append under the
  fitting section, skip duplicates. The style rules above win over an existing verbose note.
- Only record what was actually established in the conversation — don't fill gaps.
- Finish with one line per file: what was added, where.
