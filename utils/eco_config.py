"""The ecosystem rework's numbers, its tables, and the one place a server can bend them.

This is Phase 1 of `ecosystem_doc.md`: the schema and the tuning knobs, with nothing
reading them yet. The engine that spends these numbers (absorption, the ledger, the
per-user cap) is the next PR; the tick and the commands come after it. Everything here
is either a constant, a pure function of the constants, or a table definition.

**THE SCHEMA LIVES HERE AND NOWHERE ELSE.** `migrate_eco_pollution.py` imports `SCHEMA`
and `INDEXES` rather than carrying its own copy, and so does `ensure_schema`. This repo
has been bitten by the other arrangement: a table defined in both a migration and a
module drifts the first time one of them gains a column, and the half that loses is
whichever one the deployment happened to run.

**NOTHING HERE TOUCHES A DATABASE AT IMPORT, OR AT COG LOAD.** Schema work only ever
runs on a connection the caller opened - the rule `utils/limits.py` already follows, and
for the same reason: `test_import_wiring` loads every cog against a scratch copy and
pins that doing so leaves `ecosystem.db` untouched. A module that opened its own
connection at import would escape that redirection and write to the live file.

FIVE PLACES THIS DELIBERATELY DEPARTS FROM §8 OF THE DOC, all for the same reason - the
doc was written against a blank page and this database is nine months old:

  * **`guild_id` and `user_id` are TEXT.** The doc says INTEGER. Every id in this
    database is TEXT and every call site passes `str(ctx.author.id)`; SQLite's column
    affinity would paper over the mismatch on a simple lookup and then not paper over it
    in a JOIN against `servers` or `guild_members`, which is the worst of both.
  * **`eco_deployment` keys a specimen by `instance_id TEXT`,** not `pokemon_id INTEGER`.
    A specimen's identity in this codebase is a uuid in `caught_pokemon.instance_id`;
    `pokedex_id` is the species, of which a trainer may own forty.
  * **`eco_activity.day` is a TEXT ISO day,** not a unix day number. It matches
    `daily_activity.day` and `command_usage.day`, the two day-bucketed tables already
    here, and ISO dates still compare correctly for the "last 7 days" range read that
    AU7 needs.
  * **`eco_guild` has no `biome` column.** `servers.active_biome` already holds it and
    `!sethabitat` already writes it. A second copy would create two answers to "which
    biome is this", and the loser of that race is always the one the spawner happens not
    to read.
  * **`eco_tuning` is new** - §12 asks for per-guild overrides and §8 never gave them a
    home.

**WHY KEY-VALUE, WHEN `guild_config` IS TYPED COLUMNS.** That module's shape is right for
what it holds: a dozen player-facing settings of five different kinds, each with a panel
entry and a control. These are two dozen homogeneous REAL numbers that an operator tunes
against live data, and §12 promises the list will grow. Typed columns would mean an
ALTER TABLE per knob and a `!config` panel flooded with arithmetic nobody running a
server wants to scroll past.
"""
import datetime

import aiosqlite

from utils.constants import DB_FILE


# ==========================================
# THE KNOBS
# ==========================================
class Knob:
    """One tunable number.

    `minimum` and `maximum` are what `coerce` enforces, so `!ecoadmin config` cannot be
    talked into a capacity of zero (every server instantly at score 0) or an absorption
    rate above 1.0 (pollution that heals faster than it can be generated).
    """

    def __init__(self, key, default, label, *, minimum=0.0, maximum=None, unit=''):
        self.key = key
        self.default = float(default)
        self.label = label
        self.minimum = minimum
        self.maximum = maximum
        self.unit = unit


