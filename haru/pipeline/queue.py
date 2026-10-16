"""콘텐츠 큐 (haru/data/queue.json).

아이템 필드:
  id, kind (product|daily|journal), channels [..], text, image_url, video_url,
  affiliate {program, url, label} | null, scheduled_at (ISO, KST),
  status (pending|posted|failed), result {channel: ids}
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from . import KST

QUEUE_PATH = Path(__file__).resolve().parent.parent / "data" / "queue.json"

STATUSES = ("pending", "posted", "failed")


def load(path: Path = QUEUE_PATH) -> list[dict[str, Any]]:
    """큐 파일을 읽습니다. 없으면 빈 리스트."""
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    return list(data.get("items", []))


def save(items: list[dict[str, Any]], path: Path = QUEUE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump({"items": items}, f, ensure_ascii=False, indent=2)
        f.write("\n")
    tmp.replace(path)


def parse_kst(value: str) -> datetime:
    """ISO 문자열을 KST aware datetime 으로. tz 가 없으면 KST 로 간주."""
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=KST)
    return dt.astimezone(KST)


def due_items(now: datetime, items: Optional[list[dict[str, Any]]] = None) -> list[dict[str, Any]]:
    """status == pending 이고 scheduled_at <= now 인 아이템 (예정 시각 순)."""
    if items is None:
        items = load()
    if now.tzinfo is None:
        now = now.replace(tzinfo=KST)
    due = [it for it in items if it.get("status") == "pending" and parse_kst(it["scheduled_at"]) <= now]
    return sorted(due, key=lambda it: parse_kst(it["scheduled_at"]))


def mark(item_id: str, status: str, result: Optional[dict[str, Any]] = None, path: Path = QUEUE_PATH) -> None:
    """아이템 상태와 결과 id 를 기록하고 저장합니다."""
    if status not in STATUSES:
        raise ValueError(f"알 수 없는 status: {status}")
    items = load(path)
    for it in items:
        if it.get("id") == item_id:
            it["status"] = status
            existing = it.get("result") or {}
            existing.update(result or {})
            it["result"] = existing
            it["updated_at"] = datetime.now(KST).isoformat(timespec="seconds")
            break
    else:
        raise KeyError(f"큐에 없는 id: {item_id}")
    save(items, path)
