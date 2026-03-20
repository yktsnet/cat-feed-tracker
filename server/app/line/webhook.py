"""
cat-feed-tracker / server/app/line/webhook.py
LINEからの照会・設定変更・体重記録ロジック
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
from app.line.notify import build_today_message

logger = logging.getLogger(__name__)
JST = timedelta(hours=9)

# ── ステート管理 ──────────────────────────────────────────────────────────────
_waiting_limit_input: set[str] = set()
_waiting_weight_cat: set[str] = set()  # 猫番号の入力待ち
_waiting_weight_input: dict[str, int] = {}  # user_id → cat_id、体重数値の入力待ち

CAT_NAMES = {1: "タマ", 2: "ミケ", 3: "クロ"}
CAT_EMOJI = {1: "🍑", 2: "🍫", 3: "🍙"}


# ── 共通ユーティリティ ────────────────────────────────────────────────────────
def _reply(reply_token: str, text: str) -> None:
    config = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN", ""))
    api = MessagingApi(ApiClient(config))
    api.reply_message(
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[TextMessage(text=text)],
        )
    )


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


def _clear_all_states(user_id: str) -> None:
    """どの待機状態も全クリア（キャンセル時に使う）"""
    _waiting_limit_input.discard(user_id)
    _waiting_weight_cat.discard(user_id)
    _waiting_weight_input.pop(user_id, None)


# ── 既存ハンドラ ──────────────────────────────────────────────────────────────
def handle_today(reply_token: str) -> None:
    """今日の記録：0時JSTから現在時刻までの全件"""
    body = build_today_message()
    if body is None:
        body = "🐱 今日はまだ給餌の記録がありません"
    _reply(reply_token, body)


def handle_average(reply_token: str) -> None:
    """週平均（直近4週）・月平均（直近3ヶ月）"""
    body = "🐱 給餌平均\n\n" + _build_average_text()
    _reply(reply_token, body)


def _build_average_text() -> str:
    """給餌平均テキストを返す（体重記録後の表示にも流用）。
    平均は「記録がある日」のみを有効日として計算する。
    """
    now_utc = datetime.now(timezone.utc)
    today_jst = (now_utc + JST).date()
    day_start_utc = (
        datetime(today_jst.year, today_jst.month, today_jst.day, tzinfo=timezone.utc)
        - JST
    )

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            week_lines = ["🍽️ 週平均（直近4週）"]
            for i in range(4):
                w_end = day_start_utc - timedelta(weeks=i)
                w_start = w_end - timedelta(weeks=1)
                cur.execute(
                    """
                    SELECT COUNT(*) AS total,
                           COUNT(DISTINCT ((received_at AT TIME ZONE 'Asia/Tokyo')::date)) AS active_days
                    FROM feed_events
                    WHERE received_at >= %s AND received_at < %s
                    """,
                    (w_start, w_end),
                )
                total, active_days = cur.fetchone()
                avg = round(total / active_days, 1) if active_days > 0 else 0
                w_start_jst = (w_start + JST).date()
                w_end_jst = (w_end + JST).date()
                week_lines.append(
                    f"  {w_start_jst.strftime('%m/%d')}〜{w_end_jst.strftime('%m/%d')}  {avg}回/日（{active_days}日）"
                )

            month_lines = ["📅 月平均（直近3ヶ月）"]
            for i in range(3):
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
                    """
                    SELECT COUNT(*) AS total,
                           COUNT(DISTINCT ((received_at AT TIME ZONE 'Asia/Tokyo')::date)) AS active_days
                    FROM feed_events
                    WHERE received_at >= %s AND received_at < %s
                    """,
                    (m_start_utc, m_end_utc),
                )
                total, active_days = cur.fetchone()
                avg = round(total / active_days, 1) if active_days > 0 else 0
                month_lines.append(
                    f"  {m_start_jst.strftime('%Y/%m')}  {avg}回/日（{active_days}日）"
                )
    finally:
        conn.close()

    return "\n".join(week_lines) + "\n\n" + "\n".join(month_lines)


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
        f"⚙️ 設定\n\n"
        f"通知：{status}\n"
        f"上限アラート：{limit}回\n\n"
        f"変更するには以下を送信してください：\n"
        f"・「通知オフ」または「通知オン」\n"
        f"・「上限変更」"
    )
    _reply(reply_token, body)


# ── 体重ハンドラ ──────────────────────────────────────────────────────────────
def handle_weight_start(reply_token: str) -> None:
    """猫の選択肢を表示し番号入力を促す"""
    body = (
        "⚖️ 体重を記録します\n\n"
        "猫を選んでください：\n"
        "1. 🍑 タマ\n"
        "2. 🍫 ミケ\n"
        "3. 🍙 クロ\n\n"
        "番号を送ってください\n"
        "（キャンセルする場合は「キャンセル」）"
    )
    _reply(reply_token, body)


def handle_weight_cat_selected(user_id: str, reply_token: str, cat_id: int) -> None:
    """猫が選ばれたら体重数値の入力を促す"""
    _waiting_weight_cat.discard(user_id)
    _waiting_weight_input[user_id] = cat_id
    cat_name = CAT_NAMES[cat_id]
    emoji = CAT_EMOJI[cat_id]
    _reply(
        reply_token,
        f"{emoji} {cat_name}の体重を測って入力してください\n"
        f"（例：5.6）\n\n"
        f"キャンセルする場合は「キャンセル」",
    )


def handle_weight_record(user_id: str, reply_token: str, text: str) -> None:
    """体重を DB に保存し、直近5回履歴＋給餌平均を返す"""
    cat_id = _waiting_weight_input[user_id]
    cat_name = CAT_NAMES[cat_id]
    emoji = CAT_EMOJI[cat_id]

    # バリデーション
    try:
        weight = round(float(text), 1)
        if not (0.5 <= weight <= 20.0):
            raise ValueError("out of range")
    except ValueError:
        _reply(
            reply_token,
            "正しい体重を入力してください（例：5.6）\n"
            "キャンセルする場合は「キャンセル」",
        )
        return  # _waiting_weight_input はそのまま（再入力待ち）

    # DB保存
    now_utc = datetime.now(timezone.utc)
    today_jst = (now_utc + JST).date()

    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO cat_weights (cat_id, weight_kg, recorded_at)
                    VALUES (%s, %s, %s)
                    """,
                    (cat_id, weight, today_jst),
                )

        # 直近5回の体重を取得
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT weight_kg, recorded_at
                FROM cat_weights
                WHERE cat_id = %s
                ORDER BY recorded_at DESC, created_at DESC
                LIMIT 5
                """,
                (cat_id,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    _waiting_weight_input.pop(user_id, None)

    # 体重履歴テキスト
    weight_lines = [f"✅ {emoji} {cat_name}の体重を記録しました\n"]
    weight_lines.append("📋 直近の体重：")
    for w, d in rows:
        marker = " ← 今回" if d == today_jst and w == weight else ""
        weight_lines.append(f"  {d.strftime('%m/%d')}  {float(w):.1f} kg{marker}")

    # 給餌平均（「平均」ボタンと同じ内容）
    avg_text = _build_average_text()

    body = "\n".join(weight_lines) + "\n\n" + avg_text
    _reply(reply_token, body)


# ── メッセージルーティング ────────────────────────────────────────────────────
def handle_message(user_id: str, reply_token: str, text: str) -> None:
    text = text.strip()

    # キャンセルはどの状態からでも受け付ける
    if text == "キャンセル":
        _clear_all_states(user_id)
        _reply(reply_token, "キャンセルしました。")
        return

    # ── 上限回数の入力待ち ──
    if user_id in _waiting_limit_input:
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

    # ── 体重数値の入力待ち ──
    if user_id in _waiting_weight_input:
        handle_weight_record(user_id, reply_token, text)
        return

    # ── 猫番号の選択待ち ──
    if user_id in _waiting_weight_cat:
        if text in ("1", "2", "3"):
            handle_weight_cat_selected(user_id, reply_token, int(text))
        else:
            _reply(
                reply_token,
                "1・2・3 のいずれかを送ってください。\n（キャンセルする場合は「キャンセル」）",
            )
        return

    # ── 通常コマンド ──
    if text == "今日の記録":
        handle_today(reply_token)
    elif text == "平均":
        handle_average(reply_token)
    elif text == "体重":
        _waiting_weight_cat.add(user_id)
        handle_weight_start(reply_token)
    elif text == "設定":
        handle_settings(reply_token)
    elif text == "通知オフ":
        _set_rule("notify_enabled", "false")
        _reply(reply_token, "🔕 通知をオフにしました。")
    elif text == "通知オン":
        _set_rule("notify_enabled", "true")
        _reply(reply_token, "🔔 通知をオンにしました。")
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
            f"1日の上限を何回にしますか？（現在：{current}回）\n"
            f"（キャンセルする場合は「キャンセル」）",
        )
