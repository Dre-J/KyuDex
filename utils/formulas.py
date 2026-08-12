import math
import random
from utils.constants import TYPE_CHART, NATURE_MULTIPLIERS, BIOLOGICAL_TRAITS, CONSUMABLE_DATABASE, MULTI_STRIKE_MOVES, get_species_weight
from datetime import datetime, timezone


def apply_entry_hazards(specimen, hazards, type_chart, owner_prefix="Your"):
    """
    Calculates environmental hazard damage and effects when a specimen enters the habitat.
    Modifies the specimen's HP, stats, and status in-place. Returns the combat log string.
    """
    log = ""
    types = specimen.get('types', [])
    
    # Is the specimen touching the ground? (We check for Flying type!)
    # Note: If you add the 'Levitate' ability later, you will add `and specimen.get('ability') != 'levitate'` here!
    ability = get_active_ability(specimen)
    
    # Is the specimen touching the ground?
    is_grounded = 'flying' not in types and ability != 'levitate'
    
    # ==========================================
    # 1. STEALTH ROCK (Affects all specimens)
    # ==========================================
    if hazards.get('stealth-rock'):
        rock_mult = 1.0
        for t in types:
            rock_mult *= type_chart.get('rock', {}).get(t, 1.0)
            
        if rock_mult > 0:
            # Base damage is 12.5% (1/8th) of max HP, scaled by weakness/resistance
            sr_dmg = max(1, int(specimen.get('max_hp', 100) * 0.125 * rock_mult))
            specimen['current_hp'] = max(0, specimen['current_hp'] - sr_dmg)
            log += f"🪨 Pointed stones dug into {owner_prefix.strip()} **{specimen['name'].capitalize()}**! (-{sr_dmg} HP)\n"
            
    # If the specimen faints instantly to Stealth Rock, stop processing the other hazards!
    if specimen['current_hp'] <= 0:
        return log
    
    # ==========================================
    # G-MAX METALLIC PARTICULATES (Steelsurge)
    # ==========================================
    if hazards.get('steelsurge') and specimen['current_hp'] > 0:
        multiplier = 1.0
        for p_type in specimen.get('types', []):
            # 🚨 Multiply the weakness against STEEL
            multiplier *= TYPE_CHART.get('steel', {}).get(p_type, 1.0)
            
        # Base damage is 1/8th (12.5%). Multiplied by type effectiveness.
        damage_fraction = (1.0 / 8.0) * multiplier
        
        # Calculate final HP loss
        surge_dmg = max(1, math.floor(specimen['max_hp'] * damage_fraction))
        specimen['current_hp'] = max(0, specimen['current_hp'] - surge_dmg)
        
        # Dynamic chat output based on effectiveness!
        if multiplier >= 2.0:
            log += f"⚙️ It's super effective! The sharp steel spikes heavily gouged {owner_prefix} **{specimen['name'].capitalize()}**! (-{surge_dmg} HP)\n"
        elif multiplier <= 0.5:
            log += f"⚙️ It's not very effective... The steel spikes scraped {owner_prefix} **{specimen['name'].capitalize()}**. (-{surge_dmg} HP)\n"
        else:
            log += f"⚙️ Sharp steel spikes dug into {owner_prefix} **{specimen['name'].capitalize()}**! (-{surge_dmg} HP)\n"

    # ==========================================
    # 2. SPIKES (Grounded only)
    # ==========================================
    spikes_layers = hazards.get('spikes', 0)
    if spikes_layers > 0 and is_grounded:
        if spikes_layers == 1: fraction = 1/8    # 12.5%
        elif spikes_layers == 2: fraction = 1/6  # 16.6%
        else: fraction = 1/4                     # 25.0%
        
        spikes_dmg = max(1, int(specimen.get('max_hp', 100) * fraction))
        specimen['current_hp'] = max(0, specimen['current_hp'] - spikes_dmg)
        log += f"🗡️ {owner_prefix.strip()} **{specimen['name'].capitalize()}** was hurt by the spikes! (-{spikes_dmg} HP)\n"
        
    if specimen['current_hp'] <= 0:
        return log

    # ==========================================
    # 3. TOXIC SPIKES (Grounded only)
    # ==========================================
    ts_layers = hazards.get('toxic-spikes', 0)
    if ts_layers > 0 and is_grounded:
        # Poison types act as biological filters and completely remove the pollution!
        if 'poison' in types:
            hazards['toxic-spikes'] = 0
            log += f"🧪 {owner_prefix.strip()} **{specimen['name'].capitalize()}** absorbed the toxic spikes and cleared the habitat!\n"
        
        # If it's not Steel (immune) and it doesn't already have a status condition...
        elif 'steel' not in types and not specimen.get('status_condition'):
            specimen['status_condition'] = {'name': 'poison', 'duration': -1}
            # (Note: Technically 2 layers causes 'bad-poison', but we default to standard poison for now)
            log += f"☣️ {owner_prefix.strip()} **{specimen['name'].capitalize()}** was poisoned by the toxic spikes!\n"

    # ==========================================
    # 4. STICKY WEB (Grounded only)
    # ==========================================
    if hazards.get('sticky-web') and is_grounded:
        if 'stat_stages' not in specimen:
            specimen['stat_stages'] = {'attack': 0, 'defense': 0, 'sp_atk': 0, 'sp_def': 0, 'speed': 0}
            
        if specimen['stat_stages']['speed'] > -6:
            specimen['stat_stages']['speed'] -= 1
            log += f"🕸️ {owner_prefix.strip()} **{specimen['name'].capitalize()}** was caught in a sticky web! Its Speed fell!\n"
            
    return log

