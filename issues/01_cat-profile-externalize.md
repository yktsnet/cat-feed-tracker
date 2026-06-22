## 猫プロファイルの外部化
id: 01
skill: pr-workflow
branch-slug: cat-profile-externalize
github_issue: 1
status: close
type: feat
対象: config/cats.yaml (新規), server/app/config.py (新規), server/app/line/webhook.py, server/requirements.txt
内容: ハードコードされた猫名・絵文字・番号判定を設定ファイルに外部化し、任意の猫数で動作するようにする（OSS化の最低条件）
確認: python -m py_compile で対象ファイルの構文確認、pytest 通過
---
## 背景

`webhook.py` に猫3匹分の名前・絵文字・番号判定がハードコードされており、他ユーザーが自分の猫で使うにはソースを直接編集する必要がある。

## ハードコード箇所

- `server/app/line/webhook.py:27-28` — `CAT_NAMES`, `CAT_EMOJI` 辞書
- `server/app/line/webhook.py:186-197` — 体重メニューテキスト（猫3匹固定）
- `server/app/line/webhook.py:326` — `text in ("1", "2", "3")` 猫番号判定が固定

## 設計

### `config/cats.yaml` (新規)

```yaml
cats:
  - name: タマ
    emoji: "🐱"
  - name: ミケ
    emoji: "🐈"
  - name: クロ
    emoji: "🐈‍⬛"
```

### `server/app/config.py` (新規)

- 起動時に `config/cats.yaml` を読み込み、猫リストを保持するモジュール
- `CAT_PROFILES: list[dict]` として公開
- ファイルが存在しない場合はエラーで起動失敗（デフォルト値は持たない）

### `server/app/line/webhook.py` の変更

- `CAT_NAMES`, `CAT_EMOJI` の直書きを `config.py` からの参照に置換
- 体重メニューテキストを猫リストから動的生成
- 番号判定を `range(1, len(cats)+1)` で動的化

## 実装順序

1. `config/cats.yaml` と `server/app/config.py` を作成
2. `webhook.py` の各ハードコード箇所を差し替え
3. テスト修正（モックに cats 設定を注入）
