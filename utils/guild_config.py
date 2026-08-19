"""Per-server settings: the table, the defaults, the cache and the validation.

Every server the bot joins currently gets the same world. One habitat channel, a spawn
every ten messages, a five-minute despawn, and a level-up announcement whether the room
wanted one or not. A twenty-person server and a two-thousand-person server need very
different numbers, and the second most common reason a bot gets removed is that it was
noisy in a way nobody could turn down.

Four decisions worth knowing about before adding a setting:

**Typed columns, not key-value.** `guild_config` has a real column per setting and
`NULL` means "use the default". A key-value store would have made every read a join and
every default a row somebody has to remember to write. `ensure_schema` adds any missing
column at boot, so a new setting needs no migration - only an entry in SETTINGS.

**Defaults live in code, never in the schema.** Changing what a fresh server does is
then a one-line edit rather than an ALTER TABLE plus a backfill, and a server that has
never touched a setting follows the default forever rather than being frozen at whatever
it was on the day they joined.

**Cached, invalidated on write.** Config is read on nearly every message - the spawn
counter alone - and written a handful of times in a server's life. The cache is per
process and the bot is one process; a write goes to the database first and only then
disturbs the cache, so a failed write cannot leave the cache lying.

**Two settings live in `servers`, not here.** The habitat channel already had a home and
`!sethabitat` already writes it. Copying it into a second table would have created two
answers to "where do things spawn", and the loser of that race is always the one the
spawner happens not to read.

Nothing here is a prerequisite. A server that never runs `!config` gets exactly the
behaviour it got before this existed.
"""
import aiosqlite

from utils.constants import DB_FILE

TABLE = 'guild_config'

# `servers` predates this module and already holds the habitat channel.
SERVERS_TABLE = 'servers'

# The kinds a setting can be. Each decides how it is stored, how it is parsed from what
# somebody typed, and which control the panel offers.
CHANNEL, CHANNEL_LIST, ROLE, BOOL, NUMBER, TEXT = (
    'channel', 'channel_list', 'role', 'bool', 'number', 'text')


class Setting:
    """One knob. `default` is what a server that has never touched it behaves as."""

    def __init__(self, key, kind, label, description, default=None,
                 column=None, table=TABLE, minimum=None, maximum=None, group='General',
                 emoji='⚙️'):
        self.key = key
        self.kind = kind
        self.label = label
        self.description = description
        self.default = default
        self.column = column or key
        self.table = table
        self.minimum = minimum
        self.maximum = maximum
        self.group = group
        self.emoji = emoji

    @property
    def sql_type(self):
        return 'INTEGER' if self.kind in (BOOL, NUMBER) else 'TEXT'


# ==========================================
# THE SETTINGS
# ==========================================
# Ordered, because this is also the order the panel lists them in.
SETTINGS = {s.key: s for s in [
    Setting('spawn_channel', CHANNEL, "Habitat channel",
            "Where wild specimens appear. `!sethabitat` sets this too.",
            column='spawn_channel_id', table=SERVERS_TABLE,
            group='Channels', emoji='🌿'),

    Setting('announce_channel', CHANNEL, "Announcement channel",
            "Rifts, disasters and ecosystem events. Defaults to the habitat channel.",
            group='Channels', emoji='📣'),

    Setting('command_channels', CHANNEL_LIST, "Command channels",
            "Where players may use bot commands. Empty means anywhere.",
            group='Channels', emoji='🔒'),

    Setting('ping_role', ROLE, "Alert role",
            "Mentioned when something rare appears. Unset means nobody is pinged.",
            group='Notifications', emoji='🔔'),

    Setting('ping_rare', BOOL, "Ping for rare spawns", default=True,
            description="Mention the alert role for shinies, legendaries and pseudo-legendaries.",
            group='Notifications', emoji='✨'),

    Setting('ping_events', BOOL, "Ping for rifts and disasters", default=True,
            description="Mention the alert role when the ecosystem changes state.",
            group='Notifications', emoji='🌌'),

    Setting('spawn_rate', NUMBER, "Messages per spawn", default=10,
            description="How much conversation it takes to draw a specimen out.",
            minimum=5, maximum=250, group='Spawning', emoji='📈'),

    Setting('despawn_seconds', NUMBER, "Despawn timeout", default=300,
            description="Seconds an uncaught specimen waits before wandering off.",
            minimum=60, maximum=3600, group='Spawning', emoji='⏳'),

    Setting('auto_delete_spawns', BOOL, "Delete expired spawns", default=False,
            description="Remove the message entirely instead of marking it lost.",
            group='Spawning', emoji='🗑️'),

    Setting('compact_spawns', BOOL, "Compact spawn cards", default=False,
            description="Show the specimen as a small thumbnail rather than a full image.",
            group='Spawning', emoji='🖼️'),

    Setting('timezone', TEXT, "Timezone", default='UTC',
            description="An IANA name such as `Europe/London`. Used for scheduled events.",
            group='General', emoji='🕒'),
]}

