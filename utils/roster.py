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
#
# `latest` used to be on this list and has moved to NEWEST_WORDS below, which is what it
# has always sounded like it meant. Nobody typing `!candy latest` is asking for the
# specimen they chose an hour ago - and a word that quietly means the opposite of what it
# says is worse than one that is not accepted at all.
PARTNER_WORDS = ('partner', 'lead', 'active', 'selected', 'select', 'current',
                 'mine', 'me')

# ...and the words for "the one I just caught". A trainer who has caught something and
# wants to act on it should not have to go and look its box number up first - the number
# is at the END of a roster that can be hundreds long.
NEWEST_WORDS = ('new', 'newest', 'latest', 'recent', 'last')

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


def parse_candy_request(first, second):
    """
    `!candy [target] [amount]` split into (target, amount, complaint).

    A LONE number is an AMOUNT: `!candy 20` means twenty candies to whoever is selected.
    It used to mean box 20, one candy - the reading the old signature forced, and the
    wrong one to optimise for, because feeding candy is nearly always done to the
    specimen already chosen and nearly always in bulk. Naming a target is still possible
    and is now explicit: `!candy 4 20` is twenty to box 4.

    Lives here rather than inline in the command so the rule can be checked without a
    database or a Discord context - the inline version could only be tested by reading
    the source for a string, which is a check that passes whether the branch runs or not.
    """
    if first is None:
        return None, 1, None
    if second is None:
        if str(first).isdigit():
            return None, int(str(first)), None
        return first, 1, None

    if not str(second).isdigit():
        return None, None, ("⚠️ Usage: `!candy [target] [amount]`\n"
                            "`!candy 20` feeds 20 candies to your selected partner; "
                            "`!candy 4 20` feeds 20 to box 4.")
    return first, int(str(second)), None


def looks_like_partner(target):
    """Whether this word means "the one I already selected"."""
    return target is not None and str(target).lower() in PARTNER_WORDS


def looks_like_newest(target):
    """Whether this word means "the one I most recently caught"."""
    return target is not None and str(target).lower() in NEWEST_WORDS


# ==========================================
# HOW MANY BOX NUMBERS AT ONCE
# ==========================================
# The ceiling exists so that a slip of the keyboard cannot empty a box. `!release 1-500`
# is a plausible typo for `!release 1-5`; it should be refused, not confirmed.
MAX_BULK_BOXES = 25


def parse_box_numbers(words):
    """
    A list of box numbers from `4`, `4 7 12`, `4-9`, or any mix of those.

    Returns `(numbers, complaint)`. `numbers` is sorted and de-duplicated, so `4 4 4`
    releases one specimen rather than trying to release the same one three times, and
    an overlapping `1-5 3` is the same request as `1-5`.

    Kept out of the cog because it is the only part of a bulk release that can be got
    wrong without a database - and it is a parser, which is the part that is worth
    testing against nonsense rather than against a happy path.
    """
    if not words:
        return [], ("⚠️ Which specimens? `!release 4`, `!release 4 7 12` or "
                    "`!release 4-9`.")

    found = set()
    for word in words:
        token = str(word).strip().strip(',')
        if not token:
            continue

        if '-' in token[1:]:
            # token[1:] so a leading minus is a bad number rather than a bad range.
            low, _, high = token.partition('-')
            if not (low.isdigit() and high.isdigit()):
                return [], f"⚠️ `{token}` is not a range of box numbers. Try `4-9`."
            low, high = int(low), int(high)
            if low < 1 or high < 1:
                return [], "⚠️ Box numbers start at 1."
            if high < low:
                return [], f"⚠️ `{token}` runs backwards. Try `{high}-{low}`."
            # Bounded BEFORE expansion: `1-100000` must not be turned into a hundred
            # thousand integers on the way to being refused for being too many.
            if high - low + 1 > MAX_BULK_BOXES:
                return [], (f"⚠️ `{token}` covers {high - low + 1} specimens. "
                            f"{MAX_BULK_BOXES} is the most one release can take.")
            found.update(range(low, high + 1))
        elif token.isdigit():
            if int(token) < 1:
                return [], "⚠️ Box numbers start at 1."
            found.add(int(token))
        else:
            return [], (f"⚠️ `{token}` is not a box number. Use the numbers from "
                        f"`!box`, e.g. `!release 4 7 12`.")

    if not found:
        return [], "⚠️ No box numbers given."
    if len(found) > MAX_BULK_BOXES:
        return [], (f"⚠️ That is {len(found)} specimens. {MAX_BULK_BOXES} is the most "
                    f"one release can take - it is a permanent action, and a limit is "
                    f"the only thing standing between a typo and an empty box.")
    return sorted(found), None


