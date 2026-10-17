import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from pipeline import KST, queue


def _item(id_, scheduled_at, status="pending"):
    return {
        "id": id_, "kind": "daily", "channels": ["threads"], "text": "t",
        "image_url": None, "video_url": None, "affiliate": None,
        "scheduled_at": scheduled_at, "status": status, "result": {},
    }


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "queue.json"
        queue.save([
            _item("a", "2026-10-17T08:00:00+09:00"),
            _item("b", "2026-10-17T10:00:00+09:00"),
            _item("c", "2026-10-17T07:00:00+09:00", status="posted"),
            _item("d", "2026-10-17T06:00:00"),  # naive -> KST
        ], self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_load_save_roundtrip(self):
        items = queue.load(self.path)
        self.assertEqual([i["id"] for i in items], ["a", "b", "c", "d"])
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertIn("items", raw)

    def test_due_items_filters_and_sorts(self):
        now = datetime(2026, 10, 17, 9, 0, tzinfo=KST)
        due = queue.due_items(now, queue.load(self.path))
        self.assertEqual([i["id"] for i in due], ["d", "a"])  # c posted, b future

    def test_due_items_utc_now(self):
        now_utc = datetime.fromisoformat("2026-10-17T00:00:00+00:00")  # 09:00 KST
        due = queue.due_items(now_utc, queue.load(self.path))
        self.assertEqual([i["id"] for i in due], ["d", "a"])

    def test_mark_updates_status_and_result(self):
        queue.mark("a", "posted", {"threads": "123"}, path=self.path)
        items = {i["id"]: i for i in queue.load(self.path)}
        self.assertEqual(items["a"]["status"], "posted")
        self.assertEqual(items["a"]["result"]["threads"], "123")
        self.assertIn("updated_at", items["a"])
        # 다시 due 에 포함되지 않음 (멱등)
        now = datetime(2026, 10, 17, 9, 0, tzinfo=KST)
        self.assertNotIn("a", [i["id"] for i in queue.due_items(now, queue.load(self.path))])

    def test_mark_bad_status(self):
        with self.assertRaises(ValueError):
            queue.mark("a", "weird", path=self.path)

    def test_mark_unknown_id(self):
        with self.assertRaises(KeyError):
            queue.mark("zzz", "posted", path=self.path)

    def test_bundled_examples_have_three_kinds(self):
        # 형식 예시는 data/queue.examples.json 에 있고 run_daily 는 읽지 않는다.
        items = queue.load(queue.QUEUE_PATH.with_name("queue.examples.json"))
        self.assertEqual(len(items), 3)
        kinds = sorted(i["kind"] for i in items)
        self.assertEqual(kinds, ["daily", "journal", "product"])

    def test_live_queue_items_are_well_formed(self):
        # 실제 큐는 매일 내용이 바뀌므로 개수 대신 형식만 검사한다.
        required = {"id", "kind", "channels", "text", "image_url", "video_url", "affiliate", "scheduled_at", "status", "result"}
        for it in queue.load():
            self.assertTrue(required <= set(it), f"{it.get('id')}: 필드 누락 {required - set(it)}")
            self.assertIn(it["kind"], ("product", "daily", "journal", "aside"))
            self.assertIn(it["status"], queue.STATUSES)
            queue.parse_kst(it["scheduled_at"])
            self.assertNotIn("example.com", json.dumps(it), f"{it['id']}: 예시 URL 은 실제 큐에 둘 수 없음")
            if "instagram" in it["channels"]:
                self.assertTrue(it["image_url"] or it["video_url"], f"{it['id']}: Instagram 은 이미지/비디오 필요")


if __name__ == "__main__":
    unittest.main()
