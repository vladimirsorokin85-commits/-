#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$script_dir"
expected=6412a49524d0d32ee73e192d6740d609b9f96fcf79d59daa3766ccee98f2c0ea
cat s01e05_full.mp4.part00 s01e05_full.mp4.part01 s01e05_full.mp4.part02 > s01e05_full.mp4

if command -v sha256sum >/dev/null 2>&1; then
  actual=$(sha256sum s01e05_full.mp4 | awk '{print $1}')
elif command -v shasum >/dev/null 2>&1; then
  actual=$(shasum -a 256 s01e05_full.mp4 | awk '{print $1}')
else
  printf 'No SHA-256 utility found (sha256sum or shasum required).\n' >&2
  exit 1
fi

if [ "$actual" != "$expected" ]; then
  printf 'SHA-256 mismatch. Expected %s, got %s.\n' "$expected" "$actual" >&2
  exit 1
fi

printf 'Restored and verified: s01e05_full.mp4\nSHA-256: %s\n' "$actual"
