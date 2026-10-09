"""Screenshot a news article in mobile layout and report headline/phrase line boxes.

usage: article_shot.py URL OUT_STEM ["phrase to locate" ...]
writes OUT_STEM.png (viewport from page top through the lead image) and OUT_STEM.json
"""
import base64
import json
import shutil
import subprocess
import sys
import tempfile
import time

import requests
import websocket

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
import os
PORT = int(os.environ.get("SHOT_PORT", 9333))
W, H, DPR = int(os.environ.get("SHOT_W", 412)), int(os.environ.get("SHOT_H", 1400)), float(os.environ.get("SHOT_DPR", 2.62))  # SHOT_H: taller viewport for pages that only paint on-screen text
MOBILE = os.environ.get("SHOT_MOBILE", "1") == "1"
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1")

CLEAN_JS = r"""
(() => {
  // The site header (logo bar) sits in the first ~140 css px; it is the source attribution, so never remove it.
  const isHeader = el => { const r = el.getBoundingClientRect(); return r.top + scrollY < 140 && r.height < 200; };
  const keep = el => el.querySelector('h1') || isHeader(el) || el.querySelector('img[alt*="logo" i], img[src*="logo" i], svg');
  document.querySelectorAll('iframe, ins, [id*="google_ads"], [class*="advert"], [id*="taboola"], [class*="taboola"], [class*="cookie"], [id*="cookie"], [class*="consent"], [class*="popup"], [class*="modal"], [class*="notification"]').forEach(el => {
    if (!keep(el)) el.remove();
  });
  document.querySelectorAll('*').forEach(el => {
    const s = getComputedStyle(el);
    const floating = s.position === 'fixed' || s.position === 'sticky' || (s.position === 'absolute' && +s.zIndex >= 100);  // late slide-in ads
    if (floating && !keep(el)) el.style.display = 'none';
  });
  // Page chrome between the headline and the story text (preferred-source pills, share rows, ad slots) breaks the card.
  const junk = /preferred source|as a preferred|^\s*add\b[\s\S]{0,40}\bas a\s*$|trusted source|follow us|read time|min read|subscribe|listen to (this|the) (article|story)|advertisement|join our|whatsapp channel|google news/i;
  const h1 = document.querySelector('h1');
  const h1top = h1 ? h1.getBoundingClientRect().top : 0;
  document.querySelectorAll('body *').forEach(el => {
    if (!el.isConnected || el.querySelector('h1') || isHeader(el)) return;
    const t = (el.innerText || '').trim();
    const r = el.getBoundingClientRect();
    if (r.top < h1top) return;
    const cls = (el.className && el.className.baseVal !== undefined ? el.className.baseVal : el.className) + ' ' + el.id;
    if ((t.length < 90 && junk.test(t) && r.height < 200) || (/share|social/i.test(cls) && t.length < 60 && r.height < 120)) el.remove();
  });
  // Recommendation slide-ins ("Read Next Story") that sit on top of the story text.
  document.querySelectorAll('body *').forEach(el => {
    if (!el.isConnected || el.children.length || !/read next story/i.test(el.textContent || '')) return;
    let box = el;
    while (box.parentElement && box.parentElement.getBoundingClientRect().height < 320 && box.parentElement.getBoundingClientRect().width < 650) box = box.parentElement;
    box.remove();
  });
  document.documentElement.style.overflowX = 'hidden';
  document.body.style.overflowX = 'hidden';
  return true;
})()
"""