# Ordered by §12's "primary tuning knobs, in order of impact" as far as that list goes,
# then by the section of the doc they come from. The order is the order `!ecoadmin config`
# will list them in.
KNOBS = {k.key: k for k in [
    # §2.2 - capacity and absorption
    Knob('capacity_per_active_user', 120, "Capacity per active user",
         minimum=1, maximum=10000, unit='pollution'),
    Knob('capacity_base', 200, "Base capacity",
         minimum=1, maximum=100000, unit='pollution'),
    Knob('absorption_rate', 0.02, "Passive absorption",
         minimum=0.0, maximum=1.0, unit='of capacity/hour'),

    # §3.2 - the sources. Industrial jobs and Blank Drives DO NOT EXIST YET; their knobs
    # are here because the doc argues for the numbers and a later PR should not have to
    # re-litigate them, not because anything reads them.
    Knob('industrial_job_pollution', 8.0, "Industrial Pokejob", maximum=1000),
    Knob('blank_drive_pollution', 12.0, "Blank Drive generation", maximum=1000),
    Knob('terraform_pollution', 25.0, "Terraforming operation", maximum=1000),
    Knob('bulk_sell_pollution', 3.0, "Bulk market sell", maximum=1000),
    Knob('bulk_sell_threshold', 20, "Items that make a sell 'bulk'",
         minimum=1, maximum=10000, unit='items'),
    Knob('job_pollution', 0.5, "Standard Pokejob", maximum=1000),
    Knob('catch_free_per_hour', 25, "Free catches per hour",
         minimum=0, maximum=10000, unit='catches'),
    Knob('catch_pollution', 0.5, "Catch past the free allowance", maximum=1000),

    # §3.3 / §3.4 - the valves
    Knob('user_hourly_cap', 40, "Per-user hourly ceiling",
         minimum=1, maximum=100000, unit='pollution/hour'),
    Knob('grace_hours', 48, "New-member grace",
         minimum=0, maximum=8760, unit='hours'),
    Knob('grace_multiplier', 0.5, "New-member pollution multiplier",
         minimum=0.0, maximum=1.0),

    # §4.3 - what a cleaner is paid
    Knob('cleanup_token_rate', 1.2, "Eco-Tokens per pollution cleaned", maximum=100),
    Knob('self_offset_bonus', 1.5, "Bonus while clearing your own debt",
         minimum=1.0, maximum=10),

    # §5.1 / §5.2 - thresholds and hysteresis. Phase 1 only ACTS on `strained_below`;
    # the rest are here so Phase 2 inherits one set of numbers rather than inventing a
    # second, and so `!eco status` can say how far a server is from the next state.
    Knob('strained_below', 60, "Strained below", minimum=1, maximum=99, unit='score'),
    Knob('critical_below', 30, "Critical below", minimum=1, maximum=98, unit='score'),
    Knob('pristine_at', 95, "Pristine at", minimum=2, maximum=100, unit='score'),
    Knob('pristine_exit_below', 88, "Pristine lost below",
         minimum=1, maximum=99, unit='score'),
    Knob('hysteresis_minutes', 10, "Transition hold",
         minimum=0, maximum=1440, unit='minutes'),
    Knob('pristine_hold_hours', 24, "Pristine qualifying period",
         minimum=0, maximum=720, unit='hours'),
    Knob('pristine_exit_minutes', 30, "Pristine breach grace",
         minimum=0, maximum=1440, unit='minutes'),
]}

DEFAULTS = {key: knob.default for key, knob in KNOBS.items()}

# The main tick's interval, from §9.1. NOT a knob: it is the loop's own period rather
# than a property of a guild, a per-guild override would not change when the loop runs,
# and absorption is prorated against it so two guilds on different periods would absorb
# at different rates from the same `absorption_rate`.
TICK_MINUTES = 5


# ==========================================
# THE STATES
# ==========================================
# All five names live here because a name belongs in one place, but Phase 1 only ever
# WRITES two of them. `state_for_score` is deliberately the narrow one: a tick that finds
# 'critical' in the column has no rules for it until Phase 2 ships them, and a state
# nothing can act on is worse than a state that merely understates the problem.
PRISTINE, STABLE, STRAINED, CRITICAL, WASTELAND = (
    'pristine', 'stable', 'strained', 'critical', 'wasteland')

STATES = (PRISTINE, STABLE, STRAINED, CRITICAL, WASTELAND)
PHASE_1_STATES = (STABLE, STRAINED)


# ==========================================
# THE DERIVATIONS
# ==========================================
def with_defaults(tuning=None):
    """A full knob mapping from a partial one. `None` means "all defaults"."""
    if not tuning:
        return dict(DEFAULTS)
    merged = dict(DEFAULTS)
    merged.update({k: v for k, v in tuning.items() if k in DEFAULTS and v is not None})
    return merged


def capacity_for(active_users, tuning=None):
    """
    C = base + per_user * AU7, with §2.2's floor of AU7 = 1.

    The floor is load-bearing rather than cosmetic: a guild whose activity window has
    gone quiet would otherwise have capacity `base` alone, and the same pollution would
    read as a far worse score on the day nobody happened to play.
    """
    t = with_defaults(tuning)
    au7 = max(1, int(active_users or 0))
    return t['capacity_base'] + t['capacity_per_active_user'] * au7


