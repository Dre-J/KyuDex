import discord
import asyncio
import time
from discord.ext import commands, tasks
import aiosqlite
import datetime
import random
import math
import uuid
from utils.constants import (DB_FILE, NATURES, CONSUMABLE_DATABASE, FIELD_MISSIONS,
                             STARTER_TOKENS, STARTER_ITEMS, STARTER_TMS,
                             STARTER_CAN_BE_SHINY, type_badges,
                             scaled_rarity, roll_shiny, ecosystem_multiplier,
                             SHINY_SCORE_CEILING, RARITY_SCORE_CEILING,
                             STARTER_IV_CEILING, OFFICIAL_BROADCAST_CHANNEL_ID,
                             SURVEY_EXCLUDES_RARE_SPECIES, spawnable_forms,
                             ultra_beasts, paradox_species,
                             HABITAT_RARITY, EXPEDITION_RARITY,
                             RARITY_LABELS, rarity_filter, roll_rarity,
                             pseudo_legendaries, is_pseudo_legendary,
                             MAX_ACTIVE_DIRECTIVES, MAX_NOTES_PER_ANALYSIS,
                             auto_tag, ALPHA_HEIGHT_THRESHOLD)
from utils.formulas import get_xp_requirement, get_planetary_cycle, calculate_real_stat, generate_biometrics, roll_gender, gender_icon, roll_starter_ivs
import re
from utils import checks
from utils.accounts import may_choose_starter, grant_starter_licence
from utils.trading import mark_as_starter
from utils.sprites import resolve_sprite, sprite_attachment_name, HOME
from utils import guild_config as cfg
from utils.embeds import rebind_image
from utils.directives import credit_evolution
# Every sprite path in this cog goes through utils.sprites now - the box browser, the
# wild spawns, the expedition encounter, the admin spawn and the catch confirmation.
# They were five hand-built copies of the same two lines, which is how none of them
# had ever heard of a female sprite.

# Memory dictionary to track what is currently spawned in each server
# Format: { 'guild_id': { spawn_id: {'pokedex_id': 1, 'name': 'bulbasaur',
#                                    'capture_rate': 45, 'channel_id': 123} } }
active_spawns = {}
MESSAGES_REQUIRED_FOR_SPAWN = 10
user_active_spawns = {} # Tracks private expedition encounters (Key: user_id)


# The tiers a server would want pulling out of a conversation for. A Wild Rattata is
# not one of them, and pinging a role for every spawn is the fastest way to be removed
# from a server - see suggestions.md, which is where this whole config layer came from.
NOTABLE_TIERS = ('MYTHICAL', 'LEGENDARY', 'PSEUDO', 'ULTRA BEAST')


def rare_spawn_alert(settings, rarity_name, is_shiny):
    """
    The role mention to put above a spawn card, or an empty string.

    Empty is the default and the failure mode: no role configured, the toggle off, or an
    ordinary specimen all produce nothing. Nothing here can ping @everyone, and the
    caller sets `allowed_mentions` regardless, so the silence is enforced twice.
    """
    settings = settings or {}
    role = settings.get('ping_role')
    if not role or not settings.get('ping_rare'):
        return ""
    notable = is_shiny or any(tier in str(rarity_name).upper() for tier in NOTABLE_TIERS)
    return f"<@&{role}> " if notable else ""


def event_alert(settings):
    """The role mention for a rift or a disaster, or an empty string."""
    settings = settings or {}
    role = settings.get('ping_role')
    return f"<@&{role}> " if role and settings.get('ping_events') else ""


# ==========================================
# 🎯 THE EXPEDITION CATCH PANEL
# ==========================================
# Buttons for expeditions ONLY. A public spawn keeps its name-guess, and the difference
# is not squeamishness about change - the two encounters are different situations:
#
# An expedition is private and deliberate. You ran a command, the encounter is assigned
# to you, nobody is competing for it. Making you then TYPE the name of something already
# yours is a toll booth on a road with nobody else on it.
#
# A channel spawn is contested, and the guess is doing three jobs at once. It is a race
# that rewards recognising the species rather than having Discord open. It paces a busy
# channel without any explicit cooldown, because typing is slower than clicking. And it
# is the small skill expression that makes a Pokemon bot feel like one - it is why
# anybody learns species names at all. Buttons on a public card would turn all of that
# into a click race that the person on the fastest connection wins.
#
# Fleeing is likewise expedition-only, and for a plainer reason: a public spawn belongs
# to the channel, so one person dismissing it would be taking it from everyone.

BALL_BUTTONS = (
    # key, label, emoji, whether it must be held in the pack
    ('pokeball',   'Poké Ball',   '⚪', False),
    ('greatball',  'Great Ball',  '🔵', True),
    ('ultraball',  'Ultra Ball',  '🟡', True),
    ('masterball', 'Master Ball', '🟣', True),
)

# A Poke Ball is free and unlimited everywhere else in the bot, so its button is never
# disabled and never carries a count.
FREE_BALL = 'pokeball'


class _ButtonContext:
    """
    Enough of a `commands.Context` for `!catch` to run from a button press.

    The alternative was a second copy of the capture logic - four hundred lines with
    the genetics roll, the biometrics, the directive progress, the loot table and the
    global broadcast in it - which would have drifted from the typed command by the end
    of the week. The button is a shortcut for typing the command, so it types it.
    """

    def __init__(self, interaction, bot):
        self.author = interaction.user
        self.guild = interaction.guild
        self.channel = interaction.channel
        self.bot = bot
        self.interaction = interaction
        self.sent = []

    async def send(self, content=None, **kwargs):
        # `reference` and `mention_author` are Message-only; a followup rejects them.
        for unsupported in ('reference', 'mention_author', 'delete_after', 'nonce'):
            kwargs.pop(unsupported, None)
        self.sent.append((content, kwargs))
        return await self.interaction.followup.send(content=content, **kwargs)


class EncounterButton(
        discord.ui.DynamicItem[discord.ui.Button],
        template=r'kyuexp:(?P<owner>\d+):(?P<spawn>[0-9a-fA-F-]+):(?P<action>[a-z]+)'):
    """
    One button on an expedition card, rebuildable from its own custom_id.

    A plain View dies with the process. The spawn it refers to dies with the process
    too - it lives in `user_active_spawns`, in memory - so after a restart the card is
    stale either way. The difference is what the player SEES when they click it: a
    dead View gets no handler at all and Discord shows "This interaction failed", which
    reads as a broken bot. Rebuilt from the custom_id, the click gets a handler that
    can look, find nothing, and say the encounter is over.
    """

    def __init__(self, owner_id, spawn_id, action, *, label=None, emoji=None,
                 style=discord.ButtonStyle.secondary, disabled=False, count=None):
        self.owner_id = str(owner_id)
        self.spawn_id = str(spawn_id)
        self.action = action

        if label is None:
            label = self._default_label(action, count)

        super().__init__(discord.ui.Button(
            label=label,
            emoji=emoji or self._default_emoji(action),
            style=style,
            disabled=disabled,
            custom_id=f"kyuexp:{owner_id}:{spawn_id}:{action}",
        ))

    @staticmethod
    def _default_emoji(action):
        if action == 'flee':
            return '🏃'
        return next((e for key, _, e, _ in BALL_BUTTONS if key == action), '⚪')

    @staticmethod
    def _default_label(action, count):
        if action == 'flee':
            return 'Leave it'
        name = next((n for key, n, _, _ in BALL_BUTTONS if key == action), action.title())
        # The count is on the button because the alternative is opening `!backpack`
        # mid-encounter to find out whether you can afford the throw you are about to
        # make. A free ball has no count to show.
        return name if count is None else f"{name} ({count})"

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(match['owner'], match['spawn'], match['action'])

    async def interaction_check(self, interaction):
        # A private encounter in a public channel. Without this, anybody scrolling past
        # can catch somebody else's expedition.
        if str(interaction.user.id) != self.owner_id:
            await interaction.response.send_message(
                "🔒 This is not your encounter — run `!expedition` for one of your own.",
                ephemeral=True)
            return False
        return True

    async def callback(self, interaction):
        cog = interaction.client.get_cog('Ecology')
        if cog is None:                                       # pragma: no cover
            return await interaction.response.send_message(
                "⚠️ The field systems are offline. Try again in a moment.",
                ephemeral=True)

        # A catch is a database write and possibly a sprite render, both of which can
        # outlast the three-second interaction deadline.
        await interaction.response.defer()

        spawn = (user_active_spawns.get(self.owner_id) or {}).get(self.spawn_id)
        if not spawn:
            # Taken, timed out, or lost to a restart. All three read the same to the
            # person clicking, and all three are answered by retiring the card.
            await self._retire(interaction, "💨 That encounter is over.")
            return await interaction.followup.send(
                "💨 That specimen is no longer here. Run `!expedition` to find another.",
                ephemeral=True)

        if self.action == 'flee':
            user_active_spawns.get(self.owner_id, {}).pop(self.spawn_id, None)
            clean = str(spawn.get('name', 'specimen')).replace('-', ' ').title()
            # Costs nothing and takes nothing. This is the legitimate way to pass on an
            # encounter rather than burning a ball or letting the card rot.
            await self._retire(
                interaction,
                f"🏃 You left the **{clean}** alone. It watches you go.")
            return

        ctx = _ButtonContext(interaction, cog.bot)
        await Ecology.catch_pokemon.callback(
            cog, ctx, full_input=f"{spawn['name']} {self.action}")

        # Whether the specimen survived the throw decides whether the panel should stay.
        # `!catch` removes it from the store on a catch AND on a flee-after-break-free,
        # so "still there" is exactly "you may throw again".
        still_there = (user_active_spawns.get(self.owner_id) or {}).get(self.spawn_id)
        if not still_there:
            await self._retire(interaction, None)
        else:
            await self._refresh(interaction)

    async def _retire(self, interaction, note):
        """
        Take the panel down, and say why ONLY when nothing else has.

        `interaction.message` is a snapshot taken when the click arrived. A catch
        rewrites the card to "Specimen Secured" while this handler is still running, so
        writing that snapshot's embed back afterwards restored the old spawn card -
        picture and all - directly over the result. The card was edited twice and the
        second edit won.

        So a note is written only when this is the one thing rewriting the card, and
        `note=None` means "somebody else already did, just take the buttons off".
        """
        try:
            message = interaction.message
            if message is None:
                return

            if note is None:
                # Touches the components and nothing else, so it cannot overwrite an
                # edit made from under us.
                return await message.edit(view=None)

            embed = message.embeds[0] if message.embeds else None
            if embed is None:
                return await message.edit(view=None)

            embed.description = note
            embed.colour = discord.Colour.dark_grey()
            keep = rebind_image(embed, message)
            await message.edit(embed=embed, attachments=keep, view=None)
        except Exception as e:
            print(f"⚠️ Could not retire the encounter panel: {e}")

    async def _refresh(self, interaction):
        """Redraw the counts after a ball was spent and the specimen stayed."""
        try:
            view = await build_encounter_view(self.owner_id, self.spawn_id)
            await interaction.message.edit(view=view)
        except Exception as e:
            print(f"⚠️ Could not refresh the encounter panel: {e}")


async def ball_counts(user_id):
    """How many of each purchasable ball this trainer holds."""
    wanted = [key for key, _, _, needed in BALL_BUTTONS if needed]
    marks = ','.join('?' * len(wanted))
    try:
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute(
                    f"SELECT item_name, quantity FROM user_inventory "
                    f"WHERE user_id = ? AND item_name IN ({marks})",
                    (str(user_id), *wanted)) as cursor:
                return {row[0]: row[1] for row in await cursor.fetchall()}
    except Exception as e:
        # A panel with every ball greyed out is a worse panel, not a broken one.
        print(f"⚠️ Could not read ball counts: {e}")
        return {}


async def build_encounter_view(owner_id, spawn_id, timeout=None):
    """
    The catch panel for one private encounter.

    Balls you do not hold are DISABLED rather than hidden, so the shape of the panel is
    the same every time and people learn what exists - a Master Ball button that only
    appears once you own one is a mechanic nobody discovers.
    """
    counts = await ball_counts(owner_id)

    view = discord.ui.View(timeout=timeout)
    for key, _label, _emoji, needed in BALL_BUTTONS:
        held = counts.get(key, 0)
        view.add_item(EncounterButton(
            owner_id, spawn_id, key,
            count=None if key == FREE_BALL else held,
            disabled=bool(needed and held < 1),
            style=(discord.ButtonStyle.primary if key == FREE_BALL
                   else discord.ButtonStyle.secondary)))

    view.add_item(EncounterButton(owner_id, spawn_id, 'flee',
                                  style=discord.ButtonStyle.danger))
    return view


async def rewrite_spawn_card(bot, spawn, title, description, colour=None):
    """
    Rewrite a spawn's own message in place, and take any buttons off it.

    The shared half of "this specimen is no longer available". Both the catch and the
    escape need it, and both used to be free to forget - a card for a specimen taken or
    lost minutes ago sat in the channel advertising it indefinitely.

    Every failure is swallowed on purpose. The message may have been deleted, the bot
    may have lost permission to edit in that channel, or the spawn may predate this and
    carry no message id at all. None of those is a reason for a successful catch to
    report an error to the person who made it.
    """
    channel_id = (spawn or {}).get('channel_id')
    message_id = (spawn or {}).get('message_id')
    if not channel_id or not message_id or bot is None:
        return False

    try:
        channel = bot.get_channel(int(channel_id))
        if channel is None:
            return False
        message = await channel.fetch_message(int(message_id))

        embed = message.embeds[0] if message.embeds else discord.Embed()
        embed.title = title
        embed.description = description
        embed.colour = colour or discord.Colour.dark_grey()

        # The sprite stays. The card is a record of what appeared, and stripping the
        # picture would make the channel history less readable rather than more.
        #
        # It has to be rebound by NAME, though. This embed came back from
        # `fetch_message` with its image url set to a signed CDN link, and editing
        # re-issues the attachment under a new signature - so the picture fell out of
        # the embed and reappeared as a bare file hanging underneath it.
        #
        # `view=None` strips the buttons. An expedition card carries a catch panel, and
        # leaving it live on a specimen nobody can have means the next click gets
        # "there is no Charmander here" from a card that plainly shows one.
        keep = rebind_image(embed, message)
        await message.edit(embed=embed, attachments=keep, view=None)
        return True
    except Exception as e:
        print(f"⚠️ Could not rewrite spawn card: {e}")
        return False


async def mark_spawn_fled(bot, spawn, species_name):
    """The card for a specimen that broke free and ran."""
    clean = str(species_name).replace('-', ' ').title()
    return await rewrite_spawn_card(
        bot, spawn, "💨 Specimen Escaped",
        f"The **{clean}** broke free and disappeared into the undergrowth.")


async def mark_spawn_caught(bot, spawn, catcher, species_name, is_shiny, tag=None):
    """
    Edit a spawn's own message to say it has been taken, and by whom.

    Until this, a caught spawn left its card in the channel unchanged. The despawn timer
    is the only thing that ever rewrote one, and it declines to touch a specimen that is
    no longer in memory - correctly, since it must not overwrite a catch - so the card
    for a specimen somebody took minutes ago sat there advertising it indefinitely.

    The rewriting itself is `rewrite_spawn_card`, shared with the escape - the two used
    to be one function and a gap where the other should have been.
    """
    clean = str(species_name).replace('-', ' ').title()
    badge = "🌟 " if is_shiny else ""
    return await rewrite_spawn_card(
        bot, spawn, "✅ Specimen Secured",
        f"The {badge}**{clean}** was tagged and rehomed by **{catcher}**."
        + (f"\n*Filed under* `{tag}`." if tag else ""))


def spawn_is_here(spawn_data, channel_id):
    """
    Whether this specimen may be caught from the channel the command was typed in.

    A spawn is a MESSAGE, with a picture and a masked name, sitting in one channel.
    Without this it could be caught from anywhere in the server, so anyone watching
    the habitat channel could read the answer and type `!catch` somewhere quiet -
    and, worse, a player in an unrelated channel would silently take the specimen out
    from under the people actually looking at it. The encounter and the catch belong
    in the same room.

    A spawn carrying no channel at all is catchable anywhere. That is the same guarded
    degradation used for every new column in this codebase: an encounter created before
    this existed - one already on screen when the bot was restarted into this build -
    keeps working rather than becoming permanently uncatchable.
    """
    home = spawn_data.get('channel_id')
    return home is None or home == channel_id

class EvolutionConfirmView(discord.ui.View):
    def __init__(self, owner_id: int, instance_id: str, new_pokedex_id: int, new_species_name: str, new_ability: str, db_file: str):
        super().__init__(timeout=60)
        self.owner_id = owner_id
        self.instance_id = instance_id
        self.new_pokedex_id = new_pokedex_id
        self.new_species_name = new_species_name
        self.new_ability = new_ability # Store the inherited trait!
        self.db_file = db_file

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if hasattr(self, 'message') and self.message:
            await self.message.edit(content="⏳ **Evolution window expired.** You can trigger it again next level.", view=self)

    @discord.ui.button(label="🧬 Trigger Evolution", style=discord.ButtonStyle.success)
    async def evolve_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            return await interaction.response.send_message("⚠️ You cannot evolve another researcher's specimen.", ephemeral=True)

        async with aiosqlite.connect(self.db_file) as db:
            # The species it is evolving FROM, read before the update overwrites it. A
            # Kinetic Maturation Study names the species you had to go and find, not
            # the one you ended up with.
            async with db.execute(
                    "SELECT s.name FROM caught_pokemon cp "
                    "JOIN base_pokemon_species s ON s.pokedex_id = cp.pokedex_id "
                    "WHERE cp.instance_id = ?", (self.instance_id,)) as cursor:
                row = await cursor.fetchone()
            old_name = row[0] if row else ''

            # 🚨 UPDATE: Apply both the new species ID and the inherited ability
            await db.execute("UPDATE caught_pokemon SET pokedex_id = ?, ability = ? WHERE instance_id = ?",
                             (self.new_pokedex_id, self.new_ability, self.instance_id))

            # THE GAP: this button is the third door an evolution can come through, and
            # the only one that never credited the directive. A trainer who evolved a
            # specimen off the back of a field mission watched their Kinetic Maturation
            # Study sit at 0/1 while the same evolution through `!evolve` counted.
            _, finished = await credit_evolution(db, self.owner_id, old_name)

            await db.commit()

        for child in self.children:
            child.disabled = True

        note = ("\n\n📡 **Directive Complete:** Kinetic Maturation Study concluded! "
                "Run `!claim` to receive your funding." if finished else "")
        await interaction.response.edit_message(
            content=f"🎉 **Success!** The specimen successfully evolved into **{self.new_species_name}** with the ability **{self.new_ability.title()}**!{note}",
            view=self
        )

    @discord.ui.button(label="🛑 Cancel", style=discord.ButtonStyle.danger)
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            return await interaction.response.send_message("⚠️ You cannot interact with this menu.", ephemeral=True)

        for child in self.children:
            child.disabled = True
            
        await interaction.response.edit_message(
            content="Evolution canceled. The specimen's biological structure remains unchanged.", 
            view=self
        )

class ReturnMissionsView(discord.ui.View):
    def __init__(self, cog, user_id, active_missions):
        super().__init__(timeout=60)
        self.cog = cog
        self.user_id = user_id
        
        # active_missions is a list of tuples from the database: [('reef', 3), ('hp', 1)]
        for mission_id, count in active_missions:
            # Grab the pretty name from your FIELD_MISSIONS dictionary
            mission_data = FIELD_MISSIONS.get(mission_id, {})
            mission_name = mission_data.get("name", mission_id.capitalize())
            
            # Create a button for this specific mission
            btn = discord.ui.Button(
                label=f"{mission_name} ({count} Deployed)",
                style=discord.ButtonStyle.primary,
                custom_id=f"return_{mission_id}"
            )
            # Bind the callback to pass the specific mission_id
            btn.callback = self.make_callback(mission_id)
            self.add_item(btn)
            
        # Always add a convenient "Recall All" button at the bottom
        all_btn = discord.ui.Button(label="Recall All Teams", style=discord.ButtonStyle.success, row=2)
        all_btn.callback = self.make_callback("all")
        self.add_item(all_btn)

    def make_callback(self, target_mission):
        """Creates a unique callback for each button so we know which one was clicked."""
        async def callback(interaction: discord.Interaction):
            # 1. Disable all buttons immediately so they can't double-click and crash the DB
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(view=self)
            
            # 2. Route to the heavy-lifting function in the Cog!
            await self.cog.execute_return_logic(interaction, self.user_id, target_mission)
            
        return callback
    
