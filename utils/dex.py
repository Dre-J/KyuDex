"""
Reading a Pokédex entry: the facts, and the flavour text that goes with them.

Everything here answers gracefully on a database that has not had migrate_dex_data.py
applied - `None`, or an empty list - because `!dex` should show a thinner entry rather
than fall over, and because the migration is meant to be applied to a running bot.

**FLAVOUR TEXT IS STORED PER VERSION AND READ IN GROUPS.** A species averages 14 entries
and many are word-for-word repeats: Red, Blue and Yellow usually share one. Storing them
separately keeps which game said what; grouping them here is what stops the reader
paging through the same sentence three times. Bulbasaur's 22 entries become 12 pages.
"""
from collections import OrderedDict

DEX_TABLE = 'species_dex'
FLAVOUR_TABLE = 'species_flavour'

# What the games measure in. Height is decimetres and weight is hectograms, both in
# base_pokemon_species, and both have been shown raw in at least one embed already.
DECIMETRES_TO_METRES = 10.0
HECTOGRAMS_TO_KILOS = 10.0
METRES_TO_FEET = 3.28084
KILOS_TO_POUNDS = 2.20462

# An egg's hatch counter is cycles, not steps. The step count differs by generation -
# 255 in Generation 1-7, 128 from Generation 8 - and this world has no walking, so the
# cycles are what is shown and the steps are a parenthetical.
STEPS_PER_CYCLE = 255


async def _table_exists(db, table):
    async with db.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table,)) as cursor:
        return (await cursor.fetchone())[0] > 0


async def dex_facts(db, pokedex_id):
    """
    The one-row facts for a species, as a dict, or {} if the migration has not run.

    A dict rather than a tuple because the caller reads five of nine fields and a tuple
    index is how the wrong one gets shown.
    """
    if not await _table_exists(db, DEX_TABLE):
        return {}
    async with db.execute(
            f"SELECT genus, generation, hatch_counter, base_happiness, is_baby, "
            f"has_gender_differences, egg_group_1, egg_group_2 "
            f"FROM {DEX_TABLE} WHERE pokedex_id = ?", (pokedex_id,)) as cursor:
        row = await cursor.fetchone()
    if not row:
        return {}
    return {
        'genus': row[0], 'generation': row[1], 'hatch_counter': row[2],
        'base_happiness': row[3], 'is_baby': bool(row[4]),
        'has_gender_differences': bool(row[5]),
        'egg_groups': [group for group in (row[6], row[7]) if group],
    }


async def flavour_entries(db, pokedex_id):
    """
    Every flavour entry for a species, grouped by identical text, newest group last.

    Returns [(text, [version names])]. The grouping is the point: Bulbasaur has 22
    entries and 12 distinct texts, and paging through the ten repeats would be a worse
    dex than one that showed a single line.

    Versions inside a group stay in release order, and the groups are ordered by the
    OLDEST version that used each text - so reading top to bottom walks forwards in time
    rather than jumping about.
    """
    if not await _table_exists(db, FLAVOUR_TABLE):
        return []
    # Ordered by GENERATION first and version_id second. Version ids are not quite
    # chronological - Colosseum and XD are Generation 3 games that were added to
    # PokeAPI's table after Black and White, so they carry higher ids - and sorting on
    # the id alone would file them after Unova. Neither has an English flavour row today,
    # so this changes nothing about the current data; it is here so that it still reads
    # in order if they ever gain one.
    async with db.execute(
            f"SELECT flavour, version FROM {FLAVOUR_TABLE} "
            f"WHERE pokedex_id = ? ORDER BY generation, version_id",
            (pokedex_id,)) as cursor:
        rows = await cursor.fetchall()

    grouped = OrderedDict()
    for text, version in rows:
        grouped.setdefault(text, []).append(version)
    return [(text, versions) for text, versions in grouped.items()]


