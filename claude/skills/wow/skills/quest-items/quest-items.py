#!/usr/bin/env python3
"""Leftover quest items in a character's bags: which quests they belong to and whether those are done.

Needs the QuestLedger addon (<repo>/Interface/AddOns/QuestLedger): it saves completed quest IDs,
the quest log and the bag quest items to SavedVariables on logout / /reload.

Item -> quest mapping, local sources:
  - QuestLedger itself: items that start a quest (GetContainerItemQuestInfo)
  - Zygor Forever guides: "collect|use ... Name##item ... |q quest/obj", and "use X##item" followed
    by "accept Quest##id" (item starts that quest)
  - RXP guides: ".collect item,count,quest"; RXP Forever DB quest -> item maps
  - ForeverDungeonJournal: quest rewards (the item is a reward, not an objective)

Usage:
  quest-items.py [--char Karums-Priest ...]        report (default: Karums-Warrior, Karums-Priest)
  quest-items.py --char X --quests 1234,5678       done / log / - for quest IDs found on the web
"""
import argparse, os, re, subprocess
from collections import defaultdict
from pathlib import Path

REPO = Path(os.environ.get("WOW_REPO", Path.home() / "repositories/wow-forever-addon-settings"))
ADDONS = REPO / "Interface/AddOns"
DEFAULT_CHARS = ["Karums-Warrior", "Karums-Priest"]

LUA_DUMP = r'''
local env = {}; assert(load(io.open(arg[1]):read("a"):gsub("\r", ""), "sv", "t", env))()
local db = env.QuestLedgerDB or {}
print("time", db.time or 0, db.level or 0)
for _, q in ipairs(db.completed or {}) do print("done", q) end
for q, title in pairs(db.log or {}) do print("log", q, tostring(title)) end
for id, e in pairs(db.bagQuestItems or {}) do
  print("item", id, e.count or 0, e.startsQuest or 0, e.questActive and 1 or 0, e.name or "")
end
'''


def load_ledger(char):
    paths = list(REPO.glob(f"WTF/Account/*/*/{char}/SavedVariables/QuestLedger.lua"))
    if not paths:
        raise SystemExit(f"{char}: no QuestLedger.lua yet - log that character in and out (or /reload) once")
    out = subprocess.run(["lua", "-", str(paths[0])], input=LUA_DUMP, capture_output=True, text=True, check=True).stdout
    led = {"done": set(), "log": {}, "items": {}, "time": 0, "level": 0}
    for line in out.splitlines():
        f = line.split("\t")
        if f[0] == "time":
            led["time"], led["level"] = int(f[1]), int(f[2])
        elif f[0] == "done":
            led["done"].add(int(f[1]))
        elif f[0] == "log":
            led["log"][int(f[1])] = f[2]
        elif f[0] == "item":
            led["items"][int(f[1])] = {"count": int(f[2]), "starts": int(f[3]) or None,
                                       "active": f[4] == "1", "name": f[5]}
    return led


def build_map():
    """item id -> {quest id: how} from local guide data."""
    m = defaultdict(dict)
    zyg_item = re.compile(r"^\s*(collect|use)\b[^\n#]*##(\d+)([^\n]*)", re.M)
    zyg_accept = re.compile(r"^\s*accept\b[^\n#]*##(\d+)", re.M)
    for p in (ADDONS / "ZygorGuidesViewerForever/Guides-Forever").rglob("*.lua"):
        text = p.read_text(encoding="utf-8", errors="ignore")
        for mt in zyg_item.finditer(text):
            verb, item, rest = mt.group(1), int(mt.group(2)), mt.group(3)
            q = re.search(r"\|q (\d+)", rest)
            if q:
                m[item].setdefault(int(q.group(1)), f"Zygor {verb}")
            elif verb == "use":  # "use X##item" then "accept Quest##id" right after: the item starts it
                nxt = zyg_accept.search(text, mt.end(), mt.end() + 200)
                if nxt:
                    m[item].setdefault(int(nxt.group(1)), "Zygor: starts quest")
    for p in (ADDONS / "RXPGuides/Guides").rglob("*.lua"):
        for item, q in re.findall(r"\.collect\s+(\d+)\s*,\s*\d+\s*,\s*(\d+)", p.read_text(encoding="utf-8", errors="ignore")):
            m[int(item)].setdefault(int(q), "RXP collect")
    rxp_db = ADDONS / "RXPGuides/DB/forever/quest.lua"
    if rxp_db.exists():
        for q, item in re.findall(r"\[(\d+)\]\s*=\s*(\d+),\s*--", rxp_db.read_text(encoding="utf-8")):
            m[int(item)].setdefault(int(q), "RXP quest item")
    fdj = ADDONS / "ForeverDungeonJournal/Data/Dungeons.lua"
    if fdj.exists():
        text = fdj.read_text(encoding="utf-8")
        for block in re.split(r"(?=\bid\s*=\s*\d+)", text):
            qid = re.match(r"id\s*=\s*(\d+)", block)
            if qid:
                for item in re.findall(r"\{(\d+),\s*\"[^\"]*\",\s*\d+\}", block):
                    m[int(item)].setdefault(int(qid.group(1)), "FDJ reward")
    return m


def status(led, q):
    return "log" if q in led["log"] else "done" if q in led["done"] else "-"


def verdict(item, quests, led):
    if item["starts"]:
        quests = {**quests, item["starts"]: "starts quest (in game)"}
    if not quests:
        return "WEB", "no local mapping - look it up"
    st = {q: status(led, q) for q in quests}
    if any(s == "log" for s in st.values()):
        return "KEEP", "quest in log"
    objective = {q for q, how in quests.items() if "reward" not in how}
    if objective and all(st[q] == "done" for q in objective):
        return "SAFE?", "every quest it is for is done - confirm no other quest uses it"
    if not objective:
        return "REWARD", "quest reward, not a quest objective - judge as a normal item"
    return "KEEP", "quest not done yet: " + ", ".join(str(q) for q in objective if st[q] != "done")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--char", action="append", help="character folder name, e.g. Karums-Priest")
    ap.add_argument("--quests", help="comma-separated quest IDs to check (done / log / -)")
    args = ap.parse_args()
    chars = args.char or DEFAULT_CHARS
    if args.quests:
        ids = [int(x) for x in args.quests.split(",") if x.strip()]
        for c in chars:
            led = load_ledger(c)
            print(c + ": " + ", ".join(f"{q} {status(led, q)}" for q in ids))
        return
    qmap = build_map()
    for c in chars:
        led = load_ledger(c)
        print(f"\n== {c} (level {led['level']}, {len(led['done'])} quests done, {len(led['log'])} in log)")
        print("| Verdict | Item | ID | Count | Quests (status, source) | Why |")
        print("|---|---|---|---|---|---|")
        rows = []
        for iid, it in led["items"].items():
            quests = dict(qmap.get(iid, {}))
            v, why = verdict(it, quests, led)
            if it["starts"]:
                quests.setdefault(it["starts"], "starts quest (in game)")
            qs = "; ".join(f"{q} {status(led, q)} ({how})" for q, how in sorted(quests.items())) or "-"
            rows.append((v, it["name"], iid, it["count"], qs, why))
        for r in sorted(rows):
            print("| " + " | ".join(str(x) for x in r) + " |")


if __name__ == "__main__":
    main()
