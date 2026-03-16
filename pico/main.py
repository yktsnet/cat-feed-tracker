"""
cat-feed-tracker / pico/main.py
Pico W: リードスイッチ検知 → VPS へイベント送信

接続:
  - GP14 : リードスイッチ（GND と短絡でLOW = 閉状態）
  - 内蔵プルアップ使用

状態:
  - LOW  = 棚が閉じている（磁石がリードスイッチに近い）
  - HIGH = 棚が開いた → 給餌イベント

secrets.py（Pico W本体のみ・dotfiles非管理）:
  WIFI_SSID, WIFI_PASSWORD, SERVER_URL, DEVICE_TOKEN
"""

import network
import ntptime
import urequests
import ujson
import utime
import machine
from machine import Pin
from secrets import WIFI_SSID, WIFI_PASSWORD, SERVER_URL, DEVICE_TOKEN

PIN_SWITCH = 14
DEBOUNCE_MS = 200
COOLDOWN_SEC = 30
RETRY_MAX = 3
RETRY_WAIT_MS = 2000

switch = Pin(PIN_SWITCH, Pin.IN, Pin.PULL_UP)
last_open_time = 0


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        return True
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    for _ in range(20):
        if wlan.isconnected():
            print("WiFi connected:", wlan.ifconfig()[0])
            return True
        utime.sleep(1)
    print("WiFi connect failed")
    return False


def sync_ntp():
    try:
        ntptime.settime()
        print("NTP synced:", utime.localtime())
    except Exception as e:
        print("NTP sync failed (continuing):", e)


def send_event(sent_at_iso: str) -> bool:
    headers = {
        "Authorization": "Bearer " + DEVICE_TOKEN,
        "Content-Type": "application/json",
    }
    payload = ujson.dumps({"sent_at": sent_at_iso})
    for attempt in range(1, RETRY_MAX + 1):
        try:
            res = urequests.post(SERVER_URL, data=payload, headers=headers)
            status = res.status_code
            res.close()
            if status in (200, 201):
                print("event sent ok:", sent_at_iso)
                return True
            print("server error:", status, "attempt", attempt)
        except Exception as e:
            print("send error:", e, "attempt", attempt)
        if attempt < RETRY_MAX:
            utime.sleep_ms(RETRY_WAIT_MS)
    print("send failed after", RETRY_MAX, "attempts")
    return False


def iso_now() -> str:
    t = utime.localtime()
    return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(
        t[0], t[1], t[2], t[3], t[4], t[5]
    )


def main():
    global last_open_time
    if not connect_wifi():
        utime.sleep(10)
        machine.reset()

    sync_ntp()

    prev_state = switch.value()
    last_open_time = utime.time()  # 起動直後はクールダウン扱い（誤送信防止）
    print(
        "cat-feed-tracker started. initial state:", "OPEN" if prev_state else "CLOSED"
    )

    while True:
        current_state = switch.value()
        if prev_state == 0 and current_state == 1:
            utime.sleep_ms(DEBOUNCE_MS)
            if switch.value() == 1:
                now = utime.time()
                if now - last_open_time >= COOLDOWN_SEC:
                    last_open_time = now
                    print("shelf opened → sending event")
                    send_event(iso_now())
                else:
                    print("cooldown active, skip")
        prev_state = current_state
        utime.sleep_ms(50)


main()
