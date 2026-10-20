import json
import unittest
from pathlib import Path

from tools import reel_spec

REF = Path(__file__).resolve().parents[1] / "assets" / "reels" / "2026-10-20-blanket"

TIMELINE = {"speed": 1.22, "total": 10.0, "lines": [
    {"i": 1, "start": 0.0, "end": 3.0, "dur": 3.0, "text": "하나."},
    {"i": 2, "start": 3.5, "end": 6.0, "dur": 2.5, "text": "둘."},
    {"i": 3, "start": 6.6, "end": 10.0, "dur": 3.4, "text": "셋."},
]}


def _plan(**over):
    plan = {"slug": "t", "audio": "a.wav", "tail": 1.0,
            "scenes": [{"kind": "video", "src": "c1.mp4"}, {"kind": "product", "src": "p.jpg", "start": "L2", "zoom": "in"}, {"kind": "video", "src": "c1.mp4", "start": "L3"}],
            "captions": [{"at": "L1", "lines": ["훅"], "size": 80, "pos": "upper"}, {"at": "S2", "lines": []}],
            "pills": [{"from": "L2", "until": "S3", "text": "① 하나"}],
            "cards": [{"group": 1, "at": "L2+1.0", "name": "잡**", "date": "2026.05.04", "text": "실제 문장"}, {"group": 1, "at": "L3", "kind": "summary", "name": "하루", "text": "메모"}]}
    plan.update(over)
    return plan


class TimingTests(unittest.TestCase):
    def setUp(self):
        self.tm = reel_spec.Timing(TIMELINE, tail=1.0)
        self.tm.scene_starts = [0.0, 3.4, 6.5]

    def test_line_ref_uses_default_lead(self):
        self.assertEqual(self.tm.at("L2"), 3.38)                       # 3.5 - 0.12
        self.assertEqual(self.tm.at("L2", reel_spec.LEAD_SCENE), 3.4)  # 3.5 - 0.10
        self.assertEqual(self.tm.at("L1"), 0.0)                        # 음수는 0 으로

    def test_explicit_offset_replaces_lead(self):
        self.assertEqual(self.tm.at("L2+1.0"), 4.5)
        self.assertEqual(self.tm.at("L2-0.5"), 3.0)
        self.assertEqual(self.tm.at("L2e"), 6.0)
        self.assertEqual(self.tm.at("L2e-0.2"), 5.8)

    def test_scene_end_and_seconds(self):
        self.assertEqual(self.tm.at("S2"), 3.4)
        self.assertEqual(self.tm.at("S3+0.5"), 7.0)
        self.assertEqual(self.tm.at("end"), 11.0)
        self.assertEqual(self.tm.at(5.556), 5.56)

    def test_unknown_refs_raise(self):
        for bad in ("L9", "S4", "x3", "L"):
            with self.assertRaises(ValueError):
                self.tm.at(bad)


class BuildSpecTests(unittest.TestCase):
    def test_scene_chain_and_last_end(self):
        spec = reel_spec.build_spec(_plan(), TIMELINE)
        self.assertEqual([(s["start"], s["end"]) for s in spec["slides"]], [(0.0, 3.4), (3.4, 6.5), (6.5, 11.0)])
        self.assertEqual(spec["slides"][1]["zoom"], "in")
        self.assertEqual(spec["slug"], "t"); self.assertEqual(spec["audio"], "a.wav")
        self.assertNotIn("scenes", spec); self.assertNotIn("timeline", spec)

    def test_caption_pill_card_times(self):
        spec = reel_spec.build_spec(_plan(), TIMELINE)
        self.assertEqual([c["t"] for c in spec["captions"]], [0.0, 3.4])
        self.assertEqual(spec["captions"][1], {"t": 3.4, "lines": [], "size": 10, "pos": "lower"})
        self.assertEqual(spec["pills"], [{"t": 3.38, "until": 6.5, "text": "① 하나"}])
        self.assertEqual([c["t"] for c in spec["cards"]], [4.5, 6.48])
        self.assertEqual(spec["cards"][0], {"group": 1, "group_until": 6.5, "t": 4.5, "name": "잡**", "date": "2026.05.04", "text": "실제 문장"})
        self.assertEqual(spec["cards"][1]["kind"], "summary")

    def test_card_until_priority(self):
        plan = _plan(cards=[{"group": 1, "at": "L2", "until": "L3", "text": "x"}, {"group": 2, "at": "L3", "text": "y"}, {"group": 1, "at": "L2+0.5", "text": "z"}])
        spec = reel_spec.build_spec(plan, TIMELINE)
        self.assertEqual(spec["cards"][0]["group_until"], 6.5)   # 카드 자체 until (L3 - 0.10)
        self.assertEqual(spec["cards"][1]["group_until"], 11.0)  # 머리말 2번 없음 → end
        self.assertEqual(spec["cards"][2]["group_until"], 6.5)   # 머리말 1번 until

    def test_missing_scene_start_raises(self):
        plan = _plan(scenes=[{"kind": "video", "src": "a"}, {"kind": "video", "src": "b"}])
        with self.assertRaises(ValueError):
            reel_spec.build_spec(plan, TIMELINE)

    def test_check_reports_card_after_group_end(self):
        spec = reel_spec.build_spec(_plan(cards=[{"group": 1, "at": "L3+2", "text": "늦음"}]), TIMELINE)
        problems = reel_spec.check(spec)
        self.assertTrue(any("group_until" in p for p in problems))

    def test_reproduces_blanket_spec_lines(self):
        """2026-10-20 릴스 1편: plan.json + timeline.json → spec-lines.json 과 같은 결과."""
        plan = json.loads((REF / "plan.json").read_text(encoding="utf-8"))
        timeline = json.loads((REF / "lines" / "timeline.json").read_text(encoding="utf-8"))
        want = json.loads((REF / "spec-lines.json").read_text(encoding="utf-8"))
        self.assertEqual(reel_spec.build_spec(plan, timeline), want)


if __name__ == "__main__":
    unittest.main()
