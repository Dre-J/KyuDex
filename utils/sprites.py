"""
Which image file to show for a specimen.

Five places in cogs/ecology.py built this path by hand, each with its own copy of the
same two lines, and none of them had ever heard of a female sprite. This is that
question asked once.

WHY A CHAIN RATHER THAN A PATH
------------------------------
The sprite sets are not complete, and they are incomplete in different places. Measured
against the 1344 species in base_pokemon_species:

    official-artwork          1332   (99.1%)
    official-artwork/shiny    1320   (98.2%)
    home                      1328   (98.8%)
    home/shiny                1321   (98.3%)
    home/female                103   ( 7.7%)
    home/shiny/female          103   ( 7.7%)

The female figure is not a gap - only about a hundred species look different by sex, and
those are exactly the hundred PokeAPI ships a female sprite for. Everything else is meant
to fall through to the shared image. So asking for "the female HOME sprite" has to be a
PREFERENCE with somewhere to land, not a filename, or 92% of the roster would show a
blank.

WHAT LOSES FIRST
----------------
When something has to give, shininess is kept and sex is dropped. A shiny Nidoran shown
as the male shiny is wrong in a way a player may not notice; the same specimen shown in
ordinary colours is wrong in the way the whole point of a shiny is to be noticed. Style
is given up before either: an official-artwork image of the right specimen beats a HOME
image of the wrong one.
"""
import os

# Relative, like DB_FILE - the bot is launched from the project root.
SPRITE_ROOT = os.path.join("KyuSprites", "sprites", "pokemon", "other")

HOME = 'home'
ARTWORK = 'official-artwork'
STYLES = (HOME, ARTWORK)

# Only these two carry a female variant. Kept as data so the chain builder does not have
# to know which folders exist on disk.
STYLES_WITH_FEMALE = (HOME,)


def is_female(gender):
    """
    Whether this specimen should be offered the female sprite.

    caught_pokemon.gender holds 'M', 'F' or the literal string 'None' for the genderless,
    which is why this is a helper rather than `gender == 'F'` written out five times.
    """
    return str(gender or '').strip().upper() in ('F', 'FEMALE')


def sprite_candidates(pokedex_id, shiny=False, gender=None, style=HOME):
    """
    Every file worth trying for this specimen, best first.

    Returned rather than resolved so a caller can log what it looked for, and so the
    ordering can be asserted directly by a test instead of inferred from which file
    happens to exist on the disk of whoever is running it.
    """
    female = is_female(gender)
    preferred = style if style in STYLES else HOME
    fallback = ARTWORK if preferred == HOME else HOME

    def variants(for_style, want_shiny, want_female):
        """
        The folders to try within ONE style at ONE shininess, most specific first.

        Deliberately says nothing about the other shininess. The first draft folded the
        non-shiny folders into the shiny pass, which put `home/female` above
        `official-artwork/shiny` and quietly reversed the rule this module's docstring
        states - a shiny specimen would have shown in ordinary colours rather than
        borrow the other sex's shiny.
        """
        base = ('shiny',) if want_shiny else ()
        parts = []
        if want_female and for_style in STYLES_WITH_FEMALE:
            parts.append(base + ('female',))
        parts.append(base)
        return parts

    chain = []
    # Shininess outranks sex, and sex outranks style - so the shiny of the preferred
    # style, then the shiny of the other, before anything non-shiny is considered.
    if shiny:
        for for_style in (preferred, fallback):
            for folder in variants(for_style, True, female):
                chain.append((for_style,) + folder)
    for for_style in (preferred, fallback):
        for folder in variants(for_style, False, female):
            chain.append((for_style,) + folder)

    seen, paths = set(), []
    for folder in chain:
        path = os.path.join(SPRITE_ROOT, *folder, f"{pokedex_id}.png")
        if path not in seen:
            seen.add(path)
            paths.append(path)
    return paths


def resolve_sprite(pokedex_id, shiny=False, gender=None, style=HOME):
    """
    The best file that actually exists, or None when the species has no art at all.

    Twelve species currently have none - the Mimikyu busted forms, the Koraidon and
    Miraidon travel modes and two Tatsugiri megas. A caller that gets None should say so
    rather than attaching a broken image.
    """
    for path in sprite_candidates(pokedex_id, shiny, gender, style):
        if os.path.exists(path):
            return path
    return None


def sprite_attachment_name(pokedex_id, shiny=False, gender=None):
    """
    A stable filename for the Discord attachment.

    Discord caches by name, so two specimens that differ only by sex or shininess must
    not share one - a female shiny and a male ordinary of the same species would
    otherwise take turns showing each other's picture.
    """
    bits = [str(pokedex_id)]
    if shiny:
        bits.append('shiny')
    if is_female(gender):
        bits.append('female')
    return '_'.join(bits) + '.png'
