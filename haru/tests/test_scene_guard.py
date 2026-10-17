import unittest

import run_daily


def _it(id_, scene, status="posted", updated="2026-10-17T10:00:00+09:00", deleted=False):
    return {"id": id_, "status": status, "image_url": "https://img.test/x.png", "image_scene": scene, "updated_at": updated, "deleted": deleted}


class SceneGuardTests(unittest.TestCase):
    def test_same_scene_as_recent_other_product_is_blocked(self):
        items = [_it("2026-10-17-curtain-v2-instagram", "floor_table")]
        new = _it("2026-10-17-multitap-v2-instagram", "floor_table", status="pending")
        self.assertIn("floor_table", run_daily.scene_conflict_reason(new, items))

    def test_same_product_repost_is_allowed(self):
        items = [_it("2026-10-17-multitap-v2-threads", "desk")]
        new = _it("2026-10-17-multitap-v2-instagram", "desk", status="pending")
        self.assertIsNone(run_daily.scene_conflict_reason(new, items))

    def test_deleted_and_old_posts_are_ignored(self):
        items = [_it("2026-10-10-a-v1-instagram", "desk", deleted=True)]
        items += [_it(f"2026-10-1{i}-p{i}-v1-instagram", f"s{i}", updated=f"2026-10-1{i}T10:00:00+09:00") for i in range(1, 7)]
        items.append(_it("2026-10-01-old-v1-instagram", "desk", updated="2026-10-01T10:00:00+09:00"))
        new = _it("2026-10-17-new-v1-instagram", "desk", status="pending")
        self.assertIsNone(run_daily.scene_conflict_reason(new, items))  # 삭제된 글과 5건 밖의 글은 무시

    def test_no_scene_key_is_not_checked(self):
        new = {"id": "2026-10-17-x-v1-instagram", "image_url": "https://img.test/x.png"}
        self.assertIsNone(run_daily.scene_conflict_reason(new, [_it("2026-10-17-y-v1-instagram", None)]))


if __name__ == "__main__":
    unittest.main()
