# Conventions

命名・コード規約・スタイル（どう書くか）。

## Python (server)

- FastAPI アプリ。エントリポイントは `server/app/main.py`（APScheduler 定時通知の登録もここ）。
- API ルーティングは `server/app/api/` 配下で router 分割。`events.py`（Pico W からのイベント受信）、`webhook.py`（LINE Webhook）。
- LINE ビジネスロジックは `server/app/line/` 配下。`webhook.py`（対話ハンドラ）と `notify.py`（定時通知）。
- DB 接続は `server/app/db/connection.py`。psycopg2 直接、生 SQL。パラメータは `%s` プレースホルダ。
- テストは `server/tests/` 配下の `test_*.py`。DB は `get_conn` を mock して外部依存なし。

## MicroPython (pico)

- `pico/main.py` 1 ファイル構成。標準 Python との互換性はない（`machine`, `network` 等の MicroPython 固有モジュール）。
- 接続情報は `pico/secrets.py`（ignore 対象）。テンプレートは `pico/secrets.py.example`。

## 既知のハードコード（OSS 向け外部化の対象）

- 猫名・絵文字: `webhook.py` の `CAT_NAMES`, `CAT_EMOJI`
- タイムゾーン: `JST = timedelta(hours=9)` が `webhook.py`, `notify.py` に散在
- 通知時刻: `main.py` の cron 時刻（UTC 2,7,12）、`notify.py` の `SLOT_LABELS` / スロット境界

## コミット

- conventional commits（`feat` / `fix` / `docs` / `style` / `chore`）。