def score_for(pollution, capacity):
    """score = 100 * (1 - pollution/C), clamped to [0, 100]."""
    if not capacity or capacity <= 0:
        return 0.0
    return max(0.0, min(100.0, 100.0 * (1.0 - (max(0.0, pollution) / capacity))))


def pollution_for_score(score, capacity):
    """
    The inverse, for the one caller that has a score and needs the pollution behind it:
    the migration, backfilling nine months of `servers.ecosystem_score`.

    Exact against `score_for` for any score in [0, 100] - which the suite checks both
    ways round, because a backfill that lands a point or two off would quietly re-rank
    every server the day it runs.
    """
    clamped = max(0.0, min(100.0, float(score)))
    return max(0.0, capacity * (1.0 - (clamped / 100.0)))


def absorbed_per_hour(capacity, tuning=None):
    """§2.2's only background timer. Prorated per tick by the engine, not here."""
    return capacity * with_defaults(tuning)['absorption_rate']


def state_for_score(score, tuning=None):
    """
    The state Phase 1 can act on: `stable` or `strained`, and nothing else.

    A score of 12 is `strained` here, not `critical`. Phase 2 adds the lower bands along
    with the debuffs and the hysteresis that make them mean something, and reclassifies
    on its first tick. Writing 'critical' now would put a value in the column that
    nothing can read, which is how a fail-state becomes unreachable.
    """
    t = with_defaults(tuning)
    return STRAINED if score < t['strained_below'] else STABLE


def utc_day(when=None):
    """
    The ISO day an `eco_activity` row is filed under.

    UTC, for the reason `utils/limits.py` is UTC: a local-time boundary moves with the
    host, and AU7 is a seven-day window that would then be seven days and a bit, or six
    and a bit, depending on where the bot is running.
    """
    moment = when or datetime.datetime.now(datetime.timezone.utc)
    return moment.strftime('%Y-%m-%d')


def coerce(key, raw):
    """
    What somebody typed, as a number this knob accepts. Raises ValueError otherwise.

    Admin input, so it refuses rather than clamps: silently turning a mistyped 1200 into
    the maximum would leave an operator tuning against a number they never set.
    """
    knob = KNOBS[key]
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ValueError(f"{knob.label} wants a number, not {raw!r}")
    if value != value or value in (float('inf'), float('-inf')):
        raise ValueError(f"{knob.label} wants a real number")
    if knob.minimum is not None and value < knob.minimum:
        raise ValueError(f"{knob.label} cannot go below {knob.minimum:g}")
    if knob.maximum is not None and value > knob.maximum:
        raise ValueError(f"{knob.label} cannot go above {knob.maximum:g}")
    return value


# ==========================================
# THE TABLES
# ==========================================
GUILD_TABLE = 'eco_guild'
LEDGER_TABLE = 'eco_ledger'
USER_TABLE = 'eco_user'
DEPLOY_TABLE = 'eco_deployment'
ACTIVITY_TABLE = 'eco_activity'
TUNING_TABLE = 'eco_tuning'

TABLES = (GUILD_TABLE, LEDGER_TABLE, USER_TABLE, DEPLOY_TABLE, ACTIVITY_TABLE,
          TUNING_TABLE)

# The schema default for a brand-new guild's capacity: §2.2 at the AU7 floor. Written as
# the formula rather than as 320 so that re-tuning `capacity_base` cannot leave the
# column default disagreeing with the function every other reader uses.
_FRESH_CAPACITY = capacity_for(1)

