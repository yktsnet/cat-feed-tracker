[🇯🇵 日本語](deploy.md) | [🇬🇧 English](deploy.en.md)

# 本番環境デプロイ手順 (Deployment)

本ドキュメントでは、`cat-feed-tracker` のサーバー（VPSなど）への本番デプロイ手順について説明します。

---

## 1. systemd によるサービス管理

本番環境で FastAPI アプリケーションをバックグラウンド実行し、自動起動させるための systemd 設定例です。

### サービスファイルの作成

`/etc/systemd/system/cat-feed-tracker.service` に以下の内容を作成します。

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

### 起動と自動起動の有効化

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now cat-feed-tracker
```

---

## 2. Nginx リバースプロキシの設定

FastAPI アプリケーション（ポート 8001 で動作）の前段に Nginx を配置するための設定例です。

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
> Cloudflare を使用して TLS（HTTPS）を終端させることを推奨します。Cloudflare の管理画面で TLS モードを **Full (strict)** に設定し、オリジン証明書を使用してください。

---

## 3. デプロイ後の疎通確認 (Verification)

Pico W を接続する前に、外部から API サーバーに正常にアクセスできるか確認します。

### ヘルスチェックの検証

```bash
curl https://your-domain.example.com/healthz
# {"status":"ok"} が返れば正常
```

### LINE Webhook パスの検証

```bash
# 署名なしで POST し、400 (Bad Request) が返れば正常（Nginx等での 502 Bad Gateway はNG）
curl -s -o /dev/null -w "%{http_code}" -X POST https://your-domain.example.com/api/webhook/line
# 400
```

### エンドツーエンド検証

テスト用のイベントをコマンドラインから送信し、データベースに保存されるか検証します。

1. **テストイベントの送信**
   ```bash
   curl -X POST https://your-domain.example.com/api/events \
     -H "Authorization: Bearer <あなたのDEVICE_TOKEN>" \
     -H "Content-Type: application/json" \
     -d '{}'
   # {"status":"ok","event_id":1,"received_at":"..."} が返れば成功
   ```

2. **データベースの確認**
   ```bash
   psql cat_feed_tracker -c "SELECT received_at FROM feed_events ORDER BY received_at DESC LIMIT 1;"
   ```
