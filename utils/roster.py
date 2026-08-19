"""Finding one of a trainer's specimens, and which party is being talked about.

Every command that acts on a specimen has to answer the same question - *which one?* -
and until recently each answered it separately. `!learn` took a box number or the word
`partner`, `!tutor` took a tag, `!equip` took a box number only, and `!party add` took a
box number and crashed outright on anything else. Four spellings of one idea, each with
its own gaps.

This is that question, once. `!learn` grew the good version of it; the rest now share it.

It lives in `utils/` rather than in a cog because two different cogs need it, and a cog
importing another cog makes the load order load-bearing - `main.py` walks the directory
and a failure there costs every command in the importing file.
"""
import aiosqlite

from utils.constants import DB_FILE

# The words a trainer uses for "the one I have already chosen". `!partner` is aliased to
# `!select`, so both nouns are in circulation and both have to work.
PARTNER_WORDS = ('partner', 'lead', 'active', 'latest', 'selected', 'select', 'current',
                 'mine', 'me')

# The default party, and the name a trainer who has never made a second one is on.
DEFAULT_PARTY = 'main'

# A party name is a label, not free text: it is typed at a prefix parser, printed in a
# select option and used as a database key.
MAX_PARTY_NAME = 24
MAX_PARTIES = 10
PARTY_SLOTS = 6


def clean_party_name(typed):
    """A party name as it will be stored, or None if it cannot be one."""
    name = " ".join(str(typed or "").split()).strip().lower()
    if not name or len(name) > MAX_PARTY_NAME:
        return None
    # Nothing that would be read as another argument, and nothing that collides with a
    # sub-command a player might reasonably type.
    if not all(ch.isalnum() or ch in "-_ " for ch in name):
        return None
    return name


def parse_learn_request(request):
    """
    `!learn [target] [slot] <move>` split into its three parts, or None.

    The target is optional, which is the whole point: a trainer with a selected partner
    should be able to say `!learn 1 tackle` rather than naming the specimen they already
    named. That makes the first word ambiguous - `!learn 3 1 tackle` and `!learn 1 tackle`
    both open with a number - so the SECOND word decides.

    A slot is a SINGLE digit, deliberately. `10-000-000-volt-thunderbolt` is the one move
    in the database whose name starts with a number, and a player typing it with spaces
    would otherwise have its `10` read as a slot. Requiring one digit costs nothing - a
    specimen has four slots - and removes the only collision there is.

    The SLOT is optional too. `!learn earthquake` means "teach my partner this, wherever
    there is room", which is what `!tm` always did.

    An out-of-range slot is passed through rather than rejected here, so the command can
    give its own message about there being four slots.
    """
    tokens = (request or "").split()
    if not tokens:
        return None
    if len(tokens) >= 3 and len(tokens[1]) == 1 and tokens[1].isdigit():
        return tokens[0], int(tokens[1]), " ".join(tokens[2:])
    if len(tokens) >= 2 and tokens[0].isdigit():
        return None, int(tokens[0]), " ".join(tokens[1:])
    return None, None, " ".join(tokens)


def looks_like_partner(target):
    """Whether this word means "the one I already selected"."""
    return target is not None and str(target).lower() in PARTNER_WORDS