class StarterSelect(discord.ui.Select):
    def __init__(self, region: str):
        self.region = region
        
        # Define the ecological starters by region
        starters = {
            'Kanto': [('Bulbasaur', '1', '🌿 Grass/Poison'), ('Charmander', '4', '🔥 Fire'), ('Squirtle', '7', '💧 Water')],
            'Johto': [('Chikorita', '152', '🌿 Grass'), ('Cyndaquil', '155', '🔥 Fire'), ('Totodile', '158', '💧 Water')],
            # 258 is Mudkip. This row said 'Totodile', so the Hoenn water starter was
            # offered under the Johto one's name while handing over the right species.
            'Hoenn': [('Treecko', '252', '🌿 Grass'), ('Torchic', '255', '🔥 Fire'), ('Mudkip', '258', '💧 Water')],
            'Sinnoh': [('Turtwig', '387', '🌿 Grass'), ('Chimchar', '390', '🔥 Fire'), ('Piplup', '393', '💧 Water')],
            'Unova': [('Snivy', '495', '🌿 Grass'), ('Tepig', '498', '🔥 Fire'), ('Oshawott', '501', '💧 Water')],
            'Kalos': [('Chespin', '650', '🌿 Grass'), ('Fennekin', '653', '🔥 Fire'), ('Froakie', '656', '💧 Water')],
            'Alola': [('Rowlet', '722', '🌿 Grass'), ('Litten', '725', '🔥 Fire'), ('Popplio', '728', '💧 Water')],
            'Galar': [('Grookey', '810', '🌿 Grass'), ('Scorbunny', '813', '🔥 Fire'), ('Sobble', '816', '💧 Water')],
            'Paldea': [('Sprigatito', '906', '🌿 Grass'), ('Fuecoco', '909', '🔥 Fire'), ('Quaxly', '912', '💧 Water')]
            # You can easily add Hoenn, Sinnoh, etc., right here!
        }
        
        options = [
            discord.SelectOption(label=name, value=p_id, description=desc)
            for name, p_id, desc in starters.get(region, [])
        ]
        
        super().__init__(placeholder=f"Select your {region} partner...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        pokedex_id = int(self.values[0])
        species_name = next(opt.label for opt in self.options if str(opt.value) == str(pokedex_id))
        user_id = str(interaction.user.id)
        
        # Generate a unique biological tag for this specific instance
        instance_id = str(uuid.uuid4()) 
        
        try:
            async with aiosqlite.connect(DB_FILE) as db:
                # ==========================================
                # 1. CREATE THE RESEARCHER PROFILE
                # ==========================================
                # Asked again here, not just in !start. The menu is a message that
                # keeps working after it is sent, so without this a trainer could hold
                # one open, pick a starter, and pick a second one from the same message.
                allowed, reason = await may_choose_starter(db, user_id)
                if not allowed:
                    return await interaction.response.edit_message(
                        content="⚠️ You already have a partner registered to your "
                                "licence. Use `!reset` if you want to start over.",
                        view=None)

                # Registers a new licence or re-equips a reset one, and hands over the
                # onboarding kit. A handful of Great Balls: Poke Balls are free and
                # unlimited, so the first catch was never blocked - what a new trainer
                # lacked was the first upgrade, at zero tokens.
                await grant_starter_licence(db, user_id, STARTER_TOKENS, STARTER_ITEMS,
                                            STARTER_TMS)

                # ==========================================
                # 2. GENERATE THE BIOLOGICAL SPECIMEN
                # ==========================================
                # Roll genetics and traits
                # A guaranteed floor rather than a free roll - see STARTER_PERFECT_IVS.
                # The starter is the specimen people name and keep, and it is the one
                # roll a trainer has no chance to do anything about.
                ivs = roll_starter_ivs()
                nature = random.choice(NATURES)

                # Never shiny. A shiny starter makes every reset a slot machine, and
                # no cooldown fully answers a slot machine.
                is_shiny = 1 if STARTER_CAN_BE_SHINY and random.randint(1, 4096) == 1 else 0
                
                # ==========================================
                # FETCH THE SPECIES' ABILITY & GENDER RATE
                # ==========================================
                # 🚨 UPDATED: Grabbing gender_rate in the same query!
                async with db.execute("SELECT standard_abilities, gender_rate, name FROM base_pokemon_species WHERE pokedex_id = ?", (pokedex_id,)) as cursor:
                    ability_row = await cursor.fetchone()
                
                species_name = None
                if ability_row:
                    raw_ability, raw_gender_rate, species_name = ability_row
                    
                    if raw_ability:
                        ability = raw_ability.split(',')[0].strip()
                    else:
                        ability = 'overgrow' # Safe fallback
                        
                    gender_rate = raw_gender_rate if raw_gender_rate is not None else 4
                else:
                    ability = 'overgrow'
                    gender_rate = 4 

                # --- GENDER ROLL ---
                gender = roll_gender(gender_rate, species_name=species_name)
                
                # Fetch Level 1-5 starting moves
                async with db.execute("""
                    SELECT move_name FROM species_movepool 
                    WHERE pokedex_id = ? AND learn_method = 'level-up' AND level_learned <= 5
                    ORDER BY level_learned DESC LIMIT 4
                """, (pokedex_id,)) as cursor:
                    moves = [row[0] for row in await cursor.fetchall()]
                
                # Pad empty move slots with 'none'
                while len(moves) < 4:
                    moves.append('none')
                    
                # Insert the specimen into the global wildlife database
                # 🚨 UPDATED: Added original_user_id and gender to the schema and values!
                await db.execute("""
                    INSERT INTO caught_pokemon (
                        instance_id, user_id, original_user_id, pokedex_id, level, experience, nature, is_shiny, ability, gender,
                        iv_hp, iv_attack, iv_defense, iv_sp_atk, iv_sp_def, iv_speed,
                        ev_hp, ev_attack, ev_defense, ev_sp_atk, ev_sp_def, ev_speed,
                        move_1, move_2, move_3, move_4, held_item, gmax_factor
                    ) VALUES (
                        ?, ?, ?, ?, 5, 0, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?,
                        0, 0, 0, 0, 0, 0,
                        ?, ?, ?, ?, 'none', 0
                    )
                """, (
                    instance_id, user_id, user_id, pokedex_id, nature, is_shiny, ability, gender,
                    ivs['hp'], ivs['attack'], ivs['defense'], ivs['sp_atk'], ivs['sp_def'], ivs['speed'],
                    moves[0], moves[1], moves[2], moves[3]
                ))
                
                # Marked as the starter, which is what makes it non-tradeable. Written
                # as a follow-up UPDATE rather than a column in the INSERT above so
                # that registration still works on a database where the trade-ledger
                # migration has not been run - the same way every other new column in
                # this codebase is read.
                await mark_as_starter(db, instance_id)

                # ==========================================
                # 3. ASSIGN THE TACTICAL ROSTER
                # ==========================================
                # Assign to Slot 1 in the party
                await db.execute("INSERT INTO user_party (user_id, instance_id, slot) VALUES (?, ?, 1)", (user_id, instance_id))
                
                # Set this specific specimen as their active follower/partner
                await db.execute("UPDATE users SET active_partner = ? WHERE user_id = ?", (instance_id, user_id))
                
                # Commit the entire transaction to the database
                await db.commit()
            
            shiny_icon = "✨ " if is_shiny else ""
            perfect = sum(1 for value in ivs.values() if value == STARTER_IV_CEILING)
            kit = ", ".join(f"{qty}x {name.replace('-', ' ').title()}"
                            for name, qty in STARTER_ITEMS.items())
            machines = ", ".join(m.replace('-', ' ').title() for m in STARTER_TMS)
            await interaction.response.edit_message(
                content=(f"🎉 **Registration Complete!**\n\nYou have secured your field "
                         f"license. Your new symbiotic partner, {shiny_icon}**{species_name}**, "
                         f"has been registered to your roster with **{perfect} perfect "
                         f"genetic markers** — every starter is issued screened stock.\n\n"
                         f"🎒 **Starter kit:** 🪙 {STARTER_TOKENS:,} Eco Tokens, {kit}\n"
                         f"💿 **Starter TMs:** {machines}\n"
                         f"*TMs are permanent — teach one with `!learn protect`, then "
                         f"teach it again to something else. `!tmshop` has 340 more.*\n\n"
                         f"Use `!profile` to view your clearance or `!expedition canopy` "
                         f"to begin your research!"),
                view=None
            )
            
        except aiosqlite.IntegrityError:
            # This catches the edge case where they somehow run the command twice at the exact same time
            await interaction.response.edit_message(content="⚠️ Registration failed: You are already in the database.", view=None)
        except Exception as e:
            print(f"Starter Registration Error: {e}")
            await interaction.response.edit_message(content="❌ A critical database error occurred during registration. Please contact a developer.", view=None)


class RegionSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Kanto", description="Gen 1: Bulbasaur, Charmander, Squirtle", emoji="🟡"),
            discord.SelectOption(label="Johto", description="Gen 2: Chikorita, Cyndaquil, Totodile", emoji="🟡"),
            discord.SelectOption(label="Hoenn", description="Gen 3: Treecko, Torchic, Mudkip", emoji="🟡"),
            discord.SelectOption(label="Sinnoh", description="Gen 4: Turtwig, Chimchar, Piplup", emoji="🟡"),
            discord.SelectOption(label="Unova", description="Gen 5: Snivy, Tepig, Oshawott", emoji="🟡"),
            discord.SelectOption(label="Kalos", description="Gen 6: Chespin, Fennekin, Froakie", emoji="🟡"),
            discord.SelectOption(label="Alola", description="Gen 7: Rowlet, Litten, Popplio", emoji="🟡"),
            discord.SelectOption(label="Galar", description="Gen 8: Grookey, Scorbunny, Sobble", emoji="🟡"),
            discord.SelectOption(label="Paldea", description="Gen 9: Sprigatito, Fuecoco, Quaxly", emoji="🟡"),
        ]
        super().__init__(placeholder="Choose a research region...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_region = self.values[0]
        
        # Create a new view with the Starter select menu for that specific region!
        view = discord.ui.View()
        view.add_item(StarterSelect(selected_region))
        
        await interaction.response.edit_message(content=f"You selected **{selected_region}**. Now, choose your starting specimen:", view=view)

class ReleaseConfirmView(discord.ui.View):
    def __init__(self, ctx, db_file, pokemon_data, user_id):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.db_file = db_file
        # pokemon_data contains (name, level, actual_tag)
        self.pokemon_data = pokemon_data
        self.user_id = user_id
        self.reward = 10 + (pokemon_data[1] * 3) # Calculate reward here

    @discord.ui.button(label="Confirm Release", style=discord.ButtonStyle.danger, custom_id="confirm_release")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("You cannot confirm this release.", ephemeral=True)

        name, level, actual_tag = self.pokemon_data

        # Disable buttons
        for child in self.children:
            child.disabled = True
        
        try:
            async with aiosqlite.connect(self.db_file) as db:
                await db.execute("BEGIN TRANSACTION")
                await db.execute("DELETE FROM caught_pokemon WHERE instance_id = ?", (actual_tag,))
                await db.execute("UPDATE users SET eco_tokens = eco_tokens + ? WHERE user_id = ?", (self.reward, self.user_id))
                await db.commit()

            embed = discord.Embed(title="🌿 Wildlife Reintroduced", color=discord.Color.green())
            embed.description = f"**{self.ctx.author.name}** successfully rehabilitated and released their **{name.capitalize()}** back into the wild."
            embed.add_field(name="Conservation Grant Awarded", value=f"🪙 +{self.reward} Eco-Tokens")
            embed.set_footer(text=f"Tag ID Deleted: {actual_tag[:8]}")

            await interaction.response.edit_message(embed=embed, view=self)

        except Exception as e:
            await interaction.response.edit_message(content="❌ A critical error occurred during release.", embed=None, view=self)
            print(f"Release Error: {e}")

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, custom_id="cancel_release")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("You cannot cancel this release.", ephemeral=True)
            
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="Release cancelled. The specimen remains in your PC.", embed=None, view=self)

class PokemonPaginator(discord.ui.View):
    def __init__(self, bot, user_id, current_index, total_pokemon, active_partner_id):
        super().__init__(timeout=180) # Buttons disable after 3 minutes
        self.bot = bot
        self.user_id = user_id
        self.current_index = current_index
        self.total_pokemon = total_pokemon
        self.active_partner_id = active_partner_id
        #self.update_button_states()

    def update_button_states(self):
        # Disable 'Prev' if we are at Pokemon #1, disable 'Next' if we are at the end
        self.children[0].disabled = self.current_index <= 1
        self.children[1].disabled = self.current_index >= self.total_pokemon

    async def generate_embed(self):
        """Fetches the data for the current Field Number and builds the UI with local assets."""
        
        async with aiosqlite.connect(DB_FILE) as db:
                
            async with db.execute("""
                WITH Roster AS (
                    SELECT 
                        cp.nickname, cp.pokedex_id, cp.level, cp.nature, cp.is_shiny, s.name, 
                        cp.instance_id, cp.original_user_id, cp.experience, s.growth_rate,
                        cp.iv_hp, cp.iv_attack, cp.iv_defense, cp.iv_sp_atk, cp.iv_sp_def, cp.iv_speed,
                        cp.ev_hp, cp.ev_attack, cp.ev_defense, cp.ev_sp_atk, cp.ev_sp_def, cp.ev_speed, 
                        cp.ability, cp.happiness, cp.held_item, cp.gmax_factor,
                        cp.height_multiplier, cp.weight_multiplier, s.height, s.weight,
                        cp.gender, 
                        ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as field_number
                    FROM caught_pokemon cp
                    JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                    WHERE cp.user_id = ?
                    AND cp.instance_id NOT IN (SELECT instance_id FROM active_deployments)
                    AND cp.instance_id NOT IN (SELECT instance_id FROM gts_deposits)
                )
                SELECT * FROM Roster WHERE field_number = ?
            """, (self.user_id, self.current_index)) as cursor:
                data = await cursor.fetchone()
            
            if not data:
                return discord.Embed(title="Error", description="Specimen data corrupted."), None

            # Unpack all 32 variables!
            (nickname, poke_id, level, nature, is_shiny, name, actual_tag_id, original_user_id, current_xp, growth_rate,
            iv_hp, iv_atk, iv_def, iv_spa, iv_spd, iv_spe, ev_hp, ev_atk, ev_def, ev_spa, ev_spd, ev_spe, 
            ability, happiness, held_item, gmax_factor, 
            h_mult, w_mult, base_h, base_w, gender, field_number) = data

            # Fetch Base Stats
            async with db.execute("SELECT stat_name, base_value FROM base_pokemon_stats WHERE pokedex_id = ?", (poke_id,)) as cursor:
                stats = {stat[0]: stat[1] for stat in await cursor.fetchall()}
                
            # Fetch Typings!
            async with db.execute("SELECT type_name FROM base_pokemon_types WHERE pokedex_id = ?", (poke_id,)) as cursor:
                type_rows = await cursor.fetchall()
                type_str = type_badges([row[0] for row in type_rows])

        # --- CALCULATIONS ---
        # Format the Gender Icon
        gender_badge = " " + gender_icon(gender)
        
        # --- Original Trainer Logic ---
        if str(original_user_id) == str(self.user_id):
            ot_display = "You"
        else:
            # Look up the user in the bot's cache
            ot_user = self.bot.get_user(int(original_user_id))
            
            if ot_user:
                # .display_name grabs their server nickname if they have one, otherwise their global username
                ot_display = ot_user.display_name 
            else:
                # Fallback just in case the original catcher left the server or the bot's cache cleared
                ot_display = "Unknown Researcher"

        display_title = f'"{nickname}" {name.capitalize()}' if nickname else name.capitalize()
        display_ability = ability.replace('-', ' ').title() if ability else "Unknown"
        item_display = held_item.replace('-', ' ').title() if held_item != 'none' else "None"
        gmax_icon = " 🌪️ (G-Max Factor)" if gmax_factor else ""
        
        if happiness < 50: bond_icon = "🤍🤍🤍 (Acclimating)"
        elif happiness < 150: bond_icon = "❤️🤍🤍 (Trusting)"
        elif happiness < 220: bond_icon = "❤️❤️🤍 (Bonded)"
        else: bond_icon = "❤️❤️❤️ (Symbiotic)"

        xp_for_next_level = get_xp_requirement(level, growth_rate) 
        
        real_hp = calculate_real_stat('hp', stats.get('hp', 0), iv_hp, ev_hp, level)
        real_atk = calculate_real_stat('attack', stats.get('attack', 0), iv_atk, ev_atk, level)
        real_def = calculate_real_stat('defense', stats.get('defense', 0), iv_def, ev_def, level)
        real_spa = calculate_real_stat('special-attack', stats.get('special-attack', 0), iv_spa, ev_spa, level)
        real_spd = calculate_real_stat('special-defense', stats.get('special-defense', 0), iv_spd, ev_spd, level)
        real_spe = calculate_real_stat('speed', stats.get('speed', 0), iv_spe, ev_spe, level)

        # --- BIOMETRIC MATH ---
        h_mult = h_mult or 1.0
        w_mult = w_mult or 1.0
        
        actual_height_m = round((base_h / 10.0) * h_mult, 2)
        actual_weight_kg = round((base_w / 10.0) * w_mult, 2)
        
        # The Alpha cutoff is the shared constant, not a number written out again. It
        # decides two separate things - the badge shown here, and the `alpha` tag a
        # capture earns - and the two disagreeing would be invisible until somebody
        # noticed a specimen labelled ALPHA that had not been tagged as one.
        size_tag = "Average"
        if h_mult <= 0.80: size_tag = "Teeny"
        elif h_mult <= 0.95: size_tag = "Small"
        elif h_mult >= ALPHA_HEIGHT_THRESHOLD: size_tag = "ALPHA"
        elif h_mult >= 1.06: size_tag = "Large"

        # ==========================================
        # LOCAL ASSET LOADING
        # ==========================================
        # The box browser shows HOME artwork, and shows the FEMALE sprite for the
        # hundred-odd species that have one. Both questions are asked by utils.sprites,
        # which owns the fallback chain - only about 8% of the roster has a female
        # image, so "give me the female HOME sprite" has to be a preference with
        # somewhere to land rather than a filename.
        safe_filename = sprite_attachment_name(poke_id, is_shiny, gender)
        file_path = resolve_sprite(poke_id, shiny=is_shiny, gender=gender, style=HOME)

        sprite_file = None
        if file_path:
            sprite_file = discord.File(file_path, filename=safe_filename)
        else:
            print(f"⚠️ WARNING: no sprite anywhere for ID {poke_id} "
                  f"(shiny={is_shiny}, gender={gender})")

        # --- BUILD EMBED ---
        color = discord.Color.gold() if is_shiny else discord.Color.green()
        title_prefix = "🌟" if is_shiny else ""

        # Inject the gender icon directly into the title!
        embed = discord.Embed(title=f"{title_prefix}{display_title}{gender_badge}{gmax_icon}", color=color)
        
        # Attach the local file to the embed using the safe filename
        if sprite_file:
            embed.set_image(url=f"attachment://{safe_filename}")

        desc_prefix = "❤️ **Active Partner**\n" if actual_tag_id == self.active_partner_id else ""
        
        # 🚨 Added Original Trainer and Typings to the main description block!
        embed.description = f"{desc_prefix}**Level {level}** | **Nature:** {nature}\n**Type:** {type_str}\n🧬 **Ability:** {display_ability}\n🎒 **Held Item:** `{item_display}`\n📏 **Dimensions:** {size_tag} ({actual_height_m}m, {actual_weight_kg}kg)\n🤝 **Bond:** {bond_icon}\n✨ **XP:** {current_xp} / {xp_for_next_level}\n👤 **Original Trainer:** {ot_display}"

        # ==========================================
        # GENETICS & STAT FORMATTING
        # ==========================================
        # Calculate Genetic Potential (IVs)
        iv_total = iv_hp + iv_atk + iv_def + iv_spa + iv_spd + iv_spe
        iv_percentage = int((iv_total / 186.0) * 100)
        
        if iv_percentage >= 90: appraisal = "S-Tier (Flawless)"
        elif iv_percentage >= 80: appraisal = "A-Tier (Excellent)"
        elif iv_percentage >= 60: appraisal = "B-Tier (Strong)"
        elif iv_percentage >= 40: appraisal = "C-Tier (Average)"
        else: appraisal = "D-Tier (Weak)"

        # 🚨 UPDATED: Shows Genetic Potential, IVs, and EVs all in one clean block!
        stat_block = f"""
🧬 **Genetic Potential:** {iv_percentage}% *({appraisal})*\n**HP:** {real_hp} `[IV: {iv_hp} | EV: {ev_hp}]`\n**Attack:** {real_atk} `[IV: {iv_atk} | EV: {ev_atk}]`\n**Defense:** {real_def} `[IV: {iv_def} | EV: {ev_def}]`\n**Sp. Atk:** {real_spa} `[IV: {iv_spa} | EV: {ev_spa}]`\n**Sp. Def:** {real_spd} `[IV: {iv_spd} | EV: {ev_spd}]`\n**Speed:** {real_spe} `[IV: {iv_spe} | EV: {ev_spe}]`
        """
        
        # Add a quick EV Total tracker to the header
        total_evs = ev_hp + ev_atk + ev_def + ev_spa + ev_spd + ev_spe
        embed.add_field(name=f"Current Biological Stats (EV Total: {total_evs}/510)", value=stat_block, inline=False)
        
        embed.set_footer(text=f"Field No. {field_number} of {self.total_pokemon} | Tag ID: {actual_tag_id[:8]}")
        return embed, sprite_file

    @discord.ui.button(label="◀️ Previous", style=discord.ButtonStyle.primary, custom_id="prev_poke")
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("❌ This is not your field notebook!", ephemeral=True)
        self.current_index -= 1
        self.update_button_states() # Update the states!

        embed, sprite_file = await self.generate_embed()
        if sprite_file:
            await interaction.response.edit_message(embed=embed, attachments=[sprite_file], view=self)
        else:
            await interaction.response.edit_message(embed=embed, attachments=[], view=self)

    @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.primary, custom_id="next_poke")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("❌ This is not your field notebook!", ephemeral=True)
        self.current_index += 1
        self.update_button_states()
        embed, sprite_file = await self.generate_embed()
        
        if sprite_file:
            await interaction.response.edit_message(embed=embed, attachments=[sprite_file], view=self)
        else:
            await interaction.response.edit_message(embed=embed, attachments=[], view=self)

def split_note_count(typed):
    """
    `notes 10` split into (10, 'notes'), and plain `notes` into (None, 'notes').

    The count is read off the END rather than taken as its own argument, because
    `!analyze` consumes the rest of the line - `*, target: str` - and a second parameter
    would have made `!analyze field notes` stop working. Both spellings of the noun
    survive, which is the point of parsing rather than re-declaring the signature.
    """
    parts = str(typed or '').split()
    if len(parts) >= 2 and parts[-1].isdigit():
        return int(parts[-1]), " ".join(parts[:-1])
    return None, " ".join(parts)


def analysis_embed(issued, *, wanted, held, room, open_after):
    """
    What a batch of analyses produced, and honestly why it produced fewer.

    Running ten and being handed three with no explanation is the kind of silence that
    reads as a bug. Whichever limit actually bit is named.
    """
    runs = len(issued)
    embed = discord.Embed(
        title="💻 Data Decryption Successful",
        description=(f"You fed the raw data into the laboratory mainframe. "
                     f"**{runs}** new ecological directive{'s' if runs != 1 else ''} "
                     f"extracted:"),
        color=discord.Color.teal())

    lines = []
    for entry in issued:
        emoji, heading, _ = describe_directive(entry['objective_type'], entry['target'])
        reward = (f"💰 {entry['reward_payload']} Eco Tokens"
                  if entry['reward_type'] == 'eco_tokens'
                  else f"📦 1x {entry['reward_payload'].replace('-', ' ').title()}")
        lines.append(f"{emoji} `#{entry['directive_id']}` **{heading}** "
                     f"×{entry['required']} — {reward}")

    # 20 directives at ~90 characters each is comfortably inside the 1024-character
    # field limit, but the limit is real and silent, so it is enforced rather than
    # trusted to arithmetic that a future change could invalidate.
    text = "\n".join(lines) or "*nothing*"
    if len(text) > 1000:
        text = text[:1000].rsplit("\n", 1)[0] + "\n…"
    embed.add_field(name="Issued", value=text, inline=False)

    if runs < wanted:
        if held <= runs:
            why = (f"You only had **{held}** Encrypted Field Note"
                   f"{'s' if held != 1 else ''} to spend.")
        else:
            why = (f"Your notebook only had room for **{room}** more. "
                   f"Finish some with `!claim`, or drop one with `!abandon <id>`.")
        embed.add_field(name=f"Only {runs} of {wanted}", value=why, inline=False)

    embed.set_footer(
        text=f"{open_after}/{MAX_ACTIVE_DIRECTIVES} directives active · "
             f"!survey to view them")
    return embed


# One place that turns a directive row into words, so the page, the menu option and the
# analysis summary cannot describe the same task three different ways.
DIRECTIVE_SHAPES = {
    'cull_type': ("⚠️", "Invasive Species Management",
                  "Defeat wild **{target}**-type specimens to restore equilibrium."),
    'survey_species': ("🧬", "Genetic Population Survey",
                       "Successfully capture and tag wild **{target}**."),
    'trigger_mutation': ("📈", "Kinetic Maturation Study",
                         "Trigger a biological evolution for a **{target}**."),
}


def describe_directive(obj_type, target):
    """A directive as (emoji, heading, instruction), whatever kind it is."""
    pretty = str(target).replace('-', ' ').title()
    emoji, heading, instruction = DIRECTIVE_SHAPES.get(
        obj_type, ("🔬", "Field Research", "Analyze **{target}**."))
    return emoji, f"{heading}: {pretty}", instruction.format(target=pretty)


class DirectiveSelect(discord.ui.Select):
    """Jump straight to a directive instead of clicking Next eleven times."""

    def __init__(self, paginator):
        self.paginator = paginator
        options = []
        for index, row in enumerate(paginator.directives):
            d_id, obj_type, target, req_amt, curr_prog = row[0], row[1], row[2], row[3], row[4]
            emoji, heading, _ = describe_directive(obj_type, target)
            options.append(discord.SelectOption(
                # The ID is on the label because it is what `!abandon` and
                # `!survey <id>` take, and a menu that hides it makes those two
                # commands guesswork.
                label=f"#{d_id} · {heading}"[:100],
                value=str(index),
                emoji=emoji,
                description=f"{curr_prog}/{req_amt} complete"[:100]))
        super().__init__(placeholder="Jump to a directive…", options=options, row=0)

    async def callback(self, interaction):
        if str(interaction.user.id) != self.paginator.user_id:
            return await interaction.response.send_message(
                "❌ This is not your field notebook!", ephemeral=True)
        self.paginator.current_index = int(self.values[0])
        self.paginator.update_button_states()
        await interaction.response.edit_message(
            embed=await self.paginator.generate_embed(), view=self.paginator)


def parse_abandon_request(request, held_ids):
    """
    What `!abandon` was asked to drop, as (ids, complaint).

    `None` for the ids means "no ids given" - open the picker. `all` is spelled out
    rather than inferred from an empty command, because emptying a notebook by accident
    is not a mistake anybody can undo.

    Every id is checked against what the trainer actually holds BEFORE anything is
    deleted, so `!abandon 4 999` refuses outright rather than dropping 4 and then
    complaining about 999.
    """
    text = " ".join(str(request or "").split())
    if not text:
        return None, None

    if text.lower() in ('all', 'everything', '*'):
        return list(held_ids), None

    tokens = text.replace(',', ' ').split()
    if not all(t.isdigit() for t in tokens):
        return None, ("\u26a0\ufe0f Give me directive numbers \u2014 `!abandon 4`, "
                      "`!abandon 4 7 9`, or `!abandon all`. Run `!abandon` on its own "
                      "to pick from a list.")

    wanted = [int(t) for t in tokens]
    unknown = [i for i in wanted if i not in held_ids]
    if unknown:
        listed = ", ".join(f"`{i}`" for i in held_ids[:20])
        return None, (f"\u26a0\ufe0f You have no directive "
                      f"{', '.join(f'**#{i}**' for i in unknown)}. "
                      f"You hold: {listed}" + ("\u2026" if len(held_ids) > 20 else ""))

    # Deduplicated, because `!abandon 4 4` should drop one directive and report one.
    return sorted(set(wanted)), None


