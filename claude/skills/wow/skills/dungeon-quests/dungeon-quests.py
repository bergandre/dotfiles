#!/usr/bin/env python3
"""Extract a dungeon's quest chain from the local Zygor Forever guides.

Usage: dungeon-quests.py "<Dungeon>" [--faction Horde|Alliance]
Prints accept/collect/kill/turnin steps (quest IDs, coords) plus an in-game
/run macro that checks which of those quests are done / in the log.
"""
import os
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WOW_REPO", "~/repositories/wow-forever-addon-settings")).expanduser()
GUIDES = ROOT / "Interface/AddOns/ZygorGuidesViewerForever/Guides-Forever/Dungeons"
STEP_RE = re.compile(r"^\s*(accept|turnin|collect|kill|talk|click|use|\|tip)\b(.*)$")
QID_RE = re.compile(r"##(\d+)")
QREF_RE = re.compile(r"\|q (\d+)")


def find_guide(text: str, dungeon: str):
    """Return (title, body) of the '<Dungeon> Quests' guide, case-insensitive fuzzy."""
    heads = list(re.finditer(r'RegisterGuide\("Dungeon Guides\\\\([^"]+)"', text))
    want = dungeon.lower()
    for i, m in enumerate(heads):
        title = m.group(1)
        if title.lower().endswith("quests") and want in title.lower():
            end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
            return title, text[m.start():end]
    return None, None


def clean(line: str) -> str:
    line = re.sub(r"\|only if walking|\|future|\|c\b|\|noway", "", line)
    line = re.sub(r"\|goto ([^|<]+?)(?:\s*<\s*\d+)?(?=\||$)", r" @ \1", line)
    return re.sub(r"\s+", " ", line).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dungeon")
    ap.add_argument("--faction", default="Horde", choices=["Horde", "Alliance"])
    a = ap.parse_args()

    src = GUIDES / f"ZygorDungeon{a.faction}CLASSIC.lua"
    title, body = find_guide(src.read_text(errors="replace"), a.dungeon)
    if not body:
        sys.exit(f"No '{a.dungeon} ... Quests' guide in {src.name}. "
                 f"List: grep -o 'Dungeon Guides\\\\\\\\[^\"]*Quests' {src}")

    print(f"# {title}  ({src.name})\n")
    qids, names = [], {}
    for raw in body.splitlines():
        m = STEP_RE.match(raw)
        if not m:
            continue
        line = clean(raw)
        for q in QID_RE.findall(raw) if m.group(1) in ("accept", "turnin") else []:
            names.setdefault(q, re.sub(r"##\d+.*", "", line.split(" ", 1)[1]).strip())
        for q in QREF_RE.findall(raw) + (QID_RE.findall(raw) if m.group(1) in ("accept", "turnin") else []):
            if q not in qids:
                qids.append(q)
        print("-", line)

    print("\n## Quest IDs")
    for q in qids:
        print(f"- {q}  {names.get(q, '(started from item/drop, see steps)')}")
    ids = ",".join(qids)
    print("\n## In-game check (paste in chat; prints done / log / -)")
    print('/run for _,q in ipairs({%s})do local L=C_QuestLog print(q,L.IsQuestFlaggedCompleted(q) and "done" or (L.IsOnQuest and L.IsOnQuest(q)) and "log" or "-")end' % ids)


if __name__ == "__main__":
    main()
