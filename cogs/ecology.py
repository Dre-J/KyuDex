import discord
from discord.ext import commands, tasks
import sqlite3
import random
import math
import uuid
from utils.constants import DB_FILE, NATURES
from utils.formulas import get_xp_requirement, get_planetary_cycle, calculate_real_stat, generate_biometrics
from utils.db_manager import check_evolution_trigger
from utils import checks

# Memory dictionary to track what is currently spawned in each server
# Format: { 'guild_id': {'pokedex_id': 1, 'name': 'bulbasaur', 'capture_rate': 45} }
active_spawns = {}
MESSAGES_REQUIRED_FOR_SPAWN = 10 
user_active_spawns = {} # Tracks private expedition encounters (Key: user_id)

class StarterSelect(discord.ui.Select):
    def __init__(self, region: str):
        self.region = region
        
        # Define the ecological starters by region
        starters = {
            'Kanto': [('Bulbasaur', '1', '🌿 Grass/Poison'), ('Charmander', '4', '🔥 Fire'), ('Squirtle', '7', '💧 Water')],
            'Johto': [('Chikorita', '152', '🌿 Grass'), ('Cyndaquil', '155', '🔥 Fire'), ('Totodile', '158', '💧 Water')],
            'Hoenn': [('Treecko', '252', '🌿 Grass'), ('Torchic', '255', '🔥 Fire'), ('Totodile', '258', '💧 Water')],
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
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        try:
            # ==========================================
            # 1. CREATE THE RESEARCHER PROFILE
            # ==========================================
            # Initialize with 0 tokens and the default 'canopy' visa
            cursor.execute("""
                INSERT INTO users (user_id, eco_tokens, unlocked_visas) 
                VALUES (?, 0, 'canopy')
            """, (user_id,))
            
            # ==========================================
            # 2. GENERATE THE BIOLOGICAL SPECIMEN
            # ==========================================
            # Roll genetics and traits
            ivs = {stat: random.randint(0, 31) for stat in ['hp', 'attack', 'defense', 'sp_atk', 'sp_def', 'speed']}
            nature = random.choice(NATURES)
            is_shiny = 1 if random.randint(1, 4096) == 1 else 0
            
            # ==========================================
            # FETCH THE SPECIES' DEFAULT ABILITY
            # ==========================================
            cursor.execute("SELECT standard_abilities FROM base_pokemon_species WHERE pokedex_id = ?", (pokedex_id,))
            ability_row = cursor.fetchone()
            
            if ability_row and ability_row[0]:
                # If it's a comma-separated list (e.g., "overgrow,chlorophyll"), 
                # we split it, grab the first one, and strip any stray spaces.
                ability = ability_row[0].split(',')[0].strip()
            else:
                ability = 'overgrow' # Safe fallback
            
            # Fetch Level 1-5 starting moves
            cursor.execute("""
                SELECT move_name FROM species_movepool 
                WHERE pokedex_id = ? AND learn_method = 'level-up' AND level_learned <= 5
                ORDER BY level_learned DESC LIMIT 4
            """, (pokedex_id,))
            moves = [row[0] for row in cursor.fetchall()]
            
            # Pad empty move slots with 'none'
            while len(moves) < 4:
                moves.append('none')
                
            # Insert the specimen into the global wildlife database
            cursor.execute("""
                INSERT INTO caught_pokemon (
                    instance_id, user_id, pokedex_id, level, experience, nature, is_shiny, ability,
                    iv_hp, iv_attack, iv_defense, iv_sp_atk, iv_sp_def, iv_speed,
                    ev_hp, ev_attack, ev_defense, ev_sp_atk, ev_sp_def, ev_speed,
                    move_1, move_2, move_3, move_4, held_item, gmax_factor
                ) VALUES (
                    ?, ?, ?, 5, 0, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?,
                    0, 0, 0, 0, 0, 0,
                    ?, ?, ?, ?, 'none', 0
                )
            """, (
                instance_id, user_id, pokedex_id, nature, is_shiny, ability,
                ivs['hp'], ivs['attack'], ivs['defense'], ivs['sp_atk'], ivs['sp_def'], ivs['speed'],
                moves[0], moves[1], moves[2], moves[3]
            ))
            
            # ==========================================
            # 3. ASSIGN THE TACTICAL ROSTER
            # ==========================================
            # Assign to Slot 1 in the party
            cursor.execute("INSERT INTO user_party (user_id, instance_id, slot) VALUES (?, ?, 1)", (user_id, instance_id))
            
            # Set this specific specimen as their active follower/partner
            cursor.execute("UPDATE users SET active_partner = ? WHERE user_id = ?", (instance_id, user_id))
            
            # Commit the entire transaction to the database
            conn.commit()
            
            shiny_icon = "✨ " if is_shiny else ""
            await interaction.response.edit_message(
                content=f"🎉 **Registration Complete!**\n\nYou have secured your field license. Your new symbiotic partner, {shiny_icon}**{species_name}**, has been registered to your roster.\n\nUse `!profile` to view your clearance or `!expedition canopy` to begin your research!", 
                view=None
            )
            
        except sqlite3.IntegrityError:
            # This catches the edge case where they somehow run the command twice at the exact same time
            await interaction.response.edit_message(content="⚠️ Registration failed: You are already in the database.", view=None)
        except Exception as e:
            print(f"Starter Registration Error: {e}")
            await interaction.response.edit_message(content="❌ A critical database error occurred during registration. Please contact a developer.", view=None)
        finally:
            conn.close()

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

class PokemonPaginator(discord.ui.View):
    def __init__(self, bot, user_id, current_index, total_pokemon, active_partner_id):
        super().__init__(timeout=180) # Buttons disable after 3 minutes
        self.bot = bot
        self.user_id = user_id
        self.current_index = current_index
        self.total_pokemon = total_pokemon
        self.active_partner_id = active_partner_id
        self.update_button_states()

    def update_button_states(self):
        # Disable 'Prev' if we are at Pokemon #1, disable 'Next' if we are at the end
        self.children[0].disabled = self.current_index <= 1
        self.children[1].disabled = self.current_index >= self.total_pokemon

    async def generate_embed(self):
        """Fetches the data for the current Field Number and builds the UI."""
        conn = sqlite3.connect(DB_FILE) 
        cursor = conn.cursor()

        
        cursor.execute("""
            WITH Roster AS (
                SELECT 
                    cp.nickname, cp.pokedex_id, cp.level, cp.nature, cp.is_shiny, s.name, 
                    cp.instance_id, cp.original_user_id, cp.experience, s.growth_rate,
                    cp.iv_hp, cp.iv_attack, cp.iv_defense, cp.iv_sp_atk, cp.iv_sp_def, cp.iv_speed,
                    cp.ev_hp, cp.ev_attack, cp.ev_defense, cp.ev_sp_atk, cp.ev_sp_def, cp.ev_speed, 
                    cp.ability, cp.happiness, cp.held_item, cp.gmax_factor,
                    cp.height_multiplier, cp.weight_multiplier, s.height, s.weight,
                    ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as field_number
                FROM caught_pokemon cp
                JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                WHERE cp.user_id = ?
            )
            SELECT * FROM Roster WHERE field_number = ?
        """, (self.user_id, self.current_index))
        
        data = cursor.fetchone()
        
        if not data:
            conn.close()
            return discord.Embed(title="Error", description="Specimen data corrupted.")

        # Unpack all 31 variables!
        (nickname, poke_id, level, nature, is_shiny, name, actual_tag_id, original_user_id, current_xp, growth_rate,
         iv_hp, iv_atk, iv_def, iv_spa, iv_spd, iv_spe, ev_hp, ev_atk, ev_def, ev_spa, ev_spd, ev_spe, 
         ability, happiness, held_item, gmax_factor, 
         h_mult, w_mult, base_h, base_w, field_number) = data

        # Fetch Base Stats
        cursor.execute("SELECT stat_name, base_value FROM base_pokemon_stats WHERE pokedex_id = ?", (poke_id,))
        stats = {stat[0]: stat[1] for stat in cursor.fetchall()}
        conn.close()

        # --- CALCULATIONS ---
        display_title = f'"{nickname}" the {name.capitalize()}' if nickname else name.capitalize()
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
        # Fallbacks to 1.0 for specimens caught before the update
        h_mult = h_mult or 1.0
        w_mult = w_mult or 1.0
        
        actual_height_m = round((base_h / 10.0) * h_mult, 2)
        actual_weight_kg = round((base_w / 10.0) * w_mult, 2)
        
        size_tag = "Average"
        if h_mult <= 0.80: size_tag = "Teeny"
        elif h_mult <= 0.95: size_tag = "Small"
        elif h_mult >= 1.30: size_tag = "ALPHA"
        elif h_mult >= 1.06: size_tag = "Large"

        # --- BUILD EMBED ---
        base_repo = "https://raw.githubusercontent.com/Dre-J/pokebotsprites/master/sprites/pokemon/other/official-artwork"
        image_url = f"{base_repo}/shiny/{poke_id}.png" if is_shiny else f"{base_repo}/{poke_id}.png"
        color = discord.Color.gold() if is_shiny else discord.Color.green()
        title_prefix = "🌟 Shiny " if is_shiny else ""

        embed = discord.Embed(title=f"{title_prefix}{display_title}{gmax_icon}", color=color)
        embed.set_image(url=image_url)

        desc_prefix = "❤️ **Active Partner**\n" if actual_tag_id == self.active_partner_id else ""
        
        # Inject the Biometrics right below the Held Item!
        embed.description = f"{desc_prefix}**Level {level}** | **Nature:** {nature}\n🧬 **Ability:** {display_ability}\n🎒 **Held Item:** `{item_display}`\n📏 **Dimensions:** {size_tag} ({actual_height_m}m, {actual_weight_kg}kg)\n🤝 **Bond:** {bond_icon}\n✨ **XP:** {current_xp} / {xp_for_next_level}"

        stat_block = f"""
        **HP:** {real_hp} `(IV: {iv_hp})`
        **Attack:** {real_atk} `(IV: {iv_atk})`
        **Defense:** {real_def} `(IV: {iv_def})`
        **Sp. Atk:** {real_spa} `(IV: {iv_spa})`
        **Sp. Def:** {real_spd} `(IV: {iv_spd})`
        **Speed:** {real_spe} `(IV: {iv_spe})`
        """
        embed.add_field(name="Current Biological Stats", value=stat_block, inline=False)
        embed.set_footer(text=f"Field No. {field_number} of {self.total_pokemon} | Tag ID: {actual_tag_id[:8]}")

        return embed

    @discord.ui.button(label="◀️ Previous", style=discord.ButtonStyle.primary, custom_id="prev_poke")
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("❌ This is not your field notebook!", ephemeral=True)
        self.current_index -= 1
        self.update_button_states()
        embed = await self.generate_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.primary, custom_id="next_poke")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("❌ This is not your field notebook!", ephemeral=True)
        self.current_index += 1
        self.update_button_states()
        embed = await self.generate_embed()
        await interaction.response.edit_message(embed=embed, view=self)