async def flavour_versions(db, pokedex_id):
    """Which games have an entry for this species, in release order."""
    if not await _table_exists(db, FLAVOUR_TABLE):
        return []
    async with db.execute(
            f"SELECT version FROM {FLAVOUR_TABLE} "
            f"WHERE pokedex_id = ? ORDER BY generation, version_id",
            (pokedex_id,)) as cursor:
        return [row[0] for row in await cursor.fetchall()]


def describe_versions(versions, limit=4):
    """'Red, Blue, Yellow' - and '…and 6 more' rather than a wall of game names."""
    versions = list(versions or ())
    if not versions:
        return ''
    if len(versions) <= limit:
        return ", ".join(versions)
    return f"{', '.join(versions[:limit])} and {len(versions) - limit} more"


def describe_height(decimetres):
    """`0.7 m (2′04″)` - metric first, because the rest of the bot is metric."""
    if not decimetres:
        return "—"
    metres = decimetres / DECIMETRES_TO_METRES
    total_inches = round(metres * METRES_TO_FEET * 12)
    return f"{metres:.1f} m ({total_inches // 12}′{total_inches % 12:02d}″)"


def describe_weight(hectograms):
    """`6.9 kg (15.2 lbs)`."""
    if not hectograms:
        return "—"
    kilos = hectograms / HECTOGRAMS_TO_KILOS
    return f"{kilos:.1f} kg ({kilos * KILOS_TO_POUNDS:.1f} lbs)"


def describe_gender_ratio(gender_rate):
    """
    What `gender_rate` means in words.

    It is EIGHTHS FEMALE, and -1 means genderless - which is not a ratio at all and is
    the value most likely to be rendered as "-12.5% female" by arithmetic that forgot to
    check for it.
    """
    if gender_rate is None or gender_rate < 0:
        return "Genderless"
    female = gender_rate / 8.0 * 100
    if female == 0:
        return "100% ♂"
    if female == 100:
        return "100% ♀"
    return f"{100 - female:.1f}% ♂ / {female:.1f}% ♀"


def describe_hatch(hatch_counter):
    """`20 cycles (~5,100 steps)`, or an em dash for a species that cannot breed."""
    if not hatch_counter:
        return "—"
    return f"{hatch_counter} cycles (~{hatch_counter * STEPS_PER_CYCLE:,} steps)"


def describe_egg_groups(groups):
    if not groups:
        return "—"
    return " / ".join(groups)


# ==========================================
# FORMS
# ==========================================
FORMS_TABLE = 'species_forms'

# The six stats, in the order every game prints them. base_pokemon_stats spells two of
# them with a hyphen, which is why this is a mapping and not a sort.
STAT_ORDER = (('hp', 'HP'), ('attack', 'Atk'), ('defense', 'Def'),
              ('special-attack', 'SpA'), ('special-defense', 'SpD'), ('speed', 'Spe'))
STAT_BAR_MAX = 200      # Blissey's 255 HP would otherwise be the only full bar
STAT_BAR_WIDTH = 10


async def base_species(db, pokedex_id):
    """
    The species a form belongs to, or the id back unchanged.

    Returns the id itself when the mapping is missing rather than None, so a caller on an
    unmigrated database treats every form as its own species - which is exactly how the
    rest of the bot has always behaved.
    """
    if not await _table_exists(db, FORMS_TABLE):
        return pokedex_id
    async with db.execute(
            f"SELECT base_pokedex_id FROM {FORMS_TABLE} WHERE pokedex_id = ?",
            (pokedex_id,)) as cursor:
        row = await cursor.fetchone()
    return row[0] if row else pokedex_id


