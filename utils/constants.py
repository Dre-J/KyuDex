import json
import os
import discord
# ==========================================
# THE BOTANICAL DATABASE (Consumables)
# ==========================================
CONSUMABLE_DATABASE = {}
_berry_file = 'consumables.json'

if os.path.exists(_berry_file):
    try:
        with open(_berry_file, 'r', encoding='utf-8') as f:
            CONSUMABLE_DATABASE = json.load(f)
        print(f"🌱 Successfully loaded {len(CONSUMABLE_DATABASE)} botanical specimens into memory.")
    except Exception as e:
        print(f"🚨 CRITICAL: Failed to parse consumables.json - {e}")
else:
    print("⚠️ WARNING: consumables.json not found! Botanical interactions will be disabled.")

DB_FILE = "ecosystem.db"

# ==========================================
# SPECIMEN MASS INDEX (Weight-based moves)
# ==========================================
# Heavy Slam, Heat Crash, Grass Knot and Low Kick all scale off body mass. We cache the
# whole table once at boot instead of threading a weight column through every combatant
# builder - and because we look up by pokedex_id, Mega and G-Max forms automatically
# report their own transformed mass mid-battle.
# The database stores hectograms (PokeAPI's native unit), so we convert to kilograms here.
SPECIES_WEIGHTS = {}
_DEFAULT_WEIGHT_KG = 50.0

try:
    import sqlite3 as _sqlite3
    with _sqlite3.connect(DB_FILE) as _conn:
        SPECIES_WEIGHTS = {
            row[0]: (row[1] / 10.0)
            for row in _conn.execute("SELECT pokedex_id, weight FROM base_pokemon_species")
            if row[1]
        }
    print(f"⚖️ Indexed body mass for {len(SPECIES_WEIGHTS)} species.")
except Exception as e:
    print(f"⚠️ WARNING: Could not index species weights ({e}). Weight-based moves will use a default mass.")

def get_species_weight(pokemon):
    """Body mass in kilograms, falling back to a neutral default for unknown species."""
    return SPECIES_WEIGHTS.get(pokemon.get('pokedex_id'), _DEFAULT_WEIGHT_KG)

# ==========================================
# SPECIMEN BASE ATTACK INDEX (Beat Up)
# ==========================================
# Beat Up's power for each strike comes from that party member's SPECIES base Attack,
# not from its trained stat, so the whole column is cached at boot the same way body mass
# is - the damage formula is synchronous and cannot go back to the database mid-swing.
SPECIES_BASE_ATTACK = {}
_DEFAULT_BASE_ATTACK = 50

try:
    import sqlite3 as _sqlite3
    with _sqlite3.connect(DB_FILE) as _conn:
        SPECIES_BASE_ATTACK = {
            row[0]: row[1]
            for row in _conn.execute(
                "SELECT pokedex_id, base_value FROM base_pokemon_stats WHERE stat_name = 'attack'")
            if row[1]
        }
    print(f"⚔️ Indexed base Attack for {len(SPECIES_BASE_ATTACK)} species.")
except Exception as e:
    print(f"⚠️ WARNING: Could not index base Attack ({e}). Beat Up will use a default.")

def get_species_base_attack(pokemon):
    """Species base Attack, falling back to a neutral default for unknown species."""
    return SPECIES_BASE_ATTACK.get((pokemon or {}).get('pokedex_id'), _DEFAULT_BASE_ATTACK)

# ==========================================
# 🎲 THE METRONOME POOL
# ==========================================
# Every move Metronome may roll, indexed once at import rather than queried per use.
# The exclusions are the moves that would either recurse into another random pick or
# have nothing sensible to copy.
METRONOME_EXCLUDED = {
    'assist', 'copycat', 'me-first', 'metronome', 'mimic', 'mirror-move', 'sketch',
    'sleep-talk', 'nature-power', 'struggle', 'transform', 'skill-swap', 'role-play',
    'quash', 'after-you', 'instruct', 'baneful-bunker', 'belch', 'counter',
    'covet', 'destiny-bond', 'detect', 'endure', 'feint', 'focus-punch', 'follow-me',
    'helping-hand', 'mirror-coat', 'protect', 'rage-powder', 'snore', 'thief',
}

METRONOME_POOL = []

try:
    import sqlite3 as _sqlite3
    with _sqlite3.connect(DB_FILE) as _conn:
        METRONOME_POOL = [
            row[0] for row in _conn.execute("SELECT name FROM base_moves ORDER BY name")
            if row[0] and row[0] not in METRONOME_EXCLUDED
        ]
    print(f"🎲 Indexed {len(METRONOME_POOL)} moves for Metronome.")
except Exception as e:
    print(f"⚠️ WARNING: Could not index the Metronome pool ({e}). Metronome will fail.")

