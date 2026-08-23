import sqlite3
# Assuming you define DB_FILE = "ecosystem.db" in constants.py
from utils.constants import DB_FILE, SPECIAL_SKIES 

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

async def check_evolution_trigger(db, pokedex_id, level, happiness, time_of_day,
                                  held_item=None):
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

    async with db.execute("""
        SELECT er.evolved_species_id, s.name, er.min_level, er.min_happiness,
               er.held_item, er.time_of_day
        FROM evolution_rules er
        JOIN base_pokemon_species s ON er.evolved_species_id = s.pokedex_id
        WHERE er.base_species_id = ? AND er.trigger_name = 'level-up'
    """, (pokedex_id,)) as cursor:
        candidates = await cursor.fetchall()

    # THE MOST SPECIFIC MATCHING RULE WINS, which is not the same as the first one.
    # Rockruff has three rules, all at level 25, differing only by sky: day, night and
    # dusk. At dusk BOTH the day rule and the dusk rule match, because dusk is a moment
    # inside the day - so ordering by level alone handed back Lycanroc-Midday and the Dusk
    # form was unreachable. A rule naming a narrower sky outranks one naming a broader
    # one, and a rule demanding an item outranks one that does not.
    def specificity(rule):
        _id, _name, min_level, min_happiness, req_item, req_when = rule
        return (1 if req_item else 0,
                2 if req_when in SPECIAL_SKIES else (1 if req_when else 0),
                min_level or 0,
                min_happiness or 0)

    candidates.sort(key=specificity, reverse=True)

    for evolved_id, name, min_level, min_happiness, req_item, req_when in candidates:
        if req_when and req_when not in skies:
            continue
        if req_item and req_item != held:
            continue

        checkable = bool(req_item)

        if min_level is not None:
            if level < min_level:
                continue
            checkable = True

        if min_happiness is not None:
            if happiness < min_happiness:
                continue
            checkable = True

        if not checkable:
            # The real requirement is not in this schema. Never fires by itself.
            continue

        return evolved_id, name

    return None