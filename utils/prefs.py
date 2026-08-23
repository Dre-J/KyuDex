"""
Per-trainer preferences, and the clock the day/night rules are read off.

**WHY A PER-USER TIMEZONE.** Day and night gate evolutions - Umbreon and Espeon, the
three Lycanroc forms, half a dozen others - and until now the clock they were read off
was UTC. That is nobody's clock. A trainer in Sydney doing their evening play session was
being told it was morning, and their Eevee would not become an Umbreon; there is no way
to work out from the outside why, and nothing about it reads as a mechanic rather than a
bug.

The guild's timezone, which already exists for scheduled events, is not the answer
either. Discord servers are routinely international - a server spanning Europe, North
America and Asia has no meaningful "server night", and whoever the admin happens to be,
most of the members get a cycle disconnected from their own. Worse, the same specimen
would then behave differently depending on which server the command was typed in: same
account, same creature, different rules.

So the order is:

    the trainer's own timezone -> the guild's -> UTC

Each step is a fallback, not a preference: the guild's timezone is still exactly right
for the thing it was added for, which is server-wide scheduling.

**IANA NAMES ARE STORED, NOT OFFSETS.** `Europe/London`, not `UTC+1`. An offset is wrong
for half the year in any country that observes daylight saving, and the failure is
seasonal - it would arrive as a wave of bug reports every March and October, about an
evolution that worked in February.

**NO COOLDOWN ON CHANGING IT.** A trainer can flip their timezone to force night, and
that is fine. Day/night evolutions are not scarce and not competitive, and a cooldown
would put friction in front of everybody who is simply travelling or moved house in order
to stop an exploit that costs nothing. If a time-gate ever becomes load-bearing - a rare
spawn on a schedule - this is the place to add one.
"""

import datetime
import difflib

DEFAULT_TIMEZONE = 'UTC'

# Where a resolved timezone came from, so the caller can say so.
SOURCE_USER = 'user'
SOURCE_GUILD = 'guild'
SOURCE_DEFAULT = 'default'


# ==========================================
# THE ZONE DATABASE
# ==========================================
def _zones():
    """Every IANA zone this host knows, or an empty set if it has no tz database."""
    try:
        from zoneinfo import available_timezones
        return available_timezones()
    except Exception:
        # Windows without the `tzdata` package. Everything below degrades to accepting
        # what it is given, because refusing every timezone on a host that is merely
        # missing an optional package would make the setting unusable rather than safe.
        return set()


def zone_exists(name):
    """Whether `name` names a real zone. True when the host cannot tell."""
    try:
        from zoneinfo import ZoneInfo
    except ImportError:                                     # pragma: no cover
        return True
    try:
        ZoneInfo(str(name))
        return True
    except Exception:
        known = _zones()
        return not known


