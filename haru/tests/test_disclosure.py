import unittest

from pipeline.disclosure import (
    AFFILIATE_LABEL,
    AI_LABEL,
    compose,
    count_links,
    validate_threads_text,
)


class ComposeTests(unittest.TestCase):
    def test_ai_label_first_line(self):
        out = compose("안녕하세요", has_affiliate=False)
        self.assertEqual(out.splitlines()[0], AI_LABEL)
        self.assertNotIn(AFFILIATE_LABEL, out)
        self.assertIn("안녕하세요", out)

    def test_affiliate_label_second_line(self):
        out = compose("상품 소개", has_affiliate=True)
        lines = out.splitlines()
        self.assertEqual(lines[0], AI_LABEL)
        self.assertEqual(lines[1], AFFILIATE_LABEL)

    def test_affiliate_label_is_definite(self):
        self.assertNotIn("받을 수 있습니다", AFFILIATE_LABEL)
        self.assertIn("제공받습니다", AFFILIATE_LABEL)

    def test_no_duplicate_labels(self):
        once = compose("본문", True)
        twice = compose(once, True)
        self.assertEqual(once.count(AI_LABEL), 1)
        self.assertEqual(twice.count(AI_LABEL), 1)
        self.assertEqual(twice.count(AFFILIATE_LABEL), 1)


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


if __name__ == "__main__":
    unittest.main()


class ExperienceClaimTests(unittest.TestCase):
    def test_affiliate_post_rejects_experience_claims(self):
        from pipeline.disclosure import compose, validate_threads_text
        bad = compose("요즘 아침마다 쓰는 토너 패드. 써보니 자극이 없어요.", has_affiliate=True)
        with self.assertRaises(ValueError):
            validate_threads_text(bad)

    def test_affiliate_post_accepts_review_based_text(self):
        from pipeline.disclosure import compose, validate_threads_text
        ok = compose("리뷰 1,842개 읽음. 불만 1위는 패드가 얇다는 것(31회).", has_affiliate=True)
        validate_threads_text(ok)

    def test_non_affiliate_post_is_not_checked(self):
        from pipeline.disclosure import compose, validate_threads_text
        text = compose("커피 내리다 말고 창가에 서 있었어.", has_affiliate=False)
        validate_threads_text(text)

    def test_legacy_short_label_is_replaced_and_moved_to_top(self):
        from pipeline.disclosure import LEGACY_AI_LABELS
        out = compose("본문\n\n" + LEGACY_AI_LABELS[0], has_affiliate=False)
        self.assertNotIn(LEGACY_AI_LABELS[0], out)
        self.assertEqual(out.splitlines(), [AI_LABEL, "", "본문"])
        with self.assertRaises(ValueError):
            validate_threads_text("라벨이 아래에만 있는 글\n\n" + AI_LABEL)
