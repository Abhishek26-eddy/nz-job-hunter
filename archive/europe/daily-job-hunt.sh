#!/usr/bin/env bash
# Europe Job Agent daily runner.
# Starts the local stack, crawls jobs, runs AI matching, builds the dashboard,
# and opens it in the browser.
#
# Usage:
#   ./daily-job-hunt.sh
#   ./daily-job-hunt.sh --no-browser

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

NO_BROWSER=0
for arg in "$@"; do
  case "$arg" in
    --no-browser) NO_BROWSER=1 ;;
    *) echo "Unknown argument: $arg"; exit 1 ;;
  esac
done

if [[ "$NO_BROWSER" -eq 1 ]]; then
  python3 run_daily.py --no-browser
else
  python3 run_daily.py
fi
