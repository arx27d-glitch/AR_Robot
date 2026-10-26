"""
AloneX/helpers/help_card.py

Premium "black metal" help cards (like the ADMIN COMMANDS picture) for the /help menu.

* A module can have a ready-made picture: put  AloneX/helpers/data/help_cards/<name>.jpg|png  in that folder
  (admin.jpg is the picture the owner made). <name> is the module name in plain letters ("admin", "chatbot" ...).
* Every other module gets a card drawn on the fly from its __help__ text (commands are read from the lines
  that start with  /command  ), 10 commands per picture, in the same style. Cards are cached on disk.
* If a module has no commands to show, get_card() returns None and the old text help is used.

Only Pillow is needed. Fonts (Poppins, OFL licence) are bundled in data/help_cards/fonts.
"""
import asyncio
import hashlib
import math
import os
import re
import tempfile
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

_HERE = os.path.dirname(os.path.abspath(__file__))
CARD_DIR = os.path.join(_HERE, "data", "help_cards")
FONT_DIR = os.path.join(CARD_DIR, "fonts")
CACHE_DIR = os.environ.get("HELP_CARD_CACHE") or os.path.join(tempfile.gettempdir(), "ar_help_cards")
BRAND = os.environ.get("HELP_CARD_TITLE", "AR X BOT")
PER_PAGE = 10
VERSION = "v1"

SIZE = 1254          # picture size (square, same as the owner's picture)
SS = 2               # drawing at 2x, then scaled down = smooth edges


# ════════════════════════════════════════════════════════════════════
#  TEXT HELPERS (module names / help text use fancy unicode letters and emoji)
# ════════════════════════════════════════════════════════════════════
_SMALLCAPS = {
    "ᴀ": "a", "ʙ": "b", "ᴄ": "c", "ᴅ": "d", "ᴇ": "e", "ғ": "f", "ꜰ": "f", "ɢ": "g", "ʜ": "h", "ɪ": "i",
    "ᴊ": "j", "ᴋ": "k", "ʟ": "l", "ᴍ": "m", "ɴ": "n", "ᴏ": "o", "ᴘ": "p", "ǫ": "q", "ʀ": "r", "ꜱ": "s",
    "ᴛ": "t", "ᴜ": "u", "ᴠ": "v", "ᴡ": "w", "ʏ": "y", "ᴢ": "z", "σ": "o", "η": "n", "є": "e", "ꝛ": "r",
    "ᴧ": "a", "υ": "u", "ι": "i", "ν": "v", "ρ": "p", "τ": "t",
}
_EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\u2300-\u23FF\uFE0F\u200D\u2060\u200B\u20E3\u2190-\u21FF"
    "\u2700-\u27BF\u2900-\u297F\u25A0-\u25FF\u2022\u2023\u2043\u2756\u2742\u2748\u274C-\u274F]")


