#!/usr/bin/env python3
"""승인된 답글을 스레드에 단다 (Aside, 하루 계정 UI) → haru/data/engage/replied.json 에 기록

  python3 haru/engage/reply.py haru/data/engage/drafts-2026-10-17.json [--only CODE,CODE] [--dry-run]

drafts 파일 형식: {"items": [{"code": "...", "href": "...", "user": "@...", "reply": "답글 본문", "approved": true}]}
approved 가 true 인 것만, 하루 상한(10개) 안에서, 정지 파일(haru/data/engage/PAUSED)이 없을 때만 단다.
절차: 글 열기 → "…님에게 답글 남기기" 칸 클릭 → 타이핑 → "게시" 클릭 → 우리 답글이 보이는지 확인.
"""
import argparse
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
from pipeline import KST, metrics  # noqa: E402

ASIDE = os.path.expanduser("~/.local/bin/aside")
DATA = HARU / "data" / "engage"
REPLIED = DATA / "replied.json"
PAUSED = DATA / "PAUSED"
DAILY_LIMIT = 10
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
    const post = await pg.evaluate(() => { const b = [...document.querySelectorAll("div[role=button], button")].find(e => e.getBoundingClientRect().width > 0 && /^게시$/.test((e.innerText||"").trim()) && e.getAttribute("aria-disabled") !== "true"); if (!b) return null; const r = b.getBoundingClientRect(); return { x: r.x + r.width/2, y: r.y + r.height/2 }; });
    console.log("POSTBTN=" + JSON.stringify(post));
    if (!post) { console.log("RESULT=no_post_button"); await pg.keyboard.press("Escape"); }
    else {
      await pg.mouse.click(post.x, post.y); await sleep(6000);
      const ok = await pg.evaluate((snippet) => (document.body.innerText||"").includes(snippet), JOB.reply.slice(0, 20));
      console.log("RESULT=" + (ok ? "posted" : "unverified"));
    }
    await closeTab(pg); console.log("GSTACK_STEP_OK");
  }
}
'''


def load_replied() -> dict:
    return json.loads(REPLIED.read_text(encoding="utf-8")) if REPLIED.exists() else {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("drafts"); ap.add_argument("--only", default=""); ap.add_argument("--dry-run", action="store_true")
    ns = ap.parse_args()
    if PAUSED.exists():
        print("[reply] 정지 상태 (haru/data/engage/PAUSED 있음). 아무것도 안 함."); return 2
    drafts = json.loads(Path(ns.drafts).read_text(encoding="utf-8"))
    only = {c.strip() for c in ns.only.split(",") if c.strip()}
    replied = load_replied()
    today = datetime.now(KST).strftime("%Y-%m-%d")
    today_count = sum(1 for r in replied.values() if r.get("at", "").startswith(today))
    done = 0
    for it in drafts.get("items", []):
        if not it.get("approved") or (only and it["code"] not in only) or it["code"] in replied:
            continue
        if today_count + done >= DAILY_LIMIT:
            print("[reply] 오늘 상한 도달"); break
        text = it["reply"].strip()
        if len(text) > MAX_LEN or "http" in text or re.search(r"쿠팡|naver\.me|ozip|링크", text):
            print(f"[reply] 규칙 위반으로 건너뜀: {it['code']}"); continue
        if ns.dry_run:
            print(f"[DRY] {it['user']} {it['href']}\n      {text}"); continue
        job = {"href": it["href"], "user": it["user"], "reply": text}
        out = subprocess.run([ASIDE, "repl", SCRIPT.replace("%(job)s", json.dumps(job, ensure_ascii=False))], capture_output=True, text=True, timeout=180)
        txt = out.stdout + out.stderr
        m = re.search(r"^RESULT=(\w+)$", txt, re.M)
        result = m.group(1) if m else "aside_error"
        print(f"[reply] {it['user']} -> {result}")
        now = datetime.now(KST).isoformat(timespec="seconds")
        metrics.append({"ts": now, "event": "reply" if result == "posted" else "reply_failed", "channel": "threads", "ref": it["href"], "user": it["user"], "result": result})
        if result in ("posted", "unverified"):
            replied[it["code"]] = {"user": it["user"], "href": it["href"], "reply": text, "at": now, "result": result}
            REPLIED.write_text(json.dumps(replied, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            done += 1
    print(f"[reply] 완료 {done}건 (오늘 누적 {today_count + done}/{DAILY_LIMIT})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