# The abbreviations people actually type. These are checked BEFORE the exact-name lookup,
# which looks backwards until you know that tzdata ships legacy zones literally called
# `EST`, `MST` and `HST` - and those are FIXED OFFSETS that never observe daylight saving.
# A trainer on the American east coast typing `EST` would have got the `EST` zone, been
# correct all winter, and been an hour out every summer: precisely the seasonal bug this
# module exists to prevent. The abbreviation therefore wins, and resolves to a real
# region zone that knows about DST.
#
# Deliberately MISSING: the genuinely ambiguous ones. IST is India, Ireland and Israel;
# CST is America, China and Cuba. Guessing would put somebody eight hours out silently,
# so they fall through to `AMBIGUOUS_ABBREVIATIONS` and get asked which they meant.
TIMEZONE_ALIASES = {
    'utc': 'UTC', 'gmt': 'UTC', 'z': 'UTC', 'zulu': 'UTC',
    'bst': 'Europe/London', 'uk': 'Europe/London', 'london': 'Europe/London',
    'cet': 'Europe/Paris', 'cest': 'Europe/Paris',
    'eet': 'Europe/Athens', 'eest': 'Europe/Athens',
    'msk': 'Europe/Moscow',
    'est': 'America/New_York', 'edt': 'America/New_York', 'et': 'America/New_York',
    'cdt': 'America/Chicago', 'ct': 'America/Chicago',
    'mst': 'America/Denver', 'mdt': 'America/Denver', 'mt': 'America/Denver',
    'pst': 'America/Los_Angeles', 'pdt': 'America/Los_Angeles',
    'pt': 'America/Los_Angeles', 'pacific': 'America/Los_Angeles',
    'akst': 'America/Anchorage', 'hst': 'Pacific/Honolulu',
    'brt': 'America/Sao_Paulo',
    'jst': 'Asia/Tokyo', 'kst': 'Asia/Seoul',
    'aest': 'Australia/Sydney', 'aedt': 'Australia/Sydney',
    'awst': 'Australia/Perth', 'acst': 'Australia/Adelaide',
    'nzst': 'Pacific/Auckland', 'nzdt': 'Pacific/Auckland',
    'sgt': 'Asia/Singapore', 'hkt': 'Asia/Hong_Kong',
    'wat': 'Africa/Lagos', 'cat': 'Africa/Harare', 'sast': 'Africa/Johannesburg',
}

# The abbreviations that mean several different things. Answered with the choices rather
# than with a guess or a shrug - somebody who typed `IST` knows which country they are
# in, they just do not know what this bot wants to be told.
AMBIGUOUS_ABBREVIATIONS = {
    'ist': ('Asia/Kolkata', 'Europe/Dublin', 'Asia/Jerusalem'),
    'cst': ('America/Chicago', 'Asia/Shanghai', 'America/Havana'),
    'wst': ('Pacific/Apia', 'Australia/Perth'),
    'amt': ('America/Manaus', 'Asia/Yerevan'),
    'bt': ('Asia/Dhaka', 'Europe/London'),
}

# The ones worth naming when somebody asks for help rather than guessing.
COMMON_ZONES = ('UTC', 'Europe/London', 'Europe/Berlin', 'America/New_York',
                'America/Chicago', 'America/Denver', 'America/Los_Angeles',
                'America/Sao_Paulo', 'Asia/Kolkata', 'Asia/Tokyo',
                'Australia/Sydney', 'Pacific/Auckland')


def _offset_zone(text):
    """
    `UTC+5`, `GMT-3`, `+05:30` as an Etc/GMT zone, or None.

    THE SIGN IS INVERTED, and this is not a bug in this function. POSIX named these
    backwards: `Etc/GMT-5` is the zone that is FIVE HOURS AHEAD of UTC. Somebody typing
    `UTC+5` means five ahead, so it becomes `Etc/GMT-5`.

    Half-hour offsets have no Etc zone at all - there is no `Etc/GMT-5:30` - so India
    and Newfoundland and South Australia get a refusal here and fall through to the
    suggester, which points them at the real zone name they should be using anyway.
    """
    body = str(text).strip().upper().replace(' ', '')
    for prefix in ('UTC', 'GMT'):
        if body.startswith(prefix):
            body = body[len(prefix):]
            break
    if not body or body[0] not in '+-':
        return None
    sign, digits = body[0], body[1:]
    if ':' in digits:
        hours, _, minutes = digits.partition(':')
        if minutes.strip('0'):
            return None                 # a half-hour offset; no Etc zone exists for it
        digits = hours
    if not digits.isdigit():
        return None
    hours = int(digits)
    if hours > 14:
        return None
    if hours == 0:
        return 'UTC'
    return f"Etc/GMT{'-' if sign == '+' else '+'}{hours}"


def _looks_like_offset(text):
    """Whether they were plainly trying to type an offset, even a rejected one."""
    body = str(text).strip().upper().replace(' ', '')
    for prefix in ('UTC', 'GMT'):
        if body.startswith(prefix):
            body = body[len(prefix):]
            break
    return bool(body) and body[0] in '+-' and any(ch.isdigit() for ch in body)


