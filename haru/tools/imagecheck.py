#!/usr/bin/env python3
"""새 이미지가 최근 게시 이미지와 너무 비슷한지 검사.

  python3 haru/tools/imagecheck.py <파일 또는 URL> [--threshold 24]
종료 코드: 0 괜찮음 / 2 너무 비슷함 / 3 검사 불가(PIL 없음)
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import imagecheck  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--threshold", type=int, default=imagecheck.TOO_SIMILAR)
    ns = ap.parse_args()
    if not imagecheck.available():
        print("[imagecheck] PIL 없음 → 검사 건너뜀")
        return 3
    d, f = imagecheck.nearest(ns.src)
    if d is None:
        print("[imagecheck] 비교할 이전 이미지 없음 → 통과")
        return 0
    verdict = "너무 비슷함 → 다른 장면으로 다시 뽑을 것" if d <= ns.threshold else "괜찮음"
    print(f"[imagecheck] 가장 비슷한 이전 이미지: {f.name} (거리 {d}/64, 임계 {ns.threshold}) → {verdict}")
    return 2 if d <= ns.threshold else 0


if __name__ == "__main__":
    sys.exit(main())
