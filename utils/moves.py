"""
What a move is, and what it does.

**`base_moves` IS NINE HUNDRED ROWS OF NUMBERS AND NOT ONE WORD OF PROSE.** Everything the
engine needs to RESOLVE a move and nothing that says what it does - so `!movedex` could
say Thousand Arrows is Ground, 90 power, and not that it drags fliers out of the sky.

`migrate_move_dex.py` fills that from PokeAPI once, into `base_move_text`. Nothing here
calls out, and a database without that table shows the numbers and no prose rather than
refusing the lookup - the same rule `cogs/dex.py` follows for its own optional tables.
"""
import aiosqlite

from utils.constants import DB_FILE

TABLE = 'base_move_text'

MAX_SUGGESTIONS = 5

# What the engine calls the two halves of a Z-Move, which is not what a person types. A
# trainer asking for `acid-downpour` means the move, not one of its damage classes.
CLASS_SUFFIXES = ('--physical', '--special')


def normalise(text):
    """`Solar Beam`, `solar_beam` and `SOLAR BEAM` all reach `solar-beam`."""
    flat = str(text or '').strip().lower().replace('_', '-').replace(' ', '-')
    while '---' in flat:
        flat = flat.replace('---', '--')
    return flat.strip('-')


def pretty_move(name):
    """`solar-beam` -> `Solar Beam`, and a Z-Move without its class suffix."""
    bare = str(name or '')
    for suffix in CLASS_SUFFIXES:
        if bare.endswith(suffix):
            bare = bare[:-len(suffix)]
    return bare.replace('-', ' ').title()


async def _table_exists(db, table):
    async with db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
            (table,)) as cursor:
        return await cursor.fetchone() is not None


async def known_moves(db):
    """Every move the engine can resolve, sorted."""
    async with db.execute(
            "SELECT name FROM base_moves WHERE name IS NOT NULL "
            "AND TRIM(name) != '' ORDER BY name") as cursor:
        return [row[0] for row in await cursor.fetchall()]


def suggest(typed, pool, limit=MAX_SUGGESTIONS):
    """Moves this might have meant - prefix, then substring, then typo."""
    needle = normalise(typed)
    if not needle:
        return []

    import difflib
    prefix = [n for n in pool if n.startswith(needle)]
    contains = [n for n in pool if needle in n and n not in prefix]
    close = [n for n in difflib.get_close_matches(needle, pool, n=limit, cutoff=0.6)
             if n not in prefix and n not in contains]
    return (prefix + contains + close)[:limit]


async def stats(db, name):
    """Every column `base_moves` has for one move, as a dict, or None."""
    async with db.execute(
            "SELECT name, type, power, accuracy, damage_class, pp, priority, target, "
            "       ailment, ailment_chance, stat_name, stat_change, stat_chance, "
            "       status_type, status_chance, healing, drain "
            "FROM base_moves WHERE name = ?", (name,)) as cursor:
        row = await cursor.fetchone()
    if not row:
        return None
    keys = ('name', 'type', 'power', 'accuracy', 'damage_class', 'pp', 'priority',
            'target', 'ailment', 'ailment_chance', 'stat_name', 'stat_change',
            'stat_chance', 'status_type', 'status_chance', 'healing', 'drain')
    return dict(zip(keys, row))


async def text_table_ready(db):
    """
    Whether the descriptions have been imported at all.

    **A DIFFERENT QUESTION FROM "IS THIS MOVE DESCRIBED".** Forty-two moves have no
    PokeAPI entry to import - every Z-Move, and the Starmobile torques - so telling a
    trainer to run the migration would be advice that cannot help. The card only says
    that when the table is genuinely absent.
    """
    return await _table_exists(db, TABLE)


async def describe(db, name):
    """
    `{'display', 'short_effect', 'effect', 'flavour', 'generation'}`, or None.

    None means the migration has not described it - not that the move does not exist.
    """
    if not await _table_exists(db, TABLE):
        return None
    async with db.execute(
            f"SELECT display, short_effect, effect, flavour, generation FROM {TABLE} "
            f"WHERE name = ?", (name,)) as cursor:
        row = await cursor.fetchone()
    if not row:
        return None
    display, short_effect, effect, flavour, generation = row
    return {'display': display or pretty_move(name),
            'short_effect': short_effect or '',
            'effect': effect or short_effect or '',
            'flavour': flavour or '',
            'generation': generation}


async def lookup(typed):
    """
    `(name, complaint)` - the move meant, or a sentence saying why not.

    A Z-Move typed bare resolves to its physical half, because the two rows differ only
    in the class they inherit and a trainer asking for Acid Downpour wants the move.
    """
    wanted = normalise(typed)
    if not wanted:
        return None, "📖 Which move? `!movedex thousand-arrows`."

    async with aiosqlite.connect(f"file:{DB_FILE}?mode=ro", uri=True) as db:
        pool = await known_moves(db)

    if wanted in pool:
        return wanted, None

    for suffix in CLASS_SUFFIXES:
        if wanted + suffix in pool:
            return wanted + suffix, None

    hints = suggest(wanted, pool)
    hint = ("  Did you mean: " + ", ".join(f"`{h}`" for h in hints)) if hints else ""
    return None, f"📖 No move called `{typed}` is on file.{hint}"
