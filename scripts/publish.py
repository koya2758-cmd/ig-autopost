"""Instagram へカルーセル（または単画像）を投稿する。

使い方:
    python scripts/publish.py posts/20261007-sample [posts/... ...]

投稿ディレクトリの構成:
    posts/<YYYYMMDD-slug>/
        01.jpg, 02.jpg, ...   画像（ファイル名順に並ぶ。1〜10枚）
        caption.txt           キャプション本文
        sources.txt           出典URL（任意。1行1URL）
        posted.json           投稿済みマーカー（投稿後に自動生成）

環境変数:
    IG_ACCESS_TOKEN   Instagram ログイン方式の長期アクセストークン
    IG_USER_ID        Instagram プロアカウントのユーザーID
    GITHUB_REPOSITORY owner/repo（Actions が自動設定）
    GITHUB_SHA        画像URLを固定するコミット（Actions が自動設定）
    DRY_RUN           "1" なら API を呼ばずに検証だけ行う
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

API_BASE = "https://graph.instagram.com/v21.0"
IMAGE_EXTS = {".jpg", ".jpeg"}
MAX_ITEMS = 10
CAPTION_MAX = 2200
URL_RE = re.compile(r"https?://[^\s)>\]」』]+")
STATUS_POLL_SEC = 5
STATUS_POLL_MAX = 60


class PublishError(Exception):
    pass


def list_images(post_dir: Path) -> list[Path]:
    images = sorted(p for p in post_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    if not images:
        raise PublishError(f"{post_dir}: JPEG画像がない")
    if len(images) > MAX_ITEMS:
        raise PublishError(f"{post_dir}: 画像が{len(images)}枚。上限は{MAX_ITEMS}枚")
    return images


def read_caption(post_dir: Path) -> str:
    caption = (post_dir / "caption.txt").read_text(encoding="utf-8").strip()
    if not caption:
        raise PublishError(f"{post_dir}: caption.txt が空")
    if len(caption) > CAPTION_MAX:
        raise PublishError(f"{post_dir}: キャプションが{len(caption)}字。上限は{CAPTION_MAX}字")
    return caption


def collect_source_urls(post_dir: Path, caption: str) -> list[str]:
    urls = URL_RE.findall(caption)
    sources = post_dir / "sources.txt"
    if sources.exists():
        for line in sources.read_text(encoding="utf-8").splitlines():
            urls.extend(URL_RE.findall(line))
    return list(dict.fromkeys(u.rstrip(".,、。") for u in urls))


def check_urls_alive(urls: list[str]) -> None:
    """出典URLが1件でも死んでいたら投稿を止める。"""
    dead = []
    headers = {"User-Agent": "Mozilla/5.0 (ig-autopost source checker)"}
    for url in urls:
        try:
            r = requests.head(url, allow_redirects=True, timeout=15, headers=headers)
            # HEAD を拒否するサイトがあるため GET で再確認する
            if r.status_code >= 400:
                r = requests.get(url, allow_redirects=True, timeout=15, headers=headers, stream=True)
                r.close()
            if r.status_code >= 400:
                dead.append(f"{url} ({r.status_code})")
        except requests.RequestException as e:
            dead.append(f"{url} ({type(e).__name__})")
    if dead:
        raise PublishError("出典URLにアクセスできない:\n  " + "\n  ".join(dead))


def image_url(path: Path) -> str:
    repo = os.environ["GITHUB_REPOSITORY"]
    sha = os.environ["GITHUB_SHA"]
    return f"https://raw.githubusercontent.com/{repo}/{sha}/{path.as_posix()}"


def api(method: str, path: str, **params) -> dict:
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    r = requests.request(method, f"{API_BASE}/{path}", params=params, timeout=60)
    data = r.json() if r.content else {}
    if r.status_code >= 400 or "error" in data:
        err = data.get("error", {})
        raise PublishError(f"API {method} {path} 失敗: {err.get('message', r.text)}")
    return data


def wait_until_ready(container_id: str) -> None:
    for _ in range(STATUS_POLL_MAX):
        status = api("GET", container_id, fields="status_code").get("status_code")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            raise PublishError(f"コンテナ {container_id} が {status}")
        time.sleep(STATUS_POLL_SEC)
    raise PublishError(f"コンテナ {container_id} の処理がタイムアウト")


def publish(post_dir: Path, images: list[Path], caption: str) -> str:
    user_id = os.environ["IG_USER_ID"]
    if len(images) == 1:
        container = api("POST", f"{user_id}/media", image_url=image_url(images[0]), caption=caption)["id"]
    else:
        children = []
        for img in images:
            child = api("POST", f"{user_id}/media", image_url=image_url(img), is_carousel_item="true")["id"]
            wait_until_ready(child)
            children.append(child)
        container = api(
            "POST", f"{user_id}/media",
            media_type="CAROUSEL", children=",".join(children), caption=caption,
        )["id"]
    wait_until_ready(container)
    return api("POST", f"{user_id}/media_publish", creation_id=container)["id"]


def process(post_dir: Path, dry_run: bool) -> bool:
    """投稿したら True、スキップしたら False を返す。"""
    marker = post_dir / "posted.json"
    if marker.exists():
        print(f"[skip] {post_dir}: 投稿済み")
        return False

    images = list_images(post_dir)
    caption = read_caption(post_dir)
    urls = collect_source_urls(post_dir, caption)
    check_urls_alive(urls)
    print(f"[ok] {post_dir}: 画像{len(images)}枚 / 出典{len(urls)}件 確認済み")

    if dry_run:
        print(f"[dry-run] {post_dir}: 投稿しない")
        return False

    media_id = publish(post_dir, images, caption)
    marker.write_text(json.dumps({
        "media_id": media_id,
        "posted_at": datetime.now(timezone.utc).isoformat(),
        "commit": os.environ.get("GITHUB_SHA", ""),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[posted] {post_dir}: media_id={media_id}")
    return True


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: publish.py <post_dir> [<post_dir> ...]", file=sys.stderr)
        return 2
    dry_run = os.environ.get("DRY_RUN") == "1"
    failed = False
    for arg in argv:
        try:
            process(Path(arg), dry_run)
        except (PublishError, OSError) as e:
            print(f"[error] {e}", file=sys.stderr)
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