async def form_siblings(db, pokedex_id):
    """
    Every form sharing this one's base species, default first, as [(id, name)].

    This is what the form button walks. It cannot be done by NAME - splitting on the
    first hyphen works for `rotom-heat` and destroys `mr-mime`, `ho-oh`, `type-null` and
    `jangmo-o` - which is why migrate_dex_data.py imports the mapping.
    """
    if not await _table_exists(db, FORMS_TABLE):
        return []
    base = await base_species(db, pokedex_id)
    async with db.execute(
            f"SELECT f.pokedex_id, s.name FROM {FORMS_TABLE} f "
            f"JOIN base_pokemon_species s ON s.pokedex_id = f.pokedex_id "
            f"WHERE f.base_pokedex_id = ? "
            f"ORDER BY f.is_default DESC, f.pokedex_id", (base,)) as cursor:
        return [(row[0], row[1]) for row in await cursor.fetchall()]


async def base_stats(db, pokedex_id):
    """The six base stats in printing order, as [(label, value)], plus the total."""
    async with db.execute(
            "SELECT stat_name, base_value FROM base_pokemon_stats WHERE pokedex_id = ?",
            (pokedex_id,)) as cursor:
        found = {row[0]: row[1] for row in await cursor.fetchall()}
    rows = [(label, found.get(key, 0)) for key, label in STAT_ORDER]
    return rows, sum(value for _label, value in rows)


def stat_bar(value, width=STAT_BAR_WIDTH, ceiling=STAT_BAR_MAX):
    """
    A ten-cell bar for one base stat.

    Capped at 200 rather than at 255: only Blissey's HP and Eternatus' reach the top of
    that range, so scaling to it would leave every ordinary species drawing half a bar.
    """
    filled = max(0, min(width, round((value or 0) / ceiling * width)))
    return "█" * filled + "░" * (width - filled)


async def evolution_stages(db, family):
    """
    An evolutionary line as ORDERED STAGES: [[(id, name)], [(id, name), ...], ...].

    `evolution_family` returns the ids sorted numerically, which is not the order they
    evolve in and reads as nonsense for any line whose baby was added in a later
    generation: Pikachu's family sorted by number is "Pikachu, Raichu, Pichu", because
    Pichu is #172 and Raichu is #26.

    So the depth is computed from evolution_rules instead. Members at the same depth are
    siblings - Eevee's nine, or a species and its regional twin - and stay together on
    one rung.
    """
    if not family:
        return []
    placeholders = ','.join('?' * len(family))
    # Only the evolved side is restricted. Restricting the base side too was in the first
    # draft and is redundant - `family` is the WHOLE line, so any parent of a member is
    # already in it - and a negative control that deleted it changed nothing, which is
    # how it was noticed.
    async with db.execute(
            f"SELECT evolved_species_id, base_species_id FROM evolution_rules "
            f"WHERE evolved_species_id IN ({placeholders})",
            tuple(family)) as cursor:
        parents = {row[0]: row[1] for row in await cursor.fetchall()}
    async with db.execute(
            f"SELECT pokedex_id, name FROM base_pokemon_species "
            f"WHERE pokedex_id IN ({placeholders})", tuple(family)) as cursor:
        names = {row[0]: row[1] for row in await cursor.fetchall()}

    def depth(pokedex_id, seen=None):
        # `seen` guards against a cycle in the rules rather than trusting them: a loop
        # here would hang the command, and reference data has been wrong before.
        seen = seen or set()
        parent = parents.get(pokedex_id)
        if parent is None or parent in seen or parent == pokedex_id:
            return 0
        return 1 + depth(parent, seen | {pokedex_id})

    rungs = {}
    for pokedex_id in family:
        rungs.setdefault(depth(pokedex_id), []).append(pokedex_id)
    return [[(pokedex_id, names.get(pokedex_id, str(pokedex_id)))
             for pokedex_id in sorted(rungs[level])]
            for level in sorted(rungs)]


async def species_types(db, pokedex_id):
    """This species' elements, in slot order."""
    async with db.execute(
            "SELECT type_name FROM base_pokemon_types WHERE pokedex_id = ? "
            "ORDER BY rowid", (pokedex_id,)) as cursor:
        return [row[0] for row in await cursor.fetchall()]
