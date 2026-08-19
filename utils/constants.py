import json
import os
import random
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
    "booster-energy":  {"name": "Booster Energy", "price": 0, "desc": "Runs a Paradox specimen's Protosynthesis or Quark Drive when the field will not. Single use.", "emoji": "🧪", "category": "formitems", "purchasable": False},
    
    # Evolution Items
    "water-stone":    {"name": "Water Stone", "price": 500, "desc": "A stone that makes certain pokemon evolve. It is clear, blue and glistens.", "emoji": "💎", "category": "evoitems"},
    "leaf-stone":    {"name": "Leaf Stone", "price": 500, "desc": "A stone that makes certain pokemon evolve. It is green and mossy.", "emoji": "💎", "category": "evoitems"},
    "fire-stone":    {"name": "Fire Stone", "price": 500, "desc": "A stone that makes certain pokemon evolve. It is clear, orange and glistens.", "emoji": "💎", "category": "evoitems"},
    "rare-candy":    {"name": "Rare Candy", "price": 10000, "desc": "A sweet treat that increases a pokemon's level by 1.", "emoji": "🍬", "category": "evoitems"},

    # ==========================================
    # HELD BATTLE EQUIPMENT
    # ==========================================
    # Every entry below is an item the ENGINE ACTUALLY READS, and the description says
    # what the engine does rather than what the games do. That distinction is the whole
    # point of this block: a scan of the source turns up around sixty competitive item
    # names, and most of them are ghosts. `wise-glasses`, `eviolite`, `wide-lens`,
    # `heavy-duty-boots`, `weakness-policy`, the type-boosting stones and the four seeds
    # appear only in FLING_POWER (what the item weighs when thrown), in ONE_USE_ITEMS
    # (that it is spent, not what it does), or in an NPC's `item_pool`. None of those is
    # an implementation, and selling them would be selling nothing.
    #
    # Priced cheap on purpose - this is meant to make team building possible, not to be
    # a money sink. Six hundred for the ones that define a set, four hundred for the
    # situational ones; a single trainer battle already pays several hundred.
    #
    # The rest of the competitive roster arrives as the item layer gets coded. Adding one
    # here before the engine reads it would put a ghost in the shop.

    # -- the ones that define a set --
    "leftovers":     {"name": "Leftovers", "price": 600, "desc": "Restores 1/16 max HP at the end of each turn.", "emoji": "🍎", "category": "battleitems"},
    "choice-band":   {"name": "Choice Band", "price": 600, "desc": "1.5x Attack, but locks the holder into its first move.", "emoji": "🎗️", "category": "battleitems"},
    "choice-specs":  {"name": "Choice Specs", "price": 600, "desc": "1.5x Special Attack, but locks the holder into its first move.", "emoji": "🎗️", "category": "battleitems"},
    "choice-scarf":  {"name": "Choice Scarf", "price": 600, "desc": "1.5x Speed, but locks the holder into its first move.", "emoji": "🎗️", "category": "battleitems"},
    "life-orb":      {"name": "Life Orb", "price": 600, "desc": "1.3x damage on every attack.", "emoji": "🔮", "category": "battleitems"},
    "focus-sash":    {"name": "Focus Sash", "price": 600, "desc": "Survives one otherwise-lethal hit on 1 HP, from full health. Single use.", "emoji": "🎀", "category": "battleitems"},
    "assault-vest":  {"name": "Assault Vest", "price": 600, "desc": "1.5x Special Defense, but the holder cannot use status moves.", "emoji": "🦺", "category": "battleitems"},

    # -- situational --
    "black-sludge":  {"name": "Black Sludge", "price": 400, "desc": "Restores 1/16 max HP each turn to Poison types, and costs 1/8 to everything else.", "emoji": "🧪", "category": "battleitems"},
    "expert-belt":   {"name": "Expert Belt", "price": 400, "desc": "1.2x damage on super-effective hits.", "emoji": "🥋", "category": "battleitems"},
    "rocky-helmet":  {"name": "Rocky Helmet", "price": 400, "desc": "Hurts attackers that make contact.", "emoji": "⛑️", "category": "battleitems"},
    "air-balloon":   {"name": "Air Balloon", "price": 400, "desc": "Lifts the holder out of reach of Ground-type moves and ground hazards.", "emoji": "🎈", "category": "battleitems"},
    "scope-lens":    {"name": "Scope Lens", "price": 400, "desc": "Raises the holder's critical-hit rate.", "emoji": "🔍", "category": "battleitems"},
    "razor-claw":    {"name": "Razor Claw", "price": 400, "desc": "Raises the holder's critical-hit rate.", "emoji": "🪒", "category": "battleitems"},
    "toxic-orb":     {"name": "Toxic Orb", "price": 400, "desc": "Badly poisons the holder at the end of the turn. For Poison Heal, Toxic Boost and Guts.", "emoji": "☣️", "category": "battleitems"},
    "flame-orb":     {"name": "Flame Orb", "price": 400, "desc": "Burns the holder at the end of the turn. For Flare Boost and Guts.", "emoji": "🔥", "category": "battleitems"},
    "power-herb":    {"name": "Power Herb", "price": 400, "desc": "Fires a two-turn move instantly. Single use.", "emoji": "🌿", "category": "battleitems"},
    "light-clay":    {"name": "Light Clay", "price": 400, "desc": "Extends Reflect, Light Screen and Aurora Veil from 5 turns to 8.", "emoji": "🔆", "category": "battleitems"},

    # -- field extenders, one per sky plus the terrain --
    "heat-rock":     {"name": "Heat Rock", "price": 400, "desc": "Extends the holder's harsh sunlight from 5 turns to 8.", "emoji": "☀️", "category": "battleitems"},
    "damp-rock":     {"name": "Damp Rock", "price": 400, "desc": "Extends the holder's rain from 5 turns to 8.", "emoji": "🌧️", "category": "battleitems"},
    "smooth-rock":   {"name": "Smooth Rock", "price": 400, "desc": "Extends the holder's sandstorm from 5 turns to 8.", "emoji": "🏜️", "category": "battleitems"},
    "icy-rock":      {"name": "Icy Rock", "price": 400, "desc": "Extends the holder's hail from 5 turns to 8.", "emoji": "❄️", "category": "battleitems"},
    "terrain-extender": {"name": "Terrain Extender", "price": 400, "desc": "Extends the holder's terrain from 5 turns to 8.", "emoji": "🌐", "category": "battleitems"},

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
    discord.SelectOption(label="Battle Equipment", value="battleitems", emoji="⚔️"),
    # Its own shelf rather than fifty-eight more rows under Battle Equipment, which
    # would have buried the Choice trio and the rocks six pages deep.
    discord.SelectOption(label="Type Boosters", value="typeboost", emoji="💠"),
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

# ==========================================
# 💎 ITEM PHASE 1: THE TYPE-BOOSTER TABLE
# ==========================================
# There was no type-booster table in the engine at all. That single absence is why every
# item in PokeAPI's `type-enhancement` category was a ghost AND why all seventeen
# elemental plates were only half-live: PLATE_TYPES already drove Judgment's element and
# Multitype's form, but the "20% more damage" half of every plate description had never
# existed anywhere. One dict finishes both, plus the gems, which are the same rule with
# a single-use flag.
#
# The plate half is NOT repeated here. It is derived from PLATE_TYPES in formulas.py,
# because that table already exists and a second copy of it is precisely the drift
# `type_from_item` was split out to prevent.

TYPE_BOOST_MULTIPLIER = 1.2

# Moved here from formulas.py, where it drove Judgment's element and Multitype's form.
# It has a second reader now - the shop stocks the same seventeen names - and formulas.py
# re-exports it, so anything importing it from there is unaffected.
PLATE_TYPES = {
    'draco-plate': 'dragon', 'dread-plate': 'dark', 'earth-plate': 'ground',
    'fist-plate': 'fighting', 'flame-plate': 'fire', 'icicle-plate': 'ice',
    'insect-plate': 'bug', 'iron-plate': 'steel', 'meadow-plate': 'grass',
    'mind-plate': 'psychic', 'pixie-plate': 'fairy', 'sky-plate': 'flying',
    'splash-plate': 'water', 'spooky-plate': 'ghost', 'stone-plate': 'rock',
    'toxic-plate': 'poison', 'zap-plate': 'electric',
}

# The permanent holdables: one per element, 1.2x to moves of that type.
TYPE_ENHANCER_ITEMS = {
    'black-belt':     'fighting',
    'black-glasses':  'dark',
    'charcoal':       'fire',
    'dragon-fang':    'dragon',
    'hard-stone':     'rock',
    'magnet':         'electric',
    'metal-coat':     'steel',
    'miracle-seed':   'grass',
    'mystic-water':   'water',
    'never-melt-ice': 'ice',
    'poison-barb':    'poison',
    'sharp-beak':     'flying',
    'silk-scarf':     'normal',
    'silver-powder':  'bug',
    'soft-sand':      'ground',
    'spell-tag':      'ghost',
    'twisted-spoon':  'psychic',
    # The incenses are the same 1.2x under different names, kept as separate entries
    # rather than aliased because a player holding a Sea Incense holds a Sea Incense.
    'odd-incense':    'psychic',
    'rock-incense':   'rock',
    'rose-incense':   'grass',
    'sea-incense':    'water',
    'wave-incense':   'water',
    # Fairy Feather sits in a different PokeAPI category and so fell outside the phase
    # as scoped. Included anyway: leaving Fairy as the one element with no booster is a
    # hole a team builder finds in about a minute.
    'fairy-feather':  'fairy',
}

# Gems are consumed on use. Gen VI onwards they are 1.3x, not the 1.5x the PokeAPI
# text still quotes - and this engine is Gen VI+ elsewhere (CRIT_DAMAGE_MULTIPLIER is
# 1.5, not the old 2.0), so following the generation beats following the description.
TYPE_GEM_MULTIPLIER = 1.3

# Written out rather than generated from the type list. A comprehension would be shorter
# and would put none of these eighteen names in the source, which matters: the item
# audit finds an implementation by looking for the item's name, and a table whose keys
# only exist at runtime reads as eighteen items nobody has done yet.
TYPE_GEMS = {
    'bug-gem':      'bug',
    'dark-gem':     'dark',
    'dragon-gem':   'dragon',
    'electric-gem': 'electric',
    'fairy-gem':    'fairy',
    'fighting-gem': 'fighting',
    'fire-gem':     'fire',
    'flying-gem':   'flying',
    'ghost-gem':    'ghost',
    'grass-gem':    'grass',
    'ground-gem':   'ground',
    'ice-gem':      'ice',
    'normal-gem':   'normal',
    'poison-gem':   'poison',
    'psychic-gem':  'psychic',
    'rock-gem':     'rock',
    'steel-gem':    'steel',
    'water-gem':    'water',
}

# Deliberately NOT boosters, and named here so their absence reads as a decision.
# Blank Plate reverts Arceus to Normal and Legend Plate grants every type at once;
# neither is "1.2x to one element", so neither belongs in the table and neither is
# sold until somebody implements what they actually do.
INERT_PLATES = {'blank-plate', 'legend-plate'}

TYPE_EMOJI = {
    'normal': '⬜', 'fire': '🔥', 'water': '💧', 'electric': '⚡', 'grass': '🌿',
    'ice': '🧊', 'fighting': '🥊', 'poison': '☠️', 'ground': '⛰️', 'flying': '🕊️',
    'psychic': '🔮', 'bug': '🐛', 'rock': '🪨', 'ghost': '👻', 'dragon': '🐉',
    'dark': '🌑', 'steel': '⚙️', 'fairy': '🧚',
}

