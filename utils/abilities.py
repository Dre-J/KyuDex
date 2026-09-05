"""
What an ability is, and who can have it.

**THE TWO HALVES COME FROM DIFFERENT PLACES, AND ONLY ONE NEEDED THE NETWORK.**
`base_pokemon_species` has always carried `standard_abilities` and `hidden_ability` for
every species, so "who can have Levitate" was answerable locally all along and nobody
could ask. What was missing was the sentence saying what Levitate does, and that is what
`migrate_ability_dex.py` fetches into `base_abilities`.

Nothing here calls out. The migration runs once; this reads two tables.

**A THINNER CARD IS BETTER THAN A CRASH**, the same rule `cogs/dex.py` follows for its
optional tables: on a database that has not had the migration applied, `describe` comes
back with no text and the roster half still works.
"""
import aiosqlite

from utils.constants import DB_FILE

TABLE = 'base_abilities'

# The literal the species import wrote where a species has no hidden ability. It is not
# an ability, and it must never reach a lookup or a suggestion list.
NOT_AN_ABILITY = {'', 'none', 'null'}

MAX_SUGGESTIONS = 5


def normalise(text):
    """`Flash Fire`, `flash_fire` and `FLASH FIRE` are all `flash-fire`."""
    flat = str(text or '').strip().lower().replace('_', '-').replace(' ', '-')
    while '--' in flat:
        flat = flat.replace('--', '-')
    return flat.strip('-')


def pretty_ability(name):
    """`flash-fire` -> `Flash Fire`, for anything with no display name on file."""
    return str(name or '').replace('-', ' ').title()


async def _table_exists(db, table):
    async with db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
            (table,)) as cursor:
        return await cursor.fetchone() is not None


async def known_abilities(db):
    """
    Every ability any species in this world can have, sorted.

    Read from the species table rather than from `base_abilities`, so a lookup works for
    an ability the migration has not described yet - the card then shows the roster and
    says the description is missing, which is more use than "no such ability".
    """
    names = set()
    async with db.execute(
            "SELECT standard_abilities, hidden_ability FROM base_pokemon_species") as c:
        for standard, hidden in await c.fetchall():
            for raw in (standard or '').split(','):
                name = normalise(raw)
                if name not in NOT_AN_ABILITY:
                    names.add(name)
            name = normalise(hidden)
            if name not in NOT_AN_ABILITY:
                names.add(name)
    return sorted(names)


def suggest(typed, pool, limit=MAX_SUGGESTIONS):
    """
    Abilities this might have meant, best first.

    Three passes for three different mistakes, the same order `utils.species` uses: a
    prefix catches a half-typed name, a substring catches a forgotten first word
    ("guard" for `wonder-guard`), and difflib catches an ordinary typo.
    """
    needle = normalise(typed)
    if not needle:
        return []

    import difflib
    prefix = [n for n in pool if n.startswith(needle)]
    contains = [n for n in pool if needle in n and n not in prefix]
    close = [n for n in difflib.get_close_matches(needle, pool, n=limit, cutoff=0.6)
             if n not in prefix and n not in contains]
    return (prefix + contains + close)[:limit]


async def describe(db, name):
    """
    `{'display', 'short_effect', 'effect', 'generation'}` for one ability, or None.

    None means the migration has not described it - NOT that the ability does not exist.
    The caller decides what to say about that.
    """
    if not await _table_exists(db, TABLE):
        return None
    async with db.execute(
            f"SELECT display, short_effect, effect, generation FROM {TABLE} "
            f"WHERE name = ?", (normalise(name),)) as cursor:
        row = await cursor.fetchone()
    if not row:
        return None
    display, short_effect, effect, generation = row
    return {'display': display or pretty_ability(name),
            'short_effect': short_effect or '',
            'effect': effect or short_effect or '',
            'generation': generation}


async def bearers(db, name):
    """
    `(standard, hidden)` - the species that can have this ability, each as a name list.

    A species appears in exactly one of the two lists per row it has, and a handful carry
    the same ability both ways; those are listed under `standard`, which is the one a
    trainer can actually walk in with.

    Matched on the ability's position in a comma-separated column, so `LIKE '%name%'`
    would not do: `heatproof` is a substring of nothing, but `guard` is a substring of
    seven other abilities and `overgrow` of none - the difference is not a rule anybody
    should have to remember.
    """
    wanted = normalise(name)
    standard, hidden = [], []
    async with db.execute(
            "SELECT name, standard_abilities, hidden_ability FROM base_pokemon_species "
            "ORDER BY pokedex_id") as cursor:
        for species, standard_column, hidden_column in await cursor.fetchall():
            slots = {normalise(part) for part in (standard_column or '').split(',')}
            if wanted in slots:
                standard.append(species)
            elif normalise(hidden_column) == wanted:
                hidden.append(species)
    return standard, hidden


async def lookup(typed):
    """
    `(name, complaint)` - the ability the trainer meant, or a sentence saying why not.

    Opened read-only, because a lookup must never be the thing that alters the schema.
    """
    wanted = normalise(typed)
    if not wanted:
        return None, "🧬 Which trait? `!abilitydex levitate`."

    async with aiosqlite.connect(f"file:{DB_FILE}?mode=ro", uri=True) as db:
        pool = await known_abilities(db)

    if wanted in pool:
        return wanted, None

    hints = suggest(wanted, pool)
    hint = ("  Did you mean: " + ", ".join(f"`{h}`" for h in hints)) if hints else ""
    return None, f"🧬 No trait called `{typed}` is on file.{hint}"
