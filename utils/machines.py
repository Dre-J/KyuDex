"""Owning a Technical Machine.

A TM is permanent. Buy it once and it works forever, on every eligible specimen, as
many times as you like - which is what the mainline games converged on, and for a
reason worth writing down: a CONSUMABLE TM is a tax on experimenting. People hoard
them, never try the odd idea, and end up playing whatever their level-up moves handed
them. That is precisely the behaviour a movepool of 340 machine moves exists to avoid.

So `user_tms` is read as a SET, not as a count. The `quantity` column is still there -
it is written by old rows and by `!buy` - but nothing reads it as a balance any more.
Ownership is "is there a row", and that is deliberately generous to the two trainers
who bought a TM under the old rules and spent it down to zero: they own it now.

Every reader goes through this module. Ownership was previously asked four different
ways in three files, and one of them (`teaching_route`) asked `quantity > 0` while
another (`!buy`) topped the quantity up - so the two could not both be right about
what a TM was.
"""

from utils.constants import TM_CATALOG, TM_SHOP


# ==========================================
# 🔐 OWNERSHIP
# ==========================================

async def owns_tm(db, user_id, move):
    """Whether this trainer holds this TM. A row is ownership; quantity is not read."""
    async with db.execute(
            "SELECT 1 FROM user_tms WHERE user_id = ? AND tm_name = ?",
            (str(user_id), move)) as cursor:
        return await cursor.fetchone() is not None


async def owned_tms(db, user_id):
    """Every TM this trainer holds, as a set - one query instead of one per move."""
    async with db.execute(
            "SELECT tm_name FROM user_tms WHERE user_id = ?", (str(user_id),)) as cursor:
        return {row[0] for row in await cursor.fetchall()}


async def grant_tm(db, user_id, move):
    """
    Hand over a TM. Returns False if they already had it.

    The caller decides what "already had it" means for its own flow - `!buy` refuses
    and keeps the tokens, the starter kit shrugs - but neither has to know that a
    second copy of a permanent item is meaningless.
    """
    if await owns_tm(db, user_id, move):
        return False

    # DO NOTHING, not an update. The guard above means this clause only fires on a race,
    # and the honest answer to "somebody else just granted this" is to leave their row
    # alone - an update that set or incremented a quantity would be writing a number
    # nothing reads, which is how `quantity` came to look like a balance in the first
    # place.
    await db.execute(
        "INSERT INTO user_tms (user_id, tm_name, quantity) VALUES (?, ?, 1) "
        "ON CONFLICT(user_id, tm_name) DO NOTHING",
        (str(user_id), move))
    return True


# ==========================================
# 🔍 FINDING ONE IN 340
# ==========================================
# A 340-item shelf is not browsable and never will be. Nobody scrolls thirty-four pages
# to find a move they already had in mind, so the search box is the shop and the pages
# are the fallback.

def normalise(typed):
    """`Stealth Rock`, `stealth-rock` and `STEALTHROCK` are the same request."""
    return ''.join(c for c in str(typed or '').lower() if c.isalnum())


def find_tm(typed):
    """
    The TM somebody means, or None.

    Exact match first, then a unique prefix, then a unique substring. Ambiguity
    resolves to None rather than to a guess - teaching the wrong move to a specimen
    that already knows four is not an undoable mistake.
    """
    wanted = normalise(typed)
    if not wanted:
        return None

    if wanted.startswith('tm'):
        # `!tmshop tm flamethrower` and `TM Flamethrower` both arrive here.
        stripped = wanted[2:]
        if stripped and stripped in {normalise(m) for m in TM_CATALOG}:
            wanted = stripped

    keys = {normalise(move): move for move in TM_CATALOG}
    if wanted in keys:
        return keys[wanted]

    prefixed = [move for key, move in keys.items() if key.startswith(wanted)]
    if len(prefixed) == 1:
        return prefixed[0]

    contained = [move for key, move in keys.items() if wanted in key]
    if len(contained) == 1:
        return contained[0]

    return None


def search_tms(typed):
    """
    Every TM matching a partial name, for telling somebody what they nearly typed.

    A plain substring search answers "flamet" and shrugs at "flamethowler", which is
    backwards: the second one is the case a suggestion is FOR. So a miss falls back to
    the longest leading fragment of what they typed that matches anything - one wrong
    letter in the middle of a name still finds its way home.
    """
    wanted = normalise(typed)
    if not wanted:
        return []

    hits = sorted(move for move in TM_CATALOG if wanted in normalise(move))
    if hits:
        return hits

    # Shortest useful fragment is three characters; below that every suggestion is
    # noise and "did you mean these forty moves" is worse than saying nothing.
    for cut in range(len(wanted) - 1, 2, -1):
        fragment = wanted[:cut]
        hits = sorted(move for move in TM_CATALOG
                      if normalise(move).startswith(fragment))
        if hits:
            return hits

    return []


def filter_tms(element=None, damage_class=None):
    """The shelf narrowed by type and/or category, alphabetically."""
    hits = []
    for move, data in TM_CATALOG.items():
        if element and (data.get('type') or '').lower() != element.lower():
            continue
        if damage_class and (data.get('class') or '').lower() != damage_class.lower():
            continue
        hits.append(move)
    return sorted(hits)


# ==========================================
# 📖 WHAT THIS SPECIES CAN ACTUALLY LEARN
# ==========================================

async def species_tms(db, pokedex_id):
    """
    The TMs this species can learn, alphabetically.

    This is the view that turns 340 options into forty. Nobody knows off the top of
    their head that Rotom-Wash learns Will-O-Wisp; the alternative to this command is
    a wiki tab open next to Discord.
    """
    async with db.execute("""
        SELECT DISTINCT move_name FROM species_movepool
        WHERE pokedex_id = ? AND learn_method = 'machine'
        ORDER BY move_name
    """, (pokedex_id,)) as cursor:
        learnable = [row[0] for row in await cursor.fetchall()]

    # A machine move with no shelf entry has no `base_moves` row, so the engine could
    # not run it either. Listing it would be offering something unbuyable, which is the
    # exact fault this whole change exists to remove.
    return [move for move in learnable if move in TM_CATALOG]


def price_of(move):
    """What a TM costs, or None if it is not stocked."""
    return TM_SHOP.get(move)
