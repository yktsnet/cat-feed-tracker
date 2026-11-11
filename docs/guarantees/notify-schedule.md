# notify-schedule

| 保証 | 対応テスト |
|---|---|
| 定時通知は `NOTIFY_SLOTS` の各時刻に、`TIMEZONE` のタイムゾーンで毎日送るよう登録される | `test_scheduler_registers_notify_slots_in_timezone` |
| 定時通知はその時間帯にイベントが無ければ「給餌まとめ（〜HH:MM）」と「この時間帯の記録はありません」を含む本文を送る | `test_send_scheduled_notify_empty_slot_message` |
| 定時通知は `notify_enabled` が `false` のとき送られない | `test_send_scheduled_notify_disabled_sends_nothing` |
| 上限アラートは `notify_enabled` が `false` のとき送られない | `test_send_alert_if_needed_disabled_sends_nothing` |
