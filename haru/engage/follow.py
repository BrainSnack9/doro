"""하루 스레드 선팔(2026-10-20 오너 결정 "자취 계정 선팔 하루 20명").

대상은 (1) 우리가 답글을 단 사람(최근 3일, 최신순) → (2) 오늘 후보 글의 작성자(검색 단계에서 광고·업체는 이미 걸러짐).
하루 상한 FOLLOW_DAILY_LIMIT, 한 번 팔로우한 계정은 다시 건드리지 않고, **언팔로우는 절대 하지 않는다**.
Aside(하루 계정 u0, threads.com 로그인 @haru.reviews)에서 프로필 페이지의 "팔로우" 버튼을 실제 클릭한다.
기록: haru/data/engage/follows.json {handle: {"at", "source", "result"}}.

사용:
  python3 haru/engage/follow.py            # 오늘 남은 한도만큼 선팔
  python3 haru/engage/follow.py --dry-run  # 대상만 출력
  python3 haru/engage/follow.py --limit 5
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from pipeline import KST  # noqa: E402

DATA = HERE.parent / "data" / "engage"
FOLLOWS = DATA / "follows.json"
REPLIED = DATA / "replied.json"
PAUSED = DATA / "PAUSED"
OWNER = "haru.reviews"
FOLLOW_DAILY_LIMIT = 20
REPLIED_LOOKBACK_DAYS = 3
PER_SCRIPT = 3  # Aside repl 120초 한도 → 한 스크립트에 3명
GAP_SECONDS = 8  # 팔로우 사이 간격(사람처럼)
ASIDE = os.path.expanduser("~/.local/bin/aside")
ASIDE_ACCOUNT = os.environ.get("HARU_ASIDE_ACCOUNT", "u0")

SCRIPT = r'''
const USERS = %(users)s;
const out = [];
for (const u of USERS) {
  const pg = await openTab("about:blank");
  let result = "error";
  try {
    await pg.goto("https://www.threads.com/@" + u, { waitUntil: "domcontentloaded", timeout: 20000 });
    await sleep(4000);
    const state = await pg.evaluate(() => {
      const btns = [...document.querySelectorAll("div[role=button], button")].map(b => ({ t: (b.innerText || "").trim(), r: b.getBoundingClientRect() })).filter(b => b.r.width > 40);
      const f = btns.find(b => /^(팔로우|Follow)$/.test(b.t)); const g = btns.find(b => /^(팔로잉|Following|요청됨|Requested)$/.test(b.t));
      const gone = /이용할 수 없는 페이지|Sorry, this page/.test(document.body.innerText);
      return f ? { s: "follow", x: f.r.x + f.r.width / 2, y: f.r.y + f.r.height / 2 } : g ? { s: "already" } : gone ? { s: "gone" } : { s: "nobutton" };
    });
    if (state.s === "follow") {
      await pg.mouse.click(state.x, state.y);
      await sleep(2500);
      const after = await pg.evaluate(() => [...document.querySelectorAll("div[role=button], button")].some(b => /^(팔로잉|Following|요청됨|Requested)$/.test((b.innerText || "").trim())));
      result = after ? "followed" : "unverified";
    } else { result = state.s; }
  } catch (e) { result = "error " + String(e.message || e).slice(0, 60); }
  out.push({ u, result });
  await closeTab(pg);
  await sleep(%(gap)d * 1000);
}
console.log("FOLLOWS=" + JSON.stringify(out));
'''


def _load(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def today_count(follows: dict, today: str) -> int:
    return sum(1 for v in follows.values() if v.get("at", "").startswith(today) and v.get("result") == "followed")


def pick_targets(follows: dict, replied: dict, candidates: list, now: datetime, limit: int) -> list[tuple[str, str]]:
    """(handle, source) 목록. 이미 팔로우했거나 시도한 계정·우리 계정 제외. 답글 단 사람(최신순) → 오늘 후보 작성자."""
    seen = {h.lstrip("@") for h in follows}
    out: list[tuple[str, str]] = []
    since = (now - timedelta(days=REPLIED_LOOKBACK_DAYS)).isoformat()
    for v in sorted(replied.values(), key=lambda v: v.get("at", ""), reverse=True):
        h = (v.get("user") or "").lstrip("@")
        if not h or h == OWNER or h in seen or v.get("at", "") < since:
            continue
        seen.add(h); out.append((h, "replied"))
        if len(out) >= limit:
            return out
    for c in candidates:
        h = (c.get("user") or "").lstrip("@")
        if not h or h == OWNER or h in seen:
            continue
        seen.add(h); out.append((h, "candidate"))
        if len(out) >= limit:
            break
    return out


def follow_batch(users: list[str]) -> list[dict]:
    js = SCRIPT % {"users": json.dumps(users), "gap": GAP_SECONDS}
    out = subprocess.run([ASIDE, "--account", ASIDE_ACCOUNT, "repl", js], capture_output=True, text=True, timeout=130)
    m = re.search(r"^FOLLOWS=(.*)$", out.stdout + out.stderr, re.M)
    if not m:
        raise RuntimeError("Aside 실패: " + (out.stdout + out.stderr)[-200:].strip())
    return json.loads(m.group(1))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=FOLLOW_DAILY_LIMIT, help="하루 상한(기본 20)")
    ns = ap.parse_args()
    if PAUSED.exists():
        print("[follow] 정지 상태(PAUSED). 아무것도 안 함."); return 2
    now = datetime.now(KST); today = now.strftime("%Y-%m-%d")
    follows = _load(FOLLOWS, {}); replied = _load(REPLIED, {})
    cands = _load(DATA / f"candidates-{today}.json", {}).get("candidates", [])
    done = today_count(follows, today)
    room = max(0, min(ns.limit, FOLLOW_DAILY_LIMIT) - done)
    targets = pick_targets(follows, replied, cands, now, room)
    print(f"[follow] 오늘 이미 {done}명 · 남은 한도 {room} · 대상 {len(targets)}명: " + ", ".join(f"@{h}({s})" for h, s in targets))
    if ns.dry_run or not targets:
        return 0
    if not ns.dry_run:
        try:
            from engage import page  # noqa: WPS433
        except ImportError:
            sys.path.insert(0, str(HERE)); import page  # type: ignore  # noqa: E401
        page.require_owner()
    followed = 0
    for i in range(0, len(targets), PER_SCRIPT):
        chunk = targets[i:i + PER_SCRIPT]
        try:
            results = follow_batch([h for h, _ in chunk])
        except Exception as ex:  # noqa: BLE001
            print(f"[follow] 실패 {[h for h, _ in chunk]}: {str(ex)[:120]}"); continue
        for (h, src), r in zip(chunk, results):
            follows[h] = {"at": now.isoformat(), "source": src, "result": r["result"]}
            if r["result"] == "followed":
                followed += 1
            print(f"  @{h} -> {r['result']}")
        FOLLOWS.write_text(json.dumps(follows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        time.sleep(2)
    print(f"[follow] 완료 {followed}명 팔로우 (오늘 누적 {done + followed}/{FOLLOW_DAILY_LIMIT})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
