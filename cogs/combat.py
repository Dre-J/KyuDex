import discord
import time
import traceback
from discord.ext import commands
import sqlite3
import random
import math
from utils.formulas import calculate_damage, calculate_stats, fetch_base_stats, calculate_real_stat, apply_entry_hazards, check_consumables
from utils.constants import DB_FILE, NATURE_MULTIPLIERS, TYPE_CHART, BIOLOGICAL_TRAITS
from utils import checks
import aiohttp
from io import BytesIO
from PIL import Image, ImageOps, ImageDraw, ImageFont

# The Ecological Gatekeepers
WARDEN_ROSTER = {
    'canopy': {
        'title': 'Canopy Warden',
        'biome_unlocked': 'trench',
        'reward_item': 'encrypted-field-notes',
        'reward_qty': 3,
        'team': [
            {
                'name': 'scyther',
                'level': 25,
                'ivs': {'hp': 31, 'attack': 31, 'defense': 31, 'sp_atk': 31, 'sp_def': 31, 'speed': 31},
                'evs': {'hp': 0, 'attack': 252, 'defense': 0, 'sp_atk': 0, 'sp_def': 0, 'speed': 252},
                'types': ['bug', 'flying'],
                'held_item': 'none',
                'moves': [
                    {'name': 'aerial-ace', 'power': 60, 'type': 'flying', 'class': 'physical', 'accuracy': 100, 'pp': 20, 'max_pp': 20},
                    {'name': 'fury-cutter', 'power': 40, 'type': 'bug', 'class': 'physical', 'accuracy': 95, 'pp': 20, 'max_pp': 20}
                ]
            }
        ]
    },
    'trench': {
        'title': 'Trench Warden',
        'biome_unlocked': 'core',
        'reward_item': 'mega-bracelet', 
        'reward_qty': 1,
        'team': [
            {
                'name': 'gyarados',
                'level': 40,
                'ivs': {'hp': 31, 'attack': 31, 'defense': 31, 'sp_atk': 31, 'sp_def': 31, 'speed': 31},
                'evs': {'hp': 4, 'attack': 252, 'defense': 0, 'sp_atk': 0, 'sp_def': 0, 'speed': 252},
                'types': ['water', 'flying'],
                'held_item': 'mystic-water',
                'moves': [
                    {'name': 'waterfall', 'power': 80, 'type': 'water', 'class': 'physical', 'accuracy': 100, 'pp': 15, 'max_pp': 15},
                    {'name': 'ice-fang', 'power': 65, 'type': 'ice', 'class': 'physical', 'accuracy': 95, 'pp': 15, 'max_pp': 15}
                ]
            }
        ]
    },
    'core': {
        'title': 'Core Warden',
        'biome_unlocked': 'sprawl',
        'reward_item': 'dynamax-band',
        'reward_qty': 1,
        'team': [
            {
                'name': 'camerupt',
                'level': 55,
                'ivs': {'hp': 31, 'attack': 31, 'defense': 31, 'sp_atk': 31, 'sp_def': 31, 'speed': 31},
                'evs': {'hp': 252, 'attack': 0, 'defense': 4, 'sp_atk': 252, 'sp_def': 0, 'speed': 0},
                'types': ['fire', 'ground'],
                'held_item': 'charcoal',
                'moves': [
                    {'name': 'earth-power', 'power': 90, 'type': 'ground', 'class': 'special', 'accuracy': 100, 'pp': 10, 'max_pp': 10},
                    {'name': 'lava-plume', 'power': 80, 'type': 'fire', 'class': 'special', 'accuracy': 100, 'pp': 15, 'max_pp': 15}
                ]
            }
        ]
    },
    'sprawl': {
        'title': 'Sprawl Warden',
        'biome_unlocked': 'apex', 
        'reward_item': 'z-ring',
        'reward_qty': 1,
        'team': [
            {
                'name': 'magnezone',
                'level': 70,
                'ivs': {'hp': 31, 'attack': 31, 'defense': 31, 'sp_atk': 31, 'sp_def': 31, 'speed': 31},
                'evs': {'hp': 252, 'attack': 0, 'defense': 0, 'sp_atk': 252, 'sp_def': 4, 'speed': 0},
                'types': ['electric', 'steel'],
                'held_item': 'magnet',
                'moves': [
                    {'name': 'thunderbolt', 'power': 90, 'type': 'electric', 'class': 'special', 'accuracy': 100, 'pp': 15, 'max_pp': 15},
                    {'name': 'flash-cannon', 'power': 80, 'type': 'steel', 'class': 'special', 'accuracy': 100, 'pp': 10, 'max_pp': 10}
                ]
            },
            {
                'name': 'gengar',
                'level': 72,
                'ivs': {'hp': 31, 'attack': 31, 'defense': 31, 'sp_atk': 31, 'sp_def': 31, 'speed': 31},
                'evs': {'hp': 4, 'attack': 0, 'defense': 0, 'sp_atk': 252, 'sp_def': 0, 'speed': 252},
                'types': ['ghost', 'poison'],
                'held_item': 'spell-tag',
                'moves': [
                    {'name': 'shadow-ball', 'power': 80, 'type': 'ghost', 'class': 'special', 'accuracy': 100, 'pp': 15, 'max_pp': 15},
                    {'name': 'sludge-bomb', 'power': 90, 'type': 'poison', 'class': 'special', 'accuracy': 100, 'pp': 10, 'max_pp': 10}
                ]
            }
        ]
    }
}

# Signature Gigantamax Overrides
GMAX_MOVES = {
    'charizard-gmax': {'type': 'fire', 'name': 'G-Max Wildfire', 'status_type': 'wildfire'},
    'venusaur-gmax': {'type': 'grass', 'name': 'G-Max Vine Lash','status_type': 'vine lash'},
    'blastoise-gmax': {'type': 'water', 'name': 'G-Max Cannonade', 'status_type': 'cannonade'},
    'pikachu-gmax': {'type': 'electric', 'name': 'G-Max Volt Crash', 'ailment': 'paralysis','target': 'all-opponents'},
    'snorlax-gmax': {'type': 'normal', 'name': 'G-Max Replenish'},
    'gengar-gmax': {'type': 'ghost', 'name': 'G-Max Terror'},
    'lapras-gmax': {'type': 'ice', 'name': 'G-Max Resonance'},
    'kingler-gmax': {'type': 'water', 'name': 'G-Max Foam Burst', 'stat_name': 'speed', 'stat_change': -2, 'target': 'all-opponents'},
    'butterfree-gmax': {'type': 'bug', 'name': 'G-Max Befuddle', 'ailment': 'paralysis','target': 'all-opponents'},
    'meowth-gmax': {'type': 'normal', 'name': 'G-Max Gold Rush', 'ailment': 'confusion','target': 'all-opponents'},
    'machamp-gmax': {'type': 'fighting', 'name': 'G-Max Chi Strike'},
    'eevee-gmax': {'type': 'normal', 'name': 'G-Max Cuddle', 'ailment': 'infatuation','target': 'all-opponents'},
    'garbodor-gmax': {'type': 'poison', 'name': 'G-Max Malodor', 'ailment': 'poison','target': 'all-opponents'},
    'melmetal-gmax': {'type': 'steel', 'name': 'G-Max Meltdown'},
    'rillaboom-gmax': {'type': 'grass', 'name': 'G-Max Drum Solo', 'power': 160},
    'cinderace-gmax': {'type': 'fire', 'name': 'G-Max Fireball', 'power': 160},
    'inteleon-gmax': {'type': 'water', 'name': 'G-Max Hydrosnipe', 'power': 160},
    'corviknight-gmax': {'type': 'flying', 'name': 'G-Max Wind Rage'},
    'orbeetle-gmax': {'type': 'psychic', 'name': 'G-Max Gravitas'},
    'drednaw-gmax': {'type': 'water', 'name': 'G-Max Stonesurge'},
    'coalossal-gmax': {'type': 'rock', 'name': 'G-Max Volcalith', 'status_type': 'volcalith'},
    'flapple-gmax': {'type': 'grass', 'name': 'G-Max Tartness', 'stat_name': 'evasion', 'stat_change': -1,'target': 'all-opponents'},
    'appletun-gmax': {'type': 'grass', 'name': 'G-Max Sweetness'},
    'sandaconda-gmax': {'type': 'ground', 'name': 'G-Max Sandblast'},
    'toxtricity-gmax': {'type': 'electric', 'name': 'G-Max Stun Shock', "ailment": "poison"},
    'centiskorch-gmax': {'type': 'fire', 'name': 'G-Max Centiferno'},
    'hatterene-gmax': {'type': 'fairy', 'name': 'G-Max Smite', 'ailment': 'confusion','target': 'all-opponents'},
    'grimmsnarl-gmax': {'type': 'dark', 'name': 'G-Max Snooze', 'ailment': 'sleep', 'ailment_chance': 50 ,'target': 'all-opponents'},
    'alcremie-gmax': {'type': 'fairy', 'name': 'G-Max Finale', 'healing': 16.5,'target': 'user-and-allies'},
    'copperajah-gmax': {'type': 'steel', 'name': 'G-Max Steelsurge'},
    'duraludon-gmax': {'type': 'dragon', 'name': 'G-Max Depletion'},
    'urshifu-single-strike-gmax': {'type': 'dark', 'name': 'G-Max Max One Blow'},
    'urshifu-rapid-strike-gmax': {'type': 'dark', 'name': 'G-Max Max Rapid Flow'}
}

# The Biological Payload for Dynamax Particles
MAX_MOVES = {
    'normal': {'name': 'Max Strike', 'stat': 'speed', 'change': -1, 'target': 'defender'},
    'fire': {'name': 'Max Flare', 'weather': 'sun'},
    'water': {'name': 'Max Geyser', 'weather': 'rain'},
    'electric': {'name': 'Max Lightning'}, 
    'grass': {'name': 'Max Overgrowth'},
    'ice': {'name': 'Max Hailstorm', 'weather': 'hail'},
    'fighting': {'name': 'Max Knuckle', 'stat': 'attack', 'change': 1, 'target': 'attacker'},
    'poison': {'name': 'Max Ooze', 'stat': 'sp_atk', 'change': 1, 'target': 'attacker'},
    'ground': {'name': 'Max Quake', 'stat': 'sp_def', 'change': 1, 'target': 'attacker'},
    'flying': {'name': 'Max Airstream', 'stat': 'speed', 'change': 1, 'target': 'attacker'},
    'psychic': {'name': 'Max Mindstorm'},
    'bug': {'name': 'Max Flutterby', 'stat': 'sp_atk', 'change': -1, 'target': 'defender'},
    'rock': {'name': 'Max Rockfall', 'weather': 'sand'},
    'ghost': {'name': 'Max Phantasm', 'stat': 'defense', 'change': -1, 'target': 'defender'},
    'dragon': {'name': 'Max Wyrmwind', 'stat': 'attack', 'change': -1, 'target': 'defender'},
    'dark': {'name': 'Max Darkness', 'stat': 'sp_def', 'change': -1, 'target': 'defender'},
    'steel': {'name': 'Max Steelspike', 'stat': 'defense', 'change': 1, 'target': 'attacker'},
    'fairy': {'name': 'Max Starfall'}
}

WEATHER_MOVES = {
    'rain-dance': 'rain',
    'sunny-day': 'sun',
    'sandstorm': 'sand',
    'hail': 'hail',
    'snowscape': 'hail',
    'Max Flare': 'sun', 
    'Max Geyser': 'rain', 
    'Max Hailstorm': 'hail', 
    'Max Rockfall': 'sand'
}

WEATHER_MESSAGES = {
    'rain': "🌧️ A heavy rain began to fall!",
    'sun': "☀️ The sunlight turned incredibly harsh!",
    'sand': "🌪️ A vicious sandstorm kicked up!",
    'hail': "❄️ It started to hail!"
}

Z_MOVE_NAMES = {
    'normal': 'Breakneck Blitz', 'fire': 'Inferno Overdrive', 'water': 'Hydro Vortex',
    'electric': 'Gigavolt Havoc', 'grass': 'Bloom Doom', 'ice': 'Subzero Slammer',
    'fighting': 'All-Out Pummeling', 'poison': 'Acid Downpour', 'ground': 'Tectonic Rage',
    'flying': 'Supersonic Skystrike', 'psychic': 'Shattered Psyche', 'bug': 'Savage Spin-Out',
    'rock': 'Continental Crush', 'ghost': 'Never-Ending Nightmare', 'dragon': 'Devastating Drake',
    'dark': 'Black Hole Eclipse', 'steel': 'Corkscrew Crash', 'fairy': 'Twinkle Tackle'
}

Z_CRYSTAL_TYPES = {
    'normalium-z': 'normal', 'firium-z': 'fire', 'waterium-z': 'water',
    'electrium-z': 'electric', 'grassium-z': 'grass', 'icium-z': 'ice',
    'fightinium-z': 'fighting', 'poisonium-z': 'poison', 'groundium-z': 'ground',
    'flyinium-z': 'flying', 'psychium-z': 'psychic', 'buginium-z': 'bug',
    'rockium-z': 'rock', 'ghostium-z': 'ghost', 'dragonium-z': 'dragon',
    'darkinium-z': 'dark', 'steelium-z': 'steel', 'fairium-z': 'fairy'
}
def trigger_single_entry_ability(entering_combatant, opponent, owner_str, state, combat_log):
    """Executes passive biological traits for a SINGLE specimen entering the biome."""

    # ==========================================
    # 0. AUTOMATIC PRIMAL REVERSION HOOK
    # ==========================================
    # We check the base name before any transformations have occurred
    base_name = entering_combatant['name'].split('-')[0].lower().strip()
    held_item = (entering_combatant.get('held_item') or "").lower().replace(' ', '-')
    
    is_primal_eligible = (base_name == 'groudon' and held_item == 'red-orb') or (base_name == 'kyogre' and held_item == 'blue-orb')
    
    # The 'primal' string check prevents recursive stat-stacking if they swap out and back in!
    if is_primal_eligible and 'primal' not in entering_combatant['name'].lower():
        try:
            target_form = f"{base_name}-primal"
            
            # Access the database to fetch the prehistoric biology
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT pokedex_id, name FROM base_pokemon_species WHERE name = ?", (target_form,))
            primal_data = cursor.fetchone()
            
            if primal_data:
                form_id, form_name = primal_data
                
                cursor.execute("SELECT stat_name, base_value FROM base_pokemon_stats WHERE pokedex_id = ?", (form_id,))
                db_stats = {row[0]: row[1] for row in cursor.fetchall()}
                
                cursor.execute("SELECT type_name FROM base_pokemon_types WHERE pokedex_id = ?", (form_id,))
                new_types = [row[0] for row in cursor.fetchall()]
                
                # Apply the stat transformation
                level = entering_combatant.get('level', 50)
                base_hp = db_stats.get('hp', 50)
                new_max_hp = math.floor((2 * base_hp + 15) * level / 100) + level + 10
                
                hp_diff = new_max_hp - entering_combatant['max_hp']
                entering_combatant['max_hp'] = new_max_hp
                entering_combatant['current_hp'] = max(1, entering_combatant['current_hp'] + hp_diff)
                
                entering_combatant['stats'] = {
                    'attack': math.floor((2 * db_stats.get('attack', 50) + 15) * level / 100) + 5,
                    'defense': math.floor((2 * db_stats.get('defense', 50) + 15) * level / 100) + 5,
                    'sp_atk': math.floor((2 * db_stats.get('special-attack', 50) + 15) * level / 100) + 5,
                    'sp_def': math.floor((2 * db_stats.get('special-defense', 50) + 15) * level / 100) + 5,
                    'speed': math.floor((2 * db_stats.get('speed', 50) + 15) * level / 100) + 5
                }
                
                entering_combatant['pokedex_id'] = form_id
                entering_combatant['name'] = form_name
                entering_combatant['types'] = new_types
                
                # 🚨 INJECT THE PRIMAL ABILITY DIRECTLY INTO THEIR MEMORY!
                if base_name == 'groudon':
                    entering_combatant['ability'] = 'desolate-land'
                elif base_name == 'kyogre':
                    entering_combatant['ability'] = 'primordial-sea'
                    
                combat_log += f"🌋 **{owner_str.strip()} {base_name.capitalize()}** underwent Primal Reversion and restored its true power as **{form_name.replace('-', ' ').title()}**!\n"
            
            conn.close()
        except Exception as e:
            print(f"DEBUG: Failed Primal Reversion: {e}")

    ability = entering_combatant.get('ability', 'none').lower().replace(' ', '-')
    name = entering_combatant['name'].capitalize()
    opp_name = opponent['name'].capitalize()

    # 1. THE INTIMIDATE HOOK 
    if ability == 'intimidate':
        if 'stat_stages' not in opponent:
            opponent['stat_stages'] = {'attack': 0, 'defense': 0, 'sp_atk': 0, 'sp_def': 0, 'speed': 0}
            
        current_atk = opponent['stat_stages']['attack']
        if current_atk > -6:
            opponent['stat_stages']['attack'] = max(-6, current_atk - 1)
            combat_log += f"💢 **{owner_str.strip()} {name}**'s Intimidate cuts {opp_name}'s Attack!\n"

    # ==========================================
    # 2. ATMOSPHERIC SUPPRESSION
    # ==========================================
    if ability in ['air-lock', 'cloud-nine']:
        if state.get('weather', {}).get('type') != 'none':
            state['weather'] = {'type': 'none', 'duration': 0, 'primordial': False}
            combat_log += f"☁️ **{owner_str.strip()} {name}**'s {ability.replace('-', ' ').title()} suppressed all atmospheric weather effects!\n"

    # ==========================================
    # 3. PRIMORDIAL MICROCLIMATES
    # ==========================================
    primordial_weathers = {
        'desolate-land': ('extremely-harsh-sunlight', "☀️ The sunlight turned extremely harsh!"),
        'primordial-sea': ('heavy-rain', "🌧️ A heavy rain began to fall!"),
        'delta-stream': ('strong-winds', "🌪️ Mysterious strong winds are protecting Flying-type specimens!")
    }

    if ability in primordial_weathers:
        w_type, msg = primordial_weathers[ability]
        # Primordial weather lasts infinitely while the specimen is on the field
        state['weather'] = {'type': w_type, 'duration': 999, 'primordial': True}
        combat_log += f"{msg}\n"

    # ==========================================
    # 4. STANDARD CLIMATOLOGY (Data-Driven)
    # ==========================================
    elif ability in BIOLOGICAL_TRAITS.get('weather_setters', {}):
        # 🚨 FIREWALL: Standard weather cannot override a primordial microclimate!
        if not state.get('weather', {}).get('primordial', False):
            w_type, msg = BIOLOGICAL_TRAITS['weather_setters'][ability]

            # Geological Weather Extenders
            held_item = (entering_combatant.get('held_item') or "").lower().replace(' ', '-')
            duration = 5

            if w_type == 'sun' and held_item == 'heat-rock': duration = 8
            elif w_type == 'rain' and held_item == 'damp-rock': duration = 8
            elif w_type == 'sand' and held_item == 'smooth-rock': duration = 8
            elif w_type == 'hail' and held_item == 'icy-rock': duration = 8

            state['weather'] = {'type': w_type, 'duration': duration, 'primordial': False}
            # Append a newline so the log parses cleanly!
            combat_log += msg.format(owner=owner_str.strip(), name=name) + "\n"

    return combat_log

class PvPForcedSwapMenu(discord.ui.View):
    def __init__(self, cog, state, player_id):
        super().__init__(timeout=60)
        self.cog = cog
        self.state = state
        self.player_id = player_id
        self.turn_created = state['turn_number']

        is_p1 = (player_id == state['p1_id'])
        team = state['p1_team'] if is_p1 else state['p2_team']

        for i, poke in enumerate(team):
            if poke['current_hp'] > 0:
                btn = discord.ui.Button(label=f"{poke['name'].capitalize()} (HP: {poke['current_hp']})", style=discord.ButtonStyle.success)
                btn.callback = self.create_swap_callback(i, poke)
                self.add_item(btn)

    def create_swap_callback(self, idx, poke):
        async def swap_callback(interaction: discord.Interaction):
            #Reject stale menus and wrong phases!
            if self.state['turn_number'] != self.turn_created:
                return await interaction.response.send_message("⚠️ This swap menu has expired!", ephemeral=True)
            
            self.state['commits'][self.player_id] = {'type': 'forced_swap', 'data': idx}
            await interaction.response.edit_message(content=f"🔒 Locked in: Deploying **{poke['name'].capitalize()}**!", view=None)
            await self.cog.check_pvp_commits(self.state)
        return swap_callback

class PvPDashboard(discord.ui.View):
    def __init__(self, cog, state):
        super().__init__(timeout=None)
        self.cog = cog
        self.state = state
        self.turn_created = state['turn_number'] # 🛡️ Stamp the menu with the current turn!

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Authentication layer: Only P1 and P2 can interact with this dashboard."""
        user_id = str(interaction.user.id)
        if user_id not in [self.state['p1_id'], self.state['p2_id']]:
            await interaction.response.send_message("⚠️ You are not an authorized researcher in this field duel!", ephemeral=True)
            return False
        
        # Reject clicks if this dashboard belongs to a previous turn!
        if self.state['turn_number'] != self.turn_created:
            await interaction.response.send_message("⚠️ This control panel has expired! Please scroll down to the newest dashboard.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Fight ⚔️", style=discord.ButtonStyle.primary)
    async def fight_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        
        # Prevent players from overwriting their choice
        if self.state['commits'][user_id] is not None:
            return await interaction.response.send_message("🔒 You have already locked in your tactical decision!", ephemeral=True)

        # Retrieve their active specimen
        is_p1 = (user_id == self.state['p1_id'])
        active_idx = self.state['p1_active_index'] if is_p1 else self.state['p2_active_index']
        active_poke = self.state['p1_team' if is_p1 else 'p2_team'][active_idx]

        # Spawn the private terminal
        view = PvPMoveMenu(self.cog, self.state, user_id, active_poke)
        await interaction.response.send_message(f"Commanding {active_poke['name'].capitalize()}...", view=view, ephemeral=True)

    @discord.ui.button(label="Swap 🔄", style=discord.ButtonStyle.secondary)
    async def swap_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        
        if self.state['commits'][user_id] is not None:
            return await interaction.response.send_message("🔒 You have already locked in your tactical decision!", ephemeral=True)

        # Spawn the private terminal
        view = PvPSwapMenu(self.cog, self.state, user_id)
        await interaction.response.send_message("Select a benched specimen to deploy:", view=view, ephemeral=True)
        
class PvPMoveMenu(discord.ui.View):
    def __init__(self, cog, state, player_id, active_poke):
        super().__init__(timeout=60)
        self.cog = cog
        self.state = state
        self.player_id = player_id
        self.active_poke = active_poke
        self.turn_created = state['turn_number'] # 🛡️ Stamp the menu!
        
        self.pending_transformation = None
        self.z_toggled = False
        
        print(f"\n=== DEBUG: Initializing PvPMoveMenu for {player_id} ===")
        self.build_ui()

    def build_ui(self):
        """Clears and redraws the buttons dynamically based on toggle states and held items."""
        try:
            print("DEBUG: build_ui() triggered. Clearing old items...")
            self.clear_items()
            
            is_p1 = (self.player_id == self.state['p1_id'])
            adp_state = self.state['p1_adaptation'] if is_p1 else self.state['p2_adaptation']
            key_items = self.state['p1_key_items'] if is_p1 else self.state['p2_key_items']
            
            held_item = (self.active_poke.get('held_item') or "").lower().replace(' ', '-')
            
            # Safely get the Z-Crystal type
            allowed_z_type = None
            if 'Z_CRYSTAL_TYPES' in globals():
                allowed_z_type = Z_CRYSTAL_TYPES.get(held_item)
            else:
                print("⚠️ WARNING: Z_CRYSTAL_TYPES dictionary is not defined globally!")

            # ==========================================
            # ROW 0: ADAPTATION TOGGLES
            # ==========================================
            print(f"DEBUG: adp_state['used'] = {adp_state['used']}")
            if not adp_state['used']:
                # ---MEGA & G-MAX DATABASE CHECK ---
                base_name = self.active_poke['name'].split('-')[0].lower().strip()
                
                import sqlite3
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("SELECT pokedex_id, name FROM base_pokemon_species WHERE name LIKE ? OR name LIKE ?", 
                               (f"{base_name}-mega%", f"{base_name}-gmax%"))
                available_forms = cursor.fetchall()
                conn.close()
                
                mega_forms = [f for f in available_forms if '-mega' in f[1]]
                gmax_form = next((f for f in available_forms if '-gmax' in f[1]), None)

                # 1. DYNAMAX / GIGANTAMAX
                if key_items.get('dynamax_band'):
                    has_gmax = self.active_poke.get('gmax_factor', False) or self.active_poke.get('gmax_factor', 0) == 1
                    
                    # Ensure they actually have a G-Max form in the database before labeling it Gigantamax
                    btn_label = "Gigantamax" if (has_gmax and gmax_form) else "Dynamax"
                    
                    dyna_style = discord.ButtonStyle.success if self.pending_transformation == 'dynamax' else discord.ButtonStyle.danger
                    dyna_btn = discord.ui.Button(label=btn_label, style=dyna_style, emoji="🔴", row=0)
                    dyna_btn.callback = self.create_transform_callback('dynamax')
                    self.add_item(dyna_btn)
                    
                # 2. MEGA EVOLUTION (Requires Mega Bracelet + Stone OR Rayquaza + Dragon Ascent)
                has_mega_stone = ('ite' in held_item)
                has_dragon_ascent = (base_name == 'rayquaza' and any(m['name'] == 'dragon-ascent' for m in self.active_poke['moves']))
                is_eternal = base_name == 'floette-eternal'
                is_raichu_alola = base_name == 'raichu-alola'

                # Normal Floettes (all flower colors) cannot Mega Evolve!
                if base_name.startswith('floette') and not is_eternal:
                    has_mega_stone = False
                # Alolan raichu can't mega evolve
                if base_name.startswith('raichu') and not is_raichu_alola:
                    has_mega_stone = False

                if mega_forms and (has_mega_stone or has_dragon_ascent or is_eternal) and key_items.get('mega_bracelet'):
                    mega_style = discord.ButtonStyle.success if self.pending_transformation == 'mega' else discord.ButtonStyle.danger
                    mega_btn = discord.ui.Button(label="Mega Evolve", style=mega_style, emoji="🧬", row=0)
                    mega_btn.callback = self.create_transform_callback('mega')
                    self.add_item(mega_btn)
                    
                # 3. Z-MOVES
                if key_items.get('z_ring') and allowed_z_type:
                    z_style = discord.ButtonStyle.success if self.z_toggled else discord.ButtonStyle.danger
                    z_btn = discord.ui.Button(label="Z-Power", style=z_style, emoji="💎", row=0)
                    z_btn.callback = self.z_toggle_callback
                    self.add_item(z_btn)

            # ==========================================
            # ROW 1: ATTACK COMMANDS
            # ==========================================
            
            # Evaluate if we should render Max Moves!
            show_max_moves = (self.pending_transformation == 'dynamax') or (adp_state['active'] and adp_state['type'] == 'dynamax')
            
            # --- CHOICE LOCK SETUP ---
            choice_lock_move = self.active_poke.get('volatile_statuses', {}).get('choice_lock')
            has_choice_item = held_item in ['choice-band', 'choice-specs', 'choice-scarf']
            print(f"DEBUG UI BUILD: Lock Move is '{choice_lock_move}', Has Choice Item: {has_choice_item}") # Tripwire 4
            for move in self.active_poke['moves']:
                m_type = move.get('type', 'normal')
                move_class = move.get('class')
                is_status = move.get('class') == 'status'
                
                # Calculate the lock state at the top of the loop!
                is_disabled = (move['pp'] <= 0)
                if has_choice_item and choice_lock_move and move['name'] != choice_lock_move:
                    is_disabled = True
                
                # ---ASSAULT VEST FIREWALL ---
                if held_item == 'assault-vest' and move_class == 'status':
                    is_disabled = True

                # --- 1. DYNAMAX / GIGANTAMAX MOVES ---
                if show_max_moves:
                    if is_status:
                        override_name = "Max Guard"
                    else:
                        species_raw = self.active_poke['name'].lower()
                        species_clean = species_raw.replace(' (dynamax)', '').replace(' (gigantamax)', '').split('-')[0].strip()
                        gmax_search_key = f"{species_clean}-gmax"
                        
                        has_gmax = self.active_poke.get('gmax_factor', False) or self.active_poke.get('gmax_factor', 0) == 1
                        
                        raw_max_data = None
                        if has_gmax and 'GMAX_MOVES' in globals() and gmax_search_key in GMAX_MOVES:
                            gmax_data = GMAX_MOVES[gmax_search_key]
                            if m_type == gmax_data.get('type'):
                                raw_max_data = gmax_data.get('name')
                        
                        if not raw_max_data:
                            raw_max_data = MAX_MOVES.get(m_type, 'Max Strike') if 'MAX_MOVES' in globals() else 'Max Strike'
                            
                        if isinstance(raw_max_data, dict):
                            override_name = raw_max_data.get('name', 'Max Strike')
                        else:
                            override_name = raw_max_data
                    
                    label_str = f"{override_name} ({move['pp']}/{move['max_pp']})"
                    
                    btn = discord.ui.Button(
                        label=label_str[:80], 
                        style=discord.ButtonStyle.danger, 
                        disabled=is_disabled,
                        row=1
                    )
                    btn.callback = self.create_move_callback(move, override_name=override_name)
                    self.add_item(btn)

                # --- 2. Z-MOVES ---
                elif self.z_toggled:
                    if not is_status and m_type == allowed_z_type:
                        override_name = Z_MOVE_NAMES.get(m_type, 'Breakneck Blitz') if 'Z_MOVE_NAMES' in globals() else 'Breakneck Blitz'
                        label_str = f"{override_name} (Z)"
                        
                        btn = discord.ui.Button(
                            label=label_str[:80], 
                            style=discord.ButtonStyle.primary, 
                            disabled=is_disabled,
                            row=1
                        )
                        btn.callback = self.create_move_callback(move, override_name=override_name, is_z_move=True)
                        self.add_item(btn)
                    else:
                        label_str = f"{move['name'].replace('-', ' ').title()} ({move['pp']}/{move['max_pp']})"
                        # If it's a Z-Move turn and this move doesn't match the crystal, it's always disabled.
                        btn = discord.ui.Button(label=label_str[:80], style=discord.ButtonStyle.secondary, disabled=True, row=1)
                        btn.callback = self.create_move_callback(move)
                        self.add_item(btn)
                        
                # --- 3. STANDARD MOVES ---
                else:
                    label_str = f"{move['name'].replace('-', ' ').title()} ({move['pp']}/{move['max_pp']})"
                    
                    btn = discord.ui.Button(
                        label=label_str[:80], 
                        style=discord.ButtonStyle.primary, 
                        disabled=is_disabled,
                        row=1
                    )
                    btn.callback = self.create_move_callback(move)
                    self.add_item(btn)
                        
            print("DEBUG: UI successfully built!")

        except Exception as e:
            print("\n🚨 CRASH IN BUILD_UI 🚨")
            import traceback
            traceback.print_exc()

    def create_transform_callback(self, transform_type):
        async def transform_callback(interaction: discord.Interaction):
            print(f"\n--- DEBUG: UI Button Clicked -> {transform_type.upper()} ---")
            try:
                if self.pending_transformation == transform_type:
                    self.pending_transformation = None
                    print("DEBUG: Toggled OFF.")
                else:
                    self.pending_transformation = transform_type
                    self.z_toggled = False
                    print("DEBUG: Toggled ON.")
                    
                self.build_ui()
                await interaction.response.edit_message(view=self)
                print("DEBUG: Discord message successfully updated.")
                
            except Exception as e:
                print(f"🚨 CRASH IN TRANSFORM_CALLBACK: {e}")
                import traceback
                traceback.print_exc()
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"Error drawing UI: {e}", ephemeral=True)
        return transform_callback

    async def z_toggle_callback(self, interaction: discord.Interaction):
        print("\n--- DEBUG: UI Button Clicked -> Z-POWER ---")
        try:
            self.z_toggled = not self.z_toggled
            if self.z_toggled:
                self.pending_transformation = None
                print("DEBUG: Z-Power toggled ON.")
            else:
                print("DEBUG: Z-Power toggled OFF.")
                
            self.build_ui()
            await interaction.response.edit_message(view=self)
            print("DEBUG: Discord message successfully updated.")
            
        except Exception as e:
            print(f"🚨 CRASH IN Z_TOGGLE_CALLBACK: {e}")
            import traceback
            traceback.print_exc()
            if not interaction.response.is_done():
                await interaction.response.send_message(f"Error drawing UI: {e}", ephemeral=True)

    def create_move_callback(self, move, override_name=None, is_z_move=False):
        async def move_callback(interaction: discord.Interaction):
            #Reject stale inputs if the engine is in the Faint Phase!
            if self.state['turn_number'] != self.turn_created:
                return await interaction.response.send_message("⚠️ This attack menu has expired! Please request a new one from the active dashboard.", ephemeral=True)
            if self.state.get('phase') == 'faint_swap':
                return await interaction.response.send_message(
                    "⚠️ Invalid Action: Your specimen fainted! Please check your DMs to deploy a replacement.", 
                    ephemeral=True
                )
            
            print(f"\n--- DEBUG: UI Button Clicked -> ATTACK: {move['name']} ---")
            
            try:
                transform = 'zmove' if is_z_move else self.pending_transformation
                
                # Fetch the move name we need to look up in the DB
                search_name = move['name']
                display_name = override_name if override_name else move['name'].replace('-', ' ').title()

                # ==========================================
                # THE 17-VARIABLE PAYLOAD HYDRATION
                # ==========================================
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT name, type, power, accuracy, damage_class, pp, priority,
                        target, ailment, ailment_chance, stat_name, stat_change, stat_chance, 
                        status_type, status_chance, healing, drain
                    FROM base_moves WHERE name = ?
                """, (search_name,))
                p_row = cursor.fetchone()
                conn.close()
                
                if p_row:
                    final_move = {
                        'base_name': search_name,
                        'name': override_name if override_name else p_row[0], 
                        'type': p_row[1], 'power': p_row[2] or 0, 'accuracy': p_row[3] or 100, 
                        'class': p_row[4], 'pp': move['pp'], 'priority': p_row[6] or 0, 'target': p_row[7], 
                        'ailment': p_row[8], 'ailment_chance': p_row[9] or 0, 'stat_name': p_row[10], 
                        'stat_change': p_row[11] or 0, 'stat_chance': p_row[12] or 0,
                        'status_type': p_row[13], 'status_chance': p_row[14] or 0, 
                        'healing': p_row[15] or 0, 'drain': p_row[16] or 0
                    }
                else:
                    print(f"⚠️ WARNING: Move '{search_name}' missing from DB! Using fallback.")
                    final_move = {
                        'base_name': search_name, 
                        'type': 'typeless', 'power': 0, 'accuracy': 100, 'class': 'status',
                        'target': 'defender', 'ailment': 'none', 'ailment_chance': 0,
                        'stat_name': 'none', 'stat_change': 0, 'stat_chance': 0,
                        'status_type': 'none', 'status_chance': 0,
                        'healing': 0, 'drain': 0, 'name': display_name, 'priority': 0, 'pp': move['pp']
                    }

                # ==========================================
                # CHOICE ITEM LOCK INTERCEPTOR
                # ==========================================
                held_item = (self.active_poke.get('held_item') or "").lower().replace(' ', '-')
                print(f"DEBUG LOCK 1: Detected held item: {held_item}") # Tripwire 1
                if held_item in ['choice-band', 'choice-specs', 'choice-scarf']:
                    if 'volatile_statuses' not in self.active_poke:
                        self.active_poke['volatile_statuses'] = {}
                    
                    # If they aren't locked in yet, lock them into the base move they just clicked!
                    if not self.active_poke['volatile_statuses'].get('choice_lock'):
                        print(f"DEBUG LOCK 2: Applying NEW choice lock for: {search_name}") # Tripwire 2
                        self.active_poke['volatile_statuses']['choice_lock'] = search_name
                    else:
                        print(f"DEBUG LOCK 3: Existing lock detected: {self.active_poke['volatile_statuses']['choice_lock']}") # Tripwire 3
                # ==========================================

                # ==========================================

                self.state['commits'][self.player_id] = {
                    'type': 'attack', 
                    'data': final_move,
                    'transform': transform
                }
                
                print(f"DEBUG: Locked payload to server memory -> {display_name}")
                
                await interaction.response.edit_message(content=f"🔒 Locked in: **{display_name}**!", view=None)
                await self.cog.check_pvp_commits(self.state)
                
            except Exception as e:
                print(f"🚨 CRASH IN MOVE_CALLBACK: {e}")
                import traceback
                traceback.print_exc()
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"Error locking in move: {e}", ephemeral=True)
                    
        return move_callback
    
