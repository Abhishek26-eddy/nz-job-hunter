#!/bin/bash
# One hunt on this Mac, then push the results to GitHub.
# The Gmail app password is read from the macOS Keychain (see README).
#
#   scripts/hunt_on_mac.sh               # normal run
#   scripts/hunt_on_mac.sh --test-email  # only send a test email
#   scripts/hunt_on_mac.sh --digest      # email everyone their full current list
set -euo pipefail
cd "$(dirname "$0")/.."

export SMTP_USER="${SMTP_USER:-abhishekprajapatiad@gmail.com}"
export ALERT_TO="${ALERT_TO:-$SMTP_USER}"
# Optional: ALERT_TO_WIFE=... in scripts/local.env (git-ignored).
[ -f scripts/local.env ] && source scripts/local.env && export ALERT_TO_WIFE
if ! SMTP_PASSWORD="$(security find-generic-password -s nz-job-hunter -a "$SMTP_USER" -w 2>/dev/null)"; then
  echo "No Gmail app password in the Keychain. Run:"
  echo "  security add-generic-password -s nz-job-hunter -a $SMTP_USER -w"
  exit 1
fi
export SMTP_PASSWORD

PYTHON="${PYTHON:-$(command -v python3)}"

if [ "${1:-}" = "--test-email" ] || [ "${1:-}" = "--digest" ]; then
  exec "$PYTHON" -m hunter.run "$1"
fi

echo "== $(date '+%Y-%m-%d %H:%M:%S') hunt"
git pull -q --no-rebase origin main
"$PYTHON" -m hunter.run
git add data/
if ! git diff --cached --quiet; then
  git commit -q -m "hunt (mac): $("$PYTHON" -c 'import json;m=json.load(open("data/meta.json"));print(m["new_this_run"],"new,",m["visa_ready_this_run"],"visa-ready")')"
  git push -q origin main
fi
