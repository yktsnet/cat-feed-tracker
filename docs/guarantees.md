# 保証台帳

## 保証

### 1. tests/test_main.py — HTTP API（`server/app/api/events.py` / `server/app/api/webhook.py`）

- `GET /healthz` は 200 で `{"status": "ok"}` を返す
- `POST /api/events` に `Authorization` ヘッダのトークンが `DEVICE_TOKEN` と一致しない（または `Bearer` スキームでない）場合、401 で `{"detail": "unauthorized"}` を返す
- `POST /api/events` はトークンが正しくてもデバイスが `devices` テーブルに未登録なら 403 で `{"detail": "device not registered"}` を返す
- `POST /api/events` は同一デバイスの直近30秒以内に既存イベントがある場合、エラーにせず 200 で `{"status": "duplicate", "ignored": true}` を返す
- `POST /api/events` は正常系で 201 を返し、レスポンスボディに `status: "ok"`・`event_id`（挿入行のID）・`received_at`（ISO形式文字列）を含む
- `POST /api/events` は `Authorization` ヘッダ自体が欠落している場合、422 を返す（FastAPI の `Header(...)` バリデーションによる）
- `POST /api/webhook/line` は `X-Line-Signature` の検証に失敗すると 400 で `{"detail": "invalid signature"}` を返す
- `POST /api/webhook/line` は署名検証以外の理由でパース失敗した場合（空bodyの検証リクエスト等）、例外を握りつぶして 200 `{"status": "ok"}` を返す

| 保証（要約） | 対応テスト |
|---|---|
| `/healthz` は 200 + `{"status": "ok"}` | `test_healthz` |
| `/api/events` トークン不一致は 401 | `test_events_unauthorized` |
| `/api/events` デバイス未登録は 403 | `test_events_device_not_registered` |
| `/api/events` 直近30秒以内の重複は 200 + `duplicate` | `test_events_duplicate` |
| `/api/events` 正常系は 201 + `event_id`/`received_at` | `test_events_success` |
| `/api/events` Authorization ヘッダ欠落は 422 | `test_events_missing_authorization_header` |
| `/api/webhook/line` 署名検証失敗は 400 | `test_line_webhook_invalid_signature` |
| `/api/webhook/line` 署名検証以外のパース失敗は握りつぶして 200 | `test_line_webhook_parse_error_returns_ok` |

### 2. tests/test_main.py — LINE通知メッセージ（`build_today_message` / `build_scheduled_message`、`server/app/line/notify.py`）

- `build_today_message` は当日イベントがある場合、`"今日の記録"` を含む見出しから始まり、各イベント時刻を `HH:MM` 形式で列挙し、2件目以降は直前イベントとの差分を `+N時間M分` 形式で付記し、末尾に `"本日計N回"` を含む
- `build_scheduled_message(slot_idx)` はそのスロットの終端時刻までのイベントがある場合、見出しに `"給餌まとめ（〜HH:MM）"`（スロット終端時刻）を含み、時刻・経過時間の表記は `build_today_message` と同様で、末尾に `"本日計N回"` を含む
- `build_scheduled_message(slot_idx)` は `slot_idx >= 1` の場合、それ以前のスロット境界時刻をまたぐイベントの間に区切り線 `"─────────"` を挿入する
- `build_today_message` / `build_scheduled_message` はその期間内にイベントが0件の場合 `None` を返す
- `build_today_message` の時刻表記は `TIMEZONE` 環境変数（`get_tz()`）に従う

| 保証（要約） | 対応テスト |
|---|---|
| 当日サマリの見出し・時刻列挙・経過時間・合計回数 | `test_build_today_message` |
| スロットまとめ（午前）の見出し・時刻・合計回数 | `test_build_scheduled_message_morning` |
| スロットまとめ（午後）は境界をまたぐイベント間に区切り線 | `test_build_scheduled_message_afternoon` |
| イベント0件は `None` を返す | `test_build_today_message_no_events_returns_none`, `test_build_scheduled_message_no_events_returns_none` |
| 時刻表記は `TIMEZONE` 環境変数に従う | `test_build_today_message_respects_timezone_env` |

## この台帳について

このリポの「契約面」（外部から観測可能な振る舞い）のうち、テストによって固定されている保証を一覧にする。地位は [design-decisions.md](../context/design-decisions.md) 相当のドキュメントと同格であり、実装が本台帳と食い違う場合は不整合として指摘対象になる。

### 対象範囲

- HTTP API のレスポンス（ステータスコード・ボディ）: `GET /healthz`、`POST /api/events`、`POST /api/webhook/line`
- LINE 通知メッセージの文言フォーマット（見出し・時刻表記・経過時間表記・区切り線・合計回数表記）: `build_today_message` / `build_scheduled_message`（`server/app/line/notify.py`）。関数自体は内部実装だが、戻り値はそのまま LINE 上でユーザーが目にする通知本文になるため契約面として扱う。

### 対象外（内部実装）

- DB スキーマ・SQL クエリの具体的な発行内容
- `send_scheduled_notify` / `send_alert_if_needed` の内部制御フロー（DB 更新順序、`notification_logs` / `alert_fired` への書き込みタイミングなど）
- APScheduler のジョブ登録自体（`main.py`）
- Pico W 側（`pico/main.py`）の実装

**ここに載っていない振る舞いは約束ではなく、予告なく変わりうる。**
