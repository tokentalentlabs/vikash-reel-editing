"""Reusable building blocks for 1080x1920 split-screen news reels (graphics, CCTV panels, preview, Premiere XML)."""
import json
import re
import subprocess
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
W, H = 1080, 1920
FPS = 30.0
FPS_STR = "30"
NTSC = False


def set_fps(fps):
    """Use 30 or 29.97 (pass 30000/1001) for the sequence, renders and XML."""
    global FPS, FPS_STR, NTSC
    NTSC = abs(fps - 30000 / 1001) < 1e-3
    FPS = 30000 / 1001 if NTSC else float(fps)
    FPS_STR = "30000/1001" if NTSC else str(int(fps))


TOP = 630            # top panel height
DIV = 8              # orange divider thickness
FACE_SHIFT = 470     # talking head moves down this much in split mode
BAR_Y_FULL = 1250    # hook-bar centre on a full-face shot (below the chin)
BAR_Y_SPLIT = 1610   # hook-bar centre in split mode: on the neck, never over the mouth (face is 470 px lower)

RED = (122, 20, 20)
ORANGE = (243, 154, 30)
PILL_ORANGE = (240, 122, 31)
YELLOW = (255, 216, 77)
CALLOUT_RED = (232, 30, 30)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

F_BLACK = "/System/Library/Fonts/Supplemental/Arial Black.ttf"
F_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


def font(path, size):
    return ImageFont.truetype(path, size)


def blank():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def frames(t):
    return int(round(t * FPS))


def src_frame(it, rec_f):
    """Source frame shown at timeline frame rec_f. The source-minus-timeline offset is rounded ONCE per item, so
    every piece of one take keeps the same offset (rounding src_in and rec_in separately slips a frame at each
    layout change when a trim point falls between frames - visible as a stutter and a 1-frame A/V drift)."""
    return max(0, int(round(round((it.src_in - it.rec_in) * FPS, 3))) + rec_f)  # inner round: float noise at half frames


# ---------- graphics ----------

def text_box(img, text, cx, cy, fnt, fg, bg, outline=None, pad=(44, 24), radius=10, outline_w=4):
    d = ImageDraw.Draw(img)
    l, t, r, b = d.textbbox((0, 0), text, font=fnt)
    tw, th = r - l, b - t
    x0, y0 = int(cx - tw / 2 - pad[0]), int(cy - th / 2 - pad[1])
    x1, y1 = int(cx + tw / 2 + pad[0]), int(cy + th / 2 + pad[1])
    d.rounded_rectangle([x0, y0, x1, y1], radius, fill=bg, outline=outline, width=outline_w if outline else 0)
    d.text((x0 + pad[0] - l, y0 + pad[1] - t), text, font=fnt, fill=fg)
    return (x0, y0, x1, y1)


def fit_font(text, path, size, max_w):
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    while size > 20:
        l, _, r, _ = d.textbbox((0, 0), text, font=font(path, size))
        if r - l <= max_w:
            break
        size -= 2
    return font(path, size)


def hook_bar(text, cy=BAR_Y_FULL, size=64):
    """Use cy=BAR_Y_SPLIT whenever the bar shows over a split-screen face."""
    img = blank()
    text_box(img, text, W / 2, cy, fit_font(text, F_BLACK, size, W - 140), WHITE, RED, outline=WHITE)
    return img


def name_tag(text, cy=TOP - 70, size=40):
    img = blank()
    text_box(img, text, W / 2, cy, fit_font(text, F_BLACK, size, W - 120), WHITE, RED, outline=WHITE, pad=(36, 18), radius=8)
    return img


def caption_label(text, cy=TOP - 70, size=44):
    img = blank()
    text_box(img, text, W / 2, cy, font(F_BLACK, size), BLACK, WHITE, pad=(40, 18), radius=14)
    return img


def divider():
    img = blank()
    ImageDraw.Draw(img).rectangle([0, TOP, W, TOP + DIV - 1], fill=ORANGE + (255,))
    return img


def panel_ff(panel):
    """Place a 1080xTOP panel image at the top of a transparent full frame."""
    img = blank()
    img.paste(panel.convert("RGB").resize((W, TOP)) if panel.size != (W, TOP) else panel.convert("RGB"), (0, 0))
    return img


def cover(img, w, h, focus=(0.5, 0.5)):
    """Scale-to-fill crop with a focus point (fractions)."""
    s = max(w / img.width, h / img.height)
    im = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    x = int(min(max(im.width * focus[0] - w / 2, 0), im.width - w))
    y = int(min(max(im.height * focus[1] - h / 2, 0), im.height - h))
    return im.crop((x, y, x + w, y + h))


def list_card(title, rows, n):
    """White top-panel card: yellow-highlighted title, then the first n of rows [(label, text)]."""
    img = Image.new("RGB", (W, TOP), WHITE)
    d = ImageDraw.Draw(img)
    fh = font(F_BLACK, 78)
    l, t, r, b = d.textbbox((0, 0), title, font=fh)
    d.rectangle([48, 40, 48 + (r - l) + 28, 40 + (b - t) + 26], fill=YELLOW)
    d.text((62 - l, 53 - t), title, font=fh, fill=BLACK)
    d.line([(48, 165), (W - 48, 165)], fill=(210, 210, 210), width=3)
    step = (TOP - 190) // max(len(rows), 1)
    size = 60 if len(rows) <= 2 else 50
    for i, (lab, txt) in enumerate(rows[:n]):
        y = 190 + i * step
        d.text((52, y), lab, font=font(F_BOLD, 30), fill=PILL_ORANGE)
        ft = font(F_BLACK, size)
        l, t, r, b = d.textbbox((0, 0), txt, font=ft)
        d.rectangle([46, y + 42, 46 + (r - l) + 16, y + 42 + (b - t) + 20], fill=YELLOW)
        d.text((54 - l, y + 52 - t), txt, font=ft, fill=BLACK)
    return img