class PvPSwapMenu(discord.ui.View):
    def __init__(self, cog, state, player_id):
        super().__init__(timeout=60)
        self.cog = cog
        self.state = state
        self.player_id = player_id
        self.turn_created = state['turn_number'] # 🛡️ Stamp the menu!

        # Determine which team we are looking at
        is_p1 = (player_id == state['p1_id'])
        team = state['p1_team'] if is_p1 else state['p2_team']
        active_idx = state['p1_active_index'] if is_p1 else state['p2_active_index']

        # Build buttons for the benched roster
        for i, poke in enumerate(team):
            if i == active_idx: continue
            
            btn = discord.ui.Button(
                label=f"{poke['name'].capitalize()} (HP: {poke['current_hp']})",
                style=discord.ButtonStyle.success if poke['current_hp'] > 0 else discord.ButtonStyle.danger,
                disabled=(poke['current_hp'] <= 0)
            )
            btn.callback = self.create_callback(i, poke)
            self.add_item(btn)

    def create_callback(self, idx, poke):
        async def swap_callback(interaction: discord.Interaction):
            # Reject standard swaps during the Faint Phase!
            # Reject stale menus and wrong phases!
            if self.state['turn_number'] != self.turn_created:
                return await interaction.response.send_message("⚠️ This swap menu has expired!", ephemeral=True)
            
            if self.state.get('phase') == 'faint_swap':
                return await interaction.response.send_message(
                    "⚠️ Invalid Action: The field is paused. Please use the Faint Menu in your DMs!", 
                    ephemeral=True
                )
            # 1. Save the swap payload
            self.state['commits'][self.player_id] = {'type': 'swap', 'data': idx}
            
            # 2. Destroy the private terminal
            await interaction.response.edit_message(content=f"🔒 Locked in: Deploying **{poke['name'].capitalize()}**!", view=None)
            
            # 3. Ping the server
            await self.cog.check_pvp_commits(self.state)
        return swap_callback

class ChallengeView(discord.ui.View):
    def __init__(self, cog, challenger: discord.Member, opponent: discord.Member):
        super().__init__(timeout=60) # 60 seconds to accept before the invite expires
        self.cog = cog
        self.challenger = challenger
        self.opponent = opponent

    @discord.ui.button(label="Accept Duel", style=discord.ButtonStyle.success, emoji="⚔️")
    async def accept_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # SECURITY: Only the challenged player can click this!
        if interaction.user.id != self.opponent.id:
            return await interaction.response.send_message("⚠️ This exhibition invitation is not directed at you!", ephemeral=True)
        
        await interaction.response.defer()
        
        # Disable buttons to prevent double-clicking
        for child in self.children:
            child.disabled = True
        await interaction.edit_original_response(content=f"⚔️ **{self.opponent.display_name}** accepted the challenge! Initializing joint-combat arena...", view=self)
        
        # Hand off to the initialization engine
        await self.cog.initialize_pvp_battle(interaction.channel, self.challenger, self.opponent)
        self.stop()

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            return await interaction.response.send_message("⚠️ This exhibition invitation is not directed at you!", ephemeral=True)
        
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content=f"🛡️ **{self.opponent.display_name}** declined the field exhibition.", view=self)
        self.stop()

    async def on_timeout(self):
        # If they ignore it for 60 seconds, gracefully cancel
        for child in self.children:
            child.disabled = True
        
        # We use a try/except here just in case the original message was deleted
        try:
            message = getattr(self, 'message', None)
            if message:
                await message.edit(content=f"⏳ The challenge from **{self.challenger.display_name}** expired.", view=self)
        except Exception:
            pass

class MoveReplacementView(discord.ui.View):
    def __init__(self, cog, ctx, user_id: str, instance_id: str, specimen_name: str, new_move: str, current_moves: list):
        super().__init__(timeout=120)
        self.cog = cog
        self.ctx = ctx
        self.user_id = user_id
        self.instance_id = instance_id
        self.specimen_name = specimen_name
        self.new_move = new_move
        
        # Build the dropdown dynamically based on the 4 moves they currently know
        options = []
        for i, move in enumerate(current_moves):
            # We store the index (1-4) in the value so we know exactly which DB column to update!
            options.append(discord.SelectOption(
                label=move.replace('-', ' ').title(), 
                value=f"move_{i+1}", 
                description=f"Forget this move to learn {new_move.replace('-', ' ').title()}."
            ))
            
        select_menu = discord.ui.Select(
            placeholder="Select a neural pathway to overwrite...", 
            min_values=1, max_values=1, options=options
        )
        select_menu.callback = self.relearn_callback
        self.add_item(select_menu)
        
        # Add a Cancel button so they can back out without spending resources
        cancel_btn = discord.ui.Button(label="Cancel Operation", style=discord.ButtonStyle.secondary, row=1)
        cancel_btn.callback = self.cancel_callback
        self.add_item(cancel_btn)

    async def relearn_callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("⚠️ You are not authorized to alter this specimen.", ephemeral=True)
            
        await interaction.response.defer()
        
        # The value will be 'move_1', 'move_2', 'move_3', or 'move_4'
        target_column = interaction.data['values'][0] 
        
        conn = sqlite3.connect(DB_FILE) # Ensure DB_FILE is accessible here!
        cursor = conn.cursor()
        
        try:
            cursor.execute("BEGIN TRANSACTION")
            
            # 1. DOUBLE-CHECK INVENTORY (In case they spent it while the menu was open)
            cursor.execute("SELECT eco_tokens FROM users WHERE user_id = ?", (self.user_id,))
            funds = cursor.fetchone()[0]
            
            cursor.execute("SELECT quantity FROM user_inventory WHERE user_id = ? AND item_name = 'memory-spore'", (self.user_id,))
            spores = cursor.fetchone()
            spore_qty = spores[0] if spores else 0
            
            if funds < 500 or spore_qty < 1:
                conn.rollback()
                return await interaction.followup.send("❌ **Transaction Failed:** You no longer have the required 500 Eco Tokens and 1 Memory Spore.", ephemeral=True)
                
            # 2. DEDUCT THE RESOURCES
            cursor.execute("UPDATE users SET eco_tokens = eco_tokens - 500 WHERE user_id = ?", (self.user_id,))
            cursor.execute("UPDATE user_inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_name = 'memory-spore'", (self.user_id,))
            
            # 3. OVERWRITE THE GENETIC CODE
            # Using f-strings for the column name is safe here because target_column is strictly generated by our own code ('move_1' to 'move_4')
            cursor.execute(f"UPDATE caught_pokemon SET {target_column} = ? WHERE instance_id = ?", (self.new_move, self.instance_id))
            
            conn.commit()
            
            # 4. UPDATE THE UI
            embed = discord.Embed(
                title="🧠 Neural Rewrite Complete", 
                description=f"The `Memory Spore` successfully catalyzed the dormant genetic traits!\n\n**{self.specimen_name.capitalize()}** forgot the old move and learned **{self.new_move.replace('-', ' ').title()}**.",
                color=discord.Color.green()
            )
            await interaction.edit_original_response(embed=embed, view=None)
            
        except Exception as e:
            conn.rollback()
            print(f"Neural Rewrite Error: {e}")
            await interaction.followup.send("❌ A critical laboratory error occurred.", ephemeral=True)
        finally:
            conn.close()

    async def cancel_callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("⚠️ You cannot interact with this console.", ephemeral=True)
            
        await interaction.response.edit_message(content="🛑 **Operation Aborted:** No resources were consumed and the specimen's genetics remain unaltered.", embed=None, view=None)

