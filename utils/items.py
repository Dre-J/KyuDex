"""
What an item is, what it costs, and where its picture lives.

**THIS ONE NEEDED NO MIGRATION, WHICH IS WORTH SAYING OUT LOUD.** The plan was a table of
descriptions fetched from PokeAPI, the way `migrate_ability_dex.py` fetches the traits.
Measured first: all 460 rows of `EQUIPMENT_CATALOG` already carry a `desc`, and 311 of
them already have a sprite sitting in `KyuSprites/sprites/items`. So the network would
have bought nothing but a second, competing description.

**AND THE CATALOG'S DESCRIPTION IS THE BETTER ONE.** It says what the item does *here* -
"2.5x Capture Rate", "Halves the holder's Speed" - which for a bot whose mechanics are
its own is the truth a player needs. PokeAPI's flavour text describes the games, and
where the two differ it would be confidently wrong.

What this module owns is the naming: the spellings a person types, the aliases between a
catalog key and a sprite filename, and the suggestions when neither matches.
"""
import os

from utils.constants import (EQUIPMENT_CATALOG, CAPTURE_BALLS,
                             is_directive_exclusive, DIRECTIVE_EXCLUSIVE_ITEMS)

SPRITE_ROOT = os.path.join("KyuSprites", "sprites", "items")

# Looked in, in order. The root set is the largest and the most consistent in style; the
# Dream World art is prettier where it exists but covers two thirds as much.
SPRITE_FOLDERS = ('', 'gen9', 'gen8', 'dream-world')

# **THE CATALOG AND THE SPRITE SET DISAGREE ABOUT FOUR NAMES**, all of them balls: the
# catalog has spelled them `greatball` since the shop was written and the sprite set uses
# the hyphenated form every other item uses. Written out rather than guessed at with a
# rule, because "insert a hyphen before 'ball'" also rewrites `beast-ball` into
# `beast--ball` and finds nothing.
SPRITE_ALIASES = {
    'pokeball': 'poke-ball',
    'greatball': 'great-ball',
    'ultraball': 'ultra-ball',
    'masterball': 'master-ball',
}

CATEGORY_LABELS = {
    'battleitems': ("Battle item", "⚔️"),
    'megastone':   ("Mega Stone", "🧬"),
    'typeboost':   ("Type booster", "🔆"),
    'berry':       ("Berry", "🍓"),
    'formitems':   ("Form item", "🔄"),
    'zcrystal':    ("Z-Crystal", "💎"),
    'evoitems':    ("Evolution item", "🌱"),
    'mints':       ("Mint", "🌿"),
    'keyitems':    ("Key item", "🔑"),
    'medicine':    ("Medicine", "💊"),
    'vitamin':     ("Vitamin", "🧪"),
    'capture':     ("Ball", "🔴"),
    'general':     ("General", "📦"),
}

MAX_SUGGESTIONS = 5


def _catalogue():
    """
    Everything a trainer can hold, which is the shop's shelf PLUS the Poke Ball.

    **THE COMMONEST ITEM IN THE GAME IS NOT IN `EQUIPMENT_CATALOG`.** The shelf is what
    the shop sells, and the Poke Ball is the one nobody buys - it lives in
    `CAPTURE_BALLS` with the rest of the ladder because it is what a trainer starts with.
    A catalogue that cannot describe it is not a catalogue, so the ladder is folded in for
    anything the shelf does not already carry.
    """
    merged = dict(EQUIPMENT_CATALOG)
    for key, ball in CAPTURE_BALLS.items():
        if key in merged:
            continue
        merged[key] = {
            'name': ball['name'],
            'price': 0,
            'desc': f"{ball['multiplier']}x Capture Rate",
            'emoji': '🔴',
            'category': 'capture',
            'purchasable': bool(ball.get('stocked')),
            'free': not ball.get('stocked'),
        }
    return merged


CATALOGUE = _catalogue()


def entry(key):
    """The catalogue row for a key, or an empty dict."""
    return CATALOGUE.get(key) or {}


def normalise(text):
    """`Great Ball`, `great_ball` and `GREAT BALL` all reach `great-ball`."""
    flat = str(text or '').strip().lower().replace('_', '-').replace(' ', '-')
    while '--' in flat:
        flat = flat.replace('--', '-')
    return flat.strip('-')


