import json
import os
import random
import re as _re
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
# 🌑 THE THREE FAMILIES THAT ARE NOT ORDINARY MOVES
# ==========================================
# base_moves is PokeAPI's whole move table, which means it carries three families that
# no specimen may ever reach for by name: the Shadow moves out of Colosseum and XD, the
# Max Moves, and the signature Z-Moves. They are declared here, once, because more than
# one rule needs them - the Metronome pool, the mimicry family and Sketch all do.
#
# The Shadow list is WRITTEN OUT rather than matched on the 'shadow-' prefix. base_moves
# holds 24 moves beginning with that word and only 18 of them are Shadow moves; Shadow
# Ball, Bone, Claw, Force, Punch and Sneak are perfectly ordinary and a prefix test would
# have quietly banned Shadow Ball from Metronome and from Sketch.
SHADOW_MOVES = frozenset({
    'shadow-blast', 'shadow-blitz', 'shadow-bolt', 'shadow-break', 'shadow-chill',
    'shadow-down', 'shadow-end', 'shadow-fire', 'shadow-half', 'shadow-hold',
    'shadow-mist', 'shadow-panic', 'shadow-rave', 'shadow-rush', 'shadow-shed',
    'shadow-sky', 'shadow-storm', 'shadow-wave',
})

# The nineteen Max Moves base_moves carries. A Max Move is BUILT by the engines out of a
# base move and marked with MAX_MOVE_MARKER, so these names are never the payload's own
# name in play - they are here to keep them out of the pools that read base_moves.
MAX_MOVE_NAMES = frozenset({
    'max-airstream', 'max-darkness', 'max-flare', 'max-flutterby', 'max-geyser',
    'max-guard', 'max-hailstorm', 'max-knuckle', 'max-lightning', 'max-mindstorm',
    'max-ooze', 'max-overgrowth', 'max-phantasm', 'max-quake', 'max-rockfall',
    'max-starfall', 'max-steelspike', 'max-strike', 'max-wyrmwind',
})

# The signature Z-Moves, which unlike the eighteen elemental ones (Z_MOVE_NAMES, further
# down) do have rows in base_moves and so are reachable by name.
Z_MOVE_SIGNATURES = frozenset({
    '10-000-000-volt-thunderbolt', 'catastropika', 'clangorous-soulblaze',
    'extreme-evoboost', 'genesis-supernova', 'guardian-of-alola',
    'light-that-burns-the-sky', 'malicious-moonsault', 'menacing-moonraze-maelstrom',
    'oceanic-operetta', 'pulverizing-pancake', 'searing-sunraze-smash',
    'sinister-arrow-raid', 'soul-stealing-7-star-strike', 'splintered-stormshards',
    'stoked-sparksurfer',
})

# The Starmobiles' five signature moves, which Sketch is specifically barred from.
STARMOBILE_MOVES = frozenset({
    'blazing-torque', 'combat-torque', 'magical-torque', 'noxious-torque',
    'wicked-torque',
})

# ==========================================
# 🎲 THE METRONOME POOL
# ==========================================
# Every move Metronome may roll, indexed once at import rather than queried per use.
#
# The list below is Bulbapedia's "Unselectable moves" table read at the GENERATION IX
# column - the ruleset KyuDex otherwise models - plus the prose above that table, which
# bars every Max Move and every Z-Move outright. It replaced a hand-written set of 32
# that let Metronome roll `max-flare`, `catastropika` and all 18 Shadow moves.
#
# Two things worth knowing before editing it:
#
#   * The table is PER GENERATION and moves move between columns. Nine of these are
#     barred in Generation IX but callable again in Legends: Z-A - Breaking Swipe,
#     Chilling Water, Make It Rain, Overdrive, Rage Fist, Shed Tail, Snarl, Steel Beam
#     and Trailblaze. Reading the table as one flat list gets them wrong in one
#     direction and Dark Void, Double Team and Oblivion Wing wrong in the other.
#   * Role Play and Skill Swap were excluded here and are NOT on the table at all.
#     Metronome may call both, and formulas.py implements both, so they were dropped.
#
# Nihil Light belongs on this list and is deliberately absent: it is a Legends: Z-A move
# with no Generation IX ruling, and base_moves has no row for it yet either.
METRONOME_EXCLUDED = frozenset({
    'after-you', 'apple-acid', 'armor-cannon', 'assist', 'astral-barrage',
    'aura-wheel', 'baneful-bunker', 'beak-blast', 'behemoth-bash', 'behemoth-blade',
    'belch', 'bestow', 'blazing-torque', 'body-press', 'branch-poke',
    'breaking-swipe', 'celebrate', 'chatter', 'chilling-water', 'chilly-reception',
    'clangorous-soul', 'collision-course', 'combat-torque', 'comeuppance', 'copycat',
    'counter', 'covet', 'crafty-shield', 'decorate', 'destiny-bond',
    'detect', 'diamond-storm', 'doodle', 'double-iron-bash', 'double-shock',
    'dragon-ascent', 'dragon-energy', 'drum-beating', 'dynamax-cannon', 'electro-drift',
    'endure', 'eternabeam', 'false-surrender', 'feint', 'fiery-wrath',
    'fillet-away', 'fleur-cannon', 'focus-punch', 'follow-me', 'freeze-shock',
    'freezing-glare', 'glacial-lance', 'grav-apple', 'helping-hand', 'hold-hands',
    'hyper-drill', 'hyperspace-fury', 'hyperspace-hole', 'ice-burn', 'instruct',
    'jet-punch', 'jungle-healing', 'kings-shield', 'life-dew', 'light-of-ruin',
    'magical-torque', 'make-it-rain', 'mat-block', 'me-first', 'meteor-assault',
    'mimic', 'mind-blown', 'mirror-coat', 'mirror-move', 'moongeist-beam',
    'nature-power', 'natures-madness', 'noxious-torque', 'obstruct', 'order-up',
    'origin-pulse', 'overdrive', 'photon-geyser', 'plasma-fists', 'population-bomb',
    'pounce', 'power-shift', 'precipice-blades', 'protect', 'pyro-ball',
    'quash', 'quick-guard', 'rage-fist', 'rage-powder', 'raging-bull',
    'raging-fury', 'relic-song', 'revival-blessing', 'ruination', 'salt-cure',
    'secret-sword', 'shed-tail', 'shell-trap', 'silk-trap', 'sketch',
    'sleep-talk', 'snap-trap', 'snarl', 'snatch', 'snore',
    'snowscape', 'spectral-thief', 'spicy-extract', 'spiky-shield', 'spirit-break',
    'spotlight', 'steam-eruption', 'steel-beam', 'strange-steam', 'struggle',
    'sunsteel-strike', 'surging-strikes', 'switcheroo', 'techno-blast', 'tera-starstorm',
    'thief', 'thousand-arrows', 'thousand-waves', 'thunder-cage', 'thunderous-kick',
    'tidy-up', 'trailblaze', 'transform', 'trick', 'twin-beam',
    'v-create', 'wicked-blow', 'wicked-torque', 'wide-guard',
    # Metronome itself is barred by the prose rather than the table: a second finger-wag
    # would just roll again.
    'metronome',
}) | SHADOW_MOVES | MAX_MOVE_NAMES | Z_MOVE_SIGNATURES

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
        "item_pool": ["water-stone", "nugget", "rare-candy"]
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

# ==========================================
# 💊 THE TWO ABILITY ITEMS
# ==========================================
# A Capsule swaps a specimen between the two STANDARD abilities its species has. A Patch
# reaches the hidden one, which is a different thing entirely: a hidden ability is the
# scarce end of the roster, and the whole point of a future breeding update is that
# earning one is work. So the Patch is priced as the shortcut it is - expensive enough
# that breeding for a hidden ability stays the sensible route and this stays the
# impatient one - and it is deliberately ONE-WAY. A Capsule cannot walk a specimen back
# off a hidden ability, exactly as in the games, which is what stops the pair being used
# to flip freely between all three.
ABILITY_CAPSULE_PRICE = 2500
ABILITY_PATCH_PRICE = 12000

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
    # The other two refining materials. They have been droppable since the anomaly rolls
    # were written and consumable by `!refine` for just as long, but neither had a
    # catalog row - so `!inventory` showed a bare hyphenated slug with no name, no emoji
    # and no hint of what it was for, and `!shop` could not describe something a player
    # was already holding. Listed here for the same reason the Wishing Fragment is, and
    # unpurchaseable for the same reason too: the anomaly roll IS the way to get one.
    "raw-keystone":  {"name": "Raw Keystone", "price": 0, "desc": "Exchange with `!refine` to make a Mega Bracelet.", "emoji": "🌠", "category": "keyitems", "purchasable": False},
    "sparkling-stone":  {"name": "Sparkling Stone", "price": 0, "desc": "Exchange with `!refine` to make a Z-Ring.", "emoji": "☀️", "category": "keyitems", "purchasable": False},
    "nugget":  {"name": "Nugget", "price": 0, "desc": "Exchange for Eco-Tokens", "emoji": "💵", "category": "keyitems", "purchasable": False, "sell_price": 5000},
    "memory-spore":  {"name": "Memory Spore", "price": 0, "desc": "Allows a pokemon to learn a tutor move.", "emoji": "🧬", "category": "keyitems", "purchasable": False},
    
    # Form Items
    "reveal-glass":  {"name": "Reveal Glass", "price": 0, "desc": "Turns Tornadus, Thundurus, Landorus or Enamorus between their Incarnate and Therian Formes. Use with `!form`.", "emoji": "🧬", "category": "formitems", "purchasable": False},
    "dna-splicers":  {"name": "DNA Splicers", "price": 0, "desc": "Fuses Kyurem with Reshiram or Zekrom, and separates them again. Use with `!form`.", "emoji": "🧬", "category": "formitems", "purchasable": False},
    "rusted-sword":  {"name": "Rusted Sword", "price": 0, "desc": "Zacian takes its Crowned form while holding this.", "emoji": "⚔️", "category": "formitems", "purchasable": False},
    "rusted-shield":  {"name": "Rusted Shield", "price": 0, "desc": "Zamazenta takes its Crowned form while holding this.", "emoji": "🛡️", "category": "formitems", "purchasable": False},
    "red-orb":  {"name": "Red Orb", "price": 0, "desc": "Groudon undergoes Primal Reversion while holding this.", "emoji": "🔴", "category": "formitems", "purchasable": False},
    "blue-orb":  {"name": "Blue Orb", "price": 0, "desc": "Kyogre undergoes Primal Reversion while holding this.", "emoji": "🔵", "category": "formitems", "purchasable": False},
    "booster-energy":  {"name": "Booster Energy", "price": 0, "desc": "Runs a Paradox specimen's Protosynthesis or Quark Drive when the field will not. Single use.", "emoji": "🧪", "category": "formitems", "purchasable": False},

    # The three Gen 8 Orbs. HELD rather than used: each reshapes its holder on entry and
    # lifts two of its elements by 20%, which is the Griseous Orb's machinery exactly -
    # so they are rows in SPECIES_FORM_ITEMS and SPECIES_TYPE_BOOST_ITEMS and the battle
    # engine already reads both. Nothing in `!form` touches them.
    "adamant-crystal": {"name": "Adamant Crystal", "price": 0, "desc": "Dialga takes its Origin Forme while holding this, and its Dragon and Steel moves do 20% more damage.", "emoji": "💠", "category": "formitems", "purchasable": False},
    "lustrous-globe":  {"name": "Lustrous Globe", "price": 0, "desc": "Palkia takes its Origin Forme while holding this, and its Dragon and Water moves do 20% more damage.", "emoji": "🔮", "category": "formitems", "purchasable": False},
    "griseous-core":   {"name": "Griseous Core", "price": 0, "desc": "Giratina takes its Origin Forme while holding this, and its Dragon and Ghost moves do 20% more damage.", "emoji": "🟣", "category": "formitems", "purchasable": False},

    # The ten used from the bag with `!form`. Unpurchaseable for the same reason the
    # seven above are: a legendary's form item is not shop stock.
    "meteorite":       {"name": "Meteorite", "price": 0, "desc": "Shifts Deoxys between its Normal, Attack, Defense and Speed Formes. Use with `!form`.", "emoji": "☄️", "category": "formitems", "purchasable": False},
    "rotom-catalog":   {"name": "Rotom Catalog", "price": 0, "desc": "Lets Rotom possess a Heat, Wash, Frost, Fan or Mow appliance. Use with `!form`.", "emoji": "📖", "category": "formitems", "purchasable": False},
    "gracidea":        {"name": "Gracidea", "price": 0, "desc": "Turns Shaymin between its Land and Sky Formes. Use with `!form`.", "emoji": "💐", "category": "formitems", "purchasable": False},
    "prison-bottle":   {"name": "Prison Bottle", "price": 0, "desc": "Releases Hoopa's true power - and seals it away again. Use with `!form`.", "emoji": "🏺", "category": "formitems", "purchasable": False},
    "zygarde-cube":    {"name": "Zygarde Cube", "price": 0, "desc": "Reassembles Zygarde between 10% and 50%, switches Aura Break and Power Construct, and teaches its three signature moves. Use with `!form`.", "emoji": "🟩", "category": "formitems", "purchasable": False},
    "n-lunarizer":     {"name": "N-Lunarizer", "price": 0, "desc": "Fuses Necrozma with Lunala into Dawn Wings, and separates them again. Use with `!form`.", "emoji": "🌙", "category": "formitems", "purchasable": False},
    "n-solarizer":     {"name": "N-Solarizer", "price": 0, "desc": "Fuses Necrozma with Solgaleo into Dusk Mane, and separates them again. Use with `!form`.", "emoji": "☀️", "category": "formitems", "purchasable": False},
    "reins-of-unity":  {"name": "Reins of Unity", "price": 0, "desc": "Lets Calyrex ride Glastrier or Spectrier, and dismount again. Dismounting costs it the moves only its steed could learn. Use with `!form`.", "emoji": "🎠", "category": "formitems", "purchasable": False},

    # Evolution Items
    "water-stone":    {"name": "Water Stone", "price": 500, "desc": "A stone that makes certain pokemon evolve. It is clear, blue and glistens.", "emoji": "💎", "category": "evoitems"},
    "leaf-stone":    {"name": "Leaf Stone", "price": 500, "desc": "A stone that makes certain pokemon evolve. It is green and mossy.", "emoji": "💎", "category": "evoitems"},
    "fire-stone":    {"name": "Fire Stone", "price": 500, "desc": "A stone that makes certain pokemon evolve. It is clear, orange and glistens.", "emoji": "💎", "category": "evoitems"},
    # 10,000 made a single level cost more than most of the shop put together, so the
    # candy was a curiosity rather than a tool and nobody built a second team. At 1,200
    # it is a real option and still dear enough that levelling by battling is the
    # cheaper road - which is the balance it should have had.
    "rare-candy":    {"name": "Rare Candy", "price": 1200, "desc": "A sweet treat that increases a pokemon's level by 1.", "emoji": "🍬", "category": "evoitems"},

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
    "life-orb":      {"name": "Life Orb", "price": 600, "desc": "1.3x damage on every attack, but costs the holder 1/10 of its max HP each time one lands.", "emoji": "🔮", "category": "battleitems"},
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
    # The Patch is deliberately expensive - see ABILITY_PATCH_PRICE below for why.
    "ability-capsule": {"name": "Ability Capsule", "price": ABILITY_CAPSULE_PRICE, "desc": "Switches a specimen between its two standard abilities.", "emoji": "💊", "category": "general"},
    "ability-patch":   {"name": "Ability Patch", "price": ABILITY_PATCH_PRICE, "desc": "Unlocks a specimen's HIDDEN ability. Cannot be reversed by a Capsule.", "emoji": "🩹", "category": "general"},
    
    # MEDICINE & BATTLE
    "potion":    {"name": "Potion", "price": 100, "desc": "Restore 20 HP in battle", "emoji": "🧪", "category": "medicine"},
    "revive":    {"name": "Revive", "price": 250, "desc": "Revive a fainted specimen", "emoji": "💠", "category": "medicine"},
    
    # VITAMINS
    # All six, one per stat. Protein and Carbos were the only two on the shelf, which
    # made Attack and Speed the only two EVs a trainer could buy their way into - so
    # every other spread had to be earned through training missions while those two
    # could be bought. `!feed` has always understood all six.
    "hp-up":     {"name": "HP Up", "price": 500, "desc": "+10 HP EVs", "emoji": "❤️", "category": "vitamin"},
    "protein":   {"name": "Protein", "price": 500, "desc": "+10 Attack EVs", "emoji": "💪", "category": "vitamin"},
    "iron":      {"name": "Iron", "price": 500, "desc": "+10 Defense EVs", "emoji": "🛡️", "category": "vitamin"},
    "calcium":   {"name": "Calcium", "price": 500, "desc": "+10 Sp. Atk EVs", "emoji": "🔮", "category": "vitamin"},
    "zinc":      {"name": "Zinc", "price": 500, "desc": "+10 Sp. Def EVs", "emoji": "🌟", "category": "vitamin"},
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
    
    # 💎 Z-CRYSTALS and 🧬 MEGA STONES are built by build_phase8_stock() further down.
    # Two crystals and two stones used to be hand-written here. They were the only four
    # of a hundred and twenty-one, and neither the Z-Crystal nor the Mega Stone one was
    # bound to anything the engine checked - see MEGA_STONE_SPECIES for what that cost.
}

