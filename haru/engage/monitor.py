#!/usr/bin/env python3
"""우리 답글에 달린 반응을 보고, 적대적이면 즉시 정지(PAUSED) + 알림 기록 — 공용 코어 iris.engage.monitor 에 하루 계정(u0, @haru.reviews)을 묶은 것.

  python3 haru/engage/monitor.py [--no-aside]
Threads API: /me/replies → 각 글의 /replies 에 '광고|봇|꺼져|신고|AI 티|스팸|차단' 등이 있으면 haru/data/engage/PAUSED 를 만들고 alerts.json 에 남긴다.
API 가 못 보는 것(2026-10-17 확인): 남의 글 안에서 우리 답글에 달린 답변 → 최근 48시간 우리 답글 페이지를 Aside 로 읽어(page.read_children)
responses.json 에 모은다. 답장은 오너가 초안을 보고 승인한 것만(자동화 이후에도 예외 없음, 2026-10-17 오너 지시).
**사람당 답장 딱 1번**(2026-10-18 오너 결정): 이미 답장한 사람의 다음 답변과 짧은 반응("ㅋㅋ"·이모지)은 like_only 로 표시하고 좋아요만 누른다.
정지 해제는 사람이 PAUSED 를 지운다. 종료 코드: 0 이상 없음 · 1 토큰 없음 · 2 적대 반응(정지) · 3 u0 로그인 계정이 @haru.reviews 아님
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HARU = HERE.parent
sys.path.insert(0, str(HARU))
import pipeline  # noqa: E402,F401  (코어 경로)
from iris.engage import monitor as _core  # noqa: E402

ASIDE_ACCOUNT = os.environ.get("HARU_ASIDE_ACCOUNT", "u0")
OWNER = "haru.reviews"
DATA = HARU / "data" / "engage"
PAUSED = DATA / "PAUSED"
ALERTS = DATA / "alerts.json"
RESPONSES = DATA / "responses.json"
HOSTILE = _core.HOSTILE


def env() -> dict:
    out = dict(os.environ)
    p = HARU / ".env"
    if p.exists():
        for ln in p.read_text(encoding="utf-8").splitlines():
            if "=" in ln and not ln.strip().startswith("#"):
                k, v = ln.split("=", 1); out.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return out


def main() -> int:
    tok = env().get("THREADS_ACCESS_TOKEN", "")
    return _core.run(DATA, tok, OWNER, ASIDE_ACCOUNT, use_aside="--no-aside" not in sys.argv, like=True)


if __name__ == "__main__":
    sys.exit(main())
