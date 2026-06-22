---
name: pr-workflow
description: ブランチ作成・実装・PR作成までの標準フロー
disable-model-invocation: true
---

以下の手順で issue を実行する。$ARGUMENTS に issue ファイルのパスを渡す。

**前提: Claude Code はコードを書いて PR を出すまでが担当。実行・確認・マージは user が行う。**

0. `context/conventions.md` を読む
1. issue ファイルを読む
2. `git status` で未コミットがあれば報告して止まる
3. `git checkout -b claude/{id}-{branch-slug}`（id と branch-slug は issue から取得）
4. 対象ファイルを読んで実装
5. issue の「確認」項目に従い静的チェックを実施する
   - `cd server && PYTHONPATH=. pytest`
   - 変更した `.py` に `python -m py_compile`
   - `pico/` 変更時は MicroPython 構文互換を目視確認
   - issue 固有の確認があればそれも実施
6. `git add {変更したファイル}`
   `git diff --name-only --cached` を実行する。
   出力が issue の「対象」フィールドと完全一致することを確認する。
   不一致があれば実装に戻り修正する。一致してから次に進む。
7. `git commit -m "{type}: {タイトル}"`
8. PR ボディを `.git/pr_body.md` に書き出し、同内容を `issues/done/{id}_{branch-slug}_pr.md` にもコピーする。
   `git add issues/done/{id}_{branch-slug}_pr.md` して `git commit -m "chore: add PR record {id}"` でコミットしてから PR を作成する。
   `.git/pr_body.md` の内容:
   ```
   ## 変更内容
   {issue の内容フィールドを展開}

   ## 静的確認結果
   {pytest の結果、py_compile の結果、issue の確認項目に対する結果}

   ## 検証手順
   {実装内容から判断して以下を記載する。該当しない項目は省略する}
   - API 変更の場合: curl や LINE での動作確認手順
   - DB スキーマ変更の場合: マイグレーション適用手順
   - pico 変更の場合: ファームウェア書き込み・動作確認手順
   ```
   `gh pr create --base main --title "{type}: {タイトル}" --body-file .git/pr_body.md`
9. PR の URL を出力して終了
   ```
   ✅ PR created: {URL}
   Next: 検証手順を実施 → gh pr merge {番号} --merge
   ```
