"""Aggregate command counts, and the daily digest that posts them.

The counting itself is two listeners and four lines; everything interesting is in
`utils/usage.py`, which owns the schema and the deliberate absence of a user column.

WHY A DIGEST RATHER THAN A POST PER COMMAND. Trades and admin actions post individually
because each one is an EVENT somebody might later need to reconstruct. A command being
run is not an event - it is a tick - and a channel receiving one embed per `!catch` would
be unreadable within a minute and would bury the trade records it shares the channel
with. So the counts accumulate and a summary goes up once a day.
"""
import datetime

import aiosqlite
import discord
from discord.ext import commands, tasks

from utils import audit, usage
from utils.constants import DB_FILE

# The digest goes up shortly after the UTC day rolls over, so a day's line is complete
# when it is posted rather than being a partial count of the day in progress.
DIGEST_HOUR_UTC = 0
DIGEST_MINUTE_UTC = 5


class Usage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily_digest.start()

    def cog_unload(self):
        self.daily_digest.cancel()

    # ==========================================
    # COUNTING
    # ==========================================
    # Two listeners rather than one. `on_command_completion` is usage; `on_command_error`
    # is a command that was reached and then failed, which is worth separating - a
    # command being run constantly and erroring constantly should not look identical to
    # one that simply works.
    #
    # Neither records WHO. `ctx.author` is right there and is deliberately not touched.
    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        await self._count(ctx, failed=False)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        # CommandNotFound has no command to count, and a failed check is a refusal by
        # design rather than a fault - the channel restriction in cogs/config.py refuses
        # constantly and correctly. Counting those as errors would make the busiest
        # "failing" command whichever one is used most in a restricted channel.
        if isinstance(error, (commands.CommandNotFound, commands.CheckFailure)):
            return
        await self._count(ctx, failed=True)

    async def _count(self, ctx, *, failed):
        command = getattr(ctx, 'command', None)
        if command is None:
            return
        try:
            async with aiosqlite.connect(DB_FILE) as db:
                await usage.record(db, command.qualified_name, failed=failed)
                await db.commit()
        except Exception as e:
            # Telemetry must never be the reason a command appears to fail. The player
            # has already had their answer by the time this runs.
            print(f"⚠️ Command usage counter failed: {e}")

    # ==========================================
    # THE DIGEST
    # ==========================================
    @tasks.loop(time=datetime.time(hour=DIGEST_HOUR_UTC, minute=DIGEST_MINUTE_UTC,
                                   tzinfo=datetime.timezone.utc))
    async def daily_digest(self):
        # A bot that has not logged in is a test harness or an import, not a deployment -
        # the same guard `prune_trade_logs` carries, and for the same reason.
        if not self.bot.is_ready():
            return
        try:
            async with aiosqlite.connect(DB_FILE) as db:
                rows = await usage.totals(db, since=usage.days_ago(1))
                removed = await usage.sweep_old(db)
                await db.commit()
            if not rows:
                return
            body, total_uses, total_errors, distinct = usage.describe(rows)
            await audit.post_command_digest(
                self.bot, rows=rows, window="last 24 hours", total_uses=total_uses,
                total_errors=total_errors, distinct=distinct, body=body)
            if removed:
                print(f"🧹 Usage counters: removed {removed} expired day-row(s).")
        except Exception as e:
            # An exception escaping a tasks.loop body CANCELS THE TASK for the rest of
            # the process, which would silently stop the digest rather than skip one.
            print(f"⚠️ Command usage digest failed: {e}")

    @daily_digest.before_loop
    async def _wait_for_bot(self):
        try:
            await self.bot.wait_until_ready()
        except Exception:
            # Anything at all - RuntimeError on a Client that never logged in,
            # AttributeError on a test double. The loop body checks is_ready() itself,
            # so falling straight through is safe, and an exception here would cancel
            # the task permanently.
            pass

    # ==========================================
    # ON DEMAND
    # ==========================================
    @commands.command(name="usage", aliases=["commandstats", "cmdstats"])
    @commands.is_owner()
    async def usage_now(self, ctx, days: int = 7):
        """[OWNER] Post the command counts for the last `days` days to the log channel."""
        days = max(1, min(365, days))
        try:
            async with aiosqlite.connect(DB_FILE) as db:
                rows = await usage.totals(db, since=usage.days_ago(days))
        except Exception as e:
            print(f"Usage report error: {e}")
            return await ctx.send("❌ Could not read the command counters.")

        body, total_uses, total_errors, distinct = usage.describe(rows)
        window = "today" if days == 1 else f"last {days} days"
        posted = await audit.post_command_digest(
            self.bot, rows=rows, window=window, total_uses=total_uses,
            total_errors=total_errors, distinct=distinct, body=body)

        if posted:
            return await ctx.send(f"📊 Posted the {window} command counts to the log channel.")
        # No log channel configured, or it is unreachable. The figures are still worth
        # having, so they come back here rather than being lost to a configuration gap.
        await ctx.send(f"📊 **Command usage — {window}**\n{body}\n"
                       f"*{total_uses:,} uses across {distinct} commands. "
                       f"No log channel is configured, so this was not posted.*")


async def setup(bot):
    await bot.add_cog(Usage(bot))
