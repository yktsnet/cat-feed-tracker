# cat-feed-tracker

Pico W のリードスイッチを介して給餌棚の開閉イベントを検知し、LINE で家族に通知を届ける IoT システムです。

<p align="center">
  <picture>
    <source media="(min-width: 800px)" srcset="./src/cat-feed-tracker.svg">
    <img src="./src/cat-feed-tracker.svg" alt="cat-feed-tracker Architecture" style="max-width: 100%;" width="300">
  </picture>
</p>

## System Overview

猫の給餌棚の開閉をリードスイッチで検知し、給餌イベントを記録・通知する小規模 IoT システムです。

## Design Concept

家族全員が簡単に確認できるシンプルな仕組みを目指して設計されています。

- **ゼロ操作**: 給餌棚を開けるだけで自動的に記録されます。スマートフォンの操作は一切不要です。
- **身近なインターフェース**: 通知や記録の確認、各種設定はすべて使い慣れた LINE アプリ内で完結します。専用のアプリをインストールする必要はありません。
- **エッジ側での誤検知対策**: チャタリング防止（デバウンス 200ms）やクールダウン（30秒）、NTPによる時刻同期をデバイス（Pico W）側で行い、不要なリクエストがサーバーへ送信されるのを防ぎます。

## Key Features

- **自動イベント検知**: リードスイッチの開閉を検知（デバウンス 200ms、クールダウン 30秒）。
- **定時まとめ通知**: 1日3回（JST 11:00 / 16:00 / 21:00）に、スロット時間帯ごとの給餌記録をまとめて LINE でブロードキャスト送信します。
- **上限超過アラート**: 1日の給餌回数が設定した上限を超えた場合、当日に1回だけ警告通知を送ります。
- **体重管理機能**: LINE から猫ごとの体重を記録し、直近5回分の履歴や給餌平均回数と並べて表示できます。
- **LINE リッチメニュー**: LINE アプリ内のメニューから、「今日の記録」「給餌平均」「体重」「設定」の確認や変更をワンタップで実行可能です。

## System Architecture

```
[Pico W]
  GP14 のリードスイッチ (PULL_UP)
  閉(CLOSED)→開(OPEN) エッジ検知 + デバウンス 200ms + クールダウン 30秒
  → HTTPS POST /api/events (Bearer トークン認証)

[VPS (NixOS / systemd など)]
  Nginx (リバースプロキシ, Cloudflare 経由の HTTPS 終端)
  FastAPI (:8001)
  ├── POST /api/events       # イベントの受信・記録
  ├── POST /api/webhook/line # LINE Webhook
  ├── GET  /api/status       # ダッシュボードサマリー
  └── GET  /healthz
  PostgreSQL 16
  ├── devices
  ├── feed_events
  ├── feeding_rules
  ├── notification_logs
  ├── alert_fired
  └── cat_weights

[LINE Messaging API]
  定時通知 (11:00 / 16:00 / 21:00 JST)
  リッチメニュー経由の操作: 今日の記録 / 平均 / 体重 / 設定
```

## Service Layout

| サービス名 | 役割 | 実行環境 |
|---|---|---|
| FastAPI (`uvicorn`) | イベント受信、LINE Webhook 受信、定時通知 | VPS (systemd) |
| APScheduler | 定時通知（11:00 / 16:00 / 21:00 JST）、上限チェック（5分間隔） | FastAPI プロセス内 |
| PostgreSQL 16 | イベント、設定ルール、アラート状態、体重データの永続化 | VPS |
| Nginx | リバースプロキシ、Cloudflare 経由 of HTTPS 終端 | VPS |
| MicroPython (`main.py`) | リードスイッチの検知、イベントの HTTPS POST 送信 | Pico W (起動時自動実行) |

## Stack

| レイヤー | 技術 / ツール |
|---|---|
| エッジ (Pico W) | Raspberry Pi Pico W / MicroPython |
| サーバー | Python / FastAPI / APScheduler |
| データベース | PostgreSQL 16 |
| 通知・連携 | LINE Messaging API |
| インフラ | Hetzner VPS / NixOS / systemd / Nginx / Cloudflare |

## Requirements

### Hardware
- Raspberry Pi Pico W
- リードスイッチ + マグネット

### Server
- Linux VPS (NixOS 推奨、他のディストリビューションでも可)
- PostgreSQL 16
- Python 3.11 以上
- ドメイン (Cloudflare DNS などで HTTPS Webhook を終端できる環境)

### External Services
- LINE Developers アカウント (Messaging API チャネルの作成が必要)

## Getting Started

### 0. Nix shell (Optional)

Nix パッケージマネージャーを使用している場合、`mpremote` や `python3` が含まれる開発環境を以下のコマンドで起動できます。

