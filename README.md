# cat-feed-tracker

An IoT system that detects cat feeding events via a reed switch on a Pico W and delivers LINE notifications to family members.

<p align="center">
  <picture>
    <source media="(min-width: 800px)" srcset="./src/cat-feed-tracker.svg">
    <img src="./src/cat-feed-tracker.svg" alt="cat-feed-tracker Architecture" style="max-width: 100%;" width="300">
  </picture>
</p>

<details>
<summary>🇯🇵 日本語による説明を表示する</summary>

## システム概要

猫の給餌棚の開閉をリードスイッチで検知し、給餌イベントを記録・通知する小規模IoTシステムです。

## 設計方針

家族全員が確認できるシンプルな仕組みを目指して設計されています。

- **ゼロ操作**: 棚を開けるだけで自動記録。スマホ操作は不要です。
- **既存サービスの活用**: 通知・照会はすべてLINEで完結。専用アプリは不要です。
- **誤検知対策**: デバウンス 200ms・クールダウン 30秒・NTP時刻同期をデバイス側で処理します。

## 主な機能

- 給餌イベントの自動検知と記録
- 1日3回（11時・16時・21時 JST）の定時まとめ通知
- 上限回数超過アラート（当日1回のみ）
- LINEリッチメニューからの照会・設定変更

## システム構成

1. **エッジ (Pico W)**: リードスイッチの開閉をGP14で検知し、デバウンス・クールダウン処理を経てイベントを送信します。
2. **サーバー (VPS)**: FastAPI でイベントを受信・記録し、APScheduler で定時通知とアラートチェックを実行します。
3. **データベース**: PostgreSQL 16 で給餌イベント・通知ルール・アラート履歴を管理します。
4. **通知**: LINE Messaging API のブロードキャストで家族全員に一斉通知し、Webhook 経由で照会・設定変更に対応します。

</details>

## System Architecture

```
[Pico W]
  Reed switch on GP14 (PULL_UP)
  CLOSED→OPEN edge detection + debounce 200ms + cooldown 30s
  → HTTPS POST /api/events (Bearer token)

[Hetzner VPS — NixOS / systemd]
  Nginx (reverse proxy, Cloudflare-terminated HTTPS)
  FastAPI :8001
  ├── POST /api/events       # event ingestion
  ├── POST /api/webhook/line # LINE webhook
  └── GET  /healthz
  PostgreSQL 16
  ├── devices
  ├── feed_events
  ├── feeding_rules
  ├── notification_logs
  └── alert_fired

[LINE Messaging API]
  Scheduled summaries at 11:00 / 16:00 / 21:00 JST
  Rich menu: 今日の記録 / 平均 / 設定
```

## Design Concept

- **Zero operation**: The shelf opening is all that is needed — no phone interaction required for logging.
- **Familiar interface**: All queries and settings are handled through LINE, which the whole family already uses.
- **Edge-side validation**: Debounce, cooldown, and NTP sync are handled on the Pico W to prevent duplicate events before they reach the server.

## Key Features

- **Auto event detection**: Reed switch edge detection with 200 ms debounce and 30 s cooldown
- **Scheduled summaries**: LINE broadcast at 11:00 / 16:00 / 21:00 JST with per-interval breakdowns
- **Overfeed alert**: Fires once per day when the daily count exceeds a configurable limit
- **LINE rich menu**: Query today's log, weekly/monthly averages, or change settings — all from LINE

## Service Layout

| Service | Role | Runs on |
|---|---|---|
| FastAPI (`uvicorn`) | Event ingestion, LINE webhook receiver, scheduled notify | VPS (systemd) |
| APScheduler | Scheduled summaries (11:00/16:00/21:00 JST), overfeed alert check (every 5 min) | In-process with FastAPI |
| PostgreSQL 16 | Persist feed events, rules, alert state | VPS |
| Nginx | Reverse proxy, Cloudflare-terminated HTTPS | VPS |
| MicroPython (`main.py`) | Reed switch detection, HTTPS event POST | Pico W (runs on boot) |

## Stack

| Layer | Technology |
|---|---|
| Edge | Raspberry Pi Pico W / MicroPython |
| Server | Python / FastAPI / APScheduler |
| Database | PostgreSQL 16 |
| Notification | LINE Messaging API |
| Infra | Hetzner VPS / NixOS / systemd / Nginx / Cloudflare |

## Requirements

### Hardware
- Raspberry Pi Pico W
- Reed switch + magnet

### Server
- Linux VPS (NixOS recommended, any distro works)
- PostgreSQL 16
- Python 3.11+
- Domain with Cloudflare DNS (for HTTPS webhook)

### External Services
- LINE Developers account (Messaging API channel)

## Getting Started

### 0. Nix shell (optional)

If you use Nix, a dev shell with `mpremote` and `python3` is provided:

```bash
nix-shell
```

### 1. Clone

```bash
git clone https://github.com/yktsnet/cat-feed-tracker.git
cd cat-feed-tracker
```

### 2. Environment

```bash
cp .env.example .env
# Fill in all values — see Environment Variables below
```

#### Environment Variables

| Variable | Used by | Description |
|---|---|---|
| `DB_HOST` / `DB_PORT` | Server | PostgreSQL host and port |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | Server | PostgreSQL credentials |
| `DEVICE_TOKEN` | Server + Pico W | Shared secret for Bearer auth on `/api/events` |
| `LINE_CHANNEL_SECRET` | Server | Used to verify LINE webhook signatures |
| `LINE_CHANNEL_ACCESS_TOKEN` | Server | Used to send messages via LINE Messaging API |

