"""
cat-feed-tracker / server/app/line/notify.py
LINE通知送信ロジック
"""

import os
import logging
from datetime import datetime, timezone
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    BroadcastRequest,
    TextMessage,
)
from app.db.connection import get_conn
from app.config import get_tz, NOTIFY_SLOTS

logger = logging.getLogger(__name__)


def _get_line_api() -> MessagingApi:
    config = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN", ""))
    return MessagingApi(ApiClient(config))


def _format_duration(minutes: int) -> str:
    if minutes < 60:
        return f"+{minutes}分"
    h, m = divmod(minutes, 60)
    return f"+{h}時間{m}分" if m else f"+{h}時間"


def build_scheduled_message(slot_idx: int) -> str | None:
    """
    slot_idx: NOTIFY_SLOTS のインデックス（0=1スロット目、1=2スロット目、…）
    その日の0時ローカルからslot時刻までの全イベントを累計で返す
    """
    tz = get_tz()
    slots = NOTIFY_SLOTS
    slot_hour, slot_minute = slots[slot_idx]
    slot_label = f"〜{slot_hour:02d}:{slot_minute:02d}"

    now_utc = datetime.now(timezone.utc)
    today_local = now_utc.astimezone(tz).date()
    day_start_utc = datetime(
        today_local.year, today_local.month, today_local.day, tzinfo=tz
    ).astimezone(timezone.utc)
    slot_end_utc = datetime(
        today_local.year, today_local.month, today_local.day,
        slot_hour, slot_minute, tzinfo=tz,
    ).astimezone(timezone.utc)

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

    # それ以前のスロット境界時刻（hour のみ）で区切り線を挿入
    boundaries = [h for h, _ in slots[:slot_idx]]

    lines = [f"🐱 給餌まとめ（{slot_label}）\n"]
    prev_time = None
    prev_boundary = 0
    section_count = 0

    for _, (received_at,) in enumerate(rows):
        local_time = received_at.astimezone(tz)
        hour = local_time.hour

        # 区切り線を挿入
        for b in boundaries:
            if prev_boundary < b <= hour:
                if section_count > 0:
                    lines.append("─────────")
                prev_boundary = b

        time_str = local_time.strftime("%H:%M")
        if prev_time is None:
            lines.append(time_str)
        else:
            diff = int((received_at - prev_time).total_seconds() / 60)
            lines.append(f"{time_str}  {_format_duration(diff)}")

        prev_time = received_at
        section_count += 1

    lines.append(f"\n本日計{len(rows)}回")
    return "\n".join(lines)


def build_today_message() -> str | None:
    """今日の記録：0時ローカルから現在時刻までの全イベント"""
    tz = get_tz()
    now_utc = datetime.now(timezone.utc)
    today_local = now_utc.astimezone(tz).date()
    day_start_utc = datetime(
        today_local.year, today_local.month, today_local.day, tzinfo=tz
    ).astimezone(timezone.utc)

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
                (day_start_utc, now_utc),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        return None

    lines = ["🐱 今日の記録\n"]
    prev_time = None
    for (received_at,) in rows:
        local_time = received_at.astimezone(tz)
        time_str = local_time.strftime("%H:%M")
        if prev_time is None:
            lines.append(time_str)
        else:
            diff = int((received_at - prev_time).total_seconds() / 60)
            lines.append(f"{time_str}  {_format_duration(diff)}")
        prev_time = received_at

    lines.append(f"\n本日計{len(rows)}回")
    return "\n".join(lines)


def send_scheduled_notify(slot_idx: int) -> None:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM feeding_rules WHERE key = 'notify_enabled'")
            row = cur.fetchone()
            if row and row[0] == "false":
                logger.info("notify disabled, skip slot_idx=%s", slot_idx)
                return
    finally:
        conn.close()

    body = build_scheduled_message(slot_idx)
    if body is None:
        slot_hour, slot_minute = NOTIFY_SLOTS[slot_idx]
        slot_label = f"〜{slot_hour:02d}:{slot_minute:02d}"
        body = f"🐱 給餌まとめ（{slot_label}）\n\nこの時間帯の記録はありません"

    api = _get_line_api()
    api.broadcast(BroadcastRequest(messages=[TextMessage(text=body)]))
    logger.info("scheduled notify sent: slot_idx=%s", slot_idx)

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
            tz = get_tz()
            today_jst = datetime.now(timezone.utc).astimezone(tz).date()
            cur.execute("SELECT 1 FROM alert_fired WHERE fired_date = %s", (today_jst,))
            if cur.fetchone():
                return

            # 今日の給餌回数
            day_start_utc = datetime(
                today_jst.year, today_jst.month, today_jst.day, tzinfo=tz
            ).astimezone(timezone.utc)
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
