"""게시 이미지 중복 검사 (지각 해시, dHash).

같은 레시피로 뽑은 이미지가 구도까지 같아지는 일을 막는다 (2026-10-17 커튼·멀티탭 글이 같은 장면으로 나감).
PIL 이 있으면 8x8 dHash 로 비교하고, 없으면 검사를 건너뛴다(None 반환, 호출자가 경고만 남김).

경험값(2026-10-17, 64비트): 같은 장면 두 장 = 20, 다른 장면 = 30~32. 임계값 26 이하면(여유 2) '너무 비슷함'.
"""

import io
import urllib.request
from pathlib import Path

try:  # PIL 은 선택 의존성
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None

HASH_SIZE = 8
TOO_SIMILAR = 26
POSTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "posts"
EXTS = (".jpg", ".jpeg", ".png", ".webp")


def available() -> bool:
    return Image is not None


def _load(src):
    if isinstance(src, (bytes, bytearray)):
        return Image.open(io.BytesIO(src))
    s = str(src)
    if s.startswith(("http://", "https://")):
        with urllib.request.urlopen(s, timeout=30) as r:  # noqa: S310
            return Image.open(io.BytesIO(r.read()))
    return Image.open(s)


def dhash(src, size: int = HASH_SIZE) -> int:
    """경로·URL·bytes → 정수 해시 (size*size 비트)."""
    im = _load(src).convert("L").resize((size + 1, size), Image.LANCZOS)
    px = list(im.get_flattened_data()) if hasattr(im, "get_flattened_data") else list(im.getdata())
    bits = 0
    for r in range(size):
        for c in range(size):
            bits = (bits << 1) | int(px[r * (size + 1) + c] > px[r * (size + 1) + c + 1])
    return bits


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def recent_images(posts_dir: Path = POSTS_DIR, limit: int = 12) -> list:
    """최근 게시 이미지 파일 (이름 역순 = 날짜 역순)."""
    if not posts_dir.exists():
        return []
    files = sorted((p for p in posts_dir.iterdir() if p.suffix.lower() in EXTS), reverse=True)
    return files[:limit]


def nearest(src, candidates=None):
    """(최소 거리, 가장 비슷한 파일) — 비교 대상이 없으면 (None, None)."""
    cands = list(candidates) if candidates is not None else recent_images()
    if not cands:
        return None, None
    h = dhash(src)
    best = min(((hamming(h, dhash(c)), c) for c in cands), key=lambda t: t[0])
    return best


def too_similar(src, candidates=None, threshold: int = TOO_SIMILAR):
    """True/False, 검사 불가(PIL 없음)면 None."""
    if not available():
        return None
    d, _ = nearest(src, candidates)
    return d is not None and d <= threshold
