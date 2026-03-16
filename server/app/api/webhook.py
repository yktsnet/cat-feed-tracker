"""
cat-feed-tracker / server/app/api/webhook.py
LINE Webhook エンドポイント
"""

import os
import logging
from fastapi import APIRouter, Header, HTTPException, Request
from linebot.v3.webhook import WebhookParser
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.exceptions import InvalidSignatureError
from app.line.webhook import handle_message

logger = logging.getLogger(__name__)
router = APIRouter()

parser = WebhookParser(os.getenv("LINE_CHANNEL_SECRET", ""))


@router.post("/webhook/line")
async def line_webhook(
    request: Request,
    x_line_signature: str = Header(...),
):
    body = await request.body()
    body_text = body.decode("utf-8")

    try:
        events = parser.parse(body_text, x_line_signature)
    except InvalidSignatureError:
        logger.warning("invalid signature")
        raise HTTPException(status_code=400, detail="invalid signature")
    except Exception as e:
        logger.warning("webhook parse error: %s", e)
        # 検証リクエスト（空body）は正常に200を返す
        return {"status": "ok"}

    for event in events:
        if isinstance(event, MessageEvent) and isinstance(
            event.message, TextMessageContent
        ):
            handle_message(
                user_id=event.source.user_id,
                reply_token=event.reply_token,
                text=event.message.text,
            )

    return {"status": "ok"}