On the Pico W side, the equivalent values live in `pico/secrets.py`:

| Variable | Description |
|---|---|
| `WIFI_SSID` / `WIFI_PASSWORD` | Wi-Fi credentials |
| `SERVER_URL` | Full URL to `/api/events` on your VPS |
| `DEVICE_TOKEN` | Must match `DEVICE_TOKEN` in `.env` |

### 3. PostgreSQL

```bash
# Create role and database
sudo -u postgres psql -c "CREATE ROLE cat_feed_tracker LOGIN PASSWORD 'your_db_password';"
createdb -O cat_feed_tracker cat_feed_tracker

psql cat_feed_tracker < server/migrations/001_initial.sql
psql cat_feed_tracker < server/migrations/002_m2.sql

# Grant privileges
sudo -u postgres psql cat_feed_tracker -c "
  GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cat_feed_tracker;
  GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO cat_feed_tracker;
  ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO cat_feed_tracker;
  ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO cat_feed_tracker;
"

# Register device (use the same token as DEVICE_TOKEN in .env)
psql cat_feed_tracker -c "
  INSERT INTO devices (device_key, name) VALUES ('your-token', 'shelf-1');
"
```

### 4. Server

**Development**

```bash
cd server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

**Production (systemd)**

```ini
# /etc/systemd/system/cat-feed-tracker.service
[Unit]
Description=cat-feed-tracker FastAPI
After=network.target postgresql.service

[Service]
WorkingDirectory=/path/to/cat-feed-tracker/server
EnvironmentFile=/path/to/cat-feed-tracker/.env
ExecStart=/path/to/cat-feed-tracker/server/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now cat-feed-tracker
```

Verify the reverse proxy is routing correctly before connecting the Pico W:

```bash
# Health check through Nginx
curl http://localhost/healthz
# {"status":"ok"}

# Confirm LINE webhook path is reachable (expects 400 on missing signature, not 502)
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost/api/webhook/line
# 400
```

### 5. Pico W

#### Wiring

Connect the reed switch between **GP14** and **GND**. The pin uses the internal pull-up, so:

- Switch **closed** (magnet near) → GP14 LOW
- Switch **open** (shelf opened) → GP14 HIGH → feeding event

#### Hardware check

Verify the switch is wired correctly before flashing. Open a REPL on the Pico W:

```python
from machine import Pin
sw = Pin(14, Pin.IN, Pin.PULL_UP)
sw.value()  # 0 = closed (magnet present), 1 = open
```

Open and close the shelf and confirm the value toggles.

#### Flash

Create `pico/secrets.py` on the device (not tracked in git):

```bash
cp pico/secrets.py.example pico/secrets.py
# Fill in real values
```

Flash to the device using [mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html):

```bash
mpremote connect /dev/ttyACM0 fs cp pico/secrets.py :secrets.py
mpremote connect /dev/ttyACM0 fs cp pico/main.py :main.py + reset
```

Expected output on boot:

```
WiFi connected: 192.168.x.x
NTP synced: (2026, ...)
cat-feed-tracker started. initial state: CLOSED
```

On shelf open:

```
shelf opened → sending event
event sent ok: 2026-03-17T10:00:00Z
```

### 6. LINE Messaging API

1. Create a channel at [LINE Developers Console](https://developers.line.biz/)
2. Enable Messaging API and set Webhook URL: `https://your-domain.example.com/api/webhook/line`
3. Add `LINE_CHANNEL_SECRET` and `LINE_CHANNEL_ACCESS_TOKEN` to `.env`

#### Rich Menu / Webhook Flow

The rich menu exposes three buttons. Each sends a text message to the webhook, which routes it as follows:

| Button | Text sent | Action |
|---|---|---|
| 今日の記録 | `今日の記録` | Returns today's feed log up to the current time slot |
| 平均 | `平均` | Returns weekly (last 4 weeks) and monthly (last 3 months) averages |
| 設定 | `設定` | Shows current notify on/off and alert limit; prompts for changes |

Additional text commands: `通知オン` / `通知オフ` toggle notifications; `上限変更` starts a two-step dialog — the server replies asking for a number, and the next message you send (e.g. `5`) sets the new daily limit. Send `キャンセル` at any point to abort.

### 7. Nginx

```nginx
server {
    listen 80;
    server_name your-domain.example.com;
    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

> Cloudflare handles TLS termination. **Full (strict)** mode with an origin certificate is recommended for production. Flexible mode works but leaves the VPS↔Cloudflare leg unencrypted.

### 8. Verify

**Health check**

```bash
curl https://your-domain.example.com/healthz
# {"status":"ok"}
```

**End-to-end: inject an event and confirm DB**

```bash
# 1. POST a test event
curl -X POST https://your-domain.example.com/api/events \
  -H "Authorization: Bearer your-device-token" \
  -H "Content-Type: application/json" \
  -d '{}'
# {"status":"ok","event_id":1,"received_at":"..."}

# 2. Confirm it landed in PostgreSQL
psql cat_feed_tracker -c "SELECT received_at FROM feed_events ORDER BY received_at DESC LIMIT 1;"
```

If a LINE channel is configured, trigger a manual summary via the rich menu (`今日の記録`) to confirm the full notification path.

## API Reference

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/events` | Bearer token | Ingest a feed event from Pico W |
| `POST` | `/api/webhook/line` | LINE signature | LINE Webhook receiver |
| `GET` | `/healthz` | — | Health check |

### POST /api/events

```bash
curl -X POST https://your-domain.example.com/api/events \
  -H "Authorization: Bearer your-device-token" \
  -H "Content-Type: application/json" \
  -d '{}'
```

## License

MIT
