"""content.json の "illust_prompt" から Gemini で挿絵を生成する。

使い方:
    python3 scripts/gen_images.py <post_dir>

- "illust_prompt" を持つスライドごとに 1:1 の画像を生成し <post_dir>/img/NN.png に保存
- 成功したスライドには "illust": "NN.png" を書き込む（render.py が配置する）
- 失敗したスライドは挿絵なしのまま続行する（投稿自体は止めない）

環境変数:
    GEMINI_API_KEY      未設定でもよい（実行環境のプロキシが注入する場合）
    GEMINI_IMAGE_MODEL  既定 gemini-3.1-flash-image
"""

from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path

import requests

MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image")
ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

# アカウントの配色に合わせた共通スタイル。文字はスライド側で描くので画像には入れない
STYLE = (
    "Warm, friendly flat vector illustration for a Japanese parenting Instagram post. "
    "Solid cream background (#FFF9F0) filling the whole canvas. Palette: navy #1B3657, "
    "orange #FF7B54, teal #3E9B9E. Simple shapes, soft rounded lines, generous margins, "
    "one clear focal subject. Absolutely no text, no letters, no numbers, no labels, "
    "no logos, no watermark."
)


def generate(prompt: str) -> bytes:
    headers = {"Content-Type": "application/json"}
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        headers["x-goog-api-key"] = key
    body = {
        "contents": [{"parts": [{"text": f"{prompt}\n\n{STYLE}"}]}],
        "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "1:1"}},
    }
    r = requests.post(ENDPOINT, json=body, headers=headers, timeout=180)
    data = r.json()
    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code} {data.get('error', {}).get('message', '')[:200]}")
    for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
        if "inlineData" in part:
            return base64.b64decode(part["inlineData"]["data"])
    raise RuntimeError("画像が返らなかった")


def main(post_dir: str) -> int:
    d = Path(post_dir)
    cj = d / "content.json"
    content = json.loads(cj.read_text(encoding="utf-8"))
    out = d / "img"
    out.mkdir(exist_ok=True)
    ok = ng = 0
    for i, slide in enumerate(content["slides"], 1):
        prompt = slide.get("illust_prompt")
        if not prompt:
            continue
        name = f"{i:02d}.png"
        try:
            (out / name).write_bytes(generate(prompt))
            slide["illust"] = name
            ok += 1
        except Exception as e:  # 挿絵の失敗で投稿を止めない
            slide.pop("illust", None)
            ng += 1
            print(f"[warn] slide {i}: {e}", file=sys.stderr)
    cj.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"挿絵 成功{ok} / 失敗{ng}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
