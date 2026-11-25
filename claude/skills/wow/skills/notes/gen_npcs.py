"""Build WoW tooltip-style NPC notes from Wowhead Forever NPC tooltips.

usage: python3 -I gen_npcs.py <out_dir> <npc_id> ... [--boss <npc_id> ...] [--force]

Writes <out_dir>/<Name>.md (callout card [!wow|npc] + ^card: title, level/type, faction, zone + coords,
/way line) and <out_dir>/icons/<icon>.jpg. Icon: skull for Elite/Boss/Rare and every id after --boss, group icon otherwise.
Existing notes are kept unless --force. Prints id, note name, icon, zone.
"""
import html
import json
import re
import sys
import urllib.request
from pathlib import Path

NPC_URL = "https://nether.wowhead.com/forever/tooltip/npc/{}"
ZONE_URL = "https://nether.wowhead.com/forever/tooltip/zone/{}"
ICON_URL = "https://wow.zamimg.com/images/wow/icons/large/{}.jpg"
CACHE = Path("~/.cache/wow-tooltips/npc").expanduser()
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) wow-notes"}
HOSTILE, FRIENDLY = "inv_misc_bone_skull_02", "inv_misc_groupneedmore"


def note_name(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|#^\[\]]', "", name.replace(": ", " - ")).strip()


def fetch(url: str, key: str) -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{key}.json"
    if not f.exists():
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
            f.write_bytes(r.read())
    return json.loads(f.read_text())


def main():
    args = [a for a in sys.argv[1:] if a != "--force"]
    force = "--force" in sys.argv
    out = Path(args[0]).expanduser()
    (out / "icons").mkdir(parents=True, exist_ok=True)
    boss = False
    for nid in args[1:]:
        if nid == "--boss":
            boss = True; continue
        try:
            j = fetch(NPC_URL.format(nid), nid)
        except Exception as e:
            print(f"{nid}\tFAILED: {e}"); continue
        name = j["name"]
        rows = [html.unescape(re.sub(r"<[^>]+>", "", r)).strip()
                for r in re.findall(r"<td>(.*?)</td>", j.get("tooltip", ""), re.S)]
        rows = [r for r in rows if r and r != name]
        level = next((r for r in rows if r.startswith("Level")), "")
        title = next((r for r in rows if r != level and not r.startswith("Level")), "")
        faction = rows[-1] if len(rows) > 2 and rows[-1] not in (title, level) else ""
        if faction == title:
            faction = ""
        zone, coords = "", None
        m = j.get("map") or {}
        if m.get("zone"):
            try:
                zone = fetch(ZONE_URL.format(m["zone"]), f"zone_{m['zone']}")["name"]
            except Exception:
                zone = ""
            pts = [p for lst in (m.get("coords") or {}).values() for p in lst]
            coords = pts[0] if pts and any(pts[0]) else None  # instances report 0,0
        icon = HOSTILE if boss or re.search(r"Elite|Boss|Rare", level) else FRIENDLY
        icon_file = out / "icons" / f"{icon}.jpg"
        if not icon_file.exists():
            with urllib.request.urlopen(urllib.request.Request(ICON_URL.format(icon), headers=UA), timeout=20) as r:
                icon_file.write_bytes(r.read())
        note = out / f"{note_name(name)}.md"
        if note.exists() and not force:
            print(f"{nid}\t{note.stem}\tSKIP (exists)"); continue
        where = f"{zone} {coords[0]}, {coords[1]}" if coords else zone
        lines = ["---", f"id: {nid}", f"icon: {icon}.jpg", f"zone: {zone}",
                 f"coords: {coords[0]} {coords[1]}" if coords else "coords:", "tags: [wow/npc]", "---",
                 f"> [!wow|npc] {name}", f"> ![[{icon}.jpg]]"]
        if title:
            lines.append(f"> <span class=\"npc-title\">&lt;{html.escape(title)}&gt;</span>")
        if level:
            lines.append(f"> {html.escape(level)}")
        if faction:
            lines.append(f"> <span class=\"extra\">{html.escape(faction)}</span>")
        if where:
            lines.append(f"> <span class=\"npc-where\">{html.escape(where)}</span>")
        if coords:
            lines.append(f"> `/way {zone} {coords[0]} {coords[1]}`")
        lines += [f"> [Wowhead](https://www.wowhead.com/forever/npc={nid})", "", "^card", ""]
        note.write_text("\n".join(lines), encoding="utf-8")
        print(f"{nid}\t{note.stem}\t{icon}.jpg\t{where}")


if __name__ == "__main__":
    main()
