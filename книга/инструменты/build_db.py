#!/usr/bin/env python3
"""Собирает SQLite-базу канона вселенной из canon.json.

Использование:
    python3 книга/инструменты/build_db.py            # пересобрать базу
    python3 книга/инструменты/build_db.py --check    # только проверить JSON
    python3 книга/инструменты/build_db.py --schema   # распечатать SQL-схему

JSON (книга/данные/canon.json) — источник правды. База данных
(книга/вселенная.db) — производная и всегда пересобирается целиком.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JSON = ROOT / "данные" / "canon.json"
DEFAULT_DB = ROOT / "вселенная.db"

CANON_STATUSES = {
    "canon": "канон",
    "partly_undefined": "частично не определён",
    "undefined": "не определён",
    "rumor": "неподтверждённый слух",
}

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE meta (
    key         TEXT PRIMARY KEY,
    value       TEXT
);

CREATE TABLE entities (
    id          TEXT PRIMARY KEY,
    type        TEXT NOT NULL,
    name        TEXT NOT NULL,
    aliases     TEXT,
    summary     TEXT,
    canon       TEXT NOT NULL CHECK (canon IN ('canon', 'partly_undefined', 'undefined', 'rumor')),
    section_id  TEXT REFERENCES sections(id) ON DELETE SET NULL
);

CREATE TABLE sections (
    id          TEXT PRIMARY KEY,
    number      TEXT NOT NULL,
    title       TEXT NOT NULL,
    parent_id   TEXT REFERENCES sections(id) ON DELETE SET NULL,
    summary     TEXT,
    sort_order  INTEGER NOT NULL
);

CREATE TABLE facts (
    id          TEXT PRIMARY KEY,
    section_id  TEXT REFERENCES sections(id) ON DELETE SET NULL,
    entity_id   TEXT REFERENCES entities(id) ON DELETE SET NULL,
    kind        TEXT NOT NULL,
    canon       TEXT NOT NULL CHECK (canon IN ('canon', 'partly_undefined', 'undefined', 'rumor')),
    statement   TEXT NOT NULL,
    tags        TEXT NOT NULL DEFAULT '',
    sort_order  INTEGER NOT NULL
);

CREATE TABLE parameters (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    value       TEXT NOT NULL,
    value_num   REAL,
    unit        TEXT,
    comparison  TEXT,
    entity_id   TEXT REFERENCES entities(id) ON DELETE SET NULL,
    section_id  TEXT REFERENCES sections(id) ON DELETE SET NULL,
    note        TEXT
);

CREATE TABLE violation_categories (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    deferred    INTEGER NOT NULL CHECK (deferred IN (0, 1)),
    court       TEXT,
    notes       TEXT,
    section_id  TEXT REFERENCES sections(id) ON DELETE SET NULL,
    sort_order  INTEGER NOT NULL
);

CREATE TABLE sanctions (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    applies_to  TEXT,
    notes       TEXT,
    section_id  TEXT REFERENCES sections(id) ON DELETE SET NULL,
    sort_order  INTEGER NOT NULL
);

CREATE TABLE glossary (
    term        TEXT PRIMARY KEY,
    definition  TEXT NOT NULL,
    section_id  TEXT REFERENCES sections(id) ON DELETE SET NULL,
    entity_id   TEXT REFERENCES entities(id) ON DELETE SET NULL
);

CREATE TABLE open_questions (
    id          TEXT PRIMARY KEY,
    question    TEXT NOT NULL,
    section_id  TEXT REFERENCES sections(id) ON DELETE SET NULL,
    status      TEXT NOT NULL DEFAULT 'open',
    origin      TEXT NOT NULL DEFAULT 'document'
);

CREATE TABLE sources (
    id          TEXT PRIMARY KEY,
    type        TEXT,
    title       TEXT NOT NULL,
    version     TEXT,
    path        TEXT,
    status      TEXT
);

CREATE TABLE versions (
    version     TEXT PRIMARY KEY,
    date        TEXT,
    status      TEXT,
    changes     TEXT,
    document    TEXT
);

CREATE INDEX idx_facts_section ON facts(section_id);
CREATE INDEX idx_facts_entity ON facts(entity_id);
CREATE INDEX idx_facts_canon ON facts(canon);
CREATE INDEX idx_sections_parent ON sections(parent_id);
CREATE INDEX idx_questions_status ON open_questions(status);

CREATE VIEW v_facts_full AS
SELECT f.id,
       f.statement,
       f.kind,
       f.canon,
       s.number AS section_number,
       s.title  AS section_title,
       e.name   AS entity_name,
       e.type   AS entity_type,
       f.tags
FROM facts f
LEFT JOIN sections s ON s.id = f.section_id
LEFT JOIN entities e ON e.id = f.entity_id
ORDER BY f.sort_order;

CREATE VIEW v_entities_full AS
SELECT e.id, e.name, e.type, e.summary, e.canon,
       s.number AS section_number, s.title AS section_title
FROM entities e
LEFT JOIN sections s ON s.id = e.section_id
ORDER BY e.type, e.name;

CREATE VIEW v_parameters_full AS
SELECT p.id, p.name, p.value, p.value_num, p.unit, p.comparison, p.note,
       s.number AS section_number, s.title AS section_title,
       e.name AS entity_name
FROM parameters p
LEFT JOIN sections s ON s.id = p.section_id
LEFT JOIN entities e ON e.id = p.entity_id
ORDER BY p.id;

CREATE VIEW v_open_questions AS
SELECT q.id, q.question, q.status, q.origin,
       s.number AS section_number, s.title AS section_title
FROM open_questions q
LEFT JOIN sections s ON s.id = q.section_id
ORDER BY q.id;
"""