FIELD_MISSIONS = {
    # ==========================================
    # EXPERIENCE MISSIONS (Type Bonus = +20% XP)
    # ==========================================
    "volcanic": {
        "category": "exp",
        "name": "Volcanic Magma Sampling",
        "desc": "Assist geologists near active vents.",
        "preferred_type": "fire",
        "base_xp_hr": 200,
        "item_pool": ["fire-stone", "nugget", "rare-candy"]
    },
    "reef": {
        "category": "exp",
        "name": "Coral Reef Restoration",
        "desc": "Clear debris from fragile underwater ecosystems.",
        "preferred_type": "water",
        "base_xp_hr": 200,
        "item_pool": ["water-stone", "nugget", "dive-ball", "rare-candy"]
    },
    "canopy": {
        "category": "exp",
        "name": "Canopy Seed Dispersal",
        "desc": "Help plant seeds in the upper rainforest levels.",
        "preferred_type": "grass",
        "base_xp_hr": 200,
        "item_pool": ["leaf-stone", "nugget", "rare-candy"]
    },
    "power": {
        "category": "exp",
        "name": "Grid Maintenance",
        "desc": "Absorb excess energy from the local power plant.",
        "preferred_type": "electric",
        "base_xp_hr": 200,
        "item_pool": ["thunder-stone", "nugget", "rare-candy"]
    },
    "mountain": {
        "category": "exp",
        "name": "Peak Surveying",
        "desc": "Map out high-altitude nesting grounds.",
        "preferred_type": "flying",
        "base_xp_hr": 200,
        "item_pool": ["sharp-beak", "nugget", "rare-candy"]
    },
    "quarry": {
        "category": "exp",
        "name": "Mineral Extraction",
        "desc": "Help excavate rare ores from the deep quarry.",
        "preferred_type": "rock",
        "base_xp_hr": 200,
        "item_pool": ["hard-stone", "nugget", "rare-candy"]
    },
    "tundra": {
        "category": "exp",
        "name": "Glacier Monitoring",
        "desc": "Track the movement of ancient ice shelves.",
        "preferred_type": "ice",
        "base_xp_hr": 200,
        "item_pool": ["never-melt-ice", "nugget", "rare-candy"]
    },
    "dojo": {
        "category": "exp",
        "name": "Tactical Sparring",
        "desc": "Train with local martial arts experts.",
        "preferred_type": "fighting",
        "base_xp_hr": 200,
        "item_pool": ["black-belt", "nugget", "rare-candy"]
    },
    "swamp": {
        "category": "exp",
        "name": "Toxin Filtration",
        "desc": "Neutralize hazardous waste in the wetlands.",
        "preferred_type": "poison",
        "base_xp_hr": 200,
        "item_pool": ["poison-barb", "nugget", "rare-candy"]
    },
    "agriculture": {
        "category": "exp",
        "name": "Community Farming",
        "desc": "Assist local farmers in plowing and harvesting fields safely.",
        "preferred_type": "normal",
        "base_xp_hr": 200,
        "item_pool": ["silk-scarf", "nugget", "rare-candy"]
    },
    "canyon": {
        "category": "exp",
        "name": "Erosion Control",
        "desc": "Fortify riverbanks and stabilize shifting soils in arid regions.",
        "preferred_type": "ground",
        "base_xp_hr": 200,
        "item_pool": ["soft-sand", "nugget", "rare-candy"]
    },
    "botanical": {
        "category": "exp",
        "name": "Floral Pollination",
        "desc": "Cross-pollinate rare flora and manage invasive pests in the gardens.",
        "preferred_type": "bug",
        "base_xp_hr": 200,
        "item_pool": ["silver-powder", "nugget", "net-ball", "rare-candy"]
    },
    "ruins": {
        "category": "exp",
        "name": "Ancestral Groundskeeping",
        "desc": "Clear overgrown vines and appease restless spirits in the old cemetery.",
        "preferred_type": "ghost",
        "base_xp_hr": 200,
        "item_pool": ["spell-tag", "nugget", "rare-candy"]
    },
    "industrial": {
        "category": "exp",
        "name": "Scrap Recycling",
        "desc": "Compact and process metallic debris from abandoned industrial zones.",
        "preferred_type": "steel",
        "base_xp_hr": 200,
        "item_pool": ["metal-coat", "nugget", "rare-candy"]
    },
    "leyline": {
        "category": "exp",
        "name": "Resonance Mapping",
        "desc": "Meditate to locate and map invisible energy pathways across the region.",
        "preferred_type": "psychic",
        "base_xp_hr": 200,
        "item_pool": ["twisted-spoon", "nugget", "rare-candy"]
    },
    "shrine": {
        "category": "exp",
        "name": "Monument Restoration",
        "desc": "Protect and restore ancient shrines dedicated to legendary figures.",
        "preferred_type": "dragon",
        "base_xp_hr": 200,
        "item_pool": ["dragon-fang", "nugget", "rare-candy"]
    },
    "patrol": {
        "category": "exp",
        "name": "Nocturnal Scouting",
        "desc": "Patrol the city limits at night to deter poachers and rogue elements.",
        "preferred_type": "dark",
        "base_xp_hr": 200,
        "item_pool": ["black-glasses", "nugget", "dusk-ball", "rare-candy"]
    },
    "glade": {
        "category": "exp",
        "name": "Aura Purification",
        "desc": "Cleanse lingering negative energy and restore the mystical glade.",
        "preferred_type": "fairy",
        "base_xp_hr": 200,
        "item_pool": ["moon-stone", "nugget", "rare-candy"]
    },
    # ==========================================
    # EV TRAINING MISSIONS (0 XP, +4 EVs per hour)
    # ==========================================
    "hp": {
        "category": "ev",
        "name": "Endurance Drills",
        "desc": "Intensive stamina training.",
        "target_ev": "ev_hp",
        "ev_hr": 4,
        "item_pool": ["hp-up", "oran-berry"]
    },
    "attack": {
        "category": "ev",
        "name": "Target Practice",
        "desc": "Focus on physical striking power.",
        "target_ev": "ev_attack",
        "ev_hr": 4,
        "item_pool": ["protein", "muscle-band"]
    },
    "defense": {
        "category": "ev",
        "name": "Impact Resistance",
        "desc": "Withstand heavy physical blows.",
        "target_ev": "ev_defense",
        "ev_hr": 4,
        "item_pool": ["iron", "hard-stone"]
    },
    "spatk": {
        "category": "ev",
        "name": "Elemental Tuning",
        "desc": "Enhance special attack output.",
        "target_ev": "ev_sp_atk",
        "ev_hr": 4,
        "item_pool": ["calcium", "wise-glasses"]
    },
    "spdef": {
        "category": "ev",
        "name": "Barrier Weaving",
        "desc": "Practice deflecting elemental energy.",
        "target_ev": "ev_sp_def",
        "ev_hr": 4,
        "item_pool": ["zinc", "light-clay"]
    },
    "speed": {
        "category": "ev",
        "name": "Agility Course",
        "desc": "High-speed reflex training.",
        "target_ev": "ev_speed",
        "ev_hr": 4,
        "item_pool": ["carbos", "quick-claw"]
    }
}

