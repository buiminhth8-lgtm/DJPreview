#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "=== check-all: backend ==="
"$ROOT/scripts/check-backend.sh" --full

echo "=== check-all: frontend ==="
"$ROOT/scripts/check-frontend.sh"

echo "=== check-all: ALL OK ==="
