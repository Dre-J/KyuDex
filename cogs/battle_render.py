"""
Battle scene renderer for the combat cog.

Layered scene: sky gradient -> far hills -> horizon haze -> ground gradient,
sprites grounded on elliptical platforms with contact shadows, HP panels with
threshold-coloured bars, weather as an atmospheric layer rather than a text tag.
Everything is drawn at 2x and downsampled so the ellipses and rounded corners
come out antialiased.

Nothing in here touches discord.py or the database on purpose -- `combat.py`
maps battle state onto `Combatant` objects and calls `render_scene`, which is
pure CPU work and must be run off the event loop (see `render_png`).
"""

import os
import random
from dataclasses import dataclass, field
from functools import lru_cache
from io import BytesIO
from typing import Dict, Optional, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ---------------------------------------------------------------- constants

W, H = 800, 450          # output size (16:9 downsizes cleanly in Discord)
SS = 2                   # supersample factor
HORIZON = 250            # y of the sky/ground boundary

# Layout, in output-space pixels. Classic crossed layout: opponent upper-right
# with its panel upper-left, player lower-left with its panel lower-right.
OPP_PLATFORM = (566, 250, 118, 30)      # cx, cy, rx, ry
PLR_PLATFORM = (236, 372, 152, 39)
OPP_SPRITE = (566, 252, 132)            # cx, base_y, height
PLR_SPRITE = (236, 376, 176)
OPP_PANEL = (30, 28, 300, 76)           # x, y, w, h
PLR_PANEL = (470, 330, 300, 76)


# ---------------------------------------------------------------- fonts

# Poppins if the host happens to have it, then the platform UI font, then
# anything with a full glyph set. Resolved once and cached.
_FONT_CANDIDATES = {
    "bold": [
        "Poppins-Bold.ttf", "segoeuib.ttf", "arialbd.ttf",
        "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "Helvetica.ttc",
    ],
    "medium": [
        "Poppins-Medium.ttf", "segoeui.ttf", "arial.ttf",
        "DejaVuSans.ttf", "LiberationSans-Regular.ttf", "Helvetica.ttc",
    ],
    # Needs the Mars/Venus glyphs, which Poppins does not carry.
    "symbol": [
        "seguisym.ttf", "DejaVuSans.ttf", "segoeui.ttf",
        "ARIALUNI.TTF", "arial.ttf", "Helvetica.ttc",
    ],
}

_FONT_DIRS = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "fonts"),
    os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"),
    "/usr/share/fonts/truetype/google-fonts",
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/truetype/liberation",
    "/usr/share/fonts",
    "/Library/Fonts",
    "/System/Library/Fonts",
    os.path.expanduser("~/.fonts"),
]


@lru_cache(maxsize=None)
def _resolve_font(role: str) -> Optional[str]:
    """Find a usable font file for a role, or None to fall back to PIL's default."""
    for name in _FONT_CANDIDATES[role]:
        for directory in _FONT_DIRS:
            path = os.path.join(directory, name)
            if os.path.exists(path):
                return path
        # PIL also searches the platform font path by bare name.
        try:
            ImageFont.truetype(name, 12)
            return name
        except OSError:
            continue
    return None


# A codepoint no font can define. Anything that renders identically to this is
# being drawn as .notdef - the hollow box (often with a cross) rather than a real glyph.
# Deliberately NOT a Private Use codepoint: symbol fonts routinely define those.
_MISSING_SENTINEL = chr(0xFFFF)   # a permanent noncharacter; no font maps it


@lru_cache(maxsize=None)
def has_glyph(role: str, size: int, ch: str) -> bool:
    """
    Whether this role's resolved font actually carries `ch`.

    Resolution only checks that a font FILE exists, never that it contains the character
    we want - so on a host without Segoe UI Symbol or DejaVu, the Mars and Venus signs
    came out as boxes. Callers use this to fall back to something always drawable.
    """
    try:
        f = font(role, size)
        return bytes(f.getmask(ch)) != bytes(f.getmask(_MISSING_SENTINEL))
    except Exception:
        return False


@lru_cache(maxsize=None)
def font(role: str, size: int):
    """Font at `size` output-space points (scaled up by SS internally)."""
    path = _resolve_font(role)
    if path is None:
        try:
            return ImageFont.load_default(size=size * SS)
        except TypeError:      # Pillow < 10.1
            return ImageFont.load_default()
    return ImageFont.truetype(path, size * SS)


# ---------------------------------------------------------------- palettes

