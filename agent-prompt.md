# Goal

Deploy a live, interactive web demo of an Android app so visitors can try it
directly in a browser at `https://demo.kantrybes.lt`, using **redroid**
(Android-in-Docker) + **ws-scrcpy** (browser screen-mirroring client),
reverse-proxied through **Caddy**.

You have root/sudo SSH access to the target VPS. Work through the steps in
order, verify each one before moving to the next, and report back any error
output verbatim before attempting a fix.

## Step 0 — Sanity check

```
uname -r
docker --version || echo "docker not installed"
```

## Step 1 — Kernel modules (redroid dependency)

```
sudo apt update && sudo apt install -y linux-modules-extra-$(uname -r)
sudo modprobe binder_linux devices="binder,hwbinder,vndbinder"
sudo modprobe ashmem_linux
lsmod | grep -E "binder|ashmem"
```

- If `ashmem_linux` fails to load: some newer kernels dropped ashmem in favor
  of `memfd`. This is fine — redroid supports `androidboot.use_memfd=true`.
  Note it and continue.
- If `binder_linux` fails to load: STOP, report the exact error. This usually
  means the VPS provider's kernel doesn't expose binder (some shared
  hosts/containers don't). Hetzner Cloud, DigitalOcean, and most KVM-based
  VPS providers work fine.

## Step 2 — Docker

```
curl -fsSL https://get.docker.com | sh
sudo systemctl enable --now docker
```

## Step 3 — Deploy redroid + ws-scrcpy

```
sudo mkdir -p /opt/android-demo && cd /opt/android-demo
# copy the provided docker-compose.yml here
sudo docker compose up -d
sudo docker compose logs -f redroid
```

Wait until the boot log settles (no more crash-loop lines), then Ctrl+C.

## Step 4 — Connect ws-scrcpy's adb to redroid

```
chmod +x connect-adb.sh
./connect-adb.sh
```

Make it survive reboots:

```
(crontab -l 2>/dev/null; echo "@reboot sleep 30 && /opt/android-demo/connect-adb.sh") | crontab -
```

## Step 5 — Install the app APK

Upload the APK to the server first (e.g. `scp app.apk user@server:/opt/android-demo/`), then:

```
adb connect 127.0.0.1:5555
adb -s 127.0.0.1:5555 install /opt/android-demo/app.apk
```

## Step 6 — Reverse proxy + basic auth

```
sudo apt install -y caddy
caddy hash-password
# paste the output hash into the provided Caddyfile
sudo cp Caddyfile /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

Point the `demo.kantrybes.lt` DNS A record at this server's IP before testing.

## Step 7 — Test

Open `https://demo.kantrybes.lt`, log in with the basic-auth credentials,
confirm the screen renders and touch/click input actually controls the app.

## Known failure points

- `ghostry/ws-scrcpy` may be stale or broken on a given day. Fallback images:
  `haris132/ws-scrcpy`, `scavin/ws-scrcpy`, or build from source at
  `github.com/NetrisTV/ws-scrcpy`.
- If the video doesn't decode in the browser, check ws-scrcpy's player mode
  (MSE vs WebCodecs) and the browser console for codec errors.
- If the APK is ARM-only and the redroid image is `amd64`, the app may crash
  on launch — you need a redroid image with libhoudini (ARM→x86 translation)
  baked in, or an arm64 host/image instead.
- Never expose port 5555 publicly — it must stay bound to 127.0.0.1 only.
- Only one browser tab can meaningfully control the device at a time; that's
  expected for a single demo instance.