class ValidationError(Exception):
    pass


def load(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def validate(data: dict) -> list[str]:
    """Проверяет ссылочную целостность и формат. Возвращает список предупреждений."""
    errors: list[str] = []
    warnings: list[str] = []
    section_ids = {s["id"] for s in data["sections"]}
    entity_ids = {e["id"] for e in data["entities"]}
    canon_values = set(CANON_STATUSES)

    seen: dict[str, set[str]] = {}

    def check_unique(collection: str, item_id: str) -> None:
        bucket = seen.setdefault(collection, set())
        if item_id in bucket:
            errors.append(f"{collection}: повторяющийся id {item_id!r}")
        bucket.add(item_id)

    for section in data["sections"]:
        check_unique("sections", section["id"])
        parent = section.get("parent")
        if parent is not None and parent not in section_ids:
            errors.append(f"sections/{section['id']}: неизвестный parent {parent!r}")
        if parent == section["id"]:
            errors.append(f"sections/{section['id']}: раздел не может быть родителем сам себе")

    numbers = [s["number"] for s in data["sections"]]
    if len(numbers) != len(set(numbers)):
        errors.append("sections: повторяющиеся номера разделов")

    for entity in data["entities"]:
        check_unique("entities", entity["id"])
        if entity["canon"] not in canon_values:
            errors.append(f"entities/{entity['id']}: недопустимый canon {entity['canon']!r}")
        if entity.get("section") and entity["section"] not in section_ids:
            errors.append(f"entities/{entity['id']}: неизвестный section {entity['section']!r}")

    fact_numbers = []
    for fact in data["facts"]:
        check_unique("facts", fact["id"])
        if fact["canon"] not in canon_values:
            errors.append(f"facts/{fact['id']}: недопустимый canon {fact['canon']!r}")
        if fact["section"] not in section_ids:
            errors.append(f"facts/{fact['id']}: неизвестный section {fact['section']!r}")
        if fact.get("entity") and fact["entity"] not in entity_ids:
            errors.append(f"facts/{fact['id']}: неизвестная сущность {fact['entity']!r}")
        match = re.fullmatch(r"F-(\d+)", fact["id"])
        if not match:
            errors.append(f"facts/{fact['id']}: id должен иметь вид F-000")
        else:
            fact_numbers.append(int(match.group(1)))

    if fact_numbers and fact_numbers != list(range(1, len(fact_numbers) + 1)):
        warnings.append("facts: нумерация F-xxx не непрерывна или идёт не по порядку")

    for param in data["parameters"]:
        check_unique("parameters", param["id"])
        if param.get("section") and param["section"] not in section_ids:
            errors.append(f"parameters/{param['id']}: неизвестный section {param['section']!r}")
        if param.get("entity") and param["entity"] not in entity_ids:
            errors.append(f"parameters/{param['id']}: неизвестная сущность {param['entity']!r}")
        if param.get("value_num") is not None and not isinstance(param["value_num"], (int, float)):
            errors.append(f"parameters/{param['id']}: value_num должен быть числом")

    for collection in ("violation_categories", "sanctions"):
        for item in data[collection]:
            check_unique(collection, item["id"])
            if item.get("section") and item["section"] not in section_ids:
                errors.append(f"{collection}/{item['id']}: неизвестный section {item['section']!r}")

    for item in data["glossary"]:
        if item.get("section") and item["section"] not in section_ids:
            errors.append(f"glossary/{item['term']}: неизвестный section {item['section']!r}")
        if item.get("entity") and item["entity"] not in entity_ids:
            errors.append(f"glossary/{item['term']}: неизвестная сущность {item['entity']!r}")

    for item in data["open_questions"]:
        check_unique("open_questions", item["id"])
        if item.get("section") and item["section"] not in section_ids:
            errors.append(f"open_questions/{item['id']}: неизвестный section {item['section']!r}")
        if item["status"] not in {"open", "resolved", "wontfix", "deferred"}:
            errors.append(f"open_questions/{item['id']}: недопустимый status {item['status']!r}")

    used_sections = {f["section"] for f in data["facts"]}
    used_sections |= {q["section"] for q in data["open_questions"] if q.get("section")}
    for section in data["sections"]:
        if section["id"] not in used_sections:
            warnings.append(f"раздел {section['number']} не имеет утверждений в facts")

    if errors:
        raise ValidationError("\n".join(errors))
    return warnings


def _join(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value)
    return str(value)


def build(data: dict, db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    meta = data["meta"]
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.execute("PRAGMA user_version = 1")

        conn.executemany(
            "INSERT INTO meta(key, value) VALUES (?, ?)",
            [
                ("schema_version", meta["schema_version"]),
                ("title", meta["title"]),
                ("volume", meta["volume"]),
                ("version", meta["version"]),
                ("status", meta["status"]),
                ("author", meta["author"] or ""),
                ("genres", _join(meta["genres"])),
                ("language", meta["language"]),
                ("created", meta["created"]),
                ("updated", meta["updated"]),
                ("source_document", meta["source_document"]),
                ("description", meta["description"]),
                ("built_at", dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()),
            ],
        )

        conn.executemany(
            "INSERT INTO sections(id, number, title, parent_id, summary, sort_order) VALUES (?, ?, ?, ?, ?, ?)",
            [
                (s["id"], s["number"], s["title"], s.get("parent"), s.get("summary"), i + 1)
                for i, s in enumerate(data["sections"])
            ],
        )

        conn.executemany(
            "INSERT INTO entities(id, type, name, aliases, summary, canon, section_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (e["id"], e["type"], e["name"], _join(e.get("aliases")), e.get("summary"), e["canon"], e.get("section"))
                for e in data["entities"]
            ],
        )

        conn.executemany(
            "INSERT INTO facts(id, section_id, entity_id, kind, canon, statement, tags, sort_order) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (f["id"], f["section"], f.get("entity"), f["kind"], f["canon"], f["statement"], _join(f.get("tags")), i + 1)
                for i, f in enumerate(data["facts"])
            ],
        )

        conn.executemany(
            "INSERT INTO parameters(id, name, value, value_num, unit, comparison, entity_id, section_id, note) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (p["id"], p["name"], p["value"], p.get("value_num"), p.get("unit"),
                 p.get("comparison"), p.get("entity"), p.get("section"), p.get("note"))
                for p in data["parameters"]
            ],
        )

        conn.executemany(
            "INSERT INTO violation_categories(id, name, deferred, court, notes, section_id, sort_order) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (v["id"], v["name"], 1 if v["deferred"] else 0, v.get("court"), v.get("notes"), v.get("section"), i + 1)
                for i, v in enumerate(data["violation_categories"])
            ],
        )

        conn.executemany(
            "INSERT INTO sanctions(id, name, applies_to, notes, section_id, sort_order) VALUES (?, ?, ?, ?, ?, ?)",
            [
                (s["id"], s["name"], s.get("applies_to"), s.get("notes"), s.get("section"), i + 1)
                for i, s in enumerate(data["sanctions"])
            ],
        )

        conn.executemany(
            "INSERT INTO glossary(term, definition, section_id, entity_id) VALUES (?, ?, ?, ?)",
            [
                (g["term"], g["definition"], g.get("section"), g.get("entity"))
                for g in data["glossary"]
            ],
        )

        conn.executemany(
            "INSERT INTO open_questions(id, question, section_id, status, origin) VALUES (?, ?, ?, ?, ?)",
            [
                (q["id"], q["question"], q.get("section"), q["status"], q.get("origin", "document"))
                for q in data["open_questions"]
            ],
        )

        conn.executemany(
            "INSERT INTO sources(id, type, title, version, path, status) VALUES (?, ?, ?, ?, ?, ?)",
            [
                (s["id"], s.get("type"), s["title"], s.get("version"), s.get("path"), s.get("status"))
                for s in data["sources"]
            ],
        )

        conn.executemany(
            "INSERT INTO versions(version, date, status, changes, document) VALUES (?, ?, ?, ?, ?)",
            [
                (v["version"], v.get("date"), v.get("status"), v.get("changes"), v.get("document"))
                for v in data["versions"]
            ],
        )

        conn.commit()
    finally:
        conn.close()


