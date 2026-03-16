-- cat-feed-tracker / 002_m2.sql

CREATE TABLE feeding_rules (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO feeding_rules (key, value) VALUES
    ('alert_limit',    '15'),
    ('notify_enabled', 'true');

CREATE TABLE notification_logs (
    id          BIGSERIAL PRIMARY KEY,
    type        TEXT NOT NULL,
    sent_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    body        TEXT
);

CREATE TABLE alert_fired (
    fired_date  DATE PRIMARY KEY
);
