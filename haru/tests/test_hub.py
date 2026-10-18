import json
import tempfile
import unittest
from pathlib import Path

from hub import build_hub


class HubBuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dist = Path(self.tmp.name) / "dist"
        self.links = Path(self.tmp.name) / "links.json"

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, items, meta=None):
        self.links.write_text(json.dumps({"title": "t", "meta": meta or {}, "items": items}, ensure_ascii=False), encoding="utf-8")

    def test_builds_home_and_item_pages(self):
        self._write([
            {"date": "2026-10-17", "name": "큐브 멀티탭", "reason": "r", "program": "네이버", "url": "https://naver.me/x", "category": "자취방", "price": "29,800원", "fact": "리뷰 2,662개", "con": "스위치"},
            {"date": "2026-10-16", "name": "트롤리", "reason": "r2", "program": "쿠팡", "url": "https://link.coupang.com/a/y"},
        ])
        build_hub.build(self.links, self.dist)
        home = (self.dist / "index.html").read_text(encoding="utf-8")
        self.assertIn("오늘의 추천", home)
        self.assertIn("큐브 멀티탭", home)          # 최신 항목이 히어로
        self.assertIn('data-cat="자취방"', home)
        self.assertIn("쿠팡 파트너스 활동", home)   # 쿠팡 항목이 있으면 지정 문구
        pages = sorted(p.name for p in (self.dist / "p").glob("*.html"))
        self.assertEqual(len(pages), 2)
        detail = (self.dist / "p" / f"{build_hub.slugify({'date': '2026-10-17', 'name': '큐브 멀티탭'})}.html").read_text(encoding="utf-8")
        self.assertIn("단점 하나", detail)
        self.assertIn('href="../go/', detail)          # 판매처 버튼은 go 페이지를 거친다
        self.assertNotIn("cloudflareinsights", detail)  # 토큰 없으면 집계 스크립트 생략
        go = (self.dist / "go" / f"{build_hub.slugify({'date': '2026-10-17', 'name': '큐브 멀티탭'})}.html").read_text(encoding="utf-8")
        self.assertIn('href="https://naver.me/x"', go)
        self.assertIn("var delay = 0;", go)             # 집계 없으면 바로 이동

    def test_cloudflare_analytics_when_token_set(self):
        self._write([{"date": "2026-10-17", "name": "a", "reason": "r", "program": "오늘의집", "url": "https://ozip.me/z?af"}], {"cloudflare_token": "abc123"})
        build_hub.build(self.links, self.dist)
        home = (self.dist / "index.html").read_text(encoding="utf-8")
        self.assertIn("static.cloudflareinsights.com/beacon.min.js", home)
        self.assertIn('"token": "abc123"', home)
        go = next((self.dist / "go").glob("*.html")).read_text(encoding="utf-8")
        self.assertIn("beacon.min.js", go)
        self.assertIn("var delay = 500;", go)           # 비콘 보낼 시간을 준다

    def test_goatcounter_fallback(self):
        self._write([{"date": "2026-10-17", "name": "a", "reason": "r", "program": "오늘의집", "url": "https://ozip.me/z?af"}], {"goatcounter_code": "haru"})
        build_hub.build(self.links, self.dist)
        self.assertIn("https://haru.goatcounter.com/count", (self.dist / "index.html").read_text(encoding="utf-8"))

    def test_empty_items(self):
        self._write([])
        build_hub.build(self.links, self.dist)
        self.assertIn("아직 고른 게 없어요", (self.dist / "index.html").read_text(encoding="utf-8"))

    def test_slug_is_stable_and_safe(self):
        s = build_hub.slugify({"date": "2026-10-17", "name": "오아 큐브 멀티탭 PD35 (3구 + USB C 35W)"})
        self.assertTrue(s.startswith("2026-10-17-"))
        self.assertNotIn(" ", s); self.assertNotIn("(", s)


if __name__ == "__main__":
    unittest.main()

    def test_hero_skips_unposted_stock_items(self):
        self._write([
            {"date": "2026-10-20", "name": "비축", "reason": "r", "program": "쿠팡", "url": "https://a.test/1", "category": "자취방", "posted": False},
            {"date": "2026-10-18", "name": "글올림", "reason": "r", "program": "쿠팡", "url": "https://a.test/2", "category": "자취방"},
        ])
        out = build_hub.build(self.links, self.dist).read_text(encoding="utf-8")
        hero = out.split('class="hero"')[1].split("</section>")[0]
        self.assertIn("글올림", hero)
        self.assertNotIn("비축", hero)
        self.assertIn("리뷰 읽어둠", out)  # 그리드에는 비축 항목도 보인다

    def test_sitemap_and_robots(self):
        self._write([{"date": "2026-10-18", "name": "물건", "reason": "r", "program": "쿠팡", "url": "https://a.test/1", "category": "자취방"}])
        build_hub.build(self.links, self.dist)
        sm = (self.dist / "sitemap.xml").read_text(encoding="utf-8")
        self.assertIn("https://harureviews.date/</loc>", sm)
        self.assertIn("/p/", sm)
        self.assertNotIn("/go/", sm)
        rb = (self.dist / "robots.txt").read_text(encoding="utf-8")
        self.assertIn("Disallow: /go/", rb)
        self.assertIn("Sitemap: https://harureviews.date/sitemap.xml", rb)

