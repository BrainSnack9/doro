#!/usr/bin/env python3
"""네이버 블로그 글의 사진을 교체한다 (기존 se-image 전부 삭제 → 첫 문단 뒤에 새 사진 → 전체공개 재발행).

  python3 haru/tools/blog_replace_image.py <logNo> <image.jpg> [--blog skekrla123]
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ASIDE = os.path.expanduser("~/.local/bin/aside")
ASIDE_ACCOUNT = os.environ.get("HARU_ASIDE_ACCOUNT", "u0")  # 하루 전용 Aside 계정(u0). 로이어픽은 u1 — 전역 기본 계정에 의존하지 않는다(2026-10-19)
SCRIPT = r'''
const logNo = "%(log)s"; const img = "%(img)s";
const pg = await openTab("about:blank");
const comps = () => pg.evaluate(() => [...document.querySelectorAll(".se-component")].map(c => c.className.split(" ").filter(x => /^se-(text|image|oglink|documentTitle)/.test(x)).join("|")));
try { await pg.goto("https://blog.naver.com/PostUpdateForm.naver?blogId=%(blog)s&logNo=" + logNo + "&widgetTypeCall=true&noTrackingCode=true&directAccess=false", { waitUntil: "commit", timeout: 20000 }); } catch (e) {}
let c0 = []; for (let i = 0; i < 10 && !c0.length; i++) { await sleep(2500); const dlg = await pg.evaluate(() => { const b = [...document.querySelectorAll("button")].find(e => e.getBoundingClientRect().width > 0 && /^취소$/.test((e.innerText||"").trim()) && (() => { let p = e; for (let k = 0; k < 8 && p; k++) { if (/작성 중인 글이 있습니다/.test(p.innerText||"")) return true; p = p.parentElement; } return false; })()); if (!b) return null; const r = b.getBoundingClientRect(); return { x: r.x + r.width/2, y: r.y + r.height/2 }; }); if (dlg) { await pg.mouse.click(dlg.x, dlg.y); await sleep(1500); } c0 = await comps(); }
console.log("LOADED=" + JSON.stringify(c0));
if (!c0.length) { console.log("RESULT=empty url=" + pg.url().slice(0, 80)); await closeTab(pg); console.log("GSTACK_STEP_OK"); }
else {
for (let i = 0; i < 4; i++) { const im = await pg.evaluate(() => { const el = document.querySelector(".se-component.se-image"); if (!el) return null; el.scrollIntoView({ block: "center" }); const r = el.getBoundingClientRect(); return { x: r.x + r.width/2, y: r.y + r.height/2 }; }); if (!im) break; await pg.mouse.click(im.x, im.y); await sleep(500); await pg.keyboard.press("Delete"); await sleep(800); }
await pg.evaluate(() => { const o = HTMLInputElement.prototype.click; HTMLInputElement.prototype.click = function () { if (this.type === "file") { window.__lastFileInput = this; return; } return o.apply(this, arguments); }; });
const p1 = await pg.evaluate(() => { const paras = [...document.querySelectorAll(".se-component.se-text .se-text-paragraph")].filter(p => (p.innerText||"").trim().length > 10); const para = paras[0]; para.scrollIntoView({ block: "center" }); const r = para.getBoundingClientRect(); return { x: r.x + Math.min(r.width - 4, 600), y: r.y + r.height - 6 }; });
await sleep(400); await pg.mouse.click(p1.x, p1.y); await sleep(400); await pg.keyboard.press("End"); await pg.keyboard.press("Enter"); await sleep(500);
const photo = await pg.evaluate(() => { const btn = [...document.querySelectorAll("button")].find(e => e.getBoundingClientRect().width > 0 && /사진/.test((e.innerText||"").trim()) && !/동영상/.test(e.innerText||"")); const r = btn.getBoundingClientRect(); return { x: r.x + r.width/2, y: r.y + r.height/2 }; });
await pg.mouse.click(photo.x, photo.y); await sleep(2500);
const doc = await pg._sendToTarget("DOM.getDocument", { depth: 1 }); const q = await pg._sendToTarget("DOM.querySelector", { nodeId: doc.root.nodeId, selector: "#hidden-file" }); await pg._sendToTarget("DOM.setFileInputFiles", { nodeId: q.nodeId, files: [img] });
await sleep(14000);
const final = await comps(); console.log("EDITED=" + JSON.stringify(final));
if (final.filter(c => c === "se-image").length === 1) {
  const pub = await pg.evaluate(() => { const b = [...document.querySelectorAll("button")].find(e => e.getBoundingClientRect().width > 0 && /^발행$/.test((e.innerText||"").trim())); const r = b.getBoundingClientRect(); return { x: r.x + r.width/2, y: r.y + r.height/2 }; });
  await pg.mouse.click(pub.x, pub.y); await sleep(2500);
  const vis = await pg.evaluate(() => { const r = document.querySelector("#open_public"); const l = document.querySelector("label[for=open_public]"); const b = l.getBoundingClientRect(); return { disabled: r.disabled, checked: r.checked, x: b.x + b.width/2, y: b.y + b.height/2 }; });
  if (!vis.checked && !vis.disabled) { await pg.mouse.click(vis.x, vis.y); await sleep(500); }
  const fin = await pg.evaluate(() => { const b = document.querySelector("[class*=layer_content_set_publish] button[class*=confirm_btn]"); const r = b.getBoundingClientRect(); return { x: r.x + r.width/2, y: r.y + r.height/2 }; });
  await pg.mouse.click(fin.x, fin.y);
  let conf = null; for (let i = 0; i < 8 && !conf; i++) { await sleep(700); if (/PostView/.test(pg.url())) break; conf = await pg.evaluate(() => { const b = [...document.querySelectorAll("button")].filter(b => b.getBoundingClientRect().width > 0 && /^확인$/.test((b.innerText||"").trim())).find(b => { let p = b; for (let k = 0; k < 8 && p; k++) { if (/발행하시겠습니까/.test(p.innerText||"")) return true; p = p.parentElement; } return false; }); if (!b) return null; const r = b.getBoundingClientRect(); return { x: r.x + r.width/2, y: r.y + r.height/2 }; }); }
  if (conf) { await pg.mouse.click(conf.x, conf.y); }
  await sleep(8000); console.log("RESULT=" + (/PostView/.test(pg.url()) ? "published" : "unverified"));
} else { console.log("RESULT=skip images=" + final.filter(c => c === "se-image").length); }
await pg.evaluate(() => { window.onbeforeunload = null; }); await closeTab(pg); console.log("GSTACK_STEP_OK");
}
'''


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("logno"); ap.add_argument("image"); ap.add_argument("--blog", default="")
    ns = ap.parse_args()
    txt = ""
    for blog in ([ns.blog] if ns.blog else ["harureviews", "skekrla123"]):
        js = SCRIPT.replace("%(log)s", ns.logno).replace("%(img)s", str(Path(ns.image).resolve())).replace("%(blog)s", blog)
        out = subprocess.run([ASIDE, "--account", ASIDE_ACCOUNT, "repl", js], capture_output=True, text=True, timeout=300)
        txt = out.stdout + out.stderr
        if "RESULT=empty" not in txt:
            break
        print(f"[blog] {blog}: 편집 화면 없음 → 다음 아이디")
    for ln in txt.splitlines():
        if ln.startswith(("LOADED=", "EDITED=", "RESULT=", "GSTACK")) or "[error" in ln:
            print(ln[:200])
    return 0 if "RESULT=published" in txt else 1


if __name__ == "__main__":
    sys.exit(main())
