#!/usr/bin/env python3
"""haru/data/dashboard.json → haru/ops/dist/*.html (로컬 전용 운영 대시보드, 페이지 분리).

index.html   요약: 오늘 할 일·경고, 핵심 숫자, 최신 글 3건, 수익 합계
posts.html   게시 현황 전체 (채널별 게시 여부·수치·예약·실패)
revenue.html 수익 (네이버·쿠팡·오늘의집 상세)
photos.html  사진
system.html  시스템·이벤트·수집 오류
보기: python3 -m http.server 8766 --directory haru  →  http://localhost:8766/ops/dist/index.html
"""
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
HARU = HERE.parent
DATA = HARU / "data" / "dashboard.json"
DIST = HERE / "dist"
TPL = HERE / "template.html"
e = html.escape
PAGES = [("index.html", "요약"), ("posts.html", "게시"), ("replies.html", "답글"), ("revenue.html", "수익"), ("photos.html", "사진"), ("system.html", "시스템")]


def fmt(v):
    return "–" if v is None or v == "" else e(str(v))


def badge(ok: bool, label: str) -> str:
    return f'<span class="badge {"ok" if ok else "no"}">{e(label)}</span>'


def nav(current: str) -> str:
    return "".join(f'<a href="{f}" class="{"on" if f == current else ""}">{t}</a>' for f, t in PAGES)


def page(current: str, title: str, body: str, generated_at: str) -> str:
    return (TPL.read_text(encoding="utf-8")
            .replace("{{TITLE}}", e(title)).replace("{{NAV}}", nav(current))
            .replace("{{BODY}}", body).replace("{{GENERATED_AT}}", e(generated_at)))


def channel_cell(entry: dict | None, kind: str) -> str:
    if not entry:
        return '<td class="no">–</td>'
    ins = entry.get("insights") or {}
    link = entry.get("permalink")
    if kind == "threads":
        stat = f'조회 {fmt(ins.get("views"))} · 좋아요 {fmt(ins.get("likes"))} · 답글 {fmt(ins.get("replies"))}'
    else:
        stat = f'조회 {fmt(ins.get("views"))} · 도달 {fmt(ins.get("reach"))} · 좋아요 {fmt(ins.get("likes"))} · 저장 {fmt(ins.get("saved"))}'
    a = f' <a href="{e(link, quote=True)}" target="_blank">열기</a>' if link else ""
    return f'<td>{badge(True, "게시")}{a}<div class="sub">{stat}</div></td>'


def post_row(p: dict, compact: bool = False) -> str:
    th, ig = p["channels"].get("threads"), p["channels"].get("instagram")
    blog = f'<td>{badge(True, "게시")} <a href="{e(p["naver_blog"], quote=True)}" target="_blank">열기</a></td>' if p.get("naver_blog") else '<td class="no">–</td>'
    extra = ""
    if not compact:
        extra += "".join(f'<div class="sub">⏳ {e(x["channel"])} {e(str(x.get("scheduled_at") or ""))}</div>' for x in p["pending"])
        extra += "".join(f'<div class="sub err">✗ {e(x["channel"])} {e(str(x.get("error") or ""))}</div>' for x in p["failed"])
    aff = p.get("affiliate") or {}
    img = f'<img class="thumb" src="{e(p["image_url"], quote=True)}" alt="">' if p.get("image_url") else '<div class="thumb"></div>'
    hook = "" if compact else f'<div class="sub hook">{e(p.get("text") or "")}</div>'
    return (f'<tr><td class="pname">{img}<div><b>{e(p["product"])}</b><div class="sub">{e(p["date"])} · {e(aff.get("program") or "제휴 없음")} · 장면 {e(p.get("image_scene") or "–")}</div>{hook}{extra}</div></td>'
            f'{channel_cell(th, "threads")}{channel_cell(ig, "instagram")}{blog}</tr>')


def posts_table(posts: list, compact: bool = False) -> str:
    rows = "\n".join(post_row(p, compact) for p in posts) or '<tr><td colspan="4" class="no">아직 글이 없습니다.</td></tr>'
    return f'<table><thead><tr><th>글</th><th>스레드</th><th>인스타</th><th>네이버 블로그</th></tr></thead><tbody>{rows}</tbody></table>'


