#!/bin/bash
# Run the hunter every 15 minutes on this Mac (launchd). Undo with:
#   launchctl bootout gui/$(id -u)/com.nzjobhunter.hunt && rm ~/Library/LaunchAgents/com.nzjobhunter.hunt.plist
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLIST="$HOME/Library/LaunchAgents/com.nzjobhunter.hunt.plist"
LOG="$HOME/Library/Logs/nz-job-hunter.log"
PY="$(command -v python3)"
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.nzjobhunter.hunt</string>
  <key>ProgramArguments</key>
  <array><string>/bin/bash</string><string>$ROOT/scripts/hunt_on_mac.sh</string></array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>$(dirname "$PY"):/usr/bin:/bin:/usr/sbin:/sbin</string>
    <key>PYTHON</key><string>$PY</string>
  </dict>
  <key>StartInterval</key><integer>900</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
</dict>
</plist>
PL
launchctl bootout "gui/$(id -u)/com.nzjobhunter.hunt" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "Installed. Runs every 15 minutes while the Mac is awake. Log: $LOG"
