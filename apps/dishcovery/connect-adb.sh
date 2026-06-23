#!/bin/bash
# Run after `docker compose up -d`, and on every reboot (see crontab note
# in agent-prompt.md). ws-scrcpy runs its own adb server inside its
# container, so it needs its own `adb connect` to see the redroid device.
set -e
docker exec ws-scrcpy-dishcovery adb connect redroid:5555
