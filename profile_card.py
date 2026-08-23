"""
profile_card.py — PIL profile card renderer for KyuDex.

Design notes for the Pi 3:
  * Assets (fonts, backgrounds, sprites) are loaded ONCE at startup and kept in
    memory. Never call Image.open() on the hot path — SD-card I/O per render is
    the single biggest avoidable cost on a Pi.
  * render_profile_card() is synchronous and CPU-bound. Never await it directly
    on the event loop; use render_profile_card_async(), which pushes the work to
    a thread pool. PIL releases the GIL for most heavy ops, so threads help.
  * Output is WebP by default — typically 30-50% smaller than PNG at the same
    quality, which directly cuts Discord upload time.
  * Finished cards are cached by a hash of the profile payload, so repeated
    /profile calls cost nothing until the profile actually changes.

Requires: Pillow >= 9.2
"""

from __future__ import annotations

import asyncio
import functools
import hashlib
import io
import json
import logging
import math
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

log = logging.getLogger(__name__)

# Pillow moved the resampling constants onto an enum in 9.1 and has been threatening the
# old spelling ever since. Named once here so the deprecation, when it lands, is one line
# rather than a hunt through every resize call.
LANCZOS = getattr(getattr(Image, "Resampling", Image), "LANCZOS")

# --------------------------------------------------------------------------
# Layout constants
# --------------------------------------------------------------------------

CARD_W, CARD_H = 900, 380
PAD = 24
RADIUS = 20

AVATAR_BOX = (PAD + 8, PAD + 8, 200, 200)      # x, y, w, h
PARTY_SLOT = 74                                 # party sprite cell size
# Lifted off the panel's bottom edge. Sitting flush against it made the row read as
# something that had fallen out of the card rather than as part of it, and left the
# rounded corner with nothing to breathe against.
PARTY_INSET = 14
PARTY_Y = CARD_H - PAD - PARTY_SLOT - PARTY_INSET

# THE ENERGY NUMBERS COME FROM THE ENGINE, not from a second copy written out here.
# `utils/limits.py` is the module that actually spends and regenerates this, and a card
# that drew a full bar at 100 while the engine banked to 200 would be lying about the
# one number a player uses to decide whether to duel. The fallback is for running this
# file outside the bot's tree at all; it mirrors the current values and nothing more.
try:
    from utils.limits import (ENERGY_BANK_CAP, ENERGY_DEBT_FLOOR, ENERGY_MAX,
                              ENERGY_REGEN_PER_HOUR, energy_yield)
except Exception:                                           # pragma: no cover
    ENERGY_MAX, ENERGY_BANK_CAP, ENERGY_DEBT_FLOOR = 100, 200, -100
    ENERGY_REGEN_PER_HOUR = 10

    def energy_yield(energy):
        return 1.0 if (energy or 0) >= 0 else max(0.25, 0.5 ** (-energy / 50.0))

INK = (236, 240, 238, 255)
INK_DIM = (236, 240, 238, 196)
# The banked stretch of the energy bar and the deficit, which are the same colour on
# every biome on purpose: they mean the same thing whatever the accent is, and tinting
# them per biome would make "you are running on reserves" read as decoration.
BANKED = (245, 200, 92)
DEFICIT = (222, 92, 78)
# 205/255 was very nearly opaque, which made the background artwork a rumour: five
# beautifully distinct biomes all rendered as the same near-black rectangle. Dropped far
# enough that the art reads through it, and paid for by a stronger text shadow — the
# panel is there to keep type legible, not to hide the picture it sits on.
PANEL = (12, 17, 16, 158)
TRACK = (255, 255, 255, 46)
BADGE_PX = 52

# Accent per biome — this is what makes a card feel like *your* server's card.
#
# THESE ARE KYUDEX'S FIVE BIOMES, and they are the only five. The names here used to be
# an invented set (temperate, wetland, reef, oldgrowth, grassland, wasteland, rift) that
# matched nothing in the game: not `users.unlocked_visas`, not WARDEN_ROSTER, not the
# emoji map in `!profile`, and not the artwork in assets/backgrounds. Every lookup fell
# through to the default, so every card came out the same colour whatever biome it was
# for — the one thing this table exists to prevent.
#
# The colours are sampled from the backgrounds themselves: the most saturated mid-bright
# pixel in each, which is what the eye reads as "the colour of that picture". An average
# goes muddy grey, because most of any painting is shadow.
BIOME_ACCENT = {
    "canopy": (172, 88, 118),      # the rose-lit forest canopy
    "trench": (26, 152, 164),      # deep teal water
    "core": (196, 84, 44),         # magma orange
    "sprawl": (126, 96, 208),      # neon violet of the city at night
    "apex": (72, 132, 214),        # cold sky blue
}
DEFAULT_BIOME = "canopy"

# The pretty name for each, matching the wording `!profile` already uses.
BIOME_LABEL = {
    "canopy": "Canopy",
    "trench": "Trench",
    "core": "Core",
    "sprawl": "Sprawl",
    "apex": "Apex",
}

