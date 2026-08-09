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
    ability = (specimen.get('ability') or 'none').lower().replace(' ', '-')
    
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

def check_consumables(pokemon, owner_str):
    """Monitors biological thresholds and dynamically consumes items based on the JSON database."""
    log = ""
    if pokemon['current_hp'] <= 0:
        return log
        
    held_item = (pokemon.get('held_item') or "").lower().replace(' ', '-')
    
    # 🚨 Check the global dictionary!
    if held_item not in CONSUMABLE_DATABASE:
        return log
        
    item_data = CONSUMABLE_DATABASE[held_item]
    behavior = item_data.get('type')
    max_hp = pokemon.get('max_hp', 100)
    current_hp = pokemon['current_hp']
    hp_pct = current_hp / max_hp
    
    # 1. FLAT HEALING (e.g., Oran Berry)
    if behavior == 'heal_flat' and hp_pct <= item_data.get('threshold', 0.5):
        heal_amt = item_data.get('value', 10)
        pokemon['current_hp'] = min(max_hp, current_hp + heal_amt)
        pokemon['held_item'] = 'none'
        log += f"{item_data.get('icon', '🫐')} {owner_str.strip()} **{pokemon['name'].capitalize()}** consumed its {held_item.replace('-', ' ').title()}! (+{heal_amt} HP)\n"
        
    # 2. PERCENTAGE HEALING (e.g., Sitrus Berry)
    elif behavior == 'heal_pct' and hp_pct <= item_data.get('threshold', 0.5):
        heal_amt = max(1, math.floor(max_hp * item_data.get('value', 0.25)))
        pokemon['current_hp'] = min(max_hp, current_hp + heal_amt)
        pokemon['held_item'] = 'none'
        log += f"{item_data.get('icon', '🍋')} {owner_str.strip()} **{pokemon['name'].capitalize()}** consumed its {held_item.replace('-', ' ').title()}! (+{heal_amt} HP)\n"
        
    # 3. STATUS CURES (e.g., Lum, Pecha)
    elif behavior == 'cure_status' and pokemon.get('status_condition'):
        status_name = pokemon['status_condition']['name']
        if item_data.get('target') == 'all' or item_data.get('target') == status_name:
            pokemon['status_condition'] = None
            pokemon['held_item'] = 'none'
            log += f"{item_data.get('icon', '🌿')} {owner_str.strip()} **{pokemon['name'].capitalize()}** consumed its {held_item.replace('-', ' ').title()} and cured its {status_name}!\n"

    # 4. PINCH STAT BOOSTERS (e.g., Liechi, Salac)
    elif behavior == 'stat_boost' and hp_pct <= item_data.get('threshold', 0.25):
        stat_target = item_data.get('stat', 'attack')
        boost_val = item_data.get('value', 1)
        
        if 'stat_stages' not in pokemon:
            pokemon['stat_stages'] = {'attack': 0, 'defense': 0, 'sp_atk': 0, 'sp_def': 0, 'speed': 0}
            
        current_stage = pokemon['stat_stages'].get(stat_target, 0)
        
        if current_stage < 6:
            pokemon['stat_stages'][stat_target] = min(6, current_stage + boost_val)
            pokemon['held_item'] = 'none'
            log += f"{item_data.get('icon', '🔴')} {owner_str.strip()} **{pokemon['name'].capitalize()}** consumed its {held_item.replace('-', ' ').title()}! Its {stat_target.replace('_', ' ').title()} rose!\n"

    return log

def is_grounded(pokemon, gravity_active=False):
    """Evaluates if a specimen is physically touching the battlefield."""
    if gravity_active: return True # 🚨 Gravity grounds everything!
    types = pokemon.get('types', [])
    ability = (pokemon.get('ability') or '').lower().replace(' ', '-')
    item = (pokemon.get('held_item') or '').lower().replace(' ', '-')
    
    if 'flying' in types: return False
    if ability == 'levitate': return False
    if item == 'air-balloon': return False
    # (Note: Magnet Rise or Telekinesis could be added here by checking volatile_statuses!)
    
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

def resolve_dynamic_power(move_name, attacker, defender):
    """
    Single entry point for every move whose base power is computed rather than stored.
    Returns None for ordinary moves so callers can fall back to the database value.
    """
    scaled = get_hp_scaled_power(move_name, attacker, defender)
    if scaled is not None:
        return scaled

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
        'ability': (attacker.get('ability') or 'none'),
        # Two full turns must pass, so the tick on the turn it was queued is skipped
        'turns': 2,
        'just_queued': True,
    }

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

