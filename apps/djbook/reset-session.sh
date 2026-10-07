#!/bin/bash
# Clear app data and reopen login screen for one demo slot (1..3).
set -e
N="${1:-}"
case "$N" in
  1|2|3) ;;
  *) echo "usage: $0 <1|2|3>" >&2; exit 1 ;;
esac
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
"$SCRIPT_DIR/connect-adb.sh"
source "$SCRIPT_DIR/launch-djbook.sh"

ADB=(docker exec ws-scrcpy-djbook adb -s "redroid${N}:5555")
PKG="com.tkestas92.djbookmobilev2"

for i in $(seq 1 30); do
  if "${ADB[@]}" shell getprop sys.boot_completed 2>/dev/null | grep -q 1; then
    break
  fi
  sleep 2
done

"${ADB[@]}" shell pm clear "$PKG" >/dev/null 2>&1
sleep 2
launch_djbook_app "$N" || true
for i in $(seq 1 30); do
  if "${ADB[@]}" shell dumpsys window 2>/dev/null | grep -q "mCurrentFocus=.*$PKG"; then
    break
  fi
  sleep 0.5
done
sleep 1.5
