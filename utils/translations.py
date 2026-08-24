"""
Species names in the nine languages the games ship, and the two lookups that read them.

**THE TABLE WAS SILENTLY EATING ROWS.** `species_translations` was keyed on
`foreign_name` alone, and a great many species are spelled identically in several
languages - Pikachu is Pikachu in French, German, Spanish and Italian. Only the first
insert of each spelling survived, so the table held 1,025 Japanese names, 1,025 Korean
and 1,025 French, but 882 German, 805 Spanish and **22 Italian**. The 22 that made it
were the Paradox species, which are the ones with genuinely unusual Italian names.

Nothing was wrong with the import. The key was wrong. Rekeying on
`(foreign_name, language_tag)` recovers 1,366 rows nobody knew were missing, and is what
makes Romaji possible at all - "Pikachu" in Romaji collides with "Pikachu" in French.

**TWO KEYS PER NAME, AND ONLY ONE OF THEM IS FOLDED.** `foreign_name` is what the games
call it, lowercased and space-joined exactly the way `!catch` treats what a player types.
`folded` is that with Latin accents removed, so someone typing `flabebe` catches
Flabébé - 181 names are otherwise unreachable from a keyboard without a compose key.

Folding is Latin-ONLY, and that restriction is load-bearing rather than tidy. Japanese
dakuten are combining marks: strip them blindly and カラカラ (Cubone) and ガラガラ
(Marowak) become the same string, along with 1,900 other kana names. Latin-only folding
touches 181 names and collides on none.
"""
import unicodedata

TABLE = 'species_translations'
ENGLISH = 'ENG'

# tag -> what to call it, and which PokeAPI language row it comes from. The order is the
# order they appear in, which the dex embed reads.
LANGUAGES = {
    'JPN': {'label': 'Japanese',   'emoji': '🇯🇵', 'pokeapi': 'ja-hrkt'},
    'ROM': {'label': 'Rōmaji',     'emoji': '🔤', 'pokeapi': 'ja-roma'},
    'KOR': {'label': 'Korean',     'emoji': '🇰🇷', 'pokeapi': 'ko'},
    'CHS': {'label': 'Chinese (Simplified)',  'emoji': '🇨🇳', 'pokeapi': 'zh-hans'},
    'CHT': {'label': 'Chinese (Traditional)', 'emoji': '🇹🇼', 'pokeapi': 'zh-hant'},
    'FRE': {'label': 'French',     'emoji': '🇫🇷', 'pokeapi': 'fr'},
    'GER': {'label': 'German',     'emoji': '🇩🇪', 'pokeapi': 'de'},
    'ESP': {'label': 'Spanish',    'emoji': '🇪🇸', 'pokeapi': 'es'},
    'ITA': {'label': 'Italian',    'emoji': '🇮🇹', 'pokeapi': 'it'},
}
LANGUAGE_ORDER = tuple(LANGUAGES)

# Japanese kanji is deliberately absent. PokeAPI carries it as a tenth language and it is
# character-for-character identical to the kana name for all 1,025 species, so a tag for
# it would be 1,025 duplicate rows and a tenth column in every dex embed saying nothing.

# What a player may actually type for a language. The `!hint` docstring has promised
# `fr` and `ja` since it was written, and neither of them worked - the tags are three
# letters and the comparison was exact.
LANGUAGE_ALIASES = {
    'ja': 'JPN', 'jp': 'JPN', 'jpn': 'JPN', 'japanese': 'JPN', 'kana': 'JPN',
    'rom': 'ROM', 'roma': 'ROM', 'romaji': 'ROM', 'roumaji': 'ROM',
    'romanji': 'ROM',       # the common misspelling, which is what people type
    'ko': 'KOR', 'kr': 'KOR', 'kor': 'KOR', 'korean': 'KOR',
    'zh': 'CHS', 'cn': 'CHS', 'chs': 'CHS', 'zh-hans': 'CHS', 'zh-cn': 'CHS',
    'simplified': 'CHS', 'chinese': 'CHS',
    'cht': 'CHT', 'tw': 'CHT', 'zh-hant': 'CHT', 'zh-tw': 'CHT',
    'traditional': 'CHT',
    'fr': 'FRE', 'fra': 'FRE', 'fre': 'FRE', 'french': 'FRE',
    'de': 'GER', 'deu': 'GER', 'ger': 'GER', 'german': 'GER',
    'es': 'ESP', 'esp': 'ESP', 'spa': 'ESP', 'spanish': 'ESP',
    'it': 'ITA', 'ita': 'ITA', 'italian': 'ITA',
    'en': ENGLISH, 'eng': ENGLISH, 'english': ENGLISH,
}