def resolve_zone(text):
    """
    A trainer's typing turned into an IANA zone, as `(name, complaint, suggestions)`.

    Exactly one of `name` and `complaint` is ever set. `suggestions` is a list of zone
    names to offer, and may be filled in alongside a complaint OR left empty.

    Tried in order, most specific first: the exact name, an abbreviation, a UTC offset,
    the city on the end of a zone name, and finally a fuzzy match. The city lookup is
    what makes this usable in a prefix command - there is no autocomplete here, and
    nobody types `America/Argentina/Buenos_Aires` from memory.
    """
    raw = str(text or '').strip()
    if not raw:
        return None, "⚠️ Which timezone? Try `!settings timezone Europe/London`.", list(COMMON_ZONES)

    # A space where an underscore belongs is the single commonest way to mistype one of
    # these: "new york", "sao paulo", "los angeles".
    cleaned = raw.replace(' ', '_')
    known = _zones()
    key = cleaned.lower().replace('_', ' ').strip()

    # 1. An abbreviation, FIRST - see the note on TIMEZONE_ALIASES for why this beats the
    #    exact-name lookup rather than losing to it.
    alias = TIMEZONE_ALIASES.get(key) or TIMEZONE_ALIASES.get(cleaned.lower())
    if alias:
        return alias, None, []

    # 2. An abbreviation that means several things. Answered with the list.
    choices = AMBIGUOUS_ABBREVIATIONS.get(key)
    if choices:
        return None, (f"🕒 `{raw}` means different things in different countries. "
                      f"Pick the one you are in:"), list(choices)

    # 3. The exact name, in whatever case they typed it.
    lowered = {z.lower(): z for z in known}
    if cleaned.lower() in lowered:
        return lowered[cleaned.lower()], None, []
    if not known and '/' in cleaned:
        # No tz database to check against. An IANA-shaped name is accepted rather than
        # refused, so the setting still works on a host missing `tzdata`.
        return cleaned, None, []

    # 4. A raw offset.
    offset = _offset_zone(cleaned)
    if offset and (not known or offset in known or offset == 'UTC'):
        return offset, None, []
    if offset is None and _looks_like_offset(cleaned):
        # A half-hour offset, or one past 14 hours. Named zones exist for these places
        # and Etc ones do not, so say which rather than falling through to a fuzzy match
        # that will suggest nothing useful.
        return None, (f"🕒 `{raw}` has no named zone - offsets that are not whole hours "
                      f"only exist as real place names. Try the city instead, such as "
                      f"`Asia/Kolkata` or `Australia/Adelaide`."), list(COMMON_ZONES)

    # 4. The city on the end. `london` -> `Europe/London`.
    target = cleaned.lower().replace('_', '')
    cities = [z for z in known if z.rsplit('/', 1)[-1].lower().replace('_', '') == target]
    if len(cities) == 1:
        return cities[0], None, []
    if len(cities) > 1:
        return None, (f"🕒 `{raw}` matches {len(cities)} zones. Which one?"), sorted(cities)[:8]

    # 5. Anything close. Matched on the city as well as the full name, because a
    #    misspelt city is much likelier than a misspelt continent.
    pool = sorted(known)
    close = difflib.get_close_matches(cleaned, pool, n=5, cutoff=0.6)
    if not close:
        by_city = {z.rsplit('/', 1)[-1].replace('_', ' ').lower(): z for z in pool}
        hits = difflib.get_close_matches(cleaned.replace('_', ' ').lower(),
                                         list(by_city), n=5, cutoff=0.6)
        close = [by_city[h] for h in hits]

    complaint = (f"🕒 `{raw}` is not a timezone I recognise. They look like "
                 f"`Europe/London` or `America/New_York`.")
    return None, complaint, close or list(COMMON_ZONES)


# ==========================================
# READING AND WRITING THE PREFERENCE
# ==========================================
async def _has_column(db, table, column):
    async with db.execute(f"PRAGMA table_info({table})") as cursor:
        return any(row[1] == column for row in await cursor.fetchall())


