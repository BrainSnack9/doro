"""선팔 대상 고르기 (2026-10-20)."""
import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engage import follow  # noqa: E402
from pipeline import KST  # noqa: E402


class PickTargetsTests(unittest.TestCase):
    def test_replied_first_then_candidates_and_skips(self):
        now = datetime(2026, 10, 20, 15, 0, tzinfo=KST)
        replied = {
            "a": {"user": "@old", "at": "2026-10-10T10:00:00+09:00"},            # 3일보다 오래됨 → 제외
            "b": {"user": "@new1", "at": "2026-10-20T14:00:00+09:00"},
            "c": {"user": "@new2", "at": "2026-10-19T20:00:00+09:00"},
            "d": {"user": "@haru.reviews", "at": "2026-10-20T14:00:00+09:00"},   # 우리 계정 → 제외
            "e": {"user": "@done", "at": "2026-10-20T14:00:00+09:00"},           # 이미 팔로우 → 제외
        }
        follows = {"done": {"at": "2026-10-19T10:00:00+09:00", "result": "followed"}}
        cands = [{"user": "@cand1"}, {"user": "@new1"}, {"user": "@cand2"}]
        out = follow.pick_targets(follows, replied, cands, now, limit=3)
        self.assertEqual(out, [("new1", "replied"), ("new2", "replied"), ("cand1", "candidate")])

    def test_daily_count_and_limit(self):
        follows = {"x": {"at": "2026-10-20T10:00:00+09:00", "result": "followed"},
                   "y": {"at": "2026-10-20T10:01:00+09:00", "result": "already"},
                   "z": {"at": "2026-10-19T10:00:00+09:00", "result": "followed"}}
        self.assertEqual(follow.today_count(follows, "2026-10-20"), 1)
        self.assertEqual(follow.FOLLOW_DAILY_LIMIT, 20)


if __name__ == "__main__":
    unittest.main()
