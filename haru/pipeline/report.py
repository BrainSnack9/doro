"""일일 리포트: 어제 게시물, 팔로워 수, 클릭, 수수료. 값이 없으면 '미입력'."""

from datetime import datetime, timedelta
from typing import Any, Optional

from . import KST, metrics

MISSING = "미입력"


def _fmt(value: Any, suffix: str = "") -> str:
    return MISSING if value is None else f"{value}{suffix}"


def daily_report(now: Optional[datetime] = None, print_out: bool = True) -> str:
    now = now or datetime.now(KST)
    yesterday = (now - timedelta(days=1)).date()
    records = metrics.read_all()

    posts = []
    followers: dict[str, Any] = {}
    clicks: Optional[int] = None
    commission: Optional[float] = None
    for rec in records:
        t = metrics._ts(rec)
        if t is None or t.date() != yesterday:
            continue
        ev = rec.get("event")
        if ev == "post":
            posts.append(rec)
        elif ev == "followers":
            followers[rec.get("channel", "?")] = rec.get("count")
        if "clicks" in rec:
            clicks = (clicks or 0) + int(rec["clicks"])
        if "commission_krw" in rec:
            commission = (commission or 0.0) + float(rec["commission_krw"])

    lines = [f"=== 하루 일일 리포트 ({yesterday} KST) ==="]
    lines.append(f"게시물: {len(posts)}건")
    for p in posts:
        lines.append(f"  - [{p.get('channel')}] {p.get('item_id')} -> {p.get('result_id', MISSING)}")
    lines.append("팔로워:")
    for ch in ("threads", "instagram", "telegram"):
        lines.append(f"  - {ch}: {_fmt(followers.get(ch))}")
    lines.append(f"클릭: {_fmt(clicks)}")
    lines.append(f"수수료: {_fmt(commission, '원')}")
    text = "\n".join(lines)
    if print_out:
        print(text)
    return text


if __name__ == "__main__":
    daily_report()
