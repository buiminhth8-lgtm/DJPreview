#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/apps/web"

echo "[check-frontend] npm ci ..."
npm ci --no-audit --no-fund

echo "[check-frontend] npm run build ..."
npm run build

cd "$ROOT"
echo "[check-frontend] OK"
