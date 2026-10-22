"""콘텐츠 큐 (haru/data/queue.json) — 공용 코어 iris.queue 에 하루 경로를 묶은 것.

아이템 필드:
  id, kind (product|daily|journal|aside — 뒷얘기·잡담처럼 링크 없는 짧은 글), channels [..], text, image_url, video_url,
  affiliate {program, url, label} | null, scheduled_at (ISO, KST),
  status (pending|posted|failed), result {channel: ids}

동시 편집 규칙 (2026-10-20 추가, 지금은 코어 iris.queue 에 있음):
  파일을 쓰는 구간은 모두 ``with_queue_lock()`` 안에서, run_daily 는 ``save_changes()`` 로 자기가 바꾼 아이템만 병합한다.
  편집 스크립트는 ``with queue.with_queue_lock(): items = queue.load(); ...; queue.save(items)`` 처럼 잠금 안에서 다시 읽고 저장한다.
"""

from pathlib import Path
from typing import Any, Iterator, Optional

from iris import queue as _q
from iris.queue import MERGE_FIELDS, STATUSES, apply_status, changed_fields, parse_kst  # noqa: F401

QUEUE_PATH = Path(__file__).resolve().parent.parent / "data" / "queue.json"


def lock_path(path: Path = QUEUE_PATH) -> Path:
    return _q.lock_path(path)


def with_queue_lock(path: Path = QUEUE_PATH) -> Iterator[None]:
    return _q.with_queue_lock(path)


def load(path: Path = QUEUE_PATH) -> list[dict[str, Any]]:
    return _q.load(path)


def save(items: list[dict[str, Any]], path: Path = QUEUE_PATH) -> None:
    _q.save(items, path, indent=1)


def save_changes(before: list[dict[str, Any]], after: list[dict[str, Any]], path: Path = QUEUE_PATH,
                 fields: tuple[str, ...] = MERGE_FIELDS) -> list[str]:
    return _q.save_changes(before, after, path, fields=fields, indent=1)


def due_items(now, items: Optional[list[dict[str, Any]]] = None) -> list[dict[str, Any]]:
    return _q.due_items(now, load() if items is None else items)


def mark(item_id: str, status: str, result: Optional[dict[str, Any]] = None, path: Path = QUEUE_PATH) -> None:
    _q.mark(item_id, status, result, path=path, indent=1)