def summarize(data: dict) -> str:
    meta = data["meta"]
    by_canon: dict[str, int] = {}
    for fact in data["facts"]:
        by_canon[fact["canon"]] = by_canon.get(fact["canon"], 0) + 1
    lines = [
        f"«{meta['title']}», {meta['volume']} — версия {meta['version']} ({meta['status']})",
        f"  сущностей:   {len(data['entities'])}",
        f"  разделов:    {len(data['sections'])}",
        f"  утверждений: {len(data['facts'])}",
        "    " + ", ".join(f"{CANON_STATUSES.get(k, k)}: {v}" for k, v in sorted(by_canon.items())),
        f"  параметров:  {len(data['parameters'])}",
        f"  категорий правонарушений: {len(data['violation_categories'])}",
        f"  наказаний:   {len(data['sanctions'])}",
        f"  терминов:    {len(data['glossary'])}",
        f"  открытых вопросов: {sum(1 for q in data['open_questions'] if q['status'] == 'open')}",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Сборка базы канона вселенной")
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON, help="путь к canon.json")
    parser.add_argument("--out", type=Path, default=DEFAULT_DB, help="путь к SQLite-базе")
    parser.add_argument("--check", action="store_true", help="только проверить JSON, не собирать базу")
    parser.add_argument("--schema", action="store_true", help="распечатать SQL-схему и выйти")
    parser.add_argument("--quiet", action="store_true", help="не печатать сводку")
    args = parser.parse_args(argv)

    if args.schema:
        print(SCHEMA)
        return 0

    try:
        data = load(args.json)
        warnings = validate(data)
    except FileNotFoundError:
        print(f"Не найден файл: {args.json}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"Ошибка разбора JSON: {exc}", file=sys.stderr)
        return 2
    except ValidationError as exc:
        print("Проверка не пройдена:\n" + str(exc), file=sys.stderr)
        return 1

    for warning in warnings:
        print(f"предупреждение: {warning}", file=sys.stderr)

    if args.check:
        print("Проверка пройдена.")
        if not args.quiet:
            print(summarize(data))
        return 0

    build(data, args.out)
    if not args.quiet:
        print(summarize(data))
        print(f"\nБаза собрана: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
