"""게시 직전 중복 검사 (2026-10-19 재시도·재게시로 같은 글이 두 번 올라간 사고의 재발 방지)."""
import contextlib
import io
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

import run_daily
from pipeline import KST, metrics, queue

NOW = datetime(2026, 10, 19, 9, 0, tzinfo=KST)
TEXT = "설거지하고 나면 손 트는 계절 왔다는 글이 늘어남\n난 손이 없어서 모르는데 궁금해서 네이버 리뷰를 읽어봄"


def _api_ts(dt: datetime) -> str:
    return dt.astimezone(KST).strftime("%Y-%m-%dT%H:%M:%S%z")  # Meta 식 '+0900'


class FakeClient:
    """recent_posts 로 가짜 최근 글을 돌려주고, post_* 호출을 기록한다."""

    def __init__(self, recent):
        self.recent = recent
        self.posted = []

    def recent_posts(self, limit=20):
        return self.recent[:limit]

    def post_text(self, text, link=None, topic_tag=None):
        self.posted.append(text)
        return "new-threads-id"

    def post_image(self, caption, image_url):
        self.posted.append(caption)
        return "new-ig-id"


def _item(id_, channels, status="pending", image=None):
    return {"id": id_, "kind": "product", "channels": channels, "text": TEXT, "image_url": image, "video_url": None,
            "affiliate": None, "scheduled_at": "2026-10-19T08:00:00+09:00", "status": status, "result": {}}


class ExistingPostIdTests(unittest.TestCase):
    def test_same_prefix_within_24h_is_duplicate(self):
        posted = run_daily.channel_text(_item("x", ["threads"]), "threads")
        c = FakeClient([{"id": "111", "text": posted, "timestamp": _api_ts(NOW - timedelta(hours=2))}])
        self.assertEqual(run_daily.existing_post_id(c, "threads", posted, NOW), "111")

    def test_same_prefix_older_than_24h_is_not_duplicate(self):
        posted = run_daily.channel_text(_item("x", ["threads"]), "threads")
        c = FakeClient([{"id": "111", "text": posted, "timestamp": _api_ts(NOW - timedelta(hours=30))}])
        self.assertIsNone(run_daily.existing_post_id(c, "threads", posted, NOW))

    def test_different_text_is_not_duplicate(self):
        c = FakeClient([{"id": "111", "text": "완전 다른 글이에요 " * 10, "timestamp": _api_ts(NOW)}])
        self.assertIsNone(run_daily.existing_post_id(c, "threads", TEXT, NOW))

    def test_prefix_compares_first_60_chars_only(self):
        a = "가" * 60 + " 뒤는 다름 1"
        b = "가" * 60 + " 뒤는 다름 2"
        c = FakeClient([{"id": "222", "text": a, "timestamp": _api_ts(NOW)}])
        self.assertEqual(run_daily.existing_post_id(c, "instagram", b, NOW), "222")

    def test_client_without_recent_posts_is_skipped(self):
        class Bare:
            pass
        self.assertIsNone(run_daily.existing_post_id(Bare(), "telegram", TEXT, NOW))