RECTS_JS = r"""
((phrases) => {
  const lineRects = (range) => {
    const out = [];
    for (const r of range.getClientRects()) {
      if (r.width < 2 || r.height < 2) continue;
      const last = out[out.length - 1];
      if (last && Math.abs(last.y - r.y) < r.height * 0.5) {
        const x2 = Math.max(last.x + last.w, r.right);
        last.x = Math.min(last.x, r.x); last.w = x2 - last.x;
        last.h = Math.max(last.h, r.height);
      } else out.push({x: r.x, y: r.y + scrollY, w: r.width, h: r.height});
    }
    return out;
  };
  const h1 = document.querySelector('h1');
  const res = {h1: null, phrases: {}};
  if (h1) { const r = document.createRange(); r.selectNodeContents(h1); res.h1 = {text: h1.innerText, lines: lineRects(r)}; }
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const nodes = []; let n; while ((n = walker.nextNode())) nodes.push(n);
  for (const p of phrases) {
    for (const node of nodes) {
      const i = node.textContent.indexOf(p);
      if (i >= 0 && node.parentElement.offsetParent !== null) {
        const r = document.createRange(); r.setStart(node, i); r.setEnd(node, i + p.length);
        res.phrases[p] = lineRects(r); break;
      }
    }
  }
  const img = [...document.images].find(im => {
    const b = im.getBoundingClientRect();
    return b.top + scrollY > (h1 ? h1.getBoundingClientRect().bottom + scrollY : 0) && b.width > 250 && b.height > 120 && im.complete && im.naturalWidth > 300;
  });
  if (img) { const b = img.getBoundingClientRect(); res.lead_image = {x: b.x, y: b.y + scrollY, w: b.width, h: b.height}; }
  if (h1) {
    const hb = h1.getBoundingClientRect().bottom;
    res.blocks = [...document.querySelectorAll('p, h2')]
      .filter(el => { const b = el.getBoundingClientRect(); return b.top >= hb - 2 && b.width > 200 && b.height > 10 && (el.innerText || '').trim().length > 60
        && !el.closest('aside, figure, footer, nav, [class*="related" i], [class*="also" i], [class*="twitter" i], blockquote'); })
      .slice(0, 10).map(el => { const r = document.createRange(); r.selectNodeContents(el); const b = el.getBoundingClientRect();
        return {text: el.innerText.trim().slice(0, 300), y: b.top + scrollY, h: b.height, lines: lineRects(r)}; });
  }
  res.paras = [...document.querySelectorAll('p, h2, blockquote')]
    .filter(el => (!h1 || el.getBoundingClientRect().top > h1.getBoundingClientRect().top) && (el.innerText || '').trim().length > 40)
    .slice(0, 14).map(el => el.innerText.trim());
  if (h1) {
    const hb = h1.getBoundingClientRect().bottom;
    const lead = [...document.querySelectorAll('h2, p, [class*="synopsis" i], [class*="summary" i], [class*="standfirst" i], [class*="excerpt" i], [class*="subhead" i], [class*="sub-head" i], [class*="description" i]')]
      .filter(el => { const b = el.getBoundingClientRect(); return b.top >= hb - 2 && b.width > 150 && (el.innerText || '').trim().length > 60 && !el.querySelector('p, h2'); })
      .sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top)[0];
    if (lead) { const r = document.createRange(); r.selectNodeContents(lead); res.lead = {text: lead.innerText.slice(0, 400), lines: lineRects(r)}; }
    let el = h1, bg = 'rgba(0, 0, 0, 0)';
    while (el && /rgba\(0, 0, 0, 0\)|transparent/.test(bg)) { bg = getComputedStyle(el).backgroundColor; el = el.parentElement; }
    res.bg = bg;
  }
  const logos = [...document.querySelectorAll('img, svg, a, span, div')].filter(el => {
    const b = el.getBoundingClientRect();
    const tag = (el.getAttribute('alt') || '') + ' ' + (el.getAttribute('src') || '') + ' ' + (el.getAttribute('class') || '') + ' ' + (el.id || '') + ' ' + (el.getAttribute('aria-label') || '');
    return b.top + scrollY < 260 && b.width > 60 && b.height > 18 && b.height < 140 && /logo|brand|masthead/i.test(tag);
  }).map(el => el.getBoundingClientRect()).sort((a, b) => b.width * b.height - a.width * a.height);
  if (logos.length) { const b = logos[0]; res.logo = {x: b.x, y: b.y + scrollY, w: b.width, h: b.height}; }
  return res;
})
"""


