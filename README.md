# cat-feed-tracker

A small IoT system that detects cat feeding events via a reed switch on a Pico W and delivers LINE notifications to family members.

<details>
<summary>🇯🇵 日本語による説明を表示する</summary>

## システム概要

猫の給餌棚の開閉をリードスイッチで検知し、給餌イベントを記録・通知する小規模IoTシステムです。

## 主な機能

- 給餌イベントの自動検知（デバウンス・クールダウン処理、NTP時刻同期）
- 1日3回（11時・16時・21時 JST）の定時まとめ通知
- 上限回数超過アラート（当日1回のみ）
- LINEリッチメニューからの照会・設定変更

</details>

## Architecture
```
[Pico W]
  Reed switch on GP14 (PULL_UP)
  CLOSED→OPEN edge detection + debounce 200ms + cooldown 30s
  → HTTPS POST /api/events (Bearer token)

[Hetzner VPS]
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

## Setup

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
