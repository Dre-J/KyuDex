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

from utils.constants import (CONDITION_TRIGGERS, HABITAT_BIOMES, RITUAL_MIN_LEVEL,
                             RITUAL_RITES)
from utils.db_manager import rule_is_checkable, stated
from utils.formulas import pretty_item
from utils.regions import region_label

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


# ==========================================
# HOW A LINE EVOLVES, IN WORDS
# ==========================================
# `evolution_stages` above draws the SHAPE of a family - Bulbasaur → Ivysaur → Venusaur -
# and says nothing about how to walk it. Everything needed to say that has been sitting in
# evolution_rules' thirteen columns the whole time, unread by anything but the rulebook.
#
# THE ROUTE IS DESCRIBED AS AN INSTRUCTION, NOT AS A ROW. Two places where that means
# reporting on THIS world rather than on the games:
#
#   * a ritual route quotes the level `!evolve <specimen> ritual` actually wants, not the
#     min_level its row happens to carry - Tandemaus' row says 25 and the ritual wants 40,
#     and the row's number is the one a trainer cannot act on.
#   * a level-up rule whose real requirement was never recorded - a mossy rock, a magnetic
#     field, an affection level - says so. It cannot fire, and a blank method beside an
#     arrow reads as "just level it up", which is the one thing that will never work.
EVOLUTION_TABLE = 'evolution_rules'

# The columns every copy of this table has, and the ones that arrive by migration. Guarded
# the same way db_manager guards them and for the same reason: the dex has to keep
# answering on a database that is mid-upgrade.
CORE_RULE_COLUMNS = ('trigger_name', 'min_level', 'item_name', 'min_happiness',
                     'time_of_day', 'held_item', 'known_move', 'known_move_type')
OPTIONAL_RULE_COLUMNS = ('region', 'gender', 'biome', 'stat_rule', 'personality')

# The four skies, said out loud. `dusk` and `full-moon` sit INSIDE day and night rather
# than replacing them - see constants.SPECIAL_SKIES - which is why they read as moments.
SKY_PHRASES = {
    'day': "in daylight", 'night': "at night",
    'dusk': "at dusk", 'full-moon': "under a full moon",
}

GENDER_PHRASES = {'f': "♀ females only", 'm': "♂ males only"}

# What a rule with nothing checkable on it is. Stated once so the panel and any test read
# the same sentence.
NO_ROUTE = "no route here — the games settle this one somewhere this world cannot see"


def article(phrase):
    """`'a'`, or `'an'` before a word that opens with a vowel. 'Use a Ice Stone' was
    the first thing anybody noticed about this panel."""
    return "an" if str(phrase or '')[:1].lower() in 'aeiou' else "a"


def describe_stat_rule(text):
    """`'attack>defense'` -> `'Attack > Defense'`."""
    text = str(text or '').strip().lower()
    for symbol in ('>', '<', '='):
        if symbol in text:
            left, _, right = text.partition(symbol)
            return f"{left.strip().title()} {symbol} {right.strip().title()}"
    return text


def describe_biome(key):
    """`'forest'` -> `'a 🌳 Forest habitat'`, off the one habitat table."""
    key = str(key or '').strip().lower()
    entry = HABITAT_BIOMES.get(key)
    emoji = f"{entry['emoji']} " if entry else ""
    return f"a {emoji}{key.title()} habitat"


