"""콘텐츠 큐 (haru/data/queue.json).

아이템 필드:
  id, kind (product|daily|journal|aside — 뒷얘기·잡담처럼 링크 없는 짧은 글), channels [..], text, image_url, video_url,
  affiliate {program, url, label} | null, scheduled_at (ISO, KST),
  status (pending|posted|failed), result {channel: ids}

동시 편집 규칙 (2026-10-20 추가):
  5분마다 도는 run_daily 루프와 사람이·에이전트가 돌리는 편집 스크립트가 같은 파일을 만진다.
  2026-10-20 에 루프가 읽은 지 몇 초 지난 메모리 사본을 통째로 다시 써서 편집이 두 번 사라졌다.
  그래서 (1) 파일을 쓰는 구간은 모두 ``with_queue_lock()`` (fcntl.flock) 안에서,
  (2) run_daily 는 통째로 저장하지 않고 ``save_changes()`` 로 자기가 바꾼 아이템(status·result·updated_at·note)만
  최신 파일에 아이템 단위로 병합한다.
  다른 편집 스크립트도 ``with queue.with_queue_lock(): items = queue.load(); ...; queue.save(items)`` 처럼
  잠금 안에서 *다시 읽고* 저장해야 한다.
"""

import contextlib
import fcntl
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, Optional

from . import KST

QUEUE_PATH = Path(__file__).resolve().parent.parent / "data" / "queue.json"

STATUSES = ("pending", "posted", "failed")

# run_daily 가 바꾸는 필드. save_changes() 는 이 필드들의 변경만 파일에 반영한다.
MERGE_FIELDS = ("status", "result", "updated_at", "note")

_lock_state = threading.local()


def lock_path(path: Path = QUEUE_PATH) -> Path:
    """잠금 파일 경로. save() 가 queue.json 을 tmp→replace 로 갈아끼우므로 큐 파일 자체가 아니라 옆의 .lock 파일을 잠근다."""
    return path.with_name(path.name + ".lock")


@contextlib.contextmanager
def with_queue_lock(path: Path = QUEUE_PATH) -> Iterator[None]:
    """큐 파일 편집 구간을 프로세스 간 배타 잠금(fcntl.flock)으로 감싼다. 같은 스레드 안에서는 중첩 가능.

    사용 예 (편집 스크립트):
        with queue.with_queue_lock():
            items = queue.load()      # 잠금 안에서 다시 읽는다
            ... 편집 ...
            queue.save(items)
    """
    held: dict[Path, int] = getattr(_lock_state, "held", None) or {}
    _lock_state.held = held
    key = lock_path(path).resolve()
    if held.get(key):
        held[key] += 1
        try:
            yield
        finally:
            held[key] -= 1
        return
    lp = lock_path(path)
    lp.parent.mkdir(parents=True, exist_ok=True)
    with lp.open("a+") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        held[key] = 1
        try:
            yield
        finally:
            held[key] = 0
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def load(path: Path = QUEUE_PATH) -> list[dict[str, Any]]:
    """큐 파일을 읽습니다. 없으면 빈 리스트."""
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    return list(data.get("items", []))


def save(items: list[dict[str, Any]], path: Path = QUEUE_PATH) -> None:
    """큐 전체를 저장한다 (indent=1, ensure_ascii=False, tmp 파일 뒤 원자적 교체). 잠금 안에서 쓴다.

    주의: 인자로 받은 ``items`` 를 그대로 쓰므로, 읽은 지 오래된 사본을 넘기면 그 사이 다른 프로세스의 편집이 사라진다.
    상태만 바꾸는 쪽(run_daily)은 ``save_changes()`` 를 쓴다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with with_queue_lock(path):
        tmp = path.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump({"items": items}, f, ensure_ascii=False, indent=1)
            f.write("\n")
        tmp.replace(path)


def apply_status(item: dict[str, Any], status: str, result: Optional[dict[str, Any]] = None,
                 now: Optional[datetime] = None) -> dict[str, Any]:
    """메모리 아이템에 status·result·updated_at 을 적용한다 (저장은 하지 않음). result 는 기존 값에 덮어쓴다(병합)."""
    if status not in STATUSES:
        raise ValueError(f"알 수 없는 status: {status}")
    item["status"] = status
    existing = dict(item.get("result") or {})
    existing.update(result or {})
    item["result"] = existing
    item["updated_at"] = (now or datetime.now(KST)).isoformat(timespec="seconds")
    return item


def changed_fields(before: list[dict[str, Any]], after: list[dict[str, Any]],
                   fields: tuple[str, ...] = MERGE_FIELDS) -> dict[str, dict[str, Any]]:
    """실행 시작 때 읽은 사본(before)과 지금 메모리(after)를 id 로 비교해, ``fields`` 중 달라진 값만 {id: {field: value}} 로 돌려준다.
    before 에 없던 아이템은 무시한다 (run_daily 는 아이템을 만들지 않는다)."""
    prev = {it.get("id"): it for it in before}
    out: dict[str, dict[str, Any]] = {}
    for it in after:
        old = prev.get(it.get("id"))
        if old is None:
            continue
        diff = {f: it[f] for f in fields if f in it and it[f] != old.get(f)}
        if diff:
            out[it["id"]] = diff
    return out


def save_changes(before: list[dict[str, Any]], after: list[dict[str, Any]], path: Path = QUEUE_PATH,
                 fields: tuple[str, ...] = MERGE_FIELDS) -> list[str]:
    """이번 실행이 바꾼 아이템만 최신 파일에 병합해 저장한다. 적용된 id 목록을 돌려준다.

    잠금 안에서 파일을 *다시 읽어*, 바뀐 아이템의 ``fields`` 만 덮어쓰고 나머지 아이템·필드는 파일의 최신 내용을 그대로 둔다.
    그 사이 파일에서 사라진 아이템은 되살리지 않고, 새로 추가된 아이템은 그대로 남는다. 바뀐 게 없으면 파일을 건드리지 않는다."""
    changes = changed_fields(before, after, fields)
    if not changes:
        return []
    with with_queue_lock(path):
        current = load(path)
        applied: list[str] = []
        for it in current:
            diff = changes.get(it.get("id"))
            if diff:
                it.update(diff)
                applied.append(it["id"])
        if applied:
            save(current, path)
    return applied


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
    """아이템 하나의 상태와 결과 id 를 기록하고 저장합니다. 잠금 안에서 파일을 다시 읽어 그 아이템만 고친다."""
    if status not in STATUSES:
        raise ValueError(f"알 수 없는 status: {status}")
    with with_queue_lock(path):
        items = load(path)
        for it in items:
            if it.get("id") == item_id:
                apply_status(it, status, result)
                break
        else:
            raise KeyError(f"큐에 없는 id: {item_id}")
        save(items, path)
