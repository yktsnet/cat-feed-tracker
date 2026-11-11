# notify-message

## 当日の記録

| 保証 | 対応テスト |
|---|---|
| `build_today_message()` は当日のイベントがあれば「今日の記録」を含む本文を返す | `test_build_today_message` |
| `build_today_message()` は各イベントの時刻を `HH:MM` で並べる | `test_build_today_message` |
| `build_today_message()` は2件目以降の時刻に直前からの経過を `+N時間M分` で添える | `test_build_today_message` |
| `build_today_message()` は末尾に「本日計N回」を含む | `test_build_today_message` |
| `build_today_message()` は当日のイベントが無ければ `None` を返す | `test_build_today_message_no_events_returns_none` |
| `build_today_message()` は時刻を `TIMEZONE` 環境変数のタイムゾーンで表す | `test_build_today_message_respects_timezone_env` |

## 時間帯ごとの給餌まとめ

| 保証 | 対応テスト |
|---|---|
| `build_scheduled_message(slot_idx)` は見出しに「給餌まとめ（〜HH:MM）」をその時間帯の終わりの時刻で含む | `test_build_scheduled_message_morning`, `test_build_scheduled_message_afternoon` |
| `build_scheduled_message(slot_idx)` はその時間帯の終わりまでの当日のイベントの時刻を `HH:MM` で並べる | `test_build_scheduled_message_morning`, `test_build_scheduled_message_afternoon` |
| `build_scheduled_message(slot_idx)` は2件目以降の時刻に直前からの経過を `+N時間M分` で添える | `test_build_scheduled_message_afternoon` |
| `build_scheduled_message(slot_idx)` は末尾に「本日計N回」を含む | `test_build_scheduled_message_morning` |
| `build_scheduled_message(slot_idx)` は前の時間帯の境界をまたぐイベントの間に区切り線「─────────」を入れる | `test_build_scheduled_message_afternoon` |
| `build_scheduled_message(slot_idx)` は対象のイベントが無ければ `None` を返す | `test_build_scheduled_message_no_events_returns_none` |
