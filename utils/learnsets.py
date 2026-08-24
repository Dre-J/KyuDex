"""
How a specimen may learn a move, and where the movepool that says so comes from.

**THE MOVEPOOL ALREADY SPANS EVERY GENERATION.** 147,291 rows across all 1,344 species,
with the legacy entries intact - Pursuit, Hidden Power, Return, Skull Bash, Charizard's
Gen 1 Dragon Rage, even `stadium-surfing-pikachu`. Every move it names exists in
`base_moves`. There was nothing to import; the cross-generation data has been there all
along.

**WHAT WAS MISSING WAS THE DOOR.** `species_movepool` records TEN learn methods and the
teaching gate handled FOUR of them. A move whose only route was `train` - Generation 8's
Technical Records, 3,837 species-and-move pairs across 342 species and 417 moves - fell
through every branch to "not physically capable of learning this", which is contradicted
by the row sitting in the database. Four more methods behind it did the same for another
74 pairs. So players could not teach moves from other generations, not because the data
was absent but because six of the ten routes led nowhere.

**AND THE QUESTION WAS ASKED TWICE.** `teaching_route` read every method; `!tutor` ran
its own `learn_method IN ('level-up', 'tutor')`, which is a different answer to the same
question in a second place. This module is the one door both go through.

---

**WHERE THE DATA COMES FROM, from here on.** Editing the live table directly leaves
movepool data with no source of truth - six months on, nobody knows whether Greninja has
Nasty Plot because the import said so, because somebody added it by hand, or because
they added it twice, and a rebuild loses the difference. So:

    species_movepool  =  species_movepool_base  +  movepool_overrides.json

`_base` is the pristine import, seeded once from what is already there. Overrides are a
file in the repo, diffable and revertible like any other code. `sync` rebuilds the live
table from the two, which makes it idempotent, re-runnable, and able to UNDO a removal
by deleting a line from a JSON file - none of which is true of an UPDATE typed into a
Discord command.

Every row carries its `source`, so "why can this thing learn that" is answerable by
looking rather than by remembering.
"""

import json
import os
from collections import namedtuple

from utils.db_manager import ensure_column, has_column

# ==========================================
# THE TEN METHODS
# ==========================================
# Every value that appears in `species_movepool.learn_method`, and what each one means
# to somebody trying to teach the move. Written out in full - including the ones nobody
# will ever hit - because the failure this module exists to fix was a method that no
# branch mentioned, and a table that lists them all cannot repeat it silently.
LEVEL_UP = 'level-up'
MACHINE = 'machine'
TUTOR = 'tutor'
EGG = 'egg'
RECORD = 'train'          # Generation 8 Technical Records

# The five that are not routes a trainer can walk at all - a move obtained by purifying
# a Shadow Pokemon in Pokemon XD, by feeding Zygarde its cube, by changing form, or from
# a Light Ball breeding line. They are real rows describing real history, and the honest
# answer names the route rather than denying the move exists.
EXOTIC_METHODS = {
    'xd-purification': "purifying a Shadow specimen in the Orre region",
    'zygarde-cube': "Zygarde's own cube",
    'form-change': "changing form",
    'stadium-surfing-pikachu': "the Stadium surfing event",
    'light-ball-egg': "a Light Ball breeding line",
}

# The order routes are read in, which is the order the games read them: something it has
# grown into is free, then a machine, then the paid doors.
ROUTE_ORDER = (LEVEL_UP, MACHINE, TUTOR, RECORD, EGG)

# Reasons a move is refused. Codes rather than sentences, so the two commands that ask
# this question cannot phrase the same refusal differently.
TOO_YOUNG = 'too-young'
NEEDS_MACHINE = 'needs-machine'
EGG_ONLY = 'egg-only'
EXOTIC_ONLY = 'exotic-only'
NOT_IN_POOL = 'not-in-pool'

Route = namedtuple('Route', 'method reason level detail')