async def _ensure_column(db, table, column, decl):
    """
    Add a column if it is missing. Does NOT commit. Returns whether it is there now.

    Called only from WRITE paths. A read must never alter the schema - that is how a
    module ends up writing to whatever database happened to be configured at import
    time, which this codebase has been bitten by once already. Each preference column
    therefore appears the first time somebody actually sets that preference, and until
    then every read falls through to its default.

    The column NAME and DECLARATION are interpolated because SQLite cannot bind an
    identifier; both are literals from this module and neither is ever player input.
    """
    if await _has_column(db, table, column):
        return True
    try:
        await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
        return True
    except Exception:
        return False


async def ensure_timezone_column(db):
    """Add `users.timezone` if it is missing. Does NOT commit."""
    return await _ensure_column(db, 'users', 'timezone', 'TEXT')


async def get_timezone(db, user_id):
    """This trainer's own timezone, or None. Never raises, never writes."""
    try:
        if not await _has_column(db, 'users', 'timezone'):
            return None
        async with db.execute("SELECT timezone FROM users WHERE user_id = ?",
                              (str(user_id),)) as cursor:
            row = await cursor.fetchone()
    except Exception:
        return None
    name = (row[0] if row else None) or None
    return str(name).strip() or None if name else None


async def set_timezone(db, user_id, name):
    """
    Store it. Returns False if the database cannot hold it. Does NOT commit.

    Reporting the failure rather than swallowing it is the same rule `set_levelup_pings`
    follows: a setting that says "done" and changes nothing is worse than one that
    admits it could not.
    """
    if not await ensure_timezone_column(db):
        return False
    await db.execute("UPDATE users SET timezone = ? WHERE user_id = ?",
                     (name, str(user_id)))
    return True


async def clear_timezone(db, user_id):
    """Forget it, falling the trainer back to the guild's clock. Does NOT commit."""
    try:
        if not await _has_column(db, 'users', 'timezone'):
            return True
        await db.execute("UPDATE users SET timezone = NULL WHERE user_id = ?",
                         (str(user_id),))
        return True
    except Exception:
        return False


# ==========================================
# HOW `!profile` IS DRAWN
# ==========================================
# An image card is the nicer thing to look at and the worse thing on a slow connection,
# on a screen reader, and on a Pi that has to render it. Neither is right for everybody,
# so it is a preference rather than a decision.
#
# THE DEFAULT IS THE IMAGE, because that is the feature; the embed is the escape hatch
# for anyone who wants text they can select, or who is on mobile data.
CARD_IMAGE = 'image'
CARD_EMBED = 'embed'
CARD_STYLES = (CARD_IMAGE, CARD_EMBED)
DEFAULT_CARD_STYLE = CARD_IMAGE

# Spellings people actually type, mapped to the two the column stores.
CARD_STYLE_WORDS = {
    'image': CARD_IMAGE, 'img': CARD_IMAGE, 'card': CARD_IMAGE, 'picture': CARD_IMAGE,
    'pic': CARD_IMAGE, 'graphic': CARD_IMAGE, 'render': CARD_IMAGE,
    'embed': CARD_EMBED, 'text': CARD_EMBED, 'plain': CARD_EMBED,
    'classic': CARD_EMBED, 'compact': CARD_EMBED, 'old': CARD_EMBED,
}


def resolve_card_style(text):
    """`(style, complaint)` from whatever they typed. Exactly one is ever set."""
    word = str(text or '').strip().lower()
    style = CARD_STYLE_WORDS.get(word)
    if style:
        return style, None
    return None, (f"🖼️ `{text}` is not a card style. Use `!settings card image` for the "
                  f"rendered card, or `!settings card embed` for plain text.")


