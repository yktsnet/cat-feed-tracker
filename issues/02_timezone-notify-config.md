## タイムゾーン・通知時刻の設定化
id: 02
skill: pr-workflow
branch-slug: timezone-notify-config
github_issue:
status: open
type: feat
対象: server/app/line/webhook.py, server/app/line/notify.py, server/app/main.py, .env.example
内容: ハードコードされたJST・通知時刻を環境変数で設定可能にし、日本以外でも使えるようにする
確認: python -m py_compile で対象ファイルの構文確認、pytest 通過
---
## 背景

タイムゾーン (`JST = timedelta(hours=9)`) と通知スロット時刻が複数ファイルにハードコードされており、日本以外のユーザーが使えない。

## ハードコード箇所

### `JST = timedelta(hours=9)` — webhook.py:21, notify.py:20
- `timedelta` ベースの手動オフセット計算が両ファイルに散在
- `zoneinfo.ZoneInfo` に置換する

### SQL 内の `'Asia/Tokyo'` リテラル — webhook.py:101,146
- `AT TIME ZONE 'Asia/Tokyo'` がクエリに直書き
- 設定値をパラメータとして渡す

### 通知 cron 時刻 — main.py:19-21
- UTC 2,7,12 固定（= JST 11,16,21）
- スロット時刻から UTC 逆算して動的に設定

### スロット定義 — notify.py:22-26, 46-49
- `SLOT_LABELS` とスロット境界時刻が固定
- 環境変数から読み込む

## 設計

### 環境変数（`.env.example` に追記）

```
TIMEZONE=Asia/Tokyo
NOTIFY_SLOTS=11:00,16:00,21:00
```

- `TIMEZONE`: IANA タイムゾーン名。`zoneinfo.ZoneInfo(TIMEZONE)` で使う
- `NOTIFY_SLOTS`: カンマ区切りのローカル時刻。スロットラベル（朝・昼・夜）は時刻から自動判定、またはデフォルト名を使う

### 共通の timezone ユーティリティ

- `server/app/config.py` に `TIMEZONE` と `NOTIFY_SLOTS` の読み込みを追加（01 で作成済みの config.py を拡張）
- `JST` 変数の代わりに `get_tz()` で `ZoneInfo` オブジェクトを返す
- webhook.py と notify.py の両方から参照

### 各ファイルの変更方針

- `webhook.py` / `notify.py`: `JST` を `config.get_tz()` に置換。SQL の `'Asia/Tokyo'` はパラメータ化
- `main.py`: cron 時刻を `NOTIFY_SLOTS` から UTC 逆算して登録
- `notify.py`: `SLOT_LABELS` / スロット境界を `NOTIFY_SLOTS` から動的生成

## テストへの影響

- 既存テストは JST 前提のモック値を使っている。テスト内で `TIMEZONE=Asia/Tokyo` を fixture として設定すれば既存テストはそのまま通るはず
