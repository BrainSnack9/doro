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
# 감축 규칙(2026-10-20 오너: "선별해서 하고 일정 수에 차면 개수를 줄여서 목표 숫자에 도달"):
# 팔로워 수 구간별 하루 상한. 팔로워가 늘수록 줄이고, 1,000 이상이면 멈춘다.
FOLLOW_TAPER = [(100, 20), (300, 10), (1000, 5)]  # (팔로워 미만, 하루 상한)
FOLLOW_RATIO_BASE = 150   # 총 팔로우 수가 max(150, 팔로워×2) 를 넘으면 멈춘다(팔로잉이 팔로워보다 너무 많아 보이지 않게)
FOLLOW_RATIO_MULT = 2
AD_HANDLE = re.compile(r"(?:^|[._\d])(?:clean|cleaning|clinic|shop|store|mall|official|biz|company|pick|deal|hotdeal|mkt|marketing|ad|ads|promo)(?:[._\d]|$)|(?:clean|shop|store|mall|official|deal|pick)\d*$", re.I)
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


def daily_limit(followers: int, total_follows: int) -> int:
    """오늘 팔로우 가능한 최대 수. 팔로워 구간별 상한(FOLLOW_TAPER), 비율 가드(FOLLOW_RATIO_*) 둘 다 적용."""
    cap = 0
    for below, n in FOLLOW_TAPER:
        if followers < below:
            cap = n; break
    if total_follows >= max(FOLLOW_RATIO_BASE, followers * FOLLOW_RATIO_MULT):
        return 0
    return cap


def followers_count() -> int | None:
    """Threads API 팔로워 수. 토큰이 없거나 실패하면 None(→ 감축 규칙은 팔로워 0으로 간주하지 않고 기본 상한만 적용)."""
    tok = os.environ.get("THREADS_ACCESS_TOKEN"); uid = os.environ.get("THREADS_USER_ID")
    if not tok or not uid:
        return None
    import urllib.parse, urllib.request
    try:
        with urllib.request.urlopen(f"https://graph.threads.net/v1.0/{uid}/threads_insights?metric=followers_count&access_token={urllib.parse.quote(tok)}", timeout=20) as r:
            data = json.load(r).get("data", [])
        for d in data:
            if d.get("name") == "followers_count":
                v = d.get("total_value", {}).get("value") if "total_value" in d else (d.get("values") or [{}])[-1].get("value")
                return int(v or 0)
    except Exception:  # noqa: BLE001
        return None
    return None


def selectable(handle: str) -> bool:
    """선별 기준: 업체·홍보형 핸들 제외(그 외 주제 적합성은 답글·후보 단계에서 이미 걸러짐)."""
    return not AD_HANDLE.search(handle)


def pick_targets(follows: dict, replied: dict, candidates: list, now: datetime, limit: int) -> list[tuple[str, str]]:
    """(handle, source) 목록. 이미 팔로우했거나 시도한 계정·우리 계정·업체형 핸들 제외. 답글 단 사람(최신순) → 오늘 후보 작성자."""
    seen = {h.lstrip("@") for h in follows}
    out: list[tuple[str, str]] = []
    if limit <= 0:
        return out
    since = (now - timedelta(days=REPLIED_LOOKBACK_DAYS)).isoformat()
    for v in sorted(replied.values(), key=lambda v: v.get("at", ""), reverse=True):
        h = (v.get("user") or "").lstrip("@")
        if not h or h == OWNER or h in seen or v.get("at", "") < since or not selectable(h):
            continue
        seen.add(h); out.append((h, "replied"))
        if len(out) >= limit:
            return out
    for c in candidates:
        h = (c.get("user") or "").lstrip("@")
        if not h or h == OWNER or h in seen or not selectable(h):
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
    fol = followers_count()
    total = sum(1 for v in follows.values() if v.get("result") == "followed")
    cap = daily_limit(fol if fol is not None else 0, total) if fol is not None else FOLLOW_DAILY_LIMIT
    room = max(0, min(ns.limit, cap) - done)
    targets = pick_targets(follows, replied, cands, now, room)
    print(f"[follow] 팔로워 {fol if fol is not None else '?'} · 지금까지 팔로우 {total} · 오늘 상한 {cap} · 오늘 이미 {done}명 · 남은 한도 {room} · 대상 {len(targets)}명: " + ", ".join(f"@{h}({s})" for h, s in targets))
    if cap == 0:
        print("[follow] 감축 규칙에 따라 오늘은 선팔하지 않음(팔로워 1,000 이상이거나 팔로잉이 팔로워×2 또는 150을 넘음).")
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
    print(f"[follow] 완료 {followed}명 팔로우 (오늘 누적 {done + followed}/{cap})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
