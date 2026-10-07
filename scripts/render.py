# -*- coding: utf-8 -*-
"""Instagram carousel renderer (1080x1350). Burns Japanese text onto slides.
Usage: python3 render.py <post_dir>   # post_dir contains content.json
Outputs <post_dir>/slides/NN.png

各スライドに "illust": "<ファイル名>" があれば <post_dir>/img/<ファイル名> を
本文下の空きスペースに挿絵として配置する（scripts/gen_images.py が生成）。
"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1350
FB = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FR = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
IDX = 0

CREAM = (255, 249, 242)
INK = (27, 54, 83)
INK_SOFT = (90, 110, 132)
ACCENT = (255, 123, 84)
TEAL = (62, 155, 158)
WHITE = (255, 255, 255)

def font(bold, size):
    return ImageFont.truetype(FB if bold else FR, size, index=IDX)

def tw(d, s, f):
    b = d.textbbox((0, 0), s, font=f)
    return b[2] - b[0]

def fit(d, lines, bold, max_w, start, min_size=36):
    s = start
    while s > min_size:
        f = font(bold, s)
        if all(tw(d, l, f) <= max_w for l in lines):
            return f
        s -= 2
    return font(bold, min_size)

NO_START = "\u3002\u3001\uff09\u300d\u300f\uff01\uff1f\u30fb\u30fc\uff5e:\u2026"
NO_END = "\uff08\u300c\u300e"
ATOM = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#-.:%/")

def tokenize(text):
    toks, buf = [], ""
    for ch in text:
        if ch in ATOM:
            buf += ch
            continue
        if buf:
            toks.append(buf); buf = ""
        toks.append(ch)
    if buf:
        toks.append(buf)
    UNIT = "\u65e5\u5e74\u6708\u4eba\u6b73\u5186\u6642\u5206\u79d2\u500b\u679a\u56de\u5272\u5ea6\u756a\u4ef6"
    merged = []
    for t in toks:
        if merged and len(t) == 1 and t in UNIT and merged[-1][-1].isdigit():
            merged[-1] += t
        else:
            merged.append(t)
    return merged

def wrap(text, n):
    out, cur = [], ""
    for t in tokenize(text):
        if t == "\n":
            out.append(cur); cur = ""; continue
        if not cur:
            cur = t; continue
        if len(cur) + len(t) <= n:
            cur += t
        elif len(t) == 1 and t in NO_START:
            cur += t
        elif cur[-1] in NO_END:
            moved = cur[-1]
            out.append(cur[:-1])
            cur = moved + t
        else:
            out.append(cur); cur = t
    if cur:
        out.append(cur)
    return [l for l in out if l != ""]

def as_lines(v, n=16):
    if isinstance(v, list):
        return v
    return wrap(v, n) if v else []

def bg_image(path, alpha):
    """Full-bleed cover-fit background with white scrim."""
    im = Image.open(path).convert("RGB")
    r = max(W / im.width, H / im.height)
    im = im.resize((int(im.width * r + 1), int(im.height * r + 1)), Image.LANCZOS)
    x = (im.width - W) // 2
    y = (im.height - H) // 2
    im = im.crop((x, y, x + W, y + H))
    scrim = Image.new("RGB", (W, H), WHITE)
    return Image.blend(im, scrim, alpha)

def base(slide, assets):
    p = slide.get("bg")
    if p:
        fp = os.path.join(assets, p)
        if os.path.exists(fp):
            return bg_image(fp, slide.get("scrim", 0.55))
    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)
    d.ellipse((-220, -260, 360, 320), fill=(255, 237, 224))
    d.ellipse((760, 1020, 1340, 1600), fill=(226, 242, 241))
    return img

def pill(d, xy, text, f, fg, bg, pad=(26, 14)):
    x, y = xy
    w = tw(d, text, f) + pad[0] * 2
    h = f.size + pad[1] * 2
    d.rounded_rectangle((x, y, x + w, y + h), radius=h // 2, fill=bg)
    d.text((x + pad[0], y + pad[1] - 2), text, font=f, fill=fg)
    return h

def block(d, lines, f, x, y, lh, fill, center=False):
    for l in lines:
        px = (W - tw(d, l, f)) / 2 if center else x
        d.text((px, y), l, font=f, fill=fill)
        y += lh
    return y

def footer(d, slide):
    src = slide.get("source")
    if src:
        f = font(False, 30)
        d.text((80, H - 92), src, font=f, fill=INK_SOFT)

def draw_cover(img, s):
    d = ImageDraw.Draw(img)
    if s.get("kicker"):
        pill(d, (80, 170), s["kicker"], font(True, 36), WHITE, INK)
    lines = as_lines(s["title"], 11)
    f = fit(d, lines, True, W - 160, 118, 70)
    y = block(d, lines, f, 80, 300, int(f.size * 1.32), INK)
    if s.get("sub"):
        sl = as_lines(s["sub"], 20)
        fs = fit(d, sl, True, W - 160, 52, 36)
        d.rounded_rectangle((80, y + 30, 92, y + 30 + len(sl) * int(fs.size * 1.5)), radius=6, fill=ACCENT)
        block(d, sl, fs, 120, y + 30, int(fs.size * 1.5), INK_SOFT)
    f2 = font(True, 34)
    d.text((80, H - 150), s.get("swipe", "\u2192 \u30b9\u30ef\u30a4\u30d7"), font=f2, fill=ACCENT)
    footer(d, s)
    return y + (len(sl) * int(fs.size * 1.5) + 30 if s.get("sub") else 0), H - 170

def draw_stat(img, s):
    d = ImageDraw.Draw(img)
    if s.get("label"):
        pill(d, (80, 180), s["label"], font(True, 34), WHITE, TEAL)
    big = s.get("big", "")
    fb = fit(d, [big], True, W - 160, 300, 120)
    d.text(((W - tw(d, big, fb)) / 2, 300), big, font=fb, fill=ACCENT)
    y = 300 + int(fb.size * 1.15)
    tl = as_lines(s.get("title", ""), 14)
    ft = fit(d, tl, True, W - 160, 70, 48)
    y = block(d, tl, ft, 80, y + 20, int(ft.size * 1.45), INK, center=True)
    bl = as_lines(s.get("body", ""), 22)
    if bl:
        fbo = fit(d, bl, False, W - 200, 44, 32)
        y = block(d, bl, fbo, 100, y + 40, int(fbo.size * 1.7), INK_SOFT)
    footer(d, s)
    return y, H - 110

def draw_point(img, s):
    d = ImageDraw.Draw(img)
    y = 150
    if s.get("no"):
        f = font(True, 40)
        t = s["no"]
        d.ellipse((80, y, 80 + 86, y + 86), fill=ACCENT)
        d.text((80 + (86 - tw(d, t, f)) / 2, y + 18), t, font=f, fill=WHITE)
        y += 126
    tl = as_lines(s["title"], 13)
    ft = fit(d, tl, True, W - 160, 88, 54)
    y = block(d, tl, ft, 80, y, int(ft.size * 1.36), INK)
    d.rounded_rectangle((80, y + 34, 240, y + 42), radius=4, fill=TEAL)
    y += 92
    bl = s.get("body", [])
    bl = bl if isinstance(bl, list) else [bl]
    fb = font(False, 42)
    for item in bl:
        ls = as_lines(item, 20)
        d.ellipse((84, y + 16, 104, y + 36), fill=ACCENT)
        y = block(d, ls, fb, 128, y, int(fb.size * 1.5), INK)
        y += 26
    footer(d, s)
    return y, H - 110

def draw_closing(img, s):
    d = ImageDraw.Draw(img)
    tl = as_lines(s["title"], 12)
    ft = fit(d, tl, True, W - 160, 92, 56)
    y = block(d, tl, ft, 80, 190, int(ft.size * 1.36), INK, center=True)
    bl = s.get("body", [])
    bl = bl if isinstance(bl, list) else [bl]
    fb = font(True, 40)
    y += 40
    for item in bl:
        ls = as_lines(item, 20)
        y = block(d, ls, fb, 80, y, int(fb.size * 1.5), INK, center=True)
        y += 18
    srcs = s.get("sources", [])
    if srcs:
        fs = font(False, 28)
        d.text((80, H - 120 - len(srcs) * 40), "\u51fa\u5178", font=font(True, 30), fill=INK)
        yy = H - 80 - len(srcs) * 40
        for t in srcs:
            d.text((80, yy), "\u30fb" + t, font=fs, fill=INK_SOFT)
            yy += 40

def place_illust(img, path, top, bottom, max_side=460):
    """top〜bottom の空きに挿絵を中央配置する。空きが狭ければ置かない。"""
    space = bottom - top - 20
    side = min(max_side, space)
    if side < 220 or not os.path.exists(path):
        return
    il = Image.open(path).convert("RGB")
    r = side / max(il.width, il.height)
    il = il.resize((max(1, int(il.width * r)), max(1, int(il.height * r))), Image.LANCZOS)
    mask = Image.new("L", il.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, il.width, il.height), radius=36, fill=255)
    x = (W - il.width) // 2
    y = top + (space - il.height) // 2 + 10
    img.paste(il, (x, y), mask)

DRAW = {"cover": draw_cover, "stat": draw_stat, "point": draw_point, "closing": draw_closing}

def main(post_dir):
    with open(os.path.join(post_dir, "content.json"), encoding="utf-8") as f:
        data = json.load(f)
    assets = os.path.normpath(os.path.join(os.path.abspath(post_dir), data.get("assets_dir") or "../../assets"))
    out = os.path.join(post_dir, "slides")
    os.makedirs(out, exist_ok=True)
    for i, s in enumerate(data["slides"], 1):
        img = base(s, assets)
        area = DRAW[s.get("type", "point")](img, s)
        if s.get("illust") and area:
            place_illust(img, os.path.join(post_dir, "img", s["illust"]), area[0], area[1])
        p = os.path.join(out, f"{i:02d}.png")
        img.save(p, "PNG", optimize=True)
        print("ok", p)

if __name__ == "__main__":
    main(sys.argv[1])
