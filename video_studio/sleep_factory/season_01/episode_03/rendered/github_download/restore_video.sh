#!/bin/sh
set -eu
cat s01e03_full.mp4.part00 s01e03_full.mp4.part01 > s01e03_full.mp4
printf 'Готово: s01e03_full.mp4\n'
if command -v sha256sum >/dev/null 2>&1; then
  sha256sum -c s01e03_full.mp4.sha256
elif command -v shasum >/dev/null 2>&1; then
  shasum -a 256 -c s01e03_full.mp4.sha256
fi