FONT_CANDIDATES = {
    "bold": [
        "assets/fonts/Inter-Bold.ttf",
        # Windows, where this is being developed. Without these the loader fell all the
        # way through to ImageFont.load_default(), which is a fixed-size bitmap face that
        # ignores the `size` argument entirely — every heading rendered at the same tiny
        # size and the layout looked broken rather than unstyled.
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ],
    "regular": [
        "assets/fonts/Inter-Regular.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/google-fonts/Poppins-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ],
}


# --------------------------------------------------------------------------
# Data payload
# --------------------------------------------------------------------------

@dataclass
class ProfileData:
    """Everything the card needs. Build this from your DB, pass it in."""
    user_name: str
    trainer_title: str = "Novice Ranger"
    trainer_level: int = 1
    xp_current: int = 0
    xp_needed: int = 100
    biome: str = DEFAULT_BIOME

    eco_tokens: int = 0
    caught: int = 0
    shinies: int = 0

    # `ladder_tier` USED TO LIVE HERE and is gone. It implied a PvP ranking that does not
    # exist - nothing in the database ever produced one - so the card was printing a
    # confident number for a system that had never been built. The slot shows VISAS
    # instead, which is real, is already the game's progression spine, and is the thing
    # the badge strip along the bottom is a picture of.
    visas: list[str] = field(default_factory=list)   # biome keys, in unlock order

    # Field Energy, as `users.current_energy` holds it: 0..energy_cap, and NEGATIVE down
    # to ENERGY_DEBT_FLOOR once a trainer has duelled past their reserve. Passed through
    # as stored rather than clamped by the caller, because the three states are what the
    # bar is for.
    energy: int = ENERGY_MAX
    # THIS TRAINER'S ceiling, which their level raises - not the global constant. The bar
    # is drawn to this width, so a levelled trainer's banked stretch is visibly longer
    # rather than being silently clipped at everybody else's cap.
    energy_cap: int = ENERGY_BANK_CAP

    # The trainer's own sky and clock, already resolved through their timezone. Held as
    # text and a set of sky names rather than a datetime so the card never has to know
    # what a zone is - `utils/prefs` owns that, and the card owns how it looks.
    local_time: str = ""                             # "22:14", or "" to hide the chip
    skies: tuple[str, ...] = ()                      # 'day'/'night' + 'dusk'/'full-moon'

    # `eco_score` USED TO LIVE HERE and is deliberately gone. It is a property of the
    # SERVER's habitat, not of the trainer - every member of a guild has the same one -
    # so a personal card was the wrong place to print it. It belongs in the server embed.

    trainer_sprite: str | None = None       # filename in sprites/trainers/
    background: str = DEFAULT_BIOME         # filename stem in backgrounds/
    party: list[str] = field(default_factory=list)   # sprite filenames
    badges: list[str] = field(default_factory=list)  # badge filenames

    def cache_key(self) -> str:
        blob = json.dumps(self.__dict__, sort_keys=True, default=str)
        return hashlib.sha1(blob.encode()).hexdigest()


# --------------------------------------------------------------------------
# Asset cache
# --------------------------------------------------------------------------

class AssetCache:
    """Loads every image and font once. Call warm() during bot startup."""

    def __init__(self, root: str | Path = "assets"):
        self.root = Path(root)
        self.backgrounds: dict[str, Image.Image] = {}
        self.trainers: dict[str, Image.Image] = {}
        self.pokemon: dict[str, Image.Image] = {}
        self.badges: dict[str, Image.Image] = {}
        self._fonts: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}

    # -- fonts -------------------------------------------------------------
    def font(self, weight: str, size: int) -> ImageFont.FreeTypeFont:
        key = (weight, size)
        if key not in self._fonts:
            for path in FONT_CANDIDATES[weight]:
                try:
                    self._fonts[key] = ImageFont.truetype(path, size)
                    break
                except OSError:
                    continue
            else:
                log.warning("No font found for %s; using PIL default", weight)
                self._fonts[key] = ImageFont.load_default()
        return self._fonts[key]

    # -- images ------------------------------------------------------------
    def _load_dir(self, sub: str, target: dict, size: tuple[int, int] | None,
                  cover: bool = False, root: Path | None = None):
        d = (root or self.root) / sub if sub else (root or self.root)
        if not d.is_dir():
            log.warning("Asset dir missing: %s", d)
            return
        for f in sorted(d.iterdir()):
            if f.suffix.lower() not in (".png", ".webp", ".jpg", ".jpeg"):
                continue
            try:
                img = Image.open(f).convert("RGBA")
                if size:
                    # `cover` SCALES AND CROPS; a plain resize squashes. The backgrounds
                    # are 4000x2400-ish and the card is 900x380, so resizing straight to
                    # the card size flattened every one of them to two-fifths of its
                    # height — and because the distortion happened here, at load time,
                    # the _fit_cover call in the renderer had nothing left to fix.
                    img = _fit_cover(img, *size) if cover else img.resize(size, LANCZOS)
                target[f.stem] = img
            except Exception:
                log.exception("Failed to load %s", f)

    def load_pokemon_from(self, directory: str | Path, names: dict[str, str]):
        """
        Pull party sprites out of a sprite tree that is not laid out like `assets/`.

        KyuSprites stores them as `<pokedex_id>.png`, which is the right shape for a bot
        looking one up by species but the wrong shape for a card that wants to say
        `party=["lapras"]`. `names` maps the name the card uses to the file stem.
        """
        d = Path(directory)
        if not d.is_dir():
            log.warning("Sprite dir missing: %s", d)
            return
        for label, stem in names.items():
            f = d / f"{stem}.png"
            if not f.is_file():
                log.warning("No sprite for %s at %s", label, f)
                continue
            try:
                img = Image.open(f).convert("RGBA")
                self.pokemon[label] = _fit_contain(img, PARTY_SLOT, PARTY_SLOT)
            except Exception:
                log.exception("Failed to load %s", f)

    def party_sprite(self, pokedex_id, shiny=False, gender=None):
        """
        One party sprite, resolved and cached on first use.

        LAZY, not warmed. There are thirteen hundred species and a warmed cache of all
        of them at party size is roughly 28MB of RGBA that a Pi would be holding for the
        six a given card actually draws. The cache never expires because the art never
        changes; it simply fills with whatever the server's players actually field.

        Resolution goes through `utils.sprites.resolve_sprite`, which already knows about
        shiny and female variants and about the twelve species with no art at all -
        re-deriving those paths here is exactly the second copy this codebase keeps
        finding the hard way.
        """
        key = (int(pokedex_id), bool(shiny), str(gender or ''))
        if key in self.pokemon:
            return self.pokemon[key]
        try:
            from utils.sprites import resolve_sprite
            path = resolve_sprite(int(pokedex_id), shiny=bool(shiny), gender=gender)
        except Exception:
            path = None
        if not path:
            self.pokemon[key] = None
            return None
        try:
            img = Image.open(path).convert("RGBA")
            self.pokemon[key] = _fit_contain(_trim(img), PARTY_SLOT, PARTY_SLOT)
        except Exception:
            log.exception("Failed to load party sprite %s", path)
            self.pokemon[key] = None
        return self.pokemon[key]

    def warm(self):
        t = time.perf_counter()
        self._load_dir("backgrounds", self.backgrounds, (CARD_W, CARD_H), cover=True)
        self._load_dir("badges", self.badges, (BADGE_PX, BADGE_PX))
        self._load_dir("pokemon", self.pokemon, (PARTY_SLOT, PARTY_SLOT))

        # TRAINERS ARE LOOKED FOR IN TWO PLACES: `assets/trainers/` alongside everything
        # else, and a bare `trainers/` at the project root. The second is not tidiness
        # for its own sake - that is where the art was actually put, and a loader that
        # only knew about the first would report "asset dir missing" for a folder full
        # of files sitting one level up. Later wins, so assets/ can override.
        for directory in (Path("trainers"), self.root / "trainers"):
            if directory.is_dir():
                self._load_dir("", self.trainers, None, root=directory)

        log.info(
            "Assets warmed in %.0fms (bg=%d trainers=%d pokemon=%d badges=%d)",
            (time.perf_counter() - t) * 1000,
            len(self.backgrounds), len(self.trainers),
            len(self.pokemon), len(self.badges),
        )
        if not self.trainers:
            log.warning(
                "No trainer art found in %s - cards will use the biome crest instead.",
                " or ".join(str(p) for p in (Path("trainers"), self.root / "trainers")))


