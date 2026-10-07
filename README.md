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
4. `check_token.yml` が毎月1日にトークンの有効性を確認する（失効時は GitHub から通知）

## 初期設定

Facebook ログイン方式の Instagram API を使う。Instagram プロアカウントを Facebook ページにリンクしておく。

リポジトリの Settings → Secrets and variables → Actions に2つ登録する。

| 名前 | 中身 | 取得元 |
|---|---|---|
| `IG_ACCESS_TOKEN` | Facebook ページの無期限アクセストークン | グラフ API エクスプローラ → 長期ユーザートークン → `me/accounts` の `access_token` |
| `IG_USER_ID` | Instagram ビジネスアカウントID | `<ページID>?fields=instagram_business_account` の `id` |

必要な権限: `instagram_basic` `instagram_content_publish` `pages_show_list` `pages_read_engagement` `business_management`

## 前提

- リポジトリは公開（Public）にする。Instagram は `raw.githubusercontent.com` の画像URLを取得して投稿するため、非公開だと画像を取得できない
- 画像は JPEG のみ。アスペクト比は 0.8〜1.91（4:5〜1.91:1）

## 手動実行

Actions → publish → Run workflow で `post_dir` を指定する。`dry_run` をオンにすると検証だけ行う。
