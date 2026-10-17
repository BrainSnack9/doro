import json
import tempfile
import unittest
from pathlib import Path

from ops import build_dashboard, collect


class DashboardTests(unittest.TestCase):
    def test_product_token(self):
        self.assertEqual(collect.product_token("2026-10-17-multitap-v2-instagram"), "multitap")

    def test_build_from_sample(self):
        sample = {
            "generated_at": "2026-10-17T18:00:00+09:00",
            "accounts": {"threads": {"views": 33, "followers_count": 0}, "instagram": {"followers_count": 2, "media_count": 3}},
            "posts": [{"key": "2026-10-17-multitap", "date": "2026-10-17", "product": "multitap", "kind": "product", "channels": {"threads": {"post_id": "1", "insights": {"views": 26, "likes": 0, "replies": 1}, "permalink": "https://t.example/1"}}, "pending": [{"channel": "instagram", "item_id": "x", "scheduled_at": "2026-10-18T07:00:00+09:00"}], "failed": [], "image_url": None, "image_scene": "desk", "naver_blog": "https://blog.example/1", "affiliate": {"program": "네이버"}, "text": "훅"}],
            "hub_items": [{}], "photos": [{"file": "2026-10-17-multitap-b.jpg", "product": "multitap", "used_by": ["2026-10-17-multitap"], "size_kb": 120}],
            "events": [{"ts": "2026-10-17T16:00:00+09:00", "event": "post_failed", "channel": "threads", "item_id": "x", "error": "boom"}],
            "revenue": {"naver": {"sales_30d": {"expected_revenue": "0", "clicks": "0"}, "settlement": {"account": "미등록"}, "links": []}, "coupang": {"status": "needs_login"}, "manual": {"ohouse": {"expected_revenue": None}}},
            "system": {"tests": "OK", "git_head": "abc", "hub_cert": {"subject": "harureviews.date", "not_after": "Jan 15 2027"}}, "errors": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "dashboard.json"; data.write_text(json.dumps(sample, ensure_ascii=False), encoding="utf-8")
            old_data, old_dist = build_dashboard.DATA, build_dashboard.DIST
            try:
                build_dashboard.DATA, build_dashboard.DIST = data, Path(tmp) / "dist"
                out = build_dashboard.build()
            finally:
                build_dashboard.DATA, build_dashboard.DIST = old_data, old_dist
            pages = {f.name: f.read_text(encoding="utf-8") for f in out.parent.glob("*.html")}
            self.assertEqual(sorted(pages), ["index.html", "photos.html", "posts.html", "revenue.html", "system.html"])
            self.assertIn("multitap", pages["index.html"]); self.assertIn("로그인 필요", pages["index.html"])
            self.assertIn("⏳ instagram", pages["posts.html"])
            self.assertIn("boom", pages["system.html"]); self.assertIn("multitap-b.jpg", pages["photos.html"])


if __name__ == "__main__":
    unittest.main()
