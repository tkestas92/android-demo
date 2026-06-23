#!/bin/bash
# Reconnect ADB if ws-scrcpy lost the redroid device after a container restart.
set -e

for app in dishcovery djbook; do
  if ! docker exec "ws-scrcpy-$app" adb devices 2>/dev/null | grep -q 'redroid:5555[[:space:]]*device'; then
    "/opt/android-demo/apps/$app/connect-adb.sh" >/dev/null 2>&1 || true
  fi
done