GROUPS = []
for _s in SETTINGS.values():
    if _s.group not in GROUPS:
        GROUPS.append(_s.group)


# ==========================================
# SCHEMA
# ==========================================
async def ensure_schema(db):
    """
    Create the table and add any column a setting needs. Idempotent, and safe at boot.

    Adding a setting to SETTINGS is the whole job - this notices the missing column the
    next time the bot starts. A migration script exists as well, for anybody who would
    rather see it happen than trust it to.
    """
    await db.execute(
        f"CREATE TABLE IF NOT EXISTS {TABLE} (guild_id TEXT PRIMARY KEY)")

    async with db.execute(f"PRAGMA table_info({TABLE})") as cursor:
        present = {row[1] for row in await cursor.fetchall()}

    added = []
    for setting in SETTINGS.values():
        if setting.table != TABLE or setting.column in present:
            continue
        await db.execute(
            f"ALTER TABLE {TABLE} ADD COLUMN {setting.column} {setting.sql_type}")
        added.append(setting.column)

    await db.commit()
    return added


# ==========================================
# THE CACHE
# ==========================================
# guild_id -> {key: stored value}. A guild absent from here has not been read yet;
# a guild present with a key missing has no stored value and follows the default.
_CACHE = {}


def invalidate(guild_id=None):
    """Forget one server's settings, or all of them. Called after every write."""
    if guild_id is None:
        _CACHE.clear()
    else:
        _CACHE.pop(str(guild_id), None)


async def _read(guild_id):
    """Everything stored for one server, straight from the database."""
    guild_id = str(guild_id)
    stored = {}

    async with aiosqlite.connect(DB_FILE) as db:
        await ensure_schema(db)

        columns = [s.column for s in SETTINGS.values() if s.table == TABLE]
        async with db.execute(
                f"SELECT {', '.join(columns)} FROM {TABLE} WHERE guild_id = ?",
                (guild_id,)) as cursor:
            row = await cursor.fetchone()
        if row:
            stored.update({c: v for c, v in zip(columns, row) if v is not None})

        # The handful that live in `servers`. Read separately because that table is
        # older, is written by other commands, and must stay the single answer.
        elsewhere = [s for s in SETTINGS.values() if s.table != TABLE]
        if elsewhere:
            cols = ', '.join(s.column for s in elsewhere)
            async with db.execute(
                    f"SELECT {cols} FROM {SERVERS_TABLE} WHERE guild_id = ?",
                    (guild_id,)) as cursor:
                row = await cursor.fetchone()
            if row:
                stored.update({s.column: v for s, v in zip(elsewhere, row)
                               if v is not None})

    return {key: stored[s.column] for key, s in SETTINGS.items() if s.column in stored}


