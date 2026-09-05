"""
What Showdown's players run, filtered to what this world can actually field.

**A SMOGON SET IS ADVICE FROM A DIFFERENT GAME.** Level 100, team preview, its own
banlist, and a movepool frozen to one generation. This world has level caps, its own
rules, and a movepool spanning every generation - so a set copied across verbatim can
name a move the species cannot learn here, an item that is not on the shelf, or an
ability it was never given.

**SO THE FIGURES ARE STORED RAW AND FILTERED ON THE WAY OUT.** `migrate_showdown_spreads`
writes exactly what Smogon published; everything here drops what cannot be fielded and
COUNTS what it dropped. That count is the honest part: once anything is removed the
percentages no longer sum to Smogon's, and a card that hid the removal would be
presenting an approximation as though it were the real figure.

**TERA IS DROPPED WHOLE.** Nothing in this engine terastallises - `tera_type` is read by
one move and set by nothing - so a Tera panel would be advice a player cannot take.

Nothing here calls out. The migration runs once; this reads three local tables.
"""
import re

import aiosqlite

from utils.constants import DB_FILE, NATURES, EV_TOTAL_CAP
from utils.items import CATALOGUE
from utils.species import normalise as normalise_species, resolve_species

USAGE_TABLE = 'showdown_usage'
SPECIES_TABLE = 'showdown_species'

DEFAULT_FORMAT = 'gen9ou'

# What a card is willing to show, in the order it shows it. `tera` is deliberately absent:
# see the module docstring.
SHOWN_KINDS = ('spread', 'move', 'item', 'ability', 'teammate')

# The six stats a Smogon spread names, in the order it names them.
SPREAD_STATS = ('hp', 'attack', 'defense', 'sp_atk', 'sp_def', 'speed')


def _flat(text):
    """`Rocky Helmet` -> `rocky-helmet`, which is how this world spells everything."""
    flat = str(text or '').strip().lower().replace('_', '-').replace(' ', '-')
    while '--' in flat:
        flat = flat.replace('--', '-')
    return flat.strip('-')


# **FIVE OF THE 291 SPECIES ARE SPELLED DIFFERENTLY BY SMOGON**, and they are three tidy
# patterns rather than five separate accidents: Showdown abbreviates the gendered forms to
# `-F`, drops `-mask` from Ogerpon's, and drops `-breed` from Paldean Tauros. Written out
# rather than guessed at with a rule - a rule that appends `-mask` to anything unresolved
# would also invent `pikachu-mask` - and small enough to read.
#
# Measured, not assumed: with these five, every species in the imported stats resolves.
SHOWDOWN_ALIASES = {
    'basculegion-f': 'basculegion-female',
    'indeedee-f': 'indeedee-female',
    'ogerpon-wellspring': 'ogerpon-wellspring-mask',
    'ogerpon-hearthflame': 'ogerpon-hearthflame-mask',
    'ogerpon-cornerstone': 'ogerpon-cornerstone-mask',
    'tauros-paldea-blaze': 'tauros-paldea-blaze-breed',
    'tauros-paldea-combat': 'tauros-paldea-combat-breed',
    'tauros-paldea-aqua': 'tauros-paldea-aqua-breed',
}

# Smogon's placeholder for a set that left a slot empty. A real percentage naming no move.
PLACEHOLDERS = {'nothing', 'other', 'none'}


def resolve_showdown(name):
    """The species this world calls that, or None. Aliases first, then the usual door."""
    aliased = SHOWDOWN_ALIASES.get(_flat(name))
    if aliased:
        return aliased
    return resolve_species(name)


def showdown_spellings(canonical):
    """
    Every spelling the stats might file this species under.

    **THE ALIAS HAS TO WORK BOTH WAYS.** Resolving `Ogerpon-Wellspring` to
    `ogerpon-wellspring-mask` is what makes the teammate list legible; QUERYING for it
    needs the journey back, because the table stores what Smogon published. Without this,
    `!spread ogerpon-wellspring` resolved the name perfectly and then looked up a spelling
    that is not in the table.
    """
    spellings = {canonical}
    spellings.update(spelling for spelling, kyu in SHOWDOWN_ALIASES.items()
                     if kyu == canonical)
    return sorted(spellings)