def resolve_combat_stats(move_name, move_class, attacker, defender, wonder_room=False):
    """
    Decides which Attack and Defense stats the damage formula reads, applies stat stages,
    Wonder Room and Assault Vest, and reports the category the move resolves as.

    Returns (attack_stat, defense_stat, effective_class). The returned class drives the
    burn penalty and screen selection, so a Photon Geyser that resolves physical is
    halved by a burn and blocked by Reflect rather than Light Screen.
    """
    a_stages = attacker.get('stat_stages') or {}
    d_stages = defender.get('stat_stages') or {}

    phys_atk = apply_stat_stage(attacker.get('stats', {}).get('attack', 50), a_stages.get('attack', 0))
    spec_atk = apply_stat_stage(attacker.get('stats', {}).get('sp_atk', 50), a_stages.get('sp_atk', 0))
    phys_def = apply_stat_stage(defender.get('stats', {}).get('defense', 50), d_stages.get('defense', 0))
    spec_def = apply_stat_stage(defender.get('stats', {}).get('sp_def', 50), d_stages.get('sp_def', 0))

    # Assault Vest reinforces the Sp. Def stat itself, so it follows that stat rather than
    # the move - a Psyshock aimed at physical Defense correctly ignores the vest.
    if (defender.get('held_item') or "").lower().replace(' ', '-') == 'assault-vest':
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
    power = resolve_dynamic_power(move_name, attacker, defender)
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
        atk_ability = (attacker.get('ability') or '').lower().replace(' ', '-')
        def_ability = (defender.get('ability') or '').lower().replace(' ', '-')

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

def apply_survival_floor(defender, damage):
    """
    Focus Sash, Sturdy, and Endure clamp any otherwise-lethal hit so the specimen
    survives on exactly 1 HP. Returns (final_damage, message_fragment).
    """
    if damage < defender.get('current_hp', 0):
        return damage, ""

    def_item = (defender.get('held_item') or "").lower().replace(' ', '-')
    def_ability = (defender.get('ability') or "").lower().replace(' ', '-')
    at_full_health = defender['current_hp'] == defender.get('max_hp', 100)

    if def_item == 'focus-sash' and at_full_health:
        defender['held_item'] = 'none' # The sash disintegrates on use!
        return defender['current_hp'] - 1, " It hung on using its Focus Sash!"

    if def_ability == 'sturdy' and at_full_health:
        return defender['current_hp'] - 1, " It endured the hit using Sturdy!"

    if defender.get('volatile_statuses', {}).get('endure'):
        return defender['current_hp'] - 1, " It endured the hit!"

    return damage, ""

