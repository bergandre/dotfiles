"""Link every mention of a carded item / player ability / NPC in vault notes.

usage: python3 -I linkify.py [--dry] <note.md> ...

Plain-text names that have a card in items/, abilities/ (player cards: "Used by: Warrior..."), npcs/ become
`![[icon|inline]] [[Card|Name]]` (pipe escaped in table rows). A name that is also a heading in the same note
links to that heading instead (`[[#Name]]`, Obsidian jumps there). Skips frontmatter, headings, HTML lines,
code blocks, existing links and URLs. Longest names first; whole words, case-sensitive.
ALIASES: shorthand in the user's notes -> card ("Imp Rend" -> Improved Rend).
"""
import re
import sys
from pathlib import Path

VAULT = Path("~/Documents/obsidian/gaming/Wow_FOREVER").expanduser()
ALIASES = {"Imp Rend": "Improved Rend", "Imp Overpower": "Improved Overpower", "Imp Charge": "Improved Charge",
           "Imp Slam": "Improved Slam", "2H Spec": "Two-Handed Weapon Specialization", "Sunder": "Sunder Armor",
           "Demo Shout": "Demoralizing Shout", "Weapon Master": "Weaponmaster", "Parry": "Deflection", "Aegis": "Aegis of the Scarlet Commander"}


def cards():
    out = {}  # display name -> (note, icon)
    for folder in ("items", "npcs", "abilities"):
        for f in (VAULT / folder).glob("*.md"):
            s = f.read_text(encoding="utf-8")
            icon = re.search(r"^icon:\s*(\S+)", s, re.M)
            if not icon:
                continue
            name = re.sub(r" \(\d+\)$", "", f.stem)
            if folder == "abilities":
                if "Used by: Warrior" not in s:
                    continue  # boss abilities are linked by the dungeon skills
                if name in out and out[name][0] == name and f.stem != name:
                    pass
            if name in out and folder != "abilities":
                continue
            out[name] = (f.stem, icon.group(1))
    for short, full in ALIASES.items():
        if full in out:
            out[short] = out[full]
    return out


SKIP = re.compile(r"!?\[\[[^\]]*\]\]|\[[^\]]*\]\([^)]*\)|`[^`]*`|https?://\S+|<[^>]+>")


def link_line(line, names, rx, heads, table):
    bar = "\\|" if table else "|"
    parts, pos = [], 0
    for m in SKIP.finditer(line):
        parts.append((line[pos:m.start()], True)); parts.append((m.group(0), False)); pos = m.end()
    parts.append((line[pos:], True))
    out = []
    for text, free in parts:
        if not free:
            out.append(text); continue
        def sub(m):
            name = m.group(0)
            if name in heads:
                return f"[[#{name}{bar}{name}]]"
            note, icon = names[name]
            link = f"[[{note}]]" if note == name else f"[[{note}{bar}{name}]]"
            return f"![[{icon}{bar}inline]] {link}"
        out.append(rx.sub(sub, text))
    return "".join(out)


def main():
    dry = "--dry" in sys.argv
    names = cards()
    rx = re.compile(r"(?<![\w'-])(" + "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True)) + r")(?![\w'-])")
    for path in [a for a in sys.argv[1:] if a != "--dry"]:
        p = Path(path)
        lines = p.read_text(encoding="utf-8").split("\n")
        heads = {re.sub(r"^#+\s*", "", l).strip() for l in lines if l.startswith("#")}
        fm, fence, changed = False, False, 0
        for i, l in enumerate(lines):
            if l.lstrip().startswith("```"):
                fence = not fence; continue
            if fence:
                continue  # macros / code must stay plain text
            if i == 0 and l == "---":
                fm = True; continue
            if fm:
                fm = l != "---"; continue
            if l.startswith("#") or l.lstrip().startswith("<") or "class=\"wowtal\"" in l:
                continue
            new = link_line(l, names, rx, heads, l.lstrip().startswith("|"))
            if new != l:
                changed += 1
                if dry:
                    print(f"  {p.name}:{i + 1}: " + re.sub(r"!\[\[[^\]]*inline\]\] ", "", new)[:150])
                lines[i] = new
        if not dry and changed:
            p.write_text("\n".join(lines), encoding="utf-8")
        print(f"{p}: {changed} lines")


if __name__ == "__main__":
    main()
