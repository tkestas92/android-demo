#!/bin/bash
# Keep the demo emulators away from everything private.
# Visitors control these Android instances, so they must not be able to reach
# the home LAN (router, smart plug, TV), the Tailscale network, or services on
# the host itself. Internet access is left open for the apps' own backends.
set -euo pipefail

SUBNET="172.31.80.0/24"   # apps/djbook/docker-compose.yml -> networks.demo
BLOCKED=(10.0.0.0/8 172.16.0.0/12 192.168.0.0/16 100.64.0.0/10 169.254.0.0/16)

add() { iptables -C "$@" 2>/dev/null || iptables -I "$@"; }

# Traffic leaving the containers towards private ranges (routed via FORWARD).
# 172.16.0.0/12 also covers other Docker networks; same-bridge traffic between
# redroid and ws-scrcpy is allowed first.
for net in "${BLOCKED[@]}"; do
  add DOCKER-USER -s "$SUBNET" -d "$net" -j DROP
done
add DOCKER-USER -s "$SUBNET" -d "$SUBNET" -j RETURN

# New connections from the containers to the host itself (Caddy, Jellyfin,
# TorrServer, SSH ...). Replies to host-initiated connections still pass.
add INPUT -s "$SUBNET" -m conntrack --ctstate NEW -j DROP