def route_for(routes, level, *, owns_machine=False, allow_paid=True):
    """
    How this specimen may learn this move. PURE - no database, no text.

    `routes` is `{learn_method: minimum_level}` as the movepool records it. `level` is
    the specimen's. `owns_machine` says whether the trainer already holds the TM, which
    is the whole of the machine question because a TM is permanent.

    `allow_paid=False` asks the narrower question `!tutor` asks - "would the tutor teach
    this" - so the same table answers both without a second copy of it existing.

    Returns a `Route`. `method` is None when the move cannot be taught right now, and
    `reason` then says why in a code the caller turns into a sentence via `explain`.
    """
    routes = {str(k): int(v or 0) for k, v in (routes or {}).items()}
    level = int(level or 0)

    if not routes:
        return Route(None, NOT_IN_POOL, 0, None)

    # GROWN INTO IT: free, and checked first because it costs nothing.
    if LEVEL_UP in routes and level >= routes[LEVEL_UP]:
        return Route(LEVEL_UP, None, routes[LEVEL_UP], None)

    if MACHINE in routes:
        if owns_machine:
            return Route(MACHINE, None, 0, None)
        return Route(None, NEEDS_MACHINE, 0, None)

    # THE PAID DOOR. A tutor move and a Technical Record are the same transaction from
    # the player's side - pay tokens and a Memory Spore, teach a move the species can
    # genuinely learn - so a TR is routed through the tutor rather than given an item,
    # a shelf and a price list of its own. That converts 3,837 wrong refusals into a
    # route that already exists and is already balanced.
    for paid in (TUTOR, RECORD):
        if paid in routes:
            return Route(paid if allow_paid else None,
                         None if allow_paid else NEEDS_MACHINE, 0, None)

    # It DOES learn it by level-up, just not yet, and has no other route to skip ahead.
    if LEVEL_UP in routes:
        return Route(None, TOO_YOUNG, routes[LEVEL_UP], None)

    if EGG in routes:
        return Route(None, EGG_ONLY, 0, None)

    exotic = [m for m in routes if m in EXOTIC_METHODS]
    if exotic:
        return Route(None, EXOTIC_ONLY, 0, EXOTIC_METHODS[sorted(exotic)[0]])

    # A method nobody has taught this module about. Refusing honestly beats claiming the
    # species cannot learn the move, which is what the old gate did for six of the ten.
    return Route(None, EXOTIC_ONLY, 0, f"a route this laboratory cannot reproduce "
                                       f"({', '.join(sorted(routes))})")


def explain(route, species_name, move, *, tm_price=None):
    """The refusal, as a sentence. One place, so both commands say the same thing."""
    pretty = str(move).replace('-', ' ').title()
    name = str(species_name).replace('-', ' ').capitalize()

    if route.method:
        return None
    if route.reason == NOT_IN_POOL:
        return (f"❌ Biological mismatch: A **{name}** is not physically capable of "
                f"learning `{pretty}`.")
    if route.reason == NEEDS_MACHINE:
        price = f" It costs 🪙 **{tm_price:,}**, once, forever." if tm_price else ""
        return (f"💿 `{pretty}` is a **TM move** for {name}, and you do not own that "
                f"TM.{price} Buy it with `!buy {move}`, or look it up with "
                f"`!tmshop {move}`. `!tech` lists what you already hold.")
    if route.reason == TOO_YOUNG:
        return (f"📈 Your **{name}** needs to reach **Level {route.level}** before it "
                f"can master `{pretty}`.")
    if route.reason == EGG_ONLY:
        return (f"🥚 `{pretty}` is an egg move for {name}. It is inherited, not taught.")
    if route.reason == EXOTIC_ONLY:
        return (f"🔒 `{pretty}` reaches a {name} only through {route.detail}, which this "
                f"laboratory cannot reproduce.")
    return f"❌ A **{name}** cannot learn `{pretty}`."


def paid_route_hint(route, move):
    """The nudge toward the tutor, for a gate that found a paid route but is not it."""
    if route.method in (TUTOR, RECORD):
        kind = "tutor move" if route.method == TUTOR else "Technical Record move"
        return (f"🧠 `{str(move).replace('-', ' ').title()}` is a {kind}. Use "
                f"`!tutor <tag> {move}` — it costs 500 Eco Tokens and a Memory Spore.")
    return None