TYPE_CHART = {
    'normal': {'rock': 0.5, 'ghost': 0.0, 'steel': 0.5},
    'fire': {'fire': 0.5, 'water': 0.5, 'grass': 2.0, 'ice': 2.0, 'bug': 2.0, 'rock': 0.5, 'dragon': 0.5, 'steel': 2.0},
    'water': {'fire': 2.0, 'water': 0.5, 'grass': 0.5, 'ground': 2.0, 'rock': 2.0, 'dragon': 0.5},
    'electric': {'water': 2.0, 'electric': 0.5, 'grass': 0.5, 'ground': 0.0, 'flying': 2.0, 'dragon': 0.5},
    'grass': {'fire': 0.5, 'water': 2.0, 'grass': 0.5, 'poison': 0.5, 'ground': 2.0, 'flying': 0.5, 'bug': 0.5, 'rock': 2.0, 'dragon': 0.5, 'steel': 0.5},
    'ice': {'fire': 0.5, 'water': 0.5, 'grass': 2.0, 'ice': 0.5, 'ground': 2.0, 'flying': 2.0, 'dragon': 2.0, 'steel': 0.5},
    'fighting': {'normal': 2.0, 'ice': 2.0, 'poison': 0.5, 'flying': 0.5, 'psychic': 0.5, 'bug': 0.5, 'rock': 2.0, 'ghost': 0.0, 'dark': 2.0, 'steel': 2.0, 'fairy': 0.5},
    'poison': {'grass': 2.0, 'poison': 0.5, 'ground': 0.5, 'rock': 0.5, 'ghost': 0.5, 'steel': 0.0, 'fairy': 2.0},
    'ground': {'fire': 2.0, 'water': 0.5, 'electric': 2.0, 'grass': 0.5, 'poison': 2.0, 'flying': 0.0, 'bug': 0.5, 'rock': 2.0, 'steel': 2.0},
    'flying': {'electric': 0.5, 'grass': 2.0, 'fighting': 2.0, 'bug': 2.0, 'rock': 0.5, 'steel': 0.5},
    'psychic': {'fighting': 2.0, 'poison': 2.0, 'psychic': 0.5, 'dark': 0.0, 'steel': 0.5},
    'bug': {'fire': 0.5, 'grass': 2.0, 'fighting': 0.5, 'poison': 0.5, 'flying': 0.5, 'psychic': 2.0, 'ghost': 0.5, 'dark': 2.0, 'steel': 0.5, 'fairy': 0.5},
    'rock': {'fire': 2.0, 'ice': 2.0, 'fighting': 0.5, 'ground': 0.5, 'flying': 2.0, 'bug': 2.0, 'steel': 0.5},
    'ghost': {'normal': 0.0, 'psychic': 2.0, 'ghost': 2.0, 'dark': 0.5},
    'dragon': {'dragon': 2.0, 'steel': 0.5, 'fairy': 0.0},
    'dark': {'fighting': 0.5, 'psychic': 2.0, 'ghost': 2.0, 'dark': 0.5, 'fairy': 0.5},
    'steel': {'fire': 0.5, 'water': 0.5, 'electric': 0.5, 'ice': 2.0, 'rock': 2.0, 'steel': 0.5, 'fairy': 2.0},
    'fairy': {'fire': 0.5, 'fighting': 2.0, 'poison': 0.5, 'dragon': 2.0, 'dark': 2.0, 'steel': 0.5}
}

# A reference dictionary for Natures. 
# Format: 'nature_name': ('increased_stat', 'decreased_stat')
NATURE_MULTIPLIERS = {
    'hardy': (None, None), 'lonely': ('attack', 'defense'), 'brave': ('attack', 'speed'),
    'adamant': ('attack', 'special-attack'), 'naughty': ('attack', 'special-defense'),
    'bold': ('defense', 'attack'), 'docile': (None, None), 'relaxed': ('defense', 'speed'),
    'impish': ('defense', 'special-attack'), 'lax': ('defense', 'special-defense'),
    'timid': ('speed', 'attack'), 'hasty': ('speed', 'defense'), 'serious': (None, None),
    'jolly': ('speed', 'special-defense'), 'naive': ('speed', 'special-defense'),
    'modest': ('special-attack', 'attack'), 'mild': ('special-attack', 'defense'), 'quiet': ('special-attack', 'speed'),
    'bashful': (None, None), 'rash': ('special-attack', 'special-defense'),
    'calm': ('special-defense', 'attack'), 'gentle': ('special-defense', 'defense'), 'sassy': ('special-defense', 'speed'),
    'careful': ('special-defense', 'special-attack'), 'quirky': (None, None)
}

# A quick list of natures for genetic diversity
NATURES = ["Hardy", "Lonely", "Brave", "Adamant", "Naughty", "Bold", "Docile", "Relaxed", "Impish", "Lax", "Timid", "Hasty", "Serious", "Jolly", "Naive", "Modest", "Mild", "Quiet", "Bashful", "Rash", "Calm", "Gentle", "Sassy", "Careful", "Quirky"]

