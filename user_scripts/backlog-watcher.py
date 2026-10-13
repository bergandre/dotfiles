#!/usr/bin/env python3
"""Следит за Backlog/Games/*.md и дописывает строку в ## Лог при смене status.

В строку попадают дата со временем, событие, текущий percent (как pct) и
содержимое поля note (как why). Имена в логе намеренно другие: датавью собирает
инлайн-поля со всей страницы, и одинаковые имена превратили бы поле файла в массив. После записи note очищается — это разовый комментарий к переходу, иначе он
прилипнет к каждому следующему событию.

Состояние (последний известный статус каждой игры) хранится отдельно от вольта,
поэтому первый запуск ничего не пишет — он только запоминает текущее положение.

Переменные окружения для тестов:
  BACKLOG_GAMES  — папка с заметками игр
  BACKLOG_STATE  — файл состояния
"""

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

GAMES = Path(os.environ.get(
    "BACKLOG_GAMES",
    "/home/supernova/Documents/obsidian/gaming/Backlog/Games",
))
STATE = Path(os.environ.get(
    "BACKLOG_STATE",
    Path.home() / ".local/state/backlog-watcher/state.json",
))
INTERVAL = 2.0

EVENTS = {
    "active": "старт",
    "pause": "пауза",
    "on-hold": "пауза",
    "dropped": "дроп",
    "done": "пройдено",
    "queue": "очередь",
}

FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
STATUS = re.compile(r"^status:\s*(.*?)\s*$", re.M)
PERCENT = re.compile(r"^percent:\s*(.*?)\s*$", re.M)
NOTE = re.compile(r"^note:\s*(.*?)\s*$", re.M)
HAS_EVENT = re.compile(r"\[event::\s*\S")


def read_field(text, pattern):
    fm = FRONTMATTER.match(text)
    if not fm:
        return None
    found = pattern.search(fm.group(1))
    if not found:
        return None
    return found.group(1).strip().strip("\"'") or None


def clean(value):
    """Инлайн-поле датавью обрывается на ']', так что скобки надо обезвредить."""
    if not value:
        return ""
    return value.replace("]", ")").replace("[", "(").replace("\n", " ").strip()


def clear_note(text):
    fm = FRONTMATTER.match(text)
    if not fm:
        return text
    block = fm.group(1)
    emptied = NOTE.sub("note:", block, count=1)
    if emptied == block:
        return text
    return text[:fm.start(1)] + emptied + text[fm.end(1):]


def append_log(path, text, event, percent, note):
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = (f"- [date:: {stamp}] [event:: {event}] "
             f"[pct:: {clean(percent)}] [why:: {clean(note)}]")
    lines = text.splitlines()

    heading = next(
        (i for i, line in enumerate(lines) if line.strip().lower() == "## лог"),
        None,
    )
    if heading is None:
        while lines and not lines[-1].strip():
            lines.pop()
        lines += ["", "## Лог", "", entry]
    else:
        # секция лога тянется до следующего заголовка того же уровня
        end = len(lines)
        for i in range(heading + 1, len(lines)):
            if lines[i].startswith("## "):
                end = i
                break
        block = lines[heading + 1:end]
        while block and not block[-1].strip():
            block.pop()
        if not block:
            block = [""]
        block.append(entry)
        lines[heading + 1:end] = block + [""]

    path.write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")


def scan(state, seed=False):
    dirty = False
    for path in sorted(GAMES.glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue

        status = read_field(text, STATUS)
        if status is None:
            continue

        previous = state.get(path.name)
        if previous == status:
            continue

        if not seed and previous is not None:
            event = EVENTS.get(status)
            if event is None:
                # неизвестный статус лучше заметить, чем молча проглотить
                print(f"{path.name}: неизвестный статус «{status}», "
                      f"в лог ничего не записано", flush=True)
            else:
                # вернулся к игре, по которой уже что-то записано
                if status == "active" and HAS_EVENT.search(text):
                    event = "возврат"
                percent = read_field(text, PERCENT)
                note = read_field(text, NOTE)
                append_log(path, clear_note(text), event, percent, note)
                print(f"{path.name}: {previous} → {status}, записано «{event}»"
                      + (f" с заметкой «{note}»" if note else ""), flush=True)

        state[path.name] = status
        dirty = True

    return dirty


def save(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2),
                     encoding="utf-8")


def main():
    first_run = not STATE.exists()
    state = {} if first_run else json.loads(STATE.read_text(encoding="utf-8"))

    scan(state, seed=first_run)
    save(state)

    if "--once" in sys.argv:
        return

    while True:
        time.sleep(INTERVAL)
        if scan(state):
            save(state)


if __name__ == "__main__":
    main()
