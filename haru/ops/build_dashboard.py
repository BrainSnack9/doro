#!/usr/bin/env python3
"""haru/data/dashboard.json → haru/ops/dist/index.html (로컬 전용 운영 대시보드).

수익·계정 정보가 들어가므로 공개 사이트에 올리지 않는다. 보기: python3 -m http.server --directory haru/ops/dist 8766
"""
import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HARU = HERE.parent
DATA = HARU / "data" / "dashboard.json"
DIST = HERE / "dist"
TPL = HERE / "template.html"
e = html.escape


def fmt(v):
    if v is None or v == "":
        return "–"
    return e(str(v))


def badge(ok: bool, label: str) -> str:
    return f'<span class="badge {"ok" if ok else "no"}">{e(label)}</span>'


def render_posts(posts: list) -> str:
    rows = []
    for p in posts:
        th = p["channels"].get("threads")
        ig = p["channels"].get("instagram")
        def cell(entry, kind):
            if not entry:
                return '<td class="no">–</td>'
            ins = entry.get("insights") or {}
            link = entry.get("permalink")
            if kind == "threads":
                stat = f'조회 {fmt(ins.get("views"))} · 좋아요 {fmt(ins.get("likes"))} · 답글 {fmt(ins.get("replies"))}'
            else:
                stat = f'조회 {fmt(ins.get("views"))} · 도달 {fmt(ins.get("reach"))} · 좋아요 {fmt(ins.get("likes"))} · 저장 {fmt(ins.get("saved"))}'
            a = f'<a href="{e(link, quote=True)}" target="_blank">열기</a>' if link else ""
            return f'<td>{badge(True, "게시")} {a}<div class="sub">{stat}</div></td>'
        blog = f'<td>{badge(True, "게시")} <a href="{e(p["naver_blog"], quote=True)}" target="_blank">열기</a></td>' if p.get("naver_blog") else '<td class="no">–</td>'
        pend = "".join(f'<div class="sub">⏳ {e(x["channel"])} {e(str(x.get("scheduled_at") or ""))}</div>' for x in p["pending"])
        fail = "".join(f'<div class="sub err">✗ {e(x["channel"])} {e(str(x.get("error") or ""))}</div>' for x in p["failed"])
        aff = p.get("affiliate") or {}
        img = f'<img class="thumb" src="{e(p["image_url"], quote=True)}" alt="">' if p.get("image_url") else ""
        rows.append(
            f'<tr><td class="pname">{img}<div><b>{e(p["product"])}</b><div class="sub">{e(p["date"])} · {e(aff.get("program") or "제휴 없음")} · 장면 {e(p.get("image_scene") or "–")}</div><div class="sub hook">{e(p.get("text") or "")}</div>{pend}{fail}</div></td>'
            f'{cell(th, "threads")}{cell(ig, "instagram")}{blog}</tr>'
        )
    return "\n".join(rows) or '<tr><td colspan="4" class="no">아직 글이 없습니다.</td></tr>'


def render_revenue(rev: dict) -> str:
    n = rev.get("naver") or {}
    s30 = n.get("sales_30d") or {}
    st = n.get("settlement") or {}
    c = rev.get("coupang") or {}
    oh = rev.get("ohouse") or {}
    if oh.get("status") != "ok":
        oh = {**((rev.get("manual") or {}).get("ohouse") or {}), "status": oh.get("status") or "manual"}
    cards = []
    cards.append(f'''<div class="card"><h3>네이버 쇼핑커넥트</h3>
      <div class="big">{fmt(s30.get("expected_revenue"))}원 <span class="sub">예상 수익 · 최근 30일</span></div>
      <div class="sub">클릭 {fmt(s30.get("clicks"))}회 · 주문 {fmt(s30.get("orders"))}건 · 판매 {fmt(s30.get("sales_amount"))}원</div>
      <div class="sub">정산: 확정 {fmt(st.get("confirmed"))}원 · 대기 {fmt(st.get("pending"))}원 · 지급 누적 {fmt(st.get("paid_total"))}원 · 계좌 {fmt(st.get("account"))}</div>
      <div class="sub">발급 링크 {len(n.get("links") or [])}개 · 업데이트 {fmt(s30.get("updated"))}</div></div>''')
    if c.get("status") == "ok":
        cards.append(f'<div class="card"><h3>쿠팡 파트너스</h3><div class="sub">리포트 읽음 (표 구조 확인 필요)</div><pre class="small">{e((c.get("text") or "")[:600])}</pre></div>')
    else:
        cards.append(f'<div class="card warn"><h3>쿠팡 파트너스</h3><div class="big">로그인 필요</div><div class="sub">Aside 브라우저에서 partners.coupang.com 에 로그인해 두면 다음 수집부터 자동으로 읽습니다.</div></div>')
    if oh.get("status") == "ok":
        cards.append(f'<div class="card"><h3>오늘의집 이웃 큐레이터</h3><div class="big">{fmt(oh.get("expected_revenue"))}원 <span class="sub">지급 예정 · {e(oh.get("period") or "이번달")}</span></div><div class="sub">방문 {fmt(oh.get("visits"))}회 · 주문 {fmt(oh.get("orders"))}건 · 리워드 {fmt(oh.get("grade"))}</div><div class="sub">누적 지급 {fmt(oh.get("paid_total"))}원 · 정산 정보 {fmt(oh.get("settlement_info"))}</div></div>')
    elif oh.get("status") == "needs_login":
        cards.append('<div class="card warn"><h3>오늘의집 이웃 큐레이터</h3><div class="big">로그인 필요</div><div class="sub">Aside 브라우저에서 ohou.se 에 로그인해 두면 다음 수집부터 자동으로 읽습니다.</div></div>')
    else:
        cards.append(f'<div class="card"><h3>오늘의집 이웃</h3><div class="big">{fmt(oh.get("expected_revenue"))}원</div><div class="sub">클릭 {fmt(oh.get("clicks"))} · 주문 {fmt(oh.get("orders"))} · {e(oh.get("note") or "")}</div><div class="sub">haru/data/revenue_manual.json 에 손으로 적는 값</div></div>')
    return "\n".join(cards)