EQUIPMENT_CATALOG = {
    # CAPTURE GEAR
    "greatball": {"name": "Great Ball", "price": 100, "desc": "2.5x Capture Rate", "emoji": "🔵", "category": "capture"},
    "ultraball": {"name": "Ultra Ball", "price": 250, "desc": "4.0x Capture Rate", "emoji": "🟡", "category": "capture"},
    "dive-ball": {"name": "Dive Ball", "price": 0, "desc": "2.0x Capture Rate for Water Types", "emoji": "🔵", "category": "capture", "purchasable": False},
    "friend-ball": {"name": "Friend Ball", "price": 0, "desc": "Increases the base happiness of a caught pokemon", "emoji": "🔵", "category": "capture", "purchasable": False},
    "masterball": {"name": "Master Ball", "price": 0, "desc": "100% Capture Rate", "emoji": "🟣", "category": "capture", "purchasable": False},
    
    # Key Items
    "dynamax-band":  {"name": "Dynamax Band", "price": 0, "desc": "Allows a pokemon to dynamax or gigantamax.", "emoji": "🧬", "category": "keyitems", "purchasable": False},
    "mega-bracelet":  {"name": "Mega Bracelet", "price": 0, "desc": "Unlocks Mega Evolution to be used in battles.", "emoji": "🧬", "category": "keyitems", "purchasable": False},
    "z-ring":  {"name": "Z Ring", "price": 0, "desc": "Allows a pokemon to use Z moves with a Z-crystal in battle.", "emoji": "🧬", "category": "keyitems", "purchasable": False},
    "encrypted-field-notes":  {"name": "Encrypted Field Notes", "price": 0, "desc": "Scan with `!analyze notes` to get a field directive.", "emoji": "📝", "category": "keyitems", "purchasable": False},
    "wishing-fragment":  {"name": "Wishing Fragment", "price": 0, "desc": "Exchange with `!refine` to make a Dynamax Band.", "emoji": "📝", "category": "keyitems", "purchasable": False},
    "nugget":  {"name": "Nugget", "price": 0, "desc": "Exchange for Eco-Tokens", "emoji": "💵", "category": "keyitems", "purchasable": False, "sell_price": 5000},
    "memory-spore":  {"name": "Memory Spore", "price": 0, "desc": "Allows a pokemon to learn a tutor move.", "emoji": "🧬", "category": "keyitems", "purchasable": False},
    
    # Form Items
    "reveal-glass":  {"name": "Reveal Glass", "price": 0, "desc": "Allows the weather trio to switch between forms.", "emoji": "🧬", "category": "formitems", "purchasable": False},
    "dna-splicers":  {"name": "DNA Splicers", "price": 0, "desc": "Allows Kyurem to fuse with Reshiram or Zekrom.", "emoji": "🧬", "category": "formitems", "purchasable": False},
    "rusted-sword":  {"name": "Rusted Sword", "price": 0, "desc": "Zacian takes its Crowned form while holding this.", "emoji": "⚔️", "category": "formitems", "purchasable": False},
    "rusted-shield":  {"name": "Rusted Shield", "price": 0, "desc": "Zamazenta takes its Crowned form while holding this.", "emoji": "🛡️", "category": "formitems", "purchasable": False},
    "red-orb":  {"name": "Red Orb", "price": 0, "desc": "Groudon undergoes Primal Reversion while holding this.", "emoji": "🔴", "category": "formitems", "purchasable": False},
    "blue-orb":  {"name": "Blue Orb", "price": 0, "desc": "Kyogre undergoes Primal Reversion while holding this.", "emoji": "🔵", "category": "formitems", "purchasable": False},
    
    # Evolution Items
    "water-stone":    {"name": "Water Stone", "price": 500, "desc": "A stone that makes certain pokemon evolve. It is clear, blue and glistens.", "emoji": "💎", "category": "evoitems"},
    "leaf-stone":    {"name": "Leaf Stone", "price": 500, "desc": "A stone that makes certain pokemon evolve. It is green and mossy.", "emoji": "💎", "category": "evoitems"},
    "fire-stone":    {"name": "Fire Stone", "price": 500, "desc": "A stone that makes certain pokemon evolve. It is clear, orange and glistens.", "emoji": "💎", "category": "evoitems"},
    "rare-candy":    {"name": "Rare Candy", "price": 10000, "desc": "A sweet treat that increases a pokemon's level by 1.", "emoji": "🍬", "category": "evoitems"},

    # GENERAL FIELD SUPPLIES
    "purifier":  {"name": "Purifier", "price": 50, "desc": "Instantly removes pollution from a server", "emoji": "🫧", "category": "general"},
    
    # MEDICINE & BATTLE
    "potion":    {"name": "Potion", "price": 100, "desc": "Restore 20 HP in battle", "emoji": "🧪", "category": "medicine"},
    "revive":    {"name": "Revive", "price": 250, "desc": "Revive a fainted specimen", "emoji": "💠", "category": "medicine"},
    
    # VITAMINS
    "protein":   {"name": "Protein", "price": 500, "desc": "+10 Attack EVs", "emoji": "💪", "category": "vitamin"},
    "carbos":    {"name": "Carbos", "price": 500, "desc": "+10 Speed EVs", "emoji": "👟", "category": "vitamin"},

    # BERRIES
    "oran-berry":   {"name": "Oran Berry", "price": 0, "desc": "Restores 10 HP. Can be eaten or held.", "emoji": "🫐", "category": "berry", "purchasable": False},
    "sitrus-berry": {"name": "Sitrus Berry", "price": 0, "desc": "Restores 25% of max HP.", "emoji": "🍋", "category": "berry", "purchasable": False},
    "cheri-berry":  {"name": "Cheri Berry", "price": 0, "desc": "Cures paralysis.", "emoji": "🌿", "category": "berry", "purchasable": False},
    "chesto-berry": {"name": "Chesto Berry", "price": 0, "desc": "Cures sleep.", "emoji": "🌿", "category": "berry", "purchasable": False},
    "pecha-berry":  {"name": "Pecha Berry", "price": 0, "desc": "Cures poison.", "emoji": "🌿", "category": "berry", "purchasable": False},
    "rawst-berry":  {"name": "Rawst Berry", "price": 0, "desc": "Cures burn.", "emoji": "🌿", "category": "berry", "purchasable": False},
    "aspear-berry": {"name": "Aspear Berry", "price": 0, "desc": "Cures freeze and other status conditions.", "emoji": "🌿", "category": "berry", "purchasable": False},
    "leppa-berry":  {"name": "Leppa Berry", "price": 0, "desc": "Restores 10 PP.", "emoji": "🌸", "category": "berry", "purchasable": False},
    "persim-berry": {"name": "Persim Berry", "price": 0, "desc": "Cures confusion.", "emoji": "🌿", "category": "berry", "purchasable": False},
    "lum-berry":    {"name": "Lum Berry", "price": 0, "desc": "Cures status conditions.", "emoji": "🌿", "category": "berry", "purchasable": False},
    "figy-berry":   {"name": "Figy Berry", "price": 0, "desc": "Restores HP, but may cause confusion.", "emoji": "🍈", "category": "berry", "purchasable": False},
    "wiki-berry":   {"name": "Wiki Berry", "price": 0, "desc": "Restores HP, but may cause confusion.", "emoji": "🍈", "category": "berry", "purchasable": False},
    "mago-berry":   {"name": "Mago Berry", "price": 0, "desc": "Restores HP, but may cause confusion.", "emoji": "🍈", "category": "berry", "purchasable": False},
    "aguav-berry":  {"name": "Aguav Berry", "price": 0, "desc": "Restores HP, but may cause confusion.", "emoji": "🍈", "category": "berry", "purchasable": False},
    "iapapa-berry": {"name": "Iapapa Berry", "price": 0, "desc": "Restores HP, but may cause confusion.", "emoji": "🍈", "category": "berry", "purchasable": False},
    "occa-berry":   {"name": "Occa Berry", "price": 0, "desc": "Reduces damage from super-effective Fire-type attacks.", "emoji": "🛡️", "category": "berry", "purchasable": False},
    "passho-berry": {"name": "Passho Berry", "price": 0, "desc": "Reduces damage from super-effective Water-type attacks.", "emoji": "🛡️", "category": "berry", "purchasable": False},
    "wacan-berry":  {"name": "Wacan Berry", "price": 0, "desc": "Reduces damage from super-effective Electric-type attacks.", "emoji": "🛡️", "category": "berry", "purchasable": False},
    "rindo-berry":  {"name": "Rindo Berry", "price": 0, "desc": "Reduces damage from super-effective Grass-type attacks.", "emoji": "🛡️", "category": "berry", "purchasable": False},
    "yache-berry":  {"name": "Yache Berry", "price": 0, "desc": "Reduces damage from super-effective Ice-type attacks.", "emoji": "🛡️", "category": "berry", "purchasable": False},
    "chople-berry": {"name": "Chople Berry", "price": 0, "desc": "Reduces damage from super-effective Fighting-type attacks.", "emoji": "🛡️", "category": "berry", "purchasable": False},
    "kebia-berry":  {"name": "Kebia Berry", "price": 0, "desc": "Reduces damage from super-effective Poison-type attacks.", "emoji": "🛡️", "category": "berry", "purchasable": False},
    "shuca-berry":  {"name": "Shuca Berry", "price": 0, "desc": "Reduces damage from super-effective Ground-type attacks.", "emoji": "🛡️", "category": "berry", "purchasable": False},
    "coba-berry":   {"name": "Coba Berry", "price": 0, "desc": "Reduces damage from super-effective Flying-type attacks.", "emoji": "🛡️", "category": "berry", "purchasable": False},
    "payapa-berry": {"name": "Payapa Berry", "price": 0, "desc": "Reduces damage from super-effective Psychic-type attacks.", "emoji": "🛡️", "category": "berry", "purchasable": False},
    "tanga-berry":  {"name": "Tanga Berry", "price": 0, "desc": "Reduces damage from super-effective Bug-type attacks.", "emoji": "🛡️", "category": "berry", "purchasable": False},
    "charti-berry": {"name": "Charti Berry", "price": 0, "desc": "Reduces damage from super-effective Rock-type attacks.", "emoji": "🛡️", "category": "berry", "purchasable": False},
    "kasib-berry":  {"name": "Kasib Berry", "price": 0, "desc": "Reduces damage from super-effective Ghost-type attacks.", "emoji": "🛡️", "category": "berry", "purchasable": False},
    "haban-berry":  {"name": "Haban Berry", "price": 0, "desc": "Reduces damage from super-effective Dragon-type attacks.", "emoji": "🛡️", "category": "berry", "purchasable": False},
    "colbur-berry": {"name": "Colbur Berry", "price": 0, "desc": "Reduces damage from super-effective Dark-type attacks.", "emoji": "🛡️", "category": "berry", "purchasable": False},
    "babiri-berry": {"name": "Babiri Berry", "price": 0, "desc": "Reduces damage from super-effective Steel-type attacks.", "emoji": "🛡️", "category": "berry", "purchasable": False},
    "chilan-berry": {"name": "Chilan Berry", "price": 0, "desc": "Reduces damage from Normal-type attacks.", "emoji": "🛡️", "category": "berry", "purchasable": False},
    "liechi-berry": {"name": "Liechi Berry", "price": 0, "desc": "Raises Attack when HP is low.", "emoji": "🔴", "category": "berry", "purchasable": False},
    "ganlon-berry": {"name": "Ganlon Berry", "price": 0, "desc": "Raises Defense when HP is low.", "emoji": "🔴", "category": "berry", "purchasable": False},
    "salac-berry":  {"name": "Salac Berry", "price": 0, "desc": "Raises Speed when HP is low.", "emoji": "🔴", "category": "berry", "purchasable": False},
    "petaya-berry": {"name": "Petaya Berry", "price": 0, "desc": "Raises Sp. Atk when HP is low.", "emoji": "🔴", "category": "berry", "purchasable": False},
    "apicot-berry": {"name": "Apicot Berry", "price": 0, "desc": "Raises Sp. Def when HP is low.", "emoji": "🔴", "category": "berry", "purchasable": False},
    "lansat-berry": {"name": "Lansat Berry", "price": 0, "desc": "Raises critical-hit ratio when HP is low.", "emoji": "🔴", "category": "berry", "purchasable": False},
    "starf-berry":  {"name": "Starf Berry", "price": 0, "desc": "Sharply raises a random stat when HP is low.", "emoji": "🔴", "category": "berry", "purchasable": False},
    "micle-berry":  {"name": "Micle Berry", "price": 0, "desc": "Raises accuracy when HP is low.", "emoji": "🔴", "category": "berry", "purchasable": False},
    "custap-berry": {"name": "Custap Berry", "price": 0, "desc": "Allows a move to go first when HP is low.", "emoji": "🔴", "category": "berry", "purchasable": False},
    
    # 💎 Z-CRYSTALS
    "firium-z":     {"name": "Firium Z", "price": 0, "desc": "Upgrades Fire-type moves into Inferno Overdrive.", "emoji": "🔥", "category": "zcrystal", "purchasable": False},
    "waterium-z":   {"name": "Waterium Z", "price": 0, "desc": "Upgrades Water-type moves into Hydro Vortex.", "emoji": "💧", "category": "zcrystal", "purchasable": False},
    
    # 🧬 MEGA STONES
    "charizardite-x":{"name": "Charizardite X", "price": 0, "desc": "Allows Charizard to Mega Evolve.", "emoji": "🖤", "category": "megastone", "purchasable": False},
    "venusaurite":  {"name": "Venusaurite", "price": 0, "desc": "Allows Venusaur to Mega Evolve.", "emoji": "🌸", "category": "megastone", "purchasable": False}
}

