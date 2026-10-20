"""장면 계획(plan.json) + timeline.json → reels.py 스펙 JSON (2026-10-20 릴스 1편 spec-lines.json 을 손으로 맞추던 계산을 옮김).

시각 표기(문자열, 또는 숫자=초):
  "L5"        5번 문장 시작 - 기본 리드(자막·머리말·카드 0.12초, 장면 경계·until 0.10초)
  "L5+1.0"    5번 문장 시작 + 1.0초 (부호 있는 오프셋은 기본 리드를 대신한다)
  "L5e"       5번 문장 끝 ("L5e-0.2" 도 됨)
  "S4"        4번 장면 시작(1부터)
  "end"       내레이션 끝 + tail
  13.96       초 그대로
plan.json 예 (haru/assets/reels/2026-10-20-blanket/plan.json 이 실제 예):
{
  "slug": "2026-10-20-blanket-3", "series": "하루 리뷰 일지", "audio": "…/voice-hallie-lines.wav",
  "music": "haru/assets/reels/music/mixkit-135.mp3", "music_db": -23, "tail": 1.0, "bottom": "하루 리뷰 일지 #1 · 전기요",
  "timeline": "haru/assets/reels/2026-10-20-blanket/lines/timeline.json",
  "scenes":   [{"kind": "video", "src": "…/clip-bed.mp4"}, {"kind": "video", "src": "…", "start": 5.9}, {"kind": "product", "src": "…", "start": "L5", "zoom": "in"}, …],
  "captions": [{"at": "L1", "lines": ["바닥난방 켜기엔 아깝고", "*안 켜기엔 추운 10월"], "size": 80, "pos": "upper"}, {"at": "S4", "lines": []}, …],
  "pills":    [{"from": "L5", "until": "S5", "text": "① 성능에 비해 싸다"}, …],
  "cards":    [{"group": 1, "at": "L5+1.0", "name": "잡**", "date": "2026.05.04", "text": "…"}, {"group": 1, "at": "L6", "kind": "summary", "name": "하루", "text": "…"}, …]
}
  - 장면: 첫 장면 start 기본 0, 각 장면 end = 다음 장면 start, 마지막 end = "end"(내레이션 끝 + tail). "end" 키로 직접 줄 수도 있다.
  - 카드 group_until: 카드의 "until" > 같은 번호 머리말(pills[group-1]).until > "end".
  - 그 밖의 최상위 키(slug, audio, music, …)는 그대로 스펙으로 복사된다.
사용: python3 haru/tools/reel_spec.py <plan.json> [--timeline <timeline.json>] [--out <spec.json>]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEAD_OVERLAY = 0.12   # 자막·머리말·카드는 문장 시작보다 이만큼 먼저
LEAD_SCENE = 0.10     # 장면 경계·머리말 끝은 문장 시작보다 이만큼 먼저
PLAN_KEYS = {"timeline", "scenes", "captions", "pills", "cards"}
_REF = re.compile(r"^([LS])(\d+)(e)?([+-]\d*\.?\d+)?$")


def _resolve(p: str) -> Path:
    q = Path(p)
    return q if q.is_absolute() else ROOT / q


def _r2(x: float) -> float:
    return round(max(0.0, x), 2)


class Timing:
    def __init__(self, timeline: dict, tail: float = 1.0):
        self.lines = {int(l["i"]): l for l in timeline["lines"]}
        self.total = float(timeline["total"])
        self.tail = float(tail)
        self.scene_starts: list[float] = []

    @property
    def end(self) -> float:
        return self.total + self.tail

    def at(self, ref, lead: float = LEAD_OVERLAY) -> float:
        """시각 표기 → 초(소수 둘째 자리). lead 는 'L' 표기에 오프셋이 없을 때 뺄 값."""
        if isinstance(ref, (int, float)):
            return _r2(float(ref))
        s = str(ref).strip()
        if s == "end":
            return _r2(self.end)
        m = _REF.match(s)
        if not m:
            raise ValueError(f"시각 표기를 모름: {ref!r}")
        kind, n, at_end, off = m.group(1), int(m.group(2)), m.group(3), m.group(4)
        if kind == "S":
            if not 1 <= n <= len(self.scene_starts):
                raise ValueError(f"장면 {n}번이 없음 (장면 {len(self.scene_starts)}개)")
            base = self.scene_starts[n - 1]
            return _r2(base + (float(off) if off else 0.0))
        if n not in self.lines:
            raise ValueError(f"문장 {n}번이 없음 (문장 {len(self.lines)}개)")
        ln = self.lines[n]
        if at_end:
            return _r2(float(ln["end"]) + (float(off) if off else 0.0))
        return _r2(float(ln["start"]) + (float(off) if off else -lead))


def build_spec(plan: dict, timeline: dict) -> dict:
    tm = Timing(timeline, plan.get("tail", 1.0))
    spec = {k: v for k, v in plan.items() if k not in PLAN_KEYS}
    # 장면
    scenes = plan.get("scenes", [])
    if not scenes:
        raise ValueError("scenes 가 비어 있음")
    starts = []
    for k, sc in enumerate(scenes):
        starts.append(tm.at(sc.get("start", 0.0 if k == 0 else None), LEAD_SCENE) if (k == 0 or "start" in sc) else None)
    if any(s is None for s in starts):
        raise ValueError("두 번째 장면부터는 start 가 있어야 함")
    tm.scene_starts = starts
    slides = []
    for k, sc in enumerate(scenes):
        end = tm.at(sc["end"], LEAD_SCENE) if "end" in sc else (starts[k + 1] if k + 1 < len(scenes) else _r2(tm.end))
        slide = {"kind": sc.get("kind", "photo"), "src": sc["src"], "start": starts[k], "end": end}
        for key in ("zoom", "badge"):
            if key in sc:
                slide[key] = sc[key]
        slides.append(slide)
    spec["slides"] = slides
    # 자막
    caps = []
    for c in plan.get("captions", []):
        cap = {"t": tm.at(c["at"]), "lines": c.get("lines", []), "size": c.get("size", 10 if not c.get("lines") else 76), "pos": c.get("pos", "lower")}
        caps.append(cap)
    spec["captions"] = caps
    # 머리말 알약
    pills = []
    for p in plan.get("pills", []):
        pills.append({"t": tm.at(p["from"]), "until": tm.at(p["until"], LEAD_SCENE), "text": p["text"]})
    spec["pills"] = pills
    # 댓글 카드
    cards = []
    for c in plan.get("cards", []):
        g = int(c.get("group", 1))
        if "until" in c:
            until = tm.at(c["until"], LEAD_SCENE)
        elif 1 <= g <= len(pills):
            until = pills[g - 1]["until"]
        else:
            until = _r2(tm.end)
        card = {"group": g, "group_until": until, "t": tm.at(c["at"])}
        for k, v in c.items():
            if k not in ("group", "at", "until"):
                card[k] = v
        cards.append(card)
    spec["cards"] = cards
    return spec


def check(spec: dict) -> list[str]:
    """흔한 실수 점검: 장면 겹침·빈틈, 카드가 group_until 뒤에 나옴, 파일 없음."""
    problems = []
    slides = spec["slides"]
    for a, b in zip(slides, slides[1:]):
        if abs(a["end"] - b["start"]) > 0.011:
            problems.append(f"장면 경계 불일치 {a['end']} → {b['start']}")
    for s in slides:
        if not _resolve(s["src"]).exists():
            problems.append(f"파일 없음 {s['src']}")
    for c in spec.get("cards", []):
        if c["t"] >= c["group_until"]:
            problems.append(f"카드 t={c['t']} 가 group_until={c['group_until']} 뒤에 있음: {c.get('text', '')[:20]}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("--timeline", default=""); ap.add_argument("--out", default="")
    ns = ap.parse_args()
    plan = json.loads(Path(ns.plan).read_text(encoding="utf-8"))
    tl_path = Path(ns.timeline) if ns.timeline else _resolve(plan.get("timeline", ""))
    timeline = json.loads(tl_path.read_text(encoding="utf-8"))
    spec = build_spec(plan, timeline)
    out = Path(ns.out) if ns.out else Path(ns.plan).with_name("spec.json")
    out.write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
    for p in check(spec):
        print(f"[reel_spec] 주의: {p}")
    print(f"[reel_spec] {out} · 장면 {len(spec['slides'])} · 자막 {len(spec['captions'])} · 머리말 {len(spec['pills'])} · 카드 {len(spec['cards'])} · 끝 {spec['slides'][-1]['end']}초")
    return 0


if __name__ == "__main__":
    sys.exit(main())