async def get_all(guild_id):
    """Every setting for one server, defaults filled in. Cached after the first read."""
    guild_id = str(guild_id)
    if guild_id not in _CACHE:
        try:
            _CACHE[guild_id] = await _read(guild_id)
        except Exception as e:
            # A configuration read must never be the reason a spawn or a command fails.
            # Deliberately NOT cached, so the next call tries again rather than pinning
            # the defaults in memory until the next restart.
            print(f"⚠️ Guild config read failed for {guild_id}: {e}")
            return {key: s.default for key, s in SETTINGS.items()}

    stored = _CACHE[guild_id]
    return {key: decode(key, stored.get(key)) if key in stored else s.default
            for key, s in SETTINGS.items()}


async def get(guild_id, key):
    """One setting, with its default already applied."""
    return (await get_all(guild_id)).get(key, SETTINGS[key].default)


async def set_value(guild_id, key, value):
    """
    Store one setting. `value` is already-coerced - see `coerce`. None clears it.

    Written to the database first and only then dropped from the cache, so a failed
    write leaves the cache agreeing with what is actually stored.
    """
    guild_id = str(guild_id)
    setting = SETTINGS[key]
    stored = encode(key, value)

    async with aiosqlite.connect(DB_FILE) as db:
        await ensure_schema(db)
        if setting.table == TABLE:
            await db.execute(
                f"INSERT INTO {TABLE} (guild_id, {setting.column}) VALUES (?, ?) "
                f"ON CONFLICT(guild_id) DO UPDATE SET {setting.column} = excluded.{setting.column}",
                (guild_id, stored))
        else:
            await db.execute(
                f"INSERT OR IGNORE INTO {SERVERS_TABLE} (guild_id) VALUES (?)",
                (guild_id,))
            await db.execute(
                f"UPDATE {SERVERS_TABLE} SET {setting.column} = ? WHERE guild_id = ?",
                (stored, guild_id))
        await db.commit()

    invalidate(guild_id)
    return True


async def reset(guild_id):
    """
    Put every setting back to its default.

    Deliberately does NOT clear the habitat channel. "Reset my settings" said by an
    admin who broke something means "undo my tuning", not "stop the bot working" - and
    the channel is the one value whose absence turns the whole ecosystem off.
    """
    guild_id = str(guild_id)
    async with aiosqlite.connect(DB_FILE) as db:
        await ensure_schema(db)
        await db.execute(f"DELETE FROM {TABLE} WHERE guild_id = ?", (guild_id,))
        await db.commit()
    invalidate(guild_id)
    return True


# ==========================================
# ENCODING
# ==========================================
def encode(key, value):
    """A Python value as the column stores it."""
    if value is None:
        return None
    kind = SETTINGS[key].kind
    if kind == BOOL:
        return 1 if value else 0
    if kind == NUMBER:
        return int(value)
    if kind == CHANNEL_LIST:
        return ",".join(str(v) for v in value) or None
    return str(value)


def decode(key, stored):
    """A stored column as the rest of the bot wants it."""
    if stored is None:
        return SETTINGS[key].default
    kind = SETTINGS[key].kind
    if kind == BOOL:
        return bool(stored)
    if kind == NUMBER:
        return int(stored)
    if kind == CHANNEL_LIST:
        return [int(part) for part in str(stored).split(',') if part.strip().isdigit()]
    if kind in (CHANNEL, ROLE):
        return int(stored) if str(stored).isdigit() else None
    return str(stored)


# ==========================================
# PARSING WHAT SOMEBODY TYPED
# ==========================================
TRUE_WORDS = ('on', 'yes', 'true', 'enable', 'enabled', '1', 'y')
FALSE_WORDS = ('off', 'no', 'false', 'disable', 'disabled', '0', 'n')
CLEAR_WORDS = ('none', 'default', 'clear', 'unset', 'reset', '-')


