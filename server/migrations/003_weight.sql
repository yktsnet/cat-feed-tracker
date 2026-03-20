-- cat-feed-tracker / 003_weight.sql
-- M3: 体重記録テーブル

CREATE TABLE cat_weights (
    id           BIGSERIAL PRIMARY KEY,
    cat_id       INTEGER NOT NULL CHECK (cat_id IN (1, 2, 3)),
    weight_kg    NUMERIC(4, 1) NOT NULL,
    recorded_at  DATE NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Tokyo')::DATE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 同じ猫の同じ日に複数回測った場合も蓄積する（重複は許可）
-- 最新値を正本にしたい場合は created_at DESC で取る
CREATE INDEX idx_cat_weights_cat_recorded
    ON cat_weights (cat_id, recorded_at DESC, created_at DESC);

-- 猫マスタコメント（テーブルはなく cat_id の定数として管理）
-- 1: たま
-- 2: みけ
-- 3: くろ
