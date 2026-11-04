#!/bin/bash
# Redeploy the DJ Book demo on macserver.
#   bash /opt/android-demo/apps/djbook/deploy.sh           # code, containers, services
#   bash /opt/android-demo/apps/djbook/deploy.sh --caddy   # also install deploy/macserver/Caddyfile
set -e
REPO=/opt/android-demo

cd "$REPO" && git pull

# systemd units: dispatcher + LAN isolation firewall
sudo install -m 644 deploy/demo-reset.service /etc/systemd/system/demo-reset.service
sudo install -m 644 deploy/demo-firewall.service /etc/systemd/system/demo-firewall.service
sudo systemctl daemon-reload
sudo systemctl enable --quiet demo-firewall demo-reset

cd "$REPO/apps/djbook"
docker compose up -d --remove-orphans
docker restart ws-scrcpy-djbook   # picks up a changed www/index.html
sudo systemctl restart demo-firewall
sudo systemctl restart demo-reset
sleep 5 && ./connect-adb.sh

if [ "${1:-}" = "--caddy" ]; then
  sudo cp /etc/caddy/Caddyfile "/etc/caddy/Caddyfile.bak.$(date +%s)"
  sudo install -m 644 "$REPO/deploy/macserver/Caddyfile" /etc/caddy/Caddyfile
  caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
  sudo systemctl reload caddy
elif ! diff -q "$REPO/deploy/macserver/Caddyfile" /etc/caddy/Caddyfile >/dev/null; then
  echo "NOTE: /etc/caddy/Caddyfile differs from deploy/macserver/Caddyfile (run with --caddy to install it)."
fi

docker ps --format '{{.Names}}: {{.Status}}'
