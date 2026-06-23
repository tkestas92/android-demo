#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
"$SCRIPT_DIR/connect-adb.sh"

ADB="docker exec ws-scrcpy-dishcovery adb -s redroid:5555"
PKG="com.dishcovery.app"

for i in $(seq 1 30); do
  if $ADB shell getprop sys.boot_completed 2>/dev/null | grep -q 1; then
    break
  fi
  sleep 2
done

$ADB shell pm clear "$PKG" >/dev/null 2>&1
sleep 2
$ADB shell am start -n "$PKG/.MainActivity" >/dev/null 2>&1
