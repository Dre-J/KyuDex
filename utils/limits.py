"""Per-day usage counters, for the things that need a ceiling rather than a cooldown.

A cooldown limits how FAST something happens; it does nothing about how much of it
happens in a day. `!expedition` wanted both - five minutes between trips so it is not a
button to mash, and a daily ceiling so a long evening cannot be turned into a hundred
rolls at the rare tiers.

**No migration.** The table is created on demand the first time anything reads it. Two
migration scripts in this repo are still waiting to be run; a third would have been a
third thing to remember.

**Nothing here runs at import or at cog load**, and the schema is only ever created on
a connection the CALLER opened. That is deliberate: `cogs/config.py` does its schema
work in `setup()`, which means loading it writes to whatever database is configured,
and `test_import_wiring` redirects `guild_config.DB_FILE` to a scratch copy to contain
exactly that. A second module doing the same thing would have escaped that redirection
and written to the live file - which is not a theory, it is what the first draft of
this module did.

**The day is UTC**, deliberately. A local-time reset means the boundary moves with the
host, and a server that changes timezone would hand everybody a fresh allowance or take
one away. UTC is the only clock every player shares.

Counters are rows keyed by day, not a counter plus a "last reset" timestamp that
something has to notice is stale. Yesterday's row simply stops being read. `sweep_old`
exists to keep the table small and is not needed for correctness.
"""

import datetime

# Deliberately no DB_FILE and no aiosqlite import: every function here takes an open
# connection. Nothing in this module can decide for itself which database to touch.

TABLE = 'daily_activity'

# The activities with a ceiling. A name here is just a string in a column, but keeping
# them together means a typo at the call site is visible next to the real ones.
EXPEDITION = 'expedition'

# Successful expedition CATCHES, counted separately from trips. A trip that finds nothing
# costs nothing, which is the whole reason this is a second counter rather than a reading
# of the first.
EXPEDITION_CATCH = 'expedition-catch'

# 40 trips, against a 5-minute cooldown that already spaces them over three hours and
# twenty minutes. The cap is the backstop for a whole day of play, not the throttle -
# most players will never reach it, and the ones who do have been at it a long time.
#
# NO LONGER A WALL. It used to refuse the 41st expedition outright, which is the bluntest
# possible answer and the one that punishes exactly the people playing the most. It is a
# SOFT cap now: the trips keep coming and the specimens keep being caught, and what decays
# is the incidental haul - the tokens, the berry, the field notes. Somebody who wants to
# keep surveying can keep surveying; they just stop being paid for volume.
EXPEDITION_DAILY_CAP = 40
EXPEDITION_SOFT_CAP = EXPEDITION_DAILY_CAP

# Every twenty catches past the cap, the incidental haul halves. A floor rather than zero,
# because a reward that reaches exactly nothing is a wall wearing a different hat - and
# somebody who has caught two hundred things in a day should still get SOMETHING for the
# two hundred and first.
EXPEDITION_DIMINISH_HALF_LIFE = 20
EXPEDITION_DIMINISH_FLOOR = 0.10


def expedition_yield(catches_today):
    """
    The multiplier on an expedition's incidental rewards, given today's catch count.

    1.0 up to and including the soft cap, then halving every
    EXPEDITION_DIMINISH_HALF_LIFE catches, never below EXPEDITION_DIMINISH_FLOOR.

    `catches_today` is the count BEFORE this catch, so the 41st catch is the first one
    that decays - which is what "diminishing returns after 40" says.
    """
    excess = (catches_today or 0) - EXPEDITION_SOFT_CAP
    if excess < 0:
        return 1.0
    factor = 0.5 ** (excess / float(EXPEDITION_DIMINISH_HALF_LIFE))
    return max(EXPEDITION_DIMINISH_FLOOR, factor)


def describe_yield(multiplier):
    """A short phrase for the footer, or None while nothing is being withheld."""
    if multiplier >= 0.999:
        return None
    return f"diminishing returns · {int(round(multiplier * 100))}% haul"


def today():
    """The current UTC date as `YYYY-MM-DD`."""
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')


def seconds_until_reset():
    """How long until the counters roll over, for telling somebody when to come back."""
    now = datetime.datetime.now(datetime.timezone.utc)
    tomorrow = (now + datetime.timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0)
    return max(0, int((tomorrow - now).total_seconds()))


def describe_reset():
    """`seconds_until_reset` as something readable, e.g. `3h 12m`."""
    remaining = seconds_until_reset()
    hours, minutes = remaining // 3600, (remaining % 3600) // 60
    if hours and minutes:
        return f"{hours}h {minutes}m"
    if hours:
        return f"{hours}h"
    return f"{max(1, minutes)}m"


async def ensure_schema(db):
    """Create the counter table. Idempotent, and safe to call on every read."""
    await db.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE} (
            user_id  TEXT NOT NULL,
            activity TEXT NOT NULL,
            day      TEXT NOT NULL,
            used     INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, activity, day)
        )
    """)


async def used_today(db, user_id, activity):
    """How many times `user_id` has done `activity` since the last UTC midnight."""
    await ensure_schema(db)
    async with db.execute(
            f"SELECT used FROM {TABLE} "
            f"WHERE user_id = ? AND activity = ? AND day = ?",
            (str(user_id), activity, today())) as cursor:
        row = await cursor.fetchone()
    return row[0] if row else 0


async def record_use(db, user_id, activity, amount=1):
    """
    Count one use and return the new total. Does NOT commit.

    The caller owns the transaction so a trip that fails to start does not spend an
    allowance - the same rule the directive helpers follow, and for the same reason.
    """
    await ensure_schema(db)
    await db.execute(
        f"INSERT INTO {TABLE} (user_id, activity, day, used) VALUES (?, ?, ?, ?) "
        f"ON CONFLICT(user_id, activity, day) DO UPDATE SET used = used + ?",
        (str(user_id), activity, today(), amount, amount))
    total = await used_today(db, user_id, activity)

    # Housekeeping folded into the first use of somebody's day, so the table maintains
    # itself without anything at boot having to remember it. Once per player per day is
    # cheap, and it happens inside a write the caller was already making.
    if total <= amount:
        await sweep_old(db)

    return total


async def check_cap(db, user_id, activity, cap):
    """
    `(allowed, used, remaining)` without spending anything.

    Separate from `record_use` because the expedition checks its allowance before it
    knows whether the trip can happen at all - there is a visa to verify and a spawn
    slot to be free - and a refused trip must not cost one.
    """
    used = await used_today(db, user_id, activity)
    return used < cap, used, max(0, cap - used)


async def sweep_old(db, keep_days=3):
    """Drop counters nobody will read again. Housekeeping, not correctness."""
    cutoff = (datetime.datetime.now(datetime.timezone.utc)
              - datetime.timedelta(days=keep_days)).strftime('%Y-%m-%d')
    cursor = await db.execute(f"DELETE FROM {TABLE} WHERE day < ?", (cutoff,))
    return cursor.rowcount
