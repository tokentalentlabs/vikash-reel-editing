"""TEMPLATE (copy to 04_project_files/<ID>/build.py and replace IDs, takes, beats). Worked example:
Elon Musk vs Ambani / Starlink tweet war (research-heavy), animated layout, for Final Cut Pro.

Raws: 1.mov -> 2.mov -> 3.mov (1080x1920, 30 fps). Retakes removed:
  raw 1 opens "Elon Musk... Elon Musk bhai sahab" - kept from the second "Elon Musk" (3.95 s);
  raw 2 opens "lekin, lekin, lekin, lekin bhai sahab" - kept from the last "lekin" (2.55 s);
  raw 3 opens "aur, aur, aur Rahul Gandhi ji" - kept from "Rahul Gandhi ji" (2.20 s).
Raw 3 (last file): the dead pause before "Jai Hind" (52.12-52.75) is cut, so raw 3 plays as two segments (3, 4). Beat times are file-local seconds from
07_scripts_research/scripts/ELON/{1,2,3}_words.json. Flagged lines stay on the plain face (beat sheet).
Run:  .venv/bin/python 04_project_files/ELON_Starlink/build.py [--no-preview] [--panels-only] [--final]
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import reel_kit as rk  # noqa: E402
from reel_kit import (TOP, W, H, FACE_SHIFT, F, Item, WHITE, YELLOW, animate_layout, bar_motion, divider,  # noqa: E402
                      export_fcpxml, highlight_layer, hook_bar, logo_header, name_tag, panel_ff, photo_panel,
                      pill_layers, pill_motion, pip_face_motion, render_preview_multi, share_button, stack_card,
                      tag_motion, tweet_panel)
from PIL import Image, ImageChops, ImageDraw  # noqa: E402

rk.set_fps(30)

ID = "ELON_Starlink"
RAW = ROOT / "01_footage/raw"
BR = ROOT / "01_footage/b-roll/ELON"
ART = ROOT / "07_scripts_research/news_articles/elon"
LOGOS = ROOT / "07_scripts_research/logos"
GFX = ROOT / f"03_graphics/{ID}"
CLIPS = BR / "panels"
OUT_XML = ROOT / f"04_project_files/{ID}/{ID}_v1.fcpxml"
OUT_PREVIEW = ROOT / f"05_exports/shorts/{ID}_preview.mp4"
for d in (GFX, CLIPS):
    d.mkdir(parents=True, exist_ok=True)
PANELS_ONLY = "--panels-only" in sys.argv

TAKES = [("1", 3.95, 51.75), ("2", 2.55, 62.88), ("3", 2.20, 52.12), ("4", 52.75, 54.20)]   # 4 = raw 3 after the end pause
RAWFILE = {"1": 0, "2": 1, "3": 2, "4": 2}
OFF, t = {}, 0.0
for name, a, b in TAKES:
    OFF[name] = t - a
    t += b - a
DURATION = t
RAWS = [str(RAW / f"{n}.mov") for n in ("1", "2", "3")]


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


def clip(src, t0, take, a, b, name, focus=0.5, crop=None):
    """Footage in the 1080xTOP panel, muted, with a 0.45 s tail for the push/exit moves. crop='w:h:x:y' cuts a source
    region first (e.g. to frame the speaker instead of the backdrop)."""
    out = str(CLIPS / f"{name}.mp4")
    if not PANELS_ONLY:
        vf = (f"fps={rk.FPS_STR},{f'crop={crop},' if crop else ''}scale={W}:{TOP}:force_original_aspect_ratio=increase,"
              f"crop={W}:{TOP}:(iw-{W})/2:(ih-{TOP})*{focus}")
        subprocess.run([rk.FFMPEG, "-loglevel", "error", "-y", "-ss", f"{t0:.3f}", "-i", str(src), "-t", f"{b - a + 0.45:.3f}",
                        "-an", "-vf", vf, "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", out], check=True)
    video_panel(out, take, a, b, name)


def photo(img, take, a, b, name, focus=(0.5, 0.4)):
    out = str(CLIPS / f"{name}.mp4")
    if not PANELS_ONLY:
        photo_panel(img, out, b - a + 0.45, focus=focus)
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
    """One wipe per line, the time [w0, w1] shared out by line width."""
    total = sum(r[2] - r[0] for r in rects)
    out, t0 = [], w0
    for r in rects:
        t1 = t0 + (w1 - w0) * (r[2] - r[0]) / total
        out.append((r, t0, t1))
        t0 = t1
    return out


def article(stem, part_keys, logo, header_h=110):
    """Card from chosen blocks ("h1", a block index, or a phrase whose block is wanted); returns (card, mapper, meta).
    mapper(phrase) -> highlight rects in card px."""
    meta = json.loads((ART / f"{stem}.json").read_text())
    img = Image.open(ART / f"{stem}.png").convert("RGB")
    k = meta["dpr"]

    def block_of(p):
        if isinstance(p, int):
            return meta["blocks"][p]["lines"]
        r = meta["phrases"][p][0]
        for b in meta["blocks"]:
            ys = [l["y"] for l in b["lines"]]
            if min(ys) - 2 <= r["y"] <= max(l["y"] + l["h"] for l in b["lines"]):
                return b["lines"]
        raise KeyError(p)

    def box(lines, pad=14):
        return (max(0, min(r["x"] for r in lines) * k - 3), max(0, min(r["y"] for r in lines) * k - pad),  # never crop outside the page (renders black)
                min(img.width, max(r["x"] + r["w"] for r in lines) * k + pad), max(r["y"] + min(r["h"], 44) for r in lines) * k + pad)
    parts = [box(meta["h1"]["lines"] if p == "h1" else block_of(p)) for p in part_keys]
    card, mapr = stack_card(img, parts, header=logo_header(Image.open(LOGOS / f"{logo}.png"), h=header_h))

    def rects(phrase):
        lines = meta["h1"]["lines"] if phrase == "h1" else meta["phrases"][phrase]
        return mapr([(r["x"] * k, r["y"] * k, (r["x"] + r["w"]) * k, (r["y"] + r["h"]) * k) for r in lines])
    return card, rects, meta


def tweet_cut(stem, last_phrase, pad=40):
    """Pixel row just under a tweet's own text (drops the quoted post, media and footer)."""
    meta = json.loads((ART / f"{stem}.json").read_text())
    return int(max(r["y"] + r["h"] for r in meta["phrases"][last_phrase]) + pad)


