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

from pipeline import KST, metrics, queue  # noqa: E402
from pipeline.disclosure import AFFILIATE_LABEL, AI_LABEL, compose  # noqa: E402
from pipeline.instagram_client import InstagramClient  # noqa: E402
from pipeline.telegram_client import TelegramClient  # noqa: E402
from pipeline.threads_client import ThreadsClient  # noqa: E402

ALL_CHANNELS = ("threads", "instagram", "telegram")
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
    return f"링크는 프로필의 하루 추천 페이지에서: {hub}"


def post_item(item: dict[str, Any], channel: str, client: Any, hub: str) -> Any:
    """채널별 게시 로직. 결과 id(또는 dict) 반환."""
    aff = item.get("affiliate")
    has_aff = bool(aff and aff.get("url"))
    program = aff.get("program") if has_aff else None
    text = compose(item["text"], has_aff, program)
    image, video = item.get("image_url"), item.get("video_url")

    if channel == "threads":
        if has_aff and image:
            link_text = compose(aff.get("label") or "링크", True, program)
            return client.post_with_link_comment(text, image, aff["url"], link_text)
        if video:
            return client.post_video(text, video)
        if image:
            return client.post_image(text, image)
        return client.post_text(text, link=aff["url"] if has_aff else None)

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

    print(f"[INFO] 고지 문구: '{AI_LABEL}' / '{AFFILIATE_LABEL}'")
    stats = run(now, channels, args.dry_run)
    return 1 if stats["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
