"""릴스 조립기 v3 (2026-10-20, 자취 릴스 85편 분석 반영).

입력: 스펙 JSON → 세로 1080x1920 H.264/AAC mp4 (최대 90초).
- 장면(slides)은 절대 시각 start/end 로 둔다(내레이션 무음 구간에 맞춰 손으로 정한다).
- 장면 종류: "video"(힉스필드 5초 클립. 장면이 클립보다 길면 슬로모션으로 늘림, 짧으면 자름),
            "photo"(사진 꽉 채움 + 느린 줌), "product"(정사각 상품 사진을 흐린 배경 위 카드로 + 번호 배지).
- 자막(captions)은 절대 시각 t 에 바뀐다(말 속도에 맞춰 줄이 늘어나는 식). 줄 앞 '*' 는 노란 강조. 0.3초 페이드인.
- 내레이션(audio) 필수에 가깝고, 음악(music)은 선택(내레이션 아래 -20dB 정도).

스펙 예:
{
  "slug": "2026-10-20-blanket-3",
  "audio": "haru/assets/reels/x/voice.mp3", "music": null, "music_db": -20, "tail": 1.0,
  "bottom": "하루 · 리뷰 읽는 자취생",
  "slides": [
    {"kind": "video", "src": "haru/assets/reels/x/clip-bed.mp4", "start": 0, "end": 5.5},
    {"kind": "product", "src": "haru/assets/reels/x/detail-pattern.jpg", "start": 10.3, "end": 19.5, "badge": "1", "zoom": "in"},
    ...
  ],
  "captions": [
    {"t": 0.0, "lines": ["3만 원 전기요로", "*바닥난방 버틴 사람"], "size": 84, "pos": "upper"},
    ...
  ]
}
사용: python3 haru/tools/reels.py <spec.json> [--out <mp4>]
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
FONT_BOLD = ROOT / "haru" / "assets" / "fonts" / "SUITE-Bold.otf"
FONT_HEAVY = ROOT / "haru" / "assets" / "fonts" / "SUITE-Heavy.otf"
W, H = 1080, 1920
FPS = 30
MAX_SECONDS = 90.0
XFADE = 0.4
CAP_FADE = 0.3
YELLOW = (246, 231, 90)
INK = (43, 43, 43)
# "이쁜 감성" 테마(2026-10-20 오너: 밤티 나지 않게, 화려하고 예쁘게): 크림·피치·버터·세이지·라일락 파스텔 + 코랄 강조, 잘난체 제목, 손글씨 포인트
CREAM = (255, 247, 232); PEACH = (255, 214, 194); BUTTER = (255, 233, 168); SAGE = (207, 232, 213); LILAC = (228, 222, 255)
CORAL = (255, 122, 89); BROWN = (120, 84, 62); SOFT_INK = (64, 58, 54)
F_DISPLAY = ROOT / "haru" / "assets" / "fonts" / "Jalnan2.otf"
F_ROUND = ROOT / "haru" / "assets" / "fonts" / "Cafe24Supermagic-Bold-v1.0.otf"
F_HAND = ROOT / "haru" / "assets" / "fonts" / "KyoboHandwriting2025lyb.otf"
F_BODY = ROOT / "haru" / "assets" / "fonts" / "SUITE-Medium.otf"
F_BODY_B = ROOT / "haru" / "assets" / "fonts" / "SUITE-Bold.otf"


def _f(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def _font(size: int, heavy: bool = True) -> ImageFont.FreeTypeFont:
    return _f(F_DISPLAY if heavy else F_BODY_B, size)


def _resolve(p: str) -> Path:
    q = Path(p)
    return q if q.is_absolute() else ROOT / q


def _probe_dur(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def _shadow(size, box, radius, blur=22, alpha=90, off=(0, 14)):
    sh = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((box[0] + off[0], box[1] + off[1], box[2] + off[0], box[3] + off[1]), radius=radius, fill=(90, 60, 40, alpha))
    return sh.filter(ImageFilter.GaussianBlur(blur))


def _sparkle(d, cx, cy, r, color):
    pts = [(cx, cy - r), (cx + r * 0.28, cy - r * 0.28), (cx + r, cy), (cx + r * 0.28, cy + r * 0.28), (cx, cy + r), (cx - r * 0.28, cy + r * 0.28), (cx - r, cy), (cx - r * 0.28, cy - r * 0.28)]
    d.polygon(pts, fill=color)


def _heart(d, cx, cy, r, color):
    d.ellipse((cx - r, cy - r, cx, cy), fill=color); d.ellipse((cx, cy - r, cx + r, cy), fill=color)
    d.polygon([(cx - r, cy - r * 0.35), (cx + r, cy - r * 0.35), (cx, cy + r)], fill=color)


def _rotate(img, deg):
    return img.rotate(deg, resample=Image.BICUBIC, expand=True)


def _paste_center(canvas, img, cx, cy):
    canvas.alpha_composite(img, (cx - img.width // 2, cy - img.height // 2))


def caption_png(lines, size, pos, badge, path):
    """훅 자막: 살짝 기운 크림 카드 + 잘난체, '*' 줄은 코랄 형광펜 띠 위에 글자. 반짝이·하트 장식."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if not lines:
        img.save(path); return
    font = _f(F_DISPLAY, size)
    probe = ImageDraw.Draw(img)
    gap = int(size * 0.34)
    metrics = []
    for ln in lines:
        txt = ln.lstrip("*"); bb = probe.textbbox((0, 0), txt, font=font)
        metrics.append((txt, ln.startswith("*"), bb[2] - bb[0], bb[3] - bb[1], bb[0], bb[1]))
    cw = max(m[2] for m in metrics) + int(size * 1.1)
    ch = sum(m[3] for m in metrics) + gap * (len(metrics) - 1) + int(size * 0.9)
    card = Image.new("RGBA", (cw + 80, ch + 80), (0, 0, 0, 0))
    box = (40, 40, 40 + cw, 40 + ch)
    card.alpha_composite(_shadow(card.size, box, int(size * 0.5), blur=18, alpha=70, off=(0, 12)))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle(box, radius=int(size * 0.5), fill=CREAM + (250,), outline=PEACH + (255,), width=4)
    y = 40 + int(size * 0.45)
    for txt, hi, w, h, ox, oy in metrics:
        x = 40 + (cw - w) // 2
        if hi:
            d.rounded_rectangle((x - 10, y + int(h * 0.42), x + w + 10, y + h + 6), radius=12, fill=(255, 170, 150, 230))
        d.text((x - ox, y - oy), txt, font=font, fill=SOFT_INK + (255,))
        y += h + gap
    _sparkle(d, 30, 44, int(size * 0.26), BUTTER + (255,))
    _sparkle(d, card.width - 30, card.height - 44, int(size * 0.2), CORAL + (255,))
    _heart(d, card.width - 44, 36, int(size * 0.17), CORAL + (255,))
    card = _rotate(card, -2.2)
    cy = {"center": H // 2, "lower": int(H * 0.68), "upper": int(H * 0.24)}[pos]
    _paste_center(img, card, W // 2, cy)
    img.save(path)


def bottom_png(text, path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f2 = _f(F_HAND, 44)
    bb = d.textbbox((0, 0), text, font=f2)
    x = (W - (bb[2] - bb[0])) // 2
    d.rounded_rectangle((x - 26, H - 168, x + (bb[2] - bb[0]) + 26, H - 104), radius=30, fill=(255, 247, 232, 200))
    d.text((x - bb[0], H - 160 - bb[1]), text, font=f2, fill=BROWN + (255,))
    _heart(d, x + (bb[2] - bb[0]) + 44, H - 136, 10, CORAL + (255,))
    img.save(path)


CARD_W = 940
CARD_SLOT_GAP = 26


def card_png(card, path):
    """댓글 카드(감성 테마): 크림 카드 + 피치 테두리 + 말풍선 꼬리, 그라데이션 아바타, 둥근 서체 이름, 출처 칩. summary 는 버터색 + 손글씨 '하루 메모'. 살짝 기울여 스티커처럼."""
    kind = card.get("kind", "review")
    name = card.get("name", "구매자"); date = card.get("date", ""); text = card.get("text", "")
    body_font = _f(F_BODY, 40); name_font = _f(F_ROUND, 38); tag_font = _f(F_BODY_B, 27); date_font = _f(F_BODY, 28)
    probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    max_w = CARD_W - 64 - 100
    lines, cur = [], ""
    for ch in text:
        if probe.textbbox((0, 0), cur + ch, font=body_font)[2] > max_w and cur:
            lines.append(cur); cur = ch
        else:
            cur += ch
    if cur: lines.append(cur)
    lines = lines[:3]
    lh = 56
    h = 44 + 60 + 16 + lh * len(lines) + 24 + 44 + 36
    base = Image.new("RGBA", (CARD_W + 60, h + 60), (0, 0, 0, 0))
    box = (30, 30, 30 + CARD_W - 1, 30 + h - 1)
    base.alpha_composite(_shadow(base.size, box, 36, blur=20, alpha=80, off=(0, 12)))
    d = ImageDraw.Draw(base)
    fill, line = (BUTTER + (250,), (255, 206, 120, 255)) if kind == "summary" else (CREAM + (248,), PEACH + (255,))
    d.rounded_rectangle(box, radius=36, fill=fill, outline=line, width=4)
    d.polygon([(box[0] + 70, box[3] - 2), (box[0] + 110, box[3] - 2), (box[0] + 78, box[3] + 26)], fill=fill, outline=line)
    ox, oy = box[0], box[1]
    ar = 36; ax, ay = ox + 44 + ar, oy + 44 + 26
    grad = Image.new("RGBA", (ar * 2, ar * 2), (0, 0, 0, 0)); gd = ImageDraw.Draw(grad)
    c1, c2 = (SAGE, (150, 200, 170)) if kind == "summary" else (PEACH, CORAL)
    for i in range(ar * 2):
        t = i / (ar * 2 - 1); col = tuple(int(c1[k] + (c2[k] - c1[k]) * t) for k in range(3)) + (255,)
        gd.line([(0, i), (ar * 2, i)], fill=col)
    mask = Image.new("L", (ar * 2, ar * 2), 0); ImageDraw.Draw(mask).ellipse((0, 0, ar * 2 - 1, ar * 2 - 1), fill=255)
    base.paste(grad, (ax - ar, ay - ar), mask)
    d = ImageDraw.Draw(base)
    initial = "하" if kind == "summary" else (name[:1] or "구")
    bb = d.textbbox((0, 0), initial, font=name_font)
    d.text((ax - (bb[2] - bb[0]) // 2 - bb[0], ay - (bb[3] - bb[1]) // 2 - bb[1]), initial, font=name_font, fill=(255, 255, 255, 255))
    d.text((ox + 44 + ar * 2 + 18, oy + 44), name, font=name_font, fill=SOFT_INK)
    nw = d.textbbox((0, 0), name, font=name_font)[2]
    if date:
        d.text((ox + 44 + ar * 2 + 18 + nw + 14, oy + 44 + 10), date, font=date_font, fill=(150, 140, 130))
    y = oy + 44 + 60 + 16
    for ln in lines:
        d.text((ox + 44 + ar * 2 + 18, y), ln, font=body_font, fill=SOFT_INK); y += lh
    if kind == "summary":
        tag = "하루 메모"; chip, tcol, tf = (255, 255, 255, 230), BROWN, _f(F_HAND, 34)
    else:
        tag = card.get("source", "쿠팡 상품평"); chip, tcol, tf = SAGE + (255,), (40, 80, 55), tag_font
    tw = d.textbbox((0, 0), tag, font=tf)[2]
    d.rounded_rectangle((box[2] - 40 - tw - 28, box[3] - 44 - 38, box[2] - 40, box[3] - 36), radius=20, fill=chip)
    d.text((box[2] - 40 - tw - 14, box[3] - 44 - 34), tag, font=tf, fill=tcol)
    if kind != "summary":
        _heart(d, box[2] - 40 - tw - 50, box[3] - 44 - 16, 9, CORAL + (255,))
    deg = card.get("tilt", 1.4 if (sum(map(ord, name)) % 2 == 0) else -1.2)
    out = _rotate(base, deg)
    out.save(path)
    return out.width, out.height


def pill_png(text, path):
    """구간 머리말: 피치→버터 그라데이션 리본, 잘난체, 흰 테두리, 양끝 반짝이."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    f = _f(F_DISPLAY, 58)
    probe = ImageDraw.Draw(img)
    bb = probe.textbbox((0, 0), text, font=f)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    pw, ph = tw + 110, th + 54
    rib = Image.new("RGBA", (pw, ph), (0, 0, 0, 0)); rd = ImageDraw.Draw(rib)
    for i in range(pw):
        t = i / max(1, pw - 1); col = tuple(int(PEACH[k] + (BUTTER[k] - PEACH[k]) * t) for k in range(3)) + (255,)
        rd.line([(i, 0), (i, ph)], fill=col)
    mask = Image.new("L", (pw, ph), 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0, pw - 1, ph - 1), radius=ph // 2, fill=255)
    x, y = (W - pw) // 2, int(H * 0.11)
    img.alpha_composite(_shadow((W, H), (x, y, x + pw, y + ph), ph // 2, blur=16, alpha=70, off=(0, 10)))
    img.paste(rib, (x, y), mask)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((x, y, x + pw - 1, y + ph - 1), radius=ph // 2, outline=(255, 255, 255, 220), width=4)
    d.text((x + 55 - bb[0], y + 27 - bb[1]), text, font=f, fill=SOFT_INK + (255,))
    _sparkle(d, x - 4, y + 10, 16, BUTTER + (255,)); _sparkle(d, x + pw + 6, y + ph - 8, 13, CORAL + (255,))
    img.save(path)


def frame_photo(image, path):
    """사진: 꽉 채우고 살짝 따뜻하게 + 아래쪽 크림 그라데이션(자막·카드 가독성)."""
    im = Image.open(image).convert("RGB")
    r = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    x, y = (im.width - W) // 2, (im.height - H) // 2
    im = im.crop((x, y, x + W, y + H))
    im = Image.blend(im, Image.new("RGB", (W, H), (255, 236, 214)), 0.08)
    grad = Image.new("L", (1, H), 0)
    for yy in range(H):
        t = max(0.0, (yy - H * 0.58) / (H * 0.42)); grad.putpixel((0, yy), int(150 * t))
    im = Image.composite(Image.new("RGB", (W, H), (255, 243, 226)), im, grad.resize((W, H)))
    im.save(path, quality=95)


def frame_product(image, path):
    """상품: 크림→피치 그라데이션 + 파스텔 블롭 + 흰 테두리 둥근 카드 + 반짝이."""
    im = Image.open(image).convert("RGB")
    bg = Image.new("RGB", (W, H), CREAM); bd = ImageDraw.Draw(bg)
    for yy in range(H):
        t = yy / (H - 1); col = tuple(int(CREAM[k] + (PEACH[k] - CREAM[k]) * t * 0.85) for k in range(3))
        bd.line([(0, yy), (W, yy)], fill=col)
    blobs = Image.new("RGBA", (W, H), (0, 0, 0, 0)); bl = ImageDraw.Draw(blobs)
    for (cx, cy, rr, col) in [(170, 420, 300, BUTTER), (930, 300, 260, LILAC), (820, 1500, 340, SAGE), (160, 1600, 220, PEACH)]:
        bl.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=col + (170,))
    out = bg.convert("RGBA"); out.alpha_composite(blobs.filter(ImageFilter.GaussianBlur(90)))
    side = 900
    sq = im if im.width == im.height else im.crop((0, 0, min(im.size), min(im.size)))
    card = sq.resize((side, side), Image.LANCZOS)
    mask = Image.new("L", (side, side), 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0, side, side), radius=60, fill=255)
    x, y = (W - side) // 2, int(H * 0.40) - side // 2
    out.alpha_composite(_shadow((W, H), (x, y, x + side, y + side), 60, blur=30, alpha=110, off=(0, 22)))
    frame = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(frame).rounded_rectangle((x - 14, y - 14, x + side + 14, y + side + 14), radius=72, fill=(255, 255, 255, 255))
    out.alpha_composite(frame); out.paste(card, (x, y), mask)
    d = ImageDraw.Draw(out)
    _sparkle(d, x - 30, y + 40, 26, CORAL + (255,)); _sparkle(d, x + side + 26, y + side - 60, 22, BUTTER + (255,)); _sparkle(d, x + side - 40, y - 34, 16, LILAC + (255,))
    out.convert("RGB").save(path, quality=95)


def grain_png(path, alpha=16):
    import random
    random.seed(7)
    g = Image.new("L", (W // 2, H // 2)); g.putdata([random.randint(90, 165) for _ in range((W // 2) * (H // 2))])
    g = g.resize((W, H))
    Image.merge("RGBA", (g, g, g, Image.new("L", (W, H), alpha))).save(path)


def build(spec: dict, out: Path, keep_tmp: bool = False) -> Path:
    slides = sorted(spec["slides"], key=lambda s: float(s["start"]))
    audio = _resolve(spec["audio"]) if spec.get("audio") else None
    music = _resolve(spec["music"]) if spec.get("music") else None
    total = float(slides[-1]["end"])
    if audio:
        total = max(total, _probe_dur(audio) + float(spec.get("tail", 1.0)))
    if total > MAX_SECONDS:
        raise ValueError(f"릴스 길이 {total:.1f}초 > {MAX_SECONDS}초")
    tmp = Path(tempfile.mkdtemp(prefix="haru-reel-"))
    try:
        inputs: list[str] = []
        filters: list[str] = []
        idx = 0
        for i, s in enumerate(slides):
            dur = float(s["end"]) - float(s["start"]) + (XFADE if i < len(slides) - 1 else 0.0)
            src = _resolve(s["src"])
            if not src.exists():
                raise FileNotFoundError(str(src))
            if s.get("kind") == "video":
                clip = _probe_dur(src)
                speed = min(1.0, clip / dur)  # 장면이 클립보다 길면 느리게(최소 0.45배)
                speed = max(0.45, speed)
                inputs += ["-i", str(src)]
                filters.append(
                    f"[{idx}:v]setpts=PTS/{speed:.4f},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                    f"fps={FPS},trim=duration={dur:.3f},setpts=PTS-STARTPTS,format=yuv420p[v{i}]"
                )
                idx += 1
            else:
                base = tmp / f"base{i}.jpg"
                (frame_product if s.get("kind") == "product" else frame_photo)(src, base)
                frames = int(round(dur * FPS))
                inputs += ["-loop", "1", "-t", f"{dur:.3f}", "-i", str(base)]
                zoom_in = s.get("zoom", "in") == "in"
                z = "min(zoom+0.0007,1.09)" if zoom_in else "if(eq(on,1),1.09,max(zoom-0.0007,1.0))"
                filters.append(
                    f"[{idx}:v]scale={W*2}:{H*2},zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS},setsar=1,format=yuv420p[v{i}]"
                )
                idx += 1
        chain = "v0"
        for i in range(1, len(slides)):
            off = float(slides[i]["start"]) - XFADE / 2
            filters.append(f"[{chain}][v{i}]xfade=transition=fade:duration={XFADE}:offset={max(0.0, off):.3f}[x{i}]")
            chain = f"x{i}"
        # 자막: 절대 시각 t 부터 다음 자막 t(또는 끝)까지. 각 PNG 를 전체 길이로 돌리고 enable + fade 로 켠다.
        caps = sorted(spec.get("captions", []), key=lambda c: float(c["t"]))
        for j, c in enumerate(caps):
            png = tmp / f"cap{j}.png"
            badge = ""
            for s in slides:  # 그 시각에 걸린 장면의 번호 배지
                if float(s["start"]) <= float(c["t"]) < float(s["end"]) + 0.01:
                    badge = str(s.get("badge", ""))
            caption_png(c["lines"], int(c.get("size", 76)), c.get("pos", "lower"), badge, png)
            t0 = float(c["t"]); t1 = float(caps[j + 1]["t"]) if j + 1 < len(caps) else total
            inputs += ["-loop", "1", "-t", f"{total:.3f}", "-i", str(png)]
            filters.append(f"[{idx}:v]format=rgba,fade=t=in:st={t0:.3f}:d={CAP_FADE}:alpha=1[cp{j}];[{chain}][cp{j}]overlay=0:0:enable='between(t,{t0:.3f},{t1:.3f})':format=auto[o{j}]")
            chain = f"o{j}"; idx += 1
        # 머리말 알약: {"t": start, "until": end, "text": "① 성능에 비해 싸다"}
        for j, pl in enumerate(spec.get("pills", [])):
            png = tmp / f"pill{j}.png"; pill_png(pl["text"], png)
            t0, t1 = float(pl["t"]), float(pl["until"])
            inputs += ["-loop", "1", "-t", f"{total:.3f}", "-i", str(png)]
            filters.append(f"[{idx}:v]format=rgba,fade=t=in:st={t0:.3f}:d={CAP_FADE}:alpha=1[pl{j}];[{chain}][pl{j}]overlay=0:0:enable='between(t,{t0:.3f},{t1:.3f})':format=auto[op{j}]")
            chain = f"op{j}"; idx += 1
        # 댓글 카드: 아래에서 올라와 쌓인다. 같은 group 안에서 최대 3장, 새 카드가 오면 위로 밀리고 4번째에 맨 위가 사라진다.
        cards = sorted(spec.get("cards", []), key=lambda c: float(c["t"]))
        groups: dict = {}
        for c in cards:
            groups.setdefault(c.get("group", 0), []).append(c)
        SLIDE = 0.35
        for g, cs in groups.items():
            sizes = []
            for k, c in enumerate(cs):
                png = tmp / f"card{g}_{k}.png"; sizes.append(card_png(c, png)); c["_png"] = png
            g_end = float(cs[0].get("group_until", total))
            for k, c in enumerate(cs):
                cw, ch = sizes[k]
                t0 = float(c["t"])
                later = [float(x["t"]) for x in cs[k + 1:]]
                a1 = later[0] if len(later) > 0 else None
                a2 = later[1] if len(later) > 1 else None
                a3 = later[2] if len(later) > 2 else None
                end = a3 if a3 else g_end
                # 슬롯 y: 맨 아래 슬롯 기준 위로 쌓기 (아래 여백 220)
                y_bottom = H - 220 - ch
                y_mid = y_bottom - (sizes[k + 1][1] + CARD_SLOT_GAP if k + 1 < len(sizes) else 0)
                y_top = y_mid - (sizes[k + 2][1] + CARD_SLOT_GAP if k + 2 < len(sizes) else 0)
                x = (W - cw) // 2
                # 등장: 화면 아래(H)에서 y_bottom 으로 SLIDE 초 동안 올라옴
                expr = f"if(lt(t,{t0 + SLIDE:.3f}),{H}+({y_bottom}-{H})*(t-{t0:.3f})/{SLIDE},{y_bottom})"
                if a1 is not None:
                    expr = f"if(lt(t,{a1:.3f}),{expr},if(lt(t,{a1 + SLIDE:.3f}),{y_bottom}+({y_mid}-{y_bottom})*(t-{a1:.3f})/{SLIDE},{y_mid}))"
                if a2 is not None:
                    expr = f"if(lt(t,{a2:.3f}),{expr},if(lt(t,{a2 + SLIDE:.3f}),{y_mid}+({y_top}-{y_mid})*(t-{a2:.3f})/{SLIDE},{y_top}))"
                inputs += ["-loop", "1", "-t", f"{total:.3f}", "-i", str(c["_png"])]
                fade_out = f",fade=t=out:st={end - 0.3:.3f}:d=0.3:alpha=1" if end < total else ""
                filters.append(f"[{idx}:v]format=rgba{fade_out}[cd{g}_{k}];[{chain}][cd{g}_{k}]overlay=x={x}:y='{expr}':enable='between(t,{t0:.3f},{end:.3f})':eval=frame:format=auto[oc{g}_{k}]")
                chain = f"oc{g}_{k}"; idx += 1
        if spec.get("grain", True):
            png = tmp / "grain.png"; grain_png(png)
            inputs += ["-loop", "1", "-t", f"{total:.3f}", "-i", str(png)]
            filters.append(f"[{chain}][{idx}:v]overlay=0:0:format=auto[og]"); chain = "og"; idx += 1
        if spec.get("bottom"):
            png = tmp / "bottom.png"; bottom_png(spec["bottom"], png)
            inputs += ["-loop", "1", "-t", f"{total:.3f}", "-i", str(png)]
            filters.append(f"[{chain}][{idx}:v]overlay=0:0:format=auto[ob]"); chain = "ob"; idx += 1
        filters.append(f"[{chain}]fade=t=out:st={max(0.0, total-0.6):.3f}:d=0.6,format=yuv420p[vout]")
        # 오디오
        if audio and music:
            inputs += ["-i", str(audio), "-stream_loop", "-1", "-i", str(music)]
            filters.append(f"[{idx}:a]apad=pad_dur=4[na];[{idx+1}:a]volume={float(spec.get('music_db', -20))}dB,afade=t=out:st={max(0.0,total-1.8):.3f}:d=1.8[mu];[na][mu]amix=inputs=2:duration=first:dropout_transition=3,atrim=0:{total:.3f}[aout]")
        elif audio:
            inputs += ["-i", str(audio)]
            filters.append(f"[{idx}:a]apad=pad_dur=4,atrim=0:{total:.3f}[aout]")
        else:
            inputs += ["-f", "lavfi", "-t", f"{total:.3f}", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
            filters.append(f"[{idx}:a]acopy[aout]")
        out.parent.mkdir(parents=True, exist_ok=True)
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filters),
               "-map", "[vout]", "-map", "[aout]", "-t", f"{total:.3f}",
               "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-profile:v", "high", "-level", "4.1", "-pix_fmt", "yuv420p", "-r", str(FPS),
               "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-movflags", "+faststart", str(out)]
        subprocess.run(cmd, check=True)
        return out
    finally:
        if keep_tmp:
            print(f"[reels] 임시 폴더 유지: {tmp}")
        else:
            shutil.rmtree(tmp, ignore_errors=True)


def probe(path: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size:stream=codec_name,width,height", "-of", "json", str(path)], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("spec"); ap.add_argument("--out", default=""); ap.add_argument("--keep-tmp", action="store_true")
    ns = ap.parse_args()
    spec = json.loads(Path(ns.spec).read_text(encoding="utf-8"))
    out = Path(ns.out) if ns.out else ROOT / "haru" / "hub" / "static" / "reels" / f"{spec['slug']}.mp4"
    build(spec, out, keep_tmp=ns.keep_tmp)
    info = probe(out)
    print(f"[reels] {out} · {float(info['format']['duration']):.1f}초 · {int(info['format']['size'])//1024}KB · " + ", ".join(f"{s.get('codec_name')} {s.get('width','')}x{s.get('height','')}" for s in info["streams"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
