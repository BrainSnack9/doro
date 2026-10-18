#!/usr/bin/env python3
"""links.json -> dist/ (GitHub Pages 큐레이션 셀렉트샵).

생성물:
  dist/index.html        첫 화면: 오늘의 추천(최신 1건) 히어로 + 카테고리 탭 + 상품 그리드
  dist/p/<slug>.html     상품 상세: 사진·가격·리뷰에서 본 것·단점 하나·판매처 버튼
  dist/go/<slug>.html    판매처로 넘기는 리다이렉트 페이지 (이 페이지뷰 = 클릭 수)
  dist/items.json        항목 데이터 (디버그/외부용)
  dist/cards/...         static/ 아래 파일 그대로 복사 (인스타 카드뉴스 이미지 호스팅)
  dist/.nojekyll, CNAME  은 배포 워크플로가 만든다.

links.json 항목 필드:
  필수 date, name, reason, program, url
  선택 category(자취방|뷰티|가성비|실험일지), image, price, was, fact, con, slug
meta: site_name, tagline, threads, instagram, categories,
      cloudflare_token (Cloudflare Web Analytics 비콘 토큰) 또는 goatcounter_code — 둘 다 비어 있으면 집계 스크립트 생략
클릭 집계: 판매처 버튼은 go/<slug>.html 로 가고, 그 페이지가 비콘을 보낸 뒤 판매처로 넘긴다.
  페이지뷰만 세는 집계(Cloudflare)로도 "go/<slug> 조회수 = 클릭 수"가 된다.
"""

import html
import json
import re
import shutil
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

HUB_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(HUB_DIR.parent))

from pipeline import KST  # noqa: E402
from pipeline.disclosure import AFFILIATE_LABEL, AFFILIATE_LABELS_BY_PROGRAM, AI_AFFILIATE_LABEL_SHORT, AI_LABEL  # noqa: E402

LINKS_PATH = HUB_DIR / "links.json"
TEMPLATE_HOME = HUB_DIR / "template.html"
TEMPLATE_ITEM = HUB_DIR / "template_item.html"
TEMPLATE_GO = HUB_DIR / "template_go.html"
DIST_DIR = HUB_DIR / "dist"
STATIC_DIR = HUB_DIR / "static"  # 그대로 복사되는 파일들(카드뉴스 이미지 등). 2026-10-18

WEEKDAYS = "월화수목금토일"
DEFAULT_CATEGORIES = ["자취방", "뷰티", "가성비", "실험일지"]
e = html.escape


def pretty_date(iso: str) -> str:
    """2026-10-17 -> 10월 17일 (금). 형식이 다르면 원문 그대로."""
    try:
        d = datetime.strptime(iso, "%Y-%m-%d")
    except ValueError:
        return iso
    return f"{d.month}월 {d.day}일 ({WEEKDAYS[d.weekday()]})"


def slugify(item: dict) -> str:
    """안정적인 파일명: 명시된 slug > date + 이름(영숫자·한글만, 24자)."""
    if item.get("slug"):
        return item["slug"]
    name = unicodedata.normalize("NFC", item["name"])
    core = re.sub(r"[^0-9A-Za-z가-힣]+", "-", name).strip("-").lower()[:24].rstrip("-")
    return f"{item['date']}-{core or 'item'}"


PROGRAM_NAMES = {"쿠팡": "쿠팡 파트너스", "네이버": "네이버 쇼핑 커넥트", "오늘의집": "오늘의집 이웃"}


def program_note(programs: set) -> str:
    """판매처 지정 고지. 문구는 판매처가 정한 그대로 써야 해서 합칠 수 없으니, 한 줄 요약 뒤에 접는 상자로 둔다 (2026-10-18 오너: 반복 줄이기).
    항목이 하나뿐인 페이지(상품 상세)는 그 판매처 문구 한 줄만 그대로 보인다."""
    present = [p for p in AFFILIATE_LABELS_BY_PROGRAM if p in programs]
    extra = [p for p in programs if p and p not in AFFILIATE_LABELS_BY_PROGRAM]  # 지정 문구 없는 판매처(오늘의집)는 공통 문구
    if not present and not extra:
        return ""
    lines = [e(AFFILIATE_LABELS_BY_PROGRAM[p]) for p in present] + ([e(AFFILIATE_LABEL)] if extra else [])
    if len(lines) == 1:
        return f"    <p>{lines[0]}</p>\n"
    names = "·".join(PROGRAM_NAMES.get(p, p) for p in present + extra)
    body = "".join(f"<p>{n}</p>" for n in lines)
    return f'    <details class="programs"><summary>{e(names)} 고지 보기</summary>{body}</details>\n'


