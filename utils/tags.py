"""
The labels a specimen carries.

**WHAT WAS WRONG.** `caught_pokemon.custom_tag` is a single TEXT column, so a specimen
had exactly one label. That is not enough for two separate reasons:

  * a shiny alpha legendary earns three descriptions and could hold one. `auto_tag` had
    a priority order - shiny beats mythical beats legendary beats pseudo beats alpha -
    that existed ONLY because the column could hold one value, and it meant the Alpha
    marking was invisible on every shiny;
  * a trainer filing their roster wants `competitive` AND `trade-fodder` AND `hisui`,
    and had to choose.

**AND THE AUTOMATIC ONES WERE ON DISPLAY.** Every `!pc` line printed the tag, so a
roster read `[shiny] [shiny] [legendary] [shiny]` - repeating what the ✨ already said,
in the space a trainer's own labels should have occupied. They are searchable, not
decorative; the list shows what the player wrote, and `.tags shiny` finds the rest.

**THE SHAPE.** One row per (specimen, tag) in `specimen_tags`. A junction table rather
than a comma-separated column because "find everything tagged X" is the whole point, and
`LIKE '%competitive%'` over a joined string matches `anti-competitive` too.

**EVERYTHING HERE DEGRADES.** `has_table` is asked first by every reader, and a database
that has not had the migration run behaves exactly as it did before: no tags, no crash.
The bot may run this code before the migration and must not fall over if it does.
"""
import re

TABLE = 'specimen_tags'

# Long enough for `trade-fodder` and `shiny-hunt-2026`, short enough that a tag is a
# label rather than a sentence somebody pasted.
MAX_TAG_LENGTH = 24

# Per specimen. A cap at all is what stops one animal carrying two hundred labels and
# making every listing that renders them unreadable.
MAX_TAGS_PER_SPECIMEN = 12

# How many tags one command may name at once - `!tags add 4 a b c`. Bounded for the same
# reason `parse_box_numbers` is: a slip should be refused, not applied.
MAX_TAGS_PER_REQUEST = 10

# ==========================================
# HOW MANY AT ONCE
# ==========================================
# A bulk tag edit acts on a set the trainer did not enumerate - `.shiny .iv >=90` could
# be four specimens or four hundred - so it is bounded, and above the confirm threshold
# it says what it is about to touch and waits. The release command reached the same two
# conclusions for the same reason; the numbers are larger here because a tag is
# reversible and a release is not.
BULK_TAG_CAP = 250
BULK_TAG_CONFIRM_AT = 25

NO_TAG_TABLE = ("\N{LABEL} Tags are not set up on this database yet. "
                "Run `python migrate_specimen_tags.py --apply`.")


def bulk_tag_result(adding, tag, label, touched, capped, considered):
    """The line a bulk tag edit prints. Shared so both directions read alike."""
    verb = "filed under" if adding else "no longer filed under"
    if not touched:
        return (f"\N{LABEL} Nothing changed — all {considered} already "
                f"{'carried' if adding else 'lacked'} `{tag}`.")
    line = (f"\N{LABEL} **{touched}** of {considered} specimens in *{label}* "
            f"{verb} `{tag}`.")
    if capped:
        # Said out loud rather than swallowed: a bulk command that quietly does less than
        # it was asked to is the one that teaches people not to trust it.
        line += (f"\n*{capped} were skipped — already at the "
                 f"{MAX_TAGS_PER_SPECIMEN}-tag limit.*")
    return line


# ==========================================
# WHAT A TAG MAY BE
# ==========================================
# Letters, digits and hyphens. Normalised on the way in so `Trade Fodder`, `trade fodder`
# and `TRADE-FODDER` are one tag rather than three that look identical in a listing.
_ALLOWED = re.compile(r'^[a-z0-9][a-z0-9-]*$')

# A PURELY NUMERIC TAG WOULD BE A BOX NUMBER. `!tags 4` has to mean "what is on box 4",
# and it cannot also mean "find everything tagged 4". Refused at the point of creation so
# the ambiguity never exists rather than being resolved by a rule nobody remembers.
#
# The sub-command words are reserved for the same reason: `!tags add` must not be
# ambiguous with a tag called `add`.
RESERVED = frozenset({
    'add', 'remove', 'rm', 'delete', 'del', 'clear', 'list', 'all', 'addall',
    'removeall', 'clearall', 'help', 'find', 'search', 'none', 'null',
})


