#!/bin/bash
set -e
cd /opt/android-demo && git pull
cd apps/djbook && docker compose up -d --remove-orphans
docker restart ws-scrcpy-djbook
sleep 5 && ./connect-adb.sh
sudo systemctl restart demo-reset
docker ps
