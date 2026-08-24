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
from discord.ext import commands, tasks

from utils import checks
from utils.accounts import (RESET_COOLDOWN_DAYS, account_summary,
                            levelup_pings_enabled, reset_available_at,
                            set_levelup_pings, wipe_user)
from utils.constants import DB_FILE
from utils.constants import BIOME_ORDER, biome_label, current_skies
from utils.prefs import (CARD_BIOME_AUTO, CARD_EMBED, CARD_IMAGE, COMMON_ZONES,
                         SOURCE_DEFAULT, SOURCE_GUILD, SOURCE_USER, clear_timezone,
                         describe_zone, get_card_biome, get_card_style, now_in,
                         resolve_biome_word, resolve_card_biome, resolve_card_style,
                         resolve_timezone, resolve_zone, set_card_biome,
                         set_card_style, set_timezone)
from utils.trading import LOG_RETENTION_DAYS, purge_expired_logs

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
        self.prune_trade_logs.start()

    def cog_unload(self):
        self.prune_trade_logs.cancel()

    # ==========================================
    # RETENTION
    # ==========================================
    # The ledger is append-only for correctness - nothing may rewrite the history of a
    # trade - but append-only FOREVER is a different promise from the one the privacy
    # policy makes. Twelve months, and this is the only thing in the codebase that
    # deletes a trade record.
    #
    # A daily sweep rather than a purge on every write: the cost is the same either way
    # on a table this size, but a scheduled job is a thing you can point at when
    # somebody asks how retention is enforced, and a side effect buried in log_trade is
    # not. Runs once at startup too, so a bot that is restarted nightly still prunes.
    @tasks.loop(hours=24)
    async def prune_trade_logs(self):
        # A bot that has not logged in is a test harness or an import, not a
        # deployment. Housekeeping that writes to the live database must not run
        # because somebody registered the cog to read its command list.
        if not self.bot.is_ready():
            return
        try:
            async with aiosqlite.connect(DB_FILE) as db:
                removed = await purge_expired_logs(db)
                await db.commit()
            if removed:
                print(f"🧹 Retention: removed {removed} trade record(s) older than "
                      f"{LOG_RETENTION_DAYS} days.")
        except Exception as e:
            # Housekeeping must never take the bot down, and must never stop the loop -
            # an exception escaping a tasks.loop body cancels the task for good.
            print(f"⚠️ Trade log retention sweep failed: {e}")

    @prune_trade_logs.before_loop
    async def _wait_for_bot(self):
        try:
            await self.bot.wait_until_ready()
        except Exception:
            # Anything at all. `wait_until_ready` raises RuntimeError on a Client that
            # was never logged in, and AttributeError on a test double that never had
            # the method - and an exception escaping before_loop CANCELS THE TASK for
            # the rest of the process, which would silently disable retention rather
            # than merely delaying it. The loop body checks is_ready() itself, so
            # falling straight through is safe.
            pass

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
    # NOTIFICATIONS - how loudly the bot talks to you
    # ==========================================
    # NOT aliased to "notifications" - `!inbox` already owns that one, and a duplicate
    # alias is not a warning: it raises CommandRegistrationError and takes the whole
    # cog down with it.
    @commands.command(name="notify", aliases=["pings"])
    @checks.has_started()
    async def notify(self, ctx, setting: str = None):
        """Turn level-up announcements on or off. `!notify off`"""
        user_id = str(ctx.author.id)
        wanted = {'on': True, 'enable': True, 'enabled': True, 'yes': True,
                  'off': False, 'disable': False, 'disabled': False, 'no': False}

        async with aiosqlite.connect(DB_FILE) as db:
            # No argument reads the setting back rather than guessing at a toggle.
            # Flipping an unseen boolean is how people end up turning a thing on when
            # they meant to check whether it was off.
            if setting is None or setting.lower() not in wanted:
                current = await levelup_pings_enabled(db, user_id)
                state = "**on**" if current else "**off**"
                return await ctx.send(
                    f"🔔 Level-up announcements are {state}.\n"
                    f"Use `!notify on` or `!notify off` to change it.\n"
                    f"*Announcements never ping or reply to you either way — this "
                    f"controls whether they are posted at all.*")

            enabled = wanted[setting.lower()]
            stored = await set_levelup_pings(db, user_id, enabled)
            await db.commit()

        if not stored:
            return await ctx.send(
                "⚠️ This database has not had `migrate_notifications.py` run against "
                "it yet, so the preference cannot be saved. Announcements stay on for "
                "now — they are silent regardless.")

        if enabled:
            await ctx.send("🔔 Level-up announcements are **on**. They will not ping "
                           "or reply to you.")
        else:
            await ctx.send("🔕 Level-up announcements are **off**. Evolution prompts "
                           "still appear — they need an answer, and there is no other "
                           "way to reach a level-up evolution.")

    # ==========================================
    # SETTINGS - the trainer's own preferences
    # ==========================================
    # Distinct from `!config`, which is the SERVER's settings and needs Manage Server.
    # These belong to one person and travel with them between servers, which is the whole
    # point of the timezone: a specimen must not behave differently depending on where
    # its owner happened to type the command.
    @commands.group(name="settings", aliases=["prefs", "preferences"],
                    invoke_without_command=True)
    @checks.has_started()
    async def settings(self, ctx):
        """Your personal preferences. `!settings timezone Europe/London`"""
        user_id = str(ctx.author.id)
        guild_id = ctx.guild.id if ctx.guild else None

        async with aiosqlite.connect(DB_FILE) as db:
            zone, source = await resolve_timezone(db, user_id, guild_id)
            pings = await levelup_pings_enabled(db, user_id)
            style = await get_card_style(db, user_id)
            stored_biome = await get_card_biome(db, user_id)
            async with db.execute("SELECT unlocked_visas FROM users WHERE user_id = ?",
                                  (user_id,)) as cursor:
                visa_row = await cursor.fetchone()

        raw_visas = (visa_row[0] if visa_row and visa_row[0] else 'canopy')
        held = [b for b in BIOME_ORDER
                if b in {v.strip().lower() for v in str(raw_visas).split(',')}]
        card_biome = resolve_card_biome(stored_biome, held)

        skies = current_skies(now_in(zone))
        origin = {SOURCE_USER: "your own setting",
                  SOURCE_GUILD: "this server's setting",
                  SOURCE_DEFAULT: "the default"}[source]

        embed = discord.Embed(
            title=f"⚙️ {ctx.author.name}'s Preferences",
            colour=discord.Colour.blurple())
        embed.add_field(
            name="🕒 Timezone",
            value=(f"**{describe_zone(zone)}**\n"
                   f"*From {origin}.* Day/night is currently "
                   f"**{'/'.join(sorted(skies))}**.\n"
                   f"`!settings timezone <zone>`"),
            inline=False)
        embed.add_field(
            name="🖼️ Profile card",
            value=(f"Drawn as **{style}** · `!settings card image|embed`\n"
                   f"Dressed in **{biome_label(card_biome)}**"
                   + ("" if stored_biome else " *(your deepest clearance)*")
                   + f" · `!settings biome`\n"
                   f"*{len(held)} of {len(BIOME_ORDER)} sectors cleared.*"),
            inline=False)
        embed.add_field(
            name="🔔 Level-up announcements",
            value=f"**{'on' if pings else 'off'}** · `!notify on` / `!notify off`",
            inline=False)

        # The nudge lives here too, not only on the evolution that failed - somebody who
        # opens the panel is already asking the question this answers.
        if source != SOURCE_USER:
            embed.set_footer(
                text="Time-gated evolutions - Umbreon, Espeon, the Lycanroc forms - "
                     "read your timezone. Set yours so they match your own evening.")
        await ctx.send(embed=embed)

    @settings.command(name="card", aliases=["profile", "cards"])
    @checks.has_started()
    async def settings_card(self, ctx, *, style: str = None):
        """
        How `!profile` is drawn. `!settings card image` or `!settings card embed`.

        The image is the default because it is the feature. The embed exists because an
        image is the worse answer on a slow connection, on a screen reader, and anywhere
        the numbers want copying out - none of which is a minority worth ignoring.
        """
        user_id = str(ctx.author.id)

        if style is None:
            async with aiosqlite.connect(DB_FILE) as db:
                current = await get_card_style(db, user_id)
            other = CARD_EMBED if current == CARD_IMAGE else CARD_IMAGE
            return await ctx.send(
                f"🖼️ Your profile is drawn as **{current}**.\n"
                f"Switch with `!settings card {other}`.")

        resolved, complaint = resolve_card_style(style)
        if not resolved:
            # `!settings card apex` is the spelling people reach for, because "the card"
            # is the thing they are changing either way. The two vocabularies do not
            # overlap - no sector is called `image` and no style is called `trench` - so
            # handing a sector word over is unambiguous, and refusing it on a
            # technicality would be pedantry about which noun the subcommand owns.
            biome, _ = resolve_biome_word(style)
            if biome:
                return await self.settings_biome(ctx, biome=style)
            return await ctx.send(complaint)

        async with aiosqlite.connect(DB_FILE) as db:
            stored = await set_card_style(db, user_id, resolved)
            await db.commit()

        if not stored:
            return await ctx.send(
                "⚠️ This database cannot store the preference yet, so it was not saved. "
                "Profiles stay on the rendered card for now.")

        extra = ("" if resolved == CARD_IMAGE else
                 "\n*The embed is plain text - selectable, screen-reader friendly, and "
                 "far smaller to send.*")
        return await ctx.send(f"🖼️ `!profile` will be drawn as **{resolved}**.{extra}")

    @settings.command(name="biome", aliases=["sector", "background", "bg"])
    @checks.has_started()
    async def settings_biome(self, ctx, *, biome: str = None):
        """
        Which sector your profile card is dressed in. `!settings biome apex`

        Gated on the visas you hold, which the Warden fights already write - so this
        adds a reward to progress that already happened rather than a new thing to
        grind. `!settings biome auto` hands the choice back to your deepest clearance,
        which is the default and keeps improving on its own.
        """
        user_id = str(ctx.author.id)

        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute(
                    "SELECT unlocked_visas FROM users WHERE user_id = ?",
                    (user_id,)) as cursor:
                row = await cursor.fetchone()
            stored = await get_card_biome(db, user_id)

        raw = (row[0] if row and row[0] else 'canopy')
        held = [b for b in BIOME_ORDER
                if b in {v.strip().lower() for v in str(raw).split(',')}]
        current = resolve_card_biome(stored, held)

        def roster():
            """Every sector, with the locked ones shown rather than hidden."""
            lines = []
            for key in BIOME_ORDER:
                if key not in held:
                    lines.append(f"🔒 ~~{biome_label(key)}~~ · *clear the Warden before it*")
                elif key == current:
                    lines.append(f"➤ **{biome_label(key)}** · in use")
                else:
                    lines.append(f"　{biome_label(key)}")
            return "\n".join(lines)

        # No argument SHOWS rather than guesses - the same rule `!settings timezone` and
        # `!settings card` follow. It is also the only place a trainer can see how many
        # sectors are still locked, which is half of why the locked ones are listed.
        if biome is None:
            following = ("*Following your deepest clearance.*" if not stored else
                         f"*You chose this one. `!settings biome auto` follows your "
                         f"deepest clearance instead.*")
            embed = discord.Embed(
                title="🗺️ Card Sector",
                description=f"{roster()}\n\n{following}",
                colour=discord.Colour.blurple())
            embed.set_footer(text="!settings biome <sector>  ·  !settings biome auto")
            return await ctx.send(embed=embed)

        chosen, complaint = resolve_biome_word(biome)
        if complaint:
            return await ctx.send(complaint)

        # THE VISA CHECK LIVES HERE, not in `set_card_biome`, because this is the only
        # place that can say WHY - and "you have not cleared Apex" is a different answer
        # from "Apex is not a sector", which is the mistake somebody is far more likely
        # to have made.
        if chosen and chosen not in held:
            return await ctx.send(
                f"🔒 You have not cleared **{biome_label(chosen)}** yet, so your card "
                f"cannot wear it. Beat the Warden guarding it and it unlocks here "
                f"automatically.\n\n{roster()}")

        async with aiosqlite.connect(DB_FILE) as db:
            saved = await set_card_biome(db, user_id, chosen)
            await db.commit()

        if not saved:
            return await ctx.send(
                "⚠️ This database cannot store the preference yet, so it was not saved. "
                "Your card still follows your deepest clearance.")

        if chosen == CARD_BIOME_AUTO:
            return await ctx.send(
                f"🗺️ Your card follows your deepest clearance again — currently "
                f"**{biome_label(resolve_card_biome(CARD_BIOME_AUTO, held))}**.")
        return await ctx.send(
            f"🗺️ Your profile card is now dressed in **{biome_label(chosen)}**. "
            f"Run `!profile` to see it.")

    @settings.command(name="timezone", aliases=["tz", "time"])
    @checks.has_started()
    async def settings_timezone(self, ctx, *, zone: str = None):
        """
        Set the clock your day/night evolutions are read off.

        `!settings timezone Europe/London`, `!settings timezone new york`, or an
        abbreviation like `PST`. `!settings timezone reset` hands you back to the
        server's clock.
        """
        user_id = str(ctx.author.id)
        guild_id = ctx.guild.id if ctx.guild else None

        # No argument READS it back rather than guessing. Same rule `!notify` follows:
        # changing an unseen setting is how people end up somewhere they did not intend.
        if zone is None:
            async with aiosqlite.connect(DB_FILE) as db:
                current, source = await resolve_timezone(db, user_id, guild_id)
            skies = current_skies(now_in(current))
            origin = {SOURCE_USER: "Your own setting.",
                      SOURCE_GUILD: "Inherited from this server - you have not set one.",
                      SOURCE_DEFAULT: "The default - you have not set one."}[source]
            examples = ", ".join(f"`{z}`" for z in COMMON_ZONES[:6])
            return await ctx.send(
                f"🕒 **{describe_zone(current)}**\n"
                f"*{origin}* It is currently **{'/'.join(sorted(skies))}** for you.\n\n"
                f"Change it with `!settings timezone <zone>` - {examples}.")

        if zone.strip().lower() in ('reset', 'clear', 'default', 'none', 'unset'):
            async with aiosqlite.connect(DB_FILE) as db:
                await clear_timezone(db, user_id)
                await db.commit()
                fallback, source = await resolve_timezone(db, user_id, guild_id)
            return await ctx.send(
                f"🕒 Cleared. Your clock falls back to **{describe_zone(fallback)}**"
                f"{' (this server)' if source == SOURCE_GUILD else ''}.")

        resolved, complaint, suggestions = resolve_zone(zone)
        if not resolved:
            hint = ""
            if suggestions:
                hint = "\n\nDid you mean: " + " · ".join(f"`{s}`" for s in suggestions)
            return await ctx.send(f"{complaint}{hint}")

        async with aiosqlite.connect(DB_FILE) as db:
            stored = await set_timezone(db, user_id, resolved)
            await db.commit()

        if not stored:
            return await ctx.send(
                "⚠️ This database cannot store a timezone yet, so the setting was not "
                "saved. Day and night stay on UTC for now.")

        skies = current_skies(now_in(resolved))
        note = ""
        if resolved.startswith('Etc/GMT'):
            # They gave a raw offset. It works, and it will be wrong for half the year
            # if their country changes its clocks - worth saying once, at the moment
            # they choose it, rather than in a bug report next spring.
            note = ("\n⚠️ That is a fixed offset, so it will not follow daylight saving. "
                    "A place name such as `Europe/London` handles the clock change for "
                    "you.")
        await ctx.send(
            f"🕒 Timezone set to **{describe_zone(resolved)}**.\n"
            f"It is **{'/'.join(sorted(skies))}** for you, so time-gated evolutions "
            f"will read it that way.{note}")

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
        # Disclosed even though there is nothing personal in it, because "we count how
        # often each command runs" is exactly the sort of thing a player would rather
        # read here than discover. The absence of attribution is the interesting half,
        # so it is stated plainly rather than left to be inferred from silence.
        embed.add_field(
            name="What is counted but not attributed",
            value=("How many times each command is run, as a running total per command. "
                   "**No user is recorded against these** — the table has no column for "
                   "one — so they say what the bot is used for and nothing about who "
                   "used it."),
            inline=False)
        embed.add_field(
            name="How long trade records are kept",
            value=(f"Every transfer — gift, trade, GTS, market — is recorded so that "
                   f"duplication bugs and disputed trades can be reconstructed. Those "
                   f"records are deleted after **{LOG_RETENTION_DAYS} days**. "
                   f"Erasing your account "
                   f"takes your name off yours straight away; the record itself stays, "
                   f"because it is also the other trainer's evidence of a trade they "
                   f"made."),
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
        embed.add_field(
            name="Being contacted",
            value="`!notify off` stops level-up announcements. They never ping or "
                  "reply to you either way. Battle and trade requests from other "
                  "players still mention you — that is how you are told about them.",
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