def calculate_real_stat(stat_name, base, iv, ev, level):
    """Calculates the actual scaled stat of a Pokemon."""
    # We use integer division (//) to perfectly replicate the math floor behavior of the games
    core_math = ((2 * base + iv + (ev // 4)) * level) // 100
    
    if stat_name == 'hp':
        return core_math + level + 10
    else:
        return core_math + 5

def calculate_stats(base_stats, ivs, evs, level, nature):
    """
    Inputs should be dictionaries holding the 6 stat keys: 
    'hp', 'attack', 'defense', 'sp_atk', 'sp_def', 'speed'
    """
    final_stats = {}
    
    # 1. Calculate HP
    hp_core = (2 * base_stats['hp'] + ivs['hp'] + math.floor(evs['hp'] / 4)) * level
    final_stats['hp'] = math.floor(hp_core / 100) + level + 10
    
    # 2. Calculate the other 5 stats
    stat_names = ['attack', 'defense', 'sp_atk', 'sp_def', 'speed']
    
    # Fetch which stats this specific nature alters
    inc_stat, dec_stat = NATURE_MULTIPLIERS.get(nature.lower(), (None, None))
    
    for stat in stat_names:
        core = (2 * base_stats[stat] + ivs[stat] + math.floor(evs[stat] / 4)) * level
        pre_nature = math.floor(core / 100) + 5
        
        # Apply the Genetic Nature Multiplier
        multiplier = 1.0
        if stat == inc_stat:
            multiplier = 1.1
        elif stat == dec_stat:
            multiplier = 0.9
            
        final_stats[stat] = math.floor(pre_nature * multiplier)
        
    return final_stats

def check_consumables(pokemon, owner_str, magic_room=False):
    """
    Monitors biological thresholds and consumes berries that have hit their trigger.

    The actual resolution lives in apply_berry_effect, which Teatime, Bug Bite, Pluck and
    a flung berry also drive - keeping one implementation is what guarantees every route
    to eating a berry records it for Belch.
    """
    if pokemon is None or pokemon['current_hp'] <= 0:
        return ""

    # An embargoed holder, or one standing in a Magic Room, cannot reach its own berry.
    held_item = get_active_item(pokemon, magic_room)
    if held_item not in CONSUMABLE_DATABASE:
        return ""

    return apply_berry_effect(pokemon, held_item, ignore_threshold=False, owner_str=owner_str)

def is_grounded(pokemon, gravity_active=False):
    """Evaluates if a specimen is physically touching the battlefield."""
    if gravity_active: return True # 🚨 Gravity grounds everything!
    types = pokemon.get('types', [])
    ability = get_active_ability(pokemon)
    item = get_active_item(pokemon)
    
    if 'flying' in types: return False
    if ability == 'levitate': return False
    if item == 'air-balloon': return False

    # Magnet Rise lifts itself; Telekinesis lifts somebody else. Either way the specimen
    # is off the ground and Ground-type moves cannot reach it.
    volatiles = pokemon.get('volatile_statuses') or {}
    if volatiles.get('magnet_rise') or volatiles.get('telekinesis'): return False
    
    return True

# ==========================================
# 🚨 SET-DAMAGE ANOMALIES (Formula Bypass)
# ==========================================
# These moves ignore the standard kinetic formula entirely. Attack, Defense, stat
# stages, STAB, criticals, weather, and type effectiveness never scale the payload.
# A 0x type matchup is still a hard immunity, which is enforced in calculate_damage.
FIXED_DAMAGE_MOVES = ['dragon-rage', 'sonic-boom', 'psywave', 'final-gambit']

# Instant-faint moves. These roll their own accuracy inside calculate_damage.
OHKO_MOVES = ['fissure', 'horn-drill', 'guillotine', 'sheer-cold']

# Every move that skips the standard damage formula. None of them bypass a 0x
# elemental matchup, so calculate_damage gates the whole family on one immunity check:
# Ghost blanks Seismic Toss / Super Fang / Endeavor / Horn Drill / Guillotine,
# Normal blanks Night Shade, and Flying blanks Fissure.
FORMULA_BYPASS_MOVES = FIXED_DAMAGE_MOVES + OHKO_MOVES + [
    'endeavor', 'seismic-toss', 'night-shade',
    'super-fang', 'natures-madness', 'ruination'
]

def get_fixed_damage(move_name, attacker):
    """
    Returns the raw HP payload for a set-damage move, or None if the move isn't one.
    The caller is responsible for the immunity check and for Final Gambit's self-KO.
    """
    if move_name == 'dragon-rage':
        return 40

    if move_name == 'sonic-boom':
        return 20

    if move_name == 'psywave':
        # 50% to 150% of the user's level, floored, but never less than 1 HP
        level = attacker.get('level', 50)
        return max(1, math.floor(level * random.randint(50, 150) / 100))

    if move_name == 'final-gambit':
        # The user donates its entire remaining life force as damage
        return attacker.get('current_hp', 0)

    return None

def estimate_fixed_damage(move_name, attacker):
    """
    Average-case payload used by the NPC AI for move scoring. Identical to
    get_fixed_damage but with the RNG resolved to its mean so the AI stays stable.
    """
    if move_name == 'psywave':
        return attacker.get('level', 50) # The 50-150% roll averages out to 100%
    return get_fixed_damage(move_name, attacker) or 0

# ==========================================
# 🚨 HP-SCALED POWER MOVES
# ==========================================
# Unlike the bypass family above, these run through the *standard* damage formula.
# Only their base power is dynamic, so STAB, type effectiveness, criticals, stat
# stages and items all still apply on top of whatever power we return here.
HP_SCALED_MOVES = ['flail', 'reversal', 'eruption', 'water-spout', 'wring-out', 'crush-grip']

def get_hp_scaled_power(move_name, attacker, defender):
    """
    Computes base power from a live HP ratio, or returns None if the move doesn't scale.
    Flail/Reversal and Eruption/Water Spout read the USER's HP; Wring Out and Crush
    Grip read the TARGET's. Power is always evaluated at the moment of execution, so
    chip damage taken earlier in the same turn already counts.
    """
    if move_name in ['flail', 'reversal']:
        # The franchise uses a 48ths bracket table rather than a smooth curve:
        #   ratio (48ths)   HP %        power
        #   0 - 1           <  4.17%    200
        #   2 - 4           < 10.42%    150
        #   5 - 9           < 20.83%    100
        #   10 - 16         < 35.42%     80
        #   17 - 32         < 68.75%     40
        #   33 - 48         rest         20
        ratio = math.floor(48 * attacker.get('current_hp', 0) / max(1, attacker.get('max_hp', 1)))

        if ratio <= 1:  return 200
        if ratio <= 4:  return 150
        if ratio <= 9:  return 100
        if ratio <= 16: return 80
        if ratio <= 32: return 40
        return 20

    if move_name in ['eruption', 'water-spout']:
        # Linear falloff from 150 at full health. Weakest possible hit is still 1 power.
        return max(1, math.floor(150 * attacker.get('current_hp', 0) / max(1, attacker.get('max_hp', 1))))

    if move_name in ['wring-out', 'crush-grip']:
        # Linear scale off the TARGET's remaining health, peaking at 120 on a full-HP target
        return max(1, math.floor(120 * defender.get('current_hp', 0) / max(1, defender.get('max_hp', 1))))

    return None

# ==========================================
# 🚨 STAT-RATIO SCALED POWER MOVES
# ==========================================
# Same contract as the HP-scaled family: these run through the standard damage formula
# and only their base power is dynamic. Body Press is listed separately because it
# doesn't alter power at all - it swaps which stat the formula reads.
STAT_SCALED_MOVES = [
    'gyro-ball', 'electro-ball',            # relative Speed
    'heavy-slam', 'heat-crash',             # relative body mass
    'grass-knot', 'low-kick',               # target body mass
    'punishment',                           # target's stat boosts
    'stored-power', 'power-trip',           # user's stat boosts
    'hex',                                  # target's status condition
    'revenge',                              # user was struck first this turn
    'stomping-tantrum',                     # user's previous move failed
    'rage-fist',                            # hits the user has absorbed
    'last-respects',                        # allies already lost
]

def _effective_speed(pokemon):
    """Speed after stat-stage modifiers, floored at 1 so it's always a safe divisor."""
    raw = pokemon.get('stats', {}).get('speed', 50)
    stage = pokemon.get('stat_stages', {}).get('speed', 0)

    if stage > 0:
        raw = int(raw * ((2.0 + stage) / 2.0))
    elif stage < 0:
        raw = int(raw * (2.0 / (2.0 + abs(stage))))

    return max(1, raw)

def _positive_stage_total(pokemon):
    """Sum of every raised stat stage. Drops are ignored - only boosts add power."""
    return sum(v for v in (pokemon.get('stat_stages') or {}).values() if v > 0)

def get_stat_scaled_power(move_name, attacker, defender):
    """
    Computes base power from a live stat/mass/counter ratio, or None if it doesn't scale.
    Every value is read at execution time, so boosts and chip damage from earlier in the
    same turn are already reflected.
    """
    # --- RELATIVE VELOCITY ---
    if move_name == 'gyro-ball':
        # Rewards being *slower*. Caps at 150 when the target massively outspeeds you.
        return min(150, max(1, math.floor(25 * _effective_speed(defender) / _effective_speed(attacker)) + 1))

    if move_name == 'electro-ball':
        # The inverse of Gyro Ball - rewards outspeeding the target
        ratio = _effective_speed(defender) / _effective_speed(attacker)
        if ratio <= 0.25:   return 150
        if ratio <= 1 / 3:  return 120
        if ratio <= 0.5:    return 80
        if ratio < 1:       return 60
        return 40

    # --- RELATIVE BODY MASS ---
    if move_name in ['heavy-slam', 'heat-crash']:
        ratio = get_species_weight(attacker) / max(0.1, get_species_weight(defender))
        if ratio >= 5: return 120
        if ratio >= 4: return 100
        if ratio >= 3: return 80
        if ratio >= 2: return 60
        return 40

    if move_name in ['grass-knot', 'low-kick']:
        # Purely the target's mass - a heavy target is easier to trip
        weight = get_species_weight(defender)
        if weight < 10:  return 20
        if weight < 25:  return 40
        if weight < 50:  return 60
        if weight < 100: return 80
        if weight < 200: return 100
        return 120

    # --- STAT STAGE ACCUMULATORS ---
    if move_name == 'punishment':
        # Punishes the target for setting up. 60 base, +20 per boost, hard cap 200.
        return min(200, 60 + 20 * _positive_stage_total(defender))

    if move_name in ['stored-power', 'power-trip']:
        # Rewards the user for setting up. 20 base, +20 per boost.
        return min(860, 20 + 20 * _positive_stage_total(attacker))

    # --- CONDITIONAL DOUBLERS ---
    if move_name == 'hex':
        status = defender.get('status_condition') or {}
        return 130 if status.get('name') else 65

    if move_name == 'revenge':
        # Doubles if the target already struck the user earlier in this same turn.
        # last_damage_taken is written on hit and wiped at end of turn, so its mere
        # presence means "was hit before moving".
        return 120 if attacker.get('last_damage_taken', 0) > 0 else 60

    if move_name == 'stomping-tantrum':
        return 150 if attacker.get('last_move_failed') else 75

    # --- PERSISTENT COUNTERS ---
    if move_name == 'rage-fist':
        # +50 per hit absorbed, capped at 350. The counter rides on the specimen, so it
        # survives switching out and back in.
        return min(350, 50 + 50 * attacker.get('times_hit', 0))

    if move_name == 'last-respects':
        # +50 for every teammate already lost. The engines refresh this before each hit.
        return min(5050, 50 + 50 * attacker.get('fainted_allies', 0))

    return None

# ==========================================
# 🌍 FIELD-WIDE SPORTS, DELUGES AND SIDE SWAPS
# ==========================================
# These sit on the FIELD rather than on either side, so both players feel them. The
# engines keep them in state['field'] alongside the rooms and Gravity, and hand the whole
# dictionary to the damage formula rather than growing another parameter per effect.
SPORT_MOVES = {'mud-sport': 'electric', 'water-sport': 'fire'}
SPORT_TURNS = 5
SPORT_MULTIPLIER = 1 / 3

# Ion Deluge only lasts the rest of the turn it was used on, which is why it moves at
# +1: used first, it catches the Normal move that was coming.
ION_DELUGE_TURNS = 1

# Every side-effect Court Change picks up and puts down on the other side: hazards,
# screens, guards and Tailwind. Deliberately NOT Happy Hour - that is a wager on the
# battle's takings rather than something standing on the field, and the games leave it
# where it was set.
COURT_CHANGE_KEYS = (
    'stealth-rock', 'spikes', 'toxic-spikes', 'sticky-web', 'steelsurge',
    'reflect', 'light-screen', 'aurora-veil', 'lucky-chant', 'safeguard', 'mist',
    'tailwind',
)

# Happy Hour doubles the takings from a battle.
PRIZE_MONEY_MULTIPLIER = 2

# ==========================================
# 💪 SELF-BUFFS THE DATABASE FORGOT
# ==========================================
# Both rows carry an empty stat_name, so the generic path had nothing to apply and the
# moves did nothing at all. Victory Dance raises three stats despite being commonly
# described as raising two; Shelter raises Defense sharply, which is two stages.
SELF_BUFF_MOVES = {
    'victory-dance': {'attack': 1, 'defense': 1, 'speed': 1},
    'shelter': {'defense': 2},
}

# ==========================================
# 👻 CURSE, PSYCHO SHIFT AND THE ODDMENTS
# ==========================================
# Curse is two different moves wearing one name, told apart by the user's typing.
CURSE_SELF_COST = 0.5          # what a Ghost pays out of its own maximum
CURSE_DRAIN_FRACTION = 0.25    # what the cursed one loses each turn thereafter
CURSE_STAT_CHANGES = {'attack': 1, 'defense': 1, 'speed': -1}

# Psycho Shift hands over anything that is not already worn by the target. These are the
# major ailments as this database spells them - there is no separate 'bad-poison' row,
# Toxic stores plain 'poison', so naming one here would only ever match nothing.
PSYCHO_SHIFT_TRANSFERS = {'burn', 'paralysis', 'poison', 'sleep', 'freeze'}

# Acupressure sharpens one stat at random, by two stages.
ACUPRESSURE_BOOST = 2
MAX_STAT_STAGE = 6

# ==========================================
def transferable_status(pokemon):
    """The ailment a specimen could hand over, or None if it has nothing to give."""
    name = (pokemon.get('status_condition') or {}).get('name')
    return name if name in PSYCHO_SHIFT_TRANSFERS else None


def random_boostable_stat(pokemon, rng=None):
    """
    One stat Acupressure could still sharpen, chosen at random. None when every stat is
    already at the ceiling, which is the move's only failure case.
    """
    stages = pokemon.get('stat_stages') or {}
    room = [stat for stat in ALL_STAT_STAGES if stages.get(stat, 0) < MAX_STAT_STAGE]
    return (rng or random).choice(room) if room else None


def field_flag(field, move_name):
    """Turns left on a field effect, keyed by move name rather than by flag spelling."""
    return int((field or {}).get(move_name.replace('-', '_'), 0) or 0)


def sport_multiplier(move_type, field):
    """
    How much the active sports damp this element. Mud Sport smothers Electric, Water
    Sport smothers Fire, and both at once damp their own element independently.
    """
    mult = 1.0
    for move, damped in SPORT_MOVES.items():
        if move_type == damped and field_flag(field, move) > 0:
            mult *= SPORT_MULTIPLIER
    return mult


def court_change(user_side, target_side):
    """
    Trade every side effect across the field. Returns whether anything actually moved,
    so a Court Change into two bare sides can fail rather than claim to have done
    something.
    """
    if user_side is None or target_side is None:
        return False

    moved = False
    for key in COURT_CHANGE_KEYS:
        mine, theirs = user_side.get(key), target_side.get(key)
        if not mine and not theirs:
            continue

        # A side that never had this effect must be left with the same falsy shape the
        # side dictionaries were built with - 0 for the stacking hazards, False for the
        # flags - because the engines do arithmetic on the counters. Writing None here
        # would break the next `spikes + 1`.
        present = mine if mine else theirs
        blank = 0 if isinstance(present, int) and not isinstance(present, bool) else False

        user_side[key] = theirs if theirs else blank
        target_side[key] = mine if mine else blank
        moved = True

    return moved


def prize_multiplier(side_hazards):
    """What a side's takings are multiplied by once the battle is settled."""
    return PRIZE_MONEY_MULTIPLIER if (side_hazards or {}).get('happy-hour') else 1


# ==========================================
# 💞 FRIENDSHIP-SCALED POWER
# ==========================================
# Return and the two partner moves hit harder the more the specimen likes its trainer;
# Frustration reads the same bond backwards. All four share one divisor, so a maxed
# bond caps them at 102 and a bottomed one still leaves 1.
FRIENDSHIP_MOVES = {'return', 'pika-papow', 'veevee-volley'}
FRUSTRATION_MOVES = {'frustration'}

MAX_HAPPINESS = 255
FRIENDSHIP_DIVISOR = 2.5

# What a specimen is worth when nothing recorded a bond. Wild encounters and NPC rosters
# are built in memory and never had a happiness row, and this is where the mainline games
# start everything, so it is the honest default rather than a stand-in for zero.
DEFAULT_HAPPINESS = 70


def get_happiness(pokemon):
    """The bond a specimen carries, clamped to the range the games store."""
    raw = (pokemon or {}).get('happiness')
    if raw is None:
        raw = DEFAULT_HAPPINESS
    try:
        return max(0, min(MAX_HAPPINESS, int(raw)))
    except (TypeError, ValueError):
        return DEFAULT_HAPPINESS


def get_friendship_power(move_name, attacker):
    """Power for the bond-scaled moves. None for everything else."""
    if move_name in FRIENDSHIP_MOVES:
        bond = get_happiness(attacker)
    elif move_name in FRUSTRATION_MOVES:
        bond = MAX_HAPPINESS - get_happiness(attacker)
    else:
        return None

    # Floors at 1: these rows carry no stored power, so returning 0 would make the move
    # silently do nothing rather than do very little.
    return max(1, math.floor(bond / FRIENDSHIP_DIVISOR))

# ==========================================
# 🍽️ STOCKPILE, SWALLOW AND SPIT UP
# ==========================================
# Stockpile banks up to three charges, each raising both defences a stage. Swallow and
# Spit Up each cash the whole bank in - one as health, one as power - and hand back the
# stages that were granted. Nothing else spends the counter, so the three moves are only
# ever meaningful together.
#
# Stockpile's database row carries a bare 'defense +1', which is why the survey counted
# it as finished: the generic path was raising one stat and banking nothing.
MAX_STOCKPILE = 3
SPIT_UP_POWER_PER_STACK = 100
SWALLOW_HEAL_BY_STACK = {1: 0.25, 2: 0.50, 3: 1.00}

STOCKPILE_STATS = ('defense', 'sp_def')


def get_stockpile(pokemon):
    """How many charges are banked, 0-3."""
    return int(((pokemon or {}).get('volatile_statuses') or {}).get('stockpile', 0) or 0)


def add_stockpile(pokemon):
    """
    Bank one charge. Returns (accepted, stat_changes) - refused at the cap, since the
    games make a fourth Stockpile fail outright rather than silently waste a turn.
    """
    held = get_stockpile(pokemon)
    if held >= MAX_STOCKPILE:
        return False, []

    pokemon.setdefault('volatile_statuses', {})['stockpile'] = held + 1
    return True, [('attacker', stat, 1) for stat in STOCKPILE_STATS]


def spend_stockpile(pokemon):
    """
    Empty the bank. Returns (charges_spent, stat_changes) where the changes undo exactly
    what was granted - tracked by count rather than by reading the stages back, so an
    unrelated boost or drop in between is left alone.
    """
    held = get_stockpile(pokemon)
    if not held:
        return 0, []

    (pokemon.get('volatile_statuses') or {}).pop('stockpile', None)
    return held, [('attacker', stat, -held) for stat in STOCKPILE_STATS]


# ==========================================
# 🎁 ITEM-DRIVEN DAMAGE
# ==========================================
# Natural Gift takes its element and its power from the berry being held, and spends it.
# Exactly the 41 berries this game actually stocks are tabled - the wider series has
# more, but a berry that cannot be obtained here would only be dead weight.
#
# Powers are the Gen VI values: the status and resist berries throw for 80, the stat
# berries for 100. (The 90-power middle tier is all berries this game does not stock.)
NATURAL_GIFT_BERRIES = {
    # --- Status-curing berries ---
    'cheri-berry': ('fire', 80),     'chesto-berry': ('water', 80),
    'pecha-berry': ('electric', 80), 'rawst-berry': ('grass', 80),
    'aspear-berry': ('ice', 80),     'leppa-berry': ('fighting', 80),
    'oran-berry': ('poison', 80),    'persim-berry': ('ground', 80),
    'lum-berry': ('flying', 80),     'sitrus-berry': ('psychic', 80),
    'figy-berry': ('bug', 80),       'wiki-berry': ('rock', 80),
    'mago-berry': ('ghost', 80),     'aguav-berry': ('dragon', 80),
    'iapapa-berry': ('dark', 80),

    # --- Type-resisting berries ---
    'occa-berry': ('fire', 80),      'passho-berry': ('water', 80),
    'wacan-berry': ('electric', 80), 'rindo-berry': ('grass', 80),
    'yache-berry': ('ice', 80),      'chople-berry': ('fighting', 80),
    'kebia-berry': ('poison', 80),   'shuca-berry': ('ground', 80),
    'coba-berry': ('flying', 80),    'payapa-berry': ('psychic', 80),
    'tanga-berry': ('bug', 80),      'charti-berry': ('rock', 80),
    'kasib-berry': ('ghost', 80),    'haban-berry': ('dragon', 80),
    'colbur-berry': ('dark', 80),    'babiri-berry': ('steel', 80),
    'chilan-berry': ('normal', 80),

    # --- Stat-boosting berries, which throw harder ---
    'liechi-berry': ('grass', 100),  'ganlon-berry': ('ice', 100),
    'salac-berry': ('fighting', 100),'petaya-berry': ('poison', 100),
    'apicot-berry': ('ground', 100), 'lansat-berry': ('flying', 100),
    'starf-berry': ('psychic', 100), 'micle-berry': ('rock', 100),
    'custap-berry': ('ghost', 100),
}

# Present is a gamble: four in ten it is a feeble tap, two in ten it HEALS the target
# instead. Weights are out of ten so the roll stays readable.
PRESENT_OUTCOMES = [(4, 40), (3, 80), (1, 120), (2, None)]   # (weight, power); None heals
PRESENT_HEAL_FRACTION = 0.25


def natural_gift_payload(attacker):
    """
    The (type, power) a held berry throws for, or None when there is nothing to throw.
    Reads the stored item so a suppressed-item field (Magic Room) is handled by the
    caller rather than silently succeeding here.
    """
    return NATURAL_GIFT_BERRIES.get((get_stored_item(attacker) or '').lower())


def roll_present(rng=None):
    """
    One draw from Present's table. Returns a power, or None when it heals instead.
    Rolled once per use and handed straight to the damage step - deliberately not
    routed through resolve_dynamic_power, which the move button also calls and would
    therefore advertise a number the swing was never going to use.
    """
    roll = (rng or random).randint(1, sum(w for w, _ in PRESENT_OUTCOMES))
    for weight, power in PRESENT_OUTCOMES:
        roll -= weight
        if roll <= 0:
            return power
    return PRESENT_OUTCOMES[-1][1]


# ==========================================
# 🃏 RESOURCE-SCALED POWER
# ==========================================
# Trump Card reads the PP left AFTER this use, so the engines - which spend the point
# before swinging - can pass what they see. The move-button hint has not spent it yet
# and says so with pending=True.
TRUMP_CARD_POWER = {0: 200, 1: 80, 2: 60, 3: 50}
TRUMP_CARD_DEFAULT = 40


def trump_card_power(attacker, pending=False):
    """Power for Trump Card, rising sharply as its own PP runs out."""
    slot = find_move_slot(attacker, 'trump-card')
    left = slot.get('pp', 0) if slot else 0
    if pending:
        left = max(0, left - 1)
    return TRUMP_CARD_POWER.get(left, TRUMP_CARD_DEFAULT)


def resolve_dynamic_power(move_name, attacker, defender, pending=False):
    """
    Single entry point for every move whose base power is computed rather than stored.
    Returns None for ordinary moves so callers can fall back to the database value.
    """
    scaled = get_hp_scaled_power(move_name, attacker, defender)
    if scaled is not None:
        return scaled

    bond = get_friendship_power(move_name, attacker)
    if bond is not None:
        return bond

    # --- Resource-scaled ---
    if move_name == 'trump-card':
        return trump_card_power(attacker, pending=pending)

    if move_name == 'spit-up':
        # Nothing banked means the move fails outright, handled in the damage engine.
        return SPIT_UP_POWER_PER_STACK * get_stockpile(attacker) or None

    if move_name == 'hard-press':
        # Scales with how much fight the TARGET has left, unlike the Flail family.
        max_hp = defender.get('max_hp', 100) or 100
        return max(1, math.floor(100 * defender.get('current_hp', 0) / max_hp))

    # Fling reads whatever the user is holding, so the AI and the move button both need
    # it resolved here rather than at swing time.
    if move_name == 'fling':
        return get_fling_power(get_stored_item(attacker)) or None

    return get_stat_scaled_power(move_name, attacker, defender)

# ==========================================
# 🚨 TERRAIN-KEYED MOVES
# ==========================================
# Move-specific terrain bonuses, separate from the generic "terrain boosts its own type"
# rule. Both stack: Expanding Force is Psychic-type, so on Psychic Terrain it collects the
# generic 1.3x *and* its own 1.5x. All of these require the user to be grounded.
TERRAIN_POWER_MOVES = {
    'misty-explosion': ('misty', 1.5),
    'psyblade':        ('electric', 1.5),
    'expanding-force': ('psychic', 1.5),
}

# Terrain effects that shift the priority bracket rather than power
TERRAIN_PRIORITY_MOVES = {
    'grassy-glide': ('grassy', 1),
}

# Solar Beam and Solar Blade are dimmed by anything that blocks out the sun
SOLAR_MOVES = ['solar-beam', 'solar-blade']
SOLAR_DIMMING_WEATHER = ['rain', 'heavy-rain', 'sandstorm', 'hail', 'snow']

# Wrings extra damage out of a super-effective hit (5461/4096 in the games)
SUPER_EFFECTIVE_BONUS_MOVES = ['collision-course', 'electro-drift']

# ==========================================
# 🚨 CRITICAL HITS & ACCURACY OVERRIDES
# ==========================================
# Moves that always land a critical hit. Battle Armor and Shell Armor still shut them
# down - those abilities block criticals outright, not just the random roll.
ALWAYS_CRIT_MOVES = [
    'storm-throw', 'frost-breath', 'wicked-blow',
    'surging-strikes', 'zippy-zap', 'flower-trick',
]

# Moves that bypass the accuracy/evasion roll entirely. Shared by both engines so the
# two copies can no longer drift apart.
#
# The database stores these at 100 accuracy rather than NULL, so the list has to be
# curated - there is no data flag to derive it from. Note this only skips the accuracy
# roll: a semi-invulnerable target (Fly, Dig, Dive) is still untouchable, which is
# handled separately in the damage engine.
GUARANTEED_HIT_MOVES = [
    'aerial-ace', 'aura-sphere', 'disarming-voice', 'false-surrender',
    'feint-attack', 'flower-trick', 'kowtow-cleave', 'magical-leaf',
    'magnet-bomb', 'shadow-punch', 'shock-wave', 'smart-strike',
    'swift', 'vital-throw',
]

def is_crit_guaranteed(move_name, attacker):
    """True when this strike is a certainty rather than a roll."""
    if move_name in ALWAYS_CRIT_MOVES:
        return True
    return bool((attacker.get('volatile_statuses') or {}).get('laser_focus'))

# Effects that sit on a team's side of the field and tick down once per turn. Shared with
# both engines so the decay loops and the deployment list cannot fall out of step.
SIDE_SCREEN_MOVES = ['reflect', 'light-screen', 'aurora-veil', 'lucky-chant',
                     'safeguard', 'mist']

# Light Clay stretches the two DAMAGE screens only. Everything else here runs a flat
# five turns however the user is equipped.
FLAT_DURATION_SCREENS = {'lucky-chant', 'safeguard', 'mist'}

# ==========================================
# 🚨 PROTECTION MOVES
# ==========================================
# Full shields: block anything aimed at the user. Names must match the move database -
# it stores "kings-shield" and "silk-trap", not "king-shield"/"silky-trap".
STANDARD_SHIELDS = [
    'protect', 'detect', 'spiky-shield', 'kings-shield', 'baneful-bunker',
    'obstruct', 'silk-trap', 'burning-bulwark', 'max-guard',
]

# What a shield does to an attacker whose CONTACT move it just swallowed.
SHIELD_PUNISH = {
    'spiky-shield':    {'kind': 'chip',   'fraction': 1.0 / 8.0},
    'kings-shield':    {'kind': 'stat',   'stat': 'attack',  'amount': -1},
    'obstruct':        {'kind': 'stat',   'stat': 'defense', 'amount': -2},
    'silk-trap':       {'kind': 'stat',   'stat': 'speed',   'amount': -1},
    'baneful-bunker':  {'kind': 'status', 'status': 'poison'},
    'burning-bulwark': {'kind': 'status', 'status': 'burn'},
}

# Selective guards only stop one category of move and let everything else through.
SELECTIVE_GUARDS = {
    'crafty-shield': 'status',    # status moves only
    'mat-block':     'damaging',  # damaging moves only
    'quick-guard':   'priority',  # anything in a raised priority bracket
    'wide-guard':    'spread',    # multi-target attacks
}

# PokeAPI target strings that describe a spread move
SPREAD_TARGETS = ['all-opponents', 'all-other-pokemon', 'all-pokemon']

PROTECT_MOVES = STANDARD_SHIELDS + list(SELECTIVE_GUARDS)

def shield_blocks(protect_type, move_class, move_priority, move_target, move_name=None):
    """
    Decides whether an active shield actually stops this particular move.

    Full shields stop everything. Selective guards only cover their own category, so a
    Quick Guard does nothing against a normal-priority attack and a Crafty Shield does
    nothing against a damaging one.
    """
    # Urshifu's pair break through everything, Max Guard included
    if move_name in GMAX_SHIELD_BREAKERS:
        return False

    if protect_type in SELECTIVE_GUARDS:
        kind = SELECTIVE_GUARDS[protect_type]
        if kind == 'status':
            return move_class == 'status'
        if kind == 'damaging':
            return move_class != 'status'
        if kind == 'priority':
            return int(move_priority or 0) > 0
        if kind == 'spread':
            return str(move_target) in SPREAD_TARGETS
        return False

    # Anything else on the field is a full shield
    return True

# ==========================================
# 🚨 TYPE-CHANGE MOVES
# ==========================================
# Held items that dictate a signature move's element. Suffix-driven so the whole family
# is covered without listing all seventeen of each.
ITEM_TYPE_MOVES = {
    'judgment':     'plate',    # Arceus Plates
    'techno-blast': 'drive',    # Genesect Drives
    'multi-attack': 'memory',   # Silvally Memories
}

PLATE_TYPES = {
    'draco-plate': 'dragon', 'dread-plate': 'dark', 'earth-plate': 'ground',
    'fist-plate': 'fighting', 'flame-plate': 'fire', 'icicle-plate': 'ice',
    'insect-plate': 'bug', 'iron-plate': 'steel', 'meadow-plate': 'grass',
    'mind-plate': 'psychic', 'pixie-plate': 'fairy', 'sky-plate': 'flying',
    'splash-plate': 'water', 'spooky-plate': 'ghost', 'stone-plate': 'rock',
    'toxic-plate': 'poison', 'zap-plate': 'electric',
}

DRIVE_TYPES = {
    'burn-drive': 'fire', 'chill-drive': 'ice',
    'douse-drive': 'water', 'shock-drive': 'electric',
}

# Camouflage reads the ground it is standing on
CAMOUFLAGE_TYPES = {
    'electric': 'electric', 'grassy': 'grass',
    'misty': 'fairy', 'psychic': 'psychic',
}

# Moves that burn away one of the user's own types once they connect
TYPE_SHEDDING_MOVES = {'burn-up': 'fire', 'double-shock': 'electric'}

def resolve_item_move_type(move_name, held_item, default_type):
    """
    Element for the signature moves that read a held item. Falls back to the stored type
    when the matching item is absent, which is what the games do for a bare Arceus.
    """
    kind = ITEM_TYPE_MOVES.get(move_name)
    if not kind:
        return default_type

    item = (held_item or '').lower().replace(' ', '-')

    if kind == 'plate':
        return PLATE_TYPES.get(item, default_type)
    if kind == 'drive':
        return DRIVE_TYPES.get(item, default_type)
    if kind == 'memory':
        # Memories are uniformly "<type>-memory"
        if item.endswith('-memory'):
            return item[:-len('-memory')]
    return default_type

def find_resisting_type(incoming_type, type_chart):
    """
    A type that would resist (or shrug off) the given attacking type. Used by
    Conversion 2. Prefers an outright immunity, then any resistance.
    """
    immunities, resistances = [], []
    for candidate in type_chart.get(incoming_type, {}):
        effectiveness = type_chart[incoming_type].get(candidate, 1.0)
        if effectiveness == 0:
            immunities.append(candidate)
        elif effectiveness < 1.0:
            resistances.append(candidate)

    pool = immunities or resistances
    return random.choice(pool) if pool else None

# ==========================================
# 🧬 ABILITY REWRITES
# ==========================================
# Abilities welded to a species' form or identity. Nothing switches these off, paints over
# them, or trades them away - they are the machinery that drives the form change itself.
FORM_LOCKED_ABILITIES = {
    'as-one-glastrier', 'as-one-spectrier', 'battle-bond', 'comatose', 'commander',
    'disguise', 'gulp-missile', 'ice-face', 'multitype', 'power-construct',
    'rks-system', 'schooling', 'shields-down', 'stance-change', 'zen-mode',
    'zero-to-hero',
}

# Abilities that re-read the field the instant they land, so handing out a copy is
# meaningless. Skill Swap can still trade these because it moves them rather than
# duplicating them.
FIELD_READING_ABILITIES = {
    'flower-gift', 'forecast', 'imposter', 'power-of-alchemy', 'receiver', 'trace',
}

# Gastro Acid / Core Enforcer. Neutralizing Gas is already an abilities-off field, so a
# second layer of suppression has nothing left to switch off.
UNSUPPRESSABLE_ABILITIES = FORM_LOCKED_ABILITIES | {'neutralizing-gas'}

# What refuses to be overwritten ON THE TARGET by Worry Seed, Simple Beam or Entrainment.
# Truant is here because the games will not let you hand the drawback away.
UNREPLACEABLE_ABILITIES = FORM_LOCKED_ABILITIES | {'truant'}

# What cannot be READ OFF a specimen by Role Play, Doodle or Entrainment.
UNCOPYABLE_ABILITIES = (FORM_LOCKED_ABILITIES | FIELD_READING_ABILITIES |
                        {'hunger-switch', 'illusion', 'neutralizing-gas', 'wonder-guard'})

# Skill Swap trades rather than copies, so the field-readers and Wonder Guard are fair game.
UNSWAPPABLE_ABILITIES = FORM_LOCKED_ABILITIES | {'hunger-switch', 'illusion',
                                                 'neutralizing-gas'}

# Moves that staple a fixed ability onto the target
ABILITY_IMPLANT_MOVES = {'worry-seed': 'insomnia', 'simple-beam': 'simple'}


def pretty_ability(ability):
    """'sheer-force' -> 'Sheer Force', for combat log lines."""
    return (ability or 'none').replace('-', ' ').title()


def pretty_item(item):
    """'choice-scarf' -> 'Choice Scarf', for combat log lines."""
    return (item or 'none').replace('-', ' ').title()


def get_stored_ability(pokemon):
    """
    The ability written on the specimen's sheet, normalised, ignoring suppression.

    This is what the ability-manipulation moves read: Role Play can still copy off a
    target that is sitting under a Gastro Acid, because the ability is switched off
    rather than erased.
    """
    if pokemon is None:
        return 'none'
    return (pokemon.get('ability') or 'none').lower().replace(' ', '-')


def get_active_ability(pokemon):
    """
    The ability actually in force right now - 'none' while it is suppressed.

    Gastro Acid and Core Enforcer switch an ability off without erasing it, so the stored
    name has to survive in order to come back when the specimen is withdrawn. Every
    battle-time read goes through here so a suppressed ability is genuinely inert; only
    code that PERSISTS an ability (evolution, Mega forms) touches ['ability'] directly.
    """
    if pokemon is None:
        return 'none'
    if (pokemon.get('volatile_statuses') or {}).get('ability_suppressed'):
        return 'none'
    return get_stored_ability(pokemon)


def set_active_ability(pokemon, new_ability):
    """
    Overwrite an ability for the rest of the battle, remembering the original so that
    restore_base_ability can put it back when the specimen leaves the field.
    """
    if pokemon is None:
        return
    if '_base_ability' not in pokemon:
        pokemon['_base_ability'] = pokemon.get('ability')
    pokemon['ability'] = new_ability
    # Suppression is a property of the SLOT, not of the ability sitting in it, so a
    # Worry Seed onto a Gastro Acid'd target lands an Insomnia that is still switched off.


def restore_base_ability(pokemon):
    """
    Undo ability rewrites and suppression when a specimen is withdrawn. Like stat stages
    and raw-stat rewrites, these are tied to the slot rather than to the specimen.
    """
    if pokemon is None:
        return
    if '_base_ability' in pokemon:
        pokemon['ability'] = pokemon.pop('_base_ability')
    (pokemon.get('volatile_statuses') or {}).pop('ability_suppressed', None)


def suppress_ability(pokemon):
    """
    Switch a specimen's ability off. Returns (worked, reason) so Gastro Acid can print a
    failure line and Core Enforcer can stay quiet.
    """
    stored = get_stored_ability(pokemon)
    if stored in ('none', ''):
        return False, "There was no ability to suppress!"
    if stored in UNSUPPRESSABLE_ABILITIES:
        return False, f"{pretty_ability(stored)} cannot be shut down!"
    if (pokemon.get('volatile_statuses') or {}).get('ability_suppressed'):
        return False, "Its ability is already suppressed!"

    pokemon.setdefault('volatile_statuses', {})['ability_suppressed'] = True
    return True, stored

# The status half of the block - Core Enforcer is scored on its power like any attack.
ABILITY_MANIPULATION_MOVES = {'gastro-acid', 'worry-seed', 'simple-beam', 'entrainment',
                              'role-play', 'doodle', 'skill-swap'}


def ability_move_would_land(move_name, attacker, defender):
    """
    Whether an ability-manipulation move would achieve anything in this matchup.

    The NPC AI reads this so it stops spending turns on a Gastro Acid that is guaranteed
    to bounce off a Stance Change, or a Skill Swap into a mirror match. Returns None for
    moves this does not cover.

    This mirrors the guards in calculate_damage rather than sharing them, because the
    handlers there each need their own failure message. The test suite pins the two
    together across a matrix of ability pairings so they cannot drift apart.
    """
    if move_name not in ABILITY_MANIPULATION_MOVES:
        return None

    mine = get_stored_ability(attacker)
    theirs = get_stored_ability(defender)

    if move_name == 'gastro-acid':
        return (theirs != 'none' and theirs not in UNSUPPRESSABLE_ABILITIES
                and not (defender.get('volatile_statuses') or {}).get('ability_suppressed'))

    if move_name in ABILITY_IMPLANT_MOVES:
        return (theirs not in UNREPLACEABLE_ABILITIES
                and theirs != ABILITY_IMPLANT_MOVES[move_name])

    if move_name == 'entrainment':
        return (mine != 'none' and mine not in UNCOPYABLE_ABILITIES
                and theirs not in UNREPLACEABLE_ABILITIES and theirs != mine)

    if move_name in ['role-play', 'doodle']:
        return (theirs != 'none' and theirs not in UNCOPYABLE_ABILITIES
                and mine not in FORM_LOCKED_ABILITIES and mine != theirs)

    # skill-swap
    return (mine not in UNSWAPPABLE_ABILITIES and theirs not in UNSWAPPABLE_ABILITIES
            and mine != theirs)

# ==========================================
# 🎒 ITEM INTERACTIONS
# ==========================================
# Items bolted to their holder. Nothing swaps, steals, flings, burns or corrodes these.
UNTRANSFERABLE_ITEMS = {
    'red-orb', 'blue-orb', 'griseous-orb', 'rusted-sword', 'rusted-shield',
}

# Items whose name ends in 'ite' but which are ordinary held items, not Mega Stones.
NON_MEGA_ITE_ITEMS = {'eviolite'}

# Fling's base power is item-dependent. Anything not listed uses FLING_DEFAULT_POWER,
# which is what the overwhelming majority of held items throw for.
FLING_DEFAULT_POWER = 30
FLING_POWER = {
    'iron-ball': 130,
    'hard-stone': 100, 'rare-bone': 100,
    'deep-sea-tooth': 90, 'thick-club': 90, 'grip-claw': 90,
    'assault-vest': 80, 'dubious-disc': 80, 'electirizer': 80, 'magmarizer': 80,
    'odd-keystone': 80, 'oval-stone': 80, 'prism-scale': 80, 'protector': 80,
    'reaper-cloth': 80, 'sachet': 80, 'whipped-dream': 80,
    'dawn-stone': 80, 'dusk-stone': 80, 'fire-stone': 80, 'ice-stone': 80,
    'leaf-stone': 80, 'moon-stone': 80, 'shiny-stone': 80, 'sun-stone': 80,
    'thunder-stone': 80, 'water-stone': 80,
    'dragon-fang': 70, 'poison-barb': 70,
    'adamant-orb': 60, 'lustrous-orb': 60, 'damp-rock': 60, 'heat-rock': 60,
    'macho-brace': 60, 'rocky-helmet': 60, 'stick': 60,
    'sharp-beak': 50,
    'eviolite': 40, 'icy-rock': 40, 'lucky-punch': 40,
    # The featherweight tier - throwing these barely registers
    'choice-band': 10, 'choice-scarf': 10, 'choice-specs': 10, 'focus-sash': 10,
    'leftovers': 10, 'air-balloon': 10, 'bright-powder': 10, 'white-herb': 10,
    'mental-herb': 10, 'shed-shell': 10, 'wide-lens': 10, 'zoom-lens': 10,
    'muscle-band': 10, 'wise-glasses': 10, 'binding-band': 10, 'safety-goggles': 10,
    'metronome': 10, 'black-sludge': 10, 'light-clay': 10, 'power-herb': 10,
}

# Items that inflict something on the target when flung at them
FLING_AILMENTS = {
    'flame-orb': 'burn', 'toxic-orb': 'poison', 'poison-barb': 'poison',
    'light-ball': 'paralysis', 'kings-rock': 'flinch', 'razor-fang': 'flinch',
}

# Moves that read the target's berry rather than destroying it outright
BERRY_EATING_MOVES = {'bug-bite', 'pluck'}

# ==========================================
# 🚫 MOVE RESTRICTIONS
# ==========================================
# Four separate ways a move can be locked out. They are gathered behind one predicate
# because a restriction has to be honoured in three places at once - the player's move
# buttons, the NPC's move selection, and the turn itself - and any of the three drifting
# out of step means the restriction is either invisible or unenforceable.

def find_move_slot(pokemon, move_name):
    """The live move dict on a specimen, so PP can be read or spent. None if absent."""
    if pokemon is None or not move_name:
        return None
    for slot in (pokemon.get('moves') or []):
        if slot.get('name') == move_name:
            return slot
    return None


def drain_move_pp(pokemon, move_name, amount=None):
    """
    Spend PP off one specific move. amount=None empties it outright, which is what Grudge
    does. Returns how much was actually taken, so callers can report it and can treat 0 as
    "there was nothing to drain".
    """
    slot = find_move_slot(pokemon, move_name)
    if not slot:
        return 0

    current = slot.get('pp', 0)
    if current <= 0:
        return 0

    taken = current if amount is None else min(current, amount)
    slot['pp'] = current - taken
    return taken


# ==========================================
# 🌪️ G-MAX SIGNATURE EFFECTS
# ==========================================
# Most of the G-Max roster expresses itself through the ordinary move payload - an
# ailment, a stat drop, a lingering hazard - and the engines already inject those. The
# ones gathered here cannot: their signature is a mechanic rather than a payload, so each
# reaches for machinery built elsewhere in this file.
GMAX_EFFECTS = {
    'G-Max Chi Strike':  'crit_boost',
    'G-Max Depletion':   'sap_pp',
    'G-Max Finale':      'heal_party',
    'G-Max Gold Rush':   'coins',
    'G-Max Meltdown':    'torment',
    'G-Max Replenish':   'recycle',
    'G-Max Resonance':   'aurora_veil',
    'G-Max Sandblast':   'bind',
    'G-Max Sweetness':   'cure_party',
    'G-Max Terror':      'trap',
    'G-Max Wind Rage':   'clear_hazards',
}

# G-Max Gold Rush scatters coins that are picked up after the battle rather than paying
# out mid-turn. The amount rides on the user, so the reward path can total it up across
# the whole team; PvP simply never reads it, which is why the coins only cash in PvE.
COIN_SCATTER_PER_LEVEL = 5


def scatter_coins(attacker):
    """Add this user's coin scatter to its running total. Returns the amount added."""
    if attacker is None:
        return 0
    coins = max(1, COIN_SCATTER_PER_LEVEL * attacker.get('level', 50))
    attacker['_coins_scattered'] = attacker.get('_coins_scattered', 0) + coins
    return coins


def collected_coins(team):
    """Everything a team scattered over the course of a battle."""
    return sum((m.get('_coins_scattered') or 0) for m in (team or []) if m)


# The three that hit for a flat 160 and shrug off the target's ability entirely.
GMAX_FIXED_POWER = {
    'G-Max Drum Solo': 160, 'G-Max Fireball': 160, 'G-Max Hydrosnipe': 160,
}

# Urshifu's pair go straight through Protect, Detect and Max Guard.
GMAX_SHIELD_BREAKERS = {'G-Max One Blow', 'G-Max Rapid Flow'}

# What Depletion takes, and how long Sandblast holds on for.
GMAX_PP_DRAIN = 2
GMAX_BIND_TURNS = (4, 5)


def gmax_ignores_ability(move_name):
    """Whether this G-Max move pays no attention to the target's ability."""
    return move_name in GMAX_FIXED_POWER


def apply_gmax_effect(move_name, attacker, defender, user_party=None,
                      user_hazards=None, target_hazards=None, held_item='none'):
    """
    Fire a G-Max move's signature effect. Returns a log fragment, or '' when there is
    nothing to say.

    Deliberately reuses the mechanics built for ordinary moves - the trap helper, the PP
    drain, the party cleanse, the screen dictionary - rather than growing a parallel set.
    """
    effect = GMAX_EFFECTS.get(move_name)
    if not effect:
        return ""

    name = defender['name'].capitalize() if defender else 'the target'
    mine = attacker['name'].capitalize() if attacker else 'the user'

    if effect == 'crit_boost':
        attacker.setdefault('volatile_statuses', {})['focus_energy'] = True
        return f" 🥊 {mine} is fired up - its critical hit ratio rose!"

    if effect == 'sap_pp':
        sapped = defender.get('last_move_used')
        taken = drain_move_pp(defender, sapped, GMAX_PP_DRAIN) if sapped else 0
        if not taken:
            return ""
        return (f" 🔻 {name}'s {sapped.replace('-', ' ').title()} lost {taken} PP!")

    if effect == 'heal_party':
        mended = []
        for member in (user_party or [attacker]):
            if member is None or member.get('current_hp', 0) <= 0:
                continue
            max_hp = member.get('max_hp', 100)
            if member['current_hp'] >= max_hp:
                continue
            member['current_hp'] = min(max_hp, member['current_hp'] + max(1, math.floor(max_hp / 6)))
            mended.append(member['name'].capitalize())
        return f" 🍰 The whole party shared the treat - {', '.join(mended)} recovered!" if mended else ""

    if effect == 'coins':
        # The confusion half rides on the ordinary ailment payload; this is the money
        coins = scatter_coins(attacker)
        return f" 🪙 Coins scattered everywhere! ({coins} to collect afterwards)"

    if effect == 'torment':
        if (defender.get('volatile_statuses') or {}).get('torment'):
            return ""
        defender.setdefault('volatile_statuses', {})['torment'] = True
        return f" 🔩 {name} cannot use the same move twice in a row!"

    if effect == 'recycle':
        # The item-persistence work already records exactly what was used up
        spent = sorted(attacker.get('_consumed_items') or [])
        if not spent or get_stored_item(attacker) != 'none':
            return ""
        restored = spent[0]
        attacker['held_item'] = restored
        attacker['_consumed_items'].discard(restored)
        return f" 🫐 {mine} found its {pretty_item(restored)} again!"

    if effect == 'aurora_veil':
        if user_hazards is None or user_hazards.get('aurora-veil', 0) > 0:
            return ""
        # Unlike the ordinary move, this one needs no hail behind it
        user_hazards['aurora-veil'] = 8 if held_item == 'light-clay' else 5
        return f" 🌌 An aurora rose to shield {mine}'s team!"

    if effect == 'bind':
        volatiles = defender.setdefault('volatile_statuses', {})
        if volatiles.get('partially_trapped', 0) > 0:
            return ""
        volatiles['partially_trapped'] = random.randint(*GMAX_BIND_TURNS)
        return f" 🌪️ {name} was caught in a swirl of sand!"

    if effect == 'cure_party':
        cured = cure_party_status(user_party, attacker)
        return f" 🍏 The sweetness revived {', '.join(cured)}!" if cured else ""

    if effect == 'trap':
        if apply_trap(defender):
            return f" 👻 {name} was gripped by fear and cannot escape!"
        return f" 👻 {name} shrugged off the terror!"

    if effect == 'clear_hazards':
        swept = 0
        for side in (user_hazards, target_hazards):
            if side is None:
                continue
            for hazard in ['stealth-rock', 'spikes', 'toxic-spikes', 'sticky-web', 'steelsurge']:
                if side.get(hazard):
                    side[hazard] = False if isinstance(side.get(hazard), bool) else 0
                    swept += 1
        return " 🌀 The gale swept the battlefield clean!" if swept else ""

    return ""


# ==========================================
# 🎯 GUARANTEED ACCURACY, GROUNDING AND SIDE GUARDS
# ==========================================
# Lock-On and Mind Reader are the same move under two names.
LOCK_ON_MOVES = {'lock-on', 'mind-reader'}

# How long a specimen stays airborne.
LEVITATION_TURNS = {'magnet-rise': 5, 'telekinesis': 3}


def consume_lock_on(attacker):
    """
    Spend a standing Lock-On, if there is one. Returns whether the next attack is
    therefore guaranteed to land.

    Consumed rather than merely read: it covers exactly one attack.
    """
    volatiles = (attacker or {}).get('volatile_statuses') or {}
    return bool(volatiles.pop('locked_on', None))


def side_is_guarded(side_hazards, guard):
    """Whether a side has an active Safeguard or Mist."""
    return bool((side_hazards or {}).get(guard, 0) > 0)


# ==========================================
# 💗 RESTORATION AND SACRIFICE
# ==========================================
# Aqua Ring trickles back a sixteenth each turn, the same share Ingrain does.
AQUA_RING_FRACTION = 16

# Refresh scrubs the three conditions that wear off on their own, and deliberately not
# sleep or freeze - those have their own timers and countering them is the point of Rest.
REFRESH_CURES = {'paralysis', 'poison', 'burn'}

# The user faints outright; the replacement arrives whole. Lunar Dance also refills PP,
# which is the only thing separating the two.
SACRIFICE_MOVES = {'healing-wish': False, 'lunar-dance': True}

REVIVAL_BLESSING_FRACTION = 0.5


def apply_healing_wish(incoming, restores_pp=False):
    """
    Pay out a banked Healing Wish to whoever takes the vacated slot.

    Returns a log fragment, or '' when the replacement needed nothing.
    """
    if incoming is None or incoming.get('current_hp', 0) <= 0:
        return ""

    max_hp = incoming.get('max_hp', 100)
    mended = incoming['current_hp'] < max_hp
    had_status = (incoming.get('status_condition') or {}).get('name')

    refilled = False
    if restores_pp:
        for slot in (incoming.get('moves') or []):
            if slot.get('pp', 0) < slot.get('max_pp', 0):
                slot['pp'] = slot['max_pp']
                refilled = True

    if not (mended or had_status or refilled):
        return ""

    incoming['current_hp'] = max_hp
    incoming['status_condition'] = None

    note = f"💗 The departed's wish restored {incoming['name'].capitalize()} completely"
    return note + (" - and refreshed its moves!" if refilled else "!")


def revive_fallen(party, exclude=None):
    """
    Bring one fainted party member back at half health. Returns (name, healed) so the
    caller can report it, or (None, 0) when there is nobody to revive.
    """
    for member in (party or []):
        if member is None or member is exclude:
            continue
        if member.get('current_hp', 0) > 0:
            continue

        max_hp = member.get('max_hp', 100)
        member['current_hp'] = max(1, math.floor(max_hp * REVIVAL_BLESSING_FRACTION))
        member['status_condition'] = None
        return member.get('name', 'a specimen').capitalize(), member['current_hp']

    return None, 0


# ==========================================
# 🪞 REDIRECTION AND INTERCEPTION
# ==========================================
# Four of these arm an interceptor that changes how the OPPONENT'S next move resolves,
# which is why Magic Coat and Snatch both sit at +4 priority - they have to be standing
# before the thing they intercept arrives.
POWDER_RECOIL_FRACTION = 0.25

# Magic Coat cannot bounce a move that was itself bounced, nor the interceptors.
BOUNCE_IMMUNE_MOVES = {
    'magic-coat', 'snatch', 'struggle', 'sketch', 'mimic', 'transform', 'metronome',
    'me-first', 'mirror-move', 'copycat', 'assist', 'sleep-talk',
}

# Snatch only takes what the user was doing to ITSELF; these are the self-aimed targets.
SNATCHABLE_TARGETS = {'user', 'users-field', 'user-and-allies', 'all-allies'}


def magic_coat_bounces(defender, move):
    """
    Whether the defender's Magic Coat reflects this move back at whoever threw it.

    Only status moves aimed AT the coat holder bounce - a self-buff has nothing to
    reflect, and a damaging move goes straight through.
    """
    if not (defender.get('volatile_statuses') or {}).get('magic_coat'):
        return False
    if move.get('class') != 'status':
        return False

    name = (move.get('name') or '').lower().replace(' ', '-')
    if name in BOUNCE_IMMUNE_MOVES:
        return False

    return 'selected-pokemon' in str(move.get('target', '')) or \
           'opponent' in str(move.get('target', ''))


def snatch_steals(thief, move):
    """
    Whether the thief's Snatch takes this move and uses it instead.

    Snatch is the mirror of Magic Coat: it takes what the user was doing FOR itself -
    a boost, a heal, a screen - rather than what was being done to somebody.
    """
    if not (thief.get('volatile_statuses') or {}).get('snatch'):
        return False
    if move.get('class') != 'status':
        return False

    name = (move.get('name') or '').lower().replace(' ', '-')
    if name in BOUNCE_IMMUNE_MOVES:
        return False

    return str(move.get('target', '')) in SNATCHABLE_TARGETS


def clear_interceptors(pokemon):
    """
    Magic Coat, Snatch and Powder all last a single turn. Cleared alongside the other
    per-turn volatiles so an unused one cannot linger into the next round.
    """
    if pokemon is None:
        return
    volatiles = pokemon.get('volatile_statuses') or {}
    for flag in ('magic_coat', 'snatch', 'powder'):
        volatiles.pop(flag, None)


# ==========================================
# 🎭 COPY AND MIMICRY MOVES
# ==========================================
# These do not resolve themselves - they name a DIFFERENT move, which the engines then
# fetch and run in their place. Resolution is kept here, pure and testable; the engines
# only have to hydrate the payload and re-dispatch.
COPY_MOVES = {'mirror-move', 'copycat', 'me-first', 'assist', 'metronome'}

# Nothing in the mimicry family can copy another member of it, or Struggle - both would
# either recurse or have nothing behind them to copy.
UNCOPYABLE_MOVES = {
    'assist', 'copycat', 'me-first', 'metronome', 'mimic', 'mirror-move', 'sketch',
    'sleep-talk', 'nature-power', 'struggle', 'transform',
}

# Me First rewards going first with half again the power.
ME_FIRST_MULTIPLIER = 1.5


def can_be_copied(move_name):
    """Whether the mimicry family is allowed to reach for this move."""
    return bool(move_name) and move_name not in UNCOPYABLE_MOVES


def resolve_copied_move(move_name, attacker, defender, party=None,
                        last_move_overall=None, pool=None):
    """
    Which move a copy move actually performs.

    Returns (chosen_move, reason). `chosen_move` is None when the copy fails, and
    `reason` is the line to print in that case.

    Each member reaches somewhere different:
      * Mirror Move - whatever the target last threw
      * Copycat     - the last move used by ANYONE, which the engines track on the battle
      * Me First    - what the target is winding up RIGHT NOW, so it needs to move first
      * Assist      - a random move off the rest of the party
      * Metronome   - anything at all
    """
    if move_name == 'mirror-move':
        copied = defender.get('last_move_used')
        if not can_be_copied(copied):
            return None, "But it failed! There was no move to mirror!"
        return copied, ""

    if move_name == 'copycat':
        if not can_be_copied(last_move_overall):
            return None, "But it failed! There was nothing to copy!"
        return last_move_overall, ""

    if move_name == 'me-first':
        # Only works while the target is still winding up, and never on a status move
        if defender.get('acted_this_turn'):
            return None, "But it failed! The target has already moved!"
        incoming = defender.get('_committed_move_name')
        if defender.get('_committed_move') == 'status':
            return None, "But it failed! Me First cannot steal a status move!"
        if not can_be_copied(incoming):
            return None, "But it failed! There was nothing to take!"
        return incoming, ""

    if move_name == 'assist':
        # Every move the REST of the party knows - the user's own are not eligible
        borrowed = [m.get('name')
                    for mate in (party or []) if mate is not None and mate is not attacker
                    for m in (mate.get('moves') or [])
                    if can_be_copied(m.get('name'))]
        if not borrowed:
            return None, "But it failed! There was no ally move to borrow!"
        return random.choice(borrowed), ""

    if move_name == 'metronome':
        options = list(pool or [])
        if not options:
            return None, "But it failed! Its finger would not budge!"
        return random.choice(options), ""

    return None, ""


def apply_sketch(attacker, defender):
    """
    Sketch overwrites its own slot with the target's last move PERMANENTLY.

    The in-memory half happens here; the specimen is stamped with '_sketched' so the
    engine knows to write the new movelist back to caught_pokemon. Doing the database
    work here would put I/O inside the damage formula, which nothing else does.
    """
    copied = defender.get('last_move_used')
    if not can_be_copied(copied):
        return False, "But it failed! There was no move to sketch!"

    slot = find_move_slot(attacker, 'sketch')
    if slot is None:
        return False, "But it failed! There was no slot to overwrite!"
    if find_move_slot(attacker, copied) is not None:
        return False, "But it failed! It already knows that move!"

    slot['name'] = copied
    attacker['_sketched'] = copied
    return True, (f"✏️ {attacker['name'].capitalize()} sketched "
                  f"{copied.replace('-', ' ').title()} - and will not forget it!")


def apply_mimic(attacker, defender):
    """
    Mimic overwrites its own slot with the target's last move for the rest of the battle.

    Returns (worked, message). The replacement carries 5 PP rather than the copied move's
    own, and the original comes back when the specimen is withdrawn, which is why the
    engines never persist it.
    """
    copied = defender.get('last_move_used')
    if not can_be_copied(copied):
        return False, "But it failed! There was no move to mimic!"

    slot = find_move_slot(attacker, 'mimic')
    if slot is None:
        return False, "But it failed! There was no slot to overwrite!"
    if find_move_slot(attacker, copied) is not None:
        return False, "But it failed! It already knows that move!"

    slot['name'] = copied
    slot['pp'] = slot['max_pp'] = 5
    return True, (f"🎭 {attacker['name'].capitalize()} mimicked "
                  f"{copied.replace('-', ' ').title()}!")


# ==========================================
# ⚡ PRIORITY-CONDITIONAL MOVES
# ==========================================
# Only usable the moment their user arrives on the field.
FIRST_TURN_MOVES = {'fake-out', 'first-impression'}

# Moves that reorder a SIDE rather than targeting anyone. This engine fields exactly one
# specimen per side, so there is no third party to shuffle - they are kept here so the
# behaviour is stated in one place rather than silently doing nothing.
TURN_ORDER_MOVES = {'quash', 'after-you'}


def is_first_turn_out(pokemon):
    """Whether the specimen has yet to finish a turn on the field."""
    if pokemon is None:
        return False
    return (pokemon.get('turns_on_field') or 0) == 0


def is_readying_attack(pokemon):
    """
    Whether this specimen is winding up an attack it has not yet thrown - which is the
    only thing Sucker Punch can interrupt.

    The engines stamp '_committed_move' with the class of whatever was locked in for the
    turn, so the queue's knowledge of both moves is available before either resolves.
    """
    if pokemon is None or pokemon.get('acted_this_turn'):
        return False
    committed = pokemon.get('_committed_move')
    return bool(committed) and committed != 'status'


# ==========================================
# 🛑 TRAPPING
# ==========================================
# Moves that pin the target in place until it faints or the trapper leaves.
HARD_TRAP_MOVES = {'anchor-shot', 'block', 'mean-look', 'spider-web',
                   'spirit-shackle', 'thousand-waves'}

# Fairy Lock binds the WHOLE field rather than one target, and only for the next turn.
FAIRY_LOCK_TURNS = 2


def can_be_trapped(pokemon):
    """
    Ghost-types walk straight through anything that would hold them.

    The engines already honoured this for Shadow Tag but not for the trapping MOVES,
    which set their flag unconditionally - so a Spider Web used to pin a Gengar.
    """
    if pokemon is None:
        return False
    return 'ghost' not in (pokemon.get('types') or [])


def apply_trap(pokemon):
    """Pin a specimen in place. Returns whether it actually took hold."""
    if not can_be_trapped(pokemon):
        return False
    pokemon.setdefault('volatile_statuses', {})['hard_trapped'] = True
    return True


def is_trapped(pokemon, opponent=None):
    """
    Whether this specimen is barred from switching out.

    One home for what the engines had copy-pasted at three sites, so the Ghost exemption
    cannot apply to some trapping sources and not others. Fairy Lock is deliberately
    outside that exemption: it pins the whole field rather than targeting anybody.
    """
    if pokemon is None:
        return False

    volatiles = pokemon.get('volatile_statuses') or {}
    if volatiles.get('fairy_lock'):
        return True

    if not can_be_trapped(pokemon):
        return False

    if volatiles.get('partially_trapped', 0) > 0 or volatiles.get('hard_trapped'):
        return True
    if opponent is not None and get_active_ability(opponent) == 'shadow-tag':
        return True

    return False


# ==========================================
# 🪆 SUBSTITUTE
# ==========================================
# A decoy that soaks hits until its own HP runs out. Built here because Shed Tail is
# meaningless without it - the move's whole purpose is to hand a live substitute to the
# replacement. The stored value IS the decoy's remaining HP.
#
# Each move pays for a decoy worth exactly what it cost the user.
SUBSTITUTE_MOVES = {'substitute': 0.25, 'shed-tail': 0.5}

# Sound goes straight through a substitute, as does Infiltrator.
SOUND_MOVES = {
    'boomburst', 'bug-buzz', 'chatter', 'clanging-scales', 'clangorous-soul',
    'clangorous-soulblaze', 'confide', 'disarming-voice', 'echoed-voice', 'eerie-spell',
    'grass-whistle', 'growl', 'heal-bell', 'howl', 'hyper-voice', 'metal-sound',
    'noble-roar', 'overdrive', 'parting-shot', 'perish-song', 'psychic-noise',
    'relic-song', 'roar', 'round', 'screech', 'shadow-panic', 'sing', 'snarl',
    'snore', 'sparkling-aria', 'supersonic', 'torch-song', 'uproar',
}


def substitute_hp(pokemon):
    """Remaining HP on the specimen's decoy, or 0 when it has none."""
    if pokemon is None:
        return 0
    return (pokemon.get('volatile_statuses') or {}).get('substitute', 0) or 0


def create_substitute(pokemon, fraction):
    """
    Spend HP to put up a decoy. Returns (worked, message).

    The user must have MORE than the cost - paying exactly its remaining HP would be
    suicide, and the games refuse it rather than allowing that.
    """
    if pokemon is None:
        return False, "But it failed!"
    if substitute_hp(pokemon):
        return False, "But it failed! It already has a substitute!"

    max_hp = pokemon.get('max_hp', 100)
    cost = max(1, math.floor(max_hp * fraction))
    if pokemon.get('current_hp', 0) <= cost:
        return False, "But it failed! It does not have the health to spare!"

    pokemon['current_hp'] -= cost
    pokemon.setdefault('volatile_statuses', {})['substitute'] = cost
    return True, (f"🪆 {pokemon['name'].capitalize()} put up a substitute! "
                  f"(-{cost} HP)")


def substitute_intercepts(defender, move, attacker=None):
    """Whether the target's decoy takes this hit rather than the target itself."""
    if not substitute_hp(defender):
        return False

    name = (move.get('name') or '').lower().replace(' ', '-') if isinstance(move, dict) else str(move)
    if name in SOUND_MOVES:
        return False
    if attacker is not None and get_active_ability(attacker) == 'infiltrator':
        return False
    return True


def absorb_with_substitute(defender, damage):
    """
    Pour damage into the decoy. Returns (damage_that_reaches_the_specimen, message).

    Overflow is thrown away rather than carrying through - a substitute that breaks
    absorbs the whole blow, however big it was.
    """
    volatiles = defender.setdefault('volatile_statuses', {})
    remaining = volatiles.get('substitute', 0) or 0
    if remaining <= 0:
        return damage, ""

    if damage < remaining:
        volatiles['substitute'] = remaining - damage
        return 0, " 🪆 The substitute took the hit!"

    volatiles.pop('substitute', None)
    return 0, " 🪆 The substitute broke!"


# ==========================================
# 💢 STRUGGLE
# ==========================================
# The last resort, for a specimen with no legal move left - out of PP, or locked out by
# Disable, Taunt, Torment and Imprison between them.
STRUGGLE_RECOIL_FRACTION = 0.25


def struggle_move():
    """
    A fresh Struggle payload, built rather than read from base_moves.

    The stored row is Normal-type, which would let a Ghost shrug Struggle off entirely -
    the one thing it must never do. It is returned as a new dict each call so callers can
    mutate it without poisoning the next one.
    """
    return {
        'name': 'struggle', 'base_name': 'struggle',
        'type': 'typeless', 'power': 50, 'accuracy': 1000, 'class': 'physical',
        'target': 'defender', 'ailment': 'none', 'ailment_chance': 0,
        'stat_name': 'none', 'stat_change': 0, 'stat_chance': 0,
        'status_type': 'none', 'status_chance': 0,
        'healing': 0, 'drain': 0, 'priority': 0, 'pp': 1, 'max_pp': 1,
    }


def apply_struggle_recoil(attacker):
    """Struggle costs the user a quarter of its maximum HP. Returns the damage taken."""
    if attacker is None:
        return 0
    recoil = max(1, math.floor(attacker.get('max_hp', 100) * STRUGGLE_RECOIL_FRACTION))
    attacker['current_hp'] = max(0, attacker.get('current_hp', 0) - recoil)
    return recoil


def move_is_restricted(pokemon, move, opponent=None):
    """
    Why this move cannot be chosen right now, or None if it is free to use.

    Returns a short human-readable reason so the same call can drive a disabled button,
    an AI filter and a "but it failed" line without three different vocabularies.

    Imprison is the odd one out: it lives on the OPPONENT and seals whatever moves that
    specimen knows, so the check needs both sides of the field.
    """
    if pokemon is None or move is None:
        return None

    if isinstance(move, dict):
        name = move.get('name')
        move_class = move.get('class')
    else:
        name = move
        move_class = None

    volatiles = pokemon.get('volatile_statuses') or {}

    disabled = volatiles.get('disable') or {}
    if disabled.get('move') and disabled['move'] == name:
        return "disabled"

    if volatiles.get('taunt') and move_class == 'status':
        return "taunted"

    # Torment blocks an immediate repeat, not the move forever
    if volatiles.get('torment') and name and pokemon.get('last_move_used') == name:
        return "tormented"

    if opponent is not None:
        sealed = (opponent.get('volatile_statuses') or {}).get('imprison') or []
        if name in sealed:
            return "sealed by Imprison"

    return None


def usable_moves(pokemon, opponent=None):
    """
    Every move a specimen may legally pick this turn: has PP and is not restricted.

    The NPC AI selects from this rather than from a bare PP filter, so it cannot pick a
    taunted status move or a disabled attack and waste its turn.
    """
    return [m for m in (pokemon.get('moves') or [])
            if m.get('pp', 0) > 0 and move_is_restricted(pokemon, m, opponent) is None]


def apply_grudge(fainted, attacker):
    """
    Grudge: when the user is knocked out, the move that finished it loses all its PP.

    Returns a log fragment, or '' when there was no grudge set or nothing left to drain.
    """
    if fainted is None or attacker is None:
        return ""

    volatiles = fainted.get('volatile_statuses') or {}
    if not volatiles.get('grudge'):
        return ""

    volatiles.pop('grudge', None)
    killer_move = attacker.get('last_move_used')
    if not drain_move_pp(attacker, killer_move, None):
        return ""

    return (f" 👻 {fainted['name'].capitalize()}'s grudge drained all the PP from "
            f"{attacker['name'].capitalize()}'s {killer_move.replace('-', ' ').title()}!")

# Item moves that can fail outright, and so are worth scoring before they are picked.
# Incinerate, Bug Bite and Pluck are deliberately absent: they still land their damage
# when the target has no berry, so there is nothing for the AI to avoid.
ITEM_MANIPULATION_MOVES = {'bestow', 'trick', 'switcheroo', 'corrosive-gas', 'embargo',
                           'teatime', 'poltergeist', 'belch', 'fling'}


def item_move_would_land(move_name, attacker, defender, magic_room=False):
    """
    Whether an item move would achieve anything in this matchup.

    Read by the NPC AI so it stops throwing a Bestow at a target whose hands are already
    full, or a Belch before it has eaten anything. Returns None for moves not covered.

    Like ability_move_would_land this mirrors the guards in calculate_damage rather than
    sharing them, because each handler needs its own failure message; the test suite pins
    the two together across a matrix of item pairings.
    """
    if move_name not in ITEM_MANIPULATION_MOVES:
        return None

    mine = get_stored_item(attacker)
    theirs = get_stored_item(defender)

    if move_name == 'bestow':
        return is_transferable_item(mine) and theirs == 'none'

    if move_name in ('trick', 'switcheroo'):
        if mine == 'none' and theirs == 'none':
            return False
        return ((mine == 'none' or is_transferable_item(mine)) and
                (theirs == 'none' or is_transferable_item(theirs)))

    if move_name == 'corrosive-gas':
        return is_transferable_item(theirs)

    if move_name == 'embargo':
        return not (defender.get('volatile_statuses') or {}).get('embargo')

    if move_name == 'teatime':
        return is_berry(mine) or is_berry(theirs)

    if move_name == 'poltergeist':
        return is_transferable_item(theirs)

    if move_name == 'belch':
        return bool(attacker.get('_ate_berry'))

    # fling
    return (get_active_item(attacker, magic_room) != 'none'
            and get_fling_power(mine) > 0)


def get_stored_item(pokemon):
    """The item on the specimen's sheet, normalised, ignoring any suppression."""
    if pokemon is None:
        return 'none'
    return (pokemon.get('held_item') or 'none').lower().replace(' ', '-')


def get_active_item(pokemon, magic_room=False):
    """
    The item whose effects are actually in force - 'none' while they are switched off.

    Embargo and Magic Room suppress what an item DOES without taking it away, so the
    stored name has to survive: Trick can still swap an embargoed Choice Scarf, and the
    Scarf comes back to life the moment the room wears off. Passive item effects read
    this; the moves that physically move or destroy an item read get_stored_item.
    """
    if pokemon is None:
        return 'none'
    if magic_room:
        return 'none'
    if (pokemon.get('volatile_statuses') or {}).get('embargo'):
        return 'none'
    return get_stored_item(pokemon)


def is_transferable_item(item):
    """
    Whether an item can be moved off its holder by Trick, Bestow, Knock Off, Thief,
    Fling, Incinerate or Corrosive Gas.

    Centralises a guard that was copy-pasted at three sites in the damage formula. The
    old inline version tested `endswith('ite')`, which silently missed the split Mega
    Stones - 'charizardite-x' does not end in 'ite', so it could be knocked off.
    """
    item = (item or 'none').lower().replace(' ', '-')

    if item in ('none', '') or item in UNTRANSFERABLE_ITEMS:
        return False
    if item.endswith('ium-z'):                      # Z-Crystals
        return False

    stem = item[:-2] if item.endswith(('-x', '-y')) else item
    if stem.endswith('ite') and stem not in NON_MEGA_ITE_ITEMS:
        return False

    return True


def is_berry(item):
    """Berries are exactly the botanical database, which is keyed '<name>-berry'."""
    item = (item or '').lower().replace(' ', '-')
    return item.endswith('-berry') or item in CONSUMABLE_DATABASE


# One-shot equipment that is genuinely spent when it triggers, alongside the berries.
# Everything NOT in here (Leftovers, Choice items, Mega Stones...) is merely carried, so
# losing it to Trick or Knock Off has to be undone when the battle ends.
ONE_USE_ITEMS = {
    'focus-sash', 'power-herb', 'white-herb', 'mental-herb', 'air-balloon',
    'absorb-bulb', 'cell-battery', 'luminous-moss', 'snowball', 'weakness-policy',
    'blunder-policy', 'throat-spray', 'eject-button', 'eject-pack', 'red-card',
    'room-service', 'electric-seed', 'grassy-seed', 'misty-seed', 'psychic-seed',
}


def is_consumable(item):
    """Whether an item is used up by its own effect rather than merely being carried."""
    item = (item or '').lower().replace(' ', '-')
    return is_berry(item) or item in ONE_USE_ITEMS


def mark_item_consumed(pokemon, item):
    """
    Record that a specific held item was USED UP - eaten, triggered or burnt away - as
    opposed to being tricked, bestowed, knocked off or stolen.

    Only a genuine consumption is written back to the database when the battle ends.
    Everything else is battle-scoped, which is what stops Trick and Bestow from
    permanently moving equipment between two players' collections.

    The item NAME is recorded rather than a bare flag, because a specimen can lose its
    own Leftovers to a Trick and then eat a berry it was handed - the Leftovers still has
    to come home.
    """
    if pokemon is None:
        return
    item = (item or '').lower().replace(' ', '-')
    if is_consumable(item):
        pokemon.setdefault('_consumed_items', set()).add(item)


def snapshot_team_items(team):
    """
    Record what each specimen walked into the battle holding, so the transfers can be
    unwound at the end. Safe to call more than once on the same team.

    Returns the team so it can wrap a roster inline where the battle state is built.
    """
    for pokemon in team or []:
        if pokemon is not None and '_original_item' not in pokemon:
            pokemon['_original_item'] = pokemon.get('held_item') or 'none'
    return team


def item_was_consumed(pokemon):
    """Whether the specimen used up the exact item it started the battle holding."""
    if pokemon is None:
        return False
    original = (pokemon.get('_original_item') or pokemon.get('held_item') or 'none')
    return original.lower().replace(' ', '-') in pokemon.get('_consumed_items', set())


def resolve_persisted_item(pokemon):
    """
    What to write back to caught_pokemon when the battle ends.

    A consumable the specimen actually used up stays gone. Everything else reverts to
    what it started with, so an item that was tricked, bestowed, knocked off or stolen
    comes home rather than changing owner permanently.
    """
    if pokemon is None:
        return 'none'

    original = pokemon.get('_original_item')
    if original is None:
        # Never snapshotted - an NPC, or a path that predates this. Leave it as found.
        return pokemon.get('held_item') or 'none'

    return 'none' if item_was_consumed(pokemon) else original


def get_fling_power(item):
    """Base power Fling throws the given item for. 0 means it cannot be flung at all."""
    item = (item or 'none').lower().replace(' ', '-')
    if not is_transferable_item(item):
        return 0
    if is_berry(item):
        return 10
    return FLING_POWER.get(item, FLING_DEFAULT_POWER)


def apply_berry_effect(pokemon, item, ignore_threshold=False, owner_str=""):
    """
    Resolve one berry on one specimen and return a log line, or '' if nothing happened.

    check_consumables uses this with the normal HP/status thresholds; Teatime, Bug Bite,
    Pluck and a flung berry force it through with ignore_threshold, which is what "eats
    the berry regardless" means.
    """
    item = (item or '').lower().replace(' ', '-')
    data = CONSUMABLE_DATABASE.get(item)
    if not data or pokemon is None or pokemon.get('current_hp', 0) <= 0:
        return ""

    behavior = data.get('type')
    max_hp = pokemon.get('max_hp', 100)
    current_hp = pokemon['current_hp']
    hp_pct = current_hp / max_hp if max_hp else 1.0
    who = f"{owner_str.strip()} " if owner_str else ""
    name = pokemon['name'].capitalize()
    label = item.replace('-', ' ').title()

    def eaten():
        # Only empty the slot when the berry actually came off THIS specimen. Bug Bite,
        # Pluck and a flung berry feed someone else's berry to the eater, and must not
        # take the eater's own item with it.
        if get_stored_item(pokemon) == item:
            pokemon['held_item'] = 'none'
            mark_item_consumed(pokemon, item)
        # Belch needs to know this happened, and it has to outlive a switch, so it lives
        # on the specimen rather than in the volatiles that get wiped on withdrawal.
        pokemon['_ate_berry'] = True

    if behavior == 'heal_flat' and (ignore_threshold or hp_pct <= data.get('threshold', 0.5)):
        if not ignore_threshold or current_hp < max_hp:
            heal_amt = data.get('value', 10)
            pokemon['current_hp'] = min(max_hp, current_hp + heal_amt)
            eaten()
            return f"{data.get('icon', '🫐')} {who}**{name}** consumed its {label}! (+{heal_amt} HP)\n"

    elif behavior == 'heal_pct' and (ignore_threshold or hp_pct <= data.get('threshold', 0.5)):
        if not ignore_threshold or current_hp < max_hp:
            heal_amt = max(1, math.floor(max_hp * data.get('value', 0.25)))
            pokemon['current_hp'] = min(max_hp, current_hp + heal_amt)
            eaten()
            return f"{data.get('icon', '🍋')} {who}**{name}** consumed its {label}! (+{heal_amt} HP)\n"

    elif behavior == 'cure_status' and pokemon.get('status_condition'):
        status_name = pokemon['status_condition']['name']
        if data.get('target') in ('all', status_name):
            pokemon['status_condition'] = None
            eaten()
            return f"{data.get('icon', '🌿')} {who}**{name}** consumed its {label} and cured its {status_name}!\n"

    elif behavior == 'stat_boost' and (ignore_threshold or hp_pct <= data.get('threshold', 0.25)):
        stat_target = data.get('stat', 'attack')
        boost_val = data.get('value', 1)
        if 'stat_stages' not in pokemon:
            pokemon['stat_stages'] = {stat: 0 for stat in ALL_STAT_STAGES}

        if pokemon['stat_stages'].get(stat_target, 0) < 6:
            pokemon['stat_stages'][stat_target] = min(6, pokemon['stat_stages'].get(stat_target, 0) + boost_val)
            eaten()
            return (f"{data.get('icon', '🔴')} {who}**{name}** consumed its {label}! "
                    f"Its {stat_target.replace('_', ' ').title()} rose!\n")

    # Resist berries and the PP restorer have no effect outside their own trigger, but a
    # forced feed still eats them.
    if ignore_threshold:
        eaten()
        return f"{data.get('icon', '🫐')} {who}**{name}** ate its {label}.\n"

    return ""

# Every stat stage a specimen can carry, including the two the damage formula reads
# via .get() defaults.
ALL_STAT_STAGES = ['attack', 'defense', 'sp_atk', 'sp_def', 'speed', 'accuracy', 'evasion']

def reset_stat_stages(pokemon):
    """
    Wipe a specimen's stat stages, as happens the moment it leaves the field.

    Boosts are tied to the slot, not the specimen, so a Swords Dance does not survive a
    switch out and back in.
    """
    if pokemon is None:
        return
    pokemon['stat_stages'] = {stat: 0 for stat in ALL_STAT_STAGES}

def snapshot_base_stats(pokemon):
    """
    Preserve the untouched stat block the first time a move rewrites raw stats.
    Called by Guard Split, Power Split, Speed Swap and Power Trick.
    """
    if pokemon is not None and '_base_stats' not in pokemon:
        pokemon['_base_stats'] = dict(pokemon.get('stats') or {})

def clear_base_stat_snapshot(pokemon):
    """
    Drop a pending snapshot without applying it. Used when a transformation (Mega,
    Dynamax) legitimately rewrites the stat block - the new form becomes the baseline,
    and restoring the pre-transformation numbers on switch-out would be wrong.
    """
    if pokemon is not None:
        pokemon.pop('_base_stats', None)

def restore_base_stats(pokemon):
    """
    Undo raw-stat rewrites when a specimen leaves the field. Like stat stages, effects
    such as Guard Split and Power Trick are tied to the slot, not the specimen.
    """
    if pokemon is not None and '_base_stats' in pokemon:
        pokemon['stats'] = dict(pokemon.pop('_base_stats'))

# ==========================================
# ⏳ TWO-TURN CHARGE LIFECYCLE
# ==========================================
# A charge has exactly three ends: it fires, something cancels it, or the user is stopped
# from firing it. The engines used to handle only the first two inline, so any path that
# skipped a charging specimen's action - paralysis, sleep, freeze, flinch, a confusion
# self-hit, or a target that fainted first - left 'charging' set forever. That in turn
# stranded 'semi_invulnerable', because the end-of-turn sweep only drops that flag while
# nothing is charging, and a specimen stuck underground can only be reached by the handful
# of moves that bypass it (and by Max moves). Routing all three ends through here is what
# stops the next new skip-path from reintroducing the bug.

def begin_charge(pokemon, move_name, invulnerability=None):
    """
    Start a two-turn move. Marked fresh so the end-of-turn sweep knows this charge has not
    had its chance to fire yet and must be left alone.
    """
    if pokemon is None:
        return
    volatiles = pokemon.setdefault('volatile_statuses', {})
    volatiles['charging'] = move_name
    volatiles['charge_fresh'] = True
    if invulnerability:
        volatiles['semi_invulnerable'] = invulnerability


def end_charge(pokemon):
    """
    Drop a charge and any invulnerability with it - used both when the charged move fires
    and when something cancels it outright, such as Gravity slamming a flier down.
    """
    if pokemon is None:
        return
    volatiles = pokemon.get('volatile_statuses') or {}
    volatiles.pop('charging', None)
    volatiles.pop('charge_fresh', None)
    volatiles.pop('semi_invulnerable', None)


def break_stale_charge(pokemon):
    """
    End-of-turn housekeeping for two-turn moves.

    A charge started THIS turn is left alone. A charge that was already pending and did
    not fire means the user was stopped, so the move fails and it comes back down - which
    is what the games do when a Pokemon cannot execute the second turn of Fly.

    Returns the name of the broken move, or None if there was nothing to break.
    """
    if pokemon is None:
        return None

    volatiles = pokemon.get('volatile_statuses') or {}
    charging = volatiles.get('charging')
    if not charging:
        volatiles.pop('charge_fresh', None)
        volatiles.pop('semi_invulnerable', None)
        return None

    if volatiles.pop('charge_fresh', None):
        # Turn one. It still has its shot next turn.
        return None

    end_charge(pokemon)
    return charging


def leave_field(pokemon):
    """Everything that comes off a specimen when it is withdrawn."""
    if pokemon is not None:
        # Coming back in counts as arriving fresh, which is what re-arms Fake Out
        pokemon['turns_on_field'] = 0
    reset_stat_stages(pokemon)
    restore_base_stats(pokemon)
    restore_base_ability(pokemon)
    end_charge(pokemon)

def baton_pass_state(outgoing, incoming):
    """
    Baton Pass hands the replacement everything the user had built up: stat stages plus
    the volatiles that are meant to travel (traps, Leech Seed, focus). Volatiles that
    belong to the departing specimen itself are deliberately left behind.
    """
    if not outgoing or not incoming:
        return

    incoming['stat_stages'] = dict(outgoing.get('stat_stages') or {})

    PASSABLE = ['leech_seed', 'volatile_leech_seed', 'confusion', 'perish_song',
                'volatile_perish_song', 'focus_energy', 'laser_focus', 'ingrain',
                'partially_trapped', 'hard_trapped', 'substitute', 'curse']

    carried = {k: v for k, v in (outgoing.get('volatile_statuses') or {}).items()
               if k in PASSABLE}
    incoming['volatile_statuses'] = carried

    # A raw-stat rewrite is NOT passed on - it belongs to the specimen that used it.
    # Neither is an ability rewrite or a Gastro Acid: the replacement arrives with its own.
    restore_base_stats(outgoing)
    restore_base_ability(outgoing)
    reset_stat_stages(outgoing)
    outgoing['volatile_statuses'] = {}

def is_crit_shielded(target_hazards):
    """True while Lucky Chant is up on the defending side - no criticals get through."""
    if not target_hazards:
        return False
    return target_hazards.get('lucky-chant', 0) > 0

# ==========================================
# 🚨 LOCK-IN MOVES
# ==========================================
# Uproar rides the same rampage machinery as Outrage, but runs a fixed 3 turns and leaves
# the user clear-headed instead of confused.
UPROAR_MOVES = ['uproar']

# Moves that cannot be copied by Encore - either they are Encore itself or they have no
# meaningful "last move" to repeat.
ENCORE_IMMUNE_MOVES = ['encore', 'struggle', 'transform', 'mimic', 'sketch', 'mirror-move']

def is_uproar_active(*combatants):
    """True while any of the given specimens is mid-Uproar. Nothing can sleep through it."""
    for mon in combatants:
        if not mon:
            continue
        rampage = (mon.get('volatile_statuses') or {}).get('rampage') or {}
        if rampage.get('move') in UPROAR_MOVES:
            return True
    return False

# Double power when the user gets in before the target has taken its action this turn.
# Distinct from Revenge/Payback, which key off having *been hit* rather than turn order.
AMBUSH_MOVES = ['bolt-beak', 'fishious-rend']

# Two-turn moves that raise a stat while CHARGING. The engines apply that boost from
# their own two-turn table, but these moves also carry a stat_name/stat_change in the
# database with target 'selected-pokemon' - so without excluding them here, the attack
# turn would hand a duplicate boost to the opponent.
CHARGE_BOOST_MOVES = ['meteor-beam', 'electro-shot']

# ==========================================
# 🚨 DELAYED STRIKES (Future Sight / Doom Desire)
# ==========================================
# These queue an attack that lands two turns later against whoever occupies the target
# slot at that moment - even if the original user has switched out or fainted.
DELAYED_ATTACK_MOVES = ['future-sight', 'doom-desire']

def snapshot_delayed_attack(move_name, attacker, move, owner_label):
    """
    Freezes the launcher's offensive profile at the moment of use. The strike later
    resolves with these numbers rather than whatever is on the field, so switching out,
    losing a stat boost, or fainting does not change the incoming damage.
    """
    return {
        'move': move_name,
        'type': move.get('type', 'psychic'),
        'power': move.get('power') or 0,
        'owner': owner_label,
        'name': attacker.get('name', 'a specimen'),
        'level': attacker.get('level', 50),
        'sp_atk': attacker.get('stats', {}).get('sp_atk', 50),
        'types': list(attacker.get('types') or []),
        'ability': get_active_ability(attacker),
        # Two full turns must pass, so the tick on the turn it was queued is skipped
        'turns': 2,
        'just_queued': True,
    }

# ==========================================
# 💊 PARTY HEALS AND CLEANSES
# ==========================================
# Moves that scrub status off the WHOLE party, bench included. That is the entire point
# of them, so they are the one family that needs to reach past the two specimens on the
# field - hence the user_party argument threaded into calculate_damage.
PARTY_CURE_MOVES = {'heal-bell', 'aromatherapy', 'sparkly-swirl'}

# Restore a quarter of maximum HP and scrub status off the user's side. With one specimen
# per side on this field, "the user's side" is the user.
SIDE_RESTORE_MOVES = {'jungle-healing', 'lunar-blessing'}


def cure_party_status(party, fallback=None):
    """
    Clear every major status across a whole party.

    Returns the names actually cured so the caller can report them and can treat an empty
    result as "but it failed". Falls back to a single specimen when no roster was handed
    in, which keeps the move working rather than silently doing nothing.
    """
    roster = [m for m in (party or []) if m is not None]
    if not roster and fallback is not None:
        roster = [fallback]

    cured = []
    for member in roster:
        if (member.get('status_condition') or {}).get('name'):
            member['status_condition'] = None
            cured.append(member.get('name', 'a specimen').capitalize())
    return cured


def snapshot_wish(attacker):
    """
    Wish banks HALF THE WISHER'S maximum HP and pays it out a turn later to whoever is
    standing in the slot - which is what makes it a switch-in heal rather than a
    self-heal. Mirrors the delayed-strike queue.
    """
    return {
        'heal': max(1, math.floor(attacker.get('max_hp', 100) / 2)),
        'name': attacker.get('name', 'a specimen'),
        'turns': 1,
        'just_queued': True,
    }


def resolve_wish(pending, occupant):
    """Pay out a queued Wish to whoever now holds the slot. Returns (healed, message)."""
    if not pending or occupant is None or occupant.get('current_hp', 0) <= 0:
        return 0, ""

    wisher = str(pending.get('name', 'a specimen')).capitalize()
    max_hp = occupant.get('max_hp', 100)
    before = occupant.get('current_hp', 0)

    if before >= max_hp:
        return 0, (f"💫 {wisher}'s wish came true, but "
                   f"{occupant['name'].capitalize()} was already at full health!")

    occupant['current_hp'] = min(max_hp, before + pending.get('heal', 0))
    gained = occupant['current_hp'] - before
    return gained, (f"💫 {wisher}'s wish came true! "
                    f"{occupant['name'].capitalize()} restored {gained} HP!")


def resolve_delayed_strike(pending, defender, weather='none', terrain='none'):
    """
    Fires a queued strike at whoever now occupies the target slot. Uses the launcher's
    frozen offence but the CURRENT occupant's defences and typing, so a switch-in eats
    the hit at its own resistances. Returns (damage, message).
    """
    # A stand-in for the original user - only the fields the damage formula reads
    ghost_attacker = {
        'name': pending['name'],
        'level': pending['level'],
        'current_hp': 1, 'max_hp': 1,
        'stats': {'attack': pending['sp_atk'], 'defense': 50,
                  'sp_atk': pending['sp_atk'], 'sp_def': 50, 'speed': 50},
        'types': pending['types'],
        'status_condition': None,
        'volatile_statuses': {},
        # Deliberately itemless: the launcher is not on the field, so held-item
        # interactions (Life Orb recoil, Rocky Helmet) have nobody to apply to.
        'held_item': 'none',
        'ability': pending['ability'],
        'stat_stages': {},
    }

    strike = {
        'name': pending['move'], 'type': pending['type'], 'class': 'special',
        'power': pending['power'], 'accuracy': 100, 'pp': 1, 'max_pp': 1,
        'ailment': 'none', 'ailment_chance': 0, 'stat_name': 'none', 'stat_change': 0,
        'stat_chance': 0, 'drain': 0, 'healing': 0, 'priority': 0,
        'target': 'selected-pokemon', 'status_type': 'none', 'status_chance': 0,
    }

    # The delayed strike arrives after the shield has served its purpose, so Protect
    # does not stop it. Lifted for the calculation and put back afterwards.
    volatiles = defender.setdefault('volatile_statuses', {})
    was_protected = volatiles.pop('protected', None)
    try:
        damage, msg, _, _, _ = calculate_damage(ghost_attacker, defender, strike,
                                                weather=weather, terrain=terrain)
    finally:
        if was_protected is not None:
            volatiles['protected'] = was_protected

    return damage, msg

def get_effective_priority(move_name, base_priority, attacker, terrain='none'):
    """
    The priority bracket a move actually moves in, after terrain effects. Grassy Glide
    jumps a bracket on Grassy Terrain, but only while the user is touching the ground.
    """
    priority = int(base_priority or 0)

    shift = TERRAIN_PRIORITY_MOVES.get((move_name or '').lower().replace(' ', '-'))
    if shift and terrain == shift[0] and is_grounded(attacker):
        priority += shift[1]

    return priority

# ==========================================
# 🚨 OFFENSIVE / DEFENSIVE STAT OVERRIDES
# ==========================================
# Psyshock, Psystrike and Secret Sword are Special moves that strike the target's
# *physical* Defense. Photon Geyser and Shell Side Arm choose their category at runtime
# from live stats. Body Press swings with the user's own Defense.
PHYSICAL_DEFENSE_MOVES = ['psyshock', 'psystrike', 'secret-sword']
ADAPTIVE_CATEGORY_MOVES = ['photon-geyser', 'shell-side-arm']
STAT_OVERRIDE_MOVES = PHYSICAL_DEFENSE_MOVES + ADAPTIVE_CATEGORY_MOVES + ['body-press']

def apply_stat_stage(raw_stat, stage):
    """Standard stage multiplier, shared by offensive and defensive stats."""
    if stage > 0:
        return int(raw_stat * ((2.0 + stage) / 2.0))
    if stage < 0:
        return int(raw_stat * (2.0 / (2.0 + abs(stage))))
    return raw_stat

def resolve_combat_stats(move_name, move_class, attacker, defender, wonder_room=False, magic_room=False,
                         ignore_boosts=False):
    """
    Decides which Attack and Defense stats the damage formula reads, applies stat stages,
    Wonder Room and Assault Vest, and reports the category the move resolves as.

    Returns (attack_stat, defense_stat, effective_class). The returned class drives the
    burn penalty and screen selection, so a Photon Geyser that resolves physical is
    halved by a burn and blocked by Reflect rather than Light Screen.

    ignore_boosts models a critical hit, which punches through anything that would make
    the hit weaker: the target's defensive *increases* and the user's offensive
    *decreases* are both discarded. Changes that favour the attacker still count.
    """
    a_stages = attacker.get('stat_stages') or {}
    d_stages = defender.get('stat_stages') or {}

    if ignore_boosts:
        a_stages = {k: max(0, v) for k, v in a_stages.items()}
        d_stages = {k: min(0, v) for k, v in d_stages.items()}

    phys_atk = apply_stat_stage(attacker.get('stats', {}).get('attack', 50), a_stages.get('attack', 0))
    spec_atk = apply_stat_stage(attacker.get('stats', {}).get('sp_atk', 50), a_stages.get('sp_atk', 0))
    phys_def = apply_stat_stage(defender.get('stats', {}).get('defense', 50), d_stages.get('defense', 0))
    spec_def = apply_stat_stage(defender.get('stats', {}).get('sp_def', 50), d_stages.get('sp_def', 0))

    # Assault Vest reinforces the Sp. Def stat itself, so it follows that stat rather than
    # the move - a Psyshock aimed at physical Defense correctly ignores the vest.
    if get_active_item(defender, magic_room) == 'assault-vest':
        spec_def = math.floor(spec_def * 1.5)

    # 🚨 WONDER ROOM swaps which of the target's two walls is standing where
    if wonder_room:
        phys_def, spec_def = spec_def, phys_def

    # --- BODY PRESS: swings with the user's own Defense ---
    if move_name == 'body-press':
        body_press_atk = apply_stat_stage(attacker.get('stats', {}).get('defense', 50), a_stages.get('defense', 0))
        return body_press_atk, phys_def, 'physical'

    # --- PSYSHOCK FAMILY: special attack aimed at the physical wall ---
    if move_name in PHYSICAL_DEFENSE_MOVES:
        return spec_atk, phys_def, 'special'

    # --- PHOTON GEYSER: turns physical when the user's Attack is the higher stat ---
    if move_name == 'photon-geyser':
        if phys_atk > spec_atk:
            return phys_atk, phys_def, 'physical'
        return spec_atk, spec_def, 'special'

    # --- SHELL SIDE ARM: takes whichever split would actually hurt more ---
    if move_name == 'shell-side-arm':
        # Level and power are identical either way, so comparing full damage reduces to
        # comparing the two attack/defense ratios. Ties resolve as special.
        if (phys_atk / max(1, phys_def)) > (spec_atk / max(1, spec_def)):
            return phys_atk, phys_def, 'physical'
        return spec_atk, spec_def, 'special'

    # --- Everything else follows its stored category ---
    if move_class == 'physical':
        return phys_atk, phys_def, 'physical'

    return spec_atk, spec_def, 'special'

def format_power_hint(move_name, attacker, defender):
    """
    Short ' ⚡NNN' suffix showing an HP-scaled move's power *right now*, for battle
    buttons. Returns '' for every other move so callers can append it unconditionally.
    """
    # pending=True: the button is offering a move whose cost has not been paid yet, and
    # Trump Card's power is decided by what is left once it has been.
    power = resolve_dynamic_power(move_name, attacker, defender, pending=True)
    return f" ⚡{power}" if power is not None else ""

def describe_power_range(move_name):
    """
    Static description of an HP-scaled move's power band, for menus that list moves
    outside of battle where there's no live HP to read. Returns None if it doesn't scale.
    """
    if move_name in ['flail', 'reversal']:
        return "20-200 (↑ as your HP drops)"
    if move_name in ['eruption', 'water-spout']:
        return "1-150 (↑ with your HP)"
    if move_name in ['wring-out', 'crush-grip']:
        return "1-120 (↑ with target's HP)"

    # --- Stat-ratio family ---
    if move_name == 'gyro-ball':
        return "1-150 (↑ the slower you are)"
    if move_name == 'electro-ball':
        return "40-150 (↑ the faster you are)"
    if move_name in ['heavy-slam', 'heat-crash']:
        return "40-120 (↑ if you outweigh the target)"
    if move_name in ['grass-knot', 'low-kick']:
        return "20-120 (↑ with target's weight)"
    if move_name == 'punishment':
        return "60-200 (↑ per target stat boost)"
    if move_name in ['stored-power', 'power-trip']:
        return "20+ (↑ 20 per stat boost)"
    if move_name == 'hex':
        return "65 / 130 vs a statused target"
    if move_name == 'revenge':
        return "60 / 120 if struck first"
    if move_name == 'stomping-tantrum':
        return "75 / 150 after a failed move"
    if move_name == 'rage-fist':
        return "50-350 (↑ 50 per hit taken)"
    if move_name == 'last-respects':
        return "50+ (↑ 50 per ally lost)"
    if move_name == 'body-press':
        return "80 (attacks with your Defense)"

    # --- Resource family ---
    if move_name == 'trump-card':
        return "40-200 (↑ as its own PP runs out)"
    if move_name == 'spit-up':
        return "100 per Stockpile charge"
    if move_name == 'hard-press':
        return "1-100 (↑ with target's HP)"

    # --- Friendship family ---
    if move_name in FRIENDSHIP_MOVES:
        return "1-102 (↑ the more it likes you)"
    if move_name in FRUSTRATION_MOVES:
        return "1-102 (↑ the less it likes you)"

    return None

def estimate_bypass_payload(move_name, move_type, attacker, defender):
    """
    Expected HP payload of any formula-bypass move, used for NPC move scoring.
    Returns 0 whenever the move would fail outright against this target, so the
    caller can simply treat 0 as "never pick this". RNG and accuracy are both
    resolved to their mean so the AI's ranking stays stable from turn to turn.
    """
    if move_name not in FORMULA_BYPASS_MOVES:
        return 0

    # A 0x elemental matchup blanks every move in this family
    multiplier = 1.0
    for def_type in (defender.get('types') or []):
        multiplier *= TYPE_CHART.get(move_type, {}).get(def_type, 1.0)
    if multiplier == 0.0:
        return 0

    def_hp = defender.get('current_hp', 0)

    if move_name in FIXED_DAMAGE_MOVES:
        return estimate_fixed_damage(move_name, attacker)

    if move_name in ['seismic-toss', 'night-shade']:
        return attacker.get('level', 50)

    if move_name in ['super-fang', 'natures-madness', 'ruination']:
        return max(1, math.floor(def_hp / 2))

    if move_name == 'endeavor':
        # Only worth a turn when the user is the more wounded of the two
        return max(0, def_hp - attacker.get('current_hp', 0))

    if move_name in OHKO_MOVES:
        atk_lvl = attacker.get('level', 50)
        def_lvl = defender.get('level', 50)
        atk_ability = get_active_ability(attacker)
        def_ability = get_active_ability(defender)

        # Conditions the engine rejects outright, so the turn would be wasted
        if atk_lvl < def_lvl:
            return 0
        if def_ability == 'sturdy':
            return 0
        if move_name == 'sheer-cold' and 'ice' in (defender.get('types') or []):
            return 0

        base_acc = 30 + (atk_lvl - def_lvl)
        if move_name == 'sheer-cold' and 'ice' not in (attacker.get('types') or []):
            base_acc = 20 + (atk_lvl - def_lvl)
        if atk_ability == 'no-guard' or def_ability == 'no-guard':
            base_acc = 100

        # Weigh the guaranteed faint against the odds of whiffing the turn entirely,
        # so a 30% coin-flip never outranks a reliable attack that does real damage.
        accuracy = max(0, min(100, base_acc))
        return math.floor(def_hp * (accuracy / 100.0))

    return 0

def apply_survival_floor(defender, damage, magic_room=False):
    """
    Focus Sash, Sturdy, and Endure clamp any otherwise-lethal hit so the specimen
    survives on exactly 1 HP. Returns (final_damage, message_fragment).
    """
    if damage < defender.get('current_hp', 0):
        return damage, ""

    def_item = get_active_item(defender, magic_room)
    def_ability = get_active_ability(defender)
    at_full_health = defender['current_hp'] == defender.get('max_hp', 100)

    if def_item == 'focus-sash' and at_full_health:
        defender['held_item'] = 'none' # The sash disintegrates on use!
        mark_item_consumed(defender, def_item)
        return defender['current_hp'] - 1, " It hung on using its Focus Sash!"

    if def_ability == 'sturdy' and at_full_health:
        return defender['current_hp'] - 1, " It endured the hit using Sturdy!"

    if defender.get('volatile_statuses', {}).get('endure'):
        return defender['current_hp'] - 1, " It endured the hit!"

    return damage, ""

def calculate_damage(attacker, defender, move, weather='none', terrain='none', target_hazards=None, user_hazards=None, wonder_room=False, gravity=False, magic_room=False, user_party=None, field=None):
    """
    Acts as the central physics and biology engine for field combat.
    Processes raw damage, parasitic drains, status afflictions, and hybrid field hazards.
    """
    damage = 0
    msg = ""
    inflicted_status = None
    stat_changes = [] 
    healing_amount = 0

    move_name = move.get('name', '').lower().replace(' ', '-')
    move_class = move.get('class', 'physical')
    move_target = str(move.get('target', ''))
    is_max_move = move_name.startswith('max-') or move_name.startswith('g-max-') or 'max' in move_name

    attacker_item = get_active_item(attacker, magic_room)
    defender_item = get_active_item(defender, magic_room)
    
    # 🚨 GRAVITY MOVE BLOCKER
    if gravity and move_name in ['fly', 'bounce', 'splash', 'jump-kick', 'high-jump-kick']:
        return 0, f"But {attacker['name'].capitalize()} couldn't use {move_name.title()} because of the intense gravity!", 'none', [], 0
    
    # ==========================================
    # 🚨 PSYCHIC TERRAIN (Priority Interceptor)
    # ==========================================
    move_prio = int(move.get('priority') or 0)
    if terrain == 'psychic' and move_prio > 0 and is_grounded(defender):
        return 0, f"👁️ The Psychic Terrain protected {defender['name'].capitalize()} from the priority attack!", 'none', [], 0

    # 🚨 FAILSAFE: Guarantee both specimens have their volatile dictionaries initialized!
    if 'volatile_statuses' not in attacker:
        attacker['volatile_statuses'] = {}
    if 'volatile_statuses' not in defender:
        defender['volatile_statuses'] = {}

    # 🚨 STRIKE COUNTER for this single execution. The engines read it to advance Rage
    # Fist, which counts individual strikes rather than moves. Defaults to one hit and is
    # overwritten by the multi-strike loop; reset here so an early return can't leak a
    # stale count from the previous attack.
    defender['last_hit_count'] = 1

    # ==========================================
    # 1. CONTAINMENT FIELD DEPLOYMENT & DECAY
    # =========================================
    if move_name in PROTECT_MOVES:
        # Selective guards are cheap to spam in the franchise, so only the full shields
        # suffer the diminishing-returns roll.
        is_selective = move_name in SELECTIVE_GUARDS
        counter = attacker['volatile_statuses'].get('protect_counter', 0)
        success_chance = 100 if is_selective else 100 / (3 ** counter) # 100%, 33%, 11%, 3%...

        if random.uniform(0, 100) <= success_chance:
            attacker['volatile_statuses']['protected'] = True
            # Remember WHICH shield it is - the collision needs it for both the
            # selective-guard filter and the on-contact punishment.
            attacker['volatile_statuses']['protect_type'] = move_name

            if not is_selective:
                attacker['volatile_statuses']['protect_counter'] = counter + 1

            guard_flavour = {
                'crafty-shield': "raised a crafty shield against status moves!",
                'mat-block':     "threw up a mat to block incoming attacks!",
                'quick-guard':   "braced against high-priority attacks!",
                'wide-guard':    "braced against wide-reaching attacks!",
            }.get(move_name, "protected itself!")

            return 0, f"🛡️ **{attacker['name'].capitalize()}** {guard_flavour}", None, [], 0
        else:
            attacker['volatile_statuses']['protected'] = False
            attacker['volatile_statuses'].pop('protect_type', None)
            attacker['volatile_statuses']['protect_counter'] = 0
            return 0, f"🛡️ **{attacker['name'].capitalize()}** tried to protect itself, but the barrier failed!", None, [], 0
    else:
        # Using any other move resets the exhaustion counter
        attacker['volatile_statuses']['protect_counter'] = 0

    # ==========================================
    # 🚨 BARRIER DEPLOYMENT (Screens)
    # ==========================================
    if move_name in SIDE_SCREEN_MOVES and user_hazards is not None:
        # Light Clay only extends the damage-reducing screens; Lucky Chant is a flat 5.
        if move_name in FLAT_DURATION_SCREENS:
            duration = 5
        else:
            duration = 8 if attacker_item == 'light-clay' else 5

        if move_name == 'aurora-veil' and weather not in ['hail', 'snow']:
            return 0, "But it failed! Aurora Veil requires Hail or Snow!", 'none', [], 0

        if user_hazards.get(move_name, 0) > 0:
            return 0, "But it failed! The barrier is already active!", 'none', [], 0

        user_hazards[move_name] = duration

        if move_name == 'reflect': msg += f" 🧱 A wondrous wall of light appeared to protect {attacker['name'].capitalize()}'s team!"
        elif move_name == 'light-screen': msg += f" 🪞 A wondrous wall of light appeared to protect {attacker['name'].capitalize()}'s team!"
        elif move_name == 'aurora-veil': msg += f" 🌌 An aurora appeared to protect {attacker['name'].capitalize()}'s team!"
        elif move_name == 'lucky-chant': msg += f" 🍀 The chant shielded {attacker['name'].capitalize()}'s team from critical hits!"
        elif move_name == 'safeguard': msg += f" 🛡️ A mystical veil shielded {attacker['name'].capitalize()}'s team from status conditions!"
        elif move_name == 'mist': msg += f" 🌫️ A white mist stopped {attacker['name'].capitalize()}'s team losing any stats!"

        return 0, msg.strip(), 'none', [], 0

    # 🚨 FEINT only exists to punish a shield. With nothing to break, it fails outright.
    if move_name == 'feint' and not defender['volatile_statuses'].get('protected'):
        return 0, "But it failed! There was no barrier to break!", 'none', [], 0

    # ==========================================
    # 2. CONTAINMENT FIELD COLLISION
    # ==========================================
    active_shield = defender['volatile_statuses'].get('protect_type', 'protect')
    shield_stops_this = shield_blocks(active_shield, move_class, move.get('priority'), move_target,
                                      move.get('name'))

    if defender['volatile_statuses'].get('protected') and shield_stops_this and 'user' not in move_target:
        BYPASS_MOVES = ['feint', 'phantom-force', 'shadow-force', 'hyperspace-fury', 'hyperspace-hole']

        if move_name in BYPASS_MOVES:
            defender['volatile_statuses']['protected'] = False
            defender['volatile_statuses'].pop('protect_type', None)
            msg += f"💥 **{attacker['name'].capitalize()}** broke through the protection! "
        elif is_max_move and move_class != 'status':
            pass # Max Moves pierce the shield! Damage quartered at the end of this function.
        else:
            if move_name in ['jump-kick', 'high-jump-kick']:
                crash_dmg = max(1, math.floor(attacker.get('max_hp', 100) / 2))
                attacker['current_hp'] = max(0, attacker['current_hp'] - crash_dmg)
                return 0, f"**{attacker['name'].capitalize()} kept going and crashed!", None, [], 0

            block_msg = f"🛡️ **{defender['name'].capitalize()}** protected itself from the attack!"

            # 🚨 ON-CONTACT PUNISHMENT
            # Only a contact move gets punished - the engine uses the physical class as
            # its contact proxy, so a blocked special move walks away unscathed.
            punish = SHIELD_PUNISH.get(active_shield)
            if punish and move_class == 'physical':
                if punish['kind'] == 'chip':
                    chip = max(1, math.floor(attacker.get('max_hp', 100) * punish['fraction']))
                    attacker['current_hp'] = max(0, attacker['current_hp'] - chip)
                    block_msg += f" 🌵 **{attacker['name'].capitalize()}** was hurt by the spikes! (-{chip} HP)"

                elif punish['kind'] == 'stat':
                    # Routed through stat_changes so the engines clamp and log it normally
                    stat_changes.append(('attacker', punish['stat'], punish['amount']))
                    block_msg += f" 📉 **{attacker['name'].capitalize()}**'s {punish['stat']} was reduced by the shield!"

                elif punish['kind'] == 'status' and not attacker.get('status_condition'):
                    ailment = punish['status']
                    immune_types = {'poison': ['poison', 'steel'], 'burn': ['fire']}.get(ailment, [])
                    if not any(t in immune_types for t in (attacker.get('types') or [])):
                        attacker['status_condition'] = {'name': ailment, 'duration': -1}
                        icon = '☣️' if ailment == 'poison' else '🔥'
                        block_msg += f" {icon} **{attacker['name'].capitalize()}** was afflicted with {ailment} by the shield!"

            return 0, block_msg, None, stat_changes, 0

    # Safely catch SQLite NULL values before running string methods!
    atk_ability = get_active_ability(attacker)
    def_ability = get_active_ability(defender)

    # Drum Solo, Fireball and Hydrosnipe pay no attention to what is defending them
    if gmax_ignores_ability(move.get('name')):
        def_ability = 'none'

    if move.get('name') == 'confusion-snap':
        level = attacker.get('level', 50)
        a = attacker.get('stats', {}).get('attack', 50)
        d = attacker.get('stats', {}).get('defense', 50)
        base_damage = (((2 * level / 5) + 2) * 40 * (a / max(1, d))) / 50 + 2
        damage = math.floor(base_damage * random.uniform(0.85, 1.00))
        return damage, "It hit itself in its confusion!", None, [], 0

    # ==========================================
    # PRE-CALCULATION: TYPE & IMMUNITY CHECKS
    # ==========================================
    move_type = move.get('type', 'normal')

    # 🚨 BIOLOGICAL TYPE MUTATION (Ivy Cudgel)
    if move_name == 'ivy-cudgel' and attacker['name'].lower().startswith('ogerpon'):
        form_name = attacker['name'].lower()
        if 'wellspring' in form_name: move_type = 'water'
        elif 'hearthflame' in form_name: move_type = 'fire'
        elif 'cornerstone' in form_name: move_type = 'rock'
        else: move_type = 'grass'

    # 🚨 ITEM-DRIVEN ELEMENTS (Judgment / Techno Blast / Multi-Attack)
    move_type = resolve_item_move_type(move_name, attacker_item, move_type)

    # ==========================================
    # 🪞 INTERCEPTORS ARMED AGAINST THIS USER
    # ==========================================
    # Electrify rewrites the element before anything reads it, so STAB, the type chart
    # and every type-keyed effect downstream all see Electric.
    if (attacker.get('volatile_statuses') or {}).get('electrified') and move_class != 'status':
        move_type = 'electric'

    # Ion Deluge does the same thing to the whole field, but only to Normal moves. Read
    # after Electrify so the two agree rather than fighting over the element.
    if move_type == 'normal' and move_class != 'status' and field_flag(field, 'ion-deluge') > 0:
        move_type = 'electric'

    # Powder detonates on any Fire move the coated specimen tries to throw, and the move
    # never happens. Checked on the ORIGINAL element as well as the rewritten one so an
    # Electrified Fire move still fizzles rather than slipping through as Electric.
    if (attacker.get('volatile_statuses') or {}).get('powder') and move_class != 'status':
        if move_type == 'fire' or (move.get('type') or '').lower() == 'fire':
            burst = max(1, math.floor(attacker.get('max_hp', 100) * POWDER_RECOIL_FRACTION))
            attacker['current_hp'] = max(0, attacker['current_hp'] - burst)
            return 0, (f"💥 The powder ignited! {attacker['name'].capitalize()} was "
                       f"caught in the blast and lost {burst} HP!"), 'none', [], 0

    # ==========================================
    # 🎁 ITEM-DRIVEN DAMAGE
    # ==========================================
    # Both settle their own power, which overrides the shared resolver at the damage
    # gate far below. They sit up HERE rather than beside that gate because Natural Gift
    # rewrites the element, and the type chart is read long before the gate - putting
    # this any later would throw a berry that the type chart never saw.
    item_power = None

    if move_name == 'natural-gift':
        # Magic Room seals held items away, so there is nothing to draw on.
        payload = None if magic_room else natural_gift_payload(attacker)
        if payload is None:
            return 0, "But it failed! It had no berry to give!", 'none', [], 0

        move_type, item_power = payload
        # Thrown, so it is spent - and spent in the database too, the way a berry eaten
        # mid-battle is, rather than handed back when the battle ends.
        mark_item_consumed(attacker, get_stored_item(attacker))
        attacker['held_item'] = None

    if move_name == 'present':
        item_power = roll_present()
        if item_power is None:
            mended = max(1, math.floor(defender.get('max_hp', 100) * PRESENT_HEAL_FRACTION))
            before = defender.get('current_hp', 0)
            defender['current_hp'] = min(defender.get('max_hp', 100), before + mended)
            return 0, (f"🎁 {attacker['name'].capitalize()} gave a present - and it "
                       f"restored {defender['name'].capitalize()}'s health instead! "
                       f"(+{defender['current_hp'] - before} HP)"), 'none', [], 0

    # 🚨 TERA BLAST takes the user's Tera type once Terastallized, Normal otherwise
    if move_name == 'tera-blast' and attacker.get('tera_type'):
        move_type = attacker['tera_type']

    if move_name in ['jump-kick', 'high-jump-kick']:
        crash_dmg = max(1, math.floor(attacker.get('max_hp', 100) / 2))
        attacker['current_hp'] = max(0, attacker['current_hp'] - crash_dmg)
        return 0, f"{attacker['name'].capitalize()} kept going and crashed!", None, [], 0
    
    if move.get('class') != 'status':
        # A specimen held off the ground cannot be reached by Ground moves. Levitate gets
        # this from the ability table below, but Magnet Rise and Telekinesis are
        # volatiles, so they need saying here.
        if move_type == 'ground' and not is_grounded(defender, gravity):
            lifted = (defender.get('volatile_statuses') or {})
            if lifted.get('magnet_rise') or lifted.get('telekinesis'):
                return 0, (f"🪂 {defender['name'].capitalize()} is airborne - the attack "
                           f"passed harmlessly underneath!"), None, [], 0

        immunity_data = BIOLOGICAL_TRAITS['immunities'].get(def_ability)
        
        # If the defender has an immunity AND the incoming attack matches its element
        if immunity_data and move_type == immunity_data['type']:
            ability_name = def_ability.replace('-', ' ').title()
            
            # A. Adrenaline Stat Boosts (Sap Sipper, Motor Drive, Well-Baked Body)
            if 'stat' in immunity_data:
                target_stat = immunity_data['stat']
                stage_boost = immunity_data['stage']
                return 0, f"📈 {defender['name'].capitalize()}'s {ability_name} absorbed the attack and raised its {target_stat.replace('_', ' ').title()}!", None, [('defender', target_stat, stage_boost)], 0
                
            # B. State Mutation (Flash Fire)
            elif def_ability == 'flash-fire':
                defender['volatile_statuses']['flash_fire'] = True
                return 0, f"🔥 {defender['name'].capitalize()}'s {ability_name} powered up its Fire-type moves!", None, [], 0
                
            # C. Cellular Regeneration (Water Absorb, Dry Skin, Earth Eater)
            elif immunity_data.get('heal', 0.0) > 0:
                if defender['current_hp'] < defender.get('max_hp', 100):
                    heal_amt = math.floor(defender.get('max_hp', 100) * immunity_data['heal'])
                    return 0, f"💧 {defender['name'].capitalize()}'s {ability_name} absorbed the attack to restore HP!", None, [], heal_amt
                else:
                    return 0, f"💧 {defender['name'].capitalize()}'s {ability_name} absorbed the attack, but its HP is already full!", None, [], 0
                    
            # D. Pure Immunity (Levitate)
            else:
                return 0, f"🎈 {defender['name'].capitalize()} is immune to the attack due to its {ability_name}!", None, [], 0
            
    type_multiplier = 1.0
    for def_type in (defender.get('types') or []):
        type_multiplier *= TYPE_CHART.get(move_type, {}).get(def_type, 1.0)
        
    # ==========================================
    # THE WONDER GUARD SHIELD
    # ==========================================
    # Wonder Guard evaluates mathematical effectiveness rather than a single element
    if def_ability == 'wonder-guard' and type_multiplier <= 1.0 and move.get('class') != 'status':
        return 0, f"🛡️ {defender['name'].capitalize()}'s Wonder Guard protected it from the attack!", None, [], 0
    
    # ==========================================
    # 2.5 SPATIAL INVULNERABILITY (Dig / Fly / Dive)
    # ==========================================
    defender_invuln = defender.get('volatile_statuses', {}).get('semi_invulnerable')
    
    if defender_invuln and move_class != 'status':
        # Certain anomalous moves can pierce specific spatial planes!
        if defender_invuln == 'underground' and move_name in ['earthquake', 'magnitude']:
            pass # Earthquake hits Digging targets! (Damage doubled later in Phase 1)
        elif defender_invuln == 'air' and move_name in ['gust', 'twister', 'thunder', 'hurricane']:
            pass # Thunder and Hurricane hit Flying targets!
        elif defender_invuln == 'underwater' and move_name in ['surf', 'whirlpool']:
            pass 
        elif is_max_move:
            pass
        else:
            return 0, f"💨 **{attacker['name'].capitalize()}**'s attack missed because {defender['name'].capitalize()} is {defender_invuln}!", None, [], 0

    # ==========================================
    # 🚨 NEW: PRIMORDIAL WEATHER EVAPORATION / DAMPENING
    # ==========================================
    if weather == 'extremely-harsh-sunlight' and move_type == 'water':
        return 0, "The Water-type attack evaporated in the harsh sunlight!", None, [], 0
        
    if weather == 'heavy-rain' and move_type == 'fire':
        return 0, "The Fire-type attack fizzled out in the heavy rain!", None, [], 0
        
    if weather == 'strong-winds' and 'flying' in (defender.get('types') or []):
        # Delta stream removes Flying-type weaknesses
        if TYPE_CHART.get(move_type, {}).get('flying', 1.0) > 1.0:
            type_multiplier /= 2.0 # Halves the super-effective damage back to neutral!
    
    # ==========================================
    # 🚨 TYPE REWRITES
    # ==========================================
    if move_name == 'conversion':
        # Takes on the element of whatever sits in the user's first move slot
        own_moves = attacker.get('moves') or []
        new_type = next((m.get('type') for m in own_moves if m.get('type')), None)
        if not new_type or attacker.get('types') == [new_type]:
            return 0, "But it failed! There was nothing to convert into!", 'none', [], 0

        attacker['types'] = [new_type]
        return 0, f"🔀 {attacker['name'].capitalize()} converted into the {new_type.title()} type!", 'none', [], 0

    if move_name == 'conversion-2':
        incoming = defender.get('last_move_type')
        if not incoming:
            return 0, "But it failed! There was no attack to adapt to!", 'none', [], 0

        new_type = find_resisting_type(incoming, TYPE_CHART)
        if not new_type:
            return 0, "But it failed! Nothing resists that element!", 'none', [], 0

        attacker['types'] = [new_type]
        return 0, f"🔀 {attacker['name'].capitalize()} adapted into the {new_type.title()} type to resist {incoming.title()}!", 'none', [], 0

    if move_name == 'camouflage':
        new_type = CAMOUFLAGE_TYPES.get(terrain, 'normal')
        if attacker.get('types') == [new_type]:
            return 0, "But it failed! It already blends in!", 'none', [], 0

        attacker['types'] = [new_type]
        return 0, f"🎨 {attacker['name'].capitalize()} blended into the surroundings and became {new_type.title()}!", 'none', [], 0

    if move_name == 'reflect-type':
        mirrored = list(defender.get('types') or [])
        if not mirrored:
            return 0, "But it failed!", 'none', [], 0

        attacker['types'] = mirrored
        return 0, f"🪞 {attacker['name'].capitalize()} mirrored {defender['name'].capitalize()}'s typing!", 'none', [], 0

    if move_name == 'magic-powder':
        if defender.get('types') == ['psychic']:
            return 0, "But it failed! It is already pure Psychic!", 'none', [], 0

        defender['types'] = ['psychic']
        return 0, (f"✨ {defender['name'].capitalize()} was dusted and became pure "
                   f"Psychic!"), 'none', [], 0

    if move_name == 'soak':
        if defender.get('types') == ['water']:
            return 0, "But it failed! It is already pure Water!", 'none', [], 0

        defender['types'] = ['water']
        return 0, f"💧 {defender['name'].capitalize()} was drenched and became pure Water!", 'none', [], 0

    if move_name in ['trick-or-treat', 'forests-curse']:
        added = 'ghost' if move_name == 'trick-or-treat' else 'grass'
        current = list(defender.get('types') or [])

        if added in current:
            return 0, f"But it failed! It is already {added.title()} type!", 'none', [], 0

        # The extra element is grafted on rather than replacing what is there
        defender['types'] = current + [added]
        flavour = "was haunted" if added == 'ghost' else "was entangled in roots"
        return 0, f"🌿 {defender['name'].capitalize()} {flavour} and gained the {added.title()} type!", 'none', [], 0

    # Burn Up and Double Shock need their element intact to fire at all
    if move_name in TYPE_SHEDDING_MOVES:
        required = TYPE_SHEDDING_MOVES[move_name]
        if required not in (attacker.get('types') or []):
            return 0, f"But it failed! There is no {required.title()} energy left to burn!", 'none', [], 0

    # ==========================================
    # 🧬 ABILITY REWRITES
    # ==========================================
    # All of these read the STORED ability rather than the active one - an ability that is
    # sitting under a Gastro Acid is switched off, not gone, so it can still be copied.
    if move_name == 'gastro-acid':
        worked, detail = suppress_ability(defender)
        if not worked:
            return 0, f"But it failed! {detail}", 'none', [], 0
        return 0, (f"🧪 {defender['name'].capitalize()} was doused in fluid - its "
                   f"{pretty_ability(detail)} was suppressed!"), 'none', [], 0

    if move_name in ABILITY_IMPLANT_MOVES:
        implant = ABILITY_IMPLANT_MOVES[move_name]
        theirs = get_stored_ability(defender)

        if theirs in UNREPLACEABLE_ABILITIES:
            return 0, (f"But it failed! {defender['name'].capitalize()}'s "
                       f"{pretty_ability(theirs)} will not budge!"), 'none', [], 0
        if theirs == implant:
            return 0, f"But it failed! It already has {pretty_ability(implant)}!", 'none', [], 0

        set_active_ability(defender, implant)
        note = f"🌱 {defender['name'].capitalize()}'s ability became {pretty_ability(implant)}!"

        # Worry Seed's Insomnia shakes the target awake the moment it lands
        if implant == 'insomnia' and (defender.get('status_condition') or {}).get('name') == 'sleep':
            defender['status_condition'] = None
            note += f" {defender['name'].capitalize()} woke up!"

        return 0, note, 'none', [], 0

    if move_name == 'entrainment':
        mine = get_stored_ability(attacker)
        theirs = get_stored_ability(defender)

        if mine in UNCOPYABLE_ABILITIES or mine == 'none':
            return 0, (f"But it failed! {attacker['name'].capitalize()}'s "
                       f"{pretty_ability(mine)} cannot be shared!"), 'none', [], 0
        if theirs in UNREPLACEABLE_ABILITIES:
            return 0, (f"But it failed! {defender['name'].capitalize()}'s "
                       f"{pretty_ability(theirs)} will not budge!"), 'none', [], 0
        if theirs == mine:
            return 0, "But it failed! They already share that ability!", 'none', [], 0

        set_active_ability(defender, mine)
        return 0, (f"🔗 {defender['name'].capitalize()} fell into step - its ability "
                   f"became {pretty_ability(mine)}!"), 'none', [], 0

    # Doodle spreads the copy across the user's whole side; with one specimen per side on
    # this field that collapses into the same behaviour as Role Play.
    if move_name in ['role-play', 'doodle']:
        mine = get_stored_ability(attacker)
        theirs = get_stored_ability(defender)

        if theirs in UNCOPYABLE_ABILITIES or theirs == 'none':
            return 0, (f"But it failed! {defender['name'].capitalize()}'s "
                       f"{pretty_ability(theirs)} cannot be copied!"), 'none', [], 0
        # Only the form-locked abilities refuse to be painted over here - unlike Worry
        # Seed, copying your way OUT of a Truant is allowed.
        if mine in FORM_LOCKED_ABILITIES:
            return 0, (f"But it failed! {attacker['name'].capitalize()}'s "
                       f"{pretty_ability(mine)} cannot be replaced!"), 'none', [], 0
        if mine == theirs:
            return 0, "But it failed! It already has that ability!", 'none', [], 0

        set_active_ability(attacker, theirs)
        return 0, (f"🎭 {attacker['name'].capitalize()} mimicked "
                   f"{defender['name'].capitalize()} and gained "
                   f"{pretty_ability(theirs)}!"), 'none', [], 0

    if move_name == 'skill-swap':
        mine = get_stored_ability(attacker)
        theirs = get_stored_ability(defender)

        if mine in UNSWAPPABLE_ABILITIES or theirs in UNSWAPPABLE_ABILITIES:
            return 0, "But it failed! Those abilities cannot be traded!", 'none', [], 0
        if mine == theirs:
            return 0, "But it failed! They already share that ability!", 'none', [], 0

        set_active_ability(attacker, theirs)
        set_active_ability(defender, mine)
        return 0, (f"🔄 {attacker['name'].capitalize()} and {defender['name'].capitalize()} "
                   f"traded abilities - {pretty_ability(theirs)} for "
                   f"{pretty_ability(mine)}!"), 'none', [], 0

    # ==========================================
    # 🎒 ITEM INTERACTIONS
    # ==========================================
    # These move or destroy the item itself, so they read the STORED name - an embargoed
    # Choice Scarf is switched off, not gone, and can still be tricked away.
    if move_name == 'bestow':
        mine = get_stored_item(attacker)
        theirs = get_stored_item(defender)

        if not is_transferable_item(mine):
            return 0, "But it failed! There is nothing it can hand over!", 'none', [], 0
        if theirs != 'none':
            return 0, (f"But it failed! {defender['name'].capitalize()} is already "
                       f"holding something!"), 'none', [], 0

        attacker['held_item'] = 'none'
        defender['held_item'] = mine
        return 0, (f"🎁 {attacker['name'].capitalize()} handed its "
                   f"{pretty_item(mine)} to {defender['name'].capitalize()}!"), 'none', [], 0

    if move_name in ['trick', 'switcheroo']:
        mine = get_stored_item(attacker)
        theirs = get_stored_item(defender)

        if mine == 'none' and theirs == 'none':
            return 0, "But it failed! Neither of them is holding anything!", 'none', [], 0
        # A bolted-on item blocks the whole swap rather than half of it
        if (mine != 'none' and not is_transferable_item(mine)) or \
           (theirs != 'none' and not is_transferable_item(theirs)):
            return 0, "But it failed! Those items cannot be swapped!", 'none', [], 0

        attacker['held_item'] = theirs
        defender['held_item'] = mine
        return 0, (f"🔀 {attacker['name'].capitalize()} swapped items - it got the "
                   f"{pretty_item(theirs)} and handed over the "
                   f"{pretty_item(mine)}!"), 'none', [], 0

    if move_name == 'embargo':
        if (defender.get('volatile_statuses') or {}).get('embargo'):
            return 0, "But it failed! It is already under an Embargo!", 'none', [], 0

        defender.setdefault('volatile_statuses', {})['embargo'] = 5
        return 0, (f"🚫 {defender['name'].capitalize()} is under an Embargo - it "
                   f"cannot use its item!"), 'none', [], 0

    if move_name == 'corrosive-gas':
        theirs = get_stored_item(defender)
        if not is_transferable_item(theirs):
            return 0, "But it failed! There is nothing to corrode!", 'none', [], 0

        defender['held_item'] = 'none'
        return 0, (f"🧪 The corrosive gas dissolved {defender['name'].capitalize()}'s "
                   f"{pretty_item(theirs)}!"), 'none', [], 0

    if move_name == 'teatime':
        # Everyone on the field is force-fed, holder and attacker alike
        note = ""
        for eater in [attacker, defender]:
            item = get_stored_item(eater)
            if is_berry(item):
                note += apply_berry_effect(eater, item, ignore_threshold=True)

        if not note:
            return 0, "But it failed! Nobody had a berry to eat!", 'none', [], 0
        return 0, ("🍵 Teatime! Everyone on the field ate their berry! " +
                   note.replace('\n', ' ').strip()), 'none', [], 0

    # --- Attacks that need something in hand to work at all ---
    if move_name == 'poltergeist' and not is_transferable_item(get_stored_item(defender)):
        return 0, "But it failed! The target has no item to turn against it!", 'none', [], 0

    if move_name == 'belch' and not attacker.get('_ate_berry'):
        return 0, "But it failed! It has not eaten a berry yet!", 'none', [], 0

    if move_name == 'fling':
        thrown = get_stored_item(attacker)
        # Embargo and Magic Room stop the user reaching its own item to throw it
        if get_active_item(attacker, magic_room) == 'none' or get_fling_power(thrown) <= 0:
            return 0, "But it failed! There is nothing it can fling!", 'none', [], 0

    # ==========================================
    # 🚫 MOVE RESTRICTIONS
    # ==========================================
    # Disable and Torment both carry a database ailment ('disable' / 'torment') that the
    # engines would otherwise hand to status_condition as a permanent bogus affliction -
    # which also blocked every real status from landing. Returning early here keeps that
    # payload from ever reaching the ailment stage.
    if move_name == 'disable':
        victim = defender.setdefault('volatile_statuses', {})
        target_last = defender.get('last_move_used')

        if victim.get('disable'):
            return 0, "But it failed! It is already disabled!", 'none', [], 0
        if not target_last or not find_move_slot(defender, target_last):
            return 0, "But it failed! There was no move to disable!", 'none', [], 0

        victim['disable'] = {'move': target_last, 'turns': 4}
        return 0, (f"🚫 {defender['name'].capitalize()}'s "
                   f"{target_last.replace('-', ' ').title()} was disabled!"), 'none', [], 0

    if move_name == 'taunt':
        victim = defender.setdefault('volatile_statuses', {})
        if victim.get('taunt'):
            return 0, "But it failed! It is already taunted!", 'none', [], 0

        victim['taunt'] = 3
        return 0, (f"😤 {defender['name'].capitalize()} was taunted - it can only "
                   f"manage attacking moves now!"), 'none', [], 0

    if move_name == 'torment':
        victim = defender.setdefault('volatile_statuses', {})
        if victim.get('torment'):
            return 0, "But it failed! It is already tormented!", 'none', [], 0

        victim['torment'] = True
        return 0, (f"😖 {defender['name'].capitalize()} was tormented - it cannot use "
                   f"the same move twice in a row!"), 'none', [], 0

    if move_name == 'imprison':
        # Storing the user's own movelist and testing membership at selection time is
        # equivalent to the games' "moves we both know", and survives the opponent
        # switching to something with a different set.
        own_moves = [m.get('name') for m in (attacker.get('moves') or []) if m.get('name')]
        if not own_moves:
            return 0, "But it failed! There was nothing to seal!", 'none', [], 0
        if (attacker.get('volatile_statuses') or {}).get('imprison'):
            return 0, "But it failed! It has already sealed its moves!", 'none', [], 0

        attacker.setdefault('volatile_statuses', {})['imprison'] = own_moves
        return 0, (f"🔒 {attacker['name'].capitalize()} sealed its own moves away - the "
                   f"opponent cannot use them!"), 'none', [], 0

    if move_name == 'spite':
        target_last = defender.get('last_move_used')
        taken = drain_move_pp(defender, target_last, random.randint(2, 5)) if target_last else 0

        if not taken:
            return 0, "But it failed! There was no move to sap!", 'none', [], 0
        return 0, (f"👻 {defender['name'].capitalize()}'s "
                   f"{target_last.replace('-', ' ').title()} lost {taken} PP!"), 'none', [], 0

    if move_name == 'grudge':
        attacker.setdefault('volatile_statuses', {})['grudge'] = True
        return 0, (f"👻 {attacker['name'].capitalize()} wants its opponent to bear a "
                   f"grudge!"), 'none', [], 0

    # ==========================================
    # ==========================================
    # 🎯 GUARANTEED ACCURACY AND LEVITATION
    # ==========================================
    if move_name in LOCK_ON_MOVES:
        if (attacker.get('volatile_statuses') or {}).get('locked_on'):
            return 0, "But it failed! It has already taken aim!", 'none', [], 0

        attacker.setdefault('volatile_statuses', {})['locked_on'] = True
        return 0, (f"🎯 {attacker['name'].capitalize()} took aim - its next "
                   f"attack cannot miss!"), 'none', [], 0

    if move_name in LEVITATION_TURNS:
        # Magnet Rise lifts the user; Telekinesis lifts the target
        subject = attacker if move_name == 'magnet-rise' else defender
        flag = move_name.replace('-', '_')

        if (subject.get('volatile_statuses') or {}).get(flag):
            return 0, "But it failed! It is already airborne!", 'none', [], 0
        subject.setdefault('volatile_statuses', {})[flag] = LEVITATION_TURNS[move_name]
        if move_name == 'magnet-rise':
            return 0, (f"🧲 {attacker['name'].capitalize()} levitated on "
                       f"electromagnetism!"), 'none', [], 0
        return 0, (f"🌀 {defender['name'].capitalize()} was hurled into the air "
                   f"and cannot dodge!"), 'none', [], 0

    if move_name == 'celebrate':
        # No battle effect whatsoever, faithfully.
        return 0, (f"🎉 {attacker['name'].capitalize()} is congratulating you on your "
                   f"special day!"), 'none', [], 0

    if move_name == 'acupressure':
        # Self-targeting here: with no ally on the field, the user is the only candidate.
        stat = random_boostable_stat(attacker)
        if stat is None:
            return 0, "But it failed! Every stat was already at its peak!", 'none', [], 0

        return (0, f"💆 {attacker['name'].capitalize()} pressed a pressure point!",
                'none', [('attacker', stat, ACUPRESSURE_BOOST)], 0)

    if move_name == 'psycho-shift':
        giving = transferable_status(attacker)
        if giving is None:
            return 0, "But it failed! It had no condition to pass on!", 'none', [], 0
        if (defender.get('status_condition') or {}).get('name'):
            return 0, "But it failed! The target is already afflicted!", 'none', [], 0

        attacker['status_condition'] = None
        return 0, (f"🔀 {attacker['name'].capitalize()} passed its {giving} to "
                   f"{defender['name'].capitalize()}!"), giving, [], 0

    if move_name == 'curse':
        # Two moves under one name, told apart by the user's typing.
        if 'ghost' in (attacker.get('types') or []):
            if (defender.get('volatile_statuses') or {}).get('curse'):
                return 0, "But it failed! The target is already cursed!", 'none', [], 0

            toll = max(1, math.floor(attacker.get('max_hp', 100) * CURSE_SELF_COST))
            attacker['current_hp'] = max(0, attacker['current_hp'] - toll)
            defender.setdefault('volatile_statuses', {})['curse'] = True
            return 0, (f"👻 {attacker['name'].capitalize()} cut its own health to lay a "
                       f"curse on {defender['name'].capitalize()}! (-{toll} HP)"), 'none', [], 0

        changes = [('attacker', stat, amount) for stat, amount in CURSE_STAT_CHANGES.items()]
        return 0, (f"😤 {attacker['name'].capitalize()} braced itself - slower, but far "
                   f"harder to move!"), 'none', changes, 0

    if move_name == 'teleport':
        # The switch itself is the engines' business; this only reports it, and the
        # pivot machinery declines when there is nobody in reserve.
        return 0, (f"✨ {attacker['name'].capitalize()} teleported away!"), 'none', [], 0

    # ==========================================
    # 🌍 FIELD-WIDE SPORTS, DELUGES AND SIDE SWAPS
    # ==========================================
    if move_name in SPORT_MOVES or move_name == 'ion-deluge':
        if field is None:
            return 0, "But it failed! There was no field to change!", 'none', [], 0

        flag = move_name.replace('-', '_')
        if field.get(flag, 0) > 0:
            return 0, "But it failed! It is already in effect!", 'none', [], 0

        if move_name == 'ion-deluge':
            field[flag] = ION_DELUGE_TURNS
            return 0, (f"⚡ A deluge of ions showered the field - Normal moves turned "
                       f"Electric!"), 'none', [], 0

        field[flag] = SPORT_TURNS
        damped = SPORT_MOVES[move_name].capitalize()
        return 0, (f"🌊 {attacker['name'].capitalize()} kicked up a sport - {damped} "
                   f"moves are weakened!"), 'none', [], 0

    if move_name == 'court-change':
        if not court_change(user_hazards, target_hazards):
            return 0, "But it failed! There was nothing to swap!", 'none', [], 0

        return 0, (f"🔄 {attacker['name'].capitalize()} swept everything across - the "
                   f"field effects changed sides!"), 'none', [], 0

    if move_name == 'happy-hour':
        if user_hazards is None:
            return 0, "But it failed! There was nobody to pay out!", 'none', [], 0
        if user_hazards.get('happy-hour'):
            return 0, "But it failed! It is already happy hour!", 'none', [], 0

        user_hazards['happy-hour'] = True
        return 0, (f"🎉 Everyone is caught up in a happy hour - the takings from this "
                   f"battle are doubled!"), 'none', [], 0

    # ==========================================
    # 🍽️ STOCKPILE AND SWALLOW
    # ==========================================
    # Spit Up is the third of the family, but it deals damage, so its power comes from
    # resolve_dynamic_power and only its empty-bank failure is handled down with the
    # other attacks.
    if move_name == 'stockpile':
        accepted, changes = add_stockpile(attacker)
        if not accepted:
            return 0, "But it failed! It cannot stockpile any more!", 'none', [], 0

        return 0, (f"🍽️ {attacker['name'].capitalize()} stockpiled "
                   f"{get_stockpile(attacker)}!"), 'none', changes, 0

    if move_name == 'swallow':
        held, changes = spend_stockpile(attacker)
        if not held:
            return 0, "But it failed! It had nothing stockpiled!", 'none', [], 0

        share = SWALLOW_HEAL_BY_STACK[held]
        healed = max(1, math.floor(attacker.get('max_hp', 100) * share))
        # The engines apply the healing amount; returning it keeps that in one place.
        return 0, (f"🍽️ {attacker['name'].capitalize()} swallowed {held} charge(s) "
                   f"and recovered {int(share * 100)}% of its health!"), 'none', changes, healed

    # ==========================================
    # 💗 RESTORATION AND SACRIFICE
    # ==========================================
    if move_name == 'aqua-ring':
        if (attacker.get('volatile_statuses') or {}).get('aqua_ring'):
            return 0, "But it failed! It is already veiled in water!", 'none', [], 0

        attacker.setdefault('volatile_statuses', {})['aqua_ring'] = True
        return 0, (f"💧 {attacker['name'].capitalize()} veiled itself in water - "
                   f"it will recover a little each turn!"), 'none', [], 0

    if move_name == 'refresh':
        current = (attacker.get('status_condition') or {}).get('name')
        if current not in REFRESH_CURES:
            return 0, "But it failed! There was nothing it could shake off!", 'none', [], 0

        attacker['status_condition'] = None
        return 0, (f"✨ {attacker['name'].capitalize()} refreshed itself and shook "
                   f"off its {current}!"), 'none', [], 0

    if move_name in SACRIFICE_MOVES:
        # The engines read this off the state and pay it to whoever takes the slot
        attacker['current_hp'] = 0
        attacker['_sacrifice_wish'] = SACRIFICE_MOVES[move_name]
        flavour = ("danced and faded away" if move_name == 'lunar-dance'
                   else "gave itself up")
        return 0, (f"💗 {attacker['name'].capitalize()} {flavour} so its "
                   f"replacement can arrive whole!"), 'none', [], 0

    if move_name == 'revival-blessing':
        name, healed = revive_fallen(user_party, exclude=attacker)
        if not name:
            return 0, "But it failed! Nobody had fallen!", 'none', [], 0

        return 0, (f"🕊️ {name} was revived and is ready to fight again! "
                   f"({healed} HP)"), 'none', [], 0

    # ==========================================
    # 🪞 REDIRECTION AND INTERCEPTION
    # ==========================================
    if move_name in ('magic-coat', 'snatch'):
        flag = move_name.replace('-', '_')
        if (attacker.get('volatile_statuses') or {}).get(flag):
            return 0, "But it failed! It is already braced!", 'none', [], 0

        attacker.setdefault('volatile_statuses', {})[flag] = True
        if move_name == 'magic-coat':
            return 0, (f"🪞 {attacker['name'].capitalize()} shrouded itself - "
                       f"status moves will bounce back!"), 'none', [], 0
        return 0, (f"🤚 {attacker['name'].capitalize()} is poised to snatch the "
                   f"next self-serving move!"), 'none', [], 0

    if move_name == 'powder':
        victim = defender.setdefault('volatile_statuses', {})
        if victim.get('powder'):
            return 0, "But it failed! It is already covered!", 'none', [], 0

        victim['powder'] = True
        return 0, (f"🟢 {defender['name'].capitalize()} was covered in a "
                   f"combustible powder!"), 'none', [], 0

    if move_name == 'electrify':
        victim = defender.setdefault('volatile_statuses', {})
        if victim.get('electrified'):
            return 0, "But it failed! It is already charged!", 'none', [], 0

        victim['electrified'] = True
        return 0, (f"⚡ {defender['name'].capitalize()} was electrified - its move "
                   f"turned Electric!"), 'none', [], 0

    # ==========================================
    # 🎭 COPY AND MIMICRY MOVES
    # ==========================================
    # The five that PERFORM another move are re-dispatched by the engines before they
    # ever reach here, so anything arriving with one of those names failed to resolve.
    if move_name == 'mimic':
        worked, note = apply_mimic(attacker, defender)
        return 0, note, 'none', [], 0

    if move_name == 'sketch':
        worked, note = apply_sketch(attacker, defender)
        return 0, note, 'none', [], 0

    # ==========================================
    # ⚡ PRIORITY-CONDITIONAL MOVES
    # ==========================================
    if move_name in FIRST_TURN_MOVES and not is_first_turn_out(attacker):
        return 0, (f"But it failed! {attacker['name'].capitalize()} has been out too "
                   f"long for that!"), 'none', [], 0

    if move_name == 'sucker-punch' and not is_readying_attack(defender):
        return 0, "But it failed! The target was not winding up an attack!", 'none', [], 0

    # Quash, After You and Instruct all shuffle one SIDE's turn order, and this engine
    # only ever fields a single specimen per side. There is nobody to move around, so they
    # say so rather than burning a turn on a silent no-op.
    if move_name == 'instruct':
        return 0, "But it failed! There is no ally to instruct!", 'none', [], 0

    if move_name in TURN_ORDER_MOVES:
        return 0, ("But it failed! With one specimen per side there is no turn order "
                   "left to rearrange!"), 'none', [], 0

    # ==========================================
    # 🪆 SUBSTITUTE
    # ==========================================
    # Shed Tail pays double for its decoy and then pivots out; the switch itself is the
    # engines' pivot handling, which only needs the decoy to exist first.
    if move_name in SUBSTITUTE_MOVES:
        worked, note = create_substitute(attacker, SUBSTITUTE_MOVES[move_name])
        return 0, note, 'none', [], 0

    # ==========================================
    # 💊 PARTY HEALS AND CLEANSES
    # ==========================================
    # These sit ahead of the generic healing block because several of them carry a
    # database healing percentage aimed at the wrong specimen - Purify's 50% belongs to
    # the USER, not the target it is curing.
    if move_name in PARTY_CURE_MOVES and move_class == 'status':
        cured = cure_party_status(user_party, attacker)
        if not cured:
            return 0, "But it failed! Nobody had anything to cure!", 'none', [], 0

        chime = "🔔" if move_name == 'heal-bell' else "🌸"
        return 0, (f"{chime} A soothing wave washed over the party - "
                   f"{', '.join(cured)} recovered!"), 'none', [], 0

    if move_name in SIDE_RESTORE_MOVES:
        max_hp = attacker.get('max_hp', 100)
        before = attacker.get('current_hp', 0)
        had_status = (attacker.get('status_condition') or {}).get('name')

        if before >= max_hp and not had_status:
            return 0, "But it failed! There was nothing to mend!", 'none', [], 0

        attacker['current_hp'] = min(max_hp, before + max(1, math.floor(max_hp * 0.25)))
        attacker['status_condition'] = None
        gained = attacker['current_hp'] - before

        note = f"🌿 {attacker['name'].capitalize()} restored {gained} HP"
        note += f" and shook off its {had_status}!" if had_status else "!"
        return 0, note, 'none', [], 0

    if move_name == 'take-heart':
        # Never fails: even at full health with no status it still steels the user.
        had_status = (attacker.get('status_condition') or {}).get('name')
        attacker['status_condition'] = None

        note = f"💗 {attacker['name'].capitalize()} took heart"
        note += f" and shook off its {had_status}!" if had_status else "!"
        return 0, note, 'none', [('attacker', 'special-attack', 1),
                                 ('attacker', 'special-defense', 1)], 0

    if move_name == 'purify':
        if not (defender.get('status_condition') or {}).get('name'):
            return 0, "But it failed! There was nothing to purify!", 'none', [], 0

        cleansed = defender['status_condition']['name']
        defender['status_condition'] = None

        # The user is repaid with half its own maximum HP - the database's 50% is aimed
        # at the target, which would otherwise heal the wrong specimen entirely.
        max_hp = attacker.get('max_hp', 100)
        before = attacker.get('current_hp', 0)
        attacker['current_hp'] = min(max_hp, before + max(1, math.floor(max_hp * 0.5)))
        gained = attacker['current_hp'] - before

        note = (f"💜 {attacker['name'].capitalize()} purified "
                f"{defender['name'].capitalize()}'s {cleansed}")
        note += f" and restored {gained} HP!" if gained else "!"
        return 0, note, 'none', [], 0

    # ==========================================
    # 🚨 RESTORATIVE MOVES
    # ==========================================
    # Rest is a special case: the database records no healing and no ailment for it, but
    # it is a full restore that puts the user to sleep for two turns.
    if move_name == 'rest':
        if attacker.get('current_hp', 0) >= attacker.get('max_hp', 1):
            return 0, "But it failed! Its health is already full!", 'none', [], 0

        attacker['current_hp'] = attacker.get('max_hp', 1)
        attacker['status_condition'] = {'name': 'sleep', 'duration': 2}
        return 0, f"😴 {attacker['name'].capitalize()} went to sleep and restored its health!", 'none', [], 0

    # Everything else drives off the database's healing percentage, which nothing was
    # reading until now - Recover, Roost, Soft-Boiled and the rest were all no-ops.
    heal_pct = move.get('healing') or 0
    if move_class == 'status' and heal_pct > 0:
        fraction = heal_pct / 100.0

        # Sun-fed recovery swings hard on the weather
        if move_name in ['synthesis', 'moonlight', 'morning-sun']:
            if weather in ['sun', 'extremely-harsh-sunlight']:
                fraction = 2.0 / 3.0
            elif weather in ['rain', 'heavy-rain', 'sandstorm', 'hail', 'snow']:
                fraction = 0.25
        elif move_name == 'shore-up' and weather == 'sandstorm':
            fraction = 2.0 / 3.0
        # Floral Healing draws on the ground it is standing on rather than the sky
        elif move_name == 'floral-healing' and terrain == 'grassy':
            fraction = 2.0 / 3.0

        # A few of these mend the opponent rather than the user
        mends_target = 'selected-pokemon' in str(move.get('target', ''))
        patient = defender if mends_target else attacker

        if patient.get('current_hp', 0) >= patient.get('max_hp', 1):
            return 0, "But it failed! Its health is already full!", 'none', [], 0

        restored = max(1, math.floor(patient.get('max_hp', 100) * fraction))
        before = patient['current_hp']
        patient['current_hp'] = min(patient.get('max_hp', 100), before + restored)
        gained = patient['current_hp'] - before

        return 0, f"💚 {patient['name'].capitalize()} restored {gained} HP!", 'none', [], 0

    # ==========================================
    # 🚨 SELF-DAMAGE STAT TRADES
    # ==========================================
    # Each pays a slice of maximum HP up front for a large boost, and each fails outright
    # if the user cannot afford the cost - the HP is never spent on a move that fizzles.
    if move_name in ['belly-drum', 'clangorous-soul', 'fillet-away']:
        max_hp = attacker.get('max_hp', 100)

        if move_name == 'clangorous-soul':
            cost = max(1, max_hp // 3)
            boosts = [('attacker', s, 1) for s in
                      ['attack', 'defense', 'special-attack', 'special-defense', 'speed']]
            flavour = "raised every stat"
        elif move_name == 'fillet-away':
            cost = max(1, max_hp // 2)
            boosts = [('attacker', s, 2) for s in ['attack', 'special-attack', 'speed']]
            flavour = "sharply raised Attack, Sp. Attack and Speed"
        else:  # belly-drum
            cost = max(1, max_hp // 2)
            current = (attacker.get('stat_stages') or {}).get('attack', 0)
            if current >= 6:
                return 0, "But it failed! Its Attack is already maxed out!", 'none', [], 0
            # Belly Drum jumps straight to the +6 ceiling rather than adding a fixed amount
            boosts = [('attacker', 'attack', 6 - current)]
            flavour = "maximised its Attack"

        if attacker.get('current_hp', 0) <= cost:
            return 0, "But it failed! There isn't enough health to pay the price!", 'none', [], 0

        attacker['current_hp'] = max(1, attacker['current_hp'] - cost)
        return 0, f"💥 {attacker['name'].capitalize()} spent {cost} HP and {flavour}!", 'none', boosts, 0

    # ==========================================
    # 🚨 STAT & HP SPLITS
    # ==========================================
    # These rewrite the raw stat block rather than adding a stage, so any stat stages
    # already in play still layer on top of the new baseline afterwards.
    #
    # NOTE: the split persists for the rest of the battle rather than resetting when the
    # specimen switches out. That matches how this engine already treats stat stages on a
    # voluntary swap, so the two behave consistently.
    if move_name in ['guard-split', 'power-split']:
        pair = ('defense', 'sp_def') if move_name == 'guard-split' else ('attack', 'sp_atk')
        label = "Defense and Sp. Defense" if move_name == 'guard-split' else "Attack and Sp. Attack"

        atk_stats = attacker.setdefault('stats', {})
        def_stats = defender.setdefault('stats', {})

        # Remember the originals so a switch-out can undo the rewrite
        snapshot_base_stats(attacker)
        snapshot_base_stats(defender)

        for stat in pair:
            averaged = (atk_stats.get(stat, 50) + def_stats.get(stat, 50)) // 2
            atk_stats[stat] = averaged
            def_stats[stat] = averaged

        return 0, f"⚖️ {attacker['name'].capitalize()} shared its power! {label} were averaged with {defender['name'].capitalize()}!", 'none', [], 0

    # ==========================================
    # 🚨 STAT SWAPS
    # ==========================================
    # Guard/Power/Heart Swap trade stat STAGES, leaving the underlying stats alone.
    if move_name in ['guard-swap', 'power-swap', 'heart-swap']:
        a_stages = attacker.setdefault('stat_stages', {})
        d_stages = defender.setdefault('stat_stages', {})

        if move_name == 'guard-swap':
            keys, label = ['defense', 'sp_def'], "defensive"
        elif move_name == 'power-swap':
            keys, label = ['attack', 'sp_atk'], "offensive"
        else:
            keys, label = ALL_STAT_STAGES, "every"

        for stat in keys:
            a_stages[stat], d_stages[stat] = d_stages.get(stat, 0), a_stages.get(stat, 0)

        return 0, f"🔄 {attacker['name'].capitalize()} swapped {label} changes with {defender['name'].capitalize()}!", 'none', [], 0

    if move_name == 'psych-up':
        # A straight copy, not a trade - the target keeps what it had.
        attacker['stat_stages'] = dict(defender.get('stat_stages') or {})
        return 0, f"🧠 {attacker['name'].capitalize()} copied {defender['name'].capitalize()}'s stat changes!", 'none', [], 0

    # Speed Swap and Power Trick trade the RAW stats rather than the stages.
    if move_name == 'speed-swap':
        a_stats = attacker.setdefault('stats', {})
        d_stats = defender.setdefault('stats', {})
        snapshot_base_stats(attacker)
        snapshot_base_stats(defender)
        a_stats['speed'], d_stats['speed'] = d_stats.get('speed', 50), a_stats.get('speed', 50)
        return 0, f"💨 {attacker['name'].capitalize()} traded Speed with {defender['name'].capitalize()}!", 'none', [], 0

    # Power Shift is Power Trick under another name - both turn the user's own Attack and
    # Defense inside out - so it shares the implementation rather than growing a second.
    if move_name in ('power-trick', 'power-shift'):
        # Self-targeting: the user turns its own Attack and Defense inside out.
        a_stats = attacker.setdefault('stats', {})
        snapshot_base_stats(attacker)
        a_stats['attack'], a_stats['defense'] = a_stats.get('defense', 50), a_stats.get('attack', 50)
        return 0, f"🔃 {attacker['name'].capitalize()} switched its own Attack and Defense!", 'none', [], 0

    if move_name == 'topsy-turvy':
        stages = defender.get('stat_stages') or {}
        if not any(stages.values()):
            return 0, "But it failed! There was nothing to turn around!", 'none', [], 0

        # Inverted, not cleared: a +2 becomes a -2. Haze is the one that wipes them.
        for stat, stage in list(stages.items()):
            stages[stat] = -stage

        return 0, (f"🙃 {defender['name'].capitalize()}'s stat changes were all turned "
                   f"upside down!"), 'none', [], 0

    # Two straightforward self-buffs whose database rows carry no stat_name at all, which
    # is why the generic path had nothing to apply and they did nothing.
    if move_name in SELF_BUFF_MOVES:
        boosts = SELF_BUFF_MOVES[move_name]
        changes = [('attacker', stat, amount) for stat, amount in boosts.items()]
        flavour = ("danced in celebration" if move_name == 'victory-dance'
                   else "hardened its surface like iron")
        return 0, f"💪 {attacker['name'].capitalize()} {flavour}!", 'none', changes, 0

    if move_name == 'pain-split':
        pooled = attacker.get('current_hp', 0) + defender.get('current_hp', 0)
        shared = pooled // 2

        # Neither side can be topped up past its own maximum
        attacker['current_hp'] = min(attacker.get('max_hp', shared), shared)
        defender['current_hp'] = min(defender.get('max_hp', shared), shared)

        return 0, f"💔 The pain was shared! Both specimens settled at {shared} HP!", 'none', [], 0

    # ==========================================
    # 🚨 CRIT SETUP MOVES
    # ==========================================
    if move_name == 'focus-energy':
        if attacker['volatile_statuses'].get('focus_energy'):
            return 0, "But it failed! It is already fired up!", 'none', [], 0
        attacker['volatile_statuses']['focus_energy'] = True
        return 0, f"🔥 {attacker['name'].capitalize()} is getting pumped! Its critical hit ratio rose!", 'none', [], 0

    if move_name == 'laser-focus':
        attacker['volatile_statuses']['laser_focus'] = True
        return 0, f"🎯 {attacker['name'].capitalize()} began focusing intently! Its next strike will be critical!", 'none', [], 0

    if move_name == 'perish-song':
        stat_changes.append(('attacker', 'volatile_perish_song', 3))
        stat_changes.append(('defender', 'volatile_perish_song', 3))
        return 0, "All Pokémon hearing the song will faint in 3 turns!", None, stat_changes, 0
    
    if move_name == 'leech-seed':
        if 'grass' in (defender.get('types') or []):
            return 0, "It doesn't affect Grass-type Pokémon!", None, stat_changes, 0
        else:
            stat_changes.append(('defender', 'volatile_leech_seed', 1))
            return 0, f"{defender['name'].capitalize()} was seeded!", None, stat_changes, 0

    # ==========================================
    # 🚨 NEW: RETALIATION OVERRIDES
    # ==========================================
    if move_name == 'counter':
        if attacker.get('last_damage_class') == 'physical' and attacker.get('last_damage_taken', 0) > 0:
            return attacker['last_damage_taken'] * 2, "It powerfully countered the strike!", 'none', [], 0
        return 0, "But it failed!", 'none', [], 0
        
    if move_name == 'mirror-coat':
        if attacker.get('last_damage_class') == 'special' and attacker.get('last_damage_taken', 0) > 0:
            return attacker['last_damage_taken'] * 2, "It reflected the special attack!", 'none', [], 0
        return 0, "But it failed!", 'none', [], 0
        
    if move_name == 'metal-burst':
        if attacker.get('last_damage_taken', 0) > 0:
            return math.floor(attacker['last_damage_taken'] * 1.5), "It retaliated with a burst of metal!", 'none', [], 0
        return 0, "But it failed!", 'none', [], 0
    
    # ==========================================
    # 🚨 FIXED DAMAGE & HP ANOMALIES
    # ==========================================
    # These moves ignore Attack/Defense, STAB, criticals and effectiveness, but a 0x
    # elemental matchup is still an absolute wall. One guard covers the whole family.
    if move_name in FORMULA_BYPASS_MOVES and type_multiplier == 0.0:
        return 0, "It had no effect!", 'none', [], 0

    if move_name == 'endeavor':
        if defender['current_hp'] > attacker['current_hp']:
            # Drags the target down to the user's HP, so it can never land a KO
            fixed_damage = defender['current_hp'] - attacker['current_hp']
            return fixed_damage, "It savagely cut down the target's HP!", 'none', [], 0
        return 0, "But it failed!", 'none', [], 0

    if move_name in ['seismic-toss', 'night-shade']:
        # These moves always deal damage exactly equal to the user's level
        fixed_damage, survival_msg = apply_survival_floor(defender, attacker.get('level', 50), magic_room)
        return fixed_damage, survival_msg.strip(), 'none', [], 0

    if move_name in ['super-fang', 'natures-madness', 'ruination']:
        # These moves instantly halve the defender's current HP!
        fixed_damage = max(1, math.floor(defender['current_hp'] / 2))
        fixed_damage, survival_msg = apply_survival_floor(defender, fixed_damage, magic_room)
        return fixed_damage, survival_msg.strip(), 'none', [], 0

    # ==========================================
    # 🚨 SET-DAMAGE ANOMALIES (Dragon Rage, Sonic Boom, Psywave, Final Gambit)
    # ==========================================
    if move_name in FIXED_DAMAGE_MOVES:
        fixed_damage = get_fixed_damage(move_name, attacker)

        if move_name == 'final-gambit':
            # Nothing left to donate means the move simply fizzles
            if fixed_damage <= 0:
                return 0, "But it failed!", 'none', [], 0
            # The user pays its full remaining HP the instant the attack connects.
            # We zero it here rather than in the Phase 4 self-KO hook because this
            # branch returns early and never reaches it.
            attacker['current_hp'] = 0

        fixed_damage, survival_msg = apply_survival_floor(defender, fixed_damage, magic_room)

        flavor_text = {
            'dragon-rage': "💢 A pulse of pure draconic rage slammed into the target!",
            'sonic-boom': "💥 A compressed shockwave of air struck the target!",
            'psywave': "🌀 An erratic wave of psychic energy washed over the target!",
            'final-gambit': f"💀 {attacker['name'].capitalize()} sacrificed itself, hurling its entire life force at the target!"
        }[move_name]

        return fixed_damage, (flavor_text + survival_msg).strip(), 'none', [], 0

    # ==========================================
    # ==========================================
    # 🚨 ONE-HIT KO ANOMALIES
    # ==========================================
    if move_name in OHKO_MOVES:
        atk_lvl = attacker.get('level', 50)
        def_lvl = defender.get('level', 50)
        
        # 1. Level Failsafe
        if atk_lvl < def_lvl:
            return 0, "But it failed! The target's level is too high!", 'none', [], 0
            
        # 2. Total Immunities (Sturdy & Ice-Types)
        if def_ability == 'sturdy':
            return 0, f"{defender['name'].capitalize()}'s Sturdy makes it completely immune to One-Hit KO moves!", 'none', [], 0
            
        if move_name == 'sheer-cold' and 'ice' in (defender.get('types') or []):
            return 0, "It doesn't affect Ice-type Pokémon!", 'none', [], 0
            
        # 3. Dynamic Accuracy Calculation
        base_ohko_acc = 30 + (atk_lvl - def_lvl)
        
        # In modern generations, non-Ice types suffer a massive accuracy penalty when using Sheer Cold!
        if move_name == 'sheer-cold' and 'ice' not in (attacker.get('types') or []):
            base_ohko_acc = 20 + (atk_lvl - def_lvl)
        
        has_no_guard = (atk_ability == 'no-guard' or def_ability == 'no-guard')

        if not has_no_guard and random.randint(1, 100) > base_ohko_acc:
            return 0, "The attack missed!", 'none', [], 0
            
        # 4. The Lethal Payload
        # We return exactly the defender's current HP to guarantee a faint, unless a
        # Focus Sash or Endure clamps it. (Sturdy already returned outright above.)
        lethal_damage, survival_msg = apply_survival_floor(defender, defender['current_hp'], magic_room)

        if survival_msg:
            return lethal_damage, survival_msg.strip(), 'none', [], 0

        return lethal_damage, "It's a One-Hit KO!", 'none', [], 0
    
    # PHASE 1: KINETIC & SPECIAL DAMAGE (The Multi-Strike Engine)
    # ==========================================
    # Resolved before the gate below: Flail, Gyro Ball, Grass Knot, Punishment and
    # friends are all stored as 0 power in the database, so without this they'd be
    # filtered out as non-damaging and silently deal nothing.
    # Spit Up is the damaging end of the Stockpile family: it needs a bank to spend, and
    # empties it on the way out. Read before the power resolves, since resolving it is
    # what the bank is for.
    if move_name == 'spit-up' and not get_stockpile(attacker):
        return 0, "But it failed! It had nothing stockpiled!", 'none', [], 0

    dynamic_power = item_power or resolve_dynamic_power(move_name, attacker, defender)

    if move_name == 'spit-up':
        # Emptied here rather than after the swing, so the stages Stockpile granted are
        # handed back in the same breath the power is taken.
        stat_changes.extend(spend_stockpile(attacker)[1])

    if move.get('class') != 'status' and (move.get('power', 0) > 0 or dynamic_power):
        level = attacker.get('level', 50)
        
        # ==========================================
        # 🚨 STAT SELECTION
        # ==========================================
        # One resolver decides which Attack and Defense stats this move reads, applying
        # stat stages, Wonder Room and Assault Vest. `effective_class` is what the move
        # actually resolved as, which can differ from its stored category for Photon
        # Geyser and Shell Side Arm.
        a, d, effective_class = resolve_combat_stats(move_name, move_class, attacker, defender, wonder_room, magic_room)

        # A critical hit reads the same stats with unfavourable stages stripped out. We
        # resolve that variant up front and express it as a ratio, so the multi-strike loop
        # can apply it per hit without recomputing the whole base damage.
        a_crit, d_crit, _ = resolve_combat_stats(move_name, move_class, attacker, defender,
                                                 wonder_room, magic_room, ignore_boosts=True)

        # Choice items reinforce the offensive stat the move ended up swinging with
        if effective_class == 'physical':
            if attacker_item == 'choice-band':
                a = math.floor(a * 1.5)
                a_crit = math.floor(a_crit * 1.5)
        else:
            if attacker_item == 'choice-specs':
                a = math.floor(a * 1.5)
                a_crit = math.floor(a_crit * 1.5)

        normal_ratio = a / max(1, d)
        crit_stat_ratio = (a_crit / max(1, d_crit)) / normal_ratio if normal_ratio > 0 else 1.0


        # 🚨 THE BATTLE BOND MUTATION
        move_power = move.get('power', 0)
        if move_name == 'water-shuriken' and atk_ability == 'battle-bond':
            move_power = 20

        # 🚨 DYNAMIC POWER OVERRIDE
        # Replaces the stored power outright. Some of these ship with a misleading fixed
        # value (Eruption 150, Hex 65, Revenge 60), so the override is what actually makes
        # them respond to the battle state.
        if dynamic_power is not None:
            move_power = dynamic_power

        # A handful of G-Max moves have a fixed power that outranks the engines' 140
        if move.get('name') in GMAX_FIXED_POWER:
            move_power = GMAX_FIXED_POWER[move['name']]

        # ==========================================
        # 🚨 CONDITIONAL POWER MULTIPLIERS
        # ==========================================
        atk_status = (attacker.get('status_condition') or {}).get('name')
        def_status = (defender.get('status_condition') or {}).get('name')

        # 1. Pathogen Synergies
        if move_name == 'facade' and atk_status in ['burn', 'poison', 'paralysis']:
            move_power *= 2
        elif move_name == 'wake-up-slap' and def_status == 'sleep':
            move_power *= 2
        elif move_name == 'smelling-salts' and def_status == 'paralysis':
            move_power *= 2
            
        # 2. Biological HP & Timeline States
        elif move_name == 'brine' and defender['current_hp'] <= (defender.get('max_hp', 100) / 2):
            move_power *= 2
        elif move_name == 'assurance' and defender.get('last_damage_taken', 0) > 0:
            move_power *= 2
        elif move_name == 'payback' and attacker.get('last_damage_taken', 0) > 0:
            # If the attacker took damage before moving, Payback doubles!
            move_power *= 2
        elif move_name == 'lash-out' and attacker.get('volatile_statuses', {}).get('stats_lowered_this_turn'):
            move_power *= 2
        elif move_name == 'pursuit' and defender.get('volatile_statuses', {}).get('is_switching'):
            move_power *= 2
            
        # 2a. Ambush Amplifiers (Bolt Beak / Fishious Rend)
        # Doubles when the user strikes before the target has acted. A target that merely
        # switched in has not acted, so it still eats the full-power hit.
        if move_name in AMBUSH_MOVES and not defender.get('acted_this_turn'):
            move_power *= 2
            msg += " ⚡ It struck before the target could react! "

        # 2b. Super-Effective Amplifiers (Collision Course / Electro Drift)
        # These stack on top of the type multiplier, which is applied separately later.
        if move_name in SUPER_EFFECTIVE_BONUS_MOVES and type_multiplier > 1.0:
            move_power = math.floor(move_power * 5461 / 4096) # ~1.3333x
            msg += " 💢 It capitalised on the weakness! "

        # 2c. Solar Dimming
        # Solar Beam skips its charge turn in sunlight (handled by the engines' two-turn
        # table); here we only dim it when the sky is obscured.
        if move_name in SOLAR_MOVES and weather in SOLAR_DIMMING_WEATHER:
            move_power = math.floor(move_power * 0.5)
            msg += " ☁️ The harsh conditions smothered the light! "

        # 3. Spatial Synergies (Terrains)
        if is_grounded(attacker):
            # Modern generation multiplier is 1.3x
            if terrain == 'electric' and move_type == 'electric': move_power *= 1.3
            elif terrain == 'grassy' and move_type == 'grass': move_power *= 1.3
            elif terrain == 'psychic' and move_type == 'psychic': move_power *= 1.3

            # Move-specific terrain synergies. Deliberately a separate check rather than
            # another elif, so Expanding Force collects both this and the generic bonus.
            terrain_boost = TERRAIN_POWER_MOVES.get(move_name)
            if terrain_boost and terrain == terrain_boost[0]:
                move_power *= terrain_boost[1]


        if is_grounded(defender):
            # Misty Terrain halves Dragon damage
            if terrain == 'misty' and move_type == 'dragon': move_power *= 0.5
            # Grassy Terrain halves specific seismic moves
            elif terrain == 'grassy' and move_name in ['earthquake', 'bulldoze', 'magnitude']: move_power *= 0.5
            
        elif move_name == 'rising-voltage' and terrain == 'electric':
            move_power *= 2

        # KNOCK OFF KINETIC AMPLIFIER
        # Checks if the item exists and isn't a symbiotic un-removable item!
        if move_name == 'knock-off' and is_transferable_item(get_stored_item(defender)):
            move_power = math.floor(move_power * 1.5)
        
        # (Defensive stats were already resolved above - Wonder Room and Assault Vest
        # included - so `d` is used directly here rather than being recomputed.)

        # 1. Calculate raw structural damage BEFORE random variance and multipliers
        base_damage_unmodified = (((2 * level / 5) + 2) * move_power * (a / max(1, d))) / 50 + 2

        # 🚨 BURN PENALTY (Physical moves deal half damage, unless it is Facade or Guts!)
        if effective_class == 'physical' and atk_status == 'burn' and move_name != 'facade' and atk_ability != 'guts':
            base_damage_unmodified = math.floor(base_damage_unmodified * 0.5)

        # ==========================================
        # 🚨 SPATIAL VULNERABILITY MULTIPLIER
        # ==========================================
        defender_invuln = defender.get('volatile_statuses', {}).get('semi_invulnerable')
        if defender_invuln == 'underground' and move_name in ['earthquake', 'magnitude']:
            base_damage_unmodified *= 2.0
            msg += " It struck the target hiding underground! "
        elif defender_invuln == 'air' and move_name in ['gust', 'twister']:
            base_damage_unmodified *= 2.0
            msg += " It struck the target up in the air! "
            
        stab = 1.5 if move_type in (attacker.get('types') or []) else 1.0

        weather_mod = 1.0
        if weather in ['sun', 'extremely-harsh-sunlight']:
            # 🚨 HYDRO STEAM: superheated water. Sunlight amplifies it by 50% instead of
            # applying the usual Water-type penalty.
            if move_name == 'hydro-steam':
                weather_mod = 1.5
            elif move_type == 'fire': weather_mod = 1.5
            elif move_type == 'water': weather_mod = 0.5
        elif weather in ['rain', 'heavy-rain']:
            if move_type == 'water': weather_mod = 1.5
            elif move_type == 'fire': weather_mod = 0.5

        # Mud Sport and Water Sport smother their element wherever it is thrown from.
        # Folded into the weather modifier because it is the same kind of thing: an
        # environmental damper on one type, applied once per strike.
        weather_mod *= sport_multiplier(move_type, field)

        ability_mod = 1.0
        amplifier = BIOLOGICAL_TRAITS.get('damage_multipliers', {}).get(atk_ability)
        if amplifier:
            cond = amplifier['condition']
            mult = amplifier['multiplier']
            if cond == 'contact' and move.get('class') == 'physical': ability_mod *= mult
            elif cond == 'punch' and 'punch' in move_name: ability_mod *= mult
            elif cond == 'bite' and any(term in move_name for term in ['bite', 'fang', 'crunch']): ability_mod *= mult
            elif cond == 'pulse' and any(term in move_name for term in ['pulse', 'aura-sphere']): ability_mod *= mult
            elif cond == 'power_cap' and 0 < move_power <= amplifier['threshold']: ability_mod *= mult
        
        if atk_ability == 'flash-fire' and move_type == 'fire' and attacker.get('volatile_statuses', {}).get('flash_fire'):
            ability_mod *= 1.5
        if def_ability == 'dry-skin' and move_type == 'fire':
            ability_mod *= 1.25

        hp_threshold = attacker.get('max_hp', 100) / 3
        if attacker.get('current_hp', 100) <= hp_threshold:
            boosted_type = BIOLOGICAL_TRAITS.get('pinch_boosters', {}).get(atk_ability)
            if boosted_type == move_type:
                ability_mod *= 1.5

        # Offensive Equipment
        if attacker_item == 'life-orb': ability_mod *= 1.3
        if attacker_item == 'expert-belt' and type_multiplier > 1.0: ability_mod *= 1.2

        # ==========================================
        # 🚨 THE MULTI-STRIKE EVALUATOR
        # ==========================================
        target_hits = 1
        
        # 1. Fixed-Hit Anomalies
        if move_name == 'water-shuriken' and atk_ability == 'battle-bond':
            target_hits = 3
        elif move_name in ['triple-kick', 'triple-axel']:
            target_hits = 3
        elif move_name == 'population-bomb':
            target_hits = 10
            
        # 2. Standard Multi-Strikes (2-to-5 hits)
        elif move_name in MULTI_STRIKE_MOVES:
            hit_data = MULTI_STRIKE_MOVES[move_name]
            if atk_ability == 'skill-link':
                target_hits = hit_data['max']
            elif hit_data['max'] == 5:
                roll = random.randint(1, 100)
                if roll <= 35: target_hits = 2
                elif roll <= 70: target_hits = 3
                elif roll <= 85: target_hits = 4
                else: target_hits = 5
            else:
                target_hits = random.randint(hit_data['min'], hit_data['max'])

        hits_landed = 0
        total_damage = 0
        simulated_hp = defender.get('current_hp', 100)
        crit_occurred = False
        
        berry_resist_map = {
            'occa-berry': 'fire', 'passho-berry': 'water', 'wacan-berry': 'electric',
            'rindo-berry': 'grass', 'yache-berry': 'ice', 'chople-berry': 'fighting',
            'kebia-berry': 'poison', 'shuca-berry': 'ground', 'coba-berry': 'flying',
            'payapa-berry': 'psychic', 'tanga-berry': 'bug', 'charti-berry': 'rock',
            'kasib-berry': 'ghost', 'haban-berry': 'dragon', 'colbur-berry': 'dark',
            'babiri-berry': 'steel', 'roseli-berry': 'fairy', 'chilan-berry': 'normal'
        }

        # ==========================================
        # 2. THE KINETIC EXECUTION LOOP
        # ==========================================
        for strike in range(target_hits):
            
            # --- A. ACCURACY-DEPENDENT BREAK CHECKS ---
            # We only check accuracy for strike > 0, because the first hit already passed the global accuracy check!
            if strike > 0 and move_name in ['triple-kick', 'triple-axel', 'population-bomb']:
                if atk_ability != 'skill-link':
                    move_acc = move.get('accuracy', 90)
                    if not isinstance(move_acc, int): move_acc = 90 # Failsafe for 'True' accuracy values
                    
                    if random.randint(1, 100) > move_acc:
                        break # The kinetic chain breaks immediately upon missing!

            # --- B. PROGRESSIVE POWER SCALING ---
            if move_name == 'triple-kick':
                current_power = 10 * (strike + 1) # 10 -> 20 -> 30
                base_damage_unmodified = (((2 * level / 5) + 2) * current_power * (a / max(1, d))) / 50 + 2
            elif move_name == 'triple-axel':
                current_power = 20 * (strike + 1) # 20 -> 40 -> 60
                base_damage_unmodified = (((2 * level / 5) + 2) * current_power * (a / max(1, d))) / 50 + 2
            elif move_name == 'population-bomb':
                current_power = 20
                base_damage_unmodified = (((2 * level / 5) + 2) * current_power * (a / max(1, d))) / 50 + 2

            # Now that accuracy and power are locked, record the hit!
            hits_landed += 1
            
            # --- C. RE-ROLL CRITICALS & VARIANCE ---
            HIGH_CRIT_MOVES = [
                'air-cutter', 'attack-order', 'blaze-kick', 'crabhammer', 'cross-chop', 
                'cross-poison', 'drill-run', 'esper-wing', 'ivy-cudgel', 'karate-chop', 
                'leaf-blade', 'night-slash', 'poison-tail', 'psycho-cut', 'razor-leaf',
                'razor-wind', 'shadow-claw', 'slash', 'snipe-shot', 'spacial-rend',
                'stone-edge', 'triple-arrows', 'sky-attack'
            ]
            
            crit_stage = 0
            if move_name in HIGH_CRIT_MOVES:
                crit_stage += 1
                
            # Future-proofing for items/statuses!
            if attacker.get('volatile_statuses', {}).get('focus_energy'):
                crit_stage += 2
            if attacker_item == 'scope-lens' or attacker_item == 'razor-claw':
                crit_stage += 1
                
            # Calculate the final threshold based on modern ecosystem rules
            if crit_stage == 0: crit_chance = 24  # ~4.17%
            elif crit_stage == 1: crit_chance = 8 # 12.5%
            elif crit_stage == 2: crit_chance = 2 # 50%
            else: crit_chance = 1                 # 100% Guaranteed!
            
            # Battle Armor, Shell Armor and a Lucky Chant on the defending side all shut
            # out criticals entirely - including the guaranteed ones, which is why both
            # checks sit ahead of the forced-crit branch.
            if def_ability in ['battle-armor', 'shell-armor']:
                is_crit = False
            elif is_crit_shielded(target_hazards):
                is_crit = False
            elif is_crit_guaranteed(move_name, attacker):
                is_crit = True
            else:
                is_crit = (random.randint(1, crit_chance) == 1)

            if is_crit: crit_occurred = True
            
            hit_modifier = type_multiplier * stab * weather_mod * ability_mod * random.uniform(0.85, 1.00)
            
            # 🚨 GLAIVE RUSH VULNERABILITY
            if defender.get('volatile_statuses', {}).get('glaive_rush'):
                hit_modifier *= 2.0
                
            if move_name == 'glaive-rush':
                # Flag the attacker as vulnerable for the next turn!
                attacker['volatile_statuses']['glaive_rush'] = True

            # ==========================================
            # 🚨 SCREEN BREAKING & MITIGATION
            # ==========================================
            if target_hazards is not None:
                # 1. Screen Shattering (Brick Break, Psychic Fangs)
                if move_name in ['brick-break', 'psychic-fangs']:
                    shattered = False
                    # Deliberately NOT SIDE_SCREEN_MOVES: these shatter the damage screens
                    # only. Lucky Chant is not a barrier and survives them.
                    for screen in ['reflect', 'light-screen', 'aurora-veil']:
                        if target_hazards.get(screen, 0) > 0:
                            target_hazards[screen] = 0
                            shattered = True
                    if shattered:
                        msg += " 💥 The protective barriers were shattered! "
                
                # 2. Damage Mitigation
                # Screens are completely bypassed by Critical Hits and the Infiltrator ability!
                elif not is_crit and atk_ability != 'infiltrator':
                    # Screens key off the category the move actually resolved as, so a
                    # physical Photon Geyser is stopped by Reflect rather than Light Screen.
                    if effective_class == 'physical' and (target_hazards.get('reflect', 0) > 0 or target_hazards.get('aurora-veil', 0) > 0):
                        hit_modifier *= 0.5
                    elif effective_class == 'special' and (target_hazards.get('light-screen', 0) > 0 or target_hazards.get('aurora-veil', 0) > 0):
                        hit_modifier *= 0.5
            # ==========================================
            
            hit_damage = math.floor(base_damage_unmodified * hit_modifier)
            if is_crit:
                # 1.5x, plus the stat ratio recomputed with unfavourable stages ignored
                hit_damage = math.floor(hit_damage * 1.5 * crit_stat_ratio)
            
            # --- D. DEFENSIVE RESIST BERRIES (Only triggers on the VERY FIRST strike) ---
            if strike == 0 and defender_item in berry_resist_map:
                protected_type = berry_resist_map[defender_item]
                if move_type == protected_type and (type_multiplier > 1.0 or protected_type == 'normal'):
                    hit_damage = math.floor(hit_damage * 0.5)
                    defender['held_item'] = 'none'
                    defender['_ate_berry'] = True
                    mark_item_consumed(defender, defender_item)
                    defender_item = 'none' 
                    msg += f" 🛡️ {defender['name'].capitalize()}'s {protected_type.title()}-Resistance Berry weakened the damage! "
                    
            total_damage += hit_damage
            simulated_hp -= hit_damage
                    
            # --- F. PHYSICAL RECOIL (Rocky Helmet & Rough Skin) ---
            # Applied straight to the attacker's HP. Routing it through healing_amount
            # silently discarded it, because both engines only act on a POSITIVE heal.
            if move.get('class') == 'physical':
                if defender_item == 'rocky-helmet':
                    spike_dmg = max(1, math.floor(attacker.get('max_hp', 100) / 6))
                    attacker['current_hp'] = max(0, attacker['current_hp'] - spike_dmg)
                    msg += f" 💥 {attacker['name'].capitalize()} was hurt by the Rocky Helmet!"
                if def_ability in BIOLOGICAL_TRAITS.get('contact_damage', []):
                    skin_dmg = max(1, math.floor(attacker.get('max_hp', 100) / 8))
                    attacker['current_hp'] = max(0, attacker['current_hp'] - skin_dmg)
                    msg += f" 💥 {attacker['name'].capitalize()} was hurt by {defender['name'].capitalize()}'s {def_ability.replace('-', ' ').title()}!"
                    
            # --- G. LETHALITY CHECK ---
            if simulated_hp <= 0:
                break
        # ==========================================
        # 3. FINALIZE THE AGGREGATED DATA
        # ==========================================
        damage = total_damage

        # Report how many strikes actually connected, so a 5-hit Bullet Seed advances
        # Rage Fist by 5 rather than by 1.
        defender['last_hit_count'] = max(1, hits_landed)

        # Laser Focus is spent on the first damaging move that follows it, whether or not
        # the crit was actually allowed through (Shell Armor still consumes the charge).
        attacker['volatile_statuses'].pop('laser_focus', None)
        
        if type_multiplier > 1.0: msg += "It's super effective! "
        elif type_multiplier > 0.0 and type_multiplier < 1.0: msg += "It's not very effective... "
        elif type_multiplier == 0.0: return 0, "It had no effect!", None, [], 0

        if crit_occurred: msg += "A critical strike! "
        if hits_landed > 1: msg += f"Hit {hits_landed} times! "
        
        if move.get('drain', 0) > 0:
            healing_amount += math.floor(damage * (move['drain'] / 100.0))

    # ==========================================
    # PHASE 2: PATHOGENS, AILMENTS, & SECONDARY EFFECTS
    # ==========================================
    ailment = move.get('ailment', 'none')
    
    if ailment not in ['none', 'unknown', None]:
        current_status = defender.get('status_condition')
        is_afflicted = current_status is not None and isinstance(current_status, dict) and current_status.get('name') is not None
        
        if not is_afflicted or ailment == 'trap': # 🚨 Allow traps even if they are poisoned/burned!
            chance = move.get('ailment_chance', 0)
            if chance == 0 and move.get('class') == 'status':
                chance = 100
                
            if random.randint(1, 100) <= chance:
                inflicted_status = ailment
        else:
            if move.get('class') == 'status':
                msg += f" But it failed because {defender['name'].capitalize()} is already afflicted!"
                
    # ==========================================
    # 🚨 TERRAIN PATHOGEN BLOCKERS
    # ==========================================
    # 🚨 UPROAR: the racket keeps everyone awake, whichever side is making it
    if inflicted_status == 'sleep' and is_uproar_active(attacker, defender):
        inflicted_status = None
        msg += " 📢 The uproar kept everyone awake!"

    if inflicted_status and inflicted_status != 'none':
        if is_grounded(defender):
            if terrain == 'misty' and inflicted_status != 'trap':
                inflicted_status = None
                msg += f" 🌫️ The Misty Terrain protected {defender['name'].capitalize()} from the status condition!"
            elif terrain == 'electric' and inflicted_status == 'sleep':
                inflicted_status = None
                msg += f" ⚡ The Electric Terrain prevented {defender['name'].capitalize()} from falling asleep!"

    # ==========================================
    # THE DATABASE TRAP CONVERTER
    # ==========================================
    if inflicted_status == 'trap':
        if 'partially_trapped' not in defender.get('volatile_statuses', {}):
            if 'volatile_statuses' not in defender:
                defender['volatile_statuses'] = {}
            # Traps lock the victim in for 4 to 5 turns!
            defender['volatile_statuses']['partially_trapped'] = random.randint(4, 5)
            msg += f" 🌪️ {defender['name'].capitalize()} became trapped in the vortex!"
            
        # Wipe the variable so it doesn't return to the main loop and overwrite their primary Status Condition!
        inflicted_status = None

    # --- SECONDARY VOLATILE EFFECTS (Flinch, Confusion, G-Max Disasters) ---
    status_type = move.get('status_type', 'none')
    status_chance = move.get('status_chance', 0)
    
    # Secondary effects only trigger if the kinetic attack actually landed and dealt damage!
    if status_type not in ['none', None] and status_chance > 0 and damage > 0:
        if random.randint(1, 100) <= status_chance:
            if status_type == 'flinch':
                # Directly inject the flinch flag into the defender's biology!
                defender['volatile_statuses']['flinch'] = True
                # (Note: We don't append to msg here because handle_move handles the Flinch printout on their turn)
            elif status_type == 'confusion':
                # Confusion lasts for 2 to 5 turns
                defender['volatile_statuses']['confusion'] = random.randint(2, 5)
                msg += f" {defender['name'].capitalize()} became confused!"

    # ==========================================
    # HARD TRAPS & ANCHORS (Anchor Shot, Block, Jaw Lock)
    # ==========================================
    # These only apply if the move is a status move, or if the kinetic strike dealt damage!
    if damage > 0 or move.get('class') == 'status':
        if move_name in HARD_TRAP_MOVES:
            if apply_trap(defender):
                msg += f" 🛑 {defender['name'].capitalize()} can no longer escape!"
            else:
                msg += f" 👻 {defender['name'].capitalize()} slipped free - Ghosts cannot be held!"

        elif move_name == 'fairy-lock':
            # Binds the whole field for the following turn rather than targeting anyone,
            # so it is the one trap a Ghost cannot walk out of.
            for bound in (attacker, defender):
                bound.setdefault('volatile_statuses', {})['fairy_lock'] = FAIRY_LOCK_TURNS
            msg += " 🔒 No one will be able to run away next turn!"

        elif move_name == 'jaw-lock':
            # Binds them together - but only whoever can actually be bound
            apply_trap(attacker)
            apply_trap(defender)
            msg += " 🛑 Neither Pokémon can run away!"

        elif move_name == 'no-retreat':
            # The all-round boost comes with a catch: there is no backing out afterwards.
            attacker['volatile_statuses']['hard_trapped'] = True
            msg += f" 🛑 {attacker['name'].capitalize()} committed itself and can no longer retreat!"
            
        elif move_name == 'octolock':
            defender['volatile_statuses']['octolock'] = True
            defender['volatile_statuses']['hard_trapped'] = True
            msg += f" 🐙 {defender['name'].capitalize()} was locked in!"
            
        elif move_name == 'ingrain':
            attacker['volatile_statuses']['ingrain'] = True
            attacker['volatile_statuses']['hard_trapped'] = True
            msg += f" 🌱 {attacker['name'].capitalize()} planted its roots!"

    # ==========================================
    # HOOK 3: POST-STRIKE RETALIATION (Contact)
    # ==========================================
    # We use the 'physical' class as our proxy for kinetic contact moves
    if move.get('class') == 'physical' and damage > 0:
        atk_types = attacker.get('types') or []
        
        # 1. CONTACT STATUS (Static, Flame Body, Poison Point, Effect Spore)
        contact_trait = BIOLOGICAL_TRAITS.get('contact_status', {}).get(def_ability)
        if contact_trait and not attacker.get('status_condition'):
            # These abilities have a 30% trigger rate in the franchise ecosystem
            if random.randint(1, 100) <= 30:
                immune_type = contact_trait.get('immune')
                # Ensure the attacker isn't biologically immune to the pathogen!
                if immune_type not in atk_types:
                    attacker['status_condition'] = {'name': contact_trait['status'], 'duration': -1}
                    msg += f" {attacker['name'].capitalize()} was afflicted with {contact_trait['status']} by {defender['name'].capitalize()}'s {def_ability.replace('-', ' ').title()}!"


    # ==========================================
    # PHASE 3: STAT MODIFIERS
    # ==========================================
    # A localized dictionary to handle moves that alter multiple biological stats at once!
    COMPLEX_STAT_MOVES = {
        # --- Parting Shot drops BOTH offences before pivoting out. The database row only
        # carries the Attack half, so left to the generic path it would land half a move.
        'parting-shot': [('defender', 'attack', -1), ('defender', 'special-attack', -1)],

        # --- The Grand Boosters ---
        'quiver-dance': [('attacker', 'special-attack', 1), ('attacker', 'special-defense', 1), ('attacker', 'speed', 1)],
        'shell-smash': [('attacker', 'defense', -1), ('attacker', 'special-defense', -1), ('attacker', 'attack', 2), ('attacker', 'special-attack', 2), ('attacker', 'speed', 2)],
        'shift-gear': [('attacker', 'speed', 2), ('attacker', 'attack', 1)],
        'dragon-dance': [('attacker', 'attack', 1), ('attacker', 'speed', 1)],
        'bulk-up': [('attacker', 'attack', 1), ('attacker', 'defense', 1)],
        'calm-mind': [('attacker', 'special-attack', 1), ('attacker', 'special-defense', 1)],
        'cosmic-power': [('attacker', 'defense', 1), ('attacker', 'special-defense', 1)],
        'coil': [('attacker', 'attack', 1), ('attacker', 'defense', 1)],
        'geomancy': [('attacker', 'special-attack', 2), ('attacker', 'special-defense', 2), ('attacker', 'speed', 2)],
        'no-retreat': [('attacker', 'attack', 1), ('attacker', 'defense', 1), ('attacker', 'special-attack', 1), ('attacker', 'special-defense', 1), ('attacker', 'speed', 1)],
        
        # --- Kinetic Recoil (Self-Inflicted Drops) ---
        'close-combat': [('attacker', 'defense', -1), ('attacker', 'special-defense', -1)],
        'superpower': [('attacker', 'attack', -1), ('attacker', 'defense', -1)],
        'v-create': [('attacker', 'defense', -1), ('attacker', 'special-defense', -1), ('attacker', 'speed', -1)],
        'leaf-storm': [('attacker', 'special-attack', -2)],
        'draco-meteor': [('attacker', 'special-attack', -2)],
        'overheat': [('attacker', 'special-attack', -2)],
        'fleur-cannon': [('attacker', 'special-attack', -2)],
        'psycho-boost': [('attacker', 'special-attack', -2)],
        'make-it-rain': [('attacker', 'special-attack', -1)],
        'hammer-arm': [('attacker', 'speed', -1)],
        'ice-hammer': [('attacker', 'speed', -1)],
        'armor-cannon': [('attacker', 'defense', -1), ('attacker', 'special-defense', -1)],
        'dragon-ascent': [('attacker', 'defense', -1), ('attacker', 'special-defense', -1)],

        # --- Kinetic Self-Boosters---
        'flame-charge': [('attacker', 'speed', 1)],
        'trailblaze': [('attacker', 'speed', 1)],
        'power-up-punch': [('attacker', 'attack', 1)],
        'aqua-step': [('attacker', 'speed', 1)],
        'esper-wing': [('attacker', 'speed', 1)],
        'rapid-spin': [('attacker', 'speed', 1)]
    }
    # 1. Complex Stat Anomalies
    if move_name in COMPLEX_STAT_MOVES:
        # Kinetic stat drops (like Close Combat) only trigger if the attack actually lands!
        if move_class == 'status' or damage > 0:
            for target, s_name, s_change in COMPLEX_STAT_MOVES[move_name]:
                # 🚨 CONTRARY ABILITY INTERCEPTOR
                active_ability = atk_ability if target == 'attacker' else def_ability
                if active_ability == 'contrary':
                    s_change *= -1
                elif active_ability == 'simple':
                    s_change *= 2
                stat_changes.append((target, s_name, s_change))
                
    # 2. Standard Single-Stat Moves (From the database payload)
    # Skipped for charge-turn boosters: Meteor Beam and Electro Shot raise the user's
    # Sp. Atk while charging (handled by the engines' two-turn table), but their database
    # rows repeat that stat with target 'selected-pokemon', which would hand a second
    # boost to the OPPONENT when the attack finally lands.
    elif move_name not in CHARGE_BOOST_MOVES:
        stat_name = move.get('stat_name', 'none')
        stat_change = move.get('stat_change', 0)
        
        if stat_name not in ['none', None] and stat_change != 0:
            chance = move.get('stat_chance', 0)
            if chance == 0 and move_class == 'status':
                chance = 100
                
            # Ensures secondary stat drops from attacks (like Moonblast) only happen if damage > 0
            if random.randint(1, 100) <= chance and (move_class == 'status' or damage > 0):
                target = "attacker" if move.get('target') in ['user', 'attacker'] else "defender"
                
                # 🚨 CONTRARY ABILITY INTERCEPTOR
                active_ability = atk_ability if target == 'attacker' else def_ability
                if active_ability == 'contrary':
                    stat_change *= -1
                elif active_ability == 'simple':
                    stat_change *= 2

                stat_changes.append((target, stat_name, stat_change))

    # ==========================================
    # PHASE 3.5: KINETIC & ATMOSPHERIC ANOMALIES
    # ==========================================
    # 1. Chemical Scrubbers (Clear Smog & Haze)
    if move_name == 'clear-smog' and damage > 0:
        defender['stat_stages'] = {'attack': 0, 'defense': 0, 'sp_atk': 0, 'sp_def': 0, 'speed': 0}
        msg += f" 🌫️ {defender['name'].capitalize()}'s stat changes were neutralized by the smog!"
        
    elif move_name == 'haze':
        attacker['stat_stages'] = {'attack': 0, 'defense': 0, 'sp_atk': 0, 'sp_def': 0, 'speed': 0}
        defender['stat_stages'] = {'attack': 0, 'defense': 0, 'sp_atk': 0, 'sp_def': 0, 'speed': 0}
        msg += " 🌫️ All biological stat changes on the field were eliminated by the Haze!"

    # 2. Ecological Equipment Destruction (Knock Off)
    elif move_name == 'knock-off' and damage > 0:
        target_item_check = get_stored_item(defender)

        if is_transferable_item(target_item_check):
            defender['held_item'] = 'none'
            msg += f" 💥 {attacker['name'].capitalize()} knocked off {defender['name'].capitalize()}'s {target_item_check.replace('-', ' ').title()}!"

    # 3. Biological Theft (Thief / Covet)
    elif move_name in ['thief', 'covet'] and damage > 0:
        atk_item = get_stored_item(attacker)
        def_item = get_stored_item(defender)
        
        # Can only steal if the attacker's hands are empty and the defender's item is removable!
        if atk_item == 'none' and is_transferable_item(def_item):
            attacker['held_item'] = defender.get('held_item')
            defender['held_item'] = 'none'
            msg += f" 🥷 {attacker['name'].capitalize()} stole the target's {def_item.replace('-', ' ').title()}!"

    # 4. Thrown Equipment (Fling) - the item is gone whether or not it did anything
    elif move_name == 'fling' and damage > 0:
        thrown = get_stored_item(attacker)
        attacker['held_item'] = 'none'
        mark_item_consumed(attacker, thrown)
        msg += f" 🤾 {attacker['name'].capitalize()} flung its {pretty_item(thrown)}!"

        if is_berry(thrown):
            # A flung berry is eaten by whoever it hits
            eaten = apply_berry_effect(defender, thrown, ignore_threshold=True)
            if eaten:
                msg += " " + eaten.strip()
        elif thrown in FLING_AILMENTS:
            payload = FLING_AILMENTS[thrown]
            if payload == 'flinch':
                defender.setdefault('volatile_statuses', {})['flinch'] = True
                msg += f" {defender['name'].capitalize()} flinched!"
            elif not (defender.get('status_condition') or {}).get('name'):
                inflicted_status = payload

    # 5. Scorched Provisions (Incinerate) - burns the berry off the target
    elif move_name == 'incinerate' and damage > 0:
        target_item = get_stored_item(defender)
        if is_berry(target_item) and is_transferable_item(target_item):
            defender['held_item'] = 'none'
            mark_item_consumed(defender, target_item)
            msg += (f" 🔥 {defender['name'].capitalize()}'s {pretty_item(target_item)} "
                    f"was burnt to a crisp!")

    # 6. Stolen Provisions (Bug Bite / Pluck) - the ATTACKER gets the berry's effect
    elif move_name in BERRY_EATING_MOVES and damage > 0:
        target_item = get_stored_item(defender)
        if is_berry(target_item) and is_transferable_item(target_item):
            defender['held_item'] = 'none'
            mark_item_consumed(defender, target_item)
            snack = apply_berry_effect(attacker, target_item, ignore_threshold=True)
            msg += (f" 😋 {attacker['name'].capitalize()} ate "
                    f"{defender['name'].capitalize()}'s {pretty_item(target_item)}!")
            if snack:
                msg += " " + snack.strip()

    # ==========================================
    # PHASE 4: CELLULAR REGENERATION & KINETIC RECOIL
    # ==========================================
    drain_pct = move.get('drain', 0)
    
    # 1. Parasitic Healing (Giga Drain, Horn Leech)
    if drain_pct > 0:
        healing_amount += math.floor(damage * (drain_pct / 100.0))
        
    # 2. Kinetic Recoil (Double-Edge, Flare Blitz, Wild Charge)
    elif drain_pct < 0:
        # 🚨 ABILITY INTERCEPTOR: Rock Head & Magic Guard negate recoil!
        if atk_ability not in ['rock-head', 'magic-guard']:
            # Calculate the recoil based on the absolute value of the negative drain percentage
            recoil_dmg = max(1, math.floor(damage * (abs(drain_pct) / 100.0)))
            
            # Apply the damage directly to the attacker's simulated biology
            attacker['current_hp'] = max(0, attacker['current_hp'] - recoil_dmg)
            msg += f" 💥 {attacker['name'].capitalize()} was damaged by the recoil!"
            
    # 3. Max-HP Recoil Anomalies (Mind Blown, Steel Beam)
    if move_name in ['mind-blown', 'steel-beam', 'chloroblast']:
        if atk_ability != 'magic-guard':
            massive_recoil = max(1, math.floor(attacker.get('max_hp', 100) / 2))
            attacker['current_hp'] = max(0, attacker['current_hp'] - massive_recoil)
            msg += f" 💥 {attacker['name'].capitalize()} sacrificed half its max HP to unleash the attack!"

    # ==========================================
    # PHASE 5: BIOLOGICAL IMMUNITY FILTER
    # ==========================================
    def_types = defender.get('types') or []
    if inflicted_status == 'paralysis' and 'electric' in def_types:
        inflicted_status = None
        msg += f" {defender['name'].capitalize()}'s Electric typing makes it immune to paralysis!"
    elif inflicted_status == 'burn' and 'fire' in def_types:
        inflicted_status = None
        msg += f" {defender['name'].capitalize()}'s Fire typing makes it immune to burns!"
    elif inflicted_status == 'poison' and ('poison' in def_types or 'steel' in def_types):
        inflicted_status = None
        msg += f" {defender['name'].capitalize()}'s typing makes it immune to poison!"
    elif inflicted_status == 'freeze' and 'ice' in def_types:
        inflicted_status = None
        msg += f" {defender['name'].capitalize()}'s Ice typing makes it immune to freezing!"

    # Worry Seed's whole purpose is to staple this on, so the sleep lock it grants has to
    # actually hold. Vital Spirit is the same trait under a different name.
    if inflicted_status == 'sleep' and def_ability in ['insomnia', 'vital-spirit']:
        inflicted_status = None
        msg += (f" {defender['name'].capitalize()}'s {pretty_ability(def_ability)} "
                f"keeps it wide awake!")

    # ==========================================
    # PHASE 6: THERMODYNAMIC REACTIONS
    # ==========================================
    if move_type == 'fire':
        current_status = defender.get('status_condition')
        if current_status and current_status.get('name') == 'freeze':
            defender['status_condition'] = None
            msg += f" The intense heat of the attack thawed {defender['name'].capitalize()} out!"
    
    # ==========================================
    # HOOK 4: EXTREME KINETIC RELEASE (Self-KO)
    # ==========================================
    if move_name in ['explosion', 'self-destruct', 'memento', 'final-gambit']:
        attacker['current_hp'] = 0
        msg += f" {attacker['name'].capitalize()} sacrificed itself!"

    # 🚨 SPARKLY SWIRL: an attack that also scrubs the user's own party clean
    if move_name == 'sparkly-swirl' and damage > 0:
        swirled = cure_party_status(user_party, attacker)
        if swirled:
            msg += f" 🌸 The swirl cleansed {', '.join(swirled)}!"

    # 🚨 FAKE OUT: the flinch is the whole point, so it is certain rather than a roll
    if move_name == 'fake-out' and damage > 0:
        defender.setdefault('volatile_statuses', {})['flinch'] = True
        msg += f" {defender['name'].capitalize()} flinched!"

    # 🚨 G-MAX SIGNATURE EFFECTS
    # Most of the roster rides on the ordinary payload; these are the ones whose
    # signature is a mechanic, so they fire here once the strike has actually landed.
    if move.get('name') in GMAX_EFFECTS and (damage > 0 or move_class == 'status'):
        msg += apply_gmax_effect(
            move['name'], attacker, defender,
            user_party=user_party, user_hazards=user_hazards,
            target_hazards=target_hazards, held_item=attacker_item)

    # 🚨 EERIE SPELL: saps the move the target last reached for
    if move_name == 'eerie-spell' and damage > 0:
        sapped = defender.get('last_move_used')
        taken = drain_move_pp(defender, sapped, 3) if sapped else 0
        if taken:
            msg += (f" 🔮 {defender['name'].capitalize()}'s "
                    f"{sapped.replace('-', ' ').title()} lost {taken} PP!")

    # 🚨 CORE ENFORCER: only bites if the target has already taken its turn. Moving second
    # is the price of the suppression, so a slower Core Enforcer is the one that lands it.
    if move_name == 'core-enforcer' and damage > 0 and defender.get('acted_this_turn'):
        worked, detail = suppress_ability(defender)
        if worked:
            msg += (f" 🧬 {defender['name'].capitalize()}'s {pretty_ability(detail)} "
                    f"was shut down by the Core Enforcer!")

    # 🚨 BURN UP / DOUBLE SHOCK: the element is spent powering the attack
    if move_name in TYPE_SHEDDING_MOVES and damage > 0:
        spent = TYPE_SHEDDING_MOVES[move_name]
        remaining = [t for t in (attacker.get('types') or []) if t != spent]
        # A mono-type user is left typeless rather than reverting to its old element
        attacker['types'] = remaining
        msg += f" 🔥 {attacker['name'].capitalize()} burned out its {spent.title()} typing!"

    # ==========================================
    # PHASE 7: HYBRID ENVIRONMENTAL POLLUTION
    # ==========================================
    if target_hazards is not None:
        if move_name == 'stealth-rock' or move_name.startswith('stone-axe') or move.get('name') == 'G-Max Stonesurge':
            if not target_hazards.get('stealth-rock'):
                target_hazards['stealth-rock'] = True
                msg += " 🪨 Pointed stones float in the air around the target!"
                
        # --- NEW: METALLIC PARTICULATES ---
        elif move_name == 'G-Max Steelsurge':
            if not target_hazards.get('steelsurge'):
                target_hazards['steelsurge'] = True
                msg += " ⚙️ Sharp spikes of steel were scattered around the target's feet!"
                
        elif move_name == 'spikes' or move_name.startswith('ceaseless-edge'):
            if target_hazards.get('spikes', 0) < 3:
                target_hazards['spikes'] = target_hazards.get('spikes', 0) + 1
                msg += " 🗡️ Spikes were scattered around the target's feet!"
                
        elif move_name == 'toxic-spikes':
            if target_hazards.get('toxic-spikes', 0) < 2:
                target_hazards['toxic-spikes'] = target_hazards.get('toxic-spikes', 0) + 1
                msg += " 🧪 Poison spikes were scattered around the target's feet!"
                
        elif move_name == 'sticky-web':
            if not target_hazards.get('sticky-web'):
                target_hazards['sticky-web'] = True
                msg += " 🕸️ A sticky web was woven around the target's feet!"

        # --- NEW: ECOLOGICAL DISASTERS (4-Turn Habitats) ---
        disaster_types = ['wildfire', 'vine lash', 'cannonade', 'volcalith']
        if status_type in disaster_types:
            # We store the integer '4' to act as a countdown timer for the habitat!
            target_hazards[status_type] = 4 
            
            msg_map = {
                'wildfire': "🔥 The habitat was engulfed in an uncontrolled brush fire!",
                'vine lash': "🌿 Invasive vines aggressively ensnared the opponent's side!",
                'cannonade': "🌊 A violent vortex of water surrounds the opponent's field!",
                'volcalith': "🪨 Floating rocks began showering the opponent's habitat!"
            }
            msg += msg_map[status_type]

    # --- 5. HAZARD CLEARING (Rapid Spin, Mortal Spin, Tidy Up) ---
    if move_name in ['rapid-spin', 'mortal-spin', 'tidy-up'] and user_hazards is not None:
        cleared_any = False
        for h in ['stealth-rock', 'sticky-web']:
            if user_hazards.get(h):
                user_hazards[h] = False
                cleared_any = True
        for h in ['spikes', 'toxic-spikes']:
            if user_hazards.get(h, 0) > 0:
                user_hazards[h] = 0
                cleared_any = True
                
        if cleared_any:
            msg += " 🧹 The hazard debris was blown away from the attacker's side!"

    # --- 6. FULL FIELD CLEARING (Defog) ---
    if move_name == 'defog':
        cleared_any = False
        # Defog blows away hazards on BOTH sides of the field!
        for field in filter(None, [user_hazards, target_hazards]):
            for h in ['stealth-rock', 'sticky-web']:
                if field.get(h):
                    field[h] = False
                    cleared_any = True
            for h in ['spikes', 'toxic-spikes']:
                if field.get(h, 0) > 0:
                    field[h] = 0
                    cleared_any = True
                    
        if cleared_any:
            msg += " 🌬️ A strong wind blew away the environmental hazards from the entire field!"

    # ==========================================
    # DYNAMAX PIERCING DAMPENER
    # ==========================================
    if defender.get('volatile_statuses', {}).get('protected') and is_max_move:
        damage = math.floor(damage * 0.25)
        msg += f" 🛡️ **{defender['name'].capitalize()}** couldn't fully protect itself from the Max Move!"

    # ==========================================
    # 🚨 THE SURVIVAL INTERCEPTOR (Focus Sash & Sturdy)
    # This acts as the absolute final filter before damage is returned!
    # ==========================================
    if damage >= defender['current_hp']:
        def_item = get_active_item(defender, magic_room)
        def_ability = get_active_ability(defender)
        
        # 1. Focus Sash
        if def_item == 'focus-sash' and defender['current_hp'] == defender.get('max_hp', 100):
            # Cap the damage so it leaves exactly 1 HP!
            damage = defender['current_hp'] - 1
            defender['held_item'] = 'none' # The item disintegrates!
            mark_item_consumed(defender, def_item)
            msg += " It hung on using its Focus Sash!"
            
        # 2. Sturdy Ability
        elif def_ability == 'sturdy' and defender['current_hp'] == defender.get('max_hp', 100):
            damage = defender['current_hp'] - 1
            msg += " It endured the hit using Sturdy!"
            
        # 3. Endure Status (If you add the move 'Endure' later!)
        elif defender.get('volatile_statuses', {}).get('endure'):
            damage = defender['current_hp'] - 1
            msg += " It endured the hit!"

    # ==========================================
    # 🚨 BIOLOGICAL CLEANSERS (Wake-Up Slap & Smelling Salts)
    # ==========================================
    if damage > 0:
        if move_name == 'wake-up-slap' and defender.get('status_condition', {}).get('name') == 'sleep':
            defender['status_condition'] = None
            msg += f" The sheer force of the slap jolted {defender['name'].capitalize()} awake!"
            
        elif move_name == 'smelling-salts' and defender.get('status_condition', {}).get('name') == 'paralysis':
            defender['status_condition'] = None
            msg += f" {defender['name'].capitalize()}'s paralysis was completely cured by the shock!"

    # ==========================================
    # 🪆 SUBSTITUTE INTERCEPTOR
    # ==========================================
    # Sits at the very end so it sees the final damage, status and stat payload together.
    # A decoy eats all three: the specimen behind it takes nothing, catches nothing, and
    # keeps its stat stages. Anything aimed at the ATTACKER (recoil, self-boosts, drain)
    # is deliberately left alone.
    # ==========================================
    # 🛡️ SIDE GUARDS
    # ==========================================
    # Safeguard turns status away from the whole side; Mist holds its stats in place.
    # Neither touches anything the ATTACKER is doing to itself.
    if inflicted_status and side_is_guarded(target_hazards, 'safeguard'):
        inflicted_status = None
        msg += f" 🛡️ {defender['name'].capitalize()}'s Safeguard turned the status away!"

    if side_is_guarded(target_hazards, 'mist'):
        blocked = [c for c in stat_changes if c[0] == 'defender' and c[2] < 0]
        if blocked:
            stat_changes = [c for c in stat_changes if c not in blocked]
            msg += f" 🌫️ The mist stopped {defender['name'].capitalize()} losing any stats!"

    if substitute_intercepts(defender, move, attacker):
        if damage > 0:
            damage, sub_note = absorb_with_substitute(defender, damage)
            msg += sub_note
        elif move_class == 'status' and 'selected-pokemon' in str(move.get('target', '')):
            return 0, "But it failed! The substitute took it instead!", 'none', [], healing_amount

        inflicted_status = None
        stat_changes = [c for c in stat_changes if c[0] != 'defender']

    return damage, msg.strip(), inflicted_status, stat_changes, healing_amount

async def fetch_base_stats(db, pokedex_id):
    """Pulls the 6 base stats for a specific species from the database."""
    async with db.execute("SELECT stat_name, base_value FROM base_pokemon_stats WHERE pokedex_id = ?", (pokedex_id,)) as cursor:
        rows = await cursor.fetchall()
    
    # Map the API names to our standard dictionary keys
    stat_map = {
        'hp': 'hp', 'attack': 'attack', 'defense': 'defense', 
        'special-attack': 'sp_atk', 'special-defense': 'sp_def', 'speed': 'speed', 'evasion': 'evasion', 'accuracy': 'accuracy'
    }
    
    base_stats = {}
    for api_name, value in rows:
        if api_name in stat_map:
            base_stats[stat_map[api_name]] = value
            
    return base_stats

def get_xp_requirement(level, growth_rate):
    """Calculates the total XP required to reach a specific level based on biology."""
    # We calculate the XP needed for the NEXT level
    L = level + 1 
    
    if growth_rate == 'fast':
        return int((4 * (L**3)) / 5)
    elif growth_rate == 'medium-slow':
        return int((6 * (L**3)) / 5 - 15 * (L**2) + 100 * L - 140)
    elif growth_rate == 'slow':
        return int((5 * (L**3)) / 4)
    else: 
        # Default to medium-fast if undefined or erratic/fluctuating (to keep math clean)
        return int(L**3)


def generate_biometrics() -> tuple[float, float, str]:
    """
    Rolls for biological size and weight variance based on standard ecological distribution.
    Returns (height_multiplier, weight_multiplier, size_classification).
    """
    roll = random.randint(1, 100)
    
    if roll <= 2:
        # 2% Chance: Teeny Anomaly (70% - 80% scale)
        h_mult = round(random.uniform(0.70, 0.80), 2)
        w_mult = round(random.uniform(0.50, 0.65), 2) # Weight scales exponentially
        classification = "Teeny"
        
    elif roll <= 12:
        # 10% Chance: Small Specimen (81% - 95% scale)
        h_mult = round(random.uniform(0.81, 0.95), 2)
        w_mult = round(random.uniform(0.66, 0.85), 2)
        classification = "Small"
        
    elif roll <= 88:
        # 76% Chance: Average Specimen (96% - 105% scale)
        h_mult = round(random.uniform(0.96, 1.05), 2)
        w_mult = round(random.uniform(0.86, 1.15), 2)
        classification = "Average"
        
    elif roll <= 98:
        # 10% Chance: Large Specimen (106% - 120% scale)
        h_mult = round(random.uniform(1.06, 1.20), 2)
        w_mult = round(random.uniform(1.16, 1.45), 2)
        classification = "Large"
        
    else:
        # 2% Chance: ALPHA PREDATOR (130% - 160% scale)
        h_mult = round(random.uniform(1.30, 1.60), 2)
        w_mult = round(random.uniform(1.80, 2.50), 2) # Massive weight increase
        classification = "Alpha"
        
    return h_mult, w_mult, classification

def get_planetary_cycle():
    """Calculates the current circadian rhythm and lunar phase."""
    now = datetime.now(timezone.utc)
    hour = now.hour
    
    # 1. Determine the Solar Cycle (Time of Day)
    if 6 <= hour < 17:
        solar_cycle = "day"
    elif 17 <= hour < 18:
        solar_cycle = "dusk" # A narrow 1-hour window for crepuscular species!
    else:
        solar_cycle = "night"
        
    # 2. Determine the Lunar Cycle
    # The toordinal() function returns the number of days since Jan 1, 1 AD.
    # Modulo 29 creates a consistent 29-day repeating cycle. Day 15 is the Full Moon!
    days_since_epoch = now.toordinal()
    lunar_phase_day = days_since_epoch % 29
    
    is_full_moon = (lunar_phase_day == 15)
    
    # If it's night AND a full moon, the full-moon condition overrides standard night
    if solar_cycle == "night" and is_full_moon:
        return "full-moon"
        
    return solar_cycle