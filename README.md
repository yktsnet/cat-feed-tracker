# cat-feed-tracker

Pico W のリードスイッチを介して給餌棚の開閉イベントを検知し、LINE で家族に通知を届ける IoT システムです。

<p align="center">
  <picture>
    <source media="(min-width: 800px)" srcset="./src/cat-feed-tracker.svg">
    <img src="./src/cat-feed-tracker.svg" alt="cat-feed-tracker Architecture" style="max-width: 100%;" width="300">
  </picture>
</p>

## Key Features

- **自動イベント検知**: リードスイッチの開閉を検知（デバウンス 200ms、クールダウン 30秒）。
- **定時まとめ通知**: 1日3回（JST 11:00 / 16:00 / 21:00）に、スロット時間帯ごとの給餌記録をまとめて LINE でブロードキャスト送信。
- **上限超過アラート**: 1日の給餌回数が設定した上限を超えた場合、当日に1回だけ警告通知を配信。
- **体重管理機能**: LINE から猫ごとの体重を記録し、履歴や給餌平均回数を並べて表示。
- **LINE リッチメニュー**: LINE からワンタップで「今日の記録」「給餌平均」「体重」「設定」の操作が可能。

## System Architecture

```
[Pico W]
  GP14 のリードスイッチ (PULL_UP)
  閉(CLOSED)→開(OPEN) エッジ検知 + デバウンス 200ms + クールダウン 30秒
  → HTTPS POST /api/events (Bearer トークン認証)

[VPS (NixOS / systemd など)]
  Nginx (リバースプロキシ, Cloudflare 経由の HTTPS 終端)
  FastAPI (:8001)
  └── PostgreSQL 16 (永続化)

[LINE Messaging API]
  定時通知 (11:00 / 16:00 / 21:00 JST)
  リッチメニュー連携: 今日の記録 / 平均 / 体重 / 設定
```

## Requirements

- **ハードウェア**: Raspberry Pi Pico W、リードスイッチ、マグネット
- **サーバー**: Linux VPS、PostgreSQL 16、Python 3.11 以上、ドメイン（Cloudflare等で HTTPS 終端できる環境）
- **外部サービス**: LINE Developers アカウント (Messaging API チャネル)

## Getting Started

### 1. クローンと環境変数の設定

```bash
git clone https://github.com/yktsnet/cat-feed-tracker.git
cd cat-feed-tracker

cp .env.example .env
# サーバー側 .env に PostgreSQL 接続情報、DEVICE_TOKEN、LINE 設定を記入します

cp pico/secrets.py.example pico/secrets.py
# Pico W 側 secrets.py に Wi-Fi 情報、SERVER_URL、DEVICE_TOKEN を記入します
```

### 2. データベースのセットアップ

```bash
# ロールとデータベースの作成
sudo -u postgres psql -c "CREATE ROLE cat_feed_tracker LOGIN PASSWORD 'your_db_password';"
createdb -O cat_feed_tracker cat_feed_tracker

# スキーマの適用
psql cat_feed_tracker < server/migrations/001_initial.sql
psql cat_feed_tracker < server/migrations/002_m2.sql
psql cat_feed_tracker < server/migrations/003_weight.sql

# デバイスの登録 (Pico W側のトークンと一致させます)
psql cat_feed_tracker -c "
  INSERT INTO devices (device_key, name) VALUES ('your-token', 'shelf-1');
"
```

### 3. 開発サーバーの起動

```bash
cd server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### 4. Pico W への書き込みと配線

- **配線**: GP14 と GND の間にリードスイッチを接続します。
- **書き込み**: [mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html) を使用してプログラムを書き込みます。

```bash
mpremote connect /dev/ttyACM0 fs cp pico/secrets.py :secrets.py
mpremote connect /dev/ttyACM0 fs cp pico/main.py :main.py + reset
```

---

## Documentation Links

各設定の詳細や本番運用については、以下のドキュメントを参照してください。

- **[本番デプロイ手順](file:///wsl.localhost/Ubuntu/home/widget/projects/clone-repos/cat-feed-tracker/docs/deploy.md)** (systemd, Nginx, 疎通確認など)
- **[LINE リッチメニューと Webhook 連携仕様](file:///wsl.localhost/Ubuntu/home/widget/projects/clone-repos/cat-feed-tracker/docs/rich_menu.md)** (リッチメニューの設定・対話コマンドフロー・サンプルデータ)

---

## API Reference

API のエンドポイント詳細は、サーバー起動後に自動生成されるインタラクティブドキュメント（Swagger UI）から確認できます。

- URL: `http://localhost:8001/docs`

## License

MIT