def plain(text: str) -> str:
    """Fancy unicode (bold math letters, small caps) -> ordinary letters; emoji removed."""
    text = unicodedata.normalize("NFKD", str(text or ""))
    text = "".join(_SMALLCAPS.get(ch, ch) for ch in text)
    text = _EMOJI_RE.sub("", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text


def canon_key(name: str) -> str:
    """Module name -> plain lowercase letters/digits ("𝐀ᴅᴍɪɴ🛠️" -> "admin")."""
    return re.sub(r"[^a-z0-9]+", "", plain(name).lower())


def display_name(name: str) -> str:
    t = re.sub(r"[^A-Za-z0-9 \-&]+", " ", plain(name))
    t = re.sub(r"\s+", " ", t).strip()
    return t.upper() or "HELP"


# ════════════════════════════════════════════════════════════════════
#  PARSING THE __help__ TEXT
# ════════════════════════════════════════════════════════════════════
_TAG_RE = re.compile(r"<[^>]+>")
_BULLET_RE = re.compile(r"^[\s•●◦▪▫■□◆◇➣➛➤➢❂⍣✦✧★☆»›\-\*·~=+\d\.\)\(]*")
_CMD_RE = re.compile(r"^/([A-Za-z][A-Za-z0-9_]{0,30})")
_ARGS_RE = re.compile(r"^(?:\s*(?:<[^>]*>|\[[^\]]*\]|\([^)]*\)|\bon\b|\boff\b|\||/|@\w+|\w+(?=\s*[|/<\[])))*")


def _clean_line(line: str) -> str:
    line = _TAG_RE.sub("", line)
    line = line.replace("`", "").replace("*", "").replace("__", "")
    line = re.sub(r"(?<!\w)_|_(?!\w)", "", line)
    return line.strip()


def _short_desc(desc: str) -> str:
    desc = plain(desc)
    desc = re.sub(r"\s+", " ", desc).strip(" -—–:·|.")
    desc = re.split(r"(?<=[a-z\)])\.\s+[A-Z]", desc)[0]  # first sentence
    desc = re.sub(r"\s*\([^)]*\)\s*$", "", desc)         # trailing "(note)"
    desc = desc.strip(" -—–:·|.")
    return desc[:1].upper() + desc[1:] if desc else ""


def parse_commands(help_text: str) -> List[Tuple[str, str]]:
    """[(/command, short description), ...] in the order of the help text, without duplicates."""
    out: List[Tuple[str, str]] = []
    seen = set()
    for raw in str(help_text or "").splitlines():
        line = _clean_line(raw)
        line = _BULLET_RE.sub("", line).strip()
        m = _CMD_RE.match(line)
        if not m:
            continue
        cmd = "/" + m.group(1).lower()
        if cmd in seen:
            continue
        rest = line[m.end():]
        sep = re.search(r"\s[—–-]\s|\s*[—–:]\s*|\s-\s", rest)
        if sep:
            desc = rest[sep.end():]
        else:
            desc = _ARGS_RE.sub("", rest, count=1)
        desc = _short_desc(desc)
        if not desc:
            desc = "Use " + cmd
        seen.add(cmd)
        out.append((cmd, desc))
    return out


# ════════════════════════════════════════════════════════════════════
#  DRAWING
# ════════════════════════════════════════════════════════════════════
def S(v: float) -> int:
    return int(round(v * SS))


@lru_cache(maxsize=64)
def _font(weight: str, size: float) -> ImageFont.FreeTypeFont:
    names = {"bold": "Poppins-Bold.ttf", "medium": "Poppins-Medium.ttf", "regular": "Poppins-Regular.ttf"}
    fallbacks = {
        "bold": ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", "DejaVuSans-Bold.ttf"],
        "medium": ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                   "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "DejaVuSans.ttf"],
        "regular": ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "DejaVuSans.ttf"],
    }
    for path in [os.path.join(FONT_DIR, names[weight])] + fallbacks[weight]:
        try:
            return ImageFont.truetype(path, S(size))
        except OSError:
            continue
    return ImageFont.load_default()


def _text_w(font, text: str, spacing: float = 0.0) -> float:
    if spacing == 0:
        return font.getlength(text)
    return sum(font.getlength(ch) for ch in text) + S(spacing) * max(0, len(text) - 1)


def _fit_font(weight: str, text: str, size: float, max_w: float, min_size: float = 16):
    """Largest font (<= size) in which the text fits max_w (in 1254-space pixels)."""
    s = size
    while s > min_size:
        if _text_w(_font(weight, s), text) <= S(max_w):
            break
        s -= 1
    return _font(weight, s), s


def _ellipsize(font, text: str, max_w: float) -> str:
    if _text_w(font, text) <= S(max_w):
        return text
    while len(text) > 3 and _text_w(font, text + "…") > S(max_w):
        text = text[:-1]
    return text.rstrip(" ,.-") + "…"


def _draw_spaced(draw, xy, text, font, fill, spacing=0.0):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += font.getlength(ch) + S(spacing)


def _gradient(size: Tuple[int, int], stops: List[Tuple[int, int, int]], horizontal: bool = False) -> Image.Image:
    """Smooth 2-3 colour gradient image."""
    w, h = size
    g = Image.linear_gradient("L")  # black (top) -> white (bottom), 256x256
    if horizontal:
        g = g.rotate(90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)
    g = g.resize((max(1, w), max(1, h)), Image.BILINEAR)
    if len(stops) == 2:
        return ImageOps.colorize(g, stops[0], stops[1]).convert("RGB")
    return ImageOps.colorize(g, stops[0], stops[2], mid=stops[1]).convert("RGB")


def _paste_masked(canvas: Image.Image, fill_img: Image.Image, mask: Image.Image, pos=(0, 0), alpha: float = 1.0):
    if alpha < 1.0:
        mask = mask.point(lambda v: int(v * alpha))
    canvas.paste(fill_img, pos, mask)


SILVER = [(255, 255, 255), (178, 184, 190), (226, 230, 233)]
SILVER_DIM = [(150, 154, 160), (70, 72, 76)]


