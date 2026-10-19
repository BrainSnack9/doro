#!/usr/bin/env python3
"""승인된 답글을 스레드에 단다 (Aside, 하루 계정 UI) → haru/data/engage/replied.json 에 기록

  python3 haru/engage/reply.py haru/data/engage/drafts-2026-10-17.json [--only CODE,CODE] [--dry-run]

drafts 파일 형식: {"items": [{"code": "...", "href": "...", "user": "@...", "reply": "답글 본문", "approved": true, "answer": false}]}
approved 가 true 인 것만, 하루 상한(10개) 안에서, 정지 파일(haru/data/engage/PAUSED)이 없을 때만 단다.
answer: true 는 우리 답글에 사람이 답해온 것에 다시 답하는 '답장'이다. 하루 상한(새 답글 10개)과 따로 세고(답장 상한 10),
href 는 그 사람의 답변 글 permalink 다. 답장은 자동화 이후에도 오너가 초안을 보고 승인한 것만 올린다(2026-10-17 오너 지시).
절차: 글 열기 → "…님에게 답글 남기기" 칸 클릭 → 타이핑 → "게시" 클릭 → 우리 답글이 보이는지 확인.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
HARU = HERE.parent
sys.path.insert(0, str(HARU))
from pipeline import KST, metrics  # noqa: E402

ASIDE = os.path.expanduser("~/.local/bin/aside")
ASIDE_ACCOUNT = os.environ.get("HARU_ASIDE_ACCOUNT", "u0")  # 하루 전용 Aside 계정(u0). 로이어픽은 u1 — 전역 기본 계정에 의존하지 않는다(2026-10-19)
DATA = HARU / "data" / "engage"
REPLIED = DATA / "replied.json"
PAUSED = DATA / "PAUSED"
DAILY_LIMIT = 10
ANSWER_LIMIT = 10
RESPONSES = DATA / "responses.json"
MAX_LEN = 300

SCRIPT = r'''
const JOB = %(job)s;
const pg = await openTab("about:blank");
try { await pg.goto(JOB.href, { waitUntil: "commit", timeout: 20000 }); } catch (e) {}
await sleep(7000);
const box = await pg.evaluate(() => { const el = [...document.querySelectorAll("*")].find(e => e.getBoundingClientRect().width > 0 && e.children.length === 0 && /님에게 답글 남기기/.test(e.innerText||"")); if (!el) return null; const r = el.getBoundingClientRect(); return { x: r.x + 10, y: r.y + r.height/2, who: (el.innerText||"").trim().slice(0, 40) }; });
console.log("BOX=" + JSON.stringify(box));
if (!box || !box.who.startsWith(JOB.user.slice(1))) { console.log("RESULT=no_box"); await closeTab(pg); console.log("GSTACK_STEP_OK"); }
else {
  await pg.mouse.click(box.x, box.y); await sleep(1200);
  await pg.keyboard.type(JOB.reply); await sleep(800);
  const typed = await pg.evaluate(() => (document.activeElement && document.activeElement.innerText || "").trim());
  console.log("TYPED=" + JSON.stringify(typed.slice(0, 80)));
  if (typed.replace(/\s+/g, " ") !== JOB.reply.replace(/\s+/g, " ")) { console.log("RESULT=typed_mismatch"); await pg.keyboard.press("Escape"); await closeTab(pg); console.log("GSTACK_STEP_OK"); }
  else {
    // 게시 버튼: 작성 칸(활성 에디터) 컨테이너 안의, 글자 없는 아이콘 버튼 중 맨 오른쪽 것
    const post = await pg.evaluate(() => { let c = document.activeElement; for (let k = 0; k < 8 && c; k++) { c = c.parentElement; if (c && c.querySelectorAll("div[role=button], button").length >= 1 && c.getBoundingClientRect().height < 220) { const btns = [...c.querySelectorAll("div[role=button], button")].filter(b => b.getBoundingClientRect().width > 0 && b.getAttribute("aria-disabled") !== "true"); if (btns.length) { const b = btns.sort((a, z) => z.getBoundingClientRect().x - a.getBoundingClientRect().x)[0]; const r = b.getBoundingClientRect(); return { x: r.x + r.width/2, y: r.y + r.height/2, label: (b.getAttribute("aria-label")||b.innerText||"").trim().slice(0, 20), n: btns.length }; } } } return null; });
    console.log("POSTBTN=" + JSON.stringify(post));
    const verify = async () => pg.evaluate((snippet) => { const t = document.body.innerText||""; return t.includes(snippet) && !(document.activeElement && (document.activeElement.innerText||"").includes(snippet)); }, JOB.reply.slice(0, 20));
    let ok = false;
    if (post) { await pg.mouse.click(post.x, post.y); await sleep(6000); ok = await verify(); }
    if (!ok) { await pg.keyboard.press("Meta+Enter"); await sleep(6000); ok = await verify(); }
    console.log("RESULT=" + (ok ? "posted" : "unverified"));
    if (!ok) { await pg.keyboard.press("Escape"); }
    await closeTab(pg); console.log("GSTACK_STEP_OK");
  }
}
'''


def load_replied() -> dict:
    return json.loads(REPLIED.read_text(encoding="utf-8")) if REPLIED.exists() else {}


def _token() -> str:
    tok = os.environ.get("THREADS_ACCESS_TOKEN", "")
    if not tok and (HARU / ".env").exists():
        for ln in (HARU / ".env").read_text(encoding="utf-8").splitlines():
            if ln.startswith("THREADS_ACCESS_TOKEN="):
                tok = ln.split("=", 1)[1].strip().strip('"').strip("'")
    return tok


def api_posted(text: str) -> bool:
    """페이지 확인이 실패했을 때 Threads API(/me/replies)로 우리 답글이 올라갔는지 2차 확인. 2026-10-17 밤 7건이 전부 unverified 로 나왔지만 실제로는 다 올라가 있었다."""
    tok = _token()
    if not tok:
        return False
    try:
        u = "https://graph.threads.net/v1.0/me/replies?" + urllib.parse.urlencode({"fields": "text,timestamp", "limit": 15, "access_token": tok})
        with urllib.request.urlopen(u, timeout=30) as resp:  # noqa: S310
            data = json.load(resp).get("data", [])
    except Exception:  # noqa: BLE001
        return False
    head = text[:20].replace(" ", "")
    return any((d.get("text") or "").replace(" ", "").startswith(head) for d in data)


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
        job = {"href": it["href"], "user": it["user"], "reply": text}
        out = subprocess.run([ASIDE, "--account", ASIDE_ACCOUNT, "repl", SCRIPT.replace("%(job)s", json.dumps(job, ensure_ascii=False))], capture_output=True, text=True, timeout=180)
        txt = out.stdout + out.stderr
        m = re.search(r"^RESULT=(\w+)$", txt, re.M)
        result = m.group(1) if m else "aside_error"
        if result in ("unverified", "aside_error") and api_posted(text):
            result = "posted"
        print(f"[reply] {it['user']} -> {result}")
        now = datetime.now(KST).isoformat(timespec="seconds")
        metrics.append({"ts": now, "event": "reply" if result == "posted" else "reply_failed", "channel": "threads", "ref": it["href"], "user": it["user"], "result": result})
        if result in ("posted", "unverified"):
            replied[it["code"]] = {"user": it["user"], "href": it["href"], "reply": text, "at": now, "result": result, "answer": is_answer}
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