class RunDedupeTests(unittest.TestCase):
    """run() 전체 흐름: 큐·지표는 임시 파일, 클라이언트는 가짜."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self.qpath, self.mpath = d / "queue.json", d / "metrics.jsonl"
        load, mark, append, read_all = queue.load, queue.mark, metrics.append, metrics.read_all  # 원본 (기본 경로 대신 임시 파일로)
        self.patches = [
            mock.patch.object(queue, "load", lambda path=self.qpath: load(path)),
            mock.patch.object(queue, "mark", lambda *a, **k: mark(*a, path=self.qpath, **k)),
            mock.patch.object(metrics, "append", lambda ev, path=self.mpath: append(ev, path)),
            mock.patch.object(metrics, "read_all", lambda path=self.mpath: read_all(path)),
        ]
        for p in self.patches:
            p.start()
        self.out = io.StringIO()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def _run(self, clients, items, retry_failed=False):
        queue.save(items, self.qpath)
        with mock.patch.object(run_daily, "build_clients", lambda env, channels, dry_run: clients), \
             mock.patch.dict("os.environ", {"HUB_BASE_URL": "https://hub.test"}), \
             contextlib.redirect_stdout(self.out):
            stats = run_daily.run(NOW, list(clients), dry_run=False, retry_failed=retry_failed)
        return stats, {i["id"]: i for i in queue.load(self.qpath)}

    def test_already_posted_is_skipped_and_marked_posted(self):
        item = _item("2026-10-19-handcream-threads", ["threads"])
        posted = run_daily.channel_text(item, "threads")
        c = FakeClient([{"id": "18000001", "text": posted, "timestamp": _api_ts(NOW - timedelta(hours=1))}])
        stats, q = self._run({"threads": c}, [item])
        self.assertEqual(c.posted, [])  # 게시 안 함
        self.assertEqual(stats["posted"], 1)
        self.assertEqual(q[item["id"]]["status"], "posted")
        self.assertEqual(q[item["id"]]["result"], {"threads": "18000001", "note": run_daily.DUP_NOTE})
        events = [e["event"] for e in metrics.read_all(self.mpath)]
        self.assertEqual(events, ["post_skipped_duplicate"])
        self.assertIn("[DUP]", self.out.getvalue())

    def test_no_existing_post_is_published(self):
        item = _item("2026-10-19-handcream-instagram", ["instagram"], image="https://img.test/a.jpg")
        c = FakeClient([{"id": "17000001", "text": "어제 올린 다른 글 " * 8, "timestamp": _api_ts(NOW - timedelta(hours=3))}])
        stats, q = self._run({"instagram": c}, [item])
        self.assertEqual(len(c.posted), 1)
        self.assertEqual(q[item["id"]]["status"], "posted")
        self.assertEqual(q[item["id"]]["result"], {"instagram": "new-ig-id"})
        self.assertEqual([e["event"] for e in metrics.read_all(self.mpath)], ["post"])

    def test_retry_failed_goes_through_same_check(self):
        # 네트워크 오류로 failed 가 된 글. 사실은 API 에 이미 올라가 있다 → 재시도해도 다시 올리지 않는다
        item = _item("2026-10-19-handcream-threads", ["threads"], status="failed")
        metrics.append({"ts": (NOW - timedelta(hours=1)).isoformat(timespec="seconds"), "event": "post_failed", "channel": "threads",
                        "item_id": item["id"], "error": "<urlopen error [Errno 8] nodename nor servname provided>", "dry_run": False}, self.mpath)
        posted = run_daily.channel_text(item, "threads")
        c = FakeClient([{"id": "18000002", "text": posted, "timestamp": _api_ts(NOW - timedelta(minutes=50))}])
        stats, q = self._run({"threads": c}, [item], retry_failed=True)
        self.assertEqual(c.posted, [])
        self.assertEqual(q[item["id"]]["status"], "posted")
        self.assertEqual(q[item["id"]]["result"]["threads"], "18000002")
        self.assertEqual(q[item["id"]]["result"]["note"], run_daily.DUP_NOTE)

    def test_recent_posts_failure_marks_failed_not_posted(self):
        # 목록을 못 읽으면 게시하지 않고 failed 로 남긴다 (중복보다 미게시가 낫다)
        class Broken(FakeClient):
            def recent_posts(self, limit=20):
                raise RuntimeError("<urlopen error [Errno 8] nodename nor servname provided>")
        item = _item("2026-10-19-handcream-threads", ["threads"])
        c = Broken([])
        stats, q = self._run({"threads": c}, [item])
        self.assertEqual(c.posted, [])
        self.assertEqual(q[item["id"]]["status"], "failed")
        self.assertEqual(stats["failed"], 1)


class ClientRecentPostsTests(unittest.TestCase):
    def test_threads_and_instagram_parse_list(self):
        from pipeline import http
        from pipeline.instagram_client import InstagramClient
        from pipeline.threads_client import ThreadsClient
        calls = []

        def fake(method, url, data=None, params=None, dry_run=False):
            calls.append((method, url, params))
            if "threads.net" in url:
                return {"data": [{"id": "1", "text": "a", "timestamp": "2026-10-19T00:00:00+0000"}]}
            return {"data": [{"id": "2", "caption": "b", "timestamp": "2026-10-19T00:00:00+0000"}, {"id": "3"}]}
        with mock.patch.object(http, "request", fake):
            t = ThreadsClient("U1", "tok").recent_posts()
            i = InstagramClient("I1", "tok").recent_posts()
        self.assertEqual(t, [{"id": "1", "text": "a", "timestamp": "2026-10-19T00:00:00+0000"}])
        self.assertEqual(i[0], {"id": "2", "text": "b", "timestamp": "2026-10-19T00:00:00+0000"})
        self.assertEqual(i[1]["text"], "")
        self.assertIn("/U1/threads", calls[0][1]); self.assertEqual(calls[0][2]["limit"], 20)
        self.assertIn("/I1/media", calls[1][1]); self.assertEqual(calls[1][2]["limit"], 10)

    def test_dry_run_returns_empty(self):
        from pipeline.threads_client import ThreadsClient
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ThreadsClient("U1", "tok", dry_run=True).recent_posts(), [])


if __name__ == "__main__":
    unittest.main()