def describe_evolution_rule(rule):
    """
    One row of evolution_rules as something a trainer can go and do.

    `rule` is any mapping carrying the table's column names - a sqlite3.Row, or the dicts
    `evolution_routes` hands back. A column that is missing is a requirement that is not
    made, which is what lets this read a half-migrated table without special-casing it.
    """
    trigger = str(rule.get('trigger_name') or '').strip().lower()

    # The two conditions this engine really counts. Their sentence lives beside the
    # threshold it quotes, so raising the bar cannot leave the dex naming the old figure.
    if trigger in CONDITION_TRIGGERS:
        spec = CONDITION_TRIGGERS[trigger]
        return spec['dex'].format(**spec).capitalize()

    # The rites this world has no equivalent of. What the games ask for is worth printing
    # anyway - it is the reason the specimen is stuck - but the actionable half is ours.
    if trigger in RITUAL_RITES:
        return (f"Ritual at Lv. {RITUAL_MIN_LEVEL}+ — in the games, "
                f"{RITUAL_RITES[trigger]}")

    clauses = []
    if trigger == 'use-item':
        item = pretty_item(rule.get('item_name'))
        clauses.append(f"Use {article(item)} {item}")
    elif trigger == 'trade':
        clauses.append("Trade")
    elif stated(rule.get('min_level')):
        clauses.append(f"Lv. {int(rule['min_level'])}")
    elif not stated(rule.get('min_happiness')):
        # Neither a level nor a friendship bar: whatever else it wants, it wants it on a
        # level-up. Suppressed when friendship IS the bar, so Golbat does not read
        # "Level up · friendship 160+" when friendship is the whole of it.
        clauses.append("Level up")

    if stated(rule.get('min_happiness')):
        clauses.append(f"friendship {int(rule['min_happiness'])}+")
    if stated(rule.get('held_item')):
        worn = pretty_item(rule['held_item'])
        clauses.append(f"holding {article(worn)} {worn}")
    if stated(rule.get('time_of_day')):
        sky = str(rule['time_of_day']).strip().lower()
        clauses.append(SKY_PHRASES.get(sky, f"at {sky.replace('-', ' ')}"))
    if stated(rule.get('known_move')):
        clauses.append(f"knowing {pretty_item(rule['known_move'])}")
    if stated(rule.get('known_move_type')):
        clauses.append(f"knowing a {str(rule['known_move_type']).title()}-type move")
    if stated(rule.get('region')):
        clauses.append(f"in {region_label(rule['region'])}")
    if stated(rule.get('biome')):
        clauses.append(f"in {describe_biome(rule['biome'])}")
    if stated(rule.get('gender')):
        clauses.append(GENDER_PHRASES.get(
            str(rule['gender']).strip().lower(), str(rule['gender'])))
    if stated(rule.get('stat_rule')):
        clauses.append(describe_stat_rule(rule['stat_rule']))
    if stated(rule.get('personality')):
        # Wurmple's coin, which was flipped when it was caught and cannot be flipped
        # again. Both of its rules read alike here on purpose - the difference between
        # them is not something a trainer can see, let alone change.
        clauses.append("decided at capture")

    # A level-up rule with nothing checkable on it never fires - the same judgement the
    # rulebook makes, made by the same predicate rather than by a second copy of it.
    if trigger == 'level-up' and not rule_is_checkable(rule):
        return NO_ROUTE
    return " · ".join(clauses)


async def evolution_routes(db, family):
    """
    Every rule out of every member of one line, as dicts keyed by column name.

    Ordered by the parent species and then by row id, so the routes out of one rung stay
    together and the order is the same on every read.
    """
    ids = [int(i) for i in (family or ()) if i is not None]
    if not ids or not await _table_exists(db, EVOLUTION_TABLE):
        return []

    async with db.execute(f"PRAGMA table_info({EVOLUTION_TABLE})") as cursor:
        present = {row[1] for row in await cursor.fetchall()}
    columns = list(CORE_RULE_COLUMNS) + [name for name in OPTIONAL_RULE_COLUMNS
                                         if name in present]

    placeholders = ','.join('?' * len(ids))
    selected = ', '.join(f"er.{name}" for name in columns)
    async with db.execute(
            f"SELECT er.base_species_id, er.evolved_species_id, {selected} "
            f"FROM {EVOLUTION_TABLE} er "
            f"WHERE er.base_species_id IN ({placeholders}) "
            f"ORDER BY er.base_species_id, er.id", tuple(ids)) as cursor:
        rows = await cursor.fetchall()

    return [dict(zip(('base', 'evolved') + tuple(columns), row)) for row in rows]


def stage_index(stages):
    """{pokedex_id: which rung it stands on}, off `evolution_stages`' output."""
    return {pokedex_id: rung
            for rung, members in enumerate(stages or ())
            for pokedex_id, _name in members}


