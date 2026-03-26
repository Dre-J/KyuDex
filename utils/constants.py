import json
import os

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
    "greatball": {"name": "Great Ball", "price": 10, "desc": "1.5x Capture Rate", "emoji": "🔵"},
    "ultraball": {"name": "Ultra Ball", "price": 25, "desc": "2.0x Capture Rate", "emoji": "🟡"},
    "purifier":  {"name": "Purifier", "price": 50, "desc": "Instantly removes pollution from a server", "emoji": "🫧"},
    "potion":    {"name": "Potion", "price": 100, "desc": "Restore 20 health points in battle", "emoji": "🧪"}
}
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
        'technician':    {'condition': 'power_cap', 'threshold': 60, 'multiplier': 1.5}
    },
    'end_of_turn': {
        'speed-boost': {'type': 'stat', 'stat': 'speed', 'value': 1},
        'moody':       {'type': 'stat', 'stat': 'random', 'value': 2, 'drop_value': -1}, # Moody is complex but easy to scale later!
        'shed-skin':   {'type': 'cure', 'chance': 33},
        'rain-dish':   {'type': 'weather_heal', 'weather': ['rain', 'heavy-rain'], 'denominator': 16},
        'ice-body':    {'type': 'weather_heal', 'weather': ['hail'], 'denominator': 16},
        # 🚨 NEW: Pathogen Symbiosis
        'poison-heal': {'type': 'status_heal', 'status': 'poison', 'denominator': 8}
    },
    'contact_status': {
        'static': {'status': 'paralysis', 'immune': 'electric'},
        'flame-body': {'status': 'burn', 'immune': 'fire'},
        'poison-point': {'status': 'poison', 'immune': 'poison'},
        'effect-spore': {'status': 'poison', 'immune': 'poison'}
    },
    'contact_damage': ['rough-skin', 'iron-barbs'],
}

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