class AbandonSelect(discord.ui.Select):
    """Pick several directives to drop, in one go."""

    def __init__(self, panel):
        self.panel = panel
        options = []
        for d_id, obj_type, target, req_amt, curr_prog in panel.directives:
            emoji, heading, _ = describe_directive(obj_type, target)
            options.append(discord.SelectOption(
                label=f"#{d_id} \u00b7 {heading}"[:100],
                value=str(d_id),
                emoji=emoji,
                description=f"{curr_prog}/{req_amt} complete"[:100]))
        super().__init__(
            placeholder="Choose the directives to abandon\u2026",
            options=options, min_values=1, max_values=len(options), row=0)

    async def callback(self, interaction):
        self.panel.chosen = [int(v) for v in self.values]
        # Re-rendered rather than acted on: a multi-select fires on every change, and
        # deleting somebody's quests the instant they tick a box is not a thing to do
        # without a second press.
        await interaction.response.edit_message(embed=self.panel.summary(), view=self.panel)


class AbandonPanel(discord.ui.View):
    """The dropdown, plus the button that actually does it."""

    def __init__(self, cog, ctx, directives):
        super().__init__(timeout=120)
        self.cog = cog
        self.ctx = ctx
        self.directives = directives
        self.chosen = []
        self.message = None
        # Discord refuses a select with more than 25 options with a 400 the library does
        # not raise. The directive cap is 20, so this only bites on a notebook filled
        # before the cap existed - and those are exactly the notebooks that need this.
        self.add_item(AbandonSelect(self))

    async def interaction_check(self, interaction):
        if str(interaction.user.id) != str(self.ctx.author.id):
            await interaction.response.send_message(
                "\u274c This is not your field notebook!", ephemeral=True)
            return False
        return True

    def summary(self):
        embed = discord.Embed(
            title="\U0001f5d1\ufe0f Archive Directives",
            description="Pick the directives you no longer want, then confirm. "
                        "Progress on them is lost.",
            colour=discord.Colour.dark_gray())
        if self.chosen:
            picked = [d for d in self.directives if d[0] in self.chosen]
            embed.add_field(
                name=f"Selected ({len(picked)})",
                value="\n".join(
                    f"`#{d[0]}` {describe_directive(d[1], d[2])[1]}" for d in picked)[:1000],
                inline=False)
        else:
            embed.add_field(name="Selected", value="*nothing yet*", inline=False)
        return embed

    @discord.ui.button(label="Archive selected", style=discord.ButtonStyle.danger, row=1)
    async def confirm(self, interaction, button):
        if not self.chosen:
            return await interaction.response.send_message(
                "Pick at least one directive first.", ephemeral=True)
        dropped = await drop_directives(str(self.ctx.author.id), self.chosen)
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            embed=archive_result(dropped), view=self)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, row=1)
    async def cancel(self, interaction, button):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            content="Nothing was archived.", embed=None, view=self)


async def drop_directives(user_id, ids):
    """Delete these directives if they belong to this trainer. Returns how many went."""
    if not ids:
        return 0
    marks = ",".join("?" * len(ids))
    async with aiosqlite.connect(DB_FILE) as db:
        # Scoped to the owner in the DELETE itself rather than checked first: a check
        # and a delete are two statements, and only one of them decides what happens.
        cursor = await db.execute(
            f"DELETE FROM field_directives WHERE user_id = ? AND is_completed = 0 "
            f"AND directive_id IN ({marks})", (user_id, *ids))
        await db.commit()
        return cursor.rowcount


def archive_result(count):
    return discord.Embed(
        title="\U0001f5d1\ufe0f Directives Archived",
        description=(f"**{count}** directive{'s' if count != 1 else ''} cleared from "
                     f"your field notebook."
                     if count else "Nothing was archived \u2014 those directives were "
                                   "already gone."),
        colour=discord.Colour.dark_gray())

class SurveyPaginator(discord.ui.View):
    def __init__(self, user_id, directives, start_index=0):
        super().__init__(timeout=180) # Disables after 3 minutes
        self.user_id = user_id
        self.directives = directives
        self.current_index = max(0, min(start_index, len(directives) - 1))
        self.total_pages = len(directives)
        # A select takes 25 options and the cap is 20, so this always fits - but a
        # notebook filled before the cap existed can hold more, and Discord answers a
        # 26-option select with a 400 the library does not raise. Trimmed rather than
        # risked; the buttons still reach everything.
        if directives and len(directives) <= 25:
            self.add_item(DirectiveSelect(self))
        self.update_button_states()

    def update_button_states(self):
        # Disable Prev if on the first page, disable Next if on the last page
        self.prev_button.disabled = self.current_index == 0
        self.next_button.disabled = self.current_index >= self.total_pages - 1

    async def generate_embed(self):
        # Grab the specific directive for the current page
        directive = self.directives[self.current_index]
        d_id, obj_type, target, req_amt, curr_prog, rev_type, rev_payload = directive

        embed = discord.Embed(
            title="📋 Ecological Field Directives",
            description="Complete these assigned tasks to balance the ecosystem and earn research funding.",
            color=discord.Color.brand_green()
        )

        # --- TRANSLATE THE DATABASE LOGIC INTO NARRATIVE ---
        emoji, heading, desc = describe_directive(obj_type, target)
        task_title = f"{emoji} {heading} (ID: {d_id})"

        # --- CALCULATE AND DRAW THE PROGRESS BAR ---
        safe_req = max(1, req_amt)
        progress_ratio = min(1.0, curr_prog / safe_req)
        
        filled_blocks = int(progress_ratio * 10)
        empty_blocks = 10 - filled_blocks
        
        bar = f"{'█' * filled_blocks}{'░' * empty_blocks}"
        progress_text = f"`{bar}` **{curr_prog}/{req_amt}**"
        
        # --- FORMAT THE REWARD PAYLOAD ---
        if rev_type == 'eco_tokens':
            reward_text = f"💰 **{rev_payload}** Eco Tokens"
        elif rev_type == 'item':
            reward_text = f"📦 **1x** {rev_payload.replace('-', ' ').title()}"
        else:
            reward_text = "Standard Equipment"
        
        # Assemble the block
        field_value = f"{desc}\n\n{progress_text}\n**Grant:** {reward_text}"
        embed.add_field(name=task_title, value=field_value, inline=False)
        
        # Add a footer showing pagination progress (e.g., "Directive 1 of 4")
        embed.set_footer(text=f"Active Directive {self.current_index + 1} of {self.total_pages}")
        
        return embed

    # Row 1, because the jump menu takes row 0 and a select fills a row on its own.
    @discord.ui.button(label="◀️ Previous", style=discord.ButtonStyle.secondary, custom_id="prev_quest", row=1)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("❌ This is not your field notebook!", ephemeral=True)
        self.current_index -= 1
        self.update_button_states()
        embed = await self.generate_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.secondary, custom_id="next_quest", row=1)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("❌ This is not your field notebook!", ephemeral=True)
        self.current_index += 1
        self.update_button_states()
        embed = await self.generate_embed()
        await interaction.response.edit_message(embed=embed, view=self)

class InventoryPaginator(discord.ui.View):
    def __init__(self, ctx, rescued_pokemon, tokens):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.rescued_pokemon = rescued_pokemon
        self.tokens = tokens
        self.current_page = 0
        self.items_per_page = 10
        self.max_pages = max(1, math.ceil(len(rescued_pokemon) / self.items_per_page))
        self.update_buttons()

    def update_buttons(self):
        # 0: First, 1: Prev, 2: Next, 3: Last (Row 0)
        self.children[0].disabled = self.current_page == 0
        self.children[1].disabled = self.current_page == 0
        self.children[2].disabled = self.current_page >= self.max_pages - 1
        self.children[3].disabled = self.current_page >= self.max_pages - 1

    def create_embed(self):
        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        chunk = self.rescued_pokemon[start:end]

        embed = discord.Embed(title=f"📋 {self.ctx.author.name}'s Ecological Survey", color=discord.Color.blue())
        embed.set_thumbnail(url=self.ctx.author.avatar.url if self.ctx.author.avatar else self.ctx.author.default_avatar.url)
        embed.add_field(name="Global Eco-Tokens", value=f"🪙 {self.tokens:,}", inline=False)

        if chunk:
            embed.description = "\n".join(chunk)
        else:
            embed.description = "*No specimens match this filter.*"
            
        embed.set_footer(text=f"Page {self.current_page + 1}/{self.max_pages} | Total Results: {len(self.rescued_pokemon)}")
        return embed

    # --- ROW 0: PAGINATION CONTROLS ---

    @discord.ui.button(label="⏪ First", style=discord.ButtonStyle.secondary, row=0)
    async def first_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("This isn't your survey notebook!", ephemeral=True)
        self.current_page = 0
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="◀️ Prev", style=discord.ButtonStyle.primary, row=0)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("This isn't your survey notebook!", ephemeral=True)
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.primary, row=0)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("This isn't your survey notebook!", ephemeral=True)
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)
        
    @discord.ui.button(label="Last ⏩", style=discord.ButtonStyle.secondary, row=0)
    async def last_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("This isn't your survey notebook!", ephemeral=True)
        self.current_page = self.max_pages - 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    # --- ROW 1: UTILITY CONTROLS ---

    @discord.ui.button(label="📦 Copy Box Numbers", style=discord.ButtonStyle.success, row=1)
    async def extract_ids_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("This isn't your survey notebook!", ephemeral=True)
        
        # Get the currently displayed chunk
        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        chunk = self.rescued_pokemon[start:end]

        if not chunk:
            return await interaction.response.send_message("No specimens on this page to copy.", ephemeral=True)

        # Extract the Box numbers using Regex
        box_numbers = []
        for line in chunk:
            # Looks for **#123** and extracts the 123
            match = re.search(r'\*\*#(\d+)\*\*', line)
            if match:
                box_numbers.append(match.group(1))

        if box_numbers:
            output_string = ", ".join(box_numbers)
            await interaction.response.send_message(
                f"📋 **Trade Helper:**\nCopy and paste this exact string into your Trade Modals:\n\n`{output_string}`", 
                ephemeral=True
            )
        else:
            await interaction.response.send_message("Could not extract any Box numbers from this page.", ephemeral=True)

    @discord.ui.button(label="🗑️ Close Survey", style=discord.ButtonStyle.danger, row=1)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("This isn't your survey notebook!", ephemeral=True)
        
        # Safely delete the message
        try:
            await interaction.message.delete()
        except discord.NotFound:
            pass # Message was already deleted

