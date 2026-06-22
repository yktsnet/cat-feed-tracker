"""
cat-feed-tracker / server/app/config.py
起動時に config/cats.yaml を読み込み、猫プロファイルリストを公開する。
ファイルが存在しない場合はエラーで起動失敗（デフォルト値は持たない）。
環境変数 TIMEZONE / NOTIFY_SLOTS もここで一元管理する。
"""

import os
from pathlib import Path
from zoneinfo import ZoneInfo
import yaml

# server/app/config.py -> server/app/ -> server/ -> プロジェクトルート
_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "cats.yaml"


def _load_cats() -> list[dict]:
    if not _CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"cats.yaml が見つかりません: {_CONFIG_PATH}\n"
            "プロジェクトルートに config/cats.yaml を作成してください。"
        )
    with _CONFIG_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    cats = data.get("cats", [])
    if not cats:
        raise ValueError("cats.yaml の cats リストが空です。")
    return cats


def _parse_notify_slots(raw: str) -> list[tuple[int, int]]:
    """'11:00,16:00,21:00' → [(11, 0), (16, 0), (21, 0)]"""
    result = []
    for s in raw.split(","):
        h, m = s.strip().split(":")
        result.append((int(h), int(m)))
    return result


def get_tz() -> ZoneInfo:
    """TIMEZONE 環境変数から ZoneInfo を返す（デフォルト: Asia/Tokyo）"""
    return ZoneInfo(os.getenv("TIMEZONE", "Asia/Tokyo"))


CAT_PROFILES: list[dict] = _load_cats()
TZ_NAME: str = os.getenv("TIMEZONE", "Asia/Tokyo")
NOTIFY_SLOTS: list[tuple[int, int]] = _parse_notify_slots(
    os.getenv("NOTIFY_SLOTS", "11:00,16:00,21:00")
)
