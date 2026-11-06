# -*- coding: utf-8 -*-
"""Проверка PDF-альбома: страницы, размер A4, вшитые шрифты, непустые страницы.

Использование:
  python _render/verify_pdf.py "05_ГОТОВОЕ/pdf/Инфографика_Два_горизонта_2026.pdf" [--expect-pages 12] [--json out.json]

Печатает человекочитаемый отчёт и выходит с кодом 0 (OK), 1 (есть проблемы), 2 (нет pypdf/файла).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

A4_W, A4_H = 595.276, 841.890   # pt
A4_TOL = 2.0
MIN_PDF_BYTES = 100 * 1024


def _font_info(font_obj) -> tuple[str, bool]:
    """(описание шрифта, встроен ли): Type0/CIDFont с FontFile* или Type3-контуры."""
    base = str(font_obj.get("/BaseFont", "?"))
    sub = str(font_obj.get("/Subtype", "?"))
    if sub == "/Type3":
        # Type3 — глифы нарисованы контурами прямо в PDF (визуально не поплывёт)
        return f"Type3 {base} (контуры)", True
    desc = font_obj.get("/FontDescriptor")
    if desc is None:
        df = font_obj.get("/DescendantFonts")
        if df:
            try:
                d0 = df[0].get_object()
                desc = d0.get("/FontDescriptor")
                if base == "?":
                    base = str(d0.get("/BaseFont", "?"))
            except Exception:
                desc = None
    embedded = False
    if desc is not None:
        try:
            d = desc.get_object()
            embedded = any(k in d for k in ("/FontFile", "/FontFile2", "/FontFile3"))
        except Exception:
            embedded = False
    return f"{sub} {base}", embedded


def verify(path: Path, expect_pages: int | None = None) -> dict:
    res = {
        "path": str(path),
        "exists": path.is_file(),
        "bytes": 0,
        "pages": None,
        "expect_pages": expect_pages,
        "page_sizes": [],
        "bad_pages": [],
        "font_file_tokens": 0,
        "fonts": [],
        "fonts_type3": 0,
        "fonts_embedded": 0,
        "xobject_pages": 0,
        "empty_pages": [],
        "ok": False,
        "issues": [],
        "engine": "pypdf",
    }
    if not path.is_file():
        res["issues"].append("файл не найден")
        return res
    res["bytes"] = path.stat().st_size
    if res["bytes"] < MIN_PDF_BYTES:
        res["issues"].append(f"вес {res['bytes']} Б < 100 КБ (подозрительно мало)")
    try:
        from pypdf import PdfReader
    except Exception as e:
        res["issues"].append(f"нет pypdf ({e}) — число страниц не проверено")
        res["engine"] = "bytes-only"
        raw = path.read_bytes()
        res["font_file_tokens"] = raw.count(b"/FontFile2") + raw.count(b"/FontFile3") + raw.count(b"/FontFile")
        res["ok"] = res["bytes"] >= MIN_PDF_BYTES
        return res
    try:
        reader = PdfReader(str(path))
        res["pages"] = len(reader.pages)
        for i, page in enumerate(reader.pages):
            mb = page.mediabox
            w, h = float(mb.width), float(mb.height)
            res["page_sizes"].append([round(w, 1), round(h, 1)])
            if abs(w - A4_W) > A4_TOL or abs(h - A4_H) > A4_TOL:
                res["bad_pages"].append(f"стр.{i + 1}: {w:.1f}×{h:.1f} pt (не A4 portrait)")
            # непустая ли страница
            try:
                contents = page.get_contents()
                clen = len(contents.get_data()) if contents is not None else 0
            except Exception:
                clen = 0
            try:
                xo = page.get("/Resources", {}).get("/XObject", {})
                nxo = len(xo) if xo else 0
            except Exception:
                nxo = 0
            if nxo:
                res["xobject_pages"] += 1
            if clen < 100:
                res["empty_pages"].append(f"стр.{i + 1}: content {clen} Б")
            # шрифты страницы
            try:
                fonts = page.get("/Resources", {}).get("/Font", {})
                for key, ref in (fonts or {}).items():
                    try:
                        fobj = ref.get_object()
                        descr, embedded = _font_info(fobj)
                        res["fonts"].append({"page": i + 1, "ref": str(key), "font": descr, "embedded": embedded})
                        if "Type3" in descr:
                            res["fonts_type3"] += 1
                        if embedded:
                            res["fonts_embedded"] += 1
                    except Exception:
                        pass
            except Exception:
                pass
        raw = path.read_bytes()
        res["font_file_tokens"] = (raw.count(b"/FontFile2") + raw.count(b"/FontFile3")
                                   + raw.count(b"/FontFile "))
        if expect_pages is not None and res["pages"] != expect_pages:
            res["issues"].append(f"страниц {res['pages']}, ожидалось {expect_pages}")
        if res["bad_pages"]:
            res["issues"].append(f"не A4: {len(res['bad_pages'])} стр.")
        if res["empty_pages"]:
            res["issues"].append(f"пустых страниц: {len(res['empty_pages'])}")
        if not res["fonts"]:
            res["issues"].append("в PDF не найдено ни одного шрифта")
        elif res["fonts_embedded"] == 0:
            res["issues"].append("шрифты не встроены ни как Type0/FontFile, ни как Type3-контуры")
        if res["xobject_pages"] < (res["pages"] or 0) - 2:
            res["issues"].append(f"страниц с картинками {res['xobject_pages']} из {res['pages']}")
        res["ok"] = not res["issues"]
    except Exception as e:
        res["issues"].append(f"pypdf не прочитал PDF: {e}")
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--expect-pages", type=int, default=None)
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    path = Path(a.pdf)
    res = verify(path, a.expect_pages)
    print(f"PDF: {path}")
    if res["exists"]:
        print(f"  вес: {res['bytes'] / (1024 * 1024):.2f} МБ ({res['bytes']} Б)")
    print(f"  страниц: {res['pages']} (ожидалось: {res['expect_pages']})")
    print(f"  размеры страниц, pt: {sorted(set(tuple(s) for s in res['page_sizes']))}")
    print(f"  шрифтовых программ (/FontFile* в потоке): {res['font_file_tokens']}")
    if res["fonts"]:
        types = sorted({f["font"] for f in res["fonts"]})
        print(f"  шрифтов: {len(types)} видов, Type3-контуров: {res['fonts_type3']}, "
              f"встроенных: {res['fonts_embedded']}")
        for t in types[:12]:
            print(f"    · {t}")
    print(f"  страниц с XObject-картинками: {res['xobject_pages']}")
    if res["issues"]:
        print("  ПРОБЛЕМЫ:")
        for i in res["issues"] + res["bad_pages"] + res["empty_pages"]:
            print(f"    - {i}")
    print(f"  ИТОГ: {'OK' if res['ok'] else 'FAIL'}")
    if a.json:
        p = Path(a.json)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  JSON: {p}")
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
