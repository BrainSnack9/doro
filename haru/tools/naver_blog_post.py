#!/usr/bin/env python3
"""네이버 블로그(SmartEditor ONE)에 마크다운 초안을 Aside 로 게시한다.

  python3 haru/tools/naver_blog_post.py haru/blog/2026-10-17-multitap.md --category 자취방 --tags 자취템,멀티탭 --image haru/assets/posts/2026-10-17-multitap-b.jpg [--dry-run]

초안 형식: 첫 줄 "# 제목", "## 소제목" 은 굵게, "- " 목록은 "· " 로, URL 한 줄은 링크 카드로(에디터가 자동 변환), "---" 아래는 고지.
--image 를 주면 첫 문단 바로 뒤에 사진을 넣는다(에디터의 숨은 파일 입력 #hidden-file 에 CDP DOM.setFileInputFiles).
Aside 에 네이버 로그인이 있어야 한다. 발행 후 글 주소를 출력한다. 블로그 주소는 2026-10-17 harureviews 로 변경 신청(전파 전까지 관리 URL 은 skekrla123).
"""
import argparse
import json
import re
import os
import subprocess
import sys
from pathlib import Path

ASIDE = os.path.expanduser("~/.local/bin/aside")
BLOG_IDS = ["harureviews", "skekrla123"]  # 2026-10-17 주소 변경 신청. 전파 전엔 옛 아이디, 전파 후엔 새 아이디만 편집 화면이 열린다