async def routes_for(db, pokedex_id, move):
    """`{learn_method: minimum_level}` for one species and move. Reads, never writes."""
    async with db.execute("""
        SELECT learn_method, MIN(level_learned)
        FROM species_movepool
        WHERE pokedex_id = ? AND move_name = ?
        GROUP BY learn_method
    """, (pokedex_id, str(move))) as cursor:
        return {row[0]: (row[1] or 0) for row in await cursor.fetchall()}


# ==========================================
# 📄 THE OVERRIDE FILE
# ==========================================
OVERRIDES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data', 'movepool_overrides.json')

BASE_TABLE = 'species_movepool_base'
LIVE_TABLE = 'species_movepool'
SOURCE_IMPORT = 'import'
SOURCE_PREFIX = 'override'

# What an `add` means when it is written as a bare move name. The tutor is the right
# default: it is the door that costs something and is not restricted by level, so a
# house-rule addition cannot accidentally be free or unreachable.
DEFAULT_ADD_METHOD = TUTOR
VALID_ADD_METHODS = (LEVEL_UP, MACHINE, TUTOR, RECORD, EGG)


def load_overrides(path=None):
    """
    `(overrides, problems)` from the JSON file. NEVER raises.

    A malformed override file must not be able to stop the bot or empty a movepool, so
    every failure here comes back as a problem to report and an empty override set - the
    live table then rebuilds to exactly the base import, which is a safe place to be.
    """
    path = path or OVERRIDES_PATH
    if not os.path.exists(path):
        return {}, []
    try:
        with open(path, encoding='utf-8') as fh:
            raw = json.load(fh)
    except Exception as e:
        return {}, [f"the override file could not be read: {e}"]
    if not isinstance(raw, dict):
        return {}, ["the override file must be an object keyed by species name"]

    overrides, problems = {}, []
    for species, entry in raw.items():
        if not isinstance(entry, dict):
            problems.append(f"`{species}`: entry must be an object")
            continue
        adds, bad = [], False
        for item in entry.get('add') or []:
            if isinstance(item, str):
                adds.append({'move': item, 'method': DEFAULT_ADD_METHOD, 'level': 0})
            elif isinstance(item, dict) and item.get('move'):
                method = str(item.get('method') or DEFAULT_ADD_METHOD)
                if method not in VALID_ADD_METHODS:
                    problems.append(f"`{species}`: `{item['move']}` has method "
                                    f"`{method}`, which is not one a trainer can walk")
                    bad = True
                    continue
                adds.append({'move': str(item['move']),
                             'method': method,
                             'level': int(item.get('level') or 0)})
            else:
                problems.append(f"`{species}`: an `add` entry is neither a move name "
                                f"nor an object with a `move`")
                bad = True
        removes = [str(m) for m in (entry.get('remove') or []) if m]
        if not adds and not removes and not bad:
            problems.append(f"`{species}`: neither adds nor removes anything")
        overrides[str(species).strip().lower()] = {
            'add': adds,
            'remove': removes,
            'source': str(entry.get('source') or 'manual'),
            'note': str(entry.get('note') or ''),
        }
    return overrides, problems


def save_overrides(overrides, path=None):
    """Write the file back, sorted and indented so a diff reads as a change of intent."""
    path = path or OVERRIDES_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    out = {}
    for species in sorted(overrides):
        entry = overrides[species]
        out[species] = {
            # Bare names where the method is the default, which keeps a hand-written
            # file readable rather than turning every line into an object.
            'add': [a['move'] if a['method'] == DEFAULT_ADD_METHOD and not a['level']
                    else a for a in entry.get('add') or []],
            'remove': list(entry.get('remove') or []),
            'source': entry.get('source') or 'manual',
            'note': entry.get('note') or '',
        }
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(out, fh, indent=2, sort_keys=False, ensure_ascii=False)
        fh.write('\n')
    return path


