"""Instagram Graph API 클라이언트. 캡션에 클릭 가능한 링크는 없으므로 프로필 링크가 허브를 가리킵니다."""

import time

from . import http

API_VERSION = "v21.0"
BASE_URL = f"https://graph.instagram.com/{API_VERSION}"


class InstagramClient:
    def __init__(self, ig_user_id: str, token: str, dry_run: bool = False) -> None:
        self.ig_user_id = ig_user_id
        self.token = token
        self.dry_run = dry_run

    def _publish(self, creation_id: str) -> str:
        res = http.request(
            "POST",
            f"{BASE_URL}/{self.ig_user_id}/media_publish",
            data={"creation_id": creation_id, "access_token": self.token},
            dry_run=self.dry_run,
        )
        return str(res["id"])

    def post_image(self, caption: str, image_url: str) -> str:
        res = http.request(
            "POST",
            f"{BASE_URL}/{self.ig_user_id}/media",
            data={"image_url": image_url, "caption": caption, "access_token": self.token},
            dry_run=self.dry_run,
        )
        return self._publish(str(res["id"]))

    def post_reel(self, caption: str, video_url: str, poll_interval: int = 5, max_wait: int = 300) -> str:
        """릴스: 컨테이너 생성 -> status_code 가 FINISHED 될 때까지 폴링 -> 게시."""
        res = http.request(
            "POST",
            f"{BASE_URL}/{self.ig_user_id}/media",
            data={
                "media_type": "REELS",
                "video_url": video_url,
                "caption": caption,
                "share_to_feed": "true",
                "access_token": self.token,
            },
            dry_run=self.dry_run,
        )
        creation_id = str(res["id"])
        waited = 0
        while True:
            status = http.request(
                "GET",
                f"{BASE_URL}/{creation_id}",
                params={"fields": "status_code", "access_token": self.token},
                dry_run=self.dry_run,
            )
            code = status.get("status_code")
            if code == "FINISHED":
                break
            if code == "ERROR":
                raise RuntimeError(f"릴스 처리 실패: {status}")
            if waited >= max_wait:
                raise TimeoutError(f"릴스 처리 대기 {max_wait}초 초과 (status={code})")
            time.sleep(poll_interval)
            waited += poll_interval
        return self._publish(creation_id)
