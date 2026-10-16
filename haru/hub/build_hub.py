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
from pipeline.disclosure import AFFILIATE_LABEL, AI_LABEL  # noqa: E402

LINKS_PATH = HUB_DIR / "links.json"
TEMPLATE_PATH = HUB_DIR / "template.html"
DIST_PATH = HUB_DIR / "dist" / "index.html"


def render_card(item: dict) -> str:
    e = html.escape
    return (
        '  <article class="card">\n'
        f'    <p class="name">{e(item["name"])}<span class="badge">{e(item["program"])}</span></p>\n'
        f'    <p class="reason">{e(item["reason"])}</p>\n'
        f'    <a class="btn" href="{e(item["url"], quote=True)}" rel="nofollow sponsored" target="_blank">보러가기</a>\n'
        "  </article>\n"
    )


def render_groups(items: list[dict]) -> str:
    by_date: dict[str, list[dict]] = {}
    for it in items:
        by_date.setdefault(it["date"], []).append(it)
    out = []
    for date in sorted(by_date, reverse=True):
        out.append(f"  <h2>{html.escape(date)}</h2>\n")
        out.extend(render_card(it) for it in by_date[date])
    return "".join(out)


def build(links_path: Path = LINKS_PATH, template_path: Path = TEMPLATE_PATH, dist_path: Path = DIST_PATH) -> Path:
    data = json.loads(links_path.read_text(encoding="utf-8"))
    template = template_path.read_text(encoding="utf-8")
    page = (
        template.replace("{{TITLE}}", html.escape(data.get("title", "하루의 오늘 추천")))
        .replace("{{AI_LABEL}}", html.escape(AI_LABEL))
        .replace("{{AFFILIATE_LABEL}}", html.escape(AFFILIATE_LABEL))
        .replace("{{GROUPS}}", render_groups(data["items"]))
        .replace("{{GENERATED_AT}}", datetime.now(KST).strftime("%Y-%m-%d %H:%M"))
    )
    dist_path.parent.mkdir(parents=True, exist_ok=True)
    dist_path.write_text(page, encoding="utf-8")
    return dist_path


if __name__ == "__main__":
    out = build()
    print(f"[hub] wrote {out} ({out.stat().st_size} bytes)")
