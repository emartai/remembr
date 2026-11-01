#!/usr/bin/env bash
set -euo pipefail
if [ "${SKIP_COMPOSE:-0}" != "1" ]; then
  python3 "$(dirname "$0")/local_setup.py"
fi
exec python3 "$(dirname "$0")/smoke_test.py" --url "${REMEMBR_URL:-http://localhost:8000}"
