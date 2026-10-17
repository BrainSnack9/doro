#!/usr/bin/env python3
"""운영 대시보드 데이터 수집 → haru/data/dashboard.json

소스
- haru/data/queue.json      게시 아이템(상태·채널·결과 id·블로그 주소·사진)
- haru/data/metrics.jsonl    이벤트 로그(post/post_failed/delete)
- haru/hub/links.json        허브 항목
- Threads API                글별 views/likes/replies, 계정 views/followers
- Instagram API              글별 views/reach/likes/saved, 계정 followers
- haru/assets/posts/*.jpg    사진 목록
- 수익(쿠팡·네이버·오늘의집)  haru/ops/revenue.py (Aside) 가 따로 채우는 haru/data/revenue.json 을 합친다

토큰은 haru/.env 에서 읽는다. 어떤 소스가 실패해도 나머지는 모은다(실패는 errors 에 기록).
"""

import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
HARU = HERE.parent
sys.path.insert(0, str(HARU))
from pipeline import KST  # noqa: E402

DATA = HARU / "data"
OUT = DATA / "dashboard.json"
POSTS_DIR = HARU / "assets" / "posts"


def load_env() -> dict:
    env = dict(os.environ)
    p = HARU / ".env"
    if p.exists():
        for ln in p.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, v = ln.split("=", 1)
                env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return env


def get_json(url: str, timeout: int = 20) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as r:  # noqa: S310
        return json.load(r)


def threads_post_insights(post_id: str, token: str) -> dict:
    d = get_json(f"https://graph.threads.net/v1.0/{post_id}/insights?metric=views,likes,replies,reposts,quotes,shares&access_token={urllib.parse.quote(token)}")
    return {m["name"]: (m.get("values") or [{}])[0].get("value") for m in d.get("data", [])}


def threads_account(user_id: str, token: str) -> dict:
    d = get_json(f"https://graph.threads.net/v1.0/{user_id}/threads_insights?metric=views,likes,replies,followers_count&access_token={urllib.parse.quote(token)}")
    out = {}
    for m in d.get("data", []):
        out[m["name"]] = (m.get("total_value") or {}).get("value", (m.get("values") or [{}])[0].get("value"))
    return out


def ig_post_insights(media_id: str, token: str) -> dict:
    d = get_json(f"https://graph.instagram.com/v21.0/{media_id}/insights?metric=views,reach,likes,comments,saved,shares&access_token={urllib.parse.quote(token)}")
    return {m["name"]: (m.get("values") or [{}])[0].get("value") for m in d.get("data", [])}


def ig_account(token: str) -> dict:
    return get_json(f"https://graph.instagram.com/v21.0/me?fields=followers_count,media_count&access_token={urllib.parse.quote(token)}")


def permalink(channel: str, post_id: str, token: str) -> str | None:
    try:
        if channel == "threads":
            return get_json(f"https://graph.threads.net/v1.0/{post_id}?fields=permalink&access_token={urllib.parse.quote(token)}").get("permalink")
        return get_json(f"https://graph.instagram.com/v21.0/{post_id}?fields=permalink&access_token={urllib.parse.quote(token)}").get("permalink")
    except Exception:  # noqa: BLE001
        return None


def product_token(item_id: str) -> str:
    return (item_id.split("-") + ["", "", "", ""])[3]


