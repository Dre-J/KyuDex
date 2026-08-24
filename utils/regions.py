"""
The nine regions a trainer registers from, and which one they belong to afterwards.

**THE CHOICE WAS ALREADY BEING MADE AND THEN THROWN AWAY.** `!start` opens a region
menu, the trainer picks one, `StarterSelect` is handed the name - and nothing ever wrote
it down. Every trainer in the database chose a region and the game forgot which. This
module is where that answer now lives.

**STORED, WITH A DERIVED FALLBACK.** The column is authoritative once written, but the
twelve trainers who registered before it existed have no row to read. Their region is
recovered from their starter instead: the nine starter trios are disjoint, so a
Cyndaquil can only have come from Johto. That is exact rather than a guess, and it means
nobody has to be migrated.

It is a fallback and not the whole answer because a starter can be gifted away. Deriving
region from "whatever specimen is flagged as a starter right now" would let somebody's
homeland change when they traded a Pokemon, which is why the stored value wins whenever
there is one.

**REGION IS NOT A PREFERENCE.** It is game state - it gates regional evolutions, and a
Cubone raised in Alola becomes a different Marowak from one raised in Kanto. So it lives
here rather than in `utils/prefs.py`, even though the lazy-column mechanics are the same.
"""

from utils.db_manager import ensure_column, evolution_family, has_column

# In generation order, which is also the order the registration menu offers them.
#
# ONE TABLE. The nine regions and their starters were written out TWICE in cogs/ecology.py
# - once as `RegionSelect`'s option list and once as `StarterSelect`'s dict - and the two
# had already disagreed: the Hoenn water starter was offered under Totodile's name while
# handing over Mudkip. Two lists that must agree and nothing checking that they do.
REGIONS = {
    'kanto':  {'label': 'Kanto',  'gen': 1, 'emoji': '🔴',
               'starters': ((1, 'Bulbasaur', '🌿 Grass/Poison'),
                            (4, 'Charmander', '🔥 Fire'),
                            (7, 'Squirtle', '💧 Water'))},
    'johto':  {'label': 'Johto',  'gen': 2, 'emoji': '🌕',
               'starters': ((152, 'Chikorita', '🌿 Grass'),
                            (155, 'Cyndaquil', '🔥 Fire'),
                            (158, 'Totodile', '💧 Water'))},
    'hoenn':  {'label': 'Hoenn',  'gen': 3, 'emoji': '🌴',
               'starters': ((252, 'Treecko', '🌿 Grass'),
                            (255, 'Torchic', '🔥 Fire'),
                            (258, 'Mudkip', '💧 Water'))},
    'sinnoh': {'label': 'Sinnoh', 'gen': 4, 'emoji': '🏔️',
               'starters': ((387, 'Turtwig', '🌿 Grass'),
                            (390, 'Chimchar', '🔥 Fire'),
                            (393, 'Piplup', '💧 Water'))},
    'unova':  {'label': 'Unova',  'gen': 5, 'emoji': '🗽',
               'starters': ((495, 'Snivy', '🌿 Grass'),
                            (498, 'Tepig', '🔥 Fire'),
                            (501, 'Oshawott', '💧 Water'))},
    'kalos':  {'label': 'Kalos',  'gen': 6, 'emoji': '🗼',
               'starters': ((650, 'Chespin', '🌿 Grass'),
                            (653, 'Fennekin', '🔥 Fire'),
                            (656, 'Froakie', '💧 Water'))},
    'alola':  {'label': 'Alola',  'gen': 7, 'emoji': '🌺',
               'starters': ((722, 'Rowlet', '🌿 Grass'),
                            (725, 'Litten', '🔥 Fire'),
                            (728, 'Popplio', '💧 Water'))},
    'galar':  {'label': 'Galar',  'gen': 8, 'emoji': '⚔️',
               'starters': ((810, 'Grookey', '🌿 Grass'),
                            (813, 'Scorbunny', '🔥 Fire'),
                            (816, 'Sobble', '💧 Water'))},
    'paldea': {'label': 'Paldea', 'gen': 9, 'emoji': '🧭',
               'starters': ((906, 'Sprigatito', '🌿 Grass'),
                            (909, 'Fuecoco', '🔥 Fire'),
                            (912, 'Quaxly', '💧 Water'))},
}

REGION_ORDER = tuple(REGIONS)
DEFAULT_REGION = 'kanto'

# pokedex_id -> region key, built from the table above so it cannot fall behind it.
STARTER_REGION = {pid: key
                  for key, entry in REGIONS.items()
                  for pid, _name, _desc in entry['starters']}

assert len(STARTER_REGION) == sum(len(e['starters']) for e in REGIONS.values()), \
    "two regions claim the same starter, so a region could not be recovered from one"


def region_label(key, emoji=True):
    """`'alola'` -> `'🌺 Alola'`. The one place a region key becomes something to read."""
    key = str(key or '').strip().lower()
    entry = REGIONS.get(key)
    if not entry:
        return key.title() if key else "Unknown"
    return f"{entry['emoji']} {entry['label']}" if emoji else entry['label']


def describe_region(key):
    """`'🌺 Alola · Generation 7'`, for a panel with room for the longer form."""
    entry = REGIONS.get(str(key or '').strip().lower())
    if not entry:
        return region_label(key)
    return f"{region_label(key)} · Generation {entry['gen']}"


