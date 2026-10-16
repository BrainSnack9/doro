"""AI 고지 / 제휴 고지 문구와 Threads 텍스트 검증.

- 공정위 2026-06-01 가이드라인, AI기본법(2026-01) 준수.
- 모든 게시물의 첫 줄은 AI 라벨, 제휴 링크가 있으면 둘째 줄은 제휴 고지.
"""

import re

AI_LABEL = "AI로 생성된 가상인물이 포함된 게시물입니다."
AFFILIATE_LABEL = "이 게시물은 제휴 활동의 일환으로 수수료를 제공받습니다."

THREADS_MAX_CHARS = 500
THREADS_MAX_LINKS = 5

_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)

# 하루는 AI라 물건을 써볼 수 없다. 직접 경험을 암시하는 표현은 공정위 기준 부당광고가 된다.
EXPERIENCE_CLAIMS = (
    "써보니", "써봤", "써 봤", "써보고", "사용해보니", "사용해봤", "사용 중", "사용중",
    "제가 쓰는", "내가 쓰는", "요즘 쓰는", "매일 쓰는", "아침마다 쓰는", "쓰고 있", "쓰는 중",
    "발라보니", "발라봤", "먹어보니", "먹어봤", "입어보니", "입어봤", "신어보니", "신어봤",
    "향이 좋", "촉감이", "발림성이", "맛있", "편했", "좋았어", "만족했",
)


def find_experience_claims(text: str) -> list[str]:
    """본문에서 직접 사용 경험을 암시하는 표현을 찾아 돌려줍니다."""
    return [w for w in EXPERIENCE_CLAIMS if w in text]


def compose(text: str, has_affiliate: bool) -> str:
    """본문 앞에 고지 문구를 붙여 돌려줍니다. 이미 붙어 있으면 중복하지 않습니다."""
    body = text.strip()
    lines = [AI_LABEL]
    if has_affiliate:
        lines.append(AFFILIATE_LABEL)
    # 이미 고지가 포함된 본문이면 제거 후 다시 붙인다 (순서 보장).
    for label in (AI_LABEL, AFFILIATE_LABEL):
        body = body.replace(label, "").strip()
    if body:
        lines.append("")
        lines.append(body)
    return "\n".join(lines)


def count_links(text: str) -> int:
    """본문에 포함된 http(s) 링크 개수."""
    return len(_URL_RE.findall(text))


def validate_threads_text(text: str, extra_links: int = 0) -> None:
    """Threads 게시 전 검증. 문제가 있으면 ValueError.

    extra_links: link_attachment 등 본문 밖에서 추가되는 링크 수.
    """
    if not text.startswith(AI_LABEL):
        raise ValueError("첫 줄에 AI 고지 문구가 없습니다: " + AI_LABEL)
    if len(text) > THREADS_MAX_CHARS:
        raise ValueError(f"Threads 본문이 {THREADS_MAX_CHARS}자를 초과합니다 ({len(text)}자)")
    links = count_links(text) + extra_links
    if links > THREADS_MAX_LINKS:
        raise ValueError(f"링크가 {THREADS_MAX_LINKS}개를 초과합니다 ({links}개)")
    if AFFILIATE_LABEL in text:
        claims = find_experience_claims(text)
        if claims:
            raise ValueError("제휴 글에 직접 사용 경험을 암시하는 표현이 있습니다: " + ", ".join(claims))