BIOMES = {
    "grassland": {
        "sky_top": (108, 176, 232), "sky_bot": (186, 222, 244),
        "hills": [(96, 150, 106), (118, 172, 118)],
        "ground_far": (126, 184, 116), "ground_near": (74, 134, 76),
        "platform": (108, 166, 100), "platform_rim": (86, 138, 82),
    },
    "cave": {
        "sky_top": (28, 26, 44), "sky_bot": (58, 52, 78),
        "hills": [(40, 38, 58), (52, 48, 72)],
        "ground_far": (78, 70, 92), "ground_near": (46, 42, 58),
        "platform": (92, 84, 104), "platform_rim": (66, 60, 78),
    },
    "water": {
        "sky_top": (120, 190, 240), "sky_bot": (198, 232, 250),
        "hills": [(72, 138, 186), (94, 164, 208)],
        "ground_far": (86, 166, 214), "ground_near": (44, 110, 168),
        "platform": (120, 194, 226), "platform_rim": (88, 156, 196),
    },
    "volcanic": {
        "sky_top": (58, 32, 40), "sky_bot": (128, 62, 48),
        "hills": [(64, 40, 44), (86, 52, 50)],
        "ground_far": (92, 56, 52), "ground_near": (52, 34, 36),
        "platform": (104, 62, 54), "platform_rim": (72, 42, 40),
    },
    "snow": {
        "sky_top": (156, 186, 214), "sky_bot": (214, 230, 242),
        "hills": [(180, 200, 218), (204, 220, 234)],
        "ground_far": (232, 240, 248), "ground_near": (198, 214, 230),
        "platform": (240, 246, 252), "platform_rim": (196, 212, 228),
    },
    "night": {
        "sky_top": (18, 22, 52), "sky_bot": (52, 58, 100),
        "hills": [(30, 36, 66), (42, 48, 82)],
        "ground_far": (52, 66, 74), "ground_near": (30, 40, 48),
        "platform": (58, 74, 78), "platform_rim": (40, 54, 58),
    },
    "desert": {
        "sky_top": (132, 178, 216), "sky_bot": (232, 214, 174),
        "hills": [(198, 168, 118), (216, 188, 138)],
        "ground_far": (228, 200, 148), "ground_near": (196, 162, 108),
        "platform": (222, 194, 142), "platform_rim": (188, 158, 108),
    },
}

DEFAULT_BIOME = "grassland"

# Warden sectors map onto the palettes above. Wild encounters and PvP have no
# sector, so they fall through to DEFAULT_BIOME.
SECTOR_BIOMES = {
    "canopy": "grassland",
    "trench": "water",
    "core": "volcanic",
    "sprawl": "night",
    "apex": "snow",
}

# Weather: an RGBA tint over the whole scene + a particle style + a badge.
WEATHER = {
    "rain":       {"tint": (48, 78, 128, 62),   "particles": "rain",  "label": "Rain",       "accent": (96, 150, 220)},
    "heavy_rain": {"tint": (30, 54, 104, 96),   "particles": "rain",  "label": "Heavy Rain", "accent": (72, 120, 210)},
    "sun":        {"tint": (255, 206, 120, 52), "particles": "sun",   "label": "Sunny",      "accent": (245, 176, 60)},
    "harsh_sun":  {"tint": (255, 176, 72, 86),  "particles": "sun",   "label": "Harsh Sun",  "accent": (240, 140, 40)},
    "sandstorm":  {"tint": (198, 158, 96, 96),  "particles": "sand",  "label": "Sandstorm",  "accent": (196, 156, 92)},
    "hail":       {"tint": (180, 208, 232, 68), "particles": "hail",  "label": "Hail",       "accent": (150, 194, 226)},
    "snow":       {"tint": (198, 216, 236, 62), "particles": "snow",  "label": "Snow",       "accent": (176, 202, 228)},
    "fog":        {"tint": (188, 192, 198, 92), "particles": "fog",   "label": "Fog",        "accent": (168, 174, 182)},
}

# The engine's weather vocabulary differs from the renderer's.
WEATHER_ALIASES = {
    "none": None, "clear": None, "": None,
    "sand": "sandstorm", "sandstorm": "sandstorm",
    "sun": "sun", "sunny": "sun", "harsh-sun": "harsh_sun", "harsh_sun": "harsh_sun",
    "drought": "harsh_sun", "extremely-harsh-sunlight": "harsh_sun",
    "rain": "rain", "rainy": "rain", "heavy-rain": "heavy_rain", "heavy_rain": "heavy_rain",
    "drizzle": "rain", "heavy-rainfall": "heavy_rain",
    "hail": "hail", "snow": "snow", "snowstorm": "snow",
    "fog": "fog", "mist": "fog",
}