SCHEMA = {
    # One row per guild. `capacity_updated_at = 0` means "recompute on the next tick",
    # which is what both a fresh row and a migrated one want.
    GUILD_TABLE: f"""
CREATE TABLE IF NOT EXISTS {GUILD_TABLE} (
    guild_id                 TEXT    PRIMARY KEY,
    pollution                REAL    NOT NULL DEFAULT 0,
    capacity                 REAL    NOT NULL DEFAULT {_FRESH_CAPACITY:g},
    capacity_updated_at      INTEGER NOT NULL DEFAULT 0,
    state                    TEXT    NOT NULL DEFAULT '{STABLE}',
    state_since              INTEGER NOT NULL DEFAULT 0,
    pristine_candidate_since INTEGER,
    pristine_breach_since    INTEGER,
    wasteland_since          INTEGER,
    last_tick                INTEGER NOT NULL DEFAULT 0,
    last_rift_closed_at      INTEGER,
    paused                   INTEGER NOT NULL DEFAULT 0
)""",

    # Append-only, like `trade_logs` and for the same reason: it exists to reconstruct
    # "why did the number move" after the fact, which it cannot do if the thing that
    # moved the number could also rewrite the record of it. Positive is pollution,
    # negative is cleanup, and §8's nightly rollup folds rows older than a week.
    LEDGER_TABLE: f"""
CREATE TABLE IF NOT EXISTS {LEDGER_TABLE} (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id   TEXT    NOT NULL,
    user_id    TEXT    NOT NULL,
    source     TEXT    NOT NULL,
    amount     REAL    NOT NULL,
    created_at INTEGER NOT NULL
)""",

    # `hourly_bucket` is a unix hour. Storing the bucket beside the counters is what
    # makes the per-user cap a read of one row rather than a COUNT over the ledger, and
    # a bucket that has rolled over simply stops matching - no reset task to forget.
    USER_TABLE: f"""
CREATE TABLE IF NOT EXISTS {USER_TABLE} (
    guild_id           TEXT    NOT NULL,
    user_id            TEXT    NOT NULL,
    outstanding        REAL    NOT NULL DEFAULT 0,
    lifetime_generated REAL    NOT NULL DEFAULT 0,
    lifetime_cleaned   REAL    NOT NULL DEFAULT 0,
    hourly_bucket      INTEGER NOT NULL DEFAULT 0,
    hourly_pollution   REAL    NOT NULL DEFAULT 0,
    hourly_catches     INTEGER NOT NULL DEFAULT 0,
    first_seen_at      INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
)""",

    # `payload` is the effectiveness computed when the deployment was made, not when it
    # resolves. A mon that levels up mid-task, or a knob an operator retunes while it is
    # out, must not change what the trainer was promised.
    DEPLOY_TABLE: f"""
CREATE TABLE IF NOT EXISTS {DEPLOY_TABLE} (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id    TEXT    NOT NULL,
    user_id     TEXT    NOT NULL,
    instance_id TEXT    NOT NULL,
    kind        TEXT    NOT NULL,
    ends_at     INTEGER NOT NULL,
    payload     REAL    NOT NULL,
    resolved    INTEGER NOT NULL DEFAULT 0
)""",

    # One row per guild per user per day: AU7 is a COUNT(DISTINCT user_id) over seven of
    # them. `daily_activity` could not answer this - it has no guild column, because it
    # is a per-user rate limiter rather than a record of who was about.
    ACTIVITY_TABLE: f"""
CREATE TABLE IF NOT EXISTS {ACTIVITY_TABLE} (
    guild_id TEXT NOT NULL,
    user_id  TEXT NOT NULL,
    day      TEXT NOT NULL,
    PRIMARY KEY (guild_id, user_id, day)
)""",

    # Absent row = the default in code, exactly as a NULL column means in guild_config.
    TUNING_TABLE: f"""
CREATE TABLE IF NOT EXISTS {TUNING_TABLE} (
    guild_id TEXT NOT NULL,
    key      TEXT NOT NULL,
    value    REAL NOT NULL,
    PRIMARY KEY (guild_id, key)
)""",
}

INDEXES = (
    # "What moved the number today", which is §11's requirement on `!eco status`.
    f"CREATE INDEX IF NOT EXISTS ix_eco_ledger_guild_time "
    f"ON {LEDGER_TABLE}(guild_id, created_at)",
    # One person's own history, for their private debt breakdown.
    f"CREATE INDEX IF NOT EXISTS ix_eco_ledger_user "
    f"ON {LEDGER_TABLE}(guild_id, user_id)",
    # The tick's own read: every deployment that has come due, across all guilds.
    f"CREATE INDEX IF NOT EXISTS ix_eco_deploy_pending "
    f"ON {DEPLOY_TABLE}(resolved, ends_at)",
    # The AU7 window.
    f"CREATE INDEX IF NOT EXISTS ix_eco_activity_day "
    f"ON {ACTIVITY_TABLE}(guild_id, day)",
)

# Parsed from the statements rather than listed beside them, so "is this index present"
# cannot be asked about a name no statement creates.
INDEX_NAMES = tuple(statement.split()[5] for statement in INDEXES)


async def ensure_schema(db):
    """
    Create any missing eco table and index on a connection the CALLER opened.

    Idempotent, and safe with the bot up: every statement is IF NOT EXISTS and nothing
    existing is altered. Returns the tables that were missing, so a caller that wants to
    log "this deployment had not been migrated" can.
    """
    async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'") as cursor:
        present = {row[0] for row in await cursor.fetchall()}

    created = [t for t in TABLES if t not in present]
    for statement in SCHEMA.values():
        await db.execute(statement)
    for statement in INDEXES:
        await db.execute(statement)
    await db.commit()
    return created


