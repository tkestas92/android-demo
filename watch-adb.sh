#!/bin/bash
# Reconnect ADB if ws-scrcpy lost a redroid device after a container restart.
set -e

for n in 1 2 3; do
  if ! docker exec ws-scrcpy-djbook adb devices 2>/dev/null | grep -q "redroid${n}:5555[[:space:]]*device"; then
    /opt/android-demo/apps/djbook/connect-adb.sh >/dev/null 2>&1 || true
    break
  fi
done
