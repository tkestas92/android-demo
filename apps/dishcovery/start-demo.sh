#!/bin/bash
# Connect ADB, wait for Android, launch Dishcovery.
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
"$SCRIPT_DIR/connect-adb.sh"

ADB="docker exec ws-scrcpy-dishcovery adb -s redroid:5555"

for i in $(seq 1 30); do
  if $ADB shell getprop sys.boot_completed 2>/dev/null | grep -q 1; then
    break
  fi
  sleep 2
done

$ADB shell am force-stop com.dishcovery.app >/dev/null 2>&1 || true
$ADB shell am start -n com.dishcovery.app/.MainActivity >/dev/null 2>&1
