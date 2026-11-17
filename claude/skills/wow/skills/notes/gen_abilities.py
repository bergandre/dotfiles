"""Build WoW tooltip-style ability (spell) notes from Wowhead Forever spell tooltips.

usage: python3 -I gen_abilities.py <out_dir> [--by "<who>"] <spell_id> ... [--by ...] [--force]

Writes <out_dir>/<Spell Name>.md (callout card [!wow|spell] + ^card) and <out_dir>/icons/<icon>.jpg.
`--by` sets the "Used by" line for the ids after it (e.g. --by "Roogug (Razorfen Kraul)").
Existing notes are kept (only a missing "Used by" entry is added) unless --force.
A different spell with an existing note's name gets "<Name> (<id>).md".
"""
import html
import json
import re
import sys
import urllib.request
from pathlib import Path

TOOLTIP_URL = "https://nether.wowhead.com/forever/tooltip/spell/{}"
ICON_URL = "https://wow.zamimg.com/images/wow/icons/large/{}.jpg"
CACHE = Path("~/.cache/wow-tooltips/spell").expanduser()
DISPEL = ("Magic", "Curse", "Poison", "Disease")


def note_name(name: str) -> str:
    """Obsidian forbids : \\ / * ? " < > | # ^ [ ] in note names."""
    return re.sub(r'[\\/:*?"<>|#^\[\]]', "", name.replace(": ", " - ")).strip()


def fetch(spell_id: int) -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{spell_id}.json"
    if not f.exists() or not f.stat().st_size:
        with urllib.request.urlopen(TOOLTIP_URL.format(spell_id), timeout=20) as r:
            f.write_bytes(r.read())
    return json.loads(f.read_text())


def clean(s: str) -> str:
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    s = re.sub(r'<th><b class="q0"><br>Level \d+</b></th>', "", s)          # wowhead level slider
    s = re.sub(r'<(div|span) class="wowhead-tooltip-requirements">.*?</\1>', "", s)  # "Requires Shaman/level"
    s = re.sub(r'Tools:<br />\s*<div class="indent q1">.*?</div>', "", s, flags=re.S)
    return s.replace("&nbsp;", " ")


def header_lines(tt: str) -> list[str]:
    """Cost / range / cast time / cooldown rows (name and description removed)."""
    head = tt.split('<div class="q">', 1)[0]
    head = re.sub(r'<a class="whtt-name".*?</a>', "", head, flags=re.S)
    head = re.sub(r"<table[^>]*>", "\n", head)
    head = re.sub(r"<th[^>]*>\s*(.*?)\s*</th>", r'<span class="r">\1</span>', head, flags=re.S)
    head = re.sub(r"<br\s*/?>|</tr>", "\n", head)
    head = re.sub(r"</?(table|tr|td|b|a)\b[^>]*>", "", head)
    out = []
    for l in head.split("\n"):
        l = re.sub(r"\s+", " ", l).strip()
        if re.sub(r"<[^>]+>", "", l).strip():
            out.append(l)
    return out


def text(s: str) -> str:
    s = re.sub(r"<br\s*/?>", "<br>", s)
    s = re.sub(r"<(?!br>)[^>]+>", "", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def aura_line(buff: str) -> tuple[str, str]:
    """Buff/debuff tooltip -> one-line HTML block + dispel type."""
    if not buff:
        return "", ""
    buff = clean(buff)
    name = re.search(r'<b class="q">(.*?)</b>', buff)
    disp = re.search(r'<th class="q"><b class="q">(\w+)</b></th>', buff)
    body = buff.split("</table>", 2 if disp else 1)[-1]
    dur = re.search(r'<span class="q">(.*?)</span>', body)
    body = re.sub(r'<span class="q">.*?</span>', "", body)
    d = disp.group(1) if disp else ""
    h = '<span class="aura">'
    h += f'<span class="aura-name">{html.escape(name.group(1)) if name else ""}</span>'
    if d:
        h += f'<span class="r disp-{d.lower()}">{d}</span>'
    h += "<br>" + re.sub(r"^(<br>\s*)+|(\s*<br>)+$", "", text(body))
    if dur:
        h += f'<br><span class="dur">{text(dur.group(1))}</span>'
    return h + "</span>", d


def build(spell_id: int, dst: Path, by: str, force: bool) -> None:
    d = fetch(spell_id)
    name, icon = d["name"], d["icon"]
    tt = clean(d["tooltip"])
    path = dst / f"{note_name(name)}.md"
    if path.exists():
        m = re.search(r"^id: (\d+)$", path.read_text(), re.M)
        if m and int(m.group(1)) != spell_id:
            path = dst / f"{note_name(name)} ({spell_id}).md"
    by_line = f'> <span class="extra">Used by: {html.escape(by)}</span>' if by else ""
    if path.exists() and not force:
        t = path.read_text()
        if by_line and by_line not in t:
            path.write_text(t.replace("> [Wowhead]", f"{by_line}\n> [Wowhead]", 1))
            print(f"{spell_id}\t{path.stem}\t+ used by {by}")
        else:
            print(f"{spell_id}\t{path.stem}\tSKIP (exists)")
        return
    img = dst / "icons" / f"{icon}.jpg"
    if not img.exists():
        urllib.request.urlretrieve(ICON_URL.format(icon), img)
    desc = re.search(r'<div class="q">(.*?)</div>', tt, re.S)
    aura, disp = aura_line(d.get("buff", ""))
    plain = " ".join(header_lines(tt))
    cast = re.search(r"([\d.]+ sec cast|Instant|Channeled|Next Melee)", plain)
    lines = header_lines(tt) + ([f'<span class="desc">{text(desc.group(1))}</span>'] if desc else []) + \
        ([aura] if aura else []) + ([by_line[2:]] if by_line else [])
    body = "\n".join(f"> {l}" for l in lines)
    path.write_text(f"""---
id: {spell_id}
icon: {icon}.jpg
cast: {cast.group(1) if cast else ""}
dispel: {disp}
tags: [wow/ability]
---
> [!wow|spell] {name}
> ![[{icon}.jpg]]
{body}
> [Wowhead](https://www.wowhead.com/forever/spell={spell_id})

^card
""")
    print(f"{spell_id}\t{path.stem}\t{icon}.jpg\t{cast.group(1) if cast else '-'}\t{disp or '-'}")


def main(argv: list[str]) -> None:
    force = "--force" in argv
    args = [a for a in argv if a != "--force"]
    dst = Path(args[0]).expanduser()
    (dst / "icons").mkdir(parents=True, exist_ok=True)
    by, it = "", iter(args[1:])
    for a in it:
        if a == "--by":
            by = next(it)
            continue
        try:
            build(int(a), dst, by, force)
        except Exception as e:  # keep going; report which IDs failed
            print(f"{a}\tFAILED: {e}")


if __name__ == "__main__":
    main(sys.argv[1:])
