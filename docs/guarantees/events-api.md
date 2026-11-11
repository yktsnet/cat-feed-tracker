# events-api

| 保証 | 対応テスト |
|---|---|
| `POST /api/events` は `Authorization` のトークンが `DEVICE_TOKEN` と一致しなければ 401 で `{"detail": "unauthorized"}` を返す | `test_events_unauthorized` |
| `POST /api/events` はトークンが正しくてもデバイスが未登録なら 403 で `{"detail": "device not registered"}` を返す | `test_events_device_not_registered` |
| `POST /api/events` は同じデバイスの直近30秒以内にイベントがあれば 200 で `{"status": "duplicate", "ignored": true}` を返す | `test_events_duplicate` |
| `POST /api/events` は受け付けたとき 201 で `status: "ok"`・`event_id`・`received_at` を含むボディを返す | `test_events_success` |
| `POST /api/events` は受け付けたイベントを `feed_events` に1行記録する | `test_events_success_inserts_feed_event` |