def _glow(base: Image.Image, mask: Image.Image, radius: float, color=(255, 255, 255), strength: float = 0.5, pos=(0, 0)):
    blurred = mask.filter(ImageFilter.GaussianBlur(S(radius))).point(lambda v: int(v * strength))
    base.paste(Image.new("RGB", blurred.size, color), pos, blurred)


# ---------- background ----------
def _background() -> Image.Image:
    W = SIZE * SS
    base = Image.new("RGB", (W, W), (5, 5, 6))
    rg = Image.radial_gradient("L").resize((W, W), Image.BILINEAR)
    rg = rg.point(lambda v: int(255 * ((v / 255) ** 1.35)))
    center = Image.new("RGB", (W, W), (30, 30, 33))
    base = Image.composite(base, center, rg)
    noise = Image.effect_noise((W // 2, W // 2), 22).resize((W, W)).point(lambda v: max(0, v - 118) // 5)
    base = ImageChops.add(base, Image.merge("RGB", (noise, noise, noise)))

    # metallic corner streaks (drawn once for the top-left corner, then mirrored)
    layer = Image.new("L", (W, W), 0)
    d = ImageDraw.Draw(layer)
    bands = [(0.0, 150, 70), (210, 260, 45), (330, 350, 30)]
    for start, end, a in bands:  # soft wide bands
        d.polygon([(S(start), 0), (S(end), 0), (0, S(end)), (0, S(start))], fill=a)
    glow = Image.new("L", (W, W), 0)
    gd = ImageDraw.Draw(glow)
    for off, wd, a in [(150, 5, 230), (214, 3, 170), (262, 2, 110), (352, 2, 90)]:
        gd.line([(S(off), 0), (0, S(off))], fill=a, width=S(wd))
    sheen = Image.new("L", (W, W), 0)
    sd = ImageDraw.Draw(sheen)
    sd.line([(S(60), S(30)), (S(30), S(60))], fill=255, width=S(5))
    corner = Image.new("RGB", (W, W), (0, 0, 0))
    silver = _gradient((W, W), [(95, 98, 104), (200, 204, 210)])
    corner.paste(silver, (0, 0), layer)
    corner.paste(Image.new("RGB", (W, W), (255, 255, 255)), (0, 0), glow)
    soft = glow.filter(ImageFilter.GaussianBlur(S(6))).point(lambda v: int(v * 0.8))
    corner.paste(Image.new("RGB", (W, W), (230, 235, 240)), (0, 0), soft)
    soft2 = sheen.filter(ImageFilter.GaussianBlur(S(14))).point(lambda v: int(v * 0.9))
    corner.paste(Image.new("RGB", (W, W), (255, 255, 255)), (0, 0), soft2)
    corner_mask = ImageChops.lighter(ImageChops.lighter(layer, glow), soft)
    corner_mask = ImageChops.lighter(corner_mask, soft2)
    for flip_h in (False, True):
        for flip_v in (False, True):
            c, m = corner, corner_mask
            if flip_h:
                c, m = ImageOps.mirror(c), ImageOps.mirror(m)
            if flip_v:
                c, m = ImageOps.flip(c), ImageOps.flip(m)
            base.paste(c, (0, 0), m)
    return base


# ---------- logo ----------
def _hex_points(cx, cy, r, rot=-90):
    return [(cx + r * math.cos(math.radians(rot + 60 * i)), cy + r * math.sin(math.radians(rot + 60 * i))) for i in range(6)]


def _logo(base: Image.Image, cx: float, cy: float, r: float):
    W = base.size[0]
    mask = Image.new("L", (W, W), 0)
    d = ImageDraw.Draw(mask)
    pts = [(S(x), S(y)) for x, y in _hex_points(cx, cy, r)]
    d.line(pts + [pts[0], pts[1]], fill=255, width=S(13), joint="curve")
    for p in pts:  # round the corners
        d.ellipse([p[0] - S(6.5), p[1] - S(6.5), p[0] + S(6.5), p[1] + S(6.5)], fill=255)
    box = (S(cx - r - 20), S(cy - r - 20), S(cx + r + 20), S(cy + r + 20))
    sub = mask.crop(box)
    _glow(base, sub, 10, (255, 255, 255), 0.55, (box[0], box[1]))
    grad = _gradient(sub.size, [(255, 255, 255), (120, 124, 130), (235, 238, 241)])
    base.paste(grad, (box[0], box[1]), sub)

    # inner hex shadow + paper plane
    inner = Image.new("L", (W, W), 0)
    ImageDraw.Draw(inner).polygon([(S(x), S(y)) for x, y in _hex_points(cx, cy, r - 26)], fill=40)
    base.paste(Image.new("RGB", (W, W), (255, 255, 255)), (0, 0), inner.filter(ImageFilter.GaussianBlur(S(3))))

    u = r / 100.0
    def P(x, y):
        return (S(cx + x * u), S(cy + y * u))
    plane = Image.new("L", (W, W), 0)
    pd = ImageDraw.Draw(plane)
    pd.polygon([P(-52, 4), P(52, -38), P(22, 44), P(2, 20)], fill=255)          # main wing
    pd.polygon([P(2, 20), P(52, -38), P(-14, 30)], fill=255)
    fold = Image.new("L", (W, W), 0)
    ImageDraw.Draw(fold).polygon([P(2, 20), P(-14, 32), P(-8, 8)], fill=255)    # lower fold (shadow)
    pbox = (S(cx - r), S(cy - r), S(cx + r), S(cy + r))
    psub = plane.crop(pbox)
    pg = _gradient(psub.size, [(255, 255, 255), (150, 154, 160)])
    _glow(base, psub, 8, (255, 255, 255), 0.35, (pbox[0], pbox[1]))
    base.paste(pg, (pbox[0], pbox[1]), psub)
    base.paste(Image.new("RGB", (W, W), (90, 92, 98)), (0, 0), fold.point(lambda v: int(v * 0.9)))


# ---------- title ----------
def _title(base: Image.Image, text: str, cy: float):
    W = base.size[0]
    parts = text.split(" ")
    # "AR X BOT" -> left word, stylised X, right word. Anything else: plain gradient text.
    f = _font("bold", 168)
    spacing = 8
    if len(parts) == 3 and parts[1].upper() == "X":
        left, right = parts[0], parts[2]
        lw, rw = _text_w(f, left, spacing), _text_w(f, right, spacing)
        xw = S(150)
        gap = S(18)
        total = lw + gap + xw + gap + rw
        x0 = (W - total) / 2
        asc, desc = f.getmetrics()
        ty = S(cy) - (asc + desc) / 2 - S(8)
        mask = Image.new("L", (W, W), 0)
        md = ImageDraw.Draw(mask)
        _draw_spaced(md, (x0, ty), left, f, 255, spacing)
        _draw_spaced(md, (x0 + lw + gap + xw + gap, ty), right, f, 255, spacing)
        # the X: one thick and one thin slash
        cxx = x0 + lw + gap + xw / 2
        top, bot = S(cy) - S(62), S(cy) + S(58)
        hw = xw / 2 - S(8)
        md.line([(cxx - hw, top), (cxx + hw, bot)], fill=255, width=S(26))
        md.line([(cxx + hw, top), (cxx - hw, bot)], fill=255, width=S(11))
        bbox = mask.getbbox()
    else:
        tw = _text_w(f, text, spacing)
        asc, desc = f.getmetrics()
        mask = Image.new("L", (W, W), 0)
        _draw_spaced(ImageDraw.Draw(mask), ((W - tw) / 2, S(cy) - (asc + desc) / 2 - S(8)), text, f, 255, spacing)
        bbox = mask.getbbox()
    if not bbox:
        return
    pad = S(30)
    box = (max(0, bbox[0] - pad), max(0, bbox[1] - pad), min(W, bbox[2] + pad), min(W, bbox[3] + pad))
    sub = mask.crop(box)
    shadow = sub.filter(ImageFilter.GaussianBlur(S(9))).point(lambda v: int(v * 0.9))
    base.paste(Image.new("RGB", sub.size, (0, 0, 0)), (box[0] + S(6), box[1] + S(10)), shadow)
    _glow(base, sub, 14, (255, 255, 255), 0.22, (box[0], box[1]))
    grad = _gradient(sub.size, [(255, 255, 255), (150, 155, 162), (232, 235, 238)])
    base.paste(grad, (box[0], box[1]), sub)
    edge = ImageChops.subtract(sub, sub.filter(ImageFilter.MinFilter(3)))  # thin light edge
    base.paste(Image.new("RGB", sub.size, (255, 255, 255)), (box[0], box[1]), edge.point(lambda v: int(v * 0.5)))


def _fade_line(base: Image.Image, x0: float, x1: float, y: float, fade_left: bool, width: float = 2.0):
    """Thin line that fades out on one side."""
    W = base.size[0]
    length = max(2, S(x1 - x0))
    mask = Image.new("L", (length, S(width)), 255)
    ramp = Image.linear_gradient("L").rotate(90, expand=True)  # black(left?) -> white
    ramp = ramp.resize((length, S(width)), Image.BILINEAR)
    if not fade_left:
        ramp = ImageOps.mirror(ramp)
    mask = ImageChops.multiply(mask, ramp)
    base.paste(Image.new("RGB", mask.size, (190, 194, 200)), (S(x0), S(y)), mask)


def _subtitle(base: Image.Image, text: str, cy: float):
    W = base.size[0]
    f = _font("medium", 41)
    sp = 15
    tw = _text_w(f, text, sp)
    x = (W - tw) / 2
    asc, desc = f.getmetrics()
    d = ImageDraw.Draw(base)
    _draw_spaced(d, (x, S(cy) - (asc + desc) / 2 - S(2)), text, f, (214, 217, 221), sp)
    gap = S(26)
    _fade_line(base, 150, (x - gap) / SS, cy, True)
    _fade_line(base, (x + tw + gap) / SS, SIZE - 150, cy, False)


# ---------- icons ----------
ICON = (240, 241, 243)


def _user(d, cx, cy, r, w):
    d.ellipse([cx - 0.52 * r, cy - 0.62 * r, cx - 0.04 * r, cy - 0.14 * r], outline=ICON, width=w)
    d.arc([cx - 0.84 * r, cy + 0.02 * r, cx + 0.28 * r, cy + 1.05 * r], 180, 360, fill=ICON, width=w)


def _badge(d, cx, cy, r, w, kind):
    bx, by, br = cx + 0.5 * r, cy + 0.42 * r, 0.36 * r
    d.ellipse([bx - br, by - br, bx + br, by + br], fill=(14, 14, 15), outline=ICON, width=max(2, w - 1))
    k = br * 0.52
    if kind == "ban":
        d.line([(bx - k, by + k), (bx + k, by - k)], fill=ICON, width=max(2, w - 1))
    elif kind == "plus":
        d.line([(bx - k, by), (bx + k, by)], fill=ICON, width=max(2, w - 1))
        d.line([(bx, by - k), (bx, by + k)], fill=ICON, width=max(2, w - 1))
    elif kind == "minus":
        d.line([(bx - k, by), (bx + k, by)], fill=ICON, width=max(2, w - 1))


def _speaker(d, cx, cy, r, w, waves: bool):
    pts = [(cx - 0.62 * r, cy - 0.2 * r), (cx - 0.3 * r, cy - 0.2 * r), (cx + 0.05 * r, cy - 0.55 * r),
           (cx + 0.05 * r, cy + 0.55 * r), (cx - 0.3 * r, cy + 0.2 * r), (cx - 0.62 * r, cy + 0.2 * r)]
    d.polygon(pts, outline=ICON, width=w)
    if waves:
        d.arc([cx - 0.15 * r, cy - 0.38 * r, cx + 0.45 * r, cy + 0.38 * r], -50, 50, fill=ICON, width=w)
        d.arc([cx - 0.15 * r, cy - 0.7 * r, cx + 0.8 * r, cy + 0.7 * r], -50, 50, fill=ICON, width=w)
    else:
        d.line([(cx + 0.3 * r, cy - 0.3 * r), (cx + 0.75 * r, cy + 0.3 * r)], fill=ICON, width=w)
        d.line([(cx + 0.75 * r, cy - 0.3 * r), (cx + 0.3 * r, cy + 0.3 * r)], fill=ICON, width=w)


def _rot(points, cx, cy, deg):
    a = math.radians(deg)
    return [(cx + (x - cx) * math.cos(a) - (y - cy) * math.sin(a), cy + (x - cx) * math.sin(a) + (y - cy) * math.cos(a))
            for x, y in points]


def _pin(d, cx, cy, r, w, slash: bool):
    head = [(cx - 0.18 * r, cy - 0.55 * r), (cx + 0.18 * r, cy - 0.55 * r), (cx + 0.22 * r, cy - 0.05 * r),
            (cx + 0.5 * r, cy + 0.12 * r), (cx - 0.5 * r, cy + 0.12 * r), (cx - 0.22 * r, cy - 0.05 * r)]
    head = _rot(head, cx, cy, 38)
    d.polygon(head, outline=ICON, width=w)
    needle = _rot([(cx, cy + 0.12 * r), (cx, cy + 0.72 * r)], cx, cy, 38)
    d.line(needle, fill=ICON, width=w)
    if slash:
        d.line([(cx - 0.7 * r, cy - 0.7 * r), (cx + 0.7 * r, cy + 0.7 * r)], fill=ICON, width=w + 1)


def _warn(d, cx, cy, r, w):
    d.polygon([(cx, cy - 0.7 * r), (cx + 0.74 * r, cy + 0.58 * r), (cx - 0.74 * r, cy + 0.58 * r)], outline=ICON, width=w,
              )
    d.line([(cx, cy - 0.2 * r), (cx, cy + 0.18 * r)], fill=ICON, width=w)
    d.ellipse([cx - w * 0.6, cy + 0.32 * r - w * 0.6, cx + w * 0.6, cy + 0.32 * r + w * 0.6], fill=ICON)


def _trash(d, cx, cy, r, w):
    d.line([(cx - 0.55 * r, cy - 0.42 * r), (cx + 0.55 * r, cy - 0.42 * r)], fill=ICON, width=w)
    d.line([(cx - 0.18 * r, cy - 0.42 * r), (cx - 0.18 * r, cy - 0.62 * r), (cx + 0.18 * r, cy - 0.62 * r),
            (cx + 0.18 * r, cy - 0.42 * r)], fill=ICON, width=w)
    d.polygon([(cx - 0.42 * r, cy - 0.3 * r), (cx + 0.42 * r, cy - 0.3 * r), (cx + 0.34 * r, cy + 0.7 * r),
               (cx - 0.34 * r, cy + 0.7 * r)], outline=ICON, width=w)
    for dx in (-0.14, 0.14):
        d.line([(cx + dx * r, cy - 0.1 * r), (cx + dx * r, cy + 0.5 * r)], fill=ICON, width=max(2, w - 1))


def _doc(d, cx, cy, r, w):
    d.polygon([(cx - 0.5 * r, cy - 0.62 * r), (cx + 0.18 * r, cy - 0.62 * r), (cx + 0.5 * r, cy - 0.3 * r),
               (cx + 0.5 * r, cy + 0.62 * r), (cx - 0.5 * r, cy + 0.62 * r)], outline=ICON, width=w)
    for y in (-0.22, 0.02):
        d.line([(cx - 0.28 * r, cy + y * r), (cx + 0.12 * r, cy + y * r)], fill=ICON, width=max(2, w - 1))
    bx, by, br = cx + 0.42 * r, cy + 0.42 * r, 0.34 * r
    d.ellipse([bx - br, by - br, bx + br, by + br], fill=(14, 14, 15), outline=ICON, width=max(2, w - 1))
    k = br * 0.45
    d.line([(bx - k, by - k), (bx + k, by + k)], fill=ICON, width=max(2, w - 1))
    d.line([(bx + k, by - k), (bx - k, by + k)], fill=ICON, width=max(2, w - 1))


def _prompt(d, cx, cy, r, w):
    d.line([(cx - 0.5 * r, cy - 0.38 * r), (cx - 0.08 * r, cy), (cx - 0.5 * r, cy + 0.38 * r)], fill=ICON, width=w, joint="curve")
    d.line([(cx + 0.02 * r, cy + 0.42 * r), (cx + 0.55 * r, cy + 0.42 * r)], fill=ICON, width=w)


_ICON_FOR = {
    "ban": "ban", "dban": "ban", "banall": "ban", "unban": "unban", "mute": "mute", "dmute": "mute", "tmute": "mute",
    "unmute": "unmute", "kick": "kick", "dkick": "kick", "kickme": "kick", "pin": "pin", "unpin": "unpin", "warn": "warn",
    "dwarn": "warn", "swarn": "warn", "warns": "warn", "unwarn": "warn", "purge": "purge", "del": "doc", "delete": "doc",
}


def _draw_icon(d, kind: str, cx: float, cy: float, r: float):
    w = S(3.6)
    if kind in ("ban", "unban", "kick"):
        _user(d, cx - 0.05 * r, cy - 0.02 * r, r, w)
        _badge(d, cx - 0.05 * r, cy - 0.02 * r, r, w, {"ban": "ban", "unban": "plus", "kick": "minus"}[kind])
    elif kind == "mute":
        _speaker(d, cx, cy, r, w, False)
    elif kind == "unmute":
        _speaker(d, cx, cy, r, w, True)
    elif kind == "pin":
        _pin(d, cx, cy, r, w, False)
    elif kind == "unpin":
        _pin(d, cx, cy, r, w, True)
    elif kind == "warn":
        _warn(d, cx, cy, r, w)
    elif kind == "purge":
        _trash(d, cx, cy, r, w)
    elif kind == "doc":
        _doc(d, cx, cy, r, w)
    else:
        _prompt(d, cx, cy, r, w)


# ---------- cards ----------
def _card(base: Image.Image, x: float, y: float, w: float, h: float, cmd: str, desc: str):
    W = base.size[0]
    X0, Y0, X1, Y1 = S(x), S(y), S(x + w), S(y + h)
    box = (X0 - S(26), Y0 - S(26), X1 + S(26), Y1 + S(26))
    bw, bh = box[2] - box[0], box[3] - box[1]
    rad = S(26)

    outer = Image.new("L", (bw, bh), 0)
    ImageDraw.Draw(outer).rounded_rectangle([S(26), S(26), bw - S(26), bh - S(26)], radius=rad, fill=255)
    inner = Image.new("L", (bw, bh), 0)
    ImageDraw.Draw(inner).rounded_rectangle([S(26) + S(2.4), S(26) + S(2.4), bw - S(26) - S(2.4), bh - S(26) - S(2.4)],
                                            radius=rad - S(2), fill=255)
    border = ImageChops.subtract(outer, inner)

    _glow(base, border, 5, (255, 255, 255), 0.22, (box[0], box[1]))          # soft outer light
    body = _gradient((bw, bh), [(30, 30, 32), (11, 11, 12)])
    base.paste(body, (box[0], box[1]), inner)
    # glass shine on the top half
    shine = Image.new("L", (bw, bh), 0)
    ImageDraw.Draw(shine).rounded_rectangle([S(26) + S(3), S(26) + S(3), bw - S(26) - S(3), bh // 2], radius=rad - S(3), fill=26)
    base.paste(Image.new("RGB", (bw, bh), (255, 255, 255)), (box[0], box[1]), ImageChops.multiply(shine, inner))
    edge = _gradient((bw, bh), [(235, 238, 242), (82, 84, 90), (170, 174, 180)], horizontal=True)
    edge = ImageChops.blend(edge, _gradient((bw, bh), [(255, 255, 255), (60, 62, 66)]), 0.5)
    base.paste(edge, (box[0], box[1]), border)

    d = ImageDraw.Draw(base)
    cy = y + h / 2
    # icon circle
    icx, icr = x + 64, 40
    circ = Image.new("L", (S(icr * 2 + 12), S(icr * 2 + 12)), 0)
    cd = ImageDraw.Draw(circ)
    c0 = S(6)
    cd.ellipse([c0, c0, c0 + S(icr * 2), c0 + S(icr * 2)], fill=255)
    cin = Image.new("L", circ.size, 0)
    ImageDraw.Draw(cin).ellipse([c0 + S(2.6), c0 + S(2.6), c0 + S(icr * 2 - 2.6), c0 + S(icr * 2 - 2.6)], fill=255)
    ring = ImageChops.subtract(circ, cin)
    cpos = (S(icx - icr - 6), S(cy - icr - 6))
    base.paste(Image.new("RGB", circ.size, (13, 13, 14)), cpos, cin)
    base.paste(_gradient(circ.size, [(255, 255, 255), (110, 114, 120)]), cpos, ring)
    _draw_icon(d, _ICON_FOR.get(cmd[1:], "prompt"), S(icx), S(cy), S(icr * 0.55))

    # command
    cf, _ = _fit_font("bold", cmd, 35, 190, 20)
    asc, desc_h = cf.getmetrics()
    tx = S(x + 126)
    d.text((tx, S(cy) - (asc + desc_h) / 2 - S(2)), cmd, font=cf, fill=(250, 250, 250))
    # divider
    dx = max(x + 270, (tx + _text_w(cf, cmd)) / SS + 40)
    dx = min(dx, x + w - 190)
    d.line([(S(dx), S(cy - 22)), (S(dx), S(cy + 22))], fill=(120, 123, 128), width=S(2))
    # description
    avail = x + w - 30 - (dx + 32)
    df, _ = _fit_font("regular", desc, 27, avail, 19)
    text = _ellipsize(df, desc, avail)
    a2, d2 = df.getmetrics()
    d.text((S(dx + 32), S(cy) - (a2 + d2) / 2 - S(1)), text, font=df, fill=(206, 209, 213))


def _sparkle(base: Image.Image, cx: float, cy: float, r: float):
    W = base.size[0]
    mask = Image.new("L", (W, W), 0)
    md = ImageDraw.Draw(mask)
    k = 0.22
    pts = [(cx, cy - r), (cx + r * k, cy - r * k), (cx + r, cy), (cx + r * k, cy + r * k),
           (cx, cy + r), (cx - r * k, cy + r * k), (cx - r, cy), (cx - r * k, cy - r * k)]
    md.polygon([(S(x), S(y)) for x, y in pts], fill=255)
    box = (S(cx - r - 40), S(cy - r - 40), S(cx + r + 40), S(cy + r + 40))
    sub = mask.crop(box)
    _glow(base, sub, 9, (255, 255, 255), 0.7, (box[0], box[1]))
    base.paste(Image.new("RGB", sub.size, (250, 250, 252)), (box[0], box[1]), sub)


def render_card(title: str, items: List[Tuple[str, str]], page: int = 1, pages: int = 1) -> Image.Image:
    """One picture with up to 10 commands (2 columns x 5 rows)."""
    base = _background()
    _logo(base, SIZE / 2, 168, 118)
    _title(base, BRAND, 395)
    _subtitle(base, f"{title} COMMANDS", 487)

    rows = max(1, math.ceil(len(items) / 2))
    ch, gap = 100, 17
    total = rows * ch + (rows - 1) * gap
    band_top, band_bot = 548, 1113
    y0 = band_top + (band_bot - band_top - total) / 2
    cols_x = [88, 641]
    cw = 525
    for i, (cmd, desc) in enumerate(items):
        r, c = divmod(i, 2)
        _card(base, cols_x[c], y0 + r * (ch + gap), cw, ch, cmd, desc)

    _fade_line(base, 320, 585, 1165, True)
    _fade_line(base, 669, 934, 1165, False)
    _sparkle(base, SIZE / 2, 1165, 17)
    if pages > 1:
        f = _font("medium", 26)
        t = f"PAGE {page} / {pages}"
        tw = _text_w(f, t, 4)
        _draw_spaced(ImageDraw.Draw(base), ((base.size[0] - tw) / 2, S(1198)), t, f, (160, 164, 170), 4)
    return base.resize((SIZE, SIZE), Image.LANCZOS)


# ════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ════════════════════════════════════════════════════════════════════
@dataclass
class Card:
    path: str          # picture file on disk
    cache_key: str     # same key = same picture (lets the bot reuse Telegram's file_id)
    page: int
    pages: int
    title: str         # "ADMIN"


_LOCKS: Dict[str, asyncio.Lock] = {}


def static_card_path(key_or_name: str) -> Optional[str]:
    """A ready-made picture for this module (data/help_cards/<name>.jpg|png|jpeg|webp), if there is one."""
    name = canon_key(key_or_name)
    if not name:
        return None
    for ext in ("jpg", "jpeg", "png", "webp"):
        p = os.path.join(CARD_DIR, f"{name}.{ext}")
        if os.path.isfile(p):
            return p
    return None


def _file_sig(path: str) -> str:
    st = os.stat(path)
    return f"{st.st_size}-{int(st.st_mtime)}"


def _render_to_file(title: str, items: List[Tuple[str, str]], page: int, pages: int, out: str) -> None:
    img = render_card(title, items, page, pages)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = out + ".tmp"
    img.save(tmp, "JPEG", quality=92, subsampling=0, optimize=True)
    os.replace(tmp, out)


async def get_card(module_key: str, help_text: str, page: int = 0) -> Optional[Card]:
    """Card for one page of a module, or None when the module has nothing to show as a picture."""
    static = static_card_path(module_key)
    if static:
        return Card(static, f"static:{canon_key(module_key)}:{_file_sig(static)}", 0, 1, display_name(module_key))

    items = parse_commands(help_text)
    if len(items) < 2:
        return None
    pages = max(1, math.ceil(len(items) / PER_PAGE))
    page = max(0, min(int(page), pages - 1))
    chunk = items[page * PER_PAGE:(page + 1) * PER_PAGE]
    title = display_name(module_key)
    sig = hashlib.sha1((VERSION + BRAND + title + repr(chunk) + f"{page}/{pages}").encode("utf-8")).hexdigest()[:20]
    out = os.path.join(CACHE_DIR, f"{canon_key(module_key) or 'help'}_{sig}.jpg")
    if not os.path.isfile(out):
        lock = _LOCKS.setdefault(out, asyncio.Lock())
        async with lock:
            if not os.path.isfile(out):
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, _render_to_file, title, chunk, page + 1, pages, out)
    return Card(out, f"dyn:{sig}", page, pages, title)
