"""상품 글 형식(글 중심/사진 글)과 인스타 해시태그 (2026-10-19)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_daily  # noqa: E402


class FakeThreads:
    def __init__(self):
        self.calls = []

    def post_text_first(self, text, link, image_url, reply_text, topic_tag=None):
        self.calls.append(("text_first", text, link, image_url, reply_text, topic_tag)); return {"post_id": "p", "reply_id": "r"}

    def post_with_link_comment(self, text, image_url, link, link_text, topic_tag=None):
        self.calls.append(("image", text, image_url, link, link_text, topic_tag)); return {"post_id": "p", "reply_id": "r"}


def _item(**over):
    it = {"id": "x-threads", "kind": "product", "channels": ["threads"], "text": "본문\n가격. 링크 댓글에",
          "image_url": "https://img.test/a.jpg", "affiliate": {"program": "쿠팡", "url": "https://aff.test/x", "label": "라벨"}}
    it.update(over); return it


class PostFormatTests(unittest.TestCase):
    def test_default_is_text_first(self):
        c = FakeThreads(); run_daily.post_item(_item(), "threads", c, "")
        kind, text, link, image, reply_text, topic = c.calls[0]
        self.assertEqual(kind, "text_first"); self.assertEqual(link, "https://aff.test/x"); self.assertEqual(image, "https://img.test/a.jpg")
        self.assertIn("링크는 아래 카드, 사진은 댓글에", text); self.assertNotIn("링크 댓글에", text)
        self.assertIn("라벨", reply_text); self.assertIn(run_daily.HUB_URL, reply_text); self.assertEqual(topic, "자취")

    def test_item_can_keep_image_format(self):
        c = FakeThreads(); run_daily.post_item(_item(format="image"), "threads", c, "")
        self.assertEqual(c.calls[0][0], "image"); self.assertIn("링크 댓글에", c.calls[0][1])

    def test_ig_hashtags(self):
        tags = run_daily.ig_hashtags({"hashtags": ["핸드크림", "#자취"]})
        self.assertTrue(tags.startswith("#핸드크림 #자취 ")); self.assertEqual(len(tags.split()), 10)
        self.assertEqual(run_daily.ig_hashtags({"hashtags": []}), "")
        cap = run_daily.channel_text(_item(channels=["instagram"]), "instagram")
        self.assertTrue(cap.rstrip().endswith("#" + run_daily.IG_HASHTAGS[-1]) or cap.count("#") == 10)
        self.assertIn("링크는 프로필에", cap)
        self.assertLess(cap.index("링크는 프로필에"), cap.index("#자취"))  # 해시태그는 맨 아래 문단


if __name__ == "__main__":
    unittest.main()