def coerce(key, typed):
    """
    What somebody typed, as a value, or (None, complaint).

    Returns (value, error). A bounded number that lands outside its bounds is REFUSED
    rather than clamped: an admin who typed 1 wanted 1, and silently giving them 5 means
    they will type it again, then come and ask why the setting does not work. The bounds
    themselves exist because a spawn every message is a hosting bill.
    """
    setting = SETTINGS.get(key)
    if setting is None:
        return None, f"`{key}` is not a setting."

    text = str(typed or '').strip()
    if not text or text.lower() in CLEAR_WORDS:
        return None, None       # clear it; the default applies again

    if setting.kind == BOOL:
        low = text.lower()
        if low in TRUE_WORDS:
            return True, None
        if low in FALSE_WORDS:
            return False, None
        return None, f"**{setting.label}** is on or off — try `on` or `off`."

    if setting.kind == NUMBER:
        try:
            number = int(text)
        except ValueError:
            return None, f"**{setting.label}** is a number, and `{text}` is not one."
        if setting.minimum is not None and number < setting.minimum:
            return None, (f"**{setting.label}** cannot go below **{setting.minimum}**. "
                          f"That floor is there on purpose.")
        if setting.maximum is not None and number > setting.maximum:
            return None, (f"**{setting.label}** cannot go above **{setting.maximum}**.")
        return number, None

    if setting.kind in (CHANNEL, ROLE):
        ident = mention_id(text)
        if ident is None:
            noun = "channel" if setting.kind == CHANNEL else "role"
            return None, f"That is not a {noun}. Mention one, or give me its id."
        return ident, None

    if setting.kind == CHANNEL_LIST:
        ids = []
        for part in text.replace(',', ' ').split():
            ident = mention_id(part)
            if ident is None:
                return None, f"`{part}` is not a channel. Mention one, or give me its id."
            ids.append(ident)
        return ids or None, None

    if key == 'timezone':
        ok, problem = valid_timezone(text)
        return (text if ok else None), problem

    return text, None


def mention_id(text):
    """The id inside `<#123>`, `<@&123>` or a bare `123`, or None."""
    digits = ''.join(ch for ch in str(text) if ch.isdigit())
    if not digits or len(digits) < 5:
        return None
    return int(digits)


def valid_timezone(name):
    """Whether this is a real IANA zone, as (ok, complaint)."""
    try:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    except ImportError:                                   # pragma: no cover
        return True, None       # too old to check; storing it is still harmless
    try:
        ZoneInfo(name)
        return True, None
    except (ZoneInfoNotFoundError, ValueError, KeyError):
        return False, (f"`{name}` is not a timezone I recognise. They look like "
                       f"`Europe/London` or `America/New_York`.")
    except Exception:
        # No tz database on this host - Windows without `tzdata` installed. The value is
        # still stored, because refusing it would make the setting unusable on a machine
        # where the only thing missing is a package.
        return True, None


def guild_now(settings):
    """The current time in a server's own timezone, for whatever schedules things next."""
    import datetime
    name = (settings or {}).get('timezone') or 'UTC'
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo(name))
    except Exception:
        return datetime.datetime.now(datetime.timezone.utc)


def describe(key, value, guild=None):
    """One setting's current value, written for a human to read in the panel."""
    setting = SETTINGS[key]

    if value is None or value == [] or value == '':
        return "*not set*"

    if setting.kind == BOOL:
        return "✅ On" if value else "❌ Off"
    if setting.kind == CHANNEL:
        return f"<#{value}>"
    if setting.kind == ROLE:
        return f"<@&{value}>"
    if setting.kind == CHANNEL_LIST:
        return " ".join(f"<#{c}>" for c in value)
    if key == 'despawn_seconds':
        return f"**{value}** seconds" + (f" ({value // 60}m)" if value >= 60 else "")
    if setting.kind == NUMBER:
        return f"**{value}**"
    return f"`{value}`"


async def is_default(guild_id, key):
    """Whether a server is following the default rather than a value it chose."""
    guild_id = str(guild_id)
    if guild_id not in _CACHE:
        await get_all(guild_id)
    return key not in _CACHE.get(guild_id, {})
