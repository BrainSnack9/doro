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
        res = http.request(
            "POST",
            f"{BASE_URL}/{self.user_id}/threads_publish",
            data={"creation_id": creation_id, "access_token": self.token},
            dry_run=self.dry_run,
        )
        return str(res["id"])

    # ----- public -----
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
        validate_threads_text(text, extra_links=1 if link else 0)
        fields = {"media_type": "TEXT", "text": text, "reply_to_id": parent_id}
        if link:
            fields["link_attachment"] = link
        return self._publish(self._create_container(fields))

    def post_with_link_comment(self, text: str, image_url: str, link: str, link_text: str) -> dict:
        """이미지 게시 + 제휴 링크 답글. {'post_id', 'reply_id'} 반환."""
        post_id = self.post_image(text, image_url)
        reply_id = self.reply(post_id, link_text, link=link)
        return {"post_id": post_id, "reply_id": reply_id}