async def has_tables(db):
    """
    Whether the migration has been run, for readers that must degrade rather than crash.

    `utils/tags.py` earns its keep this way: every reader asks first, so a bot running
    new code against an un-migrated database behaves exactly as it did before instead of
    raising `no such table` at a player.
    """
    async with db.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name IN "
            f"({','.join('?' * len(TABLES))})", TABLES) as cursor:
        return (await cursor.fetchone())[0] == len(TABLES)


# ==========================================
# PER-GUILD OVERRIDES
# ==========================================
# guild_id -> {key: float}. Same contract as `guild_config._CACHE`: a guild absent has
# not been read yet, and a guild present with a key missing follows the default.
_CACHE = {}


def invalidate(guild_id=None):
    """Forget one guild's overrides, or all of them. Called after every write."""
    if guild_id is None:
        _CACHE.clear()
    else:
        _CACHE.pop(str(guild_id), None)


async def _read(guild_id):
    """Every override stored for one guild, straight from the database."""
    async with aiosqlite.connect(DB_FILE) as db:
        if not await has_tables(db):
            return {}
        async with db.execute(
                f"SELECT key, value FROM {TUNING_TABLE} WHERE guild_id = ?",
                (str(guild_id),)) as cursor:
            return {key: value for key, value in await cursor.fetchall()
                    if key in DEFAULTS}


async def get_all(guild_id):
    """
    Every knob for one guild, defaults filled in. Cached after the first read.

    A failed read returns the defaults UNCACHED - the same choice `guild_config.get_all`
    makes. Caching a failure would pin the defaults in memory until the next restart,
    which is how an operator's tuning silently stops applying.
    """
    guild_id = str(guild_id)
    if guild_id not in _CACHE:
        try:
            _CACHE[guild_id] = await _read(guild_id)
        except Exception as e:
            print(f"⚠️ Eco tuning read failed for {guild_id}: {e}")
            return dict(DEFAULTS)
    return with_defaults(_CACHE[guild_id])


async def get(guild_id, key):
    """One knob, with its default already applied."""
    return (await get_all(guild_id))[key]


async def set_value(guild_id, key, value):
    """
    Store one override. `value` goes through `coerce` first, so this cannot store junk.

    Written to the database and only then dropped from the cache, so a failed write
    leaves the cache agreeing with what is actually stored.
    """
    guild_id = str(guild_id)
    stored = coerce(key, value)
    async with aiosqlite.connect(DB_FILE) as db:
        await ensure_schema(db)
        await db.execute(
            f"INSERT INTO {TUNING_TABLE} (guild_id, key, value) VALUES (?, ?, ?) "
            f"ON CONFLICT(guild_id, key) DO UPDATE SET value = excluded.value",
            (guild_id, key, stored))
        await db.commit()
    invalidate(guild_id)
    return stored


async def clear(guild_id, key=None):
    """Drop one override, or every override for a guild, back to the defaults."""
    guild_id = str(guild_id)
    async with aiosqlite.connect(DB_FILE) as db:
        if not await has_tables(db):
            return 0
        if key is None:
            cursor = await db.execute(
                f"DELETE FROM {TUNING_TABLE} WHERE guild_id = ?", (guild_id,))
        else:
            cursor = await db.execute(
                f"DELETE FROM {TUNING_TABLE} WHERE guild_id = ? AND key = ?",
                (guild_id, key))
        await db.commit()
        removed = cursor.rowcount
    invalidate(guild_id)
    return max(0, removed)


def declared_columns(table):
    """
    The column names `SCHEMA` declares for one table, parsed from the statement itself.

    For the suite, and for the migration's report. Reading the declaration rather than
    keeping a second list of names beside it means the two cannot disagree.
    """
    body = SCHEMA[table].strip()
    inner = body[body.index('(') + 1:body.rindex(')')]
    columns = []
    depth = 0
    for line in inner.splitlines():
        stripped = line.strip().rstrip(',')
        if not stripped:
            continue
        depth += stripped.count('(') - stripped.count(')')
        first = stripped.split()[0].upper()
        if first in ('PRIMARY', 'FOREIGN', 'UNIQUE', 'CHECK', 'CONSTRAINT'):
            continue
        if depth == 0:
            columns.append(stripped.split()[0])
    return columns