def resolve_language(text):
    """
    The tag for what the player typed, or None.

    Accepts the tag itself, the ISO code, the language's English name and a couple of
    spellings people actually use. `!hint zh` and `!hint chinese` both mean Simplified,
    which is the one more people read; Traditional needs `cht` or `tw`.
    """
    key = str(text or '').strip().lower()
    if not key:
        return None
    if key.upper() in LANGUAGES or key.upper() == ENGLISH:
        return key.upper()
    return LANGUAGE_ALIASES.get(key)


def language_label(tag, emoji=True):
    """'🇯🇵 Japanese', or just the tag back if it is not one we carry."""
    entry = LANGUAGES.get(str(tag or '').upper())
    if not entry:
        return ENGLISH if str(tag or '').upper() == ENGLISH else str(tag or '')
    return f"{entry['emoji']} {entry['label']}" if emoji else entry['label']


def normalise_name(text):
    """
    A name as the table stores it, which is what `!catch` makes of what a player types.

    Lowercased, whitespace collapsed to single hyphens, everything else left alone -
    `m.-mime`, `type:0` and `nidoran♀` all keep their punctuation, because that is what
    the existing 4,784 rows look like and the two have to agree exactly.
    """
    return '-'.join(str(text or '').strip().lower().split())


def _is_latin(char):
    """Whether a character is Latin, or is not a letter at all."""
    if not char.isalpha():
        return True
    try:
        return 'LATIN' in unicodedata.name(char)
    except ValueError:
        return False


def fold_name(text):
    """
    A name with its Latin accents removed, so an English keyboard can reach it.

    Returns the name UNCHANGED unless every letter in it is Latin. That guard is the
    whole point: NFKD treats Japanese dakuten as combining marks, so folding kana
    blindly turns ガラガラ into カラカラ and makes Marowak indistinguishable from
    Cubone. 1,902 kana and hangul names change under a blind fold; 181 Latin ones change
    under this one, and none of those 181 collide with anything.
    """
    name = normalise_name(text)
    if not name or not all(_is_latin(char) for char in name):
        return name
    return ''.join(char for char in unicodedata.normalize('NFKD', name)
                   if not unicodedata.combining(char))


async def _table_shape(db):
    """
    (does the table exist, does it have the folded column) - in one PRAGMA.

    Both answers come from the same read because `!catch` needs both on every throw, and
    because asking separately is how the two get out of step. A table that does not
    exist reports False for the column too, which is the right answer rather than a
    coincidence: a database with no translation table has no folded names either.

    This replaced a blanket `except Exception: return []` around the whole lookup. That
    swallowed the missing-column error and made the guard below untestable - a control
    that deleted the guard entirely behaved identically, because the exception handler
    quietly did the same job. It would have swallowed real errors just as quietly.
    """
    async with db.execute(f"PRAGMA table_info({TABLE})") as cursor:
        columns = [row[1] for row in await cursor.fetchall()]
    return bool(columns), ('folded' in columns)


async def species_for_name(db, typed):
    """
    Every species the typed name could be, as a list of (english_name, language_tag).

    Tries the faithful spelling first and the folded one only if that finds nothing, so
    an exact match is never outranked by an accent-blind one. That order matters more
    than it looks: `flabebe` is the RŌMAJI spelling of Flabébé as well as the folded
    French one, and the exact answer is the honest one.
    """
    name = normalise_name(typed)
    if not name:
        return []

    exists, folded = await _table_shape(db)
    if not exists:
        return []

    async with db.execute(
            f"SELECT english_name, language_tag FROM {TABLE} "
            f"WHERE foreign_name = ?", (name,)) as cursor:
        exact = await cursor.fetchall()
    if exact:
        return [(row[0], row[1]) for row in exact]

    if not folded:
        return []
    async with db.execute(
            f"SELECT english_name, language_tag FROM {TABLE} "
            f"WHERE folded = ?", (fold_name(typed),)) as cursor:
        return [(row[0], row[1]) for row in await cursor.fetchall()]


async def name_in_language(db, english_name, tag):
    """What this species is called in one language, or None."""
    tag = str(tag or '').upper()
    if not english_name or tag in ('', ENGLISH):
        return None
    async with db.execute(
            f"SELECT foreign_name FROM {TABLE} "
            f"WHERE english_name = ? AND language_tag = ?",
            (english_name, tag)) as cursor:
        row = await cursor.fetchone()
    return row[0] if row else None


async def names_for_species(db, english_name):
    """
    Every language's name for one species, as an ordered {tag: name}.

    Ordered by LANGUAGE_ORDER rather than by whatever the table returns, so the dex
    embed does not reshuffle itself between two species.
    """
    if not english_name:
        return {}
    async with db.execute(
            f"SELECT language_tag, foreign_name FROM {TABLE} WHERE english_name = ?",
            (english_name,)) as cursor:
        found = {row[0]: row[1] for row in await cursor.fetchall()}
    return {tag: found[tag] for tag in LANGUAGE_ORDER if tag in found}
