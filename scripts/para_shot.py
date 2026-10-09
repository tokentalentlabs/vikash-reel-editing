"""Screenshot ONE paragraph (and the headline) of a page that only paints on-screen text (e.g. Deccan Herald):
scrolls each element into view, waits for it to paint, captures it on its own.

usage: para_shot.py URL OUT_STEM "phrase inside the paragraph" ["phrase to highlight" ...]
writes OUT_STEM_h1.png, OUT_STEM_para.png and OUT_STEM_para.json (highlight phrases -> line rects in para png px)
(desktop layout, width 900, DPR 2.4 - same as article_shot with SHOT_W=900 SHOT_DPR=2.4 SHOT_MOBILE=0)
"""
import base64
import json
import shutil
import subprocess
import sys
import tempfile
import time

import requests

from article_shot import CDP, CHROME, CLEAN_JS

PORT, H, DPR = 9336, 1400, 2.4
W = int(__import__("os").environ.get("PARA_W", 900))   # narrower = paragraph wraps tighter = larger text on the card

FIND_JS = r"""
((needle, phrases, which) => {
  let el = null;
  if (which === 'h1') el = document.querySelector('h1');
  else {
    const ps = [...document.querySelectorAll('p, li, div')].filter(e => e.innerText && e.innerText.includes(needle));
    ps.sort((a, b) => a.innerText.length - b.innerText.length);
    el = ps[0];
  }
  if (!el) return null;
  el.scrollIntoView({block: 'center'});
  const b = el.getBoundingClientRect();
  const lineRects = (range) => {
    const out = [];
    for (const r of range.getClientRects()) {
      if (r.width < 2 || r.height < 2) continue;
      const last = out[out.length - 1];
      if (last && Math.abs(last.y - (r.y - b.y)) < r.height * 0.5) {
        const x2 = Math.max(last.x + last.w, r.right - b.x);
        last.x = Math.min(last.x, r.x - b.x); last.w = x2 - last.x; last.h = Math.max(last.h, r.height);
      } else out.push({x: r.x - b.x, y: r.y - b.y, w: r.width, h: r.height});
    }
    return out;
  };
  const res = {box: {x: b.x, y: b.y, w: b.width, h: b.height}, phrases: {}, text: el.innerText};
  const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
  const nodes = []; let n; while ((n = walker.nextNode())) nodes.push(n);
  for (const p of phrases) for (const node of nodes) {
    const i = node.textContent.indexOf(p);
    if (i >= 0) { const r = document.createRange(); r.setStart(node, i); r.setEnd(node, i + p.length); res.phrases[p] = lineRects(r); break; }
  }
  return res;
})
"""


def shoot(c, needle, phrases, which, out_png):
    c.call("Runtime.evaluate", expression=f"({FIND_JS})({json.dumps(needle)}, {json.dumps(phrases)}, {json.dumps(which)})")
    time.sleep(1.8)   # let lazy text paint, then measure again in the settled position
    info = c.call("Runtime.evaluate", returnByValue=True,
                  expression=f"({FIND_JS})({json.dumps(needle)}, {json.dumps(phrases)}, {json.dumps(which)})")["result"]["value"]
    b = info["box"]
    pad = 12
    shot = c.call("Page.captureScreenshot", format="png", captureBeyondViewport=False,
                  clip={"x": max(0, b["x"] - pad), "y": max(0, b["y"] - pad), "width": b["w"] + 2 * pad, "height": b["h"] + 2 * pad, "scale": 1})
    with open(out_png, "wb") as f:
        f.write(base64.b64decode(shot["data"]))
    for rs in info["phrases"].values():
        for r in rs:
            r["x"] = (r["x"] + pad) * DPR
            r["y"] = (r["y"] + pad) * DPR
            r["w"] *= DPR
            r["h"] *= DPR
    return info


def main():
    url, stem, needle, phrases = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
    profile = tempfile.mkdtemp(prefix="chrome-para-")
    proc = subprocess.Popen([CHROME, "--headless=new", f"--remote-debugging-port={PORT}", f"--user-data-dir={profile}",
                             "--no-first-run", "--hide-scrollbars", "--mute-audio", f"--remote-allow-origins=http://127.0.0.1:{PORT}", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                page = next(t for t in requests.get(f"http://127.0.0.1:{PORT}/json", timeout=1).json() if t["type"] == "page")
                break
            except Exception:
                time.sleep(0.2)
        c = CDP(page["webSocketDebuggerUrl"])
        c.call("Emulation.setDeviceMetricsOverride", width=W, height=H, deviceScaleFactor=DPR, mobile=False)
        c.call("Page.enable")
        c.call("Page.navigate", url=url)
        time.sleep(7)
        c.call("Runtime.evaluate", expression=CLEAN_JS)
        time.sleep(1)
        c.call("Runtime.evaluate", expression=CLEAN_JS)
        for _ in range(12):   # some pages (DH) only mount story paragraphs once they are scrolled near
            c.call("Runtime.evaluate", expression="window.scrollBy(0, 700)")
            time.sleep(0.4)
        h1 = shoot(c, "", [], "h1", f"{stem}_h1.png")
        para = shoot(c, needle, phrases, "p", f"{stem}_para.png")
        para["h1_text"] = h1["text"]
        json.dump(para, open(f"{stem}_para.json", "w"), ensure_ascii=False, indent=1)
        print(json.dumps({"h1": h1["text"][:90], "para": para["text"][:120], "phrases": {k: len(v) for k, v in para["phrases"].items()}}, ensure_ascii=False))
    finally:
        proc.terminate()
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    main()
