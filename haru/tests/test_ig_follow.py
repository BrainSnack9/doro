"""인스타 선팔 대상 선별·감축 규칙 (2026-10-21)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engage import ig_follow  # noqa: E402


class SelectableTests(unittest.TestCase):
    def test_business_handles_and_bad_formats(self):
        for h in ("jachwi.room", "lazy_but_real", "haru_day_01"):
            self.assertTrue(ig_follow.selectable(h), h)
        for h in ("oh.clean", "saramara.pick", "hot.deal0110", "mkt_log", "cozyshop", "haru_official", "oneroom_studio", "seoul.interior"):
            self.assertFalse(ig_follow.selectable(h), h)
        for h in ("", "has space", "@at", "a" * 31):
            self.assertFalse(ig_follow.selectable(h), repr(h))


class DedupeTests(unittest.TestCase):
    def test_skips_owner_seen_business_and_duplicates_keeping_order(self):
        follows = {"done": {"result": "followed"}, "Tried": {"result": "skip:followers"}}
        cands = [("@a", "comment"), ("haru.reviews", "comment"), ("done", "comment"), ("tried", "tag:자취"),
                 ("cozyshop", "tag:자취"), ("b", "tag:자취"), ("A", "tag:원룸"), ("", "tag:원룸")]
        self.assertEqual(ig_follow.dedupe_candidates(cands, follows), [("a", "comment"), ("b", "tag:자취")])


class ScreenTests(unittest.TestCase):
    def test_rules(self):
        self.assertIsNone(ig_follow.screen({"followers": 4999, "posts": 5}))
        self.assertEqual(ig_follow.screen({"followers": 5000, "posts": 50}), "followers")
        self.assertEqual(ig_follow.screen({"followers": 10, "posts": 4}), "posts")
        self.assertEqual(ig_follow.screen({"gone": True}), "gone")
        self.assertEqual(ig_follow.screen({"followers": 10, "posts": 9, "following": True}), "already")
        self.assertEqual(ig_follow.screen({"text": "뭔가 못 읽음"}), "unknown")

    def test_dom_text_fallback(self):
        ko = "팔로워 1.2만명, 팔로우 300명, 게시물 45개 - 하루(@x)님의 Instagram"
        self.assertEqual(ig_follow.parse_profile_text(ko), {"followers": 12000, "posts": 45})
        en = "1,234 Followers, 56 Following, 78 Posts - See Instagram photos"
        self.assertEqual(ig_follow.parse_profile_text(en), {"followers": 1234, "posts": 78})
        self.assertEqual(ig_follow.screen({"text": ko}), "followers")
        brand = "팔로워 1M명, 팔로잉 66명, 게시물 13K개 - 오늘의집(@todayhouse)님의 Instagram | 게시물 1.3만 팔로워 130.1만"
        self.assertEqual(ig_follow.parse_profile_text(brand), {"followers": 1_000_000, "posts": 13_000})
        small = "팔로워 63명, 팔로잉 35명, 게시물 5개 - 세포집(@sepo.zip)님의 Instagram | 게시물 5 팔로워 64 팔로우 35"
        self.assertEqual(ig_follow.parse_profile_text(small), {"followers": 63, "posts": 5})
        self.assertIsNone(ig_follow.screen({"text": small}))
        self.assertIsNone(ig_follow.screen({"text": en}))
        self.assertEqual(ig_follow.parse_count("5천"), 5000)
        self.assertEqual(ig_follow.parse_count("1.5M"), 1_500_000)
        self.assertIsNone(ig_follow.parse_count("없음"))


class PickTargetsTests(unittest.TestCase):
    def test_comment_first_then_tags_with_profile_screen(self):
        follows = {"old": {"result": "followed"}}
        cands = [("c1", "comment"), ("old", "comment"), ("big", "comment"), ("t1", "tag:자취"), ("few", "tag:자취"), ("t2", "tag:원룸"), ("unread", "tag:원룸")]
        profiles = {"c1": {"followers": 120, "posts": 30}, "big": {"followers": 9000, "posts": 300},
                    "t1": {"followers": 800, "posts": 12}, "few": {"followers": 50, "posts": 2}, "t2": {"followers": 300, "posts": 7}}
        picked, rejected = ig_follow.pick_targets(cands, follows, profiles, limit=4)
        self.assertEqual(picked, [("c1", "comment"), ("t1", "tag:자취"), ("t2", "tag:원룸")])
        self.assertEqual(rejected, {"big": "followers", "few": "posts"})   # unread 는 아직 안 읽음 → 어느 쪽에도 없음

    def test_limit(self):
        profiles = {"a": {"followers": 1, "posts": 5}, "b": {"followers": 1, "posts": 5}}
        picked, _ = ig_follow.pick_targets([("a", "comment"), ("b", "comment")], {}, profiles, limit=1)
        self.assertEqual(picked, [("a", "comment")])
        self.assertEqual(ig_follow.pick_targets([("a", "comment")], {}, profiles, limit=0), ([], {}))


class LimitTests(unittest.TestCase):
    def test_taper_and_ratio_guard(self):
        self.assertEqual(ig_follow.IG_DAILY_LIMIT, 8)
        self.assertEqual(ig_follow.PER_RUN, 4)
        self.assertEqual(ig_follow.daily_limit(0, 0), 8)
        self.assertEqual(ig_follow.daily_limit(99, 119), 8)
        self.assertEqual(ig_follow.daily_limit(100, 0), 5)
        self.assertEqual(ig_follow.daily_limit(299, 0), 5)
        self.assertEqual(ig_follow.daily_limit(300, 0), 3)
        self.assertEqual(ig_follow.daily_limit(999, 0), 3)
        self.assertEqual(ig_follow.daily_limit(1000, 0), 0)      # 목표 도달 → 멈춤
        self.assertEqual(ig_follow.daily_limit(50, 120), 0)       # 팔로잉 120 ≥ max(120, 100) → 멈춤
        self.assertEqual(ig_follow.daily_limit(200, 399), 5)      # 399 < 400 → 아직 가능
        self.assertEqual(ig_follow.daily_limit(200, 400), 0)

    def test_today_count_counts_followed_and_requested_only(self):
        follows = {"x": {"at": "2026-10-21T10:00:00+09:00", "result": "followed"},
                   "y": {"at": "2026-10-21T10:01:00+09:00", "result": "requested"},
                   "z": {"at": "2026-10-21T10:02:00+09:00", "result": "skip:followers"},
                   "w": {"at": "2026-10-20T10:00:00+09:00", "result": "followed"}}
        self.assertEqual(ig_follow.today_count(follows, "2026-10-21"), 2)
        self.assertEqual(ig_follow.total_followed(follows), 3)


if __name__ == "__main__":
    unittest.main()