async def validate(db, overrides):
    """
    Every problem with these overrides, as sentences. Empty means safe to apply.

    Checked BEFORE anything is written, because the whole point of rebuilding from a
    base plus a file is that a typo is caught while it is still only a typo. A move name
    that does not exist would otherwise become a row nothing can ever teach and nothing
    would ever report.
    """
    problems = []

    async with db.execute("SELECT LOWER(name), pokedex_id FROM base_pokemon_species") as c:
        species_ids = {row[0]: row[1] for row in await c.fetchall()}
    async with db.execute("SELECT name FROM base_moves") as c:
        known_moves = {row[0] for row in await c.fetchall()}

    for species, entry in sorted(overrides.items()):
        pid = species_ids.get(species)
        if pid is None:
            problems.append(f"`{species}` is not a species in the database")
            continue
        seen = set()
        for add in entry['add']:
            move = add['move']
            if move not in known_moves:
                problems.append(f"`{species}`: `{move}` is not a move in the database")
            key = (move, add['method'])
            if key in seen:
                problems.append(f"`{species}`: `{move}` is added twice as "
                                f"`{add['method']}`")
            seen.add(key)
            if add['method'] == LEVEL_UP and add['level'] <= 0:
                problems.append(f"`{species}`: `{move}` is a level-up move with no "
                                f"level, so nothing could ever learn it")
        for move in entry['remove']:
            if move not in known_moves:
                problems.append(f"`{species}`: cannot remove `{move}`, which is not a "
                                f"move in the database")
            if any(a['move'] == move for a in entry['add']):
                problems.append(f"`{species}`: `{move}` is both added and removed")
    return problems


async def ensure_base_snapshot(db):
    """
    Make sure the pristine base table exists, seeding it from the live one if not.

    THE CURRENT TABLE IS THE BASE. It is the untouched import - nothing has ever written
    to it by hand - so the first sync can take it at its word. After that the base is
    never written again except by a deliberate re-import, and `sync` only ever rebuilds
    the LIVE table from it. That is what makes a removal reversible: delete the line
    from the JSON, sync again, and the base row comes back.
    """
    async with db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
            (BASE_TABLE,)) as cursor:
        exists = await cursor.fetchone() is not None

    if not exists:
        await db.execute(f"""
            CREATE TABLE {BASE_TABLE} (
                pokedex_id INTEGER,
                move_name TEXT,
                learn_method TEXT,
                level_learned INTEGER,
                PRIMARY KEY (pokedex_id, move_name, learn_method)
            )
        """)

    async with db.execute(f"SELECT COUNT(*) FROM {BASE_TABLE}") as cursor:
        seeded = (await cursor.fetchone())[0]
    if seeded:
        return seeded, False

    await db.execute(f"""
        INSERT OR IGNORE INTO {BASE_TABLE}
            (pokedex_id, move_name, learn_method, level_learned)
        SELECT pokedex_id, move_name, learn_method, level_learned FROM {LIVE_TABLE}
    """)
    async with db.execute(f"SELECT COUNT(*) FROM {BASE_TABLE}") as cursor:
        return (await cursor.fetchone())[0], True


