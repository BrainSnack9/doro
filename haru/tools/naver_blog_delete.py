#!/usr/bin/env python3
"""네이버 블로그 글 삭제 (Aside, 오너 로그인 세션). 잘못 올라간 글을 다시 올린 뒤 옛 글을 지울 때만 쓴다.

  python3 haru/tools/naver_blog_delete.py <logNo> [--blog skekrla123] [--dry-run]
PC 글 보기 페이지의 '삭제' 를 누르고 확인창은 자동으로 승인한다. 결과: deleted | not_found | no_button | aside_error
"""
import argparse
import json
import os
import re
import subprocess
import sys

ASIDE = os.path.expanduser("~/.local/bin/aside")
ASIDE_ACCOUNT = os.environ.get("HARU_ASIDE_ACCOUNT", "u0")  # 하루 전용 Aside 계정(u0). 로이어픽은 u1 — 전역 기본 계정에 의존하지 않는다(2026-10-19)
SCRIPT = r'''
const BLOG = %(blog)s, LOGNO = %(logno)s, DRY = %(dry)s;
const pg = await openTab("about:blank");
try { await pg.goto("https://blog.naver.com/PostView.naver?blogId=" + BLOG + "&logNo=" + LOGNO, { waitUntil: "commit", timeout: 20000 }); } catch (e) {}
await sleep(7000);
const st = await pg.evaluate(() => { const vis = (e) => e.getBoundingClientRect().width > 0; const t = (document.body.innerText || ""); const btns = [...document.querySelectorAll("a, button")].filter(e => vis(e) && /^삭제$/.test((e.innerText || "").trim())).map(e => { const r = e.getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2, cls: (e.className || "").slice(0, 40) }; }); return { exists: !/존재하지 않는|삭제된 글|찾을 수 없/.test(t), title: document.title.slice(0, 40), btns }; });
console.log("STATE=" + JSON.stringify(st));
if (!st.exists) { console.log("RESULT=not_found"); }
else if (!st.btns.length) { console.log("RESULT=no_button"); }
else if (DRY) { console.log("RESULT=dry"); }
else {
  await pg.evaluate(() => { window.confirm = () => true; window.alert = () => {}; });
  const b = await pg.evaluate(() => { const es = [...document.querySelectorAll("a, button")].filter(e => e.getBoundingClientRect().width > 0 && /^삭제$/.test((e.innerText || "").trim())); const e = es[es.length - 1]; e.scrollIntoView({ block: "center" }); const r = e.getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; });
  await sleep(500); await pg.mouse.click(b.x, b.y); await sleep(5000);
  const after = await pg.evaluate(() => ({ url: location.href.slice(0, 100), txt: (document.body.innerText || "").replace(/\s+/g, " ").slice(0, 120) }));
  console.log("AFTER=" + JSON.stringify(after));
  try { await pg.goto("https://blog.naver.com/PostView.naver?blogId=" + BLOG + "&logNo=" + LOGNO, { waitUntil: "commit", timeout: 20000 }); } catch (e) {}
  await sleep(5000);
  const gone = await pg.evaluate(() => /존재하지 않는|삭제된 글|찾을 수 없|유효하지 않은/.test(document.body.innerText || ""));
  console.log("RESULT=" + (gone ? "deleted" : "still_there"));
}
await closeTab(pg); console.log("GSTACK_STEP_OK");
'''


def delete_post(logno: str, blog: str = "skekrla123", dry: bool = False) -> str:
    js = SCRIPT % {"blog": json.dumps(blog), "logno": json.dumps(str(logno)), "dry": "true" if dry else "false"}
    out = subprocess.run([ASIDE, "--account", ASIDE_ACCOUNT, "repl", js], capture_output=True, text=True, timeout=150)
    text = out.stdout + out.stderr
    for ln in text.splitlines():
        if ln.startswith(("STATE=", "AFTER=")):
            print(ln[:300])
    m = re.search(r"^RESULT=(\w+)$", text, re.M)
    return m.group(1) if m else "aside_error"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("logno"); ap.add_argument("--blog", default="skekrla123"); ap.add_argument("--dry-run", action="store_true")
    ns = ap.parse_args(); r = delete_post(ns.logno, ns.blog, ns.dry_run); print("RESULT=" + r); sys.exit(0 if r in ("deleted", "dry") else 1)
