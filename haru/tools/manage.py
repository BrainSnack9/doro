#!/usr/bin/env python3
"""게시물 관리 CLI: 스레드 삭제(API), 인스타 삭제(Aside 브라우저), 큐 아이템 재게시.

예:
  python3 haru/tools/manage.py threads-delete 18085106534321785
  python3 haru/tools/manage.py ig-delete https://www.instagram.com/p/DelTszoj-vU/
  python3 haru/tools/manage.py threads-ui-delete https://www.threads.com/@haru.reviews/post/DelTptWD9b4   # API 403 일 때
  python3 haru/tools/manage.py repost 2026-10-17-trolley-v2-threads   # scheduled_at 을 지금으로 바꾸고 run_daily 실행

스레드·인스타 모두 "수정" API 가 없으므로 수정 = 삭제 후 재게시.
환경변수는 haru/.env 를 셸에 올린 뒤 실행한다 (set -a; source haru/.env; set +a).
"""

import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HARU = HERE.parent
sys.path.insert(0, str(HARU))

from pipeline import queue  # noqa: E402
from pipeline.threads_client import ThreadsClient  # noqa: E402

ASIDE = os.path.expanduser("~/.local/bin/aside")
KST = datetime.timezone(datetime.timedelta(hours=9))


THREADS_UI_DELETE_SCRIPT = r'''
const pg = await openTab("about:blank");
await pg.goto("%(url)s");
await sleep(4500);
const opt = await pg.evaluate(() => { const svgs = [...document.querySelectorAll("svg")].map(e => ({ e, r: e.getBoundingClientRect() })).filter(o => o.r.width >= 18 && o.r.width <= 22 && o.r.y > 60 && o.r.y < 260 && o.r.x > 900 && !o.e.getAttribute("aria-label")); const s = svgs[0]; return s ? { x: s.r.x + s.r.width/2, y: s.r.y + s.r.height/2 } : null });
console.log("OPT=" + JSON.stringify(opt));
if (opt) {
  await pg.mouse.click(opt.x, opt.y); await sleep(1500);
  const del = await pg.evaluate(() => { const el = [...document.querySelectorAll("[role=menuitem], [role=menu] div, [role=dialog] div")].find(b => /^삭제$/.test((b.innerText||"").trim())); if (!el) return null; const r = el.getBoundingClientRect(); return { x: r.x + r.width/2, y: r.y + r.height/2 } });
  console.log("DEL_ITEM=" + JSON.stringify(del));
  if (del) { await pg.mouse.click(del.x, del.y); await sleep(2500);
    const conf = await pg.evaluate(() => { const dlg = [...document.querySelectorAll("[role=dialog],[role=alertdialog]")].pop(); const scope = dlg || document; const el = [...scope.querySelectorAll("button, [role=button], div[tabindex]")].find(b => /^삭제$/.test((b.innerText||"").trim())); if (!el) return null; const r = el.getBoundingClientRect(); return { x: r.x + r.width/2, y: r.y + r.height/2 } });
    console.log("CONFIRM=" + JSON.stringify(conf));
    if (conf) { await pg.mouse.click(conf.x, conf.y); await sleep(4000); console.log("CONFIRMED=true"); } }
}
console.log("URL_AFTER=" + pg.url());
await closeTab(pg);
console.log("GSTACK_STEP_OK");
'''


def threads_ui_delete(permalink: str, dry_run: bool) -> int:
    """threads.com 게시물 페이지에서 옵션(…) → 삭제 → 확인. Aside 에 하루 스레드 로그인이 있어야 한다.
    API 삭제가 403(권한 없음)일 때의 대체 경로. 실제 마우스 클릭(pg.mouse.click)이어야 React 핸들러가 동작한다."""
    if dry_run:
        print(f"[DRY-RUN] aside repl: {permalink} 에서 옵션 → 삭제 → 확인 클릭")
        return 0
    if not os.path.exists(ASIDE):
        print("aside CLI 가 없습니다 (~/.local/bin/aside)")
        return 2
    out = subprocess.run([ASIDE, "repl", THREADS_UI_DELETE_SCRIPT % {"url": permalink}], capture_output=True, text=True, timeout=180)
    text = out.stdout + out.stderr
    print(text[-800:])
    ok = "CONFIRMED=true" in text and "GSTACK_STEP_OK" in text
    print(f"[{'OK' if ok else 'FAIL'}] threads(UI) {permalink} 삭제")
    if ok:
        _mark_deleted("threads", permalink)
    return 0 if ok else 1


