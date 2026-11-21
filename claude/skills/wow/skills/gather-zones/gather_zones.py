"""Gathering-profession zone note for the Obsidian vault (WoW Forever).

usage:
  python3 -I gather_zones.py <prof> --stats        per route zone: nodes, share, skill for half / all nodes
  python3 -I gather_zones.py <prof> [--shift N]    write professions/<prof>/<prof>.md + zone maps, stamp item cards

<prof> = herbalism | mining. Judgment (arrival skill per zone, Targets rows, char) lives in config/<prof>.json.
--shift N moves yellow/green/grey by N after the user compares tooltip colours in-game.

Data: GatherRadar Core/Nodes.lua (node -> name, item, skill) + Data/Import<Kind>.lua (Forever node
coords, GatherMate2 encoding), Wowhead Classic zone maps (cached in ~/.cache/wow-zone-maps).
"""
import argparse, collections, io, json, os, re, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
REPO = Path(os.environ.get("WOW_REPO", Path.home() / "repositories/wow-forever-addon-settings"))
GR = REPO / "Interface/AddOns/GatherRadar"
VAULT = Path.home() / "Documents/obsidian/gaming/Wow_FOREVER"
MAP_URL = "https://wow.zamimg.com/images/wow/classic/maps/enus/zoom/{}.jpg"

PROFS = {"herbalism": ("herb", "Herbalism", "Herb", "Herbs", "herbs"), "mining": ("ore", "Mining", "Node", "Ore", "ore")}

# Horde route from level 1: union of RestedXP Forever Guide (H) (questing, "Q") and Forever Dungeon Guide (H)
# ("D"); revisits merged. zone -> (uiMapID, wowhead area id for the map image or None, levels, guide)
ROUTE = [("Durotar", 1411, 14, "1–12", "QD"), ("Mulgore", 1412, 215, "1–12", "QD"),
         ("Tirisfal Glades", 1420, 85, "1–12", "QD"), ("Zephras Isle", 2521, None, "1–13", "QD"),
         ("Silverpine Forest", 1421, 130, "12–14", "Q"), ("The Barrens", 1413, 17, "12–21, 25–26", "QD"),
         ("Stonetalon Mountains", 1442, 406, "17–22, 24–26", "Q"), ("Ashenvale", 1440, 331, "17–22, 26–28", "QD"),
         ("Hillsbrad Foothills", 1424, 267, "22–24, 30–33", "QD"), ("Thousand Needles", 1441, 400, "28–30, 33–35", "QD"),
         ("Arathi Highlands", 1417, 45, "30–33, 38–39", "QD"), ("Wetlands", 1437, 11, "32–33", "D"),
         ("Alterac Mountains", 1416, 36, "33–34, 38–39", "QD"), ("Desolace", 1443, 405, "34–35, 41", "Q"),
         ("Stranglethorn Vale", 1434, 33, "35–37, 40–41, 44–45, 50–51", "QD"),
         ("Dustwallow Marsh", 1445, 15, "37–38, 41–43", "QD"), ("Badlands", 1418, 3, "39–40", "QD"),
         ("Swamp of Sorrows", 1435, 8, "41, 45–46", "QD"), ("Tanaris", 1446, 440, "41–43, 46–48", "QD"),
         ("Feralas", 1444, 357, "43–44, 49–50", "QD"), ("The Hinterlands", 1425, 47, "48–49", "QD"),
         ("Blasted Lands", 1419, 4, "50–51", "QD"), ("Searing Gorge", 1427, 51, "51–52", "QD"),
         ("Burning Steppes", 1428, 46, "51–52", "QD"), ("Azshara", 1447, 16, "52–53", "QD"),
         ("Felwood", 1448, 361, "53–54, 55–56", "QD"), ("Un'Goro Crater", 1449, 490, "54–55", "QD"),
         ("Winterspring", 1452, 618, "55–56, 58–60", "QD"), ("Western Plaguelands", 1422, 28, "56–59", "QD"),
         ("Eastern Plaguelands", 1423, 139, "56–59", "QD"), ("Silithus", 1451, 1377, "58–60", "QD")]
GUIDE = {"QD": "both", "Q": "questing", "D": "dungeon"}

