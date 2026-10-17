#!/usr/bin/env python3
"""우리 답글에 달린 반응을 보고, 적대적이면 즉시 정지(PAUSED) + 알림 기록.

  python3 haru/engage/monitor.py
Threads API: /me/threads 에서 최근 글(답글 포함) → 각 글의 /replies 를 읽어 '광고|봇|꺼져|신고|AI 티|스팸|차단' 등이 있으면
haru/data/engage/PAUSED 를 만들고 haru/data/engage/alerts.json 에 남긴다. 정지 해제는 사람이 PAUSED 를 지운다.
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
HARU = HERE.parent
sys.path.insert(0, str(HARU))
from pipeline import KST  # noqa: E402

DATA = HARU / "data" / "engage"
PAUSED = DATA / "PAUSED"
ALERTS = DATA / "alerts.json"
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
    if new_alerts:
        ALERTS.write_text(json.dumps(alerts, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        PAUSED.write_text("auto-paused " + new_alerts[0]["at"] + "\n", encoding="utf-8")
        print(f"[monitor] 적대적 반응 {len(new_alerts)}건 → 답글 엔진 정지(PAUSED). 사람이 확인 후 PAUSED 삭제.")
        for a in new_alerts:
            print(f"  ! @{a['from']}: {a['text'][:80]}  ({a['reply_permalink']})")
        return 2
    print(f"[monitor] 우리 답글 {len(replies)}건 중 {checked}건 확인, 문제 없음. 정지 상태: {PAUSED.exists()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
