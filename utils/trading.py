"""Who may hand a specimen to somebody else, and a record of everyone who did.

Two separate jobs, deliberately kept together because they guard the same doorways.

**The starter does not leave.** The starter is now a bundle - guaranteed-good IVs, a
token grant, free Great Balls - which makes it worth farming with alt accounts: make an
account, claim the bundle, trade it to your main, abandon it. Detecting that is a losing
game; removing the incentive is not. It also protects new players who get talked out of
their starter by somebody friendly in a large server, which happens, and where the
victim usually did not understand what they were giving up.

Not forever, though. A trainer who has caught `STARTER_LOCK_CATCHES` specimens of their
own is plainly not an alt, and by then the starter is theirs to do as they like with.

**Every transfer is written down.** Not to watch anybody - to be able to reconstruct an
incident. When a duplication bug turns up, and with market, GTS and trading all writing
to the same table one will, the ledger is the difference between unwinding it and
wiping everybody's progress. It also answers "he took mine and never sent his", which
is otherwise unanswerable.

The ledger is APPEND-ONLY. Nothing here updates or deletes a row, and both sides are
stored as a JSON snapshot rather than a reference, because a specimen that gets traded
on, evolved or renamed would otherwise quietly rewrite the history of its own trade.
"""
import json
from datetime import datetime, timezone

import discord

from utils import audit
from utils.constants import TRADE_LOG_CHANNEL_ID

# How many specimens a trainer must have caught themselves before their starter is
# theirs to trade. Counted on original_user_id, so receiving specimens cannot advance
# it - only actually playing does.
STARTER_LOCK_CATCHES = 50

TRADE_TYPES = ('gift', 'trade', 'gts', 'gts-swap', 'market')

# How long a trade record is kept. Twelve months, set by the operator rather than
# guessed at here: the ledger exists to reconstruct incidents, and a duplication bug or
# a scam report can surface months after the fact, but "we keep it because we might want
# it" is not a retention policy. This is the number the privacy policy states, and
# `!privacy` reads it from here so the two cannot drift.
LOG_RETENTION_DAYS = 365


async def purge_expired_logs(db):
    """
    Delete trade records past the retention window. Returns how many went.

    Deliberately the ONLY thing in this module that removes a row. The ledger is
    append-only for correctness - nothing may rewrite the history of a trade - but
    append-only forever is a different promise from the one the privacy policy makes,
    and this is the seam between them.

    Does not commit; the caller owns the transaction.
    """
    try:
        cursor = await db.execute(
            "DELETE FROM trade_logs "
            "WHERE logged_at < datetime('now', ?)", (f'-{LOG_RETENTION_DAYS} days',))
        return cursor.rowcount
    except Exception as e:
        # A database without the ledger table yet, or without the column. Never let
        # housekeeping take the bot down.
        print(f"⚠️ Trade log purge failed: {e}")
        return 0


async def _has_column(db, table, column):
    async with db.execute(f"PRAGMA table_info({table})") as cursor:
        return any(row[1] == column for row in await cursor.fetchall())


async def mark_as_starter(db, instance_id):
    """
    Flag a specimen as the trainer's starter, if the database can hold that fact.

    A separate UPDATE rather than a column in the registration INSERT, because an
    INSERT naming a column that does not exist fails the whole registration - so
    deploying this code before running the migration would have broken `!start`
    outright. Every other new column in this codebase is read the same guarded way.

    Does not commit; the caller owns the transaction.
    """
    if not await _has_column(db, 'caught_pokemon', 'is_starter'):
        return False
    await db.execute("UPDATE caught_pokemon SET is_starter = 1 WHERE instance_id = ?",
                     (instance_id,))
    return True


async def own_catch_count(db, user_id):
    """Specimens this trainer caught themselves, however many they still hold."""
    async with db.execute(
            "SELECT COUNT(*) FROM caught_pokemon WHERE original_user_id = ?",
            (str(user_id),)) as cursor:
        return (await cursor.fetchone())[0]


async def blocked_from_trading(db, instance_id, owner_id):
    """
    Why this specimen may not be handed over, or None if it may.

    Returns a sentence fit to show a player. Answering with a REASON rather than a
    boolean is deliberate: "you cannot trade that" with no explanation is the kind of
    refusal people assume is a bug.

    Degrades open on a database without the column, rather than blocking every trade
    in the game because a migration has not been run.
    """
    if not await _has_column(db, 'caught_pokemon', 'is_starter'):
        return None

    async with db.execute(
            "SELECT is_starter FROM caught_pokemon WHERE instance_id = ?",
            (instance_id,)) as cursor:
        row = await cursor.fetchone()

    if not row or not row[0]:
        return None

    caught = await own_catch_count(db, owner_id)
    if caught >= STARTER_LOCK_CATCHES:
        return None

    return (f"🔒 Your starter cannot be traded away yet. It unlocks once you have "
            f"caught **{STARTER_LOCK_CATCHES}** specimens of your own "
            f"(**{caught}/{STARTER_LOCK_CATCHES}** so far).")


