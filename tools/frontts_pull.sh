#!/usr/bin/env bash
# Забрать данные по поставщику front-ts.ru из ветки frontts-data.
# Запуск:  bash tools/frontts_pull.sh
set -euo pipefail
cd "$(dirname "$0")/.."

BRANCH="${FRONTTS_BRANCH:-frontts-data}"
REPO="${CATALOG_REPO:-$(git remote get-url origin | sed -E 's#.*[:/]([^/]+/[^/.]+)(\.git)?$#\1#')}"

echo "Тяну ветку $BRANCH из $REPO …"
if git fetch --force --quiet origin "refs/heads/$BRANCH:refs/remotes/origin/$BRANCH" 2>/dev/null; then
  for p in suppliers/frontts/data suppliers/frontts/photos; do
    git cat-file -e "origin/$BRANCH:$p" 2>/dev/null && git checkout "origin/$BRANCH" -- "$p"
  done
  git reset -q
else
  echo "git fetch не сработал, пробую tarball через codeload…"
  tmp=$(mktemp -d)
  curl -sSL -m 600 "https://codeload.github.com/${REPO}/tar.gz/refs/heads/${BRANCH}" -o "$tmp/d.tgz"
  tar -xzf "$tmp/d.tgz" -C "$tmp"
  rm -rf suppliers/frontts/data suppliers/frontts/photos
  cp -r "$tmp"/*/suppliers/frontts/data suppliers/frontts/data 2>/dev/null || true
  [ -d "$tmp"/*/suppliers/frontts/photos ] && cp -r "$tmp"/*/suppliers/frontts/photos suppliers/frontts/photos || true
  rm -rf "$tmp"
fi

echo
echo "=== Что пришло ==="
if [ -f suppliers/frontts/data/discovery.json ]; then
  python3 - <<'PY'
import json, os
d = json.load(open("suppliers/frontts/data/discovery.json", encoding="utf-8"))
print("хост:", d.get("host"), "| товароподобных URL:", d.get("found", {}).get("product_like"))
print("прочих страниц:", d.get("found", {}).get("other_pages"),
      "| скачано:", d.get("stats", {}).get("ok"), "сбоев:", d.get("stats", {}).get("fail"))
print("\nшаблоны URL (топ-15):")
for k, v in sorted(d.get("patterns", {}).items(), key=lambda kv: -kv[1])[:15]:
    print(f"  {v:>5}  {k}")
print("\nпримеры товарных URL:")
for u in (d.get("product_urls_sample") or [])[:10]:
    print("  ", u)
PY
fi
[ -f suppliers/frontts/data/summary.txt ] && cat suppliers/frontts/data/summary.txt
echo
echo "фото:"; ls suppliers/frontts/photos 2>/dev/null | head -8; du -sh suppliers/frontts/photos 2>/dev/null || true
