"""Account lifecycle: starting over, and leaving.

Two commands that destroy the same things and differ in one respect.

`!reset` wipes progress and hands the trainer a fresh licence - a product feature, and
one with an exploit attached: if resetting is free and instant, players reset until the
starter roll goes their way. Three things answer that, and the first two live elsewhere:
starters now have a guaranteed floor and can never be shiny, so there is little left to
reroll FOR. The cooldown here is the backstop.

`!privacy delete` is erasure. Nothing remains, and there is no cooldown, because a legal
obligation is not a game mechanic.

Both confirm the same way: a list of what dies with real numbers off the account, a
phrase typed out rather than a button pressed, and a grace period afterwards. People
reset in anger and regret it within the hour, and a button is one misclick away.
"""
import asyncio
import traceback

import aiosqlite
import discord
from discord.ext import commands

from utils import checks
from utils.accounts import (RESET_COOLDOWN_DAYS, account_summary, reset_available_at,
                            wipe_user)
from utils.constants import DB_FILE

# Long enough to read the list, short enough that nobody wanders off mid-confirmation.
CONFIRM_TIMEOUT = 60.0

# The pause after the phrase is typed. Deliberately not a formality - it is the window
# in which somebody realises what they are doing.
GRACE_SECONDS = 10


def summary_lines(counts):
    """The account, itemised. Zeroes are shown too - an empty roster is worth seeing."""
    lines = [
        f"🧬 **{counts['specimens']}** registered specimen(s)"
        + (f" — including **{counts['shinies']}** shiny" if counts['shinies'] else ""),
        f"📈 Highest level reached: **{counts['highest_level'] or '—'}**",
        f"🪙 **{counts['tokens']:,}** Eco Tokens",
        f"🎒 **{counts['items']}** item(s) in the field pack",
    ]
    if counts['listings']:
        lines.append(f"🌐 **{counts['listings']}** live market listing(s) — withdrawn")
    if counts['gts']:
        lines.append(f"🔁 **{counts['gts']}** GTS deposit(s) — cancelled")
    if counts['deployments']:
        lines.append(f"🛰️ **{counts['deployments']}** deployed specimen(s) — recalled")
    return lines