# Define the categories for the dropdowns
CATEGORY_OPTIONS = [
    discord.SelectOption(label="All Items", value="all", emoji="🎒"),
    discord.SelectOption(label="Capture Gear", value="capture", emoji="🔴"),
    discord.SelectOption(label="General Supplies", value="general", emoji="🫧"),
    discord.SelectOption(label="Medicine", value="medicine", emoji="🧪"),
    discord.SelectOption(label="Vitamins", value="vitamin", emoji="💊"),
    # Their own shelf rather than twenty-one more rows under Vitamins, which are six
    # items and would have been buried. Same reasoning as the Type Boosters below.
    discord.SelectOption(label="Nature Mints", value="mints", emoji="🌱"),
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
# ==========================================
# 💿 WHAT A TM COSTS
# ==========================================
# The shelf used to be a hand-written dictionary of seven moves. `species_movepool`
# holds 340 distinct `machine` moves, so 333 of them could be READ off a specimen's
# movepool, refused by `!learn` for want of the TM, and then not found in the shop -
# unlearnable at any price. A hand-written shelf can only ever be a subset of a table
# that grows, so the shelf is derived from the table instead.
#
# Pricing is a rule rather than a list, for the same reason. Three tiers:
#
#   basic     - the utility moves every team wants and no team should have to save for
#   standard  - coverage; a modest, unremarkable purchase
#   premium   - the moves that decide a matchup rather than fill a slot
#
# The principle behind the numbers: team-building ACCESS should never be the barrier,
# only team-building skill. A new trainer starts with 500 tokens (STARTER_TOKENS) and
# the basic six in hand, so nobody's first team is shaped by their wallet.
TM_TIER_PRICES = {'basic': 300, 'standard': 1200, 'premium': 4000}

# Handed over free with the starting kit as well as sold - see STARTER_TMS. Six moves
# chosen because they teach what a TM IS: one protects, one heals, one poisons, one
# switches, one flinches, one blocks status.
TM_BASIC = frozenset({
    'protect', 'rest', 'substitute', 'toxic', 'rock-slide', 'u-turn',
    'facade', 'return', 'frustration', 'rain-dance', 'sunny-day', 'sandstorm',
    'hail', 'snowscape', 'sleep-talk', 'attract', 'double-team', 'swift',
})

# The moves that change how a matchup plays rather than what it is played with -
# hazards, recovery, burn, and the setup sweepers turn on. Priced high enough to be a
# decision and low enough to be a couple of days of casual play.
TM_PREMIUM = frozenset({
    'stealth-rock', 'knock-off', 'will-o-wisp', 'calm-mind', 'roost',
    'spikes', 'toxic-spikes', 'defog', 'rapid-spin', 'taunt', 'encore',
    'swords-dance', 'nasty-plot', 'bulk-up', 'iron-defense', 'agility',
    'thunder-wave', 'trick-room', 'light-screen', 'reflect', 'leech-seed',
    'recover', 'synthesis', 'moonlight', 'morning-sun', 'wish',
})

# A nuke is premium whatever its name. 110 sits above the coverage moves (Earthquake,
# Ice Beam, Flamethrower all land at 90-100) and below nothing worth exempting.
TM_NUKE_POWER = 110


def tm_price(move, power=None, damage_class=None):
    """
    What one TM costs, from the move rather than from a table somebody has to maintain.

    Named tiers win over the power rule, so a status move nobody would price by its
    power - Stealth Rock has none at all - still lands where it belongs.
    """
    if move in TM_BASIC:
        return TM_TIER_PRICES['basic']
    if move in TM_PREMIUM:
        return TM_TIER_PRICES['premium']
    if power and power >= TM_NUKE_POWER:
        return TM_TIER_PRICES['premium']
    return TM_TIER_PRICES['standard']

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

# The unicode fallback set. Kept, and still the answer whenever a custom emoji cannot
# be used or cannot be resolved - see `type_icon` below.
TYPE_EMOJI = {
    'normal': '⬜', 'fire': '🔥', 'water': '💧', 'electric': '⚡', 'grass': '🌿',
    'ice': '🧊', 'fighting': '🥊', 'poison': '☠️', 'ground': '⛰️', 'flying': '🕊️',
    'psychic': '🔮', 'bug': '🐛', 'rock': '🪨', 'ghost': '👻', 'dragon': '🐉',
    'dark': '🌑', 'steel': '⚙️', 'fairy': '🧚',
    # The nineteenth. Shadow is a Colosseum/XD type: 18 moves in `base_moves` carry it
    # and NO species learns any of them, so it can never appear on a specimen - but
    # `!movedex shadow-rush` still renders one, and rendering it as a bare question
    # mark would look like a bug rather than like a move nothing can learn. There is no
    # custom badge because the uploaded set is the eighteen real types.
    'shadow': '🌒',
}

# ==========================================
# 🎨 THE SERVER'S OWN TYPE BADGES
# ==========================================
# Uploaded by hand to the bot's home guild. A BOT may use a custom emoji from any guild
# it is a member of, in every other guild it is in - which is why these render on a
# server that has never seen them, and why the whole set has to stay in one place.
#
# The failure mode is worth knowing, because it is quiet: if the bot ever leaves the
# guild these live in, or an id is wrong by a digit, Discord renders the raw text
# `<:fire:1539779394397274213>` instead of an icon. Nothing errors. So `type_icon`
# falls back to TYPE_EMOJI for anything not in this table rather than inventing a
# reference that cannot resolve.
TYPE_ICONS = {
    'normal':   '<:normal:1539778963663093780>',
    'fighting': '<:fighting:1539779058328539157>',
    'flying':   '<:flying:1539779100229767268>',
    'poison':   '<:poison:1539779146949861456>',
    'ground':   '<:ground:1539779192181231626>',
    'rock':     '<:rock:1539779237320458310>',
    'bug':      '<:bug:1539779274330865774>',
    'ghost':    '<:ghost:1539779315779113000>',
    'steel':    '<:steel:1539779354618372096>',
    'fire':     '<:fire:1539779394397274213>',
    'water':    '<:water:1539779435958636555>',
    'grass':    '<:grass:1539779478601998497>',
    'electric': '<:electric:1539779510231236690>',
    'psychic':  '<:psychic:1539779562186080406>',
    'ice':      '<:ice:1539779613486747718>',
    'dragon':   '<:dragon:1539779644629327922>',
    'dark':     '<:dark:1539779706235256952>',
    'fairy':    '<:fairy:1539779735779803316>',
}


def type_icon(element):
    """
    The badge for one element.

    Falls through to the unicode set and then to a question mark, because the callers
    are all display code: a type this table has never heard of - a typo, a NULL out of
    the database, a new element in some future generation - should render as SOMETHING
    rather than take an embed down with it.
    """
    key = str(element or '').strip().lower()
    return TYPE_ICONS.get(key) or TYPE_EMOJI.get(key) or '❔'


def type_badges(types, separator=" / "):
    """
    A specimen's typing, as badges: `<:fire:…> Fire / <:flying:…> Flying`.

    One function rather than a formatting decision repeated at each of the dozen places
    that show a typing - which is how `!view` and the market listing came to disagree
    about whether an unknown type says "Unknown" or nothing at all.
    """
    labels = [f"{type_icon(t)} {str(t).strip().title()}"
              for t in (types or []) if t and str(t).strip()]
    return separator.join(labels) if labels else "❔ Unknown"


# ==========================================
# 🏅 THE TRAIT BADGES
# ==========================================
# The two things a specimen can BE rather than have. Both were being drawn with a
# stand-in unicode glyph chosen separately at each site, so the box browser called a
# G-Max specimen 🌪️, the market called the same one 🌀, and an Alpha was the word
# "ALPHA" in the box and 🔥 on the catch card.
#
# Same rule as the type badges: NEVER put one inside a code span. A custom emoji in
# backticks renders as its raw `<:alpha:154…>` text, which is the one place these
# cannot go.
GMAX_ICON = '<:gigantamax:1540095450030411806>'
ALPHA_ICON = '<:alpha:1540095412286001192>'

# The Poke Ball line, for the encounter panel's buttons. Discord takes a custom emoji on
# a button through its own `emoji=` parameter rather than in the label, so these are
# stored as bare ids and parsed by the caller - a button label containing `<:x:1>` shows
# the literal text.
BALL_ICONS = {
    'pokeball':   '<:pokeball:1538255998014193744>',
    'greatball':  '<:greatball:1538256357457789068>',
    'ultraball':  '<:ultraball:1538256466698305596>',
    'masterball': '<:masterball:1538256522193276978>',
}

# Unicode stand-ins, used only where a custom emoji cannot go. A bot may use a custom
# emoji from any guild it is in, so these should almost never be reached - but a badge
# that silently renders as raw text is worse than a plain circle.
BALL_FALLBACK = {
    'pokeball': '⚪', 'greatball': '🔵', 'ultraball': '🟡', 'masterball': '🟣',
}


def ball_icon(key):
    """The badge for one ball, falling through to a coloured circle."""
    key = str(key or '').strip().lower()
    return BALL_ICONS.get(key) or BALL_FALLBACK.get(key) or '⚪'


def is_alpha_size(height_multiplier):
    """
    Whether a height multiplier makes this specimen an Alpha.

    One question asked in one place. The tagger, the catch card and the box browser each
    compared against the threshold themselves, which is how a specimen could be labelled
    ALPHA by one and not tagged as one by another.
    """
    try:
        return float(height_multiplier or 0) >= ALPHA_HEIGHT_THRESHOLD
    except (TypeError, ValueError):
        return False


def trait_badges(*, gmax=False, height_multiplier=None, shiny=False, spaced=True):
    """
    The badges a specimen carries, in a fixed order, or an empty string.

    Order is deliberate and shared: shiny, then Alpha, then G-Max. A caller that wants
    only some of them passes only those. Returns '' when there is nothing to say, so it
    can be concatenated into a title without leaving a stray gap.
    """
    marks = []
    if shiny:
        marks.append('🌟')
    if is_alpha_size(height_multiplier):
        marks.append(ALPHA_ICON)
    if gmax:
        marks.append(GMAX_ICON)
    if not marks:
        return ''
    joined = ' '.join(marks)
    return f" {joined}" if spaced else joined


def build_species_types():
    """
    Every species' typing, by name, read once at import.

    Keyed by NAME rather than by pokedex id because that is what the callers hold: the
    GTS stores `dep_species`/`req_species` as text, and its paginator renders
    synchronously inside `create_embed`, so it cannot await a lookup at all.

    Built the same way the TM shelf is - one read-only pass at import - because the
    alternative is a query per row on a page that shows several, which is how a listing
    page becomes slow without anybody noticing why.
    """
    table = {}
    try:
        import sqlite3 as _sqlite3
        with _sqlite3.connect(f"file:{DB_FILE}?mode=ro", uri=True) as _conn:
            for name, element in _conn.execute("""
                SELECT s.name, t.type_name
                FROM base_pokemon_species s
                JOIN base_pokemon_types t ON t.pokedex_id = s.pokedex_id
                ORDER BY s.pokedex_id, t.rowid
            """):
                table.setdefault(str(name).lower(), []).append(element)
    except Exception as e:
        # A listing with no type badge is a worse listing, not a broken one.
        print(f"⚠️ WARNING: could not read species typings ({e}).")
    return table


SPECIES_TYPES = build_species_types()


def species_types(name):
    """One species' typing, or an empty list for a name nothing recognises."""
    return SPECIES_TYPES.get(str(name or '').strip().lower(), [])


def species_badges(name, separator=" / "):
    """A species' typing as badges, from its name alone."""
    return type_badges(species_types(name), separator)

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
            "emoji": type_icon(element),
            "category": "typeboost",
        }

    for item, element in TYPE_ENHANCER_ITEMS.items():
        stock[item] = {
            "name": item.replace('-', ' ').title(),
            "price": TYPE_ENHANCER_PRICE,
            "desc": f"1.2x damage to the holder's {element.title()}-type moves.",
            "emoji": type_icon(element),
            "category": "typeboost",
        }

    for item, element in TYPE_GEMS.items():
        stock[item] = {
            "name": item.replace('-', ' ').title(),
            "price": TYPE_GEM_PRICE,
            "desc": f"{TYPE_GEM_MULTIPLIER}x to one {element.title()}-type move, then it is used up.",
            "emoji": type_icon(element),
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
# 🚪 THE PHASE 3 SHELF - PIVOT AND ESCAPE
# ==========================================
# Four items that move a specimen off the field rather than changing a number on it.
# Three of them eject somebody; the fourth is the one that refuses to BE held.
#
# All three ejectors resolve at the END of the turn rather than the instant they fire.
# That is a divergence from the games and it is deliberate: it is the same divergence
# `end_of_turn_survival` already documents for Wimp Out and Emergency Exit, and making
# the items leave mid-turn while the abilities leave at the end would have meant two
# switch-out clocks in an engine that has trouble keeping one.
EJECT_ITEMS = {
    # what the holder answers -> whether the holder or the ATTACKER is the one that goes
    'eject-button': 'self',
    'eject-pack':   'self',
    'red-card':     'attacker',
}

# Where a pending ejection is parked between firing and the end of the turn. Holds the
# item name, so the log can say which one did it and so Red Card can be told apart from
# the two that move their own holder.
PIVOT_REQUEST = '_pivot_requested_by'

# Red Card drags somebody out against their will, so they do NOT get to choose the
# replacement - that is the entire difference between being Red Carded and choosing to
# pivot. Everything else here is a voluntary switch and keeps its menu.
RANDOM_REPLACEMENT_ITEMS = {'red-card'}

# Shed Shell is the item half of the trapping table. It answers `is_trapped`, not the
# ejectors, and it is here rather than beside them because it is the only one of the
# four that is not a one-shot.
SHED_SHELL = 'shed-shell'

PHASE3_PRICE = 300

PHASE3_DESCRIPTIONS = {
    'eject-button': "Switches the holder out at end of turn after it is damaged by a "
                    "move. Single use.",
    'eject-pack':   "Switches the holder out at end of turn after any of its stats is "
                    "lowered. Single use.",
    'red-card':     "Drags the attacker out at end of turn after it damages the holder. "
                    "Their replacement is random. Single use.",
    'shed-shell':   "The holder can always switch out, whatever is holding it there.",
}

PHASE3_EMOJI = {
    'eject-button': '⏏️', 'eject-pack': '🎒', 'red-card': '🟥', 'shed-shell': '🐚',
}


def build_phase3_stock():
    """
    The Phase 3 shelf, checked against the tables the engine reads.

    Same assertion as Phase 2 and for the same reason: an item on this shelf that no
    table implements is an item the shop charges for and the engine ignores.
    """
    implemented = set(EJECT_ITEMS) | {SHED_SHELL}
    missing = implemented - set(PHASE3_DESCRIPTIONS)
    assert not missing, f"Phase 3 items with no shop entry: {sorted(missing)}"
    extra = set(PHASE3_DESCRIPTIONS) - implemented
    assert not extra, f"Phase 3 shop entries with no implementation: {sorted(extra)}"

    return {
        item: {
            "name": item.replace('-', ' ').title(),
            "price": PHASE3_PRICE,
            "desc": PHASE3_DESCRIPTIONS[item],
            "emoji": PHASE3_EMOJI.get(item, '🚪'),
            "category": "battleitems",
        }
        for item in sorted(implemented)
    }


EQUIPMENT_CATALOG.update(build_phase3_stock())


# ==========================================
# 🎯 THE PHASE 4 SHELF - ACCURACY, CRITS AND FLINCHING
# ==========================================
# Nine items that bend a ROLL rather than a number, and every roll they bend already
# goes through one shared function: hit_chance for the lenses and the evasion pair,
# priority_tier for the claw and the two that dawdle, and the same inflicted_status
# route Stench uses for the two that flinch.
#
# The two evasion items are written as the ACCURACY figure the games use rather than as
# the "+1/9 evasion" their PokeAPI text quotes. For Bright Powder the two are the same
# number - 1/(1 + 1/9) is exactly 0.9 - and for Lax Incense the games' flat 0.95 is half
# a percent away from the 1/1.05 the text implies. Matching the games is worth more than
# matching the blurb, and this comment is here so the difference is a decision.
ITEM_ACCURACY_MULTIPLIERS = {
    'wide-lens': 1.1,
}

# Zoom Lens is the same idea with a condition: it only sharpens the holder when the
# holder is moving SECOND, which the engines already track as `acted_this_turn` for
# Bolt Beak. Kept out of the table above because a flat lookup cannot express it.
ZOOM_LENS_MULTIPLIER = 1.2

# What each item does to the accuracy of moves aimed AT its holder. Lower is harder to
# hit. Stored this way round rather than as an evasion divisor because that is the form
# the games state, and the one place that reads it inverts it once.
ITEM_ACCURACY_AGAINST_HOLDER = {
    'bright-powder': 0.9,
    'lax-incense': 0.95,
}

# King's Rock and Razor Fang staple a flinch chance onto every damaging move the holder
# throws - the same sentence as Stench, so they take the same route through
# inflicted_status and inherit Inner Focus's refusal for free.
#
# Two deliberate non-interactions, both matching the modern games: Serene Grace does NOT
# double this, and Shield Dust does NOT block it. Neither is a move's secondary effect,
# which is what those two abilities answer.
ITEM_FLINCH_CHANCE = {
    'kings-rock': 10,
    'razor-fang': 10,
}

# Quick Claw jumps to the front of its bracket 3 times in 16. Written as the fraction
# rather than as 18.75 because the roll below compares against it directly, and a
# percentage would invite the randint(1, 100) form that cannot express three-sixteenths.
QUICK_CLAW_ODDS = 3 / 16

# ...and the two that go to the BACK of their bracket, always. The item half of
# LAST_IN_BRACKET_ABILITIES.
LAST_IN_BRACKET_ITEMS = {'lagging-tail', 'full-incense'}

PHASE4_PRICE = 350

PHASE4_DESCRIPTIONS = {
    'wide-lens':     "Every move the holder uses is 10% more accurate.",
    'zoom-lens':     "The holder's moves are 20% more accurate when it moves second.",
    'bright-powder': "Moves aimed at the holder are 10% less accurate.",
    'lax-incense':   "Moves aimed at the holder are 5% less accurate.",
    'kings-rock':    "The holder's damaging moves gain a 10% chance to flinch.",
    'razor-fang':    "The holder's damaging moves gain a 10% chance to flinch.",
    'quick-claw':    "The holder has a 3-in-16 chance to move first in its bracket.",
    'lagging-tail':  "The holder always moves last in its bracket.",
    'full-incense':  "The holder always moves last in its bracket.",
}

PHASE4_EMOJI = {
    'wide-lens': '🔍', 'zoom-lens': '🔬', 'bright-powder': '✨', 'lax-incense': '🌸',
    'kings-rock': '👑', 'razor-fang': '🦷', 'quick-claw': '🪝',
    'lagging-tail': '🐌', 'full-incense': '🕯️',
}


def build_phase4_stock():
    """
    The Phase 4 shelf, checked against the tables the engine reads.

    Same assertion as Phases 2 and 3: an item on this shelf that no table implements is
    an item the shop charges for and the engine ignores.
    """
    implemented = (set(ITEM_ACCURACY_MULTIPLIERS) | {'zoom-lens'}
                   | set(ITEM_ACCURACY_AGAINST_HOLDER) | set(ITEM_FLINCH_CHANCE)
                   | {'quick-claw'} | set(LAST_IN_BRACKET_ITEMS))
    missing = implemented - set(PHASE4_DESCRIPTIONS)
    assert not missing, f"Phase 4 items with no shop entry: {sorted(missing)}"
    extra = set(PHASE4_DESCRIPTIONS) - implemented
    assert not extra, f"Phase 4 shop entries with no implementation: {sorted(extra)}"

    return {
        item: {
            "name": item.replace('-', ' ').title(),
            "price": PHASE4_PRICE,
            "desc": PHASE4_DESCRIPTIONS[item],
            "emoji": PHASE4_EMOJI.get(item, '🎯'),
            "category": "battleitems",
        }
        for item in sorted(implemented)
    }


EQUIPMENT_CATALOG.update(build_phase4_stock())


# ==========================================
# 🛡️ THE PHASE 5 SHELF - DEFENSIVE AND UTILITY GEAR
# ==========================================
# The modern utility layer. Almost every one of these is the ITEM half of something the
# ability layer already does, so most are a name added to a set the engine already reads
# rather than a mechanism of their own.
#
#   covert-cloak      Shield Dust        secondary_chance
#   clear-amulet      Clear Body         refuses_stat_drop
#   protective-pads   Long Reach         makes_contact
#   mirror-herb       Opportunist        copies_stat_boosts
#   safety-goggles    Overcoat           powder moves + the weather chip
#   loaded-dice       Skill Link         the multi-strike roll
#   focus-band        Sturdy             the survive-at-1 branch
SECONDARY_IMMUNE_ITEMS = {'covert-cloak'}
STAT_DROP_IMMUNE_ITEMS = {'clear-amulet'}
COPIES_BOOSTS_ITEMS = {'mirror-herb'}
POWDER_IMMUNE_ITEMS = {'safety-goggles'}
WEATHER_CHIP_IMMUNE_ITEMS = {'safety-goggles'}

# Long Reach's slot. Both of these stop the holder TOUCHING what it hits, which is what
# spares it from Rough Skin, Static, a Rocky Helmet and Pickpocket alike.
#
# The item's PokeAPI text - "prevents side effects of contact moves used on the holder" -
# has the direction backwards. In the games the pads are worn by the ATTACKER and protect
# it from what it touches, which is the reading implemented here.
NO_CONTACT_ITEMS = {'protective-pads', 'punching-glove'}

# ==========================================
# 👊 WHAT COUNTS AS A PUNCH
# ==========================================
# Written out rather than tested with `'punch' in move_name`, which is what the engine
# did before this shelf needed the same answer. That substring test called Sucker Punch a
# punch - it is not, and never has been - and missed Meteor Mash, Hammer Arm, Plasma
# Fists, Ice Hammer, Wicked Blow, Surging Strikes, Double Iron Bash and Rage Fist, none
# of which has "punch" in the name.
#
# Iron Fist reads this table now as well, so the ability and the item cannot come to
# disagree about what a punch is.
PUNCH_MOVES = {
    'bullet-punch', 'comet-punch', 'dizzy-punch', 'double-iron-bash', 'drain-punch',
    'dynamic-punch', 'fire-punch', 'focus-punch', 'hammer-arm', 'ice-hammer',
    'ice-punch', 'jet-punch', 'mach-punch', 'mega-punch', 'meteor-mash',
    'plasma-fists', 'power-up-punch', 'rage-fist', 'shadow-punch', 'sky-uppercut',
    'surging-strikes', 'thunder-punch', 'wicked-blow',
}
PUNCHING_GLOVE_BOOST = 1.1

# ==========================================
# 🥚 EVIOLITE
# ==========================================
# 1.5x both walls, but only for a specimen that still has somewhere to evolve TO.
# Answered off `evolution_rules` at import, the same way body mass and base Attack are -
# a battle-time database read inside the damage formula is not available to it, and a
# hand-written list of every unevolved species would be 453 chances to be wrong.
EVIOLITE_MULTIPLIER = 1.5
EVIOLITE_STATS = ('defense', 'special-defense')
UNEVOLVED_SPECIES = set()

try:
    import sqlite3 as _sqlite3
    with _sqlite3.connect(DB_FILE) as _conn:
        UNEVOLVED_SPECIES = {
            row[0] for row in
            _conn.execute("SELECT DISTINCT base_species_id FROM evolution_rules")
            if row[0]
        }
    print(f"🥚 Indexed {len(UNEVOLVED_SPECIES)} species that can still evolve.")
except Exception as e:
    print(f"⚠️ WARNING: Could not index evolutions ({e}). Eviolite will do nothing.")

# The rest, each a single number read in one place.
FOCUS_BAND_ODDS = 0.10          # survive at 1 HP, from any HP, unlike Focus Sash
SHELL_BELL_FRACTION = 1.0 / 8.0  # of the damage DEALT, healed back
BIG_ROOT_DRAIN_BONUS = 1.3      # to drain, Ingrain and Aqua Ring
BINDING_BAND_MULTIPLIER = 2.0   # to the per-turn bind chip
GRIP_CLAW_TURNS = 7             # a bind lasts this long instead of 4-5
LOADED_DICE_MIN_HITS = 4        # a 2-to-5 move never rolls below this

HEAVY_DUTY_BOOTS = 'heavy-duty-boots'
ABILITY_SHIELD = 'ability-shield'

PHASE5_PRICE = 400

PHASE5_DESCRIPTIONS = {
    'ability-shield':   "The holder's ability cannot be changed or suppressed.",
    'big-root':         "The holder recovers 30% more from draining moves.",
    'binding-band':     "The holder's binding moves deal double damage each turn.",
    'clear-amulet':     "The holder's stats cannot be lowered by the opponent.",
    'covert-cloak':     "The holder is immune to the secondary effects of moves.",
    'eviolite':         "1.5x Defense and Sp. Def, if the holder can still evolve.",
    'focus-band':       "A 1-in-10 chance to survive any lethal hit at 1 HP.",
    'grip-claw':        "The holder's binding moves last 7 turns.",
    'heavy-duty-boots': "The holder ignores every entry hazard.",
    'loaded-dice':      "The holder's multi-hit moves never hit fewer than 4 times.",
    'mirror-herb':      "Copies every stat boost the opponent gains.",
    'protective-pads':  "The holder's moves never make contact.",
    'punching-glove':   "Punching moves are 10% stronger and make no contact.",
    'safety-goggles':   "Immune to powder moves and to sandstorm and hail damage.",
    'shell-bell':       "The holder recovers an eighth of the damage it deals.",
}

PHASE5_EMOJI = {
    'ability-shield': '🛡️', 'big-root': '🌱', 'binding-band': '🎗️',
    'clear-amulet': '💠', 'covert-cloak': '🧥', 'eviolite': '🥚',
    'focus-band': '🎽', 'grip-claw': '🦞', 'heavy-duty-boots': '🥾',
    'loaded-dice': '🎲', 'mirror-herb': '🪞', 'protective-pads': '🧤',
    'punching-glove': '👊', 'safety-goggles': '🥽', 'shell-bell': '🔔',
}


def build_phase5_stock():
    """
    The Phase 5 shelf, checked against the tables the engine reads.

    Same assertion as Phases 2 to 4. The singletons are named explicitly because each is
    read by exactly one clause rather than looked up in a table.
    """
    implemented = (SECONDARY_IMMUNE_ITEMS | STAT_DROP_IMMUNE_ITEMS
                   | COPIES_BOOSTS_ITEMS | POWDER_IMMUNE_ITEMS | NO_CONTACT_ITEMS
                   | {'eviolite', 'focus-band', 'shell-bell', 'big-root',
                      'binding-band', 'grip-claw', 'loaded-dice',
                      HEAVY_DUTY_BOOTS, ABILITY_SHIELD})
    missing = implemented - set(PHASE5_DESCRIPTIONS)
    assert not missing, f"Phase 5 items with no shop entry: {sorted(missing)}"
    extra = set(PHASE5_DESCRIPTIONS) - implemented
    assert not extra, f"Phase 5 shop entries with no implementation: {sorted(extra)}"

    return {
        item: {
            "name": item.replace('-', ' ').title(),
            "price": PHASE5_PRICE,
            "desc": PHASE5_DESCRIPTIONS[item],
            "emoji": PHASE5_EMOJI.get(item, '🛡️'),
            "category": "battleitems",
        }
        for item in sorted(implemented)
    }


EQUIPMENT_CATALOG.update(build_phase5_stock())


# ==========================================
# 🧬 THE PHASE 6 SHELF - SPECIES-SPECIFIC GEAR
# ==========================================
# Sixteen items, and every one of them is "a flat effect, but only for this species".
# That is the shape stat_multiplier_for already handles for Huge Power, so almost all of
# this is a table rather than a mechanism.
#
# Species are matched on the BASE name - the part before the first hyphen - which is the
# same idiom the Crowned forms use. That is what lets an Alolan Marowak swing a Thick
# Club and a Galarian Farfetch'd hold a Stick, both of which are correct.

# 1. The stat multipliers. Stat keys are the ones stat_multiplier_for is called with:
#    attack, sp_atk, defense, sp_def, speed.
SPECIES_STAT_ITEMS = {
    'light-ball':     {'species': {'pikachu'},
                       'stats': {'attack': 2.0, 'sp_atk': 2.0}},
    'thick-club':     {'species': {'cubone', 'marowak'},
                       'stats': {'attack': 2.0}},
    'soul-dew':       {'species': {'latias', 'latios'},
                       'stats': {'sp_atk': 1.5, 'sp_def': 1.5}},
    'deep-sea-tooth': {'species': {'clamperl'}, 'stats': {'sp_atk': 2.0}},
    'deep-sea-scale': {'species': {'clamperl'}, 'stats': {'sp_def': 2.0}},
    # The two Ditto powders are the only rows with a condition: both descriptions end
    # "the boost is lost after transforming", and Transform is a volatile this engine
    # already tracks.
    'metal-powder':   {'species': {'ditto'},
                       'stats': {'defense': 1.5, 'sp_def': 1.5},
                       'lost_on_transform': True},
    'quick-powder':   {'species': {'ditto'}, 'stats': {'speed': 2.0},
                       'lost_on_transform': True},
}

# 2. The two that sharpen a crit rather than a stat. Sirfetch'd is included because the
#    modern games let it hold the Leek; the item is still filed under its old name here.
SPECIES_CRIT_ITEMS = {
    'lucky-punch': {'species': {'chansey'}, 'stages': 2},
    'stick':       {'species': {'farfetchd', 'sirfetchd'}, 'stages': 2},
}

# 3. The three Orbs, which are type boosters with a species gate. Kept apart from
#    TYPE_BOOST_ITEMS because that table is item -> ONE type and these are item -> two,
#    and because a plate on the wrong species still works while an Orb does not.
SPECIES_TYPE_BOOST_ITEMS = {
    'adamant-orb':  {'species': 'dialga',   'types': {'dragon', 'steel'}},
    'lustrous-orb': {'species': 'palkia',   'types': {'dragon', 'water'}},
    'griseous-orb': {'species': 'giratina', 'types': {'dragon', 'ghost'}},
    # The Generation 8 replacements for the three above. Same shape, same species, same
    # two elements - Legends: Arceus renamed the item and nothing else about it.
    'adamant-crystal': {'species': 'dialga',   'types': {'dragon', 'steel'}},
    'lustrous-globe':  {'species': 'palkia',   'types': {'dragon', 'water'}},
    'griseous-core':   {'species': 'giratina', 'types': {'dragon', 'ghost'}},
    # ITEM PHASE 10: Ogerpon's three masks. `types: None` means EVERY element, which the
    # Orbs never needed - a mask lifts all of Ogerpon's moves rather than two of them.
    'cornerstone-mask': {'species': 'ogerpon', 'types': None},
    'hearthflame-mask': {'species': 'ogerpon', 'types': None},
    'wellspring-mask':  {'species': 'ogerpon', 'types': None},
}
SPECIES_ORB_MULTIPLIER = 1.2

# 4. The ones that change a FORM on entry, which is the Rusted Sword's machinery. The
#    Griseous Orb is the only item in this phase that does both - it boosts two elements
#    AND reshapes its holder, so it appears in this table and the one above.
SPECIES_FORM_ITEMS = {
    'griseous-orb':  {'species': 'giratina', 'form': 'giratina-origin',
                      'flavour': 'was drawn into its Origin Forme'},
    # Dialga and Palkia had no entry-form item at all until now - only Giratina did,
    # because only Giratina's Orb reshapes its holder in Generation 4. The Adamant
    # Crystal and Lustrous Globe give the other two the same thing.
    'adamant-crystal': {'species': 'dialga', 'form': 'dialga-origin',
                        'flavour': 'unfolded into its Origin Forme'},
    'lustrous-globe':  {'species': 'palkia', 'form': 'palkia-origin',
                        'flavour': 'unfolded into its Origin Forme'},
    'griseous-core':   {'species': 'giratina', 'form': 'giratina-origin',
                        'flavour': 'was drawn into its Origin Forme'},
    'red-nectar':    {'species': 'oricorio', 'form': 'oricorio-baile',
                      'flavour': 'drank deep and danced the Baile style'},
    'yellow-nectar': {'species': 'oricorio', 'form': 'oricorio-pom-pom',
                      'flavour': 'drank deep and danced the Pom-Pom style'},
    'pink-nectar':   {'species': 'oricorio', 'form': 'oricorio-pau',
                      'flavour': "drank deep and danced the Pa'u style"},
    'purple-nectar': {'species': 'oricorio', 'form': 'oricorio-sensu',
                      'flavour': 'drank deep and danced the Sensu style'},
    # ITEM PHASE 10: the masks are the Griseous Orb's shape exactly - each one reshapes
    # its holder AND lifts its damage - so they are rows in this table and the one above
    # rather than a mechanism of their own.
    'cornerstone-mask': {'species': 'ogerpon', 'form': 'ogerpon-cornerstone-mask',
                         'flavour': 'donned the Cornerstone Mask'},
    'hearthflame-mask': {'species': 'ogerpon', 'form': 'ogerpon-hearthflame-mask',
                         'flavour': 'donned the Hearthflame Mask'},
    'wellspring-mask':  {'species': 'ogerpon', 'form': 'ogerpon-wellspring-mask',
                         'flavour': 'donned the Wellspring Mask'},
}

# ==========================================
# 🎭 ITEM PHASE 10: THE UNPHASED SHELF, PART TWO
# ==========================================
# The Adrenaline Orb answers Intimidate the way the Guard Dog ability does, one step
# further along: Guard Dog turns the glare into an Attack stage, this turns it into a
# Speed one and is spent doing it. It rides the shared Intimidate hook rather than a new
# one, which is what keeps it agreeing with Clear Body and Mirror Armor about whether the
# glare landed at all.
ADRENALINE_ORB = 'adrenaline-orb'
ADRENALINE_ORB_STAGES = 1

PHASE10_DESCRIPTIONS = {
    'cornerstone-mask': ("Ogerpon takes its Cornerstone form, and all its moves do 20% "
                         "more damage.", 450, '🪨'),
    'hearthflame-mask': ("Ogerpon takes its Hearthflame form, and all its moves do 20% "
                         "more damage.", 450, '🔥'),
    'wellspring-mask':  ("Ogerpon takes its Wellspring form, and all its moves do 20% "
                         "more damage.", 450, '💧'),
    ADRENALINE_ORB:     ("Raises the holder's Speed by one stage when it is Intimidated. "
                         "Single use.", 400, '🧪'),
}

PHASE6_PRICE = 450

PHASE6_DESCRIPTIONS = {
    'light-ball':     "Doubles Pikachu's Attack and Sp. Atk.",
    'thick-club':     "Doubles Cubone's or Marowak's Attack.",
    'soul-dew':       "Raises Latias's and Latios's Sp. Atk and Sp. Def by 50%.",
    'deep-sea-tooth': "Doubles Clamperl's Sp. Atk.",
    'deep-sea-scale': "Doubles Clamperl's Sp. Def.",
    'metal-powder':   "Raises Ditto's Defense and Sp. Def by 50%, until it Transforms.",
    'quick-powder':   "Doubles Ditto's Speed, until it Transforms.",
    'lucky-punch':    "Raises Chansey's critical hit ratio by two stages.",
    'stick':          "Raises Farfetch'd's critical hit ratio by two stages.",
    'adamant-orb':    "Dialga's Dragon and Steel moves do 20% more damage.",
    'lustrous-orb':   "Palkia's Dragon and Water moves do 20% more damage.",
    'griseous-orb':   "Giratina's Dragon and Ghost moves do 20% more damage, and it "
                      "takes its Origin Forme.",
    'red-nectar':     "Changes Oricorio to its Baile style.",
    'yellow-nectar':  "Changes Oricorio to its Pom-Pom style.",
    'pink-nectar':    "Changes Oricorio to its Pa'u style.",
    'purple-nectar':  "Changes Oricorio to its Sensu style.",
}

PHASE6_EMOJI = {
    'light-ball': '💡', 'thick-club': '🦴', 'soul-dew': '💧', 'deep-sea-tooth': '🦷',
    'deep-sea-scale': '🐚', 'metal-powder': '⚙️', 'quick-powder': '💨',
    'lucky-punch': '🥊', 'stick': '🥬', 'adamant-orb': '💎', 'lustrous-orb': '🔮',
    'griseous-orb': '🟣', 'red-nectar': '🌺', 'yellow-nectar': '🌼',
    'pink-nectar': '🌸', 'purple-nectar': '💜',
}


# The three Generation 8 Orbs. They belong to the same two engine tables as their
# Generation 4 twins, but not to the Phase 6 shop shelf - see build_phase6_stock.
GEN8_ORB_ITEMS = frozenset({'adamant-crystal', 'lustrous-globe', 'griseous-core'})


def build_phase6_stock():
    """
    The Phase 6 shelf, checked against the tables the engine reads.

    Same assertion as Phases 2 to 5. The Griseous Orb is deliberately in two of the
    source tables and must still appear exactly once on the shelf.
    """
    # Phase 10's masks join the same two species tables - they are the Griseous Orb's
    # shape - so they are subtracted here rather than being given a second home. This
    # assertion is about Phase 6's OWN shelf, and folding them in would have made it
    # quietly stop meaning that.
    #
    # The three Generation 8 Orbs are subtracted for the same reason and a second one:
    # they are not shop stock at all. Their Generation 4 twins sit on this 450-token
    # shelf, but an Adamant Crystal is a key item and is listed unpurchaseable in
    # EQUIPMENT_CATALOG. This assertion fired the moment they were added to the engine
    # tables, which is exactly what it is for - it just wanted telling where they went.
    implemented = ((set(SPECIES_STAT_ITEMS) | set(SPECIES_CRIT_ITEMS)
                    | set(SPECIES_TYPE_BOOST_ITEMS) | set(SPECIES_FORM_ITEMS))
                   - set(PHASE10_DESCRIPTIONS) - GEN8_ORB_ITEMS)
    missing = implemented - set(PHASE6_DESCRIPTIONS)
    assert not missing, f"Phase 6 items with no shop entry: {sorted(missing)}"
    extra = set(PHASE6_DESCRIPTIONS) - implemented
    assert not extra, f"Phase 6 shop entries with no implementation: {sorted(extra)}"

    return {
        item: {
            "name": item.replace('-', ' ').title(),
            "price": PHASE6_PRICE,
            "desc": PHASE6_DESCRIPTIONS[item],
            "emoji": PHASE6_EMOJI.get(item, '🧬'),
            "category": "battleitems",
        }
        for item in sorted(implemented)
    }


EQUIPMENT_CATALOG.update(build_phase6_stock())


# ==========================================
# 🫐 ITEM PHASE 7: THE ELEVEN BERRIES THAT WERE NEVER PLANTED
# ==========================================
# The berry layer is the best-served corner of the item shelf - Block 19 gave it Ripen,
# Gluttony, Harvest, Cud Chew, Cheek Pouch and Belch - which made these eleven easy to
# miss: they are not half-implemented, they were simply never in the botanical database
# at all, and a database that does not know a berry cannot drop it, throw it or eat it.
#
# They split into two groups that share nothing except the word berry:
#
#   five ANSWER A HIT   - the only berries whose trigger is being struck rather than
#                         getting low, which is why check_consumables walks past them
#   six LOWER AN EV     - not a battle effect at all. Fed from the bag between battles,
#                         which is the vitamin command's job, in the opposite direction
#
# The five are deliberately NOT rows in ITEM_HIT_REACTIONS beside the Weakness Policy,
# even though four of them are the same "when hit, take a stat stage" sentence. A policy
# is spent through `spend_item`; a berry is EATEN, and eating is what Unnerve blocks,
# Ripen doubles, Cheek Pouch pays for and Belch, Harvest and Cud Chew all remember.
# Filing these with the policies would have produced five items that looked right in
# every test that asked what they do, and were wrong about what they ARE.
BERRY_HIT_REACTIONS = {
    # Stat names are the RESOLVER's vocabulary - 'special-defense', not 'sp_def' -
    # for the same reason ITEM_HIT_REACTIONS uses it: STAT_STAGE_KEYS translates with a
    # .get that silently skips anything it does not recognise, so the storage spelling
    # would produce no error, no log line and no boost.
    'kee-berry':     {'trigger': 'physical', 'self': [('defense', 1)]},
    'maranga-berry': {'trigger': 'special',  'self': [('special-defense', 1)]},

    # The two that hurt whoever threw the punch. A fraction of the ATTACKER's max HP,
    # which is what makes them worth holding against a wall rather than a glass cannon.
    'jaboca-berry':  {'trigger': 'physical', 'recoil': 1.0 / 8.0},
    'rowap-berry':   {'trigger': 'special',  'recoil': 1.0 / 8.0},

    # The only one that reads effectiveness rather than damage class, and the only one
    # that heals. Its trigger is Weakness Policy's; its payload is a Sitrus Berry's.
    'enigma-berry':  {'trigger': 'super_effective', 'heal': 0.25},
}

# Derived rather than retyped, so consumables.json stays the single source of truth for
# which berry lowers which EV. A hand-written copy here would be a second place to get
# `ev_sp_atk` wrong, and the two would drift the first time one was edited alone.
EV_LOWERING_BERRIES = {
    berry: (row['stat'], row.get('value', 10))
    for berry, row in sorted(CONSUMABLE_DATABASE.items())
    if row.get('type') == 'ev_lower'
}

# What a berry is worth to a specimen's opinion of you. The games pay this for the same
# reason they let the berry lower an EV: the berry is bitter, and putting up with it is
# a favour. Happiness is read by the evolution triggers, so this is not decoration.
EV_BERRY_HAPPINESS = 10
MAX_HAPPINESS = 255

# Berries are not merchandise - none of the forty-one already here is purchasable, and
# these eleven are not either. They arrive the way every other berry does, as a catch
# drop rolled against CONSUMABLE_DATABASE, which is precisely why adding them to that
# file was the first half of this block. These rows exist so the bag can render a name
# and an icon instead of a slug.
PHASE7_BERRY_CATALOG = {
    "enigma-berry":  {"name": "Enigma Berry",  "desc": "Restores 1/4 max HP when struck by a super-effective attack.", "emoji": "🌀"},
    "jaboca-berry":  {"name": "Jaboca Berry",  "desc": "Hurts the attacker for 1/8 its max HP when struck by a physical attack.", "emoji": "🫐"},
    "rowap-berry":   {"name": "Rowap Berry",   "desc": "Hurts the attacker for 1/8 its max HP when struck by a special attack.", "emoji": "🍇"},
    "kee-berry":     {"name": "Kee Berry",     "desc": "Raises Defense when struck by a physical attack.", "emoji": "🍏"},
    "maranga-berry": {"name": "Maranga Berry", "desc": "Raises Sp. Def when struck by a special attack.", "emoji": "🥝"},
    "pomeg-berry":   {"name": "Pomeg Berry",   "desc": "Lowers HP EVs by 10 and raises happiness.", "emoji": "🍎"},
    "kelpsy-berry":  {"name": "Kelpsy Berry",  "desc": "Lowers Attack EVs by 10 and raises happiness.", "emoji": "🥬"},
    "qualot-berry":  {"name": "Qualot Berry",  "desc": "Lowers Defense EVs by 10 and raises happiness.", "emoji": "🍑"},
    "hondew-berry":  {"name": "Hondew Berry",  "desc": "Lowers Sp. Atk EVs by 10 and raises happiness.", "emoji": "🍈"},
    "grepa-berry":   {"name": "Grepa Berry",   "desc": "Lowers Sp. Def EVs by 10 and raises happiness.", "emoji": "🍇"},
    "tamato-berry":  {"name": "Tamato Berry",  "desc": "Lowers Speed EVs by 10 and raises happiness.", "emoji": "🍅"},
}


def build_phase7_stock():
    """
    The Phase 7 berries, checked against the botanical database that drives them.

    The assertion Phases 2 to 6 make is "nothing on the shelf is unimplemented". Here it
    is the tighter one the berry layer actually needs: the catalog and the botanical
    database must name the SAME berries, in both directions. A berry in the database
    with no catalog row renders in the bag as a raw slug; a catalog row with no database
    entry is a berry that can never drop, which is a shop listing for something that
    does not exist.
    """
    reactive = {b for b, r in CONSUMABLE_DATABASE.items()
                if r.get('type') == 'hit_reaction'}
    assert reactive == set(BERRY_HIT_REACTIONS), (
        f"hit_reaction berries and BERRY_HIT_REACTIONS disagree: "
        f"{sorted(reactive ^ set(BERRY_HIT_REACTIONS))}")

    assert len(EV_LOWERING_BERRIES) == 6, (
        f"expected six EV-lowering berries, found {sorted(EV_LOWERING_BERRIES)}")
    columns = {column for column, _ in EV_LOWERING_BERRIES.values()}
    assert len(columns) == 6, f"two berries lower the same EV: {sorted(columns)}"

    stock = {
        berry: dict(meta, price=0, category="berry", purchasable=False)
        for berry, meta in PHASE7_BERRY_CATALOG.items()
    }

    catalogued = {k for k, v in EQUIPMENT_CATALOG.items()
                  if v.get('category') == 'berry'} | set(stock)
    missing = set(CONSUMABLE_DATABASE) - catalogued
    assert not missing, f"berries with no catalog row: {sorted(missing)}"
    orphaned = catalogued - set(CONSUMABLE_DATABASE)
    assert not orphaned, f"catalog berries the database does not grow: {sorted(orphaned)}"

    return stock


EQUIPMENT_CATALOG.update(build_phase7_stock())


# ==========================================
# 🌟 THE FOUR PINCH BERRIES THAT ONLY LOOKED FINISHED
# ==========================================
# Starf, Lansat, Micle and Custap all carried the SAME placeholder row in
# consumables.json - attack, one stage - so all four raised Attack and all four read as
# "live" to every scan that counts mentions. That is the item audit's own caveat, "it
# cannot see a HALF-implemented item", biting four berries at once.
#
# Apicot and Petaya were the same defect one step quieter: both were implemented as
# their PHYSICAL twin (Defense and Attack) while their shop entries promised Sp. Def and
# Sp. Atk. Nothing in the codebase compared the two, so the shop had been lying about
# them for as long as they had existed.
#
# What makes these four different from the other five pinch berries is WHEN they are
# spent. A Liechi Berry banks a stat stage on the spot. These hand out a marker that a
# LATER moment reads - the crit stage, the accuracy roll, the turn order - so each one
# needs a name that both the berry and that moment agree on.
LANSAT_MARKER = 'lansat_crit'
MICLE_MARKER = 'micle_accuracy'
CUSTAP_MARKER = 'custap_priority'

BERRY_SHELF_OPEN = True         # see stock_the_berry_shelf below

LANSAT_CRIT_STAGES = 2          # the same two stages Focus Energy is worth
MICLE_ACCURACY_MULTIPLIER = 1.2  # the Gen V+ figure, not Gen IV's perfect accuracy
CUSTAP_TIER = 1                 # the front of its bracket, where Quick Claw sits

# Every stat a Starf Berry can land on. Deliberately the five BATTLE stats: the games
# exclude accuracy and evasion, and rolling one of those would make the berry's best
# outcome and its worst outcome much further apart than they should be.
STARF_STATS = ('attack', 'defense', 'sp_atk', 'sp_def', 'speed')

# Micle and Custap are spent on ONE later action, so they need to expire. Lansat does
# not: like Focus Energy it lasts until its holder leaves the field, which the volatile
# wipe on withdrawal already handles - so it is marked `lasting` in consumables.json and
# the sweep below leaves it alone.
#
# The expiry uses the charge lifecycle's trick, because it has the same problem: a marker
# handed out DURING a turn must survive that turn's own end-of-turn sweep, or a berry
# eaten at 1/4 HP would be swept away before the move it was bought for. So the first
# sweep clears the freshness and the second removes the marker.
ACTION_MARKER_FRESH = '_fresh'


# ==========================================
# 🫐 OPENING THE BERRY SHELF
# ==========================================
# Every berry has been `purchasable: False` since there were berries, because the plan
# was always that you GROW them. There is no farming yet, and until there is, the only
# way to get one is a 40% roll on a catch against a pool of fifty-two - so a trainer who
# wants a particular berry for a particular specimen is looking at a long wait and no way
# to shorten it. Selling them is the stopgap.
#
# When farming lands, this is the switch to turn back off: flip BERRY_SHELF_OPEN and
# every berry goes back to being drop-only, without touching fifty-two rows.
#
# Prices come from the BEHAVIOUR the engine reads rather than from a hand-typed number
# per berry, for the same reason the type-booster shelf does: fifty-two hand-typed prices
# is fifty-two chances to sell a Lum Berry for the price of an Oran, and a berry added
# later would arrive with no price at all.
BERRY_PRICES = {
    'cure_status':   150,   # one status, and only if it lands on you
    'restore_pp':    150,
    'heal_flat':     150,
    'heal_pct':      200,
    'resist_damage': 200,   # a single super-effective hit, halved, once
    'ev_lower':      200,   # the vitamins' twin, and priced under them
    'stat_boost':    250,   # the pinch berries, which need you to be losing first
    'random_boost':  250,
    'volatile_boost': 250,
    'hit_reaction':  250,
}
BERRY_DEFAULT_PRICE = 200


def stock_the_berry_shelf():
    """
    Put every berry the botanical database grows on sale, priced by what it does.

    Returns how many were stocked, so the caller can assert it is not zero - a silent
    no-op here would leave the shelf exactly as shut as it was before, and nothing else
    in the file would notice.
    """
    if not BERRY_SHELF_OPEN:
        return 0

    stocked = 0
    for berry, meta in EQUIPMENT_CATALOG.items():
        if meta.get('category') != 'berry':
            continue
        behaviour = (CONSUMABLE_DATABASE.get(berry) or {}).get('type')
        meta['price'] = BERRY_PRICES.get(behaviour, BERRY_DEFAULT_PRICE)
        meta['purchasable'] = True
        stocked += 1

    assert stocked == len(CONSUMABLE_DATABASE), (
        f"stocked {stocked} berries but the database grows "
        f"{len(CONSUMABLE_DATABASE)}")
    return stocked


BERRIES_ON_SALE = stock_the_berry_shelf()


# ==========================================
# 🧬 ITEM PHASE 8: STONES, CRYSTALS, MEMORIES AND SHARDS
# ==========================================
# The plan called this phase "156 items of data entry that blocks nothing else". Three of
# the four families turned out to be something other than data entry.
#
# THE MEGA STONES WERE NOT BOUND TO ANYTHING. `may_mega_evolve` identified a Mega Stone
# with `'ite' in held_item`, so nothing ever checked the stone against the SPECIES. A
# Charizard holding a White Herb - wh-ITE-herb - Mega Evolved, and a Gengar holding a
# Venusaurite became Mega Gengar. With one stone in the catalogue that was a curiosity;
# adding ninety-one more would have made every stone in the game universal. So the table
# binding a stone to its species IS this phase, and the shop rows fall out of it.
#
# THE MEMORIES AND THE ELEMENTAL Z-CRYSTALS WERE ALREADY LIVE. The audit read all
# forty-six as absent because it scanned PokeAPI's names - `bug-memory`,
# `normalium-z--held` - while the engine keys them `bug-memory` (handled generically by
# `type_from_item`, so the literal name appears nowhere) and `normalium-z` (no suffix).
# That is the audit's "a name in the source proves nothing" caveat running backwards:
# the ABSENCE of a name proves nothing either. These needed a price, not an engine.
#
# THE TERA SHARDS ARE THE ONE HONEST CASE OF THE ORIGINAL DESCRIPTION, and they stay
# inert - see TERA_SHARD_TYPES at the bottom of this section.

# Every Mega Stone, bound to the specimen it belongs to. The value is matched against a
# specimen's full name first and its base name second, which is what lets one row cover
# a species with many forms (`tatsugiri` reaches Tatsugiri-Curly) while another pins a
# single one (`raichu-alola` refuses an ordinary Raichu). That two-step match is why the
# Floette and Raichu special cases that `may_mega_evolve` used to carry in code are just
# rows here now.
MEGA_STONE_SPECIES = {
    'abomasite': 'abomasnow',
    'absolite': 'absol',
    'absolite-z': 'absol',
    'aerodactylite': 'aerodactyl',
    'aggronite': 'aggron',
    'alakazite': 'alakazam',
    'altarianite': 'altaria',
    'ampharosite': 'ampharos',
    'audinite': 'audino',
    'banettite': 'banette',
    'barbaracite': 'barbaracle',
    'baxcalibrite': 'baxcalibur',
    'beedrillite': 'beedrill',
    'blastoisinite': 'blastoise',
    'blazikenite': 'blaziken',
    'cameruptite': 'camerupt',
    'chandelurite': 'chandelure',
    'charizardite-x': 'charizard',
    'charizardite-y': 'charizard',
    'chesnaughtite': 'chesnaught',
    'chimechite': 'chimecho',
    'clefablite': 'clefable',
    'crabominite': 'crabominable',
    'darkranite': 'darkrai',
    'delphoxite': 'delphox',
    'diancite': 'diancie',
    'dragalgite': 'dragalge',
    'dragoninite': 'dragonite',
    'drampanite': 'drampa',
    'eelektrossite': 'eelektross',
    'emboarite': 'emboar',
    'excadrite': 'excadrill',
    'falinksite': 'falinks',
    'feraligite': 'feraligatr',
    # Only the Eternal Flower Floette has a Mega Forme; the ordinary flower colours
    # share the base name and must not match.
    'floettite': 'floette-eternal',
    'froslassite': 'froslass',
    'galladite': 'gallade',
    'garchompite': 'garchomp',
    'garchompite-z': 'garchomp',
    'gardevoirite': 'gardevoir',
    'gengarite': 'gengar',
    'glalitite': 'glalie',
    'glimmoranite': 'glimmora',
    'golisopite': 'golisopod',
    'golurkite': 'golurk',
    'greninjite': 'greninja',
    'gyaradosite': 'gyarados',
    'hawluchanite': 'hawlucha',
    'heatranite': 'heatran',
    'heracronite': 'heracross',
    'houndoominite': 'houndoom',
    'kangaskhanite': 'kangaskhan',
    'latiasite': 'latias',
    'latiosite': 'latios',
    'lopunnite': 'lopunny',
    'lucarionite': 'lucario',
    'lucarionite-z': 'lucario',
    'magearnite': 'magearna',
    'malamarite': 'malamar',
    'manectite': 'manectric',
    'mawilite': 'mawile',
    'medichamite': 'medicham',
    'meganiumite': 'meganium',
    'meowsticite': 'meowstic',
    'metagrossite': 'metagross',
    'mewtwonite-x': 'mewtwo',
    'mewtwonite-y': 'mewtwo',
    'pidgeotite': 'pidgeot',
    'pinsirite': 'pinsir',
    'pyroarite': 'pyroar',
    # ...and only the KANTONIAN Raichu, which is the opposite shape of problem from
    # Floette's - see MEGA_STONE_EXACT_FORMS below.
    'raichunite-x': 'raichu',
    'raichunite-y': 'raichu',
    'sablenite': 'sableye',
    'salamencite': 'salamence',
    'sceptilite': 'sceptile',
    'scizorite': 'scizor',
    'scolipite': 'scolipede',
    'scovillainite': 'scovillain',
    'scraftinite': 'scrafty',
    'sharpedonite': 'sharpedo',
    'skarmorite': 'skarmory',
    'slowbronite': 'slowbro',
    'staraptite': 'staraptor',
    'starminite': 'starmie',
    'steelixite': 'steelix',
    'swampertite': 'swampert',
    'tatsugirinite': 'tatsugiri',
    'tyranitarite': 'tyranitar',
    'venusaurite': 'venusaur',
    'victreebelite': 'victreebel',
    'zeraorite': 'zeraora',
    'zygardite': 'zygarde',
}

# Rayquaza is deliberately absent: it Mega Evolves by KNOWING Dragon Ascent rather than
# by holding anything, which is why `may_mega_evolve` keeps a second clause at all.
MEGA_STONE_FREE_SPECIES = {'rayquaza'}

# Stones that bind to a species EXACTLY, with no fall through to the regional and
# cosmetic forms sitting under the same base name.
#
# Two opposite problems share one table, which is why this set has to exist alongside it.
# Floette needed the binding to pick a form BELOW the base name - `floette-eternal` - and
# the base-name fallback handles that on its own, because 'floette-eternal' never equals
# 'floette'. Raichu needs the reverse: the stone belongs to the plain Kantonian Raichu
# and must NOT reach Alolan Raichu, whose base name is also 'raichu'. The fallback that
# makes one Tatsugiri row cover three forms is exactly what would let it through, so the
# stones that mean "this form and no other" are named here.
MEGA_STONE_EXACT_FORMS = frozenset({'raichunite-x', 'raichunite-y'})


def mega_stone_binds_to(species_name, held_item):
    """
    Whether this held item is the Mega Stone for THIS specimen.

    Replaces `'ite' in held_item`, which was true of a White Herb and an Eviolite and of
    every stone for every species. Matching the full name before the base name is what
    lets one `tatsugiri` row cover all three of its forms, and MEGA_STONE_EXACT_FORMS is
    what lets a row opt out of that fallback when the base name is shared with a regional
    form the stone does not belong to.
    """
    item = (held_item or 'none').lower().replace(' ', '-')
    bound = MEGA_STONE_SPECIES.get(item)
    if not bound:
        return False

    name = (species_name or '').lower().strip()
    if item in MEGA_STONE_EXACT_FORMS:
        return bound == name
    return bound == name or bound == name.split('-')[0].strip()


def is_mega_stone(held_item):
    """Whether the item is a Mega Stone at all, regardless of who is holding it."""
    return (held_item or 'none').lower().replace(' ', '-') in MEGA_STONE_SPECIES


# ==========================================
# 🧠 THE MEMORIES
# ==========================================
# Seventeen discs, one per type except Normal - Silvally IS Normal without one. Already
# read by `type_from_item`, which matches the '<type>-memory' shape rather than a list,
# so no Memory's name appears anywhere in the source. That generosity had a hole worth
# closing: it answered 'banana' for a `banana-memory`, because a suffix is not a
# vocabulary. This is the vocabulary, and it is checked against TYPE_CHART so a typo
# cannot invent an eighteenth element.
MEMORY_TYPES = {f'{element}-memory': element
                for element in sorted(TYPE_CHART) if element != 'normal'}
assert len(MEMORY_TYPES) == 17, f"expected 17 Memories, built {len(MEMORY_TYPES)}"

# ==========================================
# 💎 THE Z-CRYSTALS
# ==========================================
# Both tables moved here from cogs/combat.py for the reason PLATE_TYPES moved: the shop
# now needs the same eighteen names to stock them and the same eighteen Z-Move names to
# describe them, and a table with two readers in two files is how the two come to differ.
# combat.py imports them and every existing reader is unchanged.
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

# What a Z-Move is worth. The engine used to add a flat +100 to the base move's power,
# which is generous at the bottom of the range and punishing at the top: a Z-boosted
# Tackle came out at 140 against the games' 100, and a Z-boosted Giga Impact at 250
# against the games' 200. The second half of that mattered here, because the SIGNATURE
# crystals below have fixed powers taken from the games - and against a flat +100 the
# species-locked Snorlium Z came out weaker than the Normalium Z anyone can buy, which
# would have put two items in the shop whose prices told the player the opposite of the
# truth. This is the Gen VII table, so both halves are right for the same reason.
Z_POWER_TABLE = (
    (55, 100), (65, 120), (75, 140), (85, 160), (95, 175),
    (100, 180), (110, 185), (125, 190), (130, 195),
)
Z_POWER_CEILING = 200

# Guardian of Alola does not roll damage at all - it takes a fixed share of what the
# target has left. Nature's Madness already resolves in the engine's fixed-damage branch
# at one half, so the Z-Move rides the same branch with a bigger number written onto the
# move dict rather than needing a branch of its own.
Z_HP_FRACTION_KEY = '_z_hp_fraction'


def z_move_power(base_power):
    """The power a Z-Move of this base power hits for. Everything past 130 caps out."""
    base_power = base_power or 0
    for threshold, boosted in Z_POWER_TABLE:
        if base_power <= threshold:
            return boosted
    return Z_POWER_CEILING


# The eleven crystals that upgrade ONE move on ONE species instead of a whole element.
# `species` is matched the same two ways MEGA_STONE_SPECIES is - full name, then base -
# so `pikachu` covers the cap forms Pikashunium Z needs.
#
# Eevium Z was held back one phase because Extreme Evoboost is not a damaging Z-Move at
# all: it boosts all five of Eevee's stats by two and deals nothing. Now that the status
# Z-Moves below have a mechanism, it is a row like the rest - it simply carries `boost`
# where the others carry `power`.
# The wildcard a stat list uses to mean 'every stat'. Block 8's protection sets are
# its other reader; it lives here because this is the first place the file needs it.
ALL_STATS = '*'

# `element` is the crystal's own type, which is what the shelf reads for its icon - the
# eighteen elemental crystals wear their type's emoji and these wore a shared star, so a
# bag of them was seventeen identical rows. It is NOT decoration: a test asserts every
# element against the base move's type in the database, which is the one thing that
# would catch a row copied from its neighbour and half-edited.
#
# Mimikium Z is the row that proves the check is worth having. It is a FAIRY crystal -
# Let's Snuggle Forever is Fairy, off Play Rough - while Mimikyu itself is Ghost, so the
# obvious guess from the species is the wrong one.
SIGNATURE_Z_CRYSTALS = {
    'aloraichium-z': {'species': 'raichu-alola', 'move': 'thunderbolt',
                      'element': 'electric',
                      'name': 'Stoked Sparksurfer', 'power': 175},
    'decidium-z':    {'species': 'decidueye', 'move': 'spirit-shackle',
                      'element': 'ghost',
                      'name': 'Sinister Arrow Raid', 'power': 180},
    # The odd one out: Last Resort is a physical move, and its Z-Move deals no damage.
    # `boost` is what turns the move into a status one at resolution time.
    'eevium-z':      {'species': 'eevee', 'move': 'last-resort',
                      'element': 'normal',
                      'name': 'Extreme Evoboost',
                      'boost': [('attack', 2), ('defense', 2), ('special-attack', 2),
                                ('special-defense', 2), ('speed', 2)]},
    'incinium-z':    {'species': 'incineroar', 'move': 'darkest-lariat',
                      'element': 'dark',
                      'name': 'Malicious Moonsault', 'power': 180},
    # Clangorous Soulblaze is the only signature Z-Move that hits AND boosts, which is
    # why `self_boost` is a separate key from `boost`: `boost` means the move stops
    # dealing damage, and this one very much does not.
    'kommonium-z':   {'species': ('kommo-o', 'kommo-o-totem'), 'move': 'clanging-scales',
                      'element': 'dragon',
                      'name': 'Clangorous Soulblaze', 'power': 185,
                      'self_boost': [(ALL_STATS, 1)]},
    # Lunala and Dawn Wings Necrozma share Moongeist Beam, so they share the crystal.
    'lunalium-z':    {'species': ('lunala', 'necrozma-dawn'), 'move': 'moongeist-beam',
                      'element': 'ghost',
                      'name': 'Menacing Moonraze Maelstrom', 'power': 200},
    'lycanium-z':    {'species': 'lycanroc', 'move': 'stone-edge',
                      'element': 'rock',
                      'name': 'Splintered Stormshards', 'power': 190},
    'marshadium-z':  {'species': 'marshadow', 'move': 'spectral-thief',
                      'element': 'ghost',
                      'name': 'Soul-Stealing 7-Star Strike', 'power': 195},
    'mewnium-z':     {'species': 'mew', 'move': 'psychic',
                      'element': 'psychic',
                      'name': 'Genesis Supernova', 'power': 185},
    'mimikium-z':    {'species': 'mimikyu', 'move': 'play-rough',
                      'element': 'fairy',
                      'name': "Let's Snuggle Forever", 'power': 190},
    'pikanium-z':    {'species': 'pikachu', 'move': 'volt-tackle',
                      'element': 'electric',
                      'name': 'Catastropika', 'power': 210},
    'pikashunium-z': {'species': 'pikachu', 'move': 'thunderbolt',
                      'element': 'electric',
                      'name': '10,000,000 Volt Thunderbolt', 'power': 195},
    'primarium-z':   {'species': 'primarina', 'move': 'sparkling-aria',
                      'element': 'water',
                      'name': 'Oceanic Operetta', 'power': 195},
    'snorlium-z':    {'species': 'snorlax', 'move': 'giga-impact',
                      'element': 'normal',
                      'name': 'Pulverizing Pancake', 'power': 210},
    # ...and Solgaleo with Dusk Mane Necrozma, for the same reason as Lunala above.
    'solganium-z':   {'species': ('solgaleo', 'necrozma-dusk'), 'move': 'sunsteel-strike',
                      'element': 'steel',
                      'name': 'Searing Sunraze Smash', 'power': 200},
    # Guardian of Alola takes three quarters of what the target has left rather than
    # rolling damage, so it carries a fraction instead of a power. Nature's Madness
    # already resolves in the engine's fixed-damage branch at one half; this is the
    # same branch with a different number.
    'tapunium-z':    {'species': ('tapu-koko', 'tapu-lele', 'tapu-bulu', 'tapu-fini'),
                      'move': 'natures-madness',
                      'element': 'fairy',
                      'name': 'Guardian of Alola', 'hp_fraction': 0.75},
    # The fused Formes are listed beside Ultra Necrozma because they are what a trainer
    # actually holds the crystal on - in the games it is the crystal that takes them the
    # rest of the way, and Photon Geyser is a move all three know.
    'ultranecrozium-z': {'species': ('necrozma-ultra', 'necrozma-dusk', 'necrozma-dawn'),
                         'move': 'photon-geyser',
                         'element': 'psychic',
                         'name': 'Light That Burns the Sky', 'power': 200},
}



# ==========================================
# 🌟 THE STATUS Z-MOVES
# ==========================================
# A status move used through a Z-Crystal still does its own job - Swords Dance still
# raises Attack, Substitute still costs a quarter - and gains a Z-Power effect ON TOP.
# The engine used to give every one of them the same blanket full heal, which is right
# for Belly Drum and exactly wrong for the two hundred and thirty-one others.
#
# GENERATED from z_move_table.md rather than transcribed, and every key was checked to
# exist in base_moves AND to be a status move before it was written here. The table's
# twenty-four damaging rows are deliberately absent: a damaging move takes the elemental
# Z-Move path and never asks this table anything.
#
# The effects, and what each one means:
#
#   stats             raise the USER's stages, ALL_STATS meaning all five at once
#   reset             clear the user's LOWERED stages, leaving its boosts alone
#   heal              restore the user to full
#   crit              two crit stages, which is Focus Energy's own volatile
#   replacement_heal  bank a Healing Wish for whoever takes the vacated slot
#   redirect          draw in the turn's attacks - inert in singles, see below
#   NO_Z_EFFECT       the games give this one no bonus at all
#
# ORDER MATTERS and is the reason the effect is paid out BEFORE the move rather than
# after: Z-Belly Drum heals so that the half the Drum then costs is paid back, and
# healing afterwards would refund the cost AND leave the user at full HP - a different
# and much stronger item than the one the shop sells.
NO_Z_EFFECT = {}

Z_STATUS_EFFECTS = {
    'acid-armor':      {'reset': True},
    'acupressure':     {'crit': 2},
    'after-you':       {'stats': [('speed', 1)]},
    'agility':         {'reset': True},
    'ally-switch':     {'stats': [('speed', 2)]},
    'amnesia':         {'reset': True},
    'aqua-ring':       {'stats': [('defense', 1)]},
    'aromatherapy':    {'heal': True},
    'aromatic-mist':   {'stats': [('special-defense', 2)]},
    'assist':          NO_Z_EFFECT,
    'attract':         {'reset': True},
    'aurora-veil':     {'stats': [('speed', 1)]},
    'autotomize':      {'reset': True},
    'baby-doll-eyes':  {'stats': [('defense', 1)]},
    'baneful-bunker':  {'stats': [('defense', 1)]},
    'barrier':         {'reset': True},
    'baton-pass':      {'reset': True},
    'belly-drum':      {'heal': True},
    'bestow':          {'stats': [('speed', 2)]},
    'block':           {'stats': [('defense', 1)]},
    'bulk-up':         {'stats': [('attack', 1)]},
    'calm-mind':       {'reset': True},
    'camouflage':      {'stats': [('evasion', 1)]},
    'captivate':       {'stats': [('special-defense', 2)]},
    'celebrate':       {'stats': [(ALL_STATS, 1)]},
    'charge':          {'stats': [('special-defense', 1)]},
    'charm':           {'stats': [('defense', 1)]},
    'coil':            {'reset': True},
    'confide':         {'stats': [('special-defense', 1)]},
    'confuse-ray':     {'stats': [('special-attack', 1)]},
    'conversion':      {'stats': [(ALL_STATS, 1)]},
    'conversion-2':    {'heal': True},
    'copycat':         {'stats': [('accuracy', 1)]},
    'cosmic-power':    {'stats': [('special-defense', 1)]},
    'cotton-guard':    {'reset': True},
    'crafty-shield':   {'stats': [('special-defense', 1)]},
    'curse':           {'stats': [('attack', 1)]},
    'dark-void':       {'reset': True},
    'defend-order':    {'stats': [('defense', 1)]},
    'defense-curl':    {'stats': [('accuracy', 1)]},
    'defog':           {'stats': [('accuracy', 1)]},
    'destiny-bond':    {'redirect': True},
    'detect':          {'stats': [('evasion', 1)]},
    'disable':         {'reset': True},
    'double-team':     {'reset': True},
    'dragon-dance':    {'reset': True},
    'eerie-impulse':   {'stats': [('special-defense', 1)]},
    'electric-terrain':{'stats': [('speed', 1)]},
    'electrify':       {'stats': [('special-attack', 1)]},
    'embargo':         {'stats': [('special-attack', 1)]},
    'encore':          {'stats': [('speed', 1)]},
    'endure':          {'reset': True},
    'entrainment':     {'stats': [('special-defense', 1)]},
    'fairy-lock':      {'stats': [('defense', 1)]},
    'fake-tears':      {'stats': [('special-attack', 1)]},
    'feather-dance':   {'stats': [('defense', 1)]},
    'flash':           {'stats': [('evasion', 1)]},
    'flatter':         {'stats': [('special-defense', 1)]},
    'floral-healing':  {'reset': True},
    'flower-shield':   {'stats': [('defense', 1)]},
    'focus-energy':    {'stats': [('accuracy', 1)]},
    'follow-me':       {'reset': True},
    'foresight':       NO_Z_EFFECT,
    'forests-curse':   {'stats': [(ALL_STATS, 1)]},
    'gastro-acid':     {'stats': [('speed', 1)]},
    'gear-up':         {'stats': [('special-attack', 1)]},
    'geomancy':        {'stats': [(ALL_STATS, 1)]},
    'glare':           {'stats': [('special-defense', 1)]},
    'grassy-terrain':  {'stats': [('defense', 1)]},
    'gravity':         {'stats': [('special-attack', 1)]},
    'growl':           {'stats': [('defense', 1)]},
    'growth':          {'stats': [('special-attack', 1)]},
    'grudge':          NO_Z_EFFECT,
    'guard-split':     {'stats': [('speed', 1)]},
    'guard-swap':      {'stats': [('speed', 1)]},
    'hail':            {'stats': [('speed', 1)]},
    'happy-hour':      {'stats': [(ALL_STATS, 1)]},
    'harden':          {'stats': [('defense', 1)]},
    'haze':            {'heal': True},
    'heal-bell':       {'heal': True},
    'heal-block':      {'stats': [('special-attack', 2)]},
    'heal-order':      {'reset': True},
    'heal-pulse':      {'reset': True},
    'healing-wish':    NO_Z_EFFECT,
    'heart-swap':      {'crit': 2},
    'helping-hand':    NO_Z_EFFECT,
    'hold-hands':      {'stats': [(ALL_STATS, 1)]},
    'hone-claws':      {'stats': [('attack', 1)]},
    'howl':            {'stats': [('attack', 1)]},
    'hypnosis':        {'stats': [('speed', 1)]},
    'imprison':        {'stats': [('special-defense', 2)]},
    'ingrain':         {'stats': [('special-defense', 1)]},
    'instruct':        {'stats': [('special-attack', 1)]},
    'ion-deluge':      {'stats': [('special-attack', 1)]},
    'iron-defense':    {'reset': True},
    'kinesis':         {'stats': [('evasion', 1)]},
    'kings-shield':    {'reset': True},
    'laser-focus':     {'stats': [('attack', 1)]},
    'leech-seed':      {'reset': True},
    'leer':            {'stats': [('attack', 1)]},
    'light-screen':    {'stats': [('special-defense', 1)]},
    'lock-on':         {'stats': [('speed', 1)]},
    'lovely-kiss':     {'stats': [('speed', 1)]},
    'lucky-chant':     {'stats': [('evasion', 1)]},
    'lunar-dance':     NO_Z_EFFECT,
    'magic-coat':      {'stats': [('special-defense', 2)]},
    'magic-room':      {'stats': [('special-defense', 1)]},
    'magnet-rise':     {'stats': [('evasion', 1)]},
    'magnetic-flux':   {'stats': [('special-defense', 1)]},
    'mat-block':       {'stats': [('defense', 1)]},
    'me-first':        {'stats': [('speed', 2)]},
    'mean-look':       {'stats': [('special-defense', 1)]},
    'memento':         {'replacement_heal': True},
    'metal-sound':     {'stats': [('special-attack', 1)]},
    'metronome':       NO_Z_EFFECT,
    'milk-drink':      {'reset': True},
    'mimic':           {'stats': [('accuracy', 1)]},
    'mind-reader':     {'stats': [('special-attack', 1)]},
    'minimize':        {'reset': True},
    'miracle-eye':     {'stats': [('special-attack', 1)]},
    'mirror-move':     {'stats': [('attack', 2)]},
    'misty-terrain':   {'stats': [('special-defense', 1)]},
    'moonlight':       {'reset': True},
    'morning-sun':     {'reset': True},
    'nasty-plot':      {'reset': True},
    'nature-power':    NO_Z_EFFECT,
    'noble-roar':      {'stats': [('defense', 1)]},
    'odor-sleuth':     {'stats': [('attack', 1)]},
    'pain-split':      {'stats': [('defense', 1)]},
    'parting-shot':    {'replacement_heal': True},
    'perish-song':     {'reset': True},
    'play-nice':       {'stats': [('defense', 1)]},
    'poison-gas':      {'stats': [('defense', 1)]},
    'poison-powder':   {'stats': [('defense', 1)]},
    'powder':          {'stats': [('special-defense', 2)]},
    'power-split':     {'stats': [('speed', 1)]},
    'power-swap':      {'stats': [('speed', 1)]},
    'power-trick':     {'stats': [('attack', 1)]},
    'protect':         {'reset': True},
    'psych-up':        {'heal': True},
    'psychic-terrain': {'stats': [('special-attack', 1)]},
    'psycho-shift':    {'stats': [('special-attack', 2)]},
    'purify':          {'stats': [(ALL_STATS, 1)]},
    'quash':           {'stats': [('speed', 1)]},
    'quick-guard':     {'stats': [('defense', 1)]},
    'quiver-dance':    {'reset': True},
    'rage-powder':     {'reset': True},
    'rain-dance':      {'stats': [('speed', 1)]},
    'recover':         {'reset': True},
    'recycle':         {'stats': [('speed', 2)]},
    'reflect':         {'stats': [('defense', 1)]},
    'reflect-type':    {'stats': [('special-attack', 1)]},
    'refresh':         {'heal': True},
    'rest':            {'reset': True},
    'roar':            {'stats': [('defense', 1)]},
    'rock-polish':     {'reset': True},
    'role-play':       {'stats': [('speed', 1)]},
    'roost':           {'reset': True},
    'rototiller':      {'stats': [('attack', 1)]},
    'safeguard':       {'stats': [('speed', 1)]},
    'sand-attack':     {'stats': [('evasion', 1)]},
    'sandstorm':       {'stats': [('speed', 1)]},
    'scary-face':      {'stats': [('speed', 1)]},
    'screech':         {'stats': [('attack', 1)]},
    'sharpen':         {'stats': [('attack', 1)]},
    'shell-smash':     {'reset': True},
    'shift-gear':      {'reset': True},
    'shore-up':        {'reset': True},
    'simple-beam':     {'stats': [('special-attack', 1)]},
    'sing':            {'stats': [('speed', 1)]},
    'sketch':          {'stats': [(ALL_STATS, 1)]},
    'skill-swap':      {'stats': [('speed', 1)]},
    'slack-off':       {'reset': True},
    'sleep-powder':    {'stats': [('speed', 1)]},
    'sleep-talk':      {'crit': 2},
    'smokescreen':     {'stats': [('evasion', 1)]},
    'snatch':          {'stats': [('speed', 2)]},
    'soak':            {'stats': [('special-attack', 1)]},
    'soft-boiled':     {'reset': True},
    'speed-swap':      {'stats': [('speed', 1)]},
    'spider-web':      {'stats': [('defense', 1)]},
    'spikes':          {'stats': [('defense', 1)]},
    'spiky-shield':    {'stats': [('defense', 1)]},
    'spite':           {'heal': True},
    'splash':          {'stats': [('attack', 3)]},
    'spore':           {'reset': True},
    'spotlight':       {'stats': [('special-defense', 1)]},
    'stealth-rock':    {'stats': [('defense', 1)]},
    'sticky-web':      {'stats': [('speed', 1)]},
    'stockpile':       {'heal': True},
    'strength-sap':    {'stats': [('defense', 1)]},
    'string-shot':     {'stats': [('speed', 1)]},
    'stun-spore':      {'stats': [('special-defense', 1)]},
    'substitute':      {'reset': True},
    'sunny-day':       {'stats': [('speed', 1)]},
    'supersonic':      {'stats': [('speed', 1)]},
    'swagger':         {'reset': True},
    'swallow':         {'reset': True},
    'sweet-scent':     {'stats': [('evasion', 1)]},
    'switcheroo':      {'stats': [('speed', 2)]},
    'swords-dance':    {'reset': True},
    'synthesis':       {'reset': True},
    'tail-glow':       {'reset': True},
    'tail-whip':       {'stats': [('attack', 1)]},
    'tailwind':        {'crit': 2},
    'taunt':           {'stats': [('attack', 1)]},
    'tearful-look':    {'stats': [('defense', 1)]},
    'teeter-dance':    {'stats': [('special-attack', 1)]},
    'telekinesis':     {'stats': [('special-attack', 1)]},
    'teleport':        {'heal': True},
    'thunder-wave':    {'stats': [('special-defense', 1)]},
    'tickle':          {'stats': [('defense', 1)]},
    'topsy-turvy':     {'stats': [('attack', 1)]},
    'torment':         {'stats': [('defense', 1)]},
    'toxic':           {'stats': [('defense', 1)]},
    'toxic-spikes':    {'stats': [('defense', 1)]},
    'toxic-thread':    {'stats': [('speed', 1)]},
    'transform':       {'heal': True},
    'trick':           {'stats': [('speed', 2)]},
    'trick-or-treat':  {'stats': [(ALL_STATS, 1)]},
    'trick-room':      {'stats': [('accuracy', 1)]},
    'venom-drench':    {'stats': [('defense', 1)]},
    'water-sport':     {'stats': [('special-defense', 1)]},
    'whirlwind':       {'stats': [('special-defense', 1)]},
    'wide-guard':      {'stats': [('defense', 1)]},
    'will-o-wisp':     {'stats': [('attack', 1)]},
    'wish':            {'stats': [('special-defense', 1)]},
    'withdraw':        {'stats': [('defense', 1)]},
    'wonder-room':     {'stats': [('special-defense', 1)]},
    'work-up':         {'stats': [('attack', 1)]},
    'worry-seed':      {'stats': [('speed', 1)]},
    'yawn':            {'stats': [('speed', 1)]},
}

# Nothing in this table means "no bonus", and that is now the honest default: Z-Moves are
# a Gen VII mechanic, so a status move introduced after them never had a Z-Power effect
# to have. This replaces a stand-in that reset the user's stages, which was the right
# guess to make while the real table was missing and the wrong one to keep once it
# arrived - Swords Dance really does reset stats, but Toxic really does raise Defense.
Z_STATUS_DEFAULT = NO_Z_EFFECT

# Destiny Bond's Z-effect draws in every attack aimed at the user's side for the turn.
# KyuDex is a singles game, so there is no ally to draw anything away from and the effect
# has nothing to do - the same ruling DOUBLES_ONLY_ABILITIES already gets. Named so the
# gap is a decision rather than a hole.
Z_REDIRECT_IS_INERT_IN_SINGLES = True

# The five stats ALL_STATS expands to in a Z-Power effect. Accuracy and evasion are named
# individually by the moves that raise them - Z-Smokescreen, Z-Defense Curl - and are
# deliberately not swept up by "raises every stat".
Z_BOOSTABLE_STATS = ('attack', 'defense', 'special-attack', 'special-defense', 'speed')


def z_status_effect_for(move_name):
    """
    The Z-Power effect a status move carries, which is never None.

    Callers apply this IN ADDITION to the move's own effect - a Z-Move does not replace
    the move it upgrades.
    """
    return Z_STATUS_EFFECTS.get(
        (move_name or '').lower().replace(' ', '-'), Z_STATUS_DEFAULT)


def expand_z_stats(stats):
    """Turn a Z-Power stat list into (stat, stages) pairs, unrolling ALL_STATS."""
    unrolled = []
    for stat, stages in stats or ():
        if stat == ALL_STATS:
            unrolled += [(s, stages) for s in Z_BOOSTABLE_STATS]
        else:
            unrolled.append((stat, stages))
    return unrolled


def signature_z_for(species_name, held_item, move_name):
    """
    The signature Z-Move this crystal grants this specimen for this move, or None.

    All three have to agree - the crystal, the species and the base move - which is what
    separates a Pikanium Z from a Pikashunium Z on the same Pikachu.
    """
    row = SIGNATURE_Z_CRYSTALS.get((held_item or 'none').lower().replace(' ', '-'))
    if not row:
        return None
    if (move_name or '').lower().replace(' ', '-') != row['move']:
        return None

    name = (species_name or '').lower().strip()
    base = name.split('-')[0].strip()
    wanted = row['species']
    wanted = (wanted,) if isinstance(wanted, str) else wanted
    return row if any(w == name or w == base for w in wanted) else None


# ==========================================
# 🔮 THE TERA SHARDS
# ==========================================
# Eighteen shards, and nothing to hook them to: Terastallization is not implemented, so
# unlike the Memories there is no generic path already quietly reading them. They are
# here as a NAMED, type-checked table rather than as shop rows, so that the phase that
# builds Terastallization inherits a vocabulary instead of eighteen string literals -
# and they are deliberately not in EQUIPMENT_CATALOG at all, because a row in the shop
# that a specimen cannot use is the ghost this whole audit exists to count.
TERA_SHARD_TYPES = {f'{element}-tera-shard': element for element in sorted(TYPE_CHART)}
assert len(TERA_SHARD_TYPES) == 18, (
    f"expected 18 Tera Shards, built {len(TERA_SHARD_TYPES)}")


# ==========================================
# 🧬 THE PHASE 8 SHELF
# ==========================================
# Three different answers to "can you buy this", each for a stated reason:
#
#   Mega Stones     NOT on sale - they arrive with the Mega Raids update
#   Tera Shards     not in the catalogue at all - nothing reads them yet
#   Z-Crystals      premium; a once-per-battle nuke, and the Z-Ring gating it is a key
#                   item that cannot be bought either
#   Memories        cheap, because they are Silvally's ONLY way to be anything but
#                   Normal and pricing that out is pricing out a team slot
MEGA_STONE_PRICE = 0            # see MEGA_STONES_ON_SALE below
Z_CRYSTAL_PRICE = 6000          # above a premium TM, below the Ability Patch
SIGNATURE_Z_PRICE = 9000        # species-locked, and stronger for it
MEMORY_PRICE = 600              # the type-booster shelf's price

MEGA_STONES_ON_SALE = False     # flip when Mega Raids lands


def build_phase8_stock():
    """
    The Phase 8 shelf: ninety-two stones, twenty-nine crystals and seventeen Memories.

    The assertion the other phases make - every implemented item has a row, every row has
    an implementation - is made here against the tables the ENGINE reads, so a stone that
    is spelled one way in `MEGA_STONE_SPECIES` and another in the shop cannot exist.

    Tera Shards are absent on purpose and are asserted absent, so that adding them later
    is a deliberate act rather than a copy-paste.
    """
    assert not (set(Z_CRYSTAL_TYPES) & set(SIGNATURE_Z_CRYSTALS)), (
        "a crystal cannot be both elemental and signature")
    assert not (set(MEGA_STONE_SPECIES) & set(Z_CRYSTAL_TYPES)), (
        "a Mega Stone cannot also be a Z-Crystal")

    shelf = {}

    for stone, species in sorted(MEGA_STONE_SPECIES.items()):
        shelf[stone] = {
            "name": stone.replace('-', ' ').title(),
            "price": MEGA_STONE_PRICE,
            "desc": f"Allows {species.replace('-', ' ').title()} to Mega Evolve.",
            "emoji": "🧬",
            "category": "megastone",
            "purchasable": MEGA_STONES_ON_SALE,
        }

    for crystal, element in sorted(Z_CRYSTAL_TYPES.items()):
        shelf[crystal] = {
            "name": crystal.replace('-z', ' Z').title().replace(' z', ' Z'),
            "price": Z_CRYSTAL_PRICE,
            "desc": f"Upgrades {element.title()}-type moves into "
                    f"{Z_MOVE_NAMES[element]}.",
            "emoji": type_icon(element),
            "category": "zcrystal",
        }

    for crystal, row in sorted(SIGNATURE_Z_CRYSTALS.items()):
        owners = row['species']
        owners = (owners,) if isinstance(owners, str) else owners
        # Hyphens kept rather than spaced out: 'kommo-o' reads as Kommo-O and not as
        # "Kommo O", and the regional and Forme names keep their shape too.
        who = ' / '.join(o.title() for o in owners)
        shelf[crystal] = {
            "name": crystal.replace('-z', ' Z').title().replace(' z', ' Z'),
            "price": SIGNATURE_Z_PRICE,
            "desc": f"Lets {who} upgrade "
                    f"{row['move'].replace('-', ' ').title()} into {row['name']}.",
            # Its own type's icon, the same as the eighteen elemental crystals. These all
            # wore one shared star before, which made a bag of seventeen unreadable.
            "emoji": type_icon(row['element']),
            "category": "zcrystal",
        }

    for memory, element in sorted(MEMORY_TYPES.items()):
        shelf[memory] = {
            "name": memory.replace('-', ' ').title(),
            "price": MEMORY_PRICE,
            "desc": f"Makes Silvally {element.title()}-type, and its Multi-Attack too.",
            "emoji": type_icon(element),
            "category": "formitems",
        }

    assert not (set(shelf) & set(TERA_SHARD_TYPES)), (
        "Tera Shards are inert and must stay out of the shop")
    return shelf


EQUIPMENT_CATALOG.update(build_phase8_stock())


# ==========================================
# 🏺 THE FORM SHELF
# ==========================================
# Every form item was priced 0 and unpurchaseable, which meant the only way to hold one
# was for an admin to hand it over. The eighteen Silvally Memories were the exception at
# 600 apiece, and they are the reason this table starts where it does: a Memory changes
# what Silvally IS, and nobody thought that needed locking away.
#
# Priced in one table rather than on seventeen rows because the rows are scattered - some
# are hand-written in EQUIPMENT_CATALOG, some arrive from a build_ function - and because
# a tier is a decision worth being able to read in one place.
#
# The ceiling before this was the Ability Patch at 12,000, with the Z-Crystals at 9,000.
#
#   RESHAPERS take a legendary somewhere it cannot otherwise go and KEEP it there -
#   Origin Dialga, Primal Groudon, Crowned Zacian, a fused Kyurem. Premium tier, above
#   anything else in the shop.
#
#   SWITCHERS move a specimen between forms it already has. Deoxys is still Deoxys. Dear,
#   but not the dearest thing on the shelf.
#
#   The Booster Energy is neither: it is a single-use battle consumable that happens to
#   live in this category, and pricing it like a Rusted Sword would be absurd.
FORM_RESHAPER_PRICE = 15000
FORM_SWITCHER_PRICE = 10000

FORM_ITEM_PRICES = {
    # Reshapers - fusions, Origin Formes, Primal Reversion, Crowned formes.
    'dna-splicers': FORM_RESHAPER_PRICE,
    'n-lunarizer': FORM_RESHAPER_PRICE,
    'n-solarizer': FORM_RESHAPER_PRICE,
    'reins-of-unity': FORM_RESHAPER_PRICE,
    'adamant-crystal': FORM_RESHAPER_PRICE,
    'lustrous-globe': FORM_RESHAPER_PRICE,
    'griseous-core': FORM_RESHAPER_PRICE,
    'red-orb': FORM_RESHAPER_PRICE,
    'blue-orb': FORM_RESHAPER_PRICE,
    'rusted-sword': FORM_RESHAPER_PRICE,
    'rusted-shield': FORM_RESHAPER_PRICE,
    # Switchers - the same specimen, wearing a different shape.
    'meteorite': FORM_SWITCHER_PRICE,
    'gracidea': FORM_SWITCHER_PRICE,
    'prison-bottle': FORM_SWITCHER_PRICE,
    'reveal-glass': FORM_SWITCHER_PRICE,
    'rotom-catalog': FORM_SWITCHER_PRICE,
    'zygarde-cube': FORM_SWITCHER_PRICE,
    # A single-use consumable that lives in this category by accident of what it does.
    'booster-energy': 800,
}


def stock_the_form_shelf():
    """
    Put every form item on sale, and refuse to let a new one arrive without a price.

    The assertion is the point. A form item added later with no row here would otherwise
    default to price 0 and `purchasable` unset - which reads as "free" to `!shop` and as
    a bug to everyone else.
    """
    listed = {key for key, entry in EQUIPMENT_CATALOG.items()
              if entry.get('category') == 'formitems'}
    unpriced = {key for key in listed
                if key not in FORM_ITEM_PRICES and not EQUIPMENT_CATALOG[key].get('price')}
    assert not unpriced, f"form items with no price: {sorted(unpriced)}"
    unknown = set(FORM_ITEM_PRICES) - listed
    assert not unknown, f"priced items that are not form items: {sorted(unknown)}"

    for key, price in FORM_ITEM_PRICES.items():
        EQUIPMENT_CATALOG[key]['price'] = price
        EQUIPMENT_CATALOG[key]['purchasable'] = True
    return len(FORM_ITEM_PRICES)


stock_the_form_shelf()


# ==========================================
# 🔎 WHAT THE PLAYER MEANT BY AN ITEM NAME
# ==========================================
# `!use` normalised what a player typed by deleting spaces AND hyphens - "DNA Splicers"
# became `dnasplicers` - and then looked that up in user_inventory, where item names are
# stored HYPHENATED. 72 of the 82 item names in the live inventory table carry a hyphen,
# so `!use` had never once worked for any of them. The only item it could find was the
# Purifier, which is one word, and the Purifier is the only thing its dispatcher handled.
#
# The rule is the one utils/species.py already uses for species: compare on letters and
# digits only, so "DNA Splicers", "dna splicers", "dna-splicers" and "dnasplicers" all
# agree - but keep the CANONICAL hyphenated key as the answer, because that is what the
# database is keyed on.
#
# Built on first use rather than at import: Phases 9 and 10 add to EQUIPMENT_CATALOG
# further down this file, and an index built here would have missed them.
_ITEM_KEYS_BY_NORMAL = {}


def normalise_item(text):
    """Letters and digits only - the form two item names are compared in."""
    return _re.sub(r'[^a-z0-9]', '', str(text or '').lower())


def resolve_item_key(text):
    """The catalogue key for what a player typed, or None."""
    if not _ITEM_KEYS_BY_NORMAL:
        for key, entry in EQUIPMENT_CATALOG.items():
            _ITEM_KEYS_BY_NORMAL.setdefault(normalise_item(key), key)
        # Display names too, so "Great Ball" reaches `greatball`. Added second and with
        # setdefault so a display name can never shadow a real key.
        for key, entry in EQUIPMENT_CATALOG.items():
            _ITEM_KEYS_BY_NORMAL.setdefault(normalise_item(entry.get('name')), key)
    return _ITEM_KEYS_BY_NORMAL.get(normalise_item(text))


# ==========================================
# 🧰 ITEM PHASE 9: THE UNPHASED SHELF, PART ONE
# ==========================================
# The forty-seven items that never fitted a phase, started at the end that shares hooks.
# These five split cleanly into three: two multiply damage, one changes what a specimen
# WEIGHS, and two argue with what the type chart is allowed to refuse.
#
# The two damage ones are worth naming, because they are the last of their kind: the
# Muscle Band and the Wise Glasses have been the only two entries on
# test_shop_catalog's KNOWN_GHOSTS list since Item Phase 5 cleared the rest. They were
# named in FLING_POWER and an NPC's item_pool - a weight and a rumour - and nothing read
# either as an effect. With these two live, the audit's ghost column reaches zero.

# A flat multiplier on one damage class, which is what separates these from the type
# boosters: a Muscle Band does not care what element the move is, only how it is thrown.
FLAT_DAMAGE_ITEMS = {
    'muscle-band':  'physical',
    'wise-glasses': 'special',
}
FLAT_DAMAGE_BOOST = 1.1

# What a specimen counts as weighing, for Grass Knot, Low Kick, Heat Crash and Heavy
# Slam. Read beside Heavy Metal and Light Metal, which is the same question asked of an
# ability instead of an item.
WEIGHT_ITEMS = {'float-stone': 0.5}

# Iron Ball drags its holder down to the field: half Speed, and Ground-type moves reach
# it even through a Flying type or Levitate. The grounding half is the interesting one,
# because `is_grounded` is also what hazards and terrain read - so an Iron Ball holder
# eats Spikes and stands in a Grassy Terrain too, exactly as it should.
IRON_BALL = 'iron-ball'
IRON_BALL_SPEED = 0.5

# Items that pull a specimen onto the ground it would otherwise be floating above.
GROUNDING_ITEMS = {IRON_BALL}

# ...and the two ways a held item lets the chart's zeroes through. They are NOT the same
# rule, which is why this is a mapping rather than a set:
#
#   ring-target  every immunity the holder has, whatever the element
#   iron-ball    Ground only - it grounds its holder, it does not make a Gengar
#                vulnerable to Normal moves
#
# The value is the elements the item opens up, or ALL_STATS' cousin `None` for "all".
IMMUNITY_PIERCING_ITEMS = {
    'ring-target': None,
    IRON_BALL:     ('ground',),
}


def pierces_own_immunity(held_item, move_type):
    """
    Whether the DEFENDER's held item lets a move through an immunity it would refuse.

    Asked at the one place the type chart produces a zero, so Ring Target and the Iron
    Ball cannot disagree with each other about what an immunity is.
    """
    opens = IMMUNITY_PIERCING_ITEMS.get(
        (held_item or 'none').lower().replace(' ', '-'), False)
    if opens is False:
        return False
    return opens is None or (move_type or '').lower() in opens


PHASE9_PRICE = 400
PHASE9_SET_PRICE = 600      # the two that define a set rather than answering a matchup

PHASE9_DESCRIPTIONS = {
    'muscle-band':   ("Physical moves from the holder do 10% more damage.",
                      PHASE9_SET_PRICE, '🎽'),
    'wise-glasses':  ("Special moves from the holder do 10% more damage.",
                      PHASE9_SET_PRICE, '👓'),
    'float-stone':   ("Halves the holder's weight, against Grass Knot and Low Kick.",
                      PHASE9_PRICE, '🪶'),
    'iron-ball':     ("Halves the holder's Speed and drags it to the ground, where "
                      "Ground moves and hazards can reach it.", PHASE9_PRICE, '🔗'),
    'ring-target':   ("The holder loses its own type immunities.",
                      PHASE9_PRICE, '🎯'),
}


def build_phase9_stock():
    """
    The Phase 9 shelf, checked against the tables the engine reads.

    Same assertion the other phases make, in both directions. The Iron Ball is
    deliberately in two of the source tables - it grounds AND it pierces - and must
    still appear exactly once on the shelf.
    """
    implemented = (set(FLAT_DAMAGE_ITEMS) | set(WEIGHT_ITEMS) | set(GROUNDING_ITEMS)
                   | set(IMMUNITY_PIERCING_ITEMS))
    missing = implemented - set(PHASE9_DESCRIPTIONS)
    assert not missing, f"Phase 9 items with no shop entry: {sorted(missing)}"
    extra = set(PHASE9_DESCRIPTIONS) - implemented
    assert not extra, f"Phase 9 shop entries with no implementation: {sorted(extra)}"

    return {
        item: {
            "name": item.replace('-', ' ').title(),
            "price": PHASE9_DESCRIPTIONS[item][1],
            "desc": PHASE9_DESCRIPTIONS[item][0],
            "emoji": PHASE9_DESCRIPTIONS[item][2],
            "category": "battleitems",
        }
        for item in sorted(implemented)
    }


EQUIPMENT_CATALOG.update(build_phase9_stock())


def build_phase10_stock():
    """
    The Phase 10 shelf: Ogerpon's three masks and the Adrenaline Orb.

    The masks are checked against BOTH species tables, because a mask that reshaped its
    holder without lifting its damage - or the other way round - would be a half-item,
    and half-items are exactly what the audit's "it cannot see a HALF-implemented item"
    caveat says a name-scan will never catch.
    """
    masks = {m for m in PHASE10_DESCRIPTIONS if m.endswith('-mask')}
    assert masks <= set(SPECIES_FORM_ITEMS), (
        f"masks with no form: {sorted(masks - set(SPECIES_FORM_ITEMS))}")
    assert masks <= set(SPECIES_TYPE_BOOST_ITEMS), (
        f"masks with no damage boost: {sorted(masks - set(SPECIES_TYPE_BOOST_ITEMS))}")
    # The orb is SPENT when it fires, which ONE_USE_ITEMS records - but that set lives in
    # formulas.py, which imports this file rather than the reverse. Pinned in the suite
    # instead, where both halves can be seen at once.

    return {
        item: {
            "name": item.replace('-', ' ').title(),
            "price": PHASE10_DESCRIPTIONS[item][1],
            "desc": PHASE10_DESCRIPTIONS[item][0],
            "emoji": PHASE10_DESCRIPTIONS[item][2],
            "category": "battleitems",
        }
        for item in sorted(PHASE10_DESCRIPTIONS)
    }


EQUIPMENT_CATALOG.update(build_phase10_stock())


# ==========================================
# 🎒 ITEM PHASE 11: THE BAG, AND THE FOUR HELD ITEMS THAT NEEDED A HOOK
# ==========================================
# The audit excluded nine items on the grounds that "KyuDex has no in-battle bag". That
# was simply wrong: BattleDashboard.open_bag, ItemSelect and use_item_callback have been
# there the whole time, wired to a button, spending real inventory. What the bag had was
# not an absence but a CLOSED LIST - one hard-coded tuple of seven medical items in the
# query, a second copy of the same seven in the dropdown's descriptions, and a third as
# an if/elif chain in the callback. Three lists that had to be edited together to add one
# item, which is why nobody ever did.
#
# So the bag becomes a table, the way every other shelf here already is. One row per item
# drives the inventory query, the dropdown, the validation and the effect, and adding an
# item is a row rather than three edits in three places that can drift apart.

# --- The two held items -------------------------------------------------------------
STICKY_BARB = 'sticky-barb'
STICKY_BARB_DIVISOR = 8      # of max HP, to the holder, every turn

UTILITY_UMBRELLA = 'utility-umbrella'
# The two ORDINARY skies. A primordial sky is deliberately left alone, for the same
# reason personal_weather leaves it alone: those three are the ones an ordinary weather
# setter is already refused, and an umbrella does not get to do what a setter cannot.
SHELTERED_SKIES = frozenset({'sun', 'rain'})

DESTINY_KNOT = 'destiny-knot'

# --- The end-of-turn item payout ----------------------------------------------------
# Leftovers and Black Sludge were written out TWICE - once in the PvE turn-end and once
# in the PvP one, byte-identical apart from a comment. Adding the Sticky Barb would have
# made a third copy of each. The duplication is not hypothetically dangerous either: the
# grounding check next door was duplicated the same way, the two copies drifted, and an
# Air Balloon silently stopped lifting its holder over Spikes for as long as that lasted.
#
#   heal        - divisor of max HP restored, but only when HP is actually missing
#   hurt        - divisor of max HP taken, whatever the current HP
#   heal_types  - present means the row is CONDITIONAL: hold one of these elements and
#                 the row heals, hold none and it hurts instead. Black Sludge's rule.
END_OF_TURN_ITEMS = {
    'leftovers':    {'heal': 16, 'emoji': '🍎',
                     'heal_msg': "restored a little HP using its Leftovers!"},
    'black-sludge': {'heal': 16, 'hurt': 8, 'heal_types': ('poison',), 'emoji': '🧪',
                     'heal_msg': "restored HP via its Black Sludge!",
                     'hurt_msg': "is buffeted by its Black Sludge!"},
    STICKY_BARB:    {'hurt': STICKY_BARB_DIVISOR, 'emoji': '🌵',
                     'hurt_msg': "was pricked by its Sticky Barb!"},
}

# --- The bag ------------------------------------------------------------------------
# `kind` picks the effect, and every kind is answered by machinery that ALREADY EXISTS
# rather than by a new one:
#
#   heal      - amount in HP, or ALL_STATS' cousin None for "all of it"
#   cure      - clears the major status and confusion
#   revive    - a fainted specimen only, back at half
#   stages    - enqueued through resolve_stat_stages, so an X Attack meets Clear Body,
#               Mirror Armor, Defiant and Opportunist exactly as Swords Dance does
#   crit      - the `focus_energy` volatile, which is what Focus Energy, a Lansat Berry
#               and Z-Focus Energy all already set
#   side      - a timed side condition. Guard Spec is Mist, which SIDE_SCREEN_MOVES has
#               carried and side_is_guarded has read since long before this phase
#
# `needs` is the validation: an item that cannot do anything is refused BEFORE it is
# spent, because the bag costs a turn and a wasted turn is worse than a wasted item.
BATTLE_BAG_ITEMS = {
    'potion':        {'kind': 'heal', 'amount': 20, 'needs': 'hurt', 'emoji': '💊',
                      'desc': 'Restores 20 HP.',
                      'log': "💊 You sprayed a Potion! **{name}** recovered HP."},
    'super-potion':  {'kind': 'heal', 'amount': 50, 'needs': 'hurt', 'emoji': '🧪',
                      'desc': 'Restores 50 HP.',
                      'log': "🧪 You deployed a Super Potion! **{name}** recovered HP."},
    'hyper-potion':  {'kind': 'heal', 'amount': 200, 'needs': 'hurt', 'emoji': '🧴',
                      'desc': 'Restores 200 HP.',
                      'log': "🧴 You deployed a Hyper Potion! **{name}** recovered HP."},
    'max-potion':    {'kind': 'heal', 'amount': None, 'needs': 'hurt', 'emoji': '💖',
                      'desc': 'Restores all HP.',
                      'log': "💖 You deployed a Max Potion! **{name}**'s HP was fully "
                             "restored."},
    'full-heal':     {'kind': 'cure', 'needs': 'status', 'emoji': '🌿',
                      'desc': 'Cures all status conditions.',
                      'log': "🌿 You used a Full Heal! **{name}** was cured of all "
                             "ailments."},
    'full-restore':  {'kind': 'heal', 'amount': None, 'cure': True,
                      'needs': 'hurt_or_status', 'emoji': '🌟',
                      'desc': 'Restores all HP and cures status.',
                      'log': "🌟 You used a Full Restore! **{name}** is fully healed "
                             "and cured."},
    'revive':        {'kind': 'revive', 'needs': 'fainted', 'emoji': '👼',
                      'desc': 'Revives a fainted specimen to 50% HP.',
                      'log': "👼 You used a Revive! **{name}** was resuscitated."},

    'x-attack':      {'kind': 'stages', 'stats': {'attack': 1}, 'emoji': '⚔️',
                      'desc': 'Raises Attack by one stage.',
                      'log': "⚔️ You applied an X Attack to **{name}**!"},
    'x-defense':     {'kind': 'stages', 'stats': {'defense': 1}, 'emoji': '🛡️',
                      'desc': 'Raises Defense by one stage.',
                      'log': "🛡️ You applied an X Defense to **{name}**!"},
    'x-sp-atk':      {'kind': 'stages', 'stats': {'special-attack': 1}, 'emoji': '🔮',
                      'desc': 'Raises Sp. Atk by one stage.',
                      'log': "🔮 You applied an X Sp. Atk to **{name}**!"},
    'x-sp-def':      {'kind': 'stages', 'stats': {'special-defense': 1}, 'emoji': '🔰',
                      'desc': 'Raises Sp. Def by one stage.',
                      'log': "🔰 You applied an X Sp. Def to **{name}**!"},
    'x-speed':       {'kind': 'stages', 'stats': {'speed': 1}, 'emoji': '💨',
                      'desc': 'Raises Speed by one stage.',
                      'log': "💨 You applied an X Speed to **{name}**!"},
    'x-accuracy':    {'kind': 'stages', 'stats': {'accuracy': 1}, 'emoji': '🎯',
                      'desc': 'Raises accuracy by one stage.',
                      'log': "🎯 You applied an X Accuracy to **{name}**!"},
    'dire-hit':      {'kind': 'crit', 'needs': 'not_focused', 'emoji': '🥊',
                      'desc': 'Raises the critical hit ratio.',
                      'log': "🥊 You used a Dire Hit! **{name}** is fired up - its "
                             "critical hit ratio rose!"},
    'guard-spec':    {'kind': 'side', 'condition': 'mist', 'turns': 5,
                      'needs': 'no_mist', 'emoji': '🌫️',
                      'desc': 'A white mist stops your stats being lowered, 5 turns.',
                      'log': "🌫️ You used a Guard Spec! A white mist stopped your "
                             "team losing any stats."},
}

# The bag is a PvE fixture: open_bag hangs off BattleDashboard, which is the PvE view,
# and the PvP resolver has no equivalent. So the eight battle items below are honestly
# labelled PvE-only in the shop rather than sold as though they worked everywhere.
BAG_MEDICAL_KINDS = frozenset({'heal', 'cure', 'revive'})
BATTLE_BAG_MEDICAL = frozenset(
    k for k, v in BATTLE_BAG_ITEMS.items() if v['kind'] in BAG_MEDICAL_KINDS)
BATTLE_BAG_PVE_ONLY = frozenset(BATTLE_BAG_ITEMS) - BATTLE_BAG_MEDICAL

# --- Max Soup -----------------------------------------------------------------------
# Max Mushrooms do not act on their own. They are the MATERIAL for Max Soup, which is
# refined at the lab beside the Mega Bracelet and the Z-Ring, and the soup is what a
# specimen is actually fed. Two steps rather than one because a species either has a
# Gigantamax form or it does not, and the check belongs at the bowl rather than at the
# shop counter - the mushrooms are worth buying before you have decided who eats them.
MAX_MUSHROOMS = 'max-mushrooms'
MAX_SOUP = 'max-soup'
MAX_SOUP_MUSHROOMS = 3
MAX_SOUP_COST = 2000        # lab time, on top of the mushrooms

# --- Prices -------------------------------------------------------------------------
PHASE11_HELD_PRICE = 400    # the two held items: affordable, meant to be experimented with
BAG_ITEM_PRICE = 300        # spent every time they are used, so cheaper again
# Premium, deliberately. A Destiny Knot's real job is passing IVs down, and that belongs
# to a breeding update that does not exist yet - pricing it as an ordinary battle item now
# would make it worthless later.
DESTINY_KNOT_PRICE = 8000
# Premium in aggregate rather than per mushroom: three of them plus the lab's fee is
# 11,000, which is Gigantamax access and should feel like it.
MAX_MUSHROOMS_PRICE = 3000

PHASE11_DESCRIPTIONS = {
    STICKY_BARB:      ("Pricks the holder for 1/8 its HP each turn, and sticks to any "
                       "empty-handed attacker that touches it.",
                       PHASE11_HELD_PRICE, 'battleitems', '🌵'),
    UTILITY_UMBRELLA: ("Shelters the holder from rain and harsh sunlight.",
                       PHASE11_HELD_PRICE, 'battleitems', '☂️'),
    DESTINY_KNOT:     ("If the holder is infatuated, whoever charmed it falls in love "
                       "right back.", DESTINY_KNOT_PRICE, 'battleitems', '💞'),
    MAX_MUSHROOMS:    (f"Raw material for Max Soup. Refine {MAX_SOUP_MUSHROOMS} of them "
                       f"at the lab with `!refine max soup`.",
                       MAX_MUSHROOMS_PRICE, 'general', '🍄'),
}

# The five medical items the bag has always been able to USE but the shop never sold.
# Scaled off the two that were already priced: a Potion is 100 for 20 HP, a Revive 250.
PHASE11_MEDICAL = {
    'super-potion': ("Restores 50 HP to one specimen.", 300, '🧪'),
    'hyper-potion': ("Restores 200 HP to one specimen.", 900, '🧴'),
    'max-potion':   ("Fully restores one specimen's HP.", 1500, '💖'),
    'full-heal':    ("Cures every status condition.", 300, '🌿'),
    'full-restore': ("Fully restores HP and cures every status condition.", 2500, '🌟'),
}


def build_phase11_stock():
    """
    The Phase 11 shelf: two held items, the Destiny Knot, the mushrooms, the bag.

    Three assertions, because this phase is the one where a shop entry and an
    implementation can most easily part company:

      - every bag row that is not medical must be for sale, or it can never be bought
      - every bag row must be reachable by the effect resolver, which is what `kind`
        names, so a typo in `kind` is caught here rather than at the dropdown
      - Max Soup itself is NOT on the shelf. It is refined, like the Mega Bracelet and
        the Z-Ring, and a soup that could simply be bought would make the mushrooms
        pointless.
    """
    known_kinds = {'heal', 'cure', 'revive', 'stages', 'crit', 'side'}
    unknown = {k: v['kind'] for k, v in BATTLE_BAG_ITEMS.items()
               if v['kind'] not in known_kinds}
    assert not unknown, f"bag rows with an unreachable kind: {unknown}"

    assert MAX_SOUP not in PHASE11_DESCRIPTIONS, "Max Soup is refined, not sold"

    stock = {
        item: {
            "name": item.replace('-', ' ').title(),
            "price": PHASE11_DESCRIPTIONS[item][1],
            "desc": PHASE11_DESCRIPTIONS[item][0],
            "emoji": PHASE11_DESCRIPTIONS[item][3],
            "category": PHASE11_DESCRIPTIONS[item][2],
        }
        for item in sorted(PHASE11_DESCRIPTIONS)
    }

    for item in sorted(PHASE11_MEDICAL):
        desc, price, emoji = PHASE11_MEDICAL[item]
        stock[item] = {"name": item.replace('-', ' ').title(), "price": price,
                       "desc": desc, "emoji": emoji, "category": "medicine"}

    for item in sorted(BATTLE_BAG_PVE_ONLY):
        row = BATTLE_BAG_ITEMS[item]
        stock[item] = {
            "name": item.replace('-', ' ').title(),
            "price": BAG_ITEM_PRICE,
            "desc": f"{row['desc']} Used from the battle bag; PvE only.",
            "emoji": row['emoji'],
            "category": "battleitems",
        }

    unbuyable = set(BATTLE_BAG_ITEMS) - set(stock) - set(EQUIPMENT_CATALOG)
    assert not unbuyable, f"bag items nobody can buy: {sorted(unbuyable)}"
    return stock


EQUIPMENT_CATALOG.update(build_phase11_stock())


# ==========================================
# 🧬 THE EVOLUTION SHELF
# ==========================================
# `evolution_rules` names 19 items you USE and 11 you HOLD. Three of the thirty were on
# sale. So most of this bot's item-gated evolutions were gated on something nobody could
# obtain - which nobody noticed, because the code never checked the requirement either:
# the trade path read `item_name`, that column is NULL for every trade evolution, and a
# Scyther therefore became a Scizor on any trade at all.
#
# Making the engine enforce the requirement without also selling the items would trade a
# too-lax evolution for an impossible one, so the two go together or neither is a fix.
#
# Priced off the three stones that were already here at 500. The held items are cheaper,
# at 450, because they are also ordinary battle equipment - a Metal Coat and a King's Rock
# already sat on the battle shelf at 400 and 350 and keep those prices; only the ones that
# were missing entirely are added here.
EVOLUTION_STONE_PRICE = 500
EVOLUTION_HELD_PRICE = 450

EVOLUTION_SHOP_ITEMS = {
    # The stones a trainer USES, in `!evolve <stone> <specimen>`.
    'thunder-stone':    ("Evolves certain Electric species.", EVOLUTION_STONE_PRICE, '💎'),
    'moon-stone':       ("Evolves certain Normal, Fairy and Poison species.",
                         EVOLUTION_STONE_PRICE, '🌙'),
    'sun-stone':        ("Evolves certain Grass, Rock and Psychic species.",
                         EVOLUTION_STONE_PRICE, '☀️'),
    'dusk-stone':       ("Evolves certain Dark and Ghost species.",
                         EVOLUTION_STONE_PRICE, '🌑'),
    'shiny-stone':      ("Evolves certain Fairy and Grass species.",
                         EVOLUTION_STONE_PRICE, '✨'),
    'dawn-stone':       ("Evolves Kirlia and Snorunt, and only one gender of each.",
                         EVOLUTION_STONE_PRICE, '🌅'),
    'ice-stone':        ("Evolves certain Ice species.", EVOLUTION_STONE_PRICE, '🧊'),
    'black-augurite':   ("A dark stone that reshapes a Scyther.",
                         EVOLUTION_STONE_PRICE, '🪨'),
    'peat-block':       ("Dense bog soil that reshapes a Ursaluna.",
                         EVOLUTION_STONE_PRICE, '🟤'),
    'malicious-armor':  ("Cursed plating that reshapes a Charcadet.",
                         EVOLUTION_STONE_PRICE, '🩸'),
    'auspicious-armor': ("Blessed plating that reshapes a Charcadet.",
                         EVOLUTION_STONE_PRICE, '🛡️'),
    'sweet-apple':      ("An apple that reshapes an Applin.", EVOLUTION_STONE_PRICE, '🍏'),
    'tart-apple':       ("A sour apple that reshapes an Applin.",
                         EVOLUTION_STONE_PRICE, '🍎'),
    'cracked-pot':      ("A chipped teapot that reshapes a Sinistea.",
                         EVOLUTION_STONE_PRICE, '🫖'),
    'galarica-cuff':    ("A Galarian bangle that reshapes a Slowpoke.",
                         EVOLUTION_STONE_PRICE, '💍'),
    'galarica-wreath':  ("A Galarian garland that reshapes a Slowpoke.",
                         EVOLUTION_STONE_PRICE, '🌿'),
    # Kubfu's two scrolls, which arrived with the regional-form rules. Worth having on the
    # shelf for their own sake: they are the ONLY route to either Urshifu that this world
    # can stage, since the two Towers of Trials it would otherwise need do not exist here.
    'scroll-of-waters': ("Kubfu reads it and becomes Rapid Strike Urshifu.",
                         EVOLUTION_STONE_PRICE, '📜'),
    'scroll-of-darkness': ("Kubfu reads it and becomes Single Strike Urshifu.",
                           EVOLUTION_STONE_PRICE, '🌘'),

    # The items a specimen HOLDS. These are what the migration added a column for.
    'dragon-scale':     ("Held: a Seadra that is traded holding this becomes a Kingdra.",
                         EVOLUTION_HELD_PRICE, '🐉'),
    'up-grade':         ("Held: a Porygon that is traded holding this becomes a Porygon2.",
                         EVOLUTION_HELD_PRICE, '💾'),
    'dubious-disc':     ("Held: a Porygon2 that is traded holding this becomes a "
                         "Porygon-Z.", EVOLUTION_HELD_PRICE, '💿'),
    'protector':        ("Held: a Rhydon that is traded holding this becomes a Rhyperior.",
                         EVOLUTION_HELD_PRICE, '🦺'),
    'electirizer':      ("Held: an Electabuzz that is traded holding this becomes an "
                         "Electivire.", EVOLUTION_HELD_PRICE, '🔌'),
    'magmarizer':       ("Held: a Magmar that is traded holding this becomes a Magmortar.",
                         EVOLUTION_HELD_PRICE, '🔥'),
    'reaper-cloth':     ("Held: a Dusclops that is traded holding this becomes a Dusknoir.",
                         EVOLUTION_HELD_PRICE, '👘'),
    'prism-scale':      ("Held: a Feebas that is traded holding this becomes a Milotic.",
                         EVOLUTION_HELD_PRICE, '🌈'),
    'oval-stone':       ("Held: a Happiny that levels up in the day becomes a Chansey.",
                         EVOLUTION_HELD_PRICE, '🥚'),
    'sachet':           ("Held: a Spritzee that is traded holding this becomes an "
                         "Aromatisse.", EVOLUTION_HELD_PRICE, '💐'),
    'whipped-dream':    ("Held: a Swirlix that is traded holding this becomes a Slurpuff.",
                         EVOLUTION_HELD_PRICE, '🍰'),
}


def build_evolution_stock():
    """
    The evolution shelf, checked against the rulebook it exists to serve.

    The assertion runs the other way from the item phases': rather than proving every
    shelf entry has an implementation, it proves every entry is an item some evolution
    RULE actually names. An evolution item that evolves nothing is a trap - a player
    spends 500 on it and finds out afterwards.

    Read straight out of `evolution_rules` at import, the same way UNEVOLVED_SPECIES and
    the body-mass index already are, so it cannot drift from the table.
    """
    named = set()
    try:
        import sqlite3 as _sqlite3
        _conn = _sqlite3.connect(f'file:{DB_FILE}?mode=ro', uri=True)
        try:
            for column in ('item_name', 'held_item'):
                try:
                    named.update(
                        row[0] for row in _conn.execute(
                            f"SELECT DISTINCT {column} FROM evolution_rules "
                            f"WHERE {column} IS NOT NULL"))
                except _sqlite3.OperationalError:
                    # `held_item` predates its own migration on a database that has not
                    # been migrated yet. The shelf still stands; it is simply not checked
                    # against a column that is not there.
                    pass
        finally:
            _conn.close()
    except Exception:
        named = set(EVOLUTION_SHOP_ITEMS)      # no database to hand: trust the table

    if named:
        useless = set(EVOLUTION_SHOP_ITEMS) - named
        assert not useless, f"evolution items that evolve nothing: {sorted(useless)}"

    return {
        item: {
            "name": item.replace('-', ' ').title(),
            "price": EVOLUTION_SHOP_ITEMS[item][1],
            "desc": EVOLUTION_SHOP_ITEMS[item][0],
            "emoji": EVOLUTION_SHOP_ITEMS[item][2],
            "category": "evoitems",
        }
        for item in sorted(EVOLUTION_SHOP_ITEMS)
    }


EQUIPMENT_CATALOG.update(build_evolution_stock())


# The sky, for the evolutions that care. There is no in-world clock here, so the real one
# is the honest source: a Sneasel becomes a Weavile in YOUR evening. UTC rather than local
# time so two trainers in different timezones see the same sky, which is the same choice
# the daily expedition counter already makes.
#
# `evolution_rules.time_of_day` holds FOUR values, not two - 'day', 'night', 'dusk' and
# 'full-moon' - and the last two are not alternatives to the first two, they are moments
# INSIDE them. Rockruff wants dusk, which is also day; Ursaring wants a full moon, which
# is also night. So the answer is a set rather than a string, and a rule matches when the
# sky it names is in it.
#
# This mattered the moment time_of_day started being enforced at all. Before that nothing
# read the column, so Lycanroc-Dusk and Ursaluna were reachable by accident; checking only
# 'day' and 'night' would have made them unreachable on purpose, which is worse.
NIGHT_BEGINS_HOUR = 18
DAY_BEGINS_HOUR = 6
DUSK_HOUR = 17                  # the hour before night, when Rockruff can turn
FULL_MOON_WINDOW = 1.5          # days either side of the exact full moon

# The two skies that sit INSIDE another one. A rule naming one of these is more
# specific than a rule naming plain day or night, and the rulebook prefers it when
# both match - otherwise Rockruff's three level-25 rules would always resolve to the
# day one and Lycanroc-Dusk could never be reached.
SPECIAL_SKIES = frozenset({'dusk', 'full-moon'})

# ==========================================
# 🩸 EVOLUTIONS THAT ARE EARNED, NOT REACHED
# ==========================================
# Some evolutions are triggered by something that HAPPENS rather than by a level, an item
# or a clock. Two of them are conditions this engine already watches and simply never
# wrote down:
#
#   take-damage          Galarian Yamask becomes a Runerigus after surviving a single
#                        blow of 49 or more. In the games you then walk under a stone
#                        arch; there is no overworld here, so surviving the hit IS the
#                        story and the arch is the part that gets left out.
#   three-critical-hits  Galarian Farfetch'd becomes a Sirfetch'd after landing three
#                        criticals in one battle.
#
# `column` is the counter on caught_pokemon, `threshold` the figure it must reach, and
# `per_battle` says whether the counter resets when a new battle starts - a Sirfetch'd
# wants three criticals in ONE battle, while Runerigus only cares about the hardest hit
# its Yamask has ever taken.
CONDITION_TRIGGERS = {
    'take-damage': {
        'column': 'biggest_hit_taken', 'threshold': 49, 'per_battle': False,
        'flavour': "endured a devastating blow and its spirit reshaped the clay",
    },
    'three-critical-hits': {
        'column': 'crits_landed_battle', 'threshold': 3, 'per_battle': True,
        'flavour': "struck three times with lethal precision and stood taller for it",
    },
}

# The triggers left over: things this world has no equivalent of at all. Legends Arceus'
# Strong Style, the Isle of Armor's two Towers, Basculin's recoil swim. Rather than
# pretending to model them, a specimen whose only route is one of these can be pushed
# through it by hand once it is experienced enough - `!evolve <specimen> ritual`.
#
# The level is a stand-in, and is named here rather than buried so it reads as the
# deliberate substitution it is.
RITUAL_TRIGGERS = frozenset({
    'strong-style-move', 'agile-style-move', 'use-move', 'tower-of-waters',
    'tower-of-darkness', 'recoil-damage', 'spin', 'shed', 'three-defeated-bisharp',
    'gimmmighoul-coins', 'other',
})
RITUAL_MIN_LEVEL = 40
RITUAL_KEYWORD = 'ritual'


# ==========================================
# ⏳ WALKING AWAY FROM A BATTLE
# ==========================================
# A battle lives in `cog.active_battles`, keyed by trainer. The dashboard View had a
# 300-second timeout and NO on_timeout, so the buttons went dead while the entry stayed in
# the dictionary for ever - and the trainer was told "you are already in an expedition"
# with nothing on screen to leave. The only way out was a `!forfeit` on a message whose
# buttons no longer worked.
#
# PvP was worse: its dashboard was `timeout=None`, so it never expired at all, and the
# state is SHARED between both players - one person closing Discord locked out two.
#
# Ten minutes, which is long enough to think and short enough that a duel abandoned at
# lunchtime is not still holding two accounts hostage at dinner. Each interaction resets
# it, because discord.py restarts a View's timer whenever the View is used.
BATTLE_IDLE_TIMEOUT = 600


# ==========================================
# 🌱 NATURE MINTS
# ==========================================
# Built from NATURE_MULTIPLIERS rather than typed out, so a nature cannot exist without a
# mint or the other way round. The five NEUTRAL natures - the ones whose row is (None,
# None) - deliberately share one mint: there is no reason to sell five different items
# that all do exactly the same nothing, and the games make the same choice.
#
# Premium price, and for the same reason the Destiny Knot is: a mint rewrites the stat
# spread a specimen was born with, which is most of what breeding is FOR. Priced as an
# ordinary consumable now, it would make a later breeding update pointless before it
# shipped.
NATURE_MINT_PRICE = 7500
NEUTRAL_MINT = 'serious-mint'

NATURE_MINTS = {
    f'{nature}-mint': nature
    for nature, (raised, _lowered) in sorted(NATURE_MULTIPLIERS.items())
    if raised is not None
}
NATURE_MINTS[NEUTRAL_MINT] = 'serious'

# The natures a Serious Mint stands in for - every one that raises nothing.
NEUTRAL_NATURES = frozenset(
    nature for nature, (raised, _l) in NATURE_MULTIPLIERS.items() if raised is None)


def mint_for(nature):
    """The mint that grants `nature`, collapsing the five neutral ones onto Serious."""
    nature = (nature or '').strip().lower()
    if nature in NEUTRAL_NATURES:
        return NEUTRAL_MINT
    return f'{nature}-mint' if nature in NATURE_MULTIPLIERS else None


def build_mint_stock():
    """
    The mint shelf, checked against the nature table it is derived from.

    The assertion is the point: every nature a specimen can be BORN with must be
    reachable by a mint, or the shelf is a trap - a player looks for the one they need
    and it is not there.
    """
    covered = set()
    for mint, nature in NATURE_MINTS.items():
        covered.add(nature)
    missing = set(NATURE_MULTIPLIERS) - covered - NEUTRAL_NATURES
    assert not missing, f"natures with no mint: {sorted(missing)}"

    stock = {}
    for mint, nature in sorted(NATURE_MINTS.items()):
        raised, lowered = NATURE_MULTIPLIERS[nature]
        if raised is None:
            desc = ("Rewrites a specimen's nature to Serious - no stat raised, none "
                    "lowered. Stands in for every neutral nature.")
        else:
            desc = (f"Rewrites a specimen's nature to {nature.title()}: "
                    f"+{raised.replace('-', ' ').title()}, "
                    f"-{lowered.replace('-', ' ').title()}.")
        stock[mint] = {
            "name": mint.replace('-', ' ').title(),
            "price": NATURE_MINT_PRICE,
            "desc": desc,
            "emoji": '🌱',
            "category": "mints",
        }
    return stock


EQUIPMENT_CATALOG.update(build_mint_stock())

# A known new moon, and the mean synodic month. Good to a few hours over a century, which
# is far better than this needs to be.
_NEW_MOON_EPOCH = 1136073600    # 2006-01-01 00:00 UTC, near a new moon
_SYNODIC_MONTH = 29.530588853 * 86400


def is_full_moon(now=None):
    """Whether the moon is full, to within a day and a half either side."""
    import datetime as _datetime
    when = now or _datetime.datetime.now(_datetime.timezone.utc)
    age = ((when.timestamp() - _NEW_MOON_EPOCH) % _SYNODIC_MONTH) / 86400.0
    return abs(age - (_SYNODIC_MONTH / 86400.0) / 2) <= FULL_MOON_WINDOW


def current_skies(now=None):
    """
    Every sky-name true right now, as a frozenset of the strings the table uses.

    Always contains exactly one of 'day' or 'night', and may also contain 'dusk' or
    'full-moon' when those moments are inside it.
    """
    import datetime as _datetime
    when = now or _datetime.datetime.now(_datetime.timezone.utc)
    skies = set()
    if DAY_BEGINS_HOUR <= when.hour < NIGHT_BEGINS_HOUR:
        skies.add('day')
        if when.hour == DUSK_HOUR:
            skies.add('dusk')
    else:
        skies.add('night')
        if is_full_moon(when):
            skies.add('full-moon')
    return frozenset(skies)


def current_time_of_day(now=None):
    """'day' or 'night' - the one sky that is always true. Kept for callers that want a
    single string; the rulebook itself asks current_skies()."""
    return 'day' if 'day' in current_skies(now) else 'night'


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
    The TM shelf, read off `species_movepool` rather than written out by hand.

    Every move some species learns by `machine` is stocked - which is the whole point.
    A shelf listing seven of 340 meant `!learn` could name a TM move, refuse it for
    want of the TM, and send the trainer to a shop that had never heard of it. The
    table is the authority on what a machine move IS, so the table decides the shelf.

    Descriptions come from `base_moves` for the same reason: a blurb derived from the
    move's real type and power cannot drift away from what the move does in battle.

    Anything that goes wrong here degrades to an empty shelf rather than a failed
    import. A bot that boots with no TMs on sale is recoverable; one that will not boot
    is not.
    """
    stock, prices = {}, {}

    rows = []
    try:
        import sqlite3 as _sqlite3
        # Read-only. Building a catalogue must never be able to write to the live
        # database, and `mode=ro` is the difference between a query and an accident.
        with _sqlite3.connect(f"file:{DB_FILE}?mode=ro", uri=True) as _conn:
            rows = _conn.execute("""
                SELECT DISTINCT sm.move_name, bm.type, bm.power, bm.damage_class
                FROM species_movepool sm
                JOIN base_moves bm ON bm.name = sm.move_name
                WHERE sm.learn_method = 'machine'
                ORDER BY sm.move_name
            """).fetchall()
    except Exception as e:
        print(f"⚠️ WARNING: could not read the movepool for the TM shelf ({e}).")

    for move, element, power, damage_class in rows:
        pretty = move.replace('-', ' ').title()
        price = tm_price(move, power, damage_class)
        prices[move] = price

        if damage_class == 'status':
            desc = f"Teaches {pretty}. A {(element or 'normal').title()}-type status move."
        elif power:
            desc = f"Teaches {pretty}. {(element or 'normal').title()}-type, {power} power."
        else:
            desc = f"Teaches {pretty}. {(element or 'normal').title()}-type."

        stock[move] = {
            "name": f"TM {pretty}",
            "price": price,
            "desc": f"{desc} Apply it with `!tm`.",
            "emoji": type_icon(element),
            "category": "tm",
            # Kept so the shop can filter on them without going back to the database
            # on every keystroke of a search.
            "type": element,
            "class": damage_class,
            "power": power,
        }

    return stock, prices


TM_CATALOG, TM_SHOP = build_tm_stock()

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
    'mythical':   "✨ MYTHICAL",
    'legendary':  "⭐ LEGENDARY",
    'ultrabeast': "👁️ ULTRA BEAST",
    'paradox':    "🌀 PARADOX",
    'pseudo':     "🔷 PSEUDO-LEGENDARY",
    'wild':       "Wild",
}

# The twenty Paradox species. Not flagged legendary or mythical in the database - they
# genuinely are not - so until they were named here they sat in the ORDINARY wild pool
# and turned up at the same rate as a Bidoof. Iron Valiant and Roaring Moon appearing as
# routine wildlife is the same failure the pseudo tier was created to fix, one
# generation later.
PARADOX_IDS = (984, 985, 986, 987, 988, 989, 990, 991, 992, 993, 994, 995,
               1005, 1006, 1009, 1010, 1020, 1021, 1022, 1023)


def paradox_species(alias=None, negate=False):
    """The SQL fragment selecting - or excluding - the Paradox species."""
    prefix = f"{alias}." if alias else ""
    joined = ", ".join(str(dex) for dex in PARADOX_IDS)
    return f"{prefix}pokedex_id {'NOT ' if negate else ''}IN ({joined})"


# Ultra Beasts had the opposite problem: excluded from every ordinary spawn query, so
# the ONLY way to meet one was a dimensional rift. A tier gives them a front door
# without making them common.
#
# The rates are per TIER, not per species, which is why the two new ones sit below the
# pseudo share despite being scarcer per head: 20 Paradox species and 11 Ultra Beasts
# share their tiers against 11 pseudo-legendary lines.
#
# The expedition table used to give pseudos 3% against the habitat's 2%. That extra
# point was not the problem on its own - the problem is that the apex biome is
# dragon-only and NINE of the eleven pseudo lines are dragons, so a pseudo roll there is
# a near-guaranteed Garchomp or Dragapult rather than a draw from the whole pool. An
# expedition is a deliberate trip and should be worth taking, but not by aiming the
# rarest tier at the narrowest biome. Both tables are the same now.
_RARITY_TIERS = (('mythical',   0.00001),
                 ('legendary',  0.001),
                 ('ultrabeast', 0.002),
                 ('paradox',    0.003),
                 ('pseudo',     0.02))

HABITAT_RARITY = _RARITY_TIERS
EXPEDITION_RARITY = _RARITY_TIERS


# ==========================================
# 🗺️ WHERE THINGS LIVE
# ==========================================
# Two separate systems, and they are not the same thing:
#
#   * a HABITAT is the server's own channel. Its biome is set with `!terraform` and its
#     type pool shifts with the ecosystem score - a ruined one goes toxic, a pristine
#     one opens up.
#   * an EXPEDITION is a private trip, and its sectors are fixed. They are gated by
#     visas earned off Sector Wardens, and their pools do not move.
#
# Both tables lived inside the functions that used them - the habitat's in two copies,
# one in the spawner and one in `!spawn`. Nothing had gone wrong between those two yet,
# but the rarity ladders in this same file drifted apart exactly that way, and the
# expedition's copy had already outlived the error message beside it: it listed four
# sectors when there were five, so anyone who mistyped `apex` was told Apex did not
# exist.
#
# Kept here as real tuples rather than pre-baked SQL fragments so a command can READ
# them - which is what `!biomes` does. `sql_type_tuple` builds the fragment at the two
# points that still want one.

HABITAT_BIOMES = {
    'forest':  {'emoji': '🌳', 'types': ('grass', 'bug', 'ground', 'normal'),
                'blurb': "The default. Undergrowth, burrows and canopy."},
    'urban':   {'emoji': '🏙️', 'types': ('electric', 'steel', 'poison', 'normal'),
                'blurb': "Set with `!terraform urban`. Wiring, scrap and runoff."},
    'coastal': {'emoji': '🏖️', 'types': ('water', 'flying', 'ice', 'normal'),
                'blurb': "Tideline, cliffs and open water."},
}

# What a degraded or a thriving habitat does to the pool above. A score below the first
# threshold REPLACES the biome's types; above the second it ADDS to them. This is the
# one place those numbers and those lists appear.
HABITAT_DEGRADED_BELOW = 30
HABITAT_PRISTINE_ABOVE = 70
HABITAT_DEGRADED_TYPES = ('poison', 'dark', 'steel')
HABITAT_PRISTINE_BONUS = ('fairy', 'dragon', 'psychic')

EXPEDITION_BIOMES = {
    'canopy': {'emoji': '🌲', 'types': ('grass', 'bug', 'poison', 'flying', 'normal'),
               'blurb': "Layered forest. The starting sector - no visa needed."},
    'trench': {'emoji': '🌊', 'types': ('water', 'ice'),
               'blurb': "Cold deep water and the shelf above it."},
    'core':   {'emoji': '🌋', 'types': ('fire', 'ground', 'rock', 'fighting'),
               'blurb': "Volcanic rock and the tunnels under it."},
    'sprawl': {'emoji': '🏙️', 'types': ('electric', 'steel', 'dark', 'ghost',
                                        'psychic', 'fairy'),
               'blurb': "Dense settlement, and whatever moved in after."},
    'apex':   {'emoji': '🐉', 'types': ('dragon',),
               'blurb': "The high ridge. Dragons only, and nothing else at all."},
}

# THE UNLOCK ORDER, which is also the depth order: canopy is where everybody starts and
# apex is the last sector a Warden opens. `users.unlocked_visas` stores these names as a
# comma-separated list, so "the deepest visa held" is the last of these that appears in
# it - and a set, which is what a comma-split gives you, has no order of its own.
BIOME_ORDER = tuple(EXPEDITION_BIOMES)


def biome_label(key, emoji=True):
    """
    `'apex'` -> `'🐉 Apex'`. The one place a biome key becomes something to read.

    There were three copies of this map - here, `profile_card.BIOME_LABEL`, and a local
    `biome_emojis` inside `_profile_embed` - which is exactly the shape of duplication
    that put invented biome names on the card in the first place. Unknown keys are
    title-cased rather than dropped, so a sector added to the table but not to a caller
    still reads as a name rather than vanishing.
    """
    key = str(key or '').strip().lower()
    entry = EXPEDITION_BIOMES.get(key)
    name = key.title() if key else "Unknown"
    if not entry or not emoji:
        return name
    return f"{entry['emoji']} {name}"


# ==========================================
# ⚔️ DUEL FORMATS
# ==========================================
# The levels a PvP duel may be normalised to. 50 and 100 are the two the competitive
# formats use and the two worth having: 50 is where most movepools and items are
# available without the numbers getting silly, and 100 is the ceiling.
#
# A capped duel does NOT pay experience and does not level anything up - see
# `initialize_pvp_battle`. A specimen fighting at a level it has not reached is a test
# of the team, not a training session, and letting a level-20 specimen earn against a
# level-100 threshold is how a spar would permanently rewrite it.
PVP_LEVEL_CAPS = (50, 100)


def parse_level_cap(text):
    """
    A duel's level cap from what somebody typed, as (cap, complaint).

    Accepts `50`, `100`, `lv50`, `level 100`, `50s`. Returns (None, None) for nothing at
    all, which is an uncapped duel at everybody's real levels.
    """
    raw = str(text or '').strip().lower()
    if not raw:
        return None, None

    digits = ''.join(ch for ch in raw if ch.isdigit())
    if not digits:
        return None, (f"⚠️ I did not understand `{text}`. A duel is either uncapped or "
                      f"set to {' or '.join(str(c) for c in PVP_LEVEL_CAPS)} — "
                      f"try `!battle @them 50`.")

    value = int(digits)
    if value not in PVP_LEVEL_CAPS:
        return None, (f"⚠️ Level **{value}** is not a duel format. Pick "
                      f"{' or '.join(str(c) for c in PVP_LEVEL_CAPS)}, or leave it off "
                      f"to fight at your real levels.")
    return value, None


# Five minutes between trips. Long enough that `!expedition` is not a button to mash,
# short enough that a session is not spent waiting - and it is the throttle that
# actually bites, the daily cap in utils/limits.py being the backstop behind it.
EXPEDITION_COOLDOWN_SECONDS = 300

# How near the daily cap a trip has to be before the card starts counting down.
EXPEDITION_WARN_AT = 5


def sql_type_tuple(types):
    """
    A tuple of type names as a SQL `IN` list.

    Built rather than written out because a one-element tuple renders as `('dragon',)`
    in Python and that trailing comma is a syntax error in SQL - which is why the Apex
    entry was hand-written as `('dragon')` when it lived inside the command.

    These are fixed literals from the tables above, never user input.
    """
    return "(" + ", ".join(f"'{t}'" for t in types) + ")"


def habitat_types(biome, ecosystem_score=None):
    """
    What can appear in a habitat right now, given its biome and its health.

    Returns a list, because the callers pass it straight to a parameterised query.

    `ecosystem_score=None` means an untouched habitat. It is not written as a default of
    ECOSYSTEM_BASELINE because that constant is defined further down this file and a
    default argument is evaluated when the `def` runs, not when it is called - which
    would be an import-time NameError rather than anything the tests would reach.
    """
    types = list(HABITAT_BIOMES.get(
        biome, HABITAT_BIOMES['forest'])['types'])

    if ecosystem_score is None:
        return types
    if ecosystem_score < HABITAT_DEGRADED_BELOW:
        return list(HABITAT_DEGRADED_TYPES)
    if ecosystem_score > HABITAT_PRISTINE_ABOVE:
        types.extend(HABITAT_PRISTINE_BONUS)
    return types


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
        # Ultra Beasts carry `is_legendary = 1` in the database, so without this the
        # legendary tier would draw them as well and the ultrabeast tier would be a
        # second door onto the same species rather than the only one.
        return (f"AND {prefix}is_legendary = 1 AND {prefix}is_mythical = 0 "
                f"AND {ultra_beasts(alias, negate=True)}")
    if tier == 'ultrabeast':
        return f"AND {ultra_beasts(alias)}"
    if tier == 'paradox':
        return f"AND {paradox_species(alias)}"
    if tier == 'pseudo':
        return f"AND {pseudo_legendaries(alias)}"
    # Every tier excludes the others INCLUDING this one, which is the half that makes a
    # tier mean anything. A Paradox species still reachable through the 97% ordinary
    # draw has not been made rare, it has been given a second door.
    return (f"AND {prefix}is_legendary = 0 AND {prefix}is_mythical = 0 "
            f"AND {pseudo_legendaries(alias, negate=True)} "
            f"AND {paradox_species(alias, negate=True)} "
            f"AND {ultra_beasts(alias, negate=True)}")


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


# ==========================================
# 🌍 A HEALTHY HABITAT DRAWS RARER THINGS
# ==========================================
# `servers.ecosystem_score` runs 0-100 and starts at 50. It already decided which TYPES
# a habitat spawns - below 30 the pool narrows to poison/dark/steel, above 70 it gains
# fairy/dragon/psychic - but it had no bearing at all on RARITY. Maintaining a habitat
# changed the flavour of what appeared and never the odds of something remarkable.
#
# The curve is a power of the score's distance from the baseline:
#
#     multiplier = ceiling ** ((score - 50) / 50)
#
# which gives exactly three properties worth having. At 50 it is 1.0, so a server that
# never touches its habitat sees precisely today's rates and this change is invisible to
# them. At 100 it is the ceiling. At 0 it is 1/ceiling, so neglect costs the same factor
# that care earns - the symmetry is the point, otherwise the "penalty" is just a smaller
# bonus and there is no reason to ever repair anything.
#
# Two ceilings, because they are not the same kind of number. The rare TIERS are already
# severe (a mythical is one spawn in a hundred thousand) and doubling them at a pristine
# habitat still leaves them rare. Shiny is different: it is the reward people chase
# hardest and the one whose value comes from being unlikely, so its ceiling is held
# deliberately low and separately - 1.4x at a perfect score, and no arrangement of
# settings moves it further.
ECOSYSTEM_BASELINE = 50
ECOSYSTEM_RANGE = 50.0

RARITY_SCORE_CEILING = 2.0
SHINY_SCORE_CEILING = 1.4

# One in this many, before the habitat has any say.
SHINY_BASE_ODDS = 4096


def ecosystem_multiplier(score, ceiling=RARITY_SCORE_CEILING):
    """
    How much a habitat of this health multiplies a rate by.

    A missing score is the baseline rather than zero. `servers` rows predate this and a
    NULL there is "nobody has said", not "this habitat is dead" - reading it as dead
    would quietly halve the rates on every server that has never run `!maintain`.
    """
    if score is None:
        score = ECOSYSTEM_BASELINE
    try:
        score = float(score)
    except (TypeError, ValueError):
        score = ECOSYSTEM_BASELINE

    score = max(0.0, min(100.0, score))
    return float(ceiling) ** ((score - ECOSYSTEM_BASELINE) / ECOSYSTEM_RANGE)


def scaled_rarity(tiers=HABITAT_RARITY, score=None):
    """
    A rarity table with every tier's share scaled by the habitat's health.

    Returns the same shape `roll_rarity` already takes, so the scaling is a decoration
    on the existing table rather than a second way of choosing a tier.

    The shares are clamped so they cannot sum past 1.0. At today's numbers the total is
    about 3%, so the ceiling is nowhere in sight - but a future edit to the pseudo rate
    (the one number in the table meant to be tuned by watching) plus a pristine habitat
    is exactly how a table quietly starts spawning nothing ordinary at all.
    """
    multiplier = ecosystem_multiplier(score, RARITY_SCORE_CEILING)

    scaled, budget = [], 1.0
    for tier, share in tiers:
        allowed = max(0.0, min(share * multiplier, budget))
        scaled.append((tier, allowed))
        budget -= allowed
    return tuple(scaled)


def shiny_chance(score=None, base_odds=SHINY_BASE_ODDS):
    """
    The probability of a shiny in a habitat of this health, as a fraction.

    A probability rather than a denominator, because the caller used to be
    `randint(1, 4096) == 1` and a scaled denominator would have to be rounded back to a
    whole number - which at 1.4x turns 4096 into 2926 and quietly loses the rest.
    """
    return min(1.0, ecosystem_multiplier(score, SHINY_SCORE_CEILING) / float(base_odds))


def roll_shiny(score=None, roll=None):
    """Whether this specimen is shiny. `roll` is injectable so a test can pin it."""
    if roll is None:
        roll = random.random()
    return roll < shiny_chance(score)


# ==========================================
# 🏷️ TAGS A SPECIMEN EARNS BY EXISTING
# ==========================================
# `custom_tag` is a single TEXT column, compared with `=` by the box browser's
# `tag:shiny` filter. So a specimen gets ONE tag, not a set - and a shiny alpha
# legendary has to be filed under something.
#
# Ordered by what a trainer would go looking for. Shiny first because it is the one
# people sort by and the one that is visible at a glance; alpha last because it is the
# commonest of the five at 2% of captures.
#
# A tag the player chose is never overwritten. This fills an EMPTY slot, which is what
# every freshly caught specimen has - `!settag` remains the last word.
AUTO_TAGS = (
    ('shiny',     'is_shiny'),
    ('mythical',  'is_mythical'),
    ('legendary', 'is_legendary'),
    ('pseudo',    'is_pseudo'),
    ('alpha',     'is_alpha'),
)

# The height multiplier at which `generate_biometrics` calls something an Alpha. Named
# here so the tagger and the roll agree by construction: the roll produces 1.30-1.60 for
# an Alpha and at most 1.20 for a Large, so anything at or above this is unambiguous.
ALPHA_HEIGHT_THRESHOLD = 1.30


def auto_tag(**flags):
    """
    The tag a freshly caught specimen earns, or None.

    Takes the flags by keyword - `auto_tag(is_shiny=True, is_alpha=True)` - so a caller
    that forgets one gets the default rather than a silently shifted positional.
    """
    for label, flag in AUTO_TAGS:
        if flags.get(flag):
            return label
    return None


def is_pseudo_legendary(pokedex_id):
    """Whether a dex id is one of them - for the capture broadcast and the box browser."""
    try:
        return int(pokedex_id) in PSEUDO_LEGENDARY_IDS
    except (TypeError, ValueError):
        return False


# ==========================================
# 📋 HOW MANY DIRECTIVES A NOTEBOOK HOLDS
# ==========================================
# Directives were uncapped, and `!analyze notes` issued one per note with nothing
# checking how many were already open. Somebody is sitting on twenty-two, which is more
# than a Discord select menu can even offer and far more than anybody is going to work
# through - a to-do list nobody can finish is one nobody reads.
#
# Twenty is the number because that is what fits: a select takes 25 options and the
# survey menu spends none of them on anything else, so the cap and the interface agree
# by construction rather than by somebody remembering.
MAX_ACTIVE_DIRECTIVES = 20

# How many notes one `!analyze notes 10` may consume. Bounded so a player holding forty
# notes cannot spend them all on a single command and then find the cap ate most of it.
MAX_NOTES_PER_ANALYSIS = 10

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

# Six TMs in the starting kit, and not because they are expensive - they are the
# cheapest tier there is. A new trainer does not know TMs EXIST. A shop listing does not
# teach that; a Pokemon that already knows Protect and a `!tech` list with six entries
# in it does. Each one demonstrates a different thing a move can do, so the first team
# is built out of real decisions rather than out of whatever came up by level-up.
STARTER_TMS = ('protect', 'rest', 'substitute', 'toxic', 'rock-slide', 'u-turn')

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
#
# ALL_STATS moved above the Phase 8 shelf, which needs it for the Z-Power effects
# that boost every stat at once. It is the same wildcard, defined once.

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

# ==========================================
# 🚫 FORMS THAT ARE ALREADY A GIMMICK
# ==========================================
# Ash-Greninja is what Battle Bond pays out - a mid-battle transformation earned by
# knocking something out. Letting it then Dynamax or Mega Evolve stacks two gimmicks on
# one specimen, which no generation has ever allowed.
#
# Mega mattered less until base Greninja got a stone: `has_mega_stone` was a substring
# test for 'ite' in the held item, so an Ash-Greninja holding a Greninjite would have
# been offered the button.
#
# Matched on the FULL form name rather than the base species, because the base species
# is a perfectly ordinary Greninja that may do either. `can_dynamax` splitting on the
# first hyphen is exactly why this needed its own table.
GIMMICK_LOCKED_FORMS = ('greninja-ash', 'greninja-battle-bond')
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
# ==========================================
# 🤜 WHAT ACTUALLY TOUCHES
# ==========================================
# The engine's proxy for contact had always been the DAMAGE CLASS: physical meant contact.
# That is wrong for 102 of this database's moves, and wrong in the direction that hurts -
# an Earthquake triggered Flame Body, Static, Poison Point, Rough Skin, Iron Barbs, Cute
# Charm, Pickpocket, a Rocky Helmet and a Sticky Barb, none of which it has ever touched.
# It was also wrong the other way for seven SPECIAL moves that DO make contact, Grass Knot
# and Draining Kiss among them.
#
# So the flag is data now rather than a guess. Generated from Pokemon Showdown's move
# table, which carries the real per-move contact flag; PokeAPI does not expose one, which
# is presumably why the proxy existed at all. Cross-checked against every row in
# base_moves, so this set is exactly "the moves this bot knows that make contact".
#
# Five Colosseum shadow moves are in here on the OLD proxy - Showdown has no data for
# them, they are physical, and none of them is obtainable in KyuDex. The Z-Move rows
# (`--physical` / `--special`) are deliberately absent: a Z-Move keeps its BASE move's
# name in the payload, so it is classified as whatever it was built from, which is the
# correct rule. Max Moves are handled separately - see MAX_MOVE_MARKER - because they
# never make contact whatever they were built from.

CONTACT_MOVES = frozenset({
    'accelerock', 'acrobatics', 'aerial-ace', 'anchor-shot', 'aqua-jet', 'aqua-step',
    'aqua-tail', 'arm-thrust', 'assurance', 'astonish', 'avalanche', 'axe-kick',
    'behemoth-bash', 'behemoth-blade', 'bide', 'bind', 'bite', 'bitter-blade', 'blaze-kick',
    'body-press', 'body-slam', 'bolt-beak', 'bolt-strike', 'bounce', 'branch-poke',
    'brave-bird', 'breaking-swipe', 'brick-break', 'brutal-swing', 'bug-bite', 'bullet-punch',
    'catastropika', 'ceaseless-edge', 'chip-away', 'circle-throw', 'clamp', 'close-combat',
    'collision-course', 'comet-punch', 'comeuppance', 'constrict', 'counter', 'covet',
    'crabhammer', 'cross-chop', 'cross-poison', 'crunch', 'crush-claw', 'crush-grip', 'cut',
    'darkest-lariat', 'dig', 'dire-claw', 'dive', 'dizzy-punch', 'double-edge', 'double-hit',
    'double-iron-bash', 'double-kick', 'double-shock', 'double-slap', 'dragon-ascent',
    'dragon-claw', 'dragon-hammer', 'dragon-rush', 'dragon-tail', 'drain-punch',
    'draining-kiss', 'drill-peck', 'drill-run', 'dual-chop', 'dual-wingbeat', 'dynamic-punch',
    'electro-drift', 'endeavor', 'extreme-speed', 'facade', 'fake-out', 'false-surrender',
    'false-swipe', 'feint-attack', 'fell-stinger', 'fire-fang', 'fire-lash', 'fire-punch',
    'first-impression', 'fishious-rend', 'flail', 'flame-charge', 'flame-wheel', 'flare-blitz',
    'flip-turn', 'floaty-fall', 'fly', 'flying-press', 'focus-punch', 'force-palm', 'foul-play',
    'frustration', 'fury-attack', 'fury-cutter', 'fury-swipes', 'gear-grind', 'giga-impact',
    'glaive-rush', 'grass-knot', 'grassy-glide', 'guillotine', 'gyro-ball', 'hammer-arm',
    'hard-press', 'head-charge', 'head-smash', 'headbutt', 'headlong-rush', 'heart-stamp',
    'heat-crash', 'heavy-slam', 'high-horsepower', 'high-jump-kick', 'hold-back', 'horn-attack',
    'horn-drill', 'horn-leech', 'hyper-drill', 'hyper-fang', 'ice-ball', 'ice-fang',
    'ice-hammer', 'ice-punch', 'ice-spinner', 'infestation', 'iron-head', 'iron-tail',
    'jaw-lock', 'jet-punch', 'jump-kick', 'karate-chop', 'knock-off', 'kowtow-cleave',
    'lash-out', 'last-resort', 'leaf-blade', 'leech-life', 'lets-snuggle-forever', 'lick',
    'liquidation', 'low-kick', 'low-sweep', 'lunge', 'mach-punch', 'malicious-moonsault',
    'mega-kick', 'mega-punch', 'megahorn', 'metal-claw', 'meteor-mash', 'mighty-cleave',
    'mortal-spin', 'multi-attack', 'needle-arm', 'night-slash', 'nuzzle', 'outrage', 'payback',
    'peck', 'petal-dance', 'phantom-force', 'plasma-fists', 'play-rough', 'pluck',
    'poison-fang', 'poison-jab', 'poison-tail', 'population-bomb', 'pounce', 'pound',
    'power-trip', 'power-up-punch', 'power-whip', 'psyblade', 'psychic-fangs', 'psyshield-bash',
    'pulverizing-pancake', 'punishment', 'pursuit', 'quick-attack', 'rage', 'rage-fist',
    'raging-bull', 'rapid-spin', 'razor-shell', 'retaliate', 'return', 'revenge', 'reversal',
    'rock-climb', 'rock-smash', 'rolling-kick', 'rollout', 'sacred-sword', 'scratch',
    'searing-sunraze-smash', 'seismic-toss', 'shadow-blast', 'shadow-blitz', 'shadow-break',
    'shadow-claw', 'shadow-end', 'shadow-force', 'shadow-punch', 'shadow-rush', 'shadow-sneak',
    'sizzly-slide', 'skitter-smack', 'skull-bash', 'sky-drop', 'sky-uppercut', 'slam', 'slash',
    'smart-strike', 'smelling-salts', 'snap-trap', 'solar-blade', 'soul-stealing-7-star-strike',
    'spark', 'spectral-thief', 'spin-out', 'spirit-break', 'steamroller', 'steel-roller',
    'steel-wing', 'stomp', 'stomping-tantrum', 'stone-axe', 'storm-throw', 'strength',
    'struggle', 'submission', 'sucker-punch', 'sunsteel-strike', 'super-fang', 'supercell-slam',
    'superpower', 'surging-strikes', 'tackle', 'tail-slap', 'take-down', 'temper-flare',
    'thief', 'thrash', 'throat-chop', 'thunder-fang', 'thunder-punch', 'thunderous-kick',
    'trailblaze', 'triple-axel', 'triple-dive', 'triple-kick', 'trop-kick', 'trump-card',
    'u-turn', 'upper-hand', 'v-create', 'veevee-volley', 'vice-grip', 'vine-whip',
    'vital-throw', 'volt-tackle', 'wake-up-slap', 'waterfall', 'wave-crash', 'wicked-blow',
    'wild-charge', 'wing-attack', 'wood-hammer', 'wrap', 'wring-out', 'x-scissor',
    'zen-headbutt', 'zing-zap', 'zippy-zap',
})

# A Max Move is priority 0 no matter what it was built from. This was the bug behind a Max
# Geyser built on Aqua Jet being turned away by Psychic Terrain: the payload still carried
# Aqua Jet's +1, because the sanitisation pass wiped the ailment, the status, the stat
# change, the healing and the drain, and never touched the priority.
#
# Max Guard is the exception and keeps Protect's own +4.
MAX_MOVE_MARKER = '_is_max_move'
MAX_MOVE_PRIORITY = 0
MAX_GUARD_PRIORITY = 4

# A Z-Move keeps its BASE move's name in the payload for exactly the same reason a Max
# Move does - PP deduction and the move-restriction checks both look the move back up by
# that name - so "was this a Z-Move?" cannot be answered by reading the name either.
# apply_z_mutation stamps this, and the engines carry it onto the attacker as
# LAST_MOVE_WAS_Z so that Sketch can refuse a Z-Move a turn later.
Z_MOVE_MARKER = '_is_z_move'
LAST_MOVE_WAS_Z = 'last_move_was_z'

# Avalanche and Revenge are one rule with two names: 60 base, doubled if the user was
# struck earlier in the same turn. Revenge was already implemented on its own; Avalanche
# was not implemented at all. Both read `last_damage_taken`, which is written on hit and
# wiped at the end of the turn, so its mere presence means "was hit before moving".
LAST_MOVER_DOUBLING_MOVES = {'avalanche': 60, 'revenge': 60}

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