def revenue_cards(rev: dict, compact: bool = False) -> str:
    n = rev.get("naver") or {}
    s30, st = n.get("sales_30d") or {}, n.get("settlement") or {}
    c = rev.get("coupang") or {}
    oh = rev.get("ohouse") or {}
    if oh.get("status") != "ok":
        oh = {**((rev.get("manual") or {}).get("ohouse") or {}), "status": oh.get("status") or "manual"}
    cards = []
    cards.append(f'<div class="card"><h3>네이버 쇼핑커넥트</h3><div class="big">{fmt(s30.get("expected_revenue"))}원 <span class="sub">예상 수익 · 최근 30일</span></div>'
                 f'<div class="sub">클릭 {fmt(s30.get("clicks"))}회 · 주문 {fmt(s30.get("orders"))}건 · 판매 {fmt(s30.get("sales_amount"))}원</div>'
                 + ("" if compact else f'<div class="sub">정산: 확정 {fmt(st.get("confirmed"))}원 · 대기 {fmt(st.get("pending"))}원 · 지급 누적 {fmt(st.get("paid_total"))}원 · 계좌 {fmt(st.get("account"))}</div><div class="sub">발급 링크 {len(n.get("links") or [])}개 · 업데이트 {fmt(s30.get("updated"))}</div>') + '</div>')
    if c.get("status") == "ok" and c.get("summary"):
        cs = c["summary"]
        cards.append(f'<div class="card"><h3>쿠팡 파트너스</h3><div class="big">{fmt(cs.get("commission"))}원 <span class="sub">수익 · {e(cs.get("period") or "")}</span></div><div class="sub">클릭 {fmt(cs.get("clicks"))} · 주문 {fmt(cs.get("orders"))} · 구매 {fmt(cs.get("sales"))}원</div></div>')
    elif c.get("status") == "ok":
        cards.append(f'<div class="card"><h3>쿠팡 파트너스</h3><div class="sub">리포트 페이지는 읽었지만 숫자 칸을 아직 못 찾음 (수집기 보강 필요)</div>' + ("" if compact else f'<pre class="small">{e((c.get("text") or "")[:500])}</pre>') + '</div>')
    else:
        cards.append('<div class="card warn"><h3>쿠팡 파트너스</h3><div class="big">로그인 필요</div><div class="sub">Aside 에서 partners.coupang.com 로그인</div></div>')
    if oh.get("status") == "ok":
        cards.append(f'<div class="card"><h3>오늘의집 이웃 큐레이터</h3><div class="big">{fmt(oh.get("expected_revenue"))}원 <span class="sub">지급 예정 · {e(oh.get("period") or "이번달")}</span></div><div class="sub">방문 {fmt(oh.get("visits"))}회 · 주문 {fmt(oh.get("orders"))}건 · 리워드 {fmt(oh.get("grade"))}</div>' + ("" if compact else f'<div class="sub">누적 지급 {fmt(oh.get("paid_total"))}원 · 정산 정보 {fmt(oh.get("settlement_info"))}</div>') + '</div>')
    elif oh.get("status") == "needs_login":
        cards.append('<div class="card warn"><h3>오늘의집 이웃 큐레이터</h3><div class="big">로그인 필요</div><div class="sub">Aside 에서 ohou.se 로그인</div></div>')
    else:
        cards.append(f'<div class="card"><h3>오늘의집 이웃</h3><div class="big">{fmt(oh.get("expected_revenue"))}원</div><div class="sub">{e(oh.get("note") or "수동 입력")}</div></div>')
    return '<div class="cards">' + "\n".join(cards) + '</div>'


def naver_links_table(rev: dict) -> str:
    links = (rev.get("naver") or {}).get("links") or []
    if not links:
        return '<p class="no">발급된 네이버 링크가 없습니다.</p>'
    rows = "".join(f'<tr><td>{e(l["name"])}</td><td>{e(l["store"])}</td><td>{e(l["price"])}</td><td>{e(l["commission"])}</td><td>{e(l["expected"])}</td><td>{e(l["status"])}</td><td>{e(l["issued"])}</td></tr>' for l in links)
    return f'<table><thead><tr><th>상품</th><th>스토어</th><th>판매가</th><th>수수료</th><th>건당 예상</th><th>상태</th><th>발급일</th></tr></thead><tbody>{rows}</tbody></table>'


