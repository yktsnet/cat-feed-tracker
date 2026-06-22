"""
cat-feed-tracker / server/app/config.py
起動時に config/cats.yaml を読み込み、猫プロファイルリストを公開する。
ファイルが存在しない場合はエラーで起動失敗（デフォルト値は持たない）。
"""

from pathlib import Path
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


CAT_PROFILES: list[dict] = _load_cats()
