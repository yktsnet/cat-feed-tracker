# CLAUDE.md

@context/conventions.md

## コマンド

- テスト: `cd server && PYTHONPATH=. pytest`（外部 DB 不要なモック構成）
- 構文チェック: `python -m py_compile server/app/main.py`（変更ファイルごと）
- 依存: `nix-shell` に入れば venv 作成と pip install が自動実行される。**`pip install` を直接実行しない**（`nix-shell` 外での pip / ensurepip は禁止）
- テスト実行: `nix-shell --run "cd server && PYTHONPATH=. pytest"`

## アーキテクチャの要点

- Pico W（MicroPython）が給餌棚のリードスイッチ開閉を検知し `POST /api/events` で FastAPI サーバへ送信。
- サーバは PostgreSQL に記録し、APScheduler で 1 日 3 回（JST 11:00 / 16:00 / 21:00）LINE にまとめ通知。
- LINE Webhook で給餌履歴・体重記録・設定変更を対話的に操作。
- DB は psycopg2 の生 SQL（ORM なし）。マイグレーションは `server/migrations/` に生 SQL、手動適用。

## 検証手段

- `nix-shell --run "cd server && PYTHONPATH=. pytest"`
- 変更した `.py` に `python -m py_compile`
- `pico/` 変更時は MicroPython 構文互換を目視確認（標準 Python では import 不可）
