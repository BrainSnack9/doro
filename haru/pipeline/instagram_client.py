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

    def _wait_until_finished(self, creation_id: str, poll_interval: int, max_wait: int) -> None:
        """컨테이너 status_code 가 FINISHED 될 때까지 폴링. ERROR 면 RuntimeError, 시간 초과면 TimeoutError."""
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
                return
            if code == "ERROR":
                raise RuntimeError(f"미디어 처리 실패: {status}")
            if waited >= max_wait:
                raise TimeoutError(f"미디어 처리 대기 {max_wait}초 초과 (status={code})")
            time.sleep(poll_interval)
            waited += poll_interval

    def post_image(self, caption: str, image_url: str, poll_interval: int = 3, max_wait: int = 120) -> str:
        """이미지: 컨테이너 생성 -> FINISHED 폴링 -> 게시.

        이미지도 생성 직후 바로 media_publish 하면 9007/2207027 "Media ID is not available" 가 난다 (2026-10-17 실측).
        """
        res = http.request(
            "POST",
            f"{BASE_URL}/{self.ig_user_id}/media",
            data={"image_url": image_url, "caption": caption, "access_token": self.token},
            dry_run=self.dry_run,
        )
        creation_id = str(res["id"])
        self._wait_until_finished(creation_id, poll_interval, max_wait)
        return self._publish(creation_id)

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
        self._wait_until_finished(creation_id, poll_interval, max_wait)
        return self._publish(creation_id)

    def post_carousel(self, caption: str, image_urls: list[str], poll_interval: int = 3, max_wait: int = 180) -> str:
        """카드뉴스(캐러셀, 2~10장): 장마다 is_carousel_item 컨테이너 → 모두 FINISHED → CAROUSEL 컨테이너(children) → FINISHED → 게시.
        2026-10-18 추가. 캡션은 캐러셀 컨테이너에만 붙는다."""
        if not 2 <= len(image_urls) <= 10:
            raise ValueError("캐러셀은 이미지 2~10장이어야 합니다")
        children = []
        for url in image_urls:
            res = http.request(
                "POST",
                f"{BASE_URL}/{self.ig_user_id}/media",
                data={"image_url": url, "is_carousel_item": "true", "access_token": self.token},
                dry_run=self.dry_run,
            )
            children.append(str(res["id"]))
        for cid in children:
            self._wait_until_finished(cid, poll_interval, max_wait)
        res = http.request(
            "POST",
            f"{BASE_URL}/{self.ig_user_id}/media",
            data={"media_type": "CAROUSEL", "children": ",".join(children), "caption": caption, "access_token": self.token},
            dry_run=self.dry_run,
        )
        creation_id = str(res["id"])
        self._wait_until_finished(creation_id, poll_interval, max_wait)
        return self._publish(creation_id)