# Define the categories for the dropdowns
CATEGORY_OPTIONS = [
    discord.SelectOption(label="All Items", value="all", emoji="🎒"),
    discord.SelectOption(label="Capture Gear", value="capture", emoji="🔴"),
    discord.SelectOption(label="General Supplies", value="general", emoji="🫧"),
    discord.SelectOption(label="Medicine", value="medicine", emoji="🧪"),
    discord.SelectOption(label="Vitamins", value="vitamin", emoji="💊"),
    discord.SelectOption(label="Berries", value="berry", emoji="🫐"),
    discord.SelectOption(label="Z-Crystals", value="zcrystal", emoji="💎"),
    discord.SelectOption(label="Mega Stones", value="megastone", emoji="🧬"),
    discord.SelectOption(label="Key Items", value="keyitems", emoji="🔑"),
    discord.SelectOption(label="Evolution Items", value="evoitems", emoji="🧬"),
    discord.SelectOption(label="Form Items", value="formitems", emoji="🧬")
]
# The Research Shop Catalog
TM_SHOP = {
    'protect': 500,
    'toxic': 1000,
    'rest': 800,
    'ice-beam': 2000,
    'flamethrower': 2000,
    'thunderbolt': 2000,
    'swords-dance': 1500
}

BIOLOGICAL_TRAITS = {
    'weather_setters': {
        'drizzle': ('rain', "🌧️ **{owner} {name}**'s Drizzle made it rain!\n"),
        'drought': ('sun', "☀️ **{owner} {name}**'s Drought turned the sunlight harsh!\n"),
        'sand-stream': ('sand', "🌪️ **{owner} {name}**'s Sand Stream whipped up a sandstorm!\n"),
        'snow-warning': ('hail', "❄️ **{owner} {name}**'s Snow Warning whipped up a hailstorm!\n")
    },
    'immunities': {
        'water-absorb': {'type': 'water', 'heal': 0.25},
        'volt-absorb': {'type': 'electric', 'heal': 0.25},
        'dry-skin': {'type': 'water', 'heal': 0.25}, # Fixed to 0.25!
        'earth-eater': {'type': 'ground', 'heal': 0.25},
        
        'sap-sipper': {'type': 'grass', 'heal': 0.0, 'stat': 'attack', 'stage': 1},
        'lightning-rod': {'type': 'electric', 'heal': 0.0, 'stat': 'special-attack', 'stage': 1},
        'storm-drain': {'type': 'water', 'heal': 0.0, 'stat': 'special-attack', 'stage': 1},
        'motor-drive': {'type': 'electric', 'heal': 0.0, 'stat': 'speed', 'stage': 1},
        'well-baked-body': {'type': 'fire', 'heal': 0.0, 'stat': 'defense', 'stage': 2},
        
        'flash-fire': {'type': 'fire', 'heal': 0.0}, # Handled via volatile status
        'levitate': {'type': 'ground', 'heal': 0.0}  # Pure immunity
    },
    'pinch_boosters': {
        'overgrow': 'grass', 
        'blaze': 'fire', 
        'torrent': 'water', 
        'swarm': 'bug'
    },
    'damage_multipliers': {
        'tough-claws':   {'condition': 'contact', 'multiplier': 1.3},
        'iron-fist':     {'condition': 'punch', 'multiplier': 1.2},
        'strong-jaw':    {'condition': 'bite', 'multiplier': 1.5},
        'mega-launcher': {'condition': 'pulse', 'multiplier': 1.5},
        'technician':    {'condition': 'power_cap', 'threshold': 60, 'multiplier': 1.5},

        # --- Element-gated. Values are the CURRENT generation's, matching the movepool
        # rebuild: Transistor was nerfed from 1.5 to 1.3 in Gen 9, and Steely Spirit now
        # boosts the holder's own Steel moves rather than only an ally's.
        'steelworker':   {'condition': 'move_type', 'types': ['steel'], 'multiplier': 1.5},
        'steely-spirit': {'condition': 'move_type', 'types': ['steel'], 'multiplier': 1.5},
        'transistor':    {'condition': 'move_type', 'types': ['electric'], 'multiplier': 1.3},
        'dragons-maw':   {'condition': 'move_type', 'types': ['dragon'], 'multiplier': 1.5},
        'rocky-payload': {'condition': 'move_type', 'types': ['rock'], 'multiplier': 1.5},
        'fire-mane':     {'condition': 'move_type', 'types': ['fire'], 'multiplier': 1.5},
        'water-bubble':  {'condition': 'move_type', 'types': ['water'], 'multiplier': 2.0},

        # --- Everything else needs its own kind of condition
        'reckless':      {'condition': 'recoil', 'multiplier': 1.2},
        'punk-rock':     {'condition': 'sound', 'multiplier': 1.3},
        'sand-force':    {'condition': 'weather_type', 'weather': ['sand'],
                          'types': ['rock', 'ground', 'steel'], 'multiplier': 1.3},
        'neuroforce':    {'condition': 'super_effective', 'multiplier': 1.25},
        'rivalry':       {'condition': 'gender', 'same': 1.25, 'opposite': 0.75},

        # --- Block 4: conditions read off the turn rather than the move
        'tinted-lens':   {'condition': 'not_very_effective', 'multiplier': 2.0},
        'analytic':      {'condition': 'moving_last', 'multiplier': 1.3},
        'stakeout':      {'condition': 'target_just_arrived', 'multiplier': 2.0},
    },

    # The defensive half of the same idea: a multiplier on damage COMING IN, keyed on the
    # target's ability. Punk Rock and Water Bubble each cut the very thing they amplify,
    # so both sit in this table and the one above.
    'incoming_multipliers': {
        'punk-rock':    {'condition': 'sound', 'multiplier': 0.5},
        'water-bubble': {'condition': 'move_type', 'types': ['fire'], 'multiplier': 0.5},

        # --- Block 2 ---
        'thick-fat':      {'condition': 'move_type', 'types': ['fire', 'ice'], 'multiplier': 0.5},
        'heatproof':      {'condition': 'move_type', 'types': ['fire'], 'multiplier': 0.5},
        'purifying-salt': {'condition': 'move_type', 'types': ['ghost'], 'multiplier': 0.5},
        'fur-coat':       {'condition': 'move_class', 'classes': ['physical'], 'multiplier': 0.5},
        'ice-scales':     {'condition': 'move_class', 'classes': ['special'], 'multiplier': 0.5},
    },

    # A flat multiplier on one of the specimen's OWN stats, read where the damage formula
    # picks which Attack and Defense it is using. Conditions are all optional and AND
    # together; a bare entry is unconditional.
    #
    #   stats     - which of attack/sp_atk/defense/sp_def it moves
    #   status    - '*' for any major status, or a list of specific ones
    #   weather   - only while one of these is on the field
    #   terrain   - only while one of these is underfoot
    #   hp_at_or_below - only at or under this fraction of max HP
    #   unburdened - only while it has lost the item it came in holding
    #   turns_on_field_below - only for its first N turns since arriving
    'stat_multipliers': {
        'huge-power':      {'stats': ['attack'], 'multiplier': 2.0},
        'pure-power':      {'stats': ['attack'], 'multiplier': 2.0},
        'hustle':          {'stats': ['attack'], 'multiplier': 1.5},
        'gorilla-tactics': {'stats': ['attack'], 'multiplier': 1.5},
        'toxic-boost':     {'stats': ['attack'], 'multiplier': 1.5, 'status': ['poison']},
        'flare-boost':     {'stats': ['sp_atk'], 'multiplier': 1.5, 'status': ['burn']},
        'marvel-scale':    {'stats': ['defense'], 'multiplier': 1.5, 'status': '*'},
        'grass-pelt':      {'stats': ['defense'], 'multiplier': 1.5, 'terrain': ['grassy']},
        'solar-power':     {'stats': ['sp_atk'], 'multiplier': 1.5,
                            'weather': ['sun', 'extremely-harsh-sunlight']},
        'defeatist':       {'stats': ['attack', 'sp_atk'], 'multiplier': 0.5,
                            'hp_at_or_below': 0.5},

        # --- Block 3: conditional speed. Same table, same conditions - the only new ones
        # are `unburdened` and `turns_on_field_below`. Slow Start halves Attack as well as
        # Speed, and gets both from the one row.
        'swift-swim':      {'stats': ['speed'], 'multiplier': 2.0,
                            'weather': ['rain', 'heavy-rain']},
        'chlorophyll':     {'stats': ['speed'], 'multiplier': 2.0,
                            'weather': ['sun', 'extremely-harsh-sunlight']},
        'sand-rush':       {'stats': ['speed'], 'multiplier': 2.0,
                            'weather': ['sand', 'sandstorm']},
        'slush-rush':      {'stats': ['speed'], 'multiplier': 2.0,
                            'weather': ['hail', 'snow']},
        'surge-surfer':    {'stats': ['speed'], 'multiplier': 2.0, 'terrain': ['electric']},
        'quick-feet':      {'stats': ['speed'], 'multiplier': 1.5, 'status': '*'},
        'unburden':        {'stats': ['speed'], 'multiplier': 2.0, 'unburdened': True},
        'slow-start':      {'stats': ['attack', 'speed'], 'multiplier': 0.5,
                            'turns_on_field_below': 5},
    },
    'end_of_turn': {
        'speed-boost': {'type': 'stat', 'stat': 'speed', 'value': 1},
        'moody':       {'type': 'stat', 'stat': 'random', 'value': 2, 'drop_value': -1}, # Moody is complex but easy to scale later!
        'shed-skin':   {'type': 'cure', 'chance': 33},
        'rain-dish':   {'type': 'weather_heal', 'weather': ['rain', 'heavy-rain'], 'denominator': 16},
        'ice-body':    {'type': 'weather_heal', 'weather': ['hail'], 'denominator': 16},
        # 🚨 NEW: Pathogen Symbiosis
        'poison-heal': {'type': 'status_heal', 'status': 'poison', 'denominator': 8},

        # Shed Skin's weather-gated cousin - certain rather than a 33% roll
        'hydration':   {'type': 'weather_cure', 'weather': ['rain', 'heavy-rain']},
        # The only end-of-turn trait aimed at the OPPONENT rather than its owner
        'bad-dreams':  {'type': 'sleep_drain', 'denominator': 8},

        # Solar Power's price for the Sp. Atk it grants - the mirror of a weather_heal
        'solar-power': {'type': 'weather_toll', 'weather': ['sun', 'extremely-harsh-sunlight'],
                        'denominator': 8},
    },
    'contact_status': {
        'static': {'status': 'paralysis', 'immune': 'electric'},
        'flame-body': {'status': 'burn', 'immune': 'fire'},
        'poison-point': {'status': 'poison', 'immune': 'poison'},
        'effect-spore': {'status': 'poison', 'immune': 'poison'}
    },

    # The mirror of contact_status: the ATTACKER's ability infecting whoever it touches,
    # rather than the defender's punishing whoever touched it.
    'contact_status_offensive': {
        'poison-touch': {'status': 'poison', 'immune': 'poison', 'chance': 30},
    },
    'contact_damage': ['rough-skin', 'iron-barbs'],
}

