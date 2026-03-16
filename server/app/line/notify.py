"""
cat-feed-tracker / server/app/line/notify.py
LINE通知送信ロジック
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    BroadcastRequest,
    TextMessage,
)
from app.db.connection import get_conn

logger = logging.getLogger(__name__)

JST = timedelta(hours=9)


def _get_line_api() -> MessagingApi:
    config = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN", ""))
    return MessagingApi(ApiClient(config))


def _format_duration(minutes: int) -> str:
    if minutes < 60:
        return f"+{minutes}分"
    h, m = divmod(minutes, 60)
    return f"+{h}時間{m}分" if m else f"+{h}時間"


def build_scheduled_message(slot: str) -> str | None:
    """
    slot: 'morning'(〜11:00JST) | 'afternoon'(〜16:00JST) | 'night'(〜21:00JST)
    その日の0時JSTからslot時刻までの全イベントを累計で返す
    """
    slot_labels = {
        "morning": "〜11:00",
        "afternoon": "〜16:00",
        "night": "〜21:00",
    }
    slot_utc_hours = {
        "morning": 11,  # UTC 02:00
        "afternoon": 16,  # UTC 07:00
        "night": 21,  # UTC 12:00
    }

    now_utc = datetime.now(timezone.utc)
    # 今日の0時JST = 今日のUTC 前日15:00 or 当日15:00
    today_jst = (now_utc + JST).date()
    day_start_utc = (
        datetime(today_jst.year, today_jst.month, today_jst.day, tzinfo=timezone.utc)
        - JST
    )

    slot_end_jst_hour = slot_utc_hours[slot]
    slot_end_utc = day_start_utc + JST + timedelta(hours=slot_end_jst_hour) - JST

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT received_at
                FROM feed_events
                WHERE received_at >= %s AND received_at < %s
                ORDER BY received_at ASC
                """,
                (day_start_utc, slot_end_utc),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        return None

    # スロットごとに区切り線で分けて累計表示
    slot_boundaries_jst = {
        "morning": [11],
        "afternoon": [11, 16],
        "night": [11, 16, 21],
    }
    boundaries = slot_boundaries_jst[slot]

    lines = [f"🐱 給餌まとめ（{slot_labels[slot]}）\n"]
    prev_time = None
    prev_boundary = 0
    section_count = 0

    for i, (received_at,) in enumerate(rows):
        jst_time = received_at + JST
        hour = jst_time.hour

        # 区切り線を挿入
        for b in boundaries:
            if prev_boundary < b <= hour and b != boundaries[-1]:
                if section_count > 0:
                    lines.append("─────────")
                prev_boundary = b
                prev_time = None  # セクション区切りで間隔リセット

        time_str = jst_time.strftime("%H:%M")
        if prev_time is None:
            lines.append(time_str)
        else:
            diff = int((received_at - prev_time).total_seconds() / 60)
            lines.append(f"{time_str}  {_format_duration(diff)}")

        prev_time = received_at
        section_count += 1

    lines.append(f"\n本日計{len(rows)}回")
    return "\n".join(lines)


def send_scheduled_notify(slot: str) -> None:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM feeding_rules WHERE key = 'notify_enabled'")
            row = cur.fetchone()
            if row and row[0] == "false":
                logger.info("notify disabled, skip slot=%s", slot)
                return
    finally:
        conn.close()

    body = build_scheduled_message(slot)
    if body is None:
        slot_label = {"morning": "〜11:00", "afternoon": "〜16:00", "night": "〜21:00"}[
            slot
        ]
        body = f"🐱 給餌まとめ（{slot_label}）\n\nこの時間帯の記録はありません"
    api = _get_line_api()
    api.broadcast(BroadcastRequest(messages=[TextMessage(text=body)]))
    logger.info("scheduled notify sent: slot=%s", slot)

    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO notification_logs (type, body) VALUES ('scheduled', %s)",
                    (body,),
                )
    finally:
        conn.close()


def send_alert_if_needed() -> None:
    """上限超過アラート：当日未発火の場合のみ送信"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # 設定取得
            cur.execute(
                "SELECT value FROM feeding_rules WHERE key IN ('alert_limit', 'notify_enabled') ORDER BY key"
            )
            cur.execute("SELECT value FROM feeding_rules WHERE key = 'alert_limit'")
            row = cur.fetchone()
            limit = int(row[0]) if row else 15

            cur.execute("SELECT value FROM feeding_rules WHERE key = 'notify_enabled'")
            row = cur.fetchone()
            if row and row[0] == "false":
                return

            # 今日の発火済み確認
            today_jst = (datetime.now(timezone.utc) + JST).date()
            cur.execute("SELECT 1 FROM alert_fired WHERE fired_date = %s", (today_jst,))
            if cur.fetchone():
                return

            # 今日の給餌回数
            day_start_utc = (
                datetime(
                    today_jst.year, today_jst.month, today_jst.day, tzinfo=timezone.utc
                )
                - JST
            )
            cur.execute(
                "SELECT COUNT(*) FROM feed_events WHERE received_at >= %s",
                (day_start_utc,),
            )
            count = cur.fetchone()[0]

            if count <= limit:
                return

        # アラート送信
        body = f"⚠️ 本日の給餌が{limit}回を超えました（現在{count}回）"
        api = _get_line_api()
        api.broadcast(BroadcastRequest(messages=[TextMessage(text=body)]))
        logger.info("alert sent: count=%d limit=%d", count, limit)

        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO alert_fired (fired_date) VALUES (%s) ON CONFLICT DO NOTHING",
                    (today_jst,),
                )
                cur.execute(
                    "INSERT INTO notification_logs (type, body) VALUES ('alert', %s)",
                    (body,),
                )
    finally:
        conn.close()
