"""The one channel where anything worth reconstructing later gets posted.

Trades were the first thing to need this, so the posting logic grew inside
`utils/trading.py`. The owner tools need exactly the same thing - and for a stronger
reason. A trade has two participants who both saw it happen; an admin grant has one
person, acting alone, with the power to mint currency and rewrite other people's
Pokemon. That is precisely the kind of action that should not be reconstructable only
from the console of whoever ran it.

One function, and every failure is swallowed. A missing channel, a revoked permission
or a Discord outage must never turn into a command failing halfway - the authoritative
records are the database rows, and this is a readable tail on top of them.
"""
import discord

from utils.constants import TRADE_LOG_CHANNEL_ID

# Named for what it is rather than for its first caller. The trade log and the admin log
# are the same channel on purpose: one place to look when reconstructing "where did this
# Pokemon come from", whether the answer is a trade or a Director.
LOG_CHANNEL_ID = TRADE_LOG_CHANNEL_ID


async def post(bot, embed):
    """
    Put an embed in the log channel. Returns whether it went.

    A False here is not an error worth surfacing to a player - it means the channel is
    unset, unreachable or the bot cannot post there, all of which are configuration
    rather than a failed action.
    """
    if not LOG_CHANNEL_ID or bot is None or embed is None:
        return False

    try:
        channel = bot.get_channel(LOG_CHANNEL_ID)
        if channel is None:
            return False
        await channel.send(embed=embed)
        return True
    except Exception as e:
        print(f"⚠️ Audit log post failed: {e}")
        return False


async def post_admin_action(bot, *, action, actor, target=None, colour=None, fields=(),
                            detail=None):
    """
    Record an owner-only action.

    `fields` is a sequence of (name, value) pairs. The actor and the target are named by
    id as well as by display name, because a display name is not an identifier and the
    whole point of this record is being able to find the account again in six months.
    """
    embed = discord.Embed(
        title=f"🛠️ Admin · {action}",
        colour=colour or discord.Colour.dark_orange(),
        timestamp=discord.utils.utcnow())

    for name, value in fields:
        embed.add_field(name=name, value=value, inline=False)
    if detail:
        embed.add_field(name="Detail", value=detail, inline=False)

    embed.add_field(name="Authorised by", value=_who(actor), inline=True)
    if target is not None:
        embed.add_field(name="Target", value=_who(target), inline=True)

    return await post(bot, embed)


def _who(user):
    """A user as both a name and an id, because only one of those is an identifier."""
    if user is None:
        return "—"
    name = (getattr(user, 'display_name', None) or getattr(user, 'name', None)
            or str(user))
    ident = getattr(user, 'id', user)
    return f"{name} (`{ident}`)"