PALETTE = ["#ff4d4d", "#4da6ff", "#ffd11a", "#5ce65c", "#ff8c1a", "#d98cff", "#ffffff", "#00e6e6", "#ff66b3", "#a6a600"]
# character level -> item-quality colour class (wow.css .lv-*)
LEVEL_BANDS = [(5, "poor"), (10, "common"), (25, "uncommon"), (45, "rare"), (61, "epic")]


def node_defs(kind):
    """{node id: (name, item id or None, skill)} from GatherRadar's Add("<kind>", {...}) block."""
    src = (GR / "Core/Nodes.lua").read_text(encoding="utf-8")
    block = re.search(rf'Add\("{kind}", \{{(.*?)\n\}}\)', src, re.S)[1]
    return {int(i): (n, int(it) if it != "nil" else None, int(sk))
            for i, n, it, sk in re.findall(r'\{ (\d+), "([^"]+)", (\w+), (\d+) \}', block)}


def nodes(kind):
    out, cur = collections.defaultdict(list), None
    for line in (GR / f"Data/Import{kind.capitalize()}.lua").read_text(encoding="utf-8").splitlines():
        if m := re.match(r"\t\[(\d+)\] = \{", line):
            cur = int(m[1])
        elif m := re.match(r"\t\t\[(\d+)\] = (\d+)", line):
            c = int(m[1])  # GatherMate2 coord: xxxx yyyy 00
            out[cur].append((c // 1000000 / 10000, c % 1000000 // 100 / 10000, int(m[2])))
    return out


def item_notes():
    """item id -> (note name, icon) for every card in items/."""
    out = {}
    for p in (VAULT / "items").glob("*.md"):
        t = p.read_text(encoding="utf-8")
        if (i := re.search(r"^id: (\d+)$", t, re.M)) and (ic := re.search(r"^icon: (.+)$", t, re.M)):
            out[int(i[1])] = (p.stem, ic[1])
    return out


def colours(req, shift):
    cap = lambda v: str(v) if v <= 300 else "—"
    return str(req), cap(req + 25 + shift), cap(req + 50 + shift), cap(req + 100 + shift)


def span(cls, v):
    return f'<span class="{cls}">{v}</span>'


def colour_cells(req, shift):
    return " | ".join(span(c, v) for c, v in zip(("sk-o", "sk-y", "sk-g", "sk-x"), colours(req, shift)))


def level_span(levels):
    first = int(re.match(r"\d+", str(levels))[0])
    return span("lv-" + next(c for top, c in LEVEL_BANDS if first < top), levels)


def stamp_card(note, prof_name, req, shift):
    """Add 'Requires <Prof> N' + colour line to an item card (idempotent; lowest skill wins for shared items)."""
    p = VAULT / "items" / f"{note}.md"
    t = p.read_text(encoding="utf-8")
    t = re.sub(r"^gather: .*\n", "", t, flags=re.M)
    t = re.sub(r'^> <span class="extra">Requires \w+ \d+</span>\n> <span class="sk-o">.*\n', "", t, flags=re.M)
    o, y, g, x = colours(req, shift)
    t = t.replace("tags: [wow/item]", f"gather: {req}\ntags: [wow/item]", 1)
    t = t.replace("> [Wowhead]", f'> <span class="extra">Requires {prof_name} {req}</span>\n'
                  f'> {span("sk-o", o)} · {span("sk-y", y)} · {span("sk-g", g)} · {span("sk-x", x)}\n> [Wowhead]', 1)
    p.write_text(t, encoding="utf-8")


def draw_map(path, area, pts, colour_of):
    if area is None:  # Forever-only zone: no Wowhead map image -> plain parchment, dots only
        im = Image.new("RGB", (1544, 1030), "#c9a96e")
    else:
        cache = Path.home() / ".cache/wow-zone-maps"
        cache.mkdir(parents=True, exist_ok=True)
        f = cache / f"{area}.jpg"
        if not f.exists():
            req = urllib.request.Request(MAP_URL.format(area), headers={"User-Agent": "Mozilla/5.0"})
            f.write_bytes(urllib.request.urlopen(req, timeout=30).read())
        im = Image.open(io.BytesIO(f.read_bytes())).convert("RGB")
        im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS)
    d, r = ImageDraw.Draw(im), 6
    for x, y, n in pts:
        cx, cy = x * im.width, y * im.height
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=colour_of[n], outline="black", width=2)
    path.parent.mkdir(exist_ok=True)
    im.save(path)


