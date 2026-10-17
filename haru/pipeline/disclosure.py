"""AI 고지 / 제휴 고지 문구와 Threads 텍스트 검증.

- 공정위 2026-06-01 가이드라인, AI기본법(2026-01) 준수.
- 배치 (2026-10-17 오너 결정, 세 번째 조정): 첫 줄은 훅(본문 첫 줄), **둘째 줄에 짧은 고지**(AI 가상인물 + 수수료),
  제휴 글은 맨 끝에 판매처 지정 문구(쿠팡·네이버는 원문 그대로, 그 외는 공통 문구).
  이유: 첫 줄이 "AI로 생성된…"이면 읽기 전에 이탈한다. 둘째 줄은 인스타 '더보기' 접힘(약 125자) 안에 들어가므로
  공정위 "첫 부분" 요건을 지키면서 훅을 먼저 보여줄 수 있다. 맨 끝 지정 문구는 판매처 요구 사항.
"""

import re

AI_LABEL = "AI로 생성된 가상인물이 포함된 게시물입니다."
AFFILIATE_LABEL = "이 게시물은 제휴 활동의 일환으로 수수료를 제공받습니다."
# 판매처가 문구를 지정한 경우. 쿠팡 파트너스는 아래 문장을 그대로 쓰라고 요구한다 (링크 생성 화면 안내, 2026-10-17).
AFFILIATE_LABELS_BY_PROGRAM = {
    "쿠팡": "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.",
    # 네이버 쇼핑 커넥트 링크 발급 화면 안내 문구 (2026-10-17)
    "네이버": "이 포스팅은 네이버 쇼핑 커넥트 활동의 일환으로, 판매 발생 시 수수료를 제공받습니다.",
}
ALL_AFFILIATE_LABELS = (AFFILIATE_LABEL, *AFFILIATE_LABELS_BY_PROGRAM.values())


def affiliate_label(program: str | None) -> str:
    """판매처별 제휴 고지 문구. 지정된 게 없으면 공통 문구."""
    return AFFILIATE_LABELS_BY_PROGRAM.get((program or "").strip(), AFFILIATE_LABEL)
# 이전 문구. compose() 가 중복 제거할 때만 쓴다 (2026-10-17 두 번째 글 2건에 잠시 사용).
LEGACY_AI_LABELS = ("AI로 만든 가상인물이에요.",)
# 게시물 둘째 줄에 들어가는 짧은 고지. 괄호 한 줄, 하루 말투. AI 기본법(AI 생성물 표시)과 공정위(경제적 이해관계 표시)를 함께 만족.
AI_LABEL_SHORT = "(AI 가상인물 하루가 씀)"
AI_AFFILIATE_LABEL_SHORT = "(AI 가상인물 하루가 씀 · 제휴 링크라 사면 수수료 받음)"
SHORT_LABELS = (AI_LABEL_SHORT, AI_AFFILIATE_LABEL_SHORT)
LABEL_POSITION = "after_hook"  # "after_hook" | "top" | "bottom". 2026-10-17 after_hook 으로 확정.

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


def _strip_labels(text: str) -> str:
    """본문에서 알려진 고지 문구를 모두 떼고, 빈 줄을 정리해 돌려줍니다."""
    labels = (AI_LABEL, *ALL_AFFILIATE_LABELS, *LEGACY_AI_LABELS, *SHORT_LABELS)
    lines: list[str] = []
    for raw in text.strip().splitlines():
        ln = raw
        for label in labels:
            ln = ln.replace(label, "")
        ln = ln.strip()
        if ln == "" and raw.strip() != "":
            continue  # 고지만 있던 줄은 통째로 버린다
        lines.append(ln)
    out: list[str] = []
    for ln in lines:
        if ln == "" and (not out or out[-1] == ""):
            continue
        out.append(ln)
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out)


def compose(text: str, has_affiliate: bool, program: str | None = None) -> str:
    """본문에 고지 문구를 붙여 돌려줍니다.

    after_hook (기본): 1줄 훅 → 2줄 짧은 고지 → 나머지 본문 → (제휴면) 빈 줄 + 판매처 지정 문구.
    이미 붙어 있으면 중복하지 않습니다. program 을 주면 그 판매처가 요구하는 제휴 문구를 쓴다.
    """
    body = _strip_labels(text)
    aff_label = affiliate_label(program)
    short = AI_AFFILIATE_LABEL_SHORT if has_affiliate else AI_LABEL_SHORT
    if LABEL_POSITION == "after_hook":
        lines = body.splitlines()
        if not lines:
            lines = [short]
        else:
            lines = [lines[0], short] + lines[1:]
        if has_affiliate:
            lines += ["", aff_label]
        return "\n".join(lines)
    if LABEL_POSITION == "top":
        lines = [AI_LABEL] + ([aff_label] if has_affiliate else [])
        if body:
            lines += ["", body]
    else:
        lines = [body, ""] if body else []
        lines += ([aff_label] if has_affiliate else []) + [AI_LABEL]
    return "\n".join(lines)


def count_links(text: str) -> int:
    """본문에 포함된 http(s) 링크 개수."""
    return len(_URL_RE.findall(text))


def validate_threads_text(text: str, extra_links: int = 0, require_ai_label: bool = True) -> None:
    """Threads 게시 전 검증. 문제가 있으면 ValueError.

    extra_links: link_attachment 등 본문 밖에서 추가되는 링크 수.
    require_ai_label: 본문 글은 True. 링크 댓글(답글)은 고지가 본문에 있으므로 False.
    """
    if require_ai_label:
        if LABEL_POSITION == "after_hook":
            head = text.splitlines()[:2]
            if not any(lbl in ln for ln in head for lbl in (AI_LABEL, *SHORT_LABELS)):
                raise ValueError("첫 두 줄 안에 AI 고지 문구가 없습니다: " + AI_LABEL_SHORT)
        elif LABEL_POSITION == "top":
            if not text.startswith(AI_LABEL):
                raise ValueError("첫 줄에 AI 고지 문구가 없습니다: " + AI_LABEL)
        elif not text.rstrip().endswith(AI_LABEL):
            raise ValueError("마지막 줄에 AI 고지 문구가 없습니다: " + AI_LABEL)
    if len(text) > THREADS_MAX_CHARS:
        raise ValueError(f"Threads 본문이 {THREADS_MAX_CHARS}자를 초과합니다 ({len(text)}자)")
    links = count_links(text) + extra_links
    if links > THREADS_MAX_LINKS:
        raise ValueError(f"링크가 {THREADS_MAX_LINKS}개를 초과합니다 ({links}개)")
    if any(label in text for label in ALL_AFFILIATE_LABELS):
        claims = find_experience_claims(text)
        if claims:
            raise ValueError("제휴 글에 직접 사용 경험을 암시하는 표현이 있습니다: " + ", ".join(claims))
