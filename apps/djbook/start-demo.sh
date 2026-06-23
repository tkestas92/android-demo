#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
"$SCRIPT_DIR/connect-adb.sh"

ADB="docker exec ws-scrcpy-djbook adb -s redroid:5555"
PKG="com.tkestas92.djbookmobilev2"

for i in $(seq 1 30); do
  if $ADB shell getprop sys.boot_completed 2>/dev/null | grep -q 1; then
    break
  fi
  sleep 2
done

$ADB shell am force-stop "$PKG" >/dev/null 2>&1 || true
ACTIVITY=$($ADB shell cmd package resolve-activity --brief "$PKG" 2>/dev/null | tail -1)
if [ -n "$ACTIVITY" ] && [ "$ACTIVITY" != "No activity found" ]; then
  $ADB shell am start -n "$ACTIVITY" >/dev/null 2>&1
else
  $ADB shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1
fi