# The engine stores full status names; the panel shows three-letter codes.
STATUS_CODES = {
    "burn": "BRN", "poison": "PSN", "badly-poison": "TOX", "toxic": "TOX",
    "bad-poison": "TOX", "paralysis": "PAR", "paralyze": "PAR", "paralyzed": "PAR",
    "sleep": "SLP", "asleep": "SLP", "freeze": "FRZ", "frozen": "FRZ",
}

STATUS_COLORS = {
    "BRN": (240, 104, 68), "PSN": (168, 96, 200), "TOX": (140, 72, 176),
    "PAR": (240, 200, 64), "SLP": (140, 148, 168), "FRZ": (110, 196, 232),
}

AURA_STYLE = {
    "dynamax":    {"color": (232, 72, 96),   "tag": "DYNAMAX",    "scale": 1.35},
    "gigantamax": {"color": (216, 60, 140),  "tag": "GIGANTAMAX", "scale": 1.45},
    "mega":       {"color": (120, 108, 232), "tag": "MEGA",       "scale": 1.10},
    "tera":       {"color": (86, 208, 208),  "tag": "TERA",       "scale": 1.00},
}

# `state['adaptation']['type']` -> aura. 'zmove' is a move, not a form, so it
# has no persistent aura.
ADAPTATION_AURAS = {"dynamax": "dynamax", "gmax": "gigantamax", "mega": "mega", "tera": "tera"}

HAZARD_STYLE = {
    "stealth-rock": {"label": "ROCKS",   "color": (150, 112, 72)},
    "spikes":       {"label": "SPIKES",  "color": (152, 158, 172)},
    "toxic-spikes": {"label": "T.SPIKE", "color": (150, 92, 178)},
    "sticky-web":   {"label": "WEB",     "color": (112, 172, 116)},
}


# ---------------------------------------------------------------- helpers

def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(len(a)))


def vertical_gradient(size, top, bottom):
    """Smooth vertical gradient: draw a 1px column and stretch it."""
    w, h = size
    strip = Image.new("RGB", (1, h))
    px = strip.load()
    for y in range(h):
        px[0, y] = lerp(top, bottom, y / max(1, h - 1))
    return strip.resize((w, h), Image.BILINEAR)


def hp_color(ratio):
    """Threshold colouring -- the single biggest readability win over a flat bar."""
    if ratio > 0.5:
        return (76, 217, 100)
    if ratio > 0.2:
        return (255, 204, 0)
    return (255, 69, 58)


def _blurred_tile(base, box, draw_fn, blur):
    """
    Draw into a small tile, blur it, and composite it onto `base`.

    Blurring a 1600x900 canvas costs ~40ms a pop; the shadows and glows only
    ever cover a fraction of it, so this keeps the per-turn cost sane.
    `box` is (x0, y0, x1, y1) in supersampled space; `draw_fn` receives an
    ImageDraw bound to the tile plus the tile's origin offset.
    """
    pad = int(blur * 3)
    x0 = max(0, int(box[0]) - pad)
    y0 = max(0, int(box[1]) - pad)
    x1 = min(base.width, int(box[2]) + pad)
    y1 = min(base.height, int(box[3]) + pad)
    if x1 <= x0 or y1 <= y0:
        return
    tile = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(tile), (x0, y0))
    tile = tile.filter(ImageFilter.GaussianBlur(blur))
    base.alpha_composite(tile, (x0, y0))


def _blurred_overlay(base, overlay, pos, blur):
    """Blur an RGBA image inside a padded tile and composite it onto `base`."""
    pad = int(blur * 3)
    tile = Image.new("RGBA", (overlay.width + pad * 2, overlay.height + pad * 2), (0, 0, 0, 0))
    tile.alpha_composite(overlay, (pad, pad))
    tile = tile.filter(ImageFilter.GaussianBlur(blur))

    x, y = pos[0] - pad, pos[1] - pad
    # Clip against the canvas; alpha_composite refuses out-of-bounds offsets.
    cx0, cy0 = max(0, x), max(0, y)
    cx1, cy1 = min(base.width, x + tile.width), min(base.height, y + tile.height)
    if cx1 <= cx0 or cy1 <= cy0:
        return
    tile = tile.crop((cx0 - x, cy0 - y, cx1 - x, cy1 - y))
    base.alpha_composite(tile, (cx0, cy0))


def _fit_font(draw, text, role, max_size, min_size, max_width):
    """Largest font size in the range whose rendering of `text` fits `max_width`."""
    for size in range(max_size, min_size - 1, -1):
        f = font(role, size)
        if draw.textlength(text, font=f) <= max_width:
            return f
    return font(role, min_size)


