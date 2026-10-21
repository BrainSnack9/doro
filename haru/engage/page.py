#!/usr/bin/env python3
"""스레드 글 페이지를 Aside 로 열어 그 글 밑에 달린 답글을 읽는다 — 공용 코어 iris.engage.page 에 하루 계정(u0, @haru.reviews)을 묶은 것.

Threads API 는 남의 글 안에서 우리 답글에 달린 답변을 돌려주지 않는다(2026-10-17 확인). 그래서 monitor.py 와 reply.py 는 화면을 읽는다.
답변 오인식 수정(API 시각 우선·추천 스레드에서 중단·우리 블록 속 원글 제외, 2026-10-19)은 코어에 있다.

  python3 haru/engage/page.py <permalink> [--since ISO]   # 테스트: 그 글 밑 답글 목록 출력
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pipeline  # noqa: E402,F401  (코어 경로)
from iris.engage import page as _core  # noqa: E402

ASIDE = _core.aside.ASIDE
ASIDE_ACCOUNT = os.environ.get("HARU_ASIDE_ACCOUNT", "u0")  # 하루 전용 Aside 계정(u0). 로이어픽은 u2, u1 은 에듀씨어 블로그
OWNER = "haru.reviews"


def read_page(permalink: str) -> list:
    return _core.read_page(permalink, ASIDE_ACCOUNT)


def read_children(permalink: str, owner: str = OWNER, since: str = "") -> list:
    """since: 우리 글의 게시 시각(ISO, API timestamp)."""
    return _core.read_children(permalink, owner=owner, account=ASIDE_ACCOUNT, since=since)


def threads_login_user() -> str:
    """하루 전용 Aside 계정(u0)에서 threads.com 에 로그인된 핸들('@haru.reviews'). 로그아웃이면 ''."""
    return _core.threads_login_user(ASIDE_ACCOUNT)


def require_owner(owner: str = OWNER) -> None:
    """threads.com 로그인 계정이 owner 가 아니면 즉시 종료(코드 3). HARU_SKIP_OWNER_CHECK=1 이면 건너뜀."""
    _core.require_owner(owner, ASIDE_ACCOUNT, skip_env="HARU_SKIP_OWNER_CHECK")


def like_post(permalink: str) -> str:
    """글(답변) 하나에 좋아요. 반환: liked | not_liked | no_box | no_btn | aside_error. 사람당 답장 1번, 그 뒤 답변에는 좋아요만(2026-10-18)."""
    return _core.like_post(permalink, ASIDE_ACCOUNT)


if __name__ == "__main__":
    since = sys.argv[sys.argv.index("--since") + 1] if "--since" in sys.argv else ""
    for c in read_children(sys.argv[1], since=since):
        print(f"- {c['user']} {c['time'][:16]} {c['text'][:120]}  {c['href']}")
