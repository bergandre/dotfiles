#!/usr/bin/env python3
"""Dungeon map + boss pins from the ForeverDungeonJournal addon (the in-game journal's own map tab).

usage: python3 -I fdj_map.py "<Dungeon>" [--write]

Reads FDJ.DUNGEON_MAPS["<Dungeon>"] in <repo>/Interface/AddOns/ForeverDungeonJournal/Core/Journal.lua:
floors (map art TGA in Media/ + the used part texRight/texBottom), boss x/y per floor (normalized to the art,
placed by the addon author from in-game marks), entrance, floor transitions, NPCs inside (turnins).
- Floors with their own art -> map/<Dungeon> map.png: floors side by side (3+ floors: 2 columns), labelled
  "Level n" (or the floor's label). Pins are converted to % of that image.
- Floors drawn from the game client's map tiles (`tiles = Interface\\WorldMap\\...`, classic dungeons): the art
  is not in the addon -> no image; prints the raw positions only (they fit Blizzard's map, not foreverchanges').
Prints the boss pins (YAML for the main note), entrance + transitions (route anchors) and inside NPCs.
--write: sets `map:` and replaces every `kind: boss` pin in the main note's frontmatter (quest pins and the
route are left alone - move them yourself if the map changed).
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

REPO = Path("~/repositories/wow-forever-addon-settings").expanduser()
FDJ = REPO / "Interface/AddOns/ForeverDungeonJournal"
VAULT = Path("~/Documents/obsidian/gaming/Wow_FOREVER").expanduser()
MAX_W = 2400


def key(s):
    return re.sub(r"[^a-z]", "", s.lower())


def fdj_entry(dungeon):
    """The Lua table of FDJ.DUNGEON_MAPS["..."] as a dict (evaluated by lua, printed as JSON)."""
    src = (FDJ / "Core/Journal.lua").read_text(errors="replace")
    start = src.index("FDJ.DUNGEON_MAPS = {")
    for m in re.finditer(r'\n    \["([^"]+)"\] = \{', src[start:]):
        if key(m.group(1)) != key(dungeon):
            continue
        i = start + m.end() - 1  # the "{"
        depth, j = 0, i
        while True:
            c = src[j]
            depth += (c == "{") - (c == "}")
            if depth == 0:
                break
            j += 1
        lua = r'''
local function ser(v)
  if type(v) == "table" then
    local n, out = #v, {}
    if n > 0 then for _, x in ipairs(v) do out[#out+1] = ser(x) end return "[" .. table.concat(out, ",") .. "]" end
    for k, x in pairs(v) do out[#out+1] = string.format("%q", tostring(k)) .. ":" .. ser(x) end
    return "{" .. table.concat(out, ",") .. "}"
  elseif type(v) == "string" then return string.format("%q", v)
  elseif type(v) == "boolean" then return tostring(v)
  else return string.format("%.6f", v) end
end
print(ser(''' + src[i:j + 1] + "))"
        out = subprocess.run(["lua", "-e", lua], capture_output=True, text=True, check=True).stdout
        return m.group(1), json.loads(out.replace("\\\\", "/").replace("\\\n", " "))
    raise SystemExit(f"no FDJ.DUNGEON_MAPS entry for {dungeon}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dungeon")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    # "Scarlet Monastery/Graveyard" = a wing: folder dungeons/Scarlet Monastery/Graveyard/, files "Graveyard ..."
    full, base = a.dungeon.replace("/", " "), Path(a.dungeon).name
    name, e = fdj_entry(full)
    floors = e.get("floors", [])
    n = len(floors)
    cols = n if n <= 2 else 2
    rows = (n + cols - 1) // cols
    own_art = all("texture" in f for f in floors)
    print(f"# {name}: {n} floor(s), {'addon art' if own_art else 'client map tiles (no image)'}")

    def pct(fl, x, y):
        k = int(fl or 1) - 1
        c, r = k % cols, k // cols
        return round((c + float(x)) / cols * 100, 2), round((r + float(y)) / rows * 100, 2)

    ddir = VAULT / "dungeons" / a.dungeon
    out = ddir / "map" / f"{base} map.png"
    if own_art:
        out.parent.mkdir(parents=True, exist_ok=True)
        font = subprocess.run(["fc-match", "-f", "%{file}", "DejaVu Sans:bold"], capture_output=True, text=True).stdout
        parts = []
        for k, f in enumerate(floors):
            tga = FDJ / "Media" / (f["texture"].split("/")[-1] + ".tga")
            w, h = map(int, subprocess.run(["magick", "identify", "-format", "%w %h", str(tga)],
                                           capture_output=True, text=True, check=True).stdout.split())
            cw, ch = round(w * float(f.get("texRight", 1))), round(h * float(f.get("texBottom", 1)))
            part = out.parent / f".floor{k + 1}.png"
            cmd = ["magick", str(tga), "-crop", f"{cw}x{ch}+0+0", "+repage", "-resize", f"{MAX_W // cols}x"]
            if n > 1:
                cmd += ["-gravity", "south", "-font", font, "-pointsize", "34", "-fill", "#ffd100", "-stroke", "black",
                        "-strokewidth", "2", "-annotate", "+0+18", f.get("label") or f"Level {k + 1}"]
            subprocess.run(cmd + [str(part)], check=True)
            parts.append(str(part))
        tile = ["magick", "montage", *parts, "-tile", f"{cols}x{rows}", "-geometry", "+0+0", "-background", "black", str(out)]
        subprocess.run(tile if n > 1 else ["cp", parts[0], str(out)], check=True)
        for p in parts:
            Path(p).unlink()
        print(f"map -> {out}")

    pins = []
    for b in e.get("bosses", []):
        x, y = pct(b.get("floor"), b["x"], b["y"]) if own_art else (round(float(b["x"]) * 100, 1), round(float(b["y"]) * 100, 1))
        pins.append(f"  - {{kind: boss, name: {json.dumps(b['name']) if ':' in b['name'] else b['name']}, x: {x}, y: {y}}}")
    print("\npins (boss):\n" + "\n".join(pins))
    if e.get("entrance"):
        en = e["entrance"]
        print(f"\nentrance (route start): {list(pct(en.get('floor'), en['x'], en['y']))}")
    for t in e.get("transitions", []):
        lab = f"→ Level {int(float(t['to']))}" if t.get("to") else (t.get("labelKey") or "note")
        print(f"transition: {{x: {pct(t.get('floor'), t['x'], t['y'])[0]}, y: {pct(t.get('floor'), t['x'], t['y'])[1]}, label: {lab}}}")
    for t in e.get("turnins", []):
        print(f"NPC inside: {t['npc']} {list(pct(t.get('floor'), t['x'], t['y']))}")

    if a.write and own_art:
        main_note = ddir / f"{base}.md"
        s = main_note.read_text()
        m = re.match(r"---\n(.*?\n)---\n(.*)", s, re.S)
        if not m:
            raise SystemExit(f"{main_note.name}: no frontmatter")
        fm, body = m.groups()
        fm = re.sub(r"(?m)^  - \{kind: boss,.*\n", "", fm)
        fm = re.sub(r"(?m)^map:.*\n", "", fm)
        fm = f"map: {out.name}\n" + (fm.replace("pins:\n", "pins:\n" + "\n".join(pins) + "\n", 1) if "pins:\n" in fm
                                      else fm + "pins:\n" + "\n".join(pins) + "\n")
        main_note.write_text(f"---\n{fm}---\n{body}")
        print(f"\n{main_note.name}: map + {len(pins)} boss pins written (quest pins / route unchanged)")


if __name__ == "__main__":
    main()