def analytics_snippet(meta: dict) -> str:
    """Cloudflare Web Analytics(토큰) 우선, 없으면 GoatCounter(코드), 둘 다 없으면 빈 문자열."""
    token = (meta.get("cloudflare_token") or "").strip()
    if token:
        return (
            '<script defer src="https://static.cloudflareinsights.com/beacon.min.js" '
            f"data-cf-beacon='{{\"token\": \"{e(token, quote=True)}\"}}'></script>"
        )
    code = (meta.get("goatcounter_code") or "").strip()
    if code:
        return (
            f'<script data-goatcounter="https://{e(code, quote=True)}.goatcounter.com/count" '
            'async src="//gc.zgo.at/count.js"></script>'
        )
    return ""


def analytics_enabled(meta: dict) -> bool:
    return bool(analytics_snippet(meta))


def render_card(item: dict) -> str:
    slug = slugify(item)
    thumb = (
        f'<img class="thumb" src="{e(item["image"], quote=True)}" alt="" loading="lazy" width="300" height="300">'
        if item.get("image") else '<div class="thumb empty-thumb">사진 없음</div>'
    )
    price = f'<p class="price">{e(item["price"])}</p>' if item.get("price") else ""
    return (
        f'  <a class="card" href="p/{e(slug, quote=True)}.html" data-cat="{e(item.get("category", ""), quote=True)}">\n'
        f'    {thumb}\n'
        f'    <p class="name">{e(item["name"])}</p>\n'
        f'    {price}\n'
        f'    <p class="meta"><span class="badge">{e(item["program"])}</span> {e(pretty_date(item["date"])) if item.get("posted", True) else "리뷰 읽어둠"}</p>\n'
        '  </a>\n'
    )


def render_hero(item: dict) -> str:
    slug = slugify(item)
    thumb = (
        f'<img class="hero-img" src="{e(item["image"], quote=True)}" alt="" width="600" height="600">'
        if item.get("image") else '<div class="hero-img empty-thumb">사진 없음</div>'
    )
    price = ""
    if item.get("price"):
        was = f' <s>{e(item["was"])}</s>' if item.get("was") else ""
        price = f'<p class="price">{e(item["price"])}{was}</p>'
    con = f'<p class="con"><b>단점 하나</b> {e(item["con"])}</p>' if item.get("con") else ""
    return (
        '  <section class="hero">\n'
        f'    <p class="kicker">오늘의 추천 · {e(pretty_date(item["date"]))}</p>\n'
        '    <div class="hero-row">\n'
        f'      <a href="p/{e(slug, quote=True)}.html">{thumb}</a>\n'
        '      <div>\n'
        f'        <h2 class="name"><a href="p/{e(slug, quote=True)}.html"><span>{e(item["name"])}</span></a></h2>\n'
        f'        {price}\n'
        f'        <p class="reason">{e(item["reason"])}</p>\n'
        f'        {con}\n'
        f'        <a class="go" href="go/{e(slug, quote=True)}.html" rel="nofollow sponsored noopener" target="_blank">{e(item["program"])}에서 보기</a>\n'
        f'        <a class="more" href="p/{e(slug, quote=True)}.html">리뷰에서 본 것 더 보기</a>\n'
        '      </div>\n'
        '    </div>\n'
        '  </section>\n'
    )


def render_tabs(categories: list, items: list) -> str:
    counts = {c: 0 for c in categories}
    for it in items:
        counts[it.get("category", categories[0])] = counts.get(it.get("category", categories[0]), 0) + 1
    tabs = ['    <button class="tab is-on" data-cat="">전체</button>\n']
    for c in categories:
        tabs.append(f'    <button class="tab" data-cat="{e(c, quote=True)}">{e(c)} <small>{counts.get(c, 0)}</small></button>\n')
    return "".join(tabs)


def render_item_page(item: dict, meta: dict, template: str) -> str:
    slug = slugify(item)
    thumb = (
        f'<img class="detail-img" src="{e(item["image"], quote=True)}" alt="" width="600" height="600">'
        if item.get("image") else '<div class="detail-img empty-thumb">사진 없음</div>'
    )
    price = ""
    if item.get("price"):
        was = f' <s>{e(item["was"])}</s>' if item.get("was") else ""
        price = f'<p class="price">{e(item["price"])}{was}</p>'
    fact = f'<section class="block"><h3>리뷰에서 본 것</h3><p>{e(item["fact"])}</p></section>' if item.get("fact") else ""
    con = f'<section class="block con"><h3>단점 하나</h3><p>{e(item["con"])}</p></section>' if item.get("con") else ""
    return (
        template.replace("{{SITE_NAME}}", e(meta.get("site_name", "하루의 오늘 추천")))
        .replace("{{TITLE}}", e(item["name"]))
        .replace("{{DESCRIPTION}}", e(item["reason"][:140]))
        .replace("{{SHORT_LABEL}}", e(AI_AFFILIATE_LABEL_SHORT))
        .replace("{{PROGRAM_NOTES}}", program_note({item.get("program", "")}))
        .replace("{{ANALYTICS}}", analytics_snippet(meta))
        .replace("{{IMAGE}}", thumb)
        .replace("{{NAME}}", e(item["name"]))
        .replace("{{PRICE}}", price)
        .replace("{{DATE}}", e(pretty_date(item["date"])))
        .replace("{{CATEGORY}}", e(item.get("category", "")))
        .replace("{{PROGRAM}}", e(item["program"]))
        .replace("{{REASON}}", e(item["reason"]))
        .replace("{{FACT}}", fact)
        .replace("{{CON}}", con)
        .replace("{{GO}}", f"../go/{e(slug, quote=True)}.html")
        .replace("{{THREADS}}", e(meta.get("threads", ""), quote=True))
        .replace("{{GENERATED_AT}}", datetime.now(KST).strftime("%Y-%m-%d %H:%M"))
    )


