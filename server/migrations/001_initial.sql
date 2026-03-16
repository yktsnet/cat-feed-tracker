-- cat-feed-tracker / 001_initial.sql
-- M1: devices + feed_events
-- feeding_rules と notification_logs は 002_m2.sql で追加

CREATE TABLE devices (
    id          SERIAL PRIMARY KEY,
    device_key  TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE feed_events (
    id           BIGSERIAL PRIMARY KEY,
    device_id    INTEGER NOT NULL REFERENCES devices(id),
    received_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at      TIMESTAMPTZ,
    note         TEXT,
    UNIQUE (device_id, received_at)
);

CREATE INDEX idx_feed_events_received_at ON feed_events (received_at DESC);

-- 実行後に以下を手動で行う（パスワードは .env の DB_PASSWORD と合わせる）:
--   ALTER USER cat_feed_tracker WITH PASSWORD '...';
--   GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cat_feed_tracker;
--   GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO cat_feed_tracker;
--   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO cat_feed_tracker;
--   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO cat_feed_tracker;
--
-- デバイス登録:
--   INSERT INTO devices (device_key, name) VALUES ('your-token-here', 'shelf-1');