# ---------------------------------------------------------------- data

@dataclass
class Combatant:
    name: str
    level: Optional[int] = None
    hp: int = 0
    max_hp: int = 1
    status: Optional[str] = None          # three-letter code, e.g. "BRN"
    gender: Optional[str] = None          # "M", "F", or None
    sprite: Optional[Image.Image] = None
    aura: Optional[str] = None            # dynamax | gigantamax | mega | tera
    hazards: Dict = field(default_factory=dict)
    placeholder_hue: Tuple[int, int, int] = (120, 150, 200)


# ---------------------------------------------------------------- scene parts

def draw_backdrop(img, biome):
    """Sky gradient, distant hills, horizon haze, ground gradient."""
    b = BIOMES[biome]
    w, h = img.size
    hz = HORIZON * SS

    img.paste(vertical_gradient((w, hz), b["sky_top"], b["sky_bot"]), (0, 0))
    img.paste(vertical_gradient((w, h - hz), b["ground_far"], b["ground_near"]), (0, hz))

    # Distant hill silhouettes give the horizon depth instead of a hard line.
    # Drawn, then clipped to the sky region so nothing bleeds onto the ground.
    hills = Image.new("RGBA", img.size, (0, 0, 0, 0))
    hd = ImageDraw.Draw(hills)
    rng = random.Random(7)
    for layer, color in enumerate(b["hills"]):
        base = hz + 2 * SS
        for i in range(5):
            cx = int(w * (0.02 + 0.24 * i + rng.uniform(-0.05, 0.05)))
            rx = int(w * rng.uniform(0.18, 0.30))
            ry = int(rng.uniform(30, 60) * SS) - layer * 12 * SS
            hd.ellipse([cx - rx, base - ry, cx + rx, base + ry], fill=color + (255,))
    hills = hills.filter(ImageFilter.GaussianBlur(1.2 * SS))
    clip = Image.new("L", img.size, 0)
    ImageDraw.Draw(clip).rectangle([0, 0, w, hz], fill=255)
    hills.putalpha(Image.composite(hills.split()[3], Image.new("L", img.size, 0), clip))
    img.paste(hills, (0, 0), hills)

    # Atmospheric haze band at the horizon so the seam disappears.
    haze = Image.new("RGBA", (w, 40 * SS), (0, 0, 0, 0))
    hzd = ImageDraw.Draw(haze)
    band = 26 * SS
    for i in range(band):
        a = int(70 * (1 - i / band))
        hzd.line([(0, 14 * SS + i), (w, 14 * SS + i)], fill=b["sky_bot"] + (a,))
    haze = haze.filter(ImageFilter.GaussianBlur(3 * SS))
    img.alpha_composite(haze, (0, hz - 40 * SS))


def draw_platform(img, cx, cy, rx, ry, biome):
    """Elliptical stage under a sprite, so the Pokemon is grounded, not floating."""
    b = BIOMES[biome]
    cx, cy, rx, ry = cx * SS, cy * SS, rx * SS, ry * SS

    # Ambient occlusion ring, so the disc sits *in* the ground, not on top of it.
    _blurred_tile(
        img,
        (cx - rx * 1.2, cy - ry * 1.2, cx + rx * 1.2, cy + ry * 1.2 + 12 * SS),
        lambda d, o: d.ellipse(
            [cx - rx * 1.10 - o[0], cy - ry * 1.10 + 6 * SS - o[1],
             cx + rx * 1.10 - o[0], cy + ry * 1.10 + 6 * SS - o[1]],
            fill=(0, 0, 0, 70)),
        7 * SS)

    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    rim = lerp(b["platform_rim"], (0, 0, 0), 0.18)
    d.ellipse([cx - rx, cy - ry + 8 * SS, cx + rx, cy + ry + 8 * SS], fill=rim + (255,))
    top = lerp(b["platform"], (255, 255, 255), 0.10)
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=top + (255,))
    d.ellipse([cx - rx * 0.80, cy - ry * 0.76, cx + rx * 0.80, cy + ry * 0.26],
              fill=lerp(b["platform"], (255, 255, 255), 0.26) + (170,))

    layer = layer.filter(ImageFilter.GaussianBlur(0.6 * SS))
    img.alpha_composite(layer)