def parse_spread(value):
    """
    `Jolly:0/252/4/0/0/252` -> `{'nature': 'jolly', 'evs': {...}, 'total': 508}`, or None.

    None for anything that does not parse, which includes the handful of malformed rows
    Smogon publishes when a set had no nature recorded at all.
    """
    if ':' not in str(value or ''):
        return None
    nature, _, numbers = str(value).partition(':')
    parts = numbers.split('/')
    if len(parts) != len(SPREAD_STATS):
        return None
    try:
        values = [int(p) for p in parts]
    except ValueError:
        return None
    return {'nature': _flat(nature),
            'evs': dict(zip(SPREAD_STATS, values)),
            'total': sum(values)}


# How a spread reads out loud. Smogon writes `Jolly:0/252/4/0/0/252`, which is six
# numbers a reader has to count along to interpret.
STAT_LABELS = {'hp': 'HP', 'attack': 'Atk', 'defense': 'Def',
               'sp_atk': 'SpA', 'sp_def': 'SpD', 'speed': 'Spe'}


def describe_spread(value):
    """
    `Jolly:0/252/4/0/0/252` -> `Jolly · 252 Atk / 252 Spe / 4 Def`.

    The zeroes are dropped and the rest sorted heaviest first, because a spread is read
    as "what did they invest in" rather than as a row of six positions - and four of the
    six are usually zero.
    """
    parsed = parse_spread(value)
    if not parsed:
        return str(value or '')
    invested = sorted(((stat, ev) for stat, ev in parsed['evs'].items() if ev),
                      key=lambda pair: -pair[1])
    if not invested:
        return f"{parsed['nature'].title()} · no investment"
    spread = " / ".join(f"{ev} {STAT_LABELS[stat]}" for stat, ev in invested)
    return f"{parsed['nature'].title()} · {spread}"


def spread_is_legal(parsed):
    """
    Whether this world would let a trainer build that spread.

    The caps happen to match Smogon's exactly - 510 total, 252 to a stat - so this almost
    never fires. Almost never is not never: a spread naming a nature this world does not
    have would be a set nobody could follow, and checking is a line.
    """
    if not parsed:
        return False
    # NATURES is a list of capitalised names; a spread names them the same way
    # Smogon prints them, so the comparison has to be folded.
    if parsed['nature'] not in {n.lower() for n in NATURES}:
        return False
    if parsed['total'] > EV_TOTAL_CAP:
        return False
    return all(0 <= value <= 252 for value in parsed['evs'].values())


async def _table_exists(db, table):
    async with db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
            (table,)) as cursor:
        return await cursor.fetchone() is not None


async def imported(db):
    """Whether any usage data has been imported at all."""
    return await _table_exists(db, USAGE_TABLE)


async def formats(db):
    """Every format imported, with the month each came from."""
    if not await _table_exists(db, SPECIES_TABLE):
        return []
    async with db.execute(
            f"SELECT format, month, COUNT(*) FROM {SPECIES_TABLE} "
            f"GROUP BY format ORDER BY format") as cursor:
        return [{'format': row[0], 'month': row[1], 'species': row[2]}
                for row in await cursor.fetchall()]


async def _legal_moves(db, pokedex_id):
    """Every move this species can learn HERE, by any route."""
    async with db.execute(
            "SELECT DISTINCT move_name FROM species_movepool WHERE pokedex_id = ?",
            (pokedex_id,)) as cursor:
        return {row[0] for row in await cursor.fetchall()}


async def _legal_abilities(db, pokedex_id):
    """Every ability this species can have HERE, standard or hidden."""
    async with db.execute(
            "SELECT standard_abilities, hidden_ability FROM base_pokemon_species "
            "WHERE pokedex_id = ?", (pokedex_id,)) as cursor:
        row = await cursor.fetchone()
    if not row:
        return set()
    names = {_flat(part) for part in (row[0] or '').split(',')}
    names.add(_flat(row[1]))
    return {name for name in names if name and name != 'none'}