def stats(kind, defs, data):
    for zone, mid, _, levels, _ in ROUTE:
        cnt = collections.Counter(n for _, _, n in data[mid] if n in defs)
        tot = sum(cnt.values())
        if not tot:
            print(f"{zone} ({levels}): no nodes"); continue
        acc, half = 0, None
        for n in sorted(cnt, key=lambda n: defs[n][2]):
            acc += cnt[n]
            half = half or (defs[n][2] if acc >= tot / 2 else None)
        full = max(defs[n][2] for n in cnt if cnt[n] >= 10)
        print(f"{zone} ({levels}) | half {half} | all {full} | " +
              ", ".join(f"{defs[n][0]} {defs[n][2]} {cnt[n] * 100 // tot}%" for n in sorted(cnt, key=lambda n: defs[n][2])))


BENCH_LEVELS = range(1, 61)
CHAR_LEVELS = range(5, 61, 5)  # per-char tables


def bench(targets, lvl):
    """Skill to have at lvl: linear between consecutive Targets (level, skill) points, flat after the last."""
    pts = sorted({}.fromkeys((x["level"], x["skill"]) for x in targets))  # keeps max skill per level last
    pts = sorted({l: max(s for l2, s in pts if l2 == l) for l, _ in pts}.items())
    for (l0, s0), (l1, s1) in zip(pts, pts[1:]):
        if l0 <= lvl <= l1:
            return round(s0 + (s1 - s0) * (lvl - l0) / (l1 - l0))
    return pts[-1][1] if lvl >= pts[-1][0] else pts[0][1]


# benchmark columns in groups (profession pairs that feed each other), each:
# (note name, label, how, colour rgb). "route" = interpolated Targets from config/<note>.json,
# "skin" = skill to skin mobs of your level, "x5" = 5 x level (rule of thumb, no zone data)
BENCH_GROUPS = [
    [("mining", "Mining", "route", "205, 120, 60"), ("blacksmithing", "Blacksmithing", "x5", "150, 165, 185"),
     ("engineering", "Engineering", "x5", "255, 170, 30")],
    [("cooking", "Cooking", "x5", "255, 110, 50"), ("fishing", "Fishing", "x5", "50, 140, 255")],
    [("herbalism", "Herbalism", "route", "90, 200, 70"), ("alchemy", "Alchemy", "x5", "40, 200, 180")],
    [("skinning", "Skinning", "skin", "150, 85, 50"), ("leatherworking", "Leatherworking", "x5", "200, 160, 100")],
    [("tailoring", "Tailoring", "x5", "235, 80, 160"), ("enchanting", "Enchanting", "x5", "170, 90, 255"),
     ("first aid", "First Aid", "x5", "235, 50, 60")],
]
BENCH_PROFS = [p for g in BENCH_GROUPS for p in g]
CSS = VAULT.parent / ".obsidian/snippets/wow.css"


def write_bench_css():
    """Rewrite the prof-bench block in wow.css from BENCH_GROUPS (column colours + group separators)."""
    # W = the level table only: it is the one with a column per profession (char tables have 5 columns)
    W = f".prof-bench table:has(th:nth-child({len(BENCH_PROFS) + 1}))"
    rules, col = [], 2
    for g in BENCH_GROUPS:
        for i, (_, label, _, rgb) in enumerate(g):
            sep = " border-left: 3px solid #ffd100;" if i == 0 else ""
            rules.append(f"{W} :is(th, td):nth-child({col}) {{ --rgb: {rgb};{sep} }} /* {label} */")
            col += 1
    block = "\n".join([
        "/* prof-bench:start - generated by gather-zones/gather_zones.py, edit BENCH_GROUPS there */",
        "/* professions/profession-benchmarks.md: themed colour per profession, gold line between groups,",
        "   sticky header row + level column, hovered row outlined */",
        f"{W} {{ border-collapse: separate; border-spacing: 0; }}",
        f"{W} :is(th, td) {{ text-align: center; --rgb: 0, 0, 0; --a: .22; }}",
        *rules,
        f"{W} :is(th, td) {{",
        "  background: linear-gradient(rgba(var(--rgb), var(--a)), rgba(var(--rgb), var(--a))), var(--background-primary); }",
        f"{W} thead th {{ --a: .55; color: #fff; position: sticky; top: 0; z-index: 2; }}",
        f"{W} :is(th, td):first-child {{ --a: 0; position: sticky; left: 0; z-index: 1; }}",
        f"{W} thead th:first-child {{ z-index: 3; }}",
        f"{W} thead th a {{ color: #fff; }}",
        f"{W} tbody tr:hover td {{ box-shadow: inset 0 2px 0 #ffd100, inset 0 -2px 0 #ffd100; }}",
        ".prof-bench .rk-app { color: #ffffff; }",
        ".prof-bench .rk-jour { color: #1eff00; }",
        ".prof-bench .rk-exp { color: #0070dd; filter: brightness(1.4); }",
        ".prof-bench .rk-art { color: #a335ee; filter: brightness(1.3); }",
        "/* prof-bench:end */"])
    css = CSS.read_text(encoding="utf-8")
    css = re.sub(r"/\* prof-bench:start.*?/\* prof-bench:end \*/", lambda m: block, css, flags=re.S) \
        if "prof-bench:start" in css else css.rstrip("\n") + "\n\n" + block + "\n"
    CSS.write_text(css, encoding="utf-8")


