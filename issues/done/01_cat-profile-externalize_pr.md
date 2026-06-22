## 変更内容

ハードコードされた猫名・絵文字・番号判定を設定ファイルに外部化し、任意の猫数で動作するようにする（OSS化の最低条件）。

- `config/cats.yaml`（新規）: 猫プロファイル（name / emoji）のリストを定義する設定ファイル。ユーザーが自分の猫情報に書き換えるだけでよい。
- `server/app/config.py`（新規）: 起動時に `config/cats.yaml` を読み込み `CAT_PROFILES: list[dict]` として公開。ファイル不在・空リストはエラーで起動失敗（デフォルト値なし）。
- `server/app/line/webhook.py`: `CAT_NAMES` / `CAT_EMOJI` を `CAT_PROFILES` から動的構築。体重メニューテキストと猫番号判定を猫リストの長さに追従させた。
- `server/requirements.txt`: `pyyaml==6.0.2` を追加。

## 静的確認結果

```
$ python -m py_compile server/app/config.py
config.py OK

$ python -m py_compile server/app/line/webhook.py
webhook.py OK

$ cd server && PYTHONPATH=. pytest
9 passed, 1 warning in 1.68s
```

## 検証手順

- サーバー起動後に LINE で「体重」と送信し、猫の選択肢が `config/cats.yaml` の内容で表示されることを確認する
- 猫番号を選択して体重数値を入力し、記録完了メッセージに正しい猫名・絵文字が表示されることを確認する
- `config/cats.yaml` の猫数を変えてサーバーを再起動し、体重メニューの選択肢が追従することを確認する
