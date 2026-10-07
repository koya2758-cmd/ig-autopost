# ig-autopost

`caption.txt` を `main` に push すると、Instagram へ自動投稿する。

## 流れ

1. 素材（PNG＋`caption.txt`＋任意の `sources.txt`）を1フォルダに置く
2. `python scripts/push_post.py <素材フォルダ> <slug>` を実行
   - PNG を JPEG（幅1080px）に変換して `posts/<YYYYMMDD-slug>/` に保存し、1コミットで push する
3. `publish.yml` が起動する
   - 出典URLの死活を確認し、1件でも死んでいれば投稿を中止する
   - 画像1枚は単画像、2〜10枚はカルーセルで投稿する
   - `posted.json` を書き戻し、同じ投稿の二重実行を防ぐ
4. `refresh_token.yml` が毎月1日にアクセストークンを更新する

## 初期設定

リポジトリの Settings → Secrets and variables → Actions に3つ登録する。

| 名前 | 中身 |
|---|---|
| `IG_ACCESS_TOKEN` | Instagram ログイン方式の長期アクセストークン |
| `IG_USER_ID` | Instagram プロアカウントのユーザーID |
| `GH_PAT` | Fine-grained PAT（このリポジトリのみ、Secrets: Read and write）。トークン自動更新に使う |

## 前提

- リポジトリは公開（Public）にする。Instagram は `raw.githubusercontent.com` の画像URLを取得して投稿するため、非公開だと画像を取得できない
- 画像は JPEG のみ。アスペクト比は 0.8〜1.91（4:5〜1.91:1）

## 手動実行

Actions → publish → Run workflow で `post_dir` を指定する。`dry_run` をオンにすると検証だけ行う。