def contact_shadow(img, cx, cy, rx, ry):
    _blurred_tile(
        img,
        ((cx - rx) * SS, (cy - ry) * SS, (cx + rx) * SS, (cy + ry) * SS),
        lambda d, o: d.ellipse(
            [(cx - rx) * SS - o[0], (cy - ry) * SS - o[1],
             (cx + rx) * SS - o[0], (cy + ry) * SS - o[1]],
            fill=(0, 0, 0, 105)),
        6 * SS)


def placeholder_sprite(size, hue):
    """Abstract stand-in creature so the layout still reads if artwork is missing."""
    s = size * SS
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    dark = lerp(hue, (0, 0, 0), 0.35)
    light = lerp(hue, (255, 255, 255), 0.25)

    d.ellipse([s * 0.14, s * 0.34, s * 0.86, s * 0.96], fill=hue + (255,))
    d.ellipse([s * 0.24, s * 0.44, s * 0.76, s * 0.80], fill=light + (255,))
    d.ellipse([s * 0.26, s * 0.06, s * 0.74, s * 0.56], fill=hue + (255,))
    d.polygon([(s * 0.30, s * 0.18), (s * 0.20, s * 0.00), (s * 0.44, s * 0.10)], fill=dark + (255,))
    d.polygon([(s * 0.70, s * 0.18), (s * 0.80, s * 0.00), (s * 0.56, s * 0.10)], fill=dark + (255,))
    d.ellipse([s * 0.37, s * 0.24, s * 0.45, s * 0.36], fill=(255, 255, 255, 255))
    d.ellipse([s * 0.55, s * 0.24, s * 0.63, s * 0.36], fill=(255, 255, 255, 255))
    d.ellipse([s * 0.39, s * 0.28, s * 0.44, s * 0.34], fill=(20, 20, 30, 255))
    d.ellipse([s * 0.57, s * 0.28, s * 0.62, s * 0.34], fill=(20, 20, 30, 255))
    return im


def place_sprite(img, mon, cx, base_y, target_h, flip=False):
    """Anchor a sprite bottom-centre at (cx, base_y), with aura glow + contact shadow."""
    scale = AURA_STYLE.get(mon.aura, {}).get("scale", 1.0)
    target_h = int(target_h * scale)

    spr = mon.sprite or placeholder_sprite(target_h, mon.placeholder_hue)

    # Official artwork is a padded square; trimming to the opaque pixels is what
    # actually plants the sprite on the platform instead of hovering above it.
    bbox = spr.getbbox()
    if bbox:
        spr = spr.crop(bbox)

    ratio = spr.width / max(1, spr.height)
    spr = spr.resize((max(1, int(target_h * SS * ratio)), max(1, int(target_h * SS))),
                     Image.LANCZOS)
    if flip:
        spr = spr.transpose(Image.FLIP_LEFT_RIGHT)

    x = int(cx * SS - spr.width / 2)
    y = int(base_y * SS - spr.height)

    contact_shadow(img, cx, base_y - 2, target_h * 0.34, target_h * 0.10)

    if mon.aura in AURA_STYLE:
        color = AURA_STYLE[mon.aura]["color"]
        tinted = Image.new("RGBA", spr.size, color + (255,))
        tinted.putalpha(spr.split()[3].point(lambda p: int(p * 0.9)))
        _blurred_overlay(img, tinted, (x, y), 9 * SS)

    img.alpha_composite(spr, (x, y))


# ---------------------------------------------------------------- hp panels

