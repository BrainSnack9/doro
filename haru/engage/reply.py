#!/usr/bin/env python3
"""승인된 답글을 스레드에 단다 (Aside, 하루 계정 UI) → haru/data/engage/replied.json 에 기록

  python3 haru/engage/reply.py haru/data/engage/drafts-2026-10-17.json [--only CODE,CODE] [--dry-run]

drafts 파일 형식: {"items": [{"code": "...", "href": "...", "user": "@...", "reply": "답글 본문", "approved": true, "answer": false}]}
approved 가 true 인 것만, 하루 상한(10개) 안에서, 정지 파일(haru/data/engage/PAUSED)이 없을 때만 단다.
answer: true 는 우리 답글에 사람이 답해온 것에 다시 답하는 '답장'이다. 하루 상한(새 답글 10개)과 따로 세고(답장 상한 10),
href 는 그 사람의 답변 글 permalink 다. 답장은 자동화 이후에도 오너가 초안을 보고 승인한 것만 올린다(2026-10-17 오너 지시).
절차(공용 코어 iris.engage.reply): 글 열기 → 로그인 계정이 @haru.reviews 인지 확인 → "…님에게 답글 남기기" 칸 클릭 → 타이핑 → "게시" 클릭 →
우리 답글이 보이는지 확인 → 안 보이면 API /me/replies 로 2차 확인. 확인 안 된 답글(unverified)도 기록해 다시 달지 않는다.
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
HARU = HERE.parent
sys.path.insert(0, str(HARU))
from pipeline import KST, metrics  # noqa: E402
from iris.engage.reply import post_reply  # noqa: E402  (공용 코어: Aside 화면 입력 + 화면·API 게시 확인)

ASIDE_ACCOUNT = os.environ.get("HARU_ASIDE_ACCOUNT", "u0")  # 하루 전용 Aside 계정(u0). 로이어픽은 u2, u1 은 에듀씨어 블로그
OUR = "haru.reviews"
DATA = HARU / "data" / "engage"
REPLIED = DATA / "replied.json"
PAUSED = DATA / "PAUSED"
DAILY_LIMIT = 15  # 2026-10-21 오너: 성장이 더디다 → 10→15 (09·14·20시 3회, 회당 5)
ANSWER_LIMIT = 10
RESPONSES = DATA / "responses.json"
MAX_LEN = 300

def load_replied() -> dict:
    return json.loads(REPLIED.read_text(encoding="utf-8")) if REPLIED.exists() else {}


def _token() -> str:
    tok = os.environ.get("THREADS_ACCESS_TOKEN", "")
    if not tok and (HARU / ".env").exists():
        for ln in (HARU / ".env").read_text(encoding="utf-8").splitlines():
            if ln.startswith("THREADS_ACCESS_TOKEN="):
                tok = ln.split("=", 1)[1].strip().strip('"').strip("'")
    return tok


def _page():
    try:
        from engage import page  # noqa: WPS433
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parent)); import page  # type: ignore  # noqa: E401
    return page


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("drafts"); ap.add_argument("--only", default=""); ap.add_argument("--dry-run", action="store_true")
    ns = ap.parse_args()
    if PAUSED.exists():
        print("[reply] 정지 상태 (haru/data/engage/PAUSED 있음). 아무것도 안 함."); return 2
    if not ns.dry_run:
        _page().require_owner()  # 하루 계정(u0)에 @haru.reviews 로그인 확인. 아니면 종료 3
    drafts = json.loads(Path(ns.drafts).read_text(encoding="utf-8"))
    only = {c.strip() for c in ns.only.split(",") if c.strip()}
    replied = load_replied()
    today = datetime.now(KST).strftime("%Y-%m-%d")
    today_count = sum(1 for r in replied.values() if r.get("at", "").startswith(today) and not r.get("answer"))
    today_answers = sum(1 for r in replied.values() if r.get("at", "").startswith(today) and r.get("answer"))
    done = answered = 0
    for it in drafts.get("items", []):
        if not it.get("approved") or (only and it["code"] not in only) or it["code"] in replied:
            continue
        is_answer = bool(it.get("answer"))
        if is_answer and today_answers + answered >= ANSWER_LIMIT:
            print("[reply] 오늘 답장 상한 도달"); continue
        if not is_answer and today_count + done >= DAILY_LIMIT:
            print("[reply] 오늘 상한 도달"); break
        text = it["reply"].strip()
        if len(text) > MAX_LEN or "http" in text or re.search(r"쿠팡|naver\.me|ozip|링크", text):
            print(f"[reply] 규칙 위반으로 건너뜀: {it['code']}"); continue
        if ns.dry_run:
            print(f"[DRY] {it['user']} {it['href']}\n      {text}"); continue
        # 화면 입력 → 화면 확인 → 안 되면 API(/me/replies) 2차 확인(2026-10-17 밤 7건이 unverified 로 나왔지만 실제론 다 올라가 있었다). 코어가 처리.
        res = post_reply(it["href"], it["user"], text, OUR, ASIDE_ACCOUNT, _token())
        result, reply_id = res["result"], res["reply_id"]
        if result == "wrong_account":
            print(f"[reply] Aside {ASIDE_ACCOUNT} 의 스레드 로그인 계정이 @{OUR} 가 아님 → 중단"); break
        print(f"[reply] {it['user']} -> {result}")
        now = datetime.now(KST).isoformat(timespec="seconds")
        metrics.append({"ts": now, "event": "reply" if result == "posted" else "reply_failed", "channel": "threads", "ref": it["href"], "user": it["user"], "result": result})
        if result in ("posted", "unverified"):
            replied[it["code"]] = {"user": it["user"], "href": it["href"], "reply": text, "at": now, "result": result, "answer": is_answer, "reply_id": reply_id}
            REPLIED.write_text(json.dumps(replied, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            if is_answer:
                answered += 1
                if RESPONSES.exists():
                    resp = json.loads(RESPONSES.read_text(encoding="utf-8"))
                    if it["code"] in resp:
                        resp[it["code"]]["answered"] = True; resp[it["code"]]["answered_at"] = now
                        RESPONSES.write_text(json.dumps(resp, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            else:
                done += 1
    print(f"[reply] 완료 새 답글 {done}건 (오늘 누적 {today_count + done}/{DAILY_LIMIT}) · 답장 {answered}건 (오늘 누적 {today_answers + answered}/{ANSWER_LIMIT})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
