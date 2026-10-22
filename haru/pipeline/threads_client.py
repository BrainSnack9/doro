"""Threads API 클라이언트 — 공용 코어 iris.threads 에 하루의 고지 검사(disclosure.validate_threads_text)를 꽂은 것.

본문 글은 AI·제휴 고지를 요구하고, 답글(링크 댓글·사진 답글)은 고지를 요구하지 않는다(고지는 본문에).
본문 + 답글 묶음(post_with_link_comment·post_text_first)은 답글이 실패해도 본문 id 를 살려 {'post_id', 'reply_error'} 로 돌려준다
(코어 규칙: 본문은 이미 올라갔으므로 아이템을 failed 로 남기면 재시도 때 본문이 또 올라간다).
"""

from typing import Optional

from iris import threads as _core
from iris.threads import BASE_URL  # noqa: F401

from .disclosure import validate_threads_text


def _validate(text: str, extra_links: int = 0, is_reply: bool = False) -> None:
    validate_threads_text(text, extra_links=extra_links, require_ai_label=not is_reply)


class ThreadsClient(_core.ThreadsClient):
    def __init__(self, user_id: str, token: str, dry_run: bool = False, validate: Optional[_core.Validator] = None) -> None:
        super().__init__(user_id, token, dry_run=dry_run, validate=validate or _validate)
