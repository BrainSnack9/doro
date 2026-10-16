"""append-only 지표 로그 (haru/data/metrics.jsonl)."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from . import KST

METRICS_PATH = Path(__file__).resolve().parent.parent / "data" / "metrics.jsonl"


def append(event: dict[str, Any], path: Path = METRICS_PATH) -> None:
    """이벤트 한 줄을 추가합니다. ``ts`` 가 없으면 현재 KST 시각을 넣습니다."""
    record = dict(event)
    record.setdefault("ts", datetime.now(KST).isoformat(timespec="seconds"))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_all(path: Path = METRICS_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _ts(rec: dict[str, Any]) -> Optional[datetime]:
    try:
        dt = datetime.fromisoformat(rec["ts"])
    except (KeyError, ValueError):
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=KST)


def summarize(days: int = 7, now: Optional[datetime] = None, path: Path = METRICS_PATH) -> dict[str, Any]:
    """최근 N일 요약: 게시 수(채널별), 실패 수, 클릭/수수료 합계(있을 때만)."""
    now = now or datetime.now(KST)
    since = now - timedelta(days=days)
    posts_by_channel: dict[str, int] = {}
    failed = 0
    clicks = 0
    commissions = 0.0
    has_clicks = has_comm = False
    for rec in read_all(path):
        t = _ts(rec)
        if t is None or t < since:
            continue
        ev = rec.get("event")
        if ev == "post":
            posts_by_channel[rec.get("channel", "?")] = posts_by_channel.get(rec.get("channel", "?"), 0) + 1
        elif ev == "post_failed":
            failed += 1
        if "clicks" in rec:
            clicks += int(rec["clicks"]); has_clicks = True
        if "commission_krw" in rec:
            commissions += float(rec["commission_krw"]); has_comm = True
    return {
        "days": days,
        "posts_by_channel": posts_by_channel,
        "failed": failed,
        "clicks": clicks if has_clicks else None,
        "commission_krw": commissions if has_comm else None,
    }
