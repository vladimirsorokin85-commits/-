#!/usr/bin/env bash
# Забрать внешние файлы из ветки assets-inbox в рабочее дерево (assets/inbox/).
# Запуск: bash tools/fetch_asset.sh
set -euo pipefail
cd "$(dirname "$0")/.."

BRANCH="${ASSET_BRANCH:-assets-inbox}"
REPO="${CATALOG_REPO:-$(git remote get-url origin | sed -E 's#.*[:/]([^/]+/[^/.]+)(\.git)?$#\1#')}"

echo "Тяну ветку $BRANCH из $REPO …"
if git fetch --force --quiet origin "refs/heads/$BRANCH:refs/remotes/origin/$BRANCH" 2>/dev/null \
   && git cat-file -e "origin/$BRANCH:assets/inbox" 2>/dev/null; then
  rm -rf assets/inbox
  git checkout "origin/$BRANCH" -- assets/inbox
  git reset -q
else
  echo "git fetch не сработал, тяну tarball через codeload…"
  tmp=$(mktemp -d)
  curl -sSL -m 300 "https://codeload.github.com/${REPO}/tar.gz/refs/heads/${BRANCH}" -o "$tmp/a.tgz"
  tar -xzf "$tmp/a.tgz" -C "$tmp"
  rm -rf assets/inbox
  cp -r "$tmp"/*/assets/inbox assets/inbox
  rm -rf "$tmp"
fi

echo
echo "=== Файлы на месте ==="
ls -la assets/inbox/ 2>/dev/null || { echo "!! пусто"; exit 1; }
