#!/usr/bin/env python3
"""Collect material for dungeons/<Dungeon>/map/<Dungeon> map data.md (boss / trash banners) and build its assets.

usage: python3 -I tactics.py "<Dungeon>" [--slug SLUG] [--force]

- method.gg (Forever guide): every boss / important trash mob -> its spell IDs + flag icons
  -> ability cards in Wow_FOREVER/abilities/ (gen_abilities.py, "Used by: <mob> (<Dungeon>)")
- warcrafttavern (Classic): per boss intro + Tank / Healer / Damage Dealers strategy (printed)
- art: boss portraits (foreverchanges.pro) + pencil sketches (DungeonJournal addon, few bosses)
  + method.gg model render per mob/boss tile -> art/method/<tile>.jpg (trash banners, portrait fallback)
  -> dungeons/<Dungeon>/art/; journal flag icons (method.gg) -> abilities/icons/ej-<flag>.png
Prints everything as raw material; the note itself is written by hand (see SKILL.md).
"""
import argparse
import html
import importlib.util
import re
import subprocess
import urllib.request
from pathlib import Path

VAULT = Path("~/Documents/obsidian/gaming/Wow_FOREVER").expanduser()
REPO = Path("~/repositories/wow-forever-addon-settings").expanduser()
FDJ = REPO / "Interface/AddOns/ForeverDungeonJournal"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"}
FLAGS = ["tank", "healer", "dps", "interrupt", "magic", "curse", "poison", "disease", "enrage",
         "important", "bleed", "physical", "nonphys", "boss"]

# gen_abilities.py lives in the notes skill; load it by path (no package, -I ignores cwd)
_spec = importlib.util.spec_from_file_location("gen_abilities", Path(__file__).parents[1] / "notes/gen_abilities.py")
assert _spec and _spec.loader
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


def get(url, binary=False):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
        d = r.read()
    return d if binary else d.decode("utf-8", "replace")


def plain(s):
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def method_mobs(slug):
    """[(name, flags, [(spell_id, spell_name)], [text lines], [important spell names], image path)] in page order
    (trash first, then bosses)."""
    page = get(f"https://www.method.gg/wow-forever/dungeons/{slug}")
    mobs = []
    for tile in page.split('<h3 class="mob-name">')[1:]:
        name, _, tile = tile.partition("</h3>")
        name, tile = plain(name), tile.split("<h2", 1)[0]          # stop at the next page section
        if name.endswith(" Loot"):
            continue
        flags = re.findall(r'dungeon-abilities/mob-([a-z]+)\.png', tile)
        spells = list(dict.fromkeys([(i, n) for i, n in re.findall(r'spell=(\d+)[^"]*"[^>]*>([^<]+)</a>', tile)
                                        if n.strip(" ,.") not in PLAYER_SPELLS]))
        text = [plain(li) for li in re.findall(r"<(?:li|p)>(.*?)</(?:li|p)>", tile, re.S)]
        img = re.search(r'src="(/images/guides/dungeons/[^"]+\.jpg)"', tile)
        mobs.append((name, flags, spells, [t for t in text if t], important(tile), img and img.group(1)))
    return mobs


# guides have no per-ability "important" tag (method.gg's Forever pages leave its tracker empty);
# the emphasis is in the prose -> spells linked in a sentence with one of these words
IMPORTANT_WORDS = re.compile(r"main mechanic|most important|dangerous|deadly|lethal|wipe|one-?shot|"
                             r"watch out|be careful|biggest threat|key mechanic|priority", re.I)


def important(tile):
    """Spell names the guide stresses (suggestion for the ej-important flag)."""
    hits = []
    for chunk in re.findall(r"<(?:li|p)[^>]*>(.*?)</(?:li|p)>", tile, re.S):
        for sent in re.split(r"(?<=[.!?])\s+(?=[A-Z<])", chunk):
            if IMPORTANT_WORDS.search(plain(sent)):
                hits += [plain(n).strip(" ,.:") for n in re.findall(r'spell=\d+[^"]*"[^>]*>([^<]+)</a>', sent)]
    return [n for n in dict.fromkeys(hits) if n not in PLAYER_SPELLS]


# spells the guide only mentions as advice (counters, kiting) - not mob abilities
PLAYER_SPELLS = {"Blessing of Freedom", "Tremor Totem", "Fear Ward", "Concussive Shot", "Earthbind Totem",
                 "Frost Nova", "Hamstring", "Polymorph", "Sap", "Shackle Undead", "Hibernate", "Banish"}


