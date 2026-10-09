"""TEMPLATE (copy to 04_project_files/<ID>/build.py and replace IDs, takes, beats). Worked example:
Cockroach Janta Party / vote chori vs Punjab ward polls (video-heavy), animated layout, for Final Cut Pro.

Raws: 1.mov -> 2.mov -> 3.mov (1080x1920, 30 fps). Retakes removed:
  raw 1 opens with false starts ("ki aap soch... aap sochiye...") - kept from the last clean "aap sochiye" (3.45 s);
  raw 2 opens with a rehearsal repeating raw 1's last words ("unki sarkar") - kept from "aur Supreme Court" (4.05 s).
Raw 3 opens clean. Beat times are file-local seconds from 07_scripts_research/scripts/CJP/{1,2,3}_words.json.
Flagged lines stay on the plain face (beat sheet).
Run:  .venv/bin/python 04_project_files/CJP_Punjab/build.py [--no-preview] [--panels-only] [--final]
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import reel_kit as rk  # noqa: E402
from reel_kit import (TOP, W, H, FACE_SHIFT, Item, RED, WHITE, animate_layout, bar_motion, divider,  # noqa: E402
                      export_fcpxml, highlight_layer, hook_bar, logo_header, name_tag, panel_ff, photo_panel,
                      pill_layers, pill_motion, render_preview_multi, share_button, stack_card, story_still,
                      tag_motion, tweet_panel)
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

rk.set_fps(30)

ID = "CJP_Punjab"
RAW = ROOT / "01_footage/raw"
BR = ROOT / "01_footage/b-roll/CJP"
ART = ROOT / "07_scripts_research/news_articles/cjp"
LOGOS = ROOT / "07_scripts_research/logos"
GFX = ROOT / f"03_graphics/{ID}"
CLIPS = BR / "panels"
OUT_XML = ROOT / f"04_project_files/{ID}/{ID}_v1.fcpxml"
OUT_PREVIEW = ROOT / f"05_exports/shorts/{ID}_preview.mp4"
for d in (GFX, CLIPS):
    d.mkdir(parents=True, exist_ok=True)
PANELS_ONLY = "--panels-only" in sys.argv

TAKES = [("1", 3.45, 48.71), ("2", 4.05, 60.75), ("3", 1.25, 70.20)]
OFF, t = {}, 0.0
for name, a, b in TAKES:
    OFF[name] = t - a
    t += b - a
DURATION = t
RAWS = [str(RAW / f"{n}.mov") for n, _, _ in TAKES]


def T(take, sec):
    return OFF[take] + sec


items = []
gid = [0]


def png(img, name):
    p = GFX / f"{name}.png"
    img.save(p)
    return str(p)


def add(track, path, take, a, b, **kw):
    items.append(Item(track, str(path), T(take, a), T(take, b), **kw))


def new_group():
    gid[0] += 1
    return f"g{gid[0]}"


def tag(text, take, a, b, name, delay=0.5):
    add("V11", png(name_tag(text), f"tag_{name}"), take, a, b, motion=tag_motion(T(take, a), T(take, b), delay))


def bar(text, take, a, b, name, split=False):
    add("V11", png(hook_bar(text, cy=rk.BAR_Y_SPLIT if split else rk.BAR_Y_FULL), f"bar_{name}"), take, a, b,
        motion=bar_motion(T(take, a), T(take, b)))


def video_panel(out, take, a, b, name):
    add("P", out, take, a, b, kind="video", offset=(0, TOP / 2 - H / 2), name=name, group=new_group())


def clip(src, t0, take, a, b, name, crop=None, focus=0.5, fill=False):
    """Footage in the 1080xTOP panel, muted. crop='w:h:x:y' cuts a source region first (drops a corner logo);
    fill=True for vertical phone clips: centred at panel height over an enlarged blurred copy of itself."""
    out = str(CLIPS / f"{name}.mp4")
    if not PANELS_ONLY:
        pre = f"crop={crop}," if crop else ""
        if fill:
            fc = (f"[0:v]fps={rk.FPS_STR},{pre}split[a][b];"
                  f"[a]scale={W}:{TOP}:force_original_aspect_ratio=increase,crop={W}:{TOP},boxblur=24:2,eq=brightness=-0.08[bg];"
                  f"[b]scale=-2:{TOP}[fg];[bg][fg]overlay=(W-w)/2:0")
        else:
            fc = (f"[0:v]fps={rk.FPS_STR},{pre}scale={W}:{TOP}:force_original_aspect_ratio=increase,"
                  f"crop={W}:{TOP}:(iw-{W})/2:(ih-{TOP})*{focus}")
        subprocess.run([rk.FFMPEG, "-loglevel", "error", "-y", "-ss", f"{t0:.3f}", "-i", str(src), "-t", f"{b - a + 0.45:.3f}",
                        "-an", "-filter_complex", fc, "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", out], check=True)
    video_panel(out, take, a, b, name)


def photo(img, take, a, b, name, focus=(0.5, 0.4)):
    out = str(CLIPS / f"{name}.mp4")
    if not PANELS_ONLY:
        photo_panel(img, out, b - a + 0.45, focus=focus)
    video_panel(out, take, a, b, name)


def story(img, take, a, b, name, focus=(0.5, 0.5), **fx):
    fx["labels"] = [(s - a, txt, xy) for s, txt, xy in fx.get("labels", ())]
    out = str(CLIPS / f"{name}.mp4")
    if not PANELS_ONLY:
        story_still(img, out, b - a + 0.45, focus=focus, **fx)
    video_panel(out, take, a, b, name)


def still_panel(img, take, a, b, name, wipes=(), mode="black"):
    g = new_group()
    base = panel_ff(img)
    add("P", png(base, f"panel_{name}"), take, a, b, group=g)
    for k, (rect, w0, w1) in enumerate(wipes):
        layer, (x0, x1) = highlight_layer(base, rect, mode)
        add(f"H{k}", png(layer, f"hl_{name}_{k}"), take, w0, b, group=g, wipe=(T(take, w0), T(take, w1), x0, x1))


def pills(title, rows, times, take, a, b, name):
    g = new_group()
    base, layers = pill_layers(rows, title=title)
    add("P", png(panel_ff(base), f"panel_{name}"), take, a, b, group=g)
    for k, (layer, w) in enumerate(zip(layers, times)):
        add(f"H{k}", png(layer, f"pill_{name}_{k}"), take, w, b, group=g, motion=pill_motion(T(take, w)))


def spread(rects, w0, w1):
    total = sum(r[2] - r[0] for r in rects)
    out, t0 = [], w0
    for r in rects:
        t1 = t0 + (w1 - w0) * (r[2] - r[0]) / total
        out.append((r, t0, t1))
        t0 = t1
    return out


def erase_rules(img, boxes):
    """Paint out thin vertical page rules inside the crop boxes: a column that is dark over most of a block's height
    is a rule, never text (text columns always have line gaps)."""
    a = np.asarray(img.convert("L"))
    out = img.copy()
    d = ImageDraw.Draw(out)
    for x0, y0, x1, y1 in boxes:
        x0, y0, x1, y1 = (max(0, int(v)) for v in (x0, y0, x1, y1))
        sub = a[y0:y1, x0:x1]
        if sub.size == 0:
            continue
        dark = (sub < 140).mean(axis=0)
        for cx in np.nonzero(dark > 0.6)[0]:
            d.line([(x0 + cx, y0), (x0 + cx, y1)], fill=WHITE)
    return out


def article(stem, part_keys, logo):
    """Card from chosen blocks ("h1" or block index); returns (card, map lines->card rects, meta)."""
    meta = json.loads((ART / f"{stem}.json").read_text())
    img = Image.open(ART / f"{stem}.png").convert("RGB")
    k = meta["dpr"]

    def box(lines, pad=14):
        return (max(0, min(r["x"] for r in lines) * k - 3), max(0, min(r["y"] for r in lines) * k - pad),  # never crop outside the page (renders black)
                max(r["x"] + r["w"] for r in lines) * k + pad, max(r["y"] + min(r["h"], 44) for r in lines) * k + pad)
    parts = [box(meta["h1"]["lines"] if p == "h1" else meta["blocks"][p]["lines"]) for p in part_keys]
    img = erase_rules(img, parts)
    card, mapr = stack_card(img, parts, header=logo_header(logo))
    return card, (lambda lines: mapr([(r["x"] * k, r["y"] * k, (r["x"] + r["w"]) * k, (r["y"] + r["h"]) * k) for r in lines])), meta


def tweet(stem, cut_after):
    meta = json.loads((ART / f"{stem}.json").read_text())
    g = np.asarray(Image.open(ART / f"{stem}.png").convert("L"), dtype=np.int16)
    y0 = int(max(r["y"] + r["h"] for r in meta["phrases"][cut_after]))
    x0, x1 = g.shape[1] // 12, g.shape[1] * 11 // 12
    last_ink = y0
    for y in range(y0, g.shape[0]):
        if ((g[y:y + 30, x0:x1] < 235).mean(axis=1) > 0.6).all():
            break
        if (g[y, x0:x1] < 140).any():
            last_ink = y
    return tweet_panel(ART / stem, cut=last_ink + 40)


def bars_clip(out, dur, title, rows, t_rows, total_text, t_total=0.0):
    """Infographic (built as spoken): white card, a total line, then one bar per category that grows in when said.
    rows = [(label, value, colour)], t_rows = clip-time each row appears."""
    fb, fl, fv = (ImageFont.truetype(rk.F_BLACK, s) for s in (35, 30, 36))
    vmax = max(v for _, v, _ in rows)
    enc = subprocess.Popen([rk.FFMPEG, "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{TOP}",
                            "-r", rk.FPS_STR, "-i", "-", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", out],
                           stdin=subprocess.PIPE)
    for i in range(rk.frames(dur)):
        t = i / rk.FPS
        im = Image.new("RGB", (W, TOP), (238, 241, 246))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([30, 24, W - 30, TOP - 24], 28, fill=WHITE)
        d.text((W / 2, 74), title, font=fb, fill=(20, 20, 20), anchor="mm")
        u = rk.ease_out((t - t_total) / 0.3)
        if u > 0:
            d.rounded_rectangle([W / 2 - 300, 112, W / 2 + 300, 170], 12, fill=(29, 98, 216))
            d.text((W / 2, 141), total_text, font=fl, fill=WHITE, anchor="mm")
        for k, ((label, v, col), tr) in enumerate(zip(rows, t_rows)):
            u = rk.ease_out((t - tr) / 0.45)
            if u <= 0:
                continue
            y = 205 + k * 98
            d.text((70, y + 30), label, font=fl, fill=(30, 30, 30), anchor="lm")
            x0, x1 = 480, 480 + (W - 480 - 200) * v / vmax * u
            d.rounded_rectangle([x0, y + 8, max(x0 + 12, x1), y + 52], 10, fill=col)
            d.text((x1 + 16, y + 30), f"{v:.2f} cr".replace(".00", ""), font=fv, fill=col, anchor="lm")
        d.text((W - 50, TOP - 44), "Source: Election Commission data, as reported", font=ImageFont.truetype(rk.F_BOLD, 20),
               fill=(120, 120, 120), anchor="rm")
        enc.stdin.write(im.tobytes())
    enc.stdin.close()
    enc.wait()
    return out


# ---------------- cards ----------------
ie_logo = Image.open(LOGOS / "indianexpress.png")
ie, ie_map, ie_m = article("ie_punjab", ["h1", 1], ie_logo)
dh_meta = json.loads((ART / "dh_13cr.json").read_text())
dh_png = Image.open(ART / "dh_13cr.png").convert("RGB")
dh_logo = dh_png.crop((22, 6, 208, 168))   # DH mark + "DECCAN HERALD" wordmark
def para_card(stem, phrase, logo, header_h=170):
    """Card from para_shot.py captures (headline + one paragraph, each shot after scrolling to it); returns
    (card, highlight rects of `phrase` in card px)."""
    h1 = Image.open(ART / f"{stem}_h1.png").convert("RGB")
    h1 = h1.resize((round(h1.width * 0.6), round(h1.height * 0.6)), Image.LANCZOS)   # DH's headline font is huge
    para = Image.open(ART / f"{stem}_para.png").convert("RGB")
    meta = json.loads((ART / f"{stem}_para.json").read_text())
    src = Image.new("RGB", (max(h1.width, para.width), h1.height + 40 + para.height), WHITE)
    src.paste(h1, (0, 0))
    src.paste(para, (0, h1.height + 40))
    card, mapr = stack_card(src, [(0, 0, h1.width, h1.height), (0, h1.height + 40, para.width, h1.height + 40 + para.height)],
                            header=logo_header(logo, h=header_h))
    oy = h1.height + 40
    return card, mapr([(r["x"], r["y"] + oy, r["x"] + r["w"], r["y"] + oy + r["h"]) for r in meta["phrases"][phrase]])


dhre, r_re = para_card("dhp_reenter", "An option to re-enter the voter list is possible", dh_logo)
dhh, r_admit = para_card("dhp_hakimpur", "admit they procured Aadhaar cards, ration cards or voter IDs", dh_logo)
dh13, r_13 = para_card("dhp_13cr", "around 13.3 crore names were deleted from the draft voter lists", dh_logo)
demands = tweet("tw_cjp_demands", "Freeze SIR & restore the January 2025 voter list")

# ---------------- layout: split under every panel, full face in FULL windows ----------------
FULL = {"1": [(20.42, 25.50), (42.00, 48.71)],
        "2": [(16.06, 20.54), (56.48, 60.75)],
        "3": [(1.25, 8.64), (48.32, 53.40), (65.24, 70.20)]}

# ================= RAW 1 =================
hook = Image.open(BR / "hook_stage.jpg").convert("RGB")
story(hook, "1", 3.45, 9.54, "hook_stage", focus=(0.5, 0.4), zoom=0.07,
      labels=[(7.40, "DHRUV RATHEE", (250, 400)), (7.90, "PRAKASH RAJ", (600, 480))])
tag("CJP'S 'AVENGERS' ASSEMBLE", "1", 3.45, 9.54, "avengers", delay=0.4)
clip(BR / "blr_stir.mp4", 47.0, "1", 9.54, 11.90, "blr_stage", crop="1660:968:260:112")
tag("FREEDOM PARK, BENGALURU · 8 OCT", "1", 9.54, 11.90, "blr", delay=0.2)
clip(BR / "saurav_amit.mp4", 55.2, "1", 11.90, 20.42, "saurav", crop="1226:715:0:110", focus=0.4)
tag("SAURAV DAS · CJP SPOKESPERSON", "1", 11.90, 20.42, "saurav")
bar("BUT ON PUNJAB? SILENCE", "1", 21.30, 25.30, "punjab")
photo(Image.open(BR / "supreme_court.jpg").convert("RGB"), "1", 25.50, 29.30, "sc", focus=(0.5, 0.45))
tag("SUPREME COURT ORDER · PUNJAB WARD POLLS", "1", 25.50, 29.30, "sc")
r_set = ie_map(ie_m["phrases"]["The Supreme Court has set aside the elections to 50 wards in Punjab"])
still_panel(ie, "1", 29.30, 37.40, "ie_set_aside", spread(r_set, 29.46, 31.00))
clip(BR / "blr_megh.mp4", 2.0, "1", 37.40, 42.00, "blr_crowd", fill=True)
# 42.00-48.71 "Punjab me CJP ke behind-the-scene masters ki sarkar hai" -> FLAGGED (alleges who controls CJP), face only

# ================= RAW 2 =================
clip(BR / "pb_manik1.mp4", 1.4, "2", 4.05, 8.00, "pb_scuffle", crop="1600:933:0:0")
tag("PATIALA DC OFFICE · NOMINATIONS, DEC 2024", "2", 4.05, 8.00, "patiala", delay=0.3)
r_snatch = ie_map(ie_m["phrases"]["nomination papers were snatched, torn or destroyed, and candidates were assaulted, detained or threatened"])
still_panel(ie, "2", 8.00, 11.16, "ie_snatched", spread(r_snatch, 8.20, 10.80))
clip(BR / "pb_jhinjer.mp4", 18.0, "2", 11.16, 16.06, "pb_jhinjer")
bar("ELECTION CHOR, GADDI CHHOD?", "2", 17.70, 20.54, "election_chor")
clip(BR / "toi_dhruv.mp4", 5.0, "2", 20.54, 23.36, "dhruv_chant", fill=True)
tag("'VOTE CHOR, GADDI CHHOD' · BENGALURU", "2", 20.54, 23.36, "chant", delay=0.2)
r_freeze = demands[1]["Freeze SIR & restore the January 2025 voter list"]
still_panel(demands[0], "2", 23.36, 29.34, "cjp_demands", [(r_freeze[0], 26.34, 28.50)])
clip(BR / "bd_ani1.mp4", 5.0, "2", 29.34, 35.34, "hakimpur")
tag("HAKIMPUR BORDER, BENGAL · MAY 2026", "2", 29.34, 35.34, "hakimpur")
still_panel(dhh, "2", 35.34, 40.18, "dh_hakimpur", spread(r_admit, 36.30, 39.60))
clip(BR / "bd_ani3.mp4", 48.0, "2", 40.18, 44.68, "hakimpur_desk")
pills("2026 ASSEMBLY ELECTIONS", ["West Bengal", "Tamil Nadu · Kerala", "Assam · Puducherry"],
      [45.10, 48.52, 49.24], "2", 44.68, 50.92, "states")
clip(BR / "tn_vijay.mp4", 11.0, "2", 50.92, 53.20, "tn_vijay")
tag("TAMIL NADU: TVK'S VIJAY SWORN IN AS CM", "2", 50.92, 53.20, "tn", delay=0.2)
clip(BR / "kl_oath.mp4", 10.0, "2", 53.20, 56.48, "kl_oath", focus=0.35)
tag("KERALA: UDF'S VD SATHEESAN SWORN IN AS CM", "2", 53.20, 56.48, "kl", delay=0.2)
bar("THEN HOW DID THEY WIN?", "2", 57.10, 60.60, "how")

# ================= RAW 3 =================
still_panel(dh13, "3", 8.64, 12.26, "dh_13cr", spread(r_13, 9.88, 11.94))
clip(BR / "cjp_demands.mp4", 5.0, "3", 12.26, 15.12, "cjp_presser")
if not PANELS_ONLY:
    bars_clip(str(CLIPS / "sir_bars.mp4"), 40.40 - 15.12 + 0.45, "13 CRORE: NOT DELETED, NOT YET INCLUDED",
              [("Shifted permanently", 6.30, (29, 98, 216)), ("Absent / untraceable", 3.01, (90, 140, 230)),
               ("Died", 2.80, (60, 60, 60)), ("Duplicate entries", 1.02, (204, 16, 16))],
              [25.04 - 15.12, 31.58 - 15.12, 35.10 - 15.12, 37.78 - 15.12], "DRAFT-STAGE NON-INCLUSIONS",
              t_total=20.76 - 15.12)
video_panel(str(CLIPS / "sir_bars.mp4"), "3", 15.12, 40.40, "sir_bars")
still_panel(dhre, "3", 40.40, 48.32, "dh_reenter", spread(r_re, 42.00, 45.40))
bar("CJP, YOUR CHANCE TO SAVE DEMOCRACY?", "3", 49.40, 53.30, "chance")
r_h1 = ie_map([dict(l, y=l["y"] + 6, h=38) for l in ie_m["h1"]["lines"]])   # line boxes overlap; trim so each line gets its own wipe
still_panel(ie, "3", 53.40, 57.34, "ie_again", spread(r_h1, 55.20, 57.20))
clip(BR / "blr_stir.mp4", 40.0, "3", 57.34, 65.24, "blr_hands", crop="1660:968:260:112")
bar("COMMENT YOUR VIEW", "3", 65.40, 68.30, "comment")
if not PANELS_ONLY:
    share = str(CLIPS / "share.mov")
    share_button(share, dur=1.10)
    add("V14", share, "3", 69.05, 70.15, kind="video", name="SHARE")

# ---------------- face + layout ----------------
WIN = []
for name, a, b in TAKES:
    cuts = sorted({a, b, *[v for x, y in FULL[name] for v in (x, y)]})
    for s0, e0 in zip(cuts, cuts[1:]):
        full = any(x <= s0 < y for x, y in FULL[name])
        if not full:
            WIN.append((T(name, s0), T(name, e0)))
        items.append(Item("V1", RAWS[int(name) - 1], T(name, s0), T(name, e0), kind="video", src_in=s0,
                          name=f"Face {name} ({'full' if full else 'split'})",
                          **({} if full else dict(offset=(0, FACE_SHIFT)))))
    items.append(Item("A1", RAWS[int(name) - 1], T(name, a), T(name, b), kind="audio", src_in=a, name=f"VO take {name}"))
windows = []
for a, b in WIN:
    if windows and abs(windows[-1][1] - a) < 1e-3:
        windows[-1] = (windows[-1][0], b)
    else:
        windows.append((a, b))
div = png(divider(), "divider")
for a, b in windows:
    items.append(Item("D", div, a, b, name="Divider"))

if PANELS_ONLY:
    print("panels written to", GFX)
    sys.exit()
items = animate_layout(items, windows)
export_fcpxml(items, f"{ID}_v1", OUT_XML, DURATION)
print(f"timeline {DURATION:.2f}s from {len(TAKES)} takes, {len(items)} items -> {OUT_XML}")
if "--no-preview" not in sys.argv:
    OUT_PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    render_preview_multi(items, RAWS, str(OUT_PREVIEW), DURATION)
    print(f"preview -> {OUT_PREVIEW}")
if "--final" in sys.argv:
    out = OUT_PREVIEW.with_name(f"{ID}_final.mp4")
    render_preview_multi(items, RAWS, str(out), DURATION, scale=1.0)
    print(f"final -> {out}")