class SurveyPaginator(discord.ui.View):
    def __init__(self, user_id, directives):
        super().__init__(timeout=180) # Disables after 3 minutes
        self.user_id = user_id
        self.directives = directives
        self.current_index = 0
        self.total_pages = len(directives)
        self.update_button_states()

    def update_button_states(self):
        # Disable Prev if on the first page, disable Next if on the last page
        self.children[0].disabled = self.current_index == 0
        self.children[1].disabled = self.current_index == self.total_pages - 1

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
        if obj_type == 'cull_type':
            task_title = f"⚠️ Invasive Species Management: {target.capitalize()}-Type (ID: {d_id})"
            desc = f"Defeat wild **{target.capitalize()}**-type specimens to restore equilibrium."
        elif obj_type == 'survey_species':
            task_title = f"🧬 Genetic Population Survey: {target.capitalize().replace('-', ' ')} (ID: {d_id})"
            desc = f"Successfully capture and tag wild **{target.capitalize().replace('-', ' ')}**."
        elif obj_type == 'trigger_mutation':
            task_title = f"📈 Kinetic Maturation Study: {target.capitalize()} (ID: {d_id})"
            desc = f"Trigger a biological evolution for a **{target.capitalize()}**."
        else:
            task_title = f"🔬 Field Research: {target.capitalize()} (ID: {d_id})"
            desc = f"Analyze **{target.capitalize()}**."
            
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

    @discord.ui.button(label="◀️ Previous", style=discord.ButtonStyle.secondary, custom_id="prev_quest")
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("❌ This is not your field notebook!", ephemeral=True)
        self.current_index -= 1
        self.update_button_states()
        embed = await self.generate_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.secondary, custom_id="next_quest")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("❌ This is not your field notebook!", ephemeral=True)
        self.current_index += 1
        self.update_button_states()
        embed = await self.generate_embed()
        await interaction.response.edit_message(embed=embed, view=self)

class InventoryPaginator(discord.ui.View):
    def __init__(self, ctx, rescued_pokemon, tokens):
        # timeout=180 means the buttons will stop working after 3 minutes to save bot memory
        super().__init__(timeout=180)
        self.ctx = ctx
        self.rescued_pokemon = rescued_pokemon
        self.tokens = tokens
        self.current_page = 0
        self.items_per_page = 10
        # Calculate the total number of pages needed
        self.max_pages = max(1, math.ceil(len(rescued_pokemon) / self.items_per_page))
        self.update_buttons()

    def update_buttons(self):
        # FIX 2: Access the physical button objects via the children array
        # self.children[0] is Prev, self.children[1] is Next
        self.children[0].disabled = self.current_page == 0
        self.children[1].disabled = self.current_page >= self.max_pages - 1

    def create_embed(self):
            start = self.current_page * self.items_per_page
            end = start + self.items_per_page
            chunk = self.rescued_pokemon[start:end]

            embed = discord.Embed(title=f"📋 {self.ctx.author.name}'s Ecological Survey", color=discord.Color.blue())
            embed.set_thumbnail(url=self.ctx.author.avatar.url if self.ctx.author.avatar else self.ctx.author.default_avatar.url)
            embed.add_field(name="Global Eco-Tokens", value=f"🪙 {self.tokens:,}", inline=False)

            # --- THE FIX: Just join the strings together! ---
            if chunk:
                embed.description = "\n".join(chunk)
            else:
                embed.description = "*No specimens recorded in this sector.*"
                
            embed.set_footer(text=f"Page {self.current_page + 1}/{self.max_pages} | Total Rescued: {len(self.rescued_pokemon)}")
            return embed

    @discord.ui.button(label="◀️ Prev", style=discord.ButtonStyle.primary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Security check: only the person who ran the command can click the buttons
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("This isn't your survey notebook!", ephemeral=True)
            
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("This isn't your survey notebook!", ephemeral=True)
            
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)



