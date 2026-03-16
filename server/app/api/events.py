import os
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel
from app.db.connection import get_conn

logger = logging.getLogger(__name__)
router = APIRouter()

DEVICE_TOKEN = os.getenv("DEVICE_TOKEN", "")


class EventIn(BaseModel):
    sent_at: datetime | None = None  # Pico W 側の送信時刻（任意）
    note: str | None = None


@router.post("/events", status_code=status.HTTP_201_CREATED)
def receive_event(
    body: EventIn,
    authorization: str = Header(...),
):
    # トークン検証
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or token != DEVICE_TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")

    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                # device_key でデバイスを引く
                cur.execute(
                    "SELECT id FROM devices WHERE device_key = %s",
                    (DEVICE_TOKEN,),
                )
                row = cur.fetchone()
                if row is None:
                    raise HTTPException(status_code=403, detail="device not registered")
                device_id = row[0]

                # 重複チェック（UNIQUE 制約でも弾かれるが事前確認）
                now = datetime.now(timezone.utc)
                cur.execute(
                    """
                    SELECT id FROM feed_events
                    WHERE device_id = %s
                      AND received_at > NOW() - INTERVAL '30 seconds'
                    """,
                    (device_id,),
                )
                if cur.fetchone():
                    # 30秒以内の重複はスキップ（エラーではなく 200 で返す）
                    logger.warning("duplicate event ignored: device_id=%s", device_id)
                    return {"status": "duplicate", "ignored": True}

                # 保存
                cur.execute(
                    """
                    INSERT INTO feed_events (device_id, received_at, sent_at, note)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, received_at
                    """,
                    (device_id, now, body.sent_at, body.note),
                )
                event_id, received_at = cur.fetchone()

        logger.info("feed event saved: id=%s at=%s", event_id, received_at)
        return {
            "status": "ok",
            "event_id": event_id,
            "received_at": received_at.isoformat(),
        }

    finally:
        conn.close()