class Ecology(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.habitat_activity = {}
        self.xp_cooldowns = {}
    
    async def spawn_timer(self, message: discord.Message, spawn_id: str, pokemon_name: str, guild_id: str = None, user_id: str = None, timeout: int = None,
                          config_guild: str = None):
        """Background task that waits, then despawns the specimen.

        `config_guild` is separate from `guild_id` on purpose. `guild_id` decides
        WHICH store the spawn lives in - setting it on an expedition encounter
        would send the despawn looking in the public one - but an expedition still
        happens in a server whose settings apply.
        """
        settings = await cfg.get_all(config_guild or guild_id) if (config_guild or guild_id) else {}
        if timeout is None:
            timeout = settings.get('despawn_seconds') or 300

        await asyncio.sleep(timeout)

        expired = False

        # 2. Check if the specimen is still in memory
        if user_id:
            # Private Expedition Spawn
            if user_id in user_active_spawns and spawn_id in user_active_spawns[user_id]:
                user_active_spawns[user_id].pop(spawn_id, None)
                expired = True
        elif guild_id:
            # Global Camera Trap Spawn
            if guild_id in active_spawns and spawn_id in active_spawns[guild_id]:
                active_spawns[guild_id].pop(spawn_id, None)
                expired = True

        # 3. If it expired naturally, edit the Discord message - or remove it, if
        #    the server would rather its habitat channel did not fill with cards
        #    for specimens that are no longer there.
        if expired:
            try:
                if settings.get('auto_delete_spawns'):
                    return await message.delete()

                # Fetch the original embed from the message
                embed = message.embeds[0]
                
                # Format the name cleanly
                clean_name = pokemon_name.capitalize().replace('-', ' ')
                
                # Update the visual data to show it left, including the name!
                embed.title = "💨 Biological Signal Lost"
                embed.description = f"The wild **{clean_name}** grew tired of waiting and wandered back into the wild. The area is now quiet."
                embed.color = discord.Color.dark_grey()
            
                
                # Edit the message AND explicitly clear the attachments to remove the
                # stray image. `view=None` takes the catch panel down with it: an
                # expedition card that has despawned must not still offer a Poke Ball
                # button, and the View's own timeout only stops it responding - it does
                # not remove it from the screen.
                await message.edit(embed=embed, attachments=[], view=None)
                
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                # The channel or message was deleted by an admin before the timer finished, so we just safely ignore it.
                pass

    # --- The Spawning Logic Extracted into a Helper Function ---
    async def trigger_activity_spawn(self, guild):
        guild_id = str(guild.id)

        # Read once, at the top. Every one of these is a cached dictionary lookup after
        # the first spawn, and reading them together means the card, the ping and the
        # despawn all describe the same configuration rather than three snapshots of it.
        settings = await cfg.get_all(guild_id)

        async with aiosqlite.connect(DB_FILE) as db:

            # Check if a habitat channel is actually set up
            async with db.execute("SELECT spawn_channel_id, ecosystem_score, active_biome, pollution_type FROM servers WHERE guild_id = ?", (guild_id,)) as cursor:
                server_data = await cursor.fetchone()
            
            if not server_data or not server_data[0]:
                return # No channel set up, do nothing
                
            channel_id, score, biome, pollution = server_data
            channel = self.bot.get_channel(int(channel_id))
            
            if not channel:
                return
                
            ecosystem_score = score if score else 50
            active_biome = biome if biome else 'forest'
            current_pollution = pollution if pollution else 'none'
            
            # --- ECOLOGICAL DISASTER ROLL (10% Chance) ---
            event_roll = random.random()
            if event_roll < 0.10 and current_pollution == 'none':
                disasters = {
                    'oil_spill': {'damage': 20, 'msg': '⚠️ **ECOLOGICAL DISASTER:** A pipeline has ruptured, causing an oil spill!'},
                    'toxic_smog': {'damage': 15, 'msg': '⚠️ **HAZARD DETECTED:** A thick cloud of toxic smog has settled over the area.'},
                    'wildfire': {'damage': 25, 'msg': '⚠️ **ECOLOGICAL DISASTER:** An uncontrolled wildfire is sweeping through the habitat!'},
                    'spatial_rift': {'damage': 30, 'msg': '🌌 **DIMENSIONAL RIFT:** A space-time distortion has opened! Highly invasive Ultra Beasts are flooding the habitat!'}
                }
                
                disaster_type = random.choice(list(disasters.keys()))
                damage = disasters[disaster_type]['damage']
                
                new_score = max(0, ecosystem_score - damage)
                await db.execute("UPDATE servers SET ecosystem_score = ?, pollution_type = ? WHERE guild_id = ?", (new_score, disaster_type, guild_id))
                await db.commit()

                # A rift is an announcement, not a spawn, and the two want different
                # rooms - a habitat channel people watch for specimens should not be
                # where server-wide events land. Falls back to the habitat channel, so
                # a server that has set nothing behaves exactly as it did before.
                stage = self.bot.get_channel(settings.get('announce_channel') or 0) or channel
                alert = event_alert(settings)
                await stage.send(
                    f"{alert}{disasters[disaster_type]['msg']}\n"
                    f"*Biodiversity is dropping rapidly. Use `!intervene` or a "
                    f"`Purifier` to stabilize the area!*",
                    allowed_mentions=discord.AllowedMentions(
                        roles=bool(alert), users=False, everyone=False))
                return # Skip spawning to simulate wildlife fleeing the disaster!

            # --- INVASIVE RIFT OVERRIDE ---
            if current_pollution == 'spatial_rift':
                habitat_condition = "The local environment is being warped by invasive dimensional energy."
                rarity_name = "🛸 ULTRA BEAST"
                async with db.execute(f"SELECT pokedex_id, name, capture_rate, gender_rate FROM base_pokemon_species WHERE {ultra_beasts()} ORDER BY RANDOM() LIMIT 1;") as cursor:
                    spawned_data = await cursor.fetchone()
            else:
                # --- STANDARD BIOME & POLLUTION LOGIC ---
                if active_biome == 'urban': allowed_types = ['electric', 'steel', 'poison', 'normal']
                elif active_biome == 'coastal': allowed_types = ['water', 'flying', 'ice', 'normal']
                else: allowed_types = ['grass', 'bug', 'ground', 'normal']

                if ecosystem_score < 30:
                    allowed_types = ['poison', 'dark', 'steel']
                    habitat_condition = f"The {active_biome} is degraded and covered in thick smog."
                elif ecosystem_score > 70:
                    allowed_types.extend(['fairy', 'dragon', 'psychic'])
                    habitat_condition = f"The {active_biome} is pristine, vibrant, and bursting with life."
                else:
                    habitat_condition = f"The {active_biome} ecosystem is perfectly stable."

                # Rarity Roll. One shared table, so this, `!spawn` and the
                # expedition cannot drift apart again - and so the pseudo-legendaries
                # leave the ordinary pool by the same edit that gives them a tier.
                #
                # Scaled by the habitat's health, which until now decided only which
                # TYPES appeared. A server that maintains its ecosystem sees rarer
                # things; one that lets it rot sees fewer. At the default 50 the
                # multiplier is exactly 1.0, so nothing changes for anybody who has
                # never touched it.
                tier = roll_rarity(scaled_rarity(HABITAT_RARITY, ecosystem_score))
                rarity_name = RARITY_LABELS[tier]

                def rarity_query(chosen):
                    return f"""
                        SELECT s.pokedex_id, s.name, s.capture_rate, s.gender_rate
                        FROM base_pokemon_species s
                        JOIN base_pokemon_types t ON s.pokedex_id = t.pokedex_id
                        WHERE t.type_name IN ({','.join(['?']*len(allowed_types))})
                        AND {spawnable_forms('s')}
                        {rarity_filter(chosen, 's')} ORDER BY RANDOM() LIMIT 1;
                    """

                async with db.execute(rarity_query(tier), allowed_types) as cursor:
                    spawned_data = await cursor.fetchone()

                # A rare tier can come up empty: a degraded biome allows three types and
                # there may be no mythical among them. That abandoned the spawn outright
                # - the habitat simply went quiet, as often as the rare tiers came up,
                # and nothing said why. Fall back to ordinary wildlife instead.
                if not spawned_data and tier != 'wild':
                    tier, rarity_name = 'wild', RARITY_LABELS['wild']
                    async with db.execute(rarity_query('wild'), allowed_types) as cursor:
                        spawned_data = await cursor.fetchone()

        if not spawned_data:
            return

        poke_id, name, cap_rate, gender_rate = spawned_data
        # Rolled HERE, not at capture. A spawn that shows a sex has to hand the
        # same one to the specimen that gets caught. The NAME is handed over too,
        # because a species whose name states a sex must not roll the other one.
        gender = roll_gender(gender_rate, species_name=name)
        # The habitat's health nudges this too, but far less than it moves the rare
        # tiers - a shiny is worth what it is worth because it is unlikely.
        is_shiny = roll_shiny(ecosystem_score)
        shiny_text = "🌟 **SHINY MUTATION** " if is_shiny else ""
        
        # 🚨 NEW ARCHITECTURE: Initialize the guild's dictionary if it doesn't exist
        if guild_id not in active_spawns:
            active_spawns[guild_id] = {}
            
        # Create a unique 6-character tracking ID for this specific specimen
        spawn_id = str(uuid.uuid4())[:6]

        # 🚨 Store it UNDER the unique spawn_id, not just the guild_id!
        # The channel is recorded HERE, where the message is about to be sent, so a
        # spawn and the room it appeared in can never disagree.
        active_spawns[guild_id][spawn_id] = {
            'pokedex_id': poke_id, 'name': name, 'capture_rate': cap_rate,
            'is_shiny': is_shiny, 'gender': gender, 'channel_id': channel.id
        }

        # The mutation was rolled ABOVE, and rolling it again here is what this
        # used to do: the stored value went to whoever caught it and this second,
        # independent roll decided what the card SAID. One spawn in four thousand
        # announced a shiny that was not one, and another was quietly shiny with
        # nothing to say so.

        # ==========================================
        # 4. LOCAL ASSET LOADING
        # ==========================================
        # Construct the safe OS path to your sprites
        # HOME art, falling through to the official artwork - the same chain the box
        # browser and the battle scene use. A wild specimen has no gender yet; one is
        # assigned when it is caught, so there is nothing to prefer here.
        embed_color = discord.Color.gold() if is_shiny else discord.Color.green()
        safe_filename = sprite_attachment_name(poke_id, is_shiny, gender)
        file_path = resolve_sprite(poke_id, shiny=is_shiny, gender=gender, style=HOME)

        # Fallback Check: If the image is somehow missing from your folder, don't crash the bot!
        if not file_path:
            # You can point this to a default "missingno" or placeholder sprite if you have one
            print(f"⚠️ WARNING: no sprite anywhere for ID {poke_id}")
            sprite_file = None
        else:
            # Package the image as a discord File object
            sprite_file = discord.File(file_path, filename=safe_filename)
        
        def mask_name(name):
            masked = ""
            for i, char in enumerate(name):
                if char == "-":
                    masked += "- "
                elif i == 0 or (i > 0 and name[i-1] == "-"):
                    masked += f"{char.upper()} "
                else:
                    masked += "_ "
            return masked
        
        masked_display = mask_name(name)
        print(masked_display)
        # 4. Build the Visual Camera Trap Embed
        embed = discord.Embed(
            title=f"📸 Habitat Activity Detected!", 
            description=f"🌍 *{habitat_condition}*\n\nA {shiny_text}**{rarity_name} `{masked_display}`** {gender_icon(gender)} has appeared!\n\nUse `!catch <pokemon>` to deploy equipment and rescue it.",
            color=embed_color
        )

        # A full-width image is a lot of screen for a channel that also has people
        # talking in it, so a server can ask for the small version instead.
        if sprite_file:
            if settings.get('compact_spawns'):
                embed.set_thumbnail(url=f"attachment://{safe_filename}")
            else:
                embed.set_image(url=f"attachment://{safe_filename}")

        embed.set_footer(text="Automated Field Camera Trap")

        # The alert role, and only for something worth being pulled away from a
        # conversation for. `allowed_mentions` is set explicitly either way, so a
        # server that has not asked for pings cannot be pinged by accident.
        alert = rare_spawn_alert(settings, rarity_name, is_shiny)
        mentions = discord.AllowedMentions(roles=bool(alert), users=False,
                                          everyone=False)

        if sprite_file:
            msg = await channel.send(content=alert, embed=embed, file=sprite_file,
                                     allowed_mentions=mentions)
        else:
            msg = await channel.send(content=alert, embed=embed,
                                     allowed_mentions=mentions)

        # Recorded AFTER the send, because the id does not exist until then -
        # it is what lets a successful catch go back and rewrite this card.
        active_spawns[guild_id][spawn_id]['message_id'] = msg.id
        asyncio.create_task(self.spawn_timer(message=msg, spawn_id=spawn_id, pokemon_name=name, guild_id=guild_id))

    async def execute_biome_shift(self, ctx, target_biome, title, description):
        guild_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)
        cost = 100
        required_cp = 10
        
        try:
            async with aiosqlite.connect(DB_FILE) as db:
                # 2. Start the Atomic Transaction!
                await db.execute("BEGIN TRANSACTION")
                
                # Check Contribution Points (Do they have local authority?)
                async with db.execute("SELECT contribution_points FROM guild_members WHERE user_id = ? AND guild_id = ?", (user_id, guild_id)) as cursor:
                    member_data = await cursor.fetchone()
                cp = member_data[0] if member_data else 0
                
                if cp < required_cp:
                    await ctx.send(f"⚠️ You need at least {required_cp} Contribution Points in this server to lead a major ecological project. You currently have {cp}.")
                    return
                    
                # Check Global Funding (Do they have the Eco-Tokens?)
                async with db.execute("SELECT eco_tokens FROM users WHERE user_id = ?", (user_id,)) as cursor:
                    user_data = await cursor.fetchone()
                tokens = user_data[0] if user_data else 0
                
                if tokens < cost:
                    await ctx.send(f"⚠️ This project requires {cost} Eco-Tokens in funding. You only have {tokens}.")
                    return
                    
                # Check if the biome is already set to the target
                async with db.execute("SELECT active_biome FROM servers WHERE guild_id = ?", (guild_id,)) as cursor:
                    current_biome = await cursor.fetchone()
                    current_biome = current_biome[0]
                
                if current_biome == target_biome:
                    await ctx.send(f"The server is already a {target_biome.capitalize()} biome!")
                    return

                # Execute the Shift! Deduct tokens and update the server
                await db.execute("UPDATE users SET eco_tokens = eco_tokens - ? WHERE user_id = ?", (cost, user_id))
                await db.execute("UPDATE servers SET active_biome = ? WHERE guild_id = ?", (target_biome, guild_id))
                await db.commit()
            
            # Send the celebration embed
            embed = discord.Embed(title=title, description=description, color=discord.Color.gold())
            embed.set_footer(text=f"Project funded and led by {ctx.author.name} (-{cost} Eco-Tokens)")
            await ctx.send(embed=embed)
            
        except Exception as inner_e:
            # 6. ROLLBACK ON ERROR (If the database crashes, refund the money automatically)
            if db.in_transaction:
                await db.rollback()
            raise inner_e # Push the error out to the main handler

    @commands.Cog.listener()
    async def on_message(self, message):
        # 1. Ignore bot messages to prevent infinite loops
        if message.author.bot:
            return

        # 2. Safety Net: Ignore Direct Messages (DMs)
        if message.guild is None:
            return
        
        guild_id = str(message.guild.id)
        
        # 3. Increment the server's activity counter
        if guild_id not in self.habitat_activity:
            self.habitat_activity[guild_id] = 0
        
        self.habitat_activity[guild_id] += 1

        # 4. If the threshold is reached, trigger the spawn sequence. How much
        #    conversation that takes is the server's own business - twenty people
        #    and two thousand people need very different numbers, and the cached
        #    read costs nothing after the first message.
        threshold = await cfg.get(guild_id, 'spawn_rate') or MESSAGES_REQUIRED_FOR_SPAWN
        if self.habitat_activity[guild_id] >= threshold:
            self.habitat_activity[guild_id] = 0 # Reset the counter immediately

            print(f"🌿 DEBUG: Spawn threshold reached in {message.guild.name}! Triggering spawn...")

            await self.trigger_activity_spawn(message.guild)
    
    @commands.command(name="start")
    @checks.is_authorized()
    async def start_journey(self, ctx):
        user_id = str(ctx.author.id)
        
        # Whether they hold a LICENCE is the wrong question - !reset keeps the licence
        # and empties the roster, so asking that stranded reset trainers with no
        # specimens and no way to obtain one.
        async with aiosqlite.connect(DB_FILE) as db:
            allowed, reason = await may_choose_starter(db, user_id)

        if not allowed:
            if reason == 'spent':
                return await ctx.send(
                    "⚠️ Your roster is empty, but your licence has already been issued "
                    "a partner. Use `!reset` if you want to start over from scratch.")
            return await ctx.send(
                "⚠️ You are already a registered researcher! You cannot pick another starter.")

        # Spawn the interactive UI
        view = discord.ui.View()
        view.add_item(RegionSelect())
        
        embed = discord.Embed(
            title="🔬 Welcome to the Ecological Simulation", 
            description="To begin your fieldwork, you must select a symbiotic partner. First, choose a regional biome to view its native starters.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed, view=view)

    @commands.command(name="expedition", aliases=["travel", "explore"])
    @checks.has_started()
    @checks.is_authorized()
    async def start_expedition(self, ctx, *, biome_name: str = None):
        """Embark on a solo ecological expedition to a specific biome."""
        user_id = str(ctx.author.id)
        # The server the trip sets out from, whose ecosystem score scales the odds.
        # A DM has no guild; the rate helpers read a missing score as the baseline.
        guild_id = str(ctx.guild.id) if ctx.guild else None

        if not biome_name:
            return await ctx.send("🧭 **Navigation Error:** Please specify a biome (e.g., `!expedition canopy` or `!expedition trench`).")
            
        biome = biome_name.lower()
        
        # 1. Define the Biome Ecological Parameters (Elemental Types)
        biome_data = {
            'canopy': {'types': "('grass', 'bug', 'poison', 'flying', 'normal')", 'emoji': '🌲'},
            'trench': {'types': "('water', 'ice')", 'emoji': '🌊'},
            'core': {'types': "('fire', 'ground', 'rock', 'fighting')", 'emoji': '🌋'},
            'sprawl': {'types': "('electric', 'steel', 'dark', 'ghost', 'psychic', 'fairy')", 'emoji': '🏙️'},
            'apex': {'types': "('dragon')", 'emoji': '🐉'}
        }
        
        if biome not in biome_data:
            return await ctx.send("⚠️ Unknown biome. Available sectors: Canopy, Trench, Core, Sprawl.")
            
        # 2. Check if the user is already on an expedition
        # 🚨 UPDATED CHECK: Looks to see if their personal dictionary exists AND has active spawns in it
        if user_id in user_active_spawns and len(user_active_spawns[user_id]) > 0:
            return await ctx.send("🛑 You are already tracking a private spawn! Catch it first.")
        
        try:
            async with aiosqlite.connect(DB_FILE) as db:

                # 3. Verify Ecological Access (The Visa Check)
                async with db.execute("SELECT unlocked_visas FROM users WHERE user_id = ?", (user_id,)) as cursor:
                    user_data = await cursor.fetchone()
                
                # Default to canopy if they somehow don't have the column set
                visas = user_data[0] if user_data and user_data[0] else "canopy"
                
                if biome not in visas.split(','):
                    return await ctx.send(f"⛔ **ACCESS DENIED:** You do not have the required Visa for the **{biome.title()}**. Defeat the local Sector Warden to advance.")
                
                # 4. Generate the Biome-Specific Encounter (With Rarity Filter)
                type_tuple = biome_data[biome]['types']

                # The health of the server you set out FROM. An expedition is a private
                # trip, but it is a trip into this server's ecosystem - and reading the
                # score here is what stops a neglected habitat being farmed around by
                # everyone simply using `!expedition` instead.
                async with db.execute(
                        "SELECT ecosystem_score FROM servers WHERE guild_id = ?",
                        (guild_id,)) as cursor:
                    score_row = await cursor.fetchone()
                ecosystem_score = score_row[0] if score_row else None

                # Roll the ecological dice. An expedition is a deliberate trip
                # rather than an accident of conversation, so its rare tiers are a
                # little kinder than the habitat's - but they come from the same table,
                # and its legendary branch no longer forgets to exclude the mythicals.
                tier = roll_rarity(scaled_rarity(EXPEDITION_RARITY, ecosystem_score))

                def rarity_query(chosen):
                    return f"""
                        SELECT DISTINCT s.pokedex_id, s.name, s.capture_rate, s.gender_rate
                        FROM base_pokemon_species s
                        JOIN base_pokemon_types t ON s.pokedex_id = t.pokedex_id
                        WHERE t.type_name IN {type_tuple}
                        AND {spawnable_forms('s')}
                        {rarity_filter(chosen, 's')}
                        ORDER BY RANDOM() LIMIT 1
                    """

                async with db.execute(rarity_query(tier)) as cursor:
                    spawn_data = await cursor.fetchone()

                # A biome whose type pool holds nothing of the rolled tier - the Apex is
                # dragon-only - would otherwise answer "scanner error" and eat the trip.
                if not spawn_data and tier != 'wild':
                    tier = 'wild'
                    async with db.execute(rarity_query('wild')) as cursor:
                        spawn_data = await cursor.fetchone()
            
            if not spawn_data:
                return await ctx.send("📡 Scanner error: Could not locate native wildlife in this sector. Try again.")
                
            poke_id, poke_name, true_capture_rate, gender_rate = spawn_data
            gender = roll_gender(gender_rate, species_name=poke_name)
            
            # Roll for shiny. 1/4096 at a baseline habitat, up to 1.4x that at a
            # pristine one and the same factor down at a ruined one.
            is_shiny = roll_shiny(ecosystem_score)
            # Create a unique 6-character tracking ID for this specific specimen
            spawn_id = str(uuid.uuid4())[:6]

            if user_id not in user_active_spawns:
                user_active_spawns[user_id] = {}
            
            # 5. Lock the spawn to this specific user - and to this specific channel.
            #    A private encounter is still a message in a room; catching it from
            #    three channels away is the same disconnect as with a public spawn.
            user_active_spawns[user_id][spawn_id] = {
                'pokedex_id': poke_id,
                'name': poke_name,
                'is_shiny': is_shiny,
                'gender': gender,
                'capture_rate': true_capture_rate, # Dynamically assigned!
                'channel_id': ctx.channel.id
            }
            
            # 6. UI Output
            shiny_icon = "✨ " if is_shiny else ""
            b_emoji = biome_data[biome]['emoji']
            
            def mask_name(name):
                masked = ""
                for i, char in enumerate(name):
                    if char == "-":
                        masked += "- "
                    elif i == 0 or (i > 0 and name[i-1] == "-"):
                        masked += f"{char.upper()} "
                    else:
                        masked += "_ "
                return masked
            
            masked_display = mask_name(poke_name)
            embed = discord.Embed(
                title=f"{b_emoji} {biome.title()} Expedition",
                description=f"You traverse the environment and isolate a biological signal...\n\nA wild {shiny_icon}**`{masked_display}`** {gender_icon(gender)} appeared!",
                color=discord.Color.dark_green()
            )
            embed.set_footer(text="This encounter is yours. Pick a ball, or leave it.")
            
            # ==========================================
            # 4. LOCAL ASSET LOADING
            # ==========================================
            # Construct the safe OS path to your sprites
            # HOME art, falling through to the official artwork.
            safe_filename = sprite_attachment_name(poke_id, is_shiny, gender)
            file_path = resolve_sprite(poke_id, shiny=is_shiny, gender=gender, style=HOME)

            # Fallback Check: If the image is somehow missing from your folder, don't crash the bot!
            if not file_path:
                # You can point this to a default "missingno" or placeholder sprite if you have one
                print(f"⚠️ WARNING: no sprite anywhere for ID {poke_id}")
                sprite_file = None
            else:
                # Package the image as a discord File object
                sprite_file = discord.File(file_path, filename=safe_filename)
            # ==========================================
            
            # Mount the local image to the embed
            if sprite_file:
                embed.set_image(url=f"attachment://{safe_filename}")
                
            # The catch panel. Its timeout matches the despawn window, so the buttons
            # go quiet at the same moment the specimen does rather than a minute either
            # side of it - a live button on an expired encounter is the same confusing
            # bug report as a dead one on a live encounter.
            settings = await cfg.get_all(guild_id) if guild_id else {}
            despawn_after = settings.get('despawn_seconds') or 300
            panel = await build_encounter_view(user_id, spawn_id,
                                               timeout=despawn_after)

            # Send the message, passing BOTH the embed and the file object!
            if sprite_file:
                msg = await ctx.send(embed=embed, file=sprite_file, view=panel)
            else:
                msg = await ctx.send(embed=embed, view=panel)

            # Recorded AFTER the send, because the id does not exist until then -
            # it is what lets a successful catch go back and rewrite this card.
            user_active_spawns[user_id][spawn_id]['message_id'] = msg.id
            asyncio.create_task(self.spawn_timer(message=msg, spawn_id=spawn_id, pokemon_name=poke_name, user_id=user_id, config_guild=str(ctx.guild.id)))
        except Exception as e:
            print(f"Expedition Error: {e}")
            await ctx.send("❌ A critical error occurred during field deployment.")

    @commands.command(name="hint", aliases=["scan", "analyze_signal"])
    @checks.has_started()
    @checks.is_authorized()
    async def spawn_hint(self, ctx, lang_tag: str = "eng"):
        """Uses field sensors to gather data. (Optionally pass a language code like 'fr' or 'ja')"""
        guild_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)
        lang = lang_tag.upper()

        # 1. Read the sensors in THIS channel only.
        #
        # A hint is an answer to the masked name on screen, so it has to describe the
        # specimen on screen. Reading the newest spawn server-wide meant that in a
        # server with two habitat channels the hint routinely described the OTHER one -
        # and since the answer is what you then type into `!catch`, the hint was
        # actively sending people to the wrong room.
        #
        # The caller's own expedition encounter is checked first: it is theirs, it is
        # right here, and it was previously invisible to `!hint` altogether.
        here = ctx.channel.id

        def signals_here(store):
            return [data for data in (store or {}).values()
                    if isinstance(data, dict) and spawn_is_here(data, here)]

        mine = signals_here(user_active_spawns.get(user_id))
        public = signals_here(active_spawns.get(guild_id))

        if not mine and not public:
            return await ctx.send("📡 **Sensors Quiet:** There are no localized biological signals to analyze in this channel. Keep exploring!")

        # 🚨 The MOST RECENT signal in this channel, the caller's own encounter first.
        target = (mine or public)[-1]

        english_name = target['name'] 
        poke_id = target['pokedex_id']
        display_name = english_name # Default to English
        
        try:
            async with aiosqlite.connect(DB_FILE) as db:
                
                # 2. LOCALIZATION OVERRIDE
                if lang != "ENG":
                    async with db.execute("SELECT foreign_name FROM species_translations WHERE english_name = ? AND language_tag = ?", (english_name, lang)) as cursor:
                        trans_data = await cursor.fetchone()
                    if trans_data:
                        display_name = trans_data[0]
                    else:
                        await ctx.send(f"⚠️ *Sensor Warning: No telemetry data found for language code '{lang}'. Defaulting to ENG.*")
                
                # 3. Fetch Elemental Types
                async with db.execute("SELECT type_name FROM base_pokemon_types WHERE pokedex_id = ?", (poke_id,)) as cursor:
                    db_data = await cursor.fetchall()
                    
        except aiosqlite.OperationalError as e:
            print(f"Hint Query Error: {e}")
            db_data = [] 
            
        # Format the Types
        type_str = type_badges([row[0] for row in db_data])

        # 4. MASK THE DISPLAY NAME
        masked_name = ""
        for i, char in enumerate(display_name):
            if char == "-":
                masked_name += "- "
            elif i == 0 or (i > 0 and display_name[i-1] == "-"):
                masked_name += f"{char.upper()} "
            else:
                masked_name += "_ "
                
        # 5. Render the Dashboard
        embed = discord.Embed(
            title=f"📡 Biological Sensor Readout [{lang}]",
            description="Your field equipment has isolated the strongest unidentified signal nearby. Here is the partial telemetry data:",
            color=discord.Color.blue()
        )
        
        # No longer wrapped in backticks: a custom emoji inside a code span renders as
        # its raw `<:fire:123…>` text, which is the one place these badges CANNOT go.
        embed.add_field(name="Elemental Signature", value=type_str, inline=False)
        embed.add_field(name="Acoustic Syllable Profile", value=f"`{masked_name.strip()}`", inline=False)
        
        if target.get('is_shiny'):
            embed.set_footer(text="⚠️ ANOMALY DETECTED: The signal frequency exhibits a rare chromatic mutation!")
            
        await ctx.send(embed=embed)
    
    @commands.command(name="spawn", aliases=["force_spawn"])
    @commands.is_owner() # SECURITY: Only you can run this!
    async def force_spawn(self, ctx, target_species: str = None, force_shiny: bool = False):
        guild_id = str(ctx.guild.id)
        
        async with aiosqlite.connect(DB_FILE) as db:

            # 1. SPECIFIC TARGET INJECTION
            if target_species:
                target_clean = target_species.lower()
                
                # 🚨 UPDATED: Priority Sorting! Exact matches win, prefix matches randomize.
                query = """
                    SELECT pokedex_id, name, capture_rate, gender_rate
                    FROM base_pokemon_species
                    WHERE name = ? OR name LIKE ?
                    ORDER BY CASE WHEN name = ? THEN 0 ELSE 1 END, RANDOM() LIMIT 1;
                """
                # 🚨 Notice we pass target_clean THREE times now to satisfy the CASE WHEN statement!
                async with db.execute(query, (target_clean, f"{target_clean}-%", target_clean)) as cursor:
                    spawned_data = await cursor.fetchone()
                
                if not spawned_data:
                    await ctx.send(f"❌ Error: Could not locate `{target_species}` or any of its regional/morphological variants in the national database.")
                    return
                    
                rarity_name = "Admin-Injected"
                habitat_condition = "A localized spatial anomaly has occurred due to Director intervention."
                is_shiny = force_shiny
                
            # 2. NORMAL OVERRIDE (If no specific Pokemon is typed)
            else:
                async with db.execute("SELECT ecosystem_score, active_biome, pollution_type FROM servers WHERE guild_id = ?", (guild_id,)) as cursor:
                    server_data = await cursor.fetchone()
                
                ecosystem_score = server_data[0] if server_data else 50 
                active_biome = server_data[1] if server_data else 'forest'
                current_pollution = server_data[2] if server_data else 'none'

                # --- INVASIVE RIFT OVERRIDE ---
                if current_pollution == 'spatial_rift':
                    habitat_condition = "The local environment is being warped by invasive dimensional energy."
                    rarity_name = "🛸 ULTRA BEAST"
                    async with db.execute(f"SELECT pokedex_id, name, capture_rate, gender_rate FROM base_pokemon_species WHERE {ultra_beasts()} ORDER BY RANDOM() LIMIT 1;") as cursor:
                        spawned_data = await cursor.fetchone()
                else:
                    # --- STANDARD BIOME & POLLUTION LOGIC ---
                    if active_biome == 'urban': allowed_types = ['electric', 'steel', 'poison', 'normal']
                    elif active_biome == 'coastal': allowed_types = ['water', 'flying', 'ice', 'normal']
                    else: allowed_types = ['grass', 'bug', 'ground', 'normal']

                    if ecosystem_score < 30:
                        allowed_types = ['poison', 'dark', 'steel']
                        habitat_condition = f"The {active_biome} is degraded and covered in thick smog."
                    elif ecosystem_score > 70:
                        allowed_types.extend(['fairy', 'dragon', 'psychic'])
                        habitat_condition = f"The {active_biome} is pristine, vibrant, and bursting with life."
                    else:
                        habitat_condition = f"The {active_biome} ecosystem is perfectly stable."

                    # Rarity Roll - the same shared table the habitat spawner uses.
                    tier = roll_rarity(scaled_rarity(HABITAT_RARITY, ecosystem_score))
                    rarity_name = RARITY_LABELS[tier]

                    def rarity_query(chosen):
                        return f"""
                            SELECT s.pokedex_id, s.name, s.capture_rate, s.gender_rate
                            FROM base_pokemon_species s
                            JOIN base_pokemon_types t ON s.pokedex_id = t.pokedex_id
                            WHERE t.type_name IN ({','.join(['?']*len(allowed_types))})
                            AND {spawnable_forms('s')}
                            {rarity_filter(chosen, 's')} ORDER BY RANDOM() LIMIT 1;
                        """

                    async with db.execute(rarity_query(tier), allowed_types) as cursor:
                        spawned_data = await cursor.fetchone()

                    if not spawned_data and tier != 'wild':
                        tier, rarity_name = 'wild', RARITY_LABELS['wild']
                        async with db.execute(rarity_query('wild'),
                                              allowed_types) as cursor:
                            spawned_data = await cursor.fetchone()
                
                # The Genetic Mutation (Shiny) Roll
                is_shiny = roll_shiny(ecosystem_score)
        
        # 3. EXECUTE THE SPAWN
        if not spawned_data:
            return await ctx.send("The environment is currently too unstable to support life.")

        poke_id, name, cap_rate, gender_rate = spawned_data
        # Rolled HERE, not at capture. A spawn that shows a sex has to hand the
        # same one to the specimen that gets caught. The NAME is handed over too,
        # because a species whose name states a sex must not roll the other one.
        gender = roll_gender(gender_rate, species_name=name)
        
        # Ensure Ultra Beasts get a shiny roll too if it wasn't defined!
        if 'is_shiny' not in locals():
            is_shiny = roll_shiny(ecosystem_score)

        shiny_text = "🌟 **SHINY MUTATION** " if is_shiny else ""
        
        # ==========================================
        # 🚨 MULTI-SPAWN NESTED DICTIONARY UPDATE
        # ==========================================
        # Initialize dictionary if missing
        if guild_id not in active_spawns:
            active_spawns[guild_id] = {}
            
        spawn_id = str(uuid.uuid4())[:6]
        
        # Update the active spawns memory using the unique ID
        active_spawns[guild_id][spawn_id] = {
            'pokedex_id': poke_id, 'name': name, 'capture_rate': cap_rate,
            'is_shiny': is_shiny, 'gender': gender, 'channel_id': ctx.channel.id
        }
        
        # ==========================================
        # 4. LOCAL ASSET LOADING
        # ==========================================
        # Construct the safe OS path to your sprites
        # HOME art, falling through to the official artwork.
        embed_color = discord.Color.gold() if is_shiny else discord.Color.green()
        safe_filename = sprite_attachment_name(poke_id, is_shiny, gender)
        file_path = resolve_sprite(poke_id, shiny=is_shiny, gender=gender, style=HOME)

        # Fallback Check: If the image is somehow missing from your folder, don't crash the bot!
        if not file_path:
            print(f"⚠️ WARNING: no sprite anywhere for ID {poke_id}")
            sprite_file = None
        else:
            # Package the image as a discord File object
            sprite_file = discord.File(file_path, filename=safe_filename)
        # ==========================================

        def mask_name(name):
            masked = ""
            for i, char in enumerate(name):
                if char == "-":
                    masked += "- "
                elif i == 0 or (i > 0 and name[i-1] == "-"):
                    masked += f"{char.upper()} "
                else:
                    masked += "_ "
            return masked
        
        masked_display = mask_name(name)
        # Build the Visual Camera Trap Embed
        embed = discord.Embed(
            title=f"📸 Habitat Activity Detected!", 
            description=f"🌍 *{habitat_condition}*\n\nA {shiny_text}**{rarity_name} `{masked_display}`** {gender_icon(gender)} has migrated into the area!\n\nUse `!catch <pokemon>` to deploy equipment and rescue it.",
            color=embed_color
        )

        # Mount the local image to the embed
        if sprite_file:
            embed.set_image(url=f"attachment://{safe_filename}")
            
        embed.set_footer(text="Automated Field Camera Trap")
        
        # Send the message, passing BOTH the embed and the file object!
        if sprite_file:
            msg = await ctx.send(embed=embed, file=sprite_file)
        else:
            msg = await ctx.send(embed=embed)

        # Recorded AFTER the send, because the id does not exist until then -
        # it is what lets a successful catch go back and rewrite this card.
        active_spawns[guild_id][spawn_id]['message_id'] = msg.id
        asyncio.create_task(self.spawn_timer(message=msg, spawn_id=spawn_id, pokemon_name=name, guild_id=guild_id))

    @commands.command(name="nickname", aliases=["name"])
    @checks.has_started()
    @checks.is_authorized()
    async def nickname_pokemon(self, ctx, box_number: str, *, name: str):
        user_id = str(ctx.author.id)
        
        # 1. Strict Input Validation
        if not box_number.isdigit():
            return await ctx.send("⚠️ Please use the specimen's Box Number (e.g., `!nickname 4 Sparky`).")
            
        async with aiosqlite.connect(DB_FILE) as db:
            # 2. Resolve Target (Notice the 'cp' alias is fixed!)
            async with db.execute("""
                WITH Roster AS (
                    SELECT cp.instance_id, ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                    FROM caught_pokemon cp 
                    WHERE cp.user_id = ?
                    AND cp.instance_id NOT IN (SELECT instance_id FROM active_deployments)
                    AND cp.instance_id NOT IN (SELECT instance_id FROM gts_deposits)
                ) SELECT instance_id FROM Roster WHERE box_number = ?
            """, (user_id, int(box_number))) as cursor:
                target = await cursor.fetchone()  
            
            if not target:
                return await ctx.send(f"❌ Could not find a specimen in Box `#{box_number}`.")
                
            actual_id = target[0]
            
            # 3. Execute Update
            await db.execute("UPDATE caught_pokemon SET nickname = ? WHERE instance_id = ?", (name, actual_id))
            await db.commit()
        
        await ctx.send(f"🏷️ Specimen `{actual_id[:8]}` has been successfully re-designated as **{name}**.")

    @commands.command(name="release", aliases=["reintroduce", "free"])
    @checks.has_started()
    @checks.is_not_in_trade()
    @checks.is_authorized()
    async def release_pokemon(self, ctx, box_number: str):
        user_id = str(ctx.author.id)
        
        if not box_number.isdigit():
            return await ctx.send("⚠️ Please use the specimen's Box Number (e.g., `!release 4`).")
            
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute("""
                WITH Roster AS (
                    SELECT s.name, cp.level, cp.instance_id, ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                    FROM caught_pokemon cp
                    JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                    WHERE cp.user_id = ?
                    AND cp.instance_id NOT IN (SELECT instance_id FROM active_deployments)
                    AND cp.instance_id NOT IN (SELECT instance_id FROM gts_deposits)
                ) SELECT name, level, instance_id FROM Roster WHERE box_number = ?
            """, (user_id, int(box_number))) as cursor:
                pokemon = await cursor.fetchone()
            
            if not pokemon:
                return await ctx.send(f"❌ Could not find a specimen in Box `#{box_number}`.")
                
            name, level, actual_tag = pokemon
            
            async with db.execute("SELECT active_partner FROM users WHERE user_id = ?", (user_id,)) as cursor:
                partner_data = await cursor.fetchone()
            
            if partner_data and partner_data[0] == actual_tag:
                return await ctx.send("⚠️ You cannot release your Active Partner! Use `!partner` to assign a new lead researcher first.")

            async with db.execute("SELECT slot FROM user_party WHERE user_id = ? AND instance_id = ?", (user_id, actual_tag)) as cursor:
                party_data = await cursor.fetchone()
            
            if party_data:
                return await ctx.send(f"🛡️ **Safety Lock:** You cannot release a specimen that is actively deployed in your fieldwork roster (Slot {party_data[0]}). Please remove it from your party first.")

        # --- Trigger the Confirmation UI ---
        view = ReleaseConfirmView(ctx, DB_FILE, pokemon, user_id)
        embed = discord.Embed(
            title="⚠️ Confirm Reintroduction", 
            description=f"Are you sure you want to release **{name.capitalize()}** (Lv. {level})?\n\n*This action is permanent and cannot be undone.*",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, view=view)

    @commands.command(name="settag", aliases=["label"])
    @checks.has_started()
    @checks.is_authorized()
    async def set_custom_tag(self, ctx, box_number: str, *, custom_tag: str):
        user_id = str(ctx.author.id)
        
        # 1. Strict Input Validation
        if not box_number.isdigit():
            return await ctx.send("⚠️ Please use the specimen's Box Number (e.g., `!settag 4 Favorite`).")
            
        async with aiosqlite.connect(DB_FILE) as db:
            # 2. Resolve Target
            async with db.execute("""
                WITH Roster AS (
                    SELECT cp.instance_id, ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                    FROM caught_pokemon cp 
                    WHERE cp.user_id = ?
                    AND cp.instance_id NOT IN (SELECT instance_id FROM active_deployments)
                    AND cp.instance_id NOT IN (SELECT instance_id FROM gts_deposits)
                ) SELECT instance_id FROM Roster WHERE box_number = ?
            """, (user_id, int(box_number))) as cursor:
                target = await cursor.fetchone()
            
            if not target:
                return await ctx.send(f"❌ Could not find a specimen in Box `#{box_number}`.")
                
            actual_id = target[0]
            
            # 3. Execute Update
            async with db.execute("UPDATE caught_pokemon SET custom_tag = ? WHERE instance_id = ?", (custom_tag, actual_id)) as cursor:
                if cursor.rowcount > 0:
                    await ctx.send(f"📁 Specimen `{actual_id[:8]}` has been categorized under the tag: **[{custom_tag}]**.")
            
            await db.commit()

    @commands.command(name="partner", aliases=["select"])
    @checks.has_started()
    @checks.is_authorized()
    async def set_partner(self, ctx, tag_id: str):
        user_id = str(ctx.author.id)
        
        async with aiosqlite.connect(DB_FILE) as db:

            # Verify ownership and resolve target
            if tag_id.isdigit() and len(tag_id) <= 6:
                async with db.execute("""
                    WITH Roster AS (
                        SELECT cp.instance_id, s.name, ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                        FROM caught_pokemon cp
                        JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                        WHERE cp.user_id = ?
                        AND cp.instance_id NOT IN (SELECT instance_id FROM active_deployments)
                        AND cp.instance_id NOT IN (SELECT instance_id FROM gts_deposits)
                    ) SELECT name, instance_id FROM Roster WHERE box_number = ?
                """, (user_id, int(tag_id))) as cursor:
                    pokemon = await cursor.fetchone()
            else:
                async with db.execute("""
                    SELECT s.name, cp.instance_id
                    FROM caught_pokemon cp
                    JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                    WHERE cp.instance_id LIKE ? AND cp.user_id = ?
                """, (f"{tag_id}%", user_id)) as cursor:
                    pokemon = await cursor.fetchone()
            
            if not pokemon:
                await ctx.send(f"❌ Could not find a specimen matching `{tag_id}` in your survey notebook.")
                return
                
            name, actual_tag = pokemon
            
            # ==========================================
            # 🚨 NEW: DEPLOYMENT LOCKOUT CHECK
            # ==========================================
            async with db.execute("SELECT start_time FROM active_deployments WHERE instance_id = ?", (actual_tag,)) as cursor:
                if await cursor.fetchone():
                    return await ctx.send(f"⚠️ You cannot equip **{name.capitalize()}** right now, they are currently deployed on a field mission!")
            
            try:
                await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
                await db.execute("UPDATE users SET active_partner = ? WHERE user_id = ?", (actual_tag, user_id))
                await db.commit()
                
                await ctx.send(f"❤️ You have chosen **{name.capitalize()}** (`{actual_tag[:8]}`) as your lead fieldwork partner!")
            except Exception as e:
                await ctx.send("❌ A database error occurred while setting your partner.")
                print(f"Partner error: {e}")

    @commands.command(name="intervene", aliases=["respond"])
    @checks.has_started()
    @checks.is_authorized()
    async def intervene(self, ctx, tag_id: str):
        guild_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)
        
        async with aiosqlite.connect(DB_FILE) as db:

            # 1. Check if the server is actually in crisis
            async with db.execute("SELECT pollution_type, ecosystem_score FROM servers WHERE guild_id = ?", (guild_id,)) as cursor:
                server_data = await cursor.fetchone()
            
            if not server_data or server_data[0] == 'none':
                await ctx.send("🌍 The environment is currently stable! Keep an eye on the monitors for future hazards.")
                return
                
            active_hazard = server_data[0]
            current_score = server_data[1]
            
            # 2. Verify ownership and fetch the deployed Pokemon's types
            if tag_id.isdigit() and len(tag_id) <= 6:
                async with db.execute("""
                    WITH Roster AS (
                        SELECT cp.pokedex_id, cp.instance_id, s.name, ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                        FROM caught_pokemon cp
                        JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                        WHERE cp.user_id = ?
                        AND cp.instance_id NOT IN (SELECT instance_id FROM active_deployments)
                        AND cp.instance_id NOT IN (SELECT instance_id FROM gts_deposits)
                    )
                    -- 🚨 ADDED r.instance_id HERE
                    SELECT r.name, t.type_name, r.instance_id 
                    FROM Roster r
                    JOIN base_pokemon_types t ON r.pokedex_id = t.pokedex_id
                    WHERE r.box_number = ?
                """, (user_id, int(tag_id))) as cursor:
                    rows = await cursor.fetchall()
            else:
                async with db.execute("""
                    -- 🚨 ADDED cp.instance_id HERE
                    SELECT s.name, t.type_name, cp.instance_id 
                    FROM caught_pokemon cp
                    JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                    JOIN base_pokemon_types t ON s.pokedex_id = t.pokedex_id
                    WHERE cp.instance_id LIKE ? AND cp.user_id = ?
                """, (f"{tag_id}%", user_id)) as cursor:
                    rows = await cursor.fetchall()
                    
            if not rows:
                await ctx.send("❌ You don't have that specimen in your survey notebook.")
                return
                
            poke_name = rows[0][0]
            actual_id = rows[0][2] # 🚨 Extract the newly added Instance ID!
            poke_types = [row[1] for row in rows]
            
            # ==========================================
            # 🚨 NEW: DEPLOYMENT LOCKOUT CHECK
            # ==========================================
            async with db.execute("SELECT start_time FROM active_deployments WHERE instance_id = ?", (actual_id,)) as cursor:
                if await cursor.fetchone():
                    return await ctx.send(f"⚠️ You cannot deploy **{poke_name.capitalize()}** to intervene right now, they are currently on a field mission!")
            
            # 3. Type-Match Logic
            solutions = {
                'oil_spill': ['poison', 'water', 'grass'],
                'toxic_smog': ['flying', 'electric', 'steel', 'poison'],
                'wildfire': ['water', 'ground', 'rock'],
                'spatial_rift': ['psychic', 'ghost', 'dark', 'fairy']
            }
            
            valid_types = solutions.get(active_hazard, [])
            is_effective = any(pt in valid_types for pt in poke_types)
            
            if not is_effective:
                await ctx.send(f"⚠️ **Ineffective!** Your {poke_name.capitalize()} isn't biologically equipped to handle a **{active_hazard.replace('_', ' ').title()}**! You need a type like {', '.join(valid_types).title()}.")
                return

            # 4. Success! Clear the hazard and reward the player
            new_score = min(100, current_score + 20)
            tokens_earned = 50 
            
            try:
                await db.execute("UPDATE servers SET pollution_type = 'none', ecosystem_score = ? WHERE guild_id = ?", (new_score, guild_id))
                await db.execute("UPDATE users SET eco_tokens = eco_tokens + ? WHERE user_id = ?", (tokens_earned, user_id))
                await db.execute("""
                    INSERT INTO guild_members (user_id, guild_id, contribution_points)
                    VALUES (?, ?, 10)
                    ON CONFLICT(user_id, guild_id) DO UPDATE SET contribution_points = contribution_points + 10;
                """, (user_id, guild_id))
                
                await db.commit()
                
                embed = discord.Embed(title="🚨 Crisis Averted!", color=discord.Color.gold())
                embed.description = f"**{ctx.author.name}** deployed their {poke_name.capitalize()}!\n\nUsing its typing, it completely neutralized the **{active_hazard.replace('_', ' ').title()}**!"
                embed.add_field(name="Ecosystem Recovery", value=f"⬆️ +20 Points (Now {new_score}/100)", inline=True)
                embed.add_field(name="Hero's Grant", value=f"🪙 +{tokens_earned} Tokens\n⭐ +10 Contribution", inline=True)
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                print(f"Intervention error: {e}")

    @commands.command(name="use")
    @checks.has_started()
    @checks.is_authorized()
    async def use_item(self, ctx, *, item_input: str):
        # --- DATA SANITIZATION ---
        formatted_item = item_input.strip().lower().replace(" ", "").replace("-", "")
        
        guild_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)
        
        async with aiosqlite.connect(DB_FILE) as db:
            try:
                # 1. Global Inventory Check (Saves us from writing this for every single item!)
                async with db.execute("SELECT quantity FROM user_inventory WHERE user_id = ? AND item_name = ?", (user_id, formatted_item)) as cursor:
                    inv_data = await cursor.fetchone()
                
                if not inv_data or inv_data[0] < 1:
                    return await ctx.send(f"🎒 You don't have any `{item_input.title()}` in your field pack!")

                # ==========================================
                # 2. ITEM ROUTING LOGIC (The Dispatcher)
                # ==========================================
                
                if formatted_item == "purifier":
                    # Check if the server actually needs purifying
                    async with db.execute("SELECT pollution_type, ecosystem_score FROM servers WHERE guild_id = ?", (guild_id,)) as cursor:
                        server_data = await cursor.fetchone()
                    
                    if not server_data or server_data[0] == 'none':
                        return await ctx.send("🌍 This environment is already clear of major hazards! Save your Purifier for an emergency.")
                        
                    pollution = server_data[0]
                    current_score = server_data[1]
                    
                    # Deduct from inventory (Using formatted_item instead of hardcoding)
                    await db.execute("UPDATE user_inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_name = ?", (user_id, formatted_item))
                    
                    # Clear pollution and boost score by 15 (capping at 100)
                    new_score = min(100, current_score + 15)
                    await db.execute("""
                        UPDATE servers 
                        SET pollution_type = 'none', ecosystem_score = ?, last_maintained = CURRENT_TIMESTAMP 
                        WHERE guild_id = ?
                    """, (new_score, guild_id))
                    
                    # Reward the player
                    await db.execute("""
                        INSERT INTO guild_members (user_id, guild_id, contribution_points)
                        VALUES (?, ?, 5)
                        ON CONFLICT(user_id, guild_id) DO UPDATE SET contribution_points = contribution_points + 5;
                    """, (user_id, guild_id))
                    
                    await db.commit()
                    
                    embed = discord.Embed(title="🫧 Environmental Hazard Cleared!", color=discord.Color.blue())
                    embed.description = f"**{ctx.author.name}** deployed a Purifier and successfully eradicated the **{pollution.replace('_', ' ').title()}**!"
                    embed.add_field(name="Ecosystem Health", value=f"⬆️ +15 Points (Now {new_score}/100)", inline=True)
                    embed.add_field(name="Community Impact", value="⭐ +5 Contribution Points", inline=True)
                    
                    await ctx.send(embed=embed)

                # --- INVALID DEPLOYMENT ---
                else:
                    return await ctx.send(f"⚠️ `{item_input.title()}` is a passive item and cannot be deployed directly from the backpack.")

            except Exception as e:
                if db.in_transaction:
                    await db.rollback()
                print(f"Error deploying item: {e}")
                await ctx.send("An error occurred while deploying the item. No items were consumed.")

    # --- Setup Habitat Channel ---
    @commands.command(name="sethabitat")
    @checks.has_started()
    @checks.is_authorized()
    @commands.has_permissions(manage_channels=True)
    async def set_habitat(self, ctx):
        guild_id = str(ctx.guild.id)
        channel_id = str(ctx.channel.id)
        
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute("INSERT OR IGNORE INTO servers (guild_id) VALUES (?)", (guild_id,))
            await db.execute("UPDATE servers SET spawn_channel_id = ? WHERE guild_id = ?", (channel_id, guild_id))
            await db.commit()
        
        await ctx.send(f"🌿 Habitat established! Wild Pokémon will now naturally migrate to {ctx.channel.mention} over time.")


    @commands.command(name="terraform")
    @checks.has_started()
    @checks.is_authorized()
    async def terraform(self, ctx, biome_type: str = ""):
        if biome_type.lower() != "urban":
            await ctx.send("Right now, you can only use `!terraform urban` to build city infrastructure.")
            return
            
        await self.execute_biome_shift(ctx, "urban", "🏙️ Urbanization Complete", "The server has been terraformed into a sprawling Urban biome! Electric, Steel, and Poison types will now migrate here.")

    @commands.command(name="purify_water", aliases=["purify"])
    @checks.has_started()
    @checks.is_authorized()
    async def purify_water(self, ctx):
        await self.execute_biome_shift(ctx, "coastal", "🌊 Water Purification Complete", "The local waters have been purified, creating a beautiful Coastal biome! Water and Flying types will now flock here.")

    @commands.command(name="plant_trees", aliases=["reforest"])
    @checks.has_started()
    @checks.is_authorized()
    async def plant_trees(self, ctx):
        await self.execute_biome_shift(ctx, "forest", "🌲 Reforestation Complete", "Native saplings have been planted, restoring the area to a dense Forest biome! Grass and Bug types will return to the habitat.")


    @commands.command(name="plant", aliases=["sow"])
    @commands.cooldown(1, 300, commands.BucketType.user)
    @checks.has_started()
    @checks.is_authorized()
    async def plant_flora(self, ctx):
        guild_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)
        
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute("SELECT ecosystem_score FROM servers WHERE guild_id = ?", (guild_id,)) as cursor:
                server_data = await cursor.fetchone()
            score = server_data[0] if server_data else 50
                
            if score >= 100:
                ctx.command.reset_cooldown(ctx)
                await ctx.send("🌍 The ecosystem is already fully saturated with flora! Great job.")
                return

            # Planting restores 1 to 3 health points, but gives a higher chance of rare spawns later
            health_restored = random.randint(1, 3)
            new_score = min(100, score + health_restored) 
            
            # Planting yields slightly fewer tokens than cleaning (5 to 15)
            tokens_earned = random.randint(5, 15)
            
            try:
                await db.execute("UPDATE servers SET ecosystem_score = ? WHERE guild_id = ?", (new_score, guild_id))
                await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
                await db.execute("UPDATE users SET eco_tokens = eco_tokens + ? WHERE user_id = ?", (tokens_earned, user_id))
                
                await db.execute("""
                    INSERT INTO guild_members (user_id, guild_id, contribution_points)
                    VALUES (?, ?, 1)
                    ON CONFLICT(user_id, guild_id) DO UPDATE SET contribution_points = contribution_points + 1;
                """, (user_id, guild_id))
                
                await db.commit()
                
                embed = discord.Embed(title="🌱 Flora Restoration Logged", color=discord.Color.dark_green())
                embed.description = f"**{ctx.author.name}** planted native species to stabilize the soil and increase biodiversity!"
                embed.add_field(name="Ecosystem Health", value=f"⬆️ +{health_restored} (Now {new_score}/100)", inline=True)
                embed.add_field(name="Field Pay", value=f"🪙 +{tokens_earned} Eco-Tokens", inline=True)
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                print(e)

    @commands.command(name="clean", aliases=["remediate"])
    @commands.cooldown(1, 300, commands.BucketType.user)
    @checks.has_started()
    @checks.is_authorized()
    async def clean_habitat(self, ctx):
        guild_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)
        
        async with aiosqlite.connect(DB_FILE) as db:
            # 1. Check current server status
            async with db.execute("SELECT ecosystem_score, pollution_type FROM servers WHERE guild_id = ?", (guild_id,)) as cursor:
                server_data = await cursor.fetchone()
            
            if not server_data:
                await db.execute("INSERT INTO servers (guild_id, ecosystem_score) VALUES (?, 50)", (guild_id,))
                score = 50
                pollution = 'none'
            else:
                score, pollution = server_data
                
            if score >= 100:
                ctx.command.reset_cooldown(ctx)
                await ctx.send("🌍 The ecosystem here is already at 100% pristine health! Try `!plant` to maintain it, or visit another server.")
                return

            # 2. Calculate Restoration and Standard Rewards
            health_restored = random.randint(2, 5)
            new_score = min(100, score + health_restored) 
            tokens_earned = random.randint(10, 20)
            
            # 3. Calculate XP & Rare Item Drops
            xp_gained = random.randint(50, 150) # Generous XP for helping out!
            found_item = None
            active_partner_id = None
            partner_name = "Unknown"
            
            # Query the active partner
            async with db.execute("SELECT active_partner FROM users WHERE user_id = ?", (user_id,)) as cursor:
                partner_data = await cursor.fetchone()
            
            if partner_data and partner_data[0]:
                active_partner_id = partner_data[0]

                # ==========================================
                # 🚨 NEW: DEPLOYMENT LOCKOUT FAIL-SAFE
                # ==========================================
                async with db.execute("SELECT start_time FROM active_deployments WHERE instance_id = ?", (active_partner_id,)) as cursor:
                    if await cursor.fetchone():
                        return await ctx.send("⚠️ Your Active Partner is currently deployed on a field mission! Recall them with `!return` or equip a different specimen first.")
                    
                # Grab the partner's name for the UI
                async with db.execute("SELECT s.name FROM caught_pokemon cp JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id WHERE cp.instance_id = ?", (active_partner_id,)) as cursor:
                    name_data = await cursor.fetchone()
                    if name_data:
                        partner_name = name_data[0].capitalize()

            # 5% chance to find something incredibly rare in the pollution
            if random.random() <= 0.05:
                rare_pool = ['rare-candy', 'reveal-glass', 'dna-splicers']
                found_item = random.choice(rare_pool)
            
            # 4. Update the Database
            try:
                await db.execute("UPDATE servers SET ecosystem_score = ? WHERE guild_id = ?", (new_score, guild_id))
                await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
                await db.execute("UPDATE users SET eco_tokens = eco_tokens + ? WHERE user_id = ?", (tokens_earned, user_id))
                
                await db.execute("""
                    INSERT INTO guild_members (user_id, guild_id, contribution_points)
                    VALUES (?, ?, 1)
                    ON CONFLICT(user_id, guild_id) DO UPDATE SET contribution_points = contribution_points + 1;
                """, (user_id, guild_id))
                
                # Apply the XP!
                if active_partner_id:
                    await db.execute("UPDATE caught_pokemon SET experience = experience + ? WHERE instance_id = ?", (xp_gained, active_partner_id))
                    
                # Apply the Item!
                if found_item:
                    await db.execute("""
                        INSERT INTO user_inventory (user_id, item_name, quantity) 
                        VALUES (?, ?, 1) 
                        ON CONFLICT(user_id, item_name) 
                        DO UPDATE SET quantity = quantity + 1
                    """, (user_id, found_item))

                await db.commit()
                
                # 5. Send the Report
                embed = discord.Embed(title="🧹 Habitat Remediation Successful", color=discord.Color.teal())
                embed.description = f"**{ctx.author.name}** spent an hour cleaning up the local environment!"
                embed.add_field(name="Ecosystem Health", value=f"⬆️ +{health_restored} (Now {new_score}/100)", inline=True)
                embed.add_field(name="Field Pay", value=f"🪙 +{tokens_earned} Eco-Tokens", inline=True)
                
                # Add the XP line if they had a partner
                if active_partner_id:
                    embed.add_field(name="Training", value=f"✨ {partner_name} gained {xp_gained} XP!", inline=False)
                    
                # Add the Rare Item line
                if found_item:
                    embed.add_field(name="⚠️ RARE DISCOVERY", value=f"You unearthed a `{found_item.replace('-', ' ').title()}` from the debris!", inline=False)
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send("Database error during the cleaning process.")
                print(e)

    @commands.command(name="abandon", aliases=["drop", "discard", "archive"])
    @checks.has_started()
    @checks.is_authorized()
    async def abandon_directive(self, ctx, *, request: str = None):
        """Drops directives. `!abandon` opens a picker; `!abandon 4 7` drops those two."""
        user_id = str(ctx.author.id)

        async with aiosqlite.connect(DB_FILE) as db:
            try:
                async with db.execute("""
                    SELECT directive_id, objective_type, target_variable,
                           required_amount, current_progress
                    FROM field_directives
                    WHERE user_id = ? AND is_completed = 0
                    ORDER BY directive_id ASC
                """, (user_id,)) as cursor:
                    directives = await cursor.fetchall()
            except Exception as e:
                print(f"Abandon error: {e}")
                return await ctx.send("\u274c A critical database error occurred while trying to drop the directive.")

        if not directives:
            return await ctx.send("\U0001f4cb Your field notebook is empty \u2014 there is nothing to abandon.")

        held = [row[0] for row in directives]
        wanted, problem = parse_abandon_request(request, held)
        if problem:
            return await ctx.send(problem)

        # No ids given: open the picker rather than guessing. This is also the only way
        # to work through a notebook of twenty without typing twenty numbers.
        if wanted is None:
            panel = AbandonPanel(self, ctx, directives)
            panel.message = await ctx.send(embed=panel.summary(), view=panel)
            return

        dropped = await drop_directives(user_id, wanted)
        await ctx.send(embed=archive_result(dropped))

    @commands.command(name="survey", aliases=["quests", "directives", "tasks"])
    @checks.has_started()
    @checks.is_authorized()
    async def field_survey(self, ctx, directive_id: int = None):
        """Your active field directives. `!survey 14` opens that one directly."""
        user_id = str(ctx.author.id)

        async with aiosqlite.connect(DB_FILE) as db:

            try:
                # Ordered, so the menu, the page numbers and `!analyze`'s summary all
                # count the same way. Without it SQLite is free to change its mind.
                async with db.execute("""
                    SELECT directive_id, objective_type, target_variable, required_amount,
                        current_progress, reward_type, reward_payload
                    FROM field_directives
                    WHERE user_id = ? AND is_completed = 0
                    ORDER BY directive_id ASC
                """, (user_id,)) as cursor:
                    directives = await cursor.fetchall()

                if not directives:
                    return await ctx.send("📋 **Field Notebook Empty:** You have no active ecological directives at this time. Explore the ecosystem to find encrypted data!")

                # `!survey 14` names the SAME number `!abandon 14` takes. Deliberately
                # not a page number: two numberings for one list is how somebody
                # abandons the wrong directive.
                start = 0
                if directive_id is not None:
                    ids = [row[0] for row in directives]
                    if directive_id not in ids:
                        listed = ", ".join(f"`{i}`" for i in ids[:20])
                        return await ctx.send(
                            f"⚠️ **Directive #{directive_id}** is not in your notebook. "
                            f"You have: {listed}"
                            + ("…" if len(ids) > 20 else ""))
                    start = ids.index(directive_id)

                # Launch the Paginator!
                view = SurveyPaginator(user_id, directives, start_index=start)
                embed = await view.generate_embed()

                await ctx.send(embed=embed, view=view)

            except Exception as e:
                print(f"Survey UI Error: {e}")
                await ctx.send("❌ Error accessing the laboratory database.")

    def get_daily_missions(self):
        """Generates a consistent daily list of available missions based on the calendar date."""
        # Create a unique string for today (e.g., "2026-04-04")
        today_str = datetime.date.today().isoformat()
        
        # Create an isolated random generator so we don't mess with the bot's normal RNG!
        daily_rng = random.Random(today_str) 
        
        # Separate our master dictionary into pools
        exp_pool = [k for k, v in FIELD_MISSIONS.items() if v["category"] == "exp"]
        ev_pool = [k for k, v in FIELD_MISSIONS.items() if v["category"] == "ev"]
        
        # Pick 2 random EXP missions and 3 random EV missions for today's board
        todays_exp = daily_rng.sample(exp_pool, 2)
        todays_ev = daily_rng.sample(ev_pool, 3)
        
        return todays_exp + todays_ev # Returns a list of job IDs like ['reef', 'power', 'hp', 'speed', 'attack']

    @commands.command(name="jobs", aliases=["missions", "board"])
    @checks.has_started()
    @checks.is_authorized()
    async def view_mission_board(self, ctx):
        """Displays today's rotating Field Missions and PokéJobs."""
        
        todays_active_ids = self.get_daily_missions()
        
        embed = discord.Embed(
            title="📋 Daily Fieldwork Board",
            description="Deploy your specimens using `!deploy <job_id> <box_numbers>`.\nExample: `!deploy reef 4, 7, 12`\n\n*Missions rotate every day at midnight!*",
            color=discord.Color.gold()
        )
        
        exp_text = ""
        ev_text = ""
        
        # Only loop through the ones chosen for today!
        for job_id in todays_active_ids:
            data = FIELD_MISSIONS[job_id]
            
            if data["category"] == "exp":
                exp_text += f"**ID:** `{job_id}` — {data['name']}\n"
                exp_text += f"└ *{data['desc']}*\n"
                exp_text += f"└ 💡 **Advantage:** {data['preferred_type'].title()} types earn +20% XP!\n\n"
            elif data["category"] == "ev":
                stat_name = data["target_ev"].replace("ev_", "").upper()
                ev_text += f"**ID:** `{job_id}` — {data['name']}\n"
                ev_text += f"└ 🏋️ **Yield:** +{data['ev_hr']} {stat_name} EVs / hour\n\n"
                
        embed.add_field(name="🌍 Ecological Surveys (XP Gain)", value=exp_text if exp_text else "None available.", inline=False)
        embed.add_field(name="💪 Intensive Training (EV Gain)", value=ev_text if ev_text else "None available.", inline=False)
        
        embed.set_footer(text="Missions also yield rare items like Evolution Stones and Special Balls!")
        
        await ctx.send(embed=embed)

    # "find pokemon" used to sit in this list. An alias containing a space can never be
    # reached - the parser splits on whitespace first - so it was decoration.
    @commands.command(name="inventory", aliases=["inv", "box", "pc"])
    @checks.has_started()
    @checks.is_authorized()
    async def inventory(self, ctx, *, search_query: str = ""):
        user_id = str(ctx.author.id)
        
        # 1. Base CTE Parameters (This ensures Box Numbers are mapped correctly!)
        cte_params = [user_id]
        
        # 2. Dynamic Outer Filters
        outer_where_clauses = ["1=1"] # Default to true so we can easily append with AND
        outer_params = []
        order_clause = "ORDER BY cp.box_number ASC"
        
        # --- The Smart Parser ---
        if search_query:
            args = search_query.lower().split()
            for arg in args:
                # 🏷️ TAG FILTER
                if arg.startswith("tag:") or arg.startswith("label:"):
                    val = arg.split(":")[1]
                    outer_where_clauses.append("LOWER(cp.custom_tag) = ?")
                    outer_params.append(val)
                    
                # 💧 TYPE FILTER 
                elif arg.startswith("type:"):
                    val = arg.split(":")[1]
                    outer_where_clauses.append("EXISTS (SELECT 1 FROM base_pokemon_types t WHERE t.pokedex_id = cp.pokedex_id AND LOWER(t.type_name) = ?)")
                    outer_params.append(val)
                    
                # ✨ SHINY FILTER
                elif arg in ["shiny", "is:shiny"]:
                    outer_where_clauses.append("cp.is_shiny = 1")
                    
                # 🔀 SORTING
                elif arg.startswith("sort:"):
                    val = arg.split(":")[1]
                    if val in ["iv", "ivs", "stats"]:
                        order_clause = "ORDER BY (cp.iv_hp + cp.iv_attack + cp.iv_defense + cp.iv_sp_atk + cp.iv_sp_def + cp.iv_speed) DESC"
                    elif val in ["name", "az"]:
                        order_clause = "ORDER BY COALESCE(cp.nickname, cp.name) ASC"
                    elif val in ["tag", "label"]:
                        order_clause = "ORDER BY cp.custom_tag DESC, cp.box_number DESC"
                    elif val in ["desc", "new"]:
                        order_clause = "ORDER BY cp.box_number DESC"
                        
                # 🔍 NAME SEARCH (Fixed the alias crash!)
                elif ":" not in arg:
                    outer_where_clauses.append("(LOWER(cp.name) LIKE ? OR LOWER(cp.nickname) LIKE ?)")
                    outer_params.extend([f"%{arg}%", f"%{arg}%"])

        outer_where_string = " AND ".join(outer_where_clauses)
        final_params = cte_params + outer_params # Combine CTE params with the Outer params

        try:
            async with aiosqlite.connect(DB_FILE) as db:
                async with db.execute("SELECT eco_tokens FROM users WHERE user_id = ?", (user_id,)) as cursor:
                    user_data = await cursor.fetchone()
                tokens = user_data[0] if user_data else 0

                # --- The Anchored Query ---
                query = f"""
                    WITH AnchoredRoster AS (
                        SELECT 
                            s.name, cp.level, cp.is_shiny, cp.instance_id, 
                            cp.nickname, cp.custom_tag, cp.pokedex_id, cp.user_id,
                            cp.iv_hp, cp.iv_attack, cp.iv_defense, cp.iv_sp_atk, cp.iv_sp_def, cp.iv_speed,
                            ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                        FROM caught_pokemon cp
                        JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                        WHERE cp.user_id = ? 
                        AND cp.instance_id NOT IN (SELECT instance_id FROM active_deployments)
                        AND cp.instance_id NOT IN (SELECT instance_id FROM gts_deposits)
                    )
                    SELECT 
                        cp.name, cp.level, cp.is_shiny, cp.instance_id, cp.nickname, cp.custom_tag,
                        cp.iv_hp, cp.iv_attack, cp.iv_defense, cp.iv_sp_atk, cp.iv_sp_def, cp.iv_speed, cp.box_number
                    FROM AnchoredRoster cp
                    WHERE {outer_where_string}
                    {order_clause}
                """
                
                async with db.execute(query, final_params) as cursor:
                    rows = await cursor.fetchall()
                    
        except Exception as e:
            print(f"🚨 SQL ERROR IN PC COMMAND: {e}")
            return await ctx.send("❌ A database error occurred while filtering your PC. Please check your search terms.")
            
        # --- Formatting the Output ---
        if not rows:
            return await ctx.send("🎒 No specimens match your search filters!")
        
        lines = []
        for row in rows:
            species_name, level, is_shiny, tag_id, nickname, custom_tag = row[0:6]
            iv_tuple = row[6:12]
            box_number = row[12] 
            
            iv_total = sum(iv_tuple)
            iv_percentage = int((iv_total / 186.0) * 100)
            
            display_name = f'"{nickname}" ({species_name.capitalize()})' if nickname else species_name.capitalize()
            shiny_icon = "🌟" if is_shiny else "🌿"
            tag_display = f" `[{custom_tag}]`" if custom_tag else ""
            
            line = f"**#{box_number}** | {shiny_icon} **{display_name}** | Lvl {level} | IV: {iv_percentage}% | Tag: `{tag_id[:8]}`{tag_display}"
            lines.append(line)
  
        view = InventoryPaginator(ctx, lines, tokens)
        initial_embed = view.create_embed()
        
        if search_query:
            initial_embed.title = f"📋 Filtered Survey Results"
            initial_embed.set_footer(text=f"Filter: '{search_query}' | " + initial_embed.footer.text)
            
        await ctx.send(embed=initial_embed, view=view)

    @commands.command(name="catch")
    @checks.has_started()
    @checks.is_authorized()
    async def catch_pokemon(self, ctx, *, full_input: str = None):
        
        if not full_input:
            return await ctx.send("🎒 You need to specify a target! Example: `!catch pikachu` or `!catch pikachu greatball`")

        try:
            guild_id = str(ctx.guild.id)
            user_id = str(ctx.author.id)

            # 1. THE PARSER
            input_words = full_input.strip().lower().split()
            ball_type = None 
            valid_balls = ["pokeball", "greatball", "ultraball", "masterball"]

            if input_words[-1] in valid_balls:
                ball_type = input_words.pop() 

            typed_name = "-".join(input_words)
            
            if not typed_name:
                return await ctx.send(f"🎒 You pulled out a {ball_type.capitalize()}, but you didn't specify what to throw it at!")

            # ==========================================
            # 4 & 5. TARGET SELECTOR & LOCALIZATION
            # ==========================================
            target = None
            target_spawn_id = None
            is_private_spawn = False
            origin_lang = "ENG"
            # A spawn of the right species sitting in a DIFFERENT channel. Remembered
            # so the refusal can say where it actually is - "there is no Pikachu here"
            # while a Pikachu is plainly on screen two channels over reads as a bug,
            # and the player's next move is to retype the command rather than to walk
            # to the right room.
            elsewhere_channel_id = None

            async with aiosqlite.connect(DB_FILE) as db:
                async def check_spawn(spawn_data):
                    expected_english = spawn_data.get('name')
                    if not expected_english: return False, "ENG"
                        
                    if typed_name == expected_english or expected_english.startswith(f"{typed_name}-"):
                        return True, "ENG"
                        
                    async with db.execute("SELECT english_name, language_tag FROM species_translations WHERE foreign_name = ?", (typed_name,)) as cursor:
                        translations = await cursor.fetchall()
                        
                    for eng_name, lang_tag in translations:
                        if eng_name == expected_english or expected_english.startswith(f"{eng_name}-"):
                            return True, lang_tag 
                            
                    return False, "ENG"

                if user_id in user_active_spawns and isinstance(user_active_spawns[user_id], dict):
                    for sid, spawn_data in list(user_active_spawns[user_id].items()):
                        if not isinstance(spawn_data, dict):
                            user_active_spawns.pop(user_id, None)
                            break

                        is_match, matched_lang = await check_spawn(spawn_data)
                        if not is_match:
                            continue
                        if not spawn_is_here(spawn_data, ctx.channel.id):
                            elsewhere_channel_id = spawn_data.get('channel_id')
                            continue
                        target = spawn_data
                        target_spawn_id = sid
                        is_private_spawn = True
                        origin_lang = matched_lang
                        break

                if not target and guild_id in active_spawns and isinstance(active_spawns[guild_id], dict):
                    for sid, spawn_data in list(active_spawns[guild_id].items()):
                        if not isinstance(spawn_data, dict):
                            active_spawns.pop(guild_id, None)
                            break

                        is_match, matched_lang = await check_spawn(spawn_data)
                        if not is_match:
                            continue
                        if not spawn_is_here(spawn_data, ctx.channel.id):
                            elsewhere_channel_id = spawn_data.get('channel_id')
                            continue
                        target = spawn_data
                        target_spawn_id = sid
                        origin_lang = matched_lang
                        break

                if not target:
                    pretty = typed_name.capitalize().replace('-', ' ')
                    if elsewhere_channel_id:
                        return await ctx.send(
                            f"📍 The **{pretty}** is not in this channel - it appeared in "
                            f"<#{elsewhere_channel_id}>. Head over there and try again.")
                    return await ctx.send(f"There is no {pretty} here right now.")

                pokemon_name = target['name'] 

                # ==========================================
                # CAPTURE LOGIC & SMART AUTO-BALL
                # ==========================================
                if not ball_type:
                    async with db.execute("SELECT item_name, quantity FROM user_inventory WHERE user_id = ? AND item_name IN ('ultraball', 'greatball') AND quantity > 0", (user_id,)) as cursor:
                        inv_rows = await cursor.fetchall()
                    
                    inv_dict = {row[0]: row[1] for row in inv_rows}
                    if inv_dict.get('ultraball', 0) > 0:
                        ball_type = "ultraball"
                    elif inv_dict.get('greatball', 0) > 0:
                        ball_type = "greatball"
                    else:
                        ball_type = "pokeball"
                
                equipment_stats = {
                    "pokeball": {"multiplier": 1.5},
                    "greatball": {"multiplier": 2.5},
                    "ultraball": {"multiplier": 4.0},
                    "masterball": {"multiplier": 255}
                }

                if ball_type not in equipment_stats:
                    return await ctx.send("Invalid equipment. Please use `pokeball`, `greatball`, or `ultraball`.")

                multiplier = equipment_stats[ball_type]["multiplier"]

                if ball_type != "pokeball":
                    async with db.execute("SELECT quantity FROM user_inventory WHERE user_id = ? AND item_name = ?", (user_id, ball_type)) as cursor:
                        inv_data = await cursor.fetchone()
                    quantity = inv_data[0] if inv_data else 0
                    
                    if quantity < 1:
                        return await ctx.send(f"🎒 You don't have any {ball_type.capitalize()}s in your field pack! Buy some from the `!market`.")
                
                base_chance = (target['capture_rate'] + 50) / 305.0
                final_chance = min(1.0, base_chance * multiplier)
                roll = random.random() 
                
                if ball_type != "pokeball":
                    await db.execute("UPDATE user_inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_name = ?", (user_id, ball_type))
                
                # ==========================================
                # 🚨 THE NEW FLEE MECHANIC
                # ==========================================
                if roll > final_chance:
                    await db.commit() 
                    flee_roll = random.random()
                    
                    if flee_roll <= 0.30:
                        if is_private_spawn:
                            user_active_spawns[user_id].pop(target_spawn_id, None)
                        else:
                            active_spawns[guild_id].pop(target_spawn_id, None)

                        # The card is now advertising a specimen that is gone, and the
                        # despawn timer will not touch it - correctly, since it declines
                        # to overwrite anything no longer in memory. A catch has said so
                        # since the spawn-card work; an escape never did.
                        await mark_spawn_fled(self.bot, target, pokemon_name)

                        return await ctx.send(f"💥 Oh no! The **{typed_name.capitalize().replace('-', ' ')}** broke free and fled into the wild! *(Catch chance was {final_chance:.1%})*")
                    else:
                        return await ctx.send(f"💨 The **{typed_name.capitalize().replace('-', ' ')}** broke free from the {ball_type.capitalize()}, but it's still watching you! Try again! *(Catch chance was {final_chance:.1%})*")
                
                # --- GENETICS & RARE SPAWN DATA FETCH ---
                async with db.execute("SELECT standard_abilities, hidden_ability, gender_rate, is_legendary, is_mythical FROM base_pokemon_species WHERE pokedex_id = ?", (target['pokedex_id'],)) as cursor:
                    ability_data = await cursor.fetchone()
                
                assigned_ability = "Unknown"
                is_legendary = False
                is_mythical = False
                
                if ability_data:
                    standard_str, hidden_str, raw_gender_rate, is_legendary, is_mythical = ability_data
                    standard_list = standard_str.split(",") if standard_str else ["Unknown"]
                    
                    if hidden_str != "None" and random.random() <= 0.20:
                        assigned_ability = hidden_str
                    else:
                        assigned_ability = random.choice(standard_list)   
                    gender_rate = raw_gender_rate if raw_gender_rate is not None else 4
                else:
                    gender_rate = 4

                # The SPAWN decided this, and the catch inherits it. Rolling again here
                # would be rolling a second specimen: the wild encounter has already
                # shown a sex and drawn the matching sprite, and a fresh roll would
                # contradict both about a third of the time.
                #
                # The fallback is for a spawn created before this existed - one already
                # sitting in a channel when the bot restarted - which carries no sex.
                gender = target.get('gender') or roll_gender(
                    gender_rate, species_name=pokemon_name)
                gender_emoji = gender_icon(gender) 

                # ==========================================
                # BIOMETRICS & ALPHA IV LOGIC
                # ==========================================
                h_mult, w_mult, size_class = generate_biometrics()
                is_alpha = (h_mult >= ALPHA_HEIGHT_THRESHOLD)

                # The tag a specimen earns by being what it is. One tag, because
                # `custom_tag` is one column and the box browser compares it with `=`;
                # the order is in constants.AUTO_TAGS. Nothing here ever overwrites a
                # tag a player chose - a fresh capture has an empty one.
                earned_tag = auto_tag(
                    is_shiny=bool(target['is_shiny']),
                    is_mythical=bool(is_mythical),
                    is_legendary=bool(is_legendary),
                    is_pseudo=is_pseudo_legendary(target['pokedex_id']),
                    is_alpha=is_alpha)

                if is_alpha:
                    ivs = [random.randint(20, 31) for _ in range(6)]
                    max_indices = random.sample(range(6), 3)
                    for idx in max_indices:
                        ivs[idx] = 31
                else:
                    ivs = [random.randint(0, 31) for _ in range(6)]
                    
                instance_id = str(uuid.uuid4())
                nature = random.choice(NATURES)
                level = random.randint(1, 15)

                # ==========================================
                # SAVE TO DATABASE
                # ==========================================
                await db.execute("INSERT OR IGNORE INTO servers (guild_id) VALUES (?)", (guild_id,))
                await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            
                await db.execute("""
                    INSERT INTO guild_members (user_id, guild_id, contribution_points)
                    VALUES (?, ?, 1)
                    ON CONFLICT(user_id, guild_id) DO UPDATE SET contribution_points = contribution_points + 1;
                """, (user_id, guild_id))
                
                await db.execute("""
                    INSERT INTO caught_pokemon (
                        instance_id, user_id, pokedex_id, caught_in_guild, gender, level, nature, is_shiny, original_user_id,
                        iv_hp, iv_attack, iv_defense, iv_sp_atk, iv_sp_def, iv_speed, ability, height_multiplier, weight_multiplier, origin_language,
                        custom_tag
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (instance_id, user_id, target['pokedex_id'], guild_id, gender, level, nature, target['is_shiny'], user_id, *ivs, assigned_ability, h_mult, w_mult, origin_lang, earned_tag))
                
                target_species = pokemon_name 

                await db.execute("""
                    UPDATE field_directives
                    SET current_progress = current_progress + 1
                    WHERE user_id = ? AND objective_type = 'survey_species' AND target_variable = ? AND is_completed = 0
                """, (user_id, target_species))

                async with db.execute("""
                    SELECT required_amount, current_progress 
                    FROM field_directives
                    WHERE user_id = ? AND objective_type = 'survey_species' AND target_variable = ? AND is_completed = 0
                """, (user_id, target_species)) as cursor:
                    survey_row = await cursor.fetchone()

                if survey_row and survey_row[1] == survey_row[0]:
                    await ctx.send(f"📡 **Directive Complete:** You successfully surveyed the local **{target_species.capitalize().replace('-', ' ')}** population! Run `!claim` to receive your funding.")

                found_notes = False 
                found_tokens = 0
                found_berry = None

                if random.random() <= 0.10: 
                    await db.execute("""
                        INSERT INTO user_inventory (user_id, item_name, quantity) 
                        VALUES (?, 'encrypted-field-notes', 1) 
                        ON CONFLICT(user_id, item_name) 
                        DO UPDATE SET quantity = quantity + 1
                    """, (user_id,))
                    found_notes = True 
                    
                if random.random() <= 0.40:
                    berry_pool = list(CONSUMABLE_DATABASE.keys())
                    found_berry = random.choice(berry_pool)
                    await db.execute("""
                        INSERT INTO user_inventory (user_id, item_name, quantity) 
                        VALUES (?, ?, 1) 
                        ON CONFLICT(user_id, item_name) 
                        DO UPDATE SET quantity = quantity + 1
                    """, (user_id, found_berry))

                if random.random() <= 0.50:
                    found_tokens = random.randint(5, 150)
                    await db.execute("UPDATE users SET eco_tokens = eco_tokens + ? WHERE user_id = ?", (found_tokens, user_id))

                await db.commit()
                
                if is_private_spawn:
                    user_active_spawns[user_id].pop(target_spawn_id, None)
                else:
                    active_spawns[guild_id].pop(target_spawn_id, None)

                # The card that announced this specimen is still sitting in the channel
                # looking live, and the despawn timer will not touch it now that the
                # spawn is gone from memory - so anybody scrolling past sees a specimen
                # to catch that was taken minutes ago. Say what happened to it.
                await mark_spawn_caught(self.bot, target, ctx.author.display_name,
                                        pokemon_name, target['is_shiny'], earned_tag)

                # ==========================================
                # LOCAL SPRITE GENERATOR
                # ==========================================
                poke_id = target['pokedex_id']
                is_shiny = target['is_shiny']
                # The catch confirmation is the FIRST place a specimen has a sex, so it
                # is the first place the female sprite can be shown - the wild spawn
                # above had none to prefer.
                safe_filename = sprite_attachment_name(poke_id, is_shiny, gender)
                file_path = resolve_sprite(poke_id, shiny=is_shiny, gender=gender,
                                           style=HOME)

                sprite_file_local = None
                sprite_file_global = None

                if file_path:
                    # We create two File instances because Discord.py consumes them upon sending!
                    sprite_file_local = discord.File(file_path, filename=safe_filename)
                    sprite_file_global = discord.File(file_path, filename=safe_filename)
                else:
                    print(f"⚠️ WARNING: Local sprite missing for ID {poke_id} at {file_path}")
                    
                # ==========================================
                # UI ENHANCEMENT: SHOW LEVEL & IVS
                # ==========================================
                iv_total = sum(ivs)
                iv_percentage = int((iv_total / 186.0) * 100)
                
                if iv_percentage >= 90: appraisal = "S-Tier (Flawless)"
                elif iv_percentage >= 80: appraisal = "A-Tier (Excellent)"
                elif iv_percentage >= 60: appraisal = "B-Tier (Strong)"
                elif iv_percentage >= 40: appraisal = "C-Tier (Average)"
                else: appraisal = "D-Tier (Weak)"
                
                alpha_tag = "🔥 **ALPHA** " if is_alpha else ""

                base_desc = f"**{ctx.author.name}** successfully tagged the {alpha_tag}**{gender_emoji} {typed_name.capitalize().replace('-', ' ')}** using a {ball_type.capitalize()}!\n\n"
                
                stat_block = f"📊 **Level:** {level}\n🧬 **Genetic Potential:** {iv_percentage}% *({appraisal})*\n"
                base_desc += stat_block
                
                loot_text = []
                if found_notes: loot_text.append("`Encrypted Field Notes`")
                if found_berry: loot_text.append(f"`{found_berry.title().replace('-', ' ')}`")
                if found_tokens > 0: loot_text.append(f"`{found_tokens} Eco-Tokens`")
                
                if loot_text:
                    base_desc += f"\n🎁 **Recovered:** {', '.join(loot_text)}"

                shiny_icon = "🌟" if is_shiny else "🌿"
                
                embed = discord.Embed(
                    title=f"{shiny_icon} Specimen Safely Rescued! [{origin_lang}]", 
                    description=base_desc,
                    color=discord.Color.green() if not is_alpha else discord.Color.red()
                )
                embed.set_footer(text=f"Tag ID: {instance_id[:8]}")
                
                # Attach the local sprite if it exists
                if sprite_file_local:
                    embed.set_thumbnail(url=f"attachment://{safe_filename}")
                    await ctx.send(embed=embed, file=sprite_file_local)
                else:
                    await ctx.send(embed=embed)
                
                # ==========================================
                # 🌐 GLOBAL BROADCAST MECHANIC
                # ==========================================
                # Read off the id rather than a column, because that is where the
                # pseudo-legendary list lives - one tuple in constants, which the
                # migration copies into the database rather than the other way round.
                is_pseudo = is_pseudo_legendary(target['pokedex_id'])

                if is_legendary or is_mythical or is_pseudo or is_shiny:
                    # The id and its beta counterpart live in constants.CHANNELS now,
                    # switched by ACTIVE_SERVER, rather than here with the other
                    # server's id surviving in a trailing comment.
                    broadcast_channel = (self.bot.get_channel(OFFICIAL_BROADCAST_CHANNEL_ID)
                                         if OFFICIAL_BROADCAST_CHANNEL_ID else None)
                    
                    if broadcast_channel:
                        rarity_parts = []
                        if is_shiny:
                            rarity_parts.append("✨ Shiny")
                        if is_mythical:
                            rarity_parts.append("Mythical")
                        elif is_legendary:
                            rarity_parts.append("Legendary")
                        elif is_pseudo:
                            rarity_parts.append("Pseudo-Legendary")
                            
                        rarity_title = " ".join(rarity_parts) if rarity_parts else "Rare"
                        
                        broadcast_embed = discord.Embed(
                            title=f"🚨 Global {rarity_title} Capture!",
                            description=f"Trainer **{ctx.author.name}** has successfully captured a **{pokemon_name.capitalize()}**!",
                            color=discord.Color.gold()
                        )
                        broadcast_embed.add_field(name="🌍 Location Detected", value=f"*{ctx.guild.name}*")
                        broadcast_embed.add_field(name="🧬 Specimen Details", value=f"Level {level} | {iv_percentage}% IVs")
                        
                        # Attach the secondary sprite to the global broadcast!
                        if sprite_file_global:
                            broadcast_embed.set_thumbnail(url=f"attachment://{safe_filename}")
                            await broadcast_channel.send(embed=broadcast_embed, file=sprite_file_global)
                        else:
                            await broadcast_channel.send(embed=broadcast_embed)
                
        except Exception as e:
            await ctx.send("❌ A critical database or memory error occurred during the tagging process.")
            print(f"Catch Command Error: {e}")

    @commands.command(name="claim", aliases=["funding", "grant"])
    @checks.has_started()
    @checks.is_authorized()
    async def claim_rewards(self, ctx):
        """Claims funding and equipment for completed field directives."""
        user_id = str(ctx.author.id)
        
        async with aiosqlite.connect(DB_FILE) as db:
        
            try:
                # 1. Find all completed but unclaimed directives
                async with db.execute("""
                    SELECT directive_id, reward_type, reward_payload, objective_type 
                    FROM field_directives 
                    WHERE user_id = ? AND current_progress >= required_amount AND is_completed = 0
                """, (user_id,)) as cursor:
                    completed_tasks = await cursor.fetchall()
                
                if not completed_tasks:
                    return await ctx.send("⚠️ You have no completed directives awaiting grant disbursement.")
                    
                claim_log = "🎉 **Grants Disbursed!** The environmental council has approved your fieldwork:\n\n"
                
                # 2. Process each reward
                for d_id, r_type, r_payload, obj_type in completed_tasks:
                    if r_type == 'eco_tokens':
                        amount = int(r_payload)
                        # `cursor` here was the SELECT's cursor, already closed by its
                        # own `async with`, and the call was never awaited - so this
                        # built a coroutine, threw it away, and marked the directive
                        # claimed anyway. Every Eco Token grant a culling directive ever
                        # paid out went nowhere, and the player could not claim it twice.
                        await db.execute(
                            "UPDATE users SET eco_tokens = eco_tokens + ? "
                            "WHERE user_id = ?", (amount, user_id))
                        claim_log += f"💰 Received **{amount}** Eco Tokens for completing a {obj_type.replace('_', ' ').title()} directive.\n"
                        
                    elif r_type == 'item':
                        await db.execute("""
                            INSERT INTO user_inventory (user_id, item_name, quantity) 
                            VALUES (?, ?, 1) 
                            ON CONFLICT(user_id, item_name) 
                            DO UPDATE SET quantity = quantity + 1
                        """, (user_id, r_payload))
                        claim_log += f"📦 Received **1x {r_payload.replace('-', ' ').title()}** from laboratory supply.\n"
                    
                    # 3. Mark the directive as claimed/archived
                    await db.execute("UPDATE field_directives SET is_completed = 1 WHERE directive_id = ?", (d_id,))
                    
                await db.commit()
                
                embed = discord.Embed(description=claim_log, color=discord.Color.gold())
                await ctx.send(embed=embed)
                
            except Exception as e:
                if db.in_transaction:
                    await db.rollback()
                print(f"Claim error: {e}")
                await ctx.send("❌ An accounting error occurred while processing your grant funding.")

    @commands.command(name="analyze", aliases=["decode", "research"])
    @checks.has_started()
    @checks.is_authorized()
    async def analyze_notes(self, ctx, *, target: str):
        """Turns encrypted notes into directives. `!analyze notes 10` does ten at once."""
        wanted, target = split_note_count(target)

        if target.lower() not in ["notes", "field notes", "encrypted-field-notes"]:
            return await ctx.send("⚠️ Please specify what you want to analyze (e.g., `!analyze notes`).")

        if wanted is None:
            wanted = 1
        if wanted < 1:
            return await ctx.send("⚠️ Analyse at least one note.")
        if wanted > MAX_NOTES_PER_ANALYSIS:
            return await ctx.send(
                f"⚠️ The mainframe processes at most **{MAX_NOTES_PER_ANALYSIS}** notes "
                f"in one pass. Try `!analyze notes {MAX_NOTES_PER_ANALYSIS}`.")

        user_id = str(ctx.author.id)

        async with aiosqlite.connect(DB_FILE) as db:

            try:
                # 1. Check Inventory
                async with db.execute("SELECT quantity FROM user_inventory WHERE user_id = ? AND item_name = 'encrypted-field-notes'", (user_id,)) as cursor:
                    inv_data = await cursor.fetchone()

                held = inv_data[0] if inv_data else 0
                if held < 1:
                    return await ctx.send("🎒 You do not have any `Encrypted Field Notes` to analyze!")

                # 2. How many can actually be run. A note is only spent for a directive
                #    that is actually issued - the notebook filling up must not eat one.
                async with db.execute(
                        "SELECT COUNT(*) FROM field_directives "
                        "WHERE user_id = ? AND is_completed = 0", (user_id,)) as cursor:
                    open_now = (await cursor.fetchone())[0]

                room = max(0, MAX_ACTIVE_DIRECTIVES - open_now)
                if room == 0:
                    return await ctx.send(
                        f"📋 **Notebook Full:** you already have "
                        f"**{open_now}/{MAX_ACTIVE_DIRECTIVES}** active directives. "
                        f"Finish some with `!claim`, or drop one with `!abandon <id>`.")

                runs = min(wanted, held, room)

                issued = []
                for _ in range(runs):
                    issued.append(await self.issue_directive(db, user_id))

                await db.execute(
                    "UPDATE user_inventory SET quantity = quantity - ? "
                    "WHERE user_id = ? AND item_name = 'encrypted-field-notes'",
                    (runs, user_id))
                await db.commit()

                return await ctx.send(embed=analysis_embed(
                    issued, wanted=wanted, held=held, room=room,
                    open_after=open_now + runs))

            except Exception as e:
                if db.in_transaction:
                    await db.rollback()
                print(f"Decryption error: {e}")
                await ctx.send("❌ A critical error occurred in the laboratory mainframe.")

    async def issue_directive(self, db, user_id):
        """
        Roll one directive, write it, and report what it was.

        Pulled out of the command so `!analyze notes 10` runs the SAME generator ten
        times rather than growing a second copy of it - which is exactly how the three
        rarity ladders in this file drifted apart from each other.

        Does not commit; the caller owns the transaction, so a batch that fails halfway
        leaves neither the directives nor the spent notes behind.
        """
        chosen_obj = random.choice(['cull_type', 'survey_species', 'trigger_mutation'])

        if chosen_obj == 'cull_type':
            elements = ['normal', 'fire', 'water', 'grass', 'electric', 'ice',
                        'fighting', 'poison', 'ground', 'flying', 'psychic', 'bug',
                        'rock', 'ghost', 'dragon', 'dark', 'steel', 'fairy']
            target_var = random.choice(elements)
            req_amt = random.randint(5, 12)
            rev_type = 'eco_tokens'
            rev_payload = str(req_amt * 250)  # Scale payout with the random difficulty

        elif chosen_obj == 'survey_species':
            # A survey names ONE species and asks the player to go and tag it, so the
            # target has to be something the world can actually put in front of them.
            # Drawn from the same pool the spawner draws from - the unfiltered roll this
            # replaces handed out Mega Charizard X, Gigantamax Snorlax and Totem
            # Raticate, none of which will ever appear in a habitat channel.
            # Paradox species join the exclusion for the same reason the pseudos are
            # here: a directive asking for three Flutter Mane is not a research task,
            # it is a wall. They only became rare this change, so without this line the
            # generator would have kept handing them out at ordinary-wildlife odds.
            rare_filter = (f"AND is_legendary = 0 AND is_mythical = 0 "
                           f"AND {pseudo_legendaries(negate=True)} "
                           f"AND {paradox_species(negate=True)}"
                           if SURVEY_EXCLUDES_RARE_SPECIES else "")
            async with db.execute(f"""
                SELECT name FROM base_pokemon_species
                WHERE {spawnable_forms()}
                AND {ultra_beasts(negate=True)}
                {rare_filter}
                ORDER BY RANDOM() LIMIT 1
            """) as cursor:
                db_species = await cursor.fetchone()
            target_var = db_species[0] if db_species else 'pidgey'

            req_amt = random.randint(1, 3)
            rev_type = 'item'
            rev_payload = random.choice(['greatball', 'ultraball'])

        else:  # trigger_mutation
            target_var = 'any'
            req_amt = 1
            rev_type = 'item'
            rev_payload = random.choice(['rare-candy', 'raw-keystone', 'wishing-fragment'])

        cursor = await db.execute("""
            INSERT INTO field_directives
                (user_id, objective_type, target_variable, required_amount,
                 reward_type, reward_payload)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, chosen_obj, target_var, req_amt, rev_type, rev_payload))

        # The id is handed back so the summary can print the number `!survey` and
        # `!abandon` both take, rather than telling somebody to go and look it up.
        return {'directive_id': cursor.lastrowid, 'objective_type': chosen_obj,
                'target': target_var, 'required': req_amt,
                'reward_type': rev_type, 'reward_payload': rev_payload}


    @commands.command(name="view", aliases=["inspect", "i", "I", "info"])
    @checks.has_started()
    @checks.is_authorized()
    async def view_pokemon(self, ctx, tag_id: str = None):
        user_id = str(ctx.author.id)
        
        async with aiosqlite.connect(DB_FILE) as db:
        
            # 1. Fetch total Pokemon count (Synchronized with the UI Join!)
            async with db.execute("""
                SELECT COUNT(*) 
                FROM caught_pokemon cp
                JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                WHERE cp.user_id = ?
                AND cp.instance_id NOT IN (SELECT instance_id FROM active_deployments)
                AND cp.instance_id NOT IN (SELECT instance_id FROM gts_deposits)
            """, (user_id,)) as cursor:
                total_pokemon = await cursor.fetchone()
                total_pokemon = total_pokemon[0]
            
            if total_pokemon == 0:
                return await ctx.send("🎒 Your field notebook is completely empty!")
                
            async with db.execute("SELECT active_partner FROM users WHERE user_id = ?", (user_id,)) as cursor:
                partner_data = await cursor.fetchone()
            active_partner_id = partner_data[0] if partner_data else None
            
            # 2. Determine the Target Index
            target_index = 1
            
            if not tag_id:
                if not active_partner_id:
                    return await ctx.send("You don't have an Active Partner! Use `!view [Number]`.")
                    
                # Synchronized Roster CTE
                async with db.execute("""
                    WITH Roster AS (
                        SELECT cp.instance_id, ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as field_number
                        FROM caught_pokemon cp
                        JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                        WHERE cp.user_id = ?
                        AND cp.instance_id NOT IN (SELECT instance_id FROM active_deployments)
                        AND cp.instance_id NOT IN (SELECT instance_id FROM gts_deposits)
                    ) SELECT field_number FROM Roster WHERE instance_id = ?
                """, (user_id, active_partner_id)) as cursor:
                    result = await cursor.fetchone()
                target_index = result[0] if result else 1
                
            elif tag_id.lower() in ["new", "latest", "last"]:
                target_index = total_pokemon # The very last one!
                
            # THE FIX: Ensure it's treated as a box index ONLY if it's less than 6 digits!
            # (Since UUID tags are 8 characters long)
            elif tag_id.isdigit() and len(tag_id) <= 6:
                target_index = int(tag_id)
                if target_index < 1 or target_index > total_pokemon:
                    return await ctx.send(f"⚠️ Invalid index. You only have {total_pokemon} intact specimens.")
                    
            else:
                # It's a UUID tag! Synchronized Roster CTE for perfect indexing.
                async with db.execute("""
                    WITH Roster AS (
                        SELECT cp.instance_id, ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as field_number
                        FROM caught_pokemon cp
                        JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                        WHERE cp.user_id = ?
                        AND cp.instance_id NOT IN (SELECT instance_id FROM active_deployments)
                        AND cp.instance_id NOT IN (SELECT instance_id FROM gts_deposits)
                    ) SELECT field_number FROM Roster WHERE instance_id LIKE ?
                """, (user_id, f"{tag_id}%")) as cursor:
                    res = await cursor.fetchone()
                if not res:
                    return await ctx.send(f"⚠️ Could not find an intact specimen matching Tag ID `{tag_id}`.")
                target_index = res[0]

        # 3. Launch the Paginator!
        view = PokemonPaginator(self.bot, user_id, target_index, total_pokemon, active_partner_id)
        view.update_button_states()
        embed, sprite_file = await view.generate_embed()

        if sprite_file:
            await ctx.send(embed=embed, file=sprite_file, view=view)
        else:
            await ctx.send(embed=embed, view=view)
    
    @commands.command(name="rarecandy", aliases=["candy"])
    @checks.has_started()
    @checks.is_authorized()
    @checks.is_not_in_combat()
    async def use_rare_candy(self, ctx, box_number: int, amount: int = 1):
        """Feed rare candies to a specimen to artificially accelerate its growth."""
        if amount <= 0:
            return await ctx.send("⚠️ You must use at least 1 candy.")

        user_id = str(ctx.author.id)

        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute("""
                SELECT quantity FROM user_inventory 
                WHERE user_id = ? AND item_name IN ('rare candy', 'rare-candy')
            """, (user_id,)) as cursor:
                candy_record = await cursor.fetchone()

            if not candy_record or candy_record[0] < amount:
                return await ctx.send(f"🍬 You do not have `{amount}x Rare Candy` in your inventory.")

            # 🚨 UPDATE: Fetch held_item and ability traits
            async with db.execute("""
                WITH NumberedPC AS (
                    SELECT 
                        cp.instance_id, cp.level, cp.pokedex_id, cp.happiness, cp.held_item, cp.ability,
                        s.name, s.growth_rate, s.standard_abilities, s.hidden_ability,
                        ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                    FROM caught_pokemon cp
                    JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                    WHERE cp.user_id = ? 
                      AND cp.instance_id NOT IN (SELECT instance_id FROM active_deployments)
                      AND cp.instance_id NOT IN (SELECT instance_id FROM gts_deposits)  
                )
                SELECT instance_id, level, pokedex_id, happiness, name, growth_rate, held_item, ability, standard_abilities, hidden_ability 
                FROM NumberedPC 
                WHERE box_number = ?
            """, (user_id, box_number)) as cursor:
                pokemon = await cursor.fetchone()

            if not pokemon:
                return await ctx.send(f"⚠️ Could not find a valid specimen at Box `#{box_number}`. It may be deployed on a mission or doesn't exist.")

            instance_id, current_level, pokedex_id, happiness, species_name, growth_rate, held_item, current_ability, current_standards, current_hidden = pokemon

            if current_level >= 100:
                return await ctx.send(f"🛑 **{species_name.capitalize()}** is already Level 100! They cannot consume any more candies.")

            levels_gained = min(amount, 100 - current_level)
            new_level = current_level + levels_gained
            refunded_candies = amount - levels_gained
            new_total_xp = get_xp_requirement(new_level, growth_rate)

            await db.execute("BEGIN TRANSACTION")
            try:
                await db.execute("""
                    UPDATE user_inventory SET quantity = quantity - ? 
                    WHERE user_id = ? AND item_name IN ('rare candy', 'rare-candy')
                """, (levels_gained, user_id))
                await db.execute("DELETE FROM user_inventory WHERE quantity <= 0")
                await db.execute("""
                    UPDATE caught_pokemon SET level = ?, experience = ? 
                    WHERE instance_id = ?
                """, (new_level, new_total_xp, instance_id))
                await db.commit()
            except Exception as e:
                await db.rollback()
                print(f"Candy Error: {e}")
                return await ctx.send("❌ A database error occurred while consuming the item.")

            response_msg = f"🍬 **{species_name.capitalize()}** consumed `{levels_gained}x Rare Candy` and grew to **Level {new_level}**!"
            if refunded_candies > 0:
                response_msg += f"\n*(Capped at Lv. 100! Refunded `{refunded_candies}x` unused candies to your inventory.)*"

            # ==========================================
            # EVOLUTION & TRAIT INHERITANCE
            # ==========================================
            possible_evolution = None
            
            # The Everstone Bypass Shield
            if held_item != 'everstone':
                async with db.execute("SELECT evolved_species_id, trigger_name, min_level, min_happiness FROM evolution_rules WHERE base_species_id = ?", (pokedex_id,)) as cursor:
                    evo_options = await cursor.fetchall()

                for evolved_id, trigger, req_level, req_happy in evo_options:
                    can_evolve = False
                    if trigger == 'level-up' and req_level and new_level >= req_level: can_evolve = True
                    elif trigger == 'happiness' and req_happy and happiness >= req_happy: can_evolve = True
                        
                    if can_evolve:
                        # Fetch the evolved species data to map traits
                        async with db.execute("SELECT name, standard_abilities, hidden_ability FROM base_pokemon_species WHERE pokedex_id = ?", (evolved_id,)) as cursor:
                            evo_data = await cursor.fetchone()
                            
                        if evo_data:
                            new_species_name, ev_standards, ev_hidden = evo_data
                            new_species_name = new_species_name.capitalize()
                            
                            # Trait Mapping Logic
                            is_ha = (current_ability == current_hidden)
                            slot_index = 0
                            
                            # Find which slot their standard ability was in (0 or 1)
                            if not is_ha and current_standards:
                                st_list = [a.strip() for a in current_standards.split(",")]
                                if current_ability in st_list:
                                    slot_index = st_list.index(current_ability)
                                    
                            # Assign the mapped ability
                            if is_ha and ev_hidden:
                                new_ability = ev_hidden
                            else:
                                ev_st_list = [a.strip() for a in ev_standards.split(",")] if ev_standards else ["unknown"]
                                new_ability = ev_st_list[slot_index] if slot_index < len(ev_st_list) else ev_st_list[0]

                            possible_evolution = {"id": evolved_id, "name": new_species_name, "ability": new_ability}
                            break

            if possible_evolution:
                view = EvolutionConfirmView(
                    owner_id=ctx.author.id, 
                    instance_id=instance_id, 
                    new_pokedex_id=possible_evolution["id"], 
                    new_species_name=possible_evolution["name"],
                    new_ability=possible_evolution["ability"],
                    db_file=DB_FILE
                )
                response_msg += f"\n\n✨ **What? {species_name.capitalize()} is evolving!** Do you want to initiate the process?"
                message = await ctx.send(response_msg, view=view)
                view.message = message 
            else:
                await ctx.send(response_msg)

    @commands.command(name="return", aliases=["recall"])
    @checks.has_started()
    @checks.is_authorized()
    async def return_pokemon(self, ctx):
        """View and recall deployed field teams."""
        user_id = str(ctx.author.id)
        
        async with aiosqlite.connect(DB_FILE) as db:
            # Group their active deployments by mission type and count how many are on each
            async with db.execute("""
                SELECT mission_type, COUNT(*) 
                FROM active_deployments 
                WHERE user_id = ? 
                GROUP BY mission_type
            """, (user_id,)) as cursor:
                active_missions = await cursor.fetchall()
                
        if not active_missions:
            return await ctx.send("⛺ You don't have any specimens out on field missions right now.")
            
        # Spawn the interactive UI
        view = ReturnMissionsView(self, user_id, active_missions)
        embed = discord.Embed(
            title="📡 Active Field Deployments", 
            description="Select a team to recall them to base and process their field data.",
            color=discord.Color.teal()
        )
        await ctx.send(embed=embed, view=view)

    async def execute_return_logic(self, interaction: discord.Interaction, user_id: str, target_mission: str):
        """The heavy lifting function triggered by the Discord Buttons."""
        
        async with aiosqlite.connect(DB_FILE) as db:
            # 🚨 UPDATE: Joined held_item and ability logic
            query = """
                SELECT d.instance_id, d.start_time, d.mission_type, s.name, cp.experience, cp.level, s.growth_rate, cp.happiness, cp.pokedex_id,
                       cp.ev_hp, cp.ev_attack, cp.ev_defense, cp.ev_sp_atk, cp.ev_sp_def, cp.ev_speed,
                       GROUP_CONCAT(LOWER(t.type_name)),
                       cp.held_item, cp.ability, s.standard_abilities, s.hidden_ability
                FROM active_deployments d
                JOIN caught_pokemon cp ON d.instance_id = cp.instance_id
                JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                JOIN base_pokemon_types t ON s.pokedex_id = t.pokedex_id
                WHERE d.user_id = ?
            """
            params = [user_id]
            
            if target_mission != "all":
                query += " AND d.mission_type = ?"
                params.append(target_mission)
                
            query += " GROUP BY d.instance_id"
            
            async with db.execute(query, params) as cursor:
                deployed_team = await cursor.fetchall()
                
            if not deployed_team:
                return await interaction.followup.send("⛺ You don't have any specimens out on field missions right now.")
                
            results = []
            items_found = []
            pending_evolutions = [] 
            current_time = time.time()
            
            await db.execute("BEGIN TRANSACTION")
            
            try:
                for p_data in deployed_team:
                    (instance_id, start_time, mission_type, name, current_xp, current_level, growth_rate, happiness, pokedex_id,
                     ev_hp, ev_atk, ev_def, ev_spa, ev_spd, ev_spe, all_types, held_item, current_ability, current_standards, current_hidden) = p_data
                     
                    elapsed_hours = (current_time - start_time) / 3600.0
                    
                    if elapsed_hours < 0.25:
                        await db.execute("DELETE FROM active_deployments WHERE instance_id = ?", (instance_id,))
                        results.append(f"🔸 **{name.capitalize()}** returned early. *(No data gathered)*")
                        continue
                        
                    capped_hours = min(elapsed_hours, 24.0)
                    mission_data = FIELD_MISSIONS.get(mission_type, FIELD_MISSIONS.get("hp"))
                    
                    new_total_xp = current_xp
                    new_level = current_level
                    ev_updates = {}
                    gains_text = ""
                    
                    if mission_data["category"] == "exp":
                        base_xp = int(capped_hours * mission_data["base_xp_hr"])
                        type_list = all_types.split(',') if all_types else []

                        if mission_data["preferred_type"] in type_list:
                            base_xp = int(base_xp * 1.20)
                            gains_text = f"gained **{base_xp} XP** *(Type Bonus!)*"
                        else:
                            gains_text = f"gained **{base_xp} XP**"
                            
                        new_total_xp += base_xp
                        
                        while new_level < 100 and new_total_xp >= get_xp_requirement(new_level, growth_rate):
                            new_level += 1
                            
                    elif mission_data["category"] == "ev":
                        target_stat = mission_data["target_ev"]
                        raw_ev_gain = int(capped_hours * mission_data["ev_hr"])
                        current_total_evs = ev_hp + ev_atk + ev_def + ev_spa + ev_spd + ev_spe
                        current_stat_value = locals()[target_stat.replace("ev_", "ev_").replace("atk", "attack").replace("spa", "sp_atk").replace("spd", "sp_def").replace("spe", "speed")]
                        overall_room = max(0, 510 - current_total_evs)
                        stat_room = max(0, 252 - current_stat_value)
                        actual_ev_gain = min(raw_ev_gain, overall_room, stat_room)
                        ev_label = target_stat.replace('ev_', '').upper()
                        
                        if actual_ev_gain > 0:
                            ev_updates[target_stat] = current_stat_value + actual_ev_gain
                            gains_text = f"gained **+{actual_ev_gain} {ev_label} EVs**!"
                        else:
                            gains_text = f"is already maxed out! *(No EVs gained)*"

                    # ==========================================
                    # EVOLUTION CHECK & LOOT ROLLS
                    # ==========================================
                    # The Everstone Bypass Shield
                    if new_level > current_level and held_item != 'everstone':
                        async with db.execute("SELECT evolved_species_id, trigger_name, min_level, min_happiness FROM evolution_rules WHERE base_species_id = ?", (pokedex_id,)) as cursor:
                            evo_options = await cursor.fetchall()
                            
                        for evolved_id, trigger, req_level, req_happy in evo_options:
                            can_evolve = False
                            if trigger == 'level-up' and req_level and new_level >= req_level: can_evolve = True
                            elif trigger == 'happiness' and req_happy and happiness >= req_happy: can_evolve = True
                                
                            if can_evolve:
                                async with db.execute("SELECT name, standard_abilities, hidden_ability FROM base_pokemon_species WHERE pokedex_id = ?", (evolved_id,)) as cursor:
                                    evo_data = await cursor.fetchone()
                                    
                                if evo_data:
                                    new_species_name, ev_standards, ev_hidden = evo_data
                                    new_species_name = new_species_name.capitalize()
                                    
                                    # Trait Mapping
                                    is_ha = (current_ability == current_hidden)
                                    slot_index = 0
                                    
                                    if not is_ha and current_standards:
                                        st_list = [a.strip() for a in current_standards.split(",")]
                                        if current_ability in st_list:
                                            slot_index = st_list.index(current_ability)
                                            
                                    if is_ha and ev_hidden:
                                        new_ability = ev_hidden
                                    else:
                                        ev_st_list = [a.strip() for a in ev_standards.split(",")] if ev_standards else ["unknown"]
                                        new_ability = ev_st_list[slot_index] if slot_index < len(ev_st_list) else ev_st_list[0]

                                    pending_evolutions.append({
                                        "instance_id": instance_id,
                                        "old_name": name.capitalize(),
                                        "new_pokedex_id": evolved_id,
                                        "new_species_name": new_species_name,
                                        "new_ability": new_ability
                                    })
                                break 
                                
                    if elapsed_hours >= 4.0 and mission_data.get("item_pool"):
                        found_item = random.choice(mission_data["item_pool"])
                        items_found.append(found_item)
                        await db.execute("INSERT INTO user_inventory (user_id, item_name, quantity) VALUES (?, ?, 1) ON CONFLICT(user_id, item_name) DO UPDATE SET quantity = quantity + 1", (user_id, found_item))

                    if ev_updates:
                        target_col = list(ev_updates.keys())[0]
                        new_val = ev_updates[target_col]
                        await db.execute(f"UPDATE caught_pokemon SET experience = ?, level = ?, {target_col} = ? WHERE instance_id = ?", 
                                         (new_total_xp, new_level, new_val, instance_id))
                    else:
                        await db.execute("UPDATE caught_pokemon SET experience = ?, level = ? WHERE instance_id = ?", 
                                         (new_total_xp, new_level, instance_id))
                                         
                    await db.execute("DELETE FROM active_deployments WHERE instance_id = ?", (instance_id,))
                    
                    level_text = f" ⬆️ *(Lv. {new_level})*" if new_level > current_level else ""
                    evo_hint = " 🧬 *(Ready to evolve!)*" if any(p['instance_id'] == instance_id for p in pending_evolutions) else ""
                    results.append(f"🔸 **{name.capitalize()}** {gains_text}{level_text}{evo_hint}")

                await db.commit()
                
            except Exception as e:
                await db.rollback()
                print(f"Error processing return: {e}")
                return await interaction.followup.send("❌ A database error occurred while recalling your team.")
            
            embed = discord.Embed(title="⛺ Field Missions Concluded", description="\n\n".join(results), color=discord.Color.green())
            
            if items_found:
                item_counts = {i: items_found.count(i) for i in set(items_found)}
                loot_str = ", ".join([f"`{count}x {item.replace('-', ' ').title()}`" for item, count in item_counts.items()])
                embed.add_field(name="🎁 Team Forage Haul", value=loot_str, inline=False)
                
            await interaction.followup.send(embed=embed)
            
            # Fire off interactive prompts with the mapped traits!
            for pending_evo in pending_evolutions:
                view = EvolutionConfirmView(
                    owner_id=int(user_id), 
                    instance_id=pending_evo["instance_id"], 
                    new_pokedex_id=pending_evo["new_pokedex_id"], 
                    new_species_name=pending_evo["new_species_name"],
                    new_ability=pending_evo["new_ability"],
                    db_file=DB_FILE
                )
                
                msg = await interaction.followup.send(
                    content=f"✨ **What? {pending_evo['old_name']} is evolving!** Do you want to initiate the process?", 
                    view=view,
                    wait=True 
                )
                view.message = msg
    
    @commands.command(name="vitamins", aliases=["feed"])
    @checks.has_started()
    @checks.is_authorized()
    async def use_vitamin(self, ctx, item_name: str, box_number: str, amount: int = 1):
        """Feed EV Vitamins to your specimens. (e.g., !use protein 4 10)"""
        user_id = str(ctx.author.id)
        item_name = item_name.lower()
        
        # 1. Define the Vitamin Mapping (+10 EVs per item)
        VITAMINS = {
            "hp-up": "ev_hp",
            "protein": "ev_attack",
            "iron": "ev_defense",
            "calcium": "ev_sp_atk",
            "zinc": "ev_sp_def",
            "carbos": "ev_speed"
        }
        
        if item_name not in VITAMINS:
            valid_items = ", ".join([f"`{v}`" for v in VITAMINS.keys()])
            return await ctx.send(f"⚠️ I can only process EV Vitamins right now. Valid items: {valid_items}")
            
        if not box_number.isdigit() or amount < 1:
            return await ctx.send("⚠️ Usage: `!use <item> <box_number> [amount]`\nExample: `!use protein 4 10`")

        async with aiosqlite.connect(DB_FILE) as db:
            # 2. Check their Inventory
            async with db.execute("SELECT quantity FROM user_inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name)) as cursor:
                inv_data = await cursor.fetchone()
                
            if not inv_data or inv_data[0] < 1:
                return await ctx.send(f"🎒 You don't have any `{item_name.title()}` in your bag!")
                
            owned_amount = inv_data[0]
            target_amount = min(amount, owned_amount) # Don't let them use more than they own
            
            # 3. Resolve Target (Using Soft Hide to prevent feeding deployed Pokemon!)
            async with db.execute("""
                WITH Roster AS (
                    SELECT cp.instance_id, s.name, cp.ev_hp, cp.ev_attack, cp.ev_defense, cp.ev_sp_atk, cp.ev_sp_def, cp.ev_speed,
                           ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                    FROM caught_pokemon cp JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                    WHERE cp.user_id = ? AND cp.instance_id NOT IN (SELECT instance_id FROM active_deployments)
                    AND cp.instance_id NOT IN (SELECT instance_id FROM gts_deposits)
                ) SELECT * FROM Roster WHERE box_number = ?
            """, (user_id, int(box_number))) as cursor:
                target = await cursor.fetchone()
                
            if not target:
                return await ctx.send(f"❌ Could not find a specimen in Box `#{box_number}`. Are they deployed?")
                
            (instance_id, name, ev_hp, ev_atk, ev_def, ev_spa, ev_spd, ev_spe, _) = target
            
            # 4. Enforce Strict EV Caps
            target_stat_col = VITAMINS[item_name]
            
            # Map the exact current value based on the column name
            stat_map = {"ev_hp": ev_hp, "ev_attack": ev_atk, "ev_defense": ev_def, "ev_sp_atk": ev_spa, "ev_sp_def": ev_spd, "ev_speed": ev_spe}
            current_stat_value = stat_map[target_stat_col]
            current_total_evs = sum(stat_map.values())
            
            # Calculate how much EV room is left overall and for this specific stat
            overall_room = max(0, 510 - current_total_evs)
            stat_room = max(0, 252 - current_stat_value)
            
            if overall_room <= 0:
                return await ctx.send(f"🧬 **{name.capitalize()}** has reached its absolute genetic limit (510 Total EVs). It cannot consume any more vitamins.")
            if stat_room <= 0:
                return await ctx.send(f"💪 **{name.capitalize()}** has already maxed out its {item_name.title()} potential (252 EVs).")
                
            # 5. Calculate ACTUAL consumption
            # Each vitamin gives 10 EVs. How many vitamins fit in the remaining room?
            import math
            max_vitamins_for_stat = math.ceil(stat_room / 10.0)
            max_vitamins_for_total = math.ceil(overall_room / 10.0)
            
            # The bottleneck is the lowest of: What they asked to use, what they own, stat cap, or total cap
            vitamins_to_consume = min(target_amount, max_vitamins_for_stat, max_vitamins_for_total)
            
            # The actual EV gain might be slightly less than (vitamins * 10) if they hit the hard cap
            # e.g., if they have 248 EVs, 1 vitamin gives +4, not +10.
            actual_ev_gain = min(vitamins_to_consume * 10, stat_room, overall_room)
            
            # 6. Execute the Updates
            await db.execute(f"UPDATE caught_pokemon SET {target_stat_col} = {target_stat_col} + ? WHERE instance_id = ?", (actual_ev_gain, instance_id))
            
            # Deduct the vitamins from inventory (If it hits 0, delete the row to keep the DB clean)
            if owned_amount - vitamins_to_consume <= 0:
                await db.execute("DELETE FROM user_inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
            else:
                await db.execute("UPDATE user_inventory SET quantity = quantity - ? WHERE user_id = ? AND item_name = ?", (vitamins_to_consume, user_id, item_name))
                
            await db.commit()
            
            # 7. UI Output
            stat_label = target_stat_col.replace("ev_", "").upper()
            embed = discord.Embed(title="💊 Nutritional Supplement Administered", color=discord.Color.green())
            embed.description = f"**{name.capitalize()}** consumed **{vitamins_to_consume}x `{item_name.title()}`**!"
            embed.add_field(name="Stat Increase", value=f"⬆️ +{actual_ev_gain} {stat_label} EVs")
            
            if vitamins_to_consume < amount:
                embed.set_footer(text="Notice: Consumption was halted early to prevent exceeding genetic stat caps.")
                
            await ctx.send(embed=embed)

    @commands.command(name="deploy")
    @checks.has_started()
    @checks.is_authorized()
    async def deploy_pokemon(self, ctx, mission_type: str = None, *, box_numbers: str = None):
        """Send multiple specimens on a Field Mission. (e.g. !deploy reef 4, 7, 12)"""
        user_id = str(ctx.author.id)
        
        if not mission_type or not box_numbers:
            return await ctx.send("⚠️ Usage: `!deploy <mission_id> <box_numbers>`\nExample: `!deploy reef 1, 4, 5`")
            
        mission_type = mission_type.lower()
        
        # 1. Validate against TODAY'S active board!
        active_missions = self.get_daily_missions()
        if mission_type not in active_missions:
            return await ctx.send("⚠️ That mission is not on the board today! Run `!jobs` to see today's available postings.")
            
        # 2. Parse the comma-separated box numbers
        try:
            targets = [int(x.strip()) for x in box_numbers.split(',') if x.strip()]
        except ValueError:
            return await ctx.send("⚠️ Please provide valid Box Numbers separated by commas. (e.g., `1, 4, 5`)")

        # (Notice we removed the old len(targets) > 5 check here, because we handle it smarter below!)

        async with aiosqlite.connect(DB_FILE) as db:
            
            # ==========================================
            # 🚨 UPDATED: PER-MISSION DEPLOYMENT CAP
            # ==========================================
            MAX_PER_MISSION = 5
            
            # We now check how many they have deployed TO THIS SPECIFIC MISSION
            async with db.execute("SELECT COUNT(*) FROM active_deployments WHERE user_id = ? AND mission_type = ?", (user_id, mission_type)) as cursor:
                current_deployments = (await cursor.fetchone())[0]
                
            available_slots = MAX_PER_MISSION - current_deployments
            
            if available_slots <= 0:
                return await ctx.send(f"⚠️ You already have a full team of {MAX_PER_MISSION} deployed to the **{FIELD_MISSIONS[mission_type]['name']}**! Try a different mission.")
                
            if len(targets) > available_slots:
                return await ctx.send(f"⚠️ You only have **{available_slots}** slot(s) remaining for this specific mission! You cannot deploy {len(targets)} right now.")
            # ==========================================
            # 3. Resolve ALL Box Numbers simultaneously (The Batch Fetch Fix)
            # ==========================================
            placeholders = ', '.join('?' for _ in targets)
            query = f"""
                WITH Roster AS (
                    SELECT cp.instance_id, s.name, ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                    FROM caught_pokemon cp JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                    WHERE cp.user_id = ?
                    AND cp.instance_id NOT IN (SELECT instance_id FROM active_deployments)
                    AND cp.instance_id NOT IN (SELECT instance_id FROM gts_deposits)
                ) 
                SELECT instance_id, name FROM Roster WHERE box_number IN ({placeholders})
            """
            
            async with db.execute(query, [user_id] + targets) as cursor:
                team_data = await cursor.fetchall()
                
            if not team_data:
                return await ctx.send("❌ None of those specimens could be deployed. Check your Box Numbers!")
                
            deployed_names = []
            current_time = time.time()
            
            # 4. Safely loop through the confirmed IDs and deploy them!
            for instance_id, name in team_data:
                
                # Safety Cleanup: Strip Active Partner and Party status
                await db.execute("UPDATE users SET active_partner = NULL WHERE user_id = ? AND active_partner = ?", (user_id, instance_id))
                await db.execute("DELETE FROM user_party WHERE user_id = ? AND instance_id = ?", (user_id, instance_id))
                
                # Log the deployment
                await db.execute("""
                    INSERT INTO active_deployments (user_id, instance_id, start_time, mission_type) 
                    VALUES (?, ?, ?, ?)
                """, (user_id, instance_id, current_time, mission_type))
                
                deployed_names.append(name.capitalize())
                
            await db.commit()
            
            mission_name = FIELD_MISSIONS[mission_type]["name"]
            embed = discord.Embed(
                title=f"⛺ Mission Commenced: {mission_name}",
                description=f"**{ctx.author.name}** dispatched a team into the field:\n\n" + "\n".join([f"🔸 {n}" for n in deployed_names]),
                color=discord.Color.blue()
            )
            embed.set_footer(text="They have been temporarily removed from your PC. Use !return to recall the team.")
            await ctx.send(embed=embed)

    @commands.command(name="refine", aliases=["craft", "synthesize"])
    @checks.has_started()
    @checks.is_authorized()
    async def refine_item(self, ctx, *, blueprint: str):
        """Refines raw geological or biological materials into specialized research equipment."""
        user_id = str(ctx.author.id)
        blueprint_name = blueprint.lower().replace(" ", "-")
        
        # We can easily expand this dictionary later for Dynamax Bands and Z-Rings!
        LAB_BLUEPRINTS = {
            'mega-bracelet': {
                'cost': 1000, # Eco Tokens required for lab time
                'material': 'raw-keystone',
                'material_qty': 1,
                'display': '🧬 Mega Bracelet'
            },
            'dynamax-band': {
                'cost': 2500, # A heavier energy cost to contain the Dynamax particles safely
                'material': 'wishing-fragment',
                'material_qty': 3, # Requires cleaning up multiple anomalies!
                'display': '🔴 Dynamax Band'
            },
            # --- Z-RING BLUEPRINT ---
            'z-ring': {
                'cost': 1500, 
                'material': 'sparkling-stone',
                'material_qty': 2, 
                'display': '🌟 Z-Ring'
            }
        }
        
        if blueprint_name not in LAB_BLUEPRINTS:
            return await ctx.send("❌ That blueprint does not exist in the laboratory database.")
            
        recipe = LAB_BLUEPRINTS[blueprint_name]
        
        async with aiosqlite.connect(DB_FILE) as db:
        
            try:
                await db.execute("BEGIN TRANSACTION")
                
                # 1. Check Funding
                async with db.execute("SELECT eco_tokens FROM users WHERE user_id = ?", (user_id,)) as cursor:
                    user_data = await cursor.fetchone()
                current_funds = user_data[0] if user_data else 0
                
                if current_funds < recipe['cost']:
                    await db.rollback()
                    return await ctx.send(f"⚠️ Insufficient funding. You need **{recipe['cost']} Eco Tokens** to operate the refinement machinery.")
                    
                # 2. Check Raw Materials
                async with db.execute("SELECT quantity FROM user_inventory WHERE user_id = ? AND item_name = ?", (user_id, recipe['material'])) as cursor:
                    mat_data = await cursor.fetchone()
                
                if not mat_data or mat_data[0] < recipe['material_qty']:
                    await db.rollback()
                    return await ctx.send(f"⚠️ Missing materials. You need **{recipe['material_qty']}x {recipe['material'].replace('-', ' ').title()}** to synthesize this item.")
                    
                # 3. Process the Transaction (Deduct Funds & Materials)
                await db.execute("UPDATE users SET eco_tokens = eco_tokens - ? WHERE user_id = ?", (recipe['cost'], user_id))
                await db.execute("UPDATE user_inventory SET quantity = quantity - ? WHERE user_id = ? AND item_name = ?", (recipe['material_qty'], user_id, recipe['material']))
                
                # 4. Synthesize the Output
                await db.execute("""
                    INSERT INTO user_inventory (user_id, item_name, quantity) 
                    VALUES (?, ?, 1) 
                    ON CONFLICT(user_id, item_name) 
                    DO UPDATE SET quantity = quantity + 1
                """, (user_id, blueprint_name))
                
                await db.commit()
                
                embed = discord.Embed(
                    title="⚙️ Synthesis Complete", 
                    description=f"You successfully refined the raw geological materials into a **{recipe['display']}**!\n\nThe mechanical bypass in your battle UI has been permanently authorized.",
                    color=discord.Color.purple()
                )
                await ctx.send(embed=embed)
                
            except Exception as e:
                if db.in_transaction:
                    await db.rollback()
                print(f"Refinement Error: {e}")
                await ctx.send("❌ A critical error occurred in the laboratory machinery.")
    
    @commands.command(name="habitat", aliases=["server", "environment"])
    @checks.has_started()
    @checks.is_authorized()
    async def habitat_status(self, ctx):
        guild_id = str(ctx.guild.id)
        
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute("SELECT ecosystem_score, active_biome, pollution_type FROM servers WHERE guild_id = ?", (guild_id,)) as cursor:
                server_data = await cursor.fetchone()
            
        if not server_data:
            return await ctx.send("This server's habitat hasn't been initialized yet. Start chatting to attract wildlife!")
            
        score, biome, pollution = server_data
        
        # Get the planetary state using our helper function
        planetary_state = get_planetary_cycle()
        
        # Format the UI based on the time
        if planetary_state == "day":
            time_icon, time_desc = "☀️", "Daytime (High visibility)"
            color = discord.Color.gold()
        elif planetary_state == "dusk":
            time_icon, time_desc = "🌇", "Dusk (Crepuscular activity peaking)"
            color = discord.Color.orange()
        elif planetary_state == "full-moon":
            time_icon, time_desc = "🌕", "Night (Full Moon - Rare lunar energy active!)"
            color = discord.Color.light_grey()
        else:
            time_icon, time_desc = "🌙", "Nighttime (Nocturnal wildlife active)"
            color = discord.Color.dark_purple()

        embed = discord.Embed(title=f"🌍 Habitat Status: {ctx.guild.name}", color=color)
        
        # Ecosystem Health Bar
        health_bar = "🟩" * (score // 10) + "🟥" * (10 - (score // 10))
        
        # The server's own clock, from `!config`. Worth showing rather than assuming:
        # the planetary cycle above decides what is nocturnal, and an admin who set a
        # timezone has no other way to check the bot agrees with them about what time
        # it is. Falls back to UTC, which is what an unconfigured server follows.
        settings = await cfg.get_all(guild_id)
        zone = settings.get('timezone') or 'UTC'
        now = cfg.guild_now(settings)

        embed.add_field(name="Current Biome", value=f"🌲 {biome.capitalize()}", inline=True)
        embed.add_field(name="Local Time", value=f"{time_icon} {time_desc}", inline=True)
        embed.add_field(name="Server Clock",
                        value=f"🕒 {now.strftime('%H:%M')} · `{zone}`", inline=True)
        embed.add_field(name="Active Hazards", value=f"⚠️ {pollution.replace('_', ' ').title()}" if pollution != 'none' else "✅ None", inline=False)
        embed.add_field(name=f"Ecosystem Health: {score}/100", value=health_bar, inline=False)

        # What that number actually BUYS. The score has always decided which types
        # appear and now scales the rare tiers too, and a bonus nobody can see is a
        # bonus nobody will work for - so it is stated in the units people care about
        # rather than left as a bar to interpret.
        rare_mult = ecosystem_multiplier(score, RARITY_SCORE_CEILING)
        shiny_mult = ecosystem_multiplier(score, SHINY_SCORE_CEILING)

        # The commands named here have to be ones that exist. `!plant` and `!clean` are
        # the two that raise the score, and `!intervene` is the one that answers an
        # active hazard - so which to suggest depends on whether there IS one.
        repair = "`!intervene`" if pollution != 'none' else "`!plant` and `!clean`"

        if rare_mult > 1.005:
            verdict = f"A healthy habitat turns up rarer things. Keep it up with {repair}."
        elif rare_mult < 0.995:
            verdict = f"A damaged habitat turns up fewer. Use {repair} to bring it back."
        else:
            verdict = f"Baseline rates. Raise the score with {repair} to improve them."

        embed.add_field(
            name="Encounter Rates",
            value=(f"⭐ Rare tiers **×{rare_mult:.2f}**  ·  "
                   f"✨ Shiny **×{shiny_mult:.2f}**\n*{verdict}*"),
            inline=False)

        await ctx.send(embed=embed)
async def setup(bot):
    await bot.add_cog(Ecology(bot))
    # Registered so a click on a card that outlived its View - a redeploy, a crash -
    # still reaches a handler. Without this the player gets Discord's own "This
    # interaction failed", which reads as a broken bot rather than a stale card.
    bot.add_dynamic_items(EncounterButton)