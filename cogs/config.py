"""One `!config` command with a menu, rather than fifteen commands nobody finds.

The settings themselves - what they are, what they default to, what they will accept -
live in `utils/guild_config.py`. This file is the front door: a panel that shows a server
what it is currently doing, and the controls to change it.

Three things it is careful about:

**A fresh install must work with nothing configured.** Every default is a working value,
so `!config` is for servers that want something different, never a step before the bot
does anything.

**The channel restriction cannot lock anybody out.** `!config` itself is always allowed,
anyone who can manage the server is always allowed, and an empty list means everywhere.
An admin who restricts commands to a channel they then delete has not bricked the bot.

**Every change is logged.** Not for suspicion - for the moment somebody asks why spawns
stopped, and the honest answer is a name and a timestamp rather than a guess.
"""
import discord
from discord.ext import commands

from utils import audit, guild_config as cfg


def can_configure(member):
    """Whether this member may change server settings. Manage Server, as advised."""
    perms = getattr(member, 'guild_permissions', None)
    return bool(perms and (perms.manage_guild or perms.administrator))


async def render(guild):
    """The panel, as an embed. Read fresh every time so it reflects a change at once."""
    values = await cfg.get_all(guild.id)

    embed = discord.Embed(
        title=f"⚙️ Settings · {guild.name}",
        description="Pick a setting below to change it. Anything left alone follows the "
                    "default, which is a working value.",
        colour=discord.Colour.blurple())

    for group in cfg.GROUPS:
        lines = []
        for key, setting in cfg.SETTINGS.items():
            if setting.group != group:
                continue
            shown = cfg.describe(key, values.get(key), guild)
            default_note = "" if not await cfg.is_default(guild.id, key) else " *(default)*"
            lines.append(f"{setting.emoji} **{setting.label}** — {shown}{default_note}")
        if lines:
            embed.add_field(name=group, value="\n".join(lines), inline=False)

    embed.set_footer(text="!config set <setting> <value> · !config reset")
    return embed


class SettingSelect(discord.ui.Select):
    """The list of settings. Eleven of them, comfortably inside Discord's 25."""

    def __init__(self, panel):
        self.panel = panel
        options = [
            discord.SelectOption(label=s.label, value=key, emoji=s.emoji,
                                 description=s.description[:100])
            for key, s in cfg.SETTINGS.items()
        ]
        super().__init__(placeholder="Change a setting…", options=options, row=0)

    async def callback(self, interaction):
        key = self.values[0]
        setting = cfg.SETTINGS[key]

        # A switch has exactly two states, so making somebody pick one from a second
        # menu would be a click spent saying what they already said.
        if setting.kind == cfg.BOOL:
            current = await cfg.get(interaction.guild.id, key)
            return await self.panel.apply(interaction, key, not current)

        if setting.kind in (cfg.CHANNEL, cfg.CHANNEL_LIST, cfg.ROLE):
            view = PickerView(self.panel, key)
            return await interaction.response.send_message(
                f"Choose a value for **{setting.label}**.", view=view, ephemeral=True)

        await interaction.response.send_modal(ValueModal(self.panel, key))


class ValueModal(discord.ui.Modal):
    """For the settings that are a number or a piece of text."""

    def __init__(self, panel, key):
        self.panel = panel
        self.key = key
        setting = cfg.SETTINGS[key]
        super().__init__(title=setting.label[:45])

        bounds = ""
        if setting.minimum is not None:
            bounds = f" ({setting.minimum}–{setting.maximum})"

        self.field = discord.ui.TextInput(
            label=f"New value{bounds}"[:45],
            placeholder=str(setting.default),
            required=False,
            max_length=100)
        self.add_item(self.field)

    async def on_submit(self, interaction):
        value, problem = cfg.coerce(self.key, self.field.value)
        if problem:
            return await interaction.response.send_message(problem, ephemeral=True)
        await self.panel.apply(interaction, self.key, value)