async def get_card_style(db, user_id):
    """This trainer's chosen style, defaulting to the image. Never raises, never writes."""
    try:
        if not await _has_column(db, 'users', 'card_style'):
            return DEFAULT_CARD_STYLE
        async with db.execute("SELECT card_style FROM users WHERE user_id = ?",
                              (str(user_id),)) as cursor:
            row = await cursor.fetchone()
    except Exception:
        return DEFAULT_CARD_STYLE
    stored = (row[0] if row else None) or ''
    return stored if stored in CARD_STYLES else DEFAULT_CARD_STYLE


async def set_card_style(db, user_id, style):
    """Store it. Returns False if the database cannot hold it. Does NOT commit."""
    if style not in CARD_STYLES:
        return False
    if not await _ensure_column(db, 'users', 'card_style', 'TEXT'):
        return False
    await db.execute("UPDATE users SET card_style = ? WHERE user_id = ?",
                     (style, str(user_id)))
    return True


async def resolve_timezone(db, user_id, guild_id=None):
    """
    `(zone_name, source)` - the clock this trainer's day and night are read off.

    user -> guild -> UTC, and `source` says which of the three it landed on so the
    caller can offer the nudge to somebody still on a fallback.
    """
    mine = await get_timezone(db, user_id)
    if mine:
        return mine, SOURCE_USER

    if guild_id is not None:
        try:
            # cfg.get opens its own connection and caches, so `db` is deliberately not
            # threaded through it. A config read must never be the reason an evolution
            # check fails, which is why the whole thing sits under one except.
            from utils import guild_config as cfg
            theirs = await cfg.get(str(guild_id), 'timezone')
            if theirs and str(theirs).strip() and str(theirs).strip() != DEFAULT_TIMEZONE:
                return str(theirs).strip(), SOURCE_GUILD
        except Exception:
            pass

    return DEFAULT_TIMEZONE, SOURCE_DEFAULT


# ==========================================
# THE CLOCK ITSELF
# ==========================================
def now_in(zone_name):
    """
    An aware `datetime` in `zone_name`, falling back to UTC rather than raising.

    Everything downstream reads `.hour` off this, so a bad zone name must degrade to the
    old behaviour instead of taking an evolution check down with it.
    """
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo(str(zone_name or DEFAULT_TIMEZONE)))
    except Exception:
        return datetime.datetime.now(datetime.timezone.utc)


async def trainer_now(db, user_id, guild_id=None):
    """`(datetime, zone_name, source)` - the whole chain resolved and read."""
    zone, source = await resolve_timezone(db, user_id, guild_id)
    return now_in(zone), zone, source


async def trainer_skies(db, user_id, guild_id=None):
    """
    The sky-names true for THIS TRAINER right now, as `current_skies` returns them.

    The single door between the timezone preference and the evolution rulebook. Every
    place that used to call `current_skies()` bare - and there were three, one per
    engine - calls this instead, so a trainer's Umbreon behaves the same whether it
    levels up in a duel, on a walk, or through `!evolve`.

    `current_skies` is imported inside the function on purpose: utils.constants is a
    large module that indexes several tables at import, and nothing here should drag
    that in just to read a preference.
    """
    from utils.constants import current_skies
    when, _zone, _source = await trainer_now(db, user_id, guild_id)
    return current_skies(when)


def describe_zone(zone_name):
    """`Europe/London · 15:42 · UTC+01:00`, for a settings panel or a profile card."""
    when = now_in(zone_name)
    offset = when.utcoffset() or datetime.timedelta(0)
    total = int(offset.total_seconds())
    sign = '+' if total >= 0 else '-'
    hours, minutes = divmod(abs(total) // 60, 60)
    return (f"{zone_name} · {when.strftime('%H:%M')} · "
            f"UTC{sign}{hours:02d}:{minutes:02d}")


NUDGE = ("🕒 Your day/night clock is **UTC**, which may not be yours. "
         "Set it with `!settings timezone Europe/London` so time-gated evolutions "
         "match your local evening.")


def nudge_if_default(source):
    """The one-time hint, or None. Shown only to somebody still on the last resort."""
    return NUDGE if source == SOURCE_DEFAULT else None
