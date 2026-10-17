import tempfile
import unittest
from pathlib import Path

from pipeline import imagecheck


@unittest.skipUnless(imagecheck.available(), "PIL 없음")
class ImageCheckTests(unittest.TestCase):
    def setUp(self):
        from PIL import Image, ImageDraw
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        # a: 왼쪽 밝고 오른쪽 어두운 그라데이션, b: a 와 거의 같음(약간 밝기만 다름), c: 체커보드
        a = Image.new("L", (64, 64)); d = ImageDraw.Draw(a)
        for x in range(64): d.line([(x, 0), (x, 63)], fill=255 - x * 4)
        a.save(self.dir / "2026-01-01-a.jpg")
        b = a.point(lambda v: min(255, v + 10)); b.save(self.dir / "2026-01-02-b.jpg")
        c = Image.new("L", (64, 64)); d = ImageDraw.Draw(c)
        for x in range(0, 64, 8):
            for y in range(0, 64, 8):
                if (x // 8 + y // 8) % 2 == 0: d.rectangle([x, y, x + 7, y + 7], fill=255)
        c.save(self.dir / "2026-01-03-c.jpg")

    def tearDown(self):
        self.tmp.cleanup()

    def test_near_duplicate_is_flagged(self):
        cands = [self.dir / "2026-01-01-a.jpg"]
        self.assertTrue(imagecheck.too_similar(self.dir / "2026-01-02-b.jpg", cands))

    def test_different_image_passes(self):
        cands = [self.dir / "2026-01-01-a.jpg"]
        self.assertFalse(imagecheck.too_similar(self.dir / "2026-01-03-c.jpg", cands))

    def test_recent_images_newest_first(self):
        files = imagecheck.recent_images(self.dir, limit=2)
        self.assertEqual([f.name for f in files], ["2026-01-03-c.jpg", "2026-01-02-b.jpg"])

    def test_no_candidates(self):
        self.assertEqual(imagecheck.nearest(self.dir / "2026-01-01-a.jpg", []), (None, None))
        self.assertFalse(imagecheck.too_similar(self.dir / "2026-01-01-a.jpg", []))


if __name__ == "__main__":
    unittest.main()
