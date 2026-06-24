# Android Browser Demo — pilna santrauka

**Handoff dokumentas kitam AI / developeriui**  
**Data:** 2026-06-23  
**Autorius:** Kantrybės (Kęstas) demo projektas

---

## 1. Projekto tikslas

Leisti lankytojams **naršyklėje** išbandyti Android aplikacijas (**Dishcovery**, **DJ Book**) be fizinio telefono — per **redroid** emuliatorių + **ws-scrcpy** stream'ą, hostinama **Hetzner VPS**, integruota į portfolio **kantrybes.lt/dev**.

---

## 2. Infrastruktūra

| Kas | Detalės |
|-----|---------|
| VPS | Hetzner CX23, Helsinki, IP 135.181.39.195, Ubuntu |
| SSH | root@135.181.39.195, raktas Mac ~/.ssh/id_ed25519 (be passphrase) |
| Serverio kelias | /opt/android-demo/ |
| Reverse proxy | Caddy (/etc/caddy/Caddyfile) |
| Docker | 2 atskiri stack'ai (Dishcovery + DJ Book) |

### URL'ai

| App | URL | Portai (localhost) |
|-----|-----|---------------------|
| Dishcovery | https://demo-dishcovery.kantrybes.lt | redroid 5555, ws-scrcpy 8001 |
| DJ Book | https://demo-djbook.kantrybes.lt | redroid 5556, ws-scrcpy 8002 |
| IP fallback | http://135.181.39.195 | tik Dishcovery |

**Auth (tiesioginis apsilankymas):** user `demo`, pass `dishcovery2026`  
**Embed kelias (iframe iš portfolio):** `/embed/` — be auth

### DNS

- demo-dishcovery.kantrybes.lt → A → 135.181.39.195
- demo-djbook.kantrybes.lt → A → 135.181.39.195
- www.kantrybes.lt → Railway (portfolio), ne VPS
- Buvo DNSSEC problemų domreg.lt — reikėjo išjungti kad Let's Encrypt veiktų

---

## 3. Repo struktūra

**GitHub:** https://github.com/tkestas92/android-demo

```
android-demo/
├── apps/dishcovery/     # docker-compose, APK, scripts, www/index.html
├── apps/djbook/         # tas pats pattern
├── Caddyfile            # template (server'yje tikras hash)
├── demo-reset-server.py # Python HTTP reset API (:9003)
├── demo-reset.service   # systemd unit
├── watch-adb.sh         # ADB reconnect watchdog (cron kas 3 min)
└── agent-prompt.md      # pradinis deploy guide (dalis outdated)
```

**Portfolio repo:** https://github.com/tkestas92/kantrybes  
Live demo modal: components/LiveDemoModal.tsx, lib/liveDemo.ts

---

## 4. Kaip veikia vienas demo stack'as

Kiekvienam app'ui (apps/dishcovery/ ar apps/djbook/):

### docker-compose.yml

- **redroid** — Android 13 x86_64, privileged: true
  - Rezoliucija: 720×1600, DPI 280, FPS 30
  - Props: Pixel 9 (ro.product.model=Pixel9 ir kt.)
  - Volume: ./redroid-data:/data
  - Portas: 127.0.0.1:5555 arba 5556
- **ws-scrcpy** — ghostry/ws-scrcpy:latest
  - Custom index.html mount
  - Portas: 127.0.0.1:8001 / 8002

### ADB ryšys

- connect-adb.sh: docker exec ws-scrcpy-{app} adb connect redroid:5555
- Po konteinerio restart ADB atsijungia — sprendimas:
  - @reboot cron: start-demo.sh (po 45–60 s)
  - watch-adb.sh kas 3 min per cron

### start-demo.sh

- Prisijungia ADB, laukia sys.boot_completed
- Paleidžia app'ą
- Dishcovery: com.dishcovery.app/.MainActivity
- DJ Book: com.tkestas92.djbookmobilev2/.MainActivity

### Custom www/index.html

