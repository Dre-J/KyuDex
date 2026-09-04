import sqlite3
# Assuming you define DB_FILE = "ecosystem.db" in constants.py
from utils.constants import (DB_FILE, SPECIAL_SKIES, CONDITION_TRIGGERS,
                             RITUAL_TRIGGERS, nature_multiplier,
                             personality_of, stat_rule_holds)
from utils.formulas import calculate_real_stat 

def get_connection():
    """A simple helper so you never have to type the DB name repeatedly."""
    return sqlite3.connect(DB_FILE)

def get_active_partner(user_id: str):
    """Used by almost every command (!learn, !deploy, !catch) to find the lead specimen."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT active_partner FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result and result[0] else None

def get_specimen_data(instance_id: str):
    """Fetches everything about a specific caught specimen."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT cp.pokedex_id, cp.level, cp.happiness, s.name, 
               cp.move_1, cp.move_2, cp.move_3, cp.move_4
        FROM caught_pokemon cp
        JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
        WHERE cp.instance_id = ?
    """, (instance_id,))
    result = cursor.fetchone()
    conn.close()
    return result

async def known_move_types(db, moves):
    """
    The set of elements a specimen's moveset covers, for Eevee -> Sylveon.

    Asked of base_moves rather than of a table in constants.py, because the move's element
    is already stored once and a second copy would be a second thing to keep in step.
    """
    names = [m for m in (moves or []) if m]
    if not names:
        return set()
    placeholders = ','.join('?' * len(names))
    async with db.execute(
            f"SELECT DISTINCT type FROM base_moves WHERE name IN ({placeholders})",
            names) as cursor:
        return {row[0] for row in await cursor.fetchall() if row[0]}


async def check_condition_evolution(db, pokedex_id, counters):
    """
    An evolution earned by something that HAPPENED, or None.

    `counters` is whatever the caller has of caught_pokemon's battle tallies, keyed by
    column name. A counter the caller does not have is simply not satisfied, which is the
    safe direction: no evolution fires on a number nobody counted.

    Kept separate from check_evolution_trigger rather than folded into it, because these
    rules are not `level-up` rules at all - they carry their own trigger names, and the
    question "did this happen" has nothing to do with "is this specimen ready".
    """
    if not counters:
        return None

    triggers = tuple(CONDITION_TRIGGERS)
    placeholders = ','.join('?' * len(triggers))
    async with db.execute(f"""
        SELECT er.evolved_species_id, s.name, er.trigger_name
        FROM evolution_rules er
        JOIN base_pokemon_species s ON er.evolved_species_id = s.pokedex_id
        WHERE er.base_species_id = ? AND er.trigger_name IN ({placeholders})
    """, (pokedex_id, *triggers)) as cursor:
        candidates = await cursor.fetchall()

    for evolved_id, name, trigger in candidates:
        rule = CONDITION_TRIGGERS[trigger]
        if (counters.get(rule['column']) or 0) >= rule['threshold']:
            return evolved_id, name, rule['flavour']
    return None


DECIDED_ELSEWHERE_COLUMNS = ('gender', 'biome', 'stat_rule', 'personality')


async def evolution_context(db, instance_id, guild_id=None):
    """
    Everything about a SPECIMEN that the rulebook gates on, as one dict.

    Passed as a single argument rather than four more keyword parameters, because
    check_evolution_trigger already takes seven and the two call sites would each have
    grown four more lines of plumbing for conditions that always travel together.

    Returns {} for a specimen with no id - a wild encounter, or a test - which is the
    right answer rather than a guess: every rule that gates on one of these refuses when
    it cannot be checked.
    """
    if not instance_id:
        return {}

    async with db.execute(
            "SELECT cp.gender, cp.level, cp.nature, cp.pokedex_id, "
            "cp.iv_attack, cp.iv_defense, cp.ev_attack, cp.ev_defense "
            "FROM caught_pokemon cp WHERE cp.instance_id = ?",
            (instance_id,)) as cursor:
        row = await cursor.fetchone()
    if not row:
        return {'instance_id': instance_id}

    gender, level, nature, pokedex_id, iv_atk, iv_def, ev_atk, ev_def = row

    # TYROGUE'S BASE STATS ARE EQUAL, so the comparison is decided entirely by IVs, EVs
    # and nature. Base stats alone would make every Tyrogue a Hitmontop.
    async with db.execute(
            "SELECT stat_name, base_value FROM base_pokemon_stats "
            "WHERE pokedex_id = ? AND stat_name IN ('attack', 'defense')",
            (pokedex_id,)) as cursor:
        bases = {name: value for name, value in await cursor.fetchall()}

    stats = {}
    if bases:
        # `nature_multiplier` rather than a comparison written out here. This copy was
        # correct - it only ever asks about Attack and Defense, which are spelt the same
        # way on both sides - but the copy in `calculate_stats` asked about the special
        # stats too and compared `sp_atk` against `special-attack` forever. Three places
        # applied this table by hand; one of them was wrong, and none of them could tell.
        for name, iv, ev in (('attack', iv_atk, ev_atk), ('defense', iv_def, ev_def)):
            raw = calculate_real_stat(name, bases.get(name, 0), iv or 0, ev or 0,
                                      level or 1)
            stats[name] = int(raw * nature_multiplier(nature, name))

    biome = None
    if guild_id:
        async with db.execute(
                "SELECT active_biome FROM servers WHERE guild_id = ?",
                (str(guild_id),)) as cursor:
            found = await cursor.fetchone()
        biome = (found[0] if found else None) or None

    return {
        'instance_id': instance_id,
        'gender': str(gender or '').strip().lower() or None,
        'biome': str(biome or '').strip().lower() or None,
        'stats': stats,
    }


# ==========================================
# 🔎 WHETHER A LEVEL-UP RULE HAS ANY REQUIREMENT THIS SCHEMA CAN SEE
# ==========================================
# 27 of this table's level-up rules carry no level, no happiness, no held item, no move
# and no region, because their real requirement is a mossy rock, a magnetic field or an
# affection level - none of which evolution_rules records. Treating "no requirement" as
# "requirement satisfied" would turn every Eevee into a Leafeon on its first level-up, so
# such a rule never fires.
#
# EXTRACTED because `!dex` now has to say the same thing in words. Written out a second
# time inside the dex panel, the two would drift the first time a column was added - the
# panel would keep calling a route unreachable that the engine had just learned to fire.
# One predicate, two readers.
#
# `time_of_day` is deliberately NOT here: a sky narrows a rule that is already checkable
# rather than making one checkable on its own, which is how the rulebook has always read
# it. No rule in the table carries a sky and nothing else.
CHECKABLE_REQUIREMENTS = ('min_level', 'min_happiness', 'held_item', 'known_move',
                          'known_move_type', 'region', 'gender', 'biome', 'stat_rule',
                          'personality')


def stated(value):
    """
    Whether a column actually carries a requirement.

    `None` and `''` are both "no requirement" in this table - PokeAPI's importer wrote
    empty strings into time_of_day and NULLs everywhere else - and ZERO is not: Wurmple's
    `personality` bucket is 0 or 1, and a falsiness test would have read half of Wurmple's
    rulebook as blank.
    """
    return value is not None and value != ''


def rule_is_checkable(rule):
    """Whether a level-up rule states a requirement this world can actually verify."""
    return any(stated(rule.get(column)) for column in CHECKABLE_REQUIREMENTS)


async def check_evolution_trigger(db, pokedex_id, level, happiness, time_of_day,
                                  held_item=None, moves=None, region=None,
                                  specimen=None):
    """
    The central rulebook for biological metamorphosis, and now actually the one in use.

    This function was written, given a `time_of_day` parameter, and then never called by
    anything - while cogs/experience.py carried its own rule inline. That copy read:

        if trigger == 'level-up' and req_level and new_level >= req_level

    ...which has two consequences. `req_level and` means a rule with a NULL min_level can
    never fire, so Sneasel could not become Weavile at any level; and the `happiness`
    trigger it checks beside it does not exist in this table at all - PokeAPI files those
    as `level-up` with a min_happiness - so no friendship evolution has ever fired either.

    THE RULE, stated once:

      - a requirement that is present must be MET. A time of day must match, a held item
        must actually be held, a min_level and a min_happiness must be reached.
      - a requirement that is absent is not a requirement.
      - but at least ONE requirement must have been checkable, or the rule does not fire.

    That last clause is the important one and it is not pedantry. 38 of this table's
    level-up rules carry no level, no happiness, no time of day and no held item, because
    their real requirement is a mossy rock, a magnetic field, a known move or an affection
    level - none of which this schema records. Treating "no requirement" as "requirement
    satisfied" would evolve every Eevee into a Leafeon on its first level-up. The old
    `req_level and` guard was accidentally protecting against exactly that; here it is
    deliberate.

    Returns (evolved_species_id, name) or None.
    """
    held = (held_item or '').strip().lower().replace(' ', '-') or None

    # `time_of_day` accepts a single sky or a set of them. The table holds FOUR values -
    # 'day', 'night', 'dusk' and 'full-moon' - and the last two sit INSIDE the first two
    # rather than replacing them, so a caller that passes only 'day' would make
    # Lycanroc-Dusk unreachable. See constants.current_skies.
    skies = ({time_of_day} if isinstance(time_of_day, str)
             else set(time_of_day or ()))

    known = {(m or '').strip().lower().replace(' ', '-') for m in (moves or []) if m}
    elements = await known_move_types(db, known) if known else set()

    # THE COLUMN MAY NOT BE THERE YET. `migrate_regional_evolutions.py` adds it, and this
    # has to keep answering on a database where it has not been run - every rule then
    # comes back region-less, which is exactly how the rulebook behaved before regional
    # forms existed. That is what lets the migration be applied to a running bot.
    has_region = await has_column(db, 'evolution_rules', 'region')
    region_column = 'er.region' if has_region else "'' AS region"

    # The four columns migrate_decided_evolutions.py adds, guarded the same way `region`
    # is so this keeps answering on a database that has not had it run. Selected as a
    # group because they arrived as a group; a partially-migrated table would be a
    # database somebody edited by hand.
    has_decided = await has_column(db, 'evolution_rules', 'gender')
    decided_columns = (", ".join(f"er.{name}" for name in DECIDED_ELSEWHERE_COLUMNS)
                       if has_decided
                       else ", ".join(f"NULL AS {name}"
                                      for name in DECIDED_ELSEWHERE_COLUMNS))
    async with db.execute(f"""
        SELECT er.evolved_species_id, s.name, er.min_level, er.min_happiness,
               er.held_item, er.time_of_day, er.known_move, er.known_move_type,
               {region_column}, {decided_columns}
        FROM evolution_rules er
        JOIN base_pokemon_species s ON er.evolved_species_id = s.pokedex_id
        WHERE er.base_species_id = ? AND er.trigger_name = 'level-up'
    """, (pokedex_id,)) as cursor:
        candidates = await cursor.fetchall()

    where = str(region or '').strip().lower()
    context = specimen or {}
    its_gender = str(context.get('gender') or '').strip().lower()
    its_biome = str(context.get('biome') or '').strip().lower()
    its_stats = context.get('stats') or {}
    its_personality = personality_of(context.get('instance_id'))

    # THE MOST SPECIFIC MATCHING RULE WINS, which is not the same as the first one.
    # Rockruff has three rules, all at level 25, differing only by sky: day, night and
    # dusk. At dusk BOTH the day rule and the dusk rule match, because dusk is a moment
    # inside the day - so ordering by level alone handed back Lycanroc-Midday and the Dusk
    # form was unreachable. A rule naming a narrower sky outranks one naming a broader
    # one, and a rule demanding an item outranks one that does not.
    def specificity(rule):
        (_id, _name, min_level, min_happiness, req_item, req_when, req_move, req_type,
         req_region, req_gender, req_biome, req_stat, req_personality) = rule
        # A BIOME IS A NARROWER REGION and ranks beside one; a demand about the specimen
        # ITSELF - its sex, its stats, the value it was born with - is narrower still,
        # because two specimens standing in the same place can answer differently.
        #
        # In practice none of the four species this was built for needs the tie broken:
        # a Burmy is male or female, a Tyrogue's Attack is above, below or level with its
        # Defence, and Wurmple's two buckets are two halves of one value. The ordering is
        # here for the species that mixes a gated rule with an ungated one later.
        own = ((1 if req_gender else 0) + (1 if req_stat else 0)
               + (1 if req_personality is not None else 0))
        # A named move is the narrowest demand of all, a move's ELEMENT next, then a held
        # item, then a sky. Eevee is why the first two are separate: it has both a Sylveon
        # rule wanting a Fairy move and Espeon/Umbreon rules wanting only friendship and a
        # sky, and at high friendship in the day both match.
        #
        # A REGION OUTRANKS ALL OF THEM. Cubone at level 28 has three rules - two for
        # Marowak and one for Marowak-Alola - identical in every other column, so the tie
        # fell to row order and the Alolan form was unreachable. A rule naming a region
        # has already been matched against the trainer's below, so if it is still a
        # candidate here it is the more specific answer by definition.
        return (own,
                1 if req_region else 0,
                1 if req_biome else 0,
                2 if req_move else (1 if req_type else 0),
                1 if req_item else 0,
                2 if req_when in SPECIAL_SKIES else (1 if req_when else 0),
                min_level or 0,
                min_happiness or 0)

    candidates.sort(key=specificity, reverse=True)

    for (evolved_id, name, min_level, min_happiness, req_item, req_when,
         req_move, req_move_type, req_region, req_gender, req_biome, req_stat,
         req_personality) in candidates:
        # SOMEWHERE ELSE ENTIRELY. A rule naming a region is simply not available to a
        # trainer who is not in it, which is what leaves the ordinary Marowak reachable
        # everywhere and the Alolan one reachable only from Alola.
        if req_region and str(req_region).strip().lower() != where:
            continue
        if req_when and req_when not in skies:
            continue
        if req_item and req_item != held:
            continue
        # Piloswine wants to know Ancient Power; Eevee wants to know ANY Fairy move.
        # Both were rules with nothing checkable on them until the columns existed, so
        # both were refused - which is why Mamoswine and Sylveon were unobtainable.
        if req_move and req_move not in known:
            continue
        if req_move_type and req_move_type not in elements:
            continue

        # THE FOUR THE GAMES DECIDE SOMEWHERE THIS TABLE COULD NOT SEE. Each refuses
        # when it cannot be checked rather than passing: a Burmy whose sex is unknown
        # must not become a Wormadam by default, and a Tyrogue whose stats could not be
        # computed must not become a Hitmontop because the comparison silently held.
        if req_gender and str(req_gender).strip().lower() != its_gender:
            continue
        if req_biome and str(req_biome).strip().lower() != its_biome:
            continue
        if req_stat and not stat_rule_holds(req_stat, its_stats):
            continue
        if req_personality is not None and req_personality != its_personality:
            continue

        if min_level is not None and level < min_level:
            continue
        if min_happiness is not None and happiness < min_happiness:
            continue

        # A REGION IS A REQUIREMENT THAT WAS CHECKED, and has to count as one. The clause
        # below refuses a rule whose real condition this schema cannot see; a
        # region-gated rule's condition is one it CAN see and has just met, so omitting
        # it here would make every regional form unreachable again by a second route -
        # `dartrix -> decidueye-hisui` carries no item, no sky and no move.
        # The four decided-elsewhere columns are requirements that WERE checked, for the
        # same reason a region is: `burmy -> mothim` carries no item, no sky, no move and
        # no region, and counting only the old four would refuse it as unverifiable after
        # it had just been verified.
        #
        # The predicate itself lives above, because `!dex` renders the same judgement as
        # a sentence and two copies of it would drift.
        if not rule_is_checkable({
                'min_level': min_level, 'min_happiness': min_happiness,
                'held_item': req_item, 'known_move': req_move,
                'known_move_type': req_move_type, 'region': req_region,
                'gender': req_gender, 'biome': req_biome, 'stat_rule': req_stat,
                'personality': req_personality}):
            # The real requirement is not in this schema. Never fires by itself.
            continue

        return evolved_id, name

    return None

async def stone_evolution(db, pokedex_id, item_name, region=None):
    """
    What this stone turns this species into, here. `(id, name, standards, hidden)` or None.

    **THE SECOND RULEBOOK, and until now the careless one.** `check_evolution_trigger`
    above sorts its candidates by specificity; the stone path in `cogs/evolution.py` ran
    a bare `fetchone()` with NO `ORDER BY` at all. Three stones have two rules apiece -
    Thunder Stone gives Raichu or Alolan Raichu, Leaf Stone Exeggutor or Alolan
    Exeggutor, Sun Stone Lilligant or Hisuian Lilligant - so which form a player got was
    decided by whatever order SQLite felt like returning rows in. The Alolan and Hisuian
    forms were unreachable.

    Extracted from the cog so there is one place to ask, and so a test can drive the
    real query rather than a copy of it that cannot go stale in the same direction.

    A rule for somewhere else is filtered out; a rule naming the trainer's own region
    beats a region-less one; ties fall to `id`, which is stable.
    """
    where = str(region or '').strip().lower()
    if await has_column(db, 'evolution_rules', 'region'):
        sql = """
            SELECT er.evolved_species_id, s.name, s.standard_abilities, s.hidden_ability
            FROM evolution_rules er
            JOIN base_pokemon_species s ON er.evolved_species_id = s.pokedex_id
            WHERE er.base_species_id = ? AND er.trigger_name = 'use-item'
              AND er.item_name = ?
              AND (er.region IS NULL OR er.region = '' OR er.region = ?)
            ORDER BY CASE WHEN er.region = ? THEN 0 ELSE 1 END, er.id
        """
        params = (pokedex_id, item_name, where, where)
    else:
        # Before the migration. Ordered anyway, because "whatever SQLite felt like" was
        # never an acceptable answer even when there was no region to prefer.
        sql = """
            SELECT er.evolved_species_id, s.name, s.standard_abilities, s.hidden_ability
            FROM evolution_rules er
            JOIN base_pokemon_species s ON er.evolved_species_id = s.pokedex_id
            WHERE er.base_species_id = ? AND er.trigger_name = 'use-item'
              AND er.item_name = ?
            ORDER BY er.id
        """
        params = (pokedex_id, item_name)

    async with db.execute(sql, params) as cursor:
        return await cursor.fetchone()


async def trade_evolution(db, pokedex_id, held_item=None):
    """
    What a traded specimen becomes, as (evolved_species_id, item to consume) or None.

    ALL the rules, and the one that MATCHES. The trade path read `fetchone()` and then
    tested whatever it got, which is first-row-wins - and Clamperl has two trade rules
    differing only by held item: a Deep Sea Tooth for Huntail and a Deep Sea Scale for
    Gorebyss. The Huntail rule has the lower id, so a Clamperl traded holding a Scale was
    compared against the Tooth, failed, and evolved into nothing. Gorebyss was
    unreachable by the only route that produces it.

    A rule DEMANDING the item outranks one that does not, so a Scyther holding a Metal
    Coat still becomes a Scizor and one holding nothing is not handed a different
    evolution by accident.

    The requirement lives in `held_item`; `item_name` is NULL for every trade rule in the
    table today, and is read anyway because a trade rule is allowed to name one.
    """
    worn = str(held_item or '').strip().lower().replace(' ', '-')
    # `await db.execute(...)` rather than `async with`, because the trade path hands this
    # a CURSOR rather than a connection. Both answer `await .execute(...)` with something
    # that has `.fetchall()`; only a connection answers the context-manager form.
    result = await db.execute(
        "SELECT evolved_species_id, COALESCE(held_item, item_name) "
        "FROM evolution_rules WHERE base_species_id = ? AND trigger_name = 'trade' "
        "ORDER BY id", (pokedex_id,))
    rules = await result.fetchall()

    unconditional = None
    for evolved_id, required in rules:
        if required:
            if worn and worn == str(required).strip().lower():
                return evolved_id, required
        elif unconditional is None:
            unconditional = evolved_id
    return (unconditional, None) if unconditional is not None else None


async def ritual_routes(db, pokedex_id):
    """
    Every ritual route out of one species, in a DEFINED order.

    The cog ran this query inline with no ORDER BY and took row zero, which is how Kubfu
    could only ever become Single Strike Urshifu: SQLite handed back the Tower of
    Darkness rule first and the Tower of Waters one was never seen. Ordering by id is
    not what fixes that - `choose_ritual` is - but an unordered query behind a choice is
    a coin flip waiting to be reintroduced.
    """
    placeholders = ','.join('?' * len(RITUAL_TRIGGERS))
    async with db.execute(f"""
        SELECT er.evolved_species_id, s.name, s.standard_abilities,
               s.hidden_ability, er.trigger_name
        FROM evolution_rules er
        JOIN base_pokemon_species s ON er.evolved_species_id = s.pokedex_id
        WHERE er.base_species_id = ?
          AND er.trigger_name IN ({placeholders})
        ORDER BY er.id
    """, (pokedex_id, *sorted(RITUAL_TRIGGERS))) as cursor:
        return await cursor.fetchall()


async def evolution_family(db, species_name):
    """
    Every pokedex_id in one species' evolutionary line, as a sorted list.

    WALKS BOTH DIRECTIONS, TRANSITIVELY. `.evo charizard` is far more useful meaning
    "show me this whole line" than meaning "show me what Charizard evolves into", which
    for a fully-evolved specimen is nothing at all - a filter that returns an empty list
    for the most-searched-for member of a family is a filter nobody will use twice. The
    broad reading also contains the narrow one, so nothing is lost by taking it.

    Returns `(ids, resolved_name)`, or `([], None)` when the species is not recognised.

    `evolution_rules` carries DUPLICATE rows for the branching families - Eevee has four
    identical Sylveon rows, one per qualifying rule - so the walk is over a set. Without
    that a `.evo eevee` would build an IN clause with fifteen entries for eight species.
    """
    name = str(species_name or '').strip().lower().replace(' ', '-')
    if not name:
        return [], None

    async with db.execute(
            "SELECT pokedex_id, name FROM base_pokemon_species WHERE LOWER(name) = ?",
            (name,)) as cursor:
        row = await cursor.fetchone()
    if not row:
        # A partial name, so `.evo char` finds Charmander. Ordered by pokedex_id so the
        # earliest member wins, which is the one whose family a player means.
        async with db.execute(
                "SELECT pokedex_id, name FROM base_pokemon_species "
                "WHERE LOWER(name) LIKE ? ORDER BY pokedex_id LIMIT 1",
                (f"{name}%",)) as cursor:
            row = await cursor.fetchone()
    if not row:
        return [], None

    start, resolved = row[0], row[1]
    seen, frontier = {start}, [start]
    while frontier:
        placeholders = ','.join('?' for _ in frontier)
        async with db.execute(
                f"SELECT evolved_species_id FROM evolution_rules "
                f"WHERE base_species_id IN ({placeholders}) "
                f"UNION "
                f"SELECT base_species_id FROM evolution_rules "
                f"WHERE evolved_species_id IN ({placeholders})",
                (*frontier, *frontier)) as cursor:
            neighbours = {r[0] for r in await cursor.fetchall() if r[0] is not None}
        frontier = sorted(neighbours - seen)
        seen.update(frontier)

    return sorted(seen), resolved


# ==========================================
# 🧱 SCHEMA HELPERS
# ==========================================
# THE ONE IMPLEMENTATION. `utils/prefs.py` and `utils/accounts.py` each grew their own
# byte-identical copy of `_has_column`, and a third was about to appear in
# `utils/regions.py` - which is how a rule written once per module starts drifting. Both
# keep their private names as aliases so no call site had to move.


async def has_column(db, table, column):
    """Whether `table` already has `column`. Reads the schema, changes nothing."""
    async with db.execute(f"PRAGMA table_info({table})") as cursor:
        return any(row[1] == column for row in await cursor.fetchall())


async def ensure_column(db, table, column, decl):
    """
    Add a column if it is missing. Does NOT commit. Returns whether it is there now.

    Called only from WRITE paths. A read must never alter the schema - that is how a
    module ends up writing to whatever database happened to be configured at import
    time, which this codebase has been bitten by once already. A lazily-added column
    therefore appears the first time somebody actually writes to it, and until then
    every read falls through to its default.

    The column NAME and DECLARATION are interpolated because SQLite cannot bind an
    identifier; both are literals from the calling module and neither is player input.
    """
    if await has_column(db, table, column):
        return True
    try:
        await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
        return True
    except Exception:
        return False