SCRIPT = r'''
const DATA = %(data)s;
const pg = await openTab("about:blank");
try { await pg.goto("https://blog.naver.com/PostWriteForm.naver?blogId=%(blog)s&Redirect=Write&redirect=Write&widgetTypeCall=true&noTrackingCode=true&directAccess=false", { waitUntil: "commit", timeout: 20000 }); } catch (e) {}
await sleep(12000);
// "작성 중인 글이 있습니다" 팝업(이전 실패 흔적)이 있으면 "취소"로 닫고 새 글로 간다 (2026-10-18 추가)
const resume = await pg.evaluate(() => { const vis = (e) => e.getBoundingClientRect().width > 0; if (![...document.querySelectorAll("*")].some(e => vis(e) && e.children.length === 0 && /작성 중인 글이 있습니다/.test(e.innerText||""))) return null; const b = [...document.querySelectorAll("button")].find(e => vis(e) && /^취소$/.test((e.innerText||"").trim())); if (!b) return null; const r = b.getBoundingClientRect(); return { x: r.x + r.width/2, y: r.y + r.height/2 }; });
if (resume) { await pg.mouse.click(resume.x, resume.y); await sleep(1500); console.log("RESUME_POPUP=closed"); }
const ph = (re) => pg.evaluate((src) => { const re = new RegExp(src); const el = [...document.querySelectorAll("[class*=placeholder]")].find(e => re.test((e.innerText||"").trim())); if (!el) return null; const r = el.getBoundingClientRect(); return { x: r.x + 20, y: r.y + r.height/2 }; }, re.source);
const t = await ph(/^제목$/); if (!t) throw new Error("제목 자리 없음");
await pg.mouse.click(t.x, t.y); await sleep(500); await pg.keyboard.type(DATA.title); await sleep(400);
const b = await ph(/일상을 기록/); if (b) { await pg.mouse.click(b.x, b.y); } else { await pg.keyboard.press("Enter"); }
await sleep(500);
await pg.evaluate(() => { const o = HTMLInputElement.prototype.click; HTMLInputElement.prototype.click = function () { if (this.type === "file") { window.__lastFileInput = this; return; } return o.apply(this, arguments); }; });
let firstDone = false;
for (const line of DATA.lines) {
  if (line.bold) { await pg.keyboard.press("Meta+b"); await pg.keyboard.type(line.text); await pg.keyboard.press("Meta+b"); }
  else if (line.text) { await pg.keyboard.type(line.text); }
  await pg.keyboard.press("Enter");
  if (/^https?:\/\//.test(line.text)) await sleep(3500);  // 링크 카드 변환 대기
  else await sleep(120);
  if (!firstDone && line.text && !line.bold && DATA.image) {
    firstDone = true;
    const photo = await pg.evaluate(() => { const btn = [...document.querySelectorAll("button")].find(e => e.getBoundingClientRect().width > 0 && /사진/.test((e.innerText||"").trim()) && !/동영상/.test(e.innerText||"")); const r = btn.getBoundingClientRect(); return { x: r.x + r.width/2, y: r.y + r.height/2 }; });
    await pg.mouse.click(photo.x, photo.y); await sleep(2500);
    try { const doc = await pg._sendToTarget("DOM.getDocument", { depth: 1 }); const q = await pg._sendToTarget("DOM.querySelector", { nodeId: doc.root.nodeId, selector: "#hidden-file" }); await pg._sendToTarget("DOM.setFileInputFiles", { nodeId: q.nodeId, files: [DATA.image] }); console.log("IMAGE=set"); } catch (e) { console.log("IMAGE=fail " + String(e).slice(0, 100)); }
    await sleep(14000);
    // 사진 뒤 새 문단으로 커서 이동 (사진 컴포넌트 다음 빈 문단을 클릭)
    const after = await pg.evaluate(() => { const cs = [...document.querySelectorAll(".se-component")]; const i = cs.findIndex(c => /se-image/.test(c.className)); const nxt = cs[i + 1]; if (!nxt) return null; const p = nxt.querySelector(".se-text-paragraph") || nxt; p.scrollIntoView({ block: "center" }); const r = p.getBoundingClientRect(); return { x: r.x + Math.min(r.width - 4, 300), y: r.y + r.height/2 }; });
    if (after) { await pg.mouse.click(after.x, after.y); await pg.keyboard.press("End"); await sleep(300); }
  }
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


CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"


def _no_autolist(text: str) -> str:
    """SmartEditor 는 줄 머리의 '1. ' 를 번호 목록으로 자동 변환하고 이후 줄에 번호를 계속 붙인다(2026-10-18 실험 일지가 그렇게 깨짐).
    줄 머리 'N. ' 는 원문자 'N ' 로 바꾼다."""
    m = re.match(r"^(\d{1,2})\.\s+(.*)$", text)
    if m and 1 <= int(m.group(1)) <= 10:
        return CIRCLED[int(m.group(1)) - 1] + " " + m.group(2)
    return text


def _table_rows(rows: list[str]) -> list[dict]:
    """마크다운 표는 편집기에 못 넣으니 '· 항목: 값' 줄로 바꾼다. 머리글 행과 구분선은 버린다."""
    out: list[dict] = []
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    cells = [c for c in cells if not all(re.fullmatch(r":?-+:?", x or "-") for x in c)]
    for c in cells[1:] if len(cells) > 1 else cells:
        out.append({"text": "· " + c[0] + ": " + " / ".join(x for x in c[1:] if x)})
    return out


def parse_md(path: Path) -> tuple[str, list[dict]]:
    title = ""
    lines: list[dict] = []
    table: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.rstrip()
        if s.startswith("|"):
            table.append(s); continue
        if table:
            lines.extend(_table_rows(table)); table = []
        if s.startswith("# ") and not title:
            title = s[2:].strip(); continue
        if s == "---":
            lines.append({"text": ""}); continue
        if s.startswith("### "):
            lines.append({"text": _no_autolist(s[4:].strip()), "bold": True}); continue
        if s.startswith("## "):
            lines.append({"text": _no_autolist(s[3:].strip()), "bold": True}); continue
        if s.startswith("- "):
            lines.append({"text": "· " + _no_autolist(s[2:].strip())}); continue
        if s.startswith("👉 ") and "http" in s:
            label, url = s[2:].split(": ", 1)
            lines.append({"text": label.strip()}); lines.append({"text": url.strip()}); continue
        lines.append({"text": _no_autolist(s)})
    if table:
        lines.extend(_table_rows(table))
    while lines and not lines[-1]["text"]:
        lines.pop()
    return title, lines


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("md"); ap.add_argument("--category", required=True); ap.add_argument("--tags", default="")
    ap.add_argument("--image", default="", help="첫 문단 뒤에 넣을 사진 파일(절대 경로 권장)")
    ap.add_argument("--dry-run", action="store_true")
    ns = ap.parse_args()
    title, lines = parse_md(Path(ns.md))
    data = {"title": title, "lines": lines, "category": ns.category, "tags": [t.strip() for t in ns.tags.split(",") if t.strip()], "dry": ns.dry_run, "image": str(Path(ns.image).resolve()) if ns.image else ""}
    text = ""
    for blog in BLOG_IDS:  # 편집 화면이 안 열리는 아이디는 건너뛰고 다음 아이디로
        js = SCRIPT % {"data": json.dumps(data, ensure_ascii=False), "blog": blog}
        out = subprocess.run([ASIDE, "repl", js], capture_output=True, text=True, timeout=300)
        text = out.stdout + out.stderr
        if "제목 자리 없음" not in text and "Error" not in text.split("GSTACK")[0][-400:]:
            break
        print(f"[blog] {blog} 편집 화면 실패 → 다음 아이디 시도")
    for ln in text.splitlines():
        if ln.startswith(("COMPS=", "IMAGE=", "RESUME_POPUP=", "CAT_OPT=", "CATEGORY=", "VISIBILITY=", "READY=", "POST_URL=", "ASIDE_DIR=", "GSTACK", "[error")) or "Error" in ln:
            print(ln[:300])
    return 0 if "GSTACK_STEP_OK" in text else 1


if __name__ == "__main__":
    sys.exit(main())