async def sets_for(db, canonical, pokedex_id, fmt=DEFAULT_FORMAT):
    """
    `{'kinds': {...}, 'dropped': {...}, 'meta': {...}}` for one species, filtered.

    `kinds` holds the entries this world can field, best-used first. `dropped` counts what
    was removed per kind and names a few, so the card can say so out loud rather than
    presenting a filtered percentage as if it were Smogon's.
    """
    if not await _table_exists(db, USAGE_TABLE):
        return None

    # Matched against every spelling the stats might file it under - see
    # `showdown_spellings`, because the table holds Smogon's names and not ours.
    spellings = showdown_spellings(canonical)
    slots = ', '.join('?' * len(spellings))

    async with db.execute(
            f"SELECT raw_count, viability, month FROM {SPECIES_TABLE} "
            f"WHERE format = ? AND LOWER(REPLACE(species, ' ', '-')) IN ({slots})",
            (fmt, *spellings)) as cursor:
        meta_row = await cursor.fetchone()
    if not meta_row:
        return None

    async with db.execute(
            f"SELECT kind, value, usage FROM {USAGE_TABLE} "
            f"WHERE format = ? AND LOWER(REPLACE(species, ' ', '-')) IN ({slots}) "
            f"ORDER BY kind, usage DESC", (fmt, *spellings)) as cursor:
        rows = await cursor.fetchall()

    learnable = await _legal_moves(db, pokedex_id)
    has_ability = await _legal_abilities(db, pokedex_id)

    kinds = {kind: [] for kind in SHOWN_KINDS}
    dropped = {kind: [] for kind in SHOWN_KINDS}

    for kind, value, usage in rows:
        if kind not in kinds:
            # `tera`, which this engine has no mechanic for. Not counted as dropped
            # either: it was never on offer, so it is not something a trainer is missing.
            continue

        keep, shown = True, value
        if _flat(value) in PLACEHOLDERS:
            # Smogon's name for a set that left the slot empty. A real
            # percentage naming nothing, so it is not a drop either.
            continue
        if kind == 'move':
            keep = _flat(value) in learnable
        elif kind == 'item':
            keep = _flat(value) in CATALOGUE
        elif kind == 'ability':
            keep = _flat(value) in has_ability
        elif kind == 'spread':
            keep = spread_is_legal(parse_spread(value))
        elif kind == 'teammate':
            # A teammate is a suggestion rather than something to equip, so the only
            # question is whether this world has the species at all.
            keep = resolve_showdown(value) is not None

        (kinds if keep else dropped)[kind].append(
            {'value': shown, 'usage': usage} if keep else shown)

    return {
        'format': fmt,
        'month': meta_row[2],
        'raw_count': meta_row[0],
        'viability': meta_row[1],
        'kinds': kinds,
        'dropped': dropped,
    }


async def lookup(typed, fmt=DEFAULT_FORMAT):
    """
    `(payload, complaint)` for a species name a person typed.

    Resolved through `utils.species` so every spelling `!dex` accepts works here too -
    including the bare form names, which is the difference between `!spread urshifu` and
    a refusal.
    """
    if not str(typed or '').strip():
        return None, "📊 Which specimen? `!spread great-tusk`."

    canonical = resolve_showdown(typed)
    if not canonical:
        return None, f"📊 No specimen called `{typed}` is on file."

    async with aiosqlite.connect(f"file:{DB_FILE}?mode=ro", uri=True) as db:
        if not await imported(db):
            return None, ("📊 No usage data has been imported yet — run "
                          "`migrate_showdown_spreads.py --apply`.")

        async with db.execute(
                "SELECT pokedex_id FROM base_pokemon_species WHERE name = ?",
                (canonical,)) as cursor:
            row = await cursor.fetchone()
        if not row:
            return None, f"📊 No specimen called `{typed}` is on file."

        payload = await sets_for(db, canonical, row[0], fmt)
        if payload is None:
            known = await formats(db)
            names = ", ".join(f"`{f['format']}`" for f in known) or "none"
            return None, (f"📊 Showdown's {fmt} players did not field "
                          f"**{canonical.replace('-', ' ').title()}**. "
                          f"Imported formats: {names}.")
        payload['species'] = canonical
        return payload, None


def split_request(request):
    """
    `great-tusk gen9uu` -> `('great-tusk', 'gen9uu')`, and a bare name keeps the default.

    The format is recognised by its SHAPE rather than by position: a Showdown format id
    is `gen` followed by a digit and letters, which no species name is. Splitting on the
    last word instead would break every two-word species - `great tusk` would look up
    `great` in the format `tusk`.
    """
    words = str(request or '').split()
    if not words:
        return '', DEFAULT_FORMAT
    if len(words) > 1 and re.fullmatch(r'gen\d[a-z0-9]*', words[-1].lower()):
        return ' '.join(words[:-1]), words[-1].lower()
    return ' '.join(words), DEFAULT_FORMAT
