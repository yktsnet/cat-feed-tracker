## 変更内容

ハードコードされた JST・通知時刻を環境変数で設定可能にし、日本以外でも使えるようにする。

- **`server/app/config.py`（拡張）**
  - `get_tz()` — `TIMEZONE` 環境変数から `ZoneInfo` を返す（デフォルト: `Asia/Tokyo`）
  - `TZ_NAME` — IANA タイムゾーン名の文字列（SQL パラメータ用）
  - `NOTIFY_SLOTS` — `NOTIFY_SLOTS` 環境変数をパースした `list[tuple[int, int]]`（例: `[(11,0),(16,0),(21,0)]`）

- **`server/app/line/webhook.py`**
  - `JST = timedelta(hours=9)` を削除し、`get_tz()` / `TZ_NAME` を `app.config` から参照
  - `_build_average_text`: `JST` ベースの日付計算を `ZoneInfo` ベースに置換
  - SQL の `AT TIME ZONE 'Asia/Tokyo'` を `AT TIME ZONE %s`（パラメータ: `TZ_NAME`）に変更（2 箇所）
  - `handle_weight_record`: 同様に `get_tz()` ベースに置換

- **`server/app/line/notify.py`**
  - `JST = timedelta(hours=9)` / `SLOT_LABELS` 定数を削除
  - `build_scheduled_message(slot: str)` → `build_scheduled_message(slot_idx: int)` に変更
  - スロットラベルを `NOTIFY_SLOTS[slot_idx]` から動的生成（〜HH:MM 形式）
  - スロット境界リストも `NOTIFY_SLOTS[:slot_idx]` から動的生成
  - `build_today_message` / `send_alert_if_needed`: `ZoneInfo` ベースに置換
  - `send_scheduled_notify(slot: str)` → `send_scheduled_notify(slot_idx: int)` に変更

- **`server/app/main.py`**
  - ハードコードの cron 時刻（UTC 2/7/12）を廃止
  - `NOTIFY_SLOTS` をループして APScheduler の cron ジョブを登録
  - APScheduler の `timezone=ZoneInfo(TZ_NAME)` でローカル時刻を自動 UTC 変換

- **`.env.example`**
  - `TIMEZONE=Asia/Tokyo`、`NOTIFY_SLOTS=11:00,16:00,21:00` を追記

- **`server/tests/test_main.py`**
  - `TIMEZONE` / `NOTIFY_SLOTS` 環境変数をセットアップに追加
  - `build_scheduled_message("morning")` → `build_scheduled_message(0)` 等に変更

## 静的確認結果

```
$ nix-shell --run "python -m py_compile server/app/line/webhook.py" -> OK
$ nix-shell --run "python -m py_compile server/app/line/notify.py"  -> OK
$ nix-shell --run "python -m py_compile server/app/main.py"         -> OK
$ nix-shell --run "python -m py_compile server/app/config.py"       -> OK

$ nix-shell --run "cd server && PYTHONPATH=. pytest -v"
9 passed, 1 warning in 1.51s
```

## 検証手順

- `.env` に `TIMEZONE=Asia/Tokyo` と `NOTIFY_SLOTS=11:00,16:00,21:00` が存在することを確認（なければデフォルト値で動作）
- サーバ起動後、ログに `scheduled notify sent: slot_idx=0/1/2` が出力されることを確認
- LINE で「今日の記録」「平均」コマンドが正常に返答することを確認
- （任意）`TIMEZONE=America/New_York`・`NOTIFY_SLOTS=08:00,12:00,20:00` で再起動し、通知時刻が現地時間で正しく発火することを確認
