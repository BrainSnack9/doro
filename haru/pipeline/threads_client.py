"""Threads API 클라이언트 (graph.threads.net v1.0).

흐름: 컨테이너 생성 -> threads_publish. 이미지 게시물에는 링크를 못 붙이므로
``post_with_link_comment`` 로 이미지 게시 후 link_attachment 가 있는 답글을 답니다.
"""

from typing import Optional

from . import http
from .disclosure import validate_threads_text

BASE_URL = "https://graph.threads.net/v1.0"


class ThreadsClient:
    def __init__(self, user_id: str, token: str, dry_run: bool = False) -> None:
        self.user_id = user_id
        self.token = token
        self.dry_run = dry_run

    # ----- low level -----
    def _create_container(self, fields: dict) -> str:
        data = dict(fields)
        data["access_token"] = self.token
        res = http.request("POST", f"{BASE_URL}/{self.user_id}/threads", data=data, dry_run=self.dry_run)
        return str(res["id"])

    def _publish(self, creation_id: str) -> str:
        """컨테이너 게시. 이미지 컨테이너는 처리 중이면 '미디어를 찾을 수 없음'(code 24)이 나오므로 잠깐 기다렸다 다시 시도한다."""
        import time
        last: Exception | None = None
        for attempt in range(6):
            try:
                res = http.request(
                    "POST",
                    f"{BASE_URL}/{self.user_id}/threads_publish",
                    data={"creation_id": creation_id, "access_token": self.token},
                    dry_run=self.dry_run,
                )
                return str(res["id"])
            except RuntimeError as e:  # http.request 가 HTTP 오류를 RuntimeError 로 올린다
                last = e
                if "4279009" not in str(e) and "does not exist" not in str(e):
                    raise
                if self.dry_run:
                    raise
                time.sleep(5 * (attempt + 1))
        raise last  # type: ignore[misc]

    # ----- public -----
    def delete(self, post_id: str) -> bool:
        """게시물(또는 답글) 삭제. threads_delete 권한이 있는 토큰이 필요하다. Threads 는 수정 API 가 없으므로 수정 = 삭제 후 재게시."""
        res = http.request("DELETE", f"{BASE_URL}/{post_id}", params={"access_token": self.token}, dry_run=self.dry_run)
        return bool(res.get("success", True))

    def publishing_quota(self) -> dict:
        """현재 게시 쿼터 (quota_usage, config)."""
        return http.request(
            "GET",
            f"{BASE_URL}/{self.user_id}/threads_publishing_limit",
            params={"fields": "quota_usage,config", "access_token": self.token},
            dry_run=self.dry_run,
        )

    def post_text(self, text: str, link: Optional[str] = None) -> str:
        validate_threads_text(text, extra_links=1 if link else 0)
        fields = {"media_type": "TEXT", "text": text}
        if link:
            fields["link_attachment"] = link
        return self._publish(self._create_container(fields))

    def post_image(self, text: str, image_url: str) -> str:
        validate_threads_text(text)
        return self._publish(self._create_container({"media_type": "IMAGE", "text": text, "image_url": image_url}))

    def post_video(self, text: str, video_url: str) -> str:
        validate_threads_text(text)
        return self._publish(self._create_container({"media_type": "VIDEO", "text": text, "video_url": video_url}))

    def reply(self, parent_id: str, text: str, link: Optional[str] = None) -> str:
        # 답글은 고지를 요구하지 않는다 (고지는 본문에). 길이·링크 수·경험 표현 검사는 유지.
        validate_threads_text(text, extra_links=1 if link else 0, require_ai_label=False)
        fields = {"media_type": "TEXT", "text": text, "reply_to_id": parent_id}
        if link:
            fields["link_attachment"] = link
        return self._publish(self._create_container(fields))

    def post_with_link_comment(self, text: str, image_url: str, link: str, link_text: str) -> dict:
        """이미지 게시 + 제휴 링크 답글. {'post_id', 'reply_id'} 반환."""
        validate_threads_text(link_text, extra_links=1, require_ai_label=False)  # 이미지 게시 전에 댓글부터 검증
        post_id = self.post_image(text, image_url)
        reply_id = self.reply(post_id, link_text, link=link)
        return {"post_id": post_id, "reply_id": reply_id}
