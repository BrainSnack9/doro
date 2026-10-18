#!/usr/bin/env python3
"""인스타 카드뉴스(캐러셀) 이미지 생성기. JSON 스펙 → 1080x1350 JPG 여러 장.

  python3 haru/tools/cards.py <spec.json>
spec: {"out_dir": "haru/hub/static/cards/<slug>", "brand": "하루 | AI 자취생", "cards": [
  {"type": "cover", "photo": "<jpg 경로>", "kicker": "...", "title": "...", "sub": "..."},
  {"type": "list",  "kicker": "...", "title": "...", "items": ["...", "..."]},
  {"type": "stats", "kicker": "...", "title": "...", "stats": [["94%", "4점 이상"], ...]},
  {"type": "end",   "kicker": "...", "title": "...", "lines": ["...", "..."], "note": "고지"}
]}
팔레트는 허브와 같다(종이색 배경, 잉크색 글자, 노란 마커). 글꼴 Pretendard. 사진 카드는 얼굴을 가리지 않도록 글자는 사진 아래 띠에만 둔다.
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
PAPER, PAPER_DEEP, INK, SOFT, MARKER = (238, 240, 234), (227, 230, 221), (28, 36, 48), (85, 96, 108), (246, 231, 90)
FONT_DIR = Path.home() / "Library" / "Fonts"
M = 84  # 여백


def font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / f"Pretendard-{weight}.otf"), size)


def wrap(draw: ImageDraw.ImageDraw, text: str, f: ImageFont.FreeTypeFont, width: int) -> list[str]:
    """글자 단위 줄바꿈(한글). 공백이 있으면 공백 우선."""
    lines: list[str] = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split(" "):
            cand = (cur + " " + word).strip()
            if draw.textlength(cand, font=f) <= width:
                cur = cand; continue
            if cur:
                lines.append(cur)
            cur = word
            while draw.textlength(cur, font=f) > width:  # 한 단어가 너무 길면 글자 단위로
                k = len(cur)
                while k > 1 and draw.textlength(cur[:k], font=f) > width:
                    k -= 1
                lines.append(cur[:k]); cur = cur[k:]
        lines.append(cur)
    return lines


def text_block(draw: ImageDraw.ImageDraw, xy: tuple, text: str, f: ImageFont.FreeTypeFont, width: int, fill=INK, leading: float = 1.35) -> int:
    x, y = xy
    lh = int(f.size * leading)
    for ln in wrap(draw, text, f, width):
        draw.text((x, y), ln, font=f, fill=fill); y += lh
    return y


def header(draw: ImageDraw.ImageDraw, brand: str, idx: int, total: int, kicker: str = "") -> int:
    f = font("Medium", 30)
    draw.text((M, M), brand, font=f, fill=SOFT)
    pg = f"{idx}/{total}"
    draw.text((W - M - draw.textlength(pg, font=f), M), pg, font=f, fill=SOFT)
    y = M + 70
    if kicker:
        fk = font("SemiBold", 34)
        tw = draw.textlength(kicker, font=fk)
        draw.rounded_rectangle((M, y, M + tw + 36, y + 56), radius=28, fill=MARKER)
        draw.text((M + 18, y + 8), kicker, font=fk, fill=INK)
        y += 56
    return y + 40


def footer(draw: ImageDraw.ImageDraw, note: str) -> None:
    if not note:
        return
    f = font("Regular", 26)
    y = H - M - 26 * 2
    for ln in wrap(draw, note, f, W - 2 * M)[-2:]:
        draw.text((M, y), ln, font=f, fill=SOFT); y += 36


def card_cover(c: dict, brand: str, idx: int, total: int) -> Image.Image:
    im = Image.new("RGB", (W, H), PAPER)
    photo = Image.open(c["photo"]).convert("RGB")
    ph = 790
    scale = max(W / photo.width, ph / photo.height)
    photo = photo.resize((round(photo.width * scale), round(photo.height * scale)))
    left = (photo.width - W) // 2; top = max(0, (photo.height - ph) // 3)  # 얼굴이 위쪽에 있으니 위를 살린다
    im.paste(photo.crop((left, top, left + W, top + ph)), (0, 0))
    d = ImageDraw.Draw(im)
    y = ph + 56
    if c.get("kicker"):
        fk = font("SemiBold", 32); tw = d.textlength(c["kicker"], font=fk)
        d.rounded_rectangle((M, y, M + tw + 36, y + 54), radius=27, fill=MARKER); d.text((M + 18, y + 7), c["kicker"], font=fk, fill=INK); y += 54 + 28
    limit = H - M - 28 - 24  # 맨 아래 브랜드 줄 위까지만 쓴다. 넘치면 글자를 줄이고, 그래도 넘치면 부제를 줄인다 (2026-10-18 오너 지적: 표지 글이 브랜드명과 겹침)
    for title_size, sub_size in ((58, 32), (52, 30), (46, 28), (42, 26)):
        ft, fs = font("Bold", title_size), font("Regular", sub_size)
        ty = y + len(wrap(d, c["title"], ft, W - 2 * M)) * int(title_size * 1.2)
        sub_lines = wrap(d, c["sub"], fs, W - 2 * M) if c.get("sub") else []
        sy = ty + 14 + len(sub_lines) * int(sub_size * 1.3)
        if sy <= limit:
            break
    while sub_lines and ty + 14 + len(sub_lines) * int(sub_size * 1.3) > limit:
        sub_lines = sub_lines[:-1]
    y = text_block(d, (M, y), c["title"], ft, W - 2 * M, leading=1.2)
    yy = y + 14
    for ln in sub_lines:
        d.text((M, yy), ln, font=fs, fill=SOFT); yy += int(sub_size * 1.3)
    f = font("Medium", 28); d.text((W - M - d.textlength(f"{idx}/{total}", font=f), H - M - 28), f"{idx}/{total}", font=f, fill=SOFT)
    d.text((M, H - M - 28), brand, font=f, fill=SOFT)
    return im


def card_list(c: dict, brand: str, idx: int, total: int) -> Image.Image:
    im = Image.new("RGB", (W, H), PAPER); d = ImageDraw.Draw(im)
    y = header(d, brand, idx, total, c.get("kicker", ""))
    y = text_block(d, (M, y), c["title"], font("Bold", 58), W - 2 * M, leading=1.25) + 36
    fb = font("Regular", 40)
    for it in c.get("items", []):
        d.rounded_rectangle((M, y + 16, M + 18, y + 34), radius=9, fill=INK)
        y = text_block(d, (M + 48, y), it, fb, W - 2 * M - 48, leading=1.4) + 26
    footer(d, c.get("note", ""))
    return im


def card_stats(c: dict, brand: str, idx: int, total: int) -> Image.Image:
    im = Image.new("RGB", (W, H), PAPER); d = ImageDraw.Draw(im)
    y = header(d, brand, idx, total, c.get("kicker", ""))
    y = text_block(d, (M, y), c["title"], font("Bold", 58), W - 2 * M, leading=1.25) + 40
    fbig, fsm = font("ExtraBold", 96), font("Regular", 34)
    for big, small in c.get("stats", []):
        d.rounded_rectangle((M, y, W - M, y + 180), radius=22, fill=PAPER_DEEP)
        d.text((M + 36, y + 30), big, font=fbig, fill=INK)
        d.text((M + 36 + d.textlength(big, font=fbig) + 28, y + 86), small, font=fsm, fill=SOFT)
        y += 180 + 24
    if c.get("sub"):
        text_block(d, (M, y + 10), c["sub"], font("Regular", 34), W - 2 * M, fill=SOFT)
    footer(d, c.get("note", ""))
    return im


def card_end(c: dict, brand: str, idx: int, total: int) -> Image.Image:
    im = Image.new("RGB", (W, H), INK); d = ImageDraw.Draw(im)
    f = font("Medium", 30); d.text((M, M), brand, font=f, fill=(170, 176, 184))
    d.text((W - M - d.textlength(f"{idx}/{total}", font=f), M), f"{idx}/{total}", font=f, fill=(170, 176, 184))
    y = M + 120
    if c.get("kicker"):
        fk = font("SemiBold", 34); tw = d.textlength(c["kicker"], font=fk)
        d.rounded_rectangle((M, y, M + tw + 36, y + 56), radius=28, fill=MARKER); d.text((M + 18, y + 8), c["kicker"], font=fk, fill=INK); y += 56 + 40
    y = text_block(d, (M, y), c["title"], font("Bold", 64), W - 2 * M, fill=PAPER, leading=1.25) + 30
    for ln in c.get("lines", []):
        y = text_block(d, (M, y), ln, font("Regular", 38), W - 2 * M, fill=(200, 205, 212), leading=1.4) + 18
    if c.get("note"):
        fn = font("Regular", 26); yy = H - M - 36 * 3
        for ln in wrap(d, c["note"], fn, W - 2 * M)[-3:]:
            d.text((M, yy), ln, font=fn, fill=(150, 156, 165)); yy += 36
    return im


RENDER = {"cover": card_cover, "list": card_list, "stats": card_stats, "end": card_end}


def build(spec: dict) -> list[Path]:
    out = Path(spec["out_dir"]); out.mkdir(parents=True, exist_ok=True)
    cards = spec["cards"]; paths = []
    for i, c in enumerate(cards, 1):
        im = RENDER[c["type"]](c, spec.get("brand", "하루 | AI 자취생"), i, len(cards))
        p = out / f"{i}.jpg"; im.save(p, "JPEG", quality=88, optimize=True); paths.append(p)
    return paths


if __name__ == "__main__":
    for p in build(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))):
        print(p)
