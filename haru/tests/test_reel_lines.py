import json
import math
import shutil
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from tools import reel_lines

REF = Path(__file__).resolve().parents[1] / "assets" / "reels" / "2026-10-20-blanket"


def _write_wav(path: Path, lead: float, voice: float, tail: float, sr: int = 44100):
    """앞 무음 lead초 + 440Hz 소리 voice초 + 뒤 무음 tail초 짜리 가짜 문장 음성."""
    frames = bytearray()
    for n in range(int((lead + voice + tail) * sr)):
        t = n / sr
        v = 0.6 * math.sin(2 * math.pi * 440 * t) if lead <= t < lead + voice else 0.0
        frames += struct.pack("<h", int(v * 32767))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(bytes(frames))


class GapAndTimelineTests(unittest.TestCase):
    def test_default_gap_by_punctuation(self):
        self.assertEqual(reel_lines.default_gap("상관없는데,"), 0.3)
        self.assertEqual(reel_lines.default_gap("추운 10월."), 0.55)
        self.assertEqual(reel_lines.default_gap("눈 빠지는 줄"), 0.55)

    def test_gaps_priority_script_tab_then_cli(self):
        texts = ["하나.", "둘,", "셋."]
        self.assertEqual(reel_lines.gaps_for(texts), [0.55, 0.3])
        self.assertEqual(reel_lines.gaps_for(texts, {2: 0.6}), [0.55, 0.6])
        self.assertEqual(reel_lines.gaps_for(texts, {2: 0.6}, "0.1,0.2"), [0.1, 0.2])
        with self.assertRaises(ValueError):
            reel_lines.gaps_for(texts, None, "0.1")

    def test_read_script_skips_comments_and_reads_tab_gap(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.txt"
            p.write_text("# 주석\n첫 문장.\t0.45\n\n둘째 문장,\n셋째 문장.\n", encoding="utf-8")
            texts, overrides = reel_lines.read_script(p)
        self.assertEqual(texts, ["첫 문장.", "둘째 문장,", "셋째 문장."])
        self.assertEqual(overrides, {1: 0.45})

    def test_timeline_accumulates_with_gaps(self):
        tl = reel_lines.build_timeline([1.0, 2.0, 0.5], ["a.", "b,", "c."], [0.55, 0.3])
        self.assertEqual([(l["start"], l["end"]) for l in tl["lines"]], [(0.0, 1.0), (1.55, 3.55), (3.85, 4.35)])
        self.assertEqual(tl["total"], 4.35)
        self.assertEqual(tl["speed"], 1.22)

    def test_timeline_rounds_only_when_recording(self):
        # 누적은 원래 정밀도로: 0.0004 가 세 번 쌓여도 기록값이 어긋나지 않는다
        tl = reel_lines.build_timeline([1.0004, 1.0004, 1.0004], ["a.", "b.", "c."], [0.0, 0.0])
        self.assertEqual([l["start"] for l in tl["lines"]], [0.0, 1.0, 2.001])

    def test_timeline_rejects_mismatch(self):
        with self.assertRaises(ValueError):
            reel_lines.build_timeline([1.0], ["a.", "b."], [0.5])
        with self.assertRaises(ValueError):
            reel_lines.build_timeline([1.0, 1.0], ["a.", "b."], [])

    def test_reproduces_blanket_timeline_from_recorded_durations(self):
        """2026-10-20 릴스 1편: 기록된 문장 길이 + 대본 탭 쉼 → 같은 timeline.json."""
        ref = json.loads((REF / "lines" / "timeline.json").read_text(encoding="utf-8"))
        texts, overrides = reel_lines.read_script(REF / "script.txt")
        gaps = reel_lines.gaps_for(texts, overrides)
        tl = reel_lines.build_timeline([l["dur"] for l in ref["lines"]], texts, gaps)
        for a, b in zip(tl["lines"], ref["lines"]):
            self.assertEqual(a["text"], b["text"])
            self.assertAlmostEqual(a["start"], b["start"], delta=0.0015)
            self.assertAlmostEqual(a["end"], b["end"], delta=0.0015)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg 없음")
class FfmpegRunTests(unittest.TestCase):
    def test_run_trims_speeds_and_joins(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); lines = root / "lines"; lines.mkdir()
            _write_wav(lines / "01.wav", 0.4, 1.22, 0.5)   # 소리 1.22초 → 1.22배속이면 1.0초
            _write_wav(lines / "02.wav", 0.3, 2.44, 0.2)   # → 2.0초
            _write_wav(lines / "03.wav", 0.1, 0.61, 0.6)   # → 0.5초
            script = root / "script.txt"
            script.write_text("첫 문장.\n둘째 문장,\n셋째 문장.\n", encoding="utf-8")
            tl = reel_lines.run(script, lines, root / "voice.wav")
            durs = [l["dur"] for l in tl["lines"]]
            for got, want in zip(durs, [1.0, 2.0, 0.5]):
                self.assertAlmostEqual(got, want, delta=0.08)   # 무음 제거 + 배속
            self.assertAlmostEqual(tl["lines"][1]["start"], durs[0] + 0.55, delta=0.002)
            self.assertAlmostEqual(tl["lines"][2]["start"], tl["lines"][1]["end"] + 0.3, delta=0.002)
            saved = json.loads((lines / "timeline.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["total"], tl["total"])
            self.assertTrue((root / "voice.wav").exists())
            self.assertAlmostEqual(reel_lines._probe_dur(root / "voice.wav"), tl["total"], delta=0.05)


if __name__ == "__main__":
    unittest.main()