def normalise_tag(raw):
    """
    A tag as it will be stored, or None if it cannot be one.

    Lowercased, trimmed, inner whitespace and underscores folded to hyphens, repeated
    hyphens collapsed. `  Trade   Fodder ` and `trade_fodder` both become `trade-fodder`.
    """
    text = str(raw or '').strip().lower()
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-{2,}', '-', text).strip('-')
    if not text or len(text) > MAX_TAG_LENGTH:
        return None
    if not _ALLOWED.match(text):
        return None
    if text.isdigit() or text in RESERVED:
        return None
    return text


def clean_tags(words):
    """
    A list of typed words as `(tags, complaint)` - de-duplicated, order preserved.

    Refuses the whole request rather than silently dropping the bad ones. A command that
    applies three of the four tags you asked for and says nothing is worse than one that
    refuses: you would not find out until you went looking for the fourth.
    """
    raw = [w for w in (words or []) if str(w).strip()]
    if not raw:
        return None, ("⚠️ Which tag? `!tags add 4 competitive` — letters, digits and "
                      "hyphens, up to " + str(MAX_TAG_LENGTH) + " characters.")

    if len(raw) > MAX_TAGS_PER_REQUEST:
        return None, (f"⚠️ That is {len(raw)} tags. {MAX_TAGS_PER_REQUEST} is the most "
                      f"one command takes.")

    tags, seen = [], set()
    for word in raw:
        tag = normalise_tag(word)
        if tag is None:
            if str(word).strip().isdigit():
                return None, (f"⚠️ `{word}` is a number, and a number is a box number "
                              f"here. Give the tag a letter in it.")
            if str(word).strip().lower() in RESERVED:
                return None, (f"⚠️ `{word}` is a word this command uses itself. "
                              f"Pick another.")
            return None, (f"⚠️ `{word}` cannot be a tag. Letters, digits and hyphens, "
                          f"up to {MAX_TAG_LENGTH} characters.")
        if tag not in seen:
            seen.add(tag)
            tags.append(tag)
    return tags, None


# ==========================================
# READING
# ==========================================
async def has_table(db):
    """Whether the migration has been run. Every reader asks this first."""
    async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
            (TABLE,)) as cursor:
        return await cursor.fetchone() is not None


async def tags_for(db, instance_id):
    """Every tag on one specimen, alphabetically. Empty when there are none."""
    if not instance_id or not await has_table(db):
        return []
    async with db.execute(
            f"SELECT tag FROM {TABLE} WHERE instance_id = ? ORDER BY tag",
            (instance_id,)) as cursor:
        return [row[0] for row in await cursor.fetchall()]


async def tags_for_many(db, instance_ids):
    """
    `{instance_id: [tags]}` for a whole page at once.

    ONE QUERY, not one per specimen. A listing renders up to a hundred rows and asking
    per row is what turns a page render into a hundred round trips - the same mistake
    that took a 1-second suite to 4 minutes when a set was rebuilt inside a comprehension.
    """
    ids = [i for i in (instance_ids or []) if i]
    if not ids or not await has_table(db):
        return {}
    out = {}
    # Chunked: SQLite's parameter limit is 999 by default and a roster can exceed it.
    for start in range(0, len(ids), 400):
        chunk = ids[start:start + 400]
        async with db.execute(
                f"SELECT instance_id, tag FROM {TABLE} "
                f"WHERE instance_id IN ({','.join('?' for _ in chunk)}) "
                f"ORDER BY tag", chunk) as cursor:
            for instance_id, tag in await cursor.fetchall():
                out.setdefault(instance_id, []).append(tag)
    return out


async def all_tags(db, user_id):
    """
    Every tag this trainer uses, as `[(tag, count)]`, commonest first.

    Scoped to the trainer: a tag is a private filing system, and a census across the
    whole server would tell them nothing about their own roster.
    """
    if not await has_table(db):
        return []
    async with db.execute(
            f"SELECT t.tag, COUNT(*) FROM {TABLE} t "
            f"JOIN caught_pokemon cp ON cp.instance_id = t.instance_id "
            f"WHERE cp.user_id = ? GROUP BY t.tag "
            f"ORDER BY COUNT(*) DESC, t.tag ASC", (user_id,)) as cursor:
        return [(row[0], row[1]) for row in await cursor.fetchall()]


