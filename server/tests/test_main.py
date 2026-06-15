import os
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

# テスト用の環境変数
os.environ["DEVICE_TOKEN"] = "test-token"
os.environ["LINE_CHANNEL_SECRET"] = "test-secret"
os.environ["LINE_CHANNEL_ACCESS_TOKEN"] = "test-access-token"
os.environ["DB_NAME"] = "test-db"

from app.main import app

client = TestClient(app)

def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@patch("app.api.events.get_conn")
def test_events_unauthorized(mock_get_conn):
    response = client.post(
        "/api/events",
        headers={"Authorization": "Bearer invalid-token"},
        json={"note": "test"},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}

@patch("app.api.events.get_conn")
def test_events_device_not_registered(mock_get_conn):
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_get_conn.return_value = mock_conn

    # デバイス登録がない場合
    mock_cur.fetchone.return_value = None

    response = client.post(
        "/api/events",
        headers={"Authorization": "Bearer test-token"},
        json={"note": "test"},
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "device not registered"}

@patch("app.api.events.get_conn")
def test_events_duplicate(mock_get_conn):
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_get_conn.return_value = mock_conn

    # 1回目の fetchone でデバイスID=1、2回目の fetchone で重複イベント存在を検出
    mock_cur.fetchone.side_effect = [(1,), (999,)]

    response = client.post(
        "/api/events",
        headers={"Authorization": "Bearer test-token"},
        json={"note": "test"},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "duplicate", "ignored": True}

@patch("app.api.events.get_conn")
def test_events_success(mock_get_conn):
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_get_conn.return_value = mock_conn

    # 1回目の fetchone でデバイスID=1、2回目で重複なし(None)、3回目でINSERTのRETURNING(id, received_at)
    now = datetime.now(timezone.utc)
    mock_cur.fetchone.side_effect = [(1,), None, (10, now)]

    response = client.post(
        "/api/events",
        headers={"Authorization": "Bearer test-token"},
        json={"note": "test"},
    )
    assert response.status_code == 201
    res_json = response.json()
    assert res_json["status"] == "ok"
    assert res_json["event_id"] == 10
    assert "received_at" in res_json

@patch("app.line.notify.get_conn")
def test_build_today_message(mock_get_conn):
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_get_conn.return_value = mock_conn

    # JSTで10:00と11:30のイベント
    dt1 = datetime(2026, 6, 15, 1, 0, tzinfo=timezone.utc)
    dt2 = datetime(2026, 6, 15, 2, 30, tzinfo=timezone.utc)
    mock_cur.fetchall.return_value = [(dt1,), (dt2,)]

    from app.line.notify import build_today_message
    message = build_today_message()
    
    assert message is not None
    assert "今日の記録" in message
    assert "10:00" in message
    assert "11:30  +1時間30分" in message
    assert "本日計2回" in message

@patch("app.line.notify.get_conn")
def test_build_scheduled_message_morning(mock_get_conn):
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_get_conn.return_value = mock_conn

    # JSTで10:00のイベント
    dt1 = datetime(2026, 6, 15, 1, 0, tzinfo=timezone.utc)
    mock_cur.fetchall.return_value = [(dt1,)]

    from app.line.notify import build_scheduled_message
    message = build_scheduled_message("morning")
    
    assert message is not None
    assert "給餌まとめ（〜11:00）" in message
    assert "10:00" in message
    assert "本日計1回" in message

@patch("app.line.notify.get_conn")
def test_build_scheduled_message_afternoon(mock_get_conn):
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_get_conn.return_value = mock_conn

    # JSTで10:00と12:00（11:00を跨ぐ）のイベント
    dt1 = datetime(2026, 6, 15, 1, 0, tzinfo=timezone.utc)
    dt2 = datetime(2026, 6, 15, 3, 0, tzinfo=timezone.utc)
    mock_cur.fetchall.return_value = [(dt1,), (dt2,)]

    from app.line.notify import build_scheduled_message
    message = build_scheduled_message("afternoon")
    
    assert message is not None
    assert "給餌まとめ（〜16:00）" in message
    assert "10:00" in message
    assert "─────────" in message
    assert "12:00  +2時間" in message

@patch("app.api.webhook.parser")
def test_line_webhook_invalid_signature(mock_parser):
    from linebot.v3.exceptions import InvalidSignatureError
    mock_parser.parse.side_effect = InvalidSignatureError()

    response = client.post(
        "/api/webhook/line",
        headers={"X-Line-Signature": "invalid-sig"},
        content="test-body",
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "invalid signature"}