def render_replies(d: dict, today: str) -> str:
    eng = d.get("engage") or {}
    replied = eng.get("replied", [])
    today_replies = [r for r in replied if r.get("at", "").startswith(today)]
    rrows = "".join('<tr><td>%s</td><td><a href="%s" target="_blank">%s</a></td><td>%s</td><td class="sub">%s</td></tr>' % (e(r.get("at", "")[:16].replace("T", " ")), e(r.get("href", ""), quote=True), e(r.get("user", "")), e(r.get("reply", "")), e(r.get("result", ""))) for r in replied)
    drows = "".join('<li><b>%s</b> <span class="sub">%s</span><br>%s</li>' % (e(x.get("user", "")), e((x.get("post") or "")[:80]), e(x.get("reply", ""))) for x in eng.get("drafts_pending", []))
    arows = "".join('<li class="err">%s @%s: %s <a href="%s" target="_blank">보기</a></li>' % (e(a.get("at", "")[:16]), e(a.get("from", "")), e(a.get("text", "")), e(a.get("reply_permalink") or "", quote=True)) for a in eng.get("alerts", []))
    status = "정지" if eng.get("paused") else "가동"
    parts = [
        '<section class="kpis"><div class="kpi"><b>%d</b><span>오늘 단 답글 (상한 10)</span></div><div class="kpi"><b>%d</b><span>누적 답글</span></div><div class="kpi %s"><b>%s</b><span>엔진 상태</span></div><div class="kpi"><b>%d</b><span>검수 대기 초안</span></div></section>' % (len(today_replies), len(replied), "bad" if eng.get("paused") else "", status, len(eng.get("drafts_pending", []))),
        '<h2>검수 대기 초안</h2>' + ('<ul class="alerts">' + drows + '</ul>' if drows else '<p class="no">없음</p>'),
        '<h2>적대적 반응 알림</h2>' + ('<ul class="alerts">' + arows + '</ul>' if arows else '<p class="ok-text">없음</p>'),
        '<h2>단 답글</h2><table><thead><tr><th>시각</th><th>상대</th><th>답글</th><th>결과</th></tr></thead><tbody>' + (rrows or '<tr><td colspan="4" class="no">없음</td></tr>') + '</tbody></table>',
        '<p class="sub">규칙: 하루 10개, 링크·상품명 없음, 질문형·자취 주제만. 2026-10-20까지 검수 후 자동. 정지: haru/data/engage/PAUSED 파일 생성.</p>',
    ]
    return "\n".join(parts)


def alerts(d: dict) -> list[str]:
    out = []
    rev = d.get("revenue") or {}
    if (rev.get("coupang") or {}).get("status") == "needs_login":
        out.append("쿠팡 파트너스: Aside 로그인이 풀려 수익을 못 읽음")
    if (rev.get("ohouse") or {}).get("status") == "needs_login":
        out.append("오늘의집: Aside 로그인이 풀려 수익을 못 읽음")
    def _num(v):
        try:
            return int(str(v or "0").replace(",", ""))
        except ValueError:
            return 0
    # 정산 안내는 수익이 실제로 생겼을 때만 (오너 지시 2026-10-17)
    n_rev = _num(((rev.get("naver") or {}).get("sales_30d") or {}).get("expected_revenue"))
    if n_rev > 0 and ((rev.get("naver") or {}).get("settlement") or {}).get("account") == "미등록":
        out.append(f"네이버 쇼핑커넥트 예상 수익 {n_rev:,}원 발생 → 정산 계좌 등록 필요")
    o_rev = _num((rev.get("ohouse") or {}).get("expected_revenue"))
    if o_rev > 0 and (rev.get("ohouse") or {}).get("settlement_info") == "미등록":
        out.append(f"오늘의집 지급 예정 {o_rev:,}원 발생 → 정산 정보 등록 필요")
    for p in d["posts"]:
        for f in p["failed"]:
            out.append(f'게시 실패: {p["product"]} {f["channel"]} {f.get("error") or ""}')
    eng = d.get("engage") or {}
    if eng.get("paused"):
        out.append("답글 엔진 정지됨 (PAUSED). 알림을 확인하고 haru/data/engage/PAUSED 를 지우면 재개")
    if eng.get("drafts_pending"):
        out.append(f'답글 초안 {len(eng["drafts_pending"])}건 검수 대기')
    if d.get("errors"):
        out.append(f'수집 오류 {len(d["errors"])}건 (시스템 페이지)')
    return out


