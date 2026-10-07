#!/usr/bin/env bash
# Забрать свежий снапшот каталога + фото из ветки catalog-data в рабочее дерево.
# Запуск:  bash tools/catalog_pull.sh
set -euo pipefail
cd "$(dirname "$0")/.."

BRANCH="${CATALOG_BRANCH:-catalog-data}"
REPO="${CATALOG_REPO:-$(git remote get-url origin | sed -E 's#.*[:/]([^/]+/[^/.]+)(\.git)?$#\1#')}"

echo "Тяну ветку $BRANCH из $REPO …"
# явный refspec: клон может быть одно-бранчевым (тогда без него ref не создаётся)
if git fetch --force --quiet origin "refs/heads/$BRANCH:refs/remotes/origin/$BRANCH" 2>/dev/null; then
  got=0
  for p in catalog/data catalog/photos; do
    if git cat-file -e "origin/$BRANCH:$p" 2>/dev/null; then
      git checkout "origin/$BRANCH" -- "$p"
      got=1
    fi
  done
  git reset -q
  [ "$got" = 1 ] || { echo "!! в ветке $BRANCH нет catalog/data или catalog/photos"; exit 1; }
else
  echo "git fetch не сработал, пробую tarball через codeload…"
  tmp=$(mktemp -d)
  curl -sSL -m 300 "https://codeload.github.com/${REPO}/tar.gz/refs/heads/${BRANCH}" -o "$tmp/data.tgz"
  tar -xzf "$tmp/data.tgz" -C "$tmp"
  rm -rf catalog/data catalog/photos
  cp -r "$tmp"/*/catalog/data catalog/data
  [ -d "$tmp"/*/catalog/photos ] && cp -r "$tmp"/*/catalog/photos catalog/photos || true
  rm -rf "$tmp"
fi

echo
echo "=== Снапшот на месте ==="
cat catalog/data/report.md 2>/dev/null | head -25 || echo "нет report.md"
echo
if [ -f catalog/photos/manifest.json ]; then
  echo "Фото по заявке:"
  python3 - <<'PY'
import json
m = json.load(open("catalog/photos/manifest.json", encoding="utf-8"))
total = 0
for it in m:
    n = len(it.get("files", []))
    total += n
    print(f"  · {it['name'][:60]}: {n} фото" + ("" if n else "  ← НЕТ ФОТО у поставщика"))
print(f"Всего файлов: {total}")
PY
else
  echo "Заявок на фото не было (catalog/requests/photos.json)"
fi

echo
echo "=== Слежение за ценами закупки ==="
if [ -f catalog/price_baseline.json ]; then
  PYTHONPATH="${PYTHONPATH:-$PWD/vendor}" python3 catalog/price_watch.py check || true
else
  echo "Baseline пока не зафиксирован: PYTHONPATH=$PWD/vendor python3 catalog/price_watch.py snapshot"
fi