ASSETS = AssetCache()


# --------------------------------------------------------------------------
# Drawing helpers
# --------------------------------------------------------------------------

def _rounded_mask(size: tuple[int, int], radius: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, size[0] - 1, size[1] - 1), radius=radius, fill=255
    )
    return mask


def _fit_cover(img: Image.Image, w: int, h: int) -> Image.Image:
    """Scale-and-crop so the image fills w*h without distortion."""
    scale = max(w / img.width, h / img.height)
    nw, nh = int(img.width * scale + 0.5), int(img.height * scale + 0.5)
    img = img.resize((nw, nh), LANCZOS)
    left, top = (nw - w) // 2, (nh - h) // 2
    return img.crop((left, top, left + w, top + h))


def _fit_contain(img: Image.Image, w: int, h: int) -> Image.Image:
    """
    Scale to fit INSIDE w*h and centre it, keeping the whole subject.

    Cover is right for a background, where the edges are scenery. It is wrong for a
    sprite, where cropping takes the tail off a Lapras — so party cells use this.
    """
    scale = min(w / img.width, h / img.height)
    nw, nh = max(1, int(img.width * scale)), max(1, int(img.height * scale))
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(img.resize((nw, nh), LANCZOS), ((w - nw) // 2, (h - nh) // 2))
    return out


def _text(draw, xy, s, font, fill=INK, anchor="la", shadow=True):
    if shadow:
        # Two offsets rather than one. The panel behind this is half as opaque as it was
        # so the artwork can show through, and a single 1px shadow was not enough to keep
        # pale type legible over the brighter backgrounds.
        for dx, dy, alpha in ((2, 2, 150), (1, 1, 120)):
            draw.text((xy[0] + dx, xy[1] + dy), s, font=font, fill=(0, 0, 0, alpha),
                      anchor=anchor)
    draw.text(xy, s, font=font, fill=fill, anchor=anchor)


def _bar(draw, x, y, w, h, frac, accent):
    frac = max(0.0, min(1.0, frac))
    draw.rounded_rectangle((x, y, x + w, y + h), radius=h // 2, fill=TRACK)
    if frac > 0:
        fw = max(h, int(w * frac))
        draw.rounded_rectangle((x, y, x + fw, y + h), radius=h // 2,
                               fill=accent + (255,))


def _energy_bar(draw, x, y, w, h, energy, accent, bank_cap=None):
    """
    Field Energy across its whole range, which is 0..ENERGY_BANK_CAP and not 0..100.

    THE BAR IS THE BANK CAP WIDE, with a notch at the full-reserve mark. That is the
    honest shape: energy regenerates past a full reserve now, up to twice it, and a bar
    that topped out at 100 would sit pinned at maximum for the entire time somebody was
    banking - showing nothing at exactly the moment there is something to show.

    Three states, and all three are drawn by this one function so they cannot disagree:

      * a normal reserve fills the left half in the biome accent,
      * anything banked past a full reserve continues in gold, past the notch,
      * a DEFICIT - which duelling while empty now produces - fills leftward from zero
        in red, because the trainer is below the bottom of the bar rather than on it.

    Returns the caption to print underneath, since the wording depends on which of the
    three states it drew and working that out twice is how the two fall out of step.
    """
    energy = int(energy or 0)
    # THE TRAINER'S OWN CEILING, which their level raises. Drawn to this rather than to
    # the global base, so a levelled trainer's extra headroom is visible as a longer bar
    # instead of being silently clipped at everybody else's cap.
    cap = max(ENERGY_MAX, int(bank_cap or ENERGY_BANK_CAP))
    draw.rounded_rectangle((x, y, x + w, y + h), radius=h // 2, fill=TRACK)

    # The full-reserve notch. Drawn before the fill so the fill covers it as it passes,
    # which is what makes crossing it read as an event.
    notch_x = x + int(w * (ENERGY_MAX / float(cap)))
    draw.rectangle((notch_x - 1, y - 3, notch_x + 1, y + h + 3), fill=(255, 255, 255, 90))

    if energy < 0:
        # Below empty. The red grows from the left edge in proportion to how deep the
        # debt is against the floor, so a trainer can see how far from level they are.
        depth = min(1.0, abs(energy) / float(abs(ENERGY_DEBT_FLOOR) or 1))
        fw = max(h, int(w * 0.5 * depth))
        draw.rounded_rectangle((x, y, x + fw, y + h), radius=h // 2, fill=DEFICIT + (255,))
        hours = abs(energy) / float(ENERGY_REGEN_PER_HOUR)
        return (f"{energy} ENERGY  ·  running on reserves, "
                f"{int(round(energy_yield(energy) * 100))}% payout  ·  "
                f"level in {int(hours)}h {int((hours % 1) * 60):02d}m"), DEFICIT

    shown = min(energy, cap)
    fw = int(w * (shown / float(cap)))
    if fw > 0:
        draw.rounded_rectangle((x, y, x + max(h, fw), y + h), radius=h // 2,
                               fill=accent + (255,))

    if energy > ENERGY_MAX:
        # The banked stretch, drawn OVER the accent from the notch onwards. Squared off
        # at its left end and rounded at its right, so it reads as a continuation of the
        # same bar rather than as a second pill floating next to it.
        end = x + max(notch_x - x + h, fw)
        draw.rounded_rectangle((notch_x, y, end, y + h), radius=h // 2, fill=BANKED + (255,))
        draw.rectangle((notch_x, y, notch_x + h, y + h), fill=BANKED + (255,))
        return (f"{energy} / {ENERGY_MAX} ENERGY  ·  "
                f"{energy - ENERGY_MAX} banked of {cap - ENERGY_MAX}"), BANKED

    return f"{energy} / {ENERGY_MAX} ENERGY", INK_DIM[:3]


# The sky, as it is named by utils.constants.current_skies. `dusk` and `full-moon` sit
# INSIDE day and night rather than replacing them, so the label prefers the specific one
# and the glyph follows whichever was chosen.
SKY_LABEL = {
    'day': "DAY", 'night': "NIGHT", 'dusk': "DUSK", 'full-moon': "FULL MOON",
}
SKY_COLOUR = {
    'day': (255, 214, 112), 'dusk': (255, 148, 92),
    'night': (150, 178, 226), 'full-moon': (232, 238, 255),
}


def _sky_glyph(layer, cx, cy, r, sky, colour):
    """
    A sun, a crescent or a full moon, drawn rather than typed.

    DRAWN GEOMETRY, not an emoji. PIL renders text through whatever TrueType face it was
    handed, and none of the fallbacks in FONT_CANDIDATES carries colour emoji - a "☀" in
    this position comes out as a hollow box on most hosts and as nothing at all on the
    rest. Three primitives always look like what they are.
    """
    glyph = Image.new("RGBA", (r * 4, r * 4), (0, 0, 0, 0))
    g = ImageDraw.Draw(glyph)
    o = r * 2                                     # centre of the scratch tile
    body = (o - r, o - r, o + r, o + r)

    if sky == 'night':
        # A crescent: the disc, then a second disc punched out of it with alpha 0. Drawn
        # on its own tile precisely so the punch-out cannot erase the card underneath.
        g.ellipse(body, fill=colour + (255,))
        g.ellipse((o - r * 1.55, o - r * 1.2, o + r * 0.55, o + r * 1.2), fill=(0, 0, 0, 0))
    elif sky == 'day':
        for i in range(8):
            a = math.pi * i / 4
            g.line((o + math.cos(a) * r * 1.35, o + math.sin(a) * r * 1.35,
                    o + math.cos(a) * r * 1.9, o + math.sin(a) * r * 1.9),
                   fill=colour + (215,), width=max(2, r // 3))
        g.ellipse(body, fill=colour + (255,))
    elif sky == 'dusk':
        # A sun going down behind a horizon: the TOP half of a disc, sitting on a line.
        # The first attempt dimmed the upper half of a full disc instead, which at a
        # seven-pixel radius was two shades of the same blob and read as neither a sun
        # nor a moon. Half a disc plus a rule under it is unmistakable at any size.
        g.pieslice(body, 180, 360, fill=colour + (255,))
        g.line((o - r * 1.9, o + r * 0.25, o + r * 1.9, o + r * 0.25),
               fill=colour + (235,), width=max(2, r // 3))
    else:                                          # full-moon
        g.ellipse(body, fill=colour + (255,))
        g.ellipse((o - r * .45, o - r * .5, o + r * .05, o + r * .1), fill=colour + (140,))
        g.ellipse((o + r * .1, o + r * .2, o + r * .55, o + r * .6), fill=colour + (140,))

    layer.alpha_composite(glyph, (int(cx - o), int(cy - o)))


def _sky_chip(draw, layer, right_x, y, skies, clock, font):
    """
    The trainer's own clock and sky, top-right of the panel.

    IT IS ON THE CARD BECAUSE IT IS A RULE, not decoration: day and night gate a dozen
    evolutions, and a trainer whose Umbreon will not appear has otherwise no way to see
    what time the bot thinks it is for them. `utils/prefs` resolves the zone; this only
    draws what it was told.

    Returns the left edge it occupied, so the name beside it knows where to stop.
    """
    if not clock:
        return right_x

    # The SPECIFIC sky wins. dusk and full-moon sit inside day and night rather than
    # replacing them, so a card that showed 'night' during a full moon would be true and
    # useless - the whole reason those two names exist is that a rule can ask for them.
    order = ('full-moon', 'dusk', 'night', 'day')
    sky = next((s for s in order if s in (skies or ())), 'day')
    colour = SKY_COLOUR.get(sky, SKY_COLOUR['day'])
    label = f"{clock}  {SKY_LABEL.get(sky, sky.upper())}"

    text_w = int(draw.textlength(label, font=font))
    h = 30
    w = text_w + 44
    x = right_x - w
    draw.rounded_rectangle((x, y, x + w, y + h), radius=h // 2,
                           fill=(255, 255, 255, 26))
    _sky_glyph(layer, x + 18, y + h // 2, 7, sky, colour)
    _text(draw, (x + 34, y + h // 2), label, font, fill=colour + (245,), anchor="lm")
    return x


def _trim(img: Image.Image) -> Image.Image:
    """Crop away fully transparent margin. A no-op on an image that has none."""
    box = img.getbbox()
    return img.crop(box) if box else img


def _avatar_tile(art: Image.Image | None, accent: tuple[int, int, int],
                 w: int, h: int, fill: float = 0.58,
                 pixel_art: bool = False) -> Image.Image:
    """
    The avatar: one piece of art centred on a ground tinted with the biome accent.

    Used for BOTH the trainer sprite and the biome-badge fallback, because they want
    exactly the same treatment and writing it twice is how the two drift apart.

    `pixel_art` switches the upscale to nearest-neighbour. The trainer sprites are 80px
    pixel art going into a 200px box, and LANCZOS turns crisp pixels into mush at 2.5x -
    smooth interpolation is right for a photograph and wrong for a sprite.
    """
    tile = Image.new("RGBA", (w, h), tuple(int(c * 0.30) for c in accent) + (255,))
    ImageDraw.Draw(tile).ellipse((w * .06, h * .06, w * .94, h * .94),
                                 fill=accent + (46,))
    if art is None:
        return tile

    # Trimmed FIRST. These sprites are a figure floating in a lot of empty 80x80, so
    # fitting the raw file leaves the trainer sitting small in the middle of the tile
    # with the transparent margin doing the framing instead of the accent ring.
    art = _trim(art)
    inner = int(min(w, h) * fill)
    scale = min(inner / art.width, inner / art.height)
    nw, nh = max(1, int(art.width * scale)), max(1, int(art.height * scale))
    art = art.resize((nw, nh), Image.NEAREST if pixel_art else LANCZOS)
    tile.alpha_composite(art, ((w - nw) // 2, (h - nh) // 2))
    return tile


def _crest(biome: str, accent: tuple[int, int, int], w: int, h: int,
           seed: str = "") -> Image.Image:
    """The avatar when there is no trainer art: the biome's own badge."""
    badge = ASSETS.badges.get(biome)
    if badge is None:
        return _fit_cover(_placeholder((w, h), seed or biome), w, h)
    return _avatar_tile(badge, accent, w, h)


def _placeholder(size: tuple[int, int], seed: str) -> Image.Image:
    """Deterministic stand-in so missing assets never crash a render."""
    h = int(hashlib.md5(seed.encode()).hexdigest()[:6], 16)
    color = ((h >> 16) & 0xFF, (h >> 8) & 0xFF, h & 0xFF, 255)
    img = Image.new("RGBA", size, color)
    d = ImageDraw.Draw(img)
    d.ellipse((size[0] * .2, size[1] * .2, size[0] * .8, size[1] * .8),
              fill=(255, 255, 255, 40))
    return img


# --------------------------------------------------------------------------
# Renderer
# --------------------------------------------------------------------------

def render_profile_card(data: ProfileData) -> bytes:
    accent = BIOME_ACCENT.get(data.biome, BIOME_ACCENT[DEFAULT_BIOME])

    # ---- background -------------------------------------------------------
    bg = ASSETS.backgrounds.get(data.background)
    if bg is None:
        bg = _placeholder((CARD_W, CARD_H), data.background)
    canvas = _fit_cover(bg.copy(), CARD_W, CARD_H)

    # Darken + slight blur so text stays legible over any artwork. The darkening used to
    # be 110/255 ON TOP OF a near-opaque panel, which is two solutions to one problem and
    # left the art invisible. The panel does the legibility work now, so this is only
    # enough to stop a bright sky fighting the card edge.
    canvas = canvas.filter(ImageFilter.GaussianBlur(1.2))
    canvas = Image.alpha_composite(
        canvas, Image.new("RGBA", (CARD_W, CARD_H), (6, 10, 9, 64))
    )

    # ---- translucent content panel ---------------------------------------
    # DRAWN AND COMPOSITED, not pasted. `Image.paste(rgba, xy, mask)` uses the mask for
    # coverage and copies the source's alpha channel straight into the destination - it
    # does NOT blend by the source's own alpha. So the panel landed fully opaque wherever
    # the rounded mask was white, and PANEL's alpha had no effect whatsoever: turning it
    # down from 205 to 122 changed nothing, which is what gave the bug away.
    panel = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    ImageDraw.Draw(panel).rounded_rectangle(
        (PAD, PAD, CARD_W - PAD - 1, CARD_H - PAD - 1), radius=RADIUS, fill=PANEL)
    canvas = Image.alpha_composite(canvas, panel)

    layer = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    # accent rail down the left edge of the panel
    draw.rounded_rectangle((PAD, PAD + 18, PAD + 5, CARD_H - PAD - 18),
                           radius=3, fill=accent + (255,))

    # ---- trainer avatar ---------------------------------------------------
    ax, ay, aw, ah = AVATAR_BOX
    sprite = ASSETS.trainers.get(data.trainer_sprite or "")
    if sprite is not None:
        # CONTAIN, not cover. Cover-cropping a standing figure into a square takes the
        # head off - which is the one part of a trainer sprite nobody will accept losing.
        sprite = _avatar_tile(sprite, accent, aw, ah, fill=0.80, pixel_art=True)
    else:
        # NO TRAINER ART EXISTS YET, and a hashed colour square is a placeholder that
        # looks like a bug rather than like a gap. The biome's own badge on a tinted
        # ground uses art that IS here and reads as a deliberate crest, which is what
        # this corner wants to be until real trainer sprites land.
        sprite = _crest(data.biome, accent, aw, ah,
                        seed=data.trainer_sprite or data.user_name)
    layer.paste(sprite, (ax, ay), _rounded_mask((aw, ah), 16))
    draw.rounded_rectangle((ax, ay, ax + aw, ay + ah), radius=16,
                           outline=accent + (220,), width=3)

    # ---- identity block ---------------------------------------------------
    tx = ax + aw + 26
    f_name = ASSETS.font("bold", 38)
    f_sub = ASSETS.font("regular", 19)
    f_small = ASSETS.font("regular", 16)
    f_stat = ASSETS.font("bold", 24)
    f_label = ASSETS.font("regular", 14)

    # The clock goes in FIRST, because it decides how much room the name has left. A
    # name drawn to a fixed width and then overwritten by the chip is the collision the
    # party strip already taught this file to avoid.
    chip_left = _sky_chip(draw, layer, CARD_W - PAD - 20, ay + 4,
                          data.skies, data.local_time, f_label)

    name = data.user_name
    while name and draw.textlength(name, font=f_name) > (chip_left - tx - 16):
        name = name[:-1]
    _text(draw, (tx, ay + 2), name or data.user_name[:8], f_name)
    _text(draw, (tx, ay + 48), f"{data.trainer_title}  ·  Lv {data.trainer_level}",
          f_sub, fill=accent + (255,))

    # ---- the two bars -----------------------------------------------------
    # Slimmer than the single bar was, and the captions sit tighter under them, because
    # there are two of these now and the stat row still has to clear the party strip.
    bar_w = CARD_W - tx - PAD - 20
    bar_h = 12

    xp_y = ay + 80
    _bar(draw, tx, xp_y, bar_w, bar_h, data.xp_current / max(1, data.xp_needed), accent)
    _text(draw, (tx, xp_y + 16), f"{data.xp_current:,} / {data.xp_needed:,} XP",
          f_small, fill=INK_DIM)

    energy_y = xp_y + 44
    caption, caption_rgb = _energy_bar(draw, tx, energy_y, bar_w, bar_h,
                                       data.energy, accent, data.energy_cap)
    _text(draw, (tx, energy_y + 16), caption, f_small, fill=caption_rgb + (230,))

    # ---- stat row ---------------------------------------------------------
    # FOUR, not five. ECO came out: it is the server habitat's score, identical for
    # every member of a guild, so printing it on a personal card said nothing about the
    # person holding it. It belongs in the server embed, and the four that remain get
    # more room for it.
    # The visa slot names the DEEPEST sector cleared, with the count beside it. That is
    # the one a trainer would say out loud - "I'm through to Apex" - and the count is
    # what the badge strip below is already showing, so the two agree by construction.
    visa_order = list(BIOME_LABEL)
    held = [v for v in visa_order if v in (data.visas or ())]
    if held:
        deepest = BIOME_LABEL[held[-1]]
        visa_value = f"{deepest}"
        visa_label = f"SECTOR · {len(held)}/{len(visa_order)}"
    else:
        visa_value, visa_label = "—", "SECTOR"

    stats = [
        ("CAUGHT", f"{data.caught:,}"),
        ("SHINY", f"{data.shinies:,}"),
        ("TOKENS", f"{data.eco_tokens:,}"),
        (visa_label, visa_value),
    ]
    sx = tx
    step = (CARD_W - tx - PAD - 10) // len(stats)
    sy = energy_y + 46
    for label, value in stats:
        _text(draw, (sx, sy), value, f_stat)
        _text(draw, (sx, sy + 30), label, f_label, fill=INK_DIM)
        sx += step

    # ---- badges and party share one row, so the badges are measured FIRST --
    # Both strips used to be laid out independently from their own end of the card, and
    # with six party members and five badges they ran into each other in the middle: on
    # the Apex card a badge sat directly on top of the sixth specimen. The badges are
    # the smaller, fixed-size set, so they claim their space first and the party gets
    # what is left.
    badges = data.badges[:5]
    badge_cell = BADGE_PX + 12
    badge_span = (len(badges) * badge_cell + max(0, len(badges) - 1) * 6) if badges else 0

    bx = CARD_W - PAD - 16 - BADGE_PX
    for name in badges:
        badge = ASSETS.badges.get(name) or _placeholder((BADGE_PX, BADGE_PX), name)
        draw.rounded_rectangle((bx - 6, PARTY_Y, bx + BADGE_PX + 6, PARTY_Y + PARTY_SLOT),
                               radius=12, fill=(255, 255, 255, 22))
        layer.alpha_composite(badge, (bx, PARTY_Y + (PARTY_SLOT - BADGE_PX) // 2))
        bx -= badge_cell + 6

    # ---- party strip ------------------------------------------------------
    px0 = PAD + 16
    # A comfortable gap where there is room, squeezed down to 4px where there is not,
    # rather than letting the row run under the badges.
    room = CARD_W - PAD - 16 - badge_span - 18 - px0
    gap = max(4, min(10, (room - 6 * PARTY_SLOT) // 5)) if room > 6 * PARTY_SLOT else 4

    px = px0
    for i in range(6):
        cell = (px, PARTY_Y, px + PARTY_SLOT, PARTY_Y + PARTY_SLOT)
        draw.rounded_rectangle(cell, radius=12, fill=(255, 255, 255, 26))
        if i < len(data.party):
            # TWO SHAPES ACCEPTED, because two callers exist. The bot hands over
            # `(pokedex_id, shiny, gender)` and gets the right variant resolved and
            # cached; the demo hands over a name it preloaded. A cell that resolves to
            # nothing is left EMPTY rather than filled with a hashed colour square - a
            # species with no art (there are twelve) should read as a gap, not as a bug.
            entry = data.party[i]
            if isinstance(entry, (tuple, list)):
                dex, shiny, gender = (list(entry) + [False, None])[:3]
                mon = ASSETS.party_sprite(dex, shiny, gender)
            else:
                mon = ASSETS.pokemon.get(entry)
            if mon is not None:
                layer.alpha_composite(mon, (px, PARTY_Y))
        px += PARTY_SLOT + gap

    # A hairline between the two groups. Once the badge cells were given the same
    # treatment as the party cells the bottom of the card read as eleven identical
    # slots, and there was nothing to say that the last few are achievements rather
    # than a very large team.
    if badges:
        dx = px - gap // 2 - 1
        if dx < CARD_W - PAD - 16 - badge_span - 8:
            draw.rounded_rectangle((dx, PARTY_Y + 12, dx + 2, PARTY_Y + PARTY_SLOT - 12),
                                   radius=1, fill=accent + (110,))

    canvas = Image.alpha_composite(canvas, layer)

    # ---- encode -----------------------------------------------------------
    buf = io.BytesIO()
    canvas.convert("RGB").save(buf, format="WEBP", quality=88, method=4)
    return buf.getvalue()


# --------------------------------------------------------------------------
# Async wrapper + render cache
# --------------------------------------------------------------------------

class _LRU(OrderedDict):
    def __init__(self, cap=256):
        super().__init__()
        self.cap = cap

    def put(self, k, v):
        self[k] = v
        self.move_to_end(k)
        while len(self) > self.cap:
            self.popitem(last=False)


_render_cache = _LRU(256)


async def render_profile_card_async(data: ProfileData) -> bytes:
    """Render off the event loop, with caching. Use this from your cog."""
    key = data.cache_key()
    if (hit := _render_cache.get(key)) is not None:
        _render_cache.move_to_end(key)
        return hit

    loop = asyncio.get_running_loop()
    t = time.perf_counter()
    png = await loop.run_in_executor(
        None, functools.partial(render_profile_card, data)
    )
    log.info("profile render %.0fms  %.1fKB",
             (time.perf_counter() - t) * 1000, len(png) / 1024)

    _render_cache.put(key, png)
    return png


def invalidate_profile(data: ProfileData) -> None:
    _render_cache.pop(data.cache_key(), None)


# --------------------------------------------------------------------------
# The bridge from the bot's numbers to the card's
# --------------------------------------------------------------------------

def build_profile_card(gathered: dict) -> ProfileData:
    """
    A `ProfileData` from the dictionary `!profile` reads out of the database.

    ONE PLACE DOES THIS TRANSLATION. The alternative was for the cog to construct a
    ProfileData inline, which is fine until the embed rendering and the image rendering
    start deriving the same figure differently - and the derived figures here are
    exactly the ones that would drift: the level, the XP-bar numerator and denominator,
    and which biome the card is dressed in.

    The biome is the DEEPEST visa held, so the card wears the sector a trainer has
    actually fought their way into rather than the one they started in.
    """
    from utils.levels import progress

    visas = [v for v in gathered.get('visas') or [] if v in BIOME_ACCENT]
    ordered = [b for b in BIOME_ACCENT if b in visas]
    biome = ordered[-1] if ordered else DEFAULT_BIOME

    level, into, span = progress(gathered.get('lifetime', 0))

    target = gathered.get('target')
    name = getattr(target, 'display_name', None) or str(target or 'Trainer')

    return ProfileData(
        user_name=name,
        trainer_title=gathered.get('title') or '',
        trainer_level=level,
        xp_current=into,
        xp_needed=span,
        biome=biome,
        background=biome,
        eco_tokens=gathered.get('tokens', 0),
        caught=gathered.get('caught', 0),
        shinies=gathered.get('shinies', 0),
        visas=ordered,
        badges=ordered,
        energy=gathered.get('energy', ENERGY_MAX),
        energy_cap=gathered.get('bank_cap', ENERGY_BANK_CAP),
        local_time=gathered.get('clock', ''),
        skies=tuple(gathered.get('skies') or ()),
        # The bot hands over (pokedex_id, shiny, gender) triples; the renderer resolves
        # and caches each one through utils.sprites.
        party=list(gathered.get('party') or []),
        trainer_sprite=gathered.get('trainer_sprite'),
    )


# --------------------------------------------------------------------------
# discord.py usage
# --------------------------------------------------------------------------
#
#   # once, in setup_hook():
#   ASSETS.warm()
#
#   @app_commands.command(name="profile")
#   async def profile(self, interaction: discord.Interaction):
#       await interaction.response.defer()            # ALWAYS defer first
#       row = await self.db.fetch_profile(interaction.user.id)
#       data = ProfileData(user_name=interaction.user.display_name, **row)
#       image = await render_profile_card_async(data)
#       await interaction.followup.send(
#           file=discord.File(io.BytesIO(image), filename="profile.webp")
#       )
#
# --------------------------------------------------------------------------


# --------------------------------------------------------------------------
# Demo
# --------------------------------------------------------------------------
# The party sprites come out of KyuSprites, which stores them by pokedex id. The card
# wants to say `party=["lapras"]`, so the mapping lives here rather than in the renderer:
# a bot calling this for real already knows the ids and would register them the same way.
from utils.levels import progress, title_for, energy_bank_cap

SPRITE_DIR = "KyuSprites/sprites/pokemon/other/home"

DEMO_PARTIES = {
    "canopy":  {"venusaur": 3, "decidueye": 724, "leavanny": 542,
                "shiftry": 275, "sceptile": 254, "tsareena": 763},
    "trench":  {"lapras": 131, "toxapex": 748, "gastrodon": 423,
                "araquanid": 752, "lanturn": 171, "milotic": 350},
    "core":    {"magcargo": 219, "turtonator": 776, "talonflame": 663,
                "camerupt": 323, "coalossal": 839, "centiskorch": 851},
    "sprawl":  {"klinklang": 601, "grimmsnarl": 861, "porygon-z": 474,
                "muk-alola": 10113, "garbodor": 569},
    "apex":    {"dragonite": 149, "salamence": 373, "garchomp": 445,
                "hydreigon": 635, "goodra": 706, "flygon": 330},
}

# The five energy states worth seeing at once: part-full, exactly full, in deficit,
# bang on empty, and deep into the banked overflow.
DEMO_CARDS = {
    # trainer_sprite is a file stem in trainers/ — 650 of them, from Showdown, all
    # 80x80 pixel art. One picked per biome for whom the job title is plausible.
    "canopy": dict(user_name="RangerKyu", trainer_sprite="pokemonranger",
                   contribution=520,
                   eco_tokens=128_400, caught=1_284, shinies=17,
                   energy=70, local_time="09:14", skies=("day",)),
    "trench": dict(user_name="AbyssalDre", trainer_sprite="marlon",
                   contribution=196,
                   eco_tokens=402_950, caught=2_071, shinies=34,
                   energy=100, local_time="17:32", skies=("day", "dusk")),
    "core": dict(user_name="Cinderpath", trainer_sprite="flannery",
                 contribution=48,
                 eco_tokens=76_300, caught=903, shinies=6,
                 energy=-40, local_time="23:05", skies=("night",)),
    "sprawl": dict(user_name="NeonQuill", trainer_sprite="elesa",
                   contribution=9,
                   eco_tokens=19_775, caught=488, shinies=2,
                   energy=0, local_time="02:48", skies=("night", "full-moon")),
    "apex": dict(user_name="SkyveinAda", trainer_sprite="cynthia",
                 contribution=10_000,
                 eco_tokens=1_004_600, caught=5_142, shinies=118,
                 energy=185, energy_cap=300, local_time="12:00", skies=("day",)),
}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ASSETS.warm()

    for names in DEMO_PARTIES.values():
        ASSETS.load_pokemon_from(SPRITE_DIR, names)

    out_dir = Path("profile_demo")
    out_dir.mkdir(exist_ok=True)
    cards = []

    for biome, fields in DEMO_CARDS.items():
        # Every biome unlocked up to and including this one, which is how visas actually
        # accumulate - so the badge strip grows as you go down the list.
        held = list(DEMO_CARDS)[:list(DEMO_CARDS).index(biome) + 1]
        # LEVEL, TITLE AND THE XP BAR ARE DERIVED, exactly as the bot derives them: one
        # contribution total in, three display values out. Hand-setting them here would
        # let the demo show a curve the game does not have.
        contribution = fields.pop("contribution")
        level, into, span = progress(contribution)
        data = ProfileData(
            biome=biome,
            background=biome,
            badges=held,
            visas=held,
            party=list(DEMO_PARTIES[biome]),
            trainer_level=level,
            trainer_title=title_for(level),
            xp_current=into,
            xp_needed=span,
            **fields,
        )
        blob = render_profile_card(data)
        path = out_dir / f"{biome}.webp"
        path.write_bytes(blob)
        cards.append(Image.open(io.BytesIO(blob)).convert("RGB"))
        print(f"  {path}  ({len(blob) / 1024:.1f} KB)  accent={BIOME_ACCENT[biome]}")

    # One sheet with all five, so the accent-per-biome difference is visible at a glance
    # rather than by flicking between files.
    gap = 16
    sheet = Image.new("RGB", (CARD_W + gap * 2,
                              gap + (CARD_H + gap) * len(cards)), (18, 22, 21))
    for i, card in enumerate(cards):
        sheet.paste(card, (gap, gap + i * (CARD_H + gap)))
    sheet.save(out_dir / "all_biomes.png")
    print(f"  {out_dir / 'all_biomes.png'}  ({sheet.width}x{sheet.height})")