def render_photos(photos: list) -> str:
    cells = []
    for ph in photos:
        used = ", ".join(ph["used_by"]) or "미사용"
        cells.append(f'<figure><img src="../../assets/posts/{e(ph["file"], quote=True)}" alt="" loading="lazy"><figcaption>{e(ph["file"])}<div class="sub">{e(ph["product"])} · {e(used)} · {ph["size_kb"]}KB</div></figcaption></figure>')
    return "\n".join(cells) or '<p class="no">사진 없음</p>'


def render_events(events: list) -> str:
    rows = []
    for ev in sorted(events, key=lambda x: x.get("ts", ""), reverse=True)[:40]:
        kind = ev.get("event")
        cls = "err" if "failed" in str(kind) else ""
        rows.append(f'<tr class="{cls}"><td>{e(ev.get("ts", "")[:16].replace("T", " "))}</td><td>{e(str(kind))}</td><td>{e(str(ev.get("channel") or ""))}</td><td>{e(str(ev.get("item_id") or ev.get("ref") or ""))}</td><td class="sub">{e(str(ev.get("error") or ev.get("result_id") or ""))}</td></tr>')
    return "\n".join(rows) or '<tr><td colspan="5" class="no">최근 7일 이벤트 없음</td></tr>'


def build() -> Path:
    d = json.loads(DATA.read_text(encoding="utf-8"))
    acc = d.get("accounts") or {}
    th, ig = acc.get("threads") or {}, acc.get("instagram") or {}
    sysinfo = d.get("system") or {}
    cert = sysinfo.get("hub_cert") or {}
    pending_total = sum(len(p["pending"]) for p in d["posts"])
    failed_total = sum(len(p["failed"]) for p in d["posts"])
    page = (TPL.read_text(encoding="utf-8")
        .replace("{{GENERATED_AT}}", e(d.get("generated_at", "")))
        .replace("{{TH_VIEWS}}", fmt(th.get("views"))).replace("{{TH_FOLLOWERS}}", fmt(th.get("followers_count")))
        .replace("{{IG_FOLLOWERS}}", fmt(ig.get("followers_count"))).replace("{{IG_MEDIA}}", fmt(ig.get("media_count")))
        .replace("{{POST_COUNT}}", str(len(d["posts"]))).replace("{{PENDING}}", str(pending_total)).replace("{{FAILED}}", str(failed_total))
        .replace("{{POSTS}}", render_posts(d["posts"]))
        .replace("{{REVENUE}}", render_revenue(d.get("revenue") or {}))
        .replace("{{PHOTOS}}", render_photos(d.get("photos") or []))
        .replace("{{EVENTS}}", render_events(d.get("events") or []))
        .replace("{{TESTS}}", fmt(sysinfo.get("tests"))).replace("{{GIT}}", fmt(sysinfo.get("git_head")))
        .replace("{{CERT}}", fmt(f'{cert.get("subject")} · 만료 {cert.get("not_after")}' if cert.get("subject") else cert.get("error")))
        .replace("{{HUB_COUNT}}", str(len(d.get("hub_items") or [])))
        .replace("{{ERRORS}}", "".join(f"<li>{e(x)}</li>" for x in d.get("errors") or []) or "<li>없음</li>")
    )
    DIST.mkdir(parents=True, exist_ok=True)
    out = DIST / "index.html"
    out.write_text(page, encoding="utf-8")
    return out


if __name__ == "__main__":
    print(f"[dashboard] wrote {build()}")
