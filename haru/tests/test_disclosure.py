import unittest

from pipeline.disclosure import (
    AFFILIATE_LABEL,
    AFFILIATE_LABELS_BY_PROGRAM,
    AI_AFFILIATE_LABEL_SHORT,
    AI_LABEL,
    AI_LABEL_SHORT,
    LEGACY_AI_LABELS,
    compose,
    count_links,
    validate_threads_text,
)


class ComposeTests(unittest.TestCase):
    def test_body_then_short_label_at_bottom(self):
        out = compose("혼자 산 지 3년\n둘째 줄", has_affiliate=False)
        self.assertEqual(out.splitlines(), ["혼자 산 지 3년", "둘째 줄", "", AI_LABEL_SHORT])
        self.assertNotIn(AFFILIATE_LABEL, out)

    def test_affiliate_short_label_and_program_phrase_at_end(self):
        out = compose("상품 소개\n본문", has_affiliate=True, program="쿠팡")
        lines = out.splitlines()
        self.assertEqual(lines[:2], ["상품 소개", "본문"])
        self.assertEqual(lines[2], "")
        self.assertEqual(lines[3], AI_AFFILIATE_LABEL_SHORT)
        self.assertEqual(lines[4], AFFILIATE_LABELS_BY_PROGRAM["쿠팡"])
        self.assertNotIn(AFFILIATE_LABEL, out)

    def test_unknown_program_falls_back_to_common_label(self):
        out = compose("본문", has_affiliate=True, program="오늘의집")
        self.assertEqual(out.splitlines()[-1], AFFILIATE_LABEL)

    def test_affiliate_label_is_definite(self):
        self.assertNotIn("받을 수 있습니다", AFFILIATE_LABEL)
        self.assertIn("제공받습니다", AFFILIATE_LABEL)

    def test_short_labels_mention_ai_and_commission(self):
        self.assertIn("AI", AI_LABEL_SHORT)
        self.assertIn("AI", AI_AFFILIATE_LABEL_SHORT)
        self.assertIn("수수료", AI_AFFILIATE_LABEL_SHORT)

    def test_idempotent(self):
        once = compose("훅\n본문\n가격", True, program="네이버")
        twice = compose(once, True, program="네이버")
        self.assertEqual(once, twice)
        self.assertEqual(once.count(AI_AFFILIATE_LABEL_SHORT), 1)
        self.assertEqual(once.count(AFFILIATE_LABELS_BY_PROGRAM["네이버"]), 1)

    def test_legacy_and_full_labels_are_replaced(self):
        out = compose(AI_LABEL + "\n\n본문\n\n" + LEGACY_AI_LABELS[0], has_affiliate=False)
        self.assertNotIn(LEGACY_AI_LABELS[0], out)
        self.assertNotIn(AI_LABEL, out)
        self.assertEqual(out.splitlines(), ["본문", "", AI_LABEL_SHORT])

    def test_single_line_body(self):
        self.assertEqual(compose("한 줄", False).splitlines(), ["한 줄", "", AI_LABEL_SHORT])


class CountLinksTests(unittest.TestCase):
    def test_counts_http_and_https(self):
        self.assertEqual(count_links("a http://x.com b https://y.kr/p?q=1 c"), 2)
        self.assertEqual(count_links("링크 없음"), 0)


class ValidateTests(unittest.TestCase):
    def test_ok(self):
        validate_threads_text(compose("짧은 글", False))

    def test_missing_label(self):
        with self.assertRaises(ValueError):
            validate_threads_text("고지 없는 글")

    def test_label_only_at_top_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_threads_text(AI_LABEL_SHORT + "\n훅\n본문\n셋째 줄\n넷째 줄")

    def test_full_label_at_bottom_still_accepted(self):
        validate_threads_text("훅\n본문\n\n" + AI_LABEL)

    def test_too_long(self):
        with self.assertRaises(ValueError):
            validate_threads_text(compose("가" * 500, False))

    def test_too_many_links(self):
        links = " ".join(f"https://e.com/{i}" for i in range(6))
        with self.assertRaises(ValueError):
            validate_threads_text(compose(links, False))

    def test_extra_links_counted(self):
        links = " ".join(f"https://e.com/{i}" for i in range(5))
        text = compose(links, False)
        validate_threads_text(text)  # 5 is fine
        with self.assertRaises(ValueError):
            validate_threads_text(text, extra_links=1)

    def test_reply_text_without_ai_label_passes_when_not_required(self):
        validate_threads_text("리뷰 읽은 그 트롤리 (쿠팡)", extra_links=1, require_ai_label=False)
        with self.assertRaises(ValueError):
            validate_threads_text("리뷰 읽은 그 트롤리 (쿠팡)", extra_links=1)


class ExperienceClaimTests(unittest.TestCase):
    def test_affiliate_post_rejects_experience_claims(self):
        bad = compose("요즘 아침마다 쓰는 토너 패드. 써보니 자극이 없어요.", has_affiliate=True)
        with self.assertRaises(ValueError):
            validate_threads_text(bad)

    def test_coupang_post_is_checked_too(self):
        with self.assertRaises(ValueError):
            validate_threads_text(compose("써보니 좋았어요", has_affiliate=True, program="쿠팡"))

    def test_affiliate_post_accepts_review_based_text(self):
        validate_threads_text(compose("리뷰 1,842개 읽음. 불만 1위는 패드가 얇다는 것(31회).", has_affiliate=True))

    def test_non_affiliate_post_is_not_checked(self):
        validate_threads_text(compose("커피 내리다 말고 창가에 서 있었어.", has_affiliate=False))


if __name__ == "__main__":
    unittest.main()
