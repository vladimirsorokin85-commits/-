#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Доступ к снапшоту каталога Димы: индекс, полные карточки, фото, свежесть.

Снапшот приходит артефактом из GitHub Actions (см. docs/WORKFLOW.md) либо
создаётся локально: python3 catalog/remote_fetch.py
"""
import datetime as dt
import json
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(HERE, "data")
INDEX = os.path.join(DATA, "catalog_index.json")
FULL = os.path.join(DATA, "catalog_full.json")
META = os.path.join(DATA, "catalog_meta.json")
PHOTOS = os.path.join(HERE, "photos")
MANIFEST = os.path.join(PHOTOS, "manifest.json")
BASE = os.environ.get("MOYSKLAD_BASE") or "https://b2b.moysklad.ru/desktop-api/public/WDuXQTYGsuNZ"

NO_SNAPSHOT = (
    "Нет снапшота каталога (catalog/data/catalog_index.json).\n"
    "Как получить:\n"
    "  • через GitHub Actions: Actions → «Catalog fetch» → Run workflow, затем\n"
    "    gh run download -R <owner>/<repo> -n catalog-snapshot -D /tmp/cat && cp -r /tmp/cat/catalog/* catalog/\n"
    "  • или напрямую, если сеть пускает: python3 catalog/remote_fetch.py"
)


def snapshot_exists() -> bool:
    return os.path.exists(INDEX)


def load_index():
    """Компактный индекс: [{id,name,code,article,price,stock,category,...}] + meta."""
    if not snapshot_exists():
        raise SystemExit(NO_SNAPSHOT)
    rows = json.load(open(INDEX, encoding="utf-8"))
    meta = {}
    if os.path.exists(META):
        try:
            meta = json.load(open(META, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            meta = {}
    return rows, meta


def load_full():
    """Полные карточки (с описаниями). Может отсутствовать — тогда []."""
    if not os.path.exists(FULL):
        return []
    return json.load(open(FULL, encoding="utf-8"))


def full_by_id():
    return {p.get("id"): p for p in load_full()}


def photos_manifest():
    """[{id,code,name,files[]}] из catalog/photos/manifest.json (может не быть)."""
    if not os.path.exists(MANIFEST):
        return []
    try:
        return json.load(open(MANIFEST, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []


def photos_by_id():
    return {m["id"]: m for m in photos_manifest()}


def snapshot_age_hours(meta) -> float | None:
    ts = (meta or {}).get("fetched_at")
    if not ts:
        return None
    try:
        when = dt.datetime.fromisoformat(ts)
        if when.tzinfo is None:
            when = when.replace(tzinfo=dt.timezone.utc)
        return (dt.datetime.now(dt.timezone.utc) - when).total_seconds() / 3600
    except Exception:  # noqa: BLE001
        return None


def source_line(meta, live: bool = False) -> str:
    """Человеческая строка о свежести данных."""
    if live:
        return f"live API МойСклад ({dt.datetime.now():%d.%m.%Y %H:%M})"
    ts = (meta or {}).get("fetched_at")
    age = snapshot_age_hours(meta)
    if not ts:
        return "локальный снапшот (время снятия неизвестно)"
    when = dt.datetime.fromisoformat(ts).astimezone()
    hours = f", {age:.1f} ч назад" if age is not None else ""
    warn = ""
    if age is not None and age > 24:
        warn = "  ⚠ снапшот старше суток — перед ответом клиенту обнови (Actions → Catalog fetch)"
    return f"снапшот МойСклад, снят {when:%d.%m.%Y %H:%M}{hours}{warn}"


def can_reach_live(timeout: float = 8) -> bool:
    """Быстрая проверка: доступен ли API МойСклад напрямую из этого окружения."""
    url = f"{BASE}/products.json?limit=1&offset=0"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


def refresh_live():
    """Прямое обновление снапшота (если сеть пускает) — использует remote_fetch."""
    import importlib
    rf = importlib.import_module("catalog.remote_fetch")
    rf.main()


def price_label() -> str:
    """Как называть поле price в выводе: это закуп поставщика, не розница клиента."""
    return "закуп Димы"
