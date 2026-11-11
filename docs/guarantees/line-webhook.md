# line-webhook

| 保証 | 対応テスト |
|---|---|
| `POST /api/webhook/line` は `X-Line-Signature` の検証に失敗すると 400 で `{"detail": "invalid signature"}` を返す | `test_line_webhook_invalid_signature` |
| `POST /api/webhook/line` は署名の検証以外の理由で本文を解釈できなくても 200 で `{"status": "ok"}` を返す | `test_line_webhook_parse_error_returns_ok` |
| `POST /api/webhook/line` は `LINE_CHANNEL_SECRET` で正しく署名されたテキストメッセージを受けると 200 で `{"status": "ok"}` を返す | `test_line_webhook_valid_signature_dispatches_to_handle_message` |
| `POST /api/webhook/line` は正しく署名されたテキストメッセージの送信者・返信トークン・本文を `handle_message` に1回渡す | `test_line_webhook_valid_signature_dispatches_to_handle_message` |
