"""답글 후보 광고 필터 (2026-10-19 후보 17건 중 15건이 업체 홍보·상품 광고였던 사고 뒤 추가)."""
import unittest
from datetime import datetime, timedelta
from unittest import mock

from engage import search
from pipeline import KST

NOW = datetime(2026, 10, 19, 9, 0, tzinfo=KST)


def _post(code, text, user="@minsu_home", hours=2.0, counts=None):
    return {"code": code, "user": user, "href": f"https://www.threads.com/{user}/post/{code}", "query": "자취 추천", "mode": "recent",
            "time": f"{int(hours)}시간" if hours >= 1 else f"{int(hours * 60)}분", "datetime": None, "text": text, "counts": counts or ["3", "1"]}


def _filter(cands):
    with mock.patch.object(search, "load_replied", lambda: {}):
        return search.filter_candidates(cands, NOW)


class AdFilterTests(unittest.TestCase):
    REAL_QUESTIONS = [
        _post("q1", "제습기 쓰는 사람 있어? 창문이 하나뿐이라 환기가 잘 안 되는데 여름 지나도 꿉꿉함"),
        _post("q2", "살림 꿀템 추천해 줄 사람 가사 노동 확 줄여주는 거 자취 3년차인데 아직도 설거지가 제일 싫음", user="@dasom_day"),
    ]

    def _ad_reasons(self, cands):
        keep, why = _filter(self.REAL_QUESTIONS + cands)
        self.assertEqual({k["code"] for k in keep}, {"q1", "q2"}, f"질문 글만 남아야 함: {[k['code'] for k in keep]}")
        return why

    def test_real_questions_survive(self):
        keep, why = _filter(self.REAL_QUESTIONS)
        self.assertEqual([k["code"] for k in keep], ["q1", "q2"])
        self.assertEqual(why["ad"], 0)

    def test_price_is_ad(self):
        why = self._ad_reasons([_post("a1", "자취방 필수 멀티탭 오늘만 29,900원 → 19,900원 할인 중이에요 원룸 정리 끝", user="@jinho_life")])
        self.assertEqual(why["ad"], 1)

    def test_contact_words_are_ad(self):
        why = self._ad_reasons([_post("a2", "원룸 입주 청소 문의는 DM 주세요 출장 가능 자취방 곰팡이 전문 시공", user="@yeonsu_j")])
        self.assertEqual(why["ad"], 1)

    def test_profile_link_is_ad(self):
        why = self._ad_reasons([_post("a3", "자취 청소 꿀팁 모음 정리했어요 프로필 링크 타고 오면 핫딜도 있음", user="@hana_room")])
        self.assertEqual(why["ad"], 1)

    def test_business_handle_is_ad(self):
        why = self._ad_reasons([_post("a4", "자취방 이사 청소 어떻게 해야 할지 고민이면 저희가 도와드려요 추천", user="@sparkle_clean")])
        self.assertEqual(why["ad"], 1)
        self.assertIn("업체형 핸들", search.ad_reason({"user": "@mall_official"}, "원룸 수납 추천", {}))
        self.assertIn("업체형 핸들", search.ad_reason({"user": "@cleaning_doyeon"}, "원룸 수납 추천", {}))  # 앞에 붙은 업체 단어
        self.assertIn("업체형 핸들", search.ad_reason({"user": "@quickrecipe.kr"}, "원룸 수납 추천", {}))
        self.assertIsNone(search.ad_reason({"user": "@minsu_home"}, "원룸 수납 추천", {}))

    def test_price_without_digit_unit_is_ad(self):
        self.assertIn("광고 단어", search.ad_reason({"user": "@a"}, "세탁조 클리너 한 통 3천원대, 60롤 만원대에 삽니다 자취 살림", {}))

    def test_carousel_mark_is_ad(self):
        why = self._ad_reasons([_post("a5", "자취생이 꼭 사야 하는 살림 추천 5가지 수납부터 청소까지 정리 1 /", user="@tips_daily")])
        self.assertEqual(why["ad"], 1)

    def test_promo_emoji_start_is_ad(self):
        why = self._ad_reasons([_post("a6", "🛒 자취 필수템 추천 모음 원룸 수납 정리 한 번에 끝내는 꿀템들 지금 확인", user="@sunny_pick")])
        self.assertEqual(why["ad"], 1)

    def test_same_user_three_times_in_48h_is_ad(self):
        posts = [_post(f"b{i}", f"원룸 이사 청소 추천 받아요 {i}번째 이야기 수납 정리까지 같이 고민해요", user="@busy_mover", hours=3 + i * 8) for i in range(3)]
        why = self._ad_reasons(posts)
        self.assertEqual(why["ad"], 3)

    def test_same_user_twice_is_not_ad(self):
        posts = [_post(f"c{i}", f"원룸 이사 청소 추천 받아요 {i}번째 이야기 수납 정리까지 같이 고민해요", user="@two_timer", hours=5 + i) for i in range(2)]
        keep, why = _filter(posts)
        self.assertEqual(why["ad"], 0)
        self.assertEqual(len(keep), 2)

    def test_question_with_one_ad_word_is_kept(self):
        keep, why = _filter([_post("k1", "원룸 청소 전문 업체 쓰는 사람 있어? 혼자 하기엔 곰팡이가 너무 심한데")])
        self.assertEqual([k["code"] for k in keep], ["k1"])
        self.assertEqual(why["ad"], 0)

    def test_statement_with_one_ad_word_is_ad(self):
        keep, why = _filter([_post("s1", "원룸 곰팡이 청소 전문 업체입니다 자취방도 깔끔하게 해드립니다", user="@kim_homecare", counts=["30", "4"])])
        self.assertEqual(keep, [])
        self.assertEqual(why["ad"], 1)


if __name__ == "__main__":
    unittest.main()
