#!/usr/bin/env bash
# Ставим локальные зависимости «В ОКОПЕ» в vendor/ (в git не попадает).
# Запускать один раз за сессию: bash tools/bootstrap.sh
set -euo pipefail
cd "$(dirname "$0")/.."

if python3 -c "import sys; sys.path.insert(0,'vendor'); import PIL" 2>/dev/null; then
  echo "Pillow уже в vendor/ — всё готово"
  exit 0
fi

echo "Ставлю Pillow в vendor/ ..."
python3 -m pip install --quiet --target=vendor --upgrade pillow
python3 - <<'PY'
import sys; sys.path.insert(0, "vendor")
import PIL
print("Pillow", PIL.__version__, "→ vendor/ готов")
PY
