"""Telegram Bot API 클라이언트 (선택 채널)."""

from . import http

BASE_URL = "https://api.telegram.org"


class TelegramClient:
    def __init__(self, token: str, chat_id: str, dry_run: bool = False) -> None:
        self.token = token
        self.chat_id = chat_id
        self.dry_run = dry_run

    def _url(self, method: str) -> str:
        return f"{BASE_URL}/bot{self.token}/{method}"

    def send_photo(self, photo_url: str, caption_html: str) -> str:
        res = http.request(
            "POST",
            self._url("sendPhoto"),
            data={"chat_id": self.chat_id, "photo": photo_url, "caption": caption_html, "parse_mode": "HTML"},
            dry_run=self.dry_run,
        )
        return str(res.get("id") or res.get("result", {}).get("message_id", ""))

    def send_text(self, text_html: str) -> str:
        res = http.request(
            "POST",
            self._url("sendMessage"),
            data={"chat_id": self.chat_id, "text": text_html, "parse_mode": "HTML"},
            dry_run=self.dry_run,
        )
        return str(res.get("id") or res.get("result", {}).get("message_id", ""))