```bash
nix-shell
```

### 1. Clone

リポジトリをクローンし、ディレクトリに移動します。

```bash
git clone https://github.com/yktsnet/cat-feed-tracker.git
cd cat-feed-tracker
```

### 2. Environment

環境設定ファイルを作成します。

```bash
cp .env.example .env
# 各変数の値を設定してください（詳細は以下の「環境変数」セクションを参照）
```

#### Environment Variables

##### Server (`.env`)

| 変数名 | 説明 |
|---|---|
| `DB_HOST` / `DB_PORT` | PostgreSQL の接続ホスト名とポート番号 |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | PostgreSQL のデータベース名、接続ユーザー名、パスワード |
| `DEVICE_TOKEN` | `/api/events` へのリクエストを認証するためのトークン（Pico W側と一致させる必要があります） |
| `LINE_CHANNEL_SECRET` | LINE Webhook のシグネチャを検証するために使用 |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Messaging API を介してメッセージを送信するために使用 |

##### Pico W (`pico/secrets.py`)

| 変数名 | 説明 |
|---|---|
| `WIFI_SSID` / `WIFI_PASSWORD` | 接続する Wi-Fi の SSID とパスワード |
| `SERVER_URL` | VPS 上の `/api/events` のフル URL |
| `DEVICE_TOKEN` | `.env` に設定した `DEVICE_TOKEN` と同じ値 |

### 3. PostgreSQL

データベースとロールを作成し、マイグレーションファイルを適用します。

```bash
# ロールとデータベースの作成
sudo -u postgres psql -c "CREATE ROLE cat_feed_tracker LOGIN PASSWORD 'your_db_password';"
createdb -O cat_feed_tracker cat_feed_tracker

# スキーマの適用
psql cat_feed_tracker < server/migrations/001_initial.sql
psql cat_feed_tracker < server/migrations/002_m2.sql
psql cat_feed_tracker < server/migrations/003_weight.sql

# 権限の付与
sudo -u postgres psql cat_feed_tracker -c "
  GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cat_feed_tracker;
  GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO cat_feed_tracker;
  ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO cat_feed_tracker;
  ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO cat_feed_tracker;
"

# デバイスの登録 (Pico W側のトークンと一致させます)
psql cat_feed_tracker -c "
  INSERT INTO devices (device_key, name) VALUES ('your-token', 'shelf-1');
"
```

### 4. Server

**開発環境での実行**

```bash
cd server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

**本番環境での実行 (systemd)**

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

Pico W を接続する前に、リバースプロキシ経由で接続可能か検証します。

```bash
# Nginx 経由のヘルスチェック
curl http://localhost/healthz
# {"status":"ok"}

# LINE Webhook パスが疎通しているか確認 (署名なしリクエストで 400 エラーが返れば正常)
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost/api/webhook/line
# 400
```

### 5. Pico W

#### Wiring

リードスイッチを **GP14** と **GND** の間に接続します。内蔵プルアップを使用するため：

- スイッチが**閉じている**（磁石が近くにある）とき → GP14 は LOW
- スイッチが**開いた**（給餌棚を開けた）とき → GP14 は HIGH → 給餌イベント検知

#### Hardware Check

配線が正しいか確認するため、Pico W 上で REPL を開き以下のコードを実行します。

```python
from machine import Pin
sw = Pin(14, Pin.IN, Pin.PULL_UP)
sw.value()  # 0 = 閉じている(マグネットあり), 1 = 開いている
```

給餌棚を開閉したときに値が 0 と 1 で切り替わることを確認してください。

#### Flash

# デバイス上に `pico/secrets.py` を作成します（Git管理外）。

```bash
cp pico/secrets.py.example pico/secrets.py
# 実際の値を設定します
```

[mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html) を使用してプログラムを書き込みます。

```bash
mpremote connect /dev/ttyACM0 fs cp pico/secrets.py :secrets.py
mpremote connect /dev/ttyACM0 fs cp pico/main.py :main.py + reset
```

起動時のシリアル出力例：

```
WiFi connected: 192.168.x.x
NTP synced: (2026, ...)
cat-feed-tracker started. initial state: CLOSED
```

給餌棚を開けたときの出力例：

```
shelf opened → sending event
event sent ok: 2026-03-17T10:00:00Z
```

### 6. LINE Messaging API

1. [LINE Developers Console](https://developers.line.biz/) でチャネルを作成します。
2. Messaging API を有効にし、Webhook URL に `https://your-domain.example.com/api/webhook/line` を設定します。
3. `.env` に `LINE_CHANNEL_SECRET` と `LINE_CHANNEL_ACCESS_TOKEN` を設定します。

#### Rich Menu / Webhook Flow