def threads_delete(post_id: str, dry_run: bool) -> int:
    uid = os.environ.get("THREADS_USER_ID") or ("dry-run" if dry_run else "")
    tok = os.environ.get("THREADS_ACCESS_TOKEN") or ("dry-run" if dry_run else "")
    if not (uid and tok):
        print("THREADS_USER_ID / THREADS_ACCESS_TOKEN 이 비어 있습니다. set -a; source haru/.env; set +a")
        return 2
    c = ThreadsClient(uid, tok, dry_run)
    try:
        ok = c.delete(post_id)
    except RuntimeError as e:
        if "permission" in str(e).lower():
            print("API 삭제 권한 없음(403). threads-ui-delete <permalink> 로 Aside 삭제를 쓰세요.")
            return 3
        raise
    print(f"[{'OK' if ok else 'FAIL'}] threads {post_id} 삭제")
    if ok and not dry_run:
        _mark_deleted("threads", post_id)
    return 0 if ok else 1


IG_DELETE_SCRIPT = r'''
const pg = await openTab("about:blank");
await pg.goto("%(url)s");
await sleep(4000);
const clickByText = async (re) => pg.evaluate((src) => {
  const re = new RegExp(src);
  const el = [...document.querySelectorAll("button,[role=button],[role=menuitem],svg[aria-label]")]
    .find(e => re.test((e.innerText || e.getAttribute("aria-label") || "").trim()));
  if (!el) return false;
  (el.closest("button,[role=button],[role=menuitem]") || el).click();
  return true;
}, re.source);
const opened = await clickByText(/^(옵션 더 보기|More options)$/);
console.log("MENU=" + opened);
await sleep(1500);
const del1 = await clickByText(/^(삭제|Delete)$/);
console.log("DELETE1=" + del1);
await sleep(1500);
const del2 = await clickByText(/^(삭제|Delete)$/);
console.log("DELETE2=" + del2);
await sleep(3000);
console.log("URL=" + pg.url());
await pg.screenshot({ path: "ig-delete.jpg", type: "jpeg", quality: 50 });
console.log("ASIDE_DIR=" + pwd);
await closeTab(pg);
console.log("GSTACK_STEP_OK");
'''


def ig_delete(permalink: str, dry_run: bool) -> int:
    """instagram.com 게시물 페이지에서 옵션 더 보기 → 삭제 → 삭제 확인. Aside 에 하루 인스타 로그인이 있어야 한다."""
    if dry_run:
        print(f"[DRY-RUN] aside repl: {permalink} 에서 '옵션 더 보기 → 삭제 → 삭제' 클릭")
        return 0
    if not os.path.exists(ASIDE):
        print("aside CLI 가 없습니다 (~/.local/bin/aside)")
        return 2
    out = subprocess.run([ASIDE, "repl", IG_DELETE_SCRIPT % {"url": permalink}], capture_output=True, text=True, timeout=180)
    text = out.stdout + out.stderr
    print(text[-1200:])
    ok = "GSTACK_STEP_OK" in text and "DELETE2=true" in text
    print(f"[{'OK' if ok else 'FAIL'}] instagram {permalink} 삭제")
    if ok:
        _mark_deleted("instagram", permalink)
    return 0 if ok else 1


def repost(item_id: str) -> int:
    items = queue.load()
    hit = [it for it in items if it["id"] == item_id]
    if not hit:
        print(f"큐에 없음: {item_id}")
        return 1
    hit[0]["status"] = "pending"
    hit[0]["scheduled_at"] = (datetime.datetime.now(KST) - datetime.timedelta(minutes=1)).replace(microsecond=0).isoformat()
    queue.save(items)
    channels = ",".join(hit[0]["channels"])
    return subprocess.call([sys.executable, str(HARU / "run_daily.py"), "--channels", channels])


def _mark_deleted(channel: str, ref: str) -> None:
    items = queue.load()
    now = datetime.datetime.now(KST).replace(microsecond=0).isoformat()
    for it in items:
        res = it.get("result") or {}
        val = res.get(channel)
        ids = []
        if isinstance(val, dict):
            ids = [str(v) for v in val.values()]
        elif val:
            ids = [str(val)]
        if ref in ids or (channel == "instagram" and it.get("result", {}).get("permalink") == ref):
            it["deleted"] = True
            it["deleted_at"] = now
    queue.save(items)
    with open(HARU / "data" / "metrics.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": now, "event": "delete", "channel": channel, "ref": ref}, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="하루 게시물 관리")
    ap.add_argument("--dry-run", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("threads-delete"); a.add_argument("post_id")
    b = sub.add_parser("ig-delete"); b.add_argument("permalink")
    d = sub.add_parser("threads-ui-delete"); d.add_argument("permalink")
    c = sub.add_parser("repost"); c.add_argument("item_id")
    ns = ap.parse_args()
    if ns.cmd == "threads-delete":
        return threads_delete(ns.post_id, ns.dry_run)
    if ns.cmd == "ig-delete":
        return ig_delete(ns.permalink, ns.dry_run)
    if ns.cmd == "threads-ui-delete":
        return threads_ui_delete(ns.permalink, ns.dry_run)
    return repost(ns.item_id)


if __name__ == "__main__":
    sys.exit(main())
