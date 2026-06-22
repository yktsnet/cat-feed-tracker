[🇯🇵 日本語](rich_menu.md) | [🇬🇧 English](rich_menu.en.md)

# LINE Rich Menu & Webhook Integration

This document describes the LINE Messaging API integration, rich menu button layout, and related operation specifications.

---

## 1. LINE Messaging API Setup

1. Log in to the [LINE Developers Console](https://developers.line.biz/), and create a provider and a Messaging API channel.
2. Enable Webhook in the channel settings and set the URL to `https://your-domain.example.com/api/webhook/line`.
3. Obtain the channel secret (`LINE_CHANNEL_SECRET`) and long-lived channel access token (`LINE_CHANNEL_ACCESS_TOKEN`), and set them in the server's `.env` file.

---

## 2. Rich Menu Button Actions

The rich menu uses a 2×2 grid layout. Tapping each area automatically sends a specific text message from the user, which the server processes via the Webhook.

| Button | Sent Text | Response |
|---|---|---|
| **Today's Log** | `今日の記録` | Returns a list of today's feeding events so far. |
| **Average** | `平均` | Returns the weekly average for the last 4 weeks and the monthly average for the last 3 months (counting only days with feeding events). |
| **Weight** | `体重` | Starts a two-step dialog: select a cat (cats defined in `config/cats.yaml` are shown numbered) then enter the weight. After recording, displays the last 5 weight entries and feeding averages. |
| **Settings** | `設定` | Shows the current notification on/off status and daily alert threshold, with instructions for changing them. |

### Additional Text Commands
- **`通知オン`** / **`通知オフ`**: Directly toggle notifications on/off.
- **`上限変更`**: Starts a dialog to change the daily alert threshold (waits for numeric input).
- **`キャンセル`**: Exits any pending dialog state and cancels the operation.

---

## 3. Rich Menu Registration

Run the provided `setup_rich_menu.py` script to upload a 2×2 rich menu image and configure actions for the LINE official account.

### How to Run

```bash
# NixOS environment
nix-shell -p python3Packages.pillow --run "python server/scripts/setup_rich_menu.py"

# Other environments
pip install Pillow
LINE_CHANNEL_ACCESS_TOKEN=<YOUR_CHANNEL_ACCESS_TOKEN> python server/scripts/setup_rich_menu.py
```

---

## 4. Sample Weight Data

Sample weight records that can be imported into the database for testing and display verification.

```sql
INSERT INTO cat_weights (cat_id, weight_kg, recorded_at) VALUES
  (1, 4.2, '2026-01-15'), (1, 4.3, '2026-02-01'), (1, 4.1, '2026-02-15'),
  (1, 4.4, '2026-03-01'), (1, 4.3, '2026-03-15'),  -- Tama
  (2, 3.8, '2026-01-15'), (2, 3.9, '2026-02-01'), (2, 3.7, '2026-02-15'),
  (2, 3.8, '2026-03-01'), (2, 3.9, '2026-03-15'),  -- Mike
  (3, 5.1, '2026-01-15'), (3, 5.0, '2026-02-01'), (3, 5.2, '2026-02-15'),
  (3, 5.1, '2026-03-01'), (3, 5.3, '2026-03-15');  -- Kuro
```