# Statuses an ability simply refuses. Replaces the ad-hoc Insomnia branch that used to sit
# alone in the immunity filter; Block 7 (Immunity, Limber, Magma Armor, Water Veil...)
# extends this rather than adding more branches beside it.
# '*' means every major status, not just the ones listed elsewhere.
ALL_STATUSES = '*'

STATUS_IMMUNE_ABILITIES = {
    'insomnia':       {'sleep'},
    'vital-spirit':   {'sleep'},
    'water-bubble':   {'burn'},
    'purifying-salt': ALL_STATUSES,
}

# Abilities that rewrite how heavy their owner is, for Grass Knot, Low Kick, Heat Crash
# and the rest of the weight-scaled family.
WEIGHT_MULTIPLIER_ABILITIES = {
    'heavy-metal': 2.0,
    'light-metal': 0.5,
}

# Abilities that lock their owner into the first move it picks, exactly as a Choice item
# does. Kept beside the items rather than inside them so the UI can ask one question.
CHOICE_LOCK_ABILITIES = {'gorilla-tactics'}

# Abilities that halve the end-of-turn burn toll.
BURN_TOLL_HALVED_BY = {'heatproof'}

# What an ability does to the accuracy of the move its owner throws.
ACCURACY_MULTIPLIER_ABILITIES = {
    'hustle': 0.8,           # pays for its Attack boost
    'compound-eyes': 1.3,
    'victory-star': 1.1,
}

