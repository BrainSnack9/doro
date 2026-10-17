"""오너 설정 점검: 환경 변수 존재 여부, Meta API 연결, 토큰 유효성, 게시 한도.

사용: python3 haru/check_setup.py
토큰 값은 절대 출력하지 않는다. 결과는 OK / MISSING / FAIL 세 가지로만 보여준다.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

THREADS = "https://graph.threads.net/v1.0"
INSTAGRAM = "https://graph.instagram.com/v21.0"

REQUIRED = ["THREADS_USER_ID", "THREADS_ACCESS_TOKEN", "IG_USER_ID", "IG_ACCESS_TOKEN"]
OPTIONAL = ["META_APP_SECRET", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "HUB_BASE_URL"]


def get(url: str, params: dict) -> tuple[int, dict]:
    full = url + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(full, timeout=20) as res:
            return res.status, json.loads(res.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(body)
        except json.JSONDecodeError:
            return e.code, {"raw": body[:300]}
    except (urllib.error.URLError, OSError) as e:
        return 0, {"error": str(e)[:200]}


def line(status: str, name: str, detail: str = "") -> None:
    print(f"[{status:7}] {name}{(' — ' + detail) if detail else ''}")


def main() -> int:
    ok = True
    print("== 환경 변수 ==")
    for k in REQUIRED:
        present = bool(os.environ.get(k))
        line("OK" if present else "MISSING", k)
        ok &= present
    for k in OPTIONAL:
        line("OK" if os.environ.get(k) else "SKIP", k, "선택")

    if not ok:
        print("\n필수 변수가 비어 있습니다. 환경 메뉴 → Edit → Network secrets에 저장 후 새 세션에서 다시 실행하세요.")
        return 1

    print("\n== Threads ==")
    status, me = get(f"{THREADS}/me", {"fields": "id,username,threads_profile_picture_url", "access_token": os.environ["THREADS_ACCESS_TOKEN"]})
    if status == 200 and me.get("id"):
        same = str(me["id"]) == os.environ["THREADS_USER_ID"]
        line("OK" if same else "FAIL", "토큰 → 계정", f"@{me.get('username')} (id {'일치' if same else '불일치: THREADS_USER_ID를 ' + str(me['id']) + ' 로'})")
        ok &= same
    elif status == 0:
        line("FAIL", "연결", "네트워크 거부. Allowed domains에 graph.threads.net 추가 필요")
        ok = False
    else:
        line("FAIL", "토큰", json.dumps(me.get("error", me), ensure_ascii=False)[:200])
        ok = False

    if ok:
        status, quota = get(f"{THREADS}/{os.environ['THREADS_USER_ID']}/threads_publishing_limit", {"fields": "quota_usage,config", "access_token": os.environ["THREADS_ACCESS_TOKEN"]})
        if status == 200 and quota.get("data"):
            d = quota["data"][0]
            line("OK", "게시 한도", f"오늘 사용 {d.get('quota_usage')} / {d.get('config', {}).get('quota_total')}")
        else:
            line("WARN", "게시 한도 조회 실패", json.dumps(quota, ensure_ascii=False)[:200])

    print("\n== Instagram ==")
    status, ig = get(f"{INSTAGRAM}/me", {"fields": "id,username,account_type", "access_token": os.environ["IG_ACCESS_TOKEN"]})
    if status == 200 and ig.get("id"):
        same = str(ig["id"]) == os.environ["IG_USER_ID"]
        prof = ig.get("account_type") in ("BUSINESS", "MEDIA_CREATOR")
        line("OK" if same else "FAIL", "토큰 → 계정", f"@{ig.get('username')} ({ig.get('account_type')}, id {'일치' if same else '불일치: IG_USER_ID를 ' + str(ig['id']) + ' 로'})")
        if not prof:
            line("FAIL", "계정 유형", "프로페셔널(크리에이터/비즈니스) 계정이어야 게시 API 사용 가능")
        ok &= same and prof
    elif status == 0:
        line("FAIL", "연결", "네트워크 거부. Allowed domains에 graph.instagram.com 추가 필요")
        ok = False
    else:
        line("FAIL", "토큰", json.dumps(ig.get("error", ig), ensure_ascii=False)[:200])
        ok = False

    if os.environ.get("TELEGRAM_BOT_TOKEN"):
        print("\n== Telegram ==")
        status, tg = get(f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/getMe", {})
        line("OK" if status == 200 and tg.get("ok") else "FAIL", "봇", tg.get("result", {}).get("username", "") if status == 200 else "연결 또는 토큰 오류")

    print("\n결과:", "모두 통과. 첫 게시물 초안을 만들 수 있습니다." if ok else "위 FAIL 항목을 고친 뒤 다시 실행하세요.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