class PickerView(discord.ui.View):
    """A channel or role picker, in its own ephemeral message."""

    def __init__(self, panel, key):
        super().__init__(timeout=120)
        self.panel = panel
        self.key = key
        setting = cfg.SETTINGS[key]

        if setting.kind == cfg.ROLE:
            picker = discord.ui.RoleSelect(placeholder=f"Pick a role for {setting.label}")
        else:
            picker = discord.ui.ChannelSelect(
                placeholder=f"Pick a channel for {setting.label}",
                channel_types=[discord.ChannelType.text],
                max_values=10 if setting.kind == cfg.CHANNEL_LIST else 1)
        picker.callback = self.chosen
        self.picker = picker
        self.add_item(picker)

    async def chosen(self, interaction):
        setting = cfg.SETTINGS[self.key]
        picked = [item.id for item in self.picker.values]
        value = picked if setting.kind == cfg.CHANNEL_LIST else (picked[0] if picked else None)
        await self.panel.apply(interaction, self.key, value, ephemeral=True)

    @discord.ui.button(label="Clear it", style=discord.ButtonStyle.secondary, row=1)
    async def clear(self, interaction, button):
        await self.panel.apply(interaction, self.key, None, ephemeral=True)


class ConfigPanel(discord.ui.View):
    """The panel itself. Only the admin who opened it can drive it."""

    def __init__(self, bot, ctx):
        super().__init__(timeout=300)
        self.bot = bot
        self.ctx = ctx
        self.message = None
        self.add_item(SettingSelect(self))

    async def interaction_check(self, interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                "This panel belongs to whoever opened it. Run `!config` yourself.",
                ephemeral=True)
            return False
        if not can_configure(interaction.user):
            await interaction.response.send_message(
                "You need **Manage Server** to change these.", ephemeral=True)
            return False
        return True

    async def apply(self, interaction, key, value, ephemeral=False):
        """Store one value, redraw the panel, and record what happened."""
        setting = cfg.SETTINGS[key]
        before = cfg.describe(key, await cfg.get(interaction.guild.id, key),
                              interaction.guild)

        try:
            await cfg.set_value(interaction.guild.id, key, value)
        except Exception as e:
            print(f"Config write failed ({key}): {e}")
            return await interaction.response.send_message(
                "❌ That could not be saved. Nothing changed.", ephemeral=True)

        after = cfg.describe(key, await cfg.get(interaction.guild.id, key),
                             interaction.guild)

        note = f"⚙️ **{setting.label}**: {before} → {after}"
        if ephemeral:
            # The picker lives in its own ephemeral message, so the panel is a DIFFERENT
            # message and has to be redrawn by hand or it keeps showing the old value.
            await interaction.response.send_message(note, ephemeral=True)
            if self.message:
                try:
                    await self.message.edit(embed=await render(interaction.guild),
                                            view=self)
                except discord.HTTPException:
                    pass
        else:
            await interaction.response.edit_message(
                embed=await render(interaction.guild), view=self)

        await audit.post_config_change(
            self.bot, guild=interaction.guild, actor=interaction.user,
            label=setting.label, before=before, after=after)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class ResetConfirm(discord.ui.View):
    """`!config reset` asks first. Admins do break things, and also mistype."""

    def __init__(self, bot, ctx):
        super().__init__(timeout=60)
        self.bot = bot
        self.ctx = ctx

    async def interaction_check(self, interaction):
        return interaction.user.id == self.ctx.author.id

    @discord.ui.button(label="Reset everything", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction, button):
        await cfg.reset(interaction.guild.id)
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            content="♻️ Settings are back to their defaults. The habitat channel was "
                    "left alone — that one is what makes the bot work at all.",
            view=self)
        await audit.post_config_change(
            self.bot, guild=interaction.guild, actor=interaction.user,
            label="Everything", before="custom settings", after="defaults")

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction, button):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content="Nothing was changed.", view=self)