def evolution_route_lines(routes, names, highlight=(), order=None):
    """
    The routes as `Parent → Child — how`, one line each, deduplicated.

    THE DEDUPLICATION IS THE POINT. evolution_rules carries a row per qualifying rule
    rather than per outcome: Eevee has four identical Sylveon rows and Magneton five
    identical Magnezone ones, so a straight render prints Magnezone five times over. Two
    rows describing the same journey the same way ARE one route to a reader.

    A PAIR THAT HAS A REAL ROUTE DOES NOT ALSO ADVERTISE ITS DEAD ONE. Three species keep
    both: Eevee's Leafeon has the unrecorded mossy rock AND a Leaf Stone, Magneton's
    Magnezone the magnetic field AND a Thunder Stone, Feebas' Milotic the beauty stat AND
    a Prism Scale trade. Printing "no route here" beside a route that works is worse than
    saying nothing - it reads as the whole answer.

    `names` maps pokedex_id to something printable; `highlight` is the ids to embolden,
    which is how the species on screen finds itself in its own family tree.

    `order` maps a species to the rung it stands on - `stage_index` builds it - and puts
    the routes in the order they are WALKED. Without it they come back sorted by species
    number, which for Pikachu prints "Pikachu → Raichu" above "Pichu → Pikachu" because
    Pichu is #172 and was added two generations later.
    """
    highlight = set(highlight or ())
    order = order or {}
    routes = sorted(routes or (),
                    key=lambda route: (order.get(route.get('base'), len(order)),
                                       route.get('base') or 0,
                                       route.get('evolved') or 0))
    described = [(route, describe_evolution_rule(route)) for route in routes]
    reachable = {(route.get('base'), route.get('evolved'))
                 for route, method in described if method != NO_ROUTE}

    seen, lines = set(), []
    for route, method in described:
        pair = (route.get('base'), route.get('evolved'))
        if method == NO_ROUTE and pair in reachable:
            continue
        key = pair + (method,)
        if key in seen:
            continue
        seen.add(key)

        def label(pokedex_id):
            shown = names.get(pokedex_id, f"#{pokedex_id}")
            return f"**{shown}**" if pokedex_id in highlight else shown

        lines.append(f"{label(route.get('base'))} → {label(route.get('evolved'))}"
                     f"  —  {method}")
    return lines


# ==========================================
# WHAT THE READER ALREADY OWNS
# ==========================================
CAUGHT_TABLE = 'caught_pokemon'


async def owned_counts(db, user_id, pokedex_ids):
    """
    How many of each of these species one trainer holds, as {id: (total, shiny)}.

    COUNTS EVERYTHING ON THEIR SHEET, including specimens away on a field mission or
    sitting on the GTS. They are still caught: a tally that dropped by one when a
    specimen was deployed would read as one having gone missing.
    """
    ids = [int(i) for i in dict.fromkeys(pokedex_ids or ()) if i is not None]
    if not user_id or not ids:
        return {}
    placeholders = ','.join('?' * len(ids))
    async with db.execute(
            f"SELECT pokedex_id, COUNT(*), "
            f"SUM(CASE WHEN is_shiny THEN 1 ELSE 0 END) "
            f"FROM {CAUGHT_TABLE} WHERE user_id = ? "
            f"AND pokedex_id IN ({placeholders}) GROUP BY pokedex_id",
            (str(user_id), *ids)) as cursor:
        return {row[0]: (row[1], row[2] or 0) for row in await cursor.fetchall()}


def describe_ownership(counts, pokedex_id, forms=()):
    """
    What the trainer has of the shape on screen, and of the species behind it.

    The two numbers are separate on purpose: a Rotom Heat is stored under its own
    pokedex_id, so a trainer with five Rotoms in five shapes has one of each and would
    otherwise be told they have never caught the one they are looking at.
    """
    own, shiny = counts.get(pokedex_id, (0, 0))
    across = sum(total for _id, (total, _s) in counts.items())
    others = [pid for pid, _n in (forms or ()) if pid != pokedex_id]

    if not across:
        return "none caught yet"
    parts = [f"**{own}** of this form" if own else "**none** of this form"]
    if shiny:
        parts.append(f"✨ {shiny} shiny")
    if others and across != own:
        parts.append(f"**{across}** across {len(others) + 1} forms")
    return "  ·  ".join(parts)
