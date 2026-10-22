#!/bin/sh
set -eu

expected=2ffb8112fe823e2d1a9a4a946a99f39b6d5e4cdb7771fe7c06232a258049156a
cat s01e04_full.mp4.part00 s01e04_full.mp4.part01 s01e04_full.mp4.part02 > s01e04_full.mp4

if command -v sha256sum >/dev/null 2>&1; then
  actual=$(sha256sum s01e04_full.mp4 | awk '{print $1}')
elif command -v shasum >/dev/null 2>&1; then
  actual=$(shasum -a 256 s01e04_full.mp4 | awk '{print $1}')
else
  printf 'No SHA-256 utility found (sha256sum or shasum required).\n' >&2
  exit 1
fi

if [ "$actual" != "$expected" ]; then
  printf 'SHA-256 mismatch. Expected %s, got %s.\n' "$expected" "$actual" >&2
  exit 1
fi

printf 'Restored and verified: s01e04_full.mp4\nSHA-256: %s\n' "$actual"