class Config(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.add_check(self.channel_is_allowed)

    def cog_unload(self):
        self.bot.remove_check(self.channel_is_allowed)

    # ==========================================
    # THE CHANNEL RESTRICTION
    # ==========================================
    async def channel_is_allowed(self, ctx):
        """
        A global check: commands only run where the server said they may.

        Written to fail OPEN. A server with nothing configured, a DM, a read that
        throws - all of them allow the command. The failure mode of a restriction that
        fails closed is a bot that has stopped working for reasons nobody can see.
        """
        if ctx.guild is None:
            return True
        # Never lock somebody out of the command that undoes the lock.
        if ctx.command and ctx.command.qualified_name.split()[0] == 'config':
            return True
        try:
            if can_configure(ctx.author) or await ctx.bot.is_owner(ctx.author):
                return True
            allowed = await cfg.get(ctx.guild.id, 'command_channels')
        except Exception as e:
            # `is_owner` can reach for the application info, and the config read opens
            # the database. Either can fail, and neither failure is a reason to start
            # refusing commands - a lock that fails closed is a bot that has silently
            # stopped working for reasons nobody can see from the outside.
            print(f"⚠️ Channel restriction check skipped: {e}")
            return True

        if not allowed or ctx.channel.id in allowed:
            return True

        rooms = " ".join(f"<#{c}>" for c in allowed[:5])
        await ctx.send(f"🔒 Bot commands are limited to {rooms} in this server.",
                       delete_after=15)
        return False

    # ==========================================
    # THE COMMAND
    # ==========================================
    @commands.group(name="config", aliases=["settings"],
                    invoke_without_command=True)
    @commands.guild_only()
    async def config(self, ctx):
        """[ADMIN] Shows and changes this server's settings."""
        if not can_configure(ctx.author):
            return await ctx.send("⚙️ You need **Manage Server** to change settings. "
                                  "`!config view` shows them without changing anything.")

        panel = ConfigPanel(self.bot, ctx)
        panel.message = await ctx.send(embed=await render(ctx.guild), view=panel)

    @config.command(name="view", aliases=["show", "list"])
    @commands.guild_only()
    async def config_view(self, ctx):
        """Shows this server's settings. Anyone may look."""
        await ctx.send(embed=await render(ctx.guild))

    @config.command(name="set")
    @commands.guild_only()
    async def config_set(self, ctx, key: str = None, *, value: str = None):
        """[ADMIN] Changes one setting. `!config set spawn_rate 25`"""
        if not can_configure(ctx.author):
            return await ctx.send("⚙️ You need **Manage Server** to change settings.")

        key = resolve_key(key)
        if key is None:
            names = ", ".join(f"`{k}`" for k in cfg.SETTINGS)
            return await ctx.send(f"⚙️ Which setting? One of: {names}.")

        setting = cfg.SETTINGS[key]
        parsed, problem = cfg.coerce(key, value)
        if problem:
            return await ctx.send(f"⚠️ {problem}")

        before = cfg.describe(key, await cfg.get(ctx.guild.id, key), ctx.guild)
        try:
            await cfg.set_value(ctx.guild.id, key, parsed)
        except Exception as e:
            print(f"Config write failed ({key}): {e}")
            return await ctx.send("❌ That could not be saved. Nothing changed.")

        after = cfg.describe(key, await cfg.get(ctx.guild.id, key), ctx.guild)
        await ctx.send(f"⚙️ **{setting.label}**: {before} → {after}")

        await audit.post_config_change(
            self.bot, guild=ctx.guild, actor=ctx.author,
            label=setting.label, before=before, after=after)

    @config.command(name="reset", aliases=["default", "defaults"])
    @commands.guild_only()
    async def config_reset(self, ctx):
        """[ADMIN] Puts every setting back to its default."""
        if not can_configure(ctx.author):
            return await ctx.send("⚙️ You need **Manage Server** to change settings.")
        await ctx.send(
            "♻️ Reset **every** setting to its default? The habitat channel is kept.",
            view=ResetConfirm(self.bot, ctx))


def resolve_key(typed):
    """`spawn rate`, `spawn_rate` and `Messages per spawn` all mean the same setting."""
    if not typed:
        return None
    wanted = ''.join(ch for ch in str(typed).lower() if ch.isalnum())
    for key, setting in cfg.SETTINGS.items():
        if wanted in (''.join(ch for ch in key if ch.isalnum()),
                      ''.join(ch for ch in setting.label.lower() if ch.isalnum())):
            return key
    return None


async def setup(bot):
    # The columns are added at load rather than by a migration somebody has to remember
    # to run. A new setting is then one entry in SETTINGS and a restart.
    import aiosqlite
    try:
        async with aiosqlite.connect(cfg.DB_FILE) as db:
            added = await cfg.ensure_schema(db)
        if added:
            print(f"⚙️ guild_config: added {len(added)} column(s): {', '.join(added)}")
    except Exception as e:
        print(f"⚠️ WARNING: could not prepare guild_config ({e}). Defaults will apply.")

    await bot.add_cog(Config(bot))
