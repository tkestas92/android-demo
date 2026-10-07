#!/bin/bash
set -e
APK="${1:?usage: install-apk.sh <apk>}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
"$SCRIPT_DIR/connect-adb.sh"
docker cp "$APK" ws-scrcpy-djbook:/tmp/djbook.apk
for n in 1 2 3; do
  docker exec ws-scrcpy-djbook adb -s "redroid${n}:5555" install -r /tmp/djbook.apk
done