def starters_for(key):
    """The three starters offered in a region, as `(pokedex_id, name, blurb)`."""
    entry = REGIONS.get(str(key or '').strip().lower())
    return entry['starters'] if entry else ()


def region_of_starter(pokedex_id):
    """Which region a starter species comes from, or None if it is not one.

    EXACT MATCH ONLY, so this answers for Cyndaquil and not for Typhlosion. Almost every
    real starter has evolved at least once - see `region_of_specimen`, which is the one
    to call when a database is available.
    """
    try:
        return STARTER_REGION.get(int(pokedex_id))
    except (TypeError, ValueError):
        return None


async def region_of_specimen(db, pokedex_id):
    """
    Which region a specimen's LINE starts in, or None.

    **A STARTER IS USUALLY NOT A STARTER ANY MORE.** Driving this against the live
    database found that most trainers' starters had already evolved - Raboot, Greninja,
    Ivysaur - and none of those appears in a table of base forms. Matching on the
    specimen alone recovered Kanto for a Galar trainer and two Kalos ones, which is
    worse than admitting ignorance because it looks like an answer.

    So the whole evolution line is walked, and the region is the one whose starter is
    somewhere in it. `evolution_family` already walks in both directions transitively,
    which is what makes a fully-evolved specimen resolvable at all.
    """
    direct = region_of_starter(pokedex_id)
    if direct:
        return direct
    try:
        async with db.execute(
                "SELECT name FROM base_pokemon_species WHERE pokedex_id = ?",
                (int(pokedex_id),)) as cursor:
            row = await cursor.fetchone()
        if not row:
            return None
        family, _resolved = await evolution_family(db, row[0])
    except Exception:
        return None
    # Sorted, so a line that somehow touched two trios would answer deterministically
    # rather than depending on the order the walk happened to return.
    for pid in sorted(family):
        if pid in STARTER_REGION:
            return STARTER_REGION[pid]
    return None


def resolve_region(stored, starter_id=None):
    """
    The region a trainer belongs to. Stored value first, then their starter.

    THE ONE DOOR. The profile, the regional-evolution rules and any future switch all
    come through here, so there is no second opinion about where somebody is from - and
    a stored value naming a region that no longer exists falls back rather than escaping
    into a lookup that will not find it.
    """
    key = str(stored or '').strip().lower()
    if key in REGIONS:
        return key
    derived = region_of_starter(starter_id)
    return derived or DEFAULT_REGION


def resolve_region_word(text):
    """`(region_key, complaint)` from whatever they typed. Exactly one is ever set."""
    word = str(text or '').strip().lower()
    if word in REGIONS:
        return word, None
    # Matched on the label too, so "Kanto" typed with its capital still lands, and on a
    # bare generation number, because "gen 3" is how half of players name these.
    for key, entry in REGIONS.items():
        if word in (entry['label'].lower(), f"gen {entry['gen']}", f"gen{entry['gen']}",
                    str(entry['gen'])):
            return key, None
    import difflib
    close = difflib.get_close_matches(word, REGION_ORDER, n=1, cutoff=0.6)
    hint = f" Did you mean `{close[0]}`?" if close else ""
    return None, (f"🗾 `{text}` is not a region.{hint} The nine are "
                  f"{', '.join(REGIONS[k]['label'] for k in REGION_ORDER)}.")


async def get_region(db, user_id):
    """The RAW stored region, or '' if none. Never raises, never writes.

    Deliberately not resolved here: resolution needs the starter, this only needs the
    column, and a getter that quietly returned a derived value would make it impossible
    to tell a trainer who chose Johto from one who merely started with a Cyndaquil.
    """
    try:
        if not await has_column(db, 'users', 'region'):
            return ''
        async with db.execute("SELECT region FROM users WHERE user_id = ?",
                              (str(user_id),)) as cursor:
            row = await cursor.fetchone()
    except Exception:
        return ''
    stored = (row[0] if row else None) or ''
    return stored if stored in REGIONS else ''


async def set_region(db, user_id, key):
    """Store it. Returns False if the database cannot hold it. Does NOT commit."""
    key = str(key or '').strip().lower()
    if key not in REGIONS:
        return False
    if not await ensure_column(db, 'users', 'region', 'TEXT'):
        return False
    await db.execute("UPDATE users SET region = ? WHERE user_id = ?",
                     (key, str(user_id)))
    return True


async def starter_species(db, user_id):
    """The pokedex_id of this trainer's starter, or None.

    OLDEST FIRST, because a trainer can hold more than one specimen flagged as a starter
    once resets are involved, and the first one is the one that named their region.
    """
    try:
        if not await has_column(db, 'caught_pokemon', 'is_starter'):
            return None
        async with db.execute(
                "SELECT pokedex_id FROM caught_pokemon "
                "WHERE user_id = ? AND is_starter = 1 ORDER BY rowid ASC LIMIT 1",
                (str(user_id),)) as cursor:
            row = await cursor.fetchone()
    except Exception:
        return None
    return row[0] if row else None


async def trainer_region(db, user_id):
    """`(region_key, stored_raw)` - the resolved region, and whether it was chosen.

    The raw value comes back too so a caller can tell "chose Johto" from "was worked out
    from a Greninja", which reads differently in a panel and matters to any future
    command that offers to change it.
    """
    stored = await get_region(db, user_id)
    if stored:
        return stored, stored
    starter = await starter_species(db, user_id)
    if starter is None:
        return DEFAULT_REGION, ''
    return (await region_of_specimen(db, starter)) or DEFAULT_REGION, ''