class TeachMenu(discord.ui.View):
    def __init__(self, cog, user_id, instance_id, poke_name, new_move, current_moves):
        super().__init__(timeout=60)
        self.cog = cog
        self.user_id = user_id
        self.instance_id = instance_id
        self.poke_name = poke_name
        self.new_move = new_move
        self.current_moves = current_moves
        
        # Dynamically generate a button for each current move
        for i, move_name in enumerate(self.current_moves):
            btn = discord.ui.Button(
                label=move_name.replace('-', ' ').title(), 
                style=discord.ButtonStyle.secondary, 
                custom_id=f"forget_{i+1}_{move_name}"
            )
            btn.callback = self.forget_callback
            self.add_item(btn)
            
        # Add a Cancel Button
        cancel_btn = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.danger, custom_id="cancel_teach")
        cancel_btn.callback = self.cancel_callback
        self.add_item(cancel_btn)

    async def forget_callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("⚠️ You cannot interfere with another researcher's data!", ephemeral=True)
            
        custom_id = interaction.data['custom_id']
        slot_num = custom_id.split('_')[1] # Extracts '1', '2', '3', or '4'
        forgotten_move = custom_id.split('_')[2]

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # 1. Consume the TM
        cursor.execute("UPDATE user_tms SET quantity = quantity - 1 WHERE user_id = ? AND tm_name = ?", (self.user_id, self.new_move))
        
        # 2. Overwrite the specific move slot
        col_name = f"move_{slot_num}"
        cursor.execute(f"UPDATE caught_pokemon SET {col_name} = ? WHERE instance_id = ?", (self.new_move, self.instance_id))
        
        conn.commit()
        conn.close()

        # Disable all buttons
        for child in self.children:
            child.disabled = True

        embed = discord.Embed(
            title="✨ Move Successfully Overwritten!",
            description=f"1, 2, and... Poof!\n\n**{self.poke_name.capitalize()}** forgot `{forgotten_move.replace('-', ' ').title()}` and learned `{self.new_move.replace('-', ' ').title()}`!",
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def cancel_callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("⚠️ Hands off!", ephemeral=True)
            
        for child in self.children:
            child.disabled = True
            
        embed = discord.Embed(
            title="🛑 Overwrite Cancelled",
            description=f"**{self.poke_name.capitalize()}** did not learn `{self.new_move.replace('-', ' ').title()}`.",
            color=discord.Color.red()
        )
        await interaction.response.edit_message(embed=embed, view=self)

class DetailedMovepoolPaginator(discord.ui.View):
    def __init__(self, ctx, poke_info, move_data):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.poke_info = poke_info
        self.move_data = move_data # Now an array of rich dictionaries, not just strings!
        self.current_page = 0
        self.items_per_page = 5 # 5 detailed fields per page creates a perfect visual height
        
        self.max_pages = max(1, math.ceil(len(self.move_data) / self.items_per_page))
        self.update_buttons()

    def update_buttons(self):
        self.children[0].disabled = self.current_page == 0
        self.children[1].disabled = self.current_page >= self.max_pages - 1

    def create_embed(self):
        embed = discord.Embed(
            title=f"📚 Biological Movepool: {self.poke_info['name'].capitalize()}", 
            color=discord.Color.purple()
        )
        embed.description = f"**Level {self.poke_info['level']}** | Tag ID: `{self.poke_info['tag'][:8]}`\nScroll to analyze all physically possible behaviors."
        
        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        chunk = self.move_data[start:end]

        if not chunk:
            embed.add_field(name="Data Missing", value="No behaviors cataloged for this specimen.", inline=False)

        # Build a detailed field for every single move in the chunk
        for move in chunk:
            dmg_icon = "💥" if move['class'] == 'physical' else "☄️" if move['class'] == 'special' else "🛡️"
            pwr_display = move['power'] if move['power'] and move['power'] > 0 else "-"
            acc_display = f"{move['accuracy']}%" if move['accuracy'] else "-"
            
            desc = f"**Type:** {move['type'].capitalize()} | {dmg_icon} **{move['class'].capitalize()}**\n"
            desc += f"**Power:** {pwr_display} | **Accuracy:** {acc_display} | **PP:** {move['pp']}"
            
            embed.add_field(
                name=f"{move['name'].replace('-', ' ').title()} (Unlocks at Lv. {move['lvl']})", 
                value=desc, 
                inline=False
            )

        embed.set_footer(text=f"Page {self.current_page + 1}/{self.max_pages} | Use !learn [Move Name] [Slot 1-4]")
        return embed

    @discord.ui.button(label="◀️ Prev", style=discord.ButtonStyle.primary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("This isn't your data pad!", ephemeral=True)
            
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("This isn't your data pad!", ephemeral=True)
            
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="◀️ Prev", style=discord.ButtonStyle.primary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("This isn't your data pad!", ephemeral=True)
            
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("This isn't your data pad!", ephemeral=True)
            
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

class SwapMenu(discord.ui.View):
    def __init__(self, cog, user_id, ctx, main_battle_view, forced=False):
        super().__init__(timeout=180)
        self.cog = cog
        self.user_id = str(user_id)
        self.ctx = ctx
        self.main_battle_view = main_battle_view 
        self.forced = forced 

        state = self.cog.active_battles[self.user_id]
        
        options = []
        for i, p in enumerate(state['player_team']):
            if p['current_hp'] > 0 and i != state['active_player_index']:
                options.append(discord.SelectOption(
                    label=p['name'].capitalize(),
                    description=f"HP: {p['current_hp']}/{p['max_hp']} | Lv. {p['level']}",
                    value=str(i), 
                    emoji="🟢" if p['current_hp'] > (p['max_hp']/2) else "🟡"
                ))

        select = discord.ui.Select(placeholder="Select a healthy specimen to deploy...", options=options, row=0)
        select.callback = self.select_callback
        self.add_item(select)

        if not self.forced:
            cancel_btn = discord.ui.Button(label="Cancel Swap", style=discord.ButtonStyle.danger, row=1)
            cancel_btn.callback = self.cancel_callback
            self.add_item(cancel_btn)

    async def cancel_callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("⚠️ This is not your field expedition!", ephemeral=True)
            
        await interaction.response.edit_message(view=self.main_battle_view)

    async def select_callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("⚠️ This is not your field expedition!", ephemeral=True)
                    
        await interaction.response.defer()
        print("\n=== DEBUG: SwapMenu select_callback triggered ===")
        
        try:
            selected_index = int(interaction.data['values'][0])
            state = self.cog.active_battles[self.user_id]
            p_active = state['player_team'][state['active_player_index']]

            if state['adaptation'].get('active'):
                if state['adaptation'].get('type') in ['dynamax', 'gmax']:
                    backup = state['adaptation']['backup']
                    hp_percent = max(0, p_active['current_hp']) / p_active['max_hp']
                    
                    p_active['name'] = backup['name']
                    p_active['pokedex_id'] = backup['pokedex_id']
                    p_active['max_hp'] = backup['max_hp']
                    p_active['stats'] = backup['stats']
                    p_active['types'] = backup['types']
                    
                    p_active['current_hp'] = max(0, math.floor(p_active['max_hp'] * hp_percent))
                    
                    state['adaptation']['active'] = False
                    state['adaptation']['turns'] = 0
                    print(f"DEBUG: Stripped adaptation from {p_active['name']}.")
                
            state['active_player_index'] = selected_index
            new_active = state['player_team'][selected_index]
            n_active = state['npc_team'][state['active_npc_index']]

            p_active['volatile_statuses'] = {}

            if self.forced:
                combat_log = f"You sent out **{new_active['name'].capitalize()}**!\n"
                
                try:
                    combat_log = trigger_single_entry_ability(new_active, n_active, "Your", state, combat_log)
                    hazard_log = apply_entry_hazards(new_active, state['player_hazards'], TYPE_CHART, "Your")
                    if hazard_log: combat_log += hazard_log

                    #Did the hazards trigger a berry?
                    berry_log = check_consumables(new_active, "Your")
                    if berry_log: combat_log += berry_log
                except Exception as e:
                    print(f"DEBUG: Error applying forced swap hazards/abilities: {e}")
                
                # ==========================================
                # GENERATE THE NEW IMAGE!
                # ==========================================
                print("DEBUG: Generating new battlefield image for FORCED swap...")
                battle_file = await BattleDashboard.generate_battle_scene(
                    self,
                    new_active['pokedex_id'], n_active['pokedex_id'], 
                    new_active['current_hp'], new_active['max_hp'], 
                    n_active['current_hp'], n_active['max_hp'],
                    player_shiny=new_active.get('is_shiny', False),
                    npc_shiny=n_active.get('is_shiny', False),
                    weather=state.get('weather', {'type': 'none'})['type'],
                    p_status=new_active.get('status_condition'),
                    n_status=n_active.get('status_condition'),
                    p_hazards=state.get('player_hazards'),
                    n_hazards=state.get('npc_hazards')
                )
                # Attach the newly generated image to the state so render_dashboard can use it!
                self.main_battle_view.current_battle_file = battle_file
                print("DEBUG: Handoff to main_battle_view.render_dashboard (Forced Swap)")
                return await self.main_battle_view.render_dashboard(interaction, combat_log)
                
            else:
                combat_log = f"**Turn {state['turn_number']}**\n\n"
                combat_log += f"You recalled your specimen and sent out **{new_active['name'].capitalize()}**!\n"

                # ==========================================
                # GENERATE THE NEW IMAGE!
                # ==========================================
                print("DEBUG: Generating new battlefield image for VOLUNTARY swap...")
                battle_file = await BattleDashboard.generate_battle_scene(
                    self,
                    new_active['pokedex_id'], n_active['pokedex_id'], 
                    new_active['current_hp'], new_active['max_hp'], 
                    n_active['current_hp'], n_active['max_hp'],
                    player_shiny=new_active.get('is_shiny', False),
                    npc_shiny=n_active.get('is_shiny', False),
                    weather=state.get('weather', {'type': 'none'})['type'],
                    p_status=new_active.get('status_condition'),
                    n_status=n_active.get('status_condition'),
                    p_hazards=state.get('player_hazards'),
                    n_hazards=state.get('npc_hazards')
                )
                # Because process_turn_end generates its OWN image later in Phase 5, we actually 
                # don't need to assign this to self.main_battle_view.current_battle_file right here.
                # However, generating it prevents the pointer corruption bug before the handoff!
                #    
                try:
                    combat_log = trigger_single_entry_ability(new_active, n_active, "Your", state, combat_log)
                    hazard_log = apply_entry_hazards(new_active, state['player_hazards'], TYPE_CHART, "Your")
                    if hazard_log: combat_log += hazard_log
                    # Did the hazards trigger a berry?
                    berry_log = check_consumables(new_active, "Your")
                    if berry_log: combat_log += berry_log
                except Exception as e:
                    print(f"DEBUG: Error applying voluntary swap hazards/abilities: {e}")

                if new_active['current_hp'] > 0:
                    available_moves = [m for m in n_active['moves'] if m['pp'] > 0]
                    if available_moves:
                        chosen_move = random.choice(available_moves)
                        chosen_move['pp'] -= 1 
                        

                        conn = sqlite3.connect(DB_FILE)
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT type, power, accuracy, damage_class, target, ailment, ailment_chance, 
                                stat_name, stat_change, stat_chance, healing, drain, name, priority
                            FROM base_moves WHERE name = ?
                        """, (chosen_move['name'],))
                        n_row = cursor.fetchone()
                        conn.close()
                        
                        if n_row:
                            # Perfectly mapped all 14 variables
                            n_move_stats = {
                                'type': n_row[0], 'power': n_row[1] or 0, 'accuracy': n_row[2] or 100, 'class': n_row[3],
                                'target': n_row[4], 'ailment': n_row[5], 'ailment_chance': n_row[6] or 0,
                                'stat_name': n_row[7], 'stat_change': n_row[8] or 0, 'stat_chance': n_row[9] or 0,
                                'healing': n_row[10] or 0, 'drain': n_row[11] or 0,
                                'name': n_row[12], 'priority': n_row[13] or 0
                            }
                            
                            combat_log += f"🔴 The rival's **{n_active['name'].capitalize()}** struck the incoming Pokémon with `{chosen_move['name'].replace('-', ' ').title()}`!\n"
                            
                            if random.randint(1, 100) > n_move_stats['accuracy']:
                                combat_log += "The attack missed!\n"
                            else:
                                dmg, msg, inf_status, stat_chgs, heal_amt = calculate_damage(
                                    n_active, new_active, n_move_stats, 
                                    weather=state.get('weather', {'type': 'none'})['type'], 
                                    target_hazards=state['player_hazards'], # The NPC attacks the Player's habitat
                                    user_hazards=state['npc_hazards']       # The NPC's own habitat
                                )
                                new_active['current_hp'] = max(0, new_active['current_hp'] - dmg)
                                if msg: combat_log += f"*{msg}*\n"
                                # Tell the UI to actually announce the damage!
                                if dmg > 0: combat_log += f"↳ Dealt **{dmg}** damage.\n"
                else:
                    combat_log += f"💀 Your **{new_active['name'].capitalize()}** couldn't survive the treacherous habitat!\n"

                self.main_battle_view.refresh_buttons()
                print("DEBUG: Handoff to main_battle_view.process_turn_end (Voluntary Swap)")
                await self.main_battle_view.process_turn_end(interaction, combat_log)

        except Exception as e:
            print("\n🚨 CRITICAL CRASH IN SWAP MENU 🚨")
            import traceback
            traceback.print_exc()
            await interaction.followup.send("A critical error occurred during the swap sequence. Check the terminal!", ephemeral=True)

class ItemSelect(discord.ui.View):
    def __init__(self, cog, user_id, ctx, main_battle_view, items):
        super().__init__(timeout=120)
        self.cog = cog
        self.user_id = str(user_id)
        self.ctx = ctx
        self.main_battle_view = main_battle_view # We need this to return to the battle!
        
        # Build the dropdown dynamically based on what they actually own
        options = []
        for item_name, qty in items:
            item_data = {
                'potion': {'desc': 'Restores 20 HP.', 'emoji': '💊'},
                'super-potion': {'desc': 'Restores 50 HP.', 'emoji': '🧪'},
                'hyper-potion': {'desc': 'Restores 200 HP.', 'emoji': '🧴'},
                'max-potion': {'desc': 'Restores all HP.', 'emoji': '💖'},
                'full-restore': {'desc': 'Restores all HP and cures status.', 'emoji': '🌟'},
                'revive': {'desc': 'Revives a fainted specimen to 50% HP.', 'emoji': '👼'},
                'full-heal': {'desc': 'Cures all status conditions.', 'emoji': '🌿'}
            }
            
            data = item_data.get(item_name, {'desc': 'A medical supply.', 'emoji': '📦'})
            options.append(discord.SelectOption(
                label=f"{item_name.replace('-', ' ').title()} (x{qty})", 
                value=item_name, 
                description=data['desc'], 
                emoji=data['emoji']
            ))

        select_menu = discord.ui.Select(placeholder="Select a medical supply to deploy...", min_values=1, max_values=1, options=options)
        select_menu.callback = self.use_item_callback
        self.add_item(select_menu)
        
        # Add a Cancel button to return to the attack menu
        cancel_btn = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.secondary, row=1)
        cancel_btn.callback = self.cancel_callback
        self.add_item(cancel_btn)

    async def use_item_callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("⚠️ This is not your field expedition!", ephemeral=True)
            
        await interaction.response.defer()
        
        selected_item = interaction.data['values'][0]
        state = self.cog.active_battles[self.user_id]
        p_active = state['player_team'][state['active_player_index']]
        
        # --- 1. BIOLOGICAL VALIDATION ---
        # Prevent wasting items if they aren't needed!
        if selected_item in ['potion', 'super-potion', 'hyper-potion', 'max-potion'] and p_active['current_hp'] == p_active['max_hp']:
            return await interaction.followup.send("That specimen is already at maximum health!", ephemeral=True)
            
        if selected_item == 'full-heal' and p_active.get('status_condition') is None and 'confusion' not in p_active.get('volatile_statuses', {}):
            return await interaction.followup.send("That specimen is not suffering from any status conditions!", ephemeral=True)
            
        if selected_item == 'revive' and p_active['current_hp'] > 0:
             return await interaction.followup.send("You can only use a Revive on a fainted specimen!", ephemeral=True)
             
        if selected_item != 'revive' and p_active['current_hp'] <= 0:
            return await interaction.followup.send("You cannot use that item on a fainted specimen! Use a Revive.", ephemeral=True)

        # --- 2. CONSUME THE ITEM ---
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("UPDATE user_inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_name = ?", (self.user_id, selected_item))
        conn.commit()
        conn.close()

        # --- 3. APPLY THE MEDICAL EFFECT ---
        combat_log = f"**Turn {state['turn_number']}** begins!\n\n"
        
        if selected_item == 'potion':
            heal_amount = 20
            p_active['current_hp'] = min(p_active['max_hp'], p_active['current_hp'] + heal_amount)
            combat_log += f"💊 You sprayed a Potion! **{p_active['name'].capitalize()}** recovered HP.\n"
            
        elif selected_item == 'super-potion':
            heal_amount = 50
            p_active['current_hp'] = min(p_active['max_hp'], p_active['current_hp'] + heal_amount)
            combat_log += f"🧪 You deployed a Super Potion! **{p_active['name'].capitalize()}** recovered HP.\n"
            
        elif selected_item == 'hyper-potion':
            heal_amount = 200
            p_active['current_hp'] = min(p_active['max_hp'], p_active['current_hp'] + heal_amount)
            combat_log += f"🧴 You deployed a Hyper Potion! **{p_active['name'].capitalize()}** recovered HP.\n"
            
        elif selected_item == 'max-potion':
            p_active['current_hp'] = p_active['max_hp']
            combat_log += f"💖 You deployed a Max Potion! **{p_active['name'].capitalize()}**'s HP was fully restored.\n"
            
        elif selected_item == 'full-heal':
            p_active['status_condition'] = None
            if 'confusion' in p_active.get('volatile_statuses', {}):
                del p_active['volatile_statuses']['confusion']
            combat_log += f"🌿 You used a Full Heal! **{p_active['name'].capitalize()}** was cured of all ailments.\n"
            
        elif selected_item == 'full-restore':
            p_active['current_hp'] = p_active['max_hp']
            p_active['status_condition'] = None
            if 'confusion' in p_active.get('volatile_statuses', {}):
                del p_active['volatile_statuses']['confusion']
            combat_log += f"🌟 You used a Full Restore! **{p_active['name'].capitalize()}** is fully healed and cured.\n"
            
        elif selected_item == 'revive':
            p_active['current_hp'] = max(1, math.floor(p_active['max_hp'] * 0.5))
            combat_log += f"👼 You used a Revive! **{p_active['name'].capitalize()}** was resuscitated.\n"

        # --- 4. PASS THE TURN TO THE NPC ---
        await self.main_battle_view.execute_npc_retaliation(interaction, combat_log)

    async def cancel_callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("⚠️ This is not your field expedition!", ephemeral=True)
        # Redraw the main battle dashboard
        await interaction.response.edit_message(view=self.main_battle_view)

class BattleDashboard(discord.ui.View):
    def __init__(self, cog, user_id, ctx):
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = str(user_id)
        self.ctx = ctx
        self.refresh_buttons()

    async def render_dashboard(self, interaction, combat_log):
        """Helper function to redraw the UI after a Forced Swap without advancing the turn."""
        state = self.cog.active_battles[self.user_id]
        p_active = state['player_team'][state['active_player_index']]
        n_active = state['npc_team'][state['active_npc_index']]
        
        embed = discord.Embed(title=f"⚔️ Ecological Field Duel", color=discord.Color.blue())
        embed.description = combat_log
        
        p_roster = "".join(["🔴" if p['current_hp'] > 0 else "⚫" for p in state['player_team']])
        n_roster = "".join(["🔴" if p['current_hp'] > 0 else "⚫" for p in state['npc_team']])
        p_status_icon = f" [{p_active['status_condition']['name'].upper()}]" if p_active.get('status_condition') else ""
        n_status_icon = f" [{n_active['status_condition']['name'].upper()}]" if n_active.get('status_condition') else ""
        
        embed.add_field(name=f"🟢 Your {p_active['name'].capitalize()}{p_status_icon}", value=f"Team: {p_roster}", inline=True)
        embed.add_field(name=f"🔴 Rival {n_active['name'].capitalize()}{n_status_icon}", value=f"Team: {n_roster}", inline=True)
        
        # ==========================================
        # FETCH AND PASS HUD OVERLAYS TO VISUAL ENGINE
        # ==========================================
        current_weather = state.get('weather', {'type': 'none'})['type']
        
        battle_file = await self.generate_battle_scene(
            p_active['pokedex_id'], n_active['pokedex_id'], 
            p_active['current_hp'], p_active['max_hp'], 
            n_active['current_hp'], n_active['max_hp'],
            player_shiny=p_active.get('is_shiny', False), 
            npc_shiny=n_active.get('is_shiny', False),
            
            # --- HUD OVERLAYS ---
            weather=current_weather,
            p_status=p_active.get('status_condition'),
            n_status=n_active.get('status_condition'),
            p_hazards=state.get('player_hazards'),
            n_hazards=state.get('npc_hazards')
        )
        # ==========================================
        self.refresh_buttons()
        # Dynamically grab the new randomized filename!
        if battle_file:
                embed.set_image(url=f"attachment://{battle_file.filename}")
                await interaction.edit_original_response(embed=embed, view=self, attachments=[battle_file])
        else:
            await interaction.edit_original_response(embed=embed, view=self, attachments=[])

    async def check_for_evolution(self, cursor, conn, user_id, specimen, combat_log):
            """Checks if a specimen has hit its genetic threshold for level-based evolution."""
            current_pokedex_id = specimen['pokedex_id']
            current_level = specimen['level']
            instance_id = specimen['instance_id']
            current_name = specimen['name']

            # 1. Check the Metamorphosis Rulebook for level-based triggers
            cursor.execute("""
                SELECT er.evolved_species_id, s.name 
                FROM evolution_rules er
                JOIN base_pokemon_species s ON er.evolved_species_id = s.pokedex_id
                WHERE er.base_species_id = ? 
                AND er.trigger_name = 'level-up' 
                AND er.min_level <= ?
            """, (current_pokedex_id, current_level))
            
            evo_data = cursor.fetchone()
            
            # 2. If an evolution is found, mutate the database and return a success message!
            if evo_data:
                new_pokedex_id, evolved_into_name = evo_data
                
                # Update the specific Pokémon's genetics
                cursor.execute("UPDATE caught_pokemon SET pokedex_id = ? WHERE instance_id = ?", (new_pokedex_id, instance_id))
                
            
                specimen['pokedex_id'] = new_pokedex_id
                specimen['name'] = evolved_into_name
                
                # Store the base evolution message
                evo_msg = f"🌟 **{current_name.capitalize()}** reached Level {current_level} and evolved into **{evolved_into_name.capitalize()}**!\n"
                
                # ==========================================
                # DIRECTIVE TRACKER: KINETIC MATURATION (EVOLUTION)
                # ==========================================
                # We track either a specific species mutation or an 'any' mutation
                cursor.execute("""
                    UPDATE field_directives
                    SET current_progress = current_progress + 1
                    WHERE user_id = ? AND objective_type = 'trigger_mutation' 
                    AND (target_variable = 'any' OR target_variable = ?) AND is_completed = 0
                """, (user_id, current_name.lower()))

                cursor.execute("""
                    SELECT required_amount, current_progress 
                    FROM field_directives
                    WHERE user_id = ? AND objective_type = 'trigger_mutation' 
                    AND (target_variable = 'any' OR target_variable = ?) AND is_completed = 0
                """, (user_id, current_name.lower()))
                
                mut_row = cursor.fetchone()
                
                # If the tracker just hit its target, append the alert!
                if mut_row and mut_row[1] == mut_row[0]:
                    evo_msg += "📡 **Directive Complete:** Kinetic Maturation Study concluded! Run `!claim` to receive your funding.\n"
                # ==========================================
                
                return evo_msg
                
            return "" # No evolution occurred
    
    async def handle_transformation(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("⚠️ This is not your field expedition!", ephemeral=True)
            
        await interaction.response.defer()
        print("\n=== DEBUG: handle_transformation triggered ===")
        
        try:
            # 1. Extract the payload
            print(f"DEBUG: custom_id payload -> {interaction.data['custom_id']}")
            parts = interaction.data['custom_id'].split('_')
            form_id = int(parts[1])
            form_name = parts[2]
            print(f"DEBUG: Parsed form_id={form_id}, form_name='{form_name}'")
            
            state = self.cog.active_battles[self.user_id]
            
            # ==========================================
            # FAST-PATH Z-MOVE TOGGLE (MUST BE AT THE TOP!)
            # ==========================================
            if form_name == 'zmove':
                print("DEBUG: Toggling Z-Power state...")
                
                # --- SAFETY CHECK: Initialize adaptation dict if missing ---
                if 'adaptation' not in state:
                    state['adaptation'] = {'used': False, 'active': False, 'type': 'none', 'turns': 0, 'backup': {}}
                    
                if 'z_toggled' not in state['adaptation']:
                    state['adaptation']['z_toggled'] = False
                    
                # Flip the switch! (True becomes False, False becomes True)
                state['adaptation']['z_toggled'] = not state['adaptation']['z_toggled']
                
                # Instantly redraw the UI and exit the function. No turn is consumed!
                self.refresh_buttons()
                return await interaction.edit_original_response(view=self)
            # ==========================================

            p_active = state['player_team'][state['active_player_index']]
            n_active = state['npc_team'][state['active_npc_index']]
            level = p_active['level']
            old_name = p_active['name']
            
            print(f"DEBUG: Current active specimen -> {old_name} (Level {level})")

            # --- SAFETY CHECK: Catch old battle instances! ---
            if 'adaptation' not in state:
                print("CRITICAL DEBUG: 'adaptation' key is missing from state! Initializing fallback...")
                state['adaptation'] = {'used': False, 'active': False, 'type': 'none', 'turns': 0, 'backup': {}}

            # 1. CREATE THE BIOLOGICAL BACKUP
            print("DEBUG: Creating biological backup...")
            state['adaptation']['backup'] = {
                'name': p_active['name'],
                'pokedex_id': p_active['pokedex_id'],
                'max_hp': p_active['max_hp'],
                'stats': p_active['stats'].copy(),
                'types': list(p_active.get('types', []))
            }
            
            # 2. APPLY THE ADAPTATION (Dynamax vs Mega/Gmax)
            if form_name == 'dynamax':
                print("DEBUG: Applying generic Dynamax logic...")
                hp_boost = math.floor(p_active['max_hp'] * 0.5)
                p_active['max_hp'] += hp_boost
                p_active['current_hp'] += hp_boost
                p_active['name'] = f"{old_name} (Dynamax)"
                
                state['adaptation'].update({'used': True, 'active': True, 'type': 'dynamax', 'turns': 3})
                log_msg = f"🔴 **{old_name.capitalize()}** absorbed Galar particles and Dynamaxed!"
                
            else:
                print("DEBUG: Applying Mega/G-Max logic. Connecting to DB...")
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("SELECT stat_name, base_value FROM base_pokemon_stats WHERE pokedex_id = ?", (form_id,))
                raw_stats = cursor.fetchall()
                
                cursor.execute("SELECT type_name FROM base_pokemon_types WHERE pokedex_id = ?", (form_id,))
                new_types = [row[0] for row in cursor.fetchall()]
                
                #  Fetch the mutated biological ability!
                try:
                    # Query the species table directly to extract the genetic trait!
                    cursor.execute("SELECT standard_abilities FROM base_pokemon_species WHERE pokedex_id = ?", (form_id,))
                    ab_data = cursor.fetchone()
                    
                    # Ensure we actually grabbed a valid string before mutating the state
                    if ab_data and ab_data[0]:
                        # Slice the string at the comma, grab the first ability, and sanitize it!
                        raw_ability = ab_data[0].split(',')[0].strip()
                        p_active['ability'] = raw_ability.lower().replace(' ', '-')
                except Exception as e:
                    print(f"DEBUG: Could not fetch Mega Ability: {e}")
                    
                conn.close()
                
                if not raw_stats:
                    print(f"CRITICAL DEBUG: No stats found in database for ID {form_id}!")
                    return await interaction.followup.send("⚠️ Genetic data for this form is missing from the database!", ephemeral=True)
                    
                db_stats = {row[0]: row[1] for row in raw_stats}
                
                base_hp = db_stats.get('hp', 50)
                base_atk = db_stats.get('attack', 50)
                base_def = db_stats.get('defense', 50)
                base_spa = db_stats.get('special-attack', 50) 
                base_spd = db_stats.get('special-defense', 50)
                base_spe = db_stats.get('speed', 50)
                
                new_max_hp = math.floor((2 * base_hp + 15) * level / 100) + level + 10
                
                if '-gmax' in form_name:
                    new_max_hp = math.floor(new_max_hp * 1.5)
                    
                hp_diff = new_max_hp - p_active['max_hp']
                p_active['max_hp'] = new_max_hp
                p_active['current_hp'] = max(1, p_active['current_hp'] + hp_diff)
                
                p_active['stats'] = {
                    'attack': math.floor((2 * base_atk + 15) * level / 100) + 5,
                    'defense': math.floor((2 * base_def + 15) * level / 100) + 5,
                    'sp_atk': math.floor((2 * base_spa + 15) * level / 100) + 5,
                    'sp_def': math.floor((2 * base_spd + 15) * level / 100) + 5,
                    'speed': math.floor((2 * base_spe + 15) * level / 100) + 5
                }
                
                p_active['pokedex_id'] = form_id
                p_active['name'] = form_name
                p_active['types'] = new_types
                
                is_gmax = '-gmax' in form_name
                state['adaptation'].update({
                    'used': True, 
                    'active': True, 
                    'type': 'gmax' if is_gmax else 'mega', 
                    'turns': 3 if is_gmax else -1
                })
                
                transform_type = "Gigantamaxed" if is_gmax else "Mega Evolved"
                log_msg = f"✨ **{old_name.capitalize()}** achieved Hyper-Adaptation and {transform_type} into **{form_name.replace('-', ' ').title()}**!\n"
                
                # Trigger the biological entry hook so Snow Warning/Drought activates instantly!
                try:
                    log_msg = trigger_single_entry_ability(p_active, n_active, "Your", state, log_msg)
                except Exception as e:
                    print(f"DEBUG: Failed to trigger mega ability hook: {e}")

            # 3. RE-RENDER THE BATTLEFIELD
            print("DEBUG: Preparing UI and fetching artwork...")
            combat_log = f"**Turn {state['turn_number']}**\n\n{log_msg}\n\nWhat will you do next?"
            
            embed = discord.Embed(title=f"⚔️ Ecological Field Duel", color=discord.Color.purple())
            embed.description = combat_log
            
            p_roster = "".join(["🔴" if p['current_hp'] > 0 else "⚫" for p in state['player_team']])
            n_roster = "".join(["🔴" if p['current_hp'] > 0 else "⚫" for p in state['npc_team']])
            
            p_status_icon = f" [{p_active['status_condition']['name'].upper()}]" if p_active.get('status_condition') else ""
            n_status_icon = f" [{n_active['status_condition']['name'].upper()}]" if n_active.get('status_condition') else ""
            
            embed.add_field(name=f"🟢 Your {p_active['name'].capitalize()}{p_status_icon}", value=f"Team: {p_roster}\n*See visual biometrics below*", inline=True)
            embed.add_field(name=f"🔴 Rival {n_active['name'].capitalize()}{n_status_icon}", value=f"Team: {n_roster}\n*See visual biometrics below*", inline=True)
            
            # ==========================================
            # FETCH AND PASS HUD OVERLAYS TO VISUAL ENGINE
            # ==========================================
            current_weather = state.get('weather', {'type': 'none'})['type']
            
            battle_file = await self.generate_battle_scene(
                p_active['pokedex_id'], n_active['pokedex_id'], 
                p_active['current_hp'], p_active['max_hp'], 
                n_active['current_hp'], n_active['max_hp'],
                player_shiny=p_active.get('is_shiny', False),
                npc_shiny=n_active.get('is_shiny', False),
                
                # --- HUD OVERLAYS ---
                weather=current_weather,
                p_status=p_active.get('status_condition'),
                n_status=n_active.get('status_condition'),
                p_hazards=state.get('player_hazards'),
                n_hazards=state.get('npc_hazards')
            )
            
            # Dynamically grab the new randomized filename!
            if battle_file:
                embed.set_image(url=f"attachment://{battle_file.filename}")
            self.refresh_buttons() 
            
            await interaction.edit_original_response(embed=embed, view=self, attachments=[battle_file])
            print("=== DEBUG: handle_transformation COMPLETE ===")

        except Exception as e:
            print("\n🚨 CRITICAL CRASH IN HANDLE_TRANSFORMATION 🚨")
            traceback.print_exc()
            await interaction.followup.send("A critical engine failure occurred during Hyper-Adaptation.", ephemeral=True)


    def refresh_buttons(self):
        """Dynamically builds the UI buttons so they can be easily redrawn after a faint."""
        self.clear_items()
        state = self.cog.active_battles[self.user_id]
        p_active = state['player_team'][state['active_player_index']]

        # Check if the specimen has ANY energy left across all moves
        total_pp = sum(m['pp'] for m in p_active['moves'])

        # Properly format the string with hyphens!
        held_item = p_active.get('held_item', 'none').lower().replace(' ', '-')
        z_crystal_type = Z_CRYSTAL_TYPES.get(held_item)
        z_primed = state['adaptation'].get('z_toggled', False)

        # Set up the Choice Lock variables
        choice_lock_move = p_active.get('volatile_statuses', {}).get('choice_lock')
        has_choice_item = held_item in ['choice-band', 'choice-specs', 'choice-scarf']

        
        # ==========================================
        # 1. Draw Combat Behaviors (Row 0)
        # ==========================================
        # Check if the specimen is currently expanded!
        is_maxed = state['adaptation'].get('active') and state['adaptation'].get('type') in ['dynamax', 'gmax']


        if total_pp <= 0:
            # The Specimen is exhausted! Spawn the Struggle Button.
            struggle_btn = discord.ui.Button(
                label="Struggle", 
                style=discord.ButtonStyle.danger, 
                custom_id="move_struggle_struggle" 
            )
            struggle_btn.callback = self.handle_move
            self.add_item(struggle_btn)
        else:
            for i, move_dict in enumerate(p_active['moves']):
                move_name = move_dict['name']
                curr_pp = move_dict['pp']
                max_pp = move_dict['max_pp']


                # --- Self-Healing State Dictionary ---
                move_element = move_dict.get('type')
                move_class = move_dict.get('class')

                # Calculate the lock!
                is_disabled = (curr_pp <= 0)
                if has_choice_item and choice_lock_move and move_name != choice_lock_move:
                    is_disabled = True

                # --- ASSAULT VEST FIREWALL ---
                if held_item == 'assault-vest' and move_class == 'status':
                    is_disabled = True

                
                # If EITHER the type or class is missing from an older save state, fetch them!
                if not move_element or not move_class:
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    cursor.execute("SELECT type, damage_class FROM base_moves WHERE name = ?", (move_name,))
                    db_res = cursor.fetchone()
                    conn.close()
                    
                    move_element = db_res[0] if db_res else 'normal'
                    move_class = db_res[1] if db_res else 'physical'
                    
                    # Cache both into the dictionary!
                    move_dict['type'] = move_element
                    move_dict['class'] = move_class
                # ----------------------------------------------
                
                if is_maxed:
                    # 1. Check if it's a Status Move first!
                    if move_class == 'status':
                        btn_label = "🛡️ Max Guard"
                    else:
                        # 2. Check for G-Max Signature Override
                        current_form = p_active['name'].lower()
                        gmax_data = GMAX_MOVES.get(current_form)
                        
                        if gmax_data and move_element == gmax_data['type']:
                            btn_label = f"🔥 {gmax_data['name']}"
                        else:
                            # 3. Fallback to standard Max Move
                            max_data = MAX_MOVES.get(move_element, {'name': 'Max Strike'})
                            btn_label = f"🔴 {max_data['name']}"
                    
                    btn_style = discord.ButtonStyle.danger
                    custom_id = f"move_{i}_{move_name}_max"
                    disabled_flag = is_disabled # 🚨 Mapped!

                elif z_primed:
                    # Enforce the biological restriction!
                    if move_element == z_crystal_type:
                        btn_label = f"🌟 Z-{move_name.replace('-', ' ').title()}"
                        btn_style = discord.ButtonStyle.danger
                        custom_id = f"move_{i}_{move_name}_z"
                        disabled = False
                    else:
                        # Lock out incompatible elements so they can't be clicked!
                        btn_label = f"🚫 Incompatible ({move_element.title()})"
                        btn_style = discord.ButtonStyle.secondary
                        custom_id = f"locked_{i}"
                        disabled_flag = is_disabled # 🚨 Mapped!
                else:
                    # Standard UI
                    btn_label = f"{move_name.replace('-', ' ').title()} ({curr_pp}/{max_pp})"
                    btn_style = discord.ButtonStyle.primary if curr_pp > 0 else discord.ButtonStyle.secondary
                    custom_id = f"move_{i}_{move_name}"
                    disabled_flag = is_disabled # 🚨 Mapped!
                    
                btn = discord.ui.Button(label=btn_label, style=btn_style, custom_id=custom_id, row=0, disabled=disabled_flag)
                
                # Only wire the callback if it's an actual, clickable attack
                if not disabled_flag and not custom_id.startswith('locked'):
                    btn.callback = self.handle_move
                    
                self.add_item(btn)
            
        # 2. Draw Medical Supplies (Row 1)
        bag_btn = discord.ui.Button(label="🎒 Open Bag", style=discord.ButtonStyle.success, custom_id="action_bag", row=1)
        bag_btn.callback = self.open_bag
        self.add_item(bag_btn)

        # --- The Swap Button ---
        # We disable it if there are no other healthy specimens on the team!
        healthy_bench = [p for i, p in enumerate(state['player_team']) if p['current_hp'] > 0 and i != state['active_player_index']]
        
        swap_btn = discord.ui.Button(label="🔄 Swap Specimen", style=discord.ButtonStyle.secondary, custom_id="action_swap", row=1)
        swap_btn.disabled = len(healthy_bench) == 0
        swap_btn.callback = self.handle_swap
        self.add_item(swap_btn)

        # ==========================================
        # 3. THE HYPER-ADAPTATION SCANNER (Row 2)
        # ==========================================
        if not state['adaptation']['used']:
            base_name = p_active['name'].split('-')[0]
            held_item = p_active.get('held_item', 'none').lower()
            gmax_factor = p_active.get('gmax_factor', False)
            
            # Safely grab the key items from memory (defaults to False if missing)
            key_items = state.get('key_items', {})

            # We will use this flag to check if we need to spawn the generic Dynamax button
            gimmick_found = False

            # A. Z-MOVE CHECK (Requires Z-Ring)
            if held_item.endswith('-z') and key_items.get('z_ring'):
                if state['adaptation'].get('z_toggled', False):
                    btn = discord.ui.Button(label="🔄 Cancel Z-Power", style=discord.ButtonStyle.secondary, custom_id="transform_0_zmove", row=2)
                else:
                    btn = discord.ui.Button(label="🌟 Unleash Z-Move", style=discord.ButtonStyle.primary, custom_id="transform_0_zmove", row=2)
                btn.callback = self.handle_transformation
                self.add_item(btn)
                gimmick_found = True

            # B. MEGA & G-MAX DATABASE CHECK
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT pokedex_id, name FROM base_pokemon_species WHERE name LIKE ? OR name LIKE ?", 
                           (f"{base_name}-mega%", f"{base_name}-gmax%"))
            available_forms = cursor.fetchall()
            conn.close()
            
            mega_forms = [f for f in available_forms if '-mega' in f[1]]
            gmax_form = next((f for f in available_forms if '-gmax' in f[1]), None)

            # 1. MEGA EVOLUTION (Requires Mega Bracelet + Stone OR Rayquaza + Dragon Ascent)
            has_mega_stone = ('ite' in held_item)
            has_dragon_ascent = (base_name == 'rayquaza' and any(m['name'] == 'dragon-ascent' for m in p_active['moves']))
            is_eternal = base_name == 'floette-eternal'
            is_raichu_alola = base_name == 'raichu-alola'

            # 🚨 FIREWALL: Normal Floettes (all flower colors) cannot Mega Evolve!
            if base_name.startswith('floette') and not is_eternal:
                has_mega_stone = False

            if base_name.startswith('raichu') and not is_raichu_alola:
                    has_mega_stone = False
                    
            if mega_forms and (has_mega_stone or has_dragon_ascent or is_eternal) and key_items.get('mega_bracelet'):
                form_id, form_name = mega_forms[0]
                
                if held_item.endswith('-x'):
                    target = next((f for f in mega_forms if '-mega-x' in f[1]), mega_forms[0])
                    form_id, form_name = target
                elif held_item.endswith('-y'):
                    target = next((f for f in mega_forms if '-mega-y' in f[1]), mega_forms[0])
                    form_id, form_name = target
                    
                btn = discord.ui.Button(label=f"🧬 Mega Evolve", style=discord.ButtonStyle.danger, custom_id=f"transform_{form_id}_{form_name}", row=2)
                btn.callback = self.handle_transformation
                self.add_item(btn)
                gimmick_found = True
            
            # 2. GIGANTAMAX (Requires Dynamax Band)
            if gmax_form and gmax_factor and key_items.get('dynamax_band'):
                form_id, form_name = gmax_form
                btn = discord.ui.Button(label=f"🌪️ Gigantamax", style=discord.ButtonStyle.danger, custom_id=f"transform_{form_id}_{form_name}", row=2)
                btn.callback = self.handle_transformation
                self.add_item(btn)
                gimmick_found = True
                
            # 3. GENERIC DYNAMAX (Requires Dynamax Band, only spawns if no other gimmick is ready)
            if not gimmick_found and key_items.get('dynamax_band'):
                btn = discord.ui.Button(label="🔴 Dynamax", style=discord.ButtonStyle.danger, custom_id="transform_0_dynamax", row=2)
                btn.callback = self.handle_transformation
                self.add_item(btn)

    async def handle_swap(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("⚠️ This is not your field expedition!", ephemeral=True)
            
        # Instantiate the new View, passing 'self' so it remembers where it came from
        swap_view = SwapMenu(self.cog, self.user_id, self.ctx, main_battle_view=self)
        
        # Edit the message to show the dropdown menu instead of the attack buttons!
        await interaction.response.edit_message(view=swap_view)

    async def generate_battle_scene(self, player_id, npc_id, p_hp, p_max_hp, n_hp, n_max_hp, 
                                        player_shiny=False, npc_shiny=False, 
                                        weather='none', p_status=None, n_status=None, 
                                        p_hazards=None, n_hazards=None):
            """Fetches high-res official artwork and composites them onto a 2D battlefield canvas with HUD overlays."""
            
            base_url = "https://raw.githubusercontent.com/Dre-J/pokebotsprites/refs/heads/master/sprites/pokemon/other/official-artwork"
            # 🚨 THE TRIPWIRE: Print exactly what IDs the engine is receiving!
            print(f"\n🚨 VISUAL ENGINE DIAGNOSTIC -> Player ID: {player_id} | NPC ID: {npc_id}")
            p_url = f"{base_url}/shiny/{player_id}.png" if player_shiny else f"{base_url}/{player_id}.png"
            n_url = f"{base_url}/shiny/{npc_id}.png" if npc_shiny else f"{base_url}/{npc_id}.png"

            async with aiohttp.ClientSession() as session:
                async with session.get(p_url) as resp1:
                    p_data = await resp1.read() if resp1.status == 200 else None
                async with session.get(n_url) as resp2:
                    n_data = await resp2.read() if resp2.status == 200 else None

            fallback_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0bIDAT\x08\x99c\xf8\x0f\x04\x00\x09\xfb\x03\xfd\xe3U\xf2\x9c\x00\x00\x00\x00IEND\xaeB`\x82'
            
            try:
                p_img = Image.open(BytesIO(p_data if p_data else fallback_bytes)).convert("RGBA")
                n_img = Image.open(BytesIO(n_data if n_data else fallback_bytes)).convert("RGBA")
            except Exception as e:
                print(f"PIL Image Error: {e}")
                p_img = Image.new('RGBA', (250, 250), (0, 0, 0, 0))
                n_img = Image.new('RGBA', (250, 250), (0, 0, 0, 0))

            p_img = ImageOps.mirror(p_img)
            p_img = p_img.resize((180, 180), Image.Resampling.LANCZOS)
            n_img = n_img.resize((180, 180), Image.Resampling.LANCZOS)

            # ==========================================
            # 1. PROCEDURAL HABITAT BACKGROUND
            # ==========================================
            # Sky Blue top half, Grass Green bottom half
            bg = Image.new('RGBA', (600, 300), (135, 206, 235, 255)) 
            bg_draw = ImageDraw.Draw(bg)
            bg_draw.rectangle([0, 150, 600, 300], fill=(120, 200, 80, 255))
            
            # (Optional: If you ever want a custom image file, replace the 3 lines above with this:)
            # bg = Image.open("your_custom_background.png").resize((600, 300)).convert("RGBA")

            # Moved NPC down from Y=20 to Y=60 so it clears the HUD
            bg.paste(n_img, (380, 60), n_img)   
            bg.paste(p_img, (70, 80), p_img)  

            # ==========================================
            # 2. TRANSLUCENT HUD OVERLAYS
            # ==========================================
            # Pillow requires a separate transparent layer to draw translucent shapes
            overlay = Image.new('RGBA', bg.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            
            # Player HUD Backdrop (Bottom Left)
            overlay_draw.rounded_rectangle([85, 235, 265, 295], radius=10, fill=(20, 20, 20, 170))
            
            # NPC HUD Backdrop (Top Right)
            overlay_draw.rounded_rectangle([385, 10, 565, 70], radius=10, fill=(20, 20, 20, 170))

            # Weather Backdrop (Top Center)
            if weather and weather != 'none':
                overlay_draw.rounded_rectangle([250, 5, 350, 35], radius=8, fill=(20, 20, 20, 170))

            # Composite the translucent HUD onto the background
            bg = Image.alpha_composite(bg, overlay)
            
            # Re-initialize draw on the newly composited background for solid text/bars
            draw = ImageDraw.Draw(bg)
            
            bar_width = 150
            bar_height = 16 

            p_pct = max(0.0, min(1.0, p_hp / max(1, p_max_hp)))
            n_pct = max(0.0, min(1.0, n_hp / max(1, n_max_hp)))

            def get_color(pct):
                if pct > 0.5: return (46, 204, 113, 255)  
                if pct > 0.2: return (241, 196, 15, 255)  
                return (231, 76, 60, 255)                 

            font = ImageFont.load_default()

            # ==========================================
            # 3. DRAW WEATHER & STATUS TEXT
            # ==========================================
            if weather and weather != 'none':
                w_colors = {'sun': (253, 203, 110), 'rain': (116, 185, 255), 'sand': (225, 177, 44), 'hail': (223, 230, 233)}
                w_color = w_colors.get(weather, (255, 255, 255))
                # Centered in the Weather Backdrop
                draw.text((275, 13), f"[{weather.upper()}]", fill=w_color, font=font)

            status_colors = {'burn': (255, 118, 117), 'poison': (162, 155, 254), 'paralysis': (253, 203, 110), 'sleep': (178, 190, 195), 'freeze': (129, 236, 236)}
            
            if n_status and n_status.get('name'):
                s_name = n_status['name']
                draw.text((395, 15), f"[{s_name[:3].upper()}]", fill=status_colors.get(s_name, (255, 255, 255)), font=font)
                
            if p_status and p_status.get('name'):
                s_name = p_status['name']
                draw.text((95, 240), f"[{s_name[:3].upper()}]", fill=status_colors.get(s_name, (255, 255, 255)), font=font)

            # ==========================================
            # 4. DRAW HP BARS
            # ==========================================
            # NPC Bar
            draw.rectangle([400, 35, 400 + bar_width, 35 + bar_height], fill=(50, 50, 50, 255))
            draw.rectangle([400, 35, 400 + (bar_width * n_pct), 35 + bar_height], fill=get_color(n_pct))
            draw.text((405, 35), f"{n_hp} / {n_max_hp}", fill=(255, 255, 255, 255), font=font)

            # Player Bar
            draw.rectangle([100, 260, 100 + bar_width, 260 + bar_height], fill=(50, 50, 50, 255))
            draw.rectangle([100, 260, 100 + (bar_width * p_pct), 260 + bar_height], fill=get_color(p_pct))
            draw.text((105, 260), f"{p_hp} / {p_max_hp}", fill=(255, 255, 255, 255), font=font)

            # ==========================================
            # 5. DRAW ENVIRONMENTAL HAZARDS
            # ==========================================
            if p_hazards:
                h_text = []
                if p_hazards.get('stealth-rock'): h_text.append("ROCKS")
                if p_hazards.get('spikes', 0) > 0: h_text.append(f"SPIKESx{p_hazards['spikes']}")
                if p_hazards.get('toxic-spikes', 0) > 0: h_text.append(f"T.SPIKESx{p_hazards['toxic-spikes']}")
                if p_hazards.get('sticky-web'): h_text.append("WEB")
                if h_text:
                    draw.text((95, 278), " | ".join(h_text), fill=(178, 190, 195, 255), font=font)

            if n_hazards:
                h_text = []
                if n_hazards.get('stealth-rock'): h_text.append("ROCKS")
                if n_hazards.get('spikes', 0) > 0: h_text.append(f"SPIKESx{n_hazards['spikes']}")
                if n_hazards.get('toxic-spikes', 0) > 0: h_text.append(f"T.SPIKESx{n_hazards['toxic-spikes']}")
                if n_hazards.get('sticky-web'): h_text.append("WEB")
                if h_text:
                    draw.text((395, 53), " | ".join(h_text), fill=(178, 190, 195, 255), font=font)

            buffer = BytesIO()
            bg.save(buffer, format="PNG")
            buffer.seek(0)
            
            # Randomize the filename to bust Discord's aggressive image cache!
            new_filename = f"battle_{random.randint(10000, 99999)}.png"
            return discord.File(fp=buffer, filename=new_filename)

    async def open_bag(self, interaction: discord.Interaction):
        """Queries the user's inventory for medical supplies and opens the Dropdown UI."""
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("⚠️ This is not your field expedition!", ephemeral=True)

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Fetch any items classified as medical supplies that the user actually owns
        medical_items = ('potion', 'super-potion', 'hyper-potion', 'max-potion', 'full-restore', 'revive', 'full-heal')
        placeholders = ','.join('?' * len(medical_items))
        
        query = f"SELECT item_name, quantity FROM user_inventory WHERE user_id = ? AND item_name IN ({placeholders}) AND quantity > 0"
        cursor.execute(query, (self.user_id, *medical_items))
        inventory_data = cursor.fetchall()
        conn.close()
        
        if not inventory_data:
            return await interaction.response.send_message("🎒 Your medical pouch is empty! Requisition supplies from the `!market`.", ephemeral=True)
            
        # Spawn the Bag UI and pass the inventory data to it
        bag_view = ItemSelect(self.cog, self.user_id, self.ctx, main_battle_view=self, items=inventory_data)
        
        await interaction.response.edit_message(view=bag_view)

    async def handle_move(self, interaction: discord.Interaction):
            if str(interaction.user.id) != self.user_id:
                return await interaction.response.send_message("⚠️ This is not your field expedition!", ephemeral=True)
                
            await interaction.response.defer()
            
            try:
                state = self.cog.active_battles[self.user_id]
                p_active = state['player_team'][state['active_player_index']]
                n_active = state['npc_team'][state['active_npc_index']]
                
                combat_log = f"**Turn {state['turn_number']}**\n\n"

                # ==========================================
                # OPEN THE DATABASE ONCE FOR THE ENTIRE TURN
                # ==========================================
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()

                # ==========================================
                # 1. REGISTER THE PLAYER'S PAYLOAD
                # ==========================================
                custom_id = interaction.data['custom_id']
                is_z_move = custom_id.endswith('_z')
                is_max_move = custom_id.endswith('_max')
                
                # --- FIREWALL: KEY ITEM AUTHORIZATION ---
                if is_max_move and not state.get('key_items', {}).get('dynamax_band'):
                    # Close the DB before rejecting the interaction to prevent soft-locks!
                    conn.close() 
                    return await interaction.response.send_message("❌ Authorization denied. You do not possess a Dynamax Band.", ephemeral=True)
                    
                if is_z_move and not state.get('key_items', {}).get('z_ring'):
                    conn.close()
                    return await interaction.response.send_message("❌ Authorization denied. You do not possess a Z-Ring.", ephemeral=True)

                raw_id_parts = custom_id.split('_')
                move_name = raw_id_parts[2]

                # APPLY THE PVE CHOICE LOCK 🚨
                held_item = (p_active.get('held_item') or "").lower().replace(' ', '-')
                if held_item in ['choice-band', 'choice-specs', 'choice-scarf']:
                    if 'volatile_statuses' not in p_active:
                        p_active['volatile_statuses'] = {}
                    if not p_active['volatile_statuses'].get('choice_lock'):
                        p_active['volatile_statuses']['choice_lock'] = move_name
                # ------------------------------------------

                p_available_moves = [m for m in p_active['moves'] if m['pp'] > 0]
                p_z_display = ""
                
                # --- STRUGGLE OVERRIDE (PLAYER) ---
                if not p_available_moves:
                    move_name = 'struggle'
                    p_move_stats = {
                        'type': 'typeless', 'power': 50, 'accuracy': 1000, 'class': 'physical',
                        'target': 'defender', 'ailment': 'none', 'ailment_chance': 0,
                        'stat_name': 'none', 'stat_change': 0, 'stat_chance': 0,
                        'healing': 0, 'drain': 0, 'name': 'struggle', 
                        'priority': 0 
                    }
                    combat_log += f"⚠️ Your **{p_active['name'].capitalize()}** has no energy left!\n"
                else:
                    for m in p_active['moves']:
                        if m['name'] == move_name:
                            m['pp'] -= 1
                            break
                            
                    
                    # Fetch Player Move Data
                   # Pull all 17 variables in the exact order of the DB Schema!
                    cursor.execute("""
                        SELECT name, type, power, accuracy, damage_class, pp, priority,
                            target, ailment, ailment_chance, stat_name, stat_change, stat_chance, 
                            status_type, status_chance, healing, drain
                        FROM base_moves WHERE name = ?
                    """, (move_name,))
                    p_row = cursor.fetchone()
                    
                    if p_row:
                        p_move_stats = {
                            'name': p_row[0], 'type': p_row[1], 'power': p_row[2] or 0, 'accuracy': p_row[3] or 100, 
                            'class': p_row[4], 'pp': p_row[5], 'priority': p_row[6] or 0, 'target': p_row[7], 
                            'ailment': p_row[8], 'ailment_chance': p_row[9] or 0, 'stat_name': p_row[10], 
                            'stat_change': p_row[11] or 0, 'stat_chance': p_row[12] or 0,
                            'status_type': p_row[13], 'status_chance': p_row[14] or 0, # 🚨 New!
                            'healing': p_row[15] or 0, 'drain': p_row[16] or 0
                        }
                    else:
                        # A complete, fully-mapped dictionary so the physics engine never starves!
                        print(f"⚠️ WARNING: Player move '{move_name}' not found in DB! Using typeless fallback.")
                        p_move_stats = {
                            'type': 'typeless', 'power': 0, 'accuracy': 100, 'class': 'status',
                            'target': 'defender', 'ailment': 'none', 'ailment_chance': 0,
                            'stat_name': 'none', 'stat_change': 0, 'stat_chance': 0,
                            'healing': 0, 'drain': 0, 'name': move_name, 'priority': 0
                        }

                # Apply Z-Move Mutator if triggered
                if is_z_move:
                    state['adaptation']['used'] = True
                    state['adaptation']['z_toggled'] = False 
                    if p_move_stats['class'] == 'status':
                        p_active['current_hp'] = p_active['max_hp']
                        p_z_display = f"Z-{move_name.replace('-', ' ').title()}"
                        combat_log += f"🌟 **{p_active['name'].capitalize()}** surrounded itself with Z-Power and fully restored its HP!\n"
                    else:
                        p_move_stats['power'] = 175 
                        p_move_stats['accuracy'] = 1000 
                        p_z_display = Z_MOVE_NAMES.get(p_move_stats['type'], 'Maximum Overdrive')

                # Apply Dynamax & G-Max Mutator
                if is_max_move:
                    # 1. Clean the string to properly fetch G-Max data!
                    species_raw = p_active['name'].lower()
                    species_clean = species_raw.replace(' (dynamax)', '').replace(' (gigantamax)', '').split('-')[0].strip()
                    gmax_search_key = f"{species_clean}-gmax"
                    
                    gmax_data = GMAX_MOVES.get(gmax_search_key)
                    has_gmax = p_active.get('gmax_factor', False) or p_active.get('gmax_factor', 0) == 1
                    
                    is_signature_gmax = False
                    if has_gmax and gmax_data and p_move_stats['type'] == gmax_data['type']:
                        p_z_display = gmax_data['name']
                        is_signature_gmax = True
                    else:
                        max_data = MAX_MOVES.get(p_move_stats['type'], {'name': 'Max Strike'})
                        p_z_display = max_data['name']
                    
                    # 2. MAX GUARD INTERCEPTOR
                    if p_move_stats['class'] == 'status':
                        p_move_stats['name'] = 'max-guard' # 🚨 Let the physics engine know it's a shield!
                        p_move_stats['target'] = 'user'    # Target self, not the opponent!
                        p_move_stats['power'] = 0
                        p_move_stats['ailment'] = 'none'
                        p_move_stats['status_type'] = 'none'
                        p_move_stats['stat_name'] = 'none'
                        p_z_display = "Max Guard"
                        
                    # 3. KINETIC MAX MOVES & SANITIZATION
                    else:
                        p_move_stats['power'] = 140 if is_signature_gmax else 130 
                        p_move_stats['accuracy'] = 1000 
                        
                        # Wipe out base move secondary effects!
                        p_move_stats['ailment'] = 'none' 
                        p_move_stats['status_type'] = 'none'
                        p_move_stats['status_chance'] = 0
                        p_move_stats['stat_name'] = 'none'
                        p_move_stats['healing'] = 0
                        p_move_stats['drain'] = 0
                        
                        # --- THE G-MAX INTERCEPTOR (Parity with PvP) ---
                        if is_signature_gmax:
                            p_move_stats['name'] = gmax_data['name'] # Ensure the physics engine sees the true name
                            
                            # Hardcoded Anomalies
                            if p_z_display == 'G-Max Befuddle':
                                p_move_stats['ailment'] = random.choice(['poison', 'paralysis', 'sleep'])
                                p_move_stats['ailment_chance'] = 100
                            elif p_z_display == 'G-Max Stun Shock':
                                p_move_stats['ailment'] = random.choice(['poison', 'paralysis'])
                                p_move_stats['ailment_chance'] = 100
                                
                            # Persistent Ecological Disasters
                            elif p_z_display in ['G-Max Wildfire', 'G-Max Vine Lash', 'G-Max Cannonade', 'G-Max Vocalith']:
                                p_move_stats['status_type'] = p_z_display.lower().replace('g-max ', '')
                                p_move_stats['status_chance'] = 100
                                
                            # Standard Injections
                            else:
                                if 'ailment' in gmax_data:
                                    p_move_stats['ailment'] = gmax_data['ailment']
                                    p_move_stats['ailment_chance'] = 100
                                if 'stat_name' in gmax_data:
                                    p_move_stats['stat_name'] = gmax_data['stat_name']
                                    p_move_stats['stat_change'] = gmax_data['stat_change']
                                    p_move_stats['stat_chance'] = 100
                                    p_move_stats['target'] = gmax_data.get('target', 'defender')
                                if 'healing' in gmax_data:
                                    p_move_stats['healing'] = gmax_data['healing']
                                    
                        else:
                            p_move_stats['name'] = p_z_display # e.g. "Max Strike"
                            if 'stat' in max_data:
                                p_move_stats['stat_name'] = max_data['stat']
                                p_move_stats['stat_change'] = max_data['change']
                                p_move_stats['stat_chance'] = 100
                                p_move_stats['target'] = max_data['target']

                # ==========================================
                # 2. REGISTER THE NPC'S PAYLOAD
                # ==========================================
                available_moves = [m for m in n_active['moves'] if m['pp'] > 0]
                n_move_stats = None
                npc_move_name = None
                
                # --- PHASE 2 - VOLUNTARY FLIGHT AI ---
                # 1. Gather the benched team
                alive_bench = [i for i, p in enumerate(state['npc_team']) if p['current_hp'] > 0 and i != state['active_npc_index']]
                is_swapping = False
                
                print(f"DEBUG AI [FLIGHT]: Alive bench indices: {alive_bench}")
                
                # Only consider fleeing if we actually have backup!
                if alive_bench:
                    p_types = p_active.get('types', [])
                    n_types = n_active.get('types', [])
                    
                    # 2. Assess Threat Level (Defensive Vulnerability)
                    def_multiplier = 1.0
                    for p_type in p_types:
                        for n_type in n_types:
                            # Note: Ensure TYPE_CHART is accessible here!
                            def_multiplier *= TYPE_CHART.get(p_type, {}).get(n_type, 1.0)
                            
                    print(f"DEBUG AI [FLIGHT]: Player Types: {p_types} | NPC Types: {n_types}")
                    print(f"DEBUG AI [FLIGHT]: Calculated Defensive Vulnerability: {def_multiplier}x")
                            
                    # FLIGHT TRIGGER: Taking 2x damage, or taking 2x damage while below 50% HP
                    is_critical_threat = def_multiplier >= 2.0
                    is_injured_threat = (def_multiplier >= 2.0 and n_active['current_hp'] < n_active['max_hp'] * 0.5)
                    
                    if is_critical_threat or is_injured_threat:
                        print(f"DEBUG AI [FLIGHT]: THREAT DETECTED! Critical: {is_critical_threat}, Injured: {is_injured_threat}")
                        
                        # 70% chance to retreat (This keeps the AI slightly unpredictable and prone to "mistakes"!)
                        retreat_roll = random.randint(1, 100)
                        print(f"DEBUG AI [FLIGHT]: Rolling for retreat... Rolled {retreat_roll}/100 (Needs <= 70)")
                        
                        if retreat_roll <= 70:
                            best_score = -1.0
                            swap_target_idx = None
                            
                            print("DEBUG AI [FLIGHT]: Executing Tactical Analysis on benched specimens...")
                            
                            # 3. Find the Optimal Replacement (The Heuristic)
                            for i in alive_bench:
                                benched_specimen = state['npc_team'][i]
                                score = 1.0
                                b_types = benched_specimen.get('types', [])
                                
                                # Offensive Check: Can the bench hit the player hard?
                                max_off = 0.0
                                for b_t in b_types:
                                    for p_t in p_types:
                                        max_off = max(max_off, TYPE_CHART.get(b_t, {}).get(p_t, 1.0))
                                score *= (max_off if max_off > 0 else 1.0)
                                
                                # Defensive Check: Can the bench resist the player's types?
                                max_def = 0.0
                                for p_t in p_types:
                                    for b_t in b_types:
                                        max_def = max(max_def, TYPE_CHART.get(p_t, {}).get(b_t, 1.0))
                                        
                                if max_def == 0: score *= 4.0      # Immune!
                                elif max_def < 1.0: score *= 2.0   # Resists!
                                elif max_def > 1.0: score *= 0.25  # Weakness!
                                
                                print(f"DEBUG AI [FLIGHT]: Specimen {benched_specimen['name']} (Types: {b_types}) | Offense: {max_off}x | Defense: {max_def}x | Final Score: {score}")
                                
                                if score > best_score:
                                    best_score = score
                                    swap_target_idx = i
                                    
                            # 4. Execute the Swap BEFORE the turn queue!
                            # We only swap if the best replacement actually has a tactical advantage (Score > 1.0)
                            if swap_target_idx is not None and best_score > 1.0:
                                print(f"DEBUG AI [FLIGHT]: SUCCESS! Swapping to Index {swap_target_idx} (Score: {best_score}).")
                                combat_log += f"🔄 **Tactical Retreat!** The rival recalled **{n_active['name'].capitalize()}**!\n"
                                
                                # Update the state memory
                                state['active_npc_index'] = swap_target_idx
                                n_active = state['npc_team'][swap_target_idx]
                                combat_log += f"The rival deployed **{n_active['name'].capitalize()}**!\n\n"
                                
                                # Trigger Entry Hazards / Abilities for the new arrival!
                                # Make sure trigger_single_entry_ability is accessible here!
                                combat_log = trigger_single_entry_ability(n_active, p_active, "The rival's", state, combat_log)
                                
                                # --- TRIGGER ENVIRONMENTAL HAZARDS ---
                                hazard_log = apply_entry_hazards(n_active, state['npc_hazards'], TYPE_CHART, "The rival's")
                                if hazard_log:
                                    combat_log += hazard_log
                                # ------------------------------------------

                                is_swapping = True
                            else:
                                print(f"DEBUG AI [FLIGHT]: ABORT SWAP. Best benched score was {best_score}. Staying in.")
                        else:
                            print("DEBUG AI [FLIGHT]: AI decided to hold its ground despite the threat.")
                # ------------------------------------------
                
                # --- IF NOT SWAPPING, PROCEED TO PICK AN ATTACK ---
                if not is_swapping:
                    print("DEBUG AI [ATTACK]: Engaging offensive move selection...")

                    # --- STRUGGLE OVERRIDE ---
                    if not available_moves:
                        npc_move_name = 'struggle'
                        n_move_stats = {
                            'type': 'typeless', 'power': 50, 'accuracy': 1000, 'class': 'physical',
                            'target': 'defender', 'ailment': 'none', 'ailment_chance': 0,
                            'stat_name': 'none', 'stat_change': 0, 'stat_chance': 0,
                            'healing': 0, 'drain': 0, 'name': 'struggle',
                            'priority': 0 
                        }
                        combat_log += f"⚠️ The rival's **{n_active['name'].capitalize()}** has no energy left!\n"
                    else:
                        # --- TACTICAL PRIORITY FILTER (PHASE 3 UTILITY AI) ---
                        best_moves = []
                        highest_score = -10000.0
                        
                        p_types = p_active.get('types', [])
                        n_types = n_active.get('types', [])
                        
                        # Calculate health percentages for tactical decisions
                        p_hp_pct = p_active['current_hp'] / max(1, p_active.get('max_hp', 1))
                        n_hp_pct = n_active['current_hp'] / max(1, n_active.get('max_hp', 1))
                        
                        for m in available_moves:
                            cursor.execute("SELECT type, power, damage_class, healing, target FROM base_moves WHERE name = ?", (m['name'],))
                            m_data = cursor.fetchone()
                            
                            if m_data:
                                m_type, m_power, m_class, m_heal, m_target = m_data
                                m_power = m_power or 0 
                                m_heal = m_heal or 0
                                
                                score = 10.0 # Base minimum score
                                
                                # 1. DAMAGE CALCULATION & THE EXECUTIONER
                                if m_class != 'status' and m_power > 0:
                                    multiplier = 1.0
                                    for p_type in p_types:
                                        multiplier *= TYPE_CHART.get(m_type, {}).get(p_type, 1.0)
                                        
                                    # STAB (Same Type Attack Bonus) calculation
                                    if m_type in n_types:
                                        multiplier *= 1.5
                                        
                                    estimated_damage = (m_power * multiplier)
                                    score += estimated_damage
                                    
                                    # The Executioner: Massive bonus if this move is highly likely to KO
                                    # (We use a rough estimate here to avoid running the full physics engine on every bench move)
                                    if estimated_damage >= (p_active['current_hp'] * 0.8):
                                        score += 10000.0 
                                        
                                # 2. STATUS & UTILITY SCORING
                                if m_class == 'status':
                                    
                                    # Self-Preservation (Smart Healing)
                                    if m_heal > 0 or m['name'] in ['roost', 'recover', 'soft-boiled', 'slack-off']:
                                        if n_hp_pct < 0.4: score += 5000.0    # Bleeding out! Panicked healing!
                                        elif n_hp_pct > 0.8: score -= 10000.0 # Don't waste a turn overhealing
                                        else: score += 500.0
                                        
                                    # Pathogen Targeting (Smart Status Conditions)
                                    if m['name'] in ['will-o-wisp', 'toxic', 'thunder-wave', 'spore', 'sleep-powder']:
                                        if p_active.get('status_condition'):
                                            score -= 10000.0 # Do not try to burn a poisoned target!
                                        else:
                                            score += 800.0
                                            
                                    # Tactical Setup (Swords Dance, Calm Mind)
                                    # 'target' 7 is usually "user" in the PokeAPI schema
                                    if m_target == 7 and m['name'] not in ['protect', 'detect']:
                                        if n_hp_pct > 0.7: score += 400.0     # Healthy? Set up!
                                        elif n_hp_pct < 0.3: score -= 5000.0  # Dying? Do NOT set up!
                                        
                                    # Stalling (Smart Protect)
                                    if m['name'] in ['protect', 'detect', 'spiky-shield', 'king-shield']:
                                        if state.get('npc_used_protect_last_turn'):
                                            score -= 10000.0 # Never spam Protect twice
                                        elif p_active.get('status_condition') or 'leech-seed' in p_active.get('volatile_statuses', {}):
                                            score += 2000.0 # Player is bleeding out. Stall them!
                                            
                                # Lock in the highest score
                                if score > highest_score:
                                    highest_score = score
                                    best_moves = [m] 
                                elif score == highest_score:
                                    best_moves.append(m) 
                                    
                        chosen_move = random.choice(best_moves) if best_moves else random.choice(available_moves)
                        
                        # Remember if the NPC used Protect so it doesn't spam it next turn!
                        state['npc_used_protect_last_turn'] = (chosen_move['name'] in ['protect', 'detect', 'spiky-shield', 'king-shield'])
                        
                        npc_move_name = chosen_move['name']
                        print(f"DEBUG AI [ATTACK]: Selected '{npc_move_name}' (Score: {highest_score})")
                        chosen_move['pp'] -= 1 
                        
                        cursor.execute("""
                            SELECT type, power, accuracy, damage_class, target, ailment, ailment_chance, 
                                stat_name, stat_change, stat_chance, healing, drain, name, priority
                        FROM base_moves WHERE name = ?
                        """, (npc_move_name,))
                        n_row = cursor.fetchone()
                        
                        if n_row:
                            n_move_stats = {
                                'type': n_row[0], 'power': n_row[1] or 0, 'accuracy': n_row[2] or 100, 'class': n_row[3],
                                'target': n_row[4], 'ailment': n_row[5], 'ailment_chance': n_row[6] or 0,
                                'stat_name': n_row[7], 'stat_change': n_row[8] or 0, 'stat_chance': n_row[9] or 0,
                                'healing': n_row[10] or 0, 'drain': n_row[11] or 0,
                                'name': n_row[12],
                                'priority': n_row[13] or 0
                            }
                        else:
                            print(f"⚠️ WARNING: NPC move '{npc_move_name}' not found in DB! Using typeless fallback.")
                            n_move_stats = {
                                'type': 'typeless', 'power': 0, 'accuracy': 100, 'class': 'status',
                                'target': 'defender', 'ailment': 'none', 'ailment_chance': 0,
                                'stat_name': 'none', 'stat_change': 0, 'stat_chance': 0,
                                'healing': 0, 'drain': 0, 'name': npc_move_name, 'priority': 0
                            }
                        
                conn.close()

                # ==========================================
                # 3. KINETIC SPEED CHECK (PvE)
                # ==========================================
                def get_true_speed(specimen):
                    raw_spd = specimen['stats']['speed']
                    stage = specimen.get('stat_stages', {}).get('speed', 0)
                    
                    # Apply biological stages
                    if stage > 0: multiplier = (2.0 + stage) / 2.0
                    elif stage < 0: multiplier = 2.0 / (2.0 + abs(stage))
                    else: multiplier = 1.0
                    
                    final_spd = int(raw_spd * multiplier)
                    
                    # --- Equipment Modifiers ---
                    item = (specimen.get('held_item') or "").lower().replace(' ', '-')
                    if item == 'choice-scarf':
                        final_spd = int(final_spd * 1.5)

                    # Apply Paralysis penalty
                    status = specimen.get('status_condition', {})
                    if status and status.get('name') == 'paralysis':
                        final_spd = int(final_spd * 0.5)
                        
                    return final_spd

                p_speed = get_true_speed(p_active)
                n_speed = get_true_speed(n_active)

                
                player_action = (p_active, n_active, p_move_stats, move_name, True, p_z_display, is_z_move, is_max_move)
                
                # The NPC doesn't use gimmicks yet, so we pass False for both
                npc_action = (n_active, p_active, n_move_stats, npc_move_name, False, "", False, False)


                
                # Note: If the NPC is exhausted or swapped out, their action is None. 
                action_queue = []
                
                if n_move_stats is None:
                    action_queue = [player_action]
                else:
                    try:
                        # Absolute Type-Safety Casting
                        # The 'or 0' intercepts the None, and int() guarantees a mathematical integer!
                        p_prio = int(p_move_stats.get('priority') or 0)
                        n_prio = int(n_move_stats.get('priority') or 0)
                        
                        # 1. Compare Move Priority Brackets First
                        if p_prio > n_prio:
                            action_queue = [player_action, npc_action]
                        elif n_prio > p_prio:
                            action_queue = [npc_action, player_action]
                        else:
                            # 2. Priority Tie! Fall back to Biological Speed Calculation
                            if p_speed > n_speed: 
                                action_queue = [player_action, npc_action]
                            elif n_speed > p_speed: 
                                action_queue = [npc_action, player_action]
                            else: 
                                # 3. Absolute Tie! Coin flip.
                                action_queue = [player_action, npc_action] if random.choice([True, False]) else [npc_action, player_action]
                                
                    except Exception as e:
                        print("\n🚨 CRITICAL CRASH IN PRIORITY CHECKING")
                        import traceback
                        traceback.print_exc()
                        await interaction.followup.send("Error, check console", ephemeral=True)

                print(f"DEBUG 1: Queue built! Length: {len(action_queue)}")
                print(f"DEBUG 1.5: Queue contents: {[a[3] for a in action_queue]}") # Prints the move names
                
                # ==========================================
                # 4. EXECUTE THE INITIATIVE QUEUE
                # ==========================================
                for attacker, defender, move_stats, raw_move_name, is_player, z_disp, is_z_action, is_max_action in action_queue:
                    print(f"DEBUG 2: Now processing turn for: {attacker['name']} using {raw_move_name}")
                    
                    if attacker['current_hp'] <= 0:
                        continue
                    if defender['current_hp'] <= 0:
                        combat_log += f"But there was no target for **{attacker['name'].capitalize()}** to attack!\n"
                        continue

                    can_attack = True
                    status = attacker.get('status_condition', {})
                    owner_prefix = "Your " if is_player else "The rival's "
                    
                    # --- VOLATILE STATUS: CONFUSION CHECK ---
                    volatiles = attacker.get('volatile_statuses', {})
                    if 'confusion' in volatiles:
                        volatiles['confusion'] -= 1
                        if volatiles['confusion'] <= 0:
                            del volatiles['confusion']
                            combat_log += f"💫 **{attacker['name'].capitalize()}** snapped out of its confusion!\n"
                        else:
                            combat_log += f"💫 **{attacker['name'].capitalize()}** is confused...\n"
                            if random.randint(1, 100) <= 33: 
                                dmg, msg, inf_status, stat_chgs, heal_amt = calculate_damage(
                                attacker, defender, move_stats, 
                                weather=state.get('weather', {'type': 'none'})['type'],
                                target_hazards=state['npc_hazards'] if is_player else state['player_hazards'],
                                user_hazards=state['player_hazards'] if is_player else state['npc_hazards']
                            )
                                attacker['current_hp'] = max(0, attacker['current_hp'] - dmg)
                                combat_log += f"💥 {msg} (Dealt **{dmg}** damage!)\n"
                                can_attack = False 

                    if status:
                        s_name = status.get('name')
                        if s_name == 'paralysis' and random.randint(1, 4) == 1:
                            combat_log += f"⚡ {owner_prefix}**{attacker['name'].capitalize()}** is fully paralyzed!\n"
                            can_attack = False
                        elif s_name == 'sleep':
                            status['duration'] -= 1
                            if status['duration'] <= 0:
                                combat_log += f"☀️ {owner_prefix}**{attacker['name'].capitalize()}** woke up!\n"
                                attacker['status_condition'] = None
                            else:
                                combat_log += f"💤 {owner_prefix}**{attacker['name'].capitalize()}** is fast asleep.\n"
                                can_attack = False
                        elif s_name == 'freeze':
                            if random.randint(1, 5) == 1:
                                combat_log += f"🔥 {owner_prefix}**{attacker['name'].capitalize()}** thawed out!\n"
                                attacker['status_condition'] = None
                            else:
                                combat_log += f"🧊 {owner_prefix}**{attacker['name'].capitalize()}** is frozen solid!\n"
                                can_attack = False

                    if 'flinch' in volatiles:
                        combat_log += f"🚫 **{attacker['name'].capitalize()}** flinched and couldn't move!\n"
                        del volatiles['flinch'] 
                        can_attack = False

                    if can_attack:
                        # Prevent double-printing if Max Guard or Status Z-Moves already announced themselves in Phase 1
                        is_status_gimmick = (is_z_action or is_max_action) and move_stats['class'] == 'status'
                        
                        if not is_status_gimmick:
                            if is_player and is_z_action:
                                combat_log += f"🌟 Your **{attacker['name'].capitalize()}** unleashed its full-force Z-Move, `{z_disp}`!\n"
                            elif is_player and is_max_action:
                                combat_log += f"🌪️ Your **{attacker['name'].capitalize()}** warped reality with `{z_disp}`!\n"
                            else:
                                icon = "🟢" if is_player else "🔴"
                                combat_log += f"{icon} {owner_prefix.strip()} **{attacker['name'].capitalize()}** used `{raw_move_name.replace('-', ' ').title()}`!\n"

                        # ==========================================
                        # ENVIRONMENTAL HAZARD INTERCEPTOR
                        # ==========================================
                        HAZARD_MOVES = ['stealth-rock', 'spikes', 'toxic-spikes', 'sticky-web']
                        
                        if raw_move_name in HAZARD_MOVES:
                            # Target the OPPOSITE side of the field
                            target_habitat = state['npc_hazards'] if is_player else state['player_hazards']
                            habitat_owner = "the rival's" if is_player else "your"
                            
                            if raw_move_name == 'stealth-rock':
                                if target_habitat['stealth-rock']:
                                    combat_log += "But it failed! The sharp rocks are already floating!\n"
                                else:
                                    target_habitat['stealth-rock'] = True
                                    combat_log += f"🪨 Pointed stones float in the air around {habitat_owner} habitat!\n"
                                    
                            elif raw_move_name == 'spikes':
                                if target_habitat['spikes'] >= 3:
                                    combat_log += "But it failed! The habitat is fully covered in spikes!\n"
                                else:
                                    target_habitat['spikes'] += 1
                                    combat_log += f"🗡️ Spikes were scattered all around the feet of {habitat_owner} team!\n"
                                    
                            elif raw_move_name == 'toxic-spikes':
                                if target_habitat['toxic-spikes'] >= 2:
                                    combat_log += "But it failed! The habitat is saturated with toxic spikes!\n"
                                else:
                                    target_habitat['toxic-spikes'] += 1
                                    combat_log += f"☣️ Poison spikes were scattered all around {habitat_owner} habitat!\n"
                                    
                            elif raw_move_name == 'sticky-web':
                                if target_habitat['sticky-web']:
                                    combat_log += "But it failed! A sticky web already covers the habitat!\n"
                                else:
                                    target_habitat['sticky-web'] = True
                                    combat_log += f"🕸️ A sticky web spreads out across {habitat_owner} habitat!\n"
                                    
                            # Bypass the rest of the damage and accuracy calculations for this turn!
                            continue
                        # ==========================================

                        if random.randint(1, 100) > move_stats['accuracy']:
                            combat_log += "The attack missed!\n"
                        else:
                            print(f"DEBUG 3: {attacker['name']} passed status checks. Calling physics engine...")
                            dmg, msg, inf_status, stat_chgs, heal_amt = calculate_damage(
                                attacker, defender, move_stats, 
                                weather=state.get('weather', {'type': 'none'})['type'],
                                target_hazards=state['npc_hazards'] if is_player else state['player_hazards'],
                                user_hazards=state['player_hazards'] if is_player else state['npc_hazards']
                            )
                            print(f"DEBUG 4: Physics engine success! Damage calculated: {dmg}")
                            
                            defender['current_hp'] = max(0, defender['current_hp'] - dmg)
                            if msg: combat_log += f"*{msg}*\n"
                            if dmg > 0: combat_log += f"Dealt **{dmg}** damage.\n"
                            
                            #Check if the damage pushed them below the berry threshold!
                            berry_log = check_consumables(defender, owner_prefix) 
                            if berry_log: combat_log += berry_log

                            if heal_amt > 0:
                                attacker['current_hp'] = min(attacker.get('max_hp', 100), attacker['current_hp'] + heal_amt)
                                combat_log += f"💚 **{attacker['name'].capitalize()}** recovered health!\n"
                                
                            # --- STRUGGLE RECOIL INTERCEPTOR ---
                            if raw_move_name == 'struggle':
                                # Recoil is exactly 25% of the user's maximum HP!
                                recoil_dmg = max(1, math.floor(attacker.get('max_hp', 100) / 4))
                                attacker['current_hp'] = max(0, attacker['current_hp'] - recoil_dmg)
                                combat_log += f"💥 **{attacker['name'].capitalize()}** took recoil damage from thrashing about! (-{recoil_dmg} HP)\n"
                            
                            # ==========================================
                            # PHASE 1 & 2: THE FLINCH INTERCEPTOR
                            # ==========================================
                            is_flinch_proc = False
                            if inf_status == 'flinch':
                                is_flinch_proc = True
                                inf_status = None 
                            elif move_stats.get('ailment') == 'flinch' and random.randint(1, 100) <= move_stats.get('ailment_chance', 0):
                                is_flinch_proc = True

                            if is_flinch_proc:
                                if 'volatile_statuses' not in defender:
                                    defender['volatile_statuses'] = {}
                                defender['volatile_statuses']['flinch'] = True

                            # Process standard pathogens (Burn, Poison, etc.)
                            if inf_status and inf_status != 'none':
                                dur = random.randint(1, 3) if inf_status == 'sleep' else -1
                                defender['status_condition'] = {'name': inf_status, 'duration': dur}
                                hazard_icons = {'burn': '🔥', 'poison': '☣️', 'paralysis': '⚡', 'sleep': '💤', 'freeze': '🧊'}
                                combat_log += f"{hazard_icons.get(inf_status, '⚠️')} **{defender['name'].capitalize()}** was afflicted with {inf_status}!\n"

                            # ==========================================
                            # THE OMNIBOOST DICTIONARY (Complex Mutations)
                            # ==========================================
                            # DEFINED EARLY to prevent variable scope errors!
                            effective_move_name = z_disp if (is_player and is_max_action) else raw_move_name
                            
                            SPECIAL_STAT_MOVES = {
                                'ancient-power': [('attacker', 'attack', 1), ('attacker', 'defense', 1), ('attacker', 'special-attack', 1), ('attacker', 'special-defense', 1), ('attacker', 'speed', 1)],
                                'silver-wind': [('attacker', 'attack', 1), ('attacker', 'defense', 1), ('attacker', 'special-attack', 1), ('attacker', 'special-defense', 1), ('attacker', 'speed', 1)],
                                'ominous-wind': [('attacker', 'attack', 1), ('attacker', 'defense', 1), ('attacker', 'special-attack', 1), ('attacker', 'special-defense', 1), ('attacker', 'speed', 1)],
                                'clangorous-soulblaze': [('attacker', 'attack', 1), ('attacker', 'defense', 1), ('attacker', 'special-attack', 1), ('attacker', 'special-defense', 1), ('attacker', 'speed', 1)]
                            }

                            if effective_move_name in SPECIAL_STAT_MOVES:
                                effect_chance = move_stats.get('stat_chance') or 10
                                if random.randint(1, 100) <= effect_chance:
                                    stat_chgs = SPECIAL_STAT_MOVES[effective_move_name]
                                else:
                                    stat_chgs = [] 

                            # Execute the Stat Changes
                            for tgt, s_name, chg in stat_chgs:
                                target_specimen = attacker if tgt == 'attacker' else defender
                                
                                if 'volatile_statuses' not in target_specimen:
                                    target_specimen['volatile_statuses'] = {}
                                    
                                if s_name == 'flinch':
                                    target_specimen['volatile_statuses']['flinch'] = True
                                    continue 
                                    
                                # Intercept Custom Pathogens
                                if s_name == 'volatile_leech_seed':
                                    if 'leech-seed' not in target_specimen['volatile_statuses']:
                                        target_specimen['volatile_statuses']['leech-seed'] = True
                                    continue
                                    
                                if s_name == 'volatile_perish_song':
                                    if 'perish-song' not in target_specimen['volatile_statuses']:
                                        target_specimen['volatile_statuses']['perish-song'] = 3
                                    continue

                                stat_map = {'attack': 'attack', 'defense': 'defense', 'special-attack': 'sp_atk', 'special-defense': 'sp_def', 'speed': 'speed'}
                                db_stat = stat_map.get(s_name)
                                if db_stat:
                                    if 'stat_stages' not in target_specimen:
                                        target_specimen['stat_stages'] = {'attack': 0, 'defense': 0, 'sp_atk': 0, 'sp_def': 0, 'speed': 0}
                                    curr_stg = target_specimen['stat_stages'][db_stat]
                                    target_specimen['stat_stages'][db_stat] = max(-6, min(6, curr_stg + chg))
                                    
                                    direction = "fell" if chg < 0 else "rose"
                                    icon = "📉" if chg < 0 else "📈"
                                    combat_log += f"{icon} **{target_specimen['name'].capitalize()}**'s {s_name.replace('-', ' ')} {direction}!\n"
                                    
                            # Check Weather Modifications
                            new_weather = WEATHER_MOVES.get(str(effective_move_name))
                            if new_weather:
                                # Do not change weather if a Primordial climate is active!
                                if state.get('weather', {}).get('primordial', False):
                                    combat_log += f"↳ The extreme weather prevented `{effective_move_name}` from taking effect!\n"
                                else:
                                    attacker_item = (attacker.get('held_item') or "").lower().replace(' ', '-')
                                    weather_rocks = {'sun': 'heat-rock', 'rain': 'damp-rock', 'sand': 'smooth-rock', 'hail': 'icy-rock'}
                                    
                                    duration = 8 if attacker_item == weather_rocks.get(new_weather) else 5
                                    
                                    state['weather'] = {'type': new_weather, 'duration': duration, 'primordial': False}
                                    combat_log += f"↳ {WEATHER_MESSAGES.get(new_weather, 'The weather changed.')}\n"
                                
                                # If the held item matches the rock needed for this weather, 8 turns. Else, 5.
                                duration = 8 if attacker_item == weather_rocks.get(new_weather) else 5
                                
                                state['weather'] = {'type': new_weather, 'duration': duration}
                                combat_log += f"{WEATHER_MESSAGES[new_weather]}\n"

                # ==========================================
                # 5. PASS TO END OF TURN
                # ==========================================
                
                print(f"DEBUG 5: Handing off to process_turn_end. Combat log length: {len(combat_log)}")

                await self.process_turn_end(interaction, combat_log)
            except Exception as e:
                print("\n🚨 CRITICAL CRASH IN HANDLE_MOVE 🚨")
                import traceback
                traceback.print_exc()
                await interaction.followup.send("A critical engine failure occurred during the physics calculations. Check the console!", ephemeral=True)
                
                # Safely send the error to Discord so you don't even have to look at the console
                try:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(f"Engine Crash: {e}\nCheck the console!", ephemeral=True)
                    else:
                        await interaction.followup.send(f"Engine Crash: {e}\nCheck the console!", ephemeral=True)
                except:
                    pass        

    async def execute_npc_retaliation(self, interaction, combat_log):
        """Executes the NPC's free action when the player uses an item or manually swaps."""
        state = self.cog.active_battles[self.user_id]
        p_active = state['player_team'][state['active_player_index']]
        n_active = state['npc_team'][state['active_npc_index']]

        if n_active['current_hp'] <= 0:
            # If the NPC is somehow fainted (e.g., from a previous turn's poison), skip to the end
            return await self.process_turn_end(interaction, combat_log)

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        try:
            # --- 1. NPC THREAT ASSESSMENT ---
            available_moves = [m for m in n_active['moves'] if m['pp'] > 0]
            n_move_stats = None
            npc_move_name = None
            is_swapping = False
            
            alive_bench = [i for i, p in enumerate(state['npc_team']) if p['current_hp'] > 0 and i != state['active_npc_index']]
            
            # Flight AI
            if alive_bench:
                def_multiplier = 1.0
                for p_type in p_active.get('types', []):
                    for n_type in n_active.get('types', []):
                        # Ensure TYPE_CHART is imported/accessible here!
                        def_multiplier *= TYPE_CHART.get(p_type, {}).get(n_type, 1.0)
                        
                if def_multiplier >= 4.0 or (def_multiplier >= 2.0 and n_active['current_hp'] < n_active['max_hp'] * 0.5):
                    if random.randint(1, 100) <= 70:
                        best_score = -1.0
                        swap_target_idx = None
                        
                        for i in alive_bench:
                            b_spec = state['npc_team'][i]
                            score = 1.0
                            for p_t in p_active.get('types', []):
                                max_def = max([TYPE_CHART.get(p_t, {}).get(b_t, 1.0) for b_t in b_spec.get('types', [])])
                                if max_def == 0: score *= 4.0
                                elif max_def < 1.0: score *= 2.0
                                elif max_def > 1.0: score *= 0.25
                                
                            if score > best_score:
                                best_score = score
                                swap_target_idx = i
                                
                        if swap_target_idx is not None and best_score > 1.0:
                            combat_log += f"🔄 **Tactical Retreat!** The rival recalled **{n_active['name'].capitalize()}**!\n"
                            state['active_npc_index'] = swap_target_idx
                            n_active = state['npc_team'][swap_target_idx]
                            combat_log += f"The rival deployed **{n_active['name'].capitalize()}**!\n\n"
                            
                            combat_log = trigger_single_entry_ability(n_active, p_active, "The rival's", state, combat_log)
                            
                            # ==========================================
                            # PATCH 1: HAZARD TRIGGER ON RETREAT
                            # ==========================================
                            # Ensure apply_entry_hazards is imported/accessible here!
                            hazard_log = apply_entry_hazards(n_active, state['npc_hazards'], TYPE_CHART, "The rival's")
                            if hazard_log:
                                combat_log += hazard_log
                            # ==========================================
                            
                            is_swapping = True

            # --- 2. OFFENSIVE RETALIATION ---
            if not is_swapping:
                if not available_moves:
                    npc_move_name = 'struggle'
                    n_move_stats = {'type': 'typeless', 'power': 50, 'accuracy': 1000, 'class': 'physical', 'target': 'defender', 'ailment': 'none', 'ailment_chance': 0, 'stat_name': 'none', 'stat_change': 0, 'stat_chance': 0, 'healing': 0, 'drain': 0, 'name': 'struggle'}
                else:
                    best_moves = []
                    highest_score = -10000.0
                    for m in available_moves:
                        cursor.execute("SELECT type, power, damage_class, healing, target FROM base_moves WHERE name = ?", (m['name'],))
                        m_data = cursor.fetchone()
                        if m_data:
                            m_type, m_power, m_class, m_heal, m_target = m_data
                            m_power = m_power or 0 
                            score = 10.0
                            
                            if m_class != 'status' and m_power > 0:
                                mult = 1.0
                                for p_type in p_active.get('types', []):
                                    mult *= TYPE_CHART.get(m_type, {}).get(p_type, 1.0)
                                if m_type in n_active.get('types', []): mult *= 1.5
                                score += (m_power * mult)
                                
                            if score > highest_score:
                                highest_score = score
                                best_moves = [m]
                            elif score == highest_score:
                                best_moves.append(m)
                                
                    chosen_move = random.choice(best_moves) if best_moves else random.choice(available_moves)
                    npc_move_name = chosen_move['name']
                    chosen_move['pp'] -= 1
                    
                    # Fetch the complete 17-variable payload exactly as defined in the DB!
                    cursor.execute("""
                        SELECT name, type, power, accuracy, damage_class, pp, priority,
                            target, ailment, ailment_chance, stat_name, stat_change, stat_chance, 
                            status_type, status_chance, healing, drain
                        FROM base_moves WHERE name = ?
                    """, (npc_move_name,))
                    n_row = cursor.fetchone()
                    
                    if n_row:
                        # Map the payload perfectly!
                        n_move_stats = {
                            'name': n_row[0], 'type': n_row[1], 'power': n_row[2] or 0, 'accuracy': n_row[3] or 100, 
                            'class': n_row[4], 'pp': n_row[5], 'priority': n_row[6] or 0, 'target': n_row[7], 
                            'ailment': n_row[8], 'ailment_chance': n_row[9] or 0, 'stat_name': n_row[10], 
                            'stat_change': n_row[11] or 0, 'stat_chance': n_row[12] or 0,
                            'status_type': n_row[13], 'status_chance': n_row[14] or 0, 
                            'healing': n_row[15] or 0, 'drain': n_row[16] or 0
                        }
                    else:
                        n_move_stats = {'type': 'typeless', 'power': 0, 'accuracy': 100, 'class': 'status', 'target': 'defender', 'ailment': 'none', 'ailment_chance': 0, 'stat_name': 'none', 'stat_change': 0, 'stat_chance': 0, 'status_type': 'none', 'status_chance': 0, 'healing': 0, 'drain': 0, 'name': npc_move_name, 'priority': 0}
           
            # --- 3. PHYSICS EXECUTION ---
            can_attack = True
            status = n_active.get('status_condition', {})
            volatiles = n_active.get('volatile_statuses', {})
            
            if 'confusion' in volatiles:
                volatiles['confusion'] -= 1
                if volatiles['confusion'] <= 0:
                    del volatiles['confusion']
                    combat_log += f"💫 **{n_active['name'].capitalize()}** snapped out of its confusion!\n"
                else:
                    combat_log += f"💫 **{n_active['name'].capitalize()}** is confused...\n"
                    if random.randint(1, 100) <= 33: 
                        # Pass target_hazards and user_hazards!
                        dmg, msg, inf_status, stat_chgs, heal_amt = calculate_damage(
                                    n_active, p_active, n_move_stats, 
                                    weather=state.get('weather', {'type': 'none'})['type'], 
                                    target_hazards=state['player_hazards'], # NPC attacks the player's side
                                    user_hazards=state['npc_hazards']       # NPC's own side
                                )
                        n_active['current_hp'] = max(0, n_active['current_hp'] - dmg)
                        combat_log += f"💥 {msg} (Dealt **{dmg}** damage!)\n"
                        can_attack = False
                        
            if can_attack and status:
                s_name = status.get('name')
                if s_name == 'paralysis' and random.randint(1, 4) == 1:
                    combat_log += f"⚡ The rival's **{n_active['name'].capitalize()}** is fully paralyzed!\n"
                    can_attack = False
                elif s_name == 'sleep':
                    status['duration'] -= 1
                    if status['duration'] <= 0:
                        combat_log += f"☀️ The rival's **{n_active['name'].capitalize()}** woke up!\n"
                        n_active['status_condition'] = None
                    else:
                        combat_log += f"💤 The rival's **{n_active['name'].capitalize()}** is fast asleep.\n"
                        can_attack = False
                elif s_name == 'freeze':
                    if random.randint(1, 5) == 1:
                        combat_log += f"🔥 The rival's **{n_active['name'].capitalize()}** thawed out!\n"
                        n_active['status_condition'] = None
                    else:
                        combat_log += f"🧊 The rival's **{n_active['name'].capitalize()}** is frozen solid!\n"
                        can_attack = False

            if can_attack:
                combat_log += f"🔴 The rival's **{n_active['name'].capitalize()}** used `{npc_move_name.replace('-', ' ').title()}`!\n"
                
                # ==========================================
                # PATCH 2: PURE HAZARD INTERCEPTOR
                # ==========================================
                HAZARD_MOVES = ['stealth-rock', 'spikes', 'toxic-spikes', 'sticky-web']
                if npc_move_name in HAZARD_MOVES:
                    target_habitat = state['player_hazards']
                    if npc_move_name == 'stealth-rock':
                        if target_habitat['stealth-rock']: combat_log += "But it failed! The sharp rocks are already floating!\n"
                        else: target_habitat['stealth-rock'] = True; combat_log += "🪨 Pointed stones float in the air around your habitat!\n"
                    elif npc_move_name == 'spikes':
                        if target_habitat['spikes'] >= 3: combat_log += "But it failed! The habitat is fully covered in spikes!\n"
                        else: target_habitat['spikes'] += 1; combat_log += "🗡️ Spikes were scattered all around the feet of your team!\n"
                    elif npc_move_name == 'toxic-spikes':
                        if target_habitat['toxic-spikes'] >= 2: combat_log += "But it failed! The habitat is saturated with toxic spikes!\n"
                        else: target_habitat['toxic-spikes'] += 1; combat_log += "☣️ Poison spikes were scattered all around your habitat!\n"
                    elif npc_move_name == 'sticky-web':
                        if target_habitat['sticky-web']: combat_log += "But it failed! A sticky web already covers the habitat!\n"
                        else: target_habitat['sticky-web'] = True; combat_log += "🕸️ A sticky web spreads out across your habitat!\n"
                else:
                    # ==========================================
                    # PATCH 3: HYBRID HAZARD SIGNATURE UPDATE
                    # ==========================================
                    if random.randint(1, 100) > n_move_stats['accuracy']:
                        combat_log += "The attack missed!\n"
                    else:
                        
                        dmg, msg, inf_status, stat_chgs, heal_amt = calculate_damage(
                            n_active, p_active, n_move_stats, 
                            weather=state.get('weather', {'type': 'none'})['type'],
                            target_hazards=state['player_hazards'], # NPC attacks the player's side
                            user_hazards=state['npc_hazards']       # NPC's own side
                        )
                        
                        p_active['current_hp'] = max(0, p_active['current_hp'] - dmg)
                        if msg: combat_log += f"*{msg}*\n"
                        if dmg > 0: combat_log += f"You took **{dmg}** damage.\n"
                        
                        # Did the attack trigger the player's Sitrus Berry?
                        berry_log = check_consumables(p_active, "Your")
                        if berry_log: combat_log += berry_log


                        if heal_amt > 0:
                            n_active['current_hp'] = min(n_active.get('max_hp', 100), n_active['current_hp'] + heal_amt)
                            combat_log += f"💚 **{n_active['name'].capitalize()}** recovered health!\n"

            await self.process_turn_end(interaction, combat_log)

        except Exception as e:
            import traceback
            print(f"Retaliation Engine Error:")
            traceback.print_exc()
            await self.process_turn_end(interaction, combat_log)
        finally:
            conn.close()

    async def process_turn_end(self, interaction, combat_log):
        """The Central Engine: Handles NPC retaliation, hazards, faints, and UI rendering."""
        print("\n=== DEBUG: process_turn_end triggered ===")

        try:
            state = self.cog.active_battles[self.user_id]
            p_active = state['player_team'][state['active_player_index']]
            n_active = state['npc_team'][state['active_npc_index']]
            
            print("DEBUG 6: Entering Phase 3 (Weather & Pathogens)")

            # --- PHASE 3: POST-TURN ENVIRONMENTAL DAMAGE ---
            combat_log += "\n"
            
            # 1. Global Biome Effects (Weather Expiration & Chip Damage)
            weather = state.get('weather', {'type': 'none', 'duration': 0})
            if weather['type'] != 'none':
                weather['duration'] -= 1
                
                if weather['duration'] <= 0:
                    weather_clear_msgs = {
                        'rain': "The heavy rain stopped.",
                        'sun': "The harsh sunlight faded.",
                        'sand': "The sandstorm subsided.",
                        'hail': "The hail stopped."
                    }
                    combat_log += f"🌤️ {weather_clear_msgs.get(weather['type'], 'The weather cleared.')}\n"
                    weather['type'] = 'none'
                else:
                    # Apply Sandstorm/Hail chip damage
                    if weather['type'] in ['sand', 'hail']:
                        for combatant, owner_str in [(p_active, "Your"), (n_active, "The rival's")]:
                            if combatant['current_hp'] > 0:
                                is_immune = False
                                c_types = combatant.get('types', [])
                                
                                # Check biological immunities
                                if weather['type'] == 'sand' and any(t in ['rock', 'ground', 'steel'] for t in c_types):
                                    is_immune = True
                                if weather['type'] == 'hail' and 'ice' in c_types:
                                    is_immune = True
                                    
                                if not is_immune:
                                    chip_dmg = max(1, math.floor(combatant['max_hp'] / 16))
                                    combatant['current_hp'] = max(0, combatant['current_hp'] - chip_dmg)
                                    icon = "🌪️" if weather['type'] == 'sand' else "❄️"
                                    combat_log += f"{icon} {owner_str} **{combatant['name'].capitalize()}** is buffeted by the {weather['type']}! (-{chip_dmg} HP)\n"

                    # Dry Skin Atmospheric Reactions
                    for combatant, owner_str in [(p_active, "Your"), (n_active, "The rival's")]: # Remove the '_' in PvE!
                        if combatant['current_hp'] > 0 and combatant.get('ability') == 'dry-skin':
                            weather_type = state['weather']['type']
                            
                            # Takes 1/8th damage in Sunlight
                            if weather_type in ['sun', 'extremely-harsh-sunlight']:
                                dmg = max(1, math.floor(combatant['max_hp'] / 8))
                                combatant['current_hp'] = max(0, combatant['current_hp'] - dmg)
                                combat_log += f"☀️ {owner_str.strip()} **{combatant['name'].capitalize()}** was hurt by the harsh sunlight due to its Dry Skin! (-{dmg} HP)\n"
                                
                            # Restores 1/8th health in Rain
                            elif weather_type in ['rain', 'heavy-rain']:
                                if combatant['current_hp'] < combatant.get('max_hp', 100):
                                    heal = max(1, math.floor(combatant['max_hp'] / 8))
                                    combatant['current_hp'] = min(combatant.get('max_hp', 100), combatant['current_hp'] + heal)
                                    combat_log += f"🌧️ {owner_str.strip()} **{combatant['name'].capitalize()}** restored HP in the rain due to its Dry Skin! (+{heal} HP)\n"

            # ==========================================
            # 1.5 PERSISTENT HELD ITEMS (Status Orbs)
            # ==========================================
            for combatant, owner_str in [(p_active, "Your"), (n_active, "The rival's")]: # Use just 'combatant, owner_str' in PvE!
                if combatant['current_hp'] > 0 and not combatant.get('status_condition'):
                    orb_item = (combatant.get('held_item') or "").lower().replace(' ', '-')
                    
                    if orb_item == 'flame-orb' and 'fire' not in combatant.get('types', []):
                        combatant['status_condition'] = {'name': 'burn', 'duration': -1}
                        combat_log += f"🔥 {owner_str} **{combatant['name'].capitalize()}** was burned by its Flame Orb!\n"
                        
                    elif orb_item == 'toxic-orb' and 'poison' not in combatant.get('types', []) and 'steel' not in combatant.get('types', []):
                        combatant['status_condition'] = {'name': 'poison', 'duration': -1}
                        combat_log += f"☣️ {owner_str} **{combatant['name'].capitalize()}** was badly poisoned by its Toxic Orb!\n"

            # 2. Pathogen Damage (Burn/Poison)
            for combatant, owner_str in [(p_active, "Your"), (n_active, "The rival's")]:
                ability = (combatant.get('ability') or "").lower().replace(' ', '-')
                if combatant['current_hp'] > 0 and combatant.get('status_condition'):
                    status = combatant['status_condition']['name']
                    if status == 'burn':
                        burn_dmg = max(1, math.floor(combatant['max_hp'] / 16))
                        combatant['current_hp'] = max(0, combatant['current_hp'] - burn_dmg)
                        combat_log += f"🔥 {owner_str} **{combatant['name'].capitalize()}** suffered a burn! (-{burn_dmg} HP)\n"
                    elif status == 'poison':
                        # If they have Poison Heal, skip the damage entirely!
                        if ability == 'poison-heal':
                            continue
                        psn_dmg = max(1, math.floor(combatant['max_hp'] / 8))
                        combatant['current_hp'] = max(0, combatant['current_hp'] - psn_dmg)
                        combat_log += f"☣️ {owner_str} **{combatant['name'].capitalize()}** was hurt by the poison! (-{psn_dmg} HP)\n"

            # ==========================================
            # 2.5 Biological Sustenance
            # ==========================================
            for combatant, owner_str in [(p_active, "Your"), (n_active, "The rival's")]:
                if combatant['current_hp'] > 0:
                    item = (combatant.get('held_item') or "").lower().replace(' ', '-')
                    
                    if item == 'leftovers':
                        heal_qty = max(1, math.floor(combatant['max_hp'] / 16))
                        combatant['current_hp'] = min(combatant['max_hp'], combatant['current_hp'] + heal_qty)
                        combat_log += f"🍎 **{owner_str} {combatant['name'].capitalize()}** restored a little HP using its Leftovers! (+{heal_qty})\n"
                        
                    elif item == 'black-sludge':
                        if 'poison' in combatant.get('types', []):
                            heal_qty = max(1, math.floor(combatant['max_hp'] / 16))
                            combatant['current_hp'] = min(combatant['max_hp'], combatant['current_hp'] + heal_qty)
                            combat_log += f"🧪 **{owner_str} {combatant['name'].capitalize()}** restored HP via its Black Sludge! (+{heal_qty})\n"
                        else:
                            sludge_dmg = max(1, math.floor(combatant['max_hp'] / 8))
                            combatant['current_hp'] = max(0, combatant['current_hp'] - sludge_dmg)
                            combat_log += f"🧪 **{owner_str} {combatant['name'].capitalize()}** is buffeted by its Black Sludge! (-{sludge_dmg})\n"
            # ==========================================

            # --- TRIPWIRE 2: Check the biological hosts! ---
            print(f"DEBUG LEECH: Player Volatiles: {p_active.get('volatile_statuses')}")
            print(f"DEBUG LEECH: NPC Volatiles: {n_active.get('volatile_statuses')}")
            # ---

            # ==========================================
            # 2.8 BIOLOGICAL END-OF-TURN HOOKS 
            # ==========================================
            for combatant, owner_str in [(p_active, "Your"), (n_active, "The rival's")]: 
                if combatant['current_hp'] > 0:
                    ability = (combatant.get('ability') or "").lower().replace(' ', '-')
                    eot_trait = BIOLOGICAL_TRAITS.get('end_of_turn', {}).get(ability)
                    
                    if eot_trait:
                        ability_name = ability.replace('-', ' ').title()
                        
                        # 1. Adrenaline Escalation (Speed Boost)
                        if eot_trait['type'] == 'stat':
                            stat_target = eot_trait['stat']
                            
                            if 'stat_stages' not in combatant:
                                combatant['stat_stages'] = {'attack': 0, 'defense': 0, 'sp_atk': 0, 'sp_def': 0, 'speed': 0}
                            
                            current_stage = combatant['stat_stages'].get(stat_target, 0)
                            if current_stage < 6:
                                combatant['stat_stages'][stat_target] = min(6, current_stage + eot_trait['value'])
                                combat_log += f"💨 {owner_str.strip()} **{combatant['name'].capitalize()}**'s {ability_name} increased its {stat_target.capitalize()}!\n"

                        # 2. Cellular Shedding (Shed Skin)
                        elif eot_trait['type'] == 'cure' and combatant.get('status_condition'):
                            if random.randint(1, 100) <= eot_trait['chance']:
                                cured_status = combatant['status_condition']['name']
                                combatant['status_condition'] = None
                                combat_log += f"✨ {owner_str.strip()} **{combatant['name'].capitalize()}** cured its {cured_status} using {ability_name}!\n"

                        # 3. Environmental Sustenance (Rain Dish, Ice Body)
                        elif eot_trait['type'] == 'weather_heal':
                            current_weather = state.get('weather', {}).get('type', 'none')
                            
                            if current_weather in eot_trait['weather'] and combatant['current_hp'] < combatant.get('max_hp', 100):
                                heal = max(1, math.floor(combatant.get('max_hp', 100) / eot_trait['denominator']))
                                combatant['current_hp'] = min(combatant.get('max_hp', 100), combatant['current_hp'] + heal)
                                combat_log += f"💚 {owner_str.strip()} **{combatant['name'].capitalize()}** restored HP using {ability_name}!\n"

                        # Pathogen Symbiosis (Poison Heal)
                        elif eot_trait['type'] == 'status_heal':
                            target_status = eot_trait['status']
                            current_status = combatant.get('status_condition', {})
                            
                            # If they have the matching status condition, heal them!
                            if current_status and current_status.get('name') == target_status and combatant['current_hp'] < combatant.get('max_hp', 100):
                                heal = max(1, math.floor(combatant.get('max_hp', 100) / eot_trait['denominator']))
                                combatant['current_hp'] = min(combatant.get('max_hp', 100), combatant['current_hp'] + heal)
                                combat_log += f"🍄 {owner_str.strip()} **{combatant['name'].capitalize()}** restored HP using its {ability_name}!\n"

            # 3. Parasitic Drain (Leech Seed)
            for combatant, opponent, owner_str in [(p_active, n_active, "Your"), (n_active, p_active, "The rival's")]:
                if combatant['current_hp'] > 0 and 'leech-seed' in combatant.get('volatile_statuses', {}):
                    # Calculate 1/8th of max HP, but don't drain more HP than they actually have left!
                    drain_dmg = max(1, math.floor(combatant.get('max_hp', 100) / 8))
                    drain_dmg = min(drain_dmg, combatant['current_hp']) 
                    
                    combatant['current_hp'] -= drain_dmg
                    
                    # Transfer the biomass to the active opponent!
                    if opponent['current_hp'] > 0:
                        opponent['current_hp'] = min(opponent.get('max_hp', 100), opponent['current_hp'] + drain_dmg)
                        
                    combat_log += f"🌱 {owner_str} **{combatant['name'].capitalize()}** had its health sapped by Leech Seed!\n"

                if combatant['current_hp'] > 0 and 'perish-song' in combatant.get('volatile_statuses', {}):
                    # Tick the timer down
                    combatant['volatile_statuses']['perish-song'] -= 1
                    count = combatant['volatile_statuses']['perish-song']
                    
                    if count <= 0:
                        combatant['current_hp'] = 0
                        combat_log += f"🎵 **{combatant['name'].capitalize()}**'s Perish count fell to 0 and it fainted!\n"
                    else:
                        combat_log += f"🎵 **{combatant['name'].capitalize()}**'s Perish count fell to {count}.\n"

            # 4. G-Max Ecological Disasters (Wildfire, Vine Lash, Cannonade, Volcalith)
            for combatant, hazards, owner_str in [
                (p_active, state['player_hazards'], "Your"),
                (n_active, state['npc_hazards'], "The rival's")
            ]:
                if combatant['current_hp'] > 0:
                    c_types = combatant.get('types', [])
                    
                    # Map the disaster to its immune typing and chat icon
                    disaster_map = {
                        'wildfire': ('fire', "🔥"),
                        'vine lash': ('grass', "🌿"),
                        'cannonade': ('water', "🌊"),
                        'volcalith': ('rock', "🪨")
                    }
                    
                    for disaster, (immune_type, icon) in disaster_map.items():
                        # If the hazard exists and has turns remaining...
                        if hazards.get(disaster, 0) > 0:
                            # 1. Biological Filter: Apply damage only if they aren't immune
                            if immune_type not in c_types:
                                dot_dmg = max(1, math.floor(combatant['max_hp'] / 6))
                                combatant['current_hp'] = max(0, combatant['current_hp'] - dot_dmg)
                                combat_log += f"{icon} **{owner_str} {combatant['name'].capitalize()}** is trapped in the {disaster}! (-{dot_dmg} HP)\n"
                            
                            # 2. Thermodynamic Decay: Decrement the timer for this side of the field
                            hazards[disaster] -= 1
                            if hazards[disaster] <= 0:
                                del hazards[disaster] # Clear it from memory when the 4 turns expire!
                                clear_msgs = {
                                    'wildfire': "The raging wildfire died down.",
                                    'vine lash': "The invasive vines withered away.",
                                    'cannonade': "The water vortex dispersed.",
                                    'volcalith': "The floating rocks vanished."
                                }
                                combat_log += f"✨ {clear_msgs[disaster]}\n"

            print("DEBUG 7: Entering Phase 3.5 (Adaptation Expiration)")

            # --- PHASE 3.5: BIOLOGICAL DEGRADATION (G-MAX / D-MAX EXPIRATION) ---
            if state['adaptation']['active'] and state['adaptation']['type'] in ['gmax', 'dynamax']:
                state['adaptation']['turns'] -= 1
                
                if state['adaptation']['turns'] <= 0:
                    # The energy has expired! Restore the backup.
                    backup = state['adaptation']['backup']
                    
                    # Calculate the percentage of HP they had remaining so we scale it down fairly
                    hp_percent = p_active['current_hp'] / p_active['max_hp']
                    
                    p_active['name'] = backup['name']
                    p_active['pokedex_id'] = backup['pokedex_id']
                    p_active['max_hp'] = backup['max_hp']
                    p_active['stats'] = backup['stats']
                    p_active['types'] = backup['types']
                    
                    # Scale the current HP down to the normal bounds
                    p_active['current_hp'] = max(1, math.floor(p_active['max_hp'] * hp_percent))
                    
                    state['adaptation']['active'] = False
                    combat_log += f"\n🔴 The Galar particles dispersed! **{p_active['name'].capitalize()}** returned to its normal form.\n"

            # --- PHASE 3.8: KINETIC STUN & SHIELD CLEANUP ---
            # Wipe temporary flinch and protection flags before the next round begins
            
            # 1. Clear Flinch Flags
            if p_active.get('volatile_statuses', {}).get('flinch'):
                p_active['volatile_statuses']['flinch'] = False
            if n_active.get('volatile_statuses', {}).get('flinch'):
                n_active['volatile_statuses']['flinch'] = False
                
            # 2. Clear Protect Flags
            if p_active.get('volatile_statuses', {}).get('protected'):
                p_active['volatile_statuses']['protected'] = False
            if n_active.get('volatile_statuses', {}).get('protected'):
                n_active['volatile_statuses']['protected'] = False

            print("DEBUG 8: Entering Phase 4 (Survival & Swap Checks)")

            # Final End-of-Turn Berry Sweep
            for combatant, owner_str in [(p_active, "Your"), (n_active, "The rival's")]:
                berry_log = check_consumables(combatant, owner_str)
                if berry_log: combat_log += berry_log

            # --- PHASE 4: SURVIVAL & SWAP CHECK ---
            if n_active['current_hp'] <= 0:
                combat_log += f"\n💀 The rival's **{n_active['name'].capitalize()}** is unable to continue!"
                
                # ==========================================
                # TACTICAL AI: OPTIMAL REPLACEMENT HEURISTIC
                # ==========================================
                best_score = -1.0
                next_npc_idx = None
                
                for i, benched_specimen in enumerate(state['npc_team']):
                    if benched_specimen['current_hp'] > 0:
                        if next_npc_idx is None:
                            next_npc_idx = i # Set a fallback just in case
                            
                        score = 1.0
                        p_types = p_active.get('types', [])
                        b_types = benched_specimen.get('types', [])
                        
                        # 1. Offensive Threat: Can this benched specimen hit the player super-effectively?
                        max_offense = 0.0
                        for b_type in b_types:
                            off_mult = 1.0
                            for p_type in p_types:
                                off_mult *= TYPE_CHART.get(b_type, {}).get(p_type, 1.0)
                            if off_mult > max_offense:
                                max_offense = off_mult
                        score *= max_offense # A 2.0x or 4.0x multiplier greatly increases the score
                        
                        # 2. Defensive Integrity: Can this benched specimen resist the player's attacks?
                        max_defense = 0.0
                        for p_type in p_types:
                            def_mult = 1.0
                            for b_type in b_types:
                                def_mult *= TYPE_CHART.get(p_type, {}).get(b_type, 1.0)
                            if def_mult > max_defense:
                                max_defense = def_mult
                        
                        # Adjust the score based on their defensive vulnerability
                        if max_defense == 0:
                            score *= 4.0  # Biological immunity! High priority swap.
                        elif max_defense < 1.0:
                            score *= 2.0  # Resistance! Good defensive pivot.
                        elif max_defense > 1.0:
                            score *= 0.25 # Fatal weakness. Avoid sending this out if possible!
                            
                        # Lock in the highest scoring specimen
                        if score > best_score:
                            best_score = score
                            next_npc_idx = i
                # ==========================================
                
                if next_npc_idx is not None:
                    state['active_npc_index'] = next_npc_idx
                    n_active = state['npc_team'][next_npc_idx]
                    combat_log += f"\n\nThe rival deployed **{n_active['name'].capitalize()}**!"

                    # --- TRIPWIRE 1: Check the variables! ---
                    print(f"DEBUG SWAP 1: Attempting to spawn Forced SwapMenu.")

                    # ==========================================
                    # HAZARD TRIGGER: NPC SWITCH-IN
                    # ==========================================
                    hazard_log = apply_entry_hazards(n_active, state['npc_hazards'], TYPE_CHART, "The rival's")
                    if hazard_log:
                        combat_log += hazard_log
                        
                        # IMPORTANT: If the hazard instantly KO'd the new Pokémon, we need to end the turn here
                        # and let the loop naturally catch the faint on the NEXT turn!
                        if n_active['current_hp'] <= 0:
                            combat_log += f"💀 The rival's **{n_active['name'].capitalize()}** couldn't survive the treacherous habitat!\n"


                    # ==========================================
                    # NPC MID-BATTLE ENTRY HOOK
                    # ==========================================
                    combat_log = trigger_single_entry_ability(n_active, p_active, "The rival's", state, combat_log)
                else:

                    # ==========================================
                    # THE WARDEN VICTORY INTERCEPTOR
                    # ==========================================
                    if state.get('is_warden'):
                        conn = sqlite3.connect(DB_FILE)
                        cursor = conn.cursor()
                        
                        biome = state.get('warden_biome')
                        # Ensure WARDEN_ROSTER is accessible in this file!
                        w_data = WARDEN_ROSTER[biome]
                        next_biome = w_data['biome_unlocked']
                        r_item = w_data['reward_item']
                        r_qty = w_data['reward_qty']
                        
                        # 1. Upgrade the Researcher's Visa
                        cursor.execute("SELECT unlocked_visas FROM users WHERE user_id = ?", (self.user_id,))
                        user_data = cursor.fetchone()
                        current_visas = user_data[0] if user_data and user_data[0] else "canopy"
                        
                        # --- THE ANTI-FARMING LOGIC ---
                        if next_biome not in current_visas.split(','):
                            # FIRST TIME CLEAR!
                            new_visas = f"{current_visas},{next_biome}"
                            cursor.execute("UPDATE users SET unlocked_visas = ? WHERE user_id = ?", (new_visas, self.user_id))
                            
                            cursor.execute("""
                                INSERT INTO user_inventory (user_id, item_name, quantity) 
                                VALUES (?, ?, ?) 
                                ON CONFLICT(user_id, item_name) 
                                DO UPDATE SET quantity = quantity + ?
                            """, (self.user_id, r_item, r_qty, r_qty))
                            
                            rewards_log = f"\n\n🎖️ **WARDEN DEFEATED!** You have proven your ecological mastery against the {w_data['title']}!\n"
                            rewards_log += f"🛂 **Clearance Granted:** You secured the Visa for the **{next_biome.title()}** sector!\n"
                            rewards_log += f"🎁 **First-Clear Bonus:** You received **{r_qty}x {r_item.replace('-', ' ').title()}**!"
                        else:
                            # REPEAT CLEAR (SPARRING)
                            cursor.execute("UPDATE users SET eco_tokens = eco_tokens + 500 WHERE user_id = ?", (self.user_id,))
                            
                            rewards_log = f"\n\n🎖️ **WARDEN DEFEATED!** You proved your continued mastery against the {w_data['title']}!\n"
                            rewards_log += "💰 You received **500 Eco Tokens** for the sparring session.\n"
                            rewards_log += "*(Note: Sector Visas and unique equipment are only granted on the first clear.)*"
                        # ------------------------------
                        
                        conn.commit()
                        conn.close()
                        
                        # 3. Clean up and print the Victory UI!
                        del self.cog.active_battles[self.user_id]
                        embed = discord.Embed(title="🛡️ Sector Secured!", description=combat_log + rewards_log, color=discord.Color.purple())
                        return await interaction.edit_original_response(embed=embed, view=None, attachments=[])
                    
                    # ==========================================
                    # THE ECOLOGICAL REWARDS ENGINE
                    # ==========================================
                    # 1. Calculate Research Funding (Eco Tokens)
                    # Let's say you get 50 tokens per NPC Pokémon defeated, plus a base 100
                    tokens_earned = 100 + (len(state['npc_team']) * 50)
                    
                    # 2. Calculate Biomass/Experience Accumulation
                    # A standard formula: (NPC Level * 15) per Pokémon
                    total_exp_yield = sum([p.get('level', 50) * 15 for p in state['npc_team']])
                    
                    # 3. Distribute EXP (Modern Exp Share: everyone gets a cut!)
                    surviving_team = [p for p in state['player_team'] if p['current_hp'] > 0]
                    exp_per_specimen = math.floor(total_exp_yield / max(1, len(surviving_team)))
                    
                    rewards_log: str = f"\n\n💰 You earned **{tokens_earned} Eco Tokens** for your research!\n"
                    rewards_log += f"📈 Surviving team members gained **{exp_per_specimen} EXP**!\n\n"
                    
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    
                    # 4. Update the User's Bank Account
                    # (Assuming your users table has an eco_tokens column)
                    cursor.execute("UPDATE users SET eco_tokens = eco_tokens + ? WHERE user_id = ?", (tokens_earned, self.user_id))
                    
                    # 5. Process Level Ups for the Team
                    for p in surviving_team:
                        p['experience'] = p.get('experience', 0) + exp_per_specimen
                        
                        threshold = p.get('level', 5) * 100
                        
                        if p['experience'] >= threshold and p.get('level', 5) < 100:
                            p['level'] += 1
                            p['experience'] -= threshold 
                            rewards_log += f"🎉 **{p['name'].capitalize()}** grew to Level {p['level']}!\n"
                            
                            # --- THE EVOLUTION TRIGGER ---
                            if 'instance_id' in p:
                                # We pass the cursor so the helper function can use the existing database connection
                                evo_msg = await self.check_for_evolution(cursor, conn, self.user_id, p, combat_log)
                                if evo_msg:
                                    rewards_log += evo_msg
                            # -----------------------------
                    # Save the entire team's updated state (including consumed items!)
                    for p in state['player_team']:
                        if 'instance_id' in p:
                            cursor.execute("""
                                UPDATE caught_pokemon 
                                SET level = ?, experience = ?, held_item = ? 
                                WHERE instance_id = ?
                            """, (p['level'], p['experience'], p.get('held_item', 'none'), p['instance_id']))

                    # ==========================================
                    # DIRECTIVE TRACKER: INVASIVE CULLING
                    # ==========================================
                    # Grab the elemental types of the defeated NPC
                    defeated_types = n_active.get('types', [])
                    
                    for p_type in defeated_types:
                        # 1. Increment the progress for any active directives matching this type
                        cursor.execute("""
                            UPDATE field_directives
                            SET current_progress = current_progress + 1
                            WHERE user_id = ? AND objective_type = 'cull_type' AND target_variable = ? AND is_completed = 0
                        """, (self.user_id, p_type))

                        # 2. Check if that increment just maxed out the progress bar!
                        cursor.execute("""
                            SELECT required_amount, current_progress 
                            FROM field_directives
                            WHERE user_id = ? AND objective_type = 'cull_type' AND target_variable = ? AND is_completed = 0
                        """, (self.user_id, p_type))
                        
                        row = cursor.fetchone()
                        if row and row[1] == row[0]: # Progress exactly matches required amount
                            rewards_log += f"\n📡 **Directive Complete:** You successfully culled the invasive {p_type.capitalize()}-type population! Use `!claim` to receive your funding."
                    # ==========================================

                        # Update the database regardless of level up
                        if 'instance_id' in p:
                            cursor.execute("""
                                UPDATE caught_pokemon 
                                SET level = ?, experience = ? 
                                WHERE instance_id = ?
                            """, (p['level'], p['experience'], p['instance_id']))

                    # ==========================================
                    # GEOLOGICAL ANOMALY: METEOR SHOWER
                    # ==========================================
                    # 5% chance for a meteorite to strike the ecosystem after a victory
                    if random.random() <= 0.05: # 100% for testing
                        cursor.execute("""
                            INSERT INTO user_inventory (user_id, item_name, quantity) 
                            VALUES (?, 'raw-keystone', 1) 
                            ON CONFLICT(user_id, item_name) 
                            DO UPDATE SET quantity = quantity + 1
                        """, (self.user_id,))
                        
                        rewards_log += "\n🌠 **ANOMALY DETECTED:** A localized meteor shower occurred during the skirmish! You recovered a `Raw Keystone` from the crater."

                    # ==========================================
                    # BIOLOGICAL ANOMALY: MYCELIAL BLOOM
                    # ==========================================
                    # 15% chance for a rare fungal spore to drop after combat
                    if random.random() <= 0.15: 
                        cursor.execute("""
                            INSERT INTO user_inventory (user_id, item_name, quantity) 
                            VALUES (?, 'memory-spore', 1) 
                            ON CONFLICT(user_id, item_name) 
                            DO UPDATE SET quantity = quantity + 1
                        """, (self.user_id,))
                        
                        rewards_log += "\n🍄 **ANOMALY DETECTED:** The combat disturbed a localized mycelial network! You recovered a `Memory Spore`."
                    # ==========================================

                    # ==========================================
                    # FIELD DATA RECOVERY: ENCRYPTED NOTES
                    # ==========================================
                    # 10% chance to find abandoned research data after a skirmish
                    if random.random() <= 0.10: # 100% for testing
                        cursor.execute("""
                            INSERT INTO user_inventory (user_id, item_name, quantity) 
                            VALUES (?, 'encrypted-field-notes', 1) 
                            ON CONFLICT(user_id, item_name) 
                            DO UPDATE SET quantity = quantity + 1
                        """, (self.user_id,))
                        
                        rewards_log += "\n📝 **DATA RECOVERED:** You found some `Encrypted Field Notes` dropped in the brush! Run `!analyze notes` to decode them."
                    # ==========================================

                    # ==========================================
                    # RADIANT ANOMALY: SOLAR FLARE
                    # ==========================================
                    # 7% chance for a burst of radiant energy to crystallize local minerals
                    if random.random() <= 0.07: # Change to 1.0 temporarily if you want to test it!
                        cursor.execute("""
                            INSERT INTO user_inventory (user_id, item_name, quantity) 
                            VALUES (?, 'sparkling-stone', 1) 
                            ON CONFLICT(user_id, item_name) 
                            DO UPDATE SET quantity = quantity + 1
                        """, (self.user_id,))
                        
                        rewards_log += "\n☀️ **ANOMALY DETECTED:** A sudden burst of radiant energy crystallized the local soil! You extracted a `Sparkling Stone`."
                    # ==========================================

                    # ==========================================
                    # ATMOSPHERIC ANOMALY: ENERGY SMOG
                    # ==========================================
                    # 8% chance for reactive precipitation to occur
                    if random.random() <= 0.08: #100% for testing
                        cursor.execute("""
                            INSERT INTO user_inventory (user_id, item_name, quantity) 
                            VALUES (?, 'wishing-fragment', 1) 
                            ON CONFLICT(user_id, item_name) 
                            DO UPDATE SET quantity = quantity + 1
                        """, (self.user_id,))
                        
                        rewards_log += "\n🌫️ **ANOMALY DETECTED:** A dense cluster of reactive energy passed over the area! You collected a volatile `Wishing Fragment` from the fallout."
                    # ==========================================

                    conn.commit()
                    conn.close()

                    # 6. Shut down the engine and print the victory screen!
                    del self.cog.active_battles[self.user_id]
                    
                    embed = discord.Embed(title="🏆 Field Duel Victorious!", description=combat_log + rewards_log, color=discord.Color.gold())
                    return await interaction.edit_original_response(embed=embed, view=None, attachments=[])

            # --- PLAYER SURVIVAL CHECK ---
            if p_active['current_hp'] <= 0:
                combat_log += f"\n⚠️ Your **{p_active['name'].capitalize()}** requires immediate medical attention!"
                
                has_survivors = any(p['current_hp'] > 0 for p in state['player_team'])
                if has_survivors:
                    combat_log += "\n**Who will you send out next?**"
                    
                    # We pass `forced=True` to hide the cancel button!
                    swap_view = SwapMenu(self.cog, self.user_id, self.ctx, self, forced=True)
                    
                    embed = discord.Embed(title="⚠️ Specimen Down!", description=combat_log, color=discord.Color.orange())
                    return await interaction.edit_original_response(embed=embed, view=swap_view, attachments=[])
                else:
                    del self.cog.active_battles[self.user_id]
                    embed = discord.Embed(title="💥 Field Duel Lost", description=combat_log, color=discord.Color.dark_red())
                    return await interaction.edit_original_response(embed=embed, view=None, attachments=[])

            print("DEBUG 9: Entering Phase 5 (UI Render)")

            # --- PHASE 5: UI RENDER ---
            state['turn_number'] += 1
            
            embed = discord.Embed(title=f"⚔️ Ecological Field Duel", color=discord.Color.blue())
            embed.description = combat_log
            
            # --- Generate Roster Indicators ---
            p_roster = "".join(["🔴" if p['current_hp'] > 0 else "⚫" for p in state['player_team']])
            n_roster = "".join(["🔴" if p['current_hp'] > 0 else "⚫" for p in state['npc_team']])
            
            p_status_icon = f" [{p_active['status_condition']['name'].upper()}]" if p_active.get('status_condition') else ""
            n_status_icon = f" [{n_active['status_condition']['name'].upper()}]" if n_active.get('status_condition') else ""
            
            embed.add_field(name=f"🟢 Your {p_active['name'].capitalize()}{p_status_icon}", value=f"Team: {p_roster}\n*See visual biometrics below*", inline=True)
            embed.add_field(name=f"🔴 Rival {n_active['name'].capitalize()}{n_status_icon}", value=f"Team: {n_roster}\n*See visual biometrics below*", inline=True)

            print("DEBUG 10: Generating Battle Scene and dispatching to Discord")

            # ==========================================
            # PASS HUD OVERLAYS TO VISUAL ENGINE
            # ==========================================
            current_weather = state.get('weather', {'type': 'none'})['type']
            
            battle_file = await self.generate_battle_scene(
                p_active['pokedex_id'], n_active['pokedex_id'], 
                p_active['current_hp'], p_active['max_hp'], 
                n_active['current_hp'], n_active['max_hp'],
                player_shiny=p_active.get('is_shiny', False),
                npc_shiny=n_active.get('is_shiny', False),
                
                # --- NEW OVERLAYS ---
                weather=current_weather,
                p_status=p_active.get('status_condition'),
                n_status=n_active.get('status_condition'),
                p_hazards=state.get('player_hazards'),
                n_hazards=state.get('npc_hazards')
            )
            # ==========================================
            self.refresh_buttons()
            # Dynamically grab the new randomized filename!
            # If the image generated successfully, overwrite the old attachments with the new one!
            if battle_file:
                embed.set_image(url=f"attachment://{battle_file.filename}")
                await interaction.edit_original_response(embed=embed, view=self, attachments=[battle_file])
            else:
                await interaction.edit_original_response(embed=embed, view=self, attachments=[])
            print("=== DEBUG: process_turn_end COMPLETE ===")
        
        except Exception as e:
            print("\n🚨 CRITICAL CRASH IN PROCESS_TURN_END 🚨")
            traceback.print_exc()

            self.active_battles.pop(self.user_id, None)
            
            await state['message_obj'].channel.send("⚠️ A critical engine failure occurred during the turn calculation. You have been released from the battle.")

            # We use followup.send here because edit_original_response might have failed!
            await interaction.followup.send("A critical engine failure occurred during the turn rendering.", ephemeral=True)

class Combat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # This dictionary is now isolated to the Combat Cog
        self.active_battles = {}
        
    def check_and_consume_energy(self, user_id: str, cost: int = 20) -> tuple[bool, str]:
        """
        Lazy-evaluates stamina regeneration and attempts to consume the required cost.
        Returns (Success_Boolean, Status_Message).
        """
        MAX_ENERGY = 100
        REGEN_PER_HOUR = 10
        SECONDS_IN_HOUR = 3600
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT current_energy, last_energy_tick FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            
            # If they aren't in the DB, the @has_started check should catch them, but just in case:
            if not row:
                return False, "⚠️ Unregistered Personnel: Run `!start` first."
                
            current_energy, last_tick = row
            now = int(time.time())
            
            # 1. CALCULATE LAZY REGENERATION
            if current_energy < MAX_ENERGY:
                seconds_passed = now - last_tick
                hours_passed = seconds_passed // SECONDS_IN_HOUR
                
                if hours_passed > 0:
                    energy_gained = int(hours_passed * REGEN_PER_HOUR)
                    current_energy = min(MAX_ENERGY, current_energy + energy_gained)
                    
                    # We only fast-forward the tick by the exact hours consumed 
                    # so they don't lose "partial" hours of progress!
                    last_tick += (hours_passed * SECONDS_IN_HOUR)
                    
                    # If they capped out, reset the tick to now
                    if current_energy == MAX_ENERGY:
                        last_tick = now

            # 2. CHECK FOR SUFFICIENT FUNDS
            if current_energy < cost:
                # Calculate time until next tick
                next_tick_in = SECONDS_IN_HOUR - (now - last_tick)
                mins, secs = divmod(next_tick_in, 60)
                return False, f"🔋 **Ecosystem Fatigue:** Your team is exhausted. You have **{current_energy}/{MAX_ENERGY} Energy** (Need {cost}).\n*Next energy point regenerates in {mins}m {secs}s.*"
                
            # 3. CONSUME ENERGY AND UPDATE DB
            current_energy -= cost
            # If they were at max energy, the timer for the next regen starts exactly right now!
            if current_energy + cost == MAX_ENERGY:
                last_tick = now
                
            cursor.execute("""
                UPDATE users 
                SET current_energy = ?, last_energy_tick = ? 
                WHERE user_id = ?
            """, (current_energy, last_tick, user_id))
            conn.commit()
            
            return True, f"🔋 Spent **{cost} Energy** (Remaining: {current_energy}/{MAX_ENERGY})"
            
        except Exception as e:
            print(f"Energy System Error: {e}")
            return False, "❌ A critical error occurred while processing your stamina."
        finally:
            conn.close()

    def build_npc_combatant(self, cursor, pokedex_id, name, level, moves, types):
        """Generates a wild ecological variant for the rival team."""
        base_stats = fetch_base_stats(cursor, pokedex_id)
        
        ivs = {stat: random.randint(0, 31) for stat in ['hp', 'attack', 'defense', 'sp_atk', 'sp_def', 'speed']}
        evs = {stat: 0 for stat in ['hp', 'attack', 'defense', 'sp_atk', 'sp_def', 'speed']}
        nature = random.choice(list(NATURE_MULTIPLIERS.keys()))
        
        final_stats = calculate_stats(base_stats, ivs, evs, level, nature)
        
        return {
            'pokedex_id': pokedex_id, 'name': name, 'level': level, 'types': types,
            'max_hp': final_stats['hp'], 'current_hp': final_stats['hp'],
            'stats': final_stats, 'moves': moves, 'status_condition': None
        }
    
    @commands.command(name="tutor", aliases=["relearn", "teach_move"])
    @checks.has_started()
    @checks.is_authorized()
    @checks.is_not_in_trade()
    @checks.is_not_in_combat()
    async def tutor_move(self, ctx, instance_id: str, *, move_name: str):
        """Stimulates dormant genetic pathways to teach a specimen a new move."""
        user_id = str(ctx.author.id)
        requested_move = move_name.lower().replace(" ", "-")

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        try:
            # ==========================================
            # 1. SPECIMEN RETRIEVAL (Partial Tag Matching)
            # ==========================================
            # We append the % wildcard to the user's input
            search_tag = f"{instance_id}%"
            
            cursor.execute("""
                SELECT cp.instance_id, cp.pokedex_id, s.name, cp.level, 
                       cp.move_1, cp.move_2, cp.move_3, cp.move_4
                FROM caught_pokemon cp
                JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                WHERE cp.user_id = ? AND cp.instance_id LIKE ?
            """, (user_id, search_tag))
            
            # Fetch ALL matching rows
            matching_specimens = cursor.fetchall()
            
            if len(matching_specimens) == 0:
                return await ctx.send(f"⚠️ **Asset Not Found:** You do not own a specimen with a tag starting with `{instance_id}`.")
                
            if len(matching_specimens) > 1:
                # If the prefix is too short and matches multiple IDs, force them to be specific!
                matched_tags = ", ".join([f"`{row[0][:6]}` ({row[2].capitalize()})" for row in matching_specimens])
                return await ctx.send(f"🔍 **Ambiguous Tag:** `{instance_id}` matches multiple specimens in your PC:\n{matched_tags}\n\nPlease provide a few more characters of the ID to confirm the target.")
                
            # If exactly ONE match is found, we safely unpack it
            specimen_data = matching_specimens[0]
            
            # We overwrite the user's short input with the actual full database ID!
            # This ensures that when we update the database later, we hit the exact row.
            actual_instance_id = specimen_data[0] 
            
            _, p_id, species_name, current_level, m1, m2, m3, m4 = specimen_data
            
            # Filter out empty slots to see how many active moves they actually have
            current_moves = [m for m in (m1, m2, m3, m4) if m and m != 'none']

            # ==========================================
            # 2. NEURAL REDUNDANCY CHECK
            # ==========================================
            if requested_move in current_moves:
                return await ctx.send(f"🧠 **Neural Redundancy:** **{species_name.capitalize()}** already knows `{requested_move.replace('-', ' ').title()}`.")

            # ==========================================
            # 3. BIOLOGICAL COMPATIBILITY CHECK
            # ==========================================
            cursor.execute("""
                SELECT learn_method, level_learned 
                FROM species_movepool 
                WHERE pokedex_id = ? AND move_name = ? 
                AND learn_method IN ('level-up', 'tutor')
            """, (p_id, requested_move))
            
            pool_data = cursor.fetchone()
            
            if not pool_data:
                return await ctx.send(f"🧬 **Genetic Incompatibility:** **{species_name.capitalize()}** is biologically incapable of learning `{requested_move.replace('-', ' ').title()}` via tutoring.")
                
            learn_method, level_learned = pool_data
            
            if learn_method == 'level-up' and current_level < level_learned:
                return await ctx.send(f"⚠️ **Maturation Error:** **{species_name.capitalize()}** must reach Level {level_learned} before its biology can support `{requested_move.replace('-', ' ').title()}`.")

            # ==========================================
            # 4. RESOURCE VERIFICATION
            # ==========================================
            cursor.execute("SELECT eco_tokens FROM users WHERE user_id = ?", (user_id,))
            funds = cursor.fetchone()[0]
            
            cursor.execute("SELECT quantity FROM user_inventory WHERE user_id = ? AND item_name = 'memory-spore'", (user_id,))
            spores = cursor.fetchone()
            spore_qty = spores[0] if spores else 0
            
            if funds < 500 or spore_qty < 1:
                return await ctx.send("❌ **Insufficient Resources:** The laboratory requires **500 Eco Tokens** and **1x Memory Spore** to perform a neural rewrite.")

            # ==========================================
            # 5. EXECUTION PIPELINE
            # ==========================================
            if len(current_moves) < 4:
                # Target the exact column that needs to be filled
                empty_slot = f"move_{len(current_moves) + 1}"
                
                cursor.execute("BEGIN TRANSACTION")
                cursor.execute("UPDATE users SET eco_tokens = eco_tokens - 500 WHERE user_id = ?", (user_id,))
                cursor.execute("UPDATE user_inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_name = 'memory-spore'", (user_id,))
                cursor.execute(f"UPDATE caught_pokemon SET {empty_slot} = ? WHERE instance_id = ?", (requested_move, actual_instance_id))
                conn.commit()
                
                embed = discord.Embed(
                    title="🧠 Neural Rewrite Complete", 
                    description=f"The `Memory Spore` successfully catalyzed the dormant genetic traits!\n\n**{species_name.capitalize()}** learned **{requested_move.replace('-', ' ').title()}**.",
                    color=discord.Color.green()
                )
                await ctx.send(embed=embed)
            else:
                # The specimen's brain is full! Spawn the UI to let the user choose a move to delete.
                embed = discord.Embed(
                    title="⚠️ Neural Capacity Reached",
                    description=f"**{species_name.capitalize()}** cannot support any more active combat techniques. You must selectively overwrite an existing neural pathway to teach it **{requested_move.replace('-', ' ').title()}**.\n\n*Note: Resources will only be consumed if you authorize the overwrite below.*",
                    color=discord.Color.orange()
                )
                
                # Pass the instance_id to the UI we built earlier!
                view = MoveReplacementView(self, ctx, user_id, actual_instance_id, species_name, requested_move, current_moves)
                await ctx.send(embed=embed, view=view)

        except Exception as e:
            if conn.in_transaction:
                conn.rollback()
            print(f"Tutor Command Error: {e}")
            await ctx.send("❌ A critical laboratory error occurred while accessing the neural database.")
        finally:
            conn.close()

    @commands.command(name="learn")
    @checks.has_started()
    @checks.is_authorized()
    @checks.is_not_in_combat()
    async def learn_move(self, ctx, target: str, slot: int, *, move_name: str):
        user_id = str(ctx.author.id)
        
        # 1. Validate the Slot
        if slot not in [1, 2, 3, 4]:
            return await ctx.send("⚠️ Specimens can only retain 4 active behaviors at a time. Please specify a slot between 1 and 4.")
            
        formatted_move = move_name.lower().replace(" ", "-")
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 2. Determine the Target Specimen (Partner, Box Number, or UUID)
        if target.lower() in ["partner", "lead", "active", "latest"]:
            cursor.execute("SELECT active_partner FROM users WHERE user_id = ?", (user_id,))
            partner_data = cursor.fetchone()
            if not partner_data or not partner_data[0]:
                conn.close()
                return await ctx.send("You don't have an Active Partner equipped! Specify a Box Number or Tag ID instead.")
                
            # If they used partner, we can just use the UUID directly!
            cursor.execute("""
                SELECT cp.instance_id, cp.pokedex_id, cp.level, s.name,
                    cp.move_1, cp.move_2, cp.move_3, cp.move_4
                FROM caught_pokemon cp
                JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                WHERE cp.instance_id = ? AND cp.user_id = ?
            """, (partner_data[0], user_id))
            
        elif target.isdigit() and len(target) <= 6:
            # It's a Box Number! Use the CTE to find it.
            cursor.execute("""
                WITH Roster AS (
                    SELECT cp.instance_id, cp.pokedex_id, cp.level, s.name,
                        cp.move_1, cp.move_2, cp.move_3, cp.move_4,
                        ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                    FROM caught_pokemon cp
                    JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                    WHERE cp.user_id = ?
                )
                SELECT instance_id, pokedex_id, level, name, move_1, move_2, move_3, move_4
                FROM Roster WHERE box_number = ?
            """, (user_id, int(target)))
            
        else:
            # It's a UUID tag!
            cursor.execute("""
                SELECT cp.instance_id, cp.pokedex_id, cp.level, s.name,
                    cp.move_1, cp.move_2, cp.move_3, cp.move_4
                FROM caught_pokemon cp
                JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                WHERE cp.instance_id LIKE ? AND cp.user_id = ?
            """, (f"{target}%", user_id))

        pokemon_data = cursor.fetchone()
        
        if not pokemon_data:
            conn.close()
            return await ctx.send("❌ Could not locate that specimen. Check your Box Number or Tag ID.")
            
        db_tag_id, poke_id, level, poke_name, m1, m2, m3, m4 = pokemon_data
        current_moves = [m1, m2, m3, m4]

        # 4. Check for Duplicates
        if formatted_move in current_moves:
            conn.close()
            return await ctx.send(f"⚠️ Your **{poke_name.capitalize()}** already has `{formatted_move.replace('-', ' ').title()}` equipped in its active behaviors!")

        # 5. Check the Biological Compatibility (Movepool)
        cursor.execute("""
            SELECT level_learned 
            FROM species_movepool 
            WHERE pokedex_id = ? AND move_name = ?
            ORDER BY level_learned ASC
        """, (poke_id, formatted_move))
        
        movepool_data = cursor.fetchone()
        
        if not movepool_data:
            conn.close()
            return await ctx.send(f"❌ Biological mismatch: A **{poke_name.capitalize()}** is not physically capable of learning `{formatted_move.replace('-', ' ').title()}`.")
            
        required_level = movepool_data[0]
        
        # 6. Check Maturity (Level)
        if level < required_level:
            conn.close()
            return await ctx.send(f"📈 Your **{poke_name.capitalize()}** needs to reach **Level {required_level}** before it can master `{formatted_move.replace('-', ' ').title()}`.")

        # 7. Execute the Training (Update the specific slot)
        try:
            column_to_update = f"move_{slot}"
            
            cursor.execute(f"""
                UPDATE caught_pokemon 
                SET {column_to_update} = ? 
                WHERE instance_id = ?
            """, (formatted_move, db_tag_id))
            
            conn.commit()
            
            # Determine what move we replaced for the message
            replaced_move = current_moves[slot - 1]
            replaced_text = f" It forgot `{replaced_move.replace('-', ' ').title()}` to make room." if replaced_move and replaced_move != 'none' else ""
            
            embed = discord.Embed(title="🧠 Behavioral Training Successful!", color=discord.Color.blue())
            embed.description = f"**{ctx.author.name}** spent time training their **{poke_name.capitalize()}**.\n\nIt successfully mastered **{formatted_move.replace('-', ' ').title()}**!{replaced_text}"
            embed.set_footer(text=f"Tag ID: {str(db_tag_id)[:8]} | Slot {slot} Updated")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            print(f"Learn error: {e}")
            await ctx.send("A data corruption error occurred during training.")
        finally:
            conn.close()
    
    @commands.command(name="battle", aliases=["duel", "spar"])
    @checks.has_started()
    @checks.is_authorized()
    @checks.is_not_in_combat()
    async def challenge_player(self, ctx, opponent: discord.Member = None):
        """Issues a formal Ecological Field Duel invitation to another researcher."""
        challenger_id = str(ctx.author.id)
        
        if not opponent:
            return await ctx.send("⚠️ You must ping the researcher you wish to spar with! Usage: `!challenge @User`")
            
        opponent_id = str(opponent.id)

        if challenger_id == opponent_id:
            return await ctx.send("⚠️ You cannot initiate a field duel against yourself!")
        if opponent.bot:
            return await ctx.send("⚠️ You cannot spar with automated logistics drones!")

        # 1. STATE MACHINE CHECK: Are either of them already busy?
        if hasattr(self, 'active_battles'):
            if challenger_id in self.active_battles:
                return await ctx.send("🛑 You are already engaged in an active skirmish! Finish it or flee first.")
            if opponent_id in self.active_battles:
                return await ctx.send(f"🛑 **{opponent.display_name}** is already deployed in an active field duel!")

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # 2. ROSTER CHECK: Do both players have teams?
        cursor.execute("SELECT COUNT(*) FROM user_party WHERE user_id = ?", (challenger_id,))
        if cursor.fetchone()[0] == 0:
            conn.close()
            return await ctx.send("⚠️ You must assign at least one specimen to your roster using `!party add 1 [Box Number]` before initiating a spar.")

        cursor.execute("SELECT COUNT(*) FROM user_party WHERE user_id = ?", (opponent_id,))
        if cursor.fetchone()[0] == 0:
            conn.close()
            return await ctx.send(f"⚠️ **{opponent.display_name}** does not have a fieldwork roster assembled yet.")
            
        conn.close()

        # 3. FIRE THE HANDSHAKE
        view = ChallengeView(self, ctx.author, opponent)
        
        # Save the message to the view so the timeout function can edit it later
        view.message = await ctx.send(
            f"⚔️ {opponent.mention}, **{ctx.author.display_name}** has challenged you to an Ecological Field Duel!\nDo you accept?", 
            view=view
        )

    async def initialize_pvp_battle(self, channel, p1: discord.Member, p2: discord.Member):
        """Builds a shared memory state for a synchronous PvP duel."""
        print(f"\n=== DEBUG: Initializing PvP Duel: {p1.display_name} vs {p2.display_name} ===")
        p1_id = str(p1.id)
        p2_id = str(p2.id)
        
        # 🚨 THE SAFETY NET: Catch crashes and unlock players! 🚨
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            teams = {}
            key_items = {}

            # 1. Fetch Biology and Loadout for BOTH players
            for uid in [p1_id, p2_id]:
                print(f"\n--- DEBUG: Extracting Roster for User {uid} ---")
                
                
                cursor.execute("""
                    SELECT cp.instance_id, cp.pokedex_id, s.name, cp.level, cp.nature,
                        cp.iv_hp, cp.iv_attack, cp.iv_defense, cp.iv_sp_atk, cp.iv_sp_def, cp.iv_speed,
                        cp.ev_hp, cp.ev_attack, cp.ev_defense, cp.ev_sp_atk, cp.ev_sp_def, cp.ev_speed,
                        cp.move_1, cp.move_2, cp.move_3, cp.move_4, cp.is_shiny, cp.held_item, cp.gmax_factor, cp.ability, cp.experience, up.slot
                    FROM user_party up
                    JOIN caught_pokemon cp ON up.instance_id = cp.instance_id
                    JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                    WHERE up.user_id = ?
                    ORDER BY up.slot ASC
                """, (uid,))
                
                rows = cursor.fetchall()
                print(f"DEBUG: Found {len(rows)} assigned specimens in user_party table.")
                
                player_team = []
                for row in rows:
                    tag, poke_id, p_name, p_lvl, p_nature = row[0:5]
                    roster_slot = row[26]
                    
                    print(f"DEBUG: Loading [Slot {roster_slot}] -> {p_name.capitalize()} (Level {p_lvl})")
                    
                    p_ivs = {'hp': row[5], 'attack': row[6], 'defense': row[7], 'sp_atk': row[8], 'sp_def': row[9], 'speed': row[10]}
                    p_evs = {'hp': row[11], 'attack': row[12], 'defense': row[13], 'sp_atk': row[14], 'sp_def': row[15], 'speed': row[16]}
                    
                    # Format Moves
                    raw_moves = [m for m in row[17:21] if m and m != 'none']
                    p_moves = []
                    for m_name in raw_moves:
                        cursor.execute("""
                            SELECT type, power, accuracy, damage_class, pp, 
                                ailment, ailment_chance, stat_name, stat_change, 
                                stat_chance, drain, healing, priority
                            FROM base_moves WHERE name = ?
                        """, (m_name,))
                        
                        m_data = cursor.fetchone()
                        if m_data:
                            # Unpack the new 13th variable!
                            m_type, m_power, m_acc, m_class, m_pp, m_ail, m_ail_c, m_stat, m_stat_c, m_stat_ch, m_drain, m_heal, m_prio = m_data
                            p_moves.append({
                                'name': m_name, 'type': m_type, 'power': m_power, 'accuracy': m_acc,
                                'class': m_class, 'pp': m_pp, 'max_pp': m_pp, 'ailment': m_ail,
                                'ailment_chance': m_ail_c, 'stat_name': m_stat, 'stat_change': m_stat_c,
                                'stat_chance': m_stat_ch, 'drain': m_drain, 'healing': m_heal,
                                'priority': m_prio # 🚨 Save it to the dictionary!
                            })
                        else:
                            p_moves.append({'name': m_name, 'pp': 5, 'max_pp': 5, 'priority': 0})

                    # Fetch Elemental Typing
                    cursor.execute("SELECT type_name FROM base_pokemon_types WHERE pokedex_id = ?", (poke_id,))
                    p_types = [t[0] for t in cursor.fetchall()]
                    
                    # Calculate True Stats
                    p_base = fetch_base_stats(cursor, poke_id)
                    p_final_stats = calculate_stats(p_base, p_ivs, p_evs, p_lvl, p_nature)
                    
                    player_team.append({
                        'instance_id': tag, 'pokedex_id': poke_id, 'name': p_name, 'level': p_lvl,
                        'max_hp': p_final_stats['hp'], 'current_hp': p_final_stats['hp'],
                        'stats': p_final_stats, 'moves': p_moves, 'status_condition': None, 
                        'is_shiny': row[21], 'held_item': row[22], 'gmax_factor': row[23], 
                        'ability': row[24], 'types': p_types, 'experience': row[25], 'volatile_statuses': {}
                    })
                    
                teams[uid] = player_team
                print(f"--- DEBUG: Team load complete for {uid}. Total size: {len(player_team)} ---")
                
                # Key Item Scanner
                cursor.execute("""
                    SELECT item_name FROM user_inventory 
                    WHERE user_id = ? AND item_name IN ('dynamax-band', 'z-ring', 'mega-bracelet') AND quantity > 0
                """, (uid,))
                owned_key_items = [r[0] for r in cursor.fetchall()]
                
                key_items[uid] = {
                    'dynamax_band': 'dynamax-band' in owned_key_items,
                    'z_ring': 'z-ring' in owned_key_items,
                    'mega_bracelet': 'mega-bracelet' in owned_key_items
                }

            conn.close()
            print("DEBUG: Database extraction complete. Building Shared State...")

            # 2. Build the Shared Memory Reference (The PvP Ecosystem)
            shared_state = {
                'is_pvp': True,
                'p1_id': p1_id,
                'p2_id': p2_id,
                'p1': p1, 
                'p2': p2,
                
                'p1_team': teams[p1_id],
                'p2_team': teams[p2_id],
                'p1_active_index': 0,
                'p2_active_index': 0,
                
                'turn_number': 1,
                'weather': {'type': 'none', 'duration': 0},
                
                'commits': {p1_id: None, p2_id: None},
                
                'p1_adaptation': {'used': False, 'active': False, 'type': 'none', 'turns': 0, 'backup': {}},
                'p2_adaptation': {'used': False, 'active': False, 'type': 'none', 'turns': 0, 'backup': {}},
                
                'p1_key_items': key_items[p1_id],
                'p2_key_items': key_items[p2_id],
                
                'p1_hazards': {'stealth-rock': False, 'spikes': 0, 'toxic-spikes': 0, 'sticky-web': False},
                'p2_hazards': {'stealth-rock': False, 'spikes': 0, 'toxic-spikes': 0, 'sticky-web': False}
            }

            # 3. Map BOTH players to the exact same dictionary in RAM!
            print("DEBUG: Locking players into active_battles dictionary.")
            self.active_battles[p1_id] = shared_state
            self.active_battles[p2_id] = shared_state

            # 4. Trigger Initial Entry Abilities
            print("DEBUG: Firing Initial Entry Abilities...")
            p1_lead = shared_state['p1_team'][0]
            p2_lead = shared_state['p2_team'][0]
            
            combat_log = f"**{p1.display_name}** vs. **{p2.display_name}**\n\n"
            combat_log += f"{p1.display_name} sent out **{p1_lead['name'].capitalize()}**!\n"
            combat_log += f"{p2.display_name} sent out **{p2_lead['name'].capitalize()}**!\n\n"
            
            combat_log = trigger_single_entry_ability(p1_lead, p2_lead, f"{p1.display_name}'s", shared_state, combat_log)
            combat_log = trigger_single_entry_ability(p2_lead, p1_lead, f"{p2.display_name}'s", shared_state, combat_log)

            # 5. Generate Initial Battle Canvas
            print("DEBUG: Calling generate_battle_scene...")
            battle_file = await BattleDashboard.generate_battle_scene(
                self,
                player_id=p1_lead['pokedex_id'], 
                npc_id=p2_lead['pokedex_id'],
                p_hp=p1_lead['current_hp'], p_max_hp=p1_lead['max_hp'],
                n_hp=p2_lead['current_hp'], n_max_hp=p2_lead['max_hp'],
                player_shiny=p1_lead.get('is_shiny', False), 
                npc_shiny=p2_lead.get('is_shiny', False),
                weather=shared_state['weather']['type'],
                p_status=p1_lead.get('status_condition'),
                n_status=p2_lead.get('status_condition'),
                p_hazards=shared_state['p1_hazards'],
                n_hazards=shared_state['p2_hazards']
            )

            # 6. Render the UI
            print("DEBUG: Constructing UI Elements...")
            embed = discord.Embed(title="⚔️ PvP Field Duel Commencing!", description=combat_log, color=discord.Color.red())
            
            p1_roster = "".join(["🔴" for _ in shared_state['p1_team']])
            p2_roster = "".join(["🔴" for _ in shared_state['p2_team']])
            
            embed.add_field(name=f"🟢 {p1.display_name}'s {p1_lead['name'].capitalize()}", value=f"Team: {p1_roster}", inline=True)
            embed.add_field(name=f"🔴 {p2.display_name}'s {p2_lead['name'].capitalize()}", value=f"Team: {p2_roster}", inline=True)
            # Dynamically grab the new randomized filename!
            # Dynamically attach the first image!
            embed.set_image(url=f"attachment://{battle_file.filename}")
            embed.set_footer(text="Awaiting inputs from both researchers...")

            dashboard_view = PvPDashboard(self, shared_state)
            
            print("DEBUG: Sending final payload to Discord...")
            shared_state['message_obj'] = await channel.send(embed=embed, files=[battle_file], view=dashboard_view)
            print("=== DEBUG: PvP Initialization COMPLETE ===")

        except Exception as e:
            print("\n🚨 CRITICAL CRASH IN PVP INITIALIZATION 🚨")
            import traceback
            traceback.print_exc()
            
            # Safely release the players from the lock so they aren't stuck!
            self.active_battles.pop(p1_id, None)
            self.active_battles.pop(p2_id, None)
            
            await channel.send("⚠️ A critical biological error occurred while initializing the PvP arena. The duel has been aborted and both researchers have been released.")
            
        finally:
            if 'conn' in locals():
                conn.close()

    async def check_pvp_commits(self, state):
        """Verifies if both players have submitted their payloads to the shared memory block."""
        p1_ready = state['commits'][state['p1_id']] is not None
        p2_ready = state['commits'][state['p2_id']] is not None

        if p1_ready and p2_ready:
            # BOTH PLAYERS ARE LOCKED IN! 
            try:
                await state['message_obj'].edit(view=None) 
            except Exception as e:
                print(f"UI Edit Error: {e}")
            
            # Route traffic based on the phase!
            if state.get('phase') == 'faint_swap':
                await self.process_faint_swaps(state)
            else:
                await self.process_pvp_turn(state)
            
        else:
            # SOMEONE IS STILL DECIDING. Update the public footer so they know who!
            waiting_for = []
            if not p1_ready: waiting_for.append(state['p1'].display_name)
            if not p2_ready: waiting_for.append(state['p2'].display_name)
            
            try:
                # Fetch the live message from Discord to ensure we don't grab stale Embeds!
                channel = state['message_obj'].channel
                fresh_msg = await channel.fetch_message(state['message_obj'].id)
                
                
                embed = fresh_msg.embeds[0]
                embed.set_footer(text=f"⏳ Awaiting telemetry from: {', '.join(waiting_for)}...")
                
                # Explicitly pass fresh_msg.attachments so Discord doesn't orphan the images!
                await fresh_msg.edit(embed=embed, attachments=fresh_msg.attachments)
                
                # Update our state cache so it stops lagging behind
                state['message_obj'] = fresh_msg 

            except Exception as e:
                print(f"DEBUG: Footer update failed: {e}")

    async def process_pvp_turn(self, state):
        """Resolves the double-blind commits, executes the physics, and redraws the UI."""
        print("\n=== DEBUG: process_pvp_turn triggered ===")
        
        p1_id = state['p1_id']
        p2_id = state['p2_id']
        
        try:
            c1 = state['commits'][p1_id]
            c2 = state['commits'][p2_id]
            
            p1_active = state['p1_team'][state['p1_active_index']]
            p2_active = state['p2_team'][state['p2_active_index']]
            
            combat_log = f"**Turn {state['turn_number']}**\n\n"
            
            # ==========================================
            # PHASE 0: BIOLOGICAL ADAPTATIONS
            # ==========================================
            print("DEBUG: Checking for Hyper-Adaptations...")
            
            # We open a single DB connection here to process any Megas efficiently
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            for pid, commit, active_poke, adp_state in [
                (p1_id, c1, p1_active, state['p1_adaptation']),
                (p2_id, c2, p2_active, state['p2_adaptation'])
            ]:
                if commit['type'] == 'attack' and commit.get('transform'):
                    form = commit['transform']
                    owner_name = state['p1'].display_name if pid == p1_id else state['p2'].display_name
                    
                    # 1. Create Biological Backup
                    adp_state['backup'] = {
                        'name': active_poke['name'],
                        'pokedex_id': active_poke['pokedex_id'],
                        'max_hp': active_poke['max_hp'],
                        'stats': active_poke['stats'].copy(),
                        'types': list(active_poke.get('types', []))
                    }
                    
                    # 2. Apply Dynamax & Gigantamax
                    if form == 'dynamax':
                        has_gmax = active_poke.get('gmax_factor', False) or active_poke.get('gmax_factor', 0) == 1
                        base_name = active_poke['name'].lower().replace(' (dynamax)', '').replace(' (gigantamax)', '').split('-')[0].strip()
                        
                        hp_boost = math.floor(active_poke['max_hp'] * 0.5)
                        active_poke['max_hp'] += hp_boost
                        active_poke['current_hp'] += hp_boost
                        
                        if has_gmax:
                            # Query the database for the G-Max Pokedex ID!
                            cursor.execute("SELECT pokedex_id FROM base_pokemon_species WHERE name = ?", (f"{base_name}-gmax",))
                            gmax_data = cursor.fetchone()
                            
                            if gmax_data:
                                active_poke['pokedex_id'] = gmax_data[0] # Update the ID for the visual renderer!
                                
                            active_poke['name'] = f"{active_poke['name']} (Gigantamax)"
                            combat_log += f"🔴 **{owner_name}'s** specimen absorbed Galar particles and Gigantamaxed into **{active_poke['name'].capitalize()}**!\n"
                        else:
                            active_poke['name'] = f"{active_poke['name']} (Dynamax)"
                            combat_log += f"🔴 **{owner_name}'s** specimen absorbed Galar particles and Dynamaxed into **{active_poke['name'].capitalize()}**!\n"
                            
                        adp_state.update({'used': True, 'active': True, 'type': 'dynamax', 'turns': 3})

                    # 3. Apply Mega Evolution
                    elif form == 'mega':
                        # Clean the base name and query the database for the Mega form
                        base_name = active_poke['name'].split('-')[0]
                        cursor.execute("SELECT pokedex_id, name FROM base_pokemon_species WHERE name = ? OR name = ?", (f"{base_name}-mega", f"{base_name}-mega-x"))
                        mega_data = cursor.fetchone()
                        
                        if mega_data:
                            form_id, form_name = mega_data
                            
                            # Fetch new stats and types
                            cursor.execute("SELECT stat_name, base_value FROM base_pokemon_stats WHERE pokedex_id = ?", (form_id,))
                            db_stats = {row[0]: row[1] for row in cursor.fetchall()}
                            
                            cursor.execute("SELECT type_name FROM base_pokemon_types WHERE pokedex_id = ?", (form_id,))
                            new_types = [row[0] for row in cursor.fetchall()]
                            
                            level = active_poke['level']
                            base_hp = db_stats.get('hp', 50)
                            base_atk = db_stats.get('attack', 50)
                            base_def = db_stats.get('defense', 50)
                            base_spa = db_stats.get('special-attack', 50) 
                            base_spd = db_stats.get('special-defense', 50)
                            base_spe = db_stats.get('speed', 50)
                            
                            # Apply PvP Math
                            new_max_hp = math.floor((2 * base_hp + 15) * level / 100) + level + 10
                            hp_diff = new_max_hp - active_poke['max_hp']
                            active_poke['max_hp'] = new_max_hp
                            active_poke['current_hp'] = max(1, active_poke['current_hp'] + hp_diff)
                            
                            active_poke['stats'] = {
                                'attack': math.floor((2 * base_atk + 15) * level / 100) + 5,
                                'defense': math.floor((2 * base_def + 15) * level / 100) + 5,
                                'sp_atk': math.floor((2 * base_spa + 15) * level / 100) + 5,
                                'sp_def': math.floor((2 * base_spd + 15) * level / 100) + 5,
                                'speed': math.floor((2 * base_spe + 15) * level / 100) + 5
                            }
                            
                            active_poke['pokedex_id'] = form_id
                            active_poke['name'] = form_name
                            active_poke['types'] = new_types
                            
                            adp_state.update({'used': True, 'active': True, 'type': 'mega', 'turns': -1})
                            combat_log += f"✨ **{owner_name}'s** specimen achieved Hyper-Adaptation and Mega Evolved into **{form_name.replace('-', ' ').title()}**!\n"
                        else:
                            combat_log += f"⚠️ **{owner_name}'s** {active_poke['name'].capitalize()} tried to Mega Evolve, but its genetic data was missing from the database!\n"

                    # 4. Apply Z-Move Marker
                    elif form == 'zmove':
                        adp_state.update({'used': True, 'active': True, 'type': 'zmove', 'turns': 1})
                        combat_log += f"💎 **{owner_name}'s** {active_poke['name'].capitalize()} surrounded itself with its Z-Power!\n"

            conn.close() # Close the connection safely before proceeding to speed resolution
            # ==========================================
            # PHASE 1: TURN ORDER & SPEED RESOLUTION
            # ==========================================
            print("DEBUG: Resolving turn order...")
            def get_action_priority(commit):
                # Swaps are nearly instantaneous (Equivalent to +6 priority)
                if commit['type'] == 'swap': 
                    return 6 
                # Attacks dynamically pull their priority from the DB!
                if commit['type'] == 'attack':
                    return commit['data'].get('priority', 0)
                return 0
                
            def get_combat_speed(pokemon):
                base_spd = pokemon['stats'].get('speed', 50)
                stage = pokemon.get('stat_stages', {}).get('speed', 0)
                
                # 1. Calculate the base biological multiplier first
                if stage > 0: multiplier = (2.0 + stage) / 2.0
                elif stage < 0: multiplier = 2.0 / (2.0 + abs(stage))
                else: multiplier = 1.0
                
                final_spd = base_spd * multiplier
                
                # 2. Apply Equipment Modifiers
                item = (pokemon.get('held_item') or "").lower().replace(' ', '-')
                if item == 'choice-scarf':
                    final_spd *= 1.5
                    
                # 3. Apply Pathogen Penalties
                status = pokemon.get('status_condition') or {}
                if status and status.get('name') == 'paralysis':
                    final_spd *= 0.5
                    
                return int(final_spd) # Ensure we return a clean integer!

            p1_prio = get_action_priority(c1)
            p2_prio = get_action_priority(c2)
            
            p1_goes_first = False
            if p1_prio > p2_prio: p1_goes_first = True
            elif p2_prio > p1_prio: p1_goes_first = False
            else:
                spd1 = get_combat_speed(p1_active)
                spd2 = get_combat_speed(p2_active)
                if spd1 > spd2: p1_goes_first = True
                elif spd2 > spd1: p1_goes_first = False
                else: p1_goes_first = random.choice([True, False]) 

            execution_queue = []
            if p1_goes_first:
                execution_queue.append({'player': 'p1', 'commit': c1, 'active': p1_active, 'opp_active': p2_active})
                execution_queue.append({'player': 'p2', 'commit': c2, 'active': p2_active, 'opp_active': p1_active})
            else:
                execution_queue.append({'player': 'p2', 'commit': c2, 'active': p2_active, 'opp_active': p1_active})
                execution_queue.append({'player': 'p1', 'commit': c1, 'active': p1_active, 'opp_active': p2_active})

            # ==========================================
            # PHASE 2: ACTION EXECUTION
            # ==========================================
            print("DEBUG: Executing Queue...")
            for action in execution_queue:
                player_tag = action['player'] 
                opp_tag = 'p2' if player_tag == 'p1' else 'p1'
                commit = action['commit']
                attacker = action['active']
                defender = action['opp_active'] 
                
                owner_name = state[player_tag].display_name
                opp_name = state[opp_tag].display_name

                if attacker['current_hp'] <= 0:
                    continue 

                # --- EXECUTE SWAP ---
                if commit['type'] == 'swap':
                    bench_idx = commit['data']
                    new_active = state[f"{player_tag}_team"][bench_idx]

                    # 1. SERVER-SIDE FAILSAFE: Reject dead swaps BEFORE mutating the state!
                    if new_active['current_hp'] <= 0:
                        combat_log += f"⚠️ **{owner_name}** tried to send out {new_active['name'].capitalize()}, but it's already fainted!\n"
                        continue 
                    
                    # 2. STATE MUTATION: Only update the index if the specimen is alive!
                    state[f"{player_tag}_active_index"] = bench_idx
                    
                    combat_log += f"🔄 **{owner_name}** withdrew {attacker['name'].capitalize()} and sent out **{new_active['name'].capitalize()}**!\n"
                    
                    try:
                        hazard_log = apply_entry_hazards(new_active, state[f"{player_tag}_hazards"], TYPE_CHART, f"{owner_name}'s")
                        if hazard_log: combat_log += hazard_log
                    except Exception as e:
                        print(f"DEBUG WARNING: Hazard application failed: {e}")
                    
                    if new_active['current_hp'] > 0:
                        try:
                            combat_log = trigger_single_entry_ability(new_active, defender, f"{owner_name}'s", state, combat_log)
                        except Exception as e:
                            print(f"DEBUG WARNING: Ability trigger failed: {e}")
                    
                    # 3. POINTER UPDATES: Redirect incoming attacks to the new Pokémon
                    action['active'] = new_active 
                    for other_action in execution_queue:
                        if other_action['player'] == opp_tag:
                            other_action['opp_active'] = new_active

                # --- EXECUTE ATTACK ---
                elif commit['type'] == 'attack':
                    move = commit['data']
                    
                    if defender['current_hp'] <= 0:
                        combat_log += f"💥 **{owner_name}'s** {attacker['name'].capitalize()} used **{move['name'].replace('-', ' ').title()}**, but there was no target!\n"
                        continue
                    
                    can_attack = True
                    
                    # 1. VOLATILE STATUS: CONFUSION CHECK
                    volatiles = attacker.get('volatile_statuses', {})
                    if 'confusion' in volatiles:
                        volatiles['confusion'] -= 1
                        if volatiles['confusion'] <= 0:
                            del volatiles['confusion']
                            combat_log += f"💫 **{owner_name}'s** {attacker['name'].capitalize()} snapped out of its confusion!\n"
                        else:
                            combat_log += f"💫 **{owner_name}'s** {attacker['name'].capitalize()} is confused...\n"
                            if random.randint(1, 100) <= 33: 
                                conf_dmg, conf_msg, _, _, _ = calculate_damage(attacker, attacker, {'name': 'confusion-snap', 'class': 'physical', 'power': 40, 'type': 'typeless'})
                                attacker['current_hp'] = max(0, attacker['current_hp'] - conf_dmg)
                                combat_log += f"💥 {conf_msg} (Dealt **{conf_dmg}** damage!)\n"
                                can_attack = False 
                                
                    # 2. VOLATILE STATUS: FLINCH CHECK
                    if 'flinch' in volatiles and volatiles['flinch']:
                        combat_log += f"🚫 **{owner_name}'s** {attacker['name'].capitalize()} flinched and couldn't move!\n"
                        volatiles['flinch'] = False
                        can_attack = False
                    
                    # 3. BIOLOGICAL STATUS CHECK (Paralysis, Sleep, Freeze)
                    status = attacker.get('status_condition', {})
                    if status and can_attack:
                        s_name = status.get('name')
                        if s_name == 'paralysis' and random.randint(1, 4) == 1:
                            combat_log += f"⚡ **{owner_name}'s** {attacker['name'].capitalize()} is fully paralyzed!\n"
                            can_attack = False
                        elif s_name == 'sleep':
                            status['duration'] -= 1
                            if status['duration'] <= 0:
                                combat_log += f"☀️ **{owner_name}'s** {attacker['name'].capitalize()} woke up!\n"
                                attacker['status_condition'] = None
                            else:
                                combat_log += f"💤 **{owner_name}'s** {attacker['name'].capitalize()} is fast asleep.\n"
                                can_attack = False
                        elif s_name == 'freeze':
                            if random.randint(1, 5) == 1:
                                combat_log += f"🔥 **{owner_name}'s** {attacker['name'].capitalize()} thawed out!\n"
                                attacker['status_condition'] = None
                            else:
                                combat_log += f"🧊 **{owner_name}'s** {attacker['name'].capitalize()} is frozen solid!\n"
                                can_attack = False

                    # If the attacker is stunned by ANY of the above, skip the attack phase!
                    if not can_attack:
                        continue
                        
                    # Deduct the PP using the base_name!
                    for actual_move in attacker['moves']:
                        if actual_move['name'] == move.get('base_name', move['name']):
                            actual_move['pp'] = max(0, actual_move['pp'] - 1)
                            break

                    combat_log += f"💥 **{owner_name}'s** {attacker['name'].capitalize()} used **{move['name'].replace('-', ' ').title()}**!\n"
                    
                    # --- Z-MOVE KINETIC INJECTION ---
                    adp_state = state['p1_adaptation'] if player_tag == 'p1' else state['p2_adaptation']
                    if adp_state['active'] and adp_state['type'] == 'zmove':
                        move['power'] = (move['power'] or 50) + 100
                        move['accuracy'] = 1000 
                        combat_log += f"💫 It unleashed its full-force Z-Move!\n"
                        adp_state['active'] = False 
                        
                    # --- DYNAMAX KINETIC INJECTION & SANITIZATION ---
                    is_max_move = move['name'].startswith('Max ') or move['name'].startswith('G-Max')
                    if adp_state['active'] and adp_state['type'] == 'dynamax' and is_max_move:
                        
                        # Intercept Max Guard and turn it into a pure shield!
                        if move['name'] == 'Max Guard':
                            move['class'] = 'status'
                            move['power'] = 0
                            move['target'] = 'user'
                            move['ailment'] = 'none'
                            move['ailment_chance'] = 0
                            move['status_type'] = 'none'
                            move['status_chance'] = 0
                            move['stat_name'] = 'none'
                            move['stat_change'] = 0
                            move['healing'] = 0
                            move['drain'] = 0
                        
                        elif move.get('class', 'physical') != 'status':
                            # 1. Wipe the base move's original secondary effects
                            move['ailment'] = 'none'
                            move['ailment_chance'] = 0
                            move['status_type'] = 'none'
                            move['status_chance'] = 0
                            move['healing'] = 0
                            move['drain'] = 0
                            
                            # 2. Inject standard Max Move parameters
                            move['power'] = max(130, move.get('power', 0)) 
                            move['accuracy'] = 1000
                            
                            # 3. Apply Specific Max & G-Max Biological Effects
                            if move['name'] == 'Max Strike':
                                move['stat_name'] = 'speed'
                                move['stat_change'] = -1
                                move['stat_chance'] = 100
                                move['target'] = 'defender'
                            else:
                                # Look up the G-Max move in your global dictionary and inject its payload!
                                if 'GMAX_MOVES' in globals():
                                    for g_data in GMAX_MOVES.values():
                                        if g_data.get('name') == move['name']:
                                            
                                            # ==========================================
                                            # HARDCODED ANOMALIES (Befuddle, Stun Shock)
                                            # ==========================================
                                            if move['name'] == 'G-Max Befuddle':
                                                move['ailment'] = random.choice(['poison', 'paralysis', 'sleep'])
                                                move['ailment_chance'] = 100
                                            elif move['name'] == 'G-Max Stun Shock':
                                                move['ailment'] = random.choice(['poison', 'paralysis'])
                                                move['ailment_chance'] = 100
                                                
                                            # ==========================================
                                            # PERSISTENT ECOLOGICAL DISASTERS
                                            # ==========================================
                                            elif move['name'] in ['G-Max Wildfire', 'G-Max Vine Lash', 'G-Max Cannonade', 'G-Max volcalith']:
                                                # Smuggle the unique effect into the status_type column!
                                                move['status_type'] = move['name'].lower().replace('g-max ', '')
                                                move['status_chance'] = 100

                                            # ==========================================
                                            # STANDARD INJECTIONS
                                            # ==========================================
                                            else:
                                                if 'ailment' in g_data:
                                                    move['ailment'] = g_data['ailment']
                                                    move['ailment_chance'] = 100 
                                                if 'stat_name' in g_data:
                                                    move['stat_name'] = g_data['stat_name']
                                                    move['stat_change'] = g_data.get('stat_change', -1)
                                                    move['stat_chance'] = 100
                                                    move['target'] = g_data.get('target', 'defender')
                                                if 'healing' in g_data:
                                                    move['healing'] = g_data['healing']
                                            break

                    print(f"DEBUG: Firing Physics Engine. Attacker: {attacker['name']} | Defender: {defender['name']} | Move Data: {move}")
                    dmg, msg, status, stat_changes, heal = calculate_damage(
                        attacker, defender, move, 
                        weather=state['weather']['type'], 
                        target_hazards=state[f"{opp_tag}_hazards"],
                        user_hazards=state[f"{player_tag}_hazards"]
                    )

                    print(f"DEBUG: Result -> Dmg: {dmg}, Heal: {heal}, Stat Chgs: {stat_changes}")
                    
                    # Apply HP modifications
                    defender['current_hp'] = max(0, defender['current_hp'] - dmg)
                    if heal > 0:
                        attacker['current_hp'] = min(attacker.get('max_hp', 100), attacker['current_hp'] + heal)
                       
                    # Print out the damage and physics engine messages!
                    if msg: combat_log += f"↳ {msg}\n"
                    if dmg > 0: combat_log += f"↳ Dealt **{dmg}** damage.\n"
                    
                    # Check if the damage pushed them below the berry threshold!
                    berry_log = check_consumables(defender, attacker) 
                    if berry_log: combat_log += berry_log

                    # Apply Stat Changes (Swords Dance, Max Strike speed drop, etc.)
                    for tgt_str, s_name, chg in stat_changes:
                        target_specimen = attacker if tgt_str == 'attacker' else defender
                        
                        stat_map = {'attack': 'attack', 'defense': 'defense', 'special-attack': 'sp_atk', 'special-defense': 'sp_def', 'speed': 'speed'}
                        db_stat = stat_map.get(s_name)
                        if db_stat:
                            if 'stat_stages' not in target_specimen:
                                target_specimen['stat_stages'] = {'attack': 0, 'defense': 0, 'sp_atk': 0, 'sp_def': 0, 'speed': 0}
                            curr_stg = target_specimen['stat_stages'].get(db_stat, 0)
                            target_specimen['stat_stages'][db_stat] = max(-6, min(6, curr_stg + chg))
                            
                            direction = "fell" if chg < 0 else "rose"
                            icon = "📉" if chg < 0 else "📈"
                            combat_log += f"↳ {icon} **{target_specimen['name'].capitalize()}**'s {s_name.replace('-', ' ')} {direction}!\n"
                    
                    if status:
                        defender['status_condition'] = {'name': status, 'duration': -1}
                        combat_log += f"↳ **{opp_name}'s** {defender['name'].capitalize()} was afflicted with {status}!\n"

                    # ==========================================
                    # CLIMATOLOGICAL OVERRIDES (Weather Moves)
                    # ==========================================
                    effective_move_name = move.get('base_name', move['name'])
                    
                    # Try the exact name first (for 'Max Flare'), then fallback to hyphenated (for 'rain-dance')
                    new_weather = WEATHER_MOVES.get(effective_move_name) or WEATHER_MOVES.get(effective_move_name.lower().replace(' ', '-'))
                    
                    if new_weather:
                        # Do not change weather if a Primordial climate is active!
                        if state.get('weather', {}).get('primordial', False):
                            combat_log += f"↳ The extreme weather prevented `{effective_move_name}` from taking effect!\n"
                        else:
                            attacker_item = (attacker.get('held_item') or "").lower().replace(' ', '-')
                            weather_rocks = {'sun': 'heat-rock', 'rain': 'damp-rock', 'sand': 'smooth-rock', 'hail': 'icy-rock'}
                            
                            duration = 8 if attacker_item == weather_rocks.get(new_weather) else 5
                            
                            state['weather'] = {'type': new_weather, 'duration': duration, 'primordial': False}
                            combat_log += f"↳ {WEATHER_MESSAGES.get(new_weather, 'The weather changed.')}\n"
                        
                        # Apply the 8-turn extension if they are holding the right geological item!
                        duration = 8 if attacker_item == weather_rocks.get(new_weather) else 5
                        
                        state['weather'] = {'type': new_weather, 'duration': duration}
                        combat_log += f"↳ {WEATHER_MESSAGES.get(new_weather, 'The weather changed.')}\n"

                    if defender['current_hp'] <= 0:
                        combat_log += f"💀 **{opp_name}'s** {defender['name'].capitalize()} fainted!\n\n"

            # ==========================================
            # PHASE 3: POST-TURN ENVIRONMENTAL DAMAGE & CLEANUP
            # ==========================================
            print("DEBUG: End of turn cleanups and environmental damage...")
            combat_log += "\n"

            # Define the active Pokémon BEFORE we apply damage or clean their flags!
            new_p1_active = state['p1_team'][state['p1_active_index']]
            new_p2_active = state['p2_team'][state['p2_active_index']]

            # Create an iterable tuple to process both players efficiently
            combatants = [
                (new_p1_active, new_p2_active, f"{state['p1'].display_name}'s"),
                (new_p2_active, new_p1_active, f"{state['p2'].display_name}'s")
            ]

            # 1. Global Biome Effects (Weather Expiration & Chip Damage)
            if state['weather']['type'] != 'none':
                state['weather']['duration'] -= 1
                if state['weather']['duration'] <= 0:
                    weather_clear_msgs = {
                        'rain': "The heavy rain stopped.",
                        'sun': "The harsh sunlight faded.",
                        'sand': "The sandstorm subsided.",
                        'hail': "The hail stopped."
                    }
                    combat_log += f"🌤️ {weather_clear_msgs.get(state['weather']['type'], 'The weather cleared.')}\n"
                    state['weather']['type'] = 'none'
                else:
                    # Apply Sandstorm/Hail chip damage
                    if state['weather']['type'] in ['sand', 'hail']:
                        for combatant, _, owner_str in combatants:
                            if combatant['current_hp'] > 0:
                                is_immune = False
                                c_types = combatant.get('types', [])
                                
                                if state['weather']['type'] == 'sand' and any(t in ['rock', 'ground', 'steel'] for t in c_types):
                                    is_immune = True
                                if state['weather']['type'] == 'hail' and 'ice' in c_types:
                                    is_immune = True
                                    
                                if not is_immune:
                                    chip_dmg = max(1, math.floor(combatant['max_hp'] / 16))
                                    combatant['current_hp'] = max(0, combatant['current_hp'] - chip_dmg)
                                    icon = "🌪️" if state['weather']['type'] == 'sand' else "❄️"
                                    combat_log += f"{icon} {owner_str} **{combatant['name'].capitalize()}** is buffeted by the {state['weather']['type']}! (-{chip_dmg} HP)\n"
                    # Dry Skin Atmospheric Reactions
                    for combatant, _, owner_str in combatants: # Remove the '_' in PvE!
                        if combatant['current_hp'] > 0 and combatant.get('ability') == 'dry-skin':
                            weather_type = state['weather']['type']
                            
                            # Takes 1/8th damage in Sunlight
                            if weather_type in ['sun', 'extremely-harsh-sunlight']:
                                dmg = max(1, math.floor(combatant['max_hp'] / 8))
                                combatant['current_hp'] = max(0, combatant['current_hp'] - dmg)
                                combat_log += f"☀️ {owner_str.strip()} **{combatant['name'].capitalize()}** was hurt by the harsh sunlight due to its Dry Skin! (-{dmg} HP)\n"
                                
                            # Restores 1/8th health in Rain
                            elif weather_type in ['rain', 'heavy-rain']:
                                if combatant['current_hp'] < combatant.get('max_hp', 100):
                                    heal = max(1, math.floor(combatant['max_hp'] / 8))
                                    combatant['current_hp'] = min(combatant.get('max_hp', 100), combatant['current_hp'] + heal)
                                    combat_log += f"🌧️ {owner_str.strip()} **{combatant['name'].capitalize()}** restored HP in the rain due to its Dry Skin! (+{heal} HP)\n"
            # ==========================================
            # 1.5 PERSISTENT HELD ITEMS (Status Orbs)
            # ==========================================
            for combatant, _, owner_str in combatants: # Use just 'combatant, owner_str' in PvE!
                if combatant['current_hp'] > 0 and not combatant.get('status_condition'):
                    orb_item = (combatant.get('held_item') or "").lower().replace(' ', '-')
                    
                    if orb_item == 'flame-orb' and 'fire' not in combatant.get('types', []):
                        combatant['status_condition'] = {'name': 'burn', 'duration': -1}
                        combat_log += f"🔥 {owner_str} **{combatant['name'].capitalize()}** was burned by its Flame Orb!\n"
                        
                    elif orb_item == 'toxic-orb' and 'poison' not in combatant.get('types', []) and 'steel' not in combatant.get('types', []):
                        combatant['status_condition'] = {'name': 'poison', 'duration': -1}
                        combat_log += f"☣️ {owner_str} **{combatant['name'].capitalize()}** was badly poisoned by its Toxic Orb!\n"

            # 2. Pathogen Damage (Burn/Poison)
            for combatant, _, owner_str in combatants:
                ability = (combatant.get('ability') or "").lower().replace(' ', '-')
                if combatant['current_hp'] > 0 and combatant.get('status_condition'):
                    status_name = combatant['status_condition']['name']
                    if status_name == 'burn':
                        burn_dmg = max(1, math.floor(combatant['max_hp'] / 16))
                        combatant['current_hp'] = max(0, combatant['current_hp'] - burn_dmg)
                        combat_log += f"🔥 {owner_str} **{combatant['name'].capitalize()}** suffered a burn! (-{burn_dmg} HP)\n"
                    elif status_name == 'poison':
                        # If they have Poison Heal, skip the damage entirely!
                        if ability == 'poison-heal':
                            continue
                        psn_dmg = max(1, math.floor(combatant['max_hp'] / 8))
                        combatant['current_hp'] = max(0, combatant['current_hp'] - psn_dmg)
                        combat_log += f"☣️ {owner_str} **{combatant['name'].capitalize()}** was hurt by the poison! (-{psn_dmg} HP)\n"

            # 2.5 Biological Sustenance (Held Items: Leftovers, Black Sludge)
            for combatant, _ ,owner_str in combatants:
                if combatant['current_hp'] > 0:
                    item = (combatant.get('held_item') or "").lower().replace(' ', '-')
                    
                    if item == 'leftovers':
                        heal_qty = max(1, math.floor(combatant['max_hp'] / 16))
                        combatant['current_hp'] = min(combatant['max_hp'], combatant['current_hp'] + heal_qty)
                        combat_log += f"🍎 **{owner_str} {combatant['name'].capitalize()}** restored a little HP using its Leftovers! (+{heal_qty})\n"
                        
                    elif item == 'black-sludge':
                        if 'poison' in combatant.get('types', []):
                            heal_qty = max(1, math.floor(combatant['max_hp'] / 16))
                            combatant['current_hp'] = min(combatant['max_hp'], combatant['current_hp'] + heal_qty)
                            combat_log += f"🧪 **{owner_str} {combatant['name'].capitalize()}** restored HP via its Black Sludge! (+{heal_qty})\n"
                        else:
                            sludge_dmg = max(1, math.floor(combatant['max_hp'] / 8))
                            combatant['current_hp'] = max(0, combatant['current_hp'] - sludge_dmg)
                            combat_log += f"🧪 **{owner_str} {combatant['name'].capitalize()}** is buffeted by its Black Sludge! (-{sludge_dmg})\n"

            # ==========================================
            # 2.8 BIOLOGICAL END-OF-TURN HOOKS 
            # ==========================================
            # (Note: In process_turn_end, remember to use `for combatant, owner_str in combatants:`)
            for combatant, _, owner_str in combatants: 
                if combatant['current_hp'] > 0:
                    ability = (combatant.get('ability') or "").lower().replace(' ', '-')
                    eot_trait = BIOLOGICAL_TRAITS.get('end_of_turn', {}).get(ability)
                    
                    if eot_trait:
                        ability_name = ability.replace('-', ' ').title()
                        
                        # 1. Adrenaline Escalation (Speed Boost)
                        if eot_trait['type'] == 'stat':
                            stat_target = eot_trait['stat']
                            
                            if 'stat_stages' not in combatant:
                                combatant['stat_stages'] = {'attack': 0, 'defense': 0, 'sp_atk': 0, 'sp_def': 0, 'speed': 0}
                            
                            current_stage = combatant['stat_stages'].get(stat_target, 0)
                            if current_stage < 6:
                                combatant['stat_stages'][stat_target] = min(6, current_stage + eot_trait['value'])
                                combat_log += f"💨 {owner_str.strip()} **{combatant['name'].capitalize()}**'s {ability_name} increased its {stat_target.capitalize()}!\n"

                        # 2. Cellular Shedding (Shed Skin)
                        elif eot_trait['type'] == 'cure' and combatant.get('status_condition'):
                            if random.randint(1, 100) <= eot_trait['chance']:
                                cured_status = combatant['status_condition']['name']
                                combatant['status_condition'] = None
                                combat_log += f"✨ {owner_str.strip()} **{combatant['name'].capitalize()}** cured its {cured_status} using {ability_name}!\n"

                        # 3. Environmental Sustenance (Rain Dish, Ice Body)
                        elif eot_trait['type'] == 'weather_heal':
                            current_weather = state.get('weather', {}).get('type', 'none')
                            
                            if current_weather in eot_trait['weather'] and combatant['current_hp'] < combatant.get('max_hp', 100):
                                heal = max(1, math.floor(combatant.get('max_hp', 100) / eot_trait['denominator']))
                                combatant['current_hp'] = min(combatant.get('max_hp', 100), combatant['current_hp'] + heal)
                                combat_log += f"💚 {owner_str.strip()} **{combatant['name'].capitalize()}** restored HP using {ability_name}!\n"

                        # Pathogen Symbiosis (Poison Heal)
                        elif eot_trait['type'] == 'status_heal':
                            target_status = eot_trait['status']
                            current_status = combatant.get('status_condition', {})
                            
                            # If they have the matching status condition, heal them!
                            if current_status and current_status.get('name') == target_status and combatant['current_hp'] < combatant.get('max_hp', 100):
                                heal = max(1, math.floor(combatant.get('max_hp', 100) / eot_trait['denominator']))
                                combatant['current_hp'] = min(combatant.get('max_hp', 100), combatant['current_hp'] + heal)
                                combat_log += f"🍄 {owner_str.strip()} **{combatant['name'].capitalize()}** restored HP using its {ability_name}!\n"

            # 3. Parasitic Drain (Leech Seed & Perish Song)
            for combatant, opponent, owner_str in combatants:
                if combatant['current_hp'] > 0 and 'leech-seed' in combatant.get('volatile_statuses', {}):
                    drain_dmg = max(1, math.floor(combatant.get('max_hp', 100) / 8))
                    drain_dmg = min(drain_dmg, combatant['current_hp']) 
                    combatant['current_hp'] -= drain_dmg
                    
                    if opponent['current_hp'] > 0:
                        opponent['current_hp'] = min(opponent.get('max_hp', 100), opponent['current_hp'] + drain_dmg)
                        
                    combat_log += f"🌱 {owner_str} **{combatant['name'].capitalize()}** had its health sapped by Leech Seed!\n"

                if combatant['current_hp'] > 0 and 'perish-song' in combatant.get('volatile_statuses', {}):
                    combatant['volatile_statuses']['perish-song'] -= 1
                    count = combatant['volatile_statuses']['perish-song']
                    if count <= 0:
                        combatant['current_hp'] = 0
                        combat_log += f"🎵 **{owner_str} {combatant['name'].capitalize()}**'s Perish count fell to 0 and it fainted!\n"
                    else:
                        combat_log += f"🎵 **{owner_str} {combatant['name'].capitalize()}**'s Perish count fell to {count}.\n"

            # 4. G-Max Ecological Disasters (Wildfire, Vine Lash, Cannonade, volcalith)
            # Match the active Pokémon with the hazards currently polluting THEIR side of the field
            for p_active, hazards, owner_str in [
                (new_p1_active, state['p1_hazards'], f"{state['p1'].display_name}'s"),
                (new_p2_active, state['p2_hazards'], f"{state['p2'].display_name}'s")
            ]:
                if p_active['current_hp'] > 0:
                    p_types = p_active.get('types', [])
                    
                    # Map the disaster to its immune typing and chat icon
                    disaster_map = {
                        'wildfire': ('fire', "🔥"),
                        'vine lash': ('grass', "🌿"),
                        'cannonade': ('water', "🌊"),
                        'volcalith': ('rock', "🪨")
                    }
                    
                    for disaster, (immune_type, icon) in disaster_map.items():
                        # If the hazard exists and has turns remaining...
                        if hazards.get(disaster, 0) > 0:
                            # 1. Biological Filter: Apply damage only if they aren't immune
                            if immune_type not in p_types:
                                dot_dmg = max(1, math.floor(p_active['max_hp'] / 6))
                                p_active['current_hp'] = max(0, p_active['current_hp'] - dot_dmg)
                                combat_log += f"{icon} **{owner_str} {p_active['name'].capitalize()}** is trapped in the {disaster}! (-{dot_dmg} HP)\n"
                            
                            # 2. Thermodynamic Decay: Decrement the timer for this side of the field
                            hazards[disaster] -= 1
                            if hazards[disaster] <= 0:
                                del hazards[disaster] # Clear it from memory when the 4 turns expire!
                                clear_msgs = {
                                    'wildfire': "The raging wildfire died down.",
                                    'vine lash': "The invasive vines withered away.",
                                    'cannonade': "The water vortex dispersed.",
                                    'volcalith': "The floating rocks vanished."
                                }
                                combat_log += f"✨ {clear_msgs[disaster]}\n"

            # 4. Kinetic Stun & Shield Cleanup
            for p_active in [new_p1_active, new_p2_active]:
                if 'volatile_statuses' in p_active:
                    p_active['volatile_statuses']['flinch'] = False
                    p_active['volatile_statuses']['protected'] = False
            # ==========================================
            # PHASE 4: FAINT CHECKS & UI REDRAW
            # ==========================================
            print("DEBUG: Preparing UI Redraw...")
            state['turn_number'] += 1
            state['commits'] = {p1_id: None, p2_id: None}
            
            p1_alive = any(p['current_hp'] > 0 for p in state['p1_team'])
            p2_alive = any(p['current_hp'] > 0 for p in state['p2_team'])
            
            if not p1_alive or not p2_alive:
                print("DEBUG: Match concluded.")
                if not p1_alive and not p2_alive:
                    result_str = "🤝 It's a draw!"
                    p1_win, p2_win = False, False
                elif p1_alive:
                    result_str = f"🏆 **{state['p1'].display_name}** wins the duel!"
                    p1_win, p2_win = True, False
                else:
                    result_str = f"🏆 **{state['p2'].display_name}** wins the duel!"
                    p1_win, p2_win = False, True

                rewards_log = ""

                # ==========================================
                # POST-MATCH REWARDS & DATABASE SYNC
                # ==========================================
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()

                # Loop through both players to process their unique rewards and save states
                for p_tag, opp_tag, is_win in [('p1', 'p2', p1_win), ('p2', 'p1', p2_win)]:
                    p_team = state[f"{p_tag}_team"]
                    opp_team = state[f"{opp_tag}_team"]
                    player_obj = state[p_tag]
                    user_id = state[f"{p_tag}_id"]

                    # 1. Calculate EXP (Yield from fainted opponents + flat win bonus)
                    defeated_opps = [opp for opp in opp_team if opp['current_hp'] <= 0]
                    total_exp = sum([opp.get('level', 50) * 15 for opp in defeated_opps])
                    if is_win:
                        total_exp += 500 # The winning researcher gets a massive bonus!

                    survivors = [p for p in p_team if p['current_hp'] > 0]

                    # 2. Distribute EXP and Level Up
                    if survivors and total_exp > 0:
                        exp_per = math.floor(total_exp / len(survivors))
                        rewards_log += f"\n\n📈 **{player_obj.display_name}'s** surviving team gained **{exp_per} EXP**!"

                        for p in survivors:
                            p['experience'] = p.get('experience', 0) + exp_per
                            threshold = p.get('level', 5) * 100

                            if p['experience'] >= threshold and p.get('level', 5) < 100:
                                p['level'] += 1
                                p['experience'] -= threshold
                                rewards_log += f"\n🎉 **{p['name'].capitalize()}** grew to Level {p['level']}!"

                                # --- EVOLUTION CHECK ---
                                if 'instance_id' in p:
                                    try:
                                        # Trigger the same evolution helper used in PvE
                                        evo_msg = await getattr(self, 'check_for_evolution', self.cog.check_for_evolution)(cursor, conn, user_id, p, combat_log)
                                        if evo_msg: rewards_log += evo_msg
                                    except Exception as e:
                                        print(f"DEBUG: Evolution check failed in PvP: {e}")

                    # 3. Sync the complete team state to the database! (Levels, EXP, and consumed items)
                    for p in p_team:
                        if 'instance_id' in p:
                            # 🚨 This line permanently deletes any Berries/Sashes consumed during the fight!
                            cursor.execute("""
                                UPDATE caught_pokemon
                                SET level = ?, experience = ?, held_item = ?
                                WHERE instance_id = ?
                            """, (p['level'], p['experience'], p.get('held_item', 'none'), p['instance_id']))

                conn.commit()
                conn.close()

                embed = discord.Embed(title="🏁 Ecological Duel Concluded!", description=f"{combat_log}\n{result_str}{rewards_log}", color=discord.Color.gold())
                self.active_battles.pop(p1_id, None)
                self.active_battles.pop(p2_id, None)
                return await state['message_obj'].edit(embed=embed, attachments=[], view=None)

            if new_p1_active['current_hp'] <= 0 or new_p2_active['current_hp'] <= 0:
                print("DEBUG: Faint detected. Entering Faint Phase.")
                state['phase'] = 'faint_swap' # Tell the engine we are in recovery mode!
                state['commits'] = {p1_id: None, p2_id: None}
                
                embed = discord.Embed(title="⚠️ Specimen Down!", description=f"{combat_log}\nWaiting for researchers to deploy replacements...", color=discord.Color.orange())
                await state['message_obj'].edit(embed=embed, attachments=[], view=None)
                
                # Ping P1 if they fainted, otherwise auto-ready them!
                if new_p1_active['current_hp'] <= 0:
                    view1 = PvPForcedSwapMenu(self, state, p1_id)
                    await state['p1'].send("⚠️ Your active specimen fainted! Select a replacement:", view=view1)
                else:
                    state['commits'][p1_id] = {'type': 'pass'}
                    
                # Ping P2 if they fainted, otherwise auto-ready them!
                if new_p2_active['current_hp'] <= 0:
                    view2 = PvPForcedSwapMenu(self, state, p2_id)
                    await state['p2'].send("⚠️ Your active specimen fainted! Select a replacement:", view=view2)
                else:
                    state['commits'][p2_id] = {'type': 'pass'}
                return

            embed = discord.Embed(title="⚔️ PvP Field Duel", description=combat_log, color=discord.Color.blue())
            
            p1_roster = "".join(["🔴" if p['current_hp'] > 0 else "⚫" for p in state['p1_team']])
            p2_roster = "".join(["🔴" if p['current_hp'] > 0 else "⚫" for p in state['p2_team']])
            
            embed.add_field(name=f"🟢 {state['p1'].display_name}'s {new_p1_active['name'].capitalize()}", value=f"Team: {p1_roster}", inline=True)
            embed.add_field(name=f"🔴 {state['p2'].display_name}'s {new_p2_active['name'].capitalize()}", value=f"Team: {p2_roster}", inline=True)
            embed.set_footer(text="Awaiting inputs from both researchers...")

            try:
                battle_file = await BattleDashboard.generate_battle_scene(
                    self,
                    new_p1_active['pokedex_id'], new_p2_active['pokedex_id'], 
                    new_p1_active['current_hp'], new_p1_active['max_hp'], 
                    new_p2_active['current_hp'], new_p2_active['max_hp'],
                    player_shiny=new_p1_active.get('is_shiny', False),
                    npc_shiny=new_p2_active.get('is_shiny', False),
                    weather=state['weather']['type'],
                    p_status=new_p1_active.get('status_condition'),
                    n_status=new_p2_active.get('status_condition'),
                    p_hazards=state['p1_hazards'],
                    n_hazards=state['p2_hazards']
                )
                
                embed.set_image(url=f"attachment://{battle_file.filename}")
                
            except Exception as img_err:
                print(f"DEBUG: Failed to generate image: {img_err}")
                battle_file = None

            dashboard_view = PvPDashboard(self, state)
            
            if battle_file:
                await state['message_obj'].edit(embed=embed, attachments=[battle_file], view=dashboard_view)
            else:
                await state['message_obj'].edit(embed=embed, attachments=[], view=dashboard_view)

            print("=== DEBUG: process_pvp_turn COMPLETE ===")

        except Exception as e:
            print("\n🚨 CRITICAL CRASH IN PVP TURN PROCESSING 🚨")
            import traceback
            traceback.print_exc()
            self.active_battles.pop(p1_id, None)
            self.active_battles.pop(p2_id, None)
            
            try:
                await state['message_obj'].channel.send("⚠️ A critical engine failure occurred during the turn calculation. Both researchers have been safely released.")
            except:
                pass

    async def process_faint_swaps(self, state):
        """Resolves forced swaps after a mid-turn KO and returns the engine to normal."""
        print("\n=== DEBUG: Entering process_faint_swaps ===")
        
        try:
            p1_id, p2_id = state['p1_id'], state['p2_id']
            c1, c2 = state['commits'][p1_id], state['commits'][p2_id]
            
            combat_log = f"**Turn {state['turn_number']} (Recovery)**\n\n"
            
            # --- Process Player 1's Replacement ---
            if c1 and c1['type'] == 'forced_swap':
                bench_idx = c1['data']
                state['p1_active_index'] = bench_idx
                new_p1 = state['p1_team'][bench_idx]
                combat_log += f"🔄 **{state['p1'].display_name}** deployed **{new_p1['name'].capitalize()}**!\n"
                
                # Safely execute hazards
                try:
                    if 'TYPE_CHART' in globals():
                        hz_log = apply_entry_hazards(new_p1, state['p1_hazards'], TYPE_CHART, f"{state['p1'].display_name}'s")
                        if hz_log: combat_log += hz_log
                except Exception as e:
                    print(f"DEBUG: P1 Hazard crash ignored: {e}")

                # Safely execute abilities
                try:
                    if new_p1['current_hp'] > 0:
                        combat_log = trigger_single_entry_ability(new_p1, state['p2_team'][state['p2_active_index']], f"{state['p1'].display_name}'s", state, combat_log)
                except Exception as e:
                    print(f"DEBUG: P1 Ability crash ignored: {e}")

            # --- Process Player 2's Replacement ---
            if c2 and c2['type'] == 'forced_swap':
                bench_idx = c2['data']
                state['p2_active_index'] = bench_idx
                new_p2 = state['p2_team'][bench_idx]
                combat_log += f"🔄 **{state['p2'].display_name}** deployed **{new_p2['name'].capitalize()}**!\n"
                
                try:
                    if 'TYPE_CHART' in globals():
                        hz_log = apply_entry_hazards(new_p2, state['p2_hazards'], TYPE_CHART, f"{state['p2'].display_name}'s")
                        if hz_log: combat_log += hz_log
                except Exception as e:
                    print(f"DEBUG: P2 Hazard crash ignored: {e}")

                try:
                    if new_p2['current_hp'] > 0:
                        combat_log = trigger_single_entry_ability(new_p2, state['p1_team'][state['p1_active_index']], f"{state['p2'].display_name}'s", state, combat_log)
                except Exception as e:
                    print(f"DEBUG: P2 Ability crash ignored: {e}")

            # ==========================================
            # STATE RESTORATION & UI REDRAW
            # ==========================================
            print("DEBUG: Faint Swaps processed. Restoring normal turn logic...")
            
            # 🚨 THIS UNLOCKS THE GAME SO STANDARD SWAPS WORK AGAIN!
            state['phase'] = 'turn'
            state['commits'] = {p1_id: None, p2_id: None}
            
            # Retrieve the newly updated pointers for the UI
            p1_active = state['p1_team'][state['p1_active_index']]
            p2_active = state['p2_team'][state['p2_active_index']]
            
            embed = discord.Embed(title="⚔️ PvP Field Duel", description=combat_log, color=discord.Color.blue())
            
            p1_roster = "".join(["🔴" if p['current_hp'] > 0 else "⚫" for p in state['p1_team']])
            p2_roster = "".join(["🔴" if p['current_hp'] > 0 else "⚫" for p in state['p2_team']])
            
            # Draw the fresh names to the Embed!
            embed.add_field(name=f"🟢 {state['p1'].display_name}'s {p1_active['name'].capitalize()}", value=f"Team: {p1_roster}", inline=True)
            embed.add_field(name=f"🔴 {state['p2'].display_name}'s {p2_active['name'].capitalize()}", value=f"Team: {p2_roster}", inline=True)
            embed.set_footer(text="Awaiting inputs from both researchers...")

            # Safely generate the image
            try:
                battle_file = await BattleDashboard.generate_battle_scene(
                    self,
                    p1_active['pokedex_id'], p2_active['pokedex_id'], 
                    p1_active['current_hp'], p1_active['max_hp'], 
                    p2_active['current_hp'], p2_active['max_hp'],
                    player_shiny=p1_active.get('is_shiny', False), npc_shiny=p2_active.get('is_shiny', False),
                    weather=state['weather']['type'],
                    p_status=p1_active.get('status_condition'), n_status=p2_active.get('status_condition'),
                    p_hazards=state['p1_hazards'], n_hazards=state['p2_hazards']
                )
                embed.set_image(url=f"attachment://{battle_file.filename}")
            except Exception as img_err:
                print(f"DEBUG: Image generation failed in Faint Phase: {img_err}")
                battle_file = None

            dashboard_view = PvPDashboard(self, state)
            
            if battle_file:
                await state['message_obj'].edit(embed=embed, attachments=[battle_file], view=dashboard_view)
            else:
                # If image fails, clear old attachments so ghost Pokémon don't linger!
                await state['message_obj'].edit(embed=embed, attachments=[], view=dashboard_view)
                
            print("=== DEBUG: process_faint_swaps COMPLETE ===")

        except Exception as master_err:
            print("\n🚨 CRITICAL CRASH IN FAINT SWAPS 🚨")
            import traceback
            traceback.print_exc()
            
            # Unlock players if it completely dies
            self.active_battles.pop(state['p1_id'], None)
            self.active_battles.pop(state['p2_id'], None)
            try:
                await state['message_obj'].channel.send("⚠️ A critical engine failure occurred during recovery. Researchers released.")
            except: pass

    @commands.command(name="challenge")
    @checks.has_started()
    @checks.is_authorized()
    @checks.is_not_in_combat()
    async def challenge_entity(self, ctx, entity_type: str = None, target: str = None):
        """Initiates a tactical skirmish against a high-level ecological target."""
        user_id = str(ctx.author.id)
        
        if not entity_type or not target:
            return await ctx.send("⚠️ **Syntax Error:** Please specify who you are challenging (e.g., `!challenge warden canopy`).")
            
        if entity_type.lower() != "warden":
            return await ctx.send("Currently, you can only challenge Sector `warden`s.")
            
        biome = target.lower()
        
        if biome not in WARDEN_ROSTER:
            return await ctx.send(f"⚠️ Sector Warden for **{biome.title()}** does not exist or is currently on leave.")
            
        warden_data = WARDEN_ROSTER[biome]
        
        # Check if they are already in a battle
        if hasattr(self, 'active_battles') and user_id in self.active_battles:
            return await ctx.send("🛑 You are already engaged in a tactical skirmish! Finish it or flee first.")
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        try:
            # 1. Progression Check: Do they have the Visa?
            cursor.execute("SELECT unlocked_visas FROM users WHERE user_id = ?", (user_id,))
            user_data = cursor.fetchone()
            visas = user_data[0] if user_data and user_data[0] else "canopy"
            
            if biome not in visas.split(','):
                conn.close()
                return await ctx.send(f"⛔ **ACCESS DENIED:** You lack the clearance to challenge the {warden_data['title']}. Obtain the Visa for this sector first.")
            
            # 2. Compile the Warden's Tactical Team (Hydrating the roster)
            compiled_team = []
            for pkmn in warden_data['team']:
                cursor.execute("""
                    SELECT stat_name, base_value, pokedex_id
                    FROM base_pokemon_stats 
                    WHERE pokedex_id = (SELECT pokedex_id FROM base_pokemon_species WHERE name = ?)
                """, (pkmn['name'],))
                
                rows = cursor.fetchall()
                if not rows:
                    continue # Skip if database error
                
                stats = {row[0]: row[1] for row in rows}
                p_id = rows[0][2]
                
                real_hp = calculate_real_stat('hp', stats.get('hp', 0), pkmn['ivs']['hp'], pkmn['evs']['hp'], pkmn['level'])
                real_atk = calculate_real_stat('attack', stats.get('attack', 0), pkmn['ivs']['attack'], pkmn['evs']['attack'], pkmn['level'])
                real_def = calculate_real_stat('defense', stats.get('defense', 0), pkmn['ivs']['defense'], pkmn['evs']['defense'], pkmn['level'])
                real_spa = calculate_real_stat('special-attack', stats.get('special-attack', 0), pkmn['ivs']['sp_atk'], pkmn['evs']['sp_atk'], pkmn['level'])
                real_spd = calculate_real_stat('special-defense', stats.get('special-defense', 0), pkmn['ivs']['sp_def'], pkmn['evs']['sp_def'], pkmn['level'])
                real_spe = calculate_real_stat('speed', stats.get('speed', 0), pkmn['ivs']['speed'], pkmn['evs']['speed'], pkmn['level'])
                
                # Make sure the moves have 'max_pp'
                hydrated_moves = []
                for m in pkmn['moves']:
                    hydrated_moves.append({'name': m['name'], 'pp': m['pp'], 'max_pp': m['max_pp']})

                compiled_member = {
                    'pokedex_id': p_id,
                    'name': pkmn['name'],
                    'level': pkmn['level'],
                    'types': pkmn['types'],
                    'held_item': pkmn['held_item'],
                    'max_hp': real_hp, 'current_hp': real_hp,
                    'stats': {'hp': real_hp, 'attack': real_atk, 'defense': real_def, 'sp_atk': real_spa, 'sp_def': real_spd, 'speed': real_spe},
                    'moves': hydrated_moves,
                    'status_condition': None,
                    'volatile_statuses': {},
                    'is_shiny': False,
                    'ability': 'pressure', # Give Wardens a default tough ability if unassigned!
                    'gmax_factor': 0
                }
                compiled_team.append(compiled_member)

            # 3. Load the Player's Team (Identical to npc_encounter)
            player_team = []
            cursor.execute("""
                SELECT cp.instance_id, cp.pokedex_id, s.name, cp.level, cp.nature,
                    cp.iv_hp, cp.iv_attack, cp.iv_defense, cp.iv_sp_atk, cp.iv_sp_def, cp.iv_speed,
                    cp.ev_hp, cp.ev_attack, cp.ev_defense, cp.ev_sp_atk, cp.ev_sp_def, cp.ev_speed,
                    cp.move_1, cp.move_2, cp.move_3, cp.move_4, cp.is_shiny, cp.held_item, cp.gmax_factor, cp.ability, cp.experience
                FROM user_party up
                JOIN caught_pokemon cp ON up.instance_id = cp.instance_id
                JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                WHERE up.user_id = ?
                ORDER BY up.slot ASC
            """, (user_id,))
            
            
            party_rows = cursor.fetchall()
            if not party_rows:
                conn.close()
                return await ctx.send("⚠️ You must assign at least one specimen to your fieldwork roster using `!party add 1 [Tag ID]` before engaging a Warden!")

            for row in party_rows:
                tag, p_id, p_name, p_lvl, p_nature = row[0:5]
                p_ivs = {'hp': row[5], 'attack': row[6], 'defense': row[7], 'sp_atk': row[8], 'sp_def': row[9], 'speed': row[10]}
                p_evs = {'hp': row[11], 'attack': row[12], 'defense': row[13], 'sp_atk': row[14], 'sp_def': row[15], 'speed': row[16]}
                raw_moves = [m for m in row[17:21] if m and m != 'none']
                p_moves = []
                for m_name in raw_moves:
                    cursor.execute("SELECT pp FROM base_moves WHERE name = ?", (m_name,))
                    pp_row = cursor.fetchone()
                    pp_val = pp_row[0] if pp_row else 5 
                    p_moves.append({'name': m_name, 'pp': pp_val, 'max_pp': pp_val})

                cursor.execute("SELECT type_name FROM base_pokemon_types WHERE pokedex_id = ?", (p_id,))
                p_types = [t[0] for t in cursor.fetchall()]

                is_shiny = row[21]
                held_item = row[22]
                gmax_factor = row[23]
                ability = row[24]
                experience = row[25]
                
                p_base = fetch_base_stats(cursor, p_id)
                p_final_stats = calculate_stats(p_base, p_ivs, p_evs, p_lvl, p_nature)
                
                player_team.append({
                    'instance_id': tag, 'pokedex_id': p_id, 'name': p_name, 'level': p_lvl,
                    'max_hp': p_final_stats['hp'], 'current_hp': p_final_stats['hp'],
                    'stats': p_final_stats, 'moves': p_moves, 'status_condition': None, 'is_shiny': is_shiny, 
                    'held_item': held_item, 'gmax_factor': gmax_factor, 'ability': ability, 'types': p_types,
                    'experience': experience, 'volatile_statuses': {} 
                })

            # ==========================================
            # REGULATION CHECK: SECTOR LEVEL CAPS
            # ==========================================
            SECTOR_CAPS = {
                'canopy': 40, #100 for testing purposes
                'trench': 45,
                'core': 60,
                'sprawl': 75
            }
            
            max_allowed_level = SECTOR_CAPS.get(biome, 100) # Fallback to 100
            
            # Scan the player's active party for violations
            overleveled_specimens = [p for p in player_team if p['level'] > max_allowed_level]
            
            if overleveled_specimens:
                conn.close()
                names = ", ".join([p['name'].capitalize() for p in overleveled_specimens])
                return await ctx.send(f"⛔ **ECOLOGICAL REGULATION:** Your roster contains specimens that exceed the Sector Level Cap (Lv. {max_allowed_level}).\n\nViolating Specimens: **{names}**.\n\nPlease deposit them in your PC or swap them out before engaging the {warden_data['title']}.")
            # ==========================================

            # 4. Key Item Scanner
            cursor.execute("""
                SELECT item_name FROM user_inventory 
                WHERE user_id = ? AND item_name IN ('dynamax-band', 'z-ring', 'mega-bracelet') AND quantity > 0
            """, (user_id,))
            owned_key_items = [row[0] for row in cursor.fetchall()]
            access_ledger = {
                'dynamax_band': 'dynamax-band' in owned_key_items,
                'z_ring': 'z-ring' in owned_key_items,
                'mega_bracelet': 'mega-bracelet' in owned_key_items
            }
            
            conn.close()

            
            # 5. Initialize the Battle State Memory
            self.active_battles[user_id] = {
                'player_team': player_team,
                'npc_team': compiled_team,
                'active_player_index': 0, # Slot 1
                'active_npc_index': 0,    # Slot 1
                'turn_number': 1,
                'weather': {'type': 'none', 'duration': 0},
                'adaptation': {'used': False, 'active': False, 'type': 'none', 'turns': 0, 'backup': {}},
                'key_items': access_ledger,
                
                # ==========================================
                # ENVIRONMENTAL HAZARD TRACKERS
                # ==========================================
                # 'player_hazards' are rocks/spikes currently on YOUR side of the field
                'player_hazards': {
                    'stealth-rock': False,
                    'spikes': 0,           # Stacks up to 3
                    'toxic-spikes': 0,     # Stacks up to 2
                    'sticky-web': False
                },
                # 'npc_hazards' are rocks/spikes currently on the ENEMY'S side of the field
                'npc_hazards': {
                    'stealth-rock': False,
                    'spikes': 0,
                    'toxic-spikes': 0,
                    'sticky-web': False
                }
                # ==========================================
            }

            # 6. Display the Encounter
            p_lead = player_team[0]
            n_lead = compiled_team[0]
            
            p_roster = "".join(["🔴" for _ in player_team])
            n_roster = "".join(["🔴" for _ in compiled_team])

            combat_log = f"**{ctx.author.name}** vs. **{warden_data['title']}**\n\n"
            combat_log += f"The Warden sent out **{n_lead['name'].capitalize()}**!\n"
            combat_log += f"Go, **{p_lead['name'].capitalize()}**!\n\n"

            state = self.active_battles[user_id]
            combat_log = trigger_single_entry_ability(p_lead, n_lead, "Your", state, combat_log)
            combat_log = trigger_single_entry_ability(n_lead, p_lead, "The Warden's", state, combat_log)

            embed = discord.Embed(title=f"🛡️ Warden Skirmish: {biome.title()} Sector", color=discord.Color.dark_purple())
            embed.description = combat_log
            
            embed.add_field(name=f"🟢 Your {p_lead['name'].capitalize()}", value=f"Team: {p_roster}", inline=True)
            embed.add_field(name=f"🔴 {warden_data['title']}'s {n_lead['name'].capitalize()}", value=f"Team: {n_roster}", inline=True)
            embed.set_footer(text="Defeat the Warden to secure clearance for the next biome.")
            
            # Since we just fired entry abilities, grab the latest weather from the state!
            current_weather = state.get('weather', {'type': 'none'})['type']

            # Generate the Battle Image
            battle_file = await BattleDashboard.generate_battle_scene(
                self,
                player_id=p_lead['pokedex_id'], 
                npc_id=n_lead['pokedex_id'],
                p_hp=p_lead['current_hp'],
                p_max_hp=p_lead['max_hp'],
                n_hp=n_lead['current_hp'],
                n_max_hp=n_lead['max_hp'],
                player_shiny=p_lead.get('is_shiny', False), 
                npc_shiny=n_lead.get('is_shiny', False),
                # ==========================================
                # PASSING THE OVERLAY DATA TO THE RENDERER
                # ==========================================
                weather=current_weather,
                p_status=p_lead.get('status_condition'),
                n_status=n_lead.get('status_condition'),
                p_hazards=state.get('player_hazards'),
                n_hazards=state.get('npc_hazards')
            )

            # Dynamically grab the new randomized filename!
            if battle_file:
                embed.set_image(url=f"attachment://{battle_file.filename}")
            
            dashboard_view = BattleDashboard(self, user_id, ctx)
            await ctx.send(embed=embed, files=[battle_file], view=dashboard_view)

        except Exception as e:
            print("\n🚨 CRITICAL CRASH IN WARDEN INITIALIZATION 🚨")
            import traceback
            traceback.print_exc()
            await ctx.send("⚠️ A critical failure occurred while engaging the Warden. Check the console.")
            if conn: conn.close()

    @commands.command(name="tech", aliases=["techmoves"])
    @checks.has_started()
    @checks.is_authorized()
    async def view_tms(self, ctx):
        """Displays all Technical Machines (TMs) currently in your field notebook."""
        user_id = str(ctx.author.id)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        try:
            # Fetch TMs from the database
            cursor.execute("SELECT tm_name FROM user_tms WHERE user_id = ?", (user_id,))
            tms = cursor.fetchall()
            
            if not tms:
                conn.close()
                return await ctx.send("🎒 You haven't acquired any Technical Machines yet. Complete more research or visit the market!")
                
            embed = discord.Embed(
                title="💿 Technical Machines (TMs)",
                description="Specialized training routines available for your specimens:",
                color=discord.Color.teal()
            )
            
            # Format the list cleanly
            tm_list = ""
            for i, (move_name,) in enumerate(tms, 1): # The '1' makes the list start at 1 instead of 0
                tm_list += f"`{i}.` **{move_name.replace('-', ' ').title()}**\n"
                
            embed.add_field(name="Available Training Data", value=tm_list, inline=False)
            await ctx.send(embed=embed)
            
        except Exception as e:
            print(f"TM Viewer Error: {e}")
            await ctx.send("❌ Error accessing your technical data.")
        finally:
            conn.close()

    @commands.command(name="tm")
    @checks.has_started()
    @checks.is_authorized()
    async def teach_move(self, ctx, instance_id: str, *, tm_name: str):
        """Teaches a new move to a specific specimen using a TM (Debug Version)."""
        print(f"\n--- DEBUG: !tm COMMAND INITIATED ---")
        
        try:
            user_id = str(ctx.author.id)
            clean_tm_name = tm_name.lower().replace(" ", "-")
            print(f"DEBUG: Parsed Input -> User: {user_id}, ID: {instance_id}, TM: {clean_tm_name}")

            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()

            # 1. VERIFY OWNERSHIP
            print("DEBUG 1: Querying caught_pokemon...")
            # We use a relational JOIN to grab the species name from the master registry!
            cursor.execute("""
                SELECT cp.pokedex_id, s.name, cp.move_1, cp.move_2, cp.move_3, cp.move_4, cp.instance_id
                FROM caught_pokemon cp
                JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                WHERE cp.instance_id LIKE ? AND cp.user_id = ?
            """, (f"{instance_id}%", user_id))
            
            specimen = cursor.fetchone()
            print(f"DEBUG 1 RESULT: {specimen}")

            if not specimen:
                conn.close()
                print("DEBUG 1 FAILED: Specimen not found or ID mismatch.")
                return await ctx.send("⚠️ You do not own a specimen with that ID!")

            p_id, p_name, m1, m2, m3, m4, exact_instance_id = specimen
            current_moves = [m for m in [m1, m2, m3, m4] if m and m != 'none']
            print(f"DEBUG 1 SUCCESS: Found {p_name} (Exact ID: {exact_instance_id}). Current Moves: {current_moves}")

            # 2. VERIFY TM INVENTORY
            print("DEBUG 2: Querying user_tms inventory...")
            cursor.execute("SELECT quantity FROM user_tms WHERE user_id = ? AND tm_name = ?", (user_id, clean_tm_name))
            tm_data = cursor.fetchone()
            print(f"DEBUG 2 RESULT: {tm_data}")

            if not tm_data or tm_data[0] <= 0:
                conn.close()
                print("DEBUG 2 FAILED: User does not own this TM.")
                return await ctx.send(f"⚠️ You do not have the TM for `{clean_tm_name.replace('-', ' ').title()}` in your inventory!")

            # 3. VERIFY DUPLICATION
            print("DEBUG 3: Checking for duplicate moves...")
            if clean_tm_name in current_moves:
                conn.close()
                print("DEBUG 3 FAILED: Specimen already knows this move.")
                return await ctx.send(f"⚠️ **{p_name.capitalize()}** already knows `{clean_tm_name.replace('-', ' ').title()}`!")
            print("DEBUG 3 SUCCESS: Move is not a duplicate.")

            # 4. VERIFY BIOLOGICAL COMPATIBILITY
            print("DEBUG 4: Checking species_movepool compatibility...")
            cursor.execute("SELECT 1 FROM species_movepool WHERE pokedex_id = ? AND move_name = ?", (p_id, clean_tm_name))
            is_compatible = cursor.fetchone()
            print(f"DEBUG 4 RESULT: {is_compatible}")

            if not is_compatible:
                conn.close()
                print("DEBUG 4 FAILED: Incompatible biology.")
                return await ctx.send(f"🧬 **{p_name.capitalize()}**'s biology is incompatible with `{clean_tm_name.replace('-', ' ').title()}`.")
            print("DEBUG 4 SUCCESS: Specimen is compatible with this TM.")

            # ==========================================
            # 5. EXECUTE THE GENETIC OVERWRITE
            # ==========================================
            print("DEBUG 5: Executing genetic overwrite...")
            if len(current_moves) < 4:
                empty_col = "move_1" if not m1 or m1 == 'none' else \
                            "move_2" if not m2 or m2 == 'none' else \
                            "move_3" if not m3 or m3 == 'none' else "move_4"

                print(f"DEBUG 5: Found empty slot at {empty_col}. Injecting TM...")
                cursor.execute("UPDATE user_tms SET quantity = quantity - 1 WHERE user_id = ? AND tm_name = ?", (user_id, clean_tm_name))
                cursor.execute(f"UPDATE caught_pokemon SET {empty_col} = ? WHERE instance_id = ?", (clean_tm_name, exact_instance_id))
                conn.commit()
                conn.close()
                
                print("--- DEBUG: !tm COMMAND SUCCESSFUL ---")
                return await ctx.send(f"💿 You booted up the TM!\n✨ **{p_name.capitalize()}** learned `{clean_tm_name.replace('-', ' ').title()}`!")

            print("DEBUG 5: Specimen has 4 moves. Spawning Overwrite UI...")
            conn.close()
            
            embed = discord.Embed(
                title="⚠️ Genetic Capacity Reached",
                description=f"**{p_name.capitalize()}** wants to learn `{clean_tm_name.replace('-', ' ').title()}`, but it already knows 4 moves.\n\nWhich move should it forget?",
                color=discord.Color.orange()
            )
            
            view = TeachMenu(self, user_id, exact_instance_id, p_name, clean_tm_name, current_moves)
            await ctx.send(embed=embed, view=view)
            print("--- DEBUG: !tm COMMAND SPAWNED UI ---")

        except Exception as e:
            import traceback
            print("\n🚨 CRITICAL CRASH IN !tm COMMAND 🚨")
            traceback.print_exc()
            await ctx.send("❌ A critical database or syntax error occurred while trying to process the TM. Check the terminal.")


    @commands.command(name="moves", aliases=["attacks"])
    @checks.has_started()
    @checks.is_authorized()
    async def quick_moves(self, ctx, tag_id: str = None):
        """Quickly view a specimen's equipped behaviors."""
        user_id = str(ctx.author.id)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 1. Resolve Target (Partner or Tag)
        if not tag_id:
            cursor.execute("SELECT active_partner FROM users WHERE user_id = ?", (user_id,))
            partner_data = cursor.fetchone()
            if partner_data and partner_data[0]:
                tag_id = partner_data[0]
            else:
                conn.close()
                return await ctx.send("⚠️ You don't have an Active Partner equipped! Specify a Box Number or Tag ID.")

        # 2. Fast Database Query using CTE for Dynamic Indexing
        if tag_id.lower() in ["new", "latest", "last"]:
            cursor.execute("""
                WITH Roster AS (
                    SELECT cp.instance_id, cp.level, s.name, cp.move_1, cp.move_2, cp.move_3, cp.move_4,
                           ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                    FROM caught_pokemon cp JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                    WHERE cp.user_id = ?
                ) 
                SELECT * FROM Roster ORDER BY box_number DESC LIMIT 1
            """, (user_id,))
            
        elif tag_id.isdigit() and len(tag_id) <= 6:
            # It's a Box Number!
            cursor.execute("""
                WITH Roster AS (
                    SELECT cp.instance_id, cp.level, s.name, cp.move_1, cp.move_2, cp.move_3, cp.move_4,
                           ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                    FROM caught_pokemon cp JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                    WHERE cp.user_id = ?
                ) 
                SELECT * FROM Roster WHERE box_number = ?
            """, (user_id, int(tag_id)))
            
        else:
            # It's a UUID Tag!
            cursor.execute("""
                WITH Roster AS (
                    SELECT cp.instance_id, cp.level, s.name, cp.move_1, cp.move_2, cp.move_3, cp.move_4,
                           ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                    FROM caught_pokemon cp JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                    WHERE cp.user_id = ?
                ) 
                SELECT * FROM Roster WHERE instance_id LIKE ?
            """, (user_id, f"{tag_id}%"))
            
        pokemon_data = cursor.fetchone()
        conn.close()
        
        if not pokemon_data:
            return await ctx.send("❌ Could not locate that specimen. Check your Box Number or Tag ID.")
            
        # Unpack the 8 variables we selected in the CTE
        actual_tag, level, name, m1, m2, m3, m4, box_number = pokemon_data
        
        # 3. Build the Lightweight UI
        embed = discord.Embed(title=f"⚔️ Active Behaviors: {name.capitalize()}", color=discord.Color.green())
        embed.description = f"**Level {level}** | Box `#{box_number}` | Tag ID: `{actual_tag[:8]}`"
        
        equipped_moves = [m1, m2, m3, m4]
        for i, move_name in enumerate(equipped_moves, start=1):
            display = f"**{move_name.replace('-', ' ').title()}**" if move_name and move_name != 'none' else "*Empty Slot*"
            embed.add_field(name=f"Slot {i}", value=display, inline=False)
            
        embed.set_footer(text="Use !moveset [Box Number] for detailed stats and learnable moves.")
        await ctx.send(embed=embed)

    @commands.command(name="moveset", aliases=["movedata"])
    @checks.has_started()
    @checks.is_authorized()
    async def detailed_moveset(self, ctx, tag_id: str = None):
        """Analyzes biological movepool potential with full statistics."""
        user_id = str(ctx.author.id)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 1. Resolve Target
        if not tag_id:
            cursor.execute("SELECT active_partner FROM users WHERE user_id = ?", (user_id,))
            partner_data = cursor.fetchone()
            if partner_data and partner_data[0]:
                # We can use the partner's UUID directly!
                cursor.execute("""
                    SELECT cp.instance_id, cp.pokedex_id, cp.level, s.name,
                           ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                    FROM caught_pokemon cp JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                    WHERE cp.instance_id = ? AND cp.user_id = ?
                """, (partner_data[0], user_id))
            else:
                conn.close()
                return await ctx.send("⚠️ You don't have an Active Partner equipped! Specify a Box Number or Tag ID.")

        elif tag_id.lower() in ["new", "latest", "last"]:
            cursor.execute("""
                WITH Roster AS (
                    SELECT cp.instance_id, cp.pokedex_id, cp.level, s.name,
                           ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                    FROM caught_pokemon cp JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                    WHERE cp.user_id = ?
                )
                SELECT instance_id, pokedex_id, level, name, box_number
                FROM Roster ORDER BY box_number DESC LIMIT 1
            """, (user_id,))
            
        elif tag_id.isdigit() and len(tag_id) <= 6:
            # It's a Box Number!
            cursor.execute("""
                WITH Roster AS (
                    SELECT cp.instance_id, cp.pokedex_id, cp.level, s.name,
                           ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                    FROM caught_pokemon cp JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                    WHERE cp.user_id = ?
                )
                SELECT instance_id, pokedex_id, level, name, box_number
                FROM Roster WHERE box_number = ?
            """, (user_id, int(tag_id)))
            
        else:
            # It's a UUID Tag!
            cursor.execute("""
                WITH Roster AS (
                    SELECT cp.instance_id, cp.pokedex_id, cp.level, s.name,
                           ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                    FROM caught_pokemon cp JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                    WHERE cp.user_id = ?
                )
                SELECT instance_id, pokedex_id, level, name, box_number
                FROM Roster WHERE instance_id LIKE ?
            """, (user_id, f"{tag_id}%"))
            
        pokemon_data = cursor.fetchone()
        
        if not pokemon_data:
            conn.close()
            return await ctx.send("❌ Could not locate that specimen. Check your Box Number or Tag ID.")
            
        actual_tag, poke_id, level, name, box_number = pokemon_data
        
        # 2. Advanced Analytics Query: Includes Learn Method and Sorting!
        cursor.execute("""
            SELECT sm.move_name, sm.learn_method, MIN(sm.level_learned) as first_learned,
                bm.type, bm.power, bm.accuracy, bm.damage_class, bm.pp
            FROM species_movepool sm
            LEFT JOIN base_moves bm ON sm.move_name = bm.name
            WHERE sm.pokedex_id = ? 
            GROUP BY sm.move_name, sm.learn_method
            ORDER BY 
                CASE sm.learn_method 
                    WHEN 'level-up' THEN 1 
                    WHEN 'machine' THEN 2 
                    WHEN 'egg' THEN 3 
                    ELSE 4 
                END,
                first_learned ASC, sm.move_name ASC 
        """, (poke_id,))
        
        raw_movepool = cursor.fetchall()
        conn.close()

        # 3. Data Packaging (Tricking the Paginator!)
        poke_info = {"name": name, "level": level, "tag": actual_tag, "box_number": box_number}
        move_data_list = []
        
        for row in raw_movepool:
            method = row[1]
            
            # Convert the method into a clean string for your UI
            if method == 'level-up':
                display_lvl = f"Lv. {row[2]}"
            elif method == 'machine':
                display_lvl = "TM"
            elif method == 'egg':
                display_lvl = "Egg"
            else:
                display_lvl = "Tutor"

            move_data_list.append({
                'name': row[0],
                'lvl': display_lvl,
                'type': row[3] or 'unknown',
                'power': row[4],
                'accuracy': row[5],
                'class': row[6] or 'status',
                'pp': row[7] or '?'
            })

        # 4. Trigger the Paginator
        view = DetailedMovepoolPaginator(ctx, poke_info, move_data_list)
        await ctx.send(embed=view.create_embed(), view=view)

    @commands.command(name="party", aliases=["team", "roster"])
    @checks.has_started()
    @checks.is_authorized()
    async def manage_party(self, ctx, action: str = "view", slot: int = None, tag_id: str = None):
        # 🧪 SAFETY NET: Wraps the entire command to catch silent crashes!
        try:
            print(f"\n=== DEBUG: !party command initiated by {ctx.author.name} ===")
            print(f"DEBUG: Parsed Arguments -> action: '{action}', slot: {slot}, tag_id: '{tag_id}'")
            
            user_id = str(ctx.author.id)
            action = action.lower()
            
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()

            # --- ACTION: ADD TO PARTY ---
            if action in ["add", "set", "equip"]:
                print("DEBUG: Routing to ADD logic.")
                
                if slot is None or tag_id is None:
                    print("DEBUG: Aborted. Missing slot or tag_id.")
                    conn.close()
                    return await ctx.send("⚠️ Usage: `!party add [slot 1-6] [Box Number or Tag ID]`")
                    
                if int(slot) < 1 or int(slot) > 6:
                    print("DEBUG: Aborted. Slot out of bounds.")
                    conn.close()
                    return await ctx.send("⚠️ A fieldwork roster can only hold up to 6 specimens.")
                    
                print(f"DEBUG: Validating tag_id '{tag_id}'...")
                
                # Verify they own the specimen using CTE for Box Number support
                if tag_id.isdigit() and len(tag_id) <= 6:
                    print("DEBUG: Executing Box Number CTE Query.")
                    cursor.execute("""
                        WITH Roster AS (
                            SELECT cp.instance_id, s.name, ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                            FROM caught_pokemon cp
                            JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                            WHERE cp.user_id = ?
                        ) SELECT instance_id, name FROM Roster WHERE box_number = ?
                    """, (user_id, int(tag_id)))
                else:
                    print("DEBUG: Executing standard UUID Like Query.")
                    cursor.execute("""
                        SELECT cp.instance_id, s.name 
                        FROM caught_pokemon cp 
                        JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id 
                        WHERE cp.instance_id LIKE ? AND cp.user_id = ?
                    """, (f"{tag_id}%", user_id))
                    
                pokemon = cursor.fetchone()
                print(f"DEBUG: SQL Fetch Result -> {pokemon}")
                
                if not pokemon:
                    print("DEBUG: Aborted. Specimen not found.")
                    conn.close()
                    return await ctx.send("❌ Could not find that specimen in your survey notebook. Check the Box Number or Tag.")
                    
                actual_id, poke_name = pokemon
                print(f"DEBUG: Target identified -> ID: {actual_id}, Name: {poke_name}")
                    
                # Check if the specimen is already in another slot
                cursor.execute("SELECT slot FROM user_party WHERE user_id = ? AND instance_id = ?", (user_id, actual_id))
                existing_slot = cursor.fetchone()
                print(f"DEBUG: Existing slot check -> {existing_slot}")
                
                if existing_slot:
                    conn.close()
                    return await ctx.send(f"⚠️ That **{poke_name.capitalize()}** is already assigned to Slot {existing_slot[0]}!")

                print("DEBUG: Executing Database UPSERT...")
                # Upsert the new party member
                cursor.execute("""
                    INSERT INTO user_party (user_id, slot, instance_id) 
                    VALUES (?, ?, ?)
                    ON CONFLICT(user_id, slot) DO UPDATE SET instance_id = excluded.instance_id;
                """, (user_id, slot, actual_id))
                
                conn.commit()
                print("DEBUG: Upsert committed successfully!")
                await ctx.send(f"✅ **{poke_name.capitalize()}** has been assigned to Roster Slot {slot}!")

             # --- ACTION: REMOVE FROM PARTY ---
            elif action in ["remove", "clear"]:
                if not slot:
                    conn.close()
                    return await ctx.send("⚠️ Usage: `!party remove [slot 1-6]`")
                    
                cursor.execute("DELETE FROM user_party WHERE user_id = ? AND slot = ?", (user_id, slot))
                conn.commit()
                await ctx.send(f"🧹 Roster Slot {slot} has been cleared.")

            # --- ACTION: VIEW PARTY ---
            elif action == "view":
                # We inject the Roster CTE here too so players can see their Box Numbers in the party view!
                cursor.execute("""
                    WITH Roster AS (
                        SELECT instance_id, ROW_NUMBER() OVER(ORDER BY rowid ASC) as box_number
                        FROM caught_pokemon
                        WHERE user_id = ?
                    )
                    SELECT up.slot, cp.instance_id, s.name, cp.level, cp.happiness,
                        cp.move_1, cp.move_2, cp.move_3, cp.move_4, r.box_number
                    FROM user_party up
                    JOIN caught_pokemon cp ON up.instance_id = cp.instance_id
                    JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                    JOIN Roster r ON cp.instance_id = r.instance_id
                    WHERE up.user_id = ?
                    ORDER BY up.slot ASC
                """, (user_id, user_id))
                
                party_data = cursor.fetchall()
                
                if not party_data:
                    conn.close()
                    return await ctx.send("Your fieldwork roster is currently empty! Use `!party add 1 [Box Number]` to start assembling your team.")
                    
                embed = discord.Embed(title=f"📋 {ctx.author.name}'s Fieldwork Roster", color=discord.Color.blue())
                
                # Track active slots to show empty ones
                filled_slots = {row[0]: row for row in party_data}
                
                for i in range(1, 7):
                    if i in filled_slots:
                        slot, tag, name, level, happiness, m1, m2, m3, m4, box_number = filled_slots[i]
                        moves = [m.replace('-', ' ').title() for m in [m1, m2, m3, m4] if m and m != 'none']
                        move_str = ", ".join(moves) if moves else "*No learned behaviors*"
                        
                        # Visual bond indicator
                        bond = "❤️❤️❤️" if happiness >= 220 else "❤️❤️🤍" if happiness >= 150 else "❤️🤍🤍" if happiness >= 50 else "🤍🤍🤍"
                        
                        embed.add_field(
                            name=f"Slot {i}: {name.capitalize()} (Lv. {level})", 
                            value=f"**Box `#{box_number}`** | **Tag:** `{tag[:8]}` | **Bond:** {bond}\n**Moves:** {move_str}", 
                            inline=False
                        )
                    else:
                        embed.add_field(name=f"Slot {i}", value="*Empty*", inline=False)
                        
                await ctx.send(embed=embed)
                
            else:
                await ctx.send("⚠️ Invalid action. Use `!party view`, `!party add [slot] [box_number]`, or `!party remove [slot]`.")

        except Exception as e:
            # 🚨 THIS CATCHES THE SILENT CRASH! 🚨
            print("\n🚨 CRITICAL EXCEPTION IN !PARTY 🚨")
            traceback.print_exc()
            await ctx.send(f"🚨 **Engine Crash Detected!**\n```py\n{e}\n```\nCheck your terminal for the full traceback.")
        finally:
            # Ensure the database always closes, even on a crash
            if 'conn' in locals():
                conn.close()


    @commands.command(name="movedex", aliases=["move", "attackinfo", "technique"])
    @checks.has_started()
    @checks.is_authorized()
    async def move_lookup(self, ctx, *, move_name: str):
        # Format the user's input to match the database standard (e.g., "Solar Beam" -> "solar-beam")
        formatted_name = move_name.lower().replace(" ", "-")
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Query the universal move dictionary
        cursor.execute("""
            SELECT name, type, power, accuracy, damage_class, pp 
            FROM base_moves 
            WHERE name = ?
        """, (formatted_name,))
        
        move_data = cursor.fetchone()
        conn.close()
        
        if not move_data:
            return await ctx.send(f"⚠️ The behavior **{move_name.title()}** is not recognized in the standard ecological compendium.")
            
        name, move_type, power, accuracy, dmg_class, pp = move_data
        
        # Format the data for display
        pwr_display = power if power and power > 0 else "-"
        acc_display = f"{accuracy}%" if accuracy else "-"
        
        # Assign standard icons based on the damage classification
        if dmg_class == 'physical':
            dmg_icon = "💥"
            embed_color = discord.Color.orange()
        elif dmg_class == 'special':
            dmg_icon = "☄️"
            embed_color = discord.Color.purple()
        else:
            dmg_icon = "🛡️"
            embed_color = discord.Color.light_grey()

        # Build the UI
        embed = discord.Embed(title=f"📖 Field Guide: {name.replace('-', ' ').title()}", color=embed_color)
        
        embed.add_field(name="Elemental Type", value=move_type.capitalize(), inline=True)
        embed.add_field(name="Classification", value=f"{dmg_icon} {dmg_class.capitalize()}", inline=True)
        embed.add_field(name="Base Power", value=str(pwr_display), inline=True)
        
        embed.add_field(name="Accuracy", value=acc_display, inline=True)
        embed.add_field(name="Max PP", value=str(pp), inline=True)
        
        # Add a quick tip based on the damage class!
        if dmg_class == 'physical':
            embed.set_footer(text="Physical attacks calculate damage using the user's Attack stat.")
        elif dmg_class == 'special':
            embed.set_footer(text="Special attacks calculate damage using the user's Special Attack stat.")
        else:
            embed.set_footer(text="Status moves apply biological effects, stat changes, or environmental hazards.")

        await ctx.send(embed=embed)

    @commands.command(name="npcduel", aliases=["battle_npc", "rival"])
    @checks.has_started()
    @checks.is_authorized()
    async def npc_encounter(self, ctx):
        user_id = str(ctx.author.id)
        
        # Prevent parallel skirmishes
        if hasattr(self, 'active_battles') and user_id in self.active_battles:
            return await ctx.send("🛑 **Tactical Override:** You are already engaged in an active skirmish! Finish it or flee before starting a new one.")
        

        # ==========================================
        # ECOLOGICAL STAMINA CHECK
        # ==========================================
        success, msg = self.check_and_consume_energy(user_id, cost=20)

        if not success:
            # Player is out of energy! Send the error and cancel the battle.
            return await ctx.send(msg)
        
        # If success is True, the energy was successfully deducted. 
        # We can append the remaining energy text to the start of the battle log!
        combat_log = f"*{msg}*\n\n"
        # ==========================================

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # 1. Read the Player's Roster and calculate the Ecosystem Scale (Average Level)
        cursor.execute("""
            SELECT cp.level
            FROM user_party up
            JOIN caught_pokemon cp ON up.instance_id = cp.instance_id
            WHERE up.user_id = ?
        """, (user_id,))
        
        party_data = cursor.fetchall()
        
        if not party_data:
            await ctx.send("⚠️ You must assign at least one specimen to your fieldwork roster using `!party add 1 [Tag ID]` before engaging a rival team!")
            conn.close()
            return

        team_size = len(party_data)
        # Calculate the average level, ensuring it never drops below 1
        avg_level = max(1, sum(row[0] for row in party_data) // team_size)

        # 2. Generate the Rival Team Roster
        # We exclude Legendaries, Mythicals, and Ultra Beasts (793-806) to ensure standard biological encounters
        cursor.execute("""
            SELECT pokedex_id, name 
            FROM base_pokemon_species 
            WHERE is_legendary = 0 AND is_mythical = 0 AND pokedex_id NOT BETWEEN 793 AND 806 AND form_type IN ('base', 'alolan', 'galarian', 'hisuian', 'paldean')
            ORDER BY RANDOM() LIMIT ?
        """, (team_size,))
        
        npc_species = cursor.fetchall()
        
        npc_team = []
        
        # 3. Equip and Calculate the Rival Team
        for poke_id, name in npc_species:
            # Fetch Moves (Your existing code)
            cursor.execute("""
                SELECT move_name 
                FROM species_movepool 
                WHERE pokedex_id = ? AND learn_method = 'level-up' AND level_learned <= ? AND level_learned > 0
                GROUP BY move_name ORDER BY MIN(level_learned) DESC LIMIT 4
            """, (poke_id, avg_level))
            
            raw_moves = [row[0] for row in cursor.fetchall()]
            while len(raw_moves) < 4:
                if "tackle" not in raw_moves: raw_moves.append("tackle")
                else: break 
            

            # --- Convert NPC moves to PP Dictionaries ---
            npc_moves = []
            for m_name in raw_moves:
                cursor.execute("SELECT pp FROM base_moves WHERE name = ?", (m_name,))
                pp_row = cursor.fetchone()
                pp_val = pp_row[0] if pp_row and pp_row[0] else 5
                npc_moves.append({'name': m_name, 'pp': pp_val, 'max_pp': pp_val})

            cursor.execute("SELECT type_name FROM base_pokemon_types WHERE pokedex_id = ?", (poke_id,))
            npc_types = [row[0] for row in cursor.fetchall()]
                    
            # Pass the new dictionary array (npc_moves) into your builder!
            combatant = self.build_npc_combatant(cursor, poke_id, name, avg_level, npc_moves, npc_types)
            npc_team.append(combatant)

        # 4. Load the Player's Team and Calculate their Exact Stats
        player_team = []
        cursor.execute("""
            SELECT cp.instance_id, cp.pokedex_id, s.name, cp.level, cp.nature,
                cp.iv_hp, cp.iv_attack, cp.iv_defense, cp.iv_sp_atk, cp.iv_sp_def, cp.iv_speed,
                cp.ev_hp, cp.ev_attack, cp.ev_defense, cp.ev_sp_atk, cp.ev_sp_def, cp.ev_speed,
                cp.move_1, cp.move_2, cp.move_3, cp.move_4, cp.is_shiny, cp.held_item, cp.gmax_factor, cp.ability, cp.experience
            FROM user_party up
            JOIN caught_pokemon cp ON up.instance_id = cp.instance_id
            JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
            WHERE up.user_id = ?
            ORDER BY up.slot ASC
        """, (user_id,))
        
        for row in cursor.fetchall():
            tag, p_id, p_name, p_lvl, p_nature = row[0:5]
            p_ivs = {'hp': row[5], 'attack': row[6], 'defense': row[7], 'sp_atk': row[8], 'sp_def': row[9], 'speed': row[10]}
            p_evs = {'hp': row[11], 'attack': row[12], 'defense': row[13], 'sp_atk': row[14], 'sp_def': row[15], 'speed': row[16]}
            raw_moves = [m for m in row[17:21] if m and m != 'none']
            p_moves = []
            for m_name in raw_moves:
                cursor.execute("SELECT pp FROM base_moves WHERE name = ?", (m_name,))
                pp_val = cursor.fetchone()[0] or 5 # Fallback to 5 if API data is missing
                p_moves.append({'name': m_name, 'pp': pp_val, 'max_pp': pp_val})

            # Fetch the player's elemental typing for STAB and Defense!
            cursor.execute("SELECT type_name FROM base_pokemon_types WHERE pokedex_id = ?", (p_id,))
            p_types = [t[0] for t in cursor.fetchall()]

            is_shiny = row[21]
            held_item = row[22]
            gmax_factor = row[23]
            ability = row[24]
            experience = row[25]
            
            p_base = fetch_base_stats(cursor, p_id)
            p_final_stats = calculate_stats(p_base, p_ivs, p_evs, p_lvl, p_nature)
            
            player_team.append({
                'instance_id': tag, 'pokedex_id': p_id, 'name': p_name, 'level': p_lvl,
                'max_hp': p_final_stats['hp'], 'current_hp': p_final_stats['hp'],
                'stats': p_final_stats, 'moves': p_moves, 'status_condition': None, 'is_shiny': is_shiny, 
                # --- Attach Symbiotic Gear and Genetics ---
                'held_item': held_item,
                'gmax_factor': gmax_factor,
                'ability': ability,
                'types': p_types,
                'experience': experience, # <--- INJECTED INTO MEMORY!
                'volatile_statuses': {}   # <--- GUARANTEES PARASITES HAVE A HOST!
            })
        
                    # ==========================================
        # KEY ITEM SCANNER
        # ==========================================
        try:
            cursor.execute("""
                SELECT item_name FROM user_inventory 
                WHERE user_id = ? AND item_name IN ('dynamax-band', 'z-ring', 'mega-bracelet') AND quantity > 0
            """, (user_id,))
            
            # Flatten the SQL result into a simple Python list
            owned_key_items = [row[0] for row in cursor.fetchall()]
            
            # Create an access ledger in the battle state
            access_ledger = {
                'dynamax_band': 'dynamax-band' in owned_key_items,
                'z_ring': 'z-ring' in owned_key_items,
                'mega_bracelet': 'mega-bracelet' in owned_key_items
            }
            # ==========================================
        except Exception as e:
            print("\n🚨 CRITICAL CRASH IN NPCDUEL INITIALIZATION 🚨")
            traceback.print_exc()
            await ctx.send("⚠️ A critical failure occurred while initializing the key items. Check the console.")   
        conn.close()

        # 5. Initialize the Temporary Battle State Memory
        print("DEBUG: Database closed. Entering Step 5: State Initialization...")
        try:
            self.active_battles[user_id] = {
                'player_team': player_team,
                'npc_team': npc_team,
                'active_player_index': 0, # Slot 1
                'active_npc_index': 0,    # Slot 1
                'turn_number': 1,
                'weather': {'type': 'none', 'duration': 0},
                'adaptation': {'used': False, 'active': False, 'type': 'none', 'turns': 0, 'backup': {}},
                'key_items': access_ledger,
                
                # ==========================================
                # ENVIRONMENTAL HAZARD TRACKERS
                # ==========================================
                # 'player_hazards' are rocks/spikes currently on YOUR side of the field
                'player_hazards': {
                    'stealth-rock': False,
                    'spikes': 0,           # Stacks up to 3
                    'toxic-spikes': 0,     # Stacks up to 2
                    'sticky-web': False
                },
                # 'npc_hazards' are rocks/spikes currently on the ENEMY'S side of the field
                'npc_hazards': {
                    'stealth-rock': False,
                    'spikes': 0,
                    'toxic-spikes': 0,
                    'sticky-web': False
                }
                # ==========================================
            }
            print("DEBUG: State initialized. Preparing Step 6: Encounter Display...")
            # 6. Display the Encounter
            p_lead = player_team[0]
            n_lead = npc_team[0]
            
            # --- Generate Starting Roster Indicators ---
            p_roster = "".join(["🔴" for _ in player_team])
            n_roster = "".join(["🔴" for _ in npc_team])

            # ==========================================
            #  FIRE THE ON_ENTRY ABILITY HOOK
            # ==========================================
            # 1. Start with your default opening string
            combat_log = f"**{ctx.author.name}** vs. **Rival Survey Team**\n\n"
            combat_log += f"A wild rival appeared! They sent out **{n_lead['name'].capitalize()}**!\n"
            combat_log += f"Go, **{p_lead['name'].capitalize()}**!\n\n"

            # 2. Pass it through the hook to append any Ability text (like Intimidate)
            state = self.active_battles[user_id]
            print("DEBUG: Calling trigger_single_entry_ability hook...")
            # 1. Fire the Player's ability hook
            combat_log = trigger_single_entry_ability(p_lead, n_lead, "Your", state, combat_log)

            # 2. Fire the NPC's ability hook
            combat_log = trigger_single_entry_ability(n_lead, p_lead, "The rival's", state, combat_log)
            # ==========================================
            print("DEBUG: Building Discord Embed...")
            embed = discord.Embed(title="⚔️ Ecological Field Duel Commencing!", color=discord.Color.red())
            embed.description = combat_log
            
            embed.add_field(name=f"🟢 Your {p_lead['name'].capitalize()}", value=f"Team: {p_roster}", inline=True)
            embed.add_field(name=f"🔴 Rival {n_lead['name'].capitalize()}", value=f"Team: {n_roster}", inline=True)
            
            embed.set_footer(text="Use the buttons below to command your specimen.")
            
            # Generate the visual scene! 
            # Ensure we pass the 4 new biometric HP parameters to generate the starting health bars!
            print("DEBUG: Calling generate_battle_scene...")

            # Since we just fired entry abilities, grab the latest weather from the state!
            current_weather = state.get('weather', {'type': 'none'})['type']

            battle_file = await BattleDashboard.generate_battle_scene(
                self,
                player_id=p_lead['pokedex_id'], 
                npc_id=n_lead['pokedex_id'],
                p_hp=p_lead['current_hp'],
                p_max_hp=p_lead['max_hp'],
                n_hp=n_lead['current_hp'],
                n_max_hp=n_lead['max_hp'],
                player_shiny=p_lead.get('is_shiny', False), 
                npc_shiny=n_lead.get('is_shiny', False),
                # ==========================================
                # PASSING THE OVERLAY DATA TO THE RENDERER
                # ==========================================
                weather=current_weather,
                p_status=p_lead.get('status_condition'),
                n_status=n_lead.get('status_condition'),
                p_hazards=state.get('player_hazards'),
                n_hazards=state.get('npc_hazards')
            )

            # Attach the file to the embed
            # Dynamically grab the new randomized filename!
            if battle_file:
                embed.set_image(url=f"attachment://{battle_file.filename}")
            print("DEBUG: Battle scene generated and attached.")

            print("file generated and attached")
            
            print("DEBUG: Sending final payload to Discord...")
            dashboard_view = BattleDashboard(self, user_id, ctx)
            print("=== DEBUG: npcduel execution COMPLETE ===")
            # Send the embed WITH the file and the view
            print("View attached")
            await ctx.send(embed=embed, files=[battle_file], view=dashboard_view)
        except Exception as e:
            print("\n🚨 CRITICAL CRASH IN NPCDUEL INITIALIZATION 🚨")
            traceback.print_exc()
            await ctx.send("⚠️ A critical failure occurred while initializing the biological simulation. Check the console.")         

# Required for loading
async def setup(bot):
    await bot.add_cog(Combat(bot))