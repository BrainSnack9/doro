import copy
import json
import subprocess
import sys
import tempfile
import time
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


class QueueMergeSaveTests(unittest.TestCase):
    """2026-10-20: run_daily 루프가 메모리 사본을 통째로 저장해 다른 프로세스의 편집이 사라진 사고의 재발 방지."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "queue.json"
        queue.save([_item("a", "2026-10-17T08:00:00+09:00"), _item("b", "2026-10-17T10:00:00+09:00")], self.path)
        # 실행 시작: 파일을 읽고 사본을 둔다
        self.items = queue.load(self.path)
        self.snapshot = copy.deepcopy(self.items)

    def tearDown(self):
        self.tmp.cleanup()

    def _external_edit(self, fn):
        """다른 프로세스(편집 스크립트)가 그 사이 파일을 고친 상황."""
        with queue.with_queue_lock(self.path):
            cur = queue.load(self.path)
            fn(cur)
            queue.save(cur, self.path)

    def test_external_edit_of_a_and_posted_b_both_survive(self):
        def edit(cur):
            a = next(it for it in cur if it["id"] == "a")
            a["scheduled_at"] = "2026-10-17T19:10:00+09:00"; a["text"] = "릴스로 교체"; a["video_url"] = "https://v/1.mp4"
        self._external_edit(edit)
        b = next(it for it in self.items if it["id"] == "b")
        queue.apply_status(b, "posted", {"threads": "777"})
        applied = queue.save_changes(self.snapshot, self.items, self.path)
        self.assertEqual(applied, ["b"])
        after = {it["id"]: it for it in queue.load(self.path)}
        self.assertEqual(after["a"]["scheduled_at"], "2026-10-17T19:10:00+09:00")
        self.assertEqual(after["a"]["text"], "릴스로 교체")
        self.assertEqual(after["a"]["video_url"], "https://v/1.mp4")
        self.assertEqual(after["a"]["status"], "pending")
        self.assertEqual(after["b"]["status"], "posted")
        self.assertEqual(after["b"]["result"], {"threads": "777"})
        self.assertIn("updated_at", after["b"])

    def test_externally_added_item_survives(self):
        self._external_edit(lambda cur: cur.append(_item("c", "2026-10-17T22:00:00+09:00")))
        queue.apply_status(next(it for it in self.items if it["id"] == "b"), "posted", {"threads": "1"})
        queue.save_changes(self.snapshot, self.items, self.path)
        ids = [it["id"] for it in queue.load(self.path)]
        self.assertEqual(ids, ["a", "b", "c"])

    def test_externally_removed_item_is_not_revived(self):
        def edit(cur):
            cur[:] = [it for it in cur if it["id"] != "a"]
        self._external_edit(edit)
        queue.apply_status(next(it for it in self.items if it["id"] == "a"), "posted", {"threads": "1"})
        applied = queue.save_changes(self.snapshot, self.items, self.path)
        self.assertEqual(applied, [])
        self.assertEqual([it["id"] for it in queue.load(self.path)], ["b"])

    def test_no_changes_does_not_touch_file(self):
        before = self.path.stat().st_mtime_ns
        self.assertEqual(queue.save_changes(self.snapshot, self.items, self.path), [])
        self.assertEqual(self.path.stat().st_mtime_ns, before)

    def test_changed_fields_only_merge_fields(self):
        b = next(it for it in self.items if it["id"] == "b")
        b["text"] = "메모리에서만 바꿈"; b["status"] = "failed"
        self.assertEqual(queue.changed_fields(self.snapshot, self.items), {"b": {"status": "failed"}})

    def test_save_keeps_indent_1_and_unicode(self):
        raw = self.path.read_text(encoding="utf-8")
        self.assertTrue(raw.startswith('{\n "items": [\n  {\n'), raw[:30])
        self.assertIn("한글", json.dumps({"x": "한글"}, ensure_ascii=False))
        queue.save([_item("가", "2026-10-17T08:00:00+09:00")], self.path)
        self.assertIn('"가"', self.path.read_text(encoding="utf-8"))


class QueueLockTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "queue.json"

    def tearDown(self):
        self.tmp.cleanup()

    def _try_lock_in_other_process(self) -> bool:
        """다른 프로세스가 비차단으로 잠금을 잡을 수 있는지 (True 면 아무도 안 잡고 있음)."""
        code = ("import fcntl,sys\n"
                "f=open(sys.argv[1],'a+')\n"
                "try:\n fcntl.flock(f.fileno(), fcntl.LOCK_EX|fcntl.LOCK_NB); print('free')\n"
                "except OSError:\n print('held')\n")
        out = subprocess.run([sys.executable, "-c", code, str(queue.lock_path(self.path))], capture_output=True, text=True, timeout=20)
        return out.stdout.strip() == "free"

    def test_lock_is_held_across_processes_and_reentrant(self):
        with queue.with_queue_lock(self.path):
            self.assertFalse(self._try_lock_in_other_process())
            with queue.with_queue_lock(self.path):  # 같은 스레드에서 중첩 (save → with_queue_lock)
                queue.save([_item("a", "2026-10-17T08:00:00+09:00")], self.path)
            self.assertFalse(self._try_lock_in_other_process())
        self.assertTrue(self._try_lock_in_other_process())

    def test_mark_waits_for_other_process_lock(self):
        queue.save([_item("a", "2026-10-17T08:00:00+09:00")], self.path)
        holder = subprocess.Popen([sys.executable, "-c",
                                   "import fcntl,sys,time\nf=open(sys.argv[1],'a+')\nfcntl.flock(f.fileno(), fcntl.LOCK_EX)\n"
                                   "print('locked', flush=True)\ntime.sleep(0.8)\n", str(queue.lock_path(self.path))],
                                  stdout=subprocess.PIPE, text=True)
        self.assertEqual(holder.stdout.readline().strip(), "locked")
        t0 = time.monotonic()
        queue.mark("a", "posted", {"threads": "1"}, path=self.path)
        self.assertGreater(time.monotonic() - t0, 0.4)  # 잠금이 풀릴 때까지 기다렸다
        holder.wait(timeout=10)
        self.assertEqual(queue.load(self.path)[0]["status"], "posted")
