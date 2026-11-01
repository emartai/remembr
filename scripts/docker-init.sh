#!/usr/bin/env bash
# Run from any directory; Python handles .env setup and bounded readiness checks.
set -euo pipefail
exec python3 "$(dirname "$0")/local_setup.py" "$@"