def pretty_item(key):
    """A catalog key as a player should see it, preferring the catalog's own name."""
    row = CATALOGUE.get(key)
    if row and row.get('name'):
        return row['name']
    return str(key or '').replace('-', ' ').title()


def resolve(typed):
    """
    `(key, complaint)` - the catalog key meant, or a sentence saying why not.

    Three spellings are accepted before it gives up: the key itself, the key with the
    hyphens a person leaves out, and the catalog's display NAME - which is what somebody
    reading the shop will type, and which is not always the key ("Poke Ball" is
    `pokeball`).
    """
    wanted = normalise(typed)
    if not wanted:
        return None, "🎒 Which item? `!itemdex leftovers`."

    if wanted in CATALOGUE:
        return wanted, None

    # The display name, flattened the same way. Built per call rather than cached: the
    # catalog is assembled at import and never changes afterwards, so a stale index would
    # be the only way this could go wrong.
    by_display = {normalise(row.get('name')): key
                  for key, row in CATALOGUE.items() if row.get('name')}
    if wanted in by_display:
        return by_display[wanted], None

    unhyphenated = {key.replace('-', ''): key for key in CATALOGUE}
    if wanted.replace('-', '') in unhyphenated:
        return unhyphenated[wanted.replace('-', '')], None

    hints = suggest(wanted)
    hint = ("  Did you mean: " + ", ".join(f"`{h}`" for h in hints)) if hints else ""
    return None, f"🎒 No item called `{typed}` is in the catalogue.{hint}"


def suggest(typed, limit=MAX_SUGGESTIONS):
    """Items this might have meant, best first - prefix, then substring, then typo."""
    needle = normalise(typed)
    if not needle:
        return []

    import difflib
    pool = list(CATALOGUE)
    prefix = [k for k in pool if k.startswith(needle)]
    contains = [k for k in pool if needle in k and k not in prefix]
    close = [k for k in difflib.get_close_matches(needle, pool, n=limit, cutoff=0.6)
             if k not in prefix and k not in contains]
    return (prefix + contains + close)[:limit]


def sprite_path(key):
    """
    Where this item's picture is, or None.

    None is an ordinary answer, not a failure: 149 catalog entries are this world's own
    inventions - Memory Spores, Encrypted Field Notes, Wishing Fragments - and no sprite
    set has ever had a picture of them. The card leaves the media block out entirely
    rather than pointing it at a file that is not there, which renders as a broken image.
    """
    name = SPRITE_ALIASES.get(key, key)
    for folder in SPRITE_FOLDERS:
        candidate = os.path.join(SPRITE_ROOT, folder, f"{name}.png") if folder \
            else os.path.join(SPRITE_ROOT, f"{name}.png")
        if os.path.exists(candidate):
            return candidate
    return None


def category_of(key):
    """`(label, emoji)` for the shelf this item sits on."""
    return CATEGORY_LABELS.get(entry(key).get('category'), ("Item", "📦"))


def availability(key):
    """
    How a trainer gets this item, as a list of lines.

    Three separate facts that used to be one word in the shop: whether it is on the
    shelf, what it costs, and whether it is reserved for directive rewards - which is a
    deliberate ban rather than an oversight, and the reason 47 items stopped being
    purchasable when the loot tables were rebalanced.
    """
    row = entry(key)
    lines = []
    price = row.get('price')
    if row.get('free'):
        # The Poke Ball. Not stocked because nobody needs to buy it.
        lines.append("🎁 Free — every trainer starts with these.")
    elif row.get('purchasable', True) and price:
        lines.append(f"🪙 **{price:,}** at the shop.")
    elif row.get('purchasable', True):
        lines.append("🪙 Free at the shop.")
    elif is_directive_exclusive(key):
        lines.append("📋 Not sold — earned from field directives.")
    else:
        lines.append("🚫 Not sold.")

    sell = row.get('sell_price')
    if sell:
        lines.append(f"💰 Sells for **{sell:,}**.")
    return lines


def shelf(key, limit=24):
    """Other items on the same shelf, for browsing a catalogue of four hundred."""
    category = entry(key).get('category')
    if not category:
        return []
    return [k for k in CATALOGUE
            if k != key and (CATALOGUE[k].get('category') == category)][:limit]