class CDP:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=60, suppress_origin=True)
        self.i = 0

    def call(self, method, **params):
        self.i += 1
        self.ws.send(json.dumps({"id": self.i, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.i:
                if "error" in msg:
                    raise RuntimeError(msg["error"])
                return msg.get("result", {})


def main():
    url, stem, phrases = sys.argv[1], sys.argv[2], sys.argv[3:]
    profile = tempfile.mkdtemp(prefix="chrome-shot-")
    proc = subprocess.Popen([CHROME, "--headless=new", f"--remote-debugging-port={PORT}", f"--user-data-dir={profile}",
                             "--no-first-run", "--hide-scrollbars", "--mute-audio", f"--remote-allow-origins=http://127.0.0.1:{PORT}", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    page = None
    try:
        for _ in range(100):
            try:
                tabs = requests.get(f"http://127.0.0.1:{PORT}/json", timeout=1).json()
                page = next(t for t in tabs if t["type"] == "page")
                break
            except Exception:
                time.sleep(0.2)
        c = CDP(page["webSocketDebuggerUrl"])
        c.call("Emulation.setDeviceMetricsOverride", width=W, height=H, deviceScaleFactor=DPR, mobile=MOBILE)
        if MOBILE:
            c.call("Emulation.setUserAgentOverride", userAgent=UA)
        c.call("Page.enable")
        c.call("Page.navigate", url=url)
        time.sleep(7)
        for y in range(0, 2400, 400):  # trigger lazy-loaded lead images
            c.call("Runtime.evaluate", expression=f"window.scrollTo(0, {y})")
            time.sleep(0.4)
        time.sleep(2)
        c.call("Runtime.evaluate", expression="window.stop(); window.scrollTo(0, 0)")
        c.call("Runtime.evaluate", expression=CLEAN_JS)
        time.sleep(1.5)
        c.call("Runtime.evaluate", expression=CLEAN_JS)
        info = c.call("Runtime.evaluate", expression=f"({RECTS_JS})({json.dumps(phrases)})", returnByValue=True)["result"]["value"]
        bottom = H
        if info.get("lead_image"):
            li = info["lead_image"]
            bottom = min(li["y"] + li["h"] + 10, 3000)
        if info.get("h1"):
            h1_bottom = max(l["y"] + l["h"] for l in info["h1"]["lines"])
            bottom = max(bottom, min(h1_bottom + 700, 4000))  # enough story text below the headline to fill a panel
        for blk in (info.get("blocks") or [])[:6]:
            bottom = max(bottom, min(blk["y"] + blk["h"] + 40, 12000))
        for rects in info.get("phrases", {}).values():  # make sure every located phrase is inside the capture
            if rects:
                bottom = max(bottom, min(max(r["y"] + r["h"] for r in rects) + 300, 30000))
        c.call("Runtime.evaluate", expression=CLEAN_JS)
        shot = c.call("Page.captureScreenshot", format="png", captureBeyondViewport=True,
                      clip={"x": 0, "y": 0, "width": W, "height": bottom, "scale": 1})
        with open(f"{stem}.png", "wb") as f:
            f.write(base64.b64decode(shot["data"]))
        info.update({"url": url, "css_width": W, "dpr": DPR})
        with open(f"{stem}.json", "w") as f:
            json.dump(info, f, ensure_ascii=False, indent=1)
        print(json.dumps({"h1": info.get("h1", {}) and info["h1"]["text"], "lines": len((info.get("h1") or {}).get("lines", [])),
                          "phrases": {k: len(v) for k, v in info["phrases"].items()}, "img": bool(info.get("lead_image"))}, ensure_ascii=False))
    finally:
        proc.terminate()
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    main()