async def locate_specimen(db, user_id, target, columns):
    """
    One of a trainer's specimens, from a box number, a tag prefix, or nothing at all.

    `target` of None means "the one they have selected", which is what `!partner` sets.
    Returns (row, error) - the error is already written for a player to read.

    Box numbering matches every other command in the codebase: deployed specimens and
    anything sitting on the GTS are excluded, because those are the rows the numbers a
    player reads in `!party view` are counted over.
    """
    if looks_like_partner(target):
        target = None

    if target is None:
        async with db.execute("SELECT active_partner FROM users WHERE user_id = ?",
                              (user_id,)) as cursor:
            row = await cursor.fetchone()
        if not row or not row[0]:
            return None, ("🎯 You have not selected a partner yet. Choose one with "
                          "`!partner <box number>`, or name the specimen directly.")
        async with db.execute(
                f"SELECT {columns} FROM caught_pokemon cp "
                f"JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id "
                f"WHERE cp.instance_id = ? AND cp.user_id = ?",
                (row[0], user_id)) as cursor:
            found = await cursor.fetchone()
        if not found:
            return None, ("⚠️ Your selected partner is no longer in your roster. "
                          "Pick another with `!partner <box number>`.")
        return found, None

    target = str(target)
    if target.isdigit() and len(target) <= 6:
        async with db.execute(f"""
            WITH Roster AS (
                SELECT {columns}, ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                FROM caught_pokemon cp
                JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                WHERE cp.user_id = ?
                AND cp.instance_id NOT IN (SELECT instance_id FROM active_deployments)
                AND cp.instance_id NOT IN (SELECT instance_id FROM gts_deposits)
            )
            SELECT * FROM Roster WHERE box_number = ?
        """, (user_id, int(target))) as cursor:
            found = await cursor.fetchone()
        if not found:
            return None, f"❌ You have nothing in box **{int(target)}**."
        return found[:-1], None      # drop the box_number the CTE carried along

    # A tag, or the first few characters of one. Ambiguity is refused rather than
    # guessed at - six characters of a UUID collide sooner than people expect, and
    # acting on the wrong specimen is not a mistake anybody would trace.
    async with db.execute(
            f"SELECT {columns} FROM caught_pokemon cp "
            f"JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id "
            f"WHERE cp.user_id = ? AND cp.instance_id LIKE ? LIMIT 5",
            (user_id, f"{target}%")) as cursor:
        rows = await cursor.fetchall()

    if not rows:
        return None, (f"❌ Nothing in your roster matches `{target}`. Use a box number, "
                      f"a tag, or `partner` for your selected specimen.")
    if len(rows) > 1:
        return None, (f"🔍 `{target}` matches {len(rows)} of your specimens. "
                      f"Give me more of the tag.")
    return rows[0], None


# ==========================================
# WHICH PARTY
# ==========================================
async def active_party(db, user_id):
    """
    The party a trainer is currently building, defaulting to `main`.

    Read through a helper rather than inline because a database that has not had the
    migration run has no column to read, and every caller wanting a party must still
    get one. Falling back to `main` is what the whole feature degrades to: exactly the
    single party that existed before.
    """
    try:
        async with db.execute("SELECT active_party FROM users WHERE user_id = ?",
                              (user_id,)) as cursor:
            row = await cursor.fetchone()
    except Exception:
        return DEFAULT_PARTY
    return (row[0] if row and row[0] else DEFAULT_PARTY)


async def set_active_party(db, user_id, name):
    """Switch which party the party commands act on. Returns whether it could be saved."""
    try:
        await db.execute("UPDATE users SET active_party = ? WHERE user_id = ?",
                         (name, user_id))
        return True
    except Exception as e:
        print(f"⚠️ Could not switch party for {user_id}: {e}")
        return False


async def party_names(db, user_id):
    """
    Every party this trainer has, in the order they were made, `main` always first.

    An EMPTY party still counts - it is a thing they created and named - so the names
    come from the parties table rather than from what happens to be sitting in slots.
    """
    names = []
    try:
        async with db.execute(
                "SELECT party_name FROM user_parties WHERE user_id = ? "
                "ORDER BY rowid ASC", (user_id,)) as cursor:
            names = [row[0] for row in await cursor.fetchall()]
    except Exception:
        # No parties table: an un-migrated database has exactly one party.
        pass

    if DEFAULT_PARTY not in names:
        names.insert(0, DEFAULT_PARTY)
    return names


async def party_counts(db, user_id):
    """How many specimens sit in each of a trainer's parties, as {name: count}."""
    try:
        async with db.execute(
                "SELECT party_name, COUNT(*) FROM user_party WHERE user_id = ? "
                "GROUP BY party_name", (user_id,)) as cursor:
            return {row[0] or DEFAULT_PARTY: row[1] for row in await cursor.fetchall()}
    except Exception:
        async with db.execute(
                "SELECT COUNT(*) FROM user_party WHERE user_id = ?",
                (user_id,)) as cursor:
            return {DEFAULT_PARTY: (await cursor.fetchone())[0]}


async def has_party_column(db):
    """Whether this database has had the multi-party migration run."""
    async with db.execute("PRAGMA table_info(user_party)") as cursor:
        return any(row[1] == 'party_name' for row in await cursor.fetchall())
