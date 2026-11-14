"""Build WoW tooltip-style item notes from Wowhead Forever tooltips.

usage: python3 -I gen_cards.py <out_dir> <item_id> [<item_id> ...] [--force]

Writes <out_dir>/<Item Name>.md (callout card + ^card block id) and
<out_dir>/icons/<icon>.jpg. Existing notes are kept unless --force.
"""
import os
import html
import json
import re
import sys
import urllib.request
from pathlib import Path

QUALITY = {0: "poor", 1: "common", 2: "uncommon", 3: "rare", 4: "epic", 5: "legendary"}
TOOLTIP_URL = "https://nether.wowhead.com/forever/tooltip/item/{}"
ICON_URL = "https://wow.zamimg.com/images/wow/icons/large/{}.jpg"


def note_name(name: str) -> str:
    """Obsidian forbids : \\ / * ? " < > | # ^ [ ] in note names."""
    name = name.replace(": ", " - ")
    return re.sub(r'[\\/:*?"<>|#^\[\]]', "", name).strip()


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.load(r)


def tooltip_lines(tt: str) -> list[str]:
    s = re.sub(r"<!--.*?-->", "", tt, flags=re.S)
    s = re.sub(r"\s*\n\s*", " ", s)                                   # source newlines aren't line breaks
    s = re.sub(r"<table[^>]*>", "\n", s)                              # every table starts a new line
    s = re.sub(r"<b class=\"q\d\">.*?</b>", "", s, count=1)           # name → callout title
    s = re.sub(r"<th>\s*(.*?)\s*</th>", r'<span class="r">\1</span>', s, flags=re.S)
    s = re.sub(r"</?a\b[^>]*>", "", s)                                 # keep link text only (links nest)
    s = re.sub(r'<span class="q[^"]*whtt-ilvl">', "<span>", s)          # ilvl wrapper spans a <br>
    s = re.sub(r"<span id=\"[^\"]*\" class=", "<span class=", s)
    s = re.sub(r"<span>(.*?)</span>", r"\1", s, flags=re.S)
    s = re.sub(r"<div class=\"whtt-sellprice\">", '\n<span class="sell">', s)
    s = re.sub(r"(<div[^>]*>)\s*<br\s*/?>", r"\1", s)                  # no break right after a div opens
    s = re.sub(r"<div class=\"[^\"]*whtt-reagents[^\"]*\">", '\n<span class="reagents">', s)
    s = re.sub(r"<div class=\"[^\"]*whtt-extra[^\"]*\">", '\n<span class="extra">', s)
    s = s.replace("</div>", "</span>\n")
    s = re.sub(r"<br\s*/?>|</tr>", "\n", s)
    s = re.sub(r"</?(table|tr|td)[^>]*>", "", s)
    out = []
    seen_sell = 0
    for line in s.split("\n"):
        line = re.sub(r"\s+", " ", line).strip()
        # a span opened before a <br> and closed on another line → balance tags
        extra_close = line.count("</span>") - line.count("<span")
        if extra_close > 0:
            line = line.replace("</span>", "", extra_close)
        elif extra_close < 0:
            line += "</span>" * -extra_close
        # recipes embed the crafted item's tooltip after their own sell price
        m = re.fullmatch(r'<span class="q(\d)">([^<]+)</span>', line)
        if m and seen_sell == 1:
            line = f'<span class="created q{m.group(1)}">{m.group(2)}</span>'
            seen_sell += 1                                              # only the first line after
        if 'class="sell"' in line:
            seen_sell += 1
        if line.startswith("Item Level"):
            line = f'<span class="ilvl">{line}</span>'
        if re.sub(r"<[^>]+>", "", line).strip():
            out.append(line)
    return out


def build(item_id: int, dst: Path, force: bool) -> None:
    d = fetch_json(TOOLTIP_URL.format(item_id))
    name, quality, icon = d["name"], QUALITY.get(d["quality"], "common"), d["icon"]
    note_path = dst / f"{note_name(name)}.md"
    if note_path.exists() and not force:
        print(f"{item_id}\t{name}\tSKIP (exists)")
        return
    img = dst / "icons" / f"{icon}.jpg"
    if not img.exists():
        urllib.request.urlretrieve(ICON_URL.format(icon), img)
    plain = html.unescape(re.sub(r"<[^>]+>", "", d["tooltip"]))
    req = re.search(r"Requires Level (\d+)", plain)
    dps = re.search(r"\(([\d.]+) damage per second\)", plain)
    ilvl = re.search(r"Item Level (\d+)", plain)
    body = "\n".join(f"> {l}" for l in tooltip_lines(d["tooltip"]))
    note_path.write_text(f"""---
id: {item_id}
icon: {icon}.jpg
quality: {quality}
ilvl: {ilvl.group(1) if ilvl else ""}
req: {req.group(1) if req else ""}
dps: {dps.group(1) if dps else ""}
tags: [wow/item]
---
> [!wow|{quality}] {name}
> ![[{icon}.jpg]]
{body}
> [Wowhead](https://www.wowhead.com/forever/item={item_id})

^card
""")
    print(f"{item_id}\t{note_path.stem}\t{icon}.jpg\t{quality}\treq {req.group(1) if req else '-'}")


def main(argv: list[str]) -> None:
    force = "--force" in argv
    args = [a for a in argv if a != "--force"]
    dst = Path(args[0]).expanduser()
    (dst / "icons").mkdir(parents=True, exist_ok=True)
    for item_id in args[1:]:
        try:
            build(int(item_id), dst, force)
        except Exception as e:  # keep going; report which IDs failed
            print(f"{item_id}\tFAILED: {e}")


if __name__ == "__main__":
    main(sys.argv[1:])