def draw_hp_panel(img, mon, box, show_numbers):
    """box = (x, y, w, h) in output-space pixels."""
    x, y, w, h = box
    X, Y, Wd, Ht = x * SS, y * SS, w * SS, h * SS

    # Soft drop shadow, so the panel lifts off the background.
    _blurred_tile(
        img, (X, Y, X + Wd, Y + Ht + 8 * SS),
        lambda d, o: d.rounded_rectangle(
            [X - o[0], Y + 4 * SS - o[1], X + Wd - o[0], Y + Ht + 4 * SS - o[1]],
            radius=12 * SS, fill=(0, 0, 0, 110)),
        5 * SS)

    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle([X, Y, X + Wd, Y + Ht], radius=12 * SS,
                        fill=(26, 32, 44, 232),
                        outline=(255, 255, 255, 34), width=2 * SS)

    f_lvl = font("medium", 12)
    f_num = font("medium", 11)
    f_tag = font("bold", 9)

    pad = 13 * SS

    # Level + gender are right-aligned and laid out first, so the name knows how
    # much room it actually has and can shrink instead of colliding.
    right = X + Wd - pad
    gender_glyph = {"M": "\u2642", "F": "\u2640"}.get(mon.gender)
    if gender_glyph:
        # Fall back to a plain letter when the host has no font carrying the Mars/Venus
        # signs, rather than letting PIL draw .notdef as a coloured box.
        if has_glyph("symbol", 13, gender_glyph):
            f_gen = font("symbol", 13)
        else:
            gender_glyph = mon.gender
            f_gen = font("bold", 11)
        gw = d.textlength(gender_glyph, font=f_gen)
        gcol = (108, 176, 240) if mon.gender == "M" else (240, 128, 176)
        d.text((right - gw, Y + 12 * SS), gender_glyph, font=f_gen, fill=gcol + (255,))
        right -= gw + 6 * SS

    if mon.level is not None:
        lvl = f"Lv{mon.level}"
        lw = d.textlength(lvl, font=f_lvl)
        d.text((right - lw, Y + 13 * SS), lvl, font=f_lvl, fill=(176, 186, 204, 255))
        right -= lw + 8 * SS

    # Form names like "charizard-mega-x" read as "CHARIZARD MEGA X".
    label = str(mon.name or "?").replace("-", " ").replace("_", " ").upper()
    f_name = _fit_font(d, label, "bold", 15, 9, max(1, right - (X + pad)))
    d.text((X + pad, Y + 10 * SS), label, font=f_name, fill=(255, 255, 255, 255))

    # HP track
    ratio = max(0.0, min(1.0, mon.hp / max(1, mon.max_hp)))
    bar_y = Y + 36 * SS
    bar_h = 9 * SS
    bx0, bx1 = X + pad, X + Wd - pad
    d.rounded_rectangle([bx0, bar_y, bx1, bar_y + bar_h],
                        radius=bar_h // 2, fill=(56, 64, 82, 255))
    if ratio > 0:
        fill_w = max(bar_h, int((bx1 - bx0) * ratio))
        d.rounded_rectangle([bx0, bar_y, bx0 + fill_w, bar_y + bar_h],
                            radius=bar_h // 2, fill=hp_color(ratio) + (255,))

    row_y = bar_y + bar_h + 7 * SS

    # Status and aura flow left-to-right as pills, so they can never collide
    # with the right-aligned HP numbers.
    def pill(cursor, text, color):
        tw = d.textlength(text, font=f_tag)
        w_pill = tw + 14 * SS
        d.rounded_rectangle([cursor, row_y, cursor + w_pill, row_y + 15 * SS],
                            radius=7 * SS, fill=color + (255,))
        d.text((cursor + 7 * SS, row_y + 2 * SS), text, font=f_tag, fill=(255, 255, 255, 255))
        return cursor + w_pill + 6 * SS

    cur = X + pad
    if mon.status:
        cur = pill(cur, mon.status, STATUS_COLORS.get(mon.status, (140, 148, 168)))
    if mon.aura in AURA_STYLE:
        cur = pill(cur, AURA_STYLE[mon.aura]["tag"], AURA_STYLE[mon.aura]["color"])

    # Numeric HP on the player side only, mirroring the mainline games.
    if show_numbers:
        txt = f"{max(0, mon.hp)} / {mon.max_hp}"
        tw = d.textlength(txt, font=f_num)
        if X + Wd - pad - tw > cur:
            d.text((X + Wd - pad - tw, row_y + 1 * SS), txt, font=f_num,
                   fill=(206, 214, 230, 255))

    img.alpha_composite(layer)


def draw_hazard_chips(img, hazards, x, y, width):
    """
    Entry hazards as a compact chip row under the owning side's HP panel.

    `hazards` is the engine's dict: stealth-rock / sticky-web are flags,
    spikes / toxic-spikes are stack counts.
    """
    if not hazards:
        return

    chips = []
    if hazards.get("stealth-rock"):
        chips.append(("stealth-rock", HAZARD_STYLE["stealth-rock"]["label"]))
    if hazards.get("spikes", 0) > 0:
        chips.append(("spikes", f"{HAZARD_STYLE['spikes']['label']}x{hazards['spikes']}"))
    if hazards.get("toxic-spikes", 0) > 0:
        chips.append(("toxic-spikes", f"{HAZARD_STYLE['toxic-spikes']['label']}x{hazards['toxic-spikes']}"))
    if hazards.get("sticky-web"):
        chips.append(("sticky-web", HAZARD_STYLE["sticky-web"]["label"]))
    if not chips:
        return

    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = font("bold", 8)

    cur = x * SS
    limit = (x + width) * SS
    top, ch = y * SS, 14 * SS
    for key, text in chips:
        tw = d.textlength(text, font=f)
        w_chip = tw + 12 * SS
        if cur + w_chip > limit:
            break
        color = HAZARD_STYLE[key]["color"]
        d.rounded_rectangle([cur, top, cur + w_chip, top + ch], radius=5 * SS,
                            fill=(20, 24, 34, 214), outline=color + (235,), width=1 * SS)
        d.text((cur + 6 * SS, top + 1 * SS), text, font=f, fill=color + (255,))
        cur += w_chip + 5 * SS

    img.alpha_composite(layer)


# ---------------------------------------------------------------- weather

def _build_weather_overlay(key):
    cfg = WEATHER[key]
    size = (W * SS, H * SS)
    rng = random.Random(3)

    overlay = Image.new("RGBA", size, cfg["tint"])
    p = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(p)
    style = cfg["particles"]
    w, h = size

    if style == "rain":
        count = 150 if key == "heavy_rain" else 85
        length = 34 if key == "heavy_rain" else 24
        for _ in range(count):
            x, y = rng.randrange(-80, w), rng.randrange(0, h)
            d.line([(x, y), (x + 9 * SS, y + length * SS)],
                   fill=(205, 226, 246, rng.randint(90, 165)), width=SS)
    elif style in ("snow", "hail"):
        for _ in range(90):
            x, y = rng.randrange(0, w), rng.randrange(0, h)
            r = rng.randint(2, 4) * SS
            d.ellipse([x, y, x + r, y + r], fill=(255, 255, 255, rng.randint(120, 215)))
    elif style == "sand":
        for _ in range(120):
            x, y = rng.randrange(0, w), rng.randrange(0, h)
            d.line([(x, y), (x + rng.randint(20, 60) * SS, y)],
                   fill=(226, 198, 146, rng.randint(70, 150)), width=SS)
    elif style == "sun":
        g = Image.new("RGBA", size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(g)
        for r in range(150, 0, -12):
            a = int(70 * (1 - r / 150))
            gd.ellipse([int(w * 0.80) - r * SS, int(h * 0.06) - r * SS,
                        int(w * 0.80) + r * SS, int(h * 0.06) + r * SS],
                       fill=(255, 232, 168, a))
        p.alpha_composite(g.filter(ImageFilter.GaussianBlur(10 * SS)))
    elif style == "fog":
        for _ in range(22):
            x, y = rng.randrange(0, w), rng.randrange(0, h)
            rx, ry = rng.randint(70, 190) * SS, rng.randint(16, 40) * SS
            d.ellipse([x - rx, y - ry, x + rx, y + ry],
                      fill=(226, 230, 236, rng.randint(22, 46)))
        p = p.filter(ImageFilter.GaussianBlur(9 * SS))

    overlay.alpha_composite(p)
    return overlay


def draw_weather_badge(img, key):
    """A compact pill rather than a bare [HEAVY-RAIN] text block."""
    cfg = WEATHER[key]
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = font("bold", 11)

    label = cfg["label"].upper()
    tw = d.textlength(label, font=f)
    pad_x, ph = 12 * SS, 26 * SS
    x1 = W * SS - 24 * SS
    x0 = x1 - (tw + pad_x * 2 + 16 * SS)
    y0 = 24 * SS

    d.rounded_rectangle([x0, y0, x1, y0 + ph], radius=13 * SS, fill=(26, 32, 44, 226))
    dot_r = 5 * SS
    d.ellipse([x0 + 11 * SS, y0 + ph / 2 - dot_r, x0 + 11 * SS + dot_r * 2, y0 + ph / 2 + dot_r],
              fill=cfg["accent"] + (255,))
    d.text((x0 + 11 * SS + dot_r * 2 + 7 * SS, y0 + 5 * SS), label, font=f,
           fill=(232, 238, 248, 255))
    img.alpha_composite(layer)


def _build_vignette(strength=76):
    size = (W * SS, H * SS)
    mask = Image.new("L", size, 0)
    d = ImageDraw.Draw(mask)
    m = int(size[0] * 0.16)
    d.rounded_rectangle([m, m, size[0] - m, size[1] - m], radius=60 * SS, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(60 * SS))
    dark = Image.new("RGBA", size, (10, 12, 24, strength))
    dark.putalpha(Image.eval(mask, lambda p: int((255 - p) * strength / 255)))
    return dark


# ---------------------------------------------------------------- caches

# The backdrop, weather overlays and vignette are deterministic and account for
# most of the render cost (large Gaussian blurs). They are built once per
# process and reused every turn.
_STAGE_CACHE: Dict[str, Image.Image] = {}
_WEATHER_CACHE: Dict[str, Image.Image] = {}
_VIGNETTE_CACHE = []


def _stage(biome):
    if biome not in _STAGE_CACHE:
        img = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 255))
        draw_backdrop(img, biome)
        draw_platform(img, *OPP_PLATFORM, biome)
        draw_platform(img, *PLR_PLATFORM, biome)
        _STAGE_CACHE[biome] = img
    return _STAGE_CACHE[biome].copy()


def _weather_overlay(key):
    if key not in _WEATHER_CACHE:
        _WEATHER_CACHE[key] = _build_weather_overlay(key)
    return _WEATHER_CACHE[key]


def _vignette():
    if not _VIGNETTE_CACHE:
        _VIGNETTE_CACHE.append(_build_vignette())
    return _VIGNETTE_CACHE[0]


# ---------------------------------------------------------------- normalisers

def normalize_weather(weather) -> Optional[str]:
    """Engine weather value (str, or the {'type': ...} dict) -> renderer key."""
    if isinstance(weather, dict):
        weather = weather.get("type")
    if not weather:
        return None
    key = str(weather).strip().lower().replace(" ", "-")
    key = WEATHER_ALIASES.get(key, key if key in WEATHER else None)
    return key if key in WEATHER else None


def normalize_status(status) -> Optional[str]:
    """Engine status_condition dict (or plain name) -> three-letter code."""
    if isinstance(status, dict):
        status = status.get("name")
    if not status:
        return None
    key = str(status).strip().lower().replace(" ", "-")
    return STATUS_CODES.get(key, key[:3].upper())


def normalize_biome(sector) -> str:
    """Warden sector name -> biome palette; anything unknown falls back."""
    if not sector:
        return DEFAULT_BIOME
    key = str(sector).strip().lower()
    if key in BIOMES:
        return key
    return SECTOR_BIOMES.get(key, DEFAULT_BIOME)


def aura_for(adaptation) -> Optional[str]:
    """`state['adaptation']`-shaped dict -> aura name, or None when inactive."""
    if not isinstance(adaptation, dict) or not adaptation.get("active"):
        return None
    return ADAPTATION_AURAS.get(str(adaptation.get("type", "")).lower())


def load_sprite(pokedex_id, shiny=False, base_path=None) -> Optional[Image.Image]:
    """Load official artwork off local disk. Returns None when it isn't there."""
    if base_path is None:
        base_path = os.path.join("KyuSprites", "sprites", "pokemon", "other", "official-artwork")
    name = f"{pokedex_id}.png"
    path = os.path.join(base_path, "shiny", name) if shiny else os.path.join(base_path, name)
    if not os.path.exists(path):
        # Shiny artwork is patchier than the base set; fall back rather than
        # dropping to the placeholder blob.
        path = os.path.join(base_path, name)
        if not os.path.exists(path):
            return None
    try:
        return Image.open(path).convert("RGBA")
    except Exception as e:
        print(f"battle_render: failed to load {path}: {e}")
        return None


# ---------------------------------------------------------------- entry points

def render_scene(player: Combatant, opponent: Combatant,
                 biome: str = DEFAULT_BIOME, weather: Optional[str] = None) -> Image.Image:
    """Render the full battle scene. Pure CPU work -- call it off the event loop."""
    if biome not in BIOMES:
        biome = DEFAULT_BIOME
    img = _stage(biome)

    place_sprite(img, opponent, *OPP_SPRITE)
    place_sprite(img, player, *PLR_SPRITE, flip=True)

    if weather in WEATHER:
        img.alpha_composite(_weather_overlay(weather))

    img.alpha_composite(_vignette())

    draw_hp_panel(img, opponent, OPP_PANEL, show_numbers=False)
    draw_hp_panel(img, player, PLR_PANEL, show_numbers=True)

    # Hazards sit under the panel belonging to the side they were laid on.
    draw_hazard_chips(img, opponent.hazards,
                      OPP_PANEL[0], OPP_PANEL[1] + OPP_PANEL[3] + 6, OPP_PANEL[2])
    draw_hazard_chips(img, player.hazards,
                      PLR_PANEL[0], PLR_PANEL[1] + PLR_PANEL[3] + 6, PLR_PANEL[2])

    if weather in WEATHER:
        draw_weather_badge(img, weather)

    return img.resize((W, H), Image.LANCZOS).convert("RGB")


def render_png(player: Combatant, opponent: Combatant,
               biome: str = DEFAULT_BIOME, weather: Optional[str] = None) -> BytesIO:
    """render_scene, packaged as a rewound PNG buffer."""
    buf = BytesIO()
    render_scene(player, opponent, biome=biome, weather=weather).save(buf, format="PNG")
    buf.seek(0)
    return buf