# Prices, in the same band as the battle equipment already on sale (400 situational,
# 600 set-defining). A plate costs more than a plain enhancer because it does two jobs:
# the 20% AND Judgment's element. A gem costs least because it is gone after one move.
PLATE_PRICE = 500
TYPE_ENHANCER_PRICE = 400
TYPE_GEM_PRICE = 200


def build_type_booster_stock():
    """
    The shop shelf for Phase 1, generated from the tables the ENGINE reads.

    Written out programmatically rather than as fifty-eight literal rows, so the shop
    cannot come to disagree with the damage formula about which items exist or what
    element they boost - which is the failure this whole phase was fixing, one layer up.
    """
    stock = {}

    for item, element in PLATE_TYPES.items():
        stock[item] = {
            "name": item.replace('-', ' ').title(),
            "price": PLATE_PRICE,
            "desc": f"1.2x to {element.title()} moves, and sets Arceus/Judgment to {element.title()}.",
            "emoji": TYPE_EMOJI.get(element, '💠'),
            "category": "typeboost",
        }

    for item, element in TYPE_ENHANCER_ITEMS.items():
        stock[item] = {
            "name": item.replace('-', ' ').title(),
            "price": TYPE_ENHANCER_PRICE,
            "desc": f"1.2x damage to the holder's {element.title()}-type moves.",
            "emoji": TYPE_EMOJI.get(element, '💠'),
            "category": "typeboost",
        }

    for item, element in TYPE_GEMS.items():
        stock[item] = {
            "name": item.replace('-', ' ').title(),
            "price": TYPE_GEM_PRICE,
            "desc": f"{TYPE_GEM_MULTIPLIER}x to one {element.title()}-type move, then it is used up.",
            "emoji": TYPE_EMOJI.get(element, '💠'),
            "category": "typeboost",
        }

    return stock


# Stocked onto the shelf here rather than by hand inside EQUIPMENT_CATALOG above,
# because the tables this reads are defined below it - and because fifty-eight rows
# typed out by hand is fifty-eight chances to mistype an element.
EQUIPMENT_CATALOG.update(build_type_booster_stock())


# ==========================================
# 💥 ITEM PHASE 2: THE ONE-SHOT POLICIES AND SEEDS
# ==========================================
# All fourteen were already named in ONE_USE_ITEMS, which is exactly what made them look
# finished: that set records that an item is SPENT, not what spending it does. A
# specimen holding a Weakness Policy fought as though its hands were empty, and then the
# empty hands were faithfully written back to the database.
#
# Every one is the same sentence - "when X happens to me, move a stat stage and consume
# myself" - which is the shape Block 14's reaction table already has for abilities. So
# this is the same table, keyed on the item instead, and its stage changes are enqueued
# rather than written: a Weakness Policy boost meets Block 8's resolver the same way a
# Swords Dance does, which is what makes it copyable by Opportunist and refusable by
# nothing (boosts are never screened) without either of those being restated here.
# Stat names here are the RESOLVER's vocabulary - 'special-attack', not 'sp_atk'.
# STAT_STAGE_KEYS translates those into the storage keys, and it does so with a .get
# that silently skips anything it does not recognise: a table written in the storage
# spelling produces no error, no log line and no boost. Everything else that enqueues a
# stage - natures, moves, ON_HIT_REACTIONS - speaks the same dialect for the same reason.
ITEM_HIT_REACTIONS = {
    'absorb-bulb':     {'types': ['water'],      'self': [('special-attack', 1)]},
    'cell-battery':    {'types': ['electric'],   'self': [('attack', 1)]},
    'luminous-moss':   {'types': ['water'],      'self': [('special-defense', 1)]},
    'snowball':        {'types': ['ice'],        'self': [('attack', 1)]},
    # The only one that reads effectiveness rather than element, and the only one worth
    # two stages - it is a deliberate invitation to be hit hard once.
    'weakness-policy': {'super_effective': True,
                        'self': [('attack', 2), ('special-attack', 2)]},
}

# The seeds fire on ARRIVAL into a terrain, and again when a terrain is laid under a
# specimen already standing there. Both, not either: a Grassy Seed that only worked on
# switch-in would sit inert through the Grassy Surge it was bought for.
TERRAIN_SEED_ITEMS = {
    'electric-seed': ('electric', 'defense'),
    'grassy-seed':   ('grassy',   'defense'),
    'misty-seed':    ('misty',    'special-defense'),
    'psychic-seed':  ('psychic',  'special-defense'),
}

# The three that answer something other than being hit.
THROAT_SPRAY_BOOST = ('special-attack', 1)   # after using a sound move
BLUNDER_POLICY_BOOST = ('speed', 2)     # after missing because of accuracy
ROOM_SERVICE_DROP = ('speed', -1)       # when Trick Room goes up

# What a Mental Herb frees its holder from. Infatuation is the Gen III effect; the rest
# arrived in Gen V, and all five are volatiles this engine already tracks by these
# names, so the herb is a sweep over one tuple rather than five special cases.
MENTAL_HERB_CURES = ('infatuation', 'taunt', 'encore', 'torment', 'disable')

# ==========================================
# 💥 THE PHASE 2 SHELF
# ==========================================
# Cheaper than the Choice trio and the Life Orb on purpose. Every one of these is a
# conditional item - it does nothing at all unless the battle goes a particular way -
# so pricing it beside an item that works every single turn would mean nobody ever
# buys one, and the point of stocking them is to give team building something to think
# about rather than to sell tokens' worth of value.
PHASE2_PRICE = 250

# Read off the same tables the ENGINE reads, so a shop description cannot come to
# disagree with what the item does - the lesson from the type-booster shelf, where the
# alternative was fifty-eight hand-typed rows and fifty-eight chances to mistype one.
PHASE2_DESCRIPTIONS = {
    'absorb-bulb':     "Raises Sp. Atk one stage when hit by a Water move. Single use.",
    'cell-battery':    "Raises Attack one stage when hit by an Electric move. Single use.",
    'luminous-moss':   "Raises Sp. Def one stage when hit by a Water move. Single use.",
    'snowball':        "Raises Attack one stage when hit by an Ice move. Single use.",
    'weakness-policy': "Raises Attack AND Sp. Atk two stages each when hit by a super "
                       "effective move. Single use.",
    'blunder-policy':  "Raises Speed two stages when a move misses. Single use.",
    'throat-spray':    "Raises Sp. Atk one stage after a sound-based move. Single use.",
    'room-service':    "Lowers Speed one stage when Trick Room goes up. Single use.",
    'white-herb':      "Restores every lowered stat the moment one falls. Single use.",
    'mental-herb':     "Clears infatuation, Taunt, Encore, Torment or Disable. Single use.",
    'electric-seed':   "Raises Defense one stage on Electric Terrain. Single use.",
    'grassy-seed':     "Raises Defense one stage on Grassy Terrain. Single use.",
    'misty-seed':      "Raises Sp. Def one stage on Misty Terrain. Single use.",
    'psychic-seed':    "Raises Sp. Def one stage on Psychic Terrain. Single use.",
}

PHASE2_EMOJI = {
    'absorb-bulb': '💧', 'cell-battery': '🔋', 'luminous-moss': '🌿',
    'snowball': '❄️', 'weakness-policy': '🛡️', 'blunder-policy': '💨',
    'throat-spray': '🎤', 'room-service': '🛎️', 'white-herb': '🌱',
    'mental-herb': '🍃', 'electric-seed': '⚡', 'grassy-seed': '🌾',
    'misty-seed': '🌫️', 'psychic-seed': '🔮',
}


def build_phase2_stock():
    """The Phase 2 shelf, checked against the tables the engine actually reads.

    The assertion is the point: an item described here that no table implements would
    be an item the shop sells and the engine ignores, which is the exact failure
    `test_shop_catalog.py` exists to prevent. Better to fail at import than to take
    somebody's tokens for a rock.
    """
    implemented = (set(ITEM_HIT_REACTIONS) | set(TERRAIN_SEED_ITEMS)
                   | {'throat-spray', 'blunder-policy', 'room-service',
                      'white-herb', 'mental-herb'})
    missing = implemented - set(PHASE2_DESCRIPTIONS)
    assert not missing, f"Phase 2 items with no shop entry: {sorted(missing)}"
    extra = set(PHASE2_DESCRIPTIONS) - implemented
    assert not extra, f"Phase 2 shop entries with no implementation: {sorted(extra)}"

    return {
        item: {
            "name": item.replace('-', ' ').title(),
            "price": PHASE2_PRICE,
            "desc": PHASE2_DESCRIPTIONS[item],
            "emoji": PHASE2_EMOJI.get(item, '💥'),
            "category": "battleitems",
        }
        for item in sorted(implemented)
    }


EQUIPMENT_CATALOG.update(build_phase2_stock())


# ==========================================
# 💿 THE TM SHELF
# ==========================================
# TMs used to be their own command with their own hand-written emoji map, which meant a
# player had to know the shop was in two places and that one of them was called
# something else. They are a shelf in the market now.
#
# They are deliberately NOT merged into EQUIPMENT_CATALOG. A TM is not a backpack item:
# it lives in `user_tms`, not `user_inventory`, and `!buy` routes on that distinction.
# Putting them in the item catalogue would have sent every TM purchase to the wrong
# table - and would have offered them to `!sell` and `!equip`, neither of which can do
# anything with one. So there are two dictionaries: what ITEMS exist, and what the SHOP
# displays.
def build_tm_stock():
    """
    The TM shelf, described from `base_moves` rather than from a hand-written map.

    The old shop listed a price and nothing else - no type, no power, no indication of
    what you were buying beyond the name. Reading the move table means the description
    cannot come to disagree with what the move actually does in battle, and a TM added
    to TM_SHOP tomorrow describes itself without anybody writing a line of prose.
    """
    stock = {}

    details = {}
    try:
        import sqlite3 as _sqlite3
        with _sqlite3.connect(DB_FILE) as _conn:
            marks = ','.join('?' * len(TM_SHOP))
            details = {
                row[0]: row[1:]
                for row in _conn.execute(
                    f"SELECT name, type, power, damage_class FROM base_moves "
                    f"WHERE name IN ({marks})", tuple(TM_SHOP))
            }
    except Exception as e:
        # A shop that lists names and prices with no blurb is a worse shop, not a
        # broken one. Never let this stop the bot booting.
        print(f"⚠️ WARNING: could not read move data for the TM shelf ({e}).")

    for move, price in TM_SHOP.items():
        element, power, damage_class = details.get(move, (None, None, None))
        pretty = move.replace('-', ' ').title()

        if element and damage_class == 'status':
            desc = f"Teaches {pretty}. A {element.title()}-type status move."
        elif element and power:
            desc = f"Teaches {pretty}. {element.title()}-type, {power} power."
        elif element:
            desc = f"Teaches {pretty}. {element.title()}-type."
        else:
            desc = f"Teaches {pretty}."

        stock[move] = {
            "name": f"TM {pretty}",
            "price": price,
            "desc": f"{desc} Apply it with `!tm`.",
            "emoji": TYPE_EMOJI.get(element, '💿'),
            "category": "tm",
        }

    return stock


TM_CATALOG = build_tm_stock()

# What the SHOP puts on its shelves, as opposed to what items exist. `!sell`, `!equip`
# and `!backpack` all still read EQUIPMENT_CATALOG, because a TM is not a thing you can
# hold, sell or carry in a backpack.
SHOP_CATALOG = {**EQUIPMENT_CATALOG, **TM_CATALOG}

CATEGORY_OPTIONS.append(
    discord.SelectOption(label="TMs", value="tm", emoji="💿"))