async def sync(db, overrides, *, dry_run=True):
    """
    Rebuild the live movepool from the base snapshot plus these overrides.

    Idempotent by construction: it does not patch the live table, it replaces it. Running
    it twice leaves the same rows, and running it after deleting an override undoes that
    override rather than leaving its rows behind.

    `dry_run` counts everything and writes nothing, which is the default at every layer
    above this too - a command that rewrites 147,291 rows should have to be asked twice.

    Does NOT commit. The caller owns the transaction, so a validation failure halfway
    through leaves the movepool exactly as it was.
    """
    report = {'base': 0, 'seeded': False, 'added': 0, 'removed': 0, 'remove_rules': 0,
              'skipped': [], 'final': 0, 'dry_run': dry_run}

    report['base'], report['seeded'] = await ensure_base_snapshot(db)

    async with db.execute("SELECT LOWER(name), pokedex_id FROM base_pokemon_species") as c:
        species_ids = {row[0]: row[1] for row in await c.fetchall()}

    # Worked out against the BASE rather than the live table, so the numbers a dry run
    # reports are the numbers a real run would produce - not a diff against whatever the
    # last sync happened to leave behind.
    async with db.execute(
            f"SELECT pokedex_id, move_name, learn_method FROM {BASE_TABLE}") as cursor:
        base_rows = {(r[0], r[1], r[2]) for r in await cursor.fetchall()}

    additions, removals = [], []
    for species, entry in sorted(overrides.items()):
        pid = species_ids.get(species)
        if pid is None:
            report['skipped'].append(f"{species} (no such species)")
            continue
        tag = f"{SOURCE_PREFIX}:{entry['source']}"
        for add in entry['add']:
            key = (pid, add['move'], add['method'])
            if key in base_rows:
                report['skipped'].append(
                    f"{species} {add['move']} ({add['method']}) — already in the base")
                continue
            additions.append((pid, add['move'], add['method'], add['level'], tag))
        for move in entry['remove']:
            removals.append((pid, move))

    # COUNTED IN ROWS, NOT IN INSTRUCTIONS. One `remove` line takes out every route the
    # species had to that move - Hydro Cannon is a machine, a record AND a tutor move, so
    # removing it deletes three rows. A report saying "removed 1" while the table lost
    # three is the kind of small lie that makes an admin tool untrustworthy exactly when
    # somebody is checking whether it did what they meant.
    removed_keys = {(pid, move) for pid, move in removals}
    surviving = [r for r in base_rows if (r[0], r[1]) not in removed_keys]

    report['added'] = len(additions)
    report['removed'] = len(base_rows) - len(surviving)
    report['remove_rules'] = len(removals)

    if dry_run:
        # The count a real run would land on, without touching anything.
        report['final'] = len(surviving) + len(additions)
        return report

    await ensure_column(db, LIVE_TABLE, 'source', 'TEXT')

    await db.execute(f"DELETE FROM {LIVE_TABLE}")
    await db.execute(f"""
        INSERT INTO {LIVE_TABLE}
            (pokedex_id, move_name, learn_method, level_learned, source)
        SELECT pokedex_id, move_name, learn_method, level_learned, ?
        FROM {BASE_TABLE}
    """, (SOURCE_IMPORT,))

    for pid, move in removals:
        await db.execute(
            f"DELETE FROM {LIVE_TABLE} WHERE pokedex_id = ? AND move_name = ?",
            (pid, move))
    for pid, move, method, level, tag in additions:
        await db.execute(f"""
            INSERT OR REPLACE INTO {LIVE_TABLE}
                (pokedex_id, move_name, learn_method, level_learned, source)
            VALUES (?, ?, ?, ?, ?)
        """, (pid, move, method, level, tag))

    async with db.execute(f"SELECT COUNT(*) FROM {LIVE_TABLE}") as cursor:
        report['final'] = (await cursor.fetchone())[0]
    return report


def merge_bulk(overrides, payload, *, source, note=''):
    """
    Fold a community-compiled dump into the override set. Returns `(overrides, added)`.

    **THE PATH THAT MATTERS WHEN A GENERATION LANDS.** Nobody is going to type three
    hundred commands the week Gen 10 arrives; a spreadsheet appears within days and the
    useful thing is to paste it in. Accepts either shape:

        {"greninja": ["nasty-plot", "u-turn"]}
        {"greninja": {"add": [...], "remove": [...]}}

    Merged rather than replacing, so two dumps from two sources can both land, and the
    result is written back to the file for `sync` to read like any other override.
    """
    added = 0
    for species, entry in (payload or {}).items():
        key = str(species).strip().lower()
        current = overrides.setdefault(
            key, {'add': [], 'remove': [], 'source': source, 'note': note})
        incoming = entry if isinstance(entry, dict) else {'add': entry}
        for item in incoming.get('add') or []:
            move = item if isinstance(item, str) else str(item.get('move') or '')
            method = (DEFAULT_ADD_METHOD if isinstance(item, str)
                      else str(item.get('method') or DEFAULT_ADD_METHOD))
            level = 0 if isinstance(item, str) else int(item.get('level') or 0)
            if not move:
                continue
            if any(a['move'] == move and a['method'] == method
                   for a in current['add']):
                continue
            current['add'].append({'move': move, 'method': method, 'level': level})
            added += 1
        for move in incoming.get('remove') or []:
            if move not in current['remove']:
                current['remove'].append(str(move))
                added += 1
        current['source'] = source
        if note:
            current['note'] = note
    return overrides, added
