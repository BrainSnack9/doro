import contextlib
import io
import unittest

from pipeline import http
from pipeline.disclosure import compose
from pipeline.instagram_client import API_VERSION, InstagramClient
from pipeline.telegram_client import TelegramClient
from pipeline.threads_client import ThreadsClient

TOKEN = "SECRET-TOKEN-abc123"


def capture(fn, *a, **kw):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        result = fn(*a, **kw)
    return result, buf.getvalue()


class HttpDryRunTests(unittest.TestCase):
    def test_masks_token_in_body_and_query(self):
        res, out = capture(http.request, "POST", "https://x.test/p", data={"access_token": TOKEN, "text": "hi"},
                           params={"access_token": TOKEN, "fields": "a"}, dry_run=True)
        self.assertNotIn(TOKEN, out)
        self.assertIn("REDACTED", out)
        self.assertIn("fields=a", out)
        self.assertTrue(res["id"].startswith("dryrun-"))

    def test_masks_telegram_path_token(self):
        _, out = capture(http.request, "POST", f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                         data={"chat_id": "1", "text": "x"}, dry_run=True)
        self.assertNotIn(TOKEN, out)
        self.assertIn("/bot***REDACTED***/sendMessage", out)

    def test_deterministic_id(self):
        a, _ = capture(http.request, "GET", "https://x.test/a", dry_run=True)
        b, _ = capture(http.request, "GET", "https://x.test/a", dry_run=True)
        self.assertEqual(a["id"], b["id"])


class ThreadsDryRunTests(unittest.TestCase):
    def setUp(self):
        self.c = ThreadsClient("U1", TOKEN, dry_run=True)

    def test_post_text_with_link(self):
        pid, out = capture(self.c.post_text, compose("글", False), link="https://hub.test/")
        self.assertIn("POST https://graph.threads.net/v1.0/U1/threads", out)
        self.assertIn('"media_type": "TEXT"', out)
        self.assertIn('"link_attachment": "https://hub.test/"', out)
        self.assertIn("POST https://graph.threads.net/v1.0/U1/threads_publish", out)
        self.assertNotIn(TOKEN, out)
        self.assertTrue(pid.startswith("dryrun-"))

    def test_post_image_and_video(self):
        _, out = capture(self.c.post_image, compose("i", False), "https://img.test/a.jpg")
        self.assertIn('"media_type": "IMAGE"', out)
        self.assertIn('"image_url": "https://img.test/a.jpg"', out)
        _, out = capture(self.c.post_video, compose("v", False), "https://img.test/a.mp4")
        self.assertIn('"media_type": "VIDEO"', out)
        self.assertIn('"video_url"', out)

    def test_topic_tag_is_sent_and_sanitized(self):
        _, out = capture(self.c.post_text, compose("t", False), None, "자취")
        self.assertIn('"topic_tag": "자취"', out)
        _, out = capture(self.c.post_image, compose("i", False), "https://img.test/a.jpg", "#원룸")
        self.assertIn('"topic_tag": "원룸"', out)
        _, out = capture(self.c.post_text, compose("t", False), None, "a.b&c")  # 마침표·& 금지 → 안 붙임
        self.assertNotIn("topic_tag", out)
        _, out = capture(self.c.post_text, compose("t", False))
        self.assertNotIn("topic_tag", out)

    def test_post_with_link_comment(self):
        res, out = capture(self.c.post_with_link_comment, compose("상품", True), "https://img.test/p.jpg",
                           "https://aff.test/x", compose("보러가기", True))
        self.assertIn("post_id", res)
        self.assertIn("reply_id", res)
        self.assertIn(f'"reply_to_id": "{res["post_id"]}"', out)
        self.assertIn('"link_attachment": "https://aff.test/x"', out)
        self.assertEqual(out.count("threads_publish"), 2)
        self.assertNotIn(TOKEN, out)

    def test_publishing_quota(self):
        _, out = capture(self.c.publishing_quota)
        self.assertIn("GET https://graph.threads.net/v1.0/U1/threads_publishing_limit", out)
        self.assertIn("fields=quota_usage%2Cconfig", out)
        self.assertNotIn(TOKEN, out)

    def test_rejects_text_without_label(self):
        with self.assertRaises(ValueError):
            capture(self.c.post_text, "고지 없음")


class InstagramDryRunTests(unittest.TestCase):
    def setUp(self):
        self.c = InstagramClient("IG1", TOKEN, dry_run=True)

    def test_post_image(self):
        _, out = capture(self.c.post_image, "cap", "https://img.test/a.jpg")
        self.assertIn(f"POST https://graph.instagram.com/{API_VERSION}/IG1/media", out)
        self.assertIn(f"POST https://graph.instagram.com/{API_VERSION}/IG1/media_publish", out)
        self.assertIn('"creation_id"', out)
        self.assertIn("fields=status_code", out)  # 게시 전 컨테이너 FINISHED 확인
        self.assertNotIn(TOKEN, out)

    def test_post_reel_polls_status(self):
        _, out = capture(self.c.post_reel, "cap", "https://img.test/a.mp4", poll_interval=0, max_wait=0)
        self.assertIn('"media_type": "REELS"', out)
        self.assertIn('"share_to_feed": "true"', out)
        self.assertIn("fields=status_code", out)
        self.assertIn("media_publish", out)
        self.assertNotIn(TOKEN, out)


class TelegramDryRunTests(unittest.TestCase):
    def setUp(self):
        self.c = TelegramClient(TOKEN, "CHAT9", dry_run=True)

    def test_send_photo(self):
        _, out = capture(self.c.send_photo, "https://img.test/a.jpg", "<b>hi</b>")
        self.assertIn("/sendPhoto", out)
        self.assertIn('"parse_mode": "HTML"', out)
        self.assertIn('"chat_id": "CHAT9"', out)
        self.assertNotIn(TOKEN, out)

    def test_send_text(self):
        _, out = capture(self.c.send_text, "hello")
        self.assertIn("/sendMessage", out)
        self.assertNotIn(TOKEN, out)


if __name__ == "__main__":
    unittest.main()

    def test_delete_dry_run(self):
        res, out = capture(self.c.delete, "123")
        self.assertTrue(res)
        self.assertIn("DELETE https://graph.threads.net/v1.0/123", out)