# ==========================================
# 📡 BROADCAST CHANNELS
# ==========================================
# These were bare numbers in the middle of a function, with the alternative server's id
# kept alive in a trailing comment. Switching servers meant editing a line of code and
# hoping the comment stayed accurate.
#
# Both servers are named here instead, and the active one is chosen once. Every reader
# treats a missing channel as "do not broadcast" rather than as an error, so setting an
# id to None is a supported way to turn a broadcast off.
CHANNELS = {
    'official': {
        'broadcast': 1487606904321736764,   # rare, shiny and legendary spawns
        'trade_log': 1487605383857176777,   # the trade ledger's readable tail
    },
    'beta': {
        'broadcast': 1491524019495895171,
        # Beta has no trade-log channel of its own yet. None means "do not broadcast",
        # which is a working configuration rather than a broken one - the ledger is the
        # database table, and the channel post is a convenience on top of it.
        'trade_log': None,
    },
}

ACTIVE_SERVER = 'official'

OFFICIAL_BROADCAST_CHANNEL_ID = CHANNELS[ACTIVE_SERVER]['broadcast']
TRADE_LOG_CHANNEL_ID = CHANNELS[ACTIVE_SERVER]['trade_log']

# ==========================================
# 🌱 WHAT THE WORLD IS ALLOWED TO PRODUCE
# ==========================================
# `base_pokemon_species` is a form table, not a species table. Alongside the 1062
# ordinary entries it holds megas, Gigantamax forms, totems, Ash-Greninja, Zygarde's
# power levels and a dozen other things that exist only inside a battle. None of them
# can be encountered in the wild, and none of them should ever be the answer to
# "what appeared?" or "what are you being asked to find?".
#
# The list lived as a copy-pasted SQL literal in three queries and was simply absent
# from two more, which is exactly how `!spawn` ended up able to produce a mega and how
# the Genetic Population Survey ended up asking players to go and tag a Totem Mimikyu.
# One tuple, one helper, every query.
SPAWNABLE_FORM_TYPES = ('base', 'alolan', 'galarian', 'hisuian', 'paldean')

# The Ultra Beasts, written out rather than expressed as a range. `793-806` is the range
# they LOOK like they occupy, and it was used in seven queries - but three of the
# fourteen ids inside it are not Ultra Beasts at all:
#
#     800  Necrozma   (legendary)
#     801  Magearna   (mythical)
#     802  Marshadow  (mythical)
#
# That single off-by-three did two separate things. A spatial rift, which is supposed to
# flood the habitat with invasive Ultra Beasts, could produce Magearna or Marshadow
# instead; and the matching NOT-BETWEEN in every ordinary spawn query excluded those
# three from the world entirely, so the only way to see a Necrozma was a dimensional
# rift. They are ordinary legendaries and mythicals now, appearing at the same rarity as
# every other one, and the rift produces only the eleven real Ultra Beasts.
ULTRA_BEAST_IDS = (793, 794, 795, 796, 797, 798, 799, 803, 804, 805, 806)


def ultra_beasts(alias=None, negate=False):
    """The SQL fragment selecting - or excluding - the Ultra Beasts."""
    prefix = f"{alias}." if alias else ""
    joined = ", ".join(str(dex) for dex in ULTRA_BEAST_IDS)
    return f"{prefix}pokedex_id {'NOT ' if negate else ''}IN ({joined})"


def spawnable_forms(alias=None):
    """
    The SQL fragment restricting a species query to forms that can exist in the wild.

    Interpolated rather than parameterised because the values are this module's own
    constants and never touch user input, and because the alternative - threading five
    extra placeholders through queries that already build their own IN lists - is how
    parameter orders get shuffled.
    """
    prefix = f"{alias}." if alias else ""
    joined = ", ".join(f"'{form}'" for form in SPAWNABLE_FORM_TYPES)
    return f"{prefix}form_type IN ({joined})"


# ==========================================
# 🔷 THE PSEUDO-LEGENDARIES
# ==========================================
# The ten 600-BST three-stage finals, plus Hisuian Goodra, which is one of them wearing a
# different coat. They are the strongest things in the game that are not legendary, and
# until now the world treated them as ordinary wildlife: a Garchomp was drawn from the
# same 95% pool as a Rattata, so in a ground-typed biome it appeared roughly as often.
#
# Only the FINAL stages are listed. "Pseudo-legendary" names those Pokemon specifically,
# and gating the babies would have made Gible unfindable - the interesting part of the
# family is that you can raise one, which needs it to be catchable.
#
# The megas and Kommo-o's totem form are deliberately absent: they carry their own
# pokedex ids, cannot be encountered in the wild at all, and are already excluded by
# `spawnable_forms`. Listing them here would only invite somebody to drop that filter.
PSEUDO_LEGENDARY_IDS = (
    149,    # dragonite
    248,    # tyranitar
    373,    # salamence
    376,    # metagross
    445,    # garchomp
    635,    # hydreigon
    706,    # goodra
    784,    # kommo-o
    887,    # dragapult
    998,    # baxcalibur
    10242,  # goodra-hisui
)


def pseudo_legendaries(alias=None, negate=False):
    """The SQL fragment selecting - or excluding - the pseudo-legendaries."""
    prefix = f"{alias}." if alias else ""
    joined = ", ".join(str(dex) for dex in PSEUDO_LEGENDARY_IDS)
    return f"{prefix}pokedex_id {'NOT ' if negate else ''}IN ({joined})"


# ==========================================
# 🎲 THE RARITY ROLL
# ==========================================
# Three copies of the same if/elif ladder decided what tier a spawn belonged to, and they
# had already drifted - the expedition's legendary branch forgot `is_mythical = 0`, so a
# mythical could be drawn twice over. One table, one roll, one filter builder.
#
# Each number is that tier's OWN share of spawns, not a cumulative cutoff. The ladder it
# replaces was written cumulatively, which is why nobody could say at a glance what the
# legendary rate actually was - it was the difference between two numbers on two lines.
# Anything not claimed by a tier is ordinary wildlife.
#
# The two rare tiers are deliberately severe: a mythical is one spawn in a hundred
# thousand and a legendary one in a thousand, so seeing either is a server event rather
# than a Tuesday. They were 1% and 4%, which over a busy week put several Mewtwo in the
# habitat channel.
#
# The pseudo tier looks enormous beside them and per SPECIES it is not so far off:
# seventy-seven legendaries share their tier and eleven pseudo-legendaries share theirs.
# It is the one number here meant to be tuned by watching what appears - a pseudo is
# supposed to be a good day, not a ceremony.
RARITY_LABELS = {
    'mythical':  "✨ MYTHICAL",
    'legendary': "⭐ LEGENDARY",
    'pseudo':    "🔷 PSEUDO-LEGENDARY",
    'wild':      "Wild",
}

HABITAT_RARITY = (('mythical', 0.00001), ('legendary', 0.001), ('pseudo', 0.02))
EXPEDITION_RARITY = (('mythical', 0.00001), ('legendary', 0.001), ('pseudo', 0.03))


def rarity_filter(tier, alias='s'):
    """
    The WHERE fragment that selects exactly one rarity tier.

    Every tier excludes the others, including the ordinary one. That last part is the
    half that makes the tier mean anything: a pseudo-legendary that is still reachable
    through the 93% wild draw has not been made rare, it has been given a second door.
    """
    prefix = f"{alias}." if alias else ""
    if tier == 'mythical':
        return f"AND {prefix}is_mythical = 1"
    if tier == 'legendary':
        return f"AND {prefix}is_legendary = 1 AND {prefix}is_mythical = 0"
    if tier == 'pseudo':
        return f"AND {pseudo_legendaries(alias)}"
    return (f"AND {prefix}is_legendary = 0 AND {prefix}is_mythical = 0 "
            f"AND {pseudo_legendaries(alias, negate=True)}")


def roll_rarity(tiers=HABITAT_RARITY, roll=None):
    """
    Which tier this spawn belongs to. `roll` is injectable so a test can pin it.

    The shares are accumulated HERE rather than written out cumulatively in the table,
    so changing one tier's rate cannot silently move another's.
    """
    if roll is None:
        roll = random.random()
    ceiling = 0.0
    for tier, share in tiers:
        ceiling += share
        if roll < ceiling:
            return tier
    return 'wild'


def is_pseudo_legendary(pokedex_id):
    """Whether a dex id is one of them - for the capture broadcast and the box browser."""
    try:
        return int(pokedex_id) in PSEUDO_LEGENDARY_IDS
    except (TypeError, ValueError):
        return False


# A field directive names ONE species and asks for 1-3 captures of it. That is a fair
# ask for a Pidgey and an impossible one for a Mewtwo, which appears at roughly 1% of
# spawns and then only sometimes. Rare specimens are worth hunting; they are not worth
# a quest that quietly cannot be finished. Set to False to allow them back.
SURVEY_EXCLUDES_RARE_SPECIES = True

# ==========================================
# 🎓 ONBOARDING: THE STARTER KIT
# ==========================================
# A starter used to roll its genetics like any wild specimen, 0-31 on all six. That is
# the one place a random roll cannot be allowed: the starter is the specimen people name
# and keep, and rolling it randomly means some trainers lose a coin flip before they
# have typed a second command. At level 5 the difference is barely mechanical - it is
# the FEELING of having started behind, which no amount of compensating tokens fixes.
#
# So: a floor, not a fixed value. Three perfect stats guaranteed, the rest rolled in a
# narrow band. Every starter is good, no two are identical, and nobody starts behind.
STARTER_PERFECT_IVS = 3      # stats guaranteed to come out at 31
STARTER_IV_FLOOR = 20        # the worst any remaining stat can roll
STARTER_IV_CEILING = 31

# Never. A shiny starter turns every reset into a slot machine, and no cooldown fully
# fixes a slot machine - see utils/accounts.py, which is the other half of this rule.
STARTER_CAN_BE_SHINY = False

# Enough for a few Great Balls or one cheap piece of battle equipment, not enough to
# skip the early game. A Poke Ball is free and unlimited, so the first catch is never
# blocked; Great Balls are the first real upgrade and the first thing worth spending on.
STARTER_TOKENS = 500
STARTER_ITEMS = {'greatball': 5}