def render_go_page(item: dict, meta: dict, template: str) -> str:
    return (
        template.replace("{{SITE_NAME}}", e(meta.get("site_name", "하루의 오늘 추천")))
        .replace("{{NAME}}", e(item["name"]))
        .replace("{{PROGRAM}}", e(item["program"]))
        .replace("{{URL}}", e(item["url"], quote=True))
        .replace("{{ANALYTICS}}", analytics_snippet(meta))
        .replace("{{DELAY_MS}}", "500" if analytics_enabled(meta) else "0")
    )


def build(links_path: Path = LINKS_PATH, dist_dir: Path = DIST_DIR) -> Path:
    data = json.loads(links_path.read_text(encoding="utf-8"))
    meta = data.get("meta", {})
    categories = meta.get("categories") or DEFAULT_CATEGORIES
    items = sorted(data["items"], key=lambda it: it["date"], reverse=True)
    home_tpl = TEMPLATE_HOME.read_text(encoding="utf-8")
    item_tpl = TEMPLATE_ITEM.read_text(encoding="utf-8")
    go_tpl = TEMPLATE_GO.read_text(encoding="utf-8")

    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    (dist_dir / "p").mkdir(parents=True)
    (dist_dir / "go").mkdir()
    if STATIC_DIR.exists():  # 카드뉴스 등 정적 파일 → https://harureviews.date/cards/...
        shutil.copytree(STATIC_DIR, dist_dir, dirs_exist_ok=True)

    # 첫 화면 "오늘의 추천" = 글로 올린(posted) 항목 중 최신. 미리 비축만 한 항목(posted: false)은 그리드에만 보인다 (2026-10-18).
    posted = [it for it in items if it.get("posted", True)]
    hero = render_hero(posted[0]) if posted else (render_hero(items[0]) if items else '  <p class="empty">아직 고른 게 없어요. 오늘 밤에 다시 와 주세요.</p>\n')
    grid = "".join(render_card(it) for it in items)
    page = (
        home_tpl.replace("{{SITE_NAME}}", e(meta.get("site_name", data.get("title", "하루의 오늘 추천"))))
        .replace("{{TAGLINE}}", e(meta.get("tagline", "")))
        .replace("{{SHORT_LABEL}}", e(AI_AFFILIATE_LABEL_SHORT))
        .replace("{{PROGRAM_NOTES}}", program_note({it.get("program", "") for it in items}))
        .replace("{{ANALYTICS}}", analytics_snippet(meta))
        .replace("{{HERO}}", hero)
        .replace("{{TABS}}", render_tabs(categories, items))
        .replace("{{GRID}}", grid)
        .replace("{{COUNT}}", str(len(items)))
        .replace("{{THREADS}}", e(meta.get("threads", ""), quote=True))
        .replace("{{INSTAGRAM}}", e(meta.get("instagram", ""), quote=True))
        .replace("{{GENERATED_AT}}", datetime.now(KST).strftime("%Y-%m-%d %H:%M"))
    )
    (dist_dir / "index.html").write_text(page, encoding="utf-8")
    for it in items:
        (dist_dir / "p" / f"{slugify(it)}.html").write_text(render_item_page(it, meta, item_tpl), encoding="utf-8")
        (dist_dir / "go" / f"{slugify(it)}.html").write_text(render_go_page(it, meta, go_tpl), encoding="utf-8")
    (dist_dir / "items.json").write_text(json.dumps([{**it, "slug": slugify(it)} for it in items], ensure_ascii=False, indent=1), encoding="utf-8")
    return dist_dir / "index.html"


if __name__ == "__main__":
    out = build()
    n = len(list((DIST_DIR / "p").glob("*.html")))
    print(f"[hub] wrote {out} (+{n} item pages)")
