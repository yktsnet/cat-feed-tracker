# cat-feed-tracker

An IoT system that detects cat feeding events via a reed switch on a Pico W and delivers LINE notifications to family members.

<p align="center">
  <picture>
    <source media="(min-width: 800px)" srcset="./src/cat-feed-tracker.svg" width="400">
    <img src="./src/cat-feed-tracker.svg" alt="cat-feed-tracker Architecture" style="max-width: 100%;" width="800">
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

### 1. Clone

```bash
git clone https://github.com/yktsnet/cat-feed-tracker.git
cd cat-feed-tracker
```

### 2. Environment

```bash
cp .env.example .env
# Fill in all values
```

### 3. PostgreSQL

```bash
createdb cat_feed_tracker
psql cat_feed_tracker < server/migrations/001_initial.sql
psql cat_feed_tracker < server/migrations/002_m2.sql

# Grant privileges
sudo -u postgres psql cat_feed_tracker -c "
  GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cat_feed_tracker;
  GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO cat_feed_tracker;
"

# Register device (use the same token as DEVICE_TOKEN in .env)
psql cat_feed_tracker -c "
  INSERT INTO devices (device_key, name) VALUES ('your-token', 'shelf-1');
"
```

### 4. Server

```bash
cd server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### 5. Pico W

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

### 6. LINE Messaging API

1. Create a channel at [LINE Developers Console](https://developers.line.biz/)
2. Enable Messaging API and set Webhook URL: `https://your-domain.example.com/api/webhook/line`
3. Add `LINE_CHANNEL_SECRET` and `LINE_CHANNEL_ACCESS_TOKEN` to `.env`

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

> HTTPS is handled by Cloudflare (Flexible mode). No certificates needed on the server.

### 8. Verify

```bash
curl https://your-domain.example.com/healthz
# {"status":"ok"}
```

## Key Features

- **Auto event detection**: Reed switch edge detection with 200 ms debounce and 30 s cooldown
- **Scheduled summaries**: LINE broadcast at 11:00 / 16:00 / 21:00 JST with per-interval breakdowns
- **Overfeed alert**: Fires once per day when the daily count exceeds a configurable limit
- **LINE rich menu**: Query today's log, weekly/monthly averages, or change settings — all from LINE

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
