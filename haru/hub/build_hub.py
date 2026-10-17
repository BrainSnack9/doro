#!/usr/bin/env python3
"""links.json + template.html -> dist/index.html (GitHub Pages 링크 허브)."""

import html
import json
import sys
from datetime import datetime
from pathlib import Path

HUB_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(HUB_DIR.parent))

from pipeline import KST  # noqa: E402
from pipeline.disclosure import AFFILIATE_LABEL, AFFILIATE_LABELS_BY_PROGRAM, AI_LABEL  # noqa: E402

LINKS_PATH = HUB_DIR / "links.json"
TEMPLATE_PATH = HUB_DIR / "template.html"
DIST_PATH = HUB_DIR / "dist" / "index.html"


def render_card(item: dict) -> str:
    """항목 하나. 필수: date, name, reason, program, url. 선택: fact(리뷰에서 본 숫자), con(단점 하나)."""
    e = html.escape
    parts = [
        '  <article class="pick">\n',
        f'    <p class="name"><span>{e(item["name"])}</span></p>\n',
        f'    <p class="reason">{e(item["reason"])}</p>\n',
    ]
    if item.get("fact"):
        parts.append(f'    <p class="fact">리뷰에서 본 것: {e(item["fact"])}</p>\n')
    if item.get("con"):
        parts.append(f'    <p class="con"><b>단점 하나</b> {e(item["con"])}</p>\n')
    parts.append(
        f'    <a class="go" href="{e(item["url"], quote=True)}" rel="nofollow sponsored noopener" target="_blank">'
        f'{e(item["program"])}에서 보기</a>\n'
    )
    parts.append("  </article>\n")
    return "".join(parts)


WEEKDAYS = "월화수목금토일"


def pretty_date(iso: str) -> str:
    """2026-10-17 -> 10월 17일 (금). 형식이 다르면 원문 그대로."""
    try:
        d = datetime.strptime(iso, "%Y-%m-%d")
    except ValueError:
        return iso
    return f"{d.month}월 {d.day}일 ({WEEKDAYS[d.weekday()]})"


def render_groups(items: list[dict]) -> str:
    if not items:
        return '  <p class="empty">아직 고른 게 없어요. 오늘 밤에 다시 와 주세요.</p>\n'
    by_date: dict[str, list[dict]] = {}
    for it in items:
        by_date.setdefault(it["date"], []).append(it)
    out = []
    for date in sorted(by_date, reverse=True):
        out.append(f"  <h2>{html.escape(pretty_date(date))}</h2>\n")
        out.extend(render_card(it) for it in by_date[date])
    return "".join(out)


def render_program_notes(items: list[dict]) -> str:
    """판매처가 지정한 고지 문구(예: 쿠팡 파트너스)를 목록에 그 판매처 항목이 있을 때만 붙인다."""
    programs = {it.get("program", "") for it in items}
    notes = [html.escape(AFFILIATE_LABELS_BY_PROGRAM[p]) for p in AFFILIATE_LABELS_BY_PROGRAM if p in programs]
    return "".join(f"    <p>{n}</p>\n" for n in notes)


def build(links_path: Path = LINKS_PATH, template_path: Path = TEMPLATE_PATH, dist_path: Path = DIST_PATH) -> Path:
    data = json.loads(links_path.read_text(encoding="utf-8"))
    template = template_path.read_text(encoding="utf-8")
    page = (
        template.replace("{{TITLE}}", html.escape(data.get("title", "하루의 오늘 추천")))
        .replace("{{AI_LABEL}}", html.escape(AI_LABEL))
        .replace("{{AFFILIATE_LABEL}}", html.escape(AFFILIATE_LABEL))
        .replace("{{GROUPS}}", render_groups(data["items"]))
        .replace("{{PROGRAM_NOTES}}", render_program_notes(data["items"]))
        .replace("{{GENERATED_AT}}", datetime.now(KST).strftime("%Y-%m-%d %H:%M"))
    )
    dist_path.parent.mkdir(parents=True, exist_ok=True)
    dist_path.write_text(page, encoding="utf-8")
    return dist_path


if __name__ == "__main__":
    out = build()
    print(f"[hub] wrote {out} ({out.stat().st_size} bytes)")
