# Instagram 自動投稿ワークフロー（@kos.odatepapa）

最終更新: 2026-10-08
バズ設計は `docs/playbook.md` を必ず併読すること。
このファイルの「投稿済み」は毎回の投稿後に追記し、投稿と同じコミットで push する。

## アカウント
- @kos.odatepapa「子育てパパ」/ プロアカウント
- ターゲット: 0〜3歳の子を持つ親
- 方針: エビデンスのある公的一次情報のみ。推測・体験談ベースの断定はしない
- 人の確認なしで自動公開される。原典で確認できない数字・文言は載せない

## 全体の流れ（クラウド・全自動）
1. テーマ選定（下の「投稿済み」とローテーションで重複回避）
2. WebSearch / WebFetch で一次情報を裏取りし、出典URLを記録
3. `posts/<YYYYMMDD>-<slug>/` の外（作業用 `work/<slug>/`）に `content.json` を作る
4. `python3 scripts/gen_images.py work/<slug>` で Gemini 挿絵を生成（失敗しても続行）
5. `python3 scripts/render.py work/<slug>` → `work/<slug>/slides/NN.png`
6. コンタクトシート1枚で目視確認（1〜2字だけの行、はみ出しがあれば直して再生成）
7. `work/<slug>/caption.txt` と `sources.txt`（1行1URL）を書く
8. 「投稿済み」に1行追記 → `python3 scripts/push_post.py work/<slug>/slides <slug> --caption work/<slug>/caption.txt --sources work/<slug>/sources.txt`
9. main への push で GitHub Actions が出典URLを確認し Instagram に投稿する

## content.json のスライド型
- `cover`: kicker / title[] / sub / swipe / source / illust_prompt
- `stat`: label / big / title[] / body / source / illust_prompt
- `point`: no / title[] / body[] / source / illust_prompt
- `closing`: title[] / body[] / sources[]

`illust_prompt` は英語で被写体だけを書く（例: "a dad checking a calendar with a toddler on his lap"）。
配色・画風・文字禁止は `gen_images.py` が自動で付ける。表紙・stat・point に入れ、closing には入れない。
render.py は日本語の禁則処理（行頭禁止文字、数字＋単位、英数字トークンの非分割）を実装済み。
フォント: Noto Sans CJK JP。配色: クリーム #FFF9F0 / 濃紺 #1B3657 / オレンジ #FF7B54 / ティール #3E9B9E。

### 折り返しの注意
`point` の body は20字、`closing` の body は20字、`stat` の body は22字で折り返す。
1項目を20字以内に収めると2行割れを防げる。コンタクトシートで「い」「OK」など1〜2字だけの行が出たら短くする。
`cover` / `point` の title は配列で渡すと改行位置を固定でき、事故が少ない。

### レイアウト実測メモ
- `point`: 丸番号あり＋title2行＋body3項目（各1行）が上限。挿絵は本文下の余白に入る（余白220px未満なら自動で省略）
- `closing`: title2行＋body6項目まで収まる。sources は4件までが安全
- 10枚構成（cover / stat / point×6 / closing×2）が収まりが良い

## 発信テーマのローテーション
1. 事故防止（窒息・誤飲・転落・やけど・チャイルドシート）
2. 発達・生活（睡眠、イヤイヤ期、トイトレ、食事）
3. 関東の公園情報（駐車場・トイレ・遊具・授乳室）— 自治体公式サイトで裏取りし「投稿日時点の情報」と明記
4. 季節・制度（予防接種、感染症、手当・助成）
5. パパあるある風刺（エビデンス縛りを外してよいが事実は曲げない）

朝と夜で同じカテゴリを続けない。

### 公園回の裏取りメモ（2026-10-06に判明）
- 複数公園を1投稿に並べると、授乳室・駐車場の4項目を公式で裏取りできない公園が出て失速する
- 民間まとめサイトしかヒットしない公園は採用しない
- **1公園を深掘りする構成のほうが、全項目を公式ソースで固められる**
- 国営公園（昭和記念・武蔵丘陵森林・ひたち海浜）は公式サイトに「お子様をお連れの方へ」系ページがあり裏取りしやすい

### 裏取りで使える一次情報の入口（2026-10-07 追記）
- 消費者庁「子ども安全メール from 消費者庁」バックナンバー: `caa.go.jp/policies/policy/consumer_safety/child/project_001/mail/<yyyymmdd>/` — 事故事例と予防策が短文で揃う。やけど・誤飲・転落のネタ元として優秀
- 政府広報オンライン `gov-online.go.jp/useful/article/` — 件数・温度・時間などの数字が拾える
- 東京都こどもセーフティプロジェクト `kodomosafetypj.metro.tokyo.lg.jp` — 東京消防庁の救急搬送統計を引用しており、stat スライドの数字に使いやすい

### 制度回で使える一次情報（2026-10-08 追記）
- こども家庭庁「児童手当制度のご案内」 https://www.cfa.go.jp/policies/kokoseido/jidouteate/annai — 支給額・支給月・申請期限が原文で取れる
- こども家庭庁「こども誰でも通園制度」 https://www.daretsu.cfa.go.jp/ — 対象年齢・利用時間
- 厚生労働省 出生後休業支援給付金 https://www.mhlw.go.jp/content/11600000/001461102.pdf
- 厚生労働省 育児時短就業給付金 https://www.mhlw.go.jp/content/11600000/001395102.pdf

## 投稿済み
- 2026-10-06 `2026-10-06_chissoku` 窒息・誤飲を防ぐ6つの鉄則（出典: 消費者庁ほか）／キャプション未反映のまま公開、要修正
- 2026-10-06 `2026-10-06_suimin` 0〜3歳の睡眠と画面時間（カテゴリ: 発達・生活／出典: 厚労省 睡眠ガイド2023、厚労省 健康情報「こどもの睡眠」、WHO 2019）／クラウド生成・ユーザー手動投稿
- 2026-10-06 `2026-10-06_showakinen` 昭和記念公園 0〜3歳連れガイド（カテゴリ: 関東の公園情報／出典: 国営昭和記念公園 公式サイト お子様をお連れの方へ・各種料金・アクセス・よくある質問・こどもの森／2026-10-06時点）／クラウド生成・ユーザー手動投稿
- 2026-10-07 夜 `2026-10-07_yakedo` 0〜3歳のやけど予防6つ＋応急手当（カテゴリ: 事故防止／出典: 消費者庁 子ども安全メール、政府広報オンライン「家の中の思わぬ危険。乳幼児のやけど事故にご注意を！」、東京都こどもセーフティプロジェクト＝東京消防庁 令和5年 救急搬送データ）／クラウド生成・ユーザー手動投稿
- 2026-10-07 朝 `2026-10-07_seido-0to3` 0〜3歳で使える国の制度6つ（カテゴリ: 季節・制度／出典: こども家庭庁 児童手当制度のご案内、厚労省 出生後休業支援給付金、厚労省 育児時短就業給付金、こども家庭庁 こども誰でも通園制度）／2026-10-08 00:57 JST GitHub経由で自動投稿（media_id 18428581219146604）
