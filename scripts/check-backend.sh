#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export LLM_PROVIDER=mock
export AUDIO_RENDERER=fallback
export PYTHONPATH="$(pwd)"

echo "[check-backend] Running pytest ..."
if [[ "${1:-}" == "--full" ]]; then
  echo "[check-backend] Running full pytest ..."
  python -m pytest -q
else
  echo "[check-backend] Running fast pytest (skip slow integration tests) ..."
  python -m pytest -q -m "not slow"
fi
echo "[check-backend] OK"
