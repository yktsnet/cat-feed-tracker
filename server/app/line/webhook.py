"""
cat-feed-tracker / server/app/line/webhook.py
LINEからの照会・設定変更ロジック
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from app.db.connection import get_conn
from app.line.notify import build_scheduled_message, build_today_message

JST = timedelta(hours=9)


def handle_today(reply_token: str) -> None:
    """今日の記録：0時JSTから現在時刻までの全件"""
    body = build_today_message()
    if body is None:
        body = "🐱 今日はまだ給餌の記録がありません"
    _reply(reply_token, body)


def handle_average(reply_token: str) -> None:
    """週平均（直近4週）・月平均（直近3ヶ月）"""
    now_utc = datetime.now(timezone.utc)
    today_jst = (now_utc + JST).date()
    day_start_utc = (
        datetime(today_jst.year, today_jst.month, today_jst.day, tzinfo=timezone.utc)
        - JST
    )

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # 週平均：直近4週
            week_lines = ["週平均（直近4週）"]
            for i in range(4):
                w_end = day_start_utc - timedelta(weeks=i)
                w_start = w_end - timedelta(weeks=1)
                cur.execute(
                    "SELECT COUNT(*) FROM feed_events WHERE received_at >= %s AND received_at < %s",
                    (w_start, w_end),
                )
                count = cur.fetchone()[0]
                w_start_jst = (w_start + JST).date()
                w_end_jst = (w_end + JST).date()
                week_lines.append(
                    f" {w_start_jst.strftime('%m/%d')}〜{w_end_jst.strftime('%m/%d')}  {count}回"
                )

            # 月平均：直近3ヶ月
            month_lines = ["月平均（直近3ヶ月）"]
            for i in range(3):
                # i月前の1日〜末日
                target = today_jst.replace(day=1)
                for _ in range(i):
                    target = (target - timedelta(days=1)).replace(day=1)
                m_start_jst = target
                if target.month == 12:
                    m_end_jst = target.replace(year=target.year + 1, month=1, day=1)
                else:
                    m_end_jst = target.replace(month=target.month + 1, day=1)

                m_start_utc = (
                    datetime(
                        m_start_jst.year,
                        m_start_jst.month,
                        m_start_jst.day,
                        tzinfo=timezone.utc,
                    )
                    - JST
                )
                m_end_utc = (
                    datetime(
                        m_end_jst.year,
                        m_end_jst.month,
                        m_end_jst.day,
                        tzinfo=timezone.utc,
                    )
                    - JST
                )

                cur.execute(
                    "SELECT COUNT(*) FROM feed_events WHERE received_at >= %s AND received_at < %s",
                    (m_start_utc, m_end_utc),
                )
                count = cur.fetchone()[0]
                days = (m_end_jst - m_start_jst).days
                avg = round(count / days, 1) if days > 0 else 0
                month_lines.append(f" {m_start_jst.strftime('%Y/%m')}  {avg}回/日")

    finally:
        conn.close()

    body = "🐱 給餌平均\n\n" + "\n".join(week_lines) + "\n\n" + "\n".join(month_lines)
    _reply(reply_token, body)


def handle_settings(reply_token: str) -> None:
    """設定メニューを返す"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM feeding_rules WHERE key = 'notify_enabled'")
            enabled = cur.fetchone()[0] == "true"
            cur.execute("SELECT value FROM feeding_rules WHERE key = 'alert_limit'")
            limit = cur.fetchone()[0]
    finally:
        conn.close()

    status = "ON" if enabled else "OFF"
    body = (
        f"🐱 設定\n\n"
        f"通知：{status}\n"
        f"上限アラート：{limit}回\n\n"
        f"変更するには以下を送信してください：\n"
        f"・「通知オフ」または「通知オン」\n"
        f"・「上限変更」"
    )
    _reply(reply_token, body)


def handle_message(user_id: str, reply_token: str, text: str) -> None:
    """テキストメッセージのルーティング"""
    text = text.strip()

    # 上限変更の対話中
    if user_id in _waiting_limit_input:
        if text == "キャンセル":
            _waiting_limit_input.discard(user_id)
            _reply(reply_token, "キャンセルしました。")
            return
        if not text.isdigit():
            _reply(
                reply_token,
                "数字を入力してください。（キャンセルする場合は「キャンセル」）",
            )
            return
        new_limit = int(text)
        if new_limit < 1:
            _reply(reply_token, "1以上の数字を入力してください。")
            return
        conn = get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE feeding_rules SET value = %s, updated_at = NOW() WHERE key = 'alert_limit'",
                        (str(new_limit),),
                    )
        finally:
            conn.close()
        _waiting_limit_input.discard(user_id)
        _reply(
            reply_token, f"上限を{new_limit}回に変更しました。本日から適用されます。"
        )
        return

    # 通常メッセージ
    if text == "今日の記録":
        handle_today(reply_token)
    elif text == "平均":
        handle_average(reply_token)
    elif text == "設定":
        handle_settings(reply_token)
    elif text == "通知オフ":
        _set_rule("notify_enabled", "false")
        _reply(reply_token, "通知をオフにしました。")
    elif text == "通知オン":
        _set_rule("notify_enabled", "true")
        _reply(reply_token, "通知をオンにしました。")
    elif text == "上限変更":
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT value FROM feeding_rules WHERE key = 'alert_limit'")
                current = cur.fetchone()[0]
        finally:
            conn.close()
        _waiting_limit_input.add(user_id)
        _reply(
            reply_token,
            f"1日の上限を何回にしますか？（現在：{current}回）\n（キャンセルする場合は「キャンセル」）",
        )
    else:
        # リッチメニュー以外の入力は無視（返信なし）
        pass


def _set_rule(key: str, value: str) -> None:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE feeding_rules SET value = %s, updated_at = NOW() WHERE key = %s",
                    (value, key),
                )
    finally:
        conn.close()
