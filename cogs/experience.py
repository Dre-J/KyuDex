import discord
from discord.ext import commands
import aiosqlite
import time
import random
from utils.activity import is_command
from utils.constants import DB_FILE, current_skies
from utils.prefs import trainer_skies
from utils.regions import current_region
from utils.db_manager import check_evolution_trigger, evolution_context
from utils.formulas import get_xp_requirement
from utils.accounts import levelup_pings_enabled


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
            # 🚨 UPDATE: Apply both the new species ID and the inherited ability
            await db.execute("UPDATE caught_pokemon SET pokedex_id = ?, ability = ? WHERE instance_id = ?", 
                             (self.new_pokedex_id, self.new_ability, self.instance_id))
            await db.commit()

        for child in self.children:
            child.disabled = True
            
        await interaction.response.edit_message(
            content=f"🎉 **Success!** The specimen successfully evolved into **{self.new_species_name}** with the ability **{self.new_ability.title()}**!", 
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
        
class PassiveExperienceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Memory dict to prevent database spam: {user_id: last_message_timestamp}
        self.xp_cooldowns = {} 

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # 1. Ignore bots and webhook messages
        if message.author.bot:
            return

        # 2. Ignore command invocations. Passive XP is meant to reward conversation, and
        #    without this every `!catch`, `!battle` and `!party` paid out as well.
        #    The test moved to utils/activity.py when the spawn counter turned out to
        #    need the same sentence; the behaviour here is unchanged.
        if await is_command(self.bot, message):
            return

        user_id = str(message.author.id)
        current_time = time.time()

        # 2. Check Cooldown (e.g., 60 seconds between passive XP gains)
        last_xp_time = self.xp_cooldowns.get(user_id, 0)
        if current_time - last_xp_time < 60:
            return 
            
        # Update their cooldown timer
        self.xp_cooldowns[user_id] = current_time

        try:
            async with aiosqlite.connect(DB_FILE) as db:
                # 3. Check for an Active Partner
                async with db.execute("SELECT active_partner FROM users WHERE user_id = ?", (user_id,)) as cursor:
                    partner_record = await cursor.fetchone()
                
                if not partner_record or not partner_record[0]:
                    return # They don't have a specimen deployed to follow them

                instance_id = partner_record[0]

                # 4. Fetch the Specimen's Current Biological State
                async with db.execute("""
                    SELECT 
                        cp.level, cp.experience, cp.pokedex_id, cp.happiness, cp.held_item, cp.ability,
                        s.name, s.growth_rate, s.standard_abilities, s.hidden_ability,
                        cp.move_1, cp.move_2, cp.move_3, cp.move_4
                    FROM caught_pokemon cp
                    JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                    WHERE cp.instance_id = ?
                """, (instance_id,)) as cursor:
                    pokemon = await cursor.fetchone()

                if not pokemon:
                    return # Failsafe in case the partner data is orphaned

                (current_level, current_xp, pokedex_id, happiness, held_item,
                 current_ability, species_name, growth_rate, current_standards,
                 current_hidden, *known_moves) = pokemon

                # Stop if they are already max level
                if current_level >= 100:
                    return

                # 5. Calculate Passive XP Gain (e.g., 15 to 25 XP per valid message)
                xp_gain = random.randint(15, 25)
                new_total_xp = current_xp + xp_gain
                new_level = current_level

                # Dynamic Level Up Loop
                while new_level < 100 and new_total_xp >= get_xp_requirement(new_level, growth_rate):
                    new_level += 1

                # 6. Database Execution
                await db.execute("BEGIN TRANSACTION")
                try:
                    await db.execute("""
                        UPDATE caught_pokemon SET experience = ?, level = ? WHERE instance_id = ?
                    """, (new_total_xp, new_level, instance_id))
                    await db.commit()
                except Exception as e:
                    await db.rollback()
                    print(f"Passive XP DB Error: {e}")
                    return

                # ==========================================
                # 7. LEVEL UP & EVOLUTION TRIGGERS
                # ==========================================
                if new_level > current_level:
                    possible_evolution = None
                    
                    # The Everstone Bypass Shield
                    if held_item != 'everstone':
                        # THE central rulebook, which until now nothing called: this
                        # cog carried its own copy, and that copy said `req_level and
                        # new_level >= req_level`. The `req_level and` meant a rule with
                        # no minimum level could never fire, which is why Sneasel could
                        # not become Weavile at any level; and the `happiness` trigger it
                        # checked beside it does not exist in this table, so no friendship
                        # evolution had ever fired either. The shared version knows about
                        # the held item and the time of day as well.
                        match = await check_evolution_trigger(
                            db, pokedex_id, new_level, happiness,
                            await trainer_skies(
                                db, user_id,
                                message.guild.id if message.guild else None),
                            held_item, known_moves,
                            # Where the trainer is, which decides whether a Cubone
                            # becomes a Marowak or an Alolan one. Read the same way the
                            # skies above are, so both conditions this rulebook gates on
                            # arrive from the same shape of call.
                            region=await current_region(db, user_id),
                            # And what the SPECIMEN is: its sex, its real Attack and
                            # Defence, the habitat around it, the value it was caught
                            # with. Burmy, Tyrogue and Wurmple are decided by these.
                            specimen=await evolution_context(
                                db, instance_id,
                                message.guild.id if message.guild else None))

                        if match:
                            evolved_id = match[0]
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

                                possible_evolution = {"id": evolved_id, "name": new_species_name, "ability": new_ability}

                    # ==========================================
                    # 8. ANNOUNCE THE LEVEL UP / EVOLUTION
                    # ==========================================
                    # Passive XP fires on ORDINARY CONVERSATION, so this used to reply
                    # to - and ping - a chatty player every couple of minutes, in the
                    # middle of whatever they were actually talking about. An embed
                    # with the trainer's name written in it says the same thing without
                    # putting a red badge on their client.
                    #
                    # allowed_mentions is belt and braces: there is no mention left in
                    # the text, and this makes sure a future edit cannot reintroduce one
                    # by accident.
                    wants_pings = await levelup_pings_enabled(db, user_id)

                    embed = discord.Embed(
                        title="🎉 Level Up",
                        description=(f"**{message.author.display_name}**'s "
                                     f"**{species_name.capitalize()}** reached "
                                     f"**Level {new_level}**!"),
                        color=discord.Color.green()
                    )
                    silent = discord.AllowedMentions.none()

                    if possible_evolution:
                        view = EvolutionConfirmView(
                            owner_id=message.author.id,
                            instance_id=instance_id,
                            new_pokedex_id=possible_evolution["id"],
                            new_species_name=possible_evolution["name"],
                            new_ability=possible_evolution["ability"],
                            db_file=DB_FILE
                        )
                        embed.add_field(
                            name=f"✨ What? {species_name.capitalize()} is evolving!",
                            value="Do you want to initiate the process?",
                            inline=False
                        )
                        # An evolution prompt is sent whatever the preference says. It
                        # is not a notification - it is a decision with a 60 second
                        # window and no other way to reach it, since !evolve only
                        # handles the item-triggered kind. Silencing announcements must
                        # not silently cost somebody their evolutions.
                        #
                        # It still REPLIES, so the buttons are attached to the message
                        # that caused them in a busy channel - just without the ping.
                        view.message = await message.reply(
                            embed=embed, view=view,
                            mention_author=False, allowed_mentions=silent)
                    elif wants_pings:
                        await message.channel.send(embed=embed, allowed_mentions=silent)

        except Exception as e:
            print(f"Critical error in on_message XP handler: {e}")

async def setup(bot):
    await bot.add_cog(PassiveExperienceCog(bot))