# ==========================================
# WRITING
# ==========================================
async def add_tags(db, instance_id, tags):
    """
    Put tags on one specimen. Returns `(added, skipped, complaint)`. Does NOT commit.

    Already-present tags are SKIPPED rather than refused - `!tags add 4 shiny` on
    something already tagged shiny is a no-op a player should be told about, not an
    error. The cap is checked against what is already there, so it cannot be walked past
    one tag at a time.
    """
    if not await has_table(db):
        return [], [], ("⚠️ Tags are not set up on this database yet. "
                        "Run `migrate_specimen_tags.py --apply`.")

    current = set(await tags_for(db, instance_id))
    added, skipped = [], []
    for tag in tags:
        if tag in current:
            skipped.append(tag)
            continue
        if len(current) >= MAX_TAGS_PER_SPECIMEN:
            return None, None, (
                f"⚠️ That specimen already has {len(current)} tags, and "
                f"{MAX_TAGS_PER_SPECIMEN} is the limit. Remove one first.")
        current.add(tag)
        added.append(tag)

    for tag in added:
        await db.execute(
            f"INSERT OR IGNORE INTO {TABLE} (instance_id, tag) VALUES (?, ?)",
            (instance_id, tag))
    return added, skipped, None


async def remove_tags(db, instance_id, tags):
    """Take tags off one specimen. Returns `(removed, missing)`. Does NOT commit."""
    if not await has_table(db):
        return [], list(tags)
    current = set(await tags_for(db, instance_id))
    removed = [t for t in tags if t in current]
    missing = [t for t in tags if t not in current]
    if removed:
        await db.execute(
            f"DELETE FROM {TABLE} WHERE instance_id = ? "
            f"AND tag IN ({','.join('?' for _ in removed)})",
            (instance_id, *removed))
    return removed, missing


async def add_tag_to_many(db, instance_ids, tag):
    """
    One tag onto many specimens. Returns how many rows were actually new.

    `INSERT OR IGNORE` per specimen rather than one statement, because the per-specimen
    cap has to be honoured - a bulk add that ignores the limit is how one animal ends up
    with two hundred labels.
    """
    if not await has_table(db):
        return 0, 0
    added = capped = 0
    for instance_id in instance_ids:
        current = await tags_for(db, instance_id)
        if tag in current:
            continue
        if len(current) >= MAX_TAGS_PER_SPECIMEN:
            capped += 1
            continue
        await db.execute(
            f"INSERT OR IGNORE INTO {TABLE} (instance_id, tag) VALUES (?, ?)",
            (instance_id, tag))
        added += 1
    return added, capped


async def remove_tag_from_many(db, instance_ids, tag):
    """One tag off many specimens. Returns how many rows went. Does NOT commit."""
    if not await has_table(db) or not instance_ids:
        return 0
    ids = list(instance_ids)
    gone = 0
    for start in range(0, len(ids), 400):
        chunk = ids[start:start + 400]
        cursor = await db.execute(
            f"DELETE FROM {TABLE} WHERE tag = ? "
            f"AND instance_id IN ({','.join('?' for _ in chunk)})", (tag, *chunk))
        gone += cursor.rowcount if cursor.rowcount and cursor.rowcount > 0 else 0
    return gone


# ==========================================
# SEARCHING
# ==========================================
def tag_clause(tags, any_of=False):
    """
    A WHERE fragment selecting specimens by tag, as `(clause, params)`.

    AND by default - each extra tag NARROWS, which is how every other `!pc` filter
    behaves and therefore what stacking one more is expected to do. `any_of` widens it
    to OR for `.any`.

    Written as EXISTS per tag rather than as a join with a HAVING COUNT, because the
    EXISTS form composes with whatever else the filter language has already built and a
    GROUP BY would have to be threaded through the entire query.
    """
    wanted = [t for t in (tags or []) if t]
    if not wanted:
        return None, []

    one = (f"EXISTS (SELECT 1 FROM {TABLE} t WHERE t.instance_id = cp.instance_id "
           f"AND t.tag = ?)")
    if any_of:
        return "(" + " OR ".join(one for _ in wanted) + ")", list(wanted)
    return " AND ".join(one for _ in wanted), list(wanted)


def tag_like_clause(text):
    """
    The forgiving spelling: any tag CONTAINING this, as `(clause, params)`.

    `.tag competitive` has always been a substring match, and utils/filters.py's own
    docstring says a filter language that breaks what it replaces is a downgrade wearing
    a new name. So `.tag` keeps matching loosely over the set, and `.tags` is the exact
    one for when precision matters.
    """
    needle = str(text or '').strip().lower()
    if not needle:
        return None, []
    return (f"EXISTS (SELECT 1 FROM {TABLE} t WHERE t.instance_id = cp.instance_id "
            f"AND t.tag LIKE ?)", [f"%{needle}%"])