# ==========================================
# WHERE A SPECIMEN LANDS WHEN IT CHANGES HANDS
# ==========================================
async def bump_to_end_of_box(db, *instance_ids):
    """
    Move specimens to the end of their new owner's box. Does NOT commit.

    THE BUG THIS FIXES. Box numbers are `ROW_NUMBER() OVER(ORDER BY cp.rowid)` in
    twenty-eight separate queries, and a rowid is stamped when the specimen was first
    CAUGHT - by whoever caught it. A transfer only rewrites `user_id`, so a specimen
    caught in the sender's first week arrives in the recipient's box wearing the rowid
    of that week, and sorts ahead of things the recipient has owned for months. To a
    player receiving a gift, their starter stops being Box #1 and the gift takes its
    place: it reads exactly like the starter was overwritten, because every command
    that speaks in box numbers now names the gift where it used to name the starter.

    Nothing is overwritten - `instance_id` is the primary key and no two specimens can
    collide - but "nothing was lost" is not much comfort when `!release 1` is aimed at
    a different animal than the one the player has in mind.

    Renumbering at the point of transfer rather than changing the twenty-eight queries
    is deliberate: rowid is the box ordering, it is the ordering `!select new` reads,
    and the schema has no acquisition timestamp to sort by instead. Nothing in the
    database references caught_pokemon's rowid - no foreign key, no index, no trigger -
    so it is free to move, and moving it fixes every one of those queries at once.
    """
    for instance_id in instance_ids:
        if not instance_id:
            continue
        await db.execute(
            "UPDATE caught_pokemon "
            "SET rowid = (SELECT COALESCE(MAX(rowid), 0) + 1 FROM caught_pokemon) "
            "WHERE instance_id = ?", (instance_id,))


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

    # "the one I just caught". Ordered by rowid rather than by any timestamp, because
    # rowid is what the box NUMBERS are counted over - so `new` and the highest box
    # number are guaranteed to name the same specimen, which they would not be if this
    # sorted by a caught_at column that ties or is missing.
    #
    # Deployed and deposited specimens are excluded here exactly as they are from the box
    # numbering below. A specimen away on a field mission is not the one a trainer means,
    # and letting `new` reach one would be the only route in this function that can.
    if looks_like_newest(target):
        async with db.execute(f"""
            SELECT {columns} FROM caught_pokemon cp
            JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
            WHERE cp.user_id = ?
            AND cp.instance_id NOT IN (SELECT instance_id FROM active_deployments)
            AND cp.instance_id NOT IN (SELECT instance_id FROM gts_deposits)
            ORDER BY cp.rowid DESC LIMIT 1
        """, (user_id,)) as cursor:
            found = await cursor.fetchone()
        if not found:
            return None, ("📭 You have not caught anything yet, so there is no "
                          "latest specimen to point at.")
        return found, None

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
# WHICH ABILITY
# ==========================================
# `standard_abilities` is a comma-separated column and `hidden_ability` is a single name
# that is sometimes the literal string 'None'. Both are parsed in half a dozen places
# already; this is the parsing plus the two rulings, in one place a test can reach
# without a database or a Discord context.

def split_abilities(standards):
    """The standard abilities of a species, in slot order, as a list."""
    return [a.strip().lower() for a in str(standards or '').split(',') if a.strip()]


def real_hidden_ability(hidden):
    """A species' hidden ability, or None. The column stores 'None' for most species."""
    name = str(hidden or '').strip().lower()
    return None if name in ('', 'none', 'null') else name


def capsule_swap(current, standards, hidden):
    """
    What an Ability Capsule turns `current` into, as (new_ability, complaint).

    Exactly one of the two is ever set. The rulings, both taken from the games:

    - a Capsule does NOT touch a hidden ability. That is the Patch's job, and it is a
      one-way door: letting a Capsule walk a specimen back off a hidden ability would
      make the expensive item rentable rather than permanent.
    - a species with only one standard ability has nothing to swap to, which is a
      refusal rather than a silent no-op that still charges for the capsule.
    """
    slots = split_abilities(standards)
    current = str(current or '').strip().lower()

    if current and current == real_hidden_ability(hidden):
        return None, ("🩹 That specimen is on its **hidden** ability. A Capsule only "
                      "swaps between the two standard ones, and a hidden ability is a "
                      "one-way door.")
    if len(slots) < 2:
        return None, ("💊 That species has only one standard ability, so there is "
                      "nothing to swap it for.")

    # Cycle rather than flip, so the handful of species with three standard slots are
    # reachable too - a flip would strand the third one forever.
    try:
        position = slots.index(current)
    except ValueError:
        # Off-list, which a species rewrite can leave behind. Put it back on slot one.
        return slots[0], None
    return slots[(position + 1) % len(slots)], None


def patch_swap(current, hidden):
    """What an Ability Patch turns `current` into, as (new_ability, complaint)."""
    target = real_hidden_ability(hidden)
    current = str(current or '').strip().lower()

    if not target:
        return None, "🩹 That species has no hidden ability to unlock."
    if current == target:
        return None, "🩹 That specimen already has its hidden ability."
    return target, None


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
