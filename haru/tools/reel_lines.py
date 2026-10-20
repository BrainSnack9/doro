"""릴스 내레이션 문장별 음성 → 다듬기·이어 붙이기·타임라인 (2026-10-20 릴스 1편에서 손으로 한 ffmpeg 처리를 옮김).

입력
  - 대본 텍스트 파일: 한 줄 = 한 문장(빈 줄·'#' 주석은 건너뜀). 줄 끝에 탭 + 숫자를 두면 그 문장 뒤 쉼(초)을 직접 정한다.
  - 문장별 음성 폴더: 01.mp3, 02.mp3 … (이름 정렬 순서 = 대본 줄 순서. .mp3/.wav/.m4a)
처리(문장마다)
  1. 앞뒤 무음 제거: silenceremove -40dB, 0.05초 (areverse 로 뒤쪽도)
  2. 배속: atempo (기본 1.22)
  → <음성 폴더>/NN.wav (44.1kHz mono pcm_s16le)
이어 붙이기
  - 문장 사이 쉼: 줄 끝이 쉼표(,)면 0.3초, 그 외(마침표·물음표·느낌표…)는 0.55초. --gaps 로 전부 지정하거나 대본 탭 표기로 줄마다 바꿀 수 있다.
  - 결과 wav(--out, 기본 <음성 폴더>/../voice-lines.wav)와 <음성 폴더>/timeline.json
timeline.json 형식(reel_spec.py 가 읽는다):
  {"speed": 1.22, "total": 50.435, "lines": [{"i": 1, "start": 0.0, "end": 3.347, "dur": 3.347, "text": "…"}, …]}

사용: python3 haru/tools/reel_lines.py <script.txt> <lines_dir> [--out voice.wav] [--speed 1.22] [--gaps 0.45,0.25,…]
      [--period-gap 0.55] [--comma-gap 0.3] [--threshold -40dB] [--min-silence 0.05]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SPEED = 1.22
PERIOD_GAP = 0.55
COMMA_GAP = 0.3
THRESHOLD = "-40dB"
MIN_SILENCE = 0.05
AUDIO_EXTS = (".mp3", ".wav", ".m4a", ".ogg", ".flac")


def read_script(path: Path) -> tuple[list[str], dict[int, float]]:
    """대본 → (문장 목록, {줄 번호(1부터): 그 줄 뒤 쉼}). 탭 뒤 숫자는 쉼 지정."""
    texts: list[str] = []
    overrides: dict[int, float] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "\t" in line:
            text, _, tail = line.rpartition("\t")
            try:
                overrides[len(texts) + 1] = float(tail.strip())
                line = text.strip()
            except ValueError:
                pass
        texts.append(line)
    return texts, overrides


def default_gap(text: str, period_gap: float = PERIOD_GAP, comma_gap: float = COMMA_GAP) -> float:
    """문장 뒤 쉼: 쉼표로 끝나면 짧게, 그 외는 길게."""
    t = text.rstrip().rstrip("'\"”’)")
    return comma_gap if t.endswith(",") else period_gap


def gaps_for(texts: list[str], overrides: dict[int, float] | None = None, gaps_csv: str = "",
             period_gap: float = PERIOD_GAP, comma_gap: float = COMMA_GAP) -> list[float]:
    """문장 i 뒤 쉼(초) 목록. 길이는 len(texts)-1 (마지막 문장 뒤는 없음). 우선순위: --gaps > 대본 탭 표기 > 문장부호 기본값."""
    n = len(texts)
    gaps = [default_gap(t, period_gap, comma_gap) for t in texts[:-1]]
    for i, g in (overrides or {}).items():
        if 1 <= i < n:
            gaps[i - 1] = float(g)
    if gaps_csv:
        given = [float(x) for x in gaps_csv.split(",") if x.strip()]
        if len(given) not in (n - 1, n):
            raise ValueError(f"--gaps 는 {n - 1}개(또는 {n}개)여야 함, {len(given)}개 받음")
        gaps = given[: n - 1]
    return gaps


def build_timeline(durs: list[float], texts: list[str], gaps: list[float], speed: float = SPEED) -> dict:
    """문장 길이(초)·쉼으로 시작/끝 시각을 누적한다(소수 셋째 자리). ffmpeg 없이 계산만."""
    if len(durs) != len(texts):
        raise ValueError(f"문장 {len(texts)}개, 음성 {len(durs)}개 — 수가 다름")
    if len(gaps) != max(0, len(texts) - 1):
        raise ValueError(f"쉼은 {len(texts) - 1}개여야 함, {len(gaps)}개 받음")
    lines = []
    t = 0.0  # 누적은 원래 정밀도로, 기록만 셋째 자리까지(2026-10-20 timeline.json 과 같은 방식)
    for i, (d, text) in enumerate(zip(durs, texts), start=1):
        d = float(d)
        start, end = t, t + d
        lines.append({"i": i, "start": round(start, 3), "end": round(end, 3), "dur": round(d, 3), "text": text})
        t = end + (gaps[i - 1] if i - 1 < len(gaps) else 0.0)
    return {"speed": speed, "total": lines[-1]["end"] if lines else 0.0, "lines": lines}


def _probe_dur(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def trim_filter(speed: float = SPEED, threshold: str = THRESHOLD, min_silence: float = MIN_SILENCE) -> str:
    """앞 무음 제거 → 뒤집어 뒤 무음 제거 → 되돌림 → 배속. 2026-10-20 수동 처리와 같은 값(-40dB, 0.05초, 1.22)."""
    sr = f"silenceremove=start_periods=1:start_threshold={threshold}:start_silence={min_silence}"
    parts = [sr, "areverse", sr, "areverse"]
    if abs(speed - 1.0) > 1e-9:
        parts.append(f"atempo={speed}")
    return ",".join(parts)


def process_line(src: Path, dst: Path, speed: float = SPEED, threshold: str = THRESHOLD, min_silence: float = MIN_SILENCE) -> float:
    """한 문장 음성 다듬기 → dst(wav). 결과 길이(초)를 돌려준다."""
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-af", trim_filter(speed, threshold, min_silence),
                    "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(dst)], check=True)
    return _probe_dur(dst)


def join(wavs: list[Path], gaps: list[float], out: Path) -> None:
    """문장 wav 사이에 쉼(무음)을 넣어 하나로 잇는다(apad + concat)."""
    inputs: list[str] = []
    filters: list[str] = []
    for k, w in enumerate(wavs):
        inputs += ["-i", str(w)]
        pad = gaps[k] if k < len(gaps) else 0.0
        filters.append(f"[{k}:a]apad=pad_dur={pad:.3f}[a{k}]")
    filters.append("".join(f"[a{k}]" for k in range(len(wavs))) + f"concat=n={len(wavs)}:v=0:a=1[out]")
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(filters), "-map", "[out]",
                    "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(out)], check=True)


def source_files(lines_dir: Path) -> list[Path]:
    """음성 폴더의 원본(mp3 등)을 이름순으로. 이미 만든 NN.wav 는 원본 mp3 가 있으면 제외."""
    files = sorted(p for p in lines_dir.iterdir() if p.suffix.lower() in AUDIO_EXTS and not p.name.startswith(".") and not p.name.endswith(".trim.wav"))
    stems_non_wav = {p.stem for p in files if p.suffix.lower() != ".wav"}
    return [p for p in files if not (p.suffix.lower() == ".wav" and p.stem in stems_non_wav)]


def run(script: Path, lines_dir: Path, out: Path | None = None, speed: float = SPEED, gaps_csv: str = "",
        period_gap: float = PERIOD_GAP, comma_gap: float = COMMA_GAP, threshold: str = THRESHOLD, min_silence: float = MIN_SILENCE) -> dict:
    texts, overrides = read_script(script)
    srcs = source_files(lines_dir)
    if len(srcs) != len(texts):
        raise SystemExit(f"대본 {len(texts)}문장인데 음성 파일은 {len(srcs)}개: {[p.name for p in srcs]}")
    gaps = gaps_for(texts, overrides, gaps_csv, period_gap, comma_gap)
    wavs, durs = [], []
    for i, src in enumerate(srcs, start=1):
        dst = lines_dir / f"{i:02d}.wav"
        if src.resolve() == dst.resolve():  # 원본이 이미 NN.wav 면 덮어쓰지 않고 NN.trim.wav 로
            dst = lines_dir / f"{i:02d}.trim.wav"
        durs.append(process_line(src, dst, speed, threshold, min_silence))
        wavs.append(dst)
    timeline = build_timeline(durs, texts, gaps, speed)
    out = out or (lines_dir.parent / "voice-lines.wav")
    join(wavs, gaps, out)
    (lines_dir / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=1), encoding="utf-8")
    timeline["out"] = str(out)
    return timeline


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("script"); ap.add_argument("lines_dir")
    ap.add_argument("--out", default="")
    ap.add_argument("--speed", type=float, default=SPEED)
    ap.add_argument("--gaps", default="", help="문장 뒤 쉼을 전부 지정(쉼표 구분, 문장 수-1개)")
    ap.add_argument("--period-gap", type=float, default=PERIOD_GAP)
    ap.add_argument("--comma-gap", type=float, default=COMMA_GAP)
    ap.add_argument("--threshold", default=THRESHOLD)
    ap.add_argument("--min-silence", type=float, default=MIN_SILENCE)
    ns = ap.parse_args()
    tl = run(Path(ns.script), Path(ns.lines_dir), Path(ns.out) if ns.out else None, ns.speed, ns.gaps,
             ns.period_gap, ns.comma_gap, ns.threshold, ns.min_silence)
    for ln in tl["lines"]:
        print(f"{ln['i']:>2} {ln['start']:7.3f} ~ {ln['end']:7.3f}  {ln['text']}")
    print(f"[reel_lines] 총 {tl['total']:.3f}초 · {tl['out']} · timeline.json 저장")
    return 0


if __name__ == "__main__":
    sys.exit(main())
