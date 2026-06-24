#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
"$SCRIPT_DIR/connect-adb.sh"
source "$SCRIPT_DIR/launch-djbook.sh"

ADB=(docker exec ws-scrcpy-djbook adb -s redroid:5555)

for i in $(seq 1 30); do
  if "${ADB[@]}" shell getprop sys.boot_completed 2>/dev/null | grep -q 1; then
    break
  fi
  sleep 2
done

launch_djbook_app