class Account(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==========================================
    # SHARED MACHINERY
    # ==========================================
    @staticmethod
    def _forget(container, *keys):
        """
        Drop a trainer from a session store, whichever shape that store happens to be.

        These two are not the same kind of object and never have been: combat keeps
        `active_battles` as a dict keyed by str(id), social keeps `active_trades` as a
        SET of int ids. Treating both as dicts is what broke this - `set.pop()` takes no
        arguments, so the TypeError killed the command before it opened the database.
        """
        if container is None:
            return
        for key in keys:
            if isinstance(container, dict):
                container.pop(key, None)
            elif isinstance(container, (set, frozenset)):
                if isinstance(container, set):
                    container.discard(key)
            elif isinstance(container, list):
                while key in container:
                    container.remove(key)

    def release_live_sessions(self, user_id):
        """
        Drop the trainer out of any in-memory battle or trade before the wipe.

        The command checks already refuse to run mid-battle, so this is the second lock
        rather than the first: an in-memory battle holding a pointer to a specimen that
        is about to stop existing is the same orphan problem as a stale market listing,
        just in RAM instead of SQLite.

        Both spellings of the id are tried because the two stores disagree about which
        one they use, and being wrong here is cheap while guessing wrong is not.
        """
        combat = self.bot.get_cog("Combat")
        if combat is not None:
            self._forget(getattr(combat, 'active_battles', None),
                         str(user_id), int(user_id))

        social = self.bot.get_cog("Social")
        if social is not None:
            self._forget(getattr(social, 'active_trades', None),
                         int(user_id), str(user_id))

    async def confirm_destruction(self, ctx, *, title, phrase, colour, warning):
        """
        Show what will be destroyed and wait for the phrase. True if it should proceed.

        Every exit prints something. A confirmation flow that goes quiet on timeout
        leaves the trainer unsure whether it fired.
        """
        user_id = str(ctx.author.id)

        async with aiosqlite.connect(DB_FILE) as db:
            counts = await account_summary(db, user_id)

        embed = discord.Embed(title=title, colour=colour, description=warning)
        embed.add_field(name="This will be destroyed",
                        value="\n".join(summary_lines(counts)), inline=False)
        embed.add_field(
            name="To confirm",
            value=f"Type `{phrase}` exactly, within {int(CONFIRM_TIMEOUT)} seconds.\n"
                  f"Anything else — or nothing at all — cancels.",
            inline=False)
        await ctx.send(embed=embed)

        def is_the_phrase(message):
            return (message.author == ctx.author
                    and message.channel == ctx.channel)

        try:
            reply = await self.bot.wait_for('message', check=is_the_phrase,
                                            timeout=CONFIRM_TIMEOUT)
        except asyncio.TimeoutError:
            await ctx.send("⏳ Confirmation timed out. **Nothing was changed.**")
            return False

        if reply.content.strip() != phrase:
            await ctx.send("✅ Cancelled. **Nothing was changed.**")
            return False

        # The grace window. Typing anything at all here calls it off.
        countdown = await ctx.send(
            f"⚠️ Confirmed. Executing in **{GRACE_SECONDS} seconds** — "
            f"send any message to abort.")
        try:
            await self.bot.wait_for(
                'message',
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
                timeout=float(GRACE_SECONDS))
        except asyncio.TimeoutError:
            return True                      # nobody flinched; proceed

        await countdown.edit(content="✅ Aborted. **Nothing was changed.**")
        return False

    # ==========================================
    # RESET - keeps the licence
    # ==========================================
    @commands.command(name="reset")
    @checks.has_started()
    @checks.is_authorized()
    @checks.is_not_in_trade()
    @checks.is_not_in_combat()
    async def reset_account(self, ctx):
        """Wipes your progress and starts you over with a fresh licence."""
        user_id = str(ctx.author.id)

        async with aiosqlite.connect(DB_FILE) as db:
            allowed, days_left = await reset_available_at(db, user_id)

        if not allowed:
            return await ctx.send(
                f"🕒 **Reset unavailable.** You may reset once every "
                f"{RESET_COOLDOWN_DAYS} days — **{days_left}** day(s) remaining.\n"
                f"*If you meant to erase your data entirely rather than start over, "
                f"`!privacy delete` has no cooldown.*")

        proceed = await self.confirm_destruction(
            ctx,
            title="♻️ Full Progress Reset",
            phrase="RESET MY ACCOUNT",
            colour=discord.Colour.orange(),
            warning=(f"Your research licence survives — **everything on it does not.** "
                     f"This cannot be undone, and you may only do it once every "
                     f"{RESET_COOLDOWN_DAYS} days."))
        if not proceed:
            return

        # Inside the try, deliberately. This used to sit above it, so when it raised the
        # command died before touching the database and said nothing at all - the wipe
        # looked like it had silently refused to commit.
        try:
            self.release_live_sessions(user_id)
            async with aiosqlite.connect(DB_FILE) as db:
                await db.execute("BEGIN TRANSACTION")
                removed = await wipe_user(db, user_id, keep_account=True)
                await db.commit()
        except Exception as e:
            traceback.print_exc()
            print(f"Account Reset Error for {user_id}: {e}")
            return await ctx.send(
                "❌ A critical error occurred. **Your account was not changed** — the "
                "wipe runs as a single transaction and rolled back.")

        print(f"RESET {user_id}: {removed}")
        embed = discord.Embed(
            title="♻️ Progress Reset",
            description=("Your licence is intact and your roster is empty.\n\n"
                         "Use `!start` to choose a new partner."),
            colour=discord.Colour.green())
        embed.set_footer(text=f"You may reset again in {RESET_COOLDOWN_DAYS} days.")
        await ctx.send(embed=embed)

    # ==========================================
    # PRIVACY - keeps nothing
    # ==========================================
    @commands.group(name="privacy", invoke_without_command=True)
    async def privacy(self, ctx):
        """Explains what the bot stores and how to have it erased."""
        embed = discord.Embed(
            title="🔒 Your Data",
            colour=discord.Colour.blurple(),
            description="What this bot stores about you, and how to get rid of it.")
        embed.add_field(
            name="What is stored",
            value=("Your Discord user ID, the specimens you have caught and their "
                   "statistics, your tokens and items, market and GTS activity, and "
                   "per-server contribution totals."),
            inline=False)
        embed.add_field(
            name="Starting over",
            value=f"`!reset` wipes your progress but keeps your licence. "
                  f"Once every {RESET_COOLDOWN_DAYS} days.",
            inline=False)
        embed.add_field(
            name="Erasure",
            value="`!privacy delete` removes everything, including the account itself. "
                  "No cooldown. Not reversible.",
            inline=False)
        await ctx.send(embed=embed)

    @privacy.command(name="delete")
    @checks.has_started()
    @checks.is_not_in_trade()
    @checks.is_not_in_combat()
    async def privacy_delete(self, ctx):
        """Erases your account and every record attached to it."""
        user_id = str(ctx.author.id)

        proceed = await self.confirm_destruction(
            ctx,
            title="🗑️ Permanent Data Erasure",
            phrase="DELETE MY ACCOUNT",
            colour=discord.Colour.dark_red(),
            warning=("**Everything below is erased, and your account with it.** "
                     "This is not a reset — no licence remains and nothing can be "
                     "recovered. You may register again from scratch at any time."))
        if not proceed:
            return

        # Inside the try - see the note in reset_account.
        try:
            self.release_live_sessions(user_id)
            async with aiosqlite.connect(DB_FILE) as db:
                await db.execute("BEGIN TRANSACTION")
                removed = await wipe_user(db, user_id, keep_account=False)
                await db.commit()
        except Exception as e:
            traceback.print_exc()
            print(f"Account Deletion Error for {user_id}: {e}")
            return await ctx.send(
                "❌ A critical error occurred. **Nothing was erased** — the wipe runs "
                "as a single transaction and rolled back. Please try again, or contact "
                "an administrator so this can be completed manually.")

        print(f"ERASED {user_id}: {removed}")
        await ctx.send(embed=discord.Embed(
            title="🗑️ Erasure Complete",
            description=("Every record attached to your account has been removed.\n\n"
                         "*Moderation records, where any exist, are retained for abuse "
                         "prevention.*\n\nUse `!start` if you ever want to come back."),
            colour=discord.Colour.dark_grey()))


async def setup(bot):
    await bot.add_cog(Account(bot))
