#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$script_dir"
expected=db2e1639550ede5576b2305ef9dce10b5bf397be3db8a1e061950c5c6b22a406
cat s02e02_full.mp4.part00 > s02e02_full.mp4

if command -v sha256sum >/dev/null 2>&1; then
  actual=$(sha256sum s02e02_full.mp4 | awk '{print $1}')
elif command -v shasum >/dev/null 2>&1; then
  actual=$(shasum -a 256 s02e02_full.mp4 | awk '{print $1}')
else
  printf 'No SHA-256 utility found (sha256sum or shasum required).\n' >&2
  exit 1
fi

if [ "$actual" != "$expected" ]; then
  printf 'SHA-256 mismatch. Expected %s, got %s.\n' "$expected" "$actual" >&2
  exit 1
fi

printf 'Restored and verified: s02e02_full.mp4\nSHA-256: %s\n' "$actual"