# The other side of the same roll: what an ability does to its owner's EVASION. A higher
# number is harder to hit, so these divide the attacker's chance rather than multiplying
# it. Conditions are optional and AND together, as in stat_multipliers.
EVASION_MULTIPLIER_ABILITIES = {
    'sand-veil':    {'multiplier': 1.25, 'weather': ['sand', 'sandstorm']},
    'snow-cloak':   {'multiplier': 1.25, 'weather': ['hail', 'snow']},
    'tangled-feet': {'multiplier': 2.0, 'confused': True},
}

# Wonder Skin drags an incoming STATUS move down to a coin flip - and only ever downwards,
# so it cannot make a shaky move more likely to land.
WONDER_SKIN_ACCURACY = 50

# Abilities that add crit stages. Super Luck is the only one; Merciless forces the crit
# outright rather than nudging the odds, so it lives with the guaranteed-crit rule.
CRIT_STAGE_ABILITIES = {
    'super-luck': 1,
}

# ==========================================
# 🎭 BLOCK 5: MOVE-PROPERTY REWRITES
# ==========================================
# Everything here changes what the move IS before anything reads it.
#
# The -ate family carries the CURRENT generation's 1.2x. They were nerfed from 1.3 in
# Gen 7, which is why PokeAPI's older text still says 1.3 for three of them.
#
#   from       - only rewrites moves of this element ('*' for every move)
#   sound      - rewrites sound moves instead, whatever their element
TYPE_REWRITE_ABILITIES = {
    'aerilate':     {'from': 'normal', 'to': 'flying',   'multiplier': 1.2},
    'pixilate':     {'from': 'normal', 'to': 'fairy',    'multiplier': 1.2},
    'refrigerate':  {'from': 'normal', 'to': 'ice',      'multiplier': 1.2},
    'galvanize':    {'from': 'normal', 'to': 'electric', 'multiplier': 1.2},
    'dragonize':    {'from': 'normal', 'to': 'dragon',   'multiplier': 1.2},
    'normalize':    {'from': '*',      'to': 'normal',   'multiplier': 1.2},
    'liquid-voice': {'sound': True,    'to': 'water',    'multiplier': 1.0},
}