def build() -> Path:
    d = json.loads(DATA.read_text(encoding="utf-8"))
    gen = d.get("generated_at", "")
    acc = d.get("accounts") or {}
    th, ig = acc.get("threads") or {}, acc.get("instagram") or {}
    posts = d["posts"]
    pending = [x for p in posts for x in p["pending"]]
    failed = [x for p in posts for x in p["failed"]]
    rev = d.get("revenue") or {}
    DIST.mkdir(parents=True, exist_ok=True)

    # 요약
    al = alerts(d)
    today = gen[:10]
    today_posts = [p for p in posts if p["date"] == today]
    summary = f'''
<section class="refresh" id="refresh">
  <span class="when">최근 새로고침 <b><time data-gen="{e(gen)}">{e(gen)}</time></b><span class="ago" data-ago="{e(gen)}"></span></span>
  <button type="button" data-revenue="0" title="수집·집계·HTML만 다시 (30초 안팎)">새로고침</button>
  <button type="button" class="light" data-revenue="1" title="Aside로 판매처 수익까지 다시 읽음 (몇 분)">수익 포함 새로고침</button>
  <span class="status"></span>
</section>
<section class="kpis">
  <div class="kpi"><b>{len(posts)}</b><span>올라간 글</span></div>
  <div class="kpi"><b>{len(pending)}</b><span>예약 대기</span></div>
  <div class="kpi {"bad" if failed else ""}"><b>{len(failed)}</b><span>실패</span></div>
  <div class="kpi"><b>{fmt(th.get("views"))}</b><span>스레드 조회 · 팔로워 {fmt(th.get("followers_count"))}</span></div>
  <div class="kpi"><b>{fmt(ig.get("followers_count"))}</b><span>인스타 팔로워</span></div>
</section>
<h2>오늘 ({e(today)})</h2>
{"<p class='sub'>오늘 올라간 글 " + str(len(today_posts)) + "건</p>" + posts_table(today_posts, compact=True) if today_posts else "<p class='no'>오늘 올라간 글이 없습니다.</p>"}
{"<p class='sub'>예약 대기: " + ", ".join(e(x["channel"]) + " " + e(str(x.get("scheduled_at") or "")[:16]) for x in pending) + "</p>" if pending else ""}
<h2>확인할 것</h2>
{"<ul class='alerts'>" + "".join(f"<li>{e(a)}</li>" for a in al) + "</ul>" if al else "<p class='ok-text'>문제 없음</p>"}
<h2>수익</h2>
{revenue_cards(rev, compact=True)}
'''
    (DIST / "index.html").write_text(page("index.html", "요약", summary, gen), encoding="utf-8")

    # 게시
    body = f'<h2>게시 현황 ({len(posts)}건)</h2>{posts_table(posts)}'
    if pending:
        body += '<h2>예약 대기</h2><ul>' + "".join(f'<li>{e(x["item_id"])} · {e(x["channel"])} · {e(str(x.get("scheduled_at") or ""))}</li>' for x in pending) + '</ul>'
    (DIST / "posts.html").write_text(page("posts.html", "게시", body, gen), encoding="utf-8")

    # 답글
    (DIST / "replies.html").write_text(page("replies.html", "답글", render_replies(d, today), gen), encoding="utf-8")

    # 허브 클릭 (Cloudflare)
    hs = d.get("hub_stats") or {}
    if hs.get("status") == "ok":
        w7, w30 = hs.get("w7") or {}, hs.get("w30") or {}
        go_rows = "".join(f'<tr><td>{e(p)}</td><td>{c}</td><td>{(w30.get("go_clicks") or {}).get(p, 0)}</td></tr>' for p, c in sorted((w7.get("go_clicks") or {}).items(), key=lambda x: -x[1])) or '<tr><td colspan="3" class="no">아직 클릭 없음</td></tr>'
        ref_rows = "".join(f'<li>{e(str(k))}: {v}</li>' for k, v in sorted((w7.get("by_referer") or {}).items(), key=lambda x: -x[1])[:8])
        hub_html = f'<h2>허브 (harureviews.date)</h2><div class="cards"><div class="card"><h3>최근 7일</h3><div class="big">{w7.get("pageviews", 0)} <span class="sub">페이지뷰</span></div><div class="sub">판매처 클릭 {w7.get("go_total", 0)}</div></div><div class="card"><h3>최근 30일</h3><div class="big">{w30.get("pageviews", 0)} <span class="sub">페이지뷰</span></div><div class="sub">판매처 클릭 {w30.get("go_total", 0)}</div></div></div><h3 style="margin-top:12px">판매처 클릭 (7일 / 30일)</h3><table><thead><tr><th>go 경로</th><th>7일</th><th>30일</th></tr></thead><tbody>{go_rows}</tbody></table><h3 style="margin-top:12px">유입 경로 (7일)</h3><ul>{ref_rows or "<li class=no>없음</li>"}</ul>'
    elif hs.get("status") == "no_token":
        hub_html = '<h2>허브 (harureviews.date)</h2><p class="sub">Cloudflare API 토큰이 없어 클릭 수를 못 읽습니다 (haru/.env CLOUDFLARE_API_TOKEN).</p>'
    else:
        hub_html = f'<h2>허브 (harureviews.date)</h2><p class="err">수집 오류: {e(str(hs.get("error") or "미수집"))}</p>'

    # 수익
    body = revenue_cards(rev) + hub_html + '<h2>네이버 발급 링크</h2>' + naver_links_table(rev) + f'<p class="sub">수집 시각 {fmt(rev.get("collected_at"))} · 수동 보정은 haru/data/revenue_manual.json</p>'
    (DIST / "revenue.html").write_text(page("revenue.html", "수익", body, gen), encoding="utf-8")

    # 사진
    cells = "".join(f'<figure><img src="../../assets/posts/{e(ph["file"], quote=True)}" alt="" loading="lazy"><figcaption>{e(ph["file"])}<div class="sub">{e(ph["product"])} · {", ".join(ph["used_by"]) or "미사용"} · {ph["size_kb"]}KB</div></figcaption></figure>' for ph in d.get("photos") or [])
    (DIST / "photos.html").write_text(page("photos.html", "사진", f'<h2>게시 사진 ({len(d.get("photos") or [])}장)</h2><div class="gallery">{cells or "<p class=no>사진 없음</p>"}</div>', gen), encoding="utf-8")

    # 시스템
    s = d.get("system") or {}
    cert = s.get("hub_cert") or {}
    ev_rows = "".join(f'<tr class="{"err" if "failed" in str(ev.get("event")) else ""}"><td>{e(ev.get("ts", "")[:16].replace("T", " "))}</td><td>{e(str(ev.get("event")))}</td><td>{e(str(ev.get("channel") or ""))}</td><td>{e(str(ev.get("item_id") or ev.get("ref") or ""))}</td><td class="sub">{e(str(ev.get("error") or ev.get("result_id") or ""))}</td></tr>' for ev in sorted(d.get("events") or [], key=lambda x: x.get("ts", ""), reverse=True)[:40])
    body = f'''<h2>시스템</h2><div class="sys">
<div><b>테스트</b> {fmt(s.get("tests"))}</div><div><b>저장소</b> {fmt(s.get("git_head"))}</div>
<div><b>허브 인증서</b> {fmt(f'{cert.get("subject")} · 만료 {cert.get("not_after")}' if cert.get("subject") else cert.get("error"))}</div>
<div><b>허브 항목</b> {len(d.get("hub_items") or [])}개</div>
<div><b>예약 작업</b> haru-daily-post 06:30 · haru-dashboard 07:30</div></div>
<h2>수집 오류</h2><ul class="errs">{"".join(f"<li>{e(x)}</li>" for x in d.get("errors") or []) or "<li>없음</li>"}</ul>
<h2>최근 7일 이벤트</h2><table><thead><tr><th>시각</th><th>이벤트</th><th>채널</th><th>대상</th><th>비고</th></tr></thead><tbody>{ev_rows or "<tr><td colspan=5 class=no>없음</td></tr>"}</tbody></table>'''
    (DIST / "system.html").write_text(page("system.html", "시스템", body, gen), encoding="utf-8")
    return DIST / "index.html"


if __name__ == "__main__":
    print(f"[dashboard] wrote {build()} (+4 pages)")