async def first_blocked(db, instances, owner_id):
    """The first refusal among several offered specimens, or None."""
    for instance_id in instances:
        reason = await blocked_from_trading(db, instance_id, owner_id)
        if reason:
            return instance_id, reason
    return None


async def snapshot(db, instance_ids):
    """
    What these specimens were AT THE MOMENT OF THE TRADE.

    A snapshot rather than a list of ids, because the whole value of the record is
    that it still describes the trade after the Pokemon involved have moved on,
    evolved, or been renamed.
    """
    if not instance_ids:
        return []

    marks = ','.join('?' * len(instance_ids))
    async with db.execute(f"""
        SELECT cp.instance_id, s.name, cp.level, cp.is_shiny, cp.nature, cp.gender,
               cp.held_item, cp.iv_hp, cp.iv_attack, cp.iv_defense,
               cp.iv_sp_atk, cp.iv_sp_def, cp.iv_speed
        FROM caught_pokemon cp
        JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
        WHERE cp.instance_id IN ({marks})
    """, tuple(instance_ids)) as cursor:
        rows = await cursor.fetchall()

    return [{
        'instance_id': r[0], 'species': r[1], 'level': r[2], 'shiny': bool(r[3]),
        'nature': r[4], 'gender': r[5], 'held_item': r[6],
        'ivs': {'hp': r[7], 'attack': r[8], 'defense': r[9],
                'sp_atk': r[10], 'sp_def': r[11], 'speed': r[12]},
    } for r in rows]


async def log_trade(db, *, trade_type, user_a, user_b=None, side_a=None, side_b=None,
                    guild_id=None, detail=None):
    """
    Append one row to the ledger. Never updates, never deletes.

    Does NOT commit - the caller owns the transaction, so a trade that rolls back
    cannot leave a record of a transfer that did not happen.
    """
    try:
        await db.execute("""
            INSERT INTO trade_logs
                (trade_type, guild_id, user_a, user_b, side_a, side_b, detail)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (trade_type, str(guild_id) if guild_id else None, str(user_a),
              str(user_b) if user_b else None,
              json.dumps(side_a or []), json.dumps(side_b or []), detail))
    except Exception as e:
        # A failure to WRITE THE LOG must never undo the trade itself. The record is
        # worth a great deal; it is not worth a player losing a Pokemon over.
        print(f"⚠️ Trade log write failed ({trade_type}): {e}")


def describe_side(entries):
    """A logged side, as one line fit for a channel message."""
    if not entries:
        return "*nothing*"
    return ", ".join(
        f"{'✨ ' if e.get('shiny') else ''}{str(e.get('species', '?')).replace('-', ' ').title()}"
        f" (Lv {e.get('level', '?')})"
        for e in entries)


TRADE_HEADINGS = {
    'gift':     ('🎁 Gift', discord.Colour.teal()),
    'trade':    ('🤝 Direct Trade', discord.Colour.blue()),
    'gts':      ('🌐 GTS Match', discord.Colour.purple()),
    'gts-swap': ('🌐 GTS Swap', discord.Colour.purple()),
    'market':   ('💰 Market Sale', discord.Colour.gold()),
}


async def announce_trade(bot, *, trade_type, user_a, user_b, side_a, side_b,
                         detail=None):
    """
    Post the trade to the log channel, if there is one.

    Deliberately a plain record rather than a highlight reel: who, what, when. The
    ledger exists to reconstruct incidents, not to rank or expose anybody, which is the
    same call as not publishing a top-polluters leaderboard.

    Every failure here is swallowed. A missing channel, a revoked permission or a
    Discord outage must never turn into a player losing a Pokemon - the authoritative
    record is the trade_logs table, and this is a convenience on top of it.
    """
    title, colour = TRADE_HEADINGS.get(trade_type, ('📦 Transfer',
                                                    discord.Colour.greyple()))
    embed = discord.Embed(title=title, colour=colour,
                          timestamp=datetime.now(timezone.utc))
    embed.add_field(name=f"{_label(user_a)} gave", value=describe_side(side_a),
                    inline=False)
    if user_b is not None:
        embed.add_field(name=f"{_label(user_b)} gave", value=describe_side(side_b),
                        inline=False)
    if detail:
        embed.add_field(name="Detail", value=detail, inline=False)
    embed.set_footer(text=f"{trade_type} · IDs {_id(user_a)} / {_id(user_b)}")

    # The channel plumbing lives in utils/audit.py now, because the owner tools need the
    # same thing and two copies of "post this, swallow everything" is one too many.
    await audit.post(bot, embed)


def _label(user):
    """A user object, an id, or None - all readable."""
    if user is None:
        return "—"
    return getattr(user, 'display_name', None) or getattr(user, 'name', None) or str(user)


def _id(user):
    if user is None:
        return "—"
    return str(getattr(user, 'id', user))
