#!/usr/bin/env python3
"""우리 답글에 달린 반응을 보고, 적대적이면 즉시 정지(PAUSED) + 알림 기록.

  python3 haru/engage/monitor.py
Threads API: /me/threads 에서 최근 글(답글 포함) → 각 글의 /replies 를 읽어 '광고|봇|꺼져|신고|AI 티|스팸|차단' 등이 있으면
haru/data/engage/PAUSED 를 만들고 haru/data/engage/alerts.json 에 남긴다. 정지 해제는 사람이 PAUSED 를 지운다.

API 가 못 보는 것(2026-10-17 확인): 남의 글 안에서 우리 답글에 달린 답변. 그래서 최근 48시간 우리 답글은 Aside 로 페이지를 열어
(page.read_children) 답변을 읽는다. 적대적이면 위와 같이 정지, 아니면 haru/data/engage/responses.json 에 모아 둔다
(답장은 오너가 초안을 보고 승인한 것만 올린다 — 자동화 이후에도 예외 없음, 2026-10-17 오너 지시). --no-aside 로 끌 수 있다.
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
HARU = HERE.parent
sys.path.insert(0, str(HARU))
from pipeline import KST  # noqa: E402

DATA = HARU / "data" / "engage"
PAUSED = DATA / "PAUSED"
ALERTS = DATA / "alerts.json"
RESPONSES = DATA / "responses.json"
ASIDE_LOOKBACK_HOURS = 48
ASIDE_MAX_PAGES = 14
HOSTILE = re.compile(r"광고|홍보|봇이|봇임|봇 아|AI 티|ai 티|인공지능|꺼져|신고|스팸|차단|불편|기분 나쁘|역겹|짜증|그만|하지 마|하지마|소름")


def env() -> dict:
    out = dict(os.environ)
    p = HARU / ".env"
    if p.exists():
        for ln in p.read_text(encoding="utf-8").splitlines():
            if "=" in ln and not ln.strip().startswith("#"):
                k, v = ln.split("=", 1); out.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return out


def get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=20) as r:  # noqa: S310
        return json.load(r)


def main() -> int:
    e = env(); tok = urllib.parse.quote(e.get("THREADS_ACCESS_TOKEN", ""))
    if not tok:
        print("[monitor] 토큰 없음"); return 1
    # 답글은 /me/replies 에 따로 나온다 (UI 로 단 답글 포함)
    try:
        replies = get(f"https://graph.threads.net/v1.0/me/replies?fields=id,text,permalink,timestamp,replied_to&limit=50&access_token={tok}").get("data", [])
    except Exception as ex:  # noqa: BLE001
        print(f"[monitor] /me/replies 실패: {str(ex)[:120]}")
        mine = get(f"https://graph.threads.net/v1.0/me/threads?fields=id,text,is_reply,permalink,timestamp&limit=50&access_token={tok}").get("data", [])
        replies = [m for m in mine if m.get("is_reply")]
    alerts = json.loads(ALERTS.read_text(encoding="utf-8")) if ALERTS.exists() else []
    seen = {(a["reply_id"], a["response_id"]) for a in alerts}
    new_alerts, checked = [], 0
    for r in replies:
        try:
            resp = get(f"https://graph.threads.net/v1.0/{r['id']}/replies?fields=id,text,username,timestamp&access_token={tok}").get("data", [])
        except Exception as ex:  # noqa: BLE001
            print(f"[monitor] {r['id']} 응답 조회 실패: {str(ex)[:80]}"); continue
        checked += 1
        for x in resp:
            if (r["id"], x["id"]) in seen:
                continue
            t = x.get("text") or ""
            if HOSTILE.search(t):
                a = {"at": datetime.now(KST).isoformat(timespec="seconds"), "reply_id": r["id"], "reply_permalink": r.get("permalink"), "response_id": x["id"], "from": x.get("username"), "text": t[:200]}
                new_alerts.append(a); alerts.append(a)
    # Aside 로 화면을 읽어 API 가 못 보는 답변을 확인한다
    aside_checked = 0
    if "--no-aside" not in sys.argv:
        try:
            from engage import page  # noqa: WPS433
        except ImportError:
            sys.path.insert(0, str(HERE)); import page  # type: ignore  # noqa: E401
        responses = json.loads(RESPONSES.read_text(encoding="utf-8")) if RESPONSES.exists() else {}
        since = (datetime.now(KST) - timedelta(hours=ASIDE_LOOKBACK_HOURS)).strftime("%Y-%m-%dT%H:%M:%S")
        recent = [r for r in replies if (r.get("timestamp") or "").replace("+0000", "") >= since][:ASIDE_MAX_PAGES]
        for r in recent:
            if not r.get("permalink"):
                continue
            try:
                kids = page.read_children(r["permalink"])
            except Exception as ex:  # noqa: BLE001
                print(f"[monitor] 페이지 읽기 실패 {r['permalink']}: {str(ex)[:80]}"); continue
            aside_checked += 1
            for k in kids:
                key = k["code"]
                if HOSTILE.search(k["text"]) and (r["id"], key) not in seen:
                    a = {"at": datetime.now(KST).isoformat(timespec="seconds"), "reply_id": r["id"], "reply_permalink": r.get("permalink"), "response_id": key, "from": k["user"], "text": k["text"][:200], "via": "aside"}
                    new_alerts.append(a); alerts.append(a)
                if key not in responses:
                    responses[key] = {"from": k["user"], "href": k["href"], "text": k["text"][:300], "time": k.get("time", ""), "to_reply": r.get("permalink"), "our_reply": (r.get("text") or "")[:80], "seen_at": datetime.now(KST).isoformat(timespec="seconds"), "answered": False}
        RESPONSES.write_text(json.dumps(responses, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        unanswered = [v for v in responses.values() if not v.get("answered")]
        if unanswered:
            print(f"[monitor] 답장 안 한 답변 {len(unanswered)}건 (responses.json). 초안을 오너에게 보여주고 승인 뒤 reply.py 로 올린다:")
            for v in unanswered[:10]:
                print(f"  · {v['from']}: {v['text'][:70]}  ← 우리: {v['our_reply'][:30]}")
    if new_alerts:
        ALERTS.write_text(json.dumps(alerts, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        PAUSED.write_text("auto-paused " + new_alerts[0]["at"] + "\n", encoding="utf-8")
        print(f"[monitor] 적대적 반응 {len(new_alerts)}건 → 답글 엔진 정지(PAUSED). 사람이 확인 후 PAUSED 삭제.")
        for a in new_alerts:
            print(f"  ! @{a['from']}: {a['text'][:80]}  ({a['reply_permalink']})")
        return 2
    print(f"[monitor] 우리 답글 {len(replies)}건 중 API {checked}건 · 화면 {aside_checked}건 확인, 문제 없음. 정지 상태: {PAUSED.exists()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
