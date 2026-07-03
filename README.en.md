[🇯🇵 日本語](README.md) | [🇬🇧 English](README.en.md)

# cat-feed-tracker

[![CI](https://github.com/yktsnet/cat-feed-tracker/actions/workflows/ci.yml/badge.svg)](https://github.com/yktsnet/cat-feed-tracker/actions/workflows/ci.yml)

An IoT system that detects open/close events of a feeding shelf via a reed switch on a Pico W and delivers LINE notifications to family members.

<p align="center">
  <picture>
    <source media="(min-width: 800px)" srcset="./src/cat-feed-tracker.svg">
    <img src="./src/cat-feed-tracker.svg" alt="cat-feed-tracker Architecture" style="max-width: 100%;" width="300">
  </picture>
</p>

## Quick Start

Using Docker Compose, you can start the entire environment including PostgreSQL in one command.

### Prerequisites

- **Hardware**: Raspberry Pi Pico W, reed switch, magnet
- **External Services**: LINE Developers account (Messaging API channel)
- **Runtime**: Docker Compose (for production, a domain capable of HTTPS termination)

### Setup

```bash
git clone https://github.com/yktsnet/cat-feed-tracker.git
cd cat-feed-tracker

# Create environment variables file and fill in LINE tokens
cp .env.example .env
# Replace LINE_CHANNEL_SECRET and LINE_CHANNEL_ACCESS_TOKEN with actual values

# Edit to match your cats if needed
# vi config/cats.yaml

# Start the server (includes DB initialization on first run)
docker compose up -d
```

After starting, register the Pico W's DEVICE_TOKEN in the DB:

```bash
docker compose exec db psql -U cat_feed -d cat_feed \
  -c "INSERT INTO devices (device_key, name) VALUES ('your-device-token', 'shelf-1');"
```

- API Documentation (Swagger UI): http://localhost:8001/docs

---

## Overview

This tool records the open/close events of a reed switch attached to the feeding shelf door as "feeding events," and delivers them as a digest to LINE — the chat family members already use — so everyone naturally shares who fed the cats and when. Instead of notifying on every event, it sends three aggregated notifications per day to avoid notification fatigue while still detecting overfeeding.

## Key Features

- **Automatic Event Detection**: Detects open/close events from the reed switch (200ms debounce, 30-second cooldown).
- **Scheduled Summary Notifications**: Sends a LINE broadcast with feeding records grouped by time slot, 3 times daily (JST 11:00 / 16:00 / 21:00).
- **Over-Limit Alert**: Delivers a one-time warning notification on the day when the daily feeding count exceeds the configured limit.
- **Weight Management**: Records per-cat weight from LINE and displays it alongside feeding history and average feeding counts.
- **LINE Rich Menu**: One-tap access from LINE to "Today's Records", "Feeding Average", "Weight", and "Settings".

## Architecture

```
[Pico W]
  Reed switch on GP14 (PULL_UP)
  CLOSED→OPEN edge detection + 200ms debounce + 30-second cooldown
  → HTTPS POST /api/events (Bearer token auth)

[VPS (NixOS / systemd etc.)]
  Nginx (reverse proxy, HTTPS termination via Cloudflare)
  FastAPI (:8001)
  └── PostgreSQL 16 (persistence)

[LINE Messaging API]
  Scheduled notifications (11:00 / 16:00 / 21:00 JST)
  Rich menu integration: Today's records / Average / Weight / Settings
```

## Tech Stack

| Layer | Technology | Reason |
|---|---|---|
| **Device** | Raspberry Pi Pico W (MicroPython) | Sufficient and inexpensive for reed-switch detection. Built-in Wi-Fi handles HTTPS sending on a single device. |
| **Backend** | FastAPI (Python 3.11+) | Lightweight API with auto-generated OpenAPI docs. Hosts APScheduler for scheduled notifications. |
| **Database** | PostgreSQL 16 | Accessed with raw SQL via psycopg2, keeping the design simple without an ORM. |
| **Notification** | LINE Messaging API | Broadcasts to the channel family members already use, with rich-menu interactive operation. |
| **Infra** | Docker Compose / Nginx / Cloudflare | Starts everything including the DB in one command; HTTPS terminated via Cloudflare. |

## Design Decisions

- **Raw SQL via psycopg2, no ORM**: The schema is small and migrations are applied manually, so the abstraction layer's cost was avoided.
- **Scheduled digests instead of per-event notifications**: Notifying on every open/close is noisy, so notifications are limited to three time-slot digests per day, with an immediate alert only once per day when overfeeding occurs.
- **Externalized configuration for cat names, notification times, etc.**: Values that vary per household are pulled out into `config/` so they can be adjusted without code changes.

## Scope

**Focus:**
- Detecting, recording, and LINE-notifying feeding-shelf open/close, plus weight management
- Daily feeding sharing among a small family

**Out of Scope:**
- Measuring the actual amount of food (only open/close counts are handled)
- Image or video recording via cameras, etc.
- Multi-tenant operation across multiple households

## Development

Steps for developing and running locally without Docker.

### 1. Clone and Configure Environment Variables

```bash
git clone https://github.com/yktsnet/cat-feed-tracker.git
cd cat-feed-tracker

cp .env.example .env
# Fill in PostgreSQL connection info, DEVICE_TOKEN, and LINE settings in the server-side .env

cp pico/secrets.py.example pico/secrets.py
# Fill in Wi-Fi info, SERVER_URL, and DEVICE_TOKEN in the Pico W-side secrets.py
```

### 2. Database Setup

```bash
# Create role and database
sudo -u postgres psql -c "CREATE ROLE cat_feed_tracker LOGIN PASSWORD 'your_db_password';"
createdb -O cat_feed_tracker cat_feed_tracker

# Apply schema
psql cat_feed_tracker < server/migrations/001_initial.sql
psql cat_feed_tracker < server/migrations/002_m2.sql
psql cat_feed_tracker < server/migrations/003_weight.sql

# Register device (match the token on the Pico W side)
psql cat_feed_tracker -c "
  INSERT INTO devices (device_key, name) VALUES ('your-token', 'shelf-1');
"
```

### 3. Start the Development Server

```bash
cd server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

Detailed API endpoint information is available in the auto-generated Swagger UI (`http://localhost:8001/docs`) after starting the server.

### 4. Flash Pico W and Wiring

- **Wiring**: Connect the reed switch between GP14 and GND.
- **Flashing**: Use [mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html) to write the program.

```bash
mpremote connect /dev/ttyACM0 fs cp pico/secrets.py :secrets.py
mpremote connect /dev/ttyACM0 fs cp pico/main.py :main.py + reset
```

## Documentation Links

For details on each configuration and production operations, refer to the following documents.

- **[Production Deployment Guide](./docs/deploy.md)** (systemd, Nginx, connectivity checks, etc.)
- **[LINE Rich Menu and Webhook Integration Spec](./docs/rich_menu.md)** (rich menu setup, interactive command flow, sample data)

## How this was built

Development follows an issue-driven workflow that separates design (interactive AI), implementation (autonomous AI), and verification (human merge). An AI agent implements each change starting from an issue file, and dangerous operations are blocked by configuration rather than by convention. The setup lives in [dotfiles-public](https://github.com/yktsnet/dotfiles-public); the process itself is visible in this repository's issues and PRs.

## License

MIT
