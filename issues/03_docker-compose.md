## Docker Compose で一発起動
id: 03
skill: pr-workflow
branch-slug: docker-compose
github_issue: 5
status: close
type: feat
対象: Dockerfile (新規), docker-compose.yml (新規), README.md, .env.example, server/migrations/
内容: clone → .env に LINE トークン記入 → docker compose up で動く構成を作る。一般ユーザー向けの導入手段
確認: python -m py_compile で server 側の変更ファイル確認、Dockerfile の構文は目視確認
---
## 背景

現状は NixOS + systemd + PostgreSQL の手動セットアップが前提で、一般ユーザーが clone して動かせない。Docker Compose に FastAPI + PostgreSQL を同梱し、環境構築を不要にする。

## 設計

### `Dockerfile` (新規)

- Python 3.11 ベース
- `server/requirements.txt` を pip install
- `server/app/main.py` を uvicorn で起動
- `config/` ディレクトリをコピー（`cats.yaml` を参照するため）

### `docker-compose.yml` (新規)

- `app`: FastAPI サーバ（上記 Dockerfile）
- `db`: PostgreSQL コンテナ
- `.env` ファイルを `env_file` で読み込み
- `db` の初期化に `server/migrations/*.sql` を使う（PostgreSQL の `/docker-entrypoint-initdb.d/` にマウント）
- ボリューム: PostgreSQL データ永続化

### `.env.example` の更新

Docker Compose 用の DB 接続情報を追記：
```
DB_HOST=db
DB_PORT=5432
DB_NAME=cat_feed
DB_USER=cat_feed
DB_PASSWORD=cat_feed
```

### `README.md` の更新

導入手順セクションを追加：
1. `git clone`
2. `cp .env.example .env` → LINE トークン等を記入
3. `config/cats.yaml` を自分の猫に編集
4. `docker compose up -d`

## 注意事項

- VPS 側の NixOS 運用には影響しない（Docker Compose は一般ユーザー向け）
- マイグレーション SQL の適用順序に注意（001 → 002 → 003）
- `config/cats.yaml` のサンプルは 01 で作成済み
