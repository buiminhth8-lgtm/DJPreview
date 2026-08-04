#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export LLM_PROVIDER=mock
export AUDIO_RENDERER=fallback
export PYTHONPATH="$(pwd)"

echo "[check-backend] Running pytest ..."
python -m pytest -q
echo "[check-backend] OK"
