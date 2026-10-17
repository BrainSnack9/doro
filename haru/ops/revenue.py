#!/usr/bin/env python3
"""제휴 수익 수집 (Aside, 오너 로그인 세션) → haru/data/revenue.json

- 네이버 쇼핑커넥트: 판매 실적(클릭·주문·판매금액·예상수익), 발급 링크별 예상 수익, 정산 현황
- 쿠팡 파트너스: 리포트 페이지 (Aside 에 쿠팡 로그인이 없으면 needs_login)
- 오늘의집 이웃 큐레이터: https://ohou.se/curator/activity (이번달 방문·주문·지급 예정, 누적 지급). 로그인 없으면 needs_login
- 수동 보정: haru/data/revenue_manual.json
읽기만 한다. 로그아웃·설정 페이지는 절대 건드리지 않는다.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
HARU = HERE.parent
sys.path.insert(0, str(HARU))
from pipeline import KST  # noqa: E402

ASIDE = os.path.expanduser("~/.local/bin/aside")
OUT = HARU / "data" / "revenue.json"
MANUAL = HARU / "data" / "revenue_manual.json"
NAVER_SPACE = "1007223033163008"

SCRIPT = r'''
const pg = await openTab("about:blank");
const txtOf = () => pg.evaluate(() => (document.body.innerText||"").replace(/\s+/g," "));
const res = { naver: {}, coupang: {}, ohouse: {} };
// 네이버 판매 실적 (최근 30일 기본)
try { await pg.goto("https://brandconnect.naver.com/%(space)s/affiliate/sales-dashboard", { waitUntil: "commit", timeout: 20000 }); } catch (e) {}
await sleep(9000);
let t = await txtOf();
const pick = (re) => { const m = t.match(re); return m ? m[1] : null; };
res.naver.sales_30d = { clicks: pick(/클릭 수 ([\d,]+)회/), orders: pick(/상품주문 건수 ([\d,]+)건/), sold_count: pick(/판매 개수 ([\d,]+)개/), sales_amount: pick(/판매 금액 ([\d,]+)원/), expected_revenue: pick(/예상 수익 ([\d,]+)원/), updated: pick(/최근 업데이트 : ([\d. ]+\d)/), period: (t.match(/기간 (\d{4}-\d{2}-\d{2}) (\d{4}-\d{2}-\d{2})/)||[]).slice(1).join("~") };
// 발급 링크
try { await pg.goto("https://brandconnect.naver.com/%(space)s/affiliate/products-link", { waitUntil: "commit", timeout: 20000 }); } catch (e) {}
await sleep(8000);
res.naver.links = await pg.evaluate(() => [...document.querySelectorAll("table tbody tr")].map(tr => [...tr.querySelectorAll("td")].map(td => (td.innerText||"").trim().replace(/\s+/g," "))).filter(r => r.length >= 6).map(r => ({ name: r[0].slice(0, 60), store: r[1], price: r[2], commission: r[3], expected: r[4], status: r[5], issued: r[6] })));
// 정산
try { await pg.goto("https://brandconnect.naver.com/%(space)s/settlement/affiliate", { waitUntil: "commit", timeout: 20000 }); } catch (e) {}
await sleep(8000);
t = await txtOf();
res.naver.settlement = { paid_total: pick(/누적 지급 금액 \(세후\) ([\d,]+)원/), confirmed: pick(/수익 확정 금액 \(세전\) ([\d,]+)원/), pending: pick(/지급 대기 금액 \(세후\) ([\d,]+)원/), account: /등록된 계좌가 없습니다/.test(t) ? "미등록" : "등록" };
// 오늘의집 이웃 큐레이터
try { await pg.goto("https://ohou.se/curator/activity", { waitUntil: "commit", timeout: 20000 }); } catch (e) {}
await sleep(8000);
t = await txtOf();
if (/sign_in|로그인 회원가입/.test(pg.url() + " " + t.slice(0, 300)) && !/큐레이터 활동/.test(t)) { res.ohouse = { status: "needs_login" }; }
else { res.ohouse = { status: "ok", period: pick(/이번달 현황 ([\d년월일 ~]+?) 방문/), visits: pick(/방문 ([\d,]+) 회/), orders: pick(/주문 ([\d,]+) 건/), expected_revenue: pick(/주문 [\d,]+ 건 ([\d,]+) 원 지급 예정/), paid_total: pick(/총 누적 금액 ([\d,]+) 원/), settlement_info: /정산을 위한 정보를 입력해주세요/.test(t) ? "미등록" : "등록", grade: pick(/이웃 큐레이터 리워드 ([\d.]+%)/) }; }
// 쿠팡
try { await pg.goto("https://partners.coupang.com/#affiliate/ws/report", { waitUntil: "commit", timeout: 20000 }); } catch (e) {}
await sleep(9000);
t = await txtOf();
if (/login\.coupang\.com/.test(pg.url()) || /비밀번호 찾기/.test(t)) { res.coupang = { status: "needs_login" }; }
else { res.coupang = { status: "ok", url: pg.url().slice(0, 80), text: t.slice(0, 1500), tables: await pg.evaluate(() => [...document.querySelectorAll("table")].slice(0, 3).map(tb => [...tb.querySelectorAll("tr")].slice(0, 8).map(tr => [...tr.querySelectorAll("th,td")].map(c => (c.innerText||"").trim().replace(/\s+/g," ").slice(0, 20))))) }; }
console.log("REVENUE=" + JSON.stringify(res));
await closeTab(pg);
console.log("GSTACK_STEP_OK");
'''


def main() -> int:
    out = subprocess.run([ASIDE, "repl", SCRIPT % {"space": NAVER_SPACE}], capture_output=True, text=True, timeout=240)
    text = out.stdout + out.stderr
    m = re.search(r"^REVENUE=(.*)$", text, re.M)
    data = {"collected_at": datetime.now(KST).isoformat(timespec="seconds")}
    if m:
        data.update(json.loads(m.group(1)))
    else:
        data["error"] = "Aside 수집 실패: " + text[-300:].strip()
    if MANUAL.exists():
        try:
            data["manual"] = json.loads(MANUAL.read_text(encoding="utf-8"))
        except ValueError:
            data["manual_error"] = "revenue_manual.json 파싱 실패"
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"[revenue] naver={data.get('naver', {}).get('sales_30d')} ohouse={data.get('ohouse')} coupang={data.get('coupang', {}).get('status')} -> {OUT}")
    return 0 if m else 1


if __name__ == "__main__":
    sys.exit(main())