def tweet(stem, last_phrase):
    return tweet_panel(ART / stem, cut=tweet_cut(stem, last_phrase))


def tweet_war(out, dur, cards, circle=rk.PIP_CIRCLE):
    """Circle-PiP tweet war (ANIMATION.md: tweets stacked in the PiP): dark grid with the host's circle on top,
    tweet cards stacked below; each card rises from the bottom + scales 60->100 % (18 f, ease-out) when its author is
    named, and a yellow marker wipes behind a phrase as it is spoken. cards = [(stem, last_phrase, t_in, hl)] with
    hl = (phrase, t0, t1) or None; times are clip seconds. Writes ProRes 4444 with alpha."""
    base = rk.grid_background().convert("RGBA")
    cx, cy, r = circle
    mask = Image.new("L", (W, H), 255)
    ImageDraw.Draw(mask).ellipse([cx - r, cy - r, cx + r, cy + r], fill=0)
    base.putalpha(mask)
    ImageDraw.Draw(base).ellipse([cx - r - 6, cy - r - 6, cx + r + 6, cy + r + 6], outline=WHITE, width=8)
    built = []
    for stem, last, t_in, hl in cards:
        im = Image.open(ART / f"{stem}.png").convert("RGB")
        meta = json.loads((ART / f"{stem}.json").read_text())
        body = im.crop((6, 6, im.width - 6, tweet_cut(stem, last)))
        built.append([body, meta, t_in, hl])
    top, bottom, gap, cw = cy + r + 50, H - 40, 26, 940
    s = min(cw / built[0][0].width, (bottom - top - gap * (len(built) - 1)) / sum(b[0].height for b in built))
    y = top + max(0, (bottom - top - sum(round(b[0].height * s) + 24 for b in built) - gap * (len(built) - 1)) // 2)
    for b in built:
        body, meta, t_in, hl = b
        sz = (round(body.width * s), round(body.height * s))
        card = Image.new("RGBA", (sz[0] + 24, sz[1] + 24), (0, 0, 0, 0))
        m = Image.new("L", card.size, 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, card.width - 1, card.height - 1], 26, fill=255)
        card.paste(Image.new("RGBA", card.size, WHITE + (255,)), (0, 0), m)
        card.paste(body.resize(sz, Image.LANCZOS), (12, 12))
        hl_rects = []
        if hl:
            for rr in meta["phrases"][hl[0]]:
                hl_rects.append((round((rr["x"] - 6) * s) + 12 - 8, round((rr["y"] - 6) * s) + 12 - 3,
                                 round((rr["x"] + rr["w"] - 6) * s) + 12 + 8, round((rr["y"] + rr["h"] - 6) * s) + 12 + 3))
        b[:] = [card, hl_rects, t_in, hl, ((W - card.width) // 2, y)]
        y += card.height + gap
    enc = subprocess.Popen([rk.FFMPEG, "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                            "-r", rk.FPS_STR, "-i", "-", "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le",
                            out], stdin=subprocess.PIPE)
    for i in range(rk.frames(dur)):
        t = i / rk.FPS
        fr = base.copy()
        for card, hl_rects, t_in, hl, (x, y0) in built:
            u = rk.ease_out((t - t_in) * rk.FPS / 18)
            if u <= 0:
                continue
            c = card
            if hl and t > hl[1]:  # yellow marker wipes left->right behind the phrase
                c = card.copy()
                tot = sum(r_[2] - r_[0] for r_ in hl_rects)
                done = tot * min(1.0, (t - hl[1]) / (hl[2] - hl[1]))
                for r_ in hl_rects:
                    wpx = int(min(r_[2] - r_[0], max(0, done)))
                    done -= r_[2] - r_[0]
                    if wpx <= 0:
                        continue
                    box = (r_[0], r_[1], r_[0] + wpx, r_[3])
                    reg = c.crop(box).convert("RGB")
                    c.paste(ImageChops.multiply(reg, Image.new("RGB", reg.size, YELLOW)), box[:2])
            sc = 0.6 + 0.4 * u
            cs = c.resize((max(1, round(c.width * sc)), max(1, round(c.height * sc))), Image.BICUBIC)
            px = x + (c.width - cs.width) // 2
            py = y0 + (c.height - cs.height) // 2 + int((1 - u) * (H - y0))
            if py < H:
                fr.alpha_composite(cs, (px, py)) if py + cs.height <= H else fr.alpha_composite(cs.crop((0, 0, cs.width, H - py)), (px, py))
        enc.stdin.write(fr.tobytes())
    enc.stdin.close()
    enc.wait()
    return out


# ---------------- cards ----------------
tw_net, ph_net = tweet("tw_musk_internet", "don’t have a connection at all!")
tw_olig, ph_olig = tweet("tw_musk_oligarchs", "This is a crime against the people of India!")
tw_boss, ph_boss = tweet("tw_musk_boss", "Is Ambani the real boss of India?")
tw_jai, ph_jai = tweet("tw_jairam", "orchestrated by")
tw_rah, ph_rah = tweet("tw_rahul", "Wait till you discover the other guy.")

WION_P = "Some Indian X users are cancelling their subscriptions"
wion, wion_r, _ = article("wion_cancel", ["h1", WION_P], "wion")


def para_card(stem, phrase, logo, header_h=150, h1_scale=0.6):
    """Card from para_shot.py captures (headline + one paragraph, each shot after scrolling to it, for pages that only
    paint on-screen text, e.g. Deccan Herald); returns (card, highlight rects of `phrase` in card px)."""
    h1 = Image.open(ART / f"{stem}_h1.png").convert("RGB")
    h1 = h1.resize((round(h1.width * h1_scale), round(h1.height * h1_scale)), Image.LANCZOS)   # DH's headline font is huge
    para = Image.open(ART / f"{stem}_para.png").convert("RGB")
    meta = json.loads((ART / f"{stem}_para.json").read_text())
    src = Image.new("RGB", (max(h1.width, para.width), h1.height + 40 + para.height), WHITE)
    src.paste(h1, (0, 0))
    src.paste(para, (0, h1.height + 40))
    card, mapr = stack_card(src, [(0, 0, h1.width, h1.height), (0, h1.height + 40, para.width, h1.height + 40 + para.height)],
                            header=logo_header(Image.open(LOGOS / f"{logo}.png"), h=header_h))
    oy = h1.height + 40
    return card, mapr([(r["x"], r["y"] + oy, r["x"] + r["w"], r["y"] + oy + r["h"]) for r in meta["phrases"][phrase]])


dhl, dhl_hl = para_card("dhp_licence", "Starlink is the third company to get a licence from the ministry", "deccanherald")
TH_P1 = "Bharti-backed OneWeb and Reliance Industries Ltd’s satellite internet arm are the other two companies"
TH_P2 = "security assessments for both operators are “currently under way”"
th, th_r, _ = article("th_dot", ["h1", TH_P1, TH_P2], "thehindu")
dhc, dhc_hl = para_card("dhp_congress", "orchestrated by none other than the PM himself", "deccanherald")
TP_P = "more than 6,000 kg (13,000 lb) of meth"
tp, tp_r, _ = article("tp_andaman", ["h1", TP_P], "theprint")
IT_P = "Security forces in Manipur have recovered Starlink internet devices"
itm, itm_r, _ = article("it_manipur", ["h1", IT_P], "indiatoday")

# ---------------- layout: split under every panel, full face in FULL, circle-PiP in PIP ----------------
FULL = {"1": [(3.95, 5.20), (36.08, 44.52)],
        "2": [(44.18, 49.56), (53.98, 62.88)],
        "3": [(8.16, 13.64), (21.20, 32.00)],
        "4": [(52.75, 54.20)]}
PIP = {"1": (21.66, 36.08)}

# ================= RAW 1 =================
bar("MUSK vs AMBANI", "1", 3.95, 5.20, "hook")
still_panel(tw_net, "1", 5.20, 11.20, "tw_internet", spread(ph_net["high-speed, affordable Internet connectivity"], 7.30, 9.30))
still_panel(tw_olig, "1", 11.20, 15.70, "tw_oligarchs", spread(ph_olig["we are being blocked by certain oligarchs"], 12.24, 14.70))
still_panel(tw_boss, "1", 15.70, 21.66, "tw_boss", spread(ph_boss["Is Ambani the real boss of India?"], 19.54, 21.50))

# Tweet war in the circle-PiP: the panel slides up first, ~0.5 s later the whole scene (host circle included) slides
# in from the left; Rahul's reply rises in as he is named, Musk's "Thank you, Rahul" on "full support", and the
# "other guy" line gets the marker as it is spoken. Exits right as the face goes full.
PIP_A, PIP_B = PIP["1"]
DELAY, IN_F, OUT_F = 0.50, 12, 9
p0, p1 = T("1", PIP_A + DELAY), T("1", PIP_B)
pip_mo = ((p0, -W, 0, 1, 1), (p0 + F(IN_F), 0, 0, 1, 1), (p1, 0, 0, 1, 1), (p1 + F(OUT_F), W, 0, 1, 1))
war = str(CLIPS / "pip_tweet_war.mov")
if not PANELS_ONLY:
    c0 = PIP_A + DELAY
    tweet_war(war, PIP_B - c0 + F(OUT_F) + 0.1, [
        ("tw_musk_boss", "Is Ambani the real boss of India?", 0.0, None),
        ("tw_rahul", "Wait till you discover the other guy.", 24.86 - c0, ("Wait till you discover the other guy.", 32.32 - c0, 35.90 - c0)),
        ("tw_musk_thanks", "This is indeed troubling.", 27.36 - c0, None),
    ])
pip_scale, pip_off = pip_face_motion(face_center=(590, 640))
items.append(Item("V12", RAWS[0], p0, p1 + F(OUT_F), src_in=PIP_A + DELAY, kind="video",
                  scale=pip_scale, offset=pip_off, motion=pip_mo, name="Face 1 (pip circle)"))
items.append(Item("V13", war, p0, p1 + F(OUT_F), kind="video", motion=pip_mo, name="PiP tweet war"))

bar("BUT HERE'S THE TWIST", "1", 42.64, 44.40, "twist")
still_panel(wion, "1", 44.52, 48.52, "wion_cancel", spread(wion_r(WION_P), 45.20, 47.90))
clip(BR / "ani_tiwari.mp4", 20.0, "1", 48.52, 51.75, "ani_tiwari")
tag("CONGRESS MP: 'I ENDORSE RAHUL GANDHI'", "1", 48.52, 51.75, "tiwari", delay=0.2)

# ================= RAW 2 =================
still_panel(dhl, "2", 2.55, 10.60, "dh_licence", spread(dhl_hl, 5.88, 10.44))
# 10.68-15.30 "space regulator se August 2025 me approval" -> FLAGGED: IN-SPACe approved Starlink on 9 July 2025,
# so the checklist pill carries no month.
pills("STARLINK IN INDIA", ["DoT licence · June 2025", "IN-SPACe approval · done", "Security clearance · PENDING"],
      [10.68, 11.68, 16.36], "2", 10.60, 18.52, "checklist")
still_panel(th, "2", 18.52, 28.28, "th_three", spread(th_r(TH_P1), 22.10, 25.80) + spread(th_r(TH_P2), 26.54, 27.95))
photo(Image.open(BR / "amb_it_0.jpg").convert("RGB"), "2", 28.28, 32.26, "ambani", focus=(0.5, 0.3))
tag("MUKESH AMBANI · RELIANCE (JIO)", "2", 28.28, 32.26, "ambani")
clip(BR / "ani_pemmasani.mp4", 8.0, "2", 32.26, 36.16, "ani_pemmasani", crop="724:422:300:40")
tag("MoS TELECOM: MHA DOING SECURITY CHECKS", "2", 32.26, 36.16, "pemmasani", delay=0.2)
# 36.16-44.18 "BYD ko US me ban karwa ke rakha hai" -> FLAGGED: US curbs on Chinese EVs are government tariffs/rules,
# not Musk's doing. Neutral photo + name tag only, no claim on screen.
photo(Image.open(BR / "byd.jpg").convert("RGB"), "2", 36.16, 44.18, "byd", focus=(0.5, 0.5))
tag("BYD · CHINA'S EV GIANT", "2", 38.58, 44.18, "byd", delay=0.3)
bar("PRESSURE TACTICS?", "2", 46.24, 49.40, "pressure")
clip(BR / "ani_madhav.mp4", 6.0, "2", 49.56, 53.98, "ani_madhav", focus=0.3)
tag("BJP: 'INDIA IS NOT A BANANA REPUBLIC'", "2", 49.56, 53.98, "madhav", delay=0.2)
# 53.98-62.75 "Rahul Gandhi ji jaise log... India ke against narrative" -> opinion, plain face

# ================= RAW 3 =================
photo(Image.open(BR / "rahul.jpg").convert("RGB"), "3", 2.20, 8.16, "rahul", focus=(0.5, 0.3))
tag("RAHUL GANDHI · LoP, LOK SABHA", "3", 2.20, 8.16, "rahul")
# 8.16-13.64 "main Ambani ko support nahi kar raha" -> opinion, plain face
still_panel(tw_rah, "3", 13.64, 21.20, "tw_rahul_1", spread(ph_rah["Wait till you discover the other guy."], 17.80, 20.38))
bar("BUSINESS LEADERS = SOFT POWER", "3", 27.86, 31.70, "softpower")
photo(Image.open(BR / "trump_musk2.jpg").convert("RGB"), "3", 32.00, 35.62, "trump_musk", focus=(0.5, 0.35))
tag("TRUMP & MUSK · WHITE HOUSE", "3", 32.00, 35.62, "trump_musk", delay=0.3)
still_panel(dhc, "3", 35.62, 38.64, "dh_congress", spread(dhc_hl, 36.28, 38.40))
still_panel(tw_rah, "3", 38.64, 41.02, "tw_rahul_2", spread(ph_rah["Welcome to India, Elon."], 39.10, 40.40))
# 44.20-47.30 "Andaman me, Punjab me, Manipur me": Andaman and Manipur are on record (ThePrint/Reuters, India Today);
# Punjab -> FLAGGED: no whitelisted report found, so it gets no pill.
pills("STARLINK DEVICES SEIZED", ["Andaman · 6,000 kg meth", "Manipur · with rifles & grenades"],
      [44.20, 46.48], "3", 41.02, 47.30, "seized")
still_panel(tp, "3", 47.30, 50.18, "tp_andaman", spread(tp_r(TP_P), 47.66, 49.60))
still_panel(itm, "3", 50.18, 52.12, "it_manipur", spread(itm_r(IT_P), 50.25, 51.95))
if not PANELS_ONLY:
    share = str(CLIPS / "share.mov")
    share_button(share, dur=1.20)
    add("V14", share, "4", 53.00, 54.20, kind="video", name="SHARE")

# ---------------- face + layout ----------------
WIN = []
for name, a, b in TAKES:
    pip = PIP.get(name)
    cuts = sorted({a, b, *[v for x, y in FULL[name] for v in (x, y)], *(pip or ())})
    for s0, e0 in zip(cuts, cuts[1:]):
        full = any(x <= s0 < y for x, y in FULL[name]) or (pip and pip[0] <= s0 < pip[1])
        if not full:
            WIN.append((T(name, s0), T(name, e0)))
        items.append(Item("V1", RAWS[RAWFILE[name]], T(name, s0), T(name, e0), kind="video", src_in=s0,
                          name=f"Face {name} ({'full' if full else 'split'})",
                          **({} if full else dict(offset=(0, FACE_SHIFT)))))
    items.append(Item("A1", RAWS[RAWFILE[name]], T(name, a), T(name, b), kind="audio", src_in=a, name=f"VO take {name}"))
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