def tavern(slug):
    """{boss: (intro, {role: text})} from warcrafttavern's guide (Forever page first: Forever-only
    dungeons have no Classic one). No page -> {} (write the role tips from method.gg + tooltips)."""
    for section in ("forever", "wow-classic"):
        try:
            page = get(f"https://www.warcrafttavern.com/{section}/guides/{slug}/")
            break
        except Exception as e:
            print(f"  warcrafttavern {section}: {e}")
    else:
        return {}
    page = re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S)
    out = {}
    for blk in re.split(r"<h[2-4][^>]*>", page)[1:]:
        title, _, body = blk.partition("</h")
        title = plain(title)
        if title in ("Strategy",) and out:
            last = list(out)[-1]
            roles = {}
            for p in re.findall(r"<(?:p|li)[^>]*>(.*?)</(?:p|li)>", body, re.S):
                t = plain(p)
                m = re.match(r"(Tank|Healer|Damage Dealers):\s*(.*)", t)
                if m:
                    roles[m.group(1)] = m.group(2)
            out[last] = (out[last][0], roles)
        elif title and title not in ("Loot",):
            ps = [plain(p) for p in re.findall(r"<p[^>]*>(.*?)</p>", body, re.S)]
            out[title] = (next((p for p in ps if p), ""), {})
    return {k: v for k, v in out.items() if v[1]}


def magick(src, dst, *args):
    subprocess.run(["magick", str(src), *args, str(dst)], check=True)


def art(dungeon, slug, names):
    adir = VAULT / "dungeons" / dungeon / "art"
    adir.mkdir(parents=True, exist_ok=True)
    try:
        page = get(f"https://foreverchanges.pro/dungeons/{slug}")
    except Exception as e:  # Forever-only dungeons may have no foreverchanges page -> no portraits
        print(f"  foreverchanges {slug}: {e}")
        page = ""
    faces = {n: f for f, n in re.findall(r'/wow-ui/bosses/(\d+)\.webp\)[^>]*></span><span[^>]*>([^<]+)</span>', page)}
    npc = dict(re.findall(r'name = "([^"]+)",\s*npcID = (\d+)', (FDJ / "Data/Dungeons.lua").read_text()))
    disp = dict(re.findall(r"\[(\d+)\] = (\d+),\s*--", (FDJ / "Data/Bosses.lua").read_text()))
    made = []
    for n in names:
        if n in faces and not (adir / f"{n}.webp").exists():
            (adir / f"{n}.webp").write_bytes(get(f"https://foreverchanges.pro/wow-ui/bosses/{faces[n]}.webp", binary=True))
        sk = FDJ / "Media/RPG" / f"Sketch_{disp.get(npc.get(n, ''), 'x')}.tga"
        if sk.exists() and not (adir / f"{n} sketch.png").exists():
            magick(sk, adir / f"{n} sketch.png", "-trim", "+repage")
        made += [p.name for p in (adir / f"{n}.webp", adir / f"{n} sketch.png") if p.exists()]
    return made


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dungeon")
    ap.add_argument("--slug")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    slug = a.slug or re.sub(r"[^a-z0-9]+", "-", a.dungeon.lower().replace("'", "")).strip("-")

    adir = VAULT / "abilities"
    (adir / "icons").mkdir(parents=True, exist_ok=True)
    for f in FLAGS:
        p = adir / "icons" / f"ej-{f}.png"
        if not p.exists():
            try:
                raw = get(f"https://www.method.gg/images/icons/dungeon-abilities/mob-{f}.png", binary=True)
                subprocess.run(["magick", "-", "-resize", "48x48", str(p)], input=raw, check=True)
            except Exception as e:
                print(f"flag icon {f}: {e}")

    mobs = method_mobs(slug)
    print("# Abilities (method.gg) -> abilities/")
    mdir = VAULT / "dungeons" / a.dungeon / "art" / "method"   # mob renders: trash banners + boss pin fallback
    mdir.mkdir(parents=True, exist_ok=True)
    for name, flags, spells, text, imp, img in mobs:
        print(f"\n## {name}  flags={','.join(flags) or '-'}")
        f = mdir / f"{name.replace('/', '-')}.jpg"
        if img and not f.exists():
            f.write_bytes(get(f"https://www.method.gg{img}", binary=True))
        if imp:
            print(f"  ! important (guide stresses it -> add ![[ej-important.png|inline]]): {', '.join(imp)}")
        for sid, _ in spells:
            gen.build(int(sid), adir, f"{re.sub(r' [(]Rare Spawn[)]', '', name)} ({a.dungeon})", a.force)
        for t in text:
            print(f"  · {t}")

    print("\n# Role strategy (warcrafttavern)")
    for boss, (intro, roles) in tavern(slug).items():
        print(f"\n## {boss}\n  {intro}")
        for r, t in roles.items():
            print(f"  [{r}] {t}")

    names = [re.sub(r" \(Rare Spawn\)", "", n) for n, *_ in mobs]  # art() only finds files for bosses
    print("\n# Art -> dungeons/%s/art/: %s" % (a.dungeon, ", ".join(art(a.dungeon, slug, names))))


if __name__ == "__main__":
    main()