def collect(now: datetime | None = None) -> dict:
    now = now or datetime.now(KST)
    env = load_env()
    errors: list[str] = []
    th_tok, ig_tok = env.get("THREADS_ACCESS_TOKEN", ""), env.get("IG_ACCESS_TOKEN", "")

    queue = json.loads((DATA / "queue.json").read_text(encoding="utf-8"))
    items = queue if isinstance(queue, list) else queue["items"]
    links = json.loads((HARU / "hub" / "links.json").read_text(encoding="utf-8"))

    # 상품(글) 단위로 묶기: 같은 날짜·상품 토큰
    groups: dict[str, dict] = {}
    for it in items:
        if it.get("deleted"):
            continue
        key = f"{it['id'][:10]}-{product_token(it['id'])}"
        g = groups.setdefault(key, {"key": key, "date": it["id"][:10], "product": product_token(it["id"]), "kind": it.get("kind"), "channels": {}, "pending": [], "failed": [], "image_url": None, "image_scene": None, "naver_blog": None, "affiliate": None, "text": None})
        g["image_url"] = g["image_url"] or it.get("image_url")
        g["image_scene"] = g["image_scene"] or it.get("image_scene")
        g["naver_blog"] = g["naver_blog"] or it.get("naver_blog")
        g["affiliate"] = g["affiliate"] or it.get("affiliate")
        g["text"] = g["text"] or (it.get("text") or "").splitlines()[0]
        res = it.get("result") or {}
        for ch in it.get("channels", []):
            st = it.get("status")
            if st == "posted" and ch in res:
                pid = res[ch]["post_id"] if isinstance(res[ch], dict) else res[ch]
                entry = {"post_id": str(pid), "item_id": it["id"], "posted_at": it.get("updated_at")}
                tok = th_tok if ch == "threads" else ig_tok
                if tok:
                    try:
                        entry["insights"] = threads_post_insights(str(pid), tok) if ch == "threads" else ig_post_insights(str(pid), tok)
                        entry["permalink"] = permalink(ch, str(pid), tok)
                    except Exception as e:  # noqa: BLE001
                        errors.append(f"{ch} insights {pid}: {str(e)[:80]}")
                g["channels"][ch] = entry
            elif st == "pending":
                g["pending"].append({"channel": ch, "item_id": it["id"], "scheduled_at": it.get("scheduled_at")})
            elif st == "failed":
                g["failed"].append({"channel": ch, "item_id": it["id"], "error": (res.get("error") if isinstance(res, dict) else None)})

    accounts = {}
    try:
        accounts["threads"] = threads_account(env.get("THREADS_USER_ID", ""), th_tok) if th_tok else {}
    except Exception as e:  # noqa: BLE001
        errors.append(f"threads account: {str(e)[:80]}")
    try:
        accounts["instagram"] = ig_account(ig_tok) if ig_tok else {}
    except Exception as e:  # noqa: BLE001
        errors.append(f"instagram account: {str(e)[:80]}")

    # 사진
    photos = []
    used = {}
    for g in groups.values():
        if g["image_url"]:
            used.setdefault(g["product"], []).append(g["key"])
    for p in sorted(POSTS_DIR.glob("*.jpg"), reverse=True):
        tok = (p.stem.split("-") + ["", "", "", ""])[3]
        photos.append({"file": p.name, "product": tok, "used_by": used.get(tok, []), "size_kb": p.stat().st_size // 1024})

    # 이벤트 (최근 7일)
    events = []
    mp = DATA / "metrics.jsonl"
    if mp.exists():
        cutoff = (now - timedelta(days=7)).isoformat()
        for ln in mp.read_text(encoding="utf-8").splitlines():
            try:
                ev = json.loads(ln)
            except ValueError:
                continue
            if ev.get("ts", "") >= cutoff:
                events.append(ev)

    # 시스템
    system = {"generated_at": now.isoformat(timespec="seconds")}
    try:
        system["git_head"] = subprocess.run(["git", "log", "-1", "--format=%h %s"], cwd=HARU.parent, capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:  # noqa: BLE001
        pass
    try:
        system["tests"] = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(HARU / "tests"), "-t", str(HARU)], capture_output=True, text=True, timeout=120).stderr.strip().splitlines()[-1]
    except Exception as e:  # noqa: BLE001
        system["tests"] = f"실패: {str(e)[:60]}"
    try:
        import ssl, socket  # noqa: E401
        ctx = ssl.create_default_context()
        with socket.create_connection(("harureviews.date", 443), timeout=10) as s, ctx.wrap_socket(s, server_hostname="harureviews.date") as ss:
            cert = ss.getpeercert()
            system["hub_cert"] = {"subject": dict(x[0] for x in cert["subject"]).get("commonName"), "not_after": cert.get("notAfter")}
    except Exception as e:  # noqa: BLE001
        system["hub_cert"] = {"error": str(e)[:80]}

    revenue = {}
    rp = DATA / "revenue.json"
    if rp.exists():
        try:
            revenue = json.loads(rp.read_text(encoding="utf-8"))
        except ValueError:
            errors.append("revenue.json 파싱 실패")

    out = {
        "generated_at": now.isoformat(timespec="seconds"),
        "accounts": accounts,
        "posts": sorted(groups.values(), key=lambda g: g["date"], reverse=True),
        "hub_items": links.get("items", []),
        "photos": photos,
        "events": events,
        "revenue": revenue,
        "system": system,
        "errors": errors,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    d = collect()
    print(f"[collect] posts={len(d['posts'])} photos={len(d['photos'])} errors={len(d['errors'])} -> {OUT}")
    for e in d["errors"]:
        print("  !", e)