LINE のリッチメニュー（2×2のグリッド）から送信される各テキストに応じた動作フローは以下の通りです。

| ボタン | 送信テキスト | 動作 |
|---|---|---|
| 今日の記録 | `今日の記録` | 現時点までの当日の給餌ログを返します。 |
| 平均 | `平均` | 直近4週間の週平均と、直近3ヶ月の月平均（給餌イベントがあった日のみを有効日として計算）を返します。 |
| 体重 | `体重` | 猫の選択と体重入力の2ステップ対話を開始し、保存後に直近5回の履歴と給餌平均を返します。 |
| 設定 | `設定` | 現在の通知のオン/オフ設定と上限アラート回数を表示し、変更方法を案内します。 |

追加のテキストコマンド：
- 「`通知オン`」 / 「`通知オフ`」で通知の有効/無効を切り替えます。
- 「`上限変更`」で1日の上限回数の変更対話を開始します。
- どの状態からでも「`キャンセル`」を送信すれば対話を中断できます。

#### Rich Menu Setup

```bash
# NixOS 環境
nix-shell -p python3Packages.pillow --run "python server/scripts/setup_rich_menu.py"

# その他の環境
pip install Pillow
LINE_CHANNEL_ACCESS_TOKEN=xxxx python server/scripts/setup_rich_menu.py
```

#### Sample Weight Data

テスト用にサンプルの体重データをインポートするSQL：

```sql
INSERT INTO cat_weights (cat_id, weight_kg, recorded_at) VALUES
  (1, 4.2, '2026-01-15'), (1, 4.3, '2026-02-01'), (1, 4.1, '2026-02-15'),
  (1, 4.4, '2026-03-01'), (1, 4.3, '2026-03-15'),  -- タマ
  (2, 3.8, '2026-01-15'), (2, 3.9, '2026-02-01'), (2, 3.7, '2026-02-15'),
  (2, 3.8, '2026-03-01'), (2, 3.9, '2026-03-15'),  -- ミケ
  (3, 5.1, '2026-01-15'), (3, 5.0, '2026-02-01'), (3, 5.2, '2026-02-15'),
  (3, 5.1, '2026-03-01'), (3, 5.3, '2026-03-15');  -- クロ
```

### 7. Nginx

Nginx のリバースプロキシ設定例：

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

> Cloudflare で TLS を終端させ、本番環境ではオリジン証明書を使用した **Full (strict)** モードを推奨します。Flexible モードでも動作しますが、VPS と Cloudflare 間の通信が暗号化されません。

### 8. Verify

**ヘルスチェックの検証**

```bash
curl https://your-domain.example.com/healthz
# {"status":"ok"}
```

**疎通確認: テストイベントの送信とDB確認**

```bash
# 1. テストイベントの POST 送信
curl -X POST https://your-domain.example.com/api/events \
  -H "Authorization: Bearer your-device-token" \
  -H "Content-Type: application/json" \
  -d '{}'
# {"status":"ok","event_id":1,"received_at":"..."}

# 2. PostgreSQL に保存されたか確認
psql cat_feed_tracker -c "SELECT received_at FROM feed_events ORDER BY received_at DESC LIMIT 1;"
```

LINEのチャネル設定が完了している場合は、リッチメニューの「今日の記録」から手動で通知が正しく配信されることを確認できます。

### Common Errors

| 現象 | 原因 | 対策 |
|---|---|---|
| `401 unauthorized` | `.env` とリクエスト（Pico W側）の `DEVICE_TOKEN` 不一致 | Bearer トークンの値が `.env` と同じか確認します |
| `403 device not registered` | トークンは有効だが `devices` テーブルにデバイスキーが未登録 | 導入手順の §3 にある `INSERT INTO devices ...` を実行します |
| `502 Bad Gateway` | Nginx がポート 8001 の uvicorn に接続できていない | `systemctl status cat-feed-tracker` でポートとプロセス状態を確認します |
| Webhook パスで `400 invalid signature` | `.env` の `LINE_CHANNEL_SECRET` 設定の誤りまたは未設定 | LINE Developers Console の値と一致しているか確認します |

## API Reference

| メソッド | パス | 認証 | 説明 |
|---|---|---|---|
| `POST` | `/api/events` | Bearer Token | Pico W からの給餌イベント受信 |
| `POST` | `/api/webhook/line` | LINE Signature | LINE Webhook 受信 |
| `GET` | `/api/status` | なし | ダッシュボードサマリー（本日のカウント、給餌平均） |
| `GET` | `/healthz` | なし | ヘルスチェック |

### POST /api/events

```bash
curl -X POST https://your-domain.example.com/api/events \
  -H "Authorization: Bearer your-device-token" \
  -H "Content-Type: application/json" \
  -d '{}'
```

## License

MIT