BIOLOGICAL_TRAITS = {
    'weather_setters': {
        'drizzle': ('rain', "🌧️ **{owner} {name}**'s Drizzle made it rain!\n"),
        'drought': ('sun', "☀️ **{owner} {name}**'s Drought turned the sunlight harsh!\n"),
        'sand-stream': ('sand', "🌪️ **{owner} {name}**'s Sand Stream whipped up a sandstorm!\n"),
        'snow-warning': ('hail', "❄️ **{owner} {name}**'s Snow Warning whipped up a hailstorm!\n"),
        # Block 11. Orichalcum Pulse is Drought with an Attack boost attached; the boost
        # half is an ordinary row in stat_multipliers, gated on the very sun it makes.
        'orichalcum-pulse': ('sun', "🔆 **{owner} {name}**'s Orichalcum Pulse turned the sunlight harsh!\n"),
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
        'levitate': {'type': 'ground', 'heal': 0.0},  # Pure immunity
        # Block 17. Eelevate is Levitate with a knockout boost welded on; the floating
        # half is this row plus membership of LEVITATION_ABILITIES, which is what the
        # hazard check and is_grounded read. Both are needed - this table answers "does
        # the move land", that set answers "are its feet on the ground" - so the suite
        # asserts every member of the set has a row here.
        'eelevate': {'type': 'ground', 'heal': 0.0}
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

        # --- Block 12
        'sharpness':     {'condition': 'slicing', 'multiplier': 1.5},
    },

    # The defensive half of the same idea: a multiplier on damage COMING IN, keyed on the
    # target's ability. Punk Rock and Water Bubble each cut the very thing they amplify,
    # so both sit in this table and the one above.
    #
    # An entry may be a single rule or a LIST of them, in which case every rule that
    # matches applies. Fluffy is the reason: it halves contact damage and doubles Fire
    # damage, and a Fire punch meets both - which is exactly how it nets out in the games.
    'incoming_multipliers': {
        'punk-rock':    {'condition': 'sound', 'multiplier': 0.5},
        'water-bubble': {'condition': 'move_type', 'types': ['fire'], 'multiplier': 0.5},

        # --- Block 2 ---
        'thick-fat':      {'condition': 'move_type', 'types': ['fire', 'ice'], 'multiplier': 0.5},
        'heatproof':      {'condition': 'move_type', 'types': ['fire'], 'multiplier': 0.5},
        'purifying-salt': {'condition': 'move_type', 'types': ['ghost'], 'multiplier': 0.5},
        'fur-coat':       {'condition': 'move_class', 'classes': ['physical'], 'multiplier': 0.5},
        'ice-scales':     {'condition': 'move_class', 'classes': ['special'], 'multiplier': 0.5},

        # --- Block 9: damage reduction and survival ---
        # Filter, Solid Rock and Prism Armor are the same ability three times over: they
        # take a quarter off anything the chart calls super effective. Read off the
        # multiplier rather than off the element, so a 4x hit is blunted too.
        'filter':         {'condition': 'super_effective', 'multiplier': 0.75},
        'solid-rock':     {'condition': 'super_effective', 'multiplier': 0.75},
        'prism-armor':    {'condition': 'super_effective', 'multiplier': 0.75},

        # Multiscale and Shadow Shield are likewise twins - half damage while untouched.
        'multiscale':     {'condition': 'at_full_hp', 'multiplier': 0.5},
        'shadow-shield':  {'condition': 'at_full_hp', 'multiplier': 0.5},

        'fluffy': [{'condition': 'contact', 'multiplier': 0.5},
                   {'condition': 'move_type', 'types': ['fire'], 'multiplier': 2.0}],
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

        # --- Block 18. Cherrim's sunshine. The games also give it a second FORM in the
        # sun, and the species table this project reads has no cherrim-sunshine row, so
        # only the stats are here. Recorded rather than faked: adding a species would
        # mean editing the database, and the stat half is the whole of what the ability
        # text says the ability does.
        'flower-gift':     {'stats': ['attack', 'sp_def'], 'multiplier': 1.5,
                            'weather': ['sun', 'extremely-harsh-sunlight']},

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

        # --- Block 11: the boost half of the two pulse engines. Each makes the very
        # condition it then feeds on, but the two halves stay separate: the weather and
        # terrain are laid at the switch-in, and these rows are read fresh on every
        # calculation - so the boost lapses of its own accord when the field does.
        'orichalcum-pulse': {'stats': ['attack'], 'multiplier': 4.0 / 3.0,
                             'weather': ['sun', 'extremely-harsh-sunlight']},
        'hadron-engine':    {'stats': ['sp_atk'], 'multiplier': 4.0 / 3.0,
                             'terrain': ['electric']},
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

# Each row is {'statuses': ...} plus optional conditions that AND together:
#   weather   - only while one of these is on the field
#   self_type - only while the owner is this element (Flower Veil's Grass clause)
STATUS_IMMUNE_ABILITIES = {
    'insomnia':       {'statuses': {'sleep'}},
    'vital-spirit':   {'statuses': {'sleep'}},
    'water-bubble':   {'statuses': {'burn'}},
    'purifying-salt': {'statuses': ALL_STATUSES},

    # --- Block 7 ---
    'magma-armor':    {'statuses': {'freeze'}},
    'water-veil':     {'statuses': {'burn'}},
    'sweet-veil':     {'statuses': {'sleep'}},
    'pastel-veil':    {'statuses': {'poison'}},
    'leaf-guard':     {'statuses': ALL_STATUSES,
                       'weather': ['sun', 'extremely-harsh-sunlight']},
    'flower-veil':    {'statuses': ALL_STATUSES, 'self_type': 'grass'},

    # --- Block 12. These two should have arrived with Block 7 - the comment above this
    # table has named them since it was written - and did not. They were counted as
    # implemented because gym leaders carry them, which is the whole reason the phantom
    # scan exists.
    'immunity':       {'statuses': {'poison'}},
    'limber':         {'statuses': {'paralysis'}},

    # --- Block 18. Komala is already asleep, so there is no room for anything else.
    'comatose':       {'statuses': ALL_STATUSES},
}

# Volatiles an ability simply refuses. Flinch is the only one this block needs, and it is
# a volatile rather than a status, which is why it cannot ride the table above.
VOLATILE_IMMUNE_ABILITIES = {
    'inner-focus': {'flinch'},
}

# Move families an ability is deaf, armoured or sealed against. Sound already has its own
# set in formulas.py, since Punk Rock and the Substitute bypass read it too.
BULLET_MOVES = {
    'acid-spray', 'aura-sphere', 'barrage', 'beak-blast', 'bullet-seed', 'egg-bomb',
    'electro-ball', 'energy-ball', 'focus-blast', 'gyro-ball', 'ice-ball', 'magnet-bomb',
    'mist-ball', 'mud-bomb', 'octazooka', 'pollen-puff', 'pyro-ball', 'rock-blast',
    'rock-wrecker', 'searing-shot', 'seed-bomb', 'shadow-ball', 'sludge-bomb',
    'weather-ball', 'zap-cannon',
}

POWDER_MOVES = {
    'cotton-spore', 'magic-powder', 'poison-powder', 'powder', 'rage-powder',
    'sleep-powder', 'spore', 'stun-spore',
}

# Damp smothers these outright - the user does not even hurt itself.
EXPLOSIVE_MOVES = {'explosion', 'self-destruct', 'mind-blown', 'misty-explosion'}

# Which family each ability shuts out. Overcoat also shrugs off the weather chip, which
# it does through WEATHER_CHIP_IMMUNE_ABILITIES rather than here.
MOVE_FAMILY_IMMUNE_ABILITIES = {
    'soundproof':  'sound',
    'bulletproof': 'bullet',
    'overcoat':    'powder',
}

# Good as Gold refuses any status MOVE aimed at it - not a status condition, a whole
# category of move.
STATUS_MOVE_IMMUNE_ABILITIES = {'good-as-gold'}

# Magic Bounce is Magic Coat as an ability, so it reuses that predicate entirely.
MAGIC_BOUNCE_ABILITIES = {'magic-bounce'}

# Damp, and anything else that refuses to let the field be blown up.
EXPLOSION_BLOCKING_ABILITIES = {'damp'}

# Early Bird burns through sleep at this rate.
EARLY_BIRD_SLEEP_RATE = 2

# Telepathy dodges an ALLY's damaging moves. With one Pokemon per side there is no ally
# to dodge, so it has no effect in singles - recorded rather than faked, exactly like the
# redirection pair in Block 6.
ALLY_DODGE_ABILITIES = {'telepathy'}

# ==========================================
# 🛡️ BLOCK 8: STAT-STAGE PROTECTION AND RETALIATION
# ==========================================
# Everything here reads the same event: ANOTHER specimen lowering a stage. A specimen's
# own drops are its own business - Close Combat's Defense and Overheat's Sp. Atk are the
# price of the move, and nothing on this page refuses them.
ALL_STATS = '*'

# The payload speaks PokeAPI's stat names, the stage block speaks the database's. This
# mapping is the only bridge between them, so anything not named here is not a stage and
# is ignored rather than written somewhere odd.
STAT_STAGE_KEYS = {'attack': 'attack', 'defense': 'defense', 'special-attack': 'sp_atk',
                   'special-defense': 'sp_def', 'speed': 'speed',
                   'accuracy': 'accuracy', 'evasion': 'evasion'}

# A stand-in for "the other side did this" when there is no specimen to point at -
# Sticky Web's Speed drop belongs to whoever laid the web, who may not even be on the
# field any more. Marked unreflectable at the call site, so Mirror Armor refuses the drop
# rather than trying to hand it to a ghost.
HAZARD_SOURCE = {'name': 'the hazard'}

# Which stages an ability refuses to let the other side lower. '*' guards every stage;
# anything else names the ones it guards and lets the rest through, so a Hyper Cutter
# still loses Speed to Icy Wind.
STAT_DROP_IMMUNE_ABILITIES = {
    'clear-body':      ALL_STATS,
    'white-smoke':     ALL_STATS,
    'full-metal-body': ALL_STATS,
    'mirror-armor':    ALL_STATS,   # refuses AND returns - see the reflecting set below
    'hyper-cutter':    {'attack'},
    'big-pecks':       {'defense'},
    'keen-eye':        {'accuracy'},
    # PokeAPI still carries Illuminate's old "doubles the wild encounter rate" text.
    # Gen 9 rebuilt it as a battle ability: accuracy cannot be lowered, and the target's
    # evasion is ignored (the second half lives in EVASION_IGNORING_ABILITIES).
    'illuminate':      {'accuracy'},
    'minds-eye':       {'accuracy'},
    # Flower Veil shields stages the same way Block 7 had it shield status, and on the
    # same condition - see the type gate below.
    'flower-veil':     ALL_STATS,
}

# Abilities from the table above that only shield while their owner is the right element.
# Flower Veil on a non-Grass specimen guards nothing, exactly as its status half already
# behaves in STATUS_IMMUNE_ABILITIES.
STAT_DROP_IMMUNE_TYPE_GATE = {'flower-veil': 'grass'}

# Mirror Armor does not simply refuse the drop, it hands it straight back. The returned
# drop is screened again at the far end, so a Mirror Armor facing a Clear Body fizzles -
# but it is never reflected twice, which is what stops the two of them bouncing one drop
# between them for ever.
STAT_DROP_REFLECTING_ABILITIES = {'mirror-armor'}

# Losing a stage makes these angry. The stat each one raises, and by how much. They only
# fire when the drop actually LANDS: a stat already pinned at -6 cannot fall, so there is
# nothing to be angry about.
STAT_DROP_RETALIATION_ABILITIES = {
    'defiant':     ('attack', 2),
    'competitive': ('special-attack', 2),
}

# Since Gen 8 these four refuse Intimidate specifically - not stat drops in general, just
# the one on arrival. Scrappy is not intimidated by a scary face, Own Tempo and Inner
# Focus do not rattle, and Oblivious does not notice.
INTIMIDATE_IMMUNE_ABILITIES = {'inner-focus', 'own-tempo', 'oblivious', 'scrappy'}

# ==========================================
# 🪨 BLOCK 9: DAMAGE REDUCTION AND SURVIVAL
# ==========================================
# Most of this block is table rows in `incoming_multipliers` above. What is left are the
# two things that will not fit there: one reads BOTH sides of the field, and one rewrites
# the type chart rather than multiplying its result.

# The auras reach across the whole field. Whoever is carrying one, the element it names
# is strengthened for everybody - the holder's own attacks and the attacks aimed at it
# alike. That is why they cannot live in either of the one-sided tables.
AURA_ABILITIES = {'dark-aura': 'dark', 'fairy-aura': 'fairy'}
AURA_MULTIPLIER = 4.0 / 3.0

# Aura Break does not switch an aura off, it turns it upside down: the same element is
# weakened by the same fraction instead. With no aura on the field it does nothing at all.
AURA_BREAK_ABILITIES = {'aura-break'}
AURA_BREAK_MULTIPLIER = 3.0 / 4.0

# Tera Shell answers every damaging move at full HP as though the target resisted it -
# it OVERWRITES the chart rather than multiplying it, which is why it is not a row in
# incoming_multipliers. Faithful to the games, that means a move which was already worse
# than not-very-effective is nudged UP to 0.5x; the only thing it cannot touch is a
# genuine immunity.
TERA_SHELL_ABILITIES = {'tera-shell'}
TERA_SHELL_MULTIPLIER = 0.5

# ==========================================
# 🚪 BLOCK 10: SWITCH-IN TRIGGERS
# ==========================================
# Almost all of this fires from one function - trigger_single_entry_ability, which every
# entry path already calls. The exception is the Ruin quartet, which PokeAPI describes as
# though it happened on arrival but which is really a standing multiplier; see below.

# Boosts the arrival gives itself. Once per battle since Gen 9 - a Zacian that switches
# out and back in does not get a second sword.
ENTRY_STAT_BOOST_ABILITIES = {
    'intrepid-sword':   ('attack', 1),
    'dauntless-shield': ('defense', 1),
}

# What the arrival does TO the specimen opposite, and how much of it. Unlike the boosts
# above these are ordinary drops, so Clear Body refuses them and Mirror Armor sends them
# back - the Block 8 resolver is what makes that automatic.
ENTRY_STAT_DROP_ABILITIES = {
    'supersweet-syrup': ('evasion', -1),
}

# Abilities on this list fire once and then never again for the rest of the battle. The
# marker is written onto the specimen itself rather than into volatile_statuses, because
# volatiles are wiped on the way out and "once per battle" has to survive that.
ONCE_PER_BATTLE_ENTRY = set(ENTRY_STAT_BOOST_ABILITIES) | {'supersweet-syrup'}
ONCE_PER_BATTLE_MARKER = '_entry_abilities_spent'

# Download reads the target's two walls and arms itself against the softer one.
DOWNLOAD_ABILITIES = {'download'}

# What the arrival reveals about the specimen opposite. Information rather than effect -
# these change what the trainer knows, not what the battle does.
FRISK_ABILITIES = {'frisk'}
FOREWARN_ABILITIES = {'forewarn'}
ANTICIPATION_ABILITIES = {'anticipation'}

# Unnerve reaches across the field and stops the OTHER side eating its berries. Read at
# the moment a berry would be consumed rather than at entry, so it lapses the instant its
# owner leaves - which is what "while the Pokemon is in battle" means.
# The Calyrex pair are Unnerve welded to a Neigh, so each is two rows rather than a new
# mechanic - one here and one in KNOCKOUT_BOOST_ABILITIES. That is the whole of them,
# which is why they waited for Block 17 rather than arriving with Unnerve in Block 10.
BERRY_BLOCKING_ABILITIES = {'unnerve', 'as-one-glastrier', 'as-one-spectrier'}

# Screen Cleaner sweeps both sides, not just the opponent's.
SCREEN_CLEANING_ABILITIES = {'screen-cleaner'}
SIDE_SCREEN_KEYS = ('reflect', 'light-screen', 'aurora-veil')

# Teraform Zero flattens the field on arrival: no weather, no terrain.
FIELD_NEUTRALISING_ABILITIES = {'teraform-zero'}

# Terapagos rearranges itself on the way in, exactly as Zacian does - and the form it
# becomes carries Tera Shell, which Block 9 implemented.
# `becomes_ability` is named here rather than re-read from the species tables because
# the two Crowned forms in Block 1 keep the ability they arrived with, and reading the table would
# quietly change them too. Terapagos is the first form shift in the project where the new
# body carries a different trait - the whole point of it, since Tera Shell is what
# Terastal Form is FOR.
ENTRY_FORM_SHIFTS = {
    'tera-shift': {'species': 'terapagos', 'form': 'terapagos-terastal',
                   'becomes_ability': 'tera-shell',
                   'flavour': 'rearranged itself'},
}

# The Ruin quartet. PokeAPI's text - "Lowers Attack of all Pokemon except itself" - reads
# like a switch-in trigger, and implementing it as one would have been wrong twice over:
# it is a standing 0.75x on the stat itself rather than a stage change, so it is neither
# refused by Clear Body nor cleared by Haze, and it lifts the moment its owner leaves.
# The entry hook only announces it; the arithmetic lives in stat_multiplier_for.
RUIN_ABILITIES = {
    'tablets-of-ruin': 'attack',
    'sword-of-ruin':   'defense',
    'vessel-of-ruin':  'sp_atk',
    'beads-of-ruin':   'sp_def',
}
RUIN_MULTIPLIER = 0.75

# Three entry abilities that need an ALLY to do anything, and KyuDex is singles. Recorded
# as decided rather than forgotten, exactly like the redirection pair in Block 6 and
# Telepathy in Block 7.
ALLY_ONLY_ENTRY_ABILITIES = {
    'curious-medicine',  # resets adjacent ALLIES' stages, not its own
    'costar',            # copies an ally's stages
    'hospitality',       # heals an ally
}

# ==========================================
# ⚡ BLOCK 11: TERRAIN SETTERS AND THE PARADOX ENGINES
# ==========================================
# The four surges are the terrain twins of the weather_setters table above. Kept as their
# own mapping rather than folded in there because terrain and weather are separate slots
# on the field - a specimen can stand in rain on Electric Terrain.
TERRAIN_SETTER_ABILITIES = {
    'electric-surge': 'electric',
    'psychic-surge':  'psychic',
    'misty-surge':    'misty',
    'grassy-surge':   'grassy',
    # Hadron Engine lays the terrain it then feeds on; the Sp. Atk half is a row in
    # stat_multipliers, gated on that same terrain.
    'hadron-engine':  'electric',
}

# Protosynthesis and Quark Drive are the first abilities here whose EFFECT is chosen at
# runtime: they boost whichever of the five stats is highest at the moment they engage,
# rather than one named in a table. Everything else about them is ordinary.
#
#   weather / terrain - the field condition that runs the engine
PARADOX_ABILITIES = {
    'protosynthesis': {'weather': ['sun', 'extremely-harsh-sunlight']},
    'quark-drive':    {'terrain': ['electric']},
}

# 1.3x on any stat except Speed, which gets 1.5x instead.
PARADOX_BOOST = 1.3
PARADOX_SPEED_BOOST = 1.5

# Which stat the engine picks. Ties are broken by this order, highest priority first,
# which is the order the games use.
PARADOX_STAT_ORDER = ('attack', 'defense', 'sp_atk', 'sp_def', 'speed')

# Booster Energy runs the engine when the field will not. Once drunk the boost holds for
# the rest of the battle whatever the weather does, so the marker goes on the specimen
# rather than into volatile_statuses - the same reasoning as the once-per-battle entry
# abilities in Block 10.
BOOSTER_ENERGY = 'booster-energy'
BOOSTER_SPENT_MARKER = '_booster_energy_spent'

# ==========================================
# 👻 BLOCK 12: THE CHEAP PHANTOMS
# ==========================================
# Five abilities that a scan reported as implemented and were not. Each is one row in a
# table that already existed, which is what makes them worth doing together and first:
# every one of them is on a gym leader's team right now, doing nothing.
#
# Immunity and Limber go into STATUS_IMMUNE_ABILITIES above, beside the Block 7 rows they
# should have arrived with. The three below need a home of their own.

# What a critical hit multiplies by. 1.5x for everybody except Sniper, which is the whole
# of that ability - it does not crit more often, it crits harder.
CRIT_DAMAGE_MULTIPLIER = 1.5
CRIT_MULTIPLIER_ABILITIES = {'sniper': 2.25}

# Prankster lifts a STATUS move by one bracket. The rider is as old as the ability is in
# its current form: since Gen 6 a move that took the boost simply fails against a Dark
# type, which is why the boost cannot be a silent +1 and nothing else.
PRANKSTER_ABILITIES = {'prankster'}
PRANKSTER_PRIORITY = 1
PRANKSTER_BLOCKED_BY = 'dark'

# Sharpness rides the existing damage_multipliers table on a new `slicing` condition.
# Listed rather than pattern-matched on the name: 'cut' and 'slash' would catch Rock
# Slide and Sacred Sword would be missed, so a guess in either direction is wrong.
SLICING_MOVES = {
    'aerial-ace', 'air-cutter', 'air-slash', 'aqua-cutter', 'behemoth-blade',
    'bitter-blade', 'ceaseless-edge', 'cross-poison', 'cut', 'fury-cutter',
    'kowtow-cleave', 'leaf-blade', 'mighty-cleave', 'night-slash', 'psyblade',
    'psycho-cut', 'razor-leaf', 'razor-shell', 'sacred-sword', 'secret-sword',
    'slash', 'solar-blade', 'stone-axe', 'tachyon-cutter', 'x-scissor',
}

# ==========================================
# 🚪 BLOCK 13: SWITCH-OUT, TRAPPING AND PIVOTING
# ==========================================
# These decide whether a switch happens at all, or what it costs. Two of them fire on the
# way OUT, two hold the other side in place, two refuse to be moved, and two leave of
# their own accord.

# Paid on the way out, before the replacement arrives. A fainted specimen collects
# neither: it is not switching out, it is gone.
SWITCH_OUT_HEAL_FRACTION = {'regenerator': 1.0 / 3.0}
SWITCH_OUT_CURE_ABILITIES = {'natural-cure'}

# Abilities that hold the specimen OPPOSITE in place, and what they can hold.
#   None      - everything
#   'grounded' - only what is standing on the ground; Flying, Levitate and an Air Balloon
#                all walk out over the top of an Arena Trap
#   a type     - only specimens of that element
TRAPPING_ABILITIES = {
    'shadow-tag':  None,
    'arena-trap':  'grounded',
    'magnet-pull': 'steel',
}

# Whirlwind, Roar, Dragon Tail and the rest cannot move these. Guard Dog is in both this
# set and the Intimidate table below - refusing to be shoved is half of what it does.
FORCED_SWITCH_IMMUNE_ABILITIES = {'suction-cups', 'guard-dog'}

# Intimidate makes Guard Dog angry rather than nervous: it gains a stage instead of losing
# one. Kept apart from INTIMIDATE_IMMUNE_ABILITIES because refusing a drop and answering
# it are different outcomes, and a set cannot say which.
INTIMIDATE_REVERSING_ABILITIES = {'guard-dog': ('attack', 1)}

# Wimp Out and Emergency Exit leave the moment they are badly hurt.
BAIL_OUT_ABILITIES = {'wimp-out', 'emergency-exit'}
BAIL_OUT_THRESHOLD = 0.5
# Cleared on the way out, so coming back in re-arms it. Without this a specimen sitting
# below half would try to leave again every single turn.
BAIL_OUT_MARKER = '_bailed_out'

# Run Away guarantees an escape from a WILD battle. KyuDex has no such thing - battles are
# against trainers and the Forfeit button always works - so there is nothing for it to
# make more certain. Recorded as decided rather than faked, like Telepathy in Block 7.
NO_FLEE_MECHANIC_ABILITIES = {'run-away'}

# ==========================================
# 💥 BLOCK 14: REACTIONS TO THE HIT ITSELF
# ==========================================
# Seventeen abilities that answer the move that just landed, all from the one retaliation
# hook Static and Rough Skin already use.
#
#   trigger  - what has to have happened:
#              'contact'  the move touched (Long Reach and a special move both deny it)
#              'damaged'  any move that dealt damage
#              'physical' a damaging physical move
#              'crit'     the hit was a critical one
#   types    - restricts the trigger to these elements
#   wind     - restricts the trigger to wind moves
#   self     - stage changes on the specimen that was hit: [(stat, stages)]
#   foe      - stage changes on whoever threw the move
#   weather / terrain - laid on the field
#   hazard   - dropped on the ATTACKER's side of the field
#   volatile - a flag set on the specimen that was hit
#
# Everything under `self` and `foe` goes through Block 8's resolver, so a Gooey Speed drop
# meets Clear Body and rouses Defiant exactly as any other drop does.
ON_HIT_REACTIONS = {
    # --- lower the attacker's Speed
    'gooey':            {'trigger': 'contact',  'foe': [('speed', -1)]},
    'tangling-hair':    {'trigger': 'contact',  'foe': [('speed', -1)]},
    # Cotton Down lowers EVERY other specimen's Speed. With one opponent that is the
    # attacker, and it answers any damaging move rather than only a touch.
    'cotton-down':      {'trigger': 'damaged',  'foe': [('speed', -1)]},

    # --- move the specimen's own stages
    'stamina':          {'trigger': 'damaged',  'self': [('defense', 1)]},
    'weak-armor':       {'trigger': 'physical', 'self': [('defense', -1), ('speed', 2)]},
    'justified':        {'trigger': 'damaged',  'types': ['dark'], 'self': [('attack', 1)]},
    'water-compaction': {'trigger': 'damaged',  'types': ['water'], 'self': [('defense', 2)]},
    'steam-engine':     {'trigger': 'damaged',  'types': ['fire', 'water'],
                         'self': [('speed', 6)]},
    'thermal-exchange': {'trigger': 'damaged',  'types': ['fire'], 'self': [('attack', 1)]},
    'rattled':          {'trigger': 'damaged',  'types': ['dark', 'ghost', 'bug'],
                         'self': [('speed', 1)]},
    # Anger Point goes straight to the ceiling; the resolver clamps it, so twelve is a
    # deliberate "as far as it will go" rather than a figure anybody has to keep in step.
    'anger-point':      {'trigger': 'crit',     'self': [('attack', 12)]},
    # --- change the field
    'sand-spit':        {'trigger': 'damaged',  'weather': 'sand'},
    'seed-sower':       {'trigger': 'damaged',  'terrain': 'grassy'},
    'toxic-debris':     {'trigger': 'physical', 'hazard': 'toxic-spikes'},

    # --- charge the next Electric move
    'wind-power':       {'trigger': 'damaged',  'wind': True, 'volatile': 'charged'},
    'electromorphosis': {'trigger': 'damaged',  'volatile': 'charged'},
}


# The charge Wind Power and Electromorphosis bank, and what it is worth. Spent by the next
# Electric move its owner throws.
CHARGE_VOLATILE = 'charged'
CHARGE_MULTIPLIER = 2.0

# Wind moves, for Wind Rider and Wind Power. Listed rather than guessed: Blizzard and Heat
# Wave are wind moves and do not say so, while Air Cutter and Aeroblast are not.
WIND_MOVES = {
    'bleakwind-storm', 'blizzard', 'fairy-wind', 'gust', 'heat-wave', 'hurricane',
    'icy-wind', 'petal-blizzard', 'sandsear-storm', 'sandstorm', 'springtide-storm',
    'tailwind', 'twister', 'whirlwind', 'wildbolt-storm',
}

# Wind Rider does not merely answer a wind move, it refuses one outright - and is
# rewarded for doing so. That is an immunity rather than a reaction to damage,
# which is why it is not a row in the table above: the trigger there is being HURT.
WIND_IMMUNE_ABILITIES = {'wind-rider'}
WIND_RIDER_BOOST = ('attack', 1)

# The payload target marker for "the attacker, but the DEFENDER did this to it". The
# existing 'attacker' means self-inflicted - Close Combat's own Defense drop - and Block 8
# screens on exactly that distinction, so Gooey needs to say something different or its
# drop would slip past Clear Body.
# Four combinations of (who moves) x (whose doing it was), because Block 8 screens on
# exactly that distinction. The first two are the engine's originals; the second two
# are what this block needed - Gooey drops the ATTACKER's Speed but the DEFENDER did
# it, and Stamina raises the DEFENDER's Defense by its own doing.
TARGET_ATTACKER = 'attacker'                       # attacker, self-inflicted
TARGET_DEFENDER = 'defender'                       # defender, by the attacker
TARGET_ATTACKER_FROM_FOE = 'attacker_from_foe'     # attacker, by the defender
TARGET_DEFENDER_SELF = 'defender_self'             # defender, its own doing

# A field change smuggled through the stat-change channel, the way Leech Seed and
# Perish Song already are - calculate_damage has the weather as a STRING and cannot
# lay a new one, but the engines that call it can.
TARGET_FIELD = 'field'

# ==========================================
# 🩸 BLOCK 15: REACTIONS TO SOMETHING OTHER THAN THE HIT
# ==========================================
# The other half of the old on-being-hit block. None of these can be answered by the move
# that just landed, so each one hangs off a different hook: an HP threshold, a flinch, a
# faint, or the item and ability layers.

# --- the HP threshold -------------------------------------------------------------
# Fired where Block 13's Wimp Out is fired, for the same reason: that is the one place
# both engines already look at what the turn did to a specimen's HP.
HP_THRESHOLD_REACTIONS = {
    'berserk':     [('special-attack', 1)],
    'anger-shell': [('defense', -1), ('special-defense', -1),
                    ('attack', 1), ('special-attack', 1), ('speed', 1)],
}
HP_THRESHOLD = 0.5
# Cleared on the way out, exactly like the bail-out marker: these answer HP CROSSING the
# line, not sitting below it, so without a marker they would fire every single turn.
HP_THRESHOLD_MARKER = '_crossed_half'

# --- the flinch -------------------------------------------------------------------
FLINCH_REACTIONS = {'steadfast': ('speed', 1)}

# --- contact, rewriting the attacker's ability ------------------------------------
# Mummy and Lingering Aroma paint their own name onto whoever touched them. Wandering
# Spirit trades instead. Both must respect the protection sets - a Mummy cannot paint over
# a Stance Change, and the engine's existing UNREPLACEABLE / UNSWAPPABLE tables already
# say so for the MOVES that do the same thing.
ABILITY_PAINT_ON_CONTACT = {'mummy', 'lingering-aroma'}
ABILITY_SWAP_ON_CONTACT = {'wandering-spirit'}

# --- contact and attack, moving an item -------------------------------------------
# Pickpocket takes from whoever touched it; Magician takes from whatever it hits. Both
# only ever take from a specimen that HAS something, and only when they are empty-handed.
ITEM_THIEF_ON_CONTACT = {'pickpocket'}
ITEM_THIEF_ON_ATTACK = {'magician'}

# --- being hurt, answering with a condition ---------------------------------------
# PokeAPI's text for spicy-spray is "when the Pokemon takes damage from a move, it burns
# the attacker" - any damaging move rather than a touch, which is why it is not in the
# contact set above.
RETALIATORY_BURN_ABILITIES = {'spicy-spray'}

# Synchronize hands the condition straight back. Only these three travel; sleep and freeze
# stay where they landed, which is the rule in the games.
SYNCHRONIZE_ABILITIES = {'synchronize'}
SYNCHRONIZE_STATUSES = {'burn', 'paralysis', 'poison'}

CURSED_BODY_ABILITIES = {'cursed-body'}
CURSED_BODY_CHANCE = 30
CURSED_BODY_TURNS = 4

PERISH_BODY_ABILITIES = {'perish-body'}
PERISH_BODY_COUNT = 3

# --- the drain ---------------------------------------------------------------------
# Liquid Ooze turns a leech into a poisoning: the attacker takes what it meant to gain.
LIQUID_OOZE_ABILITIES = {'liquid-ooze'}

# --- the faint ---------------------------------------------------------------------
# Answered where Grudge and Destiny Bond already resolve. Aftermath needs the killing blow
# to have been a touch; Innards Out does not care how it died.
AFTERMATH_ABILITIES = {'aftermath'}
AFTERMATH_FRACTION = 0.25
INNARDS_OUT_ABILITIES = {'innards-out'}

# ==========================================
# 🦋 BLOCK 16: EVENT-DRIVEN FORM FLIPS
# ==========================================
# Ten phantoms that share one shape: watch for an event, then swap the specimen to another
# form. Every one of them was counted as implemented because it appears in
# FORM_LOCKED_ABILITIES - a set that stops an ability being REMOVED, which says nothing
# about whether it ever did anything.
#
# They are split by WHAT they watch, not by what they turn into, because that is what
# decides which hook each one can hang off.

# --- watching its own HP, at the end of the turn -----------------------------------
# Every one of these is "past this fraction, wear the other body". `reverts` says whether
# coming back above the line puts it back: Power Construct is a one-way door, the rest
# breathe in and out with the damage.
#
#   below / above - the side of the fraction the SECOND form is worn on
#   pairs         - first form -> second form
#   min_level     - Wishiwashi is a solitary fish until it is old enough to shoal
_MINIOR_COLOURS = ['red', 'orange', 'yellow', 'green', 'blue', 'indigo', 'violet']

HP_FORM_FLIPS = {
    'zen-mode': {
        'below': 0.5, 'reverts': True,
        'pairs': {'darmanitan-standard': 'darmanitan-zen',
                  'darmanitan-galar-standard': 'darmanitan-galar-zen'},
    },
    # The one that reads the other way round: Wishiwashi shoals while it is HEALTHY.
    'schooling': {
        'above': 0.25, 'reverts': True, 'min_level': 20,
        'pairs': {'wishiwashi-solo': 'wishiwashi-school'},
    },
    'shields-down': {
        'below': 0.5, 'reverts': True,
        'pairs': {f'minior-{c}-meteor': f'minior-{c}' for c in _MINIOR_COLOURS},
    },
    # Zygarde does not go back. Once it is Complete it stays Complete.
    'power-construct': {
        'below': 0.5, 'reverts': False,
        'pairs': {'zygarde-10-power-construct': 'zygarde-complete',
                  'zygarde-50-power-construct': 'zygarde-complete'},
    },
}

# --- watching what hit it ----------------------------------------------------------
# Disguise and Ice Face are the same trick: the first qualifying hit is refused outright
# and the disguise comes off instead. Disguise pays a token of its own maximum HP for the
# privilege; Ice Face pays nothing but only ever stops a PHYSICAL move.
#
#   physical_only - Ice Face stands there and takes a special move
#   toll          - fraction of its own maximum the specimen pays to break
BROKEN_BY_A_HIT = {
    'disguise': {'pairs': {'mimikyu-disguised': 'mimikyu-busted',
                           'mimikyu-totem-disguised': 'mimikyu-totem-busted'},
                 'physical_only': False, 'toll': 1.0 / 8.0},
    'ice-face': {'pairs': {'eiscue-ice': 'eiscue-noice'},
                 'physical_only': True, 'toll': 0.0},
}

# --- watching what it threw --------------------------------------------------------
# Stance Change draws its blade for a damaging move and raises the shield for King's
# Shield. The only form flip here that happens BEFORE the move lands rather than after.
STANCE_CHANGE_ABILITIES = {'stance-change'}
STANCE_BLADE = {'aegislash-shield': 'aegislash-blade'}
STANCE_SHIELD = {'aegislash-blade': 'aegislash-shield'}
STANCE_SHIELD_MOVES = {'kings-shield'}

# --- watching the clock ------------------------------------------------------------
# Morpeko is hungry every other turn, for ever, whatever else happens.
HUNGER_SWITCH_ABILITIES = {'hunger-switch'}
HUNGER_PAIRS = {'morpeko-full-belly': 'morpeko-hangry',
                'morpeko-hangry': 'morpeko-full-belly'}

# --- watching itself leave ----------------------------------------------------------
# Palafin transforms on the way OUT and comes back a hero. One way, once a battle.
ZERO_TO_HERO_ABILITIES = {'zero-to-hero'}
ZERO_TO_HERO_PAIRS = {'palafin-zero': 'palafin-hero'}
ZERO_TO_HERO_MARKER = '_became_hero'

# --- Gulp Missile -------------------------------------------------------------------
# Two form flips in one: Cramorant surfaces holding something after Surf or Dive, and
# spits it at whatever hits it next. Which mouthful it caught depends on how hurt it was
# when it dived, and each spits back differently.
# Where a pending form change waits. Deciding a form is synchronous and cheap;
# CHANGING one is async and needs the species tables, and calculate_damage is
# neither async nor holding a database. So the predicates write a request here and
# the engines cash it in - the same trick Block 14 used to smuggle a Sand Spit
# sandstorm out of the formula.
FORM_FLIP_REQUEST = '_form_flip_request'

GULP_MISSILE_ABILITIES = {'gulp-missile'}
GULP_TRIGGER_MOVES = {'surf', 'dive'}
GULP_BASE_FORM = 'cramorant'
GULP_HEALTHY_FORM = 'cramorant-gulping'
GULP_HURT_FORM = 'cramorant-gorging'
GULP_HURT_THRESHOLD = 0.5
GULP_RECOIL_FRACTION = 0.25
# What the mouthful does on the way out: a Defense drop from the little one, paralysis
# from the big one.
GULP_PAYLOADS = {
    'cramorant-gulping': {'stat': ('defense', -1)},
    'cramorant-gorging': {'status': 'paralysis'},
}

# ==========================================
# 💀 BLOCK 17: WHAT A KNOCKOUT IS WORTH
# ==========================================
# Five abilities pay their owner for finishing something off and differ only in the
# currency. Named in the payload vocabulary - 'special-attack', not 'sp_atk' - because
# these go through resolve_stat_stages like every other stage change, which means a
# Moxie boost is a real boost: Haze clears it and the cap at +6 pins it.
#
# The sentinel says "whichever stat is already highest" rather than naming one. Beast
# Boost and Eelevate choose at runtime, which is the same choice Protosynthesis makes,
# so the picker is shared rather than copied - one tie-break order (Atk > Def > SpA >
# SpD > Spe), one place to be wrong.
KNOCKOUT_BEST_STAT = '_best'

KNOCKOUT_BOOST_ABILITIES = {
    'moxie':          'attack',
    'chilling-neigh': 'attack',
    'grim-neigh':     'special-attack',
    'beast-boost':    KNOCKOUT_BEST_STAT,
    'eelevate':       KNOCKOUT_BEST_STAT,

    # --- Block 18. The other half of each is a row in BERRY_BLOCKING_ABILITIES: an
    # As One IS Unnerve and a Neigh, and pointing both rows at the same names is a
    # truer statement of that than a branch reading "or as-one" in two places.
    'as-one-glastrier': 'attack',
    'as-one-spectrier': 'special-attack',
}
KNOCKOUT_BOOST_STAGES = 1

# paradox_best_stat answers in DATABASE keys, because that is what it reads; the stage
# resolver speaks the payload vocabulary. One inverse table rather than a second literal
# spelling of the same five stats - the sp_atk/special-attack confusion has already cost
# one silently-vacuous test.
STAGE_NAME_FOR_STAT = {'attack': 'attack', 'defense': 'defense',
                       'sp_atk': 'special-attack', 'sp_def': 'special-defense',
                       'speed': 'speed'}

# Soul-Heart is not a reward for the kill. It answers ANY specimen falling, whoever
# felled it - so it is asked at the blow that lands AND at the end-of-turn residual
# check, where poison and a sandstorm do their killing. The corpse is marked once
# mourned, which is what stops those two call sites paying twice for one faint.
MOURNING_ABILITIES = {'soul-heart': 'special-attack'}
MOURNING_STAGES = 1
MOURNED_MARKER = '_mourned'

# Opportunist takes a copy of every stage its opponent GAINS - not of the ones it loses,
# and never of a copy, which is the single thing that stops two of them trading one
# Swords Dance back and forth for ever.
OPPORTUNIST_ABILITIES = {'opportunist'}

# Supreme Overlord grows with the graveyard: a tenth per fallen party member, capped at
# five of them. Coded as a stat multiplier on Attack and Sp. Atk, which is what the
# ability text this project works from says; the games phrase it as a power boost on the
# move instead. The two differ only where something else reads the stat - Foul Play
# borrows the figure here, and would not there.
SUPREME_OVERLORD_ABILITIES = {'supreme-overlord'}
SUPREME_OVERLORD_PER_FALLEN = 0.1
SUPREME_OVERLORD_MAX_FALLEN = 5
SUPREME_OVERLORD_STATS = ('attack', 'sp_atk')

# Levitate had its name written into three separate places, and Eelevate is the second
# ability to float. One set, so the next one is a single row rather than another hunt -
# and so the hazard check and the Ground immunity cannot disagree about who is airborne.
LEVITATION_ABILITIES = {'levitate', 'eelevate'}

# ==========================================
# 🌦️ BLOCK 18: ABILITIES THAT READ THE FIELD
# ==========================================
# Forecast is a form flip like Block 16's, but keyed on the WEATHER rather than on
# anything that happened to the specimen - so it reuses that block's request/resolve
# machinery and only the question is new. The type comes along for free: the resolver
# rebuilds the species half from the tables, and castform-sunny is Fire in them.
WEATHER_FORM_ABILITIES = {'forecast'}
WEATHER_FORMS = {
    'forecast': {
        'base': 'castform',
        'by_weather': {
            'sun': 'castform-sunny', 'extremely-harsh-sunlight': 'castform-sunny',
            'rain': 'castform-rainy', 'heavy-rain': 'castform-rainy',
            'hail': 'castform-snowy', 'snow': 'castform-snowy',
        },
    },
}

# Truant loafs on alternate turns. The marker rides on the specimen and is cleared on the
# way out, so a Slaking switched out and back in acts on the turn it arrives rather than
# resuming a rhythm it left behind - which is the rule in the games, and is also the only
# reading that does not quietly reward switching.
TRUANT_ABILITIES = {'truant'}
TRUANT_MARKER = '_loafing'

# Comatose is a permanent sleep that does not stop its owner moving. Everything that asks
# "is this thing asleep" for a REASON OTHER than whether it can act has to read the
# ability as well as the status slot, which is what is_effectively_asleep is for. The
# defensive half is an ordinary row in STATUS_IMMUNE_ABILITIES: something already asleep
# cannot be given anything else.
COMATOSE_ABILITIES = {'comatose'}

# ==========================================
# 🎒 BLOCK 19: HELD-ITEM INTERACTION
# ==========================================
# Eleven abilities that bend the ITEM layer rather than the damage layer. Two of them
# have nothing here to bend and are recorded as decided at the bottom of this section.

# Klutz switches the held item OFF without taking it away - which is exactly what Embargo
# and Magic Room already do, so it is a third clause in get_active_item rather than a new
# check at each of the forty places an item is read. The STORED name survives, which is
# what lets a Klutz specimen still be Tricked, still Fling, and still have the item wake
# up the moment it changes hands.
CLUMSY_ABILITIES = {'klutz'}

# Sticky Hold refuses any attempt by ANOTHER specimen to move the item. Where the line
# falls, stated rather than left for a reader to infer from the call sites:
#
#   refused - Thief, Covet, Knock Off, Trick, Switcheroo, Corrosive Gas, and the two
#             ability-thieves Pickpocket and Magician. Every one of them takes or
#             destroys the item on somebody else's initiative.
#   allowed - Bug Bite, Pluck and Incinerate, which eat or burn a BERRY rather than
#             taking an item; Bestow, which HANDS one over; and everything the holder
#             does itself - it can still eat its own berry and still Fling.
#
# Knock Off keeps its damage bonus against a Sticky Hold holder. The bonus is paid for
# having an item to knock off, and it still has one.
STICKY_HOLD_ABILITIES = {'sticky-hold'}

# Gluttony raises the floor under the HP-gated berries: a pinch berry that would wait for
# a quarter goes off at a half instead. Written as a floor rather than a replacement so
# the berries that ALREADY trigger at a half - Oran, Sitrus - are untouched by it.
GLUTTONY_ABILITIES = {'gluttony'}
GLUTTONY_THRESHOLD = 0.5

# Ripen doubles what a berry does, whichever kind it is: twice the healing, twice the
# stat stages, and twice the bite out of the damage a resist berry soaks.
RIPEN_ABILITIES = {'ripen'}
RIPEN_MULTIPLIER = 2

# Cheek Pouch pays a third of max HP for eating ANY berry, on top of whatever the berry
# itself did - including one force-fed by Teatime, a Fling or a Bug Bite, because the
# ability answers the eating rather than the holding.
CHEEK_POUCH_ABILITIES = {'cheek-pouch'}
CHEEK_POUCH_FRACTION = 3

# Harvest regrows the berry its owner ate, into hands that must be empty. Certain in the
# sun, a coin flip otherwise.
HARVEST_ABILITIES = {'harvest'}
HARVEST_CHANCE = 0.5
HARVEST_SUN_CHANCE = 1.0
HARVEST_SUN = ('sun', 'extremely-harsh-sunlight')

# Cud Chew brings the berry back UP rather than back into the hands: it is eaten a second
# time at the end of the following turn, and never lands in the item slot at all. The
# marker carries the berry and a countdown, and is armed only when the berry came off
# this specimen's own slot - which is what stops the second helping arming a third.
CUD_CHEW_ABILITIES = {'cud-chew'}
CUD_CHEW_DELAY = 2

# Pickup has two halves that share nothing but a name. In battle it lifts whatever the
# specimen opposite used up this turn, into hands that must be empty. After the battle it
# is a chance at something off the floor, which is where Honey Gather also lives - the
# whole of that ability, which is why it could not be done before an after-battle hook.
PICKUP_ABILITIES = {'pickup'}
HONEY_GATHER_ABILITIES = {'honey-gather'}
AFTER_BATTLE_FIND_CHANCE = 0.10
HONEY_GATHER_ITEM = 'honey'
# Kept deliberately dull. Pickup is a trickle, not a treasure chest, and everything here
# is already obtainable by ordinary means.
PICKUP_POOL = ('oran-berry', 'sitrus-berry', 'cheri-berry', 'pecha-berry',
               'rawst-berry', 'chesto-berry', 'aspear-berry', 'leppa-berry',
               'potion', 'super-potion', 'honey')

# What a berry leaves behind on the specimen that ate it.
LAST_BERRY_MARKER = '_last_berry'          # Harvest: which one to regrow
CUD_CHEW_MARKER = '_cud_chew'              # [berry, turns until the second helping]
ITEM_SPENT_MARKER = '_item_spent_this_turn'  # Pickup: what the foe used up

# The two that have nothing to hook onto, recorded as decided rather than faked - exactly
# like the ally-only entry abilities above, Telepathy in Block 7 and Run Away in Block 13.
# Symbiosis hands its item to an ALLY, and KyuDex is singles. Ball Fetch answers a Poke
# Ball thrown and missed IN battle, and KyuDex throws balls from the encounter command
# instead - there is no failed throw on a battlefield for it to retrieve.
NO_ALLY_ITEM_ABILITIES = {'symbiosis'}
NO_BALL_THROW_ABILITIES = {'ball-fetch'}

# ==========================================
# 🎭 BLOCK 20: WEARING ANOTHER IDENTITY
# ==========================================
# Seven abilities about carrying somebody else's ability, species or type. All seven were
# counted as implemented on their membership of the protection sets - UNCOPYABLE,
# UNSWAPPABLE, FIELD_READING - which exist precisely because these are the abilities that
# must not be copied, and say nothing whatever about whether they work.

# Trace copies the ability standing opposite, on arrival. Read through the ACTIVE
# accessor, so a Gastro Acid'd target has nothing to hand over, and written through
# set_active_ability, so withdrawing puts Trace back.
TRACE_ABILITIES = {'trace'}

# Imposter is Transform, paid on arrival instead of by spending a turn. The move already
# exists and is already careful about copying a copy, so this is one call rather than a
# second implementation.
IMPOSTER_ABILITIES = {'imposter'}

# Illusion wears the face of the last conscious party member until a damaging move
# connects. Only `name` and `pokedex_id` are borrowed - types, stats and ability stay the
# specimen's own, which is what makes it a disguise rather than a Transform. The real
# identity rides on the specimen under this marker so weight can see through it.
ILLUSION_ABILITIES = {'illusion'}
ILLUSION_MARKER = '_illusion'

# Multitype and RKS System are the same ability twice: be whatever the held item says.
# The value is the item FAMILY, which is the same vocabulary Judgment and Multi-Attack
# already read off PLATE_TYPES and the '-memory' suffix - so this block adds a question,
# not a table.
PLATE_TYPE_ABILITIES = {'multitype': 'plate', 'rks-system': 'memory'}
PLATE_BASE_TYPES = '_own_types'

# ...and both weld the item on, exactly as Sticky Hold does. Without this a Knock Off
# would strip Arceus's Plate, which the games have never allowed.
ITEM_WELDED_ABILITIES = set(PLATE_TYPE_ABILITIES)

# Receiver and Power of Alchemy inherit an ALLY's ability when that ally faints, and
# KyuDex is singles - the specimen that replaces a corpse is not its ally, it is its
# successor. Recorded as decided, like the ally-only three in Block 10 and Symbiosis in
# Block 19.
ALLY_FAINT_ABILITIES = {'receiver', 'power-of-alchemy'}

# Where the two engines keep their rosters. Illusion needs the party of whoever just
# walked in, and the shared entry hook is handed the battle state rather than a side.
BATTLE_STATE_TEAM_KEYS = ('player_team', 'npc_team', 'p1_team', 'p2_team')

# ==========================================
# 🌫️ BLOCK 21: ABILITY SUPPRESSION
# ==========================================
# Deliberately last of the mechanical blocks, because it changes what every OTHER ability
# reads. All three of these are answered inside get_active_ability rather than at the
# two hundred places that call it - the accessor split has existed since Gastro Acid, and
# this block is what it was built for.
#
# Both of the new suppressors ride on the specimen as a volatile, for the same reason
# Gastro Acid does: get_active_ability takes ONE argument and cannot be handed the field.
# Neither is a property of the ability - both are properties of the SLOT - so both are
# swept away by restore_base_ability on the way out.

# The mould-breaker family. Its marker is scoped to a single strike: it goes onto the
# DEFENDER for the length of one damage calculation and comes off in a finally, so
# nothing outside that calculation can ever see it.
MOLD_BREAKING_ABILITIES = {'mold-breaker', 'turboblaze', 'teravolt'}
MOULD_BROKEN_MARKER = 'mould_broken'

# Neutralizing Gas switches off everything ELSE on the field for as long as its owner
# stands there. Recomputed from scratch rather than toggled, so a gasser that faints,
# switches or is itself replaced cannot leave the marker behind.
NEUTRALIZING_GAS_ABILITIES = {'neutralizing-gas'}
GAS_SUPPRESSED_MARKER = 'gas_suppressed'

# Unaware reads the OTHER side's sheet as though nothing had been done to it. Which
# stages that covers depends on which end of the move its owner is standing:
#   attacking - the target's walls stop counting
#   defending - the attacker's offence stops counting
# Everything else the two of them have done to themselves still counts, which is what
# makes Unaware a counter to a sweeper rather than a Haze.
UNAWARE_ABILITIES = {'unaware'}
UNAWARE_DEFENSIVE_STATS = ('defense', 'sp_def')
UNAWARE_OFFENSIVE_STATS = ('attack', 'sp_atk')

# ==========================================
# ☀️ BLOCK 22: SIGNATURE FORM CHANGES
# ==========================================
# Mega Sol carries its own sky. Its owner's moves read the weather as harsh sunlight
# whatever is actually overhead - so its Fire moves are strengthened and its Water moves
# dulled, its Solar Beam needs no charge, and its Thunder is as unreliable as it would be
# under a real sun. Only its OWN moves: the sky it stands under is unchanged for
# everybody else, which is what makes this a reading rather than a weather setter.
PERSONAL_SUN_ABILITIES = {'mega-sol'}
PERSONAL_SUN_WEATHER = 'sun'

# ...but not over a primordial sky. Desolate Land, Primordial Sea and Delta Stream are
# the three the engine already refuses to let an ordinary weather setter overwrite, and a
# personal reading does not get to do what a weather setter cannot.
UNOVERRIDABLE_SKIES = ('extremely-harsh-sunlight', 'heavy-rain', 'strong-winds')

# ==========================================
# 🌦️ WEATHER-GATED ACCURACY
# ==========================================
# Some moves are aimed by the sky. Two different things happen, and they are kept apart
# because only one of them is a number:
#
#   perfect - the move SKIPS its accuracy check altogether. Not "100%": the check is not
#             made, so evasion stages, an accuracy drop and Sand Veil are all bypassed
#             too. hit_chance returns early for exactly that reason.
#   dimmed  - the move keeps checking, at a worse figure.
#
# Found while implementing Block 22's Mega Sol, whose whole text is "as if the weather
# were harsh sunlight" - and Thunder, the clearest thing that should have answered it,
# turned out to have a flat 70 in every sky. Recorded as a MOVE-layer gap at the time
# rather than smuggled into an ability block; this is that gap closed.
WEATHER_ACCURACY_MOVES = {
    'thunder':   {'perfect': ('rain', 'heavy-rain'),
                  'dimmed': {'sun': 50, 'extremely-harsh-sunlight': 50}},
    'hurricane': {'perfect': ('rain', 'heavy-rain'),
                  'dimmed': {'sun': 50, 'extremely-harsh-sunlight': 50}},
    'blizzard':  {'perfect': ('hail', 'snow')},

    # The Forces of Nature signature storms, which never check accuracy in rain.
    'bleakwind-storm': {'perfect': ('rain', 'heavy-rain')},
    'wildbolt-storm':  {'perfect': ('rain', 'heavy-rain')},
    'sandsear-storm':  {'perfect': ('rain', 'heavy-rain')},

    # `springtide-storm` is deliberately absent. It is the fourth of that family and sits
    # in base_moves at the same 80 accuracy, but I could not confirm it shares the rain
    # rule, and guessing would put a wrong number in a table that reads as researched.
    # One row here if it turns out it does.
}

# ==========================================
# 👥 BLOCK 23: DOUBLES-ONLY - PARKED, NOT CODED
# ==========================================
# Seven abilities that need a SECOND body on your own side of the field. KyuDex is
# singles, exactly like the existing DOUBLES_ONLY_MOVES set, so there is never an ally
# for any of them to reach and nothing here to implement.
#
# Recorded as decided rather than left off the list, which is the same treatment
# Telepathy got in Block 7, Run Away in Block 13, the ally-only three in Block 10,
# Symbiosis and Ball Fetch in Block 19 and the ally-faint pair in Block 20. Naming them
# is the point: a reader who wonders whether Battery was forgotten finds the decision
# here, and the ability scanner classifies them as deliberate no-ops rather than as
# phantoms hiding in a protection set.
DOUBLES_ONLY_ABILITIES = {
    'plus',          # 1.5x Sp. Atk when an ally has Plus or Minus
    'minus',         # the same, from the other side of the pair
    'friend-guard',  # 0.75x damage taken by an ALLY
    'healer',        # 30% to cure an adjacent ally's status each turn
    'battery',       # 1.3x power on an ALLY's moves
    'power-spot',    # the same, for standing next to it
    'commander',     # climbs into an ally Dondozo's mouth
}

# ==========================================
# 🐸 BATTLE BOND - the half that was missing
# ==========================================
# Counted as implemented for eight blocks on one Water Shuriken line, while the form
# change it exists to drive was never written. Worse, that line keyed the boost on the
# ABILITY, so an ordinary Greninja that had knocked nothing out was already throwing
# Ash-Greninja's shuriken.
#
# In the games the ability transforms Greninja after it knocks something out, and it is
# the FORM that carries the stronger Water Shuriken. Both halves are keyed accordingly:
# the flip is asked at the knockout hook Block 17 built, and the shuriken asks what the
# specimen currently IS rather than what it can do.
BATTLE_BOND_ABILITIES = {'battle-bond'}
BATTLE_BOND_FORM = 'greninja-ash'
BATTLE_BOND_SHURIKEN = 'water-shuriken'
BATTLE_BOND_SHURIKEN_POWER = 20
BATTLE_BOND_SHURIKEN_HITS = 3

# How often a generated specimen comes up with its hidden ability rather than a
# standard one. The same figure the capture path in cogs/ecology.py uses - a rival
# should be built from the rules something you could have caught was built from.
HIDDEN_ABILITY_CHANCE = 0.20

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

# The target's evasion is ignored entirely. Illuminate joins Mind's Eye here from Gen 9.
EVASION_IGNORING_ABILITIES = {'minds-eye', 'illuminate'}

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

# ==========================================
# ⏱️ BLOCK 6: PRIORITY AND TURN ORDER
# ==========================================
# Abilities whose owner refuses to be hit by a priority move at all.
PRIORITY_BLOCKING_ABILITIES = {'queenly-majesty', 'dazzling', 'armor-tail'}

# Quick Draw's chance to jump to the front of its bracket.
QUICK_DRAW_CHANCE = 30

# Abilities that send their owner to the BACK of its bracket. Mycelium Might only does so
# for status moves, which is why it is a mapping rather than a set.
#   '*'      - every move
#   'status' - status moves only
LAST_IN_BRACKET_ABILITIES = {
    'stall': '*',
    'mycelium-might': 'status',
}

# Gale Wings only lifts Flying moves while its owner is untouched.
GALE_WINGS_REQUIRES_FULL_HP = True
TRIAGE_PRIORITY = 3

# Dance moves, for Dancer. Rain Dance is NOT one of these - it is a weather move that
# happens to be called a dance, and including it is the obvious mistake here.
DANCE_MOVES = {
    'aqua-step', 'clangorous-soul', 'dragon-dance', 'feather-dance', 'fiery-dance',
    'lunar-dance', 'petal-dance', 'quiver-dance', 'revelation-dance', 'swords-dance',
    'teeter-dance', 'victory-dance',
}

# Redirection is a doubles mechanic: with one Pokemon per side there is nothing to draw a
# move away, so there is nothing for these to ignore. Recorded as decided rather than
# forgotten, exactly like the Block 18 set.
REDIRECTION_IGNORING_ABILITIES = {'propeller-tail', 'stalwart'}

# Abilities that shrug off the end-of-turn weather chip, and WHICH weather each one
# shelters from - Sand Veil is no help in hail. Type immunity is handled separately, on
# the types themselves. Block 7 adds Overcoat and Magic Guard, which shelter from both.
WEATHER_CHIP_IMMUNE_ABILITIES = {
    'sand-force': {'sand', 'sandstorm'},
    'sand-veil':  {'sand', 'sandstorm'},
    'snow-cloak': {'hail', 'snow'},
    # Overcoat and Magic Guard shelter from every kind of weather, not just their own
    'overcoat':    {'sand', 'sandstorm', 'hail', 'snow'},
    'magic-guard': {'sand', 'sandstorm', 'hail', 'snow'},
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
    'tachyon-cutter':     {'min': 2, 'max': 2},
    'twineedle':     {'min': 2, 'max': 2},
    # `gear-grind`, `surging-strikes` and `water-shuriken` were each listed TWICE in this
    # literal. The first two were harmless - both copies agreed - but Water Shuriken was
    # 2-to-5 above and a flat 3 here, and a dict literal keeps the LAST one. Every Water
    # Shuriken in the game was therefore hitting exactly three times, for everybody, which
    # is Ash-Greninja's privilege and nobody else's. See BATTLE_BOND_SHURIKEN_HITS below,
    # which is where that three actually belongs.

    # The 10-hit swarm anomaly
    'population-bomb': {'min': 1, 'max': 10}
}