def person_card(photo, name, title):
    """Reference-style ID card: rounded photo on white with an orange name pill and a title line."""
    img = Image.new("RGB", (W, TOP), WHITE)
    ph = cover(photo, 400, 410, focus=(0.5, 0.35))
    mask = Image.new("L", ph.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, ph.width - 1, ph.height - 1], 36, fill=255)
    img.paste(ph, ((W - ph.width) // 2, 28), mask)
    d = ImageDraw.Draw(img)
    fn, ft = font(F_BLACK, 46), font(F_BOLD, 30)
    l, t, r, b = d.textbbox((0, 0), name, font=fn)
    tl, tt, tr, tb = d.textbbox((0, 0), title, font=ft)
    w = max(r - l, tr - tl) + 80
    x0, y0 = (W - w) // 2, 452
    d.rounded_rectangle([x0, y0, x0 + w, y0 + 140], 22, fill=PILL_ORANGE)
    d.text(((W - (r - l)) // 2 - l, y0 + 22 - t), name, font=fn, fill=WHITE)
    d.text(((W - (tr - tl)) // 2 - tl, y0 + 90 - tt), title, font=ft, fill=WHITE)
    return img


def text_rows(img, box, light_text=False, min_gap=4):
    """Bounding boxes of text lines inside box (x0,y0,x1,y1), found from pixel contrast."""
    g = np.asarray(img.convert("L").crop(box), dtype=np.int16)
    ink = (g > 170) if light_text else (g < 110)
    rows = ink.sum(axis=1) > 2
    out, start = [], None
    for y, on in enumerate(list(rows) + [False]):
        if on and start is None:
            start = y
        elif not on and start is not None:
            if y - start >= min_gap:
                cols = np.where(ink[start:y].any(axis=0))[0]
                out.append((box[0] + cols[0], box[1] + start, box[0] + cols[-1] + 1, box[1] + y))
            start = None
    return out


# ---------- article screenshots ----------

@dataclass
class Article:
    stem: Path
    masthead_px: int
    masthead_top: int = 0
    img: Image.Image = field(init=False)
    meta: dict = field(init=False)

    def __post_init__(self):
        self.img = Image.open(f"{self.stem}.png").convert("RGB")
        self.meta = json.loads(Path(f"{self.stem}.json").read_text())
        self.dpr = self.meta["dpr"]

    def rects(self, css_rects):
        return [(r["x"] * self.dpr, r["y"] * self.dpr, (r["x"] + r["w"]) * self.dpr, (r["y"] + r["h"]) * self.dpr) for r in css_rects]

    def headline_block(self, pad=26):
        """Masthead strip + headline stacked. Returns (image, headline line rects in block coords)."""
        lines = self.rects(self.meta["h1"]["lines"])
        top = int(min(r[1] for r in lines) - pad)
        bot = int(max(r[3] for r in lines) + pad)
        mh = self.masthead_px - self.masthead_top
        block = Image.new("RGB", (self.img.width, mh + (bot - top)), WHITE)
        block.paste(self.img.crop((0, self.masthead_top, self.img.width, self.masthead_px)), (0, 0))
        block.paste(self.img.crop((0, top, self.img.width, bot)), (0, mh))
        shifted = [(x0, y0 - top + mh, x1, y1 - top + mh) for x0, y0, x1, y1 in lines]
        return block, shifted

    def bg(self):
        m = re.findall(r"[\d.]+", self.meta.get("bg") or "")
        if len(m) >= 3 and (len(m) < 4 or float(m[3]) > 0):
            return tuple(int(float(v)) for v in m[:3])
        y = int(self.meta["h1"]["lines"][0]["y"] * self.dpr)
        return self.img.getpixel((3, y))

    def card(self, logo=None, logo_h=96, pad=14, gap=22, max_blocks=6):
        """Complete, clean top-panel card (reference-channel style): outlet logo on a header band, then the
        headline, the subheading and the first body paragraphs - each cropped straight from the page and stacked,
        so bylines, photos, ads and share rows in between are dropped. Fills the panel and stops on a complete
        line of text. Background is the page's own colour.
        Returns (panel, rects) where rects has "h1", "lead", "blocks" (list per paragraph) and "phrases"
        (dict), all in panel coordinates."""
        bg = self.bg()
        h1 = self.rects(self.meta["h1"]["lines"])
        blocks = [self.rects(bk["lines"]) for bk in (self.meta.get("blocks") or [])][:max_blocks]
        blocks = [bl for bl in blocks if bl]
        if not blocks and self.meta.get("lead"):
            blocks = [self.rects(self.meta["lead"]["lines"])]
        allr = h1 + [r for bl in blocks[:3] for r in bl]
        cx0 = max(0, int(min(r[0] for r in allr)) - 36)
        cx1 = min(self.img.width, int(max(r[2] for r in allr)) + 36)
        full_width = self.meta.get("css_width", 412) <= 600  # mobile capture: single column, use the full width
        if full_width:
            cx0, cx1 = 0, self.img.width
        s = W / (cx1 - cx0)
        if logo is None and self.meta.get("logo"):
            lb = self.meta["logo"]
            logo = self.img.crop((int(lb["x"] * self.dpr) - 4, int(lb["y"] * self.dpr) - 4,
                                  int((lb["x"] + lb["w"]) * self.dpr) + 4, int((lb["y"] + lb["h"]) * self.dpr) + 4))
        header = Image.new("RGB", (W, logo_h + 44), bg)
        if logo is not None:
            logo = logo.convert("RGB")
            band = logo.getpixel((1, logo.height // 2))
            if sum(abs(x - y) for x, y in zip(band, bg)) > 60:
                header = Image.new("RGB", header.size, band)
            k = min(logo_h / logo.height, 640 / logo.width)
            logo = logo.resize((round(logo.width * k), round(logo.height * k)), Image.LANCZOS)
            header.paste(logo, ((W - logo.width) // 2, (header.height - logo.height) // 2))
        panel = Image.new("RGB", (W, TOP), bg)
        panel.paste(header, (0, 0))
        y = header.height
        dark_bg = sum(bg) / 3 < 110
        placed = []
        segs = [h1] + blocks
        margin = 44
        for i, rs in enumerate(segs):
            a = int(min(r[1] for r in rs) - pad)
            b = int(max(r[3] for r in rs) + pad)
            if placed and a < placed[-1][1]:  # touches/overlaps the previous segment
                if b <= placed[-1][1]:
                    continue
                a = placed[-1][1]
            if full_width:
                sx0, sx1, ss, px = cx0, cx1, s, 0
            else:  # desktop: crop this segment's own text column and scale it to fill the card width
                sx0 = max(0, int(min(r[0] for r in rs)) - 10)
                sx1 = min(self.img.width, int(max(r[2] for r in rs)) + 10)
                ss = min((W - 2 * margin) / (sx1 - sx0), 1.6)
                px = margin
            gap_px = 0 if not placed else round(gap * (0.6 if i == 1 else 1.0) * ss)
            room = TOP - y - gap_px
            if room < 40:
                break
            end = min(b, a + int(room / ss))
            if end < b:
                if len(placed) >= 2:  # later paragraphs are shown whole or not at all
                    break
                rows = [r for r in text_rows(self.img, (sx0, a, sx1, end), light_text=dark_bg) if r[3] < end - 2]
                if not rows:
                    break
                end = min(rows[-1][3] + pad, end)
            y += gap_px
            crop = self.img.crop((sx0, a, sx1, end))
            crop = crop.resize((round(crop.width * ss), round(crop.height * ss)), Image.LANCZOS)
            panel.paste(crop, (px, y))
            placed.append((a, end, y, sx0, ss, px))
            y += crop.height
            if end < b:
                break
        if placed and not full_width:  # centre the stacked content vertically in the space under the logo
            shift = max(0, (TOP - y) // 2)
            if shift:
                body = panel.crop((0, header.height, W, y))
                panel.paste(Image.new("RGB", (W, TOP - header.height), bg), (0, header.height))
                panel.paste(body, (0, header.height + shift))
                placed = [(a, e, py + shift, sx, sc, pxx) for a, e, py, sx, sc, pxx in placed]

        def mapr(rs):
            out = []
            for x0, y0, x1, y1 in rs:
                for a, b, py, sx, sc, pxx in placed:
                    if a <= y0 and y1 <= b:
                        out.append(((x0 - sx) * sc + pxx, (y0 - a) * sc + py, (x1 - sx) * sc + pxx, (y1 - a) * sc + py))
                        break
            return out
        rects = {"h1": mapr(h1), "blocks": [mapr(bl) for bl in blocks],
                 "phrases": {k: mapr(self.rects(v)) for k, v in (self.meta.get("phrases") or {}).items()}}
        rects["lead"] = rects["blocks"][0] if rects["blocks"] else []
        return panel, rects

    def lead_image(self):
        li = self.meta["lead_image"]
        box = [li["x"] * self.dpr, li["y"] * self.dpr, (li["x"] + li["w"]) * self.dpr, (li["y"] + li["h"]) * self.dpr]
        return self.img.crop(tuple(int(v) for v in box))


def pill_layers(rows, title=None, fill=(204, 16, 16)):
    """Red rounded pills stacked in the top panel (editor style), one layer per row so each can slide in from the
    right as it's spoken. Returns (white base panel, [full-frame RGBA layer per pill])."""
    base = Image.new("RGB", (W, TOP), WHITE)
    fnt = font(F_BOLD, 58)
    d = ImageDraw.Draw(base)
    y = 40
    if title:
        ft = font(F_BLACK, 56)
        l, t_, r, b_ = d.textbbox((0, 0), title, font=ft)
        d.rectangle([(W - (r - l)) // 2 - 14, y - 6, (W + (r - l)) // 2 + 14, y + (b_ - t_) + 16], fill=YELLOW)
        d.text(((W - (r - l)) // 2 - l, y + 5 - t_), title, font=ft, fill=BLACK)
        y += (b_ - t_) + 50
    step = (TOP - y - 20) // max(len(rows), 1)
    layers = []
    for i, text in enumerate(rows):
        im = blank()
        f = fit_font(text, F_BOLD, 58, W - 200)
        text_box(im, text, W / 2, y + step * i + step / 2, f, WHITE, fill, pad=(48, 22), radius=16)
        layers.append(im)
    return base, layers


def pill_motion(a):
    """Pill entrance: slide in from the right, ease-out, 9 f."""
    return ((a, W, 0, 1, 1), (a + F(9), 0, 0, 1, 1))


def logo_header(logo, bg=WHITE, h=110, max_w=520):
    """W-wide header band with the outlet logo centred (band colour = the logo's own background)."""
    logo = logo.convert("RGB")
    band = logo.getpixel((2, logo.height // 2))
    k = min((h - 30) / logo.height, max_w / logo.width)
    logo = logo.resize((round(logo.width * k), round(logo.height * k)), Image.LANCZOS)
    img = Image.new("RGB", (W, h), band if sum(abs(a - b) for a, b in zip(band, bg)) > 60 else bg)
    img.paste(logo, ((W - logo.width) // 2, (h - logo.height) // 2))
    return img


def stack_card(src, parts, header=None, bg=WHITE, gap=26, margin=44, max_scale=1.6, bottom_pad=26):
    """Top-panel card stacked from crops of one page screenshot (headline, subheading, chosen paragraphs). Each part
    is scaled to the card's text width (so small body text reads as well as the headline), then everything shrinks
    together if needed to fit, and is centred under the logo header. parts = [(x0, y0, x1, y1)] in screenshot px,
    each a whole block of text so no line is ever sliced. Returns (panel, mapr) where mapr(rects in screenshot px)
    -> rects in panel px (rects outside every part are dropped)."""
    crops = [src.crop(tuple(int(v) for v in p)) for p in parts]
    hh = header.height if header is not None else 0
    scales = [min(max_scale, (W - 2 * margin) / c.width) for c in crops]
    room = TOP - hh - bottom_pad - 16 - gap * (len(crops) - 1)
    k = min(1.0, room / sum(c.height * sc for c, sc in zip(crops, scales)))
    scales = [sc * k for sc in scales]
    total = sum(round(c.height * sc) for c, sc in zip(crops, scales)) + gap * (len(crops) - 1)
    panel = Image.new("RGB", (W, TOP), bg)
    if header is not None:
        panel.paste(header, (0, 0))
    y = hh + 16 + max(0, (TOP - hh - bottom_pad - 16 - total) // 2)
    placed = []
    for p, c, sc in zip(parts, crops, scales):
        c2 = c.resize((round(c.width * sc), round(c.height * sc)), Image.LANCZOS)
        x0 = (W - c2.width) // 2
        panel.paste(c2, (x0, y))
        placed.append((p, x0, y, sc))
        y += c2.height + gap

    def mapr(rects):
        out = []
        for rx0, ry0, rx1, ry1 in rects:
            for (px0, py0, px1, py1), x0, py, sc in placed:
                if px0 - 2 <= rx0 and rx1 <= px1 + 2 and py0 - 2 <= ry0 and ry1 <= py1 + 2:
                    out.append(((rx0 - px0) * sc + x0, (ry0 - py0) * sc + py, (rx1 - px0) * sc + x0, (ry1 - py0) * sc + py))
                    break
        return out
    return panel, mapr


def tweet_panel(stem, cut=None, matte=(232, 237, 241), max_w=1000, max_h=590):
    """Top panel with a tweet card (from tools/tweet_shot.py) centred on a light matte. The card is cut above its
    likes/replies footer (or at cut, px) and given a fresh rounded border. Returns (panel, phrase rects dict)."""
    im = Image.open(f"{stem}.png").convert("RGB")
    meta = json.loads(Path(f"{stem}.json").read_text())
    if cut is None:  # the grey rule between the date row and the footer
        g = np.asarray(im.convert("L"), dtype=np.int16)
        x0, x1 = im.width // 10, im.width * 9 // 10
        rule = [y for y in range(im.height // 3, im.height - 4)
                if 200 <= g[y, x0:x1].mean() <= 240 and g[y, x0:x1].std() < 6 and g[y - 3, x0:x1].mean() > 248]
        cut = rule[0] if rule else im.height
    inset = 6
    body = im.crop((inset, inset, im.width - inset, cut))
    s = min(max_w / body.width, max_h / body.height)
    body = body.resize((round(body.width * s), round(body.height * s)), Image.LANCZOS)
    panel = Image.new("RGB", (W, TOP), matte)
    cx, cy = (W - body.width) // 2, (TOP - body.height) // 2
    card = Image.new("RGB", (body.width + 24, body.height + 24), WHITE)
    card.paste(body, (12, 12))
    mask = Image.new("L", card.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, card.width - 1, card.height - 1], 26, fill=255)
    panel.paste(card, (cx - 12, cy - 12), mask)
    ImageDraw.Draw(panel).rounded_rectangle([cx - 12, cy - 12, cx + body.width + 11, cy + body.height + 11], 26,
                                            outline=(207, 217, 222), width=3)
    phrases = {k: [((r["x"] - inset) * s + cx, (r["y"] - inset) * s + cy, (r["x"] + r["w"] - inset) * s + cx,
                    (r["y"] + r["h"] - inset) * s + cy) for r in v if r["y"] + r["h"] <= cut]
               for k, v in meta["phrases"].items()}
    return panel, phrases


def fit_block(block, rects, box_w, box_h, bg=WHITE, valign="top"):
    s = min(box_w / block.width, box_h / block.height, 1.0)
    b = block.resize((round(block.width * s), round(block.height * s)), Image.LANCZOS)
    canvas = Image.new("RGB", (box_w, box_h), bg)
    ox = (box_w - b.width) // 2
    oy = 0 if valign == "top" else (box_h - b.height) // 2
    canvas.paste(b, (ox, oy))
    return canvas, [(x0 * s + ox, y0 * s + oy, x1 * s + ox, y1 * s + oy) for x0, y0, x1, y1 in rects]


def highlight_layer(base_ff, rect, mode, pad=(14, 6)):
    """Full-frame RGBA containing only the highlighted version of one text line."""
    x0, y0, x1, y1 = int(rect[0] - pad[0]), int(rect[1] - pad[1]), int(rect[2] + pad[0]), int(rect[3] + pad[1])
    region = base_ff.convert("RGB").crop((x0, y0, x1, y1))
    if mode == "black":
        region = ImageChops.invert(region)
    elif mode == "yellow_dark":  # light text on a dark page -> black text on a yellow marker
        ink = region.convert("L").point(lambda v: 255 if v > 128 else 0)
        region = Image.composite(Image.new("RGB", region.size, BLACK), Image.new("RGB", region.size, YELLOW), ink)
    else:
        region = ImageChops.multiply(region, Image.new("RGB", region.size, YELLOW))
    out = blank()
    out.paste(region, (x0, y0))
    return out, (x0, x1)


def floating_card(block, rects, width=940, top=1180, border=5):
    s = width / block.width
    b = block.resize((width, round(block.height * s)), Image.LANCZOS)
    x = (W - width) // 2
    out = blank()
    shadow = Image.new("RGBA", (width + 60, b.height + 60), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rectangle([30, 36, width + 30, b.height + 36], fill=(0, 0, 0, 150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    out.alpha_composite(shadow, (x - 30, top - 30))
    framed = Image.new("RGB", (width + 2 * border, b.height + 2 * border), BLACK)
    framed.paste(b, (border, border))
    out.paste(framed, (x - border, top - border))
    return out, [(x0 * s + x, y0 * s + top, x1 * s + x, y1 * s + top) for x0, y0, x1, y1 in rects]


# ---------- CCTV-style panel with tracked callouts ----------

def interp_track(track, t):
    ks = sorted(track)
    if t <= ks[0]:
        return track[ks[0]]
    if t >= ks[-1]:
        return track[ks[-1]]
    for a, b in zip(ks, ks[1:]):
        if a <= t <= b:
            u = (t - a) / (b - a)
            return tuple(track[a][i] + (track[b][i] - track[a][i]) * u for i in range(2))


def ease(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


def ease_out(u):
    u = min(max(u, 0.0), 1.0)
    return 1 - (1 - u) ** 3


def motion_at(it, t):
    """(dx, dy, scale_mul, opacity) of an item at timeline time t (ease-out between keyframes)."""
    if not it.motion:
        return 0.0, 0.0, 1.0, 1.0
    ks = it.motion
    if t <= ks[0][0]:
        return tuple(ks[0][1:])
    for k0, k1 in zip(ks, ks[1:]):
        if t <= k1[0]:
            u = ease_out((t - k0[0]) / max(k1[0] - k0[0], 1e-6))
            return tuple(a + (b - a) * u for a, b in zip(k0[1:], k1[1:]))
    return tuple(ks[-1][1:])


# ---------- animation presets (ANIMATION.md) ----------
F = lambda n: n / FPS  # noqa: E731  frames -> seconds
PUSH_F, ENTER_F, EXIT_F = 9, 9, 12


def bar_motion(a, b):
    """Hook/text bar: fade + rise in 4 f, slow upward drift, fade out 3 f."""
    return ((a, 0, 24, 1, 0), (a + F(4), 0, 0, 1, 1), (b - F(3), 0, -14, 1, 1), (b, 0, -16, 1, 0))


def tag_motion(a, b, delay=0.5):
    """Name bar on a photo: arrives ~0.5 s after the photo, sliding up from the panel edge."""
    return ((a + delay, 0, 40, 1, 0), (a + delay + F(6), 0, 0, 1, 1), (b, 0, 0, 1, 1))


def animate_layout(items, split_windows, tracks=("V2", "V3", "V4", "V5", "V6", "V7", "V8", "V9"), divider="V10"):
    """Give every split window the editors' moves (ANIMATION.md section 1-2):
    - window start (from full face): panel group + divider slide down from above, face slides down to split (ENTER_F)
    - panel -> panel inside a window: push left (old group extended PUSH_F and moved -W, new group moved in from +W)
    - window end (to full face): panel group + divider slide up and out (EXIT_F) while the face glides up to full.
    Panel items use track "P" (base) and "H0".."H2" (highlights) plus a group id; groups alternate between two track
    sets so the pushes can overlap. split_windows are timeline-time (a, b) pairs."""
    import dataclasses
    groups = {}
    for it in items:
        if it.group:
            groups.setdefault(it.group, []).append(it)
    order = sorted(groups, key=lambda g: min(i.rec_in for i in groups[g]))
    out = [it for it in items if not it.group]
    up = -(TOP + DIV + 4)
    for a, b in split_windows:
        gs = [g for g in order if a - 1e-3 <= min(i.rec_in for i in groups[g]) < b - 1e-3]
        for k, g in enumerate(gs):
            g0 = min(i.rec_in for i in groups[g])
            g1 = max(i.rec_out for i in groups[g])
            first, last = k == 0, k == len(gs) - 1
            for it in groups[g]:
                base = 0 if it.track == "P" else 1 + int(it.track[1:])
                trk = tracks[(k % 2) * 4 + base]
                ks = list(it.motion or [])  # own entrance (e.g. a pill sliding in) is kept
                if it.rec_in > g0 + 1e-3:
                    pass
                elif first:
                    ks += [(g0, 0, up, 1, 1), (g0 + F(ENTER_F), 0, 0, 1, 1)]
                else:
                    ks += [(g0, W, 0, 1, 1), (g0 + F(PUSH_F), 0, 0, 1, 1)]
                if not ks:
                    ks = [(it.rec_in, 0, 0, 1, 1)]
                end = g1
                if last:
                    ks += [(g1, 0, 0, 1, 1), (g1 + F(EXIT_F), 0, up, 1, 1)]
                    end = g1 + F(EXIT_F)
                else:
                    ks += [(g1, 0, 0, 1, 1), (g1 + F(PUSH_F), -W, 0, 1, 1)]
                    end = g1 + F(PUSH_F)
                rec_out = end if it.rec_out >= g1 - 1e-3 else it.rec_out
                ks = sorted({round(k_[0], 4): k_ for k_ in ks if it.rec_in - 1e-3 <= k_[0] <= rec_out + 1e-3}.values())
                out.append(dataclasses.replace(it, track=trk, rec_out=rec_out, motion=tuple(ks) if ks else None))
    res = []  # face clips glide between full and split on the window edges
    for it in out:
        if it.track == "V1" and it.kind == "video":
            from_pip = any(o.track == "V1" and o.scale != 100 and abs(o.rec_out - it.rec_in) < 1e-3 for o in out)
            if from_pip:  # the editors hard-cut out of the circle-PiP scene
                pass
            elif it.offset == (0, FACE_SHIFT) and any(abs(it.rec_in - a) < 1e-3 for a, _ in split_windows):
                it = dataclasses.replace(it, motion=((it.rec_in, 0, -FACE_SHIFT, 1, 1), (it.rec_in + F(ENTER_F), 0, 0, 1, 1)))
            elif it.offset == (0, 0) and it.scale == 100 and any(abs(it.rec_in - b) < 1e-3 for _, b in split_windows):
                it = dataclasses.replace(it, motion=((it.rec_in, 0, FACE_SHIFT, 1, 1), (it.rec_in + F(EXIT_F), 0, 0, 1, 1)))
        if it.track == "D":
            it = dataclasses.replace(it, track=divider, rec_out=it.rec_out + F(EXIT_F),
                                     motion=((it.rec_in, 0, up, 1, 1), (it.rec_in + F(ENTER_F), 0, 0, 1, 1),
                                             (it.rec_out, 0, 0, 1, 1), (it.rec_out + F(EXIT_F), 0, up, 1, 1)))
        res.append(it)
    return res


def draw_callout(img, cx, cy, r, grow):
    d = ImageDraw.Draw(img)
    r = r * (1.35 - 0.35 * grow)
    for k, w in ((0, 9), (3, 5)):
        d.ellipse([cx - r - k, cy - r * 0.92 + k, cx + r + k, cy + r * 0.92 - k], outline=CALLOUT_RED, width=w)
    # arrow from upper-left pointing at the circle
    ang = np.deg2rad(40)
    tip = (cx - (r + 10) * np.cos(ang), cy - (r + 10) * np.sin(ang))
    length = 150
    tail = (tip[0] - length * np.cos(ang), tip[1] - length * np.sin(ang))
    if tail[1] < 8:
        tail = (tail[0], 8)
    d.line([tail, tip], fill=CALLOUT_RED, width=14)
    ux, uy = np.cos(ang), np.sin(ang)
    px, py = -uy, ux
    head = [(tip[0] + ux * 6, tip[1] + uy * 6),
            (tip[0] - ux * 40 + px * 26, tip[1] - uy * 40 + py * 26),
            (tip[0] - ux * 40 - px * 26, tip[1] - uy * 40 - py * 26)]
    d.polygon(head, fill=CALLOUT_RED)


def render_panel_clip(src, out, t0, t1, framing, callouts=(), size=(W, TOP), crf=14):
    """framing(t) -> (scale, (cx, cy)) in source px; callouts: dicts with t0,t1,track{t:(x,y)},r (source px)."""
    probe = subprocess.run([FFMPEG, "-hide_banner", "-i", src], capture_output=True, text=True).stderr
    sw, sh = map(int, re.search(r"Video:.*?(\d{3,4})x(\d{3,4})", probe).groups())
    dec = subprocess.Popen([FFMPEG, "-loglevel", "error", "-ss", f"{t0:.3f}", "-i", src, "-t", f"{t1 - t0:.3f}",
                            "-vf", f"fps={FPS_STR}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen([FFMPEG, "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{size[0]}x{size[1]}",
                            "-r", FPS_STR, "-i", "-", "-c:v", "libx264", "-crf", str(crf), "-preset", "medium",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    n = frames(t1 - t0)
    fsz = sw * sh * 3
    last = None
    for i in range(n):
        buf = dec.stdout.read(fsz)
        if len(buf) == fsz:
            last = Image.frombytes("RGB", (sw, sh), buf)
        t = t0 + i / FPS
        s, (cx, cy) = framing(t)
        a = 1 / s
        im = last.transform(size, Image.AFFINE, (a, 0, cx - size[0] / 2 * a, 0, a, cy - size[1] / 2 * a), Image.BICUBIC)
        for c in callouts:
            if c["t0"] <= t < c["t1"]:
                x, y = interp_track(c["track"], t)
                grow = ease((t - c["t0"]) / 0.2)
                draw_callout(im, size[0] / 2 + (x - cx) * s, size[1] / 2 + (y - cy) * s, c["r"] * s, grow)
        enc.stdin.write(im.tobytes())
    enc.stdin.close()
    enc.wait()
    dec.kill()
    return out


# ---------- edit decision list ----------

@dataclass
class Item:
    track: str               # V1..V7 or A1
    path: str
    rec_in: float            # seconds on the timeline
    rec_out: float
    src_in: float = 0.0      # seconds into the source
    kind: str = "still"      # still | video | audio
    scale: float = 100.0
    offset: tuple = (0, 0)   # px offset of the clip centre from frame centre
    wipe: tuple = None       # (t_start, t_end, x_start_px, x_end_px) reveal left->right, times on the timeline
    name: str = ""
    motion: tuple = None     # keyframes ((t_timeline, dx, dy, scale_mul, opacity), ...) on top of offset/scale; ease-out
    group: str = ""          # panel group id (a panel base + its highlights move together)


def keep_ranges(silences, start, end, min_gap=0.28, keep_pad=0.07):
    """Speech ranges after removing pauses longer than min_gap (each pause keeps keep_pad on both sides)."""
    ranges, cur = [], start
    for s, e in silences:
        if e - s < min_gap or e <= start or s >= end:
            continue
        cut0, cut1 = max(s + keep_pad, start), min(e - keep_pad, end)
        if cut0 > cur:
            ranges.append((cur, cut0))
        cur = max(cur, cut1)
    if cur < end:
        ranges.append((cur, end))
    return ranges


class Timeline:
    def __init__(self, ranges):
        self.ranges = ranges
        self.starts = []
        t = 0.0
        for a, b in ranges:
            self.starts.append(t)
            t += b - a
        self.duration = t

    def rec(self, raw_t):
        """Map a raw-source time to timeline time (times inside a removed pause snap to the next kept range)."""
        for (a, b), s in zip(self.ranges, self.starts):
            if raw_t < a:
                return s
            if raw_t <= b:
                return s + raw_t - a
        return self.duration


def detect_silences(path, noise="-32dB", d=0.28):
    err = subprocess.run([FFMPEG, "-hide_banner", "-i", path, "-af", f"highpass=f=80,silencedetect=noise={noise}:d={d}",
                          "-vn", "-f", "null", "-"], capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    return list(zip(starts, ends))


# ---------- preview render (half resolution) ----------

def render_preview(items, raw_path, ranges, out, duration, scale=0.5):
    pw, ph = int(W * scale), int(H * scale)
    tl = Timeline(ranges)
    stills, clips = {}, {}

    def still(path):
        if path not in stills:
            stills[path] = Image.open(path).convert("RGBA").resize((pw, ph), Image.LANCZOS)
        return stills[path]

    def clip_frames(path):
        if path not in clips:
            probe = subprocess.run([FFMPEG, "-hide_banner", "-i", path], capture_output=True, text=True).stderr
            cw, ch = map(int, re.search(r"Video:.*?(\d{3,4})x(\d{3,4})", probe).groups())
            w2, h2 = int(cw * scale), int(ch * scale)
            raw = subprocess.run([FFMPEG, "-loglevel", "error", "-i", path, "-vf", f"fps={FPS_STR},scale={w2}:{h2}", "-f", "rawvideo",
                                  "-pix_fmt", "rgba", "-"], capture_output=True).stdout
            n = len(raw) // (w2 * h2 * 4)
            clips[path] = [Image.frombytes("RGBA", (w2, h2), raw[i * w2 * h2 * 4:(i + 1) * w2 * h2 * 4]) for i in range(n)]
        return clips[path]

    dec = subprocess.Popen([FFMPEG, "-loglevel", "error", "-i", raw_path, "-vf", f"fps={FPS_STR},scale={pw}:{ph}",
                            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    raw_idx, raw_frame = -1, None
    fsz = pw * ph * 3

    af = ";".join(f"[1:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS[a{i}]" for i, (a, b) in enumerate(ranges))
    af += ";" + "".join(f"[a{i}]" for i in range(len(ranges))) + f"concat=n={len(ranges)}:v=0:a=1[aout]"
    enc = subprocess.Popen([FFMPEG, "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{pw}x{ph}",
                            "-r", FPS_STR, "-i", "-", "-i", raw_path, "-filter_complex", af, "-map", "0:v", "-map", "[aout]",
                            "-c:v", "libx264", "-crf", "20", "-preset", "fast", "-pix_fmt", "yuv420p", "-c:a", "aac",
                            "-b:a", "160k", "-shortest", out], stdin=subprocess.PIPE)
    order = sorted({i.track for i in items if i.track.startswith("V")}, key=lambda s: int(s[1:]))
    for f in range(frames(duration)):
        t = f / FPS
        canvas = Image.new("RGBA", (pw, ph), (0, 0, 0, 255))
        for tr in order:
            for it in items:
                if it.track != tr or not (it.rec_in <= t < it.rec_out):
                    continue
                if it.kind == "video" and it.path == raw_path:
                    want = src_frame(it, f)
                    while raw_idx < want:
                        buf = dec.stdout.read(fsz)
                        if len(buf) < fsz:
                            break
                        raw_frame, raw_idx = Image.frombytes("RGB", (pw, ph), buf), raw_idx + 1
                    layer = raw_frame.convert("RGBA")
                elif it.kind == "video":
                    fr = clip_frames(it.path)
                    layer = fr[min(src_frame(it, f), len(fr) - 1)]
                else:
                    layer = still(it.path)
                mdx, mdy, mms, mop = motion_at(it, t)
                if it.scale != 100 or mms != 1:
                    s = it.scale / 100 * mms
                    layer = layer.resize((int(layer.width * s), int(layer.height * s)), Image.LANCZOS)
                if it.wipe:
                    ws, we, xs, xe = it.wipe
                    x = (xs + (xe - xs) * ease((t - ws) / max(we - ws, 1e-6))) * scale if t >= ws else xs * scale
                    layer = layer.copy()
                    a = layer.getchannel("A")
                    ImageDraw.Draw(a).rectangle([int(x), 0, layer.width, layer.height], fill=0)
                    layer.putalpha(a)
                if mop < 1:
                    layer = layer.copy()
                    layer.putalpha(layer.getchannel("A").point(lambda v: int(v * mop)))
                ox = int((pw - layer.width) / 2 + (it.offset[0] + mdx) * scale)
                oy = int((ph - layer.height) / 2 + (it.offset[1] + mdy) * scale)
                sx0, sy0 = max(-ox, 0), max(-oy, 0)
                sx1, sy1 = min(layer.width, pw - ox), min(layer.height, ph - oy)
                if sx1 > sx0 and sy1 > sy0:
                    canvas.alpha_composite(layer.crop((sx0, sy0, sx1, sy1)), (ox + sx0, oy + sy0))
        enc.stdin.write(canvas.convert("RGB").tobytes())
    enc.stdin.close()
    enc.wait()
    dec.kill()
    return out


# ---------- Premiere-compatible FCP7 XML ----------

def _rate():
    return f"<rate><timebase>{round(FPS)}</timebase><ntsc>{'TRUE' if NTSC else 'FALSE'}</ntsc></rate>"


def _media_info(path):
    probe = subprocess.run([FFMPEG, "-hide_banner", "-i", path], capture_output=True, text=True).stderr
    m = re.search(r"Video:.*?(\d{3,4})x(\d{3,4})", probe)
    dur = re.search(r"Duration: (\d+):(\d+):([\d.]+)", probe)
    secs = int(dur.group(1)) * 3600 + int(dur.group(2)) * 60 + float(dur.group(3)) if dur else None
    return (int(m.group(1)), int(m.group(2))) if m else (W, H), secs, "Audio:" in probe


def export_xml(items, seq_name, out, duration):
    from xml.sax.saxutils import escape
    files, fid = {}, 0
    tracks = {}
    for it in items:
        tracks.setdefault(it.track, []).append(it)

    def file_el(path, kind):
        nonlocal fid
        path = str(Path(path).resolve())
        if path in files:
            return f'<file id="{files[path]}"/>'
        fid += 1
        files[path] = f"file-{fid}"
        (w, h), secs, has_audio = _media_info(path)
        dur = frames(secs) if (secs and kind != "still") else frames(3600)
        url = "file://localhost" + urllib.parse.quote(path)
        vid = f"<video><samplecharacteristics>{_rate()}<width>{w}</width><height>{h}</height><anamorphic>FALSE</anamorphic><pixelaspectratio>square</pixelaspectratio><fielddominance>none</fielddominance></samplecharacteristics></video>"
        aud = "<audio><samplecharacteristics><depth>16</depth><samplerate>48000</samplerate></samplecharacteristics><channelcount>2</channelcount></audio>" if has_audio else ""
        return (f'<file id="{files[path]}"><name>{escape(Path(path).name)}</name><pathurl>{url}</pathurl>{_rate()}'
                f"<duration>{dur}</duration><media>{vid}{aud}</media></file>")

    def filters(it):
        out_f = ""
        if it.scale != 100 or it.offset != (0, 0):
            # Premiere reads Center as a fraction of the clip's own frame size, not the sequence's.
            cw, ch = _media_info(it.path)[0]
            out_f += ("<filter><effect><name>Basic Motion</name><effectid>basic</effectid><effectcategory>motion</effectcategory>"
                      "<effecttype>motion</effecttype><mediatype>video</mediatype>"
                      f"<parameter><parameterid>scale</parameterid><name>Scale</name><valuemin>0</valuemin><valuemax>1000</valuemax><value>{it.scale:g}</value></parameter>"
                      f"<parameter><parameterid>center</parameterid><name>Center</name><value><horiz>{it.offset[0] / cw:.6f}</horiz><vert>{it.offset[1] / ch:.6f}</vert></value></parameter>"
                      "</effect></filter>")
        if it.wipe:
            ws, we, xs, xe = it.wipe
            k0, k1 = frames(ws - it.rec_in), frames(we - it.rec_in)
            r0, r1 = (W - xs) / W * 100, (W - xe) / W * 100
            out_f += ("<filter><effect><name>Crop</name><effectid>crop</effectid><effectcategory>motion</effectcategory>"
                      "<effecttype>motion</effecttype><mediatype>video</mediatype>"
                      "<parameter><parameterid>left</parameterid><name>left</name><valuemin>0</valuemin><valuemax>100</valuemax><value>0</value></parameter>"
                      f"<parameter><parameterid>right</parameterid><name>right</name><valuemin>0</valuemin><valuemax>100</valuemax><value>{r0:.3f}</value>"
                      f"<keyframe><when>{k0}</when><value>{r0:.3f}</value></keyframe><keyframe><when>{k1}</when><value>{r1:.3f}</value></keyframe></parameter>"
                      "<parameter><parameterid>top</parameterid><name>top</name><valuemin>0</valuemin><valuemax>100</valuemax><value>0</value></parameter>"
                      "<parameter><parameterid>bottom</parameterid><name>bottom</name><valuemin>0</valuemin><valuemax>100</valuemax><value>0</value></parameter>"
                      "</effect></filter>")
        return out_f

    cid = 0

    def clip_xml(it, media):
        nonlocal cid
        cid += 1
        start, end = frames(it.rec_in), frames(it.rec_out)
        cin = src_frame(it, start)
        cout = cin + (end - start)
        kind = "still" if it.kind == "still" else "av"
        src = (f"<sourcetrack><mediatype>audio</mediatype><trackindex>1</trackindex></sourcetrack>" if media == "audio" else "")
        return (f'<clipitem id="clip-{cid}"><name>{escape(it.name or Path(it.path).name)}</name><enabled>TRUE</enabled>'
                f"<duration>{cout + 1}</duration>{_rate()}<start>{start}</start><end>{end}</end><in>{cin}</in><out>{cout}</out>"
                f"{file_el(it.path, kind)}{src}{filters(it) if media == 'video' else ''}</clipitem>")

    vtracks = sorted([k for k in tracks if k.startswith("V")], key=lambda s: int(s[1:]))
    atracks = sorted([k for k in tracks if k.startswith("A")], key=lambda s: int(s[1:]))
    v = "".join("<track>" + "".join(clip_xml(i, "video") for i in sorted(tracks[k], key=lambda i: i.rec_in)) + "</track>" for k in vtracks)
    a = "".join("<track>" + "".join(clip_xml(i, "audio") for i in sorted(tracks[k], key=lambda i: i.rec_in)) + "</track>" for k in atracks)
    xml = (f'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n<xmeml version="4"><sequence id="seq-1">'
           f"<name>{escape(seq_name)}</name><duration>{frames(duration)}</duration>{_rate()}"
           f"<media><video><format><samplecharacteristics>{_rate()}<width>{W}</width><height>{H}</height>"
           f"<anamorphic>FALSE</anamorphic><pixelaspectratio>square</pixelaspectratio><fielddominance>none</fielddominance>"
           f"</samplecharacteristics></format>{v}</video>"
           f"<audio><numOutputChannels>2</numOutputChannels><format><samplecharacteristics><depth>16</depth><samplerate>48000</samplerate>"
           f"</samplecharacteristics></format>{a}</audio></media></sequence></xmeml>\n")
    Path(out).write_text(xml)
    return out


# ---------- Final Cut Pro FCPXML ----------

def _media_tc(path):
    """Timecode origin of a media file in seconds (iPhone / camera .mov files often start at a non-zero timecode)."""
    probe = subprocess.run([FFMPEG, "-hide_banner", "-i", path], capture_output=True, text=True).stderr
    tc = re.search(r"timecode\s*:\s*(\d+):(\d+):(\d+)[:;](\d+)", probe)
    if not tc:
        return 0.0
    fps = re.search(r"([\d.]+) fps", probe)
    h, m, sec, f = (int(x) for x in tc.groups())
    return h * 3600 + m * 60 + sec + f / round(float(fps.group(1)) if fps else FPS)


def export_fcpxml(items, seq_name, out, duration):
    """Same edit as export_xml, written as FCPXML 1.10 for Final Cut Pro (File > Import > XML).
    V1 = primary storyline (video only); V2..V7 = connected clips on lanes 1..6; A1, A2.. = connected audio on lanes -1, -2..
    Every clip uses Spatial Conform "None" (native pixel size, like Premiere), scale/offset -> Transform,
    wipe -> keyframed Trim right."""
    from xml.sax.saxutils import quoteattr
    num, den = (1001, 30000) if NTSC else (100, 3000)

    def t(f):
        return "0s" if f == 0 else f"{f * num}/{den}s"

    res = [f'<format id="r1" frameDuration="{num}/{den}s" width="{W}" height="{H}" colorSpace="1-1-1 (Rec. 709)"/>']
    assets = {}

    def asset(path, still):
        """-> (asset id, timecode origin in frames, source frame height)"""
        path = str(Path(path).resolve())
        if path not in assets:
            (w, h), secs, has_audio = _media_info(path)
            fid, aid = f"r{len(res) + 1}", f"r{len(res) + 2}"
            tc = 0 if still else frames(_media_tc(path))
            if still:
                res.append(f'<format id="{fid}" name="FFVideoFormatRateUndefined" width="{w}" height="{h}"/>')
                av = 'start="0s" duration="0s" hasVideo="1" videoSources="1"'
            else:
                res.append(f'<format id="{fid}" frameDuration="{num}/{den}s" width="{w}" height="{h}"/>')
                av = f'start="{t(tc)}" duration="{t(frames(secs))}" hasVideo="1" videoSources="1"'
                if has_audio:
                    av += ' hasAudio="1" audioSources="1" audioChannels="2" audioRate="48000"'
            url = "file://" + urllib.parse.quote(path)
            res.append(f'<asset id="{aid}" name={quoteattr(Path(path).stem)} {av} format="{fid}">'
                       f'<media-rep kind="original-media" src={quoteattr(url)}/></asset>')
            assets[path] = (aid, tc, h)
        return assets[path]

    def video_params(it, local0, src_h):
        """Intrinsic video params, in DTD order: adjust-crop, adjust-conform, adjust-transform."""
        p = ""
        if it.wipe:
            ws, we, xs, xe = it.wipe
            r0, r1 = (W - xs) / src_h * 100, (W - xe) / src_h * 100  # FCP trim is a % of the source frame height
            k0, k1 = local0 + frames(ws - it.rec_in), local0 + frames(we - it.rec_in)
            p += (f'<adjust-crop mode="trim"><trim-rect right="{r0:.4f}"><param name="right"><keyframeAnimation>'
                  f'<keyframe time="{t(k0)}" value="{r0:.4f}" curve="linear"/>'
                  f'<keyframe time="{t(k1)}" value="{r1:.4f}" curve="linear"/>'
                  f'</keyframeAnimation></param></trim-rect></adjust-crop>')
        p += '<adjust-conform type="none"/>'

        def pos(dx, dy):  # FCP position is a % of the sequence frame height with +y up; ours is px with +y down
            return f"{(it.offset[0] + dx) / H * 100:.4f} {-(it.offset[1] + dy) / H * 100:.4f}"
        if it.motion:
            ks = it.motion
            kt = [t(local0 + frames(k[0] - it.rec_in)) for k in ks]

            def anim(vals):
                return "<keyframeAnimation>" + "".join(f'<keyframe time="{tt}" value="{v}" interp="easeOut" curve="linear"/>'
                                                       for tt, v in zip(kt, vals)) + "</keyframeAnimation>"
            sc = [f"{it.scale / 100 * k[3]:g} {it.scale / 100 * k[3]:g}" for k in ks]
            p += (f'<adjust-transform position="{pos(*ks[0][1:3])}" scale="{sc[0]}">'
                  f'<param name="position">{anim([pos(k[1], k[2]) for k in ks])}</param>'
                  + (f'<param name="scale">{anim(sc)}</param>' if len(set(sc)) > 1 else "") + "</adjust-transform>")
            if any(k[4] != 1 for k in ks):
                p += f'<adjust-blend amount="{ks[0][4]:g}"><param name="amount">{anim([f"{k[4]:g}" for k in ks])}</param></adjust-blend>'
        elif it.scale != 100 or it.offset != (0, 0):
            p += f'<adjust-transform position="{pos(0, 0)}" scale="{it.scale / 100:g} {it.scale / 100:g}"/>'
        return p

    def element(it, offset_f, lane=None, kids=""):
        """FCPXML element for one Item; returns (xml, local start frame)."""
        still = it.kind == "still"
        aid, tc, src_h = asset(it.path, still)
        dur = frames(it.rec_out) - frames(it.rec_in)
        start = 0 if still else tc + src_frame(it, frames(it.rec_in))
        head = (f'ref="{aid}"' + (f' lane="{lane}"' if lane else "") +
                f' offset="{t(offset_f)}" name={quoteattr(it.name or Path(it.path).stem)} start="{t(start)}" duration="{t(dur)}"')
        if still:
            return f"<video {head}>{video_params(it, start, src_h)}{kids}</video>", start
        if it.track.startswith("A"):
            return f'<asset-clip {head} srcEnable="audio" audioRole="dialogue">{kids}</asset-clip>', start
        return f'<asset-clip {head} srcEnable="video">{video_params(it, start, src_h)}{kids}</asset-clip>', start

    # primary storyline: V1 clips back to back, holes filled with gaps -> (item|None, rec in, rec out, local start)
    spine, cur = [], 0
    for it in sorted([i for i in items if i.track == "V1"], key=lambda i: i.rec_in):
        a, b = frames(it.rec_in), frames(it.rec_out)
        if a > cur:
            spine.append((None, cur, a, 0))
        spine.append((it, a, b, element(it, a)[1]))
        cur = b
    if frames(duration) > cur:
        spine.append((None, cur, frames(duration), 0))

    # connect every other item to the storyline element under its start (offset is in that element's local time)
    kids = [[] for _ in spine]
    for it in sorted([i for i in items if i.track != "V1"], key=lambda i: (i.rec_in, i.track)):
        a = frames(it.rec_in)
        k = next((k for k, (_, s0, s1, _) in enumerate(spine) if s0 <= a < s1), len(spine) - 1)
        n = int(it.track[1:])
        kids[k].append(element(it, spine[k][3] + a - spine[k][1], lane=n - 1 if it.track.startswith("V") else -n)[0])

    body = ""
    for (it, a, b, _), ks in zip(spine, kids):
        if it is None:
            body += f'<gap name="Gap" offset="{t(a)}" start="0s" duration="{t(b - a)}">{"".join(ks)}</gap>'
        else:
            body += element(it, a, kids="".join(ks))[0]

    xml = (f'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n<fcpxml version="1.10"><resources>{"".join(res)}</resources>'
           f'<library><event name={quoteattr(seq_name)}><project name={quoteattr(seq_name)}>'
           f'<sequence format="r1" duration="{t(frames(duration))}" tcStart="0s" tcFormat="NDF" audioLayout="stereo" audioRate="48k">'
           f'<spine>{body}</spine></sequence></project></event></library></fcpxml>\n')
    Path(out).write_text(xml)
    return out


def render_preview_multi(items, raws, out, duration, scale=0.5):
    """Preview for a video built from several raw files (listed in timeline order).
    Joins the raws into one temporary file, remaps V1/A1 items onto it, then uses render_preview."""
    import dataclasses
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="reel-join-"))
    joined = str(tmp / "joined.mp4")
    offsets, t, nf = {}, 0.0, []
    for p in raws:  # each file is cut to a whole number of frames so later files start exactly on a frame
        offsets[str(p)] = t
        nf.append(int(_media_info(str(p))[1] * FPS))
        t += nf[-1] / FPS
    inputs = sum([["-i", str(p)] for p in raws], [])
    fc = "".join(f"[{i}:v]fps={FPS_STR},scale={W}:{H},setsar=1,trim=end_frame={n},setpts=PTS-STARTPTS[v{i}];"
                 f"[{i}:a]atrim=end={n / FPS:.6f},asetpts=PTS-STARTPTS[s{i}];" for i, n in enumerate(nf))
    fc += "".join(f"[v{i}][s{i}]" for i in range(len(raws))) + f"concat=n={len(raws)}:v=1:a=1[v][a]"
    subprocess.run([FFMPEG, "-loglevel", "error", "-y", *inputs, "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-c:a", "aac", joined], check=True)
    remapped = [dataclasses.replace(it, path=joined, src_in=it.src_in + offsets[str(it.path)])
                if str(it.path) in offsets else it for it in items]
    ranges = sorted((it.src_in, it.src_in + it.rec_out - it.rec_in) for it in remapped if it.track == "A1")
    return render_preview(remapped, joined, ranges, out, duration, scale)


# ---------- b-roll helpers ----------

def _decode(src, t0, dur, size):
    """Decode dur seconds of src starting at t0, scaled to cover size (w, h), as a list of RGB frames at FPS."""
    w, h = size
    vf = f"fps={FPS_STR},scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"
    raw = subprocess.run([FFMPEG, "-loglevel", "error", "-ss", f"{t0:.3f}", "-i", src, "-t", f"{dur:.3f}", "-an",
                          "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    n = len(raw) // (w * h * 3)
    fr = [Image.frombytes("RGB", (w, h), raw[i * w * h * 3:(i + 1) * w * h * 3]) for i in range(n)]
    need = frames(dur)
    return (fr + [fr[-1]] * need)[:need] if fr else [Image.new("RGB", size)] * need


def broll_panel(src, out, t0, dur, size=(W, TOP)):
    """Top-panel b-roll clip: cover-crop to the panel, audio removed (b-roll always plays silent)."""
    vf = f"fps={FPS_STR},scale={size[0]}:{size[1]}:force_original_aspect_ratio=increase,crop={size[0]}:{size[1]}"
    subprocess.run([FFMPEG, "-loglevel", "error", "-y", "-ss", f"{t0:.3f}", "-i", src, "-t", f"{dur:.3f}", "-an", "-vf", vf,
                    "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", out], check=True)
    return out


def grid_background(bg=(10, 10, 14), line=(34, 34, 48), step=64):
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    for x in range(0, W, step):
        d.line([(x, 0), (x, H)], fill=line, width=2)
    for y in range(0, H, step):
        d.line([(0, y), (W, y)], fill=line, width=2)
    return img


def caption_bar(img, cx, cy, parts, size=40, fill=(122, 10, 10)):
    """Dark-red caption bar with mixed regular/bold runs: parts = [(text, bold), ...]."""
    d = ImageDraw.Draw(img)
    fonts = [font(F_BLACK if b else F_BOLD, size) for _, b in parts]
    widths = [d.textbbox((0, 0), t, font=f)[2] for (t, _), f in zip(parts, fonts)]
    tw, th = sum(widths), size
    x0, y0 = int(cx - tw / 2 - 36), int(cy - th / 2 - 22)
    d.rectangle([x0, y0, x0 + tw + 72, y0 + th + 44], fill=fill)
    x = x0 + 36
    for (t, _), f, w in zip(parts, fonts, widths):
        d.text((x, y0 + 22 - d.textbbox((0, 0), t, font=f)[1] + 2), t, font=f, fill=WHITE)
        x += w


PIP_CIRCLE = (540, 340, 255)  # centre x, centre y, radius of the host circle


def pip_layout(out, dur, clips, circle=PIP_CIRCLE, rise=True):
    """Circle-PiP scene (reference style): dark grid, a transparent circle (host shows through from V1) with a white
    ring, and up to two clips stacked below in rounded white-bordered frames with dark-red caption bars.
    clips = [(src, t0, [(text, bold), ...]), ...]. Writes ProRes 4444 with alpha."""
    base = grid_background().convert("RGBA")
    cx, cy, r = circle
    boxes = [(90, 690, 990, 1196), (90, 1300, 990, 1806)] if len(clips) > 1 else [(60, 820, 1020, 1360)]
    mask = Image.new("L", (W, H), 255)
    ImageDraw.Draw(mask).ellipse([cx - r, cy - r, cx + r, cy + r], fill=0)
    base.putalpha(mask)
    ImageDraw.Draw(base).ellipse([cx - r - 6, cy - r - 6, cx + r + 6, cy + r + 6], outline=WHITE, width=8)
    streams = [_decode(src, t0, dur, (b[2] - b[0], b[3] - b[1])) for (src, t0, _), b in zip(clips, boxes)]
    rmask = [Image.new("L", (b[2] - b[0], b[3] - b[1]), 0) for b in boxes]
    for m in rmask:
        ImageDraw.Draw(m).rounded_rectangle([0, 0, m.width - 1, m.height - 1], 22, fill=255)
    enc = subprocess.Popen([FFMPEG, "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                            "-r", FPS_STR, "-i", "-", "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le",
                            out], stdin=subprocess.PIPE)
    for i in range(frames(dur)):
        fr = base.copy()
        for k, ((src, t0, cap), b, st, m) in enumerate(zip(clips, boxes, streams, rmask)):
            # entrance: each clip rises from below, staggered 3 f, ease-out over 12 f (ANIMATION.md)
            u = ease_out((i - 3 * k) / 12) if rise else 1.0
            if u <= 0:
                continue
            dy = int((1 - u) * (H - b[1] + 40))
            card = Image.new("RGBA", (b[2] - b[0] + 12, b[3] - b[1] + 12), (0, 0, 0, 0))
            ImageDraw.Draw(card).rounded_rectangle([0, 0, card.width - 1, card.height - 1], 28, fill=WHITE)
            card.paste(st[i], (6, 6), m)
            if cap:
                caption_bar(card, card.width / 2, card.height - 44, cap)
            fr.alpha_composite(card, (b[0] - 6, b[1] - 6 + dy)) if b[1] - 6 + dy < H else None
        enc.stdin.write(fr.tobytes())
    enc.stdin.close()
    enc.wait()
    return out


def photo_panel(img, out, dur, zoom=0.05, focus=(0.5, 0.4)):
    """Top-panel clip for a still photo (ANIMATION.md): photo centred at full panel height, the leftover width filled
    with an enlarged blurred copy of itself, and a slow Ken Burns zoom-in (1.0 -> 1+zoom) over the shot."""
    img = img.convert("RGB")
    bg = cover(img, W, TOP, focus).filter(ImageFilter.GaussianBlur(28))
    bg = Image.blend(bg, Image.new("RGB", bg.size, (0, 0, 0)), 0.25)
    s = TOP / img.height
    fg = img.resize((round(img.width * s), TOP), Image.LANCZOS)
    if fg.width >= W:
        fg = cover(img, W, TOP, focus)
    base = bg.copy()
    base.paste(fg, ((W - fg.width) // 2, 0))
    enc = subprocess.Popen([FFMPEG, "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{TOP}",
                            "-r", FPS_STR, "-i", "-", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", out],
                           stdin=subprocess.PIPE)
    n = frames(dur)
    for i in range(n):
        enc.stdin.write(base_zoom(base, 1 + zoom * i / max(n - 1, 1)).tobytes())
    enc.stdin.close()
    enc.wait()
    return out


def base_zoom(img, z):
    """img scaled by z about its centre, cropped back to its own size."""
    w, h = img.size
    cw, ch = w / z, h / z
    return img.crop(((w - cw) / 2, (h - ch) / 2, (w + cw) / 2, (h + ch) / 2)).resize((w, h), Image.BILINEAR)


def share_button(out, dur=3.0, cy=1560):
    """End SHARE button (ANIMATION.md): black bar wipes in, white wipes over it, then the blue SHARE wipes in; holds.
    Written as ProRes 4444 with alpha."""
    fnt = font(F_BLACK, 64)
    d0 = ImageDraw.Draw(Image.new("L", (1, 1)))
    l, t_, r, b_ = d0.textbbox((0, 0), "SHARE", font=fnt)
    bw, bh = (r - l) + 90, (b_ - t_) + 50
    x0, y0 = (W - bw) // 2, cy - bh // 2
    layers = []
    for fill in ((0, 0, 0), (255, 255, 255), (29, 155, 240)):
        im = Image.new("RGBA", (bw, bh), fill + (255,))
        if fill == (29, 155, 240):
            ImageDraw.Draw(im).text(((bw - (r - l)) // 2 - l, (bh - (b_ - t_)) // 2 - t_), "SHARE", font=fnt, fill=WHITE)
        layers.append(im)
    enc = subprocess.Popen([FFMPEG, "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                            "-r", FPS_STR, "-i", "-", "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le",
                            out], stdin=subprocess.PIPE)
    for i in range(frames(dur)):
        fr = blank()
        for k, im in enumerate(layers):
            u = ease_out((i - 7 * k) / 10)
            if u > 0:
                fr.alpha_composite(im.crop((0, 0, max(1, int(bw * u)), bh)), (x0, y0))
        enc.stdin.write(fr.tobytes())
    enc.stdin.close()
    enc.wait()
    return out


def pip_face_motion(face_center=(545, 600), face_scale=0.50, lift=0.28, circle=PIP_CIRCLE):
    """(scale %, offset px) for the V1 talking head inside the PiP circle, framed like a bust shot: face + neck + a bit
    of shoulder (face height ~45-55 % of the circle), not a face-filling close-up. face_center is the raw-frame point
    between eyes and nose; it sits lift*r above the circle centre. Scale never drops below what still covers the
    circle's width (raw is 1080 wide), so no black edges show inside the ring."""
    cx, cy, r = circle
    face_scale = max(face_scale, (2 * r + 16) / W)
    ox = cx - (W / 2 + (face_center[0] - W / 2) * face_scale)
    oy = (cy - lift * r) - (H / 2 + (face_center[1] - H / 2) * face_scale)
    return face_scale * 100, (round(ox), round(oy))


def story_still(img, out, dur, focus=(0.5, 0.5), zoom=0.06, blur=None, tilt=None, shakes=(), flashes=(), labels=(),
                red=None, margin=1.14):
    """Storytelling top-panel clip from one still: Ken Burns plus timed effects that act out the narration.
    blur=(t0, t1, s0, s1) gaussian ramp ("vision went blurry"); tilt=(t0, t1, deg0, deg1) rotation ramp ("nose going
    down"); shakes=[(t, amp_px, length_s)] decaying camera shake ("a hard blow"); flashes=[t] 3-frame white flash;
    labels=[(t, text, (x, y))] red pills that scale-pop in (0->105->100 %) at panel px; red=(t0, t1, max_alpha)
    red vignette ramp. The photo is rendered `margin` larger so rotation and shake never show its edges."""
    img = img.convert("RGB")
    bw, bh = round(W * margin), round(TOP * margin)
    base = cover(img, bw, bh, focus)
    fnt = font(F_BLACK, 34)
    pills = []
    for t, text, xy in labels:
        tmp = Image.new("RGBA", (W, 200), (0, 0, 0, 0))
        b = text_box(tmp, text, W / 2, 100, fnt, WHITE, RED + (255,), outline=WHITE, pad=(26, 14), radius=8)
        pills.append((t, tmp.crop((b[0] - 3, b[1] - 3, b[2] + 3, b[3] + 3)), xy))
    vig = None
    if red:
        yy, xx = np.mgrid[0:TOP, 0:W]
        d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - TOP / 2) / (TOP / 2)) ** 2)
        vig = np.clip((d - 0.55) / 0.6, 0, 1)
    enc = subprocess.Popen([FFMPEG, "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{TOP}",
                            "-r", FPS_STR, "-i", "-", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", out],
                           stdin=subprocess.PIPE)
    n = frames(dur)
    rng = np.random.default_rng(7)
    jit = rng.uniform(-1, 1, (n, 2))
    for i in range(n):
        t = i / FPS
        z = 1 + zoom * i / max(n - 1, 1)
        fr = base_zoom(base, z)
        if tilt:
            u = ease((t - tilt[0]) / max(tilt[1] - tilt[0], 1e-6))
            fr = fr.rotate(tilt[2] + (tilt[3] - tilt[2]) * u, resample=Image.BICUBIC)
        dx = dy = 0.0
        for ts, amp, ln in shakes:
            if ts <= t < ts + ln:
                k = amp * (1 - (t - ts) / ln) ** 2
                dx += jit[i, 0] * k
                dy += jit[i, 1] * k
        x0, y0 = (bw - W) / 2 + dx, (bh - TOP) / 2 + dy
        fr = fr.crop((round(x0), round(y0), round(x0) + W, round(y0) + TOP))
        if blur:
            u = ease((t - blur[0]) / max(blur[1] - blur[0], 1e-6))
            s = blur[2] + (blur[3] - blur[2]) * u
            if s > 0.3:
                fr = fr.filter(ImageFilter.GaussianBlur(s))
        if vig is not None:
            u = ease((t - red[0]) / max(red[1] - red[0], 1e-6)) * red[2]
            if u > 0:
                a = np.asarray(fr, np.float32)
                m = (vig * u)[..., None]
                fr = Image.fromarray((a * (1 - m) + np.array([120, 0, 0], np.float32) * m).astype(np.uint8))
        for tf in flashes:
            if tf <= t < tf + 3 / FPS:
                fr = Image.blend(fr, Image.new("RGB", fr.size, WHITE), 0.75 * (1 - (t - tf) * FPS / 3))
        fr = fr.convert("RGBA")
        for tp, pill, (cx, cy) in pills:
            if t < tp:
                continue
            u = (t - tp) * FPS
            s = 1.05 * ease_out(u / 5) if u < 5 else 1.05 - 0.05 * ease_out((u - 5) / 3)
            if s <= 0.02:
                continue
            p = pill.resize((max(1, round(pill.width * s)), max(1, round(pill.height * s))), Image.BICUBIC)
            fr.alpha_composite(p, (round(cx - p.width / 2), round(cy - p.height / 2)))
        enc.stdin.write(fr.convert("RGB").tobytes())
    enc.stdin.close()
    enc.wait()
    return out