def skin_skill(lvl):
    """Classic skinning requirement for a mob of level lvl: <=10 -> 1, 11-20 -> (lvl-10)*10, 21+ -> lvl*5."""
    return 1 if lvl <= 10 else (lvl - 10) * 10 if lvl <= 20 else min(lvl * 5, 300)


# skill -> rank whose range it is in (cap 75 / 150 / 225 / 300), coloured like item quality in wow.css
RANKS = [(75, "app", "Apprentice"), (150, "jour", "Journeyman"), (225, "exp", "Expert"), (300, "art", "Artisan")]


def rank_span(skill):
    cls = next(c for cap, c, _ in RANKS if skill <= cap)
    return f'<span class="rk-{cls}">{skill}</span>'


def write_benchmarks():
    """professions/profession-benchmarks.md: contents, per played char (config/chars.json) its professions
    every 5 levels, then every profession at every level 1-60."""
    cfgs = {n: json.loads((HERE / "config" / f"{n}.json").read_text(encoding="utf-8"))
            for n, _, how, _ in BENCH_PROFS if how == "route"}
    calc = {"route": lambda n, l: bench(cfgs[n]["targets"], l), "skin": lambda n, l: skin_skill(l),
            "x5": lambda n, l: min(l * 5, 300)}
    prof = {n: (lab, how) for n, lab, how, _ in BENCH_PROFS}
    chars = json.loads((HERE / "config/chars.json").read_text(encoding="utf-8"))
    md = ["---", "cssclasses: [prof-bench]", "---",  # column colours + sticky header in wow.css
          "# Profession benchmarks — Horde route (RestedXP Forever)", "",
          *[f"- [[#{c}]]" for c in chars], "- [[#Level benchmarks]]", "",
          "Skill colour = rank range: " + " · ".join(
              f'<span class="rk-{c}">{name} {lo}–{cap}</span>'
              for (cap, c, name), lo in zip(RANKS, (1, 76, 151, 226)))]
    for char, profs in chars.items():  # static: only config, no live skill data
        md += ["", f"## {char}", "| Level | " + " | ".join(f"[[{n}\\|{prof[n][0]}]]" for n in profs) + " |",
               "|---|" + "---|" * len(profs)]
        md += [f"| {level_span(lvl)} | " + " | ".join(rank_span(calc[prof[n][1]](n, lvl)) for n in profs) + " |"
               for lvl in CHAR_LEVELS]
    md += ["", "## Level benchmarks",
           "| Level | " + " | ".join(f"[[{n}\\|{lab}]]" for n, lab, _, _ in BENCH_PROFS) + " |",
           "|---|" + "---|" * len(BENCH_PROFS)]
    for lvl in BENCH_LEVELS:
        md.append(f"| {level_span(lvl)} | " + " | ".join(str(calc[how](n, lvl)) for n, _, how, _ in BENCH_PROFS) + " |")
    (VAULT / "professions/profession-benchmarks.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    write_bench_css()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prof", choices=[*PROFS, "benchmarks"])
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--shift", type=int, default=0)
    a = ap.parse_args()
    if a.prof == "benchmarks":
        return write_benchmarks()
    kind, prof_name, col, plural, suffix = PROFS[a.prof]
    defs, data = node_defs(kind), nodes(kind)
    if a.stats:
        return stats(kind, defs, data)

    cfg = json.loads((HERE / "config" / f"{a.prof}.json").read_text(encoding="utf-8"))
    items = item_notes()
    missing = sorted({it for _, it, _ in defs.values() if it and it not in items})
    if missing:
        raise SystemExit("no item card for ids " + " ".join(map(str, missing)) +
                         "\n-> python3 -I ~/.claude/skills/wow/skills/notes/gen_cards.py "
                         f"{VAULT}/items " + " ".join(map(str, missing)))

    # tier = rank of the node's skill among nodes on the route (same skill -> same tier)
    on_route = {p[2] for _, m, _, _, _ in ROUTE for p in data[m]}
    tier = {sk: i for i, sk in enumerate(sorted({d[2] for n, d in defs.items() if n in on_route}), 1)}

    def link(n, table=True):
        name, it, sk = defs[n]
        t = f" (T{tier[sk]})" if sk in tier else ""
        if not it:
            return name + t  # Forever-only node, no known item
        note, icon = items[it]
        bar = "\\|" if table else "|"  # bare pipe would split a table cell
        alias = f"{bar}{name}" if note != name and kind == "ore" else ""
        return f"![[{icon}{bar}inline]] [[{note}{alias}]]{t}"

    by_name = {d[0]: n for n, d in defs.items()}
    have = cfg["have"]
    head = {z: f"{z} — {lv} — have {have[z]}" for z, _, _, lv, _ in ROUTE}

    # cards: lowest skill per item
    low = {}
    for n, (_, it, sk) in defs.items():
        if it:
            low[it] = min(low.get(it, 999), sk)
    for it, sk in low.items():
        stamp_card(items[it][0], prof_name, sk, a.shift)

    zlink = lambda z: f"[[#{head[z]}\\|{z}]]"
    md = [f"# {prof_name} — Horde route (RestedXP Forever)", "", "## Zones",
          "| Levels | Zone | Have | Guide |", "|---|---|---|---|"]
    md += [f"| {level_span(lv)} | {zlink(z)} | {have[z]} | {GUIDE[g]} |" for z, _, _, lv, g in ROUTE]
    md += ["", "## Targets", f"| Level | Skill | {plural} | Zone |", "|---|---|---|---|"]
    for t in cfg["targets"]:
        what = ", ".join(link(by_name[n]) for n in t.get("nodes", [])) or t.get("note", "")
        where = ", ".join(zlink(z) for z in t.get("zones", []))
        md.append(f"| {level_span(t['level'])} | {t['skill']} | {what} | {where} |")
    md += ["", "## Ranks"] + [f"- {r}" for r in cfg["ranks"]]
    md += ["", f"## {plural}", f"| {col} | Pick | Yellow | Green | Grey |", "|---|---|---|---|---|"]
    md += [f"| {link(n)} | {colour_cells(d[2], a.shift)} |" for n, d in sorted(defs.items(), key=lambda x: x[1][2])
           if n in on_route]

    for zone, mid, area, levels, _ in ROUTE:
        pts = [p for p in data[mid] if p[2] in defs]
        cnt = collections.Counter(n for _, _, n in pts)
        if not cnt:
            continue
        order = sorted(cnt, key=lambda n: defs[n][2])
        colour_of = {n: PALETTE[i % len(PALETTE)] for i, n in enumerate(order)}
        img = f"{zone} {suffix}.png"
        draw_map(VAULT / "professions" / a.prof / "maps" / img, area, pts, colour_of)  # professions/<prof>/maps/
        md += ["", f"## {head[zone]}", f"![[{img}]]", "",
               f"| | {col} | Share | Pick | Yellow | Green | Grey |", "|---|---|---|---|---|---|---|"]
        for n in order:
            share = cnt[n] * 100 / len(pts)
            share = f"{share:.0f}%" if share >= 1 else "<1%"
            md.append(f'| <span class="dot" style="color:{colour_of[n]}">●</span> | {link(n)} | {share} | '
                      f"{colour_cells(defs[n][2], a.shift)} |")
    out = VAULT / "professions" / a.prof / f"{a.prof}.md"  # one folder per profession
    out.write_text("\n".join(md) + "\n", encoding="utf-8")
    write_benchmarks()
    print(f"wrote {out} + maps in professions/{a.prof}/maps/ + professions/profession-benchmarks.md")


main()
