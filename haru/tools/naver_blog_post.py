#!/usr/bin/env python3
"""네이버 블로그(SmartEditor ONE)에 마크다운 초안을 Aside 로 게시한다.

  python3 haru/tools/naver_blog_post.py haru/blog/2026-10-17-multitap.md --category 자취방 --tags 자취템,멀티탭 [--dry-run]

초안 형식: 첫 줄 "# 제목", "## 소제목" 은 굵게, "- " 목록은 "· " 로, URL 한 줄은 링크 카드로(에디터가 자동 변환), "---" 아래는 고지.
Aside 에 네이버 로그인이 있어야 한다. 발행 후 글 주소를 출력한다.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ASIDE = os.path.expanduser("~/.local/bin/aside")
BLOG_ID = "skekrla123"

SCRIPT = r'''
const DATA = %(data)s;
const pg = await openTab("about:blank");
try { await pg.goto("https://blog.naver.com/PostWriteForm.naver?blogId=%(blog)s&Redirect=Write&redirect=Write&widgetTypeCall=true&noTrackingCode=true&directAccess=false", { waitUntil: "commit", timeout: 20000 }); } catch (e) {}
await sleep(12000);
const ph = (re) => pg.evaluate((src) => { const re = new RegExp(src); const el = [...document.querySelectorAll("[class*=placeholder]")].find(e => re.test((e.innerText||"").trim())); if (!el) return null; const r = el.getBoundingClientRect(); return { x: r.x + 20, y: r.y + r.height/2 }; }, re.source);
const t = await ph(/^제목$/); if (!t) throw new Error("제목 자리 없음");
await pg.mouse.click(t.x, t.y); await sleep(500); await pg.keyboard.type(DATA.title); await sleep(400);
const b = await ph(/일상을 기록/); if (b) { await pg.mouse.click(b.x, b.y); } else { await pg.keyboard.press("Enter"); }
await sleep(500);
for (const line of DATA.lines) {
  if (line.bold) { await pg.keyboard.press("Meta+b"); await pg.keyboard.type(line.text); await pg.keyboard.press("Meta+b"); }
  else if (line.text) { await pg.keyboard.type(line.text); }
  await pg.keyboard.press("Enter");
  if (/^https?:\/\//.test(line.text)) await sleep(3500);  // 링크 카드 변환 대기
  else await sleep(120);
}
await sleep(1500);
const comps = await pg.evaluate(() => [...document.querySelectorAll(".se-component")].map(c => c.className.split(" ").filter(x => /^se-(text|image|oglink|documentTitle)/.test(x)).join("|")));
console.log("COMPS=" + JSON.stringify(comps));
if (DATA.dry) { await pg.screenshot({ path: "draft.jpg", type: "jpeg", quality: 50 }); console.log("ASIDE_DIR=" + pwd); await pg.evaluate(() => { window.onbeforeunload = null; }); await closeTab(pg); console.log("GSTACK_STEP_OK"); }
else {
  const pub = await pg.evaluate(() => { const b = [...document.querySelectorAll("button")].find(e => e.getBoundingClientRect().width > 0 && /^발행$/.test((e.innerText||"").trim())); const r = b.getBoundingClientRect(); return { x: r.x + r.width/2, y: r.y + r.height/2 }; });
  await pg.mouse.click(pub.x, pub.y); await sleep(2500);
  // 카테고리
  const sel = await pg.evaluate(() => { const b = document.querySelector("[class*=layer_content_set_publish] button[class*=selectbox_button]"); const r = b.getBoundingClientRect(); return { x: r.x + r.width/2, y: r.y + r.height/2, cur: b.innerText.trim() }; });
  if (sel.cur !== DATA.category) {
    await pg.mouse.click(sel.x, sel.y); await sleep(800);
    const opt = await pg.evaluate((name) => { const el = [...document.querySelectorAll("[class*=layer_content_set_publish] li, [class*=layer_content_set_publish] button, [class*=layer_content_set_publish] label, [class*=layer_content_set_publish] span")].find(e => e.getBoundingClientRect().width > 0 && (e.innerText||"").trim() === name && !/selectbox_button/.test(e.className)); if (!el) return null; const r = el.getBoundingClientRect(); return { x: r.x + r.width/2, y: r.y + r.height/2 }; }, DATA.category);
    console.log("CAT_OPT=" + JSON.stringify(opt));
    if (opt) { await pg.mouse.click(opt.x, opt.y); await sleep(600); }
  }
  const catNow = await pg.evaluate(() => document.querySelector("[class*=layer_content_set_publish] button[class*=selectbox_button]").innerText.trim());
  console.log("CATEGORY=" + catNow);
  // 태그
  const tagBox = await pg.evaluate(() => { const i = document.querySelector("#tag-input"); const r = i.getBoundingClientRect(); return { x: r.x + 10, y: r.y + r.height/2 }; });
  await pg.mouse.click(tagBox.x, tagBox.y); await sleep(300);
  for (const tg of DATA.tags) { await pg.keyboard.type(tg); await pg.keyboard.press("Enter"); await sleep(250); }
  // 전체공개 (카테고리가 비공개면 라디오가 disabled 라 선택이 안 된다 → 카테고리 공개설정부터 확인)
  const lab = await pg.evaluate(() => { const r = document.querySelector("#open_public"); const l = document.querySelector("label[for=open_public]"); const b = l.getBoundingClientRect(); return { disabled: r.disabled, x: b.x + b.width/2, y: b.y + b.height/2 }; });
  if (!lab.disabled) { await pg.mouse.click(lab.x, lab.y); await sleep(500); }
  const vis = await pg.evaluate(() => ([...document.querySelectorAll("[class*=layer_content_set_publish] input[type=radio][id^=open_]")].find(x => x.checked)||{}).id);
  console.log("VISIBILITY=" + vis + (lab.disabled ? " (전체공개 비활성: 카테고리 비공개?)" : ""));
  const ok = catNow === DATA.category && vis === "open_public";
  console.log("READY=" + ok);
  if (ok) {
    const fin = await pg.evaluate(() => { const b = document.querySelector("[class*=layer_content_set_publish] button[class*=confirm_btn]"); const r = b.getBoundingClientRect(); return { x: r.x + r.width/2, y: r.y + r.height/2 }; });
    await pg.mouse.click(fin.x, fin.y);
    // 공개 범위가 바뀌면 "발행하시겠습니까?" 확인창이 한 번 더 뜬다
    let conf = null;
    for (let i = 0; i < 8 && !conf; i++) { await sleep(700); conf = await pg.evaluate(() => { const b = [...document.querySelectorAll("button")].filter(b => b.getBoundingClientRect().width > 0 && /^확인$/.test((b.innerText||"").trim())).find(b => { let p = b; for (let k = 0; k < 8 && p; k++) { if (/발행하시겠습니까/.test(p.innerText||"")) return true; p = p.parentElement; } return false; }); if (!b) return null; const r = b.getBoundingClientRect(); return { x: r.x + r.width/2, y: r.y + r.height/2 }; }); if (/PostView/.test(pg.url())) break; }
    if (conf) { await pg.mouse.click(conf.x, conf.y); }
    await sleep(8000);
    console.log("POST_URL=" + pg.url());
  }
  await pg.evaluate(() => { window.onbeforeunload = null; });
  await closeTab(pg);
  console.log("GSTACK_STEP_OK");
}
'''


def parse_md(path: Path) -> tuple[str, list[dict]]:
    title = ""
    lines: list[dict] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.rstrip()
        if s.startswith("# ") and not title:
            title = s[2:].strip(); continue
        if s == "---":
            lines.append({"text": ""}); continue
        if s.startswith("## "):
            lines.append({"text": s[3:].strip(), "bold": True}); continue
        if s.startswith("- "):
            lines.append({"text": "· " + s[2:].strip()}); continue
        if s.startswith("👉 ") and "http" in s:
            label, url = s[2:].split(": ", 1)
            lines.append({"text": label.strip()}); lines.append({"text": url.strip()}); continue
        lines.append({"text": s})
    while lines and not lines[-1]["text"]:
        lines.pop()
    return title, lines


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("md"); ap.add_argument("--category", required=True); ap.add_argument("--tags", default="")
    ap.add_argument("--dry-run", action="store_true")
    ns = ap.parse_args()
    title, lines = parse_md(Path(ns.md))
    data = {"title": title, "lines": lines, "category": ns.category, "tags": [t.strip() for t in ns.tags.split(",") if t.strip()], "dry": ns.dry_run}
    js = SCRIPT % {"data": json.dumps(data, ensure_ascii=False), "blog": BLOG_ID}
    out = subprocess.run([ASIDE, "repl", js], capture_output=True, text=True, timeout=300)
    text = out.stdout + out.stderr
    for ln in text.splitlines():
        if ln.startswith(("COMPS=", "CAT_OPT=", "CATEGORY=", "VISIBILITY=", "READY=", "POST_URL=", "ASIDE_DIR=", "GSTACK", "[error")) or "Error" in ln:
            print(ln[:300])
    return 0 if "GSTACK_STEP_OK" in text else 1


if __name__ == "__main__":
    sys.exit(main())
