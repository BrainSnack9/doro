#!/usr/bin/env python3
"""인스타 카드뉴스 v2: HTML/CSS 로 디자인하고 Aside(크롬)로 1080x1350 캡처.

  python3 haru/tools/cards_html.py <spec.json>          # HTML 생성 + 캡처 → <out_dir>/N.jpg
  python3 haru/tools/cards_html.py <spec.json> --html   # HTML 만 생성(검수용)

디자인(2026-10-18 v2, 오너: "다른 글과 비교해 눈에 안 띈다"): 노랑(#F6E75A)·먹색(#15181D) 두 색의 고대비. 글자가 곧 그림이다.
- cover: 사진 위에 먹색 그라데이션, 흰 큰 제목(핵심 구절은 노란 마커), 기울어진 '리뷰 N개 읽음' 스티커
- list: 노란 바탕, 검은 대문자급 제목, 번호 대신 큰 따옴표 인용 블록
- stats: 먹색 바탕, 숫자 하나를 화면 절반 크기로
- versus: 좌(노랑) 우(먹색) 반반, 같은 사실의 두 얼굴
- photo: 힉스필드 장면 사진 전면 + 아래 먹색 그라데이션 + 짧은 문장 (글자 카드 사이의 숨구멍)
- end: 먹색, 노란 도메인, 고지
spec 은 cards.py 와 같되 type 에 versus({"left":{"label","text"},"right":{...}}, "foot") 추가. 캡처는 http://localhost:8766 (serve.py) 로 HTML 을 연다.
"""
import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HARU = Path(__file__).resolve().parents[1]
ASIDE = os.path.expanduser("~/.local/bin/aside")
ASIDE_ACCOUNT = os.environ.get("HARU_ASIDE_ACCOUNT", "u0")  # 하루 전용 Aside 계정(u0). 로이어픽은 u1 — 전역 기본 계정에 의존하지 않는다(2026-10-19)
PORT = 8766

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1080px;height:1350px;overflow:hidden;background:#15181D}
body{font-family:Pretendard,"Apple SD Gothic Neo",sans-serif;color:#15181D;-webkit-font-smoothing:antialiased;letter-spacing:-0.01em}
.card{position:relative;width:1080px;height:1350px;overflow:hidden}
.yellow{background:#F6E75A}.ink{background:#15181D;color:#F4F1E6}.paper{background:#F4F1E6}
.brand{position:absolute;left:72px;top:64px;font-size:28px;font-weight:600;letter-spacing:0.02em;opacity:.85}
.pg{position:absolute;right:72px;top:64px;font-size:28px;font-weight:600;font-variant-numeric:tabular-nums;opacity:.6}
.ink .brand,.ink .pg{color:#F4F1E6}
mark{background:none;color:inherit;background-image:linear-gradient(transparent 58%,#F6E75A 58%,#F6E75A 94%,transparent 94%);padding:0 6px;margin:0 -6px}
.ink mark{background-image:linear-gradient(transparent 68%,rgba(201,184,46,.72) 68%,rgba(201,184,46,.72) 96%,transparent 96%);color:inherit}
.cover mark,.photo mark{background-image:linear-gradient(transparent 68%,rgba(201,184,46,.72) 68%,rgba(201,184,46,.72) 96%,transparent 96%);color:inherit}
.yellow mark{background-image:none;background:#15181D;color:#F6E75A;padding:0 14px;margin:0;border-radius:10px}
/* cover */
.cover img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:50% 20%}
.cover .shade{position:absolute;inset:0;background:linear-gradient(180deg,rgba(21,24,29,.05) 0%,rgba(21,24,29,.15) 40%,rgba(21,24,29,.92) 72%,#15181D 100%)}
.cover .brand,.cover .pg{color:#F4F1E6;text-shadow:0 1px 8px rgba(0,0,0,.4)}
.cover .bottom{position:absolute;left:72px;right:72px;bottom:84px;display:flex;flex-direction:column;gap:30px}
.cover .title{color:#F4F1E6;font-size:84px;line-height:1.16;font-weight:800;word-break:keep-all}
.cover .sub{color:#F4F1E6;opacity:.8;font-size:30px;line-height:1.45;font-weight:500;word-break:keep-all}
.sticker{position:absolute;right:64px;top:170px;width:270px;height:270px;border-radius:50%;background:#F6E75A;color:#15181D;display:flex;flex-direction:column;align-items:center;justify-content:center;transform:rotate(-12deg);box-shadow:0 18px 50px rgba(0,0,0,.35);text-align:center}
.sticker b{font-size:68px;font-weight:900;line-height:1;letter-spacing:-0.03em}.sticker span{font-size:30px;font-weight:700;margin-top:8px}.sticker small{font-size:24px;font-weight:600;opacity:.75}
/* list */
.kicker{position:absolute;left:72px;top:150px;font-size:30px;font-weight:700;letter-spacing:0.04em}
.list .title{position:absolute;left:72px;right:72px;top:210px;font-size:78px;line-height:1.14;font-weight:900;word-break:keep-all;letter-spacing:-0.025em}
.quotes{position:absolute;left:72px;right:72px;top:440px;bottom:230px;display:flex;flex-direction:column;justify-content:center;gap:34px}
.q{position:relative;padding:34px 44px;border-radius:22px;background:rgba(21,24,29,.08);font-size:38px;line-height:1.5;font-weight:600;word-break:keep-all}
.q:before{content:"“ ";font-weight:900;opacity:.55}
.q:after{content:" ”";font-weight:900;opacity:.55}
.ink .q{background:rgba(244,241,230,.08)}
.foot{position:absolute;left:72px;right:72px;bottom:84px;font-size:30px;line-height:1.45;font-weight:600;word-break:keep-all}
.foot span{display:inline-block;background:#15181D;color:#F6E75A;padding:14px 24px;border-radius:14px}
.ink .foot span{background:#F6E75A;color:#15181D}
/* stats */
.stats .title{position:absolute;left:72px;right:72px;top:210px;font-size:62px;line-height:1.18;font-weight:800;word-break:keep-all;color:#F4F1E6}
.bignum{position:absolute;left:60px;top:400px;font-size:340px;line-height:.95;font-weight:900;color:#F6E75A;letter-spacing:-0.06em}
.bignum.small{font-size:260px}
.biglabel{position:absolute;left:72px;top:790px;font-size:40px;font-weight:700;color:#F4F1E6;line-height:1.3;word-break:keep-all}
.chips{position:absolute;left:72px;right:72px;top:920px;display:flex;flex-direction:column;gap:18px}
.chip{display:flex;align-items:baseline;gap:22px;border-top:2px solid rgba(244,241,230,.2);padding-top:18px;color:#F4F1E6}
.chip b{font-size:52px;font-weight:900;color:#F6E75A;min-width:280px;letter-spacing:-0.03em}.chip span{font-size:32px;font-weight:500;opacity:.85}
/* versus */
.vs{display:flex;height:100%}
.vs .half{flex:1;padding:170px 56px 0 56px;position:relative}
.vs .l{background:#F6E75A;color:#15181D}.vs .r{background:#15181D;color:#F4F1E6}
.vs .label{font-size:32px;font-weight:800;letter-spacing:0.06em;opacity:.7}
.vs .stars{font-size:52px;letter-spacing:-0.05em;margin-top:8px}
.vs .text{font-size:66px;line-height:1.2;font-weight:900;margin-top:40px;word-break:keep-all;letter-spacing:-0.03em}
.vs .badge{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%) rotate(-8deg);background:#F4F1E6;color:#15181D;font-size:44px;font-weight:900;padding:18px 34px;border-radius:999px;box-shadow:0 14px 40px rgba(0,0,0,.35);white-space:nowrap}
.vs-foot{position:absolute;left:72px;right:72px;bottom:90px;text-align:center;font-size:32px;line-height:1.45;font-weight:600;color:#F4F1E6;word-break:keep-all}
.vs-foot .box{display:inline-block;max-width:860px;background:#F4F1E6;color:#15181D;padding:22px 34px;border-radius:18px;box-shadow:0 14px 40px rgba(0,0,0,.35)}
/* photo */
.photo img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:50% 50%}
.photo .shade{position:absolute;inset:0;background:linear-gradient(180deg,rgba(21,24,29,.0) 0%,rgba(21,24,29,.0) 45%,rgba(21,24,29,.9) 78%,#15181D 100%)}
.photo .brand,.photo .pg{color:#F4F1E6;text-shadow:0 1px 8px rgba(0,0,0,.4)}
.photo .bottom{position:absolute;left:72px;right:72px;bottom:84px;display:flex;flex-direction:column;gap:22px}
.photo .kicker{position:static;color:#F6E75A;font-size:30px;font-weight:700;letter-spacing:0.04em;text-shadow:0 1px 8px rgba(0,0,0,.4)}
.photo .title{color:#F4F1E6;font-size:76px;line-height:1.16;font-weight:900;word-break:keep-all;letter-spacing:-0.025em}
.photo .sub{color:#F4F1E6;opacity:.8;font-size:28px;line-height:1.45;font-weight:500;margin-top:6px}
/* end */
.end .big{position:absolute;left:72px;right:72px;top:210px;font-size:92px;line-height:1.12;font-weight:900;color:#F4F1E6;word-break:keep-all;letter-spacing:-0.03em}
.end .mid{position:absolute;left:72px;right:72px;top:470px;height:520px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;text-align:center}
.end .arrow{font-size:150px;line-height:1;color:#F6E75A;font-weight:900}
.end .domain{font-size:78px;font-weight:900;color:#F6E75A;letter-spacing:-0.02em;background:rgba(246,231,90,.08);padding:14px 36px;border-radius:999px;border:3px solid rgba(246,231,90,.35)}
.end .lines{position:absolute;left:72px;right:72px;top:1030px;font-size:30px;line-height:1.5;color:#F4F1E6;opacity:.85;word-break:keep-all;text-align:center}
.end .note{position:absolute;left:72px;right:72px;bottom:56px;font-size:21px;line-height:1.45;color:#F4F1E6;opacity:.5;word-break:keep-all;text-align:center}
"""


def esc(t: str) -> str:
    """텍스트 → HTML. [[마커]] 는 <mark> 로."""
    return re.sub(r"\[\[(.+?)\]\]", r"<mark>\1</mark>", html.escape(t))


def render(c: dict, brand: str, idx: int, total: int, base: Path) -> str:
    pg = f'<div class="brand">{esc(brand)}</div><div class="pg">{idx:02d} / {total:02d}</div>'
    t = c["type"]
    if t == "cover":
        photo = os.path.relpath(Path(c["photo"]).resolve(), base)
        st = c.get("sticker") or {}
        sticker = f'<div class="sticker"><b>{esc(st.get("big", ""))}</b><span>{esc(st.get("mid", ""))}</span><small>{esc(st.get("small", ""))}</small></div>' if st else ""
        body = f'<div class="card cover"><img src="{html.escape(photo)}"><div class="shade"></div>{pg}{sticker}<div class="bottom"><div class="title">{esc(c["title"])}</div><div class="sub">{esc(c.get("sub", ""))}</div></div></div>'
    elif t == "list":
        qs = "".join(f'<div class="q">{esc(x)}</div>' for x in c.get("items", []))
        foot = f'<div class="foot"><span>{esc(c["foot"])}</span></div>' if c.get("foot") else ""
        body = f'<div class="card list {c.get("bg", "yellow")}">{pg}<div class="kicker">{esc(c.get("kicker", ""))}</div><div class="title">{esc(c["title"])}</div><div class="quotes">{qs}</div>{foot}</div>'
    elif t == "stats":
        big = c["big"]; cls = "bignum small" if len(big) > 4 else "bignum"
        chips = "".join(f'<div class="chip"><b>{esc(a)}</b><span>{esc(b)}</span></div>' for a, b in c.get("chips", []))
        body = f'<div class="card stats ink">{pg}<div class="kicker" style="color:#F4F1E6">{esc(c.get("kicker", ""))}</div><div class="title">{esc(c["title"])}</div><div class="{cls}">{esc(big)}</div><div class="biglabel">{esc(c.get("big_label", ""))}</div><div class="chips">{chips}</div></div>'
    elif t == "versus":
        l, r = c["left"], c["right"]
        body = (f'<div class="card versus"><div class="vs"><div class="half l"><div class="label">{esc(l["label"])}</div><div class="stars">{esc(l.get("stars", ""))}</div><div class="text">{esc(l["text"])}</div></div>'
                f'<div class="half r"><div class="label">{esc(r["label"])}</div><div class="stars">{esc(r.get("stars", ""))}</div><div class="text">{esc(r["text"])}</div></div></div>'
                f'<div class="badge" style="position:absolute;left:50%;top:50%;transform:translate(-50%,-50%) rotate(-8deg);background:#F4F1E6;color:#15181D;font-size:44px;font-weight:900;padding:18px 34px;border-radius:999px;box-shadow:0 14px 40px rgba(0,0,0,.35);white-space:nowrap">{esc(c.get("badge", "같은 물건"))}</div>'
                f'{pg}<div class="vs-foot"><span class="box">{esc(c.get("foot", ""))}</span></div></div>')
    elif t == "photo":
        photo = os.path.relpath(Path(c["photo"]).resolve(), base)
        body = f'<div class="card photo"><img src="{html.escape(photo)}"><div class="shade"></div>{pg}<div class="bottom"><div class="kicker">{esc(c.get("kicker", ""))}</div><div class="title">{esc(c["title"])}</div><div class="sub">{esc(c.get("sub", ""))}</div></div></div>'
    elif t == "end":
        lines = "<br>".join(esc(x) for x in c.get("lines", []))
        body = f'<div class="card end ink">{pg}<div class="kicker" style="color:#F4F1E6">{esc(c.get("kicker", ""))}</div><div class="big">{esc(c["title"])}</div><div class="mid"><div class="arrow">↓</div><div class="domain">{esc(c.get("domain", "harureviews.date"))}</div></div><div class="lines">{lines}</div><div class="note">{esc(c.get("note", ""))}</div></div>'
    else:
        raise ValueError(t)
    return f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>{CSS}</style></head><body>{body}</body></html>'


CAPTURE = r'''
const URLS = %(urls)s; const OUT = %(names)s;
const pg = await openTab("about:blank");
await pg._sendToTarget("Emulation.setDeviceMetricsOverride", { width: 1080, height: 1350, deviceScaleFactor: 1, mobile: false });
for (let i = 0; i < URLS.length; i++) {
  try { await pg.goto(URLS[i], { waitUntil: "load", timeout: 20000 }); } catch (e) {}
  await sleep(1200);
  await pg.screenshot({ path: OUT[i], type: "jpeg", quality: 92, fullPage: true, clip: { x: 0, y: 0, width: 1080, height: 1350 } });
}
console.log("ASIDE_DIR=" + pwd);
await closeTab(pg); console.log("GSTACK_STEP_OK");
'''


def build(spec: dict, html_only: bool = False) -> list[Path]:
    out = (HARU.parent / spec["out_dir"]).resolve() if not Path(spec["out_dir"]).is_absolute() else Path(spec["out_dir"])
    hdir = out / "html"; hdir.mkdir(parents=True, exist_ok=True)
    cards = spec["cards"]; brand = spec.get("brand", "하루 | AI 자취생")
    pages = []
    for i, c in enumerate(cards, 1):
        p = hdir / f"{i}.html"; p.write_text(render(c, brand, i, len(cards), hdir), encoding="utf-8"); pages.append(p)
    if html_only:
        return pages
    rel = [p.relative_to(HARU) for p in pages]
    urls = [f"http://localhost:{PORT}/{r.as_posix()}" for r in rel]
    names = [f"card-{i}.jpg" for i in range(1, len(cards) + 1)]
    js = CAPTURE.replace("%(urls)s", json.dumps(urls)).replace("%(names)s", json.dumps(names))
    r = subprocess.run([ASIDE, "--account", ASIDE_ACCOUNT, "repl", js], capture_output=True, text=True, timeout=150)
    m = re.search(r"^ASIDE_DIR=(.*)$", r.stdout + r.stderr, re.M)
    if not m:
        raise RuntimeError("캡처 실패: " + (r.stdout + r.stderr)[-300:])
    import shutil
    outs = []
    from PIL import Image
    for i, n in enumerate(names, 1):
        src = Path(m.group(1)) / n; dst = out / f"{i}.jpg"
        im = Image.open(src).convert("RGB")
        if im.size != (1080, 1350):  # 레티나 캡처(2160x2700 등)는 1080x1350 으로 줄인다
            im = im.crop((0, 0, min(im.width, im.height * 1080 // 1350), min(im.height, im.width * 1350 // 1080))).resize((1080, 1350), Image.LANCZOS)
        im.save(dst, "JPEG", quality=90, optimize=True); outs.append(dst)
    return outs


if __name__ == "__main__":
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    for p in build(spec, html_only="--html" in sys.argv):
        print(p)