def calculate_damage(attacker, defender, move, weather='none', terrain='none', target_hazards=None, user_hazards=None, wonder_room=False, gravity=False):
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

    attacker_item = (attacker.get('held_item') or "").lower().replace(' ', '-')
    defender_item = (defender.get('held_item') or "").lower().replace(' ', '-')
    
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
    PROTECT_MOVES = ['protect', 'detect', 'spiky-shield', 'king-shield', 'baneful-bunker', 'obstruct', 'silky-trap', 'burning-bulwark', 'max-guard']
    
    if move_name in PROTECT_MOVES:
        counter = attacker['volatile_statuses'].get('protect_counter', 0)
        success_chance = 100 / (3 ** counter) # 100%, 33%, 11%, 3%...
        
        if random.uniform(0, 100) <= success_chance:
            attacker['volatile_statuses']['protected'] = True
            attacker['volatile_statuses']['protect_counter'] = counter + 1
            return 0, f"🛡️ **{attacker['name'].capitalize()}** protected itself!", None, [], 0
        else:
            attacker['volatile_statuses']['protected'] = False
            attacker['volatile_statuses']['protect_counter'] = 0
            return 0, f"🛡️ **{attacker['name'].capitalize()}** tried to protect itself, but the barrier failed!", None, [], 0
    else:
        # Using any other move resets the exhaustion counter
        attacker['volatile_statuses']['protect_counter'] = 0

    # ==========================================
    # 🚨 BARRIER DEPLOYMENT (Screens)
    # ==========================================
    if move_name in ['reflect', 'light-screen', 'aurora-veil'] and user_hazards is not None:
        duration = 8 if attacker_item == 'light-clay' else 5
        
        if move_name == 'aurora-veil' and weather not in ['hail', 'snow']:
            return 0, "But it failed! Aurora Veil requires Hail or Snow!", 'none', [], 0
            
        if user_hazards.get(move_name, 0) > 0:
            return 0, "But it failed! The barrier is already active!", 'none', [], 0
            
        user_hazards[move_name] = duration
        
        if move_name == 'reflect': msg += f" 🧱 A wondrous wall of light appeared to protect {attacker['name'].capitalize()}'s team!"
        elif move_name == 'light-screen': msg += f" 🪞 A wondrous wall of light appeared to protect {attacker['name'].capitalize()}'s team!"
        elif move_name == 'aurora-veil': msg += f" 🌌 An aurora appeared to protect {attacker['name'].capitalize()}'s team!"
            
        return 0, msg.strip(), 'none', [], 0

    # ==========================================
    # 2. CONTAINMENT FIELD COLLISION
    # ==========================================
    if defender['volatile_statuses'].get('protected') and 'user' not in move_target:
        BYPASS_MOVES = ['feint', 'phantom-force', 'shadow-force', 'hyperspace-fury', 'hyperspace-hole']
        
        if move_name in BYPASS_MOVES:
            defender['volatile_statuses']['protected'] = False
            msg += f"💥 **{attacker['name'].capitalize()}** broke through the protection! "
        elif is_max_move and move_class != 'status':
            pass # Max Moves pierce the shield! Damage quartered at the end of this function.
        else:
            if move_name in ['jump-kick', 'high-jump-kick']:
                crash_dmg = max(1, math.floor(attacker.get('max_hp', 100) / 2))
                attacker['current_hp'] = max(0, attacker['current_hp'] - crash_dmg)
                return 0, f"**{attacker['name'].capitalize()} kept going and crashed!", None, [], 0
            
            return 0, f"🛡️ **{defender['name'].capitalize()}** protected itself from the attack!", None, [], 0

    # Safely catch SQLite NULL values before running string methods!
    atk_ability = (attacker.get('ability') or 'none').lower().replace(' ', '-')
    def_ability = (defender.get('ability') or 'none').lower().replace(' ', '-')

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

    if move_name in ['jump-kick', 'high-jump-kick']:
        crash_dmg = max(1, math.floor(attacker.get('max_hp', 100) / 2))
        attacker['current_hp'] = max(0, attacker['current_hp'] - crash_dmg)
        return 0, f"{attacker['name'].capitalize()} kept going and crashed!", None, [], 0
    
    if move.get('class') != 'status':
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
        fixed_damage, survival_msg = apply_survival_floor(defender, attacker.get('level', 50))
        return fixed_damage, survival_msg.strip(), 'none', [], 0

    if move_name in ['super-fang', 'natures-madness', 'ruination']:
        # These moves instantly halve the defender's current HP!
        fixed_damage = max(1, math.floor(defender['current_hp'] / 2))
        fixed_damage, survival_msg = apply_survival_floor(defender, fixed_damage)
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

        fixed_damage, survival_msg = apply_survival_floor(defender, fixed_damage)

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
        lethal_damage, survival_msg = apply_survival_floor(defender, defender['current_hp'])

        if survival_msg:
            return lethal_damage, survival_msg.strip(), 'none', [], 0

        return lethal_damage, "It's a One-Hit KO!", 'none', [], 0
    
    # PHASE 1: KINETIC & SPECIAL DAMAGE (The Multi-Strike Engine)
    # ==========================================
    # Resolved before the gate below: Flail, Gyro Ball, Grass Knot, Punishment and
    # friends are all stored as 0 power in the database, so without this they'd be
    # filtered out as non-damaging and silently deal nothing.
    dynamic_power = resolve_dynamic_power(move_name, attacker, defender)

    if move.get('class') != 'status' and (move.get('power', 0) > 0 or dynamic_power):
        level = attacker.get('level', 50)
        
        # ==========================================
        # 🚨 STAT SELECTION
        # ==========================================
        # One resolver decides which Attack and Defense stats this move reads, applying
        # stat stages, Wonder Room and Assault Vest. `effective_class` is what the move
        # actually resolved as, which can differ from its stored category for Photon
        # Geyser and Shell Side Arm.
        a, d, effective_class = resolve_combat_stats(move_name, move_class, attacker, defender, wonder_room)

        # Choice items reinforce the offensive stat the move ended up swinging with
        if effective_class == 'physical':
            if attacker_item == 'choice-band': a = math.floor(a * 1.5)
        else:
            if attacker_item == 'choice-specs': a = math.floor(a * 1.5)


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
        is_removable = defender_item not in ['none', 'red-orb', 'blue-orb'] and not defender_item.endswith('ite') and not defender_item.endswith('ium-z')
        
        if move_name == 'knock-off' and is_removable:
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
            
            # The Merciless Ability: Total immunity to critical hits!
            if def_ability in ['battle-armor', 'shell-armor']:
                is_crit = False
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
            if is_crit: hit_damage = math.floor(hit_damage * 1.5)
            
            # --- D. DEFENSIVE RESIST BERRIES (Only triggers on the VERY FIRST strike) ---
            if strike == 0 and defender_item in berry_resist_map:
                protected_type = berry_resist_map[defender_item]
                if move_type == protected_type and (type_multiplier > 1.0 or protected_type == 'normal'):
                    hit_damage = math.floor(hit_damage * 0.5)
                    defender['held_item'] = 'none'
                    defender_item = 'none' 
                    msg += f" 🛡️ {defender['name'].capitalize()}'s {protected_type.title()}-Resistance Berry weakened the damage! "
                    
            total_damage += hit_damage
            simulated_hp -= hit_damage
                    
            # --- F. PHYSICAL RECOIL (Rocky Helmet & Rough Skin) ---
            if move.get('class') == 'physical':
                if defender_item == 'rocky-helmet':
                    healing_amount -= max(1, math.floor(attacker.get('max_hp', 100) / 6))
                    msg += f" 💥 {attacker['name'].capitalize()} was hurt by the Rocky Helmet!"
                if def_ability in BIOLOGICAL_TRAITS.get('contact_damage', []):
                    healing_amount -= max(1, math.floor(attacker.get('max_hp', 100) / 8))
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
        if move_name in ['anchor-shot', 'spirit-shackle', 'block', 'mean-look', 'spider-web']:
            defender['volatile_statuses']['hard_trapped'] = True
            msg += f" 🛑 {defender['name'].capitalize()} can no longer escape!"
            
        elif move_name == 'jaw-lock':
            attacker['volatile_statuses']['hard_trapped'] = True
            defender['volatile_statuses']['hard_trapped'] = True
            msg += " 🛑 Neither Pokémon can run away!"
            
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
        target_item_check = (defender.get('held_item') or "").lower().replace(' ', '-')
        is_removable = target_item_check not in ['none', 'red-orb', 'blue-orb', None] and not target_item_check.endswith('ite') and not target_item_check.endswith('ium-z')
        
        if is_removable:
            defender['held_item'] = 'none'
            msg += f" 💥 {attacker['name'].capitalize()} knocked off {defender['name'].capitalize()}'s {target_item_check.replace('-', ' ').title()}!"

    # 3. Biological Theft (Thief / Covet)
    elif move_name in ['thief', 'covet'] and damage > 0:
        atk_item = (attacker.get('held_item') or "none").lower()
        def_item = (defender.get('held_item') or "none").lower()
        
        # Can only steal if the attacker's hands are empty and the defender's item is removable!
        if atk_item == 'none' and def_item not in ['none', 'red-orb', 'blue-orb'] and not def_item.endswith('ite') and not def_item.endswith('ium-z'):
            attacker['held_item'] = defender.get('held_item')
            defender['held_item'] = 'none'
            msg += f" 🥷 {attacker['name'].capitalize()} stole the target's {def_item.replace('-', ' ').title()}!"

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
        def_item = (defender.get('held_item') or "").lower().replace(' ', '-')
        def_ability = (defender.get('ability') or "").lower().replace(' ', '-')
        
        # 1. Focus Sash
        if def_item == 'focus-sash' and defender['current_hp'] == defender.get('max_hp', 100):
            # Cap the damage so it leaves exactly 1 HP!
            damage = defender['current_hp'] - 1
            defender['held_item'] = 'none' # The item disintegrates!
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