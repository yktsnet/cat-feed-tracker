## 変更内容

clone → .env に LINE トークン記入 → `docker compose up` で動く構成を作る。一般ユーザー向けの導入手段。

**追加・変更ファイル:**

- `Dockerfile` (新規): Python 3.11-slim ベース。`server/requirements.txt` を pip install し、`server/` と `config/` をコピー。`PYTHONPATH=/app/server` を設定して `uvicorn app.main:app` で起動。
- `docker-compose.yml` (新規): `app`（FastAPI）+ `db`（PostgreSQL 16）の 2 サービス構成。`db` は `server/migrations/*.sql` を `/docker-entrypoint-initdb.d/` にマウントして初期化。ヘルスチェック付きで `app` は DB 起動完了を待ってから起動。PostgreSQL データはボリューム永続化。
- `.env.example`: DB 接続情報を Docker Compose 用デフォルト値（`DB_HOST=db`, `DB_NAME=cat_feed`, `DB_USER=cat_feed`, `DB_PASSWORD=cat_feed`）に更新。
- `README.md`: Docker Compose を使ったクイックスタートセクションを追加。

## 静的確認結果

- `nix-shell --run "cd server && PYTHONPATH=. pytest"`: **9 passed, 0 failed**
- `python -m py_compile` (server/app 配下の全 .py): **OK**（構文エラーなし）
- Dockerfile 構文: 目視確認 OK（`FROM` / `COPY` / `RUN` / `ENV` / `CMD` の正常構成）

## 検証手順

```bash
# 1. 環境変数を設定
cp .env.example .env
# .env の LINE_CHANNEL_SECRET, LINE_CHANNEL_ACCESS_TOKEN, DEVICE_TOKEN を実値に書き換える

# 2. コンテナを起動
docker compose up -d

# 3. ヘルスチェック
curl http://localhost:8001/healthz
# → {"status":"ok"}

# 4. デバイスを登録（Pico W の DEVICE_TOKEN と合わせる）
docker compose exec db psql -U cat_feed -d cat_feed \
  -c "INSERT INTO devices (device_key, name) VALUES ('your-device-token', 'shelf-1');"

# 5. API ドキュメント確認
open http://localhost:8001/docs
```
