#!/bin/bash
set -e
docker exec ws-scrcpy-djbook adb connect redroid1:5555
docker exec ws-scrcpy-djbook adb connect redroid2:5555
docker exec ws-scrcpy-djbook adb connect redroid3:5555
