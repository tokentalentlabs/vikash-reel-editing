"""Screenshot a tweet as a clean card (X's official embed, no login wall) and report phrase line boxes.

usage: tweet_shot.py TWEET_ID OUT_STEM ["phrase to locate" ...]   (env: TWEET_THEME=light|dark)
writes OUT_STEM.png (just the tweet card, DPR 3) and OUT_STEM.json (phrases -> line rects in png px)
"""
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

import requests

from article_shot import CDP, CHROME

PORT = int(os.environ.get("SHOT_PORT", 9334))
DPR = 3

RECTS_JS = r"""
((phrases) => {
  const card = document.querySelector('article') || document.querySelector('[data-testid="tweet"]') || document.body.firstElementChild;
  const cb = card.getBoundingClientRect();
  const lineRects = (range) => {
    const out = [];
    for (const r of range.getClientRects()) {
      if (r.width < 2 || r.height < 2) continue;
      const last = out[out.length - 1];
      if (last && Math.abs(last.y - (r.y - cb.y)) < r.height * 0.5) {
        const x2 = Math.max(last.x + last.w, r.right - cb.x);
        last.x = Math.min(last.x, r.x - cb.x); last.w = x2 - last.x; last.h = Math.max(last.h, r.height);
      } else out.push({x: r.x - cb.x, y: r.y - cb.y, w: r.width, h: r.height});
    }
    return out;
  };
  const walker = document.createTreeWalker(card, NodeFilter.SHOW_TEXT);
  const nodes = []; let n; while ((n = walker.nextNode())) nodes.push(n);
  const res = {card: {x: cb.x, y: cb.y, w: cb.width, h: cb.height}, phrases: {}, text: card.innerText};
  for (const p of phrases) {
    for (const node of nodes) {
      const i = node.textContent.indexOf(p);
      if (i >= 0) { const r = document.createRange(); r.setStart(node, i); r.setEnd(node, i + p.length); res.phrases[p] = lineRects(r); break; }
    }
  }
  return res;
})
"""


def main():
    tid, stem, phrases = sys.argv[1], sys.argv[2], sys.argv[3:]
    theme = os.environ.get("TWEET_THEME", "light")
    url = f"https://platform.twitter.com/embed/Tweet.html?id={tid}&theme={theme}&hideThread=true&lang=en"
    profile = tempfile.mkdtemp(prefix="chrome-tweet-")
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
        c.call("Emulation.setDeviceMetricsOverride", width=550, height=1600, deviceScaleFactor=DPR, mobile=False)
        c.call("Page.enable")
        c.call("Page.navigate", url=url)
        for _ in range(60):  # wait for the embed to render (it loads slowly when X rate-limits)
            time.sleep(0.5)
            ready = c.call("Runtime.evaluate", returnByValue=True,
                           expression="(() => { const a = document.querySelector('article'); return !!a && a.getBoundingClientRect().height > 50 && [...document.images].every(i => i.complete); })()")
            if ready["result"].get("value"):
                break
        time.sleep(1.5)
        info = c.call("Runtime.evaluate", expression=f"({RECTS_JS})({json.dumps(phrases)})", returnByValue=True)["result"]["value"]
        b = info["card"]
        shot = c.call("Page.captureScreenshot", format="png", captureBeyondViewport=False,  # True re-lays out the embed at another font size
                      clip={"x": b["x"], "y": b["y"], "width": b["w"], "height": b["h"], "scale": 1})
        with open(f"{stem}.png", "wb") as f:
            f.write(base64.b64decode(shot["data"]))
        for rs in info["phrases"].values():  # css px -> png px
            for r in rs:
                for k in r:
                    r[k] *= DPR
        info.update({"id": tid, "url": url, "dpr": DPR})
        with open(f"{stem}.json", "w") as f:
            json.dump(info, f, ensure_ascii=False, indent=1)
        print(json.dumps({"size": [b["w"], b["h"]], "phrases": {k: len(v) for k, v in info["phrases"].items()},
                          "text": info["text"][:160]}, ensure_ascii=False))
    finally:
        proc.terminate()
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    main()
