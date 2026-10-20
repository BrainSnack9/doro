import unittest

from tools import coupang_reviews as cr

HEAD = "판매자: 쿠팡(주) HanilMedical 탄소열선 고급 전기요 HL-D205(25)"
A1 = f"윤*기 2026.10.19 {HEAD} (100 x 180 cm) 강아지 오줌 공격에 결국 사망한 전기장판… 똑같은 제품으로 재구매했어요ㅋㅋ 3명에게 도움 됨 도움돼요 신고하기"
A2 = f"윤*호 2026.10.05 {HEAD} (135 x 180 cm) 0:15 아이 둘(5세, 2세)을 데리고 야외 캠핑을 자주 다녀서 밤추위 대비용으로 구매했어요."
A3 = f"엄마미소 2026.09.13 {HEAD} (100 x 180 cm) 세밀한 온도 설정이 마음에 드네요. 한일 의료기 전기 장판을 10년 정도 썼는데요."
JUNK = "장바구니0최근본상품5 HanilMedical 탄소열선 고급 전기요 HL-D205(25) 9,800원 필립스 무선 전기 주전자 6,080원"


class CoupangReviewParseTests(unittest.TestCase):
    def test_mask_name(self):
        self.assertEqual(cr.mask_name("윤*기"), "윤*기")      # 쿠팡이 가린 건 그대로
        self.assertEqual(cr.mask_name("엄마미소"), "엄***")   # 첫 글자 + 별 최대 3개
        self.assertEqual(cr.mask_name("희야"), "희*")
        self.assertEqual(cr.mask_name(""), "구매자")

    def test_junk_without_date_is_dropped(self):
        self.assertIsNone(cr.split_header(JUNK))
        self.assertIsNone(cr.parse_article(JUNK, 3))

    def test_common_prefix_is_the_header(self):
        rests = [cr.split_header(a)[2] for a in (A1, A2, A3)]
        n = cr.common_prefix_tokens(rests)
        self.assertEqual(" ".join(rests[0].split(" ")[:n]), HEAD)

    def test_body_skips_options_and_video_length(self):
        rows = cr.parse_articles([{"text": A1, "stars": "100%"}, {"text": A2, "stars": "80%"}, {"text": A3, "stars": ""}, {"text": JUNK, "stars": ""}])
        self.assertEqual([r["name"] for r in rows], ["윤*기", "윤*호", "엄***"])
        self.assertTrue(rows[0]["text"].startswith("강아지 오줌 공격에"))
        self.assertTrue(rows[0]["text"].endswith("재구매했어요ㅋㅋ"))   # "N명에게 도움 됨…" 꼬리 제거
        self.assertTrue(rows[1]["text"].startswith("아이 둘(5세, 2세)을"))  # 괄호 옵션과 0:15 를 건너뜀
        self.assertTrue(rows[2]["text"].startswith("세밀한 온도 설정이"))
        self.assertEqual(rows[0]["date"], "2026.10.19")
        self.assertEqual(rows[0]["stars"], 5.0)
        self.assertEqual(rows[1]["stars"], 4.0)
        self.assertIsNone(rows[2]["stars"])
        self.assertTrue(rows[1]["header"].endswith("(135 x 180 cm) 0:15"))

    def test_single_review_uses_product_name(self):
        rows = cr.parse_articles([{"text": A2, "stars": ""}], product_name="HanilMedical 탄소열선 고급 전기요 HL-D205(25)")
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["text"].startswith("아이 둘(5세, 2세)을"))

    def test_single_review_without_name_only_strips_seller(self):
        rows = cr.parse_articles([{"text": "희야 2026.10.18 판매자: 쿠팡(주) 북극곰 패브릭 패턴이 아기자기해 예쁘고 좋아요", "stars": ""}])
        self.assertTrue(rows[0]["text"].startswith("북극곰 패브릭"))

    def test_duplicates_collapsed_and_limited(self):
        rows = cr.parse_articles([{"text": A1, "stars": ""}, {"text": A1, "stars": ""}, {"text": A2, "stars": ""}], n=1)
        self.assertEqual(len(rows), 1)


if __name__ == "__main__":
    unittest.main()