- Auto-redirect į stream (#!action=stream&player=mse&...)
- localStorage stream settings (bitrate, bounds, fit: true)
- MSE player (ne WebCodecs — buvo black screen)
- Fone kviečia POST /demo-reset
- Redirect vyksta iškart, ne laukiant reset

### Sesijos reset

- reset-session.sh: pm clear {package} + app restart → login
- demo-reset-server.py (:9003): pagal Host header paleidžia script
- Caddy: POST /demo-reset → proxy į :9003

---

## 5. Caddy routing

Kiekvienam subdomain:

1. WebSocket (Upgrade: websocket) → ws-scrcpy be auth
2. /embed* → ws-scrcpy be auth, strip_prefix /embed, CSP frame-ancestors kantrybes.lt
3. /demo-reset → Python reset server
4. Visa kita → basic auth + reverse proxy

---

## 6. Portfolio integracija (kantrybes.lt/dev)

### DB (Railway MySQL)

- Stulpelis live_type ENUM('web', 'app')
- DJBook → live_type=app, URL https://demo-djbook.kantrybes.lt
- Dishcovery → live_type=app, URL https://demo-dishcovery.kantrybes.lt
- Kiti web projektai → live_type=web
- Migracija: portfolio/migrations/012_add_live_type.sql

### UI

- **Live app** → siauras telefono modalas, iframe su /embed/
- **Live web** → platus modalas (75vh), pilnas URL
- Uždarymas: X, backdrop, Esc

---

## 7. APK / package info

| App | Package | Activity |
|-----|---------|----------|
| Dishcovery | com.dishcovery.app | .MainActivity |
| DJ Book | com.tkestas92.djbookmobilev2 | .MainActivity |

DJ Book backend: https://djbook-backend-production.up.railway.app

---

## 8. Žinomos problemos

### DJ Book nuotraukos demo'e

- Railway ./uploads ephemeral — failai dingsta po redeploy, DB URL lieka → HTTP 404
- Ne demo serverio bug
- Fix: Railway Volume arba S3/R2 djbook-backend projekte

### Shared demo instance

- Vienas redroid = visi lankytojai dalinasi session
- Sesijos reset ant naujo apsilankymo

### ADB atsijungimas

- Po ws-scrcpy restart reikia connect-adb.sh — watchdog taiso automatiškai

---

## 9. Cron (serveryje)

```
@reboot sleep 45 && /opt/android-demo/apps/dishcovery/start-demo.sh
@reboot sleep 60 && /opt/android-demo/apps/djbook/start-demo.sh
*/3 * * * * /opt/android-demo/watch-adb.sh
```

---

## 10. Naudingos komandos (VPS)

```bash
docker ps | grep -E 'dishcovery|djbook'
docker exec ws-scrcpy-dishcovery adb devices
docker exec ws-scrcpy-djbook adb devices

cd /opt/android-demo/apps/dishcovery && docker compose restart
cd /opt/android-demo/apps/djbook && docker compose restart

/opt/android-demo/apps/djbook/connect-adb.sh
/opt/android-demo/apps/djbook/start-demo.sh

caddy validate --config /etc/caddy/Caddyfile && systemctl reload caddy
systemctl status demo-reset
```

---

## 11. Chronologija

1. Deploy redroid + ws-scrcpy ant Hetzner, Caddy + basic auth
2. Dishcovery APK, auto-stream index.html, viewport sizing
3. SSH troubleshooting (passphrase raktas → naujas raktas)
4. DNS/subdomain strategija (ne /www/ path — Railway konfliktas)
5. Antras app — DJ Book (portai 5556/8002)
6. Black screen fix → MSE player
7. Sesijos reset (pm clear per /demo-reset)
8. ADB watchdog
9. Stream redirect fix (iškart, ne po reset)
10. Portfolio modal embed + Caddy /embed
11. live_type app vs web + DB migracija
12. Git push: kantrybes + android-demo repo

---

## 12. Deploy map

| Pakeitimas | Kur deploy |
|------------|------------|
| android-demo repo | VPS /opt/android-demo/ |
| Caddy | /etc/caddy/Caddyfile + reload |
| demo-reset | systemd service |
| Portfolio UI/DB | Git push → Railway |
| APK failai | rankiniu būdu ant serverio (ne git'e) |

---

## 13. Credentials (demo)

- Caddy: demo / dishcovery2026
- Portfolio admin: .env.local (Railway)
- VPS: SSH key auth kaip root