# The user takes on the element of the move it is throwing, before it lands.
PROTEAN_ABILITIES = {'protean', 'libero'}

# Mimicry wears the terrain.
MIMICRY_TYPES = {'electric': 'electric', 'grassy': 'grass',
                 'misty': 'fairy', 'psychic': 'psychic'}

# Normal and Fighting reach Ghost types.
GHOST_PIERCING_ABILITIES = {'scrappy', 'minds-eye'}

# The target's evasion is ignored entirely.
EVASION_IGNORING_ABILITIES = {'minds-eye'}

# These moves never make contact, so nothing that punishes contact can answer them.
NO_CONTACT_ABILITIES = {'long-reach'}

# Contact moves punch straight through Protect and Detect.
PROTECT_PIERCING_ABILITIES = {'unseen-fist', 'piercing-drill'}

# Poison lands on Poison and Steel types anyway.
CORROSIVE_ABILITIES = {'corrosion'}

# What an ability does to the chance of a move's SECONDARY effect firing, and who ignores
# those effects altogether.
SECONDARY_CHANCE_ABILITIES = {'serene-grace': 2.0}
SECONDARY_IMMUNE_ABILITIES = {'shield-dust'}

# A flinch chance stapled onto every damaging move the owner throws.
FLINCH_ON_HIT_ABILITIES = {'stench': 10}

# Parental Bond's second strike, at the current generation's quarter power rather than
# the half PokeAPI's Gen 6 text describes.
PARENTAL_BOND_SECOND_HIT = 0.25

# Toxic Chain's chance to poison on contact with a move. The schema has no separate bad
# poison, so this lands as ordinary poison - the same simplification Toxic already makes.
TOXIC_CHAIN_CHANCE = 30

# Poison Puppeteer adds confusion to anything ITS OWNER poisons.
POISON_CONFUSION_ABILITIES = {'poison-puppeteer'}

# Adaptability's upgraded same-type bonus.
ADAPTABILITY_STAB = 2.0

# Abilities that shrug off the end-of-turn weather chip, and WHICH weather each one
# shelters from - Sand Veil is no help in hail. Type immunity is handled separately, on
# the types themselves. Block 7 adds Overcoat and Magic Guard, which shelter from both.
WEATHER_CHIP_IMMUNE_ABILITIES = {
    'sand-force': {'sand', 'sandstorm'},
    'sand-veil':  {'sand', 'sandstorm'},
    'snow-cloak': {'hail', 'snow'},
}


def shrugs_off_weather(ability, weather):
    """True when this ability shelters its owner from this weather's chip damage."""
    return weather in WEATHER_CHIP_IMMUNE_ABILITIES.get(ability, ())

# ==========================================
# KINETIC MULTI-STRIKE PROFILES
# ==========================================
MULTI_STRIKE_MOVES = {
    # The 2-to-5 hit variables
    'bullet-seed':    {'min': 2, 'max': 5},
    'icicle-spear':   {'min': 2, 'max': 5},
    'rock-blast':     {'min': 2, 'max': 5},
    'pin-missile':    {'min': 2, 'max': 5},
    'arm-thrust':     {'min': 2, 'max': 5},
    'fury-swipes':    {'min': 2, 'max': 5},
    'bone-rush':      {'min': 2, 'max': 5},
    'scale-shot':     {'min': 2, 'max': 5},
    'water-shuriken': {'min': 2, 'max': 5},
    'tail-slap':      {'min': 2, 'max': 5},
    'barrage':      {'min': 2, 'max': 5},
    'comet-punch':      {'min': 2, 'max': 5},
    'double-slap':      {'min': 2, 'max': 5},
    'fury-attack':      {'min': 2, 'max': 5},
    'spike-cannon':      {'min': 2, 'max': 5},
    
    
    # Fixed-hit anomalies
    'double-kick':     {'min': 2, 'max': 2},
    'dual-chop':       {'min': 2, 'max': 2},
    'gear-grind':     {'min': 2, 'max': 2},
    'twin-beam':       {'min': 2, 'max': 2},
    'dragon-darts':    {'min': 2, 'max': 2},
    'surging-strikes': {'min': 3, 'max': 3},
    'triple-dive':     {'min': 3, 'max': 3},
    'bonemerang':     {'min': 2, 'max': 2},
    'double-hit':     {'min': 2, 'max': 2},
    'double-iron-bash':     {'min': 2, 'max': 2},
    'dual-wingbeat':     {'min': 2, 'max': 2},
    'gear-grind':     {'min': 2, 'max': 2},
    'surging-strikes':     {'min': 3, 'max': 3},
    'tachyon-cutter':     {'min': 2, 'max': 2},
    'twineedle':     {'min': 2, 'max': 2},
    'water-shuriken':     {'min': 3, 'max': 3},
    
    # The 10-hit swarm anomaly
    'population-bomb': {'min': 1, 'max': 10}
}