[🇯🇵 日本語](deploy.md) | [🇬🇧 English](deploy.en.md)

# Production Deployment Guide

This document describes the production deployment procedure for `cat-feed-tracker` on a server (e.g., VPS).

---

## 1. Service Management with systemd

A systemd configuration example for running the FastAPI application in the background with automatic startup.

### Creating the Service File

Create `/etc/systemd/system/cat-feed-tracker.service` with the following content:

```ini
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

### Starting and Enabling the Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now cat-feed-tracker
```

---

## 2. Nginx Reverse Proxy Configuration

Configuration example for placing Nginx in front of the FastAPI application (running on port 8001).

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

> [!TIP]
> We recommend using Cloudflare for TLS (HTTPS) termination. Set the TLS mode to **Full (strict)** in the Cloudflare dashboard and use an origin certificate.

---

## 3. Post-Deployment Verification

Before connecting the Pico W, verify that the API server is accessible from outside.

### Health Check

```bash
curl https://your-domain.example.com/healthz
# Should return {"status":"ok"}
```

### LINE Webhook Path Verification

```bash
# POST without a signature — 400 (Bad Request) means the app is reachable (502 Bad Gateway means Nginx/upstream issue)
curl -s -o /dev/null -w "%{http_code}" -X POST https://your-domain.example.com/api/webhook/line
# 400
```

### End-to-End Verification

Send a test event from the command line and verify it is saved to the database.

1. **Send a test event**
   ```bash
   curl -X POST https://your-domain.example.com/api/events \
     -H "Authorization: Bearer <YOUR_DEVICE_TOKEN>" \
     -H "Content-Type: application/json" \
     -d '{}'
   # Should return {"status":"ok","event_id":1,"received_at":"..."}
   ```

2. **Check the database**
   ```bash
   psql cat_feed_tracker -c "SELECT received_at FROM feed_events ORDER BY received_at DESC LIMIT 1;"
   ```
