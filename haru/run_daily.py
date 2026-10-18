#!/usr/bin/env python3
"""하루 일일 실행기.

예:
  python3 haru/run_daily.py --dry-run --now 2026-10-17T09:00:00+09:00
  python3 haru/run_daily.py --channels threads,instagram

큐에서 예정 시각이 지난 pending 아이템을 채널별로 게시하고 metrics.jsonl 에 기록합니다.
status 가 pending 이 아닌 아이템은 절대 다시 게시하지 않습니다.
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline import KST, imagecheck, metrics, queue  # noqa: E402
from pipeline.disclosure import AFFILIATE_LABEL, AI_AFFILIATE_LABEL_SHORT, AI_LABEL_SHORT, compose  # noqa: E402
from pipeline.instagram_client import InstagramClient  # noqa: E402
from pipeline.telegram_client import TelegramClient  # noqa: E402
from pipeline.threads_client import ThreadsClient  # noqa: E402

ALL_CHANNELS = ("threads", "instagram", "telegram")
DEFAULT_TOPIC_TAG = "자취"  # 스레드 주제 태그(글당 1개). 큐 아이템 topic_tag 로 바꿀 수 있고, "" 이면 안 붙인다 (2026-10-18)
DRY_PLACEHOLDER = "dry-run"


def load_env(dry_run: bool) -> dict[str, str]:
    """환경변수를 읽습니다. dry_run 이면 비어 있어도 플레이스홀더로 진행."""
    keys = [
        "THREADS_USER_ID", "THREADS_ACCESS_TOKEN",
        "IG_USER_ID", "IG_ACCESS_TOKEN",
        "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
        "HUB_BASE_URL",
    ]
    env = {k: os.environ.get(k, "") for k in keys}
    if dry_run:
        for k in keys:
            env[k] = env[k] or DRY_PLACEHOLDER
    return env


def build_clients(env: dict[str, str], channels: list[str], dry_run: bool) -> dict[str, Any]:
    clients: dict[str, Any] = {}
    if "threads" in channels and env["THREADS_USER_ID"] and env["THREADS_ACCESS_TOKEN"]:
        clients["threads"] = ThreadsClient(env["THREADS_USER_ID"], env["THREADS_ACCESS_TOKEN"], dry_run)
    if "instagram" in channels and env["IG_USER_ID"] and env["IG_ACCESS_TOKEN"]:
        clients["instagram"] = InstagramClient(env["IG_USER_ID"], env["IG_ACCESS_TOKEN"], dry_run)
    if "telegram" in channels and env["TELEGRAM_BOT_TOKEN"] and env["TELEGRAM_CHAT_ID"]:
        clients["telegram"] = TelegramClient(env["TELEGRAM_BOT_TOKEN"], env["TELEGRAM_CHAT_ID"], dry_run)
    return clients


def _hub_note(hub: str) -> str:
    # 인스타는 캡션 링크가 안 눌린다. 프로필 링크 → 허브 맨 위 항목으로 안내한다.
    return "링크는 프로필에. 오늘 추천 맨 위에 있음"


def post_item(item: dict[str, Any], channel: str, client: Any, hub: str) -> Any:
    """채널별 게시 로직. 결과 id(또는 dict) 반환."""
    aff = item.get("affiliate")
    has_aff = bool(aff and aff.get("url"))
    program = aff.get("program") if has_aff else None
    text = compose(item["text"], has_aff, program)
    image, video = item.get("image_url"), item.get("video_url")

    if channel == "threads":
        topic = item.get("topic_tag", DEFAULT_TOPIC_TAG)
        if has_aff and image:
            # 고지는 본문(첫 줄들)에만 둔다. 링크 댓글은 라벨 한 줄 + 링크만 (2026-10-17 오너 결정: 댓글 중복 고지 제거).
            # 공정위 지침상 고지를 댓글에만 두는 것은 불가하므로 본문 고지는 유지한다.
            link_text = aff.get("label") or "링크"
            return client.post_with_link_comment(text, image, aff["url"], link_text, topic_tag=topic)
        if video:
            return client.post_video(text, video, topic_tag=topic)
        if image:
            return client.post_image(text, image, topic_tag=topic)
        return client.post_text(text, link=aff["url"] if has_aff else None, topic_tag=topic)

    if channel == "instagram":
        caption = text + ("\n\n" + _hub_note(hub) if has_aff else "")
        if video:
            return client.post_reel(caption, video)
        if image:
            return client.post_image(caption, image)
        raise ValueError("Instagram 은 이미지 또는 비디오가 필요합니다")

    if channel == "telegram":
        html = text
        if has_aff:
            html += f'\n\n<a href="{aff["url"]}">{aff.get("label") or "링크"}</a>'
        if image:
            return client.send_photo(image, html)
        return client.send_text(html)

    raise ValueError(f"알 수 없는 채널: {channel}")


SCENE_LOOKBACK = 5  # 최근 이미지 글 몇 건과 장면 키가 겹치면 안 되는지


def _product_token(item_id: str) -> str:
    return (item_id.split("-") + ["", "", "", ""])[3]  # 예: 2026-10-17-multitap-v2-instagram -> multitap


def scene_conflict_reason(item: dict[str, Any], items: list[dict[str, Any]], lookback: int = SCENE_LOOKBACK) -> Optional[str]:
    """같은 장면 키(image_scene)를 최근 이미지 글이 이미 썼으면 사유, 아니면 None. 같은 상품의 글은 제외.

    2026-10-17 커튼·멀티탭 글이 둘 다 floor_table 장면으로 나가 구도가 겹친 사고의 재발 방지. 사진 해시는 구도를 못 가린다.
    """
    scene = item.get("image_scene")
    if not scene:
        return None
    me = _product_token(item["id"])
    recent = [it for it in items
              if it.get("status") == "posted" and not it.get("deleted") and it.get("image_url")
              and _product_token(it["id"]) != me]
    recent.sort(key=lambda it: it.get("updated_at") or "", reverse=True)
    seen: list[str] = []
    for it in recent:
        tok = _product_token(it["id"])
        if tok in seen:
            continue
        seen.append(tok)
        if it.get("image_scene") == scene:
            return f"최근 글 {it['id']} 이 이미 같은 장면({scene})을 썼음. scene_variants 에서 다른 key 로 다시 뽑을 것"
        if len(seen) >= lookback:
            break
    return None


def duplicate_image_reason(item: dict[str, Any]) -> Optional[str]:
    """이미지가 최근 게시 이미지와 너무 비슷하면 사유 문자열, 아니면 None.

    같은 상품의 이전 저장본(파일명에 상품 토큰이 들어간 것)은 비교에서 뺀다 — 재게시 시 자기 자신과 비교되지 않게.
    PIL 이 없으면 검사하지 않는다(None).
    """
    image = item.get("image_url")
    if not image or not imagecheck.available():
        return None
    token = _product_token(item["id"])
    cands = [f for f in imagecheck.recent_images() if not (token and (f"-{token}-" in f.name or f.name.endswith(f"-{token}.jpg")))]
    try:
        d, f = imagecheck.nearest(image, cands)
    except Exception as e:  # noqa: BLE001  (다운로드 실패 등은 게시를 막지 않는다)
        print(f"[WARN] 이미지 중복 검사 실패, 계속 진행: {e}")
        return None
    if d is not None and d <= imagecheck.TOO_SIMILAR:
        return f"최근 게시 이미지 {f.name} 와 너무 비슷함 (거리 {d}/64)"
    return None


def run(now: datetime, channels: list[str], dry_run: bool) -> dict[str, int]:
    env = load_env(dry_run)
    clients = build_clients(env, channels, dry_run)
    missing = [c for c in channels if c not in clients]
    if missing:
        print(f"[WARN] 환경변수 없음 -> 건너뜀: {', '.join(missing)}")

    items = queue.load()
    due = queue.due_items(now, items)
    print(f"[INFO] now={now.isoformat()} 예정 아이템 {len(due)}건 / 전체 {len(items)}건 (dry_run={dry_run})")

    stats = {"posted": 0, "failed": 0, "skipped": 0}
    for item in due:
        if item.get("status") != "pending":  # 이중 안전장치
            stats["skipped"] += 1
            continue
        result: dict[str, Any] = {}
        ok = True
        dup = scene_conflict_reason(item, items) or duplicate_image_reason(item)
        if dup:
            print(f"[FAIL] {item['id']}: 이미지 중복 → 게시 안 함. {dup}")
            metrics.append({"ts": now.isoformat(timespec="seconds"), "event": "post_failed", "channel": "all",
                            "item_id": item["id"], "error": "duplicate_image: " + dup, "dry_run": dry_run})
            if not dry_run:
                queue.mark(item["id"], "failed", {"error": "duplicate_image"})
            stats["failed"] += 1
            continue
        for ch in item.get("channels", []):
            if ch not in clients:
                continue
            try:
                res = post_item(item, ch, clients[ch], env["HUB_BASE_URL"])
                result[ch] = res
                metrics.append({"ts": now.isoformat(timespec="seconds"), "event": "post", "channel": ch,
                                "item_id": item["id"], "kind": item["kind"], "result_id": res,
                                "has_affiliate": bool(item.get("affiliate")), "dry_run": dry_run})
                print(f"[OK] {item['id']} -> {ch}: {res}")
            except Exception as e:  # noqa: BLE001
                ok = False
                metrics.append({"ts": now.isoformat(timespec="seconds"), "event": "post_failed", "channel": ch,
                                "item_id": item["id"], "error": str(e), "dry_run": dry_run})
                print(f"[FAIL] {item['id']} -> {ch}: {e}")
        status = "posted" if ok and result else "failed"
        if dry_run:
            print(f"[DRY-RUN] queue mark {item['id']} -> {status} (저장 안 함)")
        else:
            queue.mark(item["id"], status, result)
        stats["posted" if status == "posted" else "failed"] += 1

    print(f"[SUMMARY] posted={stats['posted']} failed={stats['failed']} skipped={stats['skipped']}")
    return stats


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="하루 일일 게시 실행기")
    ap.add_argument("--dry-run", action="store_true", help="요청을 출력만 하고 전송하지 않음")
    ap.add_argument("--now", help="테스트용 현재 시각 (ISO, 예: 2026-10-17T09:00:00+09:00)")
    ap.add_argument("--channels", default=",".join(ALL_CHANNELS), help="쉼표 구분 채널 목록")
    args = ap.parse_args(argv)

    now = queue.parse_kst(args.now) if args.now else datetime.now(KST)
    channels = [c.strip() for c in args.channels.split(",") if c.strip()]
    bad = [c for c in channels if c not in ALL_CHANNELS]
    if bad:
        ap.error(f"알 수 없는 채널: {bad}")

    print(f"[INFO] 고지(둘째 줄): '{AI_LABEL_SHORT}' / 제휴 '{AI_AFFILIATE_LABEL_SHORT}' + 맨 끝 판매처 문구(기본 '{AFFILIATE_LABEL}')")
    stats = run(now, channels, args.dry_run)
    return 1 if stats["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