class Ecology(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.habitat_activity = {}
    
    # --- The Spawning Logic Extracted into a Helper Function ---
    async def trigger_activity_spawn(self, guild):
        guild_id = str(guild.id)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Check if a habitat channel is actually set up
        cursor.execute("SELECT spawn_channel_id, ecosystem_score, active_biome, pollution_type FROM servers WHERE guild_id = ?", (guild_id,))
        server_data = cursor.fetchone()
        
        if not server_data or not server_data[0]:
            conn.close()
            return # No channel set up, do nothing
            
        channel_id, score, biome, pollution = server_data
        channel = self.bot.get_channel(int(channel_id))
        
        if not channel:
            conn.close()
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
            cursor.execute("UPDATE servers SET ecosystem_score = ?, pollution_type = ? WHERE guild_id = ?", (new_score, disaster_type, guild_id))
            conn.commit()
            conn.close()

            await channel.send(f"{disasters[disaster_type]['msg']}\n*Biodiversity is dropping rapidly. Use `!intervene` or a `Purifier` to stabilize the area!*")
            return # Skip spawning to simulate wildlife fleeing the disaster!

        # --- INVASIVE RIFT OVERRIDE ---
        if current_pollution == 'spatial_rift':
            habitat_condition = "The local environment is being warped by invasive dimensional energy."
            rarity_name = "🛸 ULTRA BEAST"
            cursor.execute("SELECT pokedex_id, name, capture_rate FROM base_pokemon_species WHERE pokedex_id BETWEEN 793 AND 806 ORDER BY RANDOM() LIMIT 1;")
            spawned_data = cursor.fetchone()
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

            # Rarity Roll
            roll = random.random()
            if roll < 0.01: rarity_filter, rarity_name = "AND s.is_mythical = 1", "✨ MYTHICAL"
            elif roll < 0.05: rarity_filter, rarity_name = "AND s.is_legendary = 1 AND s.is_mythical = 0", "⭐ LEGENDARY"
            else: rarity_filter, rarity_name = "AND s.is_legendary = 0 AND s.is_mythical = 0", "Wild"

            query = f"""
                SELECT s.pokedex_id, s.name, s.capture_rate 
                FROM base_pokemon_species s
                JOIN base_pokemon_types t ON s.pokedex_id = t.pokedex_id
                WHERE t.type_name IN ({','.join(['?']*len(allowed_types))})
                AND s.pokedex_id NOT BETWEEN 793 AND 806 AND form_type IN ('base','alolan', 'galarian', 'hisuian', 'paldean')
                {rarity_filter} ORDER BY RANDOM() LIMIT 1;
            """
            cursor.execute(query, allowed_types)
            spawned_data = cursor.fetchone()
            
        conn.close()

        if not spawned_data:
            return

        poke_id, name, cap_rate = spawned_data
        is_shiny = random.randint(1, 4096) == 1 
        shiny_text = "🌟 **SHINY MUTATION** " if is_shiny else ""
        
        active_spawns[guild_id] = {
            'pokedex_id': poke_id, 'name': name, 'capture_rate': cap_rate, 'is_shiny': is_shiny 
        }
        
    # 1. Generate the Mutation Status
        is_shiny = random.randint(1, 4096) == 1 
        shiny_text = "🌟 **SHINY MUTATION** " if is_shiny else ""
        
        # 2. Update the active spawns memory
        active_spawns[guild_id] = {
            'pokedex_id': poke_id, 'name': name, 'capture_rate': cap_rate, 'is_shiny': is_shiny 
        }
        
        # 3. Format the Image URL based on Shiny Status
        base_repo_url = "https://raw.githubusercontent.com/Dre-J/pokebotsprites/refs/heads/master/sprites/pokemon/other/official-artwork"
        if is_shiny:
            image_url = f"{base_repo_url}/shiny/{poke_id}.png"
            embed_color = discord.Color.gold()
        else:
            image_url = f"{base_repo_url}/{poke_id}.png"
            embed_color = discord.Color.green()

        # 4. Build the Visual Camera Trap Embed
        embed = discord.Embed(
            title=f"📸 Habitat Activity Detected!", 
            description=f"🌍 *{habitat_condition}*\n\nA {shiny_text}**{rarity_name} {name.capitalize()}** has migrated into the area!\n\nUse `!catch {name}` to deploy equipment and rescue it.",
            color=embed_color
        )
        embed.set_image(url=image_url)
        embed.set_footer(text="Automated Field Camera Trap")

        await channel.send(embed=embed)

    async def execute_biome_shift(self, ctx, target_biome, title, description):
        guild_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)
        cost = 100
        required_cp = 10
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        try:
            # 2. Start the Atomic Transaction!
            cursor.execute("BEGIN TRANSACTION")
            
            # Check Contribution Points (Do they have local authority?)
            cursor.execute("SELECT contribution_points FROM guild_members WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
            member_data = cursor.fetchone()
            cp = member_data[0] if member_data else 0
            
            if cp < required_cp:
                await ctx.send(f"⚠️ You need at least {required_cp} Contribution Points in this server to lead a major ecological project. You currently have {cp}.")
                return
                
            # Check Global Funding (Do they have the Eco-Tokens?)
            cursor.execute("SELECT eco_tokens FROM users WHERE user_id = ?", (user_id,))
            user_data = cursor.fetchone()
            tokens = user_data[0] if user_data else 0
            
            if tokens < cost:
                await ctx.send(f"⚠️ This project requires {cost} Eco-Tokens in funding. You only have {tokens}.")
                return
                
            # Check if the biome is already set to the target
            cursor.execute("SELECT active_biome FROM servers WHERE guild_id = ?", (guild_id,))
            current_biome = cursor.fetchone()[0]
            
            if current_biome == target_biome:
                await ctx.send(f"The server is already a {target_biome.capitalize()} biome!")
                return

            # Execute the Shift! Deduct tokens and update the server
            cursor.execute("UPDATE users SET eco_tokens = eco_tokens - ? WHERE user_id = ?", (cost, user_id))
            cursor.execute("UPDATE servers SET active_biome = ? WHERE guild_id = ?", (target_biome, guild_id))
            conn.commit()
            
            # Send the celebration embed
            embed = discord.Embed(title=title, description=description, color=discord.Color.gold())
            embed.set_footer(text=f"Project funded and led by {ctx.author.name} (-{cost} Eco-Tokens)")
            await ctx.send(embed=embed)
            
        except Exception as e:
            # 3. ROLLBACK ADDED: If the database crashes, refund their tokens instantly!
            conn.rollback()
            await ctx.send("❌ A database error occurred during the biome shift. No funds were deducted.")
            print(f"Biome Shift Error: {e}")
            
        finally:
            conn.close()

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
        
        # 4. If the threshold is reached, trigger the spawn sequence!
        if self.habitat_activity[guild_id] >= MESSAGES_REQUIRED_FOR_SPAWN:
            self.habitat_activity[guild_id] = 0 # Reset the counter immediately

            #print(f"🌿 DEBUG: Spawn threshold reached in {message.guild.name}! Triggering spawn...")

            await self.trigger_activity_spawn(message.guild)
    
    @commands.command(name="start")
    @checks.is_authorized()
    async def start_journey(self, ctx):
        user_id = str(ctx.author.id)
        
        # Check if they already exist
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        if cursor.fetchone():
            conn.close()
            return await ctx.send("⚠️ You are already a registered researcher! You cannot pick another starter.")
        conn.close()
        
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
        
        if not biome_name:
            return await ctx.send("🧭 **Navigation Error:** Please specify a biome (e.g., `!expedition canopy` or `!expedition trench`).")
            
        biome = biome_name.lower()
        
        # 1. Define the Biome Ecological Parameters (Elemental Types)
        biome_data = {
            'canopy': {'types': "('grass', 'bug', 'poison', 'flying', 'normal')", 'emoji': '🌲'},
            'trench': {'types': "('water', 'ice')", 'emoji': '🌊'},
            'core': {'types': "('fire', 'ground', 'rock', 'fighting')", 'emoji': '🌋'},
            'sprawl': {'types': "('electric', 'steel', 'dark', 'ghost', 'psychic', 'fairy')", 'emoji': '🏙️'}
        }
        
        if biome not in biome_data:
            return await ctx.send("⚠️ Unknown biome. Available sectors: Canopy, Trench, Core, Sprawl.")
            
        # 2. Check if the user is already on an expedition
        if user_id in user_active_spawns:
            return await ctx.send("🛑 You are already tracking a private spawn! Catch, defeat, or run from it first.")
            
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        try:
            # 3. Verify Ecological Access (The Visa Check)
            cursor.execute("SELECT unlocked_visas FROM users WHERE user_id = ?", (user_id,))
            user_data = cursor.fetchone()
            
            # Default to canopy if they somehow don't have the column set
            visas = user_data[0] if user_data and user_data[0] else "canopy"
            
            if biome not in visas.split(','):
                conn.close()
                return await ctx.send(f"⛔ **ACCESS DENIED:** You do not have the required Visa for the **{biome.title()}**. Defeat the local Sector Warden to advance.")
            
            # 4. Generate the Biome-Specific Encounter (With Rarity Filter)
            type_tuple = biome_data[biome]['types']
            
            # Default to standard wildlife
            rarity_filter = "AND s.is_legendary = 0 AND s.is_mythical = 0"
            
            # Roll the ecological dice!
            rarity_roll = random.random()
            if rarity_roll <= 0.005: 
                # 0.5% chance for a Mythical anomaly
                rarity_filter = "AND s.is_mythical = 1"
            elif rarity_roll <= 0.015: 
                # 1% chance for a Legendary predator (up to 0.015 total)
                rarity_filter = "AND s.is_legendary = 1"

            # We inject the rarity_filter dynamically into the query
            cursor.execute(f"""
                SELECT DISTINCT s.pokedex_id, s.name, s.capture_rate 
                FROM base_pokemon_species s
                JOIN base_pokemon_types t ON s.pokedex_id = t.pokedex_id
                WHERE t.type_name IN {type_tuple} 
                AND s.pokedex_id NOT BETWEEN 793 AND 806 
                AND s.form_type IN ('base', 'alolan', 'galarian', 'hisuian', 'paldean')
                {rarity_filter}
                ORDER BY RANDOM() LIMIT 1
            """)
            
            spawn_data = cursor.fetchone()
            
            if not spawn_data:
                conn.close()
                return await ctx.send("📡 Scanner error: Could not locate native wildlife in this sector. Try again.")
                
            poke_id, poke_name, true_capture_rate = spawn_data
            
            # Roll for shiny (1/4096 standard rate)
            is_shiny = random.randint(1, 4096) == 1
            
            # 5. Lock the spawn to this specific user!
            user_active_spawns[user_id] = {
                'pokedex_id': poke_id,
                'name': poke_name,
                'is_shiny': is_shiny,
                'capture_rate': true_capture_rate # Dynamically assigned!
            }
            
            conn.close()
            
            # 6. UI Output
            shiny_icon = "✨ " if is_shiny else ""
            b_emoji = biome_data[biome]['emoji']
            
            embed = discord.Embed(
                title=f"{b_emoji} {biome.title()} Expedition",
                description=f"You traverse the environment and isolate a biological signal...\n\nA wild {shiny_icon}**{poke_name.capitalize().replace('-', ' ')}** appeared!",
                color=discord.Color.dark_green()
            )
            embed.set_footer(text="This is a private encounter. Use !catch [name]")
            
            
            # ---Format and attach the Specimen Image ---
            base_repo_url = "https://raw.githubusercontent.com/Dre-J/pokebotsprites/refs/heads/master/sprites/pokemon/other/official-artwork"
            
            if is_shiny:
                image_url = f"{base_repo_url}/shiny/{poke_id}.png"
                embed.color = discord.Color.gold() # Optionally override the color if it's shiny!
            else:
                image_url = f"{base_repo_url}/{poke_id}.png"
                
            embed.set_image(url=image_url)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            print(f"Expedition Error: {e}")
            await ctx.send("❌ A critical error occurred during field deployment.")
            if conn:
                conn.close()

    @commands.command(name="hint", aliases=["scan", "analyze_signal"])
    @checks.has_started()
    @checks.is_authorized()
    async def spawn_hint(self, ctx):
        """Uses field sensors to gather data on the current unidentified wild specimen."""
        guild_id = str(ctx.guild.id)
        
        # 1. Check if there is actually a signal to analyze
        if guild_id not in active_spawns: 
            return await ctx.send("📡 **Sensors Quiet:** There are no localized biological signals to analyze right now. Keep exploring!")
            
        target = active_spawns[guild_id]
        poke_name = target['name'] 
        poke_id = target['pokedex_id']
        
        # 2. Fetch the biological data from the registry
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        try:
            # Query the exact column name and fetch ALL matching rows
            cursor.execute("SELECT type_name FROM base_pokemon_types WHERE pokedex_id = ?", (poke_id,))
            db_data = cursor.fetchall()
        except sqlite3.OperationalError as e:
            print(f"Hint Query Error: {e}")
            db_data = [] # Return an empty list if it fails
        finally:
            conn.close()
            
        # 3. Format the Intelligence Report
        if db_data:
            # db_data looks like: [('grass',), ('poison',)]
            # We loop through the tuples, extract the strings, capitalize them, and join them together!
            types_list = [row[0].title() for row in db_data]
            type_str = " / ".join(types_list)
        else:
            type_str = "Unknown"
            
        masked_name = ""

        for i, char in enumerate(poke_name):
            if char == "-":
                masked_name += "- "
            elif i == 0 or (i > 0 and poke_name[i-1] == "-"):
                masked_name += f"{char.upper()} "
            else:
                masked_name += "_ "
                
        # 4. Render the Sensor Dashboard
        embed = discord.Embed(
            title="📡 Biological Sensor Readout",
            description="Your field equipment has isolated an unidentified specimen's signal nearby. Here is the partial telemetry data:",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Elemental Signature", value=f"`{type_str}`", inline=False)
        embed.add_field(name="Acoustic Syllable Profile", value=f"`{masked_name.strip()}`", inline=False)
        
        if target.get('is_shiny'):
            embed.set_footer(text="⚠️ ANOMALY DETECTED: The signal frequency exhibits a rare chromatic mutation!")
            
        await ctx.send(embed=embed)
    
    @commands.command(name="spawn", aliases=["force_spawn"])
    @commands.is_owner() # SECURITY: Only you can run this!
    async def force_spawn(self, ctx, target_species: str = None, force_shiny: bool = False):
        guild_id = str(ctx.guild.id)
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 1. SPECIFIC TARGET INJECTION
        if target_species:
            query = """
                SELECT pokedex_id, name, capture_rate 
                FROM base_pokemon_species 
                WHERE name = ? LIMIT 1;
            """
            cursor.execute(query, (target_species.lower(),))
            spawned_data = cursor.fetchone()
            
            if not spawned_data:
                await ctx.send(f"❌ Error: Could not locate `{target_species}` in the national database.")
                conn.close()
                return
                
            rarity_name = "Admin-Injected"
            habitat_condition = "A localized spatial anomaly has occurred due to Director intervention."
            is_shiny = force_shiny
            
        # 2. NORMAL OVERRIDE (If no specific Pokemon is typed)
        else:
            cursor.execute("SELECT ecosystem_score, active_biome, pollution_type FROM servers WHERE guild_id = ?", (guild_id,))
            server_data = cursor.fetchone()
            
            ecosystem_score = server_data[0] if server_data else 50 
            active_biome = server_data[1] if server_data else 'forest'
            current_pollution = server_data[2] if server_data else 'none'

            # --- INVASIVE RIFT OVERRIDE ---
            if current_pollution == 'spatial_rift':
                habitat_condition = "The local environment is being warped by invasive dimensional energy."
                rarity_name = "🛸 ULTRA BEAST"
                cursor.execute("SELECT pokedex_id, name, capture_rate FROM base_pokemon_species WHERE pokedex_id BETWEEN 793 AND 806 ORDER BY RANDOM() LIMIT 1;")
                spawned_data = cursor.fetchone()
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

                # Rarity Roll
                roll = random.random()
                if roll < 0.01: rarity_filter, rarity_name = "AND s.is_mythical = 1", "✨ MYTHICAL"
                elif roll < 0.05: rarity_filter, rarity_name = "AND s.is_legendary = 1 AND s.is_mythical = 0", "⭐ LEGENDARY"
                else: rarity_filter, rarity_name = "AND s.is_legendary = 0 AND s.is_mythical = 0", "Wild"

                query = f"""
                    SELECT s.pokedex_id, s.name, s.capture_rate 
                    FROM base_pokemon_species s
                    JOIN base_pokemon_types t ON s.pokedex_id = t.pokedex_id
                    WHERE t.type_name IN ({','.join(['?']*len(allowed_types))})
                    AND s.pokedex_id NOT BETWEEN 793 AND 806
                    {rarity_filter} ORDER BY RANDOM() LIMIT 1;
                """
                cursor.execute(query, allowed_types)
                spawned_data = cursor.fetchone()
                
                # The Genetic Mutation (Shiny) Roll 
                is_shiny = random.randint(1, 4096) == 1 

        conn.close()
        
    # 3. EXECUTE THE SPAWN
        if not spawned_data:
            return await ctx.send("The environment is currently too unstable to support life.")

        poke_id, name, cap_rate = spawned_data
        
        # Ensure Ultra Beasts get a shiny roll too if it wasn't defined!
        if 'is_shiny' not in locals():
            is_shiny = random.randint(1, 4096) == 1 

        shiny_text = "🌟 **SHINY MUTATION** " if is_shiny else ""
        
        # Update the active spawns memory
        active_spawns[guild_id] = {
            'pokedex_id': poke_id, 'name': name, 'capture_rate': cap_rate, 'is_shiny': is_shiny 
        }
        
        # Format the Image URL based on Shiny Status
        base_repo_url = "https://raw.githubusercontent.com/Dre-J/pokebotsprites/refs/heads/master/sprites/pokemon/other/official-artwork"
        if is_shiny:
            image_url = f"{base_repo_url}/shiny/{poke_id}.png"
            embed_color = discord.Color.gold()
        else:
            image_url = f"{base_repo_url}/{poke_id}.png"
            embed_color = discord.Color.green()

        # Build the Visual Camera Trap Embed
        embed = discord.Embed(
            title=f"📸 Habitat Activity Detected!", 
            description=f"🌍 *{habitat_condition}*\n\nA {shiny_text}**{rarity_name} {name.capitalize()}** has migrated into the area!\n\nUse `!catch {name}` to deploy equipment and rescue it.",
            color=embed_color
        )
        embed.set_image(url=image_url)
        embed.set_footer(text="Automated Field Camera Trap")

        await ctx.send(embed=embed)

    @commands.command(name="nickname", aliases=["name"])
    @checks.has_started()
    @checks.is_authorized()
    async def nickname_pokemon(self, ctx, tag_id: str, *, name: str):
        user_id = str(ctx.author.id)
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 1. Resolve Target (Box Number or UUID)
        if tag_id.isdigit() and len(tag_id) <= 6:
            cursor.execute("""
                WITH Roster AS (
                    SELECT instance_id, ROW_NUMBER() OVER(ORDER BY rowid ASC) as box_number
                    FROM caught_pokemon WHERE user_id = ?
                ) SELECT instance_id FROM Roster WHERE box_number = ?
            """, (user_id, int(tag_id)))
        else:
            cursor.execute("SELECT instance_id FROM caught_pokemon WHERE instance_id LIKE ? AND user_id = ?", (f"{tag_id}%", user_id))
            
        target = cursor.fetchone()
        
        if not target:
            conn.close()
            return await ctx.send(f"❌ Could not find a specimen matching `{tag_id}` in your survey.")
            
        actual_id = target[0]
        
        # 2. Update using the exact UUID
        cursor.execute("UPDATE caught_pokemon SET nickname = ? WHERE instance_id = ?", (name, actual_id))
        conn.commit()
        conn.close()
        
        await ctx.send(f"🏷️ Specimen `{actual_id[:8]}` has been successfully re-designated as **{name}**.")

    @commands.command(name="release", aliases=["reintroduce", "free"])
    @checks.has_started()
    @checks.is_not_in_trade()
    @checks.is_authorized()
    async def release_pokemon(self, ctx, tag_id: str):
        user_id = str(ctx.author.id)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 1. Resolve Target and Verify Ownership
        if tag_id.isdigit() and len(tag_id) <= 6:
            cursor.execute("""
                WITH Roster AS (
                    SELECT s.name, cp.level, cp.instance_id, ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                    FROM caught_pokemon cp
                    JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                    WHERE cp.user_id = ?
                ) SELECT name, level, instance_id FROM Roster WHERE box_number = ?
            """, (user_id, int(tag_id)))
        else:
            cursor.execute("""
                SELECT s.name, cp.level, cp.instance_id 
                FROM caught_pokemon cp 
                JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id 
                WHERE cp.instance_id LIKE ? AND cp.user_id = ?
            """, (f"{tag_id}%", user_id))
            
        pokemon = cursor.fetchone()
        
        if not pokemon:
            await ctx.send(f"❌ Could not find a specimen matching `{tag_id}` in your survey.")
            conn.close()
            return
            
        name, level, actual_tag = pokemon
        
        # 2. Safety Check A: Is this their Active Partner?
        cursor.execute("SELECT active_partner FROM users WHERE user_id = ?", (user_id,))
        partner_data = cursor.fetchone()
        
        if partner_data and partner_data[0] == actual_tag:
            await ctx.send("⚠️ You cannot release your Active Partner! Use `!partner` to assign a new lead researcher first.")
            conn.close()
            return

        # 3. Safety Check B: Is this specimen currently equipped to the Fieldwork Roster?
        cursor.execute("SELECT slot FROM user_party WHERE user_id = ? AND instance_id = ?", (user_id, actual_tag))
        party_data = cursor.fetchone()
        
        if party_data:
            await ctx.send(f"🛡️ **Safety Lock:** You cannot release a specimen that is actively deployed in your fieldwork roster (Slot {party_data[0]}). Please remove it from your party first.")
            conn.close()
            return

        # 4. Calculate Grant Reward (Base 10 + 3 per Level)
        reward = 10 + (level * 3)

        # 5. Execute the Release
        try:
            # We must use BEGIN TRANSACTION to ensure the deletion and reward are linked
            cursor.execute("BEGIN TRANSACTION")
            
            # Delete the specific row from the database
            cursor.execute("DELETE FROM caught_pokemon WHERE instance_id = ?", (actual_tag,))
            
            # Award the tokens
            cursor.execute("UPDATE users SET eco_tokens = eco_tokens + ? WHERE user_id = ?", (reward, user_id))
            
            conn.commit()
            
            embed = discord.Embed(title="🌿 Wildlife Reintroduced", color=discord.Color.green())
            embed.description = f"**{ctx.author.name}** successfully rehabilitated and released their **{name.capitalize()}** back into the wild."
            embed.add_field(name="Conservation Grant Awarded", value=f"🪙 +{reward} Eco-Tokens")
            embed.set_footer(text=f"Tag ID Deleted: {actual_tag[:8]}")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            conn.rollback() # If it fails, refund the Pokemon and abort the grant!
            print(f"Release Error: {e}")
            await ctx.send("❌ A critical database error occurred during the reintroduction process. The release has been safely aborted.")
        finally:
            conn.close()

    @commands.command(name="settag", aliases=["label"])
    @checks.has_started()
    @checks.is_authorized()
    async def set_custom_tag(self, ctx, tag_id: str, *, custom_tag: str):
        user_id = str(ctx.author.id)
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Resolve Target (Box Number or UUID)
        if tag_id.isdigit() and len(tag_id) <= 6:
            cursor.execute("""
                WITH Roster AS (
                    SELECT instance_id, ROW_NUMBER() OVER(ORDER BY rowid ASC) as box_number
                    FROM caught_pokemon WHERE user_id = ?
                ) SELECT instance_id FROM Roster WHERE box_number = ?
            """, (user_id, int(tag_id)))
        else:
            cursor.execute("SELECT instance_id FROM caught_pokemon WHERE instance_id LIKE ? AND user_id = ?", (f"{tag_id}%", user_id))
            
        target = cursor.fetchone()
        
        if not target:
            conn.close()
            return await ctx.send(f"❌ Could not find a specimen matching `{tag_id}` in your survey.")
            
        actual_id = target[0]
        
        cursor.execute("UPDATE caught_pokemon SET custom_tag = ? WHERE instance_id = ?", (custom_tag, actual_id))
        
        if cursor.rowcount > 0:
            await ctx.send(f"📁 Specimen `{actual_id[:8]}` has been categorized under the tag: **[{custom_tag}]**.")
            
        conn.commit()
        conn.close()

    @commands.command(name="partner", aliases=["buddy", "lead"])
    @checks.has_started()
    @checks.is_authorized()
    async def set_partner(self, ctx, tag_id: str):
        user_id = str(ctx.author.id)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Verify ownership and resolve target
        if tag_id.isdigit() and len(tag_id) <= 6:
            cursor.execute("""
                WITH Roster AS (
                    SELECT cp.instance_id, s.name, ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                    FROM caught_pokemon cp
                    JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                    WHERE cp.user_id = ?
                ) SELECT name, instance_id FROM Roster WHERE box_number = ?
            """, (user_id, int(tag_id)))
        else:
            cursor.execute("""
                SELECT s.name, cp.instance_id
                FROM caught_pokemon cp
                JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                WHERE cp.instance_id LIKE ? AND cp.user_id = ?
            """, (f"{tag_id}%", user_id))
        
        pokemon = cursor.fetchone()
        
        if not pokemon:
            await ctx.send(f"❌ Could not find a specimen matching `{tag_id}` in your survey notebook.")
            conn.close()
            return
            
        name, actual_tag = pokemon
        
        try:
            cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            cursor.execute("UPDATE users SET active_partner = ? WHERE user_id = ?", (actual_tag, user_id))
            conn.commit()
            
            await ctx.send(f"❤️ You have chosen **{name.capitalize()}** (`{actual_tag[:8]}`) as your lead fieldwork partner!")
        except Exception as e:
            await ctx.send("❌ A database error occurred while setting your partner.")
            print(f"Partner error: {e}")
        finally:
            conn.close()

    @commands.command(name="intervene", aliases=["respond"])
    @checks.has_started()
    @checks.is_authorized()
    async def intervene(self, ctx, tag_id: str):
        guild_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 1. Check if the server is actually in crisis
        cursor.execute("SELECT pollution_type, ecosystem_score FROM servers WHERE guild_id = ?", (guild_id,))
        server_data = cursor.fetchone()
        
        if not server_data or server_data[0] == 'none':
            await ctx.send("🌍 The environment is currently stable! Keep an eye on the monitors for future hazards.")
            conn.close()
            return
            
        active_hazard = server_data[0]
        current_score = server_data[1]
        
        # 2. Verify ownership and fetch the deployed Pokemon's types
        if tag_id.isdigit() and len(tag_id) <= 6:
            cursor.execute("""
                WITH Roster AS (
                    SELECT cp.pokedex_id, cp.instance_id, s.name, ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                    FROM caught_pokemon cp
                    JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                    WHERE cp.user_id = ?
                )
                SELECT r.name, t.type_name
                FROM Roster r
                JOIN base_pokemon_types t ON r.pokedex_id = t.pokedex_id
                WHERE r.box_number = ?
            """, (user_id, int(tag_id)))
        else:
            cursor.execute("""
                SELECT s.name, t.type_name
                FROM caught_pokemon cp
                JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                JOIN base_pokemon_types t ON s.pokedex_id = t.pokedex_id
                WHERE cp.instance_id LIKE ? AND cp.user_id = ?
            """, (f"{tag_id}%", user_id))
        
        rows = cursor.fetchall()
        if not rows:
            await ctx.send("❌ You don't have that specimen in your survey notebook.")
            conn.close()
            return
            
        poke_name = rows[0][0]
        poke_types = [row[1] for row in rows]
        
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
            conn.close()
            return

        # 4. Success! Clear the hazard and reward the player
        new_score = min(100, current_score + 20)
        tokens_earned = 50 
        
        try:
            cursor.execute("UPDATE servers SET pollution_type = 'none', ecosystem_score = ? WHERE guild_id = ?", (new_score, guild_id))
            cursor.execute("UPDATE users SET eco_tokens = eco_tokens + ? WHERE user_id = ?", (tokens_earned, user_id))
            cursor.execute("""
                INSERT INTO guild_members (user_id, guild_id, contribution_points)
                VALUES (?, ?, 10)
                ON CONFLICT(user_id, guild_id) DO UPDATE SET contribution_points = contribution_points + 10;
            """, (user_id, guild_id))
            
            conn.commit()
            
            embed = discord.Embed(title="🚨 Crisis Averted!", color=discord.Color.gold())
            embed.description = f"**{ctx.author.name}** deployed their {poke_name.capitalize()}!\n\nUsing its typing, it completely neutralized the **{active_hazard.replace('_', ' ').title()}**!"
            embed.add_field(name="Ecosystem Recovery", value=f"⬆️ +20 Points (Now {new_score}/100)", inline=True)
            embed.add_field(name="Hero's Grant", value=f"🪙 +{tokens_earned} Tokens\n⭐ +10 Contribution", inline=True)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            print(f"Intervention error: {e}")
        finally:
            conn.close()

    @commands.command(name="use")
    @checks.has_started()
    @checks.is_authorized()
    async def use_item(self, ctx, *, item_input: str):
        # --- DATA SANITIZATION ---
        formatted_item = item_input.strip().lower().replace(" ", "").replace("-", "")
        
        guild_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        try:
            # 1. Global Inventory Check (Saves us from writing this for every single item!)
            cursor.execute("SELECT quantity FROM user_inventory WHERE user_id = ? AND item_name = ?", (user_id, formatted_item))
            inv_data = cursor.fetchone()
            
            if not inv_data or inv_data[0] < 1:
                return await ctx.send(f"🎒 You don't have any `{item_input.title()}` in your field pack!")

            # ==========================================
            # 2. ITEM ROUTING LOGIC (The Dispatcher)
            # ==========================================
            
            if formatted_item == "purifier":
                # Check if the server actually needs purifying
                cursor.execute("SELECT pollution_type, ecosystem_score FROM servers WHERE guild_id = ?", (guild_id,))
                server_data = cursor.fetchone()
                
                if not server_data or server_data[0] == 'none':
                    return await ctx.send("🌍 This environment is already clear of major hazards! Save your Purifier for an emergency.")
                    
                pollution = server_data[0]
                current_score = server_data[1]
                
                # Deduct from inventory (Using formatted_item instead of hardcoding)
                cursor.execute("UPDATE user_inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_name = ?", (user_id, formatted_item))
                
                # Clear pollution and boost score by 15 (capping at 100)
                new_score = min(100, current_score + 15)
                cursor.execute("""
                    UPDATE servers 
                    SET pollution_type = 'none', ecosystem_score = ?, last_maintained = CURRENT_TIMESTAMP 
                    WHERE guild_id = ?
                """, (new_score, guild_id))
                
                # Reward the player
                cursor.execute("""
                    INSERT INTO guild_members (user_id, guild_id, contribution_points)
                    VALUES (?, ?, 5)
                    ON CONFLICT(user_id, guild_id) DO UPDATE SET contribution_points = contribution_points + 5;
                """, (user_id, guild_id))
                
                conn.commit()
                
                embed = discord.Embed(title="🫧 Environmental Hazard Cleared!", color=discord.Color.blue())
                embed.description = f"**{ctx.author.name}** deployed a Purifier and successfully eradicated the **{pollution.replace('_', ' ').title()}**!"
                embed.add_field(name="Ecosystem Health", value=f"⬆️ +15 Points (Now {new_score}/100)", inline=True)
                embed.add_field(name="Community Impact", value="⭐ +5 Contribution Points", inline=True)
                
                await ctx.send(embed=embed)

            # --- INVALID DEPLOYMENT ---
            else:
                return await ctx.send(f"⚠️ `{item_input.title()}` is a passive item and cannot be deployed directly from the backpack.")

        except Exception as e:
            conn.rollback()
            print(f"Error deploying item: {e}")
            await ctx.send("An error occurred while deploying the item. No items were consumed.")
        finally:
            conn.close()

    # --- Setup Habitat Channel ---
    @commands.command(name="sethabitat")
    @checks.has_started()
    @checks.is_authorized()
    @commands.has_permissions(manage_channels=True)
    async def set_habitat(self, ctx):
        guild_id = str(ctx.guild.id)
        channel_id = str(ctx.channel.id)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO servers (guild_id) VALUES (?)", (guild_id,))
        cursor.execute("UPDATE servers SET spawn_channel_id = ? WHERE guild_id = ?", (channel_id, guild_id))
        conn.commit()
        conn.close()
        
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
    @commands.cooldown(1, 3600, commands.BucketType.user)
    @checks.has_started()
    @checks.is_authorized()
    async def plant_flora(self, ctx):
        guild_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT ecosystem_score FROM servers WHERE guild_id = ?", (guild_id,))
        server_data = cursor.fetchone()
        score = server_data[0] if server_data else 50
            
        if score >= 100:
            ctx.command.reset_cooldown(ctx)
            await ctx.send("🌍 The ecosystem is already fully saturated with flora! Great job.")
            conn.close()
            return

        # Planting restores 1 to 3 health points, but gives a higher chance of rare spawns later
        health_restored = random.randint(1, 3)
        new_score = min(100, score + health_restored) 
        
        # Planting yields slightly fewer tokens than cleaning (5 to 15)
        tokens_earned = random.randint(5, 15)
        
        try:
            cursor.execute("UPDATE servers SET ecosystem_score = ? WHERE guild_id = ?", (new_score, guild_id))
            cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            cursor.execute("UPDATE users SET eco_tokens = eco_tokens + ? WHERE user_id = ?", (tokens_earned, user_id))
            
            cursor.execute("""
                INSERT INTO guild_members (user_id, guild_id, contribution_points)
                VALUES (?, ?, 1)
                ON CONFLICT(user_id, guild_id) DO UPDATE SET contribution_points = contribution_points + 1;
            """, (user_id, guild_id))
            
            conn.commit()
            
            embed = discord.Embed(title="🌱 Flora Restoration Logged", color=discord.Color.dark_green())
            embed.description = f"**{ctx.author.name}** planted native species to stabilize the soil and increase biodiversity!"
            embed.add_field(name="Ecosystem Health", value=f"⬆️ +{health_restored} (Now {new_score}/100)", inline=True)
            embed.add_field(name="Field Pay", value=f"🪙 +{tokens_earned} Eco-Tokens", inline=True)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            print(e)
        finally:
            conn.close()

    @commands.command(name="clean", aliases=["remediate"])
    @commands.cooldown(1, 3600, commands.BucketType.user) # 1 use per 3600 seconds (1 hour) per user
    @checks.has_started()
    @checks.is_authorized()
    async def clean_habitat(self, ctx):
        guild_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 1. Check current server status
        cursor.execute("SELECT ecosystem_score, pollution_type FROM servers WHERE guild_id = ?", (guild_id,))
        server_data = cursor.fetchone()
        
        if not server_data:
            # Initialize if not present
            cursor.execute("INSERT INTO servers (guild_id, ecosystem_score) VALUES (?, 50)", (guild_id,))
            score = 50
            pollution = 'none'
        else:
            score, pollution = server_data
            
        if score >= 100:
            # Reset their cooldown so they aren't punished for trying to clean a perfect server
            ctx.command.reset_cooldown(ctx)
            await ctx.send("🌍 The ecosystem here is already at 100% pristine health! Try `!plant` to maintain it, or visit another server.")
            conn.close()
            return

        # 2. Calculate Restoration and Rewards
        # Cleaning restores 2 to 5 health points
        health_restored = random.randint(2, 5)
        new_score = min(100, score + health_restored) 
        
        # Players earn 10 to 20 Eco-Tokens for their hard work
        tokens_earned = random.randint(10, 20)
        
        # 3. Update the Database
        try:
            # Update Server Health
            cursor.execute("UPDATE servers SET ecosystem_score = ? WHERE guild_id = ?", (new_score, guild_id))
            
            # Give Tokens to User
            cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            cursor.execute("UPDATE users SET eco_tokens = eco_tokens + ? WHERE user_id = ?", (tokens_earned, user_id))
            
            # Give Contribution Points
            cursor.execute("""
                INSERT INTO guild_members (user_id, guild_id, contribution_points)
                VALUES (?, ?, 1)
                ON CONFLICT(user_id, guild_id) DO UPDATE SET contribution_points = contribution_points + 1;
            """, (user_id, guild_id))
            
            conn.commit()
            
            # 4. Send the Report
            embed = discord.Embed(title="🧹 Habitat Remediation Successful", color=discord.Color.teal())
            embed.description = f"**{ctx.author.name}** spent an hour cleaning up the local environment!"
            embed.add_field(name="Ecosystem Health", value=f"⬆️ +{health_restored} (Now {new_score}/100)", inline=True)
            embed.add_field(name="Field Pay", value=f"🪙 +{tokens_earned} Eco-Tokens", inline=True)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send("Database error during the cleaning process.")
            print(e)
        finally:
            conn.close()

    @commands.command(name="release", aliases=["reintroduce", "free"])
    @checks.has_started()
    @checks.is_authorized()
    @checks.is_not_in_trade()
    async def release_pokemon(self, ctx, tag_id: str):
        user_id = str(ctx.author.id)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 1. Verify ownership
        cursor.execute("""
            SELECT s.name, cp.level, cp.instance_id 
            FROM caught_pokemon cp 
            JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id 
            WHERE cp.instance_id LIKE ? AND cp.user_id = ?
        """, (f"{tag_id}%", user_id))
        
        pokemon = cursor.fetchone()
        
        if not pokemon:
            await ctx.send(f"Could not find a specimen with Tag `{tag_id}` in your survey.")
            conn.close()
            return
            
        name, level, actual_tag = pokemon
        
        # 2. Safety Check: Is this their Active Partner?
        cursor.execute("SELECT active_partner FROM users WHERE user_id = ?", (user_id,))
        partner_data = cursor.fetchone()
        
        if partner_data and partner_data[0] == actual_tag:
            await ctx.send("⚠️ You cannot release your Active Partner! Use `!partner` to assign a new lead researcher first.")
            conn.close()
            return

        # 3. Calculate Grant Reward (Base 10 + 3 per Level)
        reward = 10 + (level * 3)

        # 4. Execute the Release
        try:
            # Delete the specific row from the database
            cursor.execute("DELETE FROM caught_pokemon WHERE instance_id = ?", (actual_tag,))
            
            # Award the tokens
            cursor.execute("UPDATE users SET eco_tokens = eco_tokens + ? WHERE user_id = ?", (reward, user_id))
            conn.commit()
            
            embed = discord.Embed(title="🌿 Wildlife Reintroduced", color=discord.Color.green())
            embed.description = f"**{ctx.author.name}** successfully rehabilitated and released their **{name.capitalize()}** back into the wild."
            embed.add_field(name="Conservation Grant Awarded", value=f"🪙 +{reward} Eco-Tokens")
            embed.set_footer(text=f"Tag ID Deleted: {actual_tag[:8]}")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            print(f"Release Error: {e}")
            await ctx.send("A database error occurred during the reintroduction process.")
        finally:
            conn.close()

    @commands.command(name="abandon", aliases=["drop", "discard", "archive"])
    @checks.has_started()
    @checks.is_authorized()
    async def abandon_directive(self, ctx, directive_id: int):
        """Discards an active ecological directive from your field notebook."""
        user_id = str(ctx.author.id)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        try:
            # 1. Verify the directive exists and belongs to this specific researcher
            cursor.execute("""
                SELECT objective_type, target_variable 
                FROM field_directives 
                WHERE directive_id = ? AND user_id = ? AND is_completed = 0
            """, (directive_id, user_id))
            
            target_quest = cursor.fetchone()
            
            if not target_quest:
                conn.close()
                return await ctx.send(f"⚠️ **Directive #{directive_id}** not found. Ensure you are providing a valid, active ID from your `!survey` ledger.")
            
            # 2. Execute the precise deletion
            cursor.execute("DELETE FROM field_directives WHERE directive_id = ? AND user_id = ?", (directive_id, user_id))
            conn.commit()
            
            obj_type, target_var = target_quest
            formatted_target = target_var.capitalize().replace('-', ' ')
            
            embed = discord.Embed(
                title="🗑️ Directive Archived",
                description=f"You have successfully abandoned **Directive #{directive_id}** ({formatted_target}).\n\nThe unviable tracking data has been cleared from your field notebook.",
                color=discord.Color.dark_gray()
            )
            await ctx.send(embed=embed)
            
        except ValueError:
            await ctx.send("❌ Please provide a valid numerical ID. Example: `!abandon 4`")
        except Exception as e:
            conn.rollback()
            print(f"Abandon error: {e}")
            await ctx.send("❌ A critical database error occurred while trying to drop the directive.")
        finally:
            conn.close()

    @commands.command(name="survey", aliases=["quests", "directives", "tasks"])
    @checks.has_started()
    @checks.is_authorized()
    async def field_survey(self, ctx):
        """Displays your active ecological field directives and progress."""
        user_id = str(ctx.author.id)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        try:
            # Fetch all active directives
            cursor.execute("""
                SELECT directive_id, objective_type, target_variable, required_amount, 
                       current_progress, reward_type, reward_payload
                FROM field_directives
                WHERE user_id = ? AND is_completed = 0
            """, (user_id,))
            
            directives = cursor.fetchall()
            
            if not directives:
                return await ctx.send("📋 **Field Notebook Empty:** You have no active ecological directives at this time. Explore the ecosystem to find encrypted data!")
                
            # Launch the Paginator!
            view = SurveyPaginator(user_id, directives)
            embed = await view.generate_embed()
            
            await ctx.send(embed=embed, view=view)
            
        except Exception as e:
            print(f"Survey UI Error: {e}")
            await ctx.send("❌ Error accessing the laboratory database.")
        finally:
            conn.close()

    @commands.command(name="inventory", aliases=["inv", "box"])
    @checks.has_started()
    @checks.is_authorized()
    async def inventory(self, ctx, sort_by: str = "recent"):
        user_id = str(ctx.author.id)
        sort_by = sort_by.lower()

        # --- 1. Dynamic Sorting Logic ---
        if sort_by in ["iv", "ivs", "stats"]:
            order_clause = "ORDER BY (cp.iv_hp + cp.iv_attack + cp.iv_defense + cp.iv_sp_atk + cp.iv_sp_def + cp.iv_speed) DESC"
        elif sort_by in ["name", "nickname", "az"]:
            order_clause = "ORDER BY COALESCE(cp.nickname, s.name) ASC"
        elif sort_by in ["tag", "label", "folder"]:
            order_clause = "ORDER BY cp.custom_tag DESC, cp.rowid DESC"
        elif sort_by in ["asc", "ascending"]:
            order_clause = "ORDER BY cp.rowid ASC"
        else:
            order_clause = "ORDER BY cp.rowid DESC"

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT eco_tokens FROM users WHERE user_id = ?", (user_id,))
        user_data = cursor.fetchone()
        tokens = user_data[0] if user_data else 0

        # --- 2. The Updated Query ---
        # We inject the ROW_NUMBER() function at the very end of the SELECT statement!
        query = f"""
            SELECT 
                s.name, cp.level, cp.is_shiny, cp.instance_id, 
                cp.nickname, cp.custom_tag,
                cp.iv_hp, cp.iv_attack, cp.iv_defense, cp.iv_sp_atk, cp.iv_sp_def, cp.iv_speed,
                ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
            FROM caught_pokemon cp
            JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
            WHERE cp.user_id = ?
            {order_clause}
        """
        cursor.execute(query, (user_id,))
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return await ctx.send("🎒 Your survey notebook is completely empty!")
        
        # --- 3. Formatting the Output ---
        lines = []
        for row in rows:
            species_name, level, is_shiny, tag_id, nickname, custom_tag = row[0:6]
            iv_tuple = row[6:12]
            box_number = row[12] # The newly injected chronological ID!
            
            iv_total = sum(iv_tuple)
            iv_percentage = int((iv_total / 186.0) * 100)
            
            display_name = f'"{nickname}" ({species_name.capitalize()})' if nickname else species_name.capitalize()
            shiny_icon = "🌟" if is_shiny else "🌿"
            tag_display = f" `[{custom_tag}]`" if custom_tag else ""
            
            # Formatted to prominently display the Box Number first!
            # Output: **#12** | 🌟 "Bubbles" (Squirtle) | Lvl 15 | IV: 85% | Tag: `123e4567` [Water]
            line = f"**#{box_number}** | {shiny_icon} **{display_name}** | Lvl {level} | IV: {iv_percentage}% | Tag: `{tag_id[:8]}`{tag_display}"
            lines.append(line)
  
        view = InventoryPaginator(ctx, lines, tokens)
        initial_embed = view.create_embed()
        await ctx.send(embed=initial_embed, view=view)

    @commands.command(name="catch")
    @checks.has_started()
    @checks.is_authorized()
    async def catch_pokemon(self, ctx, *, full_input: str):
        guild_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)

        # 1. THE PARSER: Split the user's input into separate words
        input_words = full_input.strip().lower().split()

        # 2. Extract the ball type if they typed one
        ball_type = "pokeball" # Default
        valid_balls = ["pokeball", "greatball", "ultraball", "masterball"]


        # Check if the very last word they typed is a valid ball
        if input_words[-1] in valid_balls:
            ball_type = input_words.pop() # Remove the ball from the list and save it

        # 3. DATA SANITIZATION: Rejoin whatever is left into the Pokemon's name
        # If they typed "wooper paldea greatball", it is now just "wooper-paldea"
        pokemon_name = "-".join(input_words)
    
        # ==========================================
        # LOCALIZATION INTERCEPTOR (Masuda Method Prep)
        # ==========================================
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        origin_lang = "ENG" # Default to English
        
        # Check if the name they typed exists as a foreign name in our matrix
        cursor.execute("SELECT english_name, language_tag FROM species_translations WHERE foreign_name = ?", (pokemon_name,))
        translation_data = cursor.fetchone()
        
        if translation_data:
            # Swap the typed name for the internal English name so the bot can process it!
            pokemon_name = translation_data[0] 
            origin_lang = translation_data[1] # e.g., 'FRE', 'JPN', 'GER'
            
        conn.close()
        # ==========================================

        equipment_stats = {
            "pokeball": {"multiplier": 1.0},
            "greatball": {"multiplier": 1.5},
            "ultraball": {"multiplier": 2.0},
            "masterball": {"multiplier": 255}
        }

        if ball_type not in equipment_stats:
            await ctx.send("Invalid equipment. Please use `pokeball`, `greatball`, or `ultraball`.")
            return
            
        # ==========================================
        # TARGET SELECTOR: Private vs Global Spawns (DEBUG MODE)
        # ==========================================
        print(f"\n--- DEBUG: Catch Attempt by {ctx.author.name} ({user_id}) ---")
        print(f"Typed Name: '{pokemon_name}'")
        print(f"Private Spawns Dict: {user_active_spawns.get(user_id)}")
        print(f"Global Spawns Dict (Guild {guild_id}): {active_spawns.get(guild_id)}")

        target = None
        is_private_spawn = False

        # 1. Check the researcher's private expedition first
        if user_id in user_active_spawns:
            expected_name = user_active_spawns[user_id]['name']
            print(f"Private spawn found. Expected Name: '{expected_name}', Typed Name: '{pokemon_name}'")
            if expected_name == pokemon_name:
                print("Match successful! Target locked to Private Spawn.")
                target = user_active_spawns[user_id]
                is_private_spawn = True
            else:
                print("Name mismatch on private spawn.")

        # 2. Check the global server environment
        if not is_private_spawn:
            if guild_id in active_spawns:
                expected_name = active_spawns[guild_id]['name']
                print(f"Global spawn found. Expected Name: '{expected_name}', Typed Name: '{pokemon_name}'")
                if expected_name == pokemon_name:
                    print("Match successful! Target locked to Global Spawn.")
                    target = active_spawns[guild_id]
                else:
                    print("Name mismatch on global spawn.")
            else:
                print("No global spawn active in this guild.")

        # 3. Abort if no match
        if target is None:
            print("Target is still None. Aborting catch.")
            return await ctx.send(f"There is no {pokemon_name.capitalize().replace('-', ' ')} here right now.")

        multiplier = equipment_stats[ball_type]["multiplier"]
        print(f"Target successfully locked. Proceeding to calculations...")
        # ==========================================
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        try:
            # Check their Inventory for specialized gear
            if ball_type != "pokeball":
                cursor.execute("SELECT quantity FROM user_inventory WHERE user_id = ? AND item_name = ?", (user_id, ball_type))
                inv_data = cursor.fetchone()
                quantity = inv_data[0] if inv_data else 0
                
                if quantity < 1:
                    await ctx.send(f"🎒 You don't have any {ball_type.capitalize()}s in your field pack! Buy some from the `!market`.")
                    return
            
            # Calculate Probability
            base_chance = target['capture_rate'] / 255.0
            final_chance = min(1.0, base_chance * multiplier)
            roll = random.random() 
            
            # Deduct the equipment from inventory
            if ball_type != "pokeball":
                cursor.execute("UPDATE user_inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_name = ?", (user_id, ball_type))
            
            # Check if the catch failed
            if roll > final_chance:
                conn.commit() 
                if is_private_spawn:
                    del user_active_spawns[user_id]
                else:
                    del active_spawns[guild_id]
                await ctx.send(f"💥 Oh no! The **{pokemon_name.capitalize()}** broke free from the {ball_type.capitalize()} and fled! (Catch chance was {final_chance:.1%})")
                return
        
            # ---The Genetic Ability Roll ---
            # Fetch the possible abilities for this specific species
            cursor.execute("SELECT standard_abilities, hidden_ability FROM base_pokemon_species WHERE pokedex_id = ?", (target['pokedex_id'],))
            ability_data = cursor.fetchone()
            
            assigned_ability = "Unknown"
            if ability_data:
                standard_str, hidden_str = ability_data
                standard_list = standard_str.split(",") if standard_str else ["Unknown"]
                
                # 20% chance to inherit the recessive Hidden Ability
                if hidden_str != "None" and random.random() <= 0.20:
                    assigned_ability = hidden_str
                else:
                    assigned_ability = random.choice(standard_list)
                    

            # Generate IVs, Instance ID, Nature, and BIOMETRICS
            instance_id = str(uuid.uuid4())
            nature = random.choice(NATURES)
            ivs = [random.randint(0, 31) for _ in range(6)]
            
            # ---BIOMETRIC ROLL ---
            h_mult, w_mult, size_class = generate_biometrics()
            
            # Apply the Alpha prefix dynamically!
            display_name = f"Alpha {pokemon_name}" if size_class == "Alpha" else pokemon_name

            cursor.execute("INSERT OR IGNORE INTO servers (guild_id) VALUES (?)", (guild_id,))
            cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        
            cursor.execute("""
                INSERT INTO guild_members (user_id, guild_id, contribution_points)
                VALUES (?, ?, 1)
                ON CONFLICT(user_id, guild_id) DO UPDATE SET contribution_points = contribution_points + 1;
            """, (user_id, guild_id))
            
            
            cursor.execute("""
                INSERT INTO caught_pokemon (
                    instance_id, user_id, pokedex_id, caught_in_guild, level, nature, is_shiny, original_user_id,
                    iv_hp, iv_attack, iv_defense, iv_sp_atk, iv_sp_def, iv_speed, ability, height_multiplier, weight_multiplier, origin_language
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (instance_id, user_id, target['pokedex_id'], guild_id, random.randint(1, 15), nature, target['is_shiny'], user_id, *ivs, assigned_ability, h_mult, w_mult, origin_lang))
            # ==========================================
            # DIRECTIVE TRACKER: POPULATION SURVEY
            # ==========================================
            # We use pokemon_name because your parser already perfectly formatted it (e.g., 'wooper-paldea')
            target_species = pokemon_name

            # 1. Increment the progress
            cursor.execute("""
                UPDATE field_directives
                SET current_progress = current_progress + 1
                WHERE user_id = ? AND objective_type = 'survey_species' AND target_variable = ? AND is_completed = 0
            """, (user_id, target_species))

            # 2. Check for completion
            cursor.execute("""
                SELECT required_amount, current_progress 
                FROM field_directives
                WHERE user_id = ? AND objective_type = 'survey_species' AND target_variable = ? AND is_completed = 0
            """, (user_id, target_species))
            
            survey_row = cursor.fetchone()
            if survey_row and survey_row[1] == survey_row[0]:
                await ctx.send(f"📡 **Directive Complete:** You successfully surveyed the local **{target_species.capitalize().replace('-', ' ')}** population! Run `!claim` to receive your funding.")
            # ==========================================

            # ==========================================
            # FIELD DATA RECOVERY (CATCH)
            # ==========================================
            found_notes = False # We set a flag to track if the drop occurred

            if random.random() <= 0.10: #100% for testing
                cursor.execute("""
                    INSERT INTO user_inventory (user_id, item_name, quantity) 
                    VALUES (?, 'encrypted-field-notes', 1) 
                    ON CONFLICT(user_id, item_name) 
                    DO UPDATE SET quantity = quantity + 1
                """, (user_id,))
                found_notes = True # The drop was successful!
                # You can append a quick note to your catch Embed description later!
            # ==========================================

            # Commit BOTH the caught pokemon and the updated quest progress at the exact same time!
            conn.commit()
            if is_private_spawn:
                del user_active_spawns[user_id]
            else:
                del active_spawns[guild_id]
            
            # Build the base narrative string
            base_desc = f"**{ctx.author.name}** successfully tagged the **{pokemon_name.capitalize().replace('-', ' ')}** using a {ball_type.capitalize()}!\n\nYour contribution to this server's ecosystem has increased."
            
            # If the flag is True, we cleanly append the alert!
            if found_notes:
                base_desc += "\n\n📝 **DATA RECOVERED:** You found some `Encrypted Field Notes` near the habitat! Run `!analyze notes`."

            shiny_icon = "🌟" if target['is_shiny'] else "🌿"
            
            embed = discord.Embed(
                title=f"{shiny_icon} Specimen Safely Rescued! [{origin_lang}]", 
                description=base_desc,
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Tag ID: {instance_id[:8]}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send("Database error during the tagging process.")
            print(f"Error: {e}")
        finally:
            conn.close()

    @commands.command(name="claim", aliases=["funding", "grant"])
    @checks.has_started()
    @checks.is_authorized()
    async def claim_rewards(self, ctx):
        """Claims funding and equipment for completed field directives."""
        user_id = str(ctx.author.id)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        try:
            # 1. Find all completed but unclaimed directives
            cursor.execute("""
                SELECT directive_id, reward_type, reward_payload, objective_type 
                FROM field_directives 
                WHERE user_id = ? AND current_progress >= required_amount AND is_completed = 0
            """, (user_id,))
            
            completed_tasks = cursor.fetchall()
            
            if not completed_tasks:
                conn.close()
                return await ctx.send("⚠️ You have no completed directives awaiting grant disbursement.")
                
            claim_log = "🎉 **Grants Disbursed!** The environmental council has approved your fieldwork:\n\n"
            
            # 2. Process each reward
            for d_id, r_type, r_payload, obj_type in completed_tasks:
                if r_type == 'eco_tokens':
                    amount = int(r_payload)
                    cursor.execute("UPDATE users SET eco_tokens = eco_tokens + ? WHERE user_id = ?", (amount, user_id))
                    claim_log += f"💰 Received **{amount}** Eco Tokens for completing a {obj_type.replace('_', ' ').title()} directive.\n"
                    
                elif r_type == 'item':
                    cursor.execute("""
                        INSERT INTO user_inventory (user_id, item_name, quantity) 
                        VALUES (?, ?, 1) 
                        ON CONFLICT(user_id, item_name) 
                        DO UPDATE SET quantity = quantity + 1
                    """, (user_id, r_payload))
                    claim_log += f"📦 Received **1x {r_payload.replace('-', ' ').title()}** from laboratory supply.\n"
                
                # 3. Mark the directive as claimed/archived
                cursor.execute("UPDATE field_directives SET is_completed = 1 WHERE directive_id = ?", (d_id,))
                
            conn.commit()
            
            embed = discord.Embed(description=claim_log, color=discord.Color.gold())
            await ctx.send(embed=embed)
            
        except Exception as e:
            conn.rollback()
            print(f"Claim error: {e}")
            await ctx.send("❌ An accounting error occurred while processing your grant funding.")
        finally:
            conn.close()

    @commands.command(name="analyze", aliases=["decode", "research"])
    @checks.has_started()
    @checks.is_authorized()
    async def analyze_notes(self, ctx, *, target: str):
        """Procedurally generates ecological directives from encrypted field data."""
        if target.lower() not in ["notes", "field notes", "encrypted-field-notes"]:
            return await ctx.send("⚠️ Please specify what you want to analyze (e.g., `!analyze notes`).")
            
        user_id = str(ctx.author.id)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        try:
            # 1. Check Inventory
            cursor.execute("SELECT quantity FROM user_inventory WHERE user_id = ? AND item_name = 'encrypted-field-notes'", (user_id,))
            inv_data = cursor.fetchone()
            
            if not inv_data or inv_data[0] < 1:
                conn.close()
                return await ctx.send("🎒 You do not have any `Encrypted Field Notes` to analyze!")
                
            # 2. Deduct the item
            cursor.execute("UPDATE user_inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_name = 'encrypted-field-notes'", (user_id,))
            
            # ==========================================
            # 3. PROCEDURAL DIRECTIVE GENERATION
            # ==========================================
            objective_types = ['cull_type', 'survey_species', 'trigger_mutation']
            chosen_obj = random.choice(objective_types)
            
            if chosen_obj == 'cull_type':
                elements = ['normal', 'fire', 'water', 'grass', 'electric', 'ice', 'fighting', 'poison', 'ground', 'flying', 'psychic', 'bug', 'rock', 'ghost', 'dragon', 'dark', 'steel', 'fairy']
                target_var = random.choice(elements)
                req_amt = random.randint(5, 12)
                rev_type = 'eco_tokens'
                rev_payload = str(req_amt * 250) # Scale payout based on the random difficulty!
                narrative_title = f"Invasive {target_var.capitalize()}-Type Culling"
                
            elif chosen_obj == 'survey_species':
                # Dynamically query the ecosystem for a random species!
                cursor.execute("SELECT name FROM base_pokemon_species ORDER BY RANDOM() LIMIT 1")
                db_species = cursor.fetchone()
                target_var = db_species[0] if db_species else 'pidgey'
                
                req_amt = random.randint(1, 3)
                rev_type = 'item'
                rev_payload = random.choice(['greatball', 'ultraball'])
                narrative_title = f"Genetic Population Survey: {target_var.capitalize().replace('-', ' ')}"
                
            else: # trigger_mutation
                target_var = 'any'
                req_amt = 1
                rev_type = 'item'
                rev_payload = random.choice(['rare-candy', 'raw-keystone', 'wishing-fragment'])
                narrative_title = "Kinetic Maturation Study"
            # ==========================================
            
            # 4. Inject the generated directive
            cursor.execute("""
                INSERT INTO field_directives (user_id, objective_type, target_variable, required_amount, reward_type, reward_payload)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, chosen_obj, target_var, req_amt, rev_type, rev_payload))
            
            conn.commit()
            
            embed = discord.Embed(
                title="💻 Data Decryption Successful",
                description=f"You fed the raw data into the laboratory mainframe. A new ecological directive has been extracted:\n\n**{narrative_title}**\n\nRun `!survey` to view your updated task parameters.",
                color=discord.Color.teal()
            )
            await ctx.send(embed=embed)
            
        except Exception as e:
            conn.rollback()
            print(f"Decryption error: {e}")
            await ctx.send("❌ A critical error occurred in the laboratory mainframe.")
        finally:
            conn.close()

    @commands.command(name="view", aliases=["inspect"])
    @checks.has_started()
    @checks.is_authorized()
    async def view_pokemon(self, ctx, tag_id: str = None):
        user_id = str(ctx.author.id)
        
        conn = sqlite3.connect(DB_FILE) 
        cursor = conn.cursor()
        
        # 1. Fetch total Pokemon count (Synchronized with the UI Join!)
        cursor.execute("""
            SELECT COUNT(*) 
            FROM caught_pokemon cp
            JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
            WHERE cp.user_id = ?
        """, (user_id,))
        total_pokemon = cursor.fetchone()[0]
        
        if total_pokemon == 0:
            conn.close()
            return await ctx.send("🎒 Your field notebook is completely empty!")
            
        cursor.execute("SELECT active_partner FROM users WHERE user_id = ?", (user_id,))
        partner_data = cursor.fetchone()
        active_partner_id = partner_data[0] if partner_data else None
        
        # 2. Determine the Target Index
        target_index = 1
        
        if not tag_id:
            if not active_partner_id:
                conn.close()
                return await ctx.send("You don't have an Active Partner! Use `!view [Number]`.")
                
            # Synchronized Roster CTE
            cursor.execute("""
                WITH Roster AS (
                    SELECT cp.instance_id, ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as field_number
                    FROM caught_pokemon cp
                    JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                    WHERE cp.user_id = ?
                ) SELECT field_number FROM Roster WHERE instance_id = ?
            """, (user_id, active_partner_id))
            
            result = cursor.fetchone()
            target_index = result[0] if result else 1
            
        elif tag_id.lower() in ["new", "latest", "last"]:
            target_index = total_pokemon # The very last one!
            
        # THE FIX: Ensure it's treated as a box index ONLY if it's less than 6 digits!
        # (Since UUID tags are 8 characters long)
        elif tag_id.isdigit() and len(tag_id) <= 6:
            target_index = int(tag_id)
            if target_index < 1 or target_index > total_pokemon:
                conn.close()
                return await ctx.send(f"⚠️ Invalid index. You only have {total_pokemon} intact specimens.")
                
        else:
            # It's a UUID tag! Synchronized Roster CTE for perfect indexing.
            cursor.execute("""
                WITH Roster AS (
                    SELECT cp.instance_id, ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as field_number
                    FROM caught_pokemon cp
                    JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                    WHERE cp.user_id = ?
                ) SELECT field_number FROM Roster WHERE instance_id LIKE ?
            """, (user_id, f"{tag_id}%"))
            
            res = cursor.fetchone()
            if not res:
                conn.close()
                return await ctx.send(f"⚠️ Could not find an intact specimen matching Tag ID `{tag_id}`.")
            target_index = res[0]
            
        conn.close()

        # 3. Launch the Paginator!
        view = PokemonPaginator(self.bot, user_id, target_index, total_pokemon, active_partner_id)
        embed = await view.generate_embed()
        
        await ctx.send(embed=embed, view=view)

    @commands.command(name="deploy", aliases=["fieldwork"])
    @commands.cooldown(1, 3600, commands.BucketType.user) # 1 expedition per hour
    @checks.has_started()
    @checks.is_authorized()
    async def deploy_pokemon(self, ctx, tag_id: str = None):
        user_id = str(ctx.author.id)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # ==========================================
        # 1. RESOLVE THE TARGET (Partner, Box Number, or UUID)
        # ==========================================
        actual_tag = None
        
        if not tag_id:
            cursor.execute("SELECT active_partner FROM users WHERE user_id = ?", (user_id,))
            partner_data = cursor.fetchone()
            
            if partner_data and partner_data[0]:
                actual_tag = partner_data[0]
            else:
                ctx.command.reset_cooldown(ctx)
                await ctx.send("⚠️ You haven't specified a Box Number or Tag ID, and you don't have an Active Partner equipped!")
                conn.close()
                return
                
        elif tag_id.isdigit() and len(tag_id) <= 6:
            # It's a Box Number! 
            cursor.execute("""
                WITH Roster AS (
                    SELECT instance_id, ROW_NUMBER() OVER(ORDER BY rowid ASC) as box_number
                    FROM caught_pokemon WHERE user_id = ?
                ) SELECT instance_id FROM Roster WHERE box_number = ?
            """, (user_id, int(tag_id)))
            
            res = cursor.fetchone()
            if not res:
                ctx.command.reset_cooldown(ctx)
                await ctx.send(f"❌ You don't have a specimen in Box `#{tag_id}` available for fieldwork.")
                conn.close()
                return
            actual_tag = res[0]
            
        else:
            # It's a UUID Tag!
            cursor.execute("SELECT instance_id FROM caught_pokemon WHERE instance_id LIKE ? AND user_id = ?", (f"{tag_id}%", user_id))
            res = cursor.fetchone()
            if not res:
                ctx.command.reset_cooldown(ctx)
                await ctx.send(f"❌ You don't have a specimen with tag `{tag_id}` available for fieldwork.")
                conn.close()
                return
            actual_tag = res[0]

        # ==========================================
        # 2. FETCH TYPES FOR THEMATIC MISSION
        # ==========================================
        # Notice we are now using exact '=' matching with actual_tag instead of LIKE!
        cursor.execute("""
            SELECT s.name, t.type_name
            FROM caught_pokemon cp
            JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
            JOIN base_pokemon_types t ON s.pokedex_id = t.pokedex_id
            WHERE cp.instance_id = ? AND cp.user_id = ?
        """, (actual_tag, user_id))
        
        rows = cursor.fetchall()
        
        # (We technically don't need this check anymore since we verified above, but good for safety!)
        if not rows:
            ctx.command.reset_cooldown(ctx)
            await ctx.send(f"❌ Could not retrieve biological data for specimen.")
            conn.close()
            return
            
        poke_name = rows[0][0]
        # A Pokemon can have 1 or 2 types. This creates a list of them (e.g., ['grass', 'poison'])
        poke_types = [row[1] for row in rows] 
        
        # Thematic missions based on biology
        missions = {
            'electric': "optimized a local solar microgrid ☀️",
            'water': "filtered microplastics out of the local river 🌊",
            'grass': "assisted in a massive reforestation project 🌲",
            'poison': "safely broke down and neutralized toxic waste ☣️",
            'fire': "performed a controlled burn to prevent future wildfires 🔥",
            'ground': "stabilized an eroding cliffside near the coast 🪨",
            'flying': "conducted an aerial survey of migratory bird patterns 🦅",
            'bug': "pollinated a struggling community garden 🌸",
            'steel': "helped recycle scrap metal into building materials 🏗️",
            'ice': "helped stabilize core temperatures in a local data center ❄️"
        }
        
        # Pick a mission based on one of the Pokemon's types (default to a generic one if no match)
        mission_text = "conducted a general biodiversity survey 📋"
        for pt in poke_types:
            if pt in missions:
                mission_text = missions[pt]
                break
                
        # --- Calculate Rewards & Experience ---
        tokens_earned = random.randint(15, 30)
        
        # Base XP earned from fieldwork
        base_xp_earned = random.randint(50, 150)
        
        # 1. Fetch the exact specimen data
        cursor.execute("""
            SELECT cp.level, cp.experience, cp.original_user_id, s.growth_rate, cp.pokedex_id, cp.happiness
            FROM caught_pokemon cp
            JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
            WHERE cp.instance_id = ? AND cp.user_id = ?
        """, (actual_tag, user_id))
        
        current_level, current_xp, original_owner, growth_rate, current_pokedex_id, current_happiness = cursor.fetchone()
        
        # 2. The "Traded" Specimen Boost
        if original_owner != user_id:
            xp_earned = int(base_xp_earned * 1.5)
            boost_text = "\n*(Traded Specimen Bonus: 1.5x XP!)*"
        else:
            xp_earned = base_xp_earned
            boost_text = ""
            
        new_total_xp = current_xp + xp_earned
        
        # ---Friendship/Happiness Boost ---
        # Max happiness in the biological data is usually 255
        new_happiness = min(255, current_happiness + random.randint(2, 5))
        
        # 3. Check for Level Up!
        xp_needed_for_next_level = get_xp_requirement(current_level, growth_rate)
        leveled_up = False
        new_level = current_level
        evolved_into_name = None
        
        if new_total_xp >= xp_needed_for_next_level and current_level < 100:
            leveled_up = True
            new_level += 1
            
            # --- Circadian Rhythm (Day/Night) Check ---
            current_planetary_state = get_planetary_cycle()
            
            evo_data = check_evolution_trigger(cursor, current_pokedex_id, new_level, new_happiness, current_planetary_state)
            
            if evo_data:
                new_pokedex_id, evolved_into_name = evo_data
                current_pokedex_id = new_pokedex_id # Update local variable for the DB save

        # THE SAFETY BLOCK
        try:
            # Update User Tokens
            cursor.execute("UPDATE users SET eco_tokens = eco_tokens + ? WHERE user_id = ?", (tokens_earned, user_id))
            
            # Update Pokemon XP, Level, Happiness, and POTENTIALLY the Pokedex ID if it evolved!
            cursor.execute("""
                UPDATE caught_pokemon 
                SET experience = ?, level = ?, happiness = ?, pokedex_id = ? 
                WHERE instance_id = ?
            """, (new_total_xp, new_level, new_happiness, current_pokedex_id, actual_tag))
            
            conn.commit()
            
            embed = discord.Embed(title="🎒 Fieldwork Expedition Complete!", color=discord.Color.green())
            
            # Adjust the description if a metamorphosis occurred
            if evolved_into_name:
                embed.description = f"**{ctx.author.name}** deployed their **{poke_name.capitalize()}** into the field!\n\nUsing its natural biology, it {mission_text}\n\n✨ **WHAT'S THIS?!** The intense fieldwork triggered a biological metamorphosis! Your specimen evolved into a **{evolved_into_name.capitalize()}**!"
            else:
                embed.description = f"**{ctx.author.name}** deployed their **{poke_name.capitalize()}** into the field!\n\nUsing its natural biology, it {mission_text}"
            
            embed.add_field(name="Mission Funding", value=f"🪙 +{tokens_earned} Eco-Tokens", inline=True)
            embed.add_field(name="Combat Data", value=f"✨ +{xp_earned} XP {boost_text}", inline=True)
            
            if leveled_up:
                embed.add_field(name="🎉 Level Up!", value=f"Grew to **Level {new_level}**!", inline=False)
            else:
                embed.add_field(name="Progress", value=f"XP to next level: {xp_needed_for_next_level - new_total_xp}", inline=False)
                
            embed.set_footer(text=f"Tag ID: {actual_tag[:8]}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            print(f"Deploy error: {e}")
            await ctx.send("Oh no! The fieldwork data was corrupted during transmission.")
            
        finally:
            conn.close()

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
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        try:
            cursor.execute("BEGIN TRANSACTION")
            
            # 1. Check Funding
            cursor.execute("SELECT eco_tokens FROM users WHERE user_id = ?", (user_id,))
            user_data = cursor.fetchone()
            current_funds = user_data[0] if user_data else 0
            
            if current_funds < recipe['cost']:
                conn.rollback()
                return await ctx.send(f"⚠️ Insufficient funding. You need **{recipe['cost']} Eco Tokens** to operate the refinement machinery.")
                
            # 2. Check Raw Materials
            cursor.execute("SELECT quantity FROM user_inventory WHERE user_id = ? AND item_name = ?", (user_id, recipe['material']))
            mat_data = cursor.fetchone()
            
            if not mat_data or mat_data[0] < recipe['material_qty']:
                conn.rollback()
                return await ctx.send(f"⚠️ Missing materials. You need **{recipe['material_qty']}x {recipe['material'].replace('-', ' ').title()}** to synthesize this item.")
                
            # 3. Process the Transaction (Deduct Funds & Materials)
            cursor.execute("UPDATE users SET eco_tokens = eco_tokens - ? WHERE user_id = ?", (recipe['cost'], user_id))
            cursor.execute("UPDATE user_inventory SET quantity = quantity - ? WHERE user_id = ? AND item_name = ?", (recipe['material_qty'], user_id, recipe['material']))
            
            # 4. Synthesize the Output
            cursor.execute("""
                INSERT INTO user_inventory (user_id, item_name, quantity) 
                VALUES (?, ?, 1) 
                ON CONFLICT(user_id, item_name) 
                DO UPDATE SET quantity = quantity + 1
            """, (user_id, blueprint_name))
            
            conn.commit()
            
            embed = discord.Embed(
                title="⚙️ Synthesis Complete", 
                description=f"You successfully refined the raw geological materials into a **{recipe['display']}**!\n\nThe mechanical bypass in your battle UI has been permanently authorized.",
                color=discord.Color.purple()
            )
            await ctx.send(embed=embed)
            
        except Exception as e:
            conn.rollback()
            print(f"Refinement Error: {e}")
            await ctx.send("❌ A critical error occurred in the laboratory machinery.")
        finally:
            conn.close()
    
    @commands.command(name="habitat", aliases=["server", "environment"])
    @checks.has_started()
    @checks.is_authorized()
    async def habitat_status(self, ctx):
        guild_id = str(ctx.guild.id)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT ecosystem_score, active_biome, pollution_type FROM servers WHERE guild_id = ?", (guild_id,))
        server_data = cursor.fetchone()
        conn.close()
        
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
        
        embed.add_field(name="Current Biome", value=f"🌲 {biome.capitalize()}", inline=True)
        embed.add_field(name="Local Time", value=f"{time_icon} {time_desc}", inline=True)
        embed.add_field(name="Active Hazards", value=f"⚠️ {pollution.replace('_', ' ').title()}" if pollution != 'none' else "✅ None", inline=False)
        embed.add_field(name=f"Ecosystem Health: {score}/100", value=health_bar, inline=False)
        
        await ctx.send(embed=embed)   
async def setup(bot):
    await bot.add_cog(Ecology(bot))