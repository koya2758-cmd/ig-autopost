"""生成した PNG を JPEG に変換し、投稿ディレクトリとして1コミットで push する。

使い方:
    python scripts/push_post.py <素材ディレクトリ> <slug> [--date YYYYMMDD] [--no-push]

素材ディレクトリ:
    *.png（ファイル名順にカルーセルの並びになる）
    caption.txt
    sources.txt（任意）

caption.txt の push が publish.yml を起動し、投稿が走る。
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
MAX_WIDTH = 1080
JPEG_QUALITY = 90
# Instagram フィード画像の許容アスペクト比（幅/高さ）
MIN_RATIO, MAX_RATIO = 4 / 5, 1.91


def to_jpeg(src: Path, dst: Path) -> None:
    with Image.open(src) as im:
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[-1])
            im = bg
        else:
            im = im.convert("RGB")
        if im.width > MAX_WIDTH:
            im = im.resize((MAX_WIDTH, round(im.height * MAX_WIDTH / im.width)), Image.LANCZOS)
        ratio = im.width / im.height
        if not MIN_RATIO - 0.01 <= ratio <= MAX_RATIO + 0.01:
            raise SystemExit(f"{src.name}: アスペクト比 {ratio:.2f} は Instagram の許容範囲外（0.8〜1.91）")
        im.save(dst, "JPEG", quality=JPEG_QUALITY, optimize=True)


def git(*args: str) -> None:
    subprocess.run(["git", "-C", str(REPO_ROOT), *args], check=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path)
    ap.add_argument("slug")
    ap.add_argument("--date", default=datetime.now().strftime("%Y%m%d"))
    ap.add_argument("--no-push", action="store_true")
    args = ap.parse_args()

    pngs = sorted(args.src.glob("*.png"))
    caption = args.src / "caption.txt"
    if not pngs:
        raise SystemExit(f"{args.src}: PNG がない")
    if len(pngs) > 10:
        raise SystemExit(f"{args.src}: PNG が{len(pngs)}枚。上限は10枚")
    if not caption.exists():
        raise SystemExit(f"{args.src}: caption.txt がない")

    dest = REPO_ROOT / "posts" / f"{args.date}-{args.slug}"
    if dest.exists():
        raise SystemExit(f"{dest} は既に存在する")
    dest.mkdir(parents=True)

    for i, png in enumerate(pngs, 1):
        to_jpeg(png, dest / f"{i:02d}.jpg")
    shutil.copy(caption, dest / "caption.txt")
    if (args.src / "sources.txt").exists():
        shutil.copy(args.src / "sources.txt", dest / "sources.txt")

    rel = dest.relative_to(REPO_ROOT).as_posix()
    git("add", rel)
    git("commit", "-m", f"post: {dest.name}")
    if not args.no_push:
        git("push")
    print(f"{rel}: 画像{len(pngs)}枚を{'コミット' if args.no_push else 'push'}した")
    return 0


if __name__ == "__main__":
    sys.exit(main())
