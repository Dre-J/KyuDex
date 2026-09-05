import math
import random
from utils.constants import TYPE_CHART, NATURE_MULTIPLIERS, nature_multiplier, BIOLOGICAL_TRAITS, CONSUMABLE_DATABASE, MULTI_STRIKE_MOVES, STATUS_IMMUNE_ABILITIES, ALL_STATUSES, WEIGHT_MULTIPLIER_ABILITIES, ACCURACY_MULTIPLIER_ABILITIES, EVASION_MULTIPLIER_ABILITIES, WONDER_SKIN_ACCURACY, CRIT_STAGE_ABILITIES, VOLATILE_IMMUNE_ABILITIES, BULLET_MOVES, POWDER_MOVES, EXPLOSIVE_MOVES, MOVE_FAMILY_IMMUNE_ABILITIES, STATUS_MOVE_IMMUNE_ABILITIES, MAGIC_BOUNCE_ABILITIES, EXPLOSION_BLOCKING_ABILITIES, PRIORITY_BLOCKING_ABILITIES, QUICK_DRAW_CHANCE, LAST_IN_BRACKET_ABILITIES, GALE_WINGS_REQUIRES_FULL_HP, TRIAGE_PRIORITY, DANCE_MOVES, TYPE_REWRITE_ABILITIES, PROTEAN_ABILITIES, MIMICRY_TYPES, GHOST_PIERCING_ABILITIES, EVASION_IGNORING_ABILITIES, NO_CONTACT_ABILITIES, PROTECT_PIERCING_ABILITIES, CORROSIVE_ABILITIES, SECONDARY_CHANCE_ABILITIES, SECONDARY_IMMUNE_ABILITIES, FLINCH_ON_HIT_ABILITIES, PARENTAL_BOND_SECOND_HIT, TOXIC_CHAIN_CHANCE, POISON_CONFUSION_ABILITIES, ADAPTABILITY_STAB, ALL_STATS, STAT_DROP_IMMUNE_ABILITIES, STAT_DROP_IMMUNE_TYPE_GATE, STAT_DROP_REFLECTING_ABILITIES, STAT_DROP_RETALIATION_ABILITIES, INTIMIDATE_IMMUNE_ABILITIES, STAT_STAGE_KEYS, HAZARD_SOURCE, AURA_ABILITIES, AURA_MULTIPLIER, AURA_BREAK_ABILITIES, AURA_BREAK_MULTIPLIER, TERA_SHELL_ABILITIES, TERA_SHELL_MULTIPLIER, RUIN_ABILITIES, RUIN_MULTIPLIER, BERRY_BLOCKING_ABILITIES, PARADOX_ABILITIES, PARADOX_BOOST, PARADOX_SPEED_BOOST, PARADOX_STAT_ORDER, BOOSTER_SPENT_MARKER, CRIT_DAMAGE_MULTIPLIER, CRIT_MULTIPLIER_ABILITIES, PRANKSTER_ABILITIES, PRANKSTER_PRIORITY, PRANKSTER_BLOCKED_BY, SLICING_MOVES, SWITCH_OUT_HEAL_FRACTION, SWITCH_OUT_CURE_ABILITIES, TRAPPING_ABILITIES, FORCED_SWITCH_IMMUNE_ABILITIES, INTIMIDATE_REVERSING_ABILITIES, BAIL_OUT_ABILITIES, BAIL_OUT_THRESHOLD, BAIL_OUT_MARKER, ON_HIT_REACTIONS, CHARGE_VOLATILE, CHARGE_MULTIPLIER, WIND_MOVES, WIND_IMMUNE_ABILITIES, WIND_RIDER_BOOST, HP_FORM_FLIPS, BROKEN_BY_A_HIT, STANCE_CHANGE_ABILITIES, STANCE_BLADE, STANCE_SHIELD, STANCE_SHIELD_MOVES, HUNGER_SWITCH_ABILITIES, HUNGER_PAIRS, ZERO_TO_HERO_ABILITIES, ZERO_TO_HERO_PAIRS, ZERO_TO_HERO_MARKER, GULP_MISSILE_ABILITIES, GULP_TRIGGER_MOVES, GULP_BASE_FORM, GULP_HEALTHY_FORM, GULP_HURT_FORM, GULP_HURT_THRESHOLD, GULP_RECOIL_FRACTION, GULP_PAYLOADS, FORM_FLIP_REQUEST, HP_THRESHOLD_REACTIONS, HP_THRESHOLD, HP_THRESHOLD_MARKER, FLINCH_REACTIONS, ABILITY_PAINT_ON_CONTACT, ABILITY_SWAP_ON_CONTACT, ITEM_THIEF_ON_CONTACT, ITEM_THIEF_ON_ATTACK, RETALIATORY_BURN_ABILITIES, SYNCHRONIZE_ABILITIES, SYNCHRONIZE_STATUSES, CURSED_BODY_ABILITIES, CURSED_BODY_CHANCE, CURSED_BODY_TURNS, PERISH_BODY_ABILITIES, PERISH_BODY_COUNT, LIQUID_OOZE_ABILITIES, SYNCHRONIZE_ABILITIES, AFTERMATH_ABILITIES, AFTERMATH_FRACTION, INNARDS_OUT_ABILITIES, TARGET_ATTACKER, TARGET_ATTACKER_FROM_FOE, TARGET_DEFENDER_SELF, TARGET_FIELD, LEVITATION_ABILITIES, KNOCKOUT_BOOST_ABILITIES, KNOCKOUT_BEST_STAT, KNOCKOUT_BOOST_STAGES, STAGE_NAME_FOR_STAT, MOURNING_ABILITIES, MOURNING_STAGES, MOURNED_MARKER, OPPORTUNIST_ABILITIES, SUPREME_OVERLORD_ABILITIES, SUPREME_OVERLORD_PER_FALLEN, SUPREME_OVERLORD_MAX_FALLEN, SUPREME_OVERLORD_STATS, WEATHER_FORM_ABILITIES, WEATHER_FORMS, TRUANT_ABILITIES, TRUANT_MARKER, COMATOSE_ABILITIES, CLUMSY_ABILITIES, STICKY_HOLD_ABILITIES, GLUTTONY_ABILITIES, GLUTTONY_THRESHOLD, RIPEN_ABILITIES, RIPEN_MULTIPLIER, CHEEK_POUCH_ABILITIES, CHEEK_POUCH_FRACTION, HARVEST_ABILITIES, HARVEST_CHANCE, HARVEST_SUN_CHANCE, HARVEST_SUN, CUD_CHEW_ABILITIES, CUD_CHEW_DELAY, PICKUP_ABILITIES, LAST_BERRY_MARKER, CUD_CHEW_MARKER, ITEM_SPENT_MARKER, TRACE_ABILITIES, IMPOSTER_ABILITIES, ILLUSION_ABILITIES, ILLUSION_MARKER, PLATE_TYPE_ABILITIES, PLATE_BASE_TYPES, ITEM_WELDED_ABILITIES, MOLD_BREAKING_ABILITIES, MOULD_BROKEN_MARKER, NEUTRALIZING_GAS_ABILITIES, GAS_SUPPRESSED_MARKER, UNAWARE_ABILITIES, UNAWARE_DEFENSIVE_STATS, UNAWARE_OFFENSIVE_STATS, PERSONAL_SUN_ABILITIES, PERSONAL_SUN_WEATHER, UNOVERRIDABLE_SKIES, BATTLE_BOND_ABILITIES, BATTLE_BOND_FORM, BATTLE_BOND_SHURIKEN, BATTLE_BOND_SHURIKEN_POWER, BATTLE_BOND_SHURIKEN_HITS, WEATHER_ACCURACY_MOVES, STARTER_PERFECT_IVS, STARTER_IV_FLOOR, STARTER_IV_CEILING, TYPE_BOOST_MULTIPLIER, TYPE_ENHANCER_ITEMS, TYPE_GEM_MULTIPLIER, TYPE_GEMS, INERT_PLATES, PLATE_TYPES, ITEM_HIT_REACTIONS, TERRAIN_SEED_ITEMS, THROAT_SPRAY_BOOST, BLUNDER_POLICY_BOOST, ROOM_SERVICE_DROP, MENTAL_HERB_CURES, EJECT_ITEMS, PIVOT_REQUEST, RANDOM_REPLACEMENT_ITEMS, SHED_SHELL, ITEM_ACCURACY_MULTIPLIERS, ZOOM_LENS_MULTIPLIER, ITEM_ACCURACY_AGAINST_HOLDER, ITEM_FLINCH_CHANCE, QUICK_CLAW_ODDS, LAST_IN_BRACKET_ITEMS, SECONDARY_IMMUNE_ITEMS, STAT_DROP_IMMUNE_ITEMS, COPIES_BOOSTS_ITEMS, POWDER_IMMUNE_ITEMS, WEATHER_CHIP_IMMUNE_ITEMS, NO_CONTACT_ITEMS, PUNCH_MOVES, PUNCHING_GLOVE_BOOST, EVIOLITE_MULTIPLIER, EVIOLITE_STATS, UNEVOLVED_SPECIES, FOCUS_BAND_ODDS, SHELL_BELL_FRACTION, BIG_ROOT_DRAIN_BONUS, BINDING_BAND_MULTIPLIER, GRIP_CLAW_TURNS, LOADED_DICE_MIN_HITS, HEAVY_DUTY_BOOTS, ABILITY_SHIELD, SPECIES_STAT_ITEMS, SPECIES_CRIT_ITEMS, SPECIES_TYPE_BOOST_ITEMS, SPECIES_ORB_MULTIPLIER, SPECIES_FORM_ITEMS, BERRY_HIT_REACTIONS, LANSAT_MARKER, MICLE_MARKER, CUSTAP_MARKER, LANSAT_CRIT_STAGES, MICLE_ACCURACY_MULTIPLIER, CUSTAP_TIER, STARF_STATS, ACTION_MARKER_FRESH, Z_HP_FRACTION_KEY, MEGA_STONE_SPECIES, Z_CRYSTAL_TYPES, SIGNATURE_Z_CRYSTALS, MEMORY_TYPES, FLAT_DAMAGE_ITEMS, FLAT_DAMAGE_BOOST, WEIGHT_ITEMS, GROUNDING_ITEMS, IRON_BALL, IRON_BALL_SPEED, pierces_own_immunity, move_pierces_immunity, ADRENALINE_ORB, ADRENALINE_ORB_STAGES, END_OF_TURN_ITEMS, STICKY_BARB, STICKY_BARB_DIVISOR, UTILITY_UMBRELLA, SHELTERED_SKIES, DESTINY_KNOT, BATTLE_BAG_ITEMS, CONTACT_MOVES, MAX_MOVE_MARKER, MAX_MOVE_PRIORITY, MAX_GUARD_PRIORITY, Z_MOVE_MARKER, LAST_MOVE_WAS_Z, SHADOW_MOVES, MAX_MOVE_NAMES, Z_MOVE_SIGNATURES, STARMOBILE_MOVES, LAST_MOVER_DOUBLING_MOVES, get_species_weight, get_species_base_attack
from datetime import datetime, timezone


def apply_entry_hazards(specimen, hazards, type_chart, owner_prefix="Your"):
    """
    Calculates environmental hazard damage and effects when a specimen enters the habitat.
    Modifies the specimen's HP, stats, and status in-place. Returns the combat log string.
    """
    log = ""
    types = specimen.get('types', [])

    # ITEM PHASE 5: Heavy-Duty Boots walk over everything laid on this side of the field.
    # Answered before anything is read, because the boots do not care WHICH hazard it is.
    if ignores_hazards(specimen):
        return log

    # Is the specimen touching the ground?
    #
    # This was a LOCAL re-implementation - `'flying' not in types and ability not in
    # LEVITATION_ABILITIES` - which knew about types and abilities and nothing else. So
    # the Air Balloon did not lift its holder over Spikes, despite being sold with the
    # words "ground hazards" in its own shop entry, and neither did Magnet Rise or
    # Telekinesis. The comment it carried even said this line and `is_grounded` had to
    # be changed together, which is the tell: two copies that must agree are one copy
    # waiting to be written. It asks the shared function now, and the Iron Ball's
    # grounding half arrives for free because of it.
    grounded = is_grounded(specimen)

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
    if spikes_layers > 0 and grounded:
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
    if ts_layers > 0 and grounded:
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
    if hazards.get('sticky-web') and grounded:
        # Routed through the shared resolver rather than writing the stage here, so the
        # web meets Clear Body and rouses Defiant exactly as any other drop does. The
        # source is a stand-in - whoever laid the web may be long gone - and the entry is
        # marked unreflectable so Mirror Armor refuses the drop instead of trying to hand
        # it back to nobody.
        web_log = resolve_stat_stages(
            [(specimen, 'speed', -1, HAZARD_SOURCE, False)])
        if web_log:
            log += (f"🕸️ {owner_prefix.strip()} **{specimen['name'].capitalize()}** "
                    f"was caught in a sticky web!\n")
            log += web_log


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
    
    for stat in stat_names:
        core = (2 * base_stats[stat] + ivs[stat] + math.floor(evs[stat] / 4)) * level
        pre_nature = math.floor(core / 100) + 5

        # **THIS USED TO COMPARE `stat` TO THE NATURE TABLE'S OWN SPELLING**, and the
        # table says `special-attack` where this loop says `sp_atk`. The comparison was
        # therefore never true for either special stat, and every special-stat modifier
        # in the game was silently discarded: fourteen of the twenty-five natures lost
        # half their effect, Careful and Rash lost all of it, and Modest applied its
        # -Attack and never its +Special Attack. `nature_multiplier` speaks both
        # spellings, so the loop's names no longer have to match the table's.
        final_stats[stat] = math.floor(pre_nature * nature_multiplier(nature, stat))

    return final_stats

def check_consumables(pokemon, owner_str, magic_room=False, opponent=None):
    """
    Monitors biological thresholds and consumes berries that have hit their trigger.

    The actual resolution lives in apply_berry_effect, which Teatime, Bug Bite, Pluck and
    a flung berry also drive - keeping one implementation is what guarantees every route
    to eating a berry records it for Belch.

    `opponent` is read only for Unnerve. Asked here rather than remembered from the
    switch-in, so the moment its owner withdraws the berries become edible again - which
    is what "while the Pokemon is in battle" means.
    """
    if pokemon is None or pokemon['current_hp'] <= 0:
        return ""

    # An embargoed holder, or one standing in a Magic Room, cannot reach its own berry.
    held_item = get_active_item(pokemon, magic_room)
    if held_item not in CONSUMABLE_DATABASE:
        return ""

    if berries_are_blocked(opponent):
        return (f"😰 {owner_str} **{pokemon['name'].capitalize()}** is too unnerved "
                f"to eat its {held_item.replace('-', ' ').title()}!\n")

    return apply_berry_effect(pokemon, held_item, ignore_threshold=False, owner_str=owner_str)


def berries_are_blocked(opponent):
    """Unnerve, read off the specimen standing opposite."""
    return bool(opponent) and get_active_ability(opponent) in BERRY_BLOCKING_ABILITIES

# ==========================================
# 🏹 KNOCKED OUT OF THE AIR
# ==========================================
# Thousand Arrows drags a raised specimen down and KEEPS IT DOWN for the rest of the
# battle - so this is a volatile rather than a one-off, and `is_grounded` has to honour
# it or the grounding would last exactly as long as the turn it happened in.
#
# Named for Smack Down, which is the same effect and is already sitting in `base_moves`
# doing nothing. It is deliberately NOT in GROUNDING_MOVES: adding it would change how an
# existing move behaves, and that was not asked for. One word, when it is.
SMACKED_DOWN = 'smacked_down'

# **SMACK DOWN IS THE SAME EFFECT AND WAS SITTING IN `base_moves` DOING NOTHING.** It is
# Rock rather than Ground, so it never needed the type chart opened for it - a Rock move
# is super effective on a Flying type already - but it knocks its target out of the air
# exactly as Thousand Arrows does, and now says so.
GROUNDING_MOVES = {'thousand-arrows', 'smack-down'}

# The two ways of being raised that live in volatiles. The other two - the Flying type and
# Levitate - are read off the specimen itself and cannot be popped.
LIFTING_VOLATILES = ('magnet_rise', 'telekinesis')


def is_raised(pokemon, ability=None):
    """
    Whether this specimen is off the ground for a reason a grounding move answers.

    **THE AIR BALLOON COUNTS.** It did not at first - the brief named the Flying type,
    Levitate, Magnet Rise and Telekinesis, and the balloon is none of those - but the
    games let Thousand Arrows through it, and being kept airborne is being kept airborne
    however it is done. The balloon then pops on the hit like any other damaging move, so
    a specimen is not both grounded and still holding one.

    Still NOT the same question as `not is_grounded`: an Iron Ball holder is grounded and
    was never raised, and anything already smacked down is on the floor for good.
    """
    if pokemon is None:
        return False
    volatiles = pokemon.get('volatile_statuses') or {}
    if volatiles.get(SMACKED_DOWN):
        return False
    if 'flying' in (pokemon.get('types') or []):
        return True
    if (ability if ability is not None else get_active_ability(pokemon)) \
            in LEVITATION_ABILITIES:
        return True
    if get_active_item(pokemon) == 'air-balloon':
        return True
    return any(volatiles.get(key) for key in LIFTING_VOLATILES)


def ground_specimen(pokemon):
    """
    Knock it down and keep it there. Returns whether anything actually changed.

    Magnet Rise and Telekinesis are POPPED rather than merely overruled, because they are
    counted down elsewhere and a specimen that is already on the floor should not still be
    told its Magnet Rise has three turns left.
    """
    if pokemon is None:
        return False
    volatiles = pokemon.setdefault('volatile_statuses', {})
    if volatiles.get(SMACKED_DOWN):
        return False
    volatiles[SMACKED_DOWN] = True
    for key in LIFTING_VOLATILES:
        volatiles.pop(key, None)
    return True


def is_grounded(pokemon, gravity_active=False):
    """Evaluates if a specimen is physically touching the battlefield."""
    if gravity_active: return True # 🚨 Gravity grounds everything!
    # Knocked out of the air and kept there. Read before the Iron Ball for the same
    # reason the Iron Ball is read before the Flying type: it is the fact that settles
    # the question, whatever else is true.
    if (pokemon.get('volatile_statuses') or {}).get(SMACKED_DOWN): return True
    types = pokemon.get('types', [])
    ability = get_active_ability(pokemon)
    item = get_active_item(pokemon)

    # ITEM PHASE 9: the Iron Ball outranks every reason to be off the ground, which is
    # why it is checked before the Flying type rather than after. Hazards and terrain
    # read this too, so an Iron Ball holder eats Spikes and stands in a Grassy Terrain.
    if item in GROUNDING_ITEMS: return True

    if 'flying' in types: return False
    if ability in LEVITATION_ABILITIES: return False
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
        ratio = effective_weight(attacker) / max(0.1, effective_weight(defender))
        if ratio >= 5: return 120
        if ratio >= 4: return 100
        if ratio >= 3: return 80
        if ratio >= 2: return 60
        return 40

    if move_name in ['grass-knot', 'low-kick']:
        # Purely the target's mass - a heavy target is easier to trip
        weight = effective_weight(defender)
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
        # Comatose counts. It is a status the specimen wears permanently, and Hex
        # asks whether the target is afflicted rather than which affliction it is.
        status = defender.get('status_condition') or {}
        return 130 if (status.get('name') or is_effectively_asleep(defender)) else 65

    if move_name in LAST_MOVER_DOUBLING_MOVES:
        # Doubles if the target already struck the user earlier in this same turn.
        # last_damage_taken is written on hit and wiped at end of turn, so its mere
        # presence means "was hit before moving".
        #
        # AVALANCHE is the same rule as Revenge with a different name and was simply
        # missing - it dealt a flat 60 whether or not the user had been hit, so the whole
        # point of a -4 priority move was never paid out. One table rather than two
        # branches, because two branches is how they came to disagree in the first place.
        base = LAST_MOVER_DOUBLING_MOVES[move_name]
        return base * 2 if attacker.get('last_damage_taken', 0) > 0 else base

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
# 🎲 MOVES THAT DECIDE THEIR OWN ELEMENT OR POWER
# ==========================================
# Hidden Power's element is read out of the six IVs - one bit each, least significant,
# in the order the games use. Sixteen types: Normal and Fairy are never produced.
HIDDEN_POWER_TYPES = [
    'fighting', 'flying', 'poison', 'ground', 'rock', 'bug', 'ghost', 'steel',
    'fire', 'water', 'grass', 'electric', 'psychic', 'ice', 'dragon', 'dark',
]
HIDDEN_POWER_IV_ORDER = ['hp', 'attack', 'defense', 'speed', 'sp_atk', 'sp_def']

# Weather Ball and Terrain Pulse both take their element from the conditions and double
# in power when there are any. Terrain Pulse additionally needs the user on the ground -
# terrain cannot reach something that is airborne.
WEATHER_BALL_TYPES = {
    'sun': 'fire', 'extremely-harsh-sunlight': 'fire',
    'rain': 'water', 'heavy-rain': 'water',
    'sandstorm': 'rock', 'hail': 'ice', 'snow': 'ice',
}
TERRAIN_PULSE_TYPES = {
    'electric': 'electric', 'grassy': 'grass', 'misty': 'fairy', 'psychic': 'psychic',
}
CONDITION_BALL_MULTIPLIER = 2

# Nature Power becomes a different move depending on what is underfoot.
NATURE_POWER_MOVES = {
    'electric': 'thunderbolt', 'grassy': 'energy-ball',
    'misty': 'moonblast', 'psychic': 'psychic',
}
NATURE_POWER_DEFAULT = 'tri-attack'

# Every move Transform copies arrives with five PP, however much the original had.
TRANSFORM_COPIED_PP = 5

# ==========================================
# 🛡️ BIDE
# ==========================================
# Two turns of soaking up punishment, then twice the total handed straight back. The
# payout ignores type entirely - it is not an elemental hit, which is why it goes back
# as raw damage rather than through the chart.
#
# NOTE: the user is not force-locked into Bide across those turns the way the mainline
# games lock it. The storage persists regardless, so choosing something else in between
# delays the release rather than losing it. Locking the move would mean routing Bide
# through the two-turn charge machinery, which is built to fire on the second turn
# rather than the third.
BIDE_TURNS = 2
BIDE_MULTIPLIER = 2


def begin_bide(pokemon):
    """Start soaking. Returns nothing - the storage lives on the specimen."""
    volatiles = pokemon.setdefault('volatile_statuses', {})
    volatiles['bide'] = BIDE_TURNS
    volatiles['bide_damage'] = 0


def store_bide_damage(pokemon, amount):
    """
    Add to a biding specimen's tally. Called wherever damage is recorded, and silently
    ignored by anything that is not currently biding.
    """
    volatiles = (pokemon or {}).get('volatile_statuses') or {}
    if volatiles.get('bide'):
        volatiles['bide_damage'] = volatiles.get('bide_damage', 0) + max(0, amount or 0)


def bide_stored(pokemon):
    """How much punishment is banked so far."""
    return ((pokemon or {}).get('volatile_statuses') or {}).get('bide_damage', 0) or 0

# Magnitude rolls its own power. Weights are out of 100, as the games distribute them -
# the middling tremors are far more common than either extreme.
MAGNITUDE_TABLE = [(5, 10, 4), (10, 30, 5), (20, 50, 6), (30, 70, 7),
                   (20, 90, 8), (10, 110, 9), (5, 150, 10)]


def beat_up_powers(user_party):
    """
    One power per conscious party member, from that member's SPECIES base Attack. The
    user's own Attack still swings every strike - only the power varies down the party,
    which is what makes a weak user with a strong bench worth something.
    """
    return [math.floor(get_species_base_attack(member) / 10) + 5
            for member in (user_party or [])
            if member and member.get('current_hp', 0) > 0
            and not (member.get('status_condition') or {}).get('name') in
            ('sleep', 'freeze', 'paralysis', 'burn', 'poison')]


def apply_transform(attacker, defender):
    """
    Take on the target's shape: its species, types, stats bar HP, ability and movelist,
    every copied move carrying 5 PP. Returns a log fragment, or '' when it cannot.

    The original is stashed whole so withdrawing undoes it - a transformed specimen that
    switched out and came back wearing the other's face would be a lasting corruption of
    the roster rather than a battle effect.
    """
    if attacker is None or defender is None:
        return ""
    if (attacker.get('volatile_statuses') or {}).get('transformed'):
        return ""
    # Copying a copy would compound the borrowed shape rather than mirror the original.
    if (defender.get('volatile_statuses') or {}).get('transformed'):
        return ""

    attacker['_pre_transform'] = {
        'pokedex_id': attacker.get('pokedex_id'),
        'name': attacker.get('name'),
        'types': list(attacker.get('types') or []),
        'stats': dict(attacker.get('stats') or {}),
        'moves': [dict(slot) for slot in (attacker.get('moves') or [])],
        'ability': attacker.get('ability'),
    }

    borrowed = dict(defender.get('stats') or {})
    borrowed['hp'] = (attacker.get('stats') or {}).get('hp', borrowed.get('hp', 50))

    attacker['pokedex_id'] = defender.get('pokedex_id')
    # The name has always been stashed in the snapshot above and was never actually
    # changed here, so a Transform swapped the SPRITE and left the label reading Ditto.
    # Found by Block 20, where Imposter pays for this on arrival rather than on a turn.
    attacker['name'] = defender.get('name')
    attacker['types'] = list(defender.get('types') or [])
    attacker['stats'] = borrowed
    # Read through the accessor rather than the raw key, so a suppressed target hands
    # over the ability it actually owns rather than whatever was left lying in the dict.
    attacker['ability'] = get_stored_ability(defender)
    attacker['moves'] = [{'name': slot.get('name'), 'pp': TRANSFORM_COPIED_PP,
                          'max_pp': TRANSFORM_COPIED_PP}
                         for slot in (defender.get('moves') or [])]
    attacker.setdefault('volatile_statuses', {})['transformed'] = True

    return (f"🎭 {attacker['_pre_transform']['name'].capitalize()} transformed into "
            f"{defender['name'].capitalize()}!")


def restore_pre_transform(pokemon):
    """Put a transformed specimen back in its own shape when it leaves the field."""
    original = (pokemon or {}).pop('_pre_transform', None)
    if not original:
        return
    pokemon.update(original)
    (pokemon.get('volatile_statuses') or {}).pop('transformed', None)


def hidden_power_type(attacker):
    """
    The element Hidden Power resolves to for this specimen. Defaults to a flawless
    spread when nothing recorded IVs, which is what NPC and wild rosters carry.
    """
    ivs = (attacker or {}).get('ivs') or {}
    total = 0
    for slot, stat in enumerate(HIDDEN_POWER_IV_ORDER):
        total += (int(ivs.get(stat, 31)) & 1) << slot

    return HIDDEN_POWER_TYPES[(total * 15) // 63]


def roll_magnitude(rng=None):
    """One tremor: returns (power, magnitude_number)."""
    roll = (rng or random).randint(1, 100)
    for weight, power, number in MAGNITUDE_TABLE:
        roll -= weight
        if roll <= 0:
            return power, number
    return MAGNITUDE_TABLE[-1][1], MAGNITUDE_TABLE[-1][2]


def nature_power_move(terrain):
    """Which move Nature Power becomes underfoot."""
    return NATURE_POWER_MOVES.get(terrain, NATURE_POWER_DEFAULT)


def shares_a_type(attacker, defender):
    """Whether the two have any element in common - Synchronoise's whole condition."""
    return bool(set(attacker.get('types') or []) & set(defender.get('types') or []))


# ==========================================
# 💘 INFATUATION
# ==========================================
# Attract and G-Max Cuddle both arrive through the database's 'infatuation' ailment, so
# the rule lives here rather than on either move.
#
# Infatuation is a VOLATILE in the games, not a major status: a charmed specimen can
# still be burned or put to sleep. The database only offers it as an ailment, so it is
# converted on arrival the same way 'trap' already is.
INFATUATION_IMMOBILISE_CHANCE = 50

# Oblivious cannot be charmed at all; Aroma Veil shields against it too.
INFATUATION_IMMUNE_ABILITIES = {'oblivious', 'aroma-veil'}


def can_be_infatuated(attacker, defender):
    """
    Whether the target can be charmed by this user.

    Both sides need a KNOWN and OPPOSITE gender. A genderless specimen can neither charm
    nor be charmed, and two of the same gender have nothing to work with - which is the
    whole point of the move and was the part going unchecked.
    """
    charmer = (attacker or {}).get('gender')
    target = (defender or {}).get('gender')
    if charmer not in ('M', 'F') or target not in ('M', 'F'):
        return False
    return charmer != target


def infatuation_blocked_by(defender):
    """The ability shielding this target from infatuation, or None."""
    ability = get_active_ability(defender)
    return ability if ability in INFATUATION_IMMUNE_ABILITIES else None


def is_infatuated(pokemon):
    """Whether this specimen is currently charmed."""
    return bool(((pokemon or {}).get('volatile_statuses') or {}).get('infatuation'))


def infatuation_holds_it_back(pokemon, rng=None):
    """
    Whether infatuation stops this specimen acting this turn. Rolled per turn, so a
    charmed specimen is hampered rather than disabled.
    """
    if not is_infatuated(pokemon):
        return False
    return (rng or random).randint(1, 100) <= INFATUATION_IMMOBILISE_CHANCE


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
# 👥 MOVES THAT NEED AN ALLY ON THE FIELD
# ==========================================
# These fail in a single battle in the mainline games too - this is not a shortcut around
# a one-per-side engine, it is what the move does. They are named here so they fail with
# an explanation rather than doing nothing quietly, the same as Quash and After You.
DOUBLES_ONLY_MOVES = {
    'ally-switch': "there was no ally to switch places with",
    'dragon-cheer': "there were no allies to cheer on",
    'hold-hands': "there was no ally to hold hands with",
    'spotlight': "there was nobody else to put in the spotlight",
}


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
# berries and the five that answer a hit for 100, and the six EV-lowering berries for
# the 90-power middle tier - which was empty until Item Phase 7 planted them.
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

    # --- Item Phase 7: the five that answer a hit, which throw just as hard ---
    'enigma-berry': ('bug', 100),    'jaboca-berry': ('dragon', 100),
    'rowap-berry': ('dark', 100),    'kee-berry': ('fairy', 100),
    'maranga-berry': ('dark', 100),

    # --- ...and the six that lower an EV, the whole of the 90-power tier ---
    'pomeg-berry': ('ice', 90),      'kelpsy-berry': ('fighting', 90),
    'qualot-berry': ('poison', 90),  'hondew-berry': ('ground', 90),
    'grepa-berry': ('flying', 90),   'tamato-berry': ('grass', 90),
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

    if move_name == 'beat-up':
        # One strike per able party member, resolved as a single blow carrying their
        # combined power. The engine's strike loop applies one power to every hit, so
        # summing here keeps the party's contribution without pretending each member
        # rolls its own critical.
        return sum(beat_up_powers(attacker.get('_beat_up_party'))) or None

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

def is_crit_guaranteed(move_name, attacker, defender=None):
    """
    True when this strike is a certainty rather than a roll.

    Merciless takes the defender, which is why this grew a third argument: it is the one
    guaranteed crit that depends on the state of the TARGET rather than the user.
    """
    if move_name in ALWAYS_CRIT_MOVES:
        return True
    if (get_active_ability(attacker) == 'merciless'
            and (defender or {}).get('status_condition')
            and (defender['status_condition'] or {}).get('name') == 'poison'):
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

# PLATE_TYPES now lives in constants.py and is imported above. It moved because it has
# a second reader: the shop needs the same seventeen names to stock them, and a plate
# table in two files is exactly the drift `type_from_item` was split out to prevent.
# Everything that imported it from here still can - it is re-exported by the import.

DRIVE_TYPES = {
    'burn-drive': 'fire', 'chill-drive': 'ice',
    'douse-drive': 'water', 'shock-drive': 'electric',
}

# ==========================================
# 💎 ITEM PHASE 1: THE TYPE-BOOSTER TABLE
# ==========================================
# Derived, not retyped. The plates already have a table - the one directly above, which
# drives Judgment's element and Multitype's form - and their missing 20% is the SAME
# seventeen rows read for a different purpose. Writing them out again in constants.py
# would have created the second plate table that `type_from_item` exists to prevent.
TYPE_BOOST_ITEMS = dict(PLATE_TYPES)
TYPE_BOOST_ITEMS.update(TYPE_ENHANCER_ITEMS)


def type_boost_multiplier(held_item, move_type):
    """
    What a plate, enhancer or incense does to a move of this element.

    Permanent items only - gems are consumed and so are asked separately, by the
    caller that is in a position to spend them.
    """
    if not held_item or not move_type:
        return 1.0
    item = str(held_item).lower().replace(' ', '-')
    if TYPE_BOOST_ITEMS.get(item) == str(move_type).lower():
        return TYPE_BOOST_MULTIPLIER
    return 1.0


def gem_for(held_item, move_type):
    """The gem this move would spend, or None. Spending it is the caller's business."""
    if not held_item or not move_type:
        return None
    item = str(held_item).lower().replace(' ', '-')
    if TYPE_GEMS.get(item) == str(move_type).lower():
        return item
    return None

# Camouflage reads the ground it is standing on
CAMOUFLAGE_TYPES = {
    'electric': 'electric', 'grassy': 'grass',
    'misty': 'fairy', 'psychic': 'psychic',
}

# Moves that burn away one of the user's own types once they connect
TYPE_SHEDDING_MOVES = {'burn-up': 'fire', 'double-shock': 'electric'}

def type_from_item(kind, held_item):
    """
    The element one of the three signature item families dictates, or None.

    Split out of resolve_item_move_type for Block 20: Multitype and RKS System ask the
    same question of the same items that Judgment and Multi-Attack do, and asking it in
    two places is how the Plate table would eventually come to have two versions.
    """
    item = (held_item or '').lower().replace(' ', '-')

    if kind == 'plate':
        return PLATE_TYPES.get(item)
    if kind == 'drive':
        return DRIVE_TYPES.get(item)
    if kind == 'memory':
        # Memories are uniformly "<type>-memory", which this used to read off the string.
        # A suffix is not a vocabulary though: it answered 'banana' for a banana-memory,
        # and a type nothing in TYPE_CHART recognises makes a specimen immune to
        # everything. MEMORY_TYPES is the vocabulary, checked against TYPE_CHART where
        # it is built.
        return MEMORY_TYPES.get(item)
    return None


def resolve_item_move_type(move_name, held_item, default_type):
    """
    Element for the signature moves that read a held item. Falls back to the stored type
    when the matching item is absent, which is what the games do for a bare Arceus.
    """
    kind = ITEM_TYPE_MOVES.get(move_name)
    if not kind:
        return default_type
    return type_from_item(kind, held_item) or default_type

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

# What a mould-breaker's move stops noticing on the way in.
#
# DERIVED from the tables that already say what blunts or refuses a move, rather than
# hand-listed. Two reasons, and the second is the important one: a hand-list of forty
# names would be wrong the day it was written, and it would go on being wrong every time
# a later block added an immunity - Mold Breaker would silently stop covering it. Built
# this way, the next defensive ability anybody adds is ignored the moment it exists.
#
# The rule, stated: a mould-breaker ignores anything that would BLUNT OR REFUSE the
# incoming move. It does not touch anything that merely answers a move once it has
# landed - Rough Skin, Iron Barbs, Static, Effect Spore, Colour Change, Cursed Body and
# Aftermath all still fire, because none of them stops the move.
#
# FORM_LOCKED_ABILITIES is subtracted for the same reason it exists everywhere else in
# this file: those are not defences, they are the machinery of somebody's body.
MOLD_BREAKER_IGNORES = (
    set(BIOLOGICAL_TRAITS.get('immunities', {}))
    | set(BIOLOGICAL_TRAITS.get('incoming_multipliers', {}))
    | set(STATUS_IMMUNE_ABILITIES)
    | set(VOLATILE_IMMUNE_ABILITIES)
    | set(STATUS_MOVE_IMMUNE_ABILITIES)
    | set(MOVE_FAMILY_IMMUNE_ABILITIES)
    | set(STAT_DROP_IMMUNE_ABILITIES)
    | set(EVASION_MULTIPLIER_ABILITIES)
    | set(SECONDARY_IMMUNE_ABILITIES)
    | set(INTIMIDATE_IMMUNE_ABILITIES)
    | set(EXPLOSION_BLOCKING_ABILITIES)
    | set(WIND_IMMUNE_ABILITIES)
    | set(TERA_SHELL_ABILITIES)
    | set(MAGIC_BOUNCE_ABILITIES)
    | set(PRIORITY_BLOCKING_ABILITIES)
    | set(LEVITATION_ABILITIES)
    | set(FORCED_SWITCH_IMMUNE_ABILITIES)
    # The handful that live in a branch rather than a table, so no set names them.
    | {'sturdy', 'wonder-guard', 'battle-armor', 'shell-armor'}
) - FORM_LOCKED_ABILITIES


# ==========================================
# 🎭 BLOCK 20: WEARING ANOTHER IDENTITY
# ==========================================
def traced_ability(tracer, opponent):
    """
    What Trace copies off the specimen standing opposite, or None.

    Read through the ACTIVE accessor on both ends: a Trace that has itself been
    suppressed copies nothing, and a target sitting under a Gastro Acid has nothing to
    hand over. UNCOPYABLE_ABILITIES is the same guard Role Play and Doodle answer to -
    duplicating a form-locked ability would hand out the machinery of somebody else's
    body.
    """
    if get_active_ability(tracer) not in TRACE_ABILITIES:
        return None
    if opponent is None or opponent.get('current_hp', 0) <= 0:
        return None

    theirs = get_active_ability(opponent)
    if theirs in ('none', '') or theirs in UNCOPYABLE_ABILITIES:
        return None
    return theirs


def disguise_model(party, wearer):
    """
    Illusion: whose face the wearer puts on - the LAST conscious member of its own party.

    Identity rather than name, so a party carrying two of a species does not have one
    answering for the other, and a fainted member is never worn: the disguise is meant to
    be a specimen the opponent could plausibly still be sent.
    """
    for member in reversed(list(party or [])):
        if member is None or member is wearer:
            continue
        if member.get('current_hp', 0) > 0:
            return member
    return None


def wear_illusion(wearer, model):
    """
    Put the disguise on. Returns True when one went on.

    ONLY the name and the dex id are borrowed. Types, stats, ability and movelist stay
    the wearer's own - that is the whole difference between Illusion and Transform, and
    it is why this cannot reuse apply_transform however similar the two look.
    """
    if wearer is None or model is None:
        return False
    if wearer.get(ILLUSION_MARKER):
        return False
    if get_active_ability(wearer) not in ILLUSION_ABILITIES:
        return False

    wearer[ILLUSION_MARKER] = {'name': wearer.get('name'),
                               'pokedex_id': wearer.get('pokedex_id')}
    wearer['name'] = model.get('name')
    wearer['pokedex_id'] = model.get('pokedex_id')
    return True


def drop_illusion(wearer):
    """
    Take the disguise off. Returns the real name when one came off, or None.

    Deliberately does NOT ask whether the ability is still Illusion. Once the face is on,
    what takes it off is a hit landing - and by then a Mummy or a Skill Swap may well
    have painted over the ability that put it there.
    """
    real = (wearer or {}).pop(ILLUSION_MARKER, None)
    if not real:
        return None
    wearer['name'] = real['name']
    wearer['pokedex_id'] = real['pokedex_id']
    return real['name']


def true_pokedex_id(pokemon):
    """
    The specimen's OWN dex id, seeing through any disguise.

    Illusion is meant to fool a trainer, not the physics. Everything species-derived that
    is read during a battle has to ask this rather than the borrowed id, or a disguised
    Zoroark would be weighed as whatever it is pretending to be and Grass Knot would
    quietly tell the opponent it was lying.
    """
    real = (pokemon or {}).get(ILLUSION_MARKER)
    return real['pokedex_id'] if real else (pokemon or {}).get('pokedex_id')


def rewrite_plate_type(pokemon, magic_room=False):
    """
    Multitype and RKS System: be whatever the held Plate or Memory says.

    Returns the element it has just become, or None when nothing changed. The specimen's
    OWN types are stashed the first time it is asked, so an item that goes away - a Magic
    Room, an Embargo - puts the real ones back instead of leaving it stuck wearing the
    last Plate it held.

    Written straight onto `types`, the way Colour Change already writes, rather than as a
    read-through accessor: Mimicry is the read-through one and its own docstring records
    that it reaches the damage formula but not the places that read `types` directly.
    A type this permanent should reach all of them.
    """
    kind = PLATE_TYPE_ABILITIES.get(get_active_ability(pokemon))
    if not kind:
        return None

    pokemon.setdefault(PLATE_BASE_TYPES, list(pokemon.get('types') or []))
    # Handed the room rather than defaulting it: get_active_item cannot see a Magic Room
    # it was not told about, and the whole reason this is re-asked every turn is that the
    # room can come down.
    worn = type_from_item(kind, get_active_item(pokemon, magic_room))
    wanted = [worn] if worn else list(pokemon[PLATE_BASE_TYPES])

    if list(pokemon.get('types') or []) == wanted:
        return None
    pokemon['types'] = wanted
    return wanted[0] if wanted else None


def restore_own_types(pokemon):
    """Undo a Plate type on the way out, so the roster keeps the specimen's real one."""
    own = (pokemon or {}).pop(PLATE_BASE_TYPES, None)
    if own is not None:
        pokemon['types'] = list(own)


def pretty_ability(ability):
    """'sheer-force' -> 'Sheer Force', for combat log lines."""
    return (ability or 'none').replace('-', ' ').title()


# The words a title leaves in lower case. Four names in the reference data are built
# around one - 'scroll-of-darkness', 'roar-of-time', 'light-of-ruin', 'guardian-of-alola' -
# and `.title()` alone rendered every one of them with a capital 'Of'.
TITLE_MINOR_WORDS = frozenset({'of', 'the', 'and', 'in', 'on', 'to', 'a', 'an'})


def pretty_item(item):
    """'choice-scarf' -> 'Choice Scarf', for combat log lines and the dex."""
    words = (item or 'none').replace('-', ' ').split()
    return " ".join(word.title() if index == 0 or word.lower() not in TITLE_MINOR_WORDS
                    else word.lower()
                    for index, word in enumerate(words))


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


def _shield_in_hand(pokemon):
    """
    Whether an Ability Shield is in force, WITHOUT asking what ability the holder has.

    get_active_item consults Klutz, and Klutz is an ability, so the ordinary accessor
    cannot be used from inside get_active_ability - it would call back into the function
    it was called from. Embargo is a volatile and costs no ability lookup, so it is
    honoured here; Klutz and Magic Room are not, and a shield under either keeps working.
    Stated rather than hidden: it is a narrow gap, and closing it would mean untangling
    the accessor pair.
    """
    if pokemon is None:
        return False
    held = (pokemon.get('held_item') or 'none').lower().replace(' ', '-')
    if held != ABILITY_SHIELD:
        return False
    return not (pokemon.get('volatile_statuses') or {}).get('embargo')


def get_active_ability(pokemon):
    """
    The ability actually in force right now - 'none' while it is suppressed.

    Gastro Acid and Core Enforcer switch an ability off without erasing it, so the stored
    name has to survive in order to come back when the specimen is withdrawn. Every
    battle-time read goes through here so a suppressed ability is genuinely inert; only
    code that PERSISTS an ability (evolution, Mega forms) touches ['ability'] directly.

    Block 21 adds the other two suppressors here rather than at the two hundred places
    that call this, which is what the accessor split was built for. All three are
    properties of the SLOT, so restore_base_ability sweeps all three away on withdrawal:

      ability_suppressed  Gastro Acid and Core Enforcer. Switches off everything except
                          the form-locked machinery, and lasts until the specimen leaves.
      gas_suppressed      Neutralizing Gas, standing opposite. Same reach, but recomputed
                          from the field every time anybody arrives or the turn ends, so
                          it lapses the moment the gasser does.
      mould_broken        A mould-breaker's move, mid-strike. Reaches only the abilities
                          that would have BLUNTED OR REFUSED it, and is gone again before
                          the call that set it returns.
    """
    if pokemon is None:
        return 'none'

    volatiles = pokemon.get('volatile_statuses') or {}

    # ITEM PHASE 5: an Ability Shield refuses all three suppressors at once, which is why
    # it is answered before any of them rather than beside one.
    if _shield_in_hand(pokemon):
        return get_stored_ability(pokemon)

    if volatiles.get('ability_suppressed'):
        return 'none'

    stored = get_stored_ability(pokemon)
    if volatiles.get(GAS_SUPPRESSED_MARKER) and stored not in UNSUPPRESSABLE_ABILITIES:
        return 'none'
    if volatiles.get(MOULD_BROKEN_MARKER) and stored in MOLD_BREAKER_IGNORES:
        return 'none'
    return stored


def set_active_ability(pokemon, new_ability):
    """
    Overwrite an ability for the rest of the battle, remembering the original so that
    restore_base_ability can put it back when the specimen leaves the field.
    """
    if pokemon is None:
        return
    # ITEM PHASE 5: an Ability Shield refuses to have its holder's ability rewritten.
    # Skill Swap, Entrainment, Worry Seed, Simple Beam and a Trace aimed at it all stop
    # here, because this is the one function every one of them goes through.
    if _shield_in_hand(pokemon):
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
    volatiles = pokemon.get('volatile_statuses') or {}
    volatiles.pop('ability_suppressed', None)
    # Block 21's two, for the same reason: all three are properties of the slot. The gas
    # is recomputed on arrival anyway, but a specimen must not sit on the bench carrying
    # a suppression from a field it is no longer standing on.
    volatiles.pop(GAS_SUPPRESSED_MARKER, None)
    volatiles.pop(MOULD_BROKEN_MARKER, None)


def breaks_moulds(attacker):
    """Whether this specimen's move ignores what the target would do to stop it."""
    return get_active_ability(attacker) in MOLD_BREAKING_ABILITIES


def sky_never_misses(move_name, weather):
    """
    Whether the sky lets this move skip its accuracy check altogether.

    Not the same as "100% accurate". The check is not MADE, so an evasion boost, a
    lowered accuracy stage and a Sand Veil are all bypassed with it - which is why the
    caller returns rather than setting the figure to 100 and carrying on.
    """
    return weather in WEATHER_ACCURACY_MOVES.get(move_name, {}).get('perfect', ())


def sky_accuracy(move_name, base_accuracy, weather):
    """The figure this move drops to in an unhelpful sky, or the one it came with."""
    dimmed = WEATHER_ACCURACY_MOVES.get(move_name, {}).get('dimmed', {})
    return dimmed.get(weather, base_accuracy)


def personal_weather(attacker, weather):
    """
    The sky as this specimen's OWN move sees it. Block 22's Mega Sol.

    A reading rather than a weather setter: the sky over the battlefield is unchanged,
    and only the moves this specimen throws are answered as though the sun were out.
    Everything downstream - the elemental multipliers, Weather Ball, the solar charge,
    Thunder's accuracy - then follows for free, because every one of them is already
    handed the weather as a string.

    A primordial sky is left alone. Those three are the ones an ordinary weather setter
    is already refused, and a personal reading does not get to do what a setter cannot.
    """
    if weather in UNOVERRIDABLE_SKIES:
        return weather
    # ITEM PHASE 11. The umbrella is read BEFORE the ability, so a Mega Sol carrying one
    # still gets its own sun: the umbrella keeps the SKY off its holder, and a personal
    # sun is not the sky. Everything downstream then follows for free, which is the whole
    # reason this function exists.
    weather = sheltered_weather(attacker, weather)
    if get_active_ability(attacker) in PERSONAL_SUN_ABILITIES:
        return PERSONAL_SUN_WEATHER
    return weather


def sheltered_weather(pokemon, weather, magic_room=False):
    """
    Sun and rain, as a specimen under a Utility Umbrella reads them: not there at all.

    Deliberately built as a READING rather than as a pile of special cases, because
    personal_weather had already proved the shape works - hand one specimen a different
    weather string and the elemental multipliers, Weather Ball, the solar charge, Thunder's
    accuracy and the weather-gated abilities all answer correctly without being told.

    Only the two ORDINARY skies are sheltered. A primordial sky is left alone for exactly
    the reason personal_weather leaves it alone, and the hail and sandstorm chip damage is
    not the umbrella's business either - it is an umbrella, not a tent.
    """
    if get_active_item(pokemon, magic_room) != UTILITY_UMBRELLA:
        return weather
    return 'none' if weather in SHELTERED_SKIES else weather


def battle_bond_form_for(pokemon):
    """
    The form a Battle Bond specimen bursts into on a knockout, or None.

    Asked at the knockout hook, banked as a form-flip request and cashed in by the same
    resolver every other form change uses. Once per battle falls out of the question
    rather than needing a marker: the form it becomes is not the form that asks.
    """
    if pokemon is None or get_active_ability(pokemon) not in BATTLE_BOND_ABILITIES:
        return None
    if (pokemon.get('name') or '').lower() == BATTLE_BOND_FORM:
        return None
    return BATTLE_BOND_FORM


def wears_bonded_form(pokemon):
    """
    Whether this specimen is the bonded form, whose Water Shuriken is the stronger one.

    Keyed on what it IS, not on what it can do. The ability is what causes the change;
    the stronger shuriken belongs to the body the change produced, and reading the
    ability instead handed it to every Greninja that had knocked nothing out.
    """
    return (pokemon or {}).get('name', '').lower() == BATTLE_BOND_FORM


def begin_mould_break(attacker, defender):
    """
    Mark the defender for the length of ONE strike, and return what to put back.

    Scoped rather than standing, because a mould-breaker only breaks moulds with its own
    moves: the defender's Levitate is off while the Mold Breaker's Earthquake is landing
    and on again the instant it has. The previous value is returned rather than assumed
    absent, so a nested calculation could never clear a marker it did not set.
    """
    if defender is None or not breaks_moulds(attacker):
        return None
    volatiles = defender.setdefault('volatile_statuses', {})
    previous = volatiles.get(MOULD_BROKEN_MARKER)
    volatiles[MOULD_BROKEN_MARKER] = True
    return ('restore', previous)


def end_mould_break(defender, token):
    """Undo begin_mould_break. Always reached, because its caller uses a finally."""
    if token is None or defender is None:
        return
    volatiles = defender.get('volatile_statuses') or {}
    _, previous = token
    if previous is None:
        volatiles.pop(MOULD_BROKEN_MARKER, None)
    else:
        volatiles[MOULD_BROKEN_MARKER] = previous


def refresh_neutralizing_gas(*combatants):
    """
    Recompute who is standing in the gas, and return a log line for a change.

    Recomputed from the field rather than toggled on and off, because every way the gas
    can END is a way somebody forgets to toggle it: the gasser switching out, fainting to
    a move, fainting to poison, or being replaced by something that is also a gasser.
    Asking the question again is cheap; remembering to unask it is what goes wrong.

    A fainted gasser holds nothing down - it is not on the field any more.
    """
    live = [c for c in combatants if c is not None and c.get('current_hp', 0) > 0]
    gassers = [c for c in live
               if get_stored_ability(c) in NEUTRALIZING_GAS_ABILITIES
               and not (c.get('volatile_statuses') or {}).get('ability_suppressed')]

    log = ""
    for combatant in combatants:
        if combatant is None:
            continue
        volatiles = combatant.setdefault('volatile_statuses', {})
        # Its own gas never switches itself off.
        gassed = bool(gassers) and not any(g is combatant for g in gassers)
        was = bool(volatiles.get(GAS_SUPPRESSED_MARKER))

        if gassed and not was:
            volatiles[GAS_SUPPRESSED_MARKER] = True
            if get_stored_ability(combatant) not in ('none', ''):
                log += (f"☁️ **{combatant['name'].capitalize()}**'s "
                        f"{pretty_ability(get_stored_ability(combatant))} "
                        f"was smothered by the Neutralizing Gas!\n")
        elif was and not gassed:
            volatiles.pop(GAS_SUPPRESSED_MARKER, None)
            if get_stored_ability(combatant) not in ('none', ''):
                log += (f"💨 The gas cleared, and **{combatant['name'].capitalize()}**'s "
                        f"{pretty_ability(get_stored_ability(combatant))} "
                        f"came back!\n")

    return log


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

# NON_MEGA_ITE_ITEMS held back the Eviolite from a substring test for 'ite'. Phase 8
# gave Mega Stones a real table, so the test - and the exception it needed - are gone.
# See MEGA_STONE_SPECIES in constants.py.

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

# Pay Day and Make It Rain scatter the same way G-Max Gold Rush does, so all three share
# one purse. Make It Rain's Sp. Atk drop already comes off its database row.
COIN_SCATTER_MOVES = {'pay-day', 'make-it-rain'}

# What Metal Burst and Comeuppance hand back, as a share of what they were dealt.
RETALIATION_MULTIPLIER = 1.5


def scatter_coins(attacker, source=None):
    """
    Add this user's coin scatter to its running total. Returns the amount added.

    `source` is the move that shook the money loose. Three different moves fill this one
    purse, so the reward line has to be told which of them actually did it rather than
    naming whichever was implemented first.
    """
    if attacker is None:
        return 0
    coins = max(1, COIN_SCATTER_PER_LEVEL * attacker.get('level', 50))
    attacker['_coins_scattered'] = attacker.get('_coins_scattered', 0) + coins
    if source:
        credited = attacker.setdefault('_coin_sources', [])
        if source not in credited:
            credited.append(source)
    return coins


def collected_coins(team):
    """Everything a team scattered over the course of a battle."""
    return sum((m.get('_coins_scattered') or 0) for m in (team or []) if m)


def coin_sources(team):
    """
    Which moves filled the purse, prettified and in the order they were first used.
    Empty when coins arrived from somewhere that did not say.
    """
    seen = []
    for member in (team or []):
        for source in ((member or {}).get('_coin_sources') or []):
            if source not in seen:
                seen.append(source)
    return [name.replace('-', ' ').title().replace('G Max', 'G-Max') for name in seen]


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
        coins = scatter_coins(attacker, move_name)
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
        # It is no longer dead, so it is no longer mourned. Without this a specimen
        # brought back and knocked out again would be worth nothing to a Soul-Heart.
        member.pop(MOURNED_MARKER, None)
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
    # Magic Bounce is the same reflection as a permanent Magic Coat, so it reuses this
    # predicate entirely rather than growing a parallel one.
    has_coat = (defender.get('volatile_statuses') or {}).get('magic_coat')
    has_bounce = get_active_ability(defender) in MAGIC_BOUNCE_ABILITIES
    if not (has_coat or has_bounce):
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
COPY_MOVES = {'mirror-move', 'copycat', 'me-first', 'assist', 'metronome', 'nature-power'}

# Nothing in the mimicry family can copy another member of it, or Struggle - both would
# either recurse or have nothing behind them to copy. The three families that are not
# ordinary moves are refused here too: base_moves carries all of them by name, so without
# this Copycat could answer a Shadow Rush with a Shadow Rush.
UNCOPYABLE_MOVES = ({
    'assist', 'copycat', 'me-first', 'metronome', 'mimic', 'mirror-move', 'sketch',
    'sleep-talk', 'nature-power', 'struggle', 'transform',
} | set(SHADOW_MOVES) | set(Z_MOVE_SIGNATURES) | set(MAX_MOVE_NAMES))

# Me First rewards going first with half again the power.
ME_FIRST_MULTIPLIER = 1.5

# ==========================================
# ✏️ WHAT SKETCH MAY AND MAY NOT TAKE
# ==========================================
# Sketch's list is NOT the mimicry family's list, and it differs in both directions - so
# it is its own table rather than a flag on can_be_copied.
#
# It may take what the others may not: from Generation III, Sketch copies Mirror Move,
# Sleep Talk and Metronome THEMSELVES rather than whatever they called, and from
# Generation IV it copies Mimic and Transform like any other move.
SKETCHABLE_DESPITE_UNCOPYABLE = frozenset({
    'assist', 'copycat', 'me-first', 'metronome', 'mimic', 'mirror-move',
    'nature-power', 'sleep-talk', 'transform',
})

# And it may not take what the others may. Chatter, Struggle, Sketch itself, the Shadow
# moves and every Z-Move are barred in all generations; Scarlet and Violet 3.0.0 added
# Dark Void, Hyperspace Fury, Revival Blessing, Tera Starstorm and the Starmobiles' five.
# Breakneck Blitz is named there too, despite being unreachable.
#
# Aura Wheel is deliberately NOT here. It reads like it belongs - it sits beside Dark Void
# and Hyperspace Fury on Bulbapedia - but that passage is about moves that cannot be USED
# once sketched, not moves that cannot be sketched.
SKETCH_BLOCKED_MOVES = (frozenset({
    'chatter', 'sketch', 'struggle',
    'dark-void', 'hyperspace-fury', 'revival-blessing', 'tera-starstorm',
    'breakneck-blitz',
}) | SHADOW_MOVES | Z_MOVE_SIGNATURES | STARMOBILE_MOVES)


def can_be_copied(move_name):
    """Whether the mimicry family is allowed to reach for this move."""
    return bool(move_name) and move_name not in UNCOPYABLE_MOVES


def can_be_sketched(move_name, from_z_move=False):
    """
    Whether Sketch may take this move permanently.

    `from_z_move` is the answer to "was the move the target actually threw a Z-Move?",
    which the NAME cannot answer: a Z-Move keeps its base move's name in the payload, so
    a Smeargle facing a Z-Boosted Volt Tackle sees `volt-tackle` and nothing else. The
    engines carry the provenance forward on the target as LAST_MOVE_WAS_Z.

    A Max Move is a different case and is deliberately allowed: Copycat is documented as
    copying the BASE move a Max Move was built from, the engines already record that base
    name, and nothing bars Sketch from doing the same.
    """
    if not move_name:
        return False
    if from_z_move:
        return False
    if move_name in SKETCH_BLOCKED_MOVES:
        return False
    if move_name in SKETCHABLE_DESPITE_UNCOPYABLE:
        return True
    return move_name not in UNCOPYABLE_MOVES


def resolve_copied_move(move_name, attacker, defender, party=None,
                        last_move_overall=None, pool=None, terrain='none'):
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
      * Nature Power - whatever suits the ground underfoot
    """
    if move_name == 'nature-power':
        # Never fails: bare ground is still ground, and answers with Tri Attack.
        return nature_power_move(terrain), ""

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

    This asks can_be_sketched rather than can_be_copied. The two lists are genuinely
    different - Sketch may take Transform and may not take Chatter, and the mimicry
    family is the other way round - and because a sketch is PERMANENT, a wrong answer
    here writes itself into caught_pokemon and outlives the battle.
    """
    copied = defender.get('last_move_used')
    if not can_be_sketched(copied, defender.get(LAST_MOVE_WAS_Z)):
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


# The exact words a landed critical writes into the damage message, named once so the
# emitter and the reader below cannot drift apart. Deliberately NOT the phrase "critical
# hit": Focus Energy, Laser Focus and Z-Focus Energy all say "critical hit ratio rose",
# and a substring match on that would have counted three criticals for a Farfetch'd that
# had merely psyched itself up three times.
CRIT_STRIKE_MESSAGE = "A critical strike! "


def record_battle_conditions(defender, damage, attacker=None, message=""):
    """
    The two tallies that some evolutions are earned by, kept on the battle payload.

    Galarian Yamask becomes a Runerigus after surviving a single blow of 49 or more, and
    Galarian Farfetch'd becomes a Sirfetch'd after landing three criticals in one battle.
    Both are things this engine has always SEEN and never written down, which is why those
    two evolutions were unreachable however the rules were keyed.

    The hardest hit is a high-water mark that persists between battles - it is the worst
    thing that ever happened to this specimen. The critical tally is per-battle, and the
    battle payload is rebuilt every time, so it resets on its own.

    Read off the damage message rather than a crit flag because the flag is local to the
    damage resolver and never leaves it; the message is what both engines already receive.
    A miss deals no damage and produces no line, so there is nothing to miscount.
    """
    if not defender or damage is None or damage <= 0:
        return

    if damage > (defender.get('biggest_hit_taken') or 0):
        defender['biggest_hit_taken'] = damage

    if attacker is not None and CRIT_STRIKE_MESSAGE.strip() in (message or ''):
        attacker['crits_landed_battle'] = (attacker.get('crits_landed_battle') or 0) + 1


def advance_field_tenure(combatant):
    """
    Count one more turn survived out here - the thing that disarms Fake Out.

    Both engines incremented this unconditionally at the end of the turn, which counted
    the turn a specimen SWITCHED IN. Switching is the trainer's action for that turn, so
    the replacement never got to move; by its first actual turn the counter already read
    1 and Fake Out was refused. leave_field resetting the counter on the way out did not
    help, because the miscount happens on the way in.

    `acted_this_turn` is the discriminator, and it is already maintained for Bolt Beak and
    Fishious Rend: it is set for everything in the action queue BEFORE the move resolves,
    so a flinched or fully-paralysed specimen still counts as having taken its turn, while
    a specimen that arrived mid-turn was never in the queue at all. The comment beside it
    in both engines already says "so a switch-in starts the turn 'not yet acted'".
    """
    if not combatant or combatant.get('current_hp', 0) <= 0:
        return
    if not combatant.get('acted_this_turn'):
        return
    combatant['turns_on_field'] = (combatant.get('turns_on_field') or 0) + 1


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


def trapper_mark(pokemon):
    """Who is doing the holding, as something that survives being copied about."""
    if pokemon is None:
        return True
    return pokemon.get('instance_id') or pokemon.get('name') or True


def apply_trap(pokemon, trapper=None):
    """
    Pin a specimen in place. Returns whether it actually took hold.

    **THE TRAP BELONGS TO WHOEVER SET IT.** "Prevents the target from fleeing or
    switching out, AS LONG AS THE USER REMAINS IN BATTLE" is the whole of Thousand Waves,
    and of Mean Look, Block and Spider Web before it - and the flag was a bare True, so a
    trapper that walked away left its victim pinned by nobody for the rest of the battle.

    Recorded rather than released on the way out, because `leave_field` is called from ten
    places and knows only the specimen that is leaving. `is_trapped` already takes the
    opponent, so the question "is the one who caught you still standing there" can be
    answered where it is asked instead.
    """
    if not can_be_trapped(pokemon):
        return False
    pokemon.setdefault('volatile_statuses', {})['hard_trapped'] = trapper_mark(trapper)
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

    # ITEM PHASE 3: Shed Shell walks out of anything that is HOLDING it - Mean Look, a
    # Wrap, Shadow Tag, Arena Trap. Placed after Fairy Lock and beside the Ghost
    # exemption on purpose: Fairy Lock pins the whole field rather than targeting
    # anybody, and the games do not let a Shed Shell out of it either.
    #
    # "Multi-turn moves still cannot be switched out of" in the item's description is
    # about the holder's OWN locked-in move - Outrage, a charge turn - which this
    # function has never answered. That lives with the move lock, so the caveat is
    # satisfied by where the check is rather than by a clause here.
    if get_active_item(pokemon) == SHED_SHELL:
        return False

    if not can_be_trapped(pokemon):
        return False

    if volatiles.get('partially_trapped', 0) > 0:
        return True

    # A HARD TRAP LASTS ONLY WHILE ITS SETTER IS STILL THERE. The stored value names the
    # specimen that set it, so a Mean Look whose owner has since been withdrawn stops
    # holding anybody. `True` is the old shape, kept meaningful: a trap with no owner
    # recorded holds unconditionally, which is what every trap did before this.
    held_by = volatiles.get('hard_trapped')
    if held_by:
        if held_by is True or opponent is None:
            return True
        if trapper_mark(opponent) == held_by:
            return True

    # What the specimen OPPOSITE is holding it with. Shadow Tag holds everything; Arena
    # Trap only reaches what is standing on the ground, and Magnet Pull only Steel - so
    # the table says what each one can catch rather than adding a branch per ability.
    if opponent is not None:
        catches = get_active_ability(opponent)
        if catches in TRAPPING_ABILITIES:
            reach = TRAPPING_ABILITIES[catches]
            if reach is None:
                return True
            if reach == 'grounded':
                return is_grounded(pokemon)
            return reach in (pokemon.get('types') or [])

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

# Reckless boosts these two despite their carrying no recoil in the database: they hurt
# their user only on a MISS, which the schema has no field for.
CRASH_MOVES = {'jump-kick', 'high-jump-kick'}

# Typings that refuse a condition outright. The contact abilities used to carry a single
# 'immune' type each, which meant Poison Point could poison a Steel type - the immunity
# filter that knows better runs on `inflicted_status`, and a contact ability writes the
# status slot directly, going around it.
STATUS_TYPE_IMMUNITY = {
    'paralysis': {'electric'},
    'burn':      {'fire'},
    'poison':    {'poison', 'steel'},
    'freeze':    {'ice'},
}


def status_type_immune(status, types, attacker=None):
    """
    True when the target's typing refuses the condition outright.

    Corrosion is the exception the games carved out: it poisons Poison and Steel types
    that nothing else can touch.
    """
    if (status == 'poison' and attacker is not None
            and get_active_ability(attacker) in CORROSIVE_ABILITIES):
        return False
    return bool(STATUS_TYPE_IMMUNITY.get(status, set()) & set(types or []))


def normalise_move_name(move_name):
    """Move names reach here as both 'Rain Dance' and 'rain-dance' depending on the path."""
    return str(move_name or '').lower().replace(' ', '-')


def is_sound_move(move_name):
    """Sound-based, for Punk Rock, Soundproof and the Substitute bypass."""
    return normalise_move_name(move_name) in SOUND_MOVES


def is_slicing_move(move_name):
    """Blade-shaped, for Sharpness. Listed rather than guessed from the name."""
    return normalise_move_name(move_name) in SLICING_MOVES


def is_recoil_move(move_name, move=None):
    """
    True for moves that hurt their own user when they land.

    Recoil is stored as a NEGATIVE drain percentage, which is already how the engine
    applies it, so there is no separate list to drift out of date. Struggle is excluded:
    its recoil is a fixed fraction applied by the engine, and Reckless does not boost it.
    """
    name = normalise_move_name(move_name)
    if name == 'struggle':
        return False
    if name in CRASH_MOVES:
        return True
    return ((move or {}).get('drain') or 0) < 0


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


# The Life Orb bills the holder a tenth of its maximum HP for every hit that lands.
# A divisor rather than a fraction because that is how the games state it, and how the
# rest of the fixed-fraction recoil in this file is written.
LIFE_ORB_RECOIL_DIVISOR = 10


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


# ==========================================
# 🃏 LAST RESORT
# ==========================================
# 140 base power, physical, and 266 species can learn it. Nothing gated it, so it was
# simply the strongest Normal move in the game with no cost attached.
LAST_RESORT = 'last-resort'

# The key a specimen's used-move set lives under. A set, not a list: the question is
# only ever "has this been used", never how often or in what order.
MOVES_USED_KEY = 'moves_used_this_battle'


def record_move_used(pokemon, move_name):
    """
    Remember that this specimen has used this move during this battle.

    Called from the same two places that set `last_move_used`, which is the point a move
    has actually RESOLVED - recording at selection instead would let a move that was
    flinched or fully paralysed away count toward Last Resort.

    The set is cleared on switch-out by `reset_stat_stages`, because Last Resort's
    condition is per-appearance in the games: a specimen that comes back in has to earn
    it again.
    """
    if pokemon is None or not move_name:
        return
    used = pokemon.get(MOVES_USED_KEY)
    if not isinstance(used, set):
        used = set(used or ())
    used.add(move_name)
    pokemon[MOVES_USED_KEY] = used


def last_resort_ready(pokemon, opponent=None):
    """
    Whether Last Resort may be used right now, and why not if it may not.

    Returns (ready, reason). Two doors, and the second is the wider one:

    * the games' rule - every OTHER move the specimen knows has been used at least once
      since it came in; and
    * it is genuinely the only move left to pick, which is what "a last resort" means in
      plain English and is the rule this was asked for. The games actually FAIL a lone
      Last Resort; refusing to let a specimen act at all is a worse outcome than
      diverging here, and a specimen with nothing else usable would otherwise be pushed
      into Struggle while holding a 140-power attack.
    """
    others = [m for m in (pokemon.get('moves') or [])
              if m.get('name') and m.get('name') != LAST_RESORT]

    # Knows nothing else at all.
    if not others:
        return True, None

    # Nothing else is pickable - out of PP, disabled, taunted, sealed. Checking the
    # other moves cannot recurse: this branch is only reached for Last Resort itself,
    # and none of `others` is named that.
    still_open = [m for m in others
                  if m.get('pp', 0) > 0
                  and move_is_restricted(pokemon, m, opponent) is None]
    if not still_open:
        return True, None

    used = pokemon.get(MOVES_USED_KEY) or set()
    missing = [m['name'] for m in others if m['name'] not in used]
    if not missing:
        return True, None

    pretty = ", ".join(n.replace('-', ' ').title() for n in missing[:3])
    if len(missing) > 3:
        pretty += f" +{len(missing) - 3} more"
    return False, f"needs {pretty} used first"


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

    # Last. Everything above can rule the move out on its own, and this branch walks the
    # specimen's OTHER moves - so it wants the cheap disqualifications settled first.
    #
    # Put here rather than at either engine's move handler because this one function
    # already drives all three consumers: the player's move buttons (which grey out and
    # explain), the NPC's `usable_moves` filter, and the "but it failed" path. Gating it
    # in the engines would have meant two copies and would have missed the button.
    if name == LAST_RESORT:
        ready, reason = last_resort_ready(pokemon, opponent)
        if not ready:
            return reason

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

    Block 19's Klutz is a third suppressor of exactly that shape, which is why it is a
    clause here rather than a check at the forty-odd places an item is read.
    """
    if pokemon is None:
        return 'none'
    if magic_room:
        return 'none'
    if (pokemon.get('volatile_statuses') or {}).get('embargo'):
        return 'none'
    if get_active_ability(pokemon) in CLUMSY_ABILITIES:
        return 'none'
    return get_stored_item(pokemon)


def item_is_stuck(pokemon):
    """
    Sticky Hold: whether another specimen is allowed to take this item away.

    Read off the ACTIVE ability, so a Gastro Acid frees the item the same turn it lands.
    Deliberately says nothing about what the holder itself does with the item - see the
    note beside STICKY_HOLD_ABILITIES for where the line falls.

    Block 20 adds Multitype and RKS System to the same question rather than standing up a
    second one. Their Plate or Memory is not equipment, it is what the specimen currently
    IS, and the games have never let a Knock Off take it.
    """
    return get_active_ability(pokemon) in (STICKY_HOLD_ABILITIES | ITEM_WELDED_ABILITIES)


def harvest_regrows(pokemon, weather='none'):
    """
    The berry Harvest grows back this turn, or None.

    Three conditions, and all three are the ability's own text rather than convenience:
    the hands must be empty ("has held no items in the meantime"), there must be a berry
    it ate to grow back, and the roll must come up - which it always does in the sun.
    """
    if pokemon is None or pokemon.get('current_hp', 0) <= 0:
        return None
    if get_active_ability(pokemon) not in HARVEST_ABILITIES:
        return None
    if get_stored_item(pokemon) != 'none':
        return None

    berry = pokemon.get(LAST_BERRY_MARKER)
    if not berry or not is_berry(berry):
        return None

    chance = HARVEST_SUN_CHANCE if weather in HARVEST_SUN else HARVEST_CHANCE
    return berry if random.random() < chance else None


def cud_chew_due(pokemon):
    """
    Advance the Cud Chew clock by one turn and return the berry that has come back up,
    or None.

    Mutating and asking in one call is deliberate: two callers that could disagree about
    whether the clock had already been wound is exactly how the Truant marker nearly went
    wrong. There is one clock, and asking it is what turns it.
    """
    if pokemon is None:
        return None

    pending = pokemon.get(CUD_CHEW_MARKER)
    if not pending:
        return None

    berry, turns = pending[0], pending[1] - 1
    if turns > 0:
        pokemon[CUD_CHEW_MARKER] = [berry, turns]
        return None

    pokemon.pop(CUD_CHEW_MARKER, None)
    # A corpse chews nothing, but the clock still had to be wound - otherwise a specimen
    # that fainted and was revived would come back holding a stale countdown.
    if pokemon.get('current_hp', 0) <= 0:
        return None
    return berry


def pickup_finds(taker, dropper):
    """
    What Pickup lifts off the floor this turn, or None.

    Empty hands only, and only something the specimen opposite SPENT rather than had
    destroyed - see the by_owner note on mark_item_consumed. Reading the foe's marker
    rather than the field is what keeps it from recovering its own used berry.
    """
    if taker is None or dropper is None or taker is dropper:
        return None
    if taker.get('current_hp', 0) <= 0:
        return None
    if get_active_ability(taker) not in PICKUP_ABILITIES:
        return None
    if get_stored_item(taker) != 'none':
        return None

    dropped = dropper.get(ITEM_SPENT_MARKER)
    return dropped if dropped and dropped != 'none' else None


def clear_spent_item_markers(*combatants):
    """
    Wipe the "used something up this turn" note once Pickup has had its look.

    Left set, a single eaten berry would be picked up again every turn for the rest of
    the battle - which is the same shape of bug as the pivot flags PvP never flushed.
    """
    for combatant in combatants:
        if combatant is not None:
            combatant.pop(ITEM_SPENT_MARKER, None)


def is_transferable_item(item):
    """
    Whether an item can be moved off its holder by Trick, Bestow, Knock Off, Thief,
    Fling, Incinerate or Corrosive Gas.

    Centralises a guard that was copy-pasted at three sites in the damage formula. The
    old inline version tested `endswith('ite')`, which silently missed the split Mega
    Stones - 'charizardite-x' does not end in 'ite', so it could be knocked off.

    Phase 8 replaced the spelling tests with the tables themselves, and doing so closed
    a gap the spellings left between them: the three Z-suffixed Mega Stones - Absolite Z,
    Garchompite Z and Lucarionite Z - ended in neither 'ite' nor 'ium-z', so each one
    fell through both tests and could be Knocked Off. It also retires the
    NON_MEGA_ITE_ITEMS exception, which existed only to hold back the Eviolite and would
    have needed a new row for every future item spelled that way.
    """
    item = (item or 'none').lower().replace(' ', '-')

    if item in ('none', '') or item in UNTRANSFERABLE_ITEMS:
        return False
    if item in Z_CRYSTAL_TYPES or item in SIGNATURE_Z_CRYSTALS:
        return False
    if item in MEGA_STONE_SPECIES:
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
    ADRENALINE_ORB,     # ITEM PHASE 10 - spent the moment it answers an Intimidate
    'focus-sash', 'power-herb', 'white-herb', 'mental-herb', 'air-balloon',
    'absorb-bulb', 'cell-battery', 'luminous-moss', 'snowball', 'weakness-policy',
    'blunder-policy', 'throat-spray', 'eject-button', 'eject-pack', 'red-card',
    'room-service', 'electric-seed', 'grassy-seed', 'misty-seed', 'psychic-seed',
}


def is_consumable(item):
    """Whether an item is used up by its own effect rather than merely being carried."""
    item = (item or '').lower().replace(' ', '-')
    return is_berry(item) or item in ONE_USE_ITEMS


def mark_item_consumed(pokemon, item, by_owner=True):
    """
    Record that a specific held item was USED UP - eaten, triggered or burnt away - as
    opposed to being tricked, bestowed, knocked off or stolen.

    Only a genuine consumption is written back to the database when the battle ends.
    Everything else is battle-scoped, which is what stops Trick and Bestow from
    permanently moving equipment between two players' collections.

    The item NAME is recorded rather than a bare flag, because a specimen can lose its
    own Leftovers to a Trick and then eat a berry it was handed - the Leftovers still has
    to come home.

    `by_owner` is Block 19's Pickup, which recovers what somebody else SPENT and not what
    somebody else DESTROYED. Incinerate, Bug Bite and Pluck are the three routes here
    that use up a berry on the foe's initiative rather than the holder's, and they pass
    False: a berry burnt to a crisp is not lying around to be picked up.
    """
    if pokemon is None:
        return
    item = (item or '').lower().replace(' ', '-')
    if item in ('', 'none'):
        return
    if by_owner:
        pokemon[ITEM_SPENT_MARKER] = item
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


def berry_threshold(pokemon, base):
    """
    The HP fraction a berry actually waits for on THIS specimen.

    Gluttony is a floor rather than a replacement: a pinch berry that would hold out for
    a quarter goes off at a half, and the berries already keyed to a half are untouched.
    """
    if get_active_ability(pokemon) in GLUTTONY_ABILITIES:
        return max(base, GLUTTONY_THRESHOLD)
    return base


def ripened(pokemon, amount):
    """Ripen doubles what a berry is worth. Applied to the figure, not to the berry."""
    if get_active_ability(pokemon) in RIPEN_ABILITIES:
        return amount * RIPEN_MULTIPLIER
    return amount


def cheek_pouch_refill(pokemon, owner_str=""):
    """
    What eating a berry is worth on top of the berry, and a log line for it.

    Answers the EATING rather than the holding, so a berry forced down by Teatime, a
    Fling or a Bug Bite pays exactly the same - which is why it is charged from the one
    place every route to swallowing a berry passes through.
    """
    if get_active_ability(pokemon) not in CHEEK_POUCH_ABILITIES:
        return ""
    max_hp = pokemon.get('max_hp', 100)
    if pokemon.get('current_hp', 0) >= max_hp:
        return ""

    heal = max(1, math.floor(max_hp / CHEEK_POUCH_FRACTION))
    pokemon['current_hp'] = min(max_hp, pokemon['current_hp'] + heal)
    who = f"{owner_str.strip()} " if owner_str else ""
    return (f"🐿️ {who}**{pokemon['name'].capitalize()}**'s Cheek Pouch "
            f"gave it back some HP! (+{heal} HP)\n")


def apply_berry_effect(pokemon, item, ignore_threshold=False, owner_str=""):
    """
    Resolve one berry on one specimen and return a log line, or '' if nothing happened.

    check_consumables uses this with the normal HP/status thresholds; Teatime, Bug Bite,
    Pluck and a flung berry force it through with ignore_threshold, which is what "eats
    the berry regardless" means.

    Cheek Pouch is charged here rather than inside the resolver because a non-empty log
    line is exactly the signal that a berry went down: every branch below that returns
    something has already called eaten(), and every branch that eats returns something.
    """
    note = _resolve_berry(pokemon, item, ignore_threshold, owner_str)
    if note:
        note += cheek_pouch_refill(pokemon, owner_str)
    return note


# ==========================================
# THE MARKERS A PINCH BERRY LEAVES BEHIND
# ==========================================
# Lansat, Micle and Custap buy something that is spent LATER - two crit stages, a fifth
# more accuracy, the front of the priority bracket - so eating one leaves a marker and
# the moment that reads it does the rest.
#
# Micle and Custap are spent on one action and have to expire. That is the same problem
# the two-turn charge has, and it gets the same answer: a marker handed out DURING a turn
# must survive that turn's own end-of-turn sweep, or a berry eaten at a quarter HP would
# be swept away before the move it was bought for. The first sweep clears the freshness;
# the second removes the marker.
#
# Lansat is `lasting` and never expires here. Like Focus Energy it holds until its owner
# leaves the field, and the volatile wipe on withdrawal already does that.

def grant_action_marker(pokemon, marker, lasting=False):
    """Leave a berry's marker on a specimen, to be read by a later moment."""
    if pokemon is None or not marker:
        return
    volatiles = pokemon.setdefault('volatile_statuses', {})
    volatiles[marker] = True
    if not lasting:
        volatiles[marker + ACTION_MARKER_FRESH] = True


def has_action_marker(pokemon, marker):
    """Whether this specimen is carrying `marker`."""
    if pokemon is None:
        return False
    return bool((pokemon.get('volatile_statuses') or {}).get(marker))


def expire_action_markers(pokemon):
    """
    End-of-turn housekeeping for the markers that are spent on a single action.

    A marker still marked fresh was handed out this turn and keeps its shot. One that is
    not was available for a whole turn, taken or not, and goes.
    """
    if pokemon is None:
        return
    volatiles = pokemon.get('volatile_statuses') or {}
    for marker in (MICLE_MARKER, CUSTAP_MARKER):
        if not volatiles.get(marker):
            continue
        if volatiles.pop(marker + ACTION_MARKER_FRESH, None):
            continue
        volatiles.pop(marker, None)


def swallow_berry(pokemon, item):
    """
    The bookkeeping of a berry going down, for every route that eats one.

    Extracted from _resolve_berry when Item Phase 7 added the five berries that answer a
    HIT rather than a threshold. Those five never reach the threshold sweep, and a second
    hand-written copy of this would have been a second place to forget Harvest.

    Only empties the slot when the berry actually came off THIS specimen. Bug Bite,
    Pluck and a flung berry feed someone else's berry to the eater, and must not take the
    eater's own item with it.
    """
    if pokemon is None:
        return
    item = (item or '').lower().replace(' ', '-')

    if get_stored_item(pokemon) == item:
        pokemon['held_item'] = 'none'
        mark_item_consumed(pokemon, item)
        # Block 19. Both of these answer for a berry that came out of this specimen's
        # OWN slot, which is also what stops the second helping arming a third: by the
        # time Cud Chew re-eats, the slot is already empty.
        pokemon[LAST_BERRY_MARKER] = item
        if get_active_ability(pokemon) in CUD_CHEW_ABILITIES:
            pokemon[CUD_CHEW_MARKER] = [item, CUD_CHEW_DELAY]

    # Belch needs to know this happened, and it has to outlive a switch, so it lives on
    # the specimen rather than in the volatiles that get wiped on withdrawal.
    pokemon['_ate_berry'] = True


def _resolve_berry(pokemon, item, ignore_threshold=False, owner_str=""):
    """The berry itself. Wrapped by apply_berry_effect, which pays Cheek Pouch after."""
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
        swallow_berry(pokemon, item)

    if behavior == 'heal_flat' and (ignore_threshold or hp_pct <= berry_threshold(pokemon, data.get('threshold', 0.5))):
        if not ignore_threshold or current_hp < max_hp:
            heal_amt = ripened(pokemon, data.get('value', 10))
            pokemon['current_hp'] = min(max_hp, current_hp + heal_amt)
            eaten()
            return f"{data.get('icon', '🫐')} {who}**{name}** consumed its {label}! (+{heal_amt} HP)\n"

    elif behavior == 'heal_pct' and (ignore_threshold or hp_pct <= berry_threshold(pokemon, data.get('threshold', 0.5))):
        if not ignore_threshold or current_hp < max_hp:
            heal_amt = max(1, math.floor(max_hp * ripened(pokemon, data.get('value', 0.25))))
            pokemon['current_hp'] = min(max_hp, current_hp + heal_amt)
            eaten()
            return f"{data.get('icon', '🍋')} {who}**{name}** consumed its {label}! (+{heal_amt} HP)\n"

    elif behavior == 'cure_status' and pokemon.get('status_condition'):
        status_name = pokemon['status_condition']['name']
        if data.get('target') in ('all', status_name):
            pokemon['status_condition'] = None
            eaten()
            return f"{data.get('icon', '🌿')} {who}**{name}** consumed its {label} and cured its {status_name}!\n"

    elif behavior == 'stat_boost' and (ignore_threshold or hp_pct <= berry_threshold(pokemon, data.get('threshold', 0.25))):
        stat_target = data.get('stat', 'attack')
        boost_val = ripened(pokemon, data.get('value', 1))
        if 'stat_stages' not in pokemon:
            pokemon['stat_stages'] = {stat: 0 for stat in ALL_STAT_STAGES}

        if pokemon['stat_stages'].get(stat_target, 0) < 6:
            pokemon['stat_stages'][stat_target] = min(6, pokemon['stat_stages'].get(stat_target, 0) + boost_val)
            eaten()
            return (f"{data.get('icon', '🔴')} {who}**{name}** consumed its {label}! "
                    f"Its {stat_target.replace('_', ' ').title()} rose!\n")

    elif behavior == 'random_boost' and (ignore_threshold or hp_pct <= berry_threshold(pokemon, data.get('threshold', 0.25))):
        # The Starf Berry. Rolled here rather than chosen, and rolled from the stats that
        # are already at their ceiling as well - a berry that quietly re-rolled until it
        # found room would be a different, much better berry than the one described.
        stat_target = random.choice(STARF_STATS)
        boost_val = ripened(pokemon, data.get('value', 2))
        if 'stat_stages' not in pokemon:
            pokemon['stat_stages'] = {stat: 0 for stat in ALL_STAT_STAGES}

        if pokemon['stat_stages'].get(stat_target, 0) < 6:
            pokemon['stat_stages'][stat_target] = min(
                6, pokemon['stat_stages'].get(stat_target, 0) + boost_val)
            eaten()
            return (f"{data.get('icon', '\U0001f31f')} {who}**{name}** consumed its "
                    f"{label}! Its {stat_target.replace('_', ' ').title()} rose "
                    f"sharply!\n")

    elif behavior == 'volatile_boost' and (ignore_threshold or hp_pct <= berry_threshold(pokemon, data.get('threshold', 0.25))):
        # Lansat, Micle and Custap. What they buy is spent on a LATER moment - the crit
        # stage, the accuracy roll, the turn order - so the berry leaves a marker behind
        # rather than changing anything now.
        marker = data.get('volatile')
        if marker and not (pokemon.get('volatile_statuses') or {}).get(marker):
            grant_action_marker(pokemon, marker, lasting=data.get('lasting', False))
            eaten()
            return (f"{data.get('icon', '\U0001f349')} {who}**{name}** consumed its "
                    f"{label}!\n")

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

    The Last Resort tally goes with them, and for the same reason: the games count moves
    used since the specimen ENTERED, so a switch out and back in makes it earn the move
    again. Leaving the set behind would have turned a pivot into a way to bank the
    condition and bring it back ready.
    """
    if pokemon is None:
        return
    pokemon['stat_stages'] = {stat: 0 for stat in ALL_STAT_STAGES}
    pokemon.pop(MOVES_USED_KEY, None)

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
    """
    Everything that comes off a specimen when it is withdrawn.

    Returns a log line for the things that are worth announcing - Natural Cure and
    Regenerator - or "" for the ordinary case. Callers that have no log to write to can
    keep ignoring the return value; the healing happens either way.
    """
    note = ""
    if pokemon is not None:
        # Coming back in counts as arriving fresh, which is what re-arms Fake Out
        pokemon['turns_on_field'] = 0
        # Infatuation is an attachment to the specimen that was standing opposite, so it
        # cannot survive either of them leaving.
        (pokemon.get('volatile_statuses') or {}).pop('infatuation', None)
        # ...and so is having already bailed out. Re-entering re-arms Wimp Out, and
        # Berserk and Anger Shell for the same reason: both answer HP CROSSING the
        # line rather than sitting under it.
        pokemon.pop(BAIL_OUT_MARKER, None)
        pokemon.pop(HP_THRESHOLD_MARKER, None)
        # A parked ejection dies with the departure it was asking for. Left set, a
        # specimen that walked off for any other reason would be asked to leave AGAIN
        # the moment it came back in, on the strength of a button it no longer holds.
        pokemon.pop(PIVOT_REQUEST, None)
        # Truant starts afresh: whatever it was owed, it acts on the turn it
        # arrives back. Left set, a Slaking could bank its loafing on the bench.
        pokemon.pop(TRUANT_MARKER, None)
        # A half-chewed cud does not survive the walk to the bench, and neither does
        # "used something up this turn" - the turn it referred to is over for this
        # specimen. Harvest's memory of WHICH berry deliberately does survive: the
        # ability asks whether the hands are empty, not how long they have been.
        pokemon.pop(CUD_CHEW_MARKER, None)
        pokemon.pop(ITEM_SPENT_MARKER, None)
        # Block 20. The disguise and the Plate type are both borrowed identities, and
        # neither may follow the specimen back to the roster - a Zoroark filed under
        # somebody else's name would be a lasting corruption rather than a battle effect.
        # Both are re-established on the way back in by the entry hook.
        drop_illusion(pokemon)
        restore_own_types(pokemon)
        # Palafin transforms on the way OUT, and comes back a hero. Requested here
        # rather than done here for the usual reason: this function is synchronous
        # and the species tables are not.
        _hero = hero_form_for(pokemon)
        if _hero:
            pokemon[ZERO_TO_HERO_MARKER] = True
            request_form_flip(pokemon, _hero, 'burst into its Hero Form')
        note = collect_switch_out_perks(pokemon)
    reset_stat_stages(pokemon)
    # Undone before the stat/ability restores, so those put back the specimen's OWN
    # figures rather than the borrowed ones it was wearing.
    restore_pre_transform(pokemon)
    restore_base_stats(pokemon)
    restore_base_ability(pokemon)
    end_charge(pokemon)
    return note


def collect_switch_out_perks(pokemon):
    """
    Natural Cure and Regenerator, paid at the door on the way out.

    A fainted specimen collects neither. It is not switching out - it is gone - and
    letting Regenerator heal a corpse would quietly resurrect it, since the engines read
    current_hp to decide whether a replacement is even needed.
    """
    if (pokemon.get('current_hp') or 0) <= 0:
        return ""

    note = ""
    ability = get_active_ability(pokemon)
    name = pokemon.get('name', 'it').capitalize()

    if ability in SWITCH_OUT_CURE_ABILITIES:
        condition = (pokemon.get('status_condition') or {}).get('name')
        if condition and condition != 'none':
            pokemon['status_condition'] = None
            note += (f"💫 **{name}**'s Natural Cure shed its {condition} "
                     f"as it withdrew!\n")

    fraction = SWITCH_OUT_HEAL_FRACTION.get(ability)
    if fraction:
        ceiling = pokemon.get('max_hp', 1)
        healed = min(ceiling, pokemon['current_hp'] + math.floor(ceiling * fraction))
        if healed > pokemon['current_hp']:
            pokemon['current_hp'] = healed
            note += f"💚 **{name}**'s Regenerator knitted it back together!\n"

    return note


def resists_forced_switch(pokemon):
    """Suction Cups and Guard Dog: Whirlwind and Roar cannot move these."""
    return get_active_ability(pokemon) in FORCED_SWITCH_IMMUNE_ABILITIES


def intimidate_reversal(pokemon):
    """Guard Dog's answer to Intimidate: (stat, stages), or None. It gains rather than loses."""
    return INTIMIDATE_REVERSING_ABILITIES.get(get_active_ability(pokemon))


def wants_to_bail_out(pokemon):
    """
    Wimp Out and Emergency Exit: hurt past half, still standing, and not already gone.

    The marker is what makes this fire on the way DOWN rather than every turn it spends
    below half, and leave_field clears it so coming back in re-arms the ability.
    """
    if not pokemon or get_active_ability(pokemon) not in BAIL_OUT_ABILITIES:
        return False
    if pokemon.get(BAIL_OUT_MARKER):
        return False

    ceiling = max(1, pokemon.get('max_hp', 1))
    standing = pokemon.get('current_hp', 0)
    return 0 < standing < ceiling * BAIL_OUT_THRESHOLD


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

def get_effective_priority(move_name, base_priority, attacker, terrain='none', move=None):
    """
    The priority bracket a move actually moves in, after terrain and abilities.

    Grassy Glide jumps a bracket on Grassy Terrain, but only while the user is touching
    the ground. Gale Wings lifts Flying moves, but only while its owner is untouched.
    Triage lifts anything that heals - read off the move's own healing and drain figures
    rather than a list, so it cannot fall behind the database.
    """
    priority = int(base_priority or 0)

    shift = TERRAIN_PRIORITY_MOVES.get((move_name or '').lower().replace(' ', '-'))
    if shift and terrain == shift[0] and is_grounded(attacker):
        priority += shift[1]

    ability = get_active_ability(attacker)
    payload = move or {}

    if ability == 'gale-wings' and payload.get('type') == 'flying':
        at_full = (attacker or {}).get('current_hp', 0) >= (attacker or {}).get('max_hp', 1)
        if at_full or not GALE_WINGS_REQUIRES_FULL_HP:
            priority += 1

    if ability == 'triage' and ((payload.get('healing') or 0) > 0
                                or (payload.get('drain') or 0) > 0):
        priority += TRIAGE_PRIORITY

    # Prankster lifts a status move by one. Whether the boost then costs it the move
    # against a Dark type is a separate question, asked at the target - see
    # prankster_is_snubbed, which has the defender that this function does not.
    if ability in PRANKSTER_ABILITIES and payload.get('class') == 'status':
        priority += PRANKSTER_PRIORITY

    return priority


def prankster_is_snubbed(attacker, defender, move):
    """
    Whether a Prankster-boosted status move simply fails, which it does against Dark.

    Only moves that actually TOOK the boost are refused, so a Prankster's damaging moves
    and its self-aimed status moves both land as normal.
    """
    if get_active_ability(attacker) not in PRANKSTER_ABILITIES:
        return False
    if (move or {}).get('class') != 'status':
        return False
    if 'user' in str((move or {}).get('target') or ''):
        return False
    return PRANKSTER_BLOCKED_BY in ((defender or {}).get('types') or [])


def priority_tier(attacker, move=None, magic_room=False):
    """
    Where inside its bracket this action sits. Higher goes first, 0 is ordinary.

    Two brackets is enough for everything here: Quick Draw jumps to the front, Stall and
    Mycelium Might drop to the back. Speed only breaks ties within the same tier, which
    is what makes Stall lose to a slower opponent rather than merely to a faster one.

    ITEM PHASE 4 adds Quick Claw, Lagging Tail and Full Incense to the same two brackets.
    A specimen holding one AND carrying an opinionated ability is the only interesting
    case, and it is settled by taking the more extreme of the two: a Lagging Tail on a
    Quick Draw dawdles, because being nailed to the back of the bracket is a certainty
    and the claw is only ever a chance. That is a ruling rather than a fact - the games
    do not let this pair happen often enough to be sure - so it is stated here and
    asserted in the suite rather than left to whichever branch happened to run first.
    """
    ability = get_active_ability(attacker)
    from_item = item_priority_tier(attacker, magic_room)

    scope = LAST_IN_BRACKET_ABILITIES.get(ability)
    if scope == '*' or (scope == 'status' and (move or {}).get('class') == 'status'):
        return -1
    if from_item == -1:
        return -1

    # A Custap Berry, which is the only CERTAINTY in this bracket - Quick Draw and the
    # Quick Claw are both chances. It is asked after the two last-in-bracket rulings
    # above and before them, so a specimen that has been nailed to the back of the
    # bracket stays there: the berry buys the front of a bracket, not an exemption from
    # being sent to the back of one.
    if has_action_marker(attacker, CUSTAP_MARKER):
        return CUSTAP_TIER

    if ability == 'quick-draw' and random.randint(1, 100) <= QUICK_DRAW_CHANCE:
        return 1

    return from_item


def turn_order_key(priority, tier, speed, trick_room=False):
    """
    The sort key both engines order a turn by - higher resolves first.

    Trick Room inverts the SPEED component only: it has never reordered priority
    brackets, and folding it in here is what stops the two engines disagreeing about
    that. PvE used to compute a trick_room flag and then never consult it.
    """
    return (priority, tier, -speed if trick_room else speed)


def blocks_priority_moves(defender):
    """True when this specimen refuses to be hit by anything with raised priority."""
    return get_active_ability(defender) in PRIORITY_BLOCKING_ABILITIES


def is_dance_move(move_name):
    """Dance moves, for Dancer. Rain Dance is not one of them."""
    return normalise_move_name(move_name) in DANCE_MOVES


def refuses_status(defender, status, weather='none'):
    """
    Whether the target's ability refuses this condition outright.

    Every condition on a row is optional and they AND together, so Leaf Guard only holds
    while the sun is out and Flower Veil only while its owner is a Grass type.
    """
    if not status or status == 'none':
        return False

    trait = STATUS_IMMUNE_ABILITIES.get(get_active_ability(defender))
    if not trait:
        return False

    statuses = trait['statuses']
    if statuses != ALL_STATUSES and status not in statuses:
        return False

    if 'weather' in trait and weather not in trait['weather']:
        return False
    if 'self_type' in trait and trait['self_type'] not in (defender.get('types') or []):
        return False

    return True


def refuses_volatile(defender, volatile):
    """Whether the target's ability refuses this volatile. Inner Focus and flinching."""
    return volatile in VOLATILE_IMMUNE_ABILITIES.get(get_active_ability(defender), ())


def move_family(move_name):
    """Which shut-out family this move belongs to, if any."""
    name = normalise_move_name(move_name)
    if name in SOUND_MOVES:
        return 'sound'
    if name in BULLET_MOVES:
        return 'bullet'
    if name in POWDER_MOVES:
        return 'powder'
    return None


def move_family_blocked(defender, move_name):
    """
    The ability shutting this move out by its family, or None.

    Soundproof, Bulletproof and Overcoat. Returned as a name rather than a boolean so the
    log can say which one answered.
    """
    family = move_family(move_name)
    if not family:
        return None
    # ITEM PHASE 5: Safety Goggles refuses powder exactly as Overcoat does. Returned as
    # the ITEM's name, which is what makes the log say what actually answered - the
    # caller only ever prints whatever came back from here.
    if refuses_powder(defender, move_name):
        return 'safety-goggles'
    ability = get_active_ability(defender)
    return ability if MOVE_FAMILY_IMMUNE_ABILITIES.get(ability) == family else None


def refuses_status_moves(defender):
    """Good as Gold: a whole category of move simply does not apply."""
    return get_active_ability(defender) in STATUS_MOVE_IMMUNE_ABILITIES


def smothers_explosion(attacker, defender):
    """
    Damp, on either side of the field.

    Checked against BOTH combatants because Damp stops the move being used at all, not
    merely stops it landing - the user does not even hurt itself.
    """
    for specimen in (attacker, defender):
        if get_active_ability(specimen) in EXPLOSION_BLOCKING_ABILITIES:
            return specimen
    return None


def is_explosive_move(move_name):
    """Explosion and its family, for Damp."""
    return normalise_move_name(move_name) in EXPLOSIVE_MOVES


# ==========================================
# 🛡️ BLOCK 8: STAT-STAGE PROTECTION AND RETALIATION
# ==========================================
# Four small predicates rather than one big one, because the engines ask three different
# questions of the same event and the answers do not compose: Mirror Armor both refuses a
# drop and returns it, while Clear Body only refuses it.

def refuses_stat_drop(target, stat):
    """
    Whether this specimen's ability forbids ANOTHER specimen lowering `stat`.

    Never consulted for a specimen's own drops - the callers screen those out first,
    because Clear Body has never stopped Close Combat costing its owner Defense.
    """
    # ITEM PHASE 5: a Clear Amulet refuses every stat, which is Clear Body's own row -
    # answered before the ability so a specimen holding one is covered whatever it has.
    if get_active_item(target) in STAT_DROP_IMMUNE_ITEMS:
        return True

    ability = get_active_ability(target)
    guarded = STAT_DROP_IMMUNE_ABILITIES.get(ability)
    if guarded is None:
        return False

    required_type = STAT_DROP_IMMUNE_TYPE_GATE.get(ability)
    if required_type and required_type not in (target.get('types') or []):
        return False

    return guarded == ALL_STATS or stat in guarded


def reflects_stat_drop(target):
    """Mirror Armor: the drop goes back to whoever threw it instead of landing."""
    return get_active_ability(target) in STAT_DROP_REFLECTING_ABILITIES


def stat_drop_retaliation(target):
    """
    What this specimen does about having lost a stage: (stat, stages), or None.

    Defiant and Competitive answer per stat lowered, not per move, so Parting Shot -
    which takes two stages off two different stats - wakes them up twice.
    """
    return STAT_DROP_RETALIATION_ABILITIES.get(get_active_ability(target))


def shrugs_off_intimidate(target):
    """Gen 8 gave four abilities a flat refusal of Intimidate, and only Intimidate."""
    return get_active_ability(target) in INTIMIDATE_IMMUNE_ABILITIES


# ==========================================
# 🪨 BLOCK 9: DAMAGE REDUCTION AND SURVIVAL
# ==========================================

def aura_multiplier(move_type, attacker, defender):
    """
    Dark Aura and Fairy Aura, read off BOTH sides of the field.

    An aura is a property of the battlefield rather than of one combatant: whoever is
    carrying it, the element it names is strengthened for everybody. Aura Break inverts
    it rather than cancelling it, and does nothing when there is no aura to invert.

    Two auras of the same element do not stack - one Dark Aura and a second Dark Aura
    still leave the field boosted once, which is what the flag rather than a running
    product gets right here.
    """
    if not any(AURA_ABILITIES.get(get_active_ability(s)) == move_type
               for s in (attacker, defender)):
        return 1.0

    broken = any(get_active_ability(s) in AURA_BREAK_ABILITIES
                 for s in (attacker, defender))
    return AURA_BREAK_MULTIPLIER if broken else AURA_MULTIPLIER


def tera_shell_multiplier(defender, move_class, type_multiplier, ability=None):
    """
    What the type chart reads as once Tera Shell has had its say, at full HP.

    Returns the multiplier unchanged when the shell does not apply. A genuine immunity
    survives it - the shell resists attacks, it does not invent a weakness to them.

    `ability` lets the caller hand in the ability the rest of the formula is working
    with, so a G-Max move that ignores the target's ability ignores this one too.
    """
    if (ability if ability is not None else get_active_ability(defender)) \
            not in TERA_SHELL_ABILITIES:
        return type_multiplier
    if move_class == 'status' or type_multiplier == 0:
        return type_multiplier
    if defender.get('current_hp', 0) < defender.get('max_hp', 1):
        return type_multiplier
    return TERA_SHELL_MULTIPLIER


def resolve_stat_stages(pending, prefix="", foe_of=None):
    """
    Walk a queue of stage changes and move the ones that survive.

    Each entry is (specimen, stat, change, source[, may_reflect[, may_copy]]):

      source      - the specimen responsible, or None when this one did it to itself.
                    Only another specimen's drops are screened at all.
      may_reflect - False once a drop has already been sent back, which is the single
                    thing that stops two Mirror Armors passing one drop between them
                    for ever. A returned drop is still REFUSABLE, so Mirror Armor into
                    Clear Body simply dies, and Mirror Armor into Mirror Armor dies at
                    the second one rather than bouncing again.
      may_copy    - False once a boost has already been copied, for the same reason in
                    the other direction: two Opportunists would otherwise trade one
                    Swords Dance back and forth until the loop guard stopped them.

    `foe_of` answers "who is this specimen facing", and is the only thing that lets a
    change landing on one side be seen by the other. Block 17's Opportunist is its only
    reader; callers that have just one side to hand pass nothing and get no copying,
    which is correct for them.

    Refusals, Mirror Armor's return, the Defiant/Competitive answer and Opportunist's
    copy all resolve here so that every path through both engines gets them for free.
    """
    log = ""
    # Whoever actually LOST a stage. A White Herb answers a drop that landed, so a drop
    # that Clear Body refused or that was already pinned at -6 must not spend one.
    dropped = []
    queue = [(entry + (True, True))[:6] for entry in pending]
    # A hard stop on the queue. Nothing should be able to grow it without bound now that
    # reflections cannot bounce, but a runaway here would hang a battle rather than
    # merely misreport one.
    for _ in range(64):
        if not queue:
            break
        specimen, s_name, chg, source, may_reflect, may_copy = queue.pop(0)
        db_stat = STAT_STAGE_KEYS.get(s_name)
        if not db_stat:
            continue

        name = specimen['name'].capitalize()
        pretty_stat = s_name.replace('-', ' ')

        if chg < 0 and source is not None:
            # Mirror Armor answers before anything else looks at the drop.
            if may_reflect and reflects_stat_drop(specimen):
                log += (f"{prefix}🪞 **{name}**'s Mirror Armor sent the "
                        f"{pretty_stat} drop straight back!\n")
                queue.append((source, s_name, chg, specimen, False, may_copy))
                continue

            if refuses_stat_drop(specimen, s_name):
                shield = get_active_ability(specimen).replace('-', ' ').title()
                log += (f"{prefix}🛡️ **{name}**'s {shield} "
                        f"held its {pretty_stat} steady!\n")
                continue

        if 'stat_stages' not in specimen:
            specimen['stat_stages'] = {'attack': 0, 'defense': 0, 'sp_atk': 0,
                                       'sp_def': 0, 'speed': 0}
        stages = specimen['stat_stages']
        # .get, not [] - accuracy and evasion are absent from a fresh stage block
        before = stages.get(db_stat, 0)
        after = max(-6, min(6, before + chg))

        if after == before:
            # Pinned at the end of the scale. Reported honestly rather than logged as a
            # change that did not happen - and Defiant stays asleep, because nothing was
            # taken from it.
            log += (f"{prefix}↔️ **{name}**'s {pretty_stat} won't go any "
                    f"{'lower' if chg < 0 else 'higher'}!\n")
            continue

        stages[db_stat] = after
        direction = "fell" if chg < 0 else "rose"
        icon = "📉" if chg < 0 else "📈"
        log += f"{prefix}{icon} **{name}**'s {pretty_stat} {direction}!\n"

        if chg < 0:
            # ==========================================
            # LASH OUT TRACKER
            # ==========================================
            specimen.setdefault('volatile_statuses', {})['stats_lowered_this_turn'] = True
            if not any(seen is specimen for seen in dropped):
                dropped.append(specimen)

            # Defiant and Competitive only wake for the OTHER side's doing, and only once
            # the drop has actually landed.
            if source is not None:
                answer = stat_drop_retaliation(specimen)
                if answer:
                    a_stat, a_chg = answer
                    log += (f"{prefix}😤 **{name}**'s "
                            f"{get_active_ability(specimen).replace('-', ' ').title()} "
                            f"flared up!\n")
                    queue.append((specimen, a_stat, a_chg, None, False, may_copy))

        elif may_copy and foe_of is not None:
            # Opportunist watches the other side get stronger and helps itself to the
            # same. Asked AFTER the stage has actually moved, so a boost that was pinned
            # at +6 and did nothing is not worth copying either - and asked here rather
            # than at each of the places a boost is granted, because this is the one
            # place they all arrive.
            thief = foe_of(specimen)
            if (thief is not None and thief is not specimen
                    and thief.get('current_hp', 0) > 0
                    and copies_stat_boosts(thief)):
                log += (f"{prefix}👁️ **{thief['name'].capitalize()}**'s Opportunist "
                        f"helped itself to the {pretty_stat} boost!\n")
                queue.append((thief, s_name, chg, None, False, False))

    # ==========================================
    # ITEM PHASE 2: THE WHITE HERB
    # ==========================================
    # After the queue drains, not during it. Restoring mid-queue would undo a drop that a
    # Defiant answer or a Mirror Armor reflection is still reading, and the herb would
    # then be spent against a stage that a later entry lowered again.
    #
    # This is the ONE place in either engine where a stat stage falls, which is what
    # makes a single line here cover Intimidate, every stat-lowering move, every ability
    # reaction and every item - none of which had to be taught what a White Herb is.
    for specimen in dropped:
        log += apply_white_herb(specimen)

    # ==========================================
    # ITEM PHASE 3: THE EJECT PACK
    # ==========================================
    # Same list and the same reason as the herb above: a drop that Clear Body refused or
    # that was pinned at -6 never reaches `dropped`, so it cannot spend a pack.
    #
    # AFTER the herb deliberately. A specimen cannot hold both, so they never argue - but
    # the order states the intent: restoring a stat is answering the drop, and leaving is
    # answering it too, and if an item ever did both the restore would come first.
    for specimen in dropped:
        _pack = eject_pack_fires(specimen)
        if _pack:
            request_pivot(specimen, _pack)
            spend_item(specimen, _pack)
            log += (f"{prefix}🎒 **{specimen['name'].capitalize()}**'s Eject Pack "
                    f"launched it off the field!\n")

    return log


# ==========================================
# 🎒 BLOCK 11: THE END-OF-TURN ITEM PAYOUT, AND THE BAG
# ==========================================

def apply_item_sustenance(combatant, owner_str="Your", magic_room=False):
    """
    What a held item does to its holder at the end of a turn. One function, both engines.

    This block existed TWICE - once in the PvE turn-end and once in the PvP one,
    byte-identical apart from a comment and some trailing whitespace. Two copies of a rule
    is not a tidiness complaint here: the grounding check a few sections over was
    duplicated in exactly the same way, the copies drifted, and an Air Balloon quietly
    stopped lifting its holder over Spikes until the two were merged. Adding the Sticky
    Barb would have made a third copy of each.

    A fainted holder is skipped by the CALLER, not here, because the caller is the one
    that knows whether the specimen has already been swapped out.
    """
    row = END_OF_TURN_ITEMS.get(get_active_item(combatant, magic_room))
    if not row:
        return ""

    name = combatant['name'].capitalize()
    max_hp = combatant.get('max_hp', 100)

    # A conditional row heals the elements it names and hurts everybody else. Black
    # Sludge's rule, and the only reason `heal` and `hurt` can both be on one row.
    heals = 'heal' in row
    if row.get('heal_types') is not None:
        heals = any(t in (combatant.get('types') or []) for t in row['heal_types'])

    if heals:
        # Only when HP is actually missing. A Leftovers announcing itself at full health
        # every turn was the bug the two copies were both patched for.
        if combatant['current_hp'] >= max_hp:
            return ""
        heal_qty = max(1, math.floor(max_hp / row['heal']))
        combatant['current_hp'] = min(max_hp, combatant['current_hp'] + heal_qty)
        return f"{row['emoji']} **{owner_str} {name}** {row['heal_msg']} (+{heal_qty})\n"

    hurt_qty = max(1, math.floor(max_hp / row['hurt']))
    combatant['current_hp'] = max(0, combatant['current_hp'] - hurt_qty)
    return f"{row['emoji']} **{owner_str} {name}** {row['hurt_msg']} (-{hurt_qty})\n"


def bag_item_is_useless(item, specimen, side_conditions=None):
    """
    Why this bag item would do nothing right now, as a sentence, or None if it would.

    Asked BEFORE the item is spent and before the turn is passed, because using the bag
    costs a turn: a wasted turn is worse than a wasted item, and the old callback checked
    only four of the seven cases it carried.
    """
    row = BATTLE_BAG_ITEMS.get(item)
    if not row:
        return "That is not something you can deploy in the field."

    fainted = specimen.get('current_hp', 0) <= 0
    if row['kind'] == 'revive':
        return None if fainted else "You can only use a Revive on a fainted specimen!"
    if fainted:
        return "You cannot use that item on a fainted specimen! Use a Revive."

    needs = row.get('needs')
    hurt = specimen['current_hp'] < specimen.get('max_hp', 100)
    ailing = bool(specimen.get('status_condition')) or 'confusion' in (
        specimen.get('volatile_statuses') or {})

    if needs == 'hurt' and not hurt:
        return "That specimen is already at maximum health!"
    if needs == 'status' and not ailing:
        return "That specimen is not suffering from any status conditions!"
    if needs == 'hurt_or_status' and not (hurt or ailing):
        return "That specimen is already in perfect condition!"
    if needs == 'not_focused' and (specimen.get('volatile_statuses') or {}).get(
            'focus_energy'):
        return "That specimen is already fired up!"
    if needs == 'no_mist' and (side_conditions or {}).get('mist', 0) > 0:
        return "A white mist is already protecting your team!"
    return None


def apply_bag_item(item, specimen, side_conditions=None, prefix=""):
    """
    Spend a bag item on a specimen and report what happened.

    Every `kind` here is answered by machinery that already existed. `stages` in
    particular goes through resolve_stat_stages rather than writing a stage by hand, so
    an X Attack meets Clear Body, Mirror Armor, Defiant and Opportunist on exactly the
    terms Swords Dance does - which is the whole reason the resolver is shared.
    """
    row = BATTLE_BAG_ITEMS[item]
    log = row['log'].format(name=specimen['name'].capitalize()) + "\n"
    kind = row['kind']

    if kind in ('heal', 'revive', 'cure'):
        if kind == 'revive':
            specimen['current_hp'] = max(1, math.floor(specimen.get('max_hp', 100) * 0.5))
        elif kind == 'heal':
            max_hp = specimen.get('max_hp', 100)
            amount = row['amount']
            specimen['current_hp'] = (max_hp if amount is None
                                      else min(max_hp, specimen['current_hp'] + amount))
        if kind == 'cure' or row.get('cure'):
            specimen['status_condition'] = None
            (specimen.get('volatile_statuses') or {}).pop('confusion', None)
        return log

    if kind == 'stages':
        # No `source`, so the change is the specimen's own doing and nothing screens it -
        # correct for an item the trainer applied rather than an enemy's Growl.
        pending = [(specimen, stat, change, None)
                   for stat, change in row['stats'].items()]
        return log + resolve_stat_stages(pending, prefix)

    if kind == 'crit':
        specimen.setdefault('volatile_statuses', {})['focus_energy'] = True
        return log

    if kind == 'side':
        if side_conditions is None:
            return log
        side_conditions[row['condition']] = row['turns']
        return log

    return log


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

def ruin_multiplier(stat, opponent):
    """
    What the specimen OPPOSITE is doing to this stat, for the Ruin quartet.

    The only ability family in the game that reaches across the field and holds a stat
    down for as long as it is standing there. Deliberately not a stage change: Clear Body
    cannot refuse it, Haze cannot clear it, and it lifts of its own accord the moment its
    owner withdraws.
    """
    if not opponent:
        return 1.0
    return (RUIN_MULTIPLIER
            if RUIN_ABILITIES.get(get_active_ability(opponent)) == stat else 1.0)


# ==========================================
# 💥 BLOCK 14: REACTIONS TO THE HIT ITSELF
# ==========================================

def is_wind_move(move_name):
    """Wind-based, for Wind Rider and Wind Power. Listed rather than guessed."""
    return normalise_move_name(move_name) in WIND_MOVES


def refuses_wind(defender):
    """Wind Rider does not merely answer a wind move - it refuses one."""
    return get_active_ability(defender) in WIND_IMMUNE_ABILITIES


def on_hit_reaction(defender, move_name, move, attacker, damage, was_crit):
    """
    What the specimen that was just hit does about it, or None.

    Returns the row from ON_HIT_REACTIONS once its trigger is satisfied. Kept separate
    from applying it so the engines can ask the question without the answer having side
    effects, and so the trigger logic is testable on its own.
    """
    row = ON_HIT_REACTIONS.get(get_active_ability(defender))
    if not row:
        return None

    trigger = row['trigger']
    if trigger == 'crit':
        if not was_crit or damage <= 0:
            return None
    elif trigger == 'contact':
        if damage <= 0 or not makes_contact(move, attacker):
            return None
    elif trigger == 'physical':
        if damage <= 0 or (move or {}).get('class') != 'physical':
            return None
    else:  # 'damaged'
        if damage <= 0:
            return None

    if 'types' in row and (move or {}).get('type') not in row['types']:
        return None
    if row.get('wind') and not is_wind_move(move_name):
        return None

    return row


# ==========================================
# ITEM PHASE 2: THE ONE-SHOT POLICIES AND SEEDS
# ==========================================
# Every one of these ASKS a question and, if the answer is yes, spends the item. They do
# not write the stat stage: they hand it back so the caller can enqueue it, which is
# what puts a Weakness Policy boost through the same resolver as a Swords Dance.
#
# `spend_item` is separate from each trigger for the same reason `on_hit_reaction` is
# separate from applying it - the question can then be asked by a test, or by the AI,
# without an item disappearing as a side effect of asking.

def spend_item(pokemon, item):
    """Burn a one-shot item out of a specimen's hands and record that it was USED."""
    if pokemon is None or not item:
        return
    pokemon['held_item'] = 'none'
    mark_item_consumed(pokemon, item)


def balloon_pops(defender, move, damage, magic_room=False):
    """
    Whether the hit the defender just took destroys its Air Balloon.

    Any damaging move that CONNECTS pops it. Two exclusions matter and both fall out of
    `damage > 0` rather than needing a rule of their own:

    - a Ground move is answered further up and returns zero, so the balloon it just
      bounced does not also burst on the way past
    - anything else the defender is immune to deals no damage either, and a move that
      never reached the specimen cannot have reached the balloon

    Status moves are excluded explicitly, because a Toxic that lands deals no damage but
    is not the kind of nothing the two rules above describe.
    """
    if defender is None or damage <= 0:
        return False
    if (move or {}).get('class') == 'status':
        return False
    return get_active_item(defender, magic_room) == 'air-balloon'


def item_hit_reaction(defender, move, damage, type_multiplier=1.0, magic_room=False):
    """
    What the specimen's ITEM does about the hit it just took, or None.

    Returns `(item, [(stat, stages), ...])`. Asked only about damaging hits that
    actually landed: an Absorb Bulb does not answer a Water-type status move, and a
    Weakness Policy does not answer a super-effective move that was blocked outright.
    """
    if defender is None or damage <= 0:
        return None
    if (move or {}).get('class') == 'status':
        return None

    item = get_active_item(defender, magic_room)
    row = ITEM_HIT_REACTIONS.get(item)
    if not row:
        return None

    if row.get('super_effective'):
        if type_multiplier <= 1.0:
            return None
    elif 'types' in row and (move or {}).get('type') not in row['types']:
        return None

    return item, list(row['self'])


# ==========================================
# ITEM PHASE 7: THE BERRIES THAT ANSWER A HIT
# ==========================================
# Kee, Maranga, Jaboca, Rowap and Enigma. Deliberately NOT rows in ITEM_HIT_REACTIONS
# above, even though four of the five are the same sentence as a Weakness Policy, because
# a policy is SPENT and a berry is EATEN - and eating is the thing Unnerve blocks, Ripen
# doubles, Cheek Pouch pays for and Belch, Harvest and Cud Chew all remember. Filing them
# with the policies would have made five berries that behaved correctly and were not
# berries.

def berry_hit_reaction(defender, attacker, move, damage, type_multiplier=1.0,
                       magic_room=False, move_class=None):
    """
    Which berry the defender eats in answer to the hit it just took, and its row.

    Returns `(berry, row)`, or None. Like `item_hit_reaction` this only ASKS - nothing is
    eaten, healed or hurt here, so a test or the AI can ask without a berry vanishing.

    `move_class` is the class the move actually RESOLVED as, so a physical Photon Geyser
    is answered by a Kee Berry rather than a Maranga. The caller passes it because only
    the damage resolver knows; the move's own class is the fallback.
    """
    if defender is None or damage <= 0:
        return None
    if (move or {}).get('class') == 'status':
        return None

    berry = get_active_item(defender, magic_room)
    row = BERRY_HIT_REACTIONS.get(berry)
    if not row:
        return None

    # Unnerve, asked of the specimen standing opposite. Same question check_consumables
    # asks, for the same reason: a berry that cannot be eaten cannot do anything.
    if berries_are_blocked(attacker):
        return None

    trigger = row['trigger']
    if trigger == 'super_effective':
        if type_multiplier <= 1.0:
            return None
    elif (move_class or (move or {}).get('class')) != trigger:
        return None

    return berry, row


# ==========================================
# ITEM PHASE 3: THE EJECTORS
# ==========================================
# Eject Button, Eject Pack and Red Card. Each one ASKS its question here and, if the
# answer is yes, parks a request on the specimen that has to leave. Nothing switches
# anybody: these functions have two combatants and no teams, which is the same reason
# the weather and terrain reactions above are smuggled out through a payload rather than
# applied in place.
#
# The request is cashed in by `end_of_turn_survival`, beside Wimp Out, which already
# owns the "this specimen wants off the field" clock. One clock, three items and two
# abilities feeding it.

def request_pivot(pokemon, item):
    """Park an ejection on `pokemon`, to be cashed in at the end of the turn."""
    if pokemon is None or pokemon.get('current_hp', 0) <= 0:
        return
    pokemon[PIVOT_REQUEST] = item


def pending_pivot(pokemon):
    """Which item is asking this specimen to leave, or None."""
    if pokemon is None:
        return None
    return pokemon.get(PIVOT_REQUEST)


def clear_pivot_request(pokemon):
    """Forget a parked ejection - it has either been honoured or has nowhere to go."""
    if pokemon is not None:
        pokemon.pop(PIVOT_REQUEST, None)


def involuntary_pivot(pokemon):
    """
    Whether this specimen is being dragged out rather than choosing to leave.

    Only Red Card. A trainer who is Red Carded does not pick the replacement - that is
    the whole difference between being dragged out and pivoting, and letting them choose
    would turn the card into a free switch for the person it was played against.
    """
    return pending_pivot(pokemon) in RANDOM_REPLACEMENT_ITEMS


def eject_button_fires(defender, move, damage, magic_room=False):
    """
    Eject Button: the holder leaves after a move damages it.

    Gated on damage landing, exactly as the Phase 2 policies are - a status move that
    lands does not press it, and neither does a move the holder was immune to.
    """
    if defender is None or damage <= 0 or defender.get('current_hp', 0) <= 0:
        return None
    if (move or {}).get('class') == 'status':
        return None
    if get_active_item(defender, magic_room) != 'eject-button':
        return None
    return 'eject-button'


def red_card_fires(defender, attacker, move, damage, magic_room=False):
    """
    Red Card: the ATTACKER leaves after damaging the holder.

    The holder spends the card; the attacker is the one that goes. Suction Cups and
    Guard Dog refuse it for the same reason they refuse Whirlwind - the card is a
    forced switch, so it is answered by the ability that answers forced switches rather
    than by a rule of its own.

    A dead attacker is not dragged anywhere, and neither is one whose holder has just
    fainted: the card needs a living hand to play it.
    """
    if defender is None or attacker is None or damage <= 0:
        return None
    if (move or {}).get('class') == 'status':
        return None
    if defender.get('current_hp', 0) <= 0 or attacker.get('current_hp', 0) <= 0:
        return None
    if get_active_item(defender, magic_room) != 'red-card':
        return None
    if resists_forced_switch(attacker):
        return None
    return 'red-card'


def eject_pack_fires(pokemon, magic_room=False):
    """
    Eject Pack: the holder leaves after any of its stats is LOWERED.

    Asked once a drop has actually landed, so a drop that Clear Body refused or that was
    already pinned at -6 does not spend the pack. That is the same place and the same
    reason as the White Herb, and both read the one list of specimens that really lost a
    stage - which is what stops the pack answering an Intimidate that never took.
    """
    if pokemon is None or pokemon.get('current_hp', 0) <= 0:
        return None
    if get_active_item(pokemon, magic_room) != 'eject-pack':
        return None
    return 'eject-pack'


def terrain_seed_fires(pokemon, terrain, magic_room=False):
    """
    Whether the holder's seed answers this terrain, as `(item, stat, stages)` or None.

    Grounded-ness is NOT tested here. A terrain only affects grounded specimens in the
    first place, and every caller already knows whether the terrain is doing anything -
    duplicating the test would give two places for the answer to differ.
    """
    if pokemon is None or pokemon.get('current_hp', 1) <= 0:
        return None

    item = get_active_item(pokemon, magic_room)
    row = TERRAIN_SEED_ITEMS.get(item)
    if not row:
        return None

    wanted, stat = row
    if (terrain or 'none') != wanted:
        return None
    return item, stat, 1


def sound_move_spray(attacker, move_name, magic_room=False):
    """Throat Spray, which answers the holder's own sound move rather than being hit."""
    if attacker is None or attacker.get('current_hp', 1) <= 0:
        return None
    if get_active_item(attacker, magic_room) != 'throat-spray':
        return None
    if not is_sound_move(move_name):
        return None
    return 'throat-spray', THROAT_SPRAY_BOOST


def blunder_policy_fires(attacker, magic_room=False):
    """Blunder Policy, after a move misses because of accuracy."""
    if attacker is None or attacker.get('current_hp', 1) <= 0:
        return None
    if get_active_item(attacker, magic_room) != 'blunder-policy':
        return None
    return 'blunder-policy', BLUNDER_POLICY_BOOST


def room_service_fires(pokemon, magic_room=False):
    """Room Service, when Trick Room goes up over the holder."""
    if pokemon is None or pokemon.get('current_hp', 1) <= 0:
        return None
    if get_active_item(pokemon, magic_room) != 'room-service':
        return None
    return 'room-service', ROOM_SERVICE_DROP


def white_herb_restores(pokemon, magic_room=False):
    """
    Which stats a White Herb would put back, as a list of names, or None.

    Reads only NEGATIVE stages. A herb does not touch a boost, which is the whole
    difference between it and Haze, and getting that backwards would make it a
    downgrade to hold.
    """
    if pokemon is None or pokemon.get('current_hp', 1) <= 0:
        return None
    if get_active_item(pokemon, magic_room) != 'white-herb':
        return None

    lowered = [stat for stat, stage in (pokemon.get('stat_stages') or {}).items()
               if (stage or 0) < 0]
    return lowered or None


def apply_white_herb(pokemon, magic_room=False):
    """Put the lowered stages back and spend the herb. Returns a log line, or ''."""
    lowered = white_herb_restores(pokemon, magic_room)
    if not lowered:
        return ""

    stages = pokemon.setdefault('stat_stages', {})
    for stat in lowered:
        stages[stat] = 0
    spend_item(pokemon, 'white-herb')
    return (f"🌿 **{pokemon['name'].capitalize()}**'s White Herb restored its "
            f"lowered stats!\n")


def mental_herb_frees(pokemon, magic_room=False):
    """Which of the mental conditions a Mental Herb would clear, or None."""
    if pokemon is None or pokemon.get('current_hp', 1) <= 0:
        return None
    if get_active_item(pokemon, magic_room) != 'mental-herb':
        return None

    volatiles = pokemon.get('volatile_statuses') or {}
    held = [name for name in MENTAL_HERB_CURES if volatiles.get(name)]
    return held or None


def apply_mental_herb(pokemon, magic_room=False):
    """Clear what the herb cures and spend it. Returns a log line, or ''."""
    cured = mental_herb_frees(pokemon, magic_room)
    if not cured:
        return ""

    volatiles = pokemon.setdefault('volatile_statuses', {})
    for name in cured:
        volatiles.pop(name, None)
    spend_item(pokemon, 'mental-herb')
    pretty = ", ".join(name.replace('_', ' ').title() for name in cured)
    return (f"🌱 **{pokemon['name'].capitalize()}**'s Mental Herb cleared its "
            f"{pretty}!\n")


def charge_multiplier(attacker, move_type):
    """
    What a banked charge is worth to the move being thrown, and spends it.

    Wind Power and Electromorphosis bank exactly one charge, worth double power on the
    next ELECTRIC move. Reading it consumes it, which is why this is a function rather
    than a lookup - a non-Electric move in between leaves the charge alone.
    """
    if move_type != 'electric':
        return 1.0
    volatiles = (attacker or {}).get('volatile_statuses') or {}
    if not volatiles.get(CHARGE_VOLATILE):
        return 1.0
    volatiles.pop(CHARGE_VOLATILE, None)
    return CHARGE_MULTIPLIER


# ==========================================
# 🩸 BLOCK 15: REACTIONS TO SOMETHING OTHER THAN THE HIT
# ==========================================

def crossed_below_half(pokemon):
    """
    Whether this specimen has just fallen past half health and not yet answered it.

    Berserk and Anger Shell answer HP CROSSING the line rather than sitting below it, so
    the marker is what stops them firing every turn afterwards. leave_field clears it, so
    switching out and back in re-arms them - the same arrangement Block 13's Wimp Out uses,
    and for the same reason.
    """
    if not pokemon or get_active_ability(pokemon) not in HP_THRESHOLD_REACTIONS:
        return False
    if pokemon.get(HP_THRESHOLD_MARKER):
        return False

    ceiling = max(1, pokemon.get('max_hp', 1))
    return 0 < pokemon.get('current_hp', 0) < ceiling * HP_THRESHOLD


def hp_threshold_stages(pokemon):
    """The stage changes owed for having crossed below half."""
    return HP_THRESHOLD_REACTIONS.get(get_active_ability(pokemon), [])


def flinch_reaction(pokemon):
    """Steadfast: (stat, stages) owed for having flinched, or None."""
    return FLINCH_REACTIONS.get(get_active_ability(pokemon))


def liquid_ooze_backfires(defender):
    """Liquid Ooze: what the attacker meant to drain, it takes instead."""
    return get_active_ability(defender) in LIQUID_OOZE_ABILITIES


def faint_recoil(fainted, killer, move, was_contact):
    """
    What the specimen that just died does to whatever killed it.

    Aftermath needs the killing blow to have been a touch. Innards Out does not care how
    it died - it hands over whatever it had left, which is why the caller has to pass the
    HP it held BEFORE the blow rather than the zero it holds now.
    """
    ability = get_active_ability(fainted)
    if ability in AFTERMATH_ABILITIES and was_contact:
        return math.floor(max(1, killer.get('max_hp', 1)) * AFTERMATH_FRACTION), ability
    if ability in INNARDS_OUT_ABILITIES:
        return max(0, fainted.get('_hp_before_blow', 0)), ability
    return 0, None


# ==========================================
# 🦋 BLOCK 16: EVENT-DRIVEN FORM FLIPS
# ==========================================
# Every one of these answers the same question - which body should this specimen be
# wearing right now - so they are predicates that NAME a form rather than functions
# that change one. The changing is done by assume_species_form, which is async and
# needs a database, and keeping that on the far side of the answer is what lets these
# be tested without standing a battle up.

def request_form_flip(pokemon, form, flavour=''):
    """Bank a form change for the engines to cash in. Returns whether one was owed."""
    if not pokemon or not form:
        return False
    pokemon[FORM_FLIP_REQUEST] = (form, flavour)
    return True


def _wearing(pokemon):
    return str(pokemon.get('name') or '').lower()


def hp_form_for(pokemon):
    """
    The form an HP-watching ability says this specimen should be in, or None.

    Zen Mode, Schooling, Shields Down and Power Construct. `reverts` is what separates
    Zygarde from the rest: coming back above the line puts the others back, and leaves
    Complete alone.
    """
    rule = HP_FORM_FLIPS.get(get_active_ability(pokemon))
    if not rule:
        return None
    if pokemon.get('level', 100) < rule.get('min_level', 0):
        return None

    share = pokemon.get('current_hp', 0) / max(1, pokemon.get('max_hp', 1))
    if 'below' in rule:
        transformed = share < rule['below']
    else:
        transformed = share > rule['above']

    here = _wearing(pokemon)
    if transformed:
        return rule['pairs'].get(here)

    if not rule.get('reverts'):
        return None
    back = {v: k for k, v in rule['pairs'].items()}
    return back.get(here)


def hit_breaks_form(defender, move):
    """
    Disguise and Ice Face: (broken_form, toll) when this hit comes off the costume.

    Returns None when the specimen is already unmasked, or when Ice Face is looking at
    a special move, which it simply stands there and takes.
    """
    rule = BROKEN_BY_A_HIT.get(get_active_ability(defender))
    if not rule or (move or {}).get('class') == 'status':
        return None
    if rule['physical_only'] and (move or {}).get('class') != 'physical':
        return None

    broken = rule['pairs'].get(_wearing(defender))
    if not broken:
        return None
    return broken, math.floor(max(1, defender.get('max_hp', 1)) * rule['toll'])


def stance_form_for(attacker, move_name, move):
    """Aegislash: the blade for a damaging move, the shield for King's Shield."""
    if get_active_ability(attacker) not in STANCE_CHANGE_ABILITIES:
        return None
    here = _wearing(attacker)
    if normalise_move_name(move_name) in STANCE_SHIELD_MOVES:
        return STANCE_SHIELD.get(here)
    if (move or {}).get('class') == 'status':
        return None
    return STANCE_BLADE.get(here)


def hunger_form_for(pokemon):
    """Morpeko, which is hungry every other turn whatever else is happening."""
    if get_active_ability(pokemon) not in HUNGER_SWITCH_ABILITIES:
        return None
    return HUNGER_PAIRS.get(_wearing(pokemon))


def hero_form_for(pokemon):
    """Palafin, on the way OUT. One way, and once a battle."""
    if get_active_ability(pokemon) not in ZERO_TO_HERO_ABILITIES:
        return None
    if pokemon.get(ZERO_TO_HERO_MARKER):
        return None
    return ZERO_TO_HERO_PAIRS.get(_wearing(pokemon))


def gulp_catch_for(attacker, move_name):
    """
    What Cramorant surfaces holding, or None.

    Which mouthful it caught depends on how hurt it was when it went under, which is
    why this reads the HP rather than just the move.
    """
    if get_active_ability(attacker) not in GULP_MISSILE_ABILITIES:
        return None
    if normalise_move_name(move_name) not in GULP_TRIGGER_MOVES:
        return None
    if _wearing(attacker) != GULP_BASE_FORM:
        return None

    share = attacker.get('current_hp', 0) / max(1, attacker.get('max_hp', 1))
    return GULP_HURT_FORM if share <= GULP_HURT_THRESHOLD else GULP_HEALTHY_FORM


def gulp_payload_for(defender):
    """What a mouthful-holding Cramorant spits at whatever just hit it."""
    if get_active_ability(defender) not in GULP_MISSILE_ABILITIES:
        return None
    return GULP_PAYLOADS.get(_wearing(defender))


def paradox_engine_running(pokemon, weather='none', terrain='none'):
    """
    Whether Protosynthesis or Quark Drive is currently engaged.

    Two ways in. The field condition is read live, so the boost lapses of its own accord
    the moment the sun goes in - no bookkeeping needed. Booster Energy is the other, and
    that one IS remembered: once drunk the engine runs for the rest of the battle whatever
    the weather does.
    """
    engine = PARADOX_ABILITIES.get(get_active_ability(pokemon))
    if not engine:
        return False

    if pokemon.get(BOOSTER_SPENT_MARKER):
        return True
    if 'weather' in engine and weather in engine['weather']:
        return True
    return 'terrain' in engine and terrain in engine['terrain']


def paradox_best_stat(pokemon):
    """
    Which stat the engine picks: the highest of the five, stages included.

    Ties go to whichever comes first in PARADOX_STAT_ORDER, which is the order the games
    break them in. HP is not a candidate - the engine boosts what a specimen fights with.
    """
    stats = pokemon.get('stats') or {}
    stages = pokemon.get('stat_stages') or {}
    best, best_value = None, None
    for key in PARADOX_STAT_ORDER:
        value = apply_stat_stage(stats.get(key, 0), stages.get(key, 0))
        if best_value is None or value > best_value:
            best, best_value = key, value
    return best


# ==========================================
# 💀 BLOCK 17: KNOCKOUT REACTIONS
# ==========================================
# What a faint is worth, to whom, and on what evidence. Three separate questions, kept
# apart because they fire at different moments and on different conditions:
#
#   knockout_boost   - paid to the KILLER, and only for a kill it made with an attack.
#   mourning_boost   - paid to a WITNESS, for any faint at all, however it happened.
#   copies_stat_boosts / supreme_overlord_multiplier - neither is about a faint landing;
#                       one reads the opponent's boosts, the other reads the graveyard.


def knockout_boost(killer):
    """
    (stat, stages) owed to whoever just finished something off, or None.

    The stat is in the payload vocabulary, so the answer goes through the ordinary stage
    resolver: a Moxie boost caps at +6 like anything else and Haze takes it away again.
    Beast Boost and Eelevate name no stat at all - they take whichever is highest right
    now, stages included, so a Beast Boost that has already fired twice can move on to a
    different stat than the one it started with.
    """
    if not killer or killer.get('current_hp', 0) <= 0:
        return None

    stat = KNOCKOUT_BOOST_ABILITIES.get(get_active_ability(killer))
    if not stat:
        return None
    if stat == KNOCKOUT_BEST_STAT:
        stat = STAGE_NAME_FOR_STAT.get(paradox_best_stat(killer))
        if not stat:
            return None
    return stat, KNOCKOUT_BOOST_STAGES


def mourning_boost(witness, fallen):
    """
    (stat, stages) owed to a specimen for having WATCHED something faint, or None.

    Deliberately indifferent to who did the killing - Soul-Heart answers a Pokemon
    fainting, not an attack connecting, so a specimen that poisons itself to death pays
    out just the same.

    A corpse cannot mourn, which is also what stops anything mourning its own death:
    the witness must be standing and the fallen must not be, and no specimen is both.
    An explicit `witness is fallen` test was written here first and taken out again -
    it could not be made to fail, because the two HP checks already cover every case
    that could reach it.
    """
    if not witness or not fallen:
        return None
    if witness.get('current_hp', 0) <= 0:
        return None
    if fallen.get('current_hp', 0) > 0:
        return None

    stat = MOURNING_ABILITIES.get(get_active_ability(witness))
    return (stat, MOURNING_STAGES) if stat else None


def mark_mourned(fallen):
    """
    Record that this faint has been answered. Returns False if it already had been.

    The blow that lands and the end-of-turn sweep both ask about the same corpse, and
    within one turn both can see it. This is the ONLY thing standing between them and
    paying twice - deliberately, because a second guard at the call site would be a
    second place for the rule to live and could not be made to fail on its own.
    """
    if fallen is None or fallen.get(MOURNED_MARKER):
        return False
    fallen[MOURNED_MARKER] = True
    return True


# ==========================================
# 🌦️ BLOCK 18: ABILITIES THAT READ THE FIELD
# ==========================================


def weather_form_for(pokemon, weather='none'):
    """
    Which body Castform should be wearing for this sky, or None if it already is.

    Block 16's form flips all answer something that happened TO the specimen; this one
    answers something about the field, so it is asked wherever the weather is known
    rather than wherever damage was applied. The request it banks is the same one, and
    the same resolver cashes it in - the type change comes along with the species half.
    """
    rule = WEATHER_FORMS.get(get_active_ability(pokemon))
    if not rule:
        return None

    wearing = (pokemon or {}).get('name')
    if wearing not in rule['by_weather'].values() and wearing != rule['base']:
        return None

    wanted = rule['by_weather'].get(weather, rule['base'])
    return None if wanted == wearing else wanted


def truancy_holds_it_back(pokemon):
    """
    Whether Truant makes this specimen loaf about instead of moving.

    Asking ADVANCES the rhythm, which is deliberate and is why this is one function
    rather than a predicate plus a toggle: it is asked once per attempt to move, from
    three separate places, and a caller that forgot to advance it would leave a Slaking
    either loafing for ever or never. The first ask after arriving always lets it move.

    The marker is cleared in leave_field, so switching out and back in re-arms it.
    """
    if get_active_ability(pokemon) not in TRUANT_ABILITIES:
        return False

    loafing = bool(pokemon.get(TRUANT_MARKER))
    pokemon[TRUANT_MARKER] = not loafing
    return loafing


def is_effectively_asleep(pokemon):
    """
    Whether this specimen counts as asleep to everything EXCEPT the question of whether
    it can act.

    Comatose is a permanent sleep its owner walks around in, so Bad Dreams torments it,
    Wake-Up Slap hits it twice as hard and Hex reads it as statused - but nothing here
    stops it moving, which is why the incapacity checks go on reading the status slot
    directly rather than calling this.
    """
    if not pokemon:
        return False
    if get_active_ability(pokemon) in COMATOSE_ABILITIES:
        return True
    return (pokemon.get('status_condition') or {}).get('name') == 'sleep'


def copies_stat_boosts(pokemon):
    """
    Opportunist: takes a copy of whatever the specimen opposite gains.

    ITEM PHASE 5: a Mirror Herb says the same thing. Answered here rather than beside the
    ability so the copy still travels through resolve_stat_stages' loop guard - two
    Mirror Herbs cannot trade one Swords Dance back and forth for ever, for the same
    reason two Opportunists cannot.
    """
    return (get_active_ability(pokemon) in OPPORTUNIST_ABILITIES
            or get_active_item(pokemon) in COPIES_BOOSTS_ITEMS)


def fallen_allies(party, exclude=None):
    """How many of a party have already been knocked out, capped where the ability caps."""
    count = sum(1 for member in (party or [])
                if member is not None and member is not exclude
                and member.get('current_hp', 0) <= 0)
    return min(count, SUPREME_OVERLORD_MAX_FALLEN)


def supreme_overlord_multiplier(pokemon, stat, party):
    """
    The graveyard boost, on Attack and Sp. Atk only.

    Read live off the party every time rather than banked when an ally falls, so it
    cannot drift out of step with a Revival Blessing bringing one back.
    """
    if not pokemon or not party:
        return 1.0
    if get_active_ability(pokemon) not in SUPREME_OVERLORD_ABILITIES:
        return 1.0
    if stat not in SUPREME_OVERLORD_STATS:
        return 1.0
    return 1.0 + SUPREME_OVERLORD_PER_FALLEN * fallen_allies(party, exclude=pokemon)


def paradox_multiplier(pokemon, stat, weather='none', terrain='none'):
    """The Protosynthesis / Quark Drive boost, on the one stat it picked."""
    if not paradox_engine_running(pokemon, weather, terrain):
        return 1.0
    if paradox_best_stat(pokemon) != stat:
        return 1.0
    return PARADOX_SPEED_BOOST if stat == 'speed' else PARADOX_BOOST


def stat_multiplier_for(pokemon, stat, weather='none', terrain='none', opponent=None,
                        party=None, magic_room=False):
    """
    The flat multiplier an ability puts on one of its owner's own stats.

    Huge Power, Marvel Scale, Defeatist and the rest. Every condition on the row is
    optional and they AND together, so a bare row is unconditional. Returns 1.0 when
    nothing applies.

    `opponent` is only read by the Ruin quartet, which is the one family that presses on
    somebody else's stats rather than its own. `party` is only read by Supreme Overlord,
    which is the one that reads the bench. Callers that have neither to hand simply get
    neither, which is correct for them.
    """
    if not pokemon:
        return 1.0

    # Three multipliers that do not come from the table: what the specimen OPPOSITE is
    # doing (the Ruin quartet), the Paradox engines, whose stat is chosen at runtime
    # rather than named in a row, and Supreme Overlord, which counts corpses. All three
    # ride alongside the table row rather than replacing it.
    against = (ruin_multiplier(stat, opponent)
               * paradox_multiplier(pokemon, stat, weather, terrain)
               * supreme_overlord_multiplier(pokemon, stat, party)
               # ITEM PHASE 6: the species-gated items ride alongside the ability row for
               # the same reason the three above do - a Light Ball and a Huge Power are
               # two separate claims on the same stat and both should be honoured.
               * species_stat_multiplier(pokemon, stat, magic_room))

    trait = BIOLOGICAL_TRAITS.get('stat_multipliers', {}).get(get_active_ability(pokemon))
    if not trait or stat not in trait['stats']:
        return against

    # Every early return below is "this specimen's own ability does not apply" - which
    # says nothing about what the specimen opposite is doing, so they all hand back the
    # Ruin figure rather than a bare 1.0.
    wanted = trait.get('status')
    if wanted is not None:
        current = (pokemon.get('status_condition') or {}).get('name')
        if not current:
            return against
        if wanted != '*' and current not in wanted:
            return against

    if 'weather' in trait and weather not in trait['weather']:
        return against
    if 'terrain' in trait and terrain not in trait['terrain']:
        return against

    if 'hp_at_or_below' in trait:
        share = pokemon.get('current_hp', 0) / max(1, pokemon.get('max_hp', 1))
        if share > trait['hp_at_or_below']:
            return against

    if trait.get('unburdened') and not is_unburdened(pokemon):
        return against

    if 'turns_on_field_below' in trait:
        if (pokemon.get('turns_on_field') or 0) >= trait['turns_on_field_below']:
            return against

    return trait['multiplier'] * against


def is_unburdened(pokemon):
    """
    True while the specimen has lost the item it walked in holding.

    Reads the STORED item rather than the active one on purpose: Embargo and Magic Room
    switch an item off without taking it away, and Unburden is about the weight being
    gone, not the effect. `_entry_item` is written by the switch-in hook; `_original_item`
    is the battle-start snapshot, and is the fallback for any entry path that misses it.
    """
    if pokemon is None:
        return False
    came_in_with = pokemon.get('_entry_item')
    if came_in_with is None:
        came_in_with = pokemon.get('_original_item')
    if not came_in_with or came_in_with == 'none':
        return False
    return get_stored_item(pokemon) == 'none'


def battle_speed(pokemon, has_tailwind=False, weather='none', terrain='none', magic_room=False):
    """
    How fast this specimen actually moves this turn, for the turn-order check.

    One function for both engines. They each had their own nested copy, and the copies had
    already drifted: one applied Tailwind before the paralysis cut and the other after,
    and they rounded at different points. Order here is stages, then the ability, then the
    Choice Scarf, then paralysis, then Tailwind.

    Quick Feet is the reason paralysis is checked against the ability rather than applied
    blindly: it takes the 1.5x for being statused AND ignores the speed cut that being
    paralysed would otherwise bring.
    """
    if not pokemon:
        return 0

    raw = (pokemon.get('stats') or {}).get('speed', 50)
    speed = apply_stat_stage(raw, (pokemon.get('stat_stages') or {}).get('speed', 0))

    # ITEM PHASE 11: the sky as THIS specimen reads it, so a Utility Umbrella holder gets
    # no Swift Swim in rain and no Chlorophyll in sun. Applied here rather than inside
    # stat_multiplier_for, because that function is also asked about the specimen
    # OPPOSITE, and an umbrella shelters its own holder rather than the whole field.
    weather = sheltered_weather(pokemon, weather, magic_room)

    speed *= stat_multiplier_for(pokemon, 'speed', weather, terrain,
                                 magic_room=magic_room)

    if get_active_item(pokemon, magic_room) == 'choice-scarf':
        speed *= 1.5

    # ITEM PHASE 9: the Iron Ball, on the same line as the Choice Scarf because it is
    # the same shape of effect pointing the other way.
    if get_active_item(pokemon, magic_room) == IRON_BALL:
        speed *= IRON_BALL_SPEED

    status = (pokemon.get('status_condition') or {}).get('name')
    if status == 'paralysis' and get_active_ability(pokemon) != 'quick-feet':
        speed *= 0.5

    if has_tailwind:
        speed *= 2.0

    return int(speed)


def accuracy_multiplier(attacker):
    """
    What an ability does to the accuracy of the move its owner is throwing.

    Hustle's 1.5x Attack is paid for here; Compound Eyes and Victory Star sharpen it.
    """
    return ACCURACY_MULTIPLIER_ABILITIES.get(get_active_ability(attacker), 1.0)


# ==========================================
# ITEM PHASE 4: THE LENSES AND THE POWDERS
# ==========================================
# Deliberately shaped as the item twin of accuracy_multiplier / evasion_multiplier above,
# and read in the same expression at the bottom of hit_chance - so a lens and a Compound
# Eyes stack the way two multipliers should, without either learning about the other.

def item_accuracy_multiplier(attacker, defender=None, magic_room=False):
    """
    What the ATTACKER's item does to the accuracy of the move it is throwing.

    Wide Lens is unconditional. Zoom Lens only sharpens a holder that is moving SECOND,
    which is exactly `defender.acted_this_turn` - the flag both engines already keep for
    Bolt Beak, reset for everybody at the top of the turn and set on each attacker as it
    acts. Reading it here rather than threading a new argument through both engines is
    what keeps the two of them from disagreeing about who moved first.
    """
    item = get_active_item(attacker, magic_room)

    if item == 'zoom-lens':
        return ZOOM_LENS_MULTIPLIER if (defender or {}).get('acted_this_turn') else 1.0

    return ITEM_ACCURACY_MULTIPLIERS.get(item, 1.0)


def item_evasion_multiplier(defender, magic_room=False):
    """
    What the DEFENDER's item does to the chance of being hit, as a number to DIVIDE by.

    Bright Powder and Lax Incense. The table stores the accuracy figure the games use -
    0.9 and 0.95 - and this is the one place it is inverted, so the value returned lines
    up with evasion_multiplier's convention where higher means harder to hit.
    """
    against = ITEM_ACCURACY_AGAINST_HOLDER.get(get_active_item(defender, magic_room))
    if not against:
        return 1.0
    return 1.0 / against


def item_flinch_chance(attacker, move, damage, magic_room=False):
    """
    The percentage chance the attacker's ITEM makes its target flinch, or 0.

    King's Rock and Razor Fang, on any damaging move that connected. Two deliberate
    non-interactions, both matching the modern games and both falling out of this being
    an ITEM rather than a move's secondary effect: Serene Grace does not double it and
    Shield Dust does not block it. Inner Focus DOES refuse it, for free, because the
    caller routes the result through the same volatile check Stench uses.
    """
    if attacker is None or damage <= 0:
        return 0
    if (move or {}).get('class') == 'status':
        return 0
    return ITEM_FLINCH_CHANCE.get(get_active_item(attacker, magic_room), 0)


# ==========================================
# ITEM PHASE 5: THE DEFENSIVE AND UTILITY SHELF
# ==========================================
# Everything here that could join an existing ability predicate already has - Covert
# Cloak sits in secondary_chance, Clear Amulet in refuses_stat_drop, Protective Pads in
# makes_contact, Mirror Herb in copies_stat_boosts. What is left are the ones with no
# ability twin, and they are gathered here rather than scattered.

def can_still_evolve(pokemon):
    """
    Whether this specimen has somewhere left to evolve to - the Eviolite condition.

    Read off the REAL species. An Illusion fools the trainer; letting it fool an Eviolite
    as well would have a disguised Zoroark wearing somebody else's walls.
    """
    return true_pokedex_id(pokemon) in UNEVOLVED_SPECIES


def eviolite_multiplier(pokemon, stat, magic_room=False):
    """The Eviolite's factor for one defensive stat, or 1.0."""
    if pokemon is None or stat not in EVIOLITE_STATS:
        return 1.0
    if get_active_item(pokemon, magic_room) != 'eviolite':
        return 1.0
    return EVIOLITE_MULTIPLIER if can_still_evolve(pokemon) else 1.0


def punching_glove_boost(attacker, move_name, magic_room=False):
    """1.1 for a punch thrown by a Punching Glove, otherwise 1.0."""
    if get_active_item(attacker, magic_room) != 'punching-glove':
        return 1.0
    return PUNCHING_GLOVE_BOOST if normalise_move_name(move_name) in PUNCH_MOVES else 1.0


def ignores_hazards(pokemon, magic_room=False):
    """Heavy-Duty Boots: the holder walks over everything laid on its side."""
    return get_active_item(pokemon, magic_room) == HEAVY_DUTY_BOOTS


def ability_is_shielded(pokemon, magic_room=False):
    """
    Ability Shield: the holder's ability cannot be changed, copied onto it or suppressed.

    Read by the paths Block 21 built for Neutralizing Gas, Skill Swap, Entrainment,
    Gastro Acid and the rest, rather than by a rule of its own.
    """
    return get_active_item(pokemon, magic_room) == ABILITY_SHIELD


def refuses_powder(defender, move_name, magic_room=False):
    """Safety Goggles: the item half of Overcoat's powder immunity."""
    if get_active_item(defender, magic_room) not in POWDER_IMMUNE_ITEMS:
        return False
    return normalise_move_name(move_name) in POWDER_MOVES


def shrugs_off_weather_chip(pokemon, magic_room=False):
    """Safety Goggles again: no sandstorm grit and no hail."""
    return get_active_item(pokemon, magic_room) in WEATHER_CHIP_IMMUNE_ITEMS


def focus_band_holds(defender, magic_room=False, rng=random):
    """
    Focus Band: a one-in-ten chance to survive a lethal hit at 1 HP.

    Unlike a Focus Sash this does NOT require full health and is not consumed, which is
    what it pays for by being a chance rather than a certainty.
    """
    if get_active_item(defender, magic_room) != 'focus-band':
        return False
    return rng.random() < FOCUS_BAND_ODDS


def shell_bell_heal(attacker, damage, magic_room=False):
    """How much a Shell Bell gives back for the damage just dealt, or 0."""
    if attacker is None or damage <= 0:
        return 0
    if get_active_item(attacker, magic_room) != 'shell-bell':
        return 0
    return max(1, math.floor(damage * SHELL_BELL_FRACTION))


def big_root_bonus(attacker, magic_room=False):
    """Big Root's multiplier on anything the holder DRAINS back."""
    if get_active_item(attacker, magic_room) != 'big-root':
        return 1.0
    return BIG_ROOT_DRAIN_BONUS


def bind_turns(attacker, magic_room=False, rng=random):
    """How long a bind laid by this attacker lasts. A Grip Claw pins it at the maximum."""
    if get_active_item(attacker, magic_room) == 'grip-claw':
        return GRIP_CLAW_TURNS
    return rng.randint(4, 5)


def bind_damage_multiplier(binder, magic_room=False):
    """A Binding Band doubles the per-turn chip of whatever ITS HOLDER tied down."""
    if get_active_item(binder, magic_room) != 'binding-band':
        return 1.0
    return BINDING_BAND_MULTIPLIER


def loaded_dice_floor(attacker, magic_room=False):
    """
    The fewest hits a multi-strike move may roll for this attacker.

    Loaded Dice only ever raises the floor, so a move that would have hit five times
    still hits five - the dice are loaded, not fixed.
    """
    if get_active_item(attacker, magic_room) != 'loaded-dice':
        return 0
    return LOADED_DICE_MIN_HITS


# ==========================================
# ITEM PHASE 6: SPECIES-SPECIFIC GEAR
# ==========================================
# Sixteen items that all say "a flat effect, but only for this species". Three of the
# four groups fold into a function that already exists - stat_multiplier_for, the crit
# stage, and the type-booster line in the damage stack - and the fourth is the Rusted
# Sword's form machinery, which lives in the engine because it needs the database.

def true_species_name(pokemon):
    """
    The BASE species name, seeing through a disguise and ignoring the form suffix.

    'marowak-alola' and 'giratina-altered' both answer as their base, which is what lets
    an Alolan Marowak swing a Thick Club. Illusion is seen through for the same reason
    true_pokedex_id sees through it: a disguise is meant to fool a trainer, not the
    physics, and a Zoroark wearing Pikachu's face must not be handed Pikachu's Light Ball.
    """
    if not pokemon:
        return ''
    real = pokemon.get(ILLUSION_MARKER)
    name = (real or pokemon).get('name') or ''
    return str(name).lower().split('-')[0].strip()


def species_stat_multiplier(pokemon, stat, magic_room=False):
    """
    What a species-gated ITEM does to one of its holder's own stats.

    The item twin of stat_multiplier_for's table, and read from inside it - so a Light
    Ball and a Huge Power multiply together rather than one quietly replacing the other.
    """
    if not pokemon:
        return 1.0

    row = SPECIES_STAT_ITEMS.get(get_active_item(pokemon, magic_room))
    if not row or stat not in row['stats']:
        return 1.0
    if true_species_name(pokemon) not in row['species']:
        return 1.0
    # The two Ditto powders, whose descriptions both end "lost after transforming".
    if row.get('lost_on_transform') and (pokemon.get('volatile_statuses') or {}).get('transformed'):
        return 1.0
    return row['stats'][stat]


def species_crit_stage(attacker, magic_room=False):
    """The Lucky Punch and the Stick: crit stages owed to a species-gated item, or 0."""
    if not attacker:
        return 0
    row = SPECIES_CRIT_ITEMS.get(get_active_item(attacker, magic_room))
    if not row or true_species_name(attacker) not in row['species']:
        return 0
    return row['stages']


def species_type_boost(attacker, move_type, magic_room=False):
    """
    The three Orbs: 1.2 to two named elements, but only in the right hands.

    Apart from TYPE_BOOST_ITEMS because that table is one item to ONE element, and
    because a plate held by the wrong species still works while an Orb does nothing at
    all - which is the whole difference between an enhancer and a signature item.
    """
    if not attacker or not move_type:
        return 1.0
    row = SPECIES_TYPE_BOOST_ITEMS.get(get_active_item(attacker, magic_room))
    if not row or true_species_name(attacker) != row['species']:
        return 1.0
    # ITEM PHASE 10: `types: None` means every element. The three Orbs each name two;
    # Ogerpon's masks lift all of its moves, which is the same item shape with the
    # element list left open rather than a second table.
    if row['types'] is None:
        return SPECIES_ORB_MULTIPLIER
    return SPECIES_ORB_MULTIPLIER if str(move_type).lower() in row['types'] else 1.0


def species_form_for(pokemon, magic_room=False):
    """
    The form a species-gated item wants its holder to take, or None.

    The Griseous Orb and the four nectars. Returns the row rather than doing the work,
    because reshaping a specimen needs the species tables and this module is synchronous
    - the same split the Crowned forms and the Primal reversions already use.
    """
    if not pokemon:
        return None
    row = SPECIES_FORM_ITEMS.get(get_active_item(pokemon, magic_room))
    if not row or true_species_name(pokemon) != row['species']:
        return None
    # Already wearing it. Without this a switch-out and back in would re-derive the stats
    # from an already-transformed specimen, which is the bug the Crowned guard exists for.
    if (pokemon.get('name') or '').lower() == row['form']:
        return None
    return row


def item_priority_tier(attacker, magic_room=False):
    """
    Where the attacker's ITEM puts it inside its bracket: 1 first, -1 last, 0 no opinion.

    Quick Claw rolls; Lagging Tail and Full Incense are certain. Returned separately from
    the ability answer so that priority_tier can decide which of the two wins rather than
    having one silently overwrite the other.
    """
    item = get_active_item(attacker, magic_room)

    if item in LAST_IN_BRACKET_ITEMS:
        return -1
    if item == 'quick-claw' and random.random() < QUICK_CLAW_ODDS:
        return 1
    return 0


def mimicry_types(pokemon, terrain='none'):
    """
    The elements this specimen counts as, with Mimicry's terrain swap applied.

    Returned rather than written onto the specimen: the change is meant to last exactly
    as long as the terrain, and there is nowhere yet that would put the original types
    back when the terrain expires. That means it reaches the damage calculation - STAB
    and the type chart - but not the places that read `types` directly, such as hazard
    immunity. Documented rather than hidden.
    """
    stored = list((pokemon or {}).get('types') or [])
    if not pokemon or get_active_ability(pokemon) != 'mimicry':
        return stored
    worn = MIMICRY_TYPES.get(terrain)
    return [worn] if worn else stored


def makes_contact(move, attacker=None):
    """
    Whether this strike physically touches the target.

    The proxy here used to be the damage class - physical meant contact - and the comment
    beside it said that was "close enough for every move that matters here". It was not:
    102 of this database's physical moves make no contact at all, so an Earthquake
    triggered Flame Body, Static, Poison Point, Rough Skin, Iron Barbs, Cute Charm,
    Pickpocket, a Rocky Helmet and a Sticky Barb. Seven special moves were wrong the other
    way, Grass Knot and Draining Kiss among them.

    CONTACT_MOVES is the real per-move flag, so this is a lookup rather than a guess.

    A Max Move never makes contact whatever it was built from, and it keeps its base
    move's NAME in the payload - so the marker is asked before the table, or a Max Move
    built on Tackle would still be read as Tackle.
    """
    if (move or {}).get(MAX_MOVE_MARKER):
        return False
    if attacker is not None and get_active_ability(attacker) in NO_CONTACT_ABILITIES:
        return False
    # ITEM PHASE 5: Protective Pads and the Punching Glove both stop the holder TOUCHING
    # what it hits, which is Long Reach's slot exactly - so Rough Skin, Static, a Rocky
    # Helmet and Pickpocket are all spared in one line rather than four.
    if attacker is not None and get_active_item(attacker) in NO_CONTACT_ITEMS:
        return False
    return normalise_move_name((move or {}).get('name')) in CONTACT_MOVES


def apply_max_sanitisation(move):
    """
    The two things every Max Move owes that the engines' own sanitisation passes missed.

    Both engines build a Max Move by wiping the base move's ailment, status, stat change,
    healing and drain and then injecting the Max power - and both forgot the PRIORITY. A
    Max Geyser built on Aqua Jet therefore carried Aqua Jet's +1, which Psychic Terrain
    duly turned away as a priority attack. Max Guard is the one that keeps a priority, and
    it keeps Protect's own.

    Contact goes the same way: a Max Move touches nothing, whatever it was built from.
    Marked on the payload rather than by renaming it, because the PvE engine deliberately
    keeps the base move's name and only the display string changes.
    """
    if not move:
        return move
    is_guard = move.get('name') == 'max-guard' or move.get('class') == 'status'
    move['priority'] = MAX_GUARD_PRIORITY if is_guard else MAX_MOVE_PRIORITY
    move[MAX_MOVE_MARKER] = True
    return move


def secondary_chance(base_chance, attacker, defender):
    """
    The odds of a move's SECONDARY effect firing, once the abilities have had their say.

    Serene Grace doubles it; Shield Dust refuses it outright. A move's primary effect -
    a status move whose whole point is the status - is not a secondary effect, so
    callers pass those through without consulting this.
    """
    # ITEM PHASE 5: a Covert Cloak is a Shield Dust you can buy, so it answers here
    # rather than anywhere of its own.
    if (get_active_ability(defender) in SECONDARY_IMMUNE_ABILITIES
            or get_active_item(defender) in SECONDARY_IMMUNE_ITEMS):
        return 0
    return base_chance * SECONDARY_CHANCE_ABILITIES.get(get_active_ability(attacker), 1.0)


def evasion_multiplier(defender, weather='none'):
    """
    What an ability does to its owner's evasion. Higher means harder to hit.

    Returned as a number to DIVIDE the attacker's chance by, so 1.25 is a quarter harder
    rather than a quarter easier.
    """
    trait = EVASION_MULTIPLIER_ABILITIES.get(get_active_ability(defender))
    if not trait:
        return 1.0
    if 'weather' in trait and weather not in trait['weather']:
        return 1.0
    if trait.get('confused') and 'confusion' not in (defender.get('volatile_statuses') or {}):
        return 1.0
    return trait['multiplier']


def hit_chance(attacker, defender, move, weather='none', magic_room=False):
    """
    The percentage chance this move connects, before the roll is made.

    One function for both engines. They each had their own copy of the stage maths, and
    the copies were identical only by luck - Block 3 found the speed pair had already
    drifted, and this block is the same shape of risk.

    Callers still decide whether to consult it at all: OHKO moves, No Guard, Lock-On and
    a standing Glaive Rush all skip the roll entirely, and those checks stay with the
    engines because they also decide what the log says.
    """
    # Block 22: the thrower's own sky, so a Mega Sol aims by its personal sunlight. That
    # reaches the weather-gated evasion abilities - a Sand Veil is not hiding anybody
    # from a specimen whose move reads a cloudless sky - and, since the weather-gated
    # ACCURACY table below reads the same variable, its Thunder is dragged down to 50
    # exactly as a real sun would drag it.
    weather = personal_weather(attacker, weather)
    move_name = (move or {}).get('name')

    move_acc = (move or {}).get('accuracy')
    if not isinstance(move_acc, int):
        move_acc = 100

    # Wonder Skin drags an incoming status move down to a coin flip, and only downwards
    if ((move or {}).get('class') == 'status'
            and get_active_ability(defender) == 'wonder-skin'
            and move_acc > WONDER_SKIN_ACCURACY):
        move_acc = WONDER_SKIN_ACCURACY

    # A sky that suits the move skips the accuracy check ALTOGETHER - so this returns
    # rather than setting the figure to 100 and carrying on. Everything below would
    # otherwise still get a say: an evasion boost, a lowered accuracy stage, a Sand Veil.
    # A Thunder in the rain is not 100% accurate, it is unaimed and it lands.
    if sky_never_misses(move_name, weather):
        return 100.0

    # ...and a sky that does not suit it just makes it worse.
    move_acc = sky_accuracy(move_name, move_acc, weather)

    acc_stage = (attacker.get('stat_stages') or {}).get('accuracy', 0)
    eva_stage = (defender.get('stat_stages') or {}).get('evasion', 0)
    # Telekinesis holds the target up where it cannot dodge
    if (defender.get('volatile_statuses') or {}).get('telekinesis'):
        eva_stage = 0

    # Mind's Eye ignores whatever the target has done to its evasion, and refuses to have
    # its own accuracy lowered.
    if get_active_ability(attacker) in EVASION_IGNORING_ABILITIES:
        eva_stage = min(0, eva_stage)
        acc_stage = max(0, acc_stage)

    # BLOCK 21: Unaware discards the OTHER side's stage outright, in both directions -
    # where Mind's Eye above only discards the half that would hurt its owner.
    if get_active_ability(attacker) in UNAWARE_ABILITIES:
        eva_stage = 0
    if get_active_ability(defender) in UNAWARE_ABILITIES:
        acc_stage = 0

    net_stage = max(-6, min(6, acc_stage - eva_stage))
    if net_stage >= 0:
        stage_mod = (3.0 + net_stage) / 3.0
    else:
        stage_mod = 3.0 / (3.0 + abs(net_stage))

    # ITEM PHASE 4: the lenses and the powders, folded in as the item twin of the two
    # ability factors either side of them. Multiplied rather than special-cased so a Wide
    # Lens and a Compound Eyes stack, and a Bright Powder answers both of them at once.
    # A Micle Berry, folded in beside the lenses because it is the same kind of factor -
    # a flat multiplier on the thrower's aim. The Gen V+ figure: a fifth more accuracy
    # rather than Gen IV's guaranteed hit, which would have made it strictly better than
    # every other pinch berry rather than a choice against them.
    micle = MICLE_ACCURACY_MULTIPLIER if has_action_marker(attacker, MICLE_MARKER) else 1.0

    return (move_acc * stage_mod
            * accuracy_multiplier(attacker)
            * micle
            * item_accuracy_multiplier(attacker, defender, magic_room)
            / max(0.01, evasion_multiplier(defender, weather))
            / max(0.01, item_evasion_multiplier(defender, magic_room)))


def effective_weight(pokemon):
    """
    How heavy the specimen counts as, for Grass Knot, Low Kick, Heat Crash and Heavy Slam.

    Heavy Metal doubles it and Light Metal halves it, so this wraps the species lookup
    rather than every caller remembering to ask.
    """
    # Asked of the REAL species, not the borrowed one. An Illusion fools the trainer;
    # letting it fool Grass Knot as well would have the disguise announce itself the
    # first time somebody weighed it.
    raw = get_species_weight({'pokedex_id': true_pokedex_id(pokemon)})
    factor = WEIGHT_MULTIPLIER_ABILITIES.get(get_active_ability(pokemon), 1.0)
    # ITEM PHASE 9: the Float Stone, which is the same question asked of an item. It
    # stacks with Light Metal rather than replacing it, exactly as the games have it.
    factor *= WEIGHT_ITEMS.get(get_active_item(pokemon), 1.0)
    return max(0.1, raw * factor)


def resolve_combat_stats(move_name, move_class, attacker, defender, wonder_room=False, magic_room=False,
                         ignore_boosts=False, weather='none', terrain='none', party=None):
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

    # Kept unfiltered for Foul Play, which borrows the target's ATTACK - an offensive
    # stat, so it needs the offensive crit rule rather than the defensive one applied
    # to everything else the defender owns.
    d_stages_raw = d_stages

    if ignore_boosts:
        a_stages = {k: max(0, v) for k, v in a_stages.items()}
        d_stages = {k: min(0, v) for k, v in d_stages.items()}
        d_stages_raw = {k: max(0, v) for k, v in d_stages_raw.items()}

    # BLOCK 21: UNAWARE reads the other side's sheet as though nothing had been done to
    # it - both directions, unlike the crit filter above, which only discards changes
    # that would make the hit weaker. Applied after that filter for exactly that reason:
    # blanking is the stronger claim of the two.
    #
    # Which stages it covers depends on which end of the move its owner is standing. An
    # Unaware attacker ignores the target's WALLS and nothing else - notably not the
    # target's Attack, which is why Foul Play's borrowed stage is untouched here.
    if get_active_ability(attacker) in UNAWARE_ABILITIES:
        d_stages = {k: (0 if k in UNAWARE_DEFENSIVE_STATS else v)
                    for k, v in d_stages.items()}

    if get_active_ability(defender) in UNAWARE_ABILITIES:
        blanked = set(UNAWARE_OFFENSIVE_STATS)
        # Body Press attacks with Defense, so for that move Defense IS the offensive
        # stage and an Unaware wall ignores it too.
        if move_name == 'body-press':
            blanked.add('defense')
        a_stages = {k: (0 if k in blanked else v) for k, v in a_stages.items()}

    phys_atk = apply_stat_stage(attacker.get('stats', {}).get('attack', 50), a_stages.get('attack', 0))
    spec_atk = apply_stat_stage(attacker.get('stats', {}).get('sp_atk', 50), a_stages.get('sp_atk', 0))
    phys_def = apply_stat_stage(defender.get('stats', {}).get('defense', 50), d_stages.get('defense', 0))
    spec_def = apply_stat_stage(defender.get('stats', {}).get('sp_def', 50), d_stages.get('sp_def', 0))

    # Flat ability multipliers (Huge Power, Marvel Scale, Defeatist...). Applied AFTER the
    # stages, which is where the real formula puts them, and to the stat itself rather
    # than the damage - so Body Press swinging with Defense picks up Marvel Scale, and a
    # Psyshock aimed at physical Defense picks up Fur Coat's owner's Defense boost.
    # Each side is handed the OTHER as `opponent`, which is what lets the Ruin quartet
    # press on stats that are not its owner's. Only the ATTACKER is handed the party:
    # Supreme Overlord counts its own fallen, and the two offensive lines are the only
    # ones it touches.
    phys_atk = math.floor(phys_atk * stat_multiplier_for(attacker, 'attack', weather, terrain, defender, party, magic_room))
    spec_atk = math.floor(spec_atk * stat_multiplier_for(attacker, 'sp_atk', weather, terrain, defender, party, magic_room))
    phys_def = math.floor(phys_def * stat_multiplier_for(defender, 'defense', weather, terrain, attacker, magic_room=magic_room))
    spec_def = math.floor(spec_def * stat_multiplier_for(defender, 'sp_def', weather, terrain, attacker, magic_room=magic_room))

    # Assault Vest reinforces the Sp. Def stat itself, so it follows that stat rather than
    # the move - a Psyshock aimed at physical Defense correctly ignores the vest.
    if get_active_item(defender, magic_room) == 'assault-vest':
        spec_def = math.floor(spec_def * 1.5)

    # ITEM PHASE 5: an Eviolite reinforces BOTH walls, and only for a specimen that still
    # has somewhere to evolve to. Beside the vest because it is the same shape of thing -
    # a flat factor on the stat rather than on the move - and before Wonder Room for the
    # same reason the vest is: the room swaps which wall is standing where, and both of
    # these belong to the wall rather than to the position.
    _evio = eviolite_multiplier(defender, 'defense', magic_room)
    if _evio != 1.0:
        phys_def = math.floor(phys_def * _evio)
        spec_def = math.floor(spec_def * eviolite_multiplier(defender, 'special-defense',
                                                             magic_room))

    # 🚨 WONDER ROOM swaps which of the target's two walls is standing where
    if wonder_room:
        phys_def, spec_def = spec_def, phys_def

    # --- FOUL PLAY: swings with the TARGET's Attack ---
    # The target's own boosts come along with it, which is the point of the move - but a
    # critical hit still discards boosts that would make the hit weaker, so this reads
    # the same filtered stages everything else here does.
    if move_name == 'foul-play':
        borrowed = apply_stat_stage(defender.get('stats', {}).get('attack', 50),
                                    d_stages_raw.get('attack', 0))
        # The target's Huge Power comes along with its Attack, because it IS the target's
        # Attack that is being swung. Its Supreme Overlord does not: only one party is
        # threaded this far down, and it is the attacker's. Stated rather than hidden.
        borrowed = math.floor(borrowed * stat_multiplier_for(defender, 'attack', weather, terrain, attacker, magic_room=magic_room))
        return borrowed, phys_def, 'physical'

    # --- BODY PRESS: swings with the user's own Defense ---
    if move_name == 'body-press':
        body_press_atk = apply_stat_stage(attacker.get('stats', {}).get('defense', 50), a_stages.get('defense', 0))
        # Likewise Marvel Scale, which is a Defense boost the move is now attacking with
        body_press_atk = math.floor(
            body_press_atk * stat_multiplier_for(attacker, 'defense', weather, terrain, defender, magic_room=magic_room))
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

    A thin wrapper, and the whole of Block 21's mould-breaker family. The marker goes
    onto the DEFENDER for the length of this one call and comes off in a `finally`, so
    the forty-odd defensive reads inside need no arguments they did not already have and
    the twenty early returns below cannot leak it. Everything else lives in
    _resolve_damage, which is this function as it has always been.

    __wrapped__ is set below the body, so `inspect.getsource(calculate_damage)` still
    hands back the formula rather than these eight lines. Nine suites read the damage
    formula that way to prove an ability is reachable at all, and none of them means
    this wrapper when it says "the damage formula".
    """
    token = begin_mould_break(attacker, defender)
    try:
        # Block 22. The sky the ATTACKER's move reads, which is the ordinary one for
        # everybody but a Mega Sol. Substituted here rather than inside, because weather
        # is already a parameter and every use of it below then follows for free.
        return _resolve_damage(attacker, defender, move,
                               personal_weather(attacker, weather), terrain,
                               target_hazards, user_hazards, wonder_room, gravity,
                               magic_room, user_party, field)
    finally:
        end_mould_break(defender, token)


def _resolve_damage(attacker, defender, move, weather='none', terrain='none', target_hazards=None, user_hazards=None, wonder_room=False, gravity=False, magic_room=False, user_party=None, field=None):
    """
    The damage calculation itself. Reached only through calculate_damage, which scopes
    the mould-breaker marker around it.
    """
    damage = 0
    msg = ""
    inflicted_status = None
    stat_changes = [] 
    # Bound here as well as inside the damage branch: a STATUS move never reaches
    # that branch, and Block 14's reaction hook asks about crits on every path.
    crit_occurred = False
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
        # Stance Change reads the move being USED, not the damage it deals - and this
        # branch returns long before the form hook near the end of the function, which
        # is why Aegislash only ever drew its blade and never raised its shield. Banked
        # here, before the success roll, because the games change forme when the move is
        # used rather than when it works: a King's Shield that fails to a repeated-use
        # roll still puts Aegislash back in Shield Forme.
        _stance = stance_form_for(attacker, move_name, move)
        if _stance:
            request_form_flip(attacker, _stance, 'changed stance')

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
    # 🔇 FAMILY SHUT-OUTS AND SMOTHERED EXPLOSIONS
    # ==========================================
    # Placed with the other refusals, well before the damage roll: these stop the move
    # happening at all rather than reducing what it does.
    damper = smothers_explosion(attacker, defender) if is_explosive_move(move_name) else None
    if damper is not None:
        return 0, (f"💧 {damper['name'].capitalize()}'s "
                   f"{pretty_ability(get_active_ability(damper))} smothered the "
                   f"explosion!"), 'none', [], 0

    shut_out = move_family_blocked(defender, move_name)
    if shut_out:
        return 0, (f"🚫 {defender['name'].capitalize()}'s {pretty_ability(shut_out)} "
                   f"shut the attack out!"), 'none', [], 0

    # Good as Gold refuses a whole category rather than a family. Self-aimed moves are
    # untouched: it answers what is thrown AT it, not what its user does to itself.
    if (move_class == 'status' and refuses_status_moves(defender)
            and 'user' not in str(move_target)):
        return 0, (f"🥇 {defender['name'].capitalize()}'s "
                   f"{pretty_ability(get_active_ability(defender))} left it "
                   f"completely unbothered!"), 'none', [], 0

    # A Prankster-boosted status move simply fails against a Dark type. Checked beside
    # Good as Gold because it is the same shape of refusal - a status move that never
    # happens - and it has to land before anything the move would have done.
    if prankster_is_snubbed(attacker, defender, dict(move, target=move_target)):
        return 0, (f"🌑 {defender['name'].capitalize()} is Dark - it paid no attention "
                   f"to the sneaky move!"), 'none', [], 0

    # ==========================================
    # 2. CONTAINMENT FIELD COLLISION
    # ==========================================
    active_shield = defender['volatile_statuses'].get('protect_type', 'protect')
    shield_stops_this = shield_blocks(active_shield, move_class, move.get('priority'), move_target,
                                      move.get('name'))

    if defender['volatile_statuses'].get('protected') and shield_stops_this and 'user' not in move_target:
        BYPASS_MOVES = ['feint', 'phantom-force', 'shadow-force', 'hyperspace-fury', 'hyperspace-hole']
        # Unseen Fist and Piercing Drill reach through a shield with anything that touches
        punches_through = (get_active_ability(attacker) in PROTECT_PIERCING_ABILITIES
                           and makes_contact(move, attacker))

        if move_name in BYPASS_MOVES or punches_through:
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

    # ==========================================
    # 🎲 MOVES THAT DECIDE THEIR OWN ELEMENT
    # ==========================================
    # All of these must settle here, above the type chart, or they would rewrite an
    # element that nothing downstream ever looks at.
    condition_power = None

    if move_name == 'hidden-power':
        move_type = hidden_power_type(attacker)

    elif move_name == 'weather-ball':
        if weather in WEATHER_BALL_TYPES:
            move_type = WEATHER_BALL_TYPES[weather]
            condition_power = CONDITION_BALL_MULTIPLIER

    elif move_name == 'terrain-pulse':
        # Terrain cannot reach a specimen that is not standing on it.
        if terrain in TERRAIN_PULSE_TYPES and is_grounded(attacker, gravity):
            move_type = TERRAIN_PULSE_TYPES[terrain]
            condition_power = CONDITION_BALL_MULTIPLIER

    # 🚨 TERA BLAST takes the user's Tera type once Terastallized, Normal otherwise
    if move_name == 'tera-blast' and attacker.get('tera_type'):
        move_type = attacker['tera_type']

    # ==========================================
    # 🎭 THE -ATE FAMILY, AND THE REST OF THE TYPE REWRITES
    # ==========================================
    # This has to be the LAST word on move_type, and it has to be here: the immunity
    # table and the type chart are both a few lines below, and the Natural Gift bug was
    # exactly a rewrite that landed after them.
    ate_multiplier = 1.0
    rewrite = TYPE_REWRITE_ABILITIES.get(atk_ability)
    if rewrite and move.get('class') != 'status':
        applies = (rewrite.get('sound') and is_sound_move(move_name)) or \
                  (rewrite.get('from') in ('*', move_type))
        if applies and move_type != rewrite['to']:
            move_type = rewrite['to']
            ate_multiplier = rewrite['multiplier']

    # Protean and Libero: the user becomes the element it is about to throw
    if atk_ability in PROTEAN_ABILITIES and move.get('class') != 'status':
        if (attacker.get('types') or []) != [move_type]:
            attacker['types'] = [move_type]
            msg += f" 🎨 {attacker['name'].capitalize()} became the {move_type.title()} type!"

    # Mimicry wears the terrain. Applied as an override for THIS calculation rather than
    # written onto the specimen: the type is meant to last only as long as the terrain,
    # and there is nowhere yet that would put it back when the terrain expires.
    atk_types = mimicry_types(attacker, terrain)
    def_types = mimicry_types(defender, terrain)

    # There WAS a second copy of the crash here, in the main flow and guarded by
    # nothing. Jump Kick and High Jump Kick crash when they MISS or when they are
    # blocked - a connecting one is a 100/130 power Fighting move - so an unguarded copy
    # meant both of them dealt zero damage every single time and took half the user's
    # max HP for the privilege. The two legitimate copies are still where they belong:
    # the Protect branch above, and the accuracy-miss branch in each engine.
    #
    # Found by an item scan, of all things: the scan picked jump-kick as its Fighting
    # probe, and every Fighting-type booster read as doing nothing because the move it
    # was being measured with could not deal damage at all.

    if move.get('class') != 'status':
        # A specimen held off the ground cannot be reached by Ground moves.
        #
        # This block used to ask `is_grounded` and then THROW THE ANSWER AWAY unless the
        # cause was Magnet Rise or Telekinesis. The other two causes each had a second
        # route that happened to save them - a Flying type is 0x on the type chart, and
        # Levitate is in the immunity table below - so the hole showed up in exactly one
        # place: the AIR BALLOON, which has neither. It read as implemented everywhere
        # (it is in `is_grounded`, it is in ONE_USE_ITEMS, it is on sale) and a specimen
        # holding one took full damage from Earthquake.
        #
        # Asked once now, and the cause only decides the wording.
        # **THOUSAND ARROWS ANSWERS THREE SEPARATE REFUSALS, NOT ONE.** The chart's
        # ground-vs-flying zero is handled by IMMUNITY_PIERCING_MOVES; this block and the
        # immunity table below are the other two, and a move that opened only one of them
        # would still be refused by whichever was left.
        drags_down = move_name in GROUNDING_MOVES
        # **ASKED BEFORE THE HIT LANDS.** An Air Balloon pops on any damaging move, so by
        # the time the grounding fires the hands are empty and `is_raised` says no - the
        # target ends up grounded either way, but nothing announces it, and the reason is
        # an unrelated item having burst. Read here, where it is still true.
        was_raised = drags_down and is_raised(defender, def_ability)

        if move_type == 'ground' and not is_grounded(defender, gravity) \
                and not (drags_down and is_raised(defender, def_ability)):
            lifted = (defender.get('volatile_statuses') or {})
            if lifted.get('magnet_rise') or lifted.get('telekinesis'):
                return 0, (f"🪂 {defender['name'].capitalize()} is airborne - the attack "
                           f"passed harmlessly underneath!"), None, [], 0
            if get_active_item(defender, magic_room) == 'air-balloon':
                return 0, (f"🎈 {defender['name'].capitalize()}'s Air Balloon kept it "
                           f"clear of the attack!"), None, [], 0
            # Flying types and Levitate fall through deliberately: both are answered
            # below, by the type chart and the immunity table, with their own wording.

        immunity_data = BIOLOGICAL_TRAITS['immunities'].get(def_ability)
        
        # If the defender has an immunity AND the incoming attack matches its element.
        #
        # **LEVITATE IS ANSWERED HERE RATHER THAN ABOVE**, so the airborne exemption has
        # to be made a second time - and for two different reasons. A move that drags a
        # levitating specimen down reaches it; and a specimen ALREADY dragged down is not
        # levitating any more, so the ordinary Earthquake that follows reaches it too.
        # Without the second clause, Thousand Arrows grounds a Gengar and its own ability
        # goes on refusing every Ground move afterwards.
        _levitating = def_ability in LEVITATION_ABILITIES
        if immunity_data and move_type == immunity_data['type'] \
                and not (_levitating
                         and (drags_down or not is_raised(defender, def_ability))):
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
            
    # ==========================================
    # WIND RIDER
    # ==========================================
    # Answered here rather than in the reaction table, because its trigger is being
    # MISSED rather than being hurt: it refuses the wind move outright and takes a
    # stage for it. The boost rides out on the payload so it meets Block 8's resolver
    # like every other stage change.
    if (refuses_wind(defender) and is_wind_move(move_name)
            and move.get('class') != 'status'):
        _gained, _stages = WIND_RIDER_BOOST
        return 0, (f"\U0001f32c\ufe0f {defender['name'].capitalize()} rode the wind "
                   f"and was unharmed!"), None, [(TARGET_DEFENDER_SELF, _gained,
                                                  _stages)], 0

    # ==========================================
    # DISGUISE AND ICE FACE
    # ==========================================
    # The costume takes the hit. Answered up here with the other immunities because
    # the move must not be allowed to happen at all - anything further down would be
    # reading a hit that never landed.
    _costume = hit_breaks_form(defender, move)
    if _costume:
        _broken, _toll = _costume
        request_form_flip(defender, _broken, 'was knocked out of its disguise')
        if _toll:
            defender['current_hp'] = max(1, defender['current_hp'] - _toll)
        return 0, (f"\U0001f3ad {defender['name'].capitalize()}'s disguise took "
                   f"the hit!"), None, [], 0

    type_multiplier = 1.0
    for def_type in def_types:
        step = TYPE_CHART.get(move_type, {}).get(def_type, 1.0)
        # Scrappy and Mind's Eye reach Ghost types with Normal and Fighting, which the
        # chart records as a flat immunity.
        if (step == 0 and def_type == 'ghost' and move_type in ('normal', 'fighting')
                and atk_ability in GHOST_PIERCING_ABILITIES):
            step = 1.0
        # ITEM PHASE 9: the same zero, opened from the DEFENDER's side instead. A Ring
        # Target gives up every immunity its holder has; an Iron Ball gives up Ground
        # only, because it grounds its holder rather than making it ordinary.
        if step == 0 and pierces_own_immunity(defender_item, move_type):
            step = 1.0
        # ...and the third: the MOVE. Nihil Light walks through Fairy's refusal of
        # Dragon and lands for NEUTRAL damage. Only this step is rewritten, so the
        # other half of a dual type still has its say.
        if step == 0 and move_pierces_immunity(move_name, move_type, def_type):
            step = 1.0
        # ...and the fourth: the DEFENDER has been knocked out of the air and stays
        # there. Being grounded has to open the chart as well as `is_grounded`, or
        # Thousand Arrows drags a Salamence down and the Earthquake that follows still
        # passes harmlessly underneath it - which is the whole point of dragging it down.
        if (step == 0 and move_type == 'ground' and def_type == 'flying'
                and (defender.get('volatile_statuses') or {}).get(SMACKED_DOWN)):
            step = 1.0
        type_multiplier *= step


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
        elif defender_invuln == 'air' and move_name in GROUNDING_MOVES:
            # Thousand Arrows reaches a specimen mid-Fly or mid-Bounce and brings it
            # down, which cancels the move it was charging. Sky Drop is in the air too
            # and is hit the same way, but is NOT knocked down - that exception lives
            # with the grounding itself, below, rather than here.
            pass
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
    # 🐢 TERA SHELL
    # ==========================================
    # Placed here, after every other adjustment to the chart, because it OVERWRITES the
    # result rather than multiplying it - anything applied afterwards would be lost. It
    # has to land before the multiplier is read by Filter's condition or by the damage
    # formula itself, which is the same rule the Block 5 rewrites obey.
    type_multiplier = tera_shell_multiplier(defender, move_class, type_multiplier,
                                            def_ability)


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
        # ...and so does a Sticky Hold, on either end of the swap. Half a Trick is not a
        # thing the move can do.
        if item_is_stuck(defender) or item_is_stuck(attacker):
            return 0, (f"But it failed! {defender['name'].capitalize()}'s grip is "
                       f"too sticky!"), 'none', [], 0

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
        if item_is_stuck(defender):
            return 0, (f"But it failed! {defender['name'].capitalize()}'s Sticky Hold "
                       f"kept hold of its {pretty_item(theirs)}!"), 'none', [], 0

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

    # ==========================================
    # 👥 MOVES THAT NEED AN ALLY ON THE FIELD
    # ==========================================
    # One specimen a side means these have nothing to work with - which is exactly what
    # they do in a single battle in the games, so the failure is the correct outcome
    # rather than a gap.
    if move_name in DOUBLES_ONLY_MOVES:
        return 0, f"But it failed! {DOUBLES_ONLY_MOVES[move_name].capitalize()}!", 'none', [], 0

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

    if move_name == 'bide':
        volatiles = attacker.setdefault('volatile_statuses', {})
        if not volatiles.get('bide'):
            begin_bide(attacker)
            return 0, (f"🛡️ {attacker['name'].capitalize()} is storing energy!"), 'none', [], 0

        volatiles['bide'] -= 1
        if volatiles['bide'] > 0:
            return 0, (f"🛡️ {attacker['name'].capitalize()} is still storing energy!"), 'none', [], 0

        banked = volatiles.pop('bide_damage', 0) or 0
        volatiles.pop('bide', None)
        if banked <= 0:
            return 0, "But it failed! It had taken nothing to give back!", 'none', [], 0

        # Handed back raw: Bide's payout is not an elemental hit, so it neither gains
        # STAB nor answers to the type chart.
        return (banked * BIDE_MULTIPLIER,
                f"💥 {attacker['name'].capitalize()} unleashed everything it had stored!",
                'none', [], 0)

    if move_name == 'transform':
        became = apply_transform(attacker, defender)
        if not became:
            return 0, "But it failed! There was no shape it could take!", 'none', [], 0
        return 0, became, 'none', [], 0

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

    # Comeuppance is Metal Burst in Dark clothing - same one-and-a-half times whatever
    # was last dealt to the user, and the same failure when nothing was.
    if move_name == 'comeuppance':
        if attacker.get('last_damage_taken', 0) > 0:
            return (math.floor(attacker['last_damage_taken'] * RETALIATION_MULTIPLIER),
                    "It paid the attacker back in kind!", 'none', [], 0)
        return 0, "But it failed! Nothing had struck it!", 'none', [], 0
    
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
        # These moves instantly halve the defender's current HP - unless a Tapunium Z
        # has turned Nature's Madness into Guardian of Alola, which takes three quarters.
        # The share is carried on the move rather than checked against a crystal here,
        # so this branch never has to know that Z-Crystals exist.
        share = move.get(Z_HP_FRACTION_KEY) or 0.5
        fixed_damage = max(1, math.floor(defender['current_hp'] * share))
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
    # Pay Day and Make It Rain shake loose money on the way past. Scattered even when the
    # blow is shrugged off, the way the games pay out for the attempt rather than the hit.
    if move_name in COIN_SCATTER_MOVES:
        shaken = scatter_coins(attacker, move_name)
        msg += f" 🪙 Coins scattered everywhere! ({shaken} to collect afterwards)"

    # Synchronoise only reaches something built like the user.
    if move_name == 'synchronoise' and not shares_a_type(attacker, defender):
        return 0, (f"But it failed! {defender['name'].capitalize()} shares no type with "
                   f"{attacker['name'].capitalize()}!"), 'none', [], 0

    # Spectral Thief robs the target of its boosts BEFORE swinging, so the stolen stages
    # are already the user's when the damage is worked out. Guarded on effectiveness: a
    # Ghost move cannot reach a Normal type, and a move that never lands steals nothing.
    if move_name == 'spectral-thief' and type_multiplier > 0:
        plundered = {stat: stage for stat, stage
                     in (defender.get('stat_stages') or {}).items() if stage > 0}
        if plundered:
            a_stages = attacker.setdefault('stat_stages', {})
            d_stages = defender.setdefault('stat_stages', {})
            for stat, stage in plundered.items():
                a_stages[stat] = min(MAX_STAT_STAGE, a_stages.get(stat, 0) + stage)
                d_stages[stat] = 0
            msg += (f" 👤 {attacker['name'].capitalize()} stole "
                    f"{defender['name'].capitalize()}'s boosts!")

    # Spit Up is the damaging end of the Stockpile family: it needs a bank to spend, and
    # empties it on the way out. Read before the power resolves, since resolving it is
    # what the bank is for.
    if move_name == 'spit-up' and not get_stockpile(attacker):
        return 0, "But it failed! It had nothing stockpiled!", 'none', [], 0

    # Beat Up reads the whole bench. resolve_dynamic_power is also called by the engines'
    # AI scorer, which has no party to hand it, so the roster is stashed on the user here
    # rather than added to that shared signature.
    if move_name == 'beat-up':
        attacker['_beat_up_party'] = user_party

    # Magnitude rolls its own tremor. It has NO stored power, so this has to happen above
    # the damage gate - rolling it further down, inside the block that gate guards, meant
    # the move never got in and quietly dealt nothing. Kept out of resolve_dynamic_power
    # because the move button calls that too, and would advertise a number the swing was
    # never going to use.
    if move_name == 'magnitude':
        item_power, magnitude_number = roll_magnitude()
        msg += f"📳 Magnitude {magnitude_number}! "

    dynamic_power = item_power or resolve_dynamic_power(move_name, attacker, defender)

    if move_name == 'spit-up':
        # Emptied here rather than after the swing, so the stages Stockpile granted are
        # handed back in the same breath the power is taken.
        stat_changes.extend(spend_stockpile(attacker)[1])

    # Bound HERE rather than only inside the branch below, because the reaction hooks at
    # the bottom of this function read it and there are damaging paths that never enter
    # the branch - a fixed-damage move with no stored power, for one. Reading it there
    # would be an UnboundLocalError on exactly those moves. The stored category is the
    # honest fallback: nothing recategorised it, so it resolved as what it says it is.
    effective_class = move_class

    if move.get('class') != 'status' and (move.get('power', 0) > 0 or dynamic_power):
        level = attacker.get('level', 50)
        
        # ==========================================
        # 🚨 STAT SELECTION
        # ==========================================
        # One resolver decides which Attack and Defense stats this move reads, applying
        # stat stages, Wonder Room and Assault Vest. `effective_class` is what the move
        # actually resolved as, which can differ from its stored category for Photon
        # Geyser and Shell Side Arm.
        a, d, effective_class = resolve_combat_stats(move_name, move_class, attacker, defender,
                                                     wonder_room, magic_room,
                                                     weather=weather, terrain=terrain,
                                                     party=user_party)

        # A critical hit reads the same stats with unfavourable stages stripped out. We
        # resolve that variant up front and express it as a ratio, so the multi-strike loop
        # can apply it per hit without recomputing the whole base damage.
        a_crit, d_crit, _ = resolve_combat_stats(move_name, move_class, attacker, defender,
                                                 wonder_room, magic_room, ignore_boosts=True,
                                                 weather=weather, terrain=terrain,
                                                 party=user_party)

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
        # Asked of the FORM, not the ability. Keyed on the ability, this handed the
        # stronger shuriken to every Greninja that had knocked nothing out yet.
        move_power = move.get('power', 0)
        if move_name == BATTLE_BOND_SHURIKEN and wears_bonded_form(attacker):
            move_power = BATTLE_BOND_SHURIKEN_POWER

        # 🚨 DYNAMIC POWER OVERRIDE
        # Replaces the stored power outright. Some of these ship with a misleading fixed
        # value (Eruption 150, Hex 65, Revenge 60), so the override is what actually makes
        # them respond to the battle state.
        if dynamic_power is not None:
            move_power = dynamic_power

        # A handful of G-Max moves have a fixed power that outranks the engines' 140
        if move.get('name') in GMAX_FIXED_POWER:
            move_power = GMAX_FIXED_POWER[move['name']]

        # Weather Ball and Terrain Pulse double when the conditions that gave them their
        # element are actually present. Set up above, beside the type rewrite, so the
        # element and the power can never disagree about whether it was in effect.
        if condition_power is not None:
            move_power *= condition_power


        # ==========================================
        # 🚨 CONDITIONAL POWER MULTIPLIERS
        # ==========================================
        atk_status = (attacker.get('status_condition') or {}).get('name')
        def_status = (defender.get('status_condition') or {}).get('name')

        # 1. Pathogen Synergies
        if move_name == 'facade' and atk_status in ['burn', 'poison', 'paralysis']:
            move_power *= 2
        elif move_name == 'wake-up-slap' and is_effectively_asleep(defender):
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
            
        stab_bonus = ADAPTABILITY_STAB if atk_ability == 'adaptability' else 1.5
        stab = stab_bonus if move_type in atk_types else 1.0

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

        # The -ate family's boost, decided when the element was rewritten far above
        ability_mod = ate_multiplier
        amplifier = BIOLOGICAL_TRAITS.get('damage_multipliers', {}).get(atk_ability)
        if amplifier:
            cond = amplifier['condition']
            mult = amplifier.get('multiplier', 1.0)
            if cond == 'contact' and move.get('class') == 'physical': ability_mod *= mult
            elif cond == 'punch' and move_name in PUNCH_MOVES: ability_mod *= mult
            elif cond == 'bite' and any(term in move_name for term in ['bite', 'fang', 'crunch']): ability_mod *= mult
            elif cond == 'pulse' and any(term in move_name for term in ['pulse', 'aura-sphere']): ability_mod *= mult
            elif cond == 'power_cap' and 0 < move_power <= amplifier['threshold']: ability_mod *= mult
            elif cond == 'move_type' and move_type in amplifier['types']: ability_mod *= mult
            elif cond == 'sound' and is_sound_move(move_name): ability_mod *= mult
            elif cond == 'recoil' and is_recoil_move(move_name, move): ability_mod *= mult
            elif cond == 'slicing' and is_slicing_move(move_name): ability_mod *= mult
            elif cond == 'super_effective' and type_multiplier > 1.0: ability_mod *= mult
            elif (cond == 'weather_type' and weather in amplifier['weather']
                  and move_type in amplifier['types']): ability_mod *= mult
            elif cond == 'not_very_effective' and 0 < type_multiplier < 1.0:
                ability_mod *= mult
            # "Moving last" is read off the TARGET: if it has already acted this turn,
            # the attacker is the one going second.
            elif cond == 'moving_last' and defender.get('acted_this_turn'):
                ability_mod *= mult
            # Stakeout. Fires on the opening turn too, since a lead has not finished a
            # turn on the field either - the same reading Fake Out already uses.
            elif cond == 'target_just_arrived' and is_first_turn_out(defender):
                ability_mod *= mult
            elif cond == 'gender':
                # Rivalry cuts both ways, and does nothing at all if either side's gender
                # is unknown - the same rule Attract obeys.
                a_gender, d_gender = attacker.get('gender'), defender.get('gender')
                if a_gender in ('M', 'F') and d_gender in ('M', 'F'):
                    ability_mod *= amplifier['same'] if a_gender == d_gender else amplifier['opposite']

        # The defensive half, keyed on the TARGET's ability. Punk Rock and Water Bubble
        # each blunt exactly what they amplify, so they appear in both tables.
        blunter = BIOLOGICAL_TRAITS.get('incoming_multipliers', {}).get(def_ability)
        # An ability may carry one rule or several. Fluffy is the reason for the list:
        # it halves contact damage AND doubles Fire damage, so a Fire punch meets both
        # and comes out level - which is how it reads in the games.
        for rule in ([blunter] if isinstance(blunter, dict) else (blunter or [])):
            cond = rule['condition']
            if cond == 'sound' and is_sound_move(move_name):
                ability_mod *= rule['multiplier']
            elif cond == 'move_type' and move_type in rule['types']:
                ability_mod *= rule['multiplier']
            # Fur Coat and Ice Scales blunt a whole category. Read off the category the
            # move RESOLVED as, so a Photon Geyser that turned physical meets Fur Coat.
            elif cond == 'move_class' and effective_class in rule['classes']:
                ability_mod *= rule['multiplier']
            # Filter, Solid Rock and Prism Armor take the edge off anything the chart
            # calls super effective, however super effective it was.
            elif cond == 'super_effective' and type_multiplier > 1.0:
                ability_mod *= rule['multiplier']
            # Multiscale and Shadow Shield, only while the target is untouched.
            elif (cond == 'at_full_hp'
                  and defender.get('current_hp', 0) >= defender.get('max_hp', 1)):
                ability_mod *= rule['multiplier']
            # Fluffy's contact half. Long Reach denies it the same way it denies Rough
            # Skin, because it is the same question being asked.
            elif cond == 'contact' and makes_contact(move, attacker):
                ability_mod *= rule['multiplier']

        # Dark Aura and Fairy Aura strengthen their element for EVERYONE on the field, so
        # this is read off both sides rather than off either table above.
        ability_mod *= aura_multiplier(move_type, attacker, defender)

        # A charge banked by Wind Power or Electromorphosis. Reading it spends it, so
        # this must sit where the move is definitely being thrown.
        ability_mod *= charge_multiplier(attacker, move_type)


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

        # ITEM PHASE 9: the Muscle Band and the Wise Glasses, beside the Life Orb rather
        # than in the type-booster table below - they read the move's CLASS, not its
        # element, which is the one thing that table cannot express.
        if FLAT_DAMAGE_ITEMS.get(attacker_item) == move_class:
            ability_mod *= FLAT_DAMAGE_BOOST

        # ==========================================
        # 💎 ITEM PHASE 1: TYPE BOOSTERS
        # ==========================================
        # Read off move_type rather than the move's printed element, so a Judgment that
        # a Draco Plate just turned Dragon collects that same plate's 20% - which is
        # what the games do, and the reason this belongs here rather than earlier.
        ability_mod *= type_boost_multiplier(attacker_item, move_type)
        # ITEM PHASE 6: the three Orbs. A separate line rather than a row in the
        # table above because each covers TWO elements and is refused outright in
        # the wrong hands, neither of which that table can express.
        ability_mod *= species_type_boost(attacker, move_type, magic_room)

        # Gems are the same rule with a single-use flag. Spent here because this is
        # where the move is definitely being thrown, and only against a target the
        # move can actually hurt: burning a gem on an immunity would be a silent loss
        # of an item the player paid for.
        _gem = gem_for(attacker_item, move_type)
        if _gem and move.get('class') != 'status' and type_multiplier > 0:
            ability_mod *= TYPE_GEM_MULTIPLIER
            mark_item_consumed(attacker, _gem)
            attacker['held_item'] = 'none'
            msg += f" 💎 The {_gem.replace('-', ' ').title()} strengthened the attack!"

        # ==========================================
        # 🚨 THE MULTI-STRIKE EVALUATOR
        # ==========================================
        target_hits = 1
        # Parental Bond's second strike. Handled as a hit count with a reduced payload
        # rather than a bespoke branch, so it rides the multi-strike loop already here.
        parental_bond = (atk_ability == 'parental-bond'
                         and move.get('class') != 'status'
                         and move_name not in MULTI_STRIKE_MOVES)
        
        # 1. Fixed-Hit Anomalies
        if move_name == BATTLE_BOND_SHURIKEN and wears_bonded_form(attacker):
            target_hits = BATTLE_BOND_SHURIKEN_HITS
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

            # ITEM PHASE 5: Loaded Dice raises the FLOOR rather than fixing the count, so
            # a roll that already beat it is left alone - the dice are loaded, not
            # rigged. Skill Link above still wins outright, which is correct: it is the
            # certainty and this is only a nudge.
            target_hits = max(target_hits,
                              min(hit_data['max'], loaded_dice_floor(attacker, magic_room)))

        if parental_bond:
            target_hits = 2

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

            # Parental Bond's follow-up is the same swing at a fraction of the force
            strike_scale = PARENTAL_BOND_SECOND_HIT if (parental_bond and strike > 0) else 1.0

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

            # Super Luck. Merciless is not here: it forces the crit outright rather than
            # nudging the odds, so it sits with the guaranteed-crit rule below.
            crit_stage += CRIT_STAGE_ABILITIES.get(atk_ability, 0)

            # ITEM PHASE 6: the Lucky Punch and the Stick, worth two stages each but only
            # in the right hands. Beside Super Luck because they are the same claim.
            crit_stage += species_crit_stage(attacker, magic_room)

            # A Lansat Berry, which is Focus Energy in fruit form and worth the same two
            # stages. Read off the marker rather than the held item, because by the time
            # it matters the berry has been eaten and the hands are empty.
            if has_action_marker(attacker, LANSAT_MARKER):
                crit_stage += LANSAT_CRIT_STAGES


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
            elif is_crit_guaranteed(move_name, attacker, defender):
                is_crit = True
            else:
                is_crit = (random.randint(1, crit_chance) == 1)

            if is_crit: crit_occurred = True
            
            hit_modifier = (type_multiplier * stab * weather_mod * ability_mod
                            * strike_scale * random.uniform(0.85, 1.00))
            
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
                # 1.5x, plus the stat ratio recomputed with unfavourable stages ignored.
                # Sniper is the only thing that changes the figure: it does not crit more
                # often, it crits harder.
                crit_power = CRIT_MULTIPLIER_ABILITIES.get(atk_ability,
                                                           CRIT_DAMAGE_MULTIPLIER)
                hit_damage = math.floor(hit_damage * crit_power * crit_stat_ratio)
            
            # --- D. DEFENSIVE RESIST BERRIES (Only triggers on the VERY FIRST strike) ---
            if strike == 0 and defender_item in berry_resist_map:
                protected_type = berry_resist_map[defender_item]
                if move_type == protected_type and (type_multiplier > 1.0 or protected_type == 'normal'):
                    # Ripen doubles what a berry is worth here too: half again off a
                    # half, so the bite taken out of the hit is a quarter rather than a
                    # half. The resist berries never reach apply_berry_effect, which is
                    # why this is the one place the doubling is written out by hand.
                    hit_damage = math.floor(hit_damage / ripened(defender, 2))
                    defender['held_item'] = 'none'
                    defender['_ate_berry'] = True
                    defender[LAST_BERRY_MARKER] = defender_item
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
                if (def_ability in BIOLOGICAL_TRAITS.get('contact_damage', [])
                and makes_contact(move, attacker)):
                    skin_dmg = max(1, math.floor(attacker.get('max_hp', 100) / 8))
                    attacker['current_hp'] = max(0, attacker['current_hp'] - skin_dmg)
                    msg += f" 💥 {attacker['name'].capitalize()} was hurt by {defender['name'].capitalize()}'s {def_ability.replace('-', ' ').title()}!"

                # ITEM PHASE 11: a Sticky Barb sticks to whoever touched it, but only if
                # that attacker's hands are EMPTY - it moves into a gap, it never swaps
                # with something. Beside the Rocky Helmet because it answers the same
                # event; the barb's own end-of-turn prick is the shared item payout's job.
                #
                # Read through get_stored_item rather than get_active_item, and asked of
                # BOTH sides: this is a physical move of an item, so an embargoed barb is
                # still a barb, and Sticky Hold both refuses to let go of one and refuses
                # to be handed one.
                if (get_stored_item(defender) == STICKY_BARB
                        and makes_contact(move, attacker)
                        and get_stored_item(attacker) == 'none'
                        and not item_is_stuck(defender) and not item_is_stuck(attacker)):
                    defender['held_item'] = 'none'
                    attacker['held_item'] = STICKY_BARB
                    defender_item = 'none'
                    msg += (f" 🌵 The Sticky Barb latched onto "
                            f"{attacker['name'].capitalize()}!")
                    
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

        if crit_occurred: msg += CRIT_STRIKE_MESSAGE
        if hits_landed > 1: msg += f"Hit {hits_landed} times! "
        
        if move.get('drain', 0) > 0:
            # Liquid Ooze turns the leech around: what the attacker meant to gain, it
            # loses instead. Kept as a negative healing_amount so it rides the channel
            # the engines already read rather than needing a sixth return value.
            _sapped = math.floor(damage * (move['drain'] / 100.0))
            if liquid_ooze_backfires(defender):
                healing_amount -= _sapped
                msg += (f" \U0001f7e2 {attacker['name'].capitalize()} was hurt by "
                        f"{defender['name'].capitalize()}'s Liquid Ooze!")
            else:
                healing_amount += _sapped

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
                # A status move's whole point is its ailment, so it is a PRIMARY effect
                # and neither Serene Grace nor Shield Dust has any say over it.
                chance = 100
            else:
                chance = secondary_chance(chance, attacker, defender)

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
    # 💘 THE DATABASE INFATUATION CONVERTER
    # ==========================================
    # Attract and G-Max Cuddle both land here as the 'infatuation' ailment. It was being
    # written straight through as a major status, which meant it charmed regardless of
    # gender, blocked every other status as "already afflicted", and then did nothing at
    # all because no part of the engine read it.
    if inflicted_status == 'infatuation':
        shielded_by = infatuation_blocked_by(defender)
        if shielded_by:
            inflicted_status = None
            msg += (f" 💗 {defender['name'].capitalize()}'s "
                    f"{shielded_by.replace('-', ' ').title()} kept it indifferent!")
        elif not can_be_infatuated(attacker, defender):
            inflicted_status = None
            msg += f" 💔 But {defender['name'].capitalize()} was unmoved!"
        else:
            defender.setdefault('volatile_statuses', {})['infatuation'] = True
            msg += f" 💘 {defender['name'].capitalize()} fell head over heels in love!"

            # ITEM PHASE 11: the Destiny Knot ties the feeling back the other way. It
            # hangs off the branch where infatuation actually LANDED, so a knot on a
            # specimen that Oblivious or the gender check just spared stays quiet - the
            # knot answers being charmed, not being aimed at.
            #
            # The return trip is screened exactly as the outward one was, which is what
            # stops two Destiny Knots, or a knot facing an Aroma Veil, doing anything odd.
            if (get_active_item(defender) == DESTINY_KNOT
                    and not is_infatuated(attacker)
                    and not infatuation_blocked_by(attacker)
                    and can_be_infatuated(defender, attacker)):
                attacker.setdefault('volatile_statuses', {})['infatuation'] = True
                msg += (f" 💞 {defender['name'].capitalize()}'s Destiny Knot charmed "
                        f"{attacker['name'].capitalize()} right back!")

            # Carried as a volatile, so it does not occupy the major-status slot.
            inflicted_status = None

    # ==========================================
    # THE DATABASE TRAP CONVERTER
    # ==========================================
    if inflicted_status == 'trap':
        if 'partially_trapped' not in defender.get('volatile_statuses', {}):
            if 'volatile_statuses' not in defender:
                defender['volatile_statuses'] = {}
            # Traps lock the victim in for 4 to 5 turns!
            defender['volatile_statuses']['partially_trapped'] = bind_turns(
                attacker, magic_room)
            # ITEM PHASE 5: whose Binding Band is doing the squeezing, recorded on the
            # VICTIM because the end-of-turn chip has the victim and not the binder.
            if bind_damage_multiplier(attacker, magic_room) > 1.0:
                defender['volatile_statuses']['bind_band'] = True
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
            # The attacker is named, so the hold ends when it does.
            if apply_trap(defender, attacker):
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
    if makes_contact(move, attacker) and damage > 0:
        contact_types = attacker.get('types') or []
        
        # 1. CONTACT STATUS (Static, Flame Body, Poison Point, Effect Spore)
        contact_trait = BIOLOGICAL_TRAITS.get('contact_status', {}).get(def_ability)
        if contact_trait and not attacker.get('status_condition'):
            # These abilities have a 30% trigger rate in the franchise ecosystem
            if random.randint(1, 100) <= 30:
                # Ensure the attacker isn't biologically immune to the pathogen!
                # Read off the shared table rather than the row's single 'immune' type,
                # which knew about Poison but not Steel.
                if not status_type_immune(contact_trait['status'], contact_types):
                    attacker['status_condition'] = {'name': contact_trait['status'], 'duration': -1}
                    msg += f" {attacker['name'].capitalize()} was afflicted with {contact_trait['status']} by {defender['name'].capitalize()}'s {def_ability.replace('-', ' ').title()}!"

        # 1a. TOXIC CHAIN - poison on contact with the move, not with the specimen.
        # The schema has no separate bad poison, so this lands as ordinary poison, the
        # same simplification Toxic already makes.
        if (atk_ability == 'toxic-chain' and not defender.get('status_condition')
                and random.randint(1, 100) <= TOXIC_CHAIN_CHANCE):
            if not status_type_immune('poison', defender.get('types'), attacker):
                defender['status_condition'] = {'name': 'poison', 'duration': -1}
                msg += (f" ☣️ {defender['name'].capitalize()} was poisoned by "
                        f"{attacker['name'].capitalize()}'s Toxic Chain!")

        # 1b. OFFENSIVE CONTACT STATUS (Poison Touch) - the attacker infecting what it hits
        touch_trait = BIOLOGICAL_TRAITS.get('contact_status_offensive', {}).get(atk_ability)
        if touch_trait and not defender.get('status_condition'):
            if random.randint(1, 100) <= touch_trait.get('chance', 30):
                if not status_type_immune(touch_trait['status'], defender.get('types')):
                    defender['status_condition'] = {'name': touch_trait['status'], 'duration': -1}
                    msg += (f" {defender['name'].capitalize()} was afflicted with "
                            f"{touch_trait['status']} by {attacker['name'].capitalize()}'s "
                            f"{pretty_ability(atk_ability)}!")

        # 1c. CUTE CHARM - infatuation is a VOLATILE, not a major status, so it cannot ride
        # the contact_status table: writing it into the status slot is the exact bug that
        # made Attract block every other condition. Obeys the same gender rule.
        if def_ability == 'cute-charm' and random.randint(1, 100) <= 30:
            shielded_by = infatuation_blocked_by(attacker)
            if not shielded_by and can_be_infatuated(defender, attacker):
                attacker.setdefault('volatile_statuses', {})['infatuation'] = True
                msg += (f" 💘 {attacker['name'].capitalize()} fell in love with "
                        f"{defender['name'].capitalize()}'s Cute Charm!")

        # ==========================================
        # BLOCK 15: WHAT THE TOUCH COSTS THE ATTACKER
        # ==========================================
        # Mummy and Lingering Aroma paint their own name onto whoever touched them;
        # Wandering Spirit trades instead. Both go through the protection tables the
        # equivalent MOVES already obey - a Mummy cannot paint over a Stance Change,
        # and Skill Swap could not either.
        if def_ability in ABILITY_PAINT_ON_CONTACT:
            if (atk_ability not in UNREPLACEABLE_ABILITIES
                    and atk_ability != def_ability):
                set_active_ability(attacker, def_ability)
                msg += (f" \U0001f9ff {attacker['name'].capitalize()}'s ability became "
                        f"{pretty_ability(def_ability)}!")

        elif def_ability in ABILITY_SWAP_ON_CONTACT:
            if (atk_ability not in UNSWAPPABLE_ABILITIES
                    and def_ability not in UNSWAPPABLE_ABILITIES
                    and atk_ability != def_ability):
                set_active_ability(attacker, def_ability)
                set_active_ability(defender, atk_ability)
                msg += (f" \U0001f47b {attacker['name'].capitalize()} and "
                        f"{defender['name'].capitalize()} swapped abilities!")

        # Pickpocket lifts whatever touched it - but only if its own hands are empty,
        # and only something that can actually be taken.
        if def_ability in ITEM_THIEF_ON_CONTACT:
            _loot = get_stored_item(attacker)
            if (_loot and _loot != 'none' and is_transferable_item(_loot)
                    and not item_is_stuck(attacker)
                    and get_stored_item(defender) in (None, '', 'none')):
                attacker['held_item'] = 'none'
                defender['held_item'] = _loot
                msg += (f" \U0001f45c {defender['name'].capitalize()} pickpocketed the "
                        f"{_loot.replace('-', ' ').title()}!")

        # Perish Body starts the count on BOTH of them - the price of touching it.
        if def_ability in PERISH_BODY_ABILITIES:
            _theirs = attacker.setdefault('volatile_statuses', {})
            if 'perish-song' not in _theirs:
                _theirs['perish-song'] = PERISH_BODY_COUNT
                defender.setdefault('volatile_statuses', {}).setdefault(
                    'perish-song', PERISH_BODY_COUNT)
                msg += (f" \U0001f480 Both specimens will faint in "
                        f"{PERISH_BODY_COUNT} turns!")


    # ==========================================
    # HOOK 3b: BLOCK 14 - REACTIONS TO THE HIT ITSELF
    # ==========================================
    # One table for seventeen abilities. The stage changes are appended to the payload  rather than written here, so they meet Block 8's resolver on the way out - which is
    # what makes a Gooey Speed drop refusable by Clear Body and interesting to Defiant.
    _reaction = on_hit_reaction(defender, move_name, move, attacker, damage,
                                crit_occurred)
    if _reaction:
        for _stat, _stages in _reaction.get('self', []):
            stat_changes.append((TARGET_DEFENDER_SELF, _stat, _stages))
        for _stat, _stages in _reaction.get('foe', []):
            stat_changes.append((TARGET_ATTACKER_FROM_FOE, _stat, _stages))

        # Weather and terrain cannot be laid from here - this function is handed the
        # weather as a string. Smuggled out through the payload instead, exactly as
        # Leech Seed and Perish Song already are.
        if _reaction.get('weather'):
            stat_changes.append((TARGET_FIELD, 'weather:' + _reaction['weather'], 0))
        if _reaction.get('terrain'):
            stat_changes.append((TARGET_FIELD, 'terrain:' + _reaction['terrain'], 0))

        # Toxic Debris scatters spikes at the feet of whoever threw the move, which is
        # the USER's side from this function's point of view.
        if _reaction.get('hazard') and user_hazards is not None:
            _layer = user_hazards.get(_reaction['hazard'], 0) or 0
            if _layer < 2:
                user_hazards[_reaction['hazard']] = _layer + 1
                msg += (f" \U0001f9ea {defender['name'].capitalize()}'s Toxic Debris "
                        f"scattered poison spikes!")

        if _reaction.get('volatile'):
            defender.setdefault('volatile_statuses', {})[_reaction['volatile']] = True
            msg += (f" \u26a1 {defender['name'].capitalize()} became charged - its next "
                    f"Electric move will hit twice as hard!")


    # ==========================================
    # HOOK 3c: ITEM PHASE 2 - THE POLICIES THAT ANSWER A HIT
    # ==========================================
    # Absorb Bulb, Cell Battery, Luminous Moss, Snowball and Weakness Policy. Deliberately
    # beside the ability reactions rather than anywhere else: they are the same sentence
    # with a different subject, and enqueuing the stages here is what sends them through
    # Block 8's resolver - so an Opportunist copies a Weakness Policy boost without
    # anybody teaching it what a Weakness Policy is.
    _item_reaction = item_hit_reaction(defender, move, damage, type_multiplier,
                                       magic_room)
    if _item_reaction:
        _policy, _moves = _item_reaction
        for _stat, _stages in _moves:
            stat_changes.append((TARGET_DEFENDER_SELF, _stat, _stages))
        spend_item(defender, _policy)
        msg += (f" \U0001f4a5 {defender['name'].capitalize()}'s "
                f"{_policy.replace('-', ' ').title()} kicked in!")

    # Item Phase 7's five berries answer a hit too, and would sit naturally here beside
    # the policies - but they are resolved much further down, immediately after the
    # Substitute. See HOOK 3c-ii for why: they are the only reaction on this list that
    # needs the FINAL damage figure rather than this provisional one.

    # ==========================================
    # HOOK 3d: ITEM PHASE 3 - THE EJECTORS THAT ANSWER A HIT
    # ==========================================
    # Eject Button moves its own holder; Red Card moves whoever just hit it. Both only
    # PARK the request - this function has no teams to switch anybody into - and
    # end_of_turn_survival cashes them in beside Wimp Out.
    #
    # A specimen can hold only one item, so these two cannot both fire on one hit.
    _eject = eject_button_fires(defender, move, damage, magic_room)
    if _eject:
        request_pivot(defender, _eject)
        spend_item(defender, _eject)
        msg += (f" ⏏️ {defender['name'].capitalize()}'s Eject Button "
                f"went off!")

    _card = red_card_fires(defender, attacker, move, damage, magic_room)
    if _card:
        request_pivot(attacker, _card)
        spend_item(defender, _card)
        msg += (f" \U0001f7e5 {defender['name'].capitalize()} held up a Red Card "
                f"against {attacker['name'].capitalize()}!")

    # The balloon bursts. Deliberately AFTER the policy above, so a specimen carrying
    # both is not saved from one by the other, and after the damage is settled, so the
    # hit that pops it still lands. From the next move onward `is_grounded` reads its
    # empty hands and Ground moves reach it - which is the whole point of popping it
    # rather than quietly leaving it there.
    if balloon_pops(defender, move, damage, magic_room):
        spend_item(defender, 'air-balloon')
        msg += (f" \U0001f4a5 {defender['name'].capitalize()}'s Air Balloon popped!")

    # Throat Spray answers the ATTACKER's own sound move rather than being hit, so it is
    # not gated on damage at all - Disarming Voice and Growl both trigger it.
    _spray = sound_move_spray(attacker, move_name, magic_room)
    if _spray:
        _item, (_stat, _stages) = _spray
        stat_changes.append((TARGET_ATTACKER, _stat, _stages))
        spend_item(attacker, _item)
        msg += (f" \U0001f3a4 {attacker['name'].capitalize()}'s Throat Spray "
                f"sharpened its voice!")


    # ==========================================
    # BLOCK 15: MAGICIAN
    # ==========================================
    # The only thief here that works the other way round: the ATTACKER lifts the item
    # off whatever it hits. Not contact-gated - a Magician's Flamethrower steals just
    # as happily - and, like Pickpocket, only ever when its own hands are empty.
    if (atk_ability in ITEM_THIEF_ON_ATTACK and damage > 0
            and move.get('class') != 'status'):
        _prize = get_stored_item(defender)
        if (_prize and _prize != 'none' and is_transferable_item(_prize)
                and not item_is_stuck(defender)
                and get_stored_item(attacker) in (None, '', 'none')):
            defender['held_item'] = 'none'
            attacker['held_item'] = _prize
            msg += (f" \U0001f3a9 {attacker['name'].capitalize()} conjured away the "
                    f"{_prize.replace('-', ' ').title()}!")

    # ==========================================
    # BLOCK 15: WHAT BEING HURT COSTS THE ATTACKER
    # ==========================================
    # These answer any damaging move rather than a touch, so they sit outside the
    # contact block above.
    if damage > 0 and move.get('class') != 'status':
        # Cursed Body seals the move that hit it.
        if def_ability in CURSED_BODY_ABILITIES and move_name:
            _sealed = (attacker.get('volatile_statuses') or {}).get('disable') or {}
            if not _sealed.get('move') and random.randint(1, 100) <= CURSED_BODY_CHANCE:
                attacker.setdefault('volatile_statuses', {})['disable'] = {
                    'move': move_name, 'turns': CURSED_BODY_TURNS}
                msg += (f" \U0001f512 {attacker['name'].capitalize()}'s "
                        f"{move_name.replace('-', ' ').title()} was sealed by "
                        f"{defender['name'].capitalize()}'s Cursed Body!")

        # Spicy Spray burns whatever hurt it, if a burn can land there at all.
        if (def_ability in RETALIATORY_BURN_ABILITIES
                and not attacker.get('status_condition')):
            if not status_type_immune('burn', attacker.get('types'), defender):
                attacker['status_condition'] = {'name': 'burn', 'duration': -1}
                msg += (f" \U0001f336\ufe0f {attacker['name'].capitalize()} was burned "
                        f"by {defender['name'].capitalize()}'s Spicy Spray!")

    # BLOCK 20: ILLUSION - the disguise comes off the moment a damaging move connects.
    # Placed beside Colour Change because it answers exactly the same question, and
    # BEFORE it so the reveal reads in the right order in the log.
    if damage > 0 and move.get('class') != 'status':
        _unmasked = drop_illusion(defender)
        if _unmasked:
            msg += (f" 🎭 The illusion shattered - it was "
                    f"{_unmasked.capitalize()} all along!")

    # COLOUR CHANGE - the target takes on the element that just hit it
    if (def_ability == 'color-change' and damage > 0 and move.get('class') != 'status'
            and (defender.get('types') or []) != [move_type]):
        defender['types'] = [move_type]
        msg += f" 🎨 {defender['name'].capitalize()} became the {move_type.title()} type!"

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
            else:
                chance = secondary_chance(chance, attacker, defender)
                
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

        # The damage bonus is paid for having an item to knock off, and a Sticky Hold
        # holder still has one - so only the removal is refused here, not the boost,
        # which was applied long before this point.
        if is_transferable_item(target_item_check) and item_is_stuck(defender):
            msg += (f" 🧲 {defender['name'].capitalize()}'s Sticky Hold kept its "
                    f"{pretty_item(target_item_check)} exactly where it was!")
        elif is_transferable_item(target_item_check):
            defender['held_item'] = 'none'
            msg += f" 💥 {attacker['name'].capitalize()} knocked off {defender['name'].capitalize()}'s {target_item_check.replace('-', ' ').title()}!"

    # 3. Biological Theft (Thief / Covet)
    elif move_name in ['thief', 'covet'] and damage > 0:
        atk_item = get_stored_item(attacker)
        def_item = get_stored_item(defender)

        if atk_item == 'none' and is_transferable_item(def_item) and item_is_stuck(defender):
            msg += (f" 🧲 {attacker['name'].capitalize()} could not prise the "
                    f"{pretty_item(def_item)} out of "
                    f"{defender['name'].capitalize()}'s Sticky Hold!")
        # Can only steal if the attacker's hands are empty and the defender's item is removable!
        elif atk_item == 'none' and is_transferable_item(def_item):
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
            # Destroyed on the attacker's initiative, so there is nothing left for a
            # Pickup opposite to recover - see the by_owner note on mark_item_consumed.
            mark_item_consumed(defender, target_item, by_owner=False)
            msg += (f" 🔥 {defender['name'].capitalize()}'s {pretty_item(target_item)} "
                    f"was burnt to a crisp!")

    # 6. Stolen Provisions (Bug Bite / Pluck) - the ATTACKER gets the berry's effect
    elif move_name in BERRY_EATING_MOVES and damage > 0:
        target_item = get_stored_item(defender)
        if is_berry(target_item) and is_transferable_item(target_item):
            defender['held_item'] = 'none'
            mark_item_consumed(defender, target_item, by_owner=False)
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
        # ...unless the thing being drained is full of Liquid Ooze.
        # ITEM PHASE 5: a Big Root takes a bigger mouthful. Applied to the sapped figure
        # rather than to the move's percentage so it reads the damage that was actually
        # dealt, and so Liquid Ooze below turns the LARGER number back on the drinker.
        _sapped = math.floor(damage * (drain_pct / 100.0)
                             * big_root_bonus(attacker, magic_room))
        if liquid_ooze_backfires(defender):
            healing_amount -= _sapped
            msg += (f" \U0001f7e2 {attacker['name'].capitalize()} was hurt by "
                    f"{defender['name'].capitalize()}'s Liquid Ooze!")
        else:
            healing_amount += _sapped
        
    # ITEM PHASE 5: a Shell Bell gives back an eighth of whatever was dealt, on ANY
    # damaging move rather than only a draining one - which is why it is here and not
    # inside the branch above.
    _bell = shell_bell_heal(attacker, damage, magic_room)
    if _bell:
        healing_amount += _bell
        msg += (f" 🔔 {attacker['name'].capitalize()}'s Shell Bell "
                f"restored a little health!")

    # 2. Kinetic Recoil (Double-Edge, Flare Blitz, Wild Charge)
    if drain_pct < 0:
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

    # 4. The Life Orb's price. It was charging nothing for its 30%, which made it a
    # strictly better Choice Band with no lock - the one item in the shop with an
    # upside and no downside at all.
    #
    # `damage > 0` is the whole trigger condition in the games: the orb bills for a
    # landed hit, so a miss, an immunity and every status move are free. Read off
    # `attacker_item` rather than the stored name so an embargoed or Magic Room orb
    # charges nothing, exactly as it boosts nothing thirty lines up.
    #
    # Magic Guard walls it, as it walls every other indirect source here. Sheer Force
    # would too, in the games - it is not in this engine, so there is nothing to check.
    if attacker_item == 'life-orb' and damage > 0 and atk_ability != 'magic-guard':
        orb_recoil = max(1, math.floor(attacker.get('max_hp', 100) / LIFE_ORB_RECOIL_DIVISOR))
        attacker['current_hp'] = max(0, attacker['current_hp'] - orb_recoil)
        msg += f" 🔮 {attacker['name'].capitalize()} was hurt by its Life Orb!"

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
    # Read through the shared table rather than testing the types here, so Corrosion -
    # which exists precisely to poison these two - is not undone one line later.
    elif inflicted_status == 'poison' and status_type_immune('poison', def_types, attacker):
        inflicted_status = None
        msg += f" {defender['name'].capitalize()}'s typing makes it immune to poison!"
    elif inflicted_status == 'freeze' and 'ice' in def_types:
        inflicted_status = None
        msg += f" {defender['name'].capitalize()}'s Ice typing makes it immune to freezing!"

    # Abilities that simply refuse a condition. Worry Seed's whole purpose is to staple
    # Insomnia on, so the sleep lock it grants has to actually hold; Vital Spirit is the
    # same trait under a different name, and Water Bubble refuses burns.
    if inflicted_status and refuses_status(defender, inflicted_status, weather):
        blocked = inflicted_status
        inflicted_status = None
        verb = "keeps it wide awake" if blocked == 'sleep' else f"refuses the {blocked}"
        msg += (f" {defender['name'].capitalize()}'s {pretty_ability(def_ability)} "
                f"{verb}!")

    # STENCH staples a flinch chance onto every damaging move its owner throws. Routed
    # through inflicted_status so it reaches apply_status_outcome, which is the one place
    # that knows flinch is a volatile rather than a status.
    if (atk_ability in FLINCH_ON_HIT_ABILITIES and damage > 0
            and move.get('class') != 'status' and not inflicted_status):
        if random.randint(1, 100) <= FLINCH_ON_HIT_ABILITIES[atk_ability]:
            inflicted_status = 'flinch'

    # ITEM PHASE 4: King's Rock and Razor Fang say the same sentence as Stench, so they
    # take the same route - through inflicted_status, which is the one place that knows
    # flinch is a volatile rather than a status, and which is therefore also where Inner
    # Focus refuses it. `not inflicted_status` keeps the item from overwriting a status
    # the move itself was already going to inflict.
    if not inflicted_status:
        _rock = item_flinch_chance(attacker, move, damage, magic_room)
        if _rock and random.randint(1, 100) <= _rock:
            inflicted_status = 'flinch'

    # POISON PUPPETEER confuses whatever ITS OWNER poisons - including the poison Toxic
    # Chain just applied directly, which is why this reads the target rather than only
    # the pending status.
    if atk_ability in POISON_CONFUSION_ABILITIES:
        landed_poison = (inflicted_status == 'poison'
                         or (defender.get('status_condition') or {}).get('name') == 'poison')
        volatiles = defender.setdefault('volatile_statuses', {})
        if landed_poison and 'confusion' not in volatiles:
            volatiles['confusion'] = random.randint(2, 5)
            msg += f" 💫 {defender['name'].capitalize()} was confused by the poison!"

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

    # 🏹 THOUSAND ARROWS: the damage is only half of it. What lands is the grounding, and
    # it lasts the rest of the battle.
    #
    # THREE THINGS IT DOES NOT KNOCK DOWN, and each is a real case rather than a
    # hypothetical:
    #
    #   * a SUBSTITUTE takes the damage in its owner's place and the owner stays in the
    #     air - the doll is what was hit;
    #   * a specimen mid-SKY DROP is hit but not brought down, because it is being held
    #     up by somebody else rather than flying under its own power;
    #   * anything already on the ground, which has nothing to knock down.
    #
    # Fly and Bounce are cancelled outright: the charge ends when its owner does.
    if move_name in GROUNDING_MOVES and damage > 0:
        _volatiles = defender.get('volatile_statuses') or {}
        if not was_raised:
            # Already on the floor when the move was thrown. Nothing to knock down, and
            # nothing to say about it - a Snorlax does not need telling it has been
            # brought to earth.
            pass
        elif _volatiles.get('substitute'):
            pass
        elif _volatiles.get('charging') == 'sky-drop':
            msg += (f" 🏹 {defender['name'].capitalize()} was struck out of the sky, "
                    f"but stayed aloft!")
        elif ground_specimen(defender):
            msg += f" 🏹 {defender['name'].capitalize()} was knocked to the ground!"
            if _volatiles.get('charging') in ('fly', 'bounce'):
                end_charge(defender)
                msg += " Its flight was cut short!"

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
            
        # 3. ITEM PHASE 5: a Focus Band. Unlike the Sash it works from ANY HP and is not
        # consumed, which is what a one-in-ten chance is buying instead of a certainty.
        #
        # Its position in this chain is style rather than behaviour: a specimen holds one
        # item, so the Sash branch above and this one are mutually exclusive and their
        # order cannot be observed. Sturdy is the only entry here that could genuinely
        # compete with it, and Sturdy wins by sitting first.
        elif focus_band_holds(defender, magic_room):
            damage = defender['current_hp'] - 1
            msg += " It hung on using its Focus Band!"

        # 4. Endure Status (If you add the move 'Endure' later!)
        elif defender.get('volatile_statuses', {}).get('endure'):
            damage = defender['current_hp'] - 1
            msg += " It endured the hit!"

    # ==========================================
    # 🚨 BIOLOGICAL CLEANSERS (Wake-Up Slap & Smelling Salts)
    # ==========================================
    if damage > 0:
        # `.get('status_condition', {})` hands back None rather than the default whenever
        # the key is PRESENT and None - which is what an unstatused combatant carries - so
        # both of these raised AttributeError on every healthy target. Read with `or {}`,
        # the way the rest of the file does.
        if move_name == 'wake-up-slap' and (defender.get('status_condition') or {}).get('name') == 'sleep':
            defender['status_condition'] = None
            msg += f" The sheer force of the slap jolted {defender['name'].capitalize()} awake!"

        elif move_name == 'smelling-salts' and (defender.get('status_condition') or {}).get('name') == 'paralysis':
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

    # ==========================================
    # HOOK 3c-ii: ITEM PHASE 7 - THE BERRIES THAT ANSWER A HIT
    # ==========================================
    # Kee, Maranga, Jaboca, Rowap and Enigma. Their natural home is HOOK 3c beside the
    # Weakness Policy - same moment, same sentence - and they are HERE instead for one
    # reason: they are the only reaction on that list that needs to know the FINAL
    # damage. Between there and here, Focus Sash, Sturdy, Focus Band and Endure can all
    # cap a lethal hit, and a Substitute can absorb it outright.
    #
    # That matters twice over. A berry must not answer a blow its holder did not
    # survive, and the Enigma Berry's helping has to be measured against the HP the
    # holder will actually be left with. Resolved up there, an Enigma Berry would have
    # revived a fainting specimen and healed the wrong amount besides.
    #
    # Separate from the policies for a second reason as well: a policy is SPENT, and a
    # berry is EATEN. `swallow_berry` is what pays Harvest, Cud Chew and Belch, and
    # `cheek_pouch_refill` is what pays Cheek Pouch.
    #
    # `effective_class` rather than the move's stored category, so a physical Photon
    # Geyser is answered by a Kee Berry and not a Maranga.
    _survivor_hp = defender.get('current_hp', 0) - damage
    if _survivor_hp > 0:
        _berry_reaction = berry_hit_reaction(defender, attacker, move, damage,
                                             type_multiplier, magic_room,
                                             move_class=effective_class)
    else:
        _berry_reaction = None

    if _berry_reaction:
        _berry, _row = _berry_reaction
        _label = _berry.replace('-', ' ').title()
        _who = defender['name'].capitalize()

        # Ripen doubles what a berry is worth, and it is worth something different in
        # each of the three shapes below - so the doubling is applied to the FIGURE in
        # all three rather than to any one of them.
        if _row.get('self'):
            for _stat, _stages in _row['self']:
                stat_changes.append((TARGET_DEFENDER_SELF, _stat,
                                     int(ripened(defender, _stages))))
            msg += f" \U0001fad0 {_who} ate its {_label}!"

        if _row.get('heal'):
            # The damage has NOT been taken off current_hp yet - this function returns it
            # for the engines to apply - so the heal is measured against what the holder
            # will be left with and then expressed as an adjustment to the figure the
            # engine will subtract from. Healing current_hp directly would overheal a
            # holder near full, because the cap would be tested against the wrong number.
            _restored = max(1, math.floor(defender.get('max_hp', 100)
                                          * ripened(defender, _row['heal'])))
            _gained = min(defender.get('max_hp', 100),
                          _survivor_hp + _restored) - _survivor_hp
            defender['current_hp'] += _gained
            msg += (f" \U0001f300 {_who} ate its {_label} and recovered "
                    f"{_gained} HP!")

        if _row.get('recoil'):
            # Written straight to the attacker's HP, the way Rocky Helmet a thousand
            # lines above does, and for the same reason: healing_amount is the ATTACKER's
            # drain channel and a negative on it would be read as Liquid Ooze.
            _bite = max(1, math.floor(attacker.get('max_hp', 100)
                                      * ripened(defender, _row['recoil'])))
            attacker['current_hp'] = max(0, attacker['current_hp'] - _bite)
            msg += (f" \U0001fad0 {_who}'s {_label} bit "
                    f"{attacker['name'].capitalize()} back!")

        swallow_berry(defender, _berry)
        msg += cheek_pouch_refill(defender)

    # ==========================================
    # BLOCK 16: WHAT THROWING THE MOVE DID TO THE THROWER
    # ==========================================
    # Aegislash draws its blade, and Cramorant surfaces with a mouthful. Requested
    # here because this is the one place both engines agree a move is being used.
    #
    # Divergence, stated rather than hidden: the games change Aegislash BEFORE the
    # move lands, so the blade's own attack swings with the blade's Attack stat.
    # Here the request is cashed in afterwards, so the stance is a beat late and the
    # first swing of a battle is made in the wrong one. Doing it properly means
    # resolving a form change mid-formula, which needs the species tables this
    # function has no way to reach.
    _stance = stance_form_for(attacker, move_name, move)
    if _stance:
        request_form_flip(attacker, _stance, 'changed stance')

    _caught = gulp_catch_for(attacker, move_name)
    if _caught:
        request_form_flip(attacker, _caught, 'surfaced with a mouthful')

    # ==========================================
    # BLOCK 16: GULP MISSILE SPITS BACK
    # ==========================================
    # Whatever Cramorant surfaced holding goes at the next thing that hurts it, and
    # the mouthful it caught decides what that costs - a Defense stage from the
    # little one, paralysis from the big one.
    _mouthful = gulp_payload_for(defender) if damage > 0 else None
    if _mouthful:
        request_form_flip(defender, GULP_BASE_FORM, 'spat out its catch')
        _recoil = math.floor(max(1, attacker.get('max_hp', 1)) * GULP_RECOIL_FRACTION)
        attacker['current_hp'] = max(0, attacker['current_hp'] - _recoil)
        msg += (f" \U0001f41f {defender['name'].capitalize()} spat its catch at "
                f"{attacker['name'].capitalize()} for {_recoil}!")
        if _mouthful.get('stat'):
            _stat, _stages = _mouthful['stat']
            stat_changes.append((TARGET_ATTACKER_FROM_FOE, _stat, _stages))
        elif _mouthful.get('status') and not attacker.get('status_condition'):
            if not status_type_immune(_mouthful['status'], attacker.get('types')):
                attacker['status_condition'] = {'name': _mouthful['status'],
                                                'duration': -1}

    # ==========================================
    # BLOCK 15: SYNCHRONIZE
    # ==========================================
    # Placed here, at the very end, because it reads inflicted_status - the condition
    # this move is about to land - and that is not final until every phase above has
    # had its say. Only the three transferable conditions travel; sleep and freeze stay
    # where they landed, which is the rule in the games.
    if (get_active_ability(defender) in SYNCHRONIZE_ABILITIES
            and inflicted_status in SYNCHRONIZE_STATUSES
            and not attacker.get('status_condition')):
        if not status_type_immune(inflicted_status, attacker.get('types'), defender):
            attacker['status_condition'] = {'name': inflicted_status, 'duration': -1}
            msg += (f" \U0001f501 {defender['name'].capitalize()}'s Synchronize passed "
                    f"the {inflicted_status} back to "
                    f"{attacker['name'].capitalize()}!")

    # Innards Out pays out whatever the specimen had left, and by the time the engines
    # see the faint that is already zero. Recorded here, where the figure still exists.
    defender['_hp_before_blow'] = defender.get('current_hp', 0)
    defender['_killed_by_contact'] = bool(damage > 0 and makes_contact(move, attacker))

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


# Block 21. calculate_damage is a wrapper that scopes the mould-breaker marker around
# _resolve_damage; this makes inspect.getsource(calculate_damage) hand back the FORMULA
# rather than the eight-line wrapper, which is what nine suites mean when they read it to
# prove an ability is reachable at all. It is the same protocol functools.wraps uses,
# written out here because the two functions are declared in the other order.
calculate_damage.__wrapped__ = _resolve_damage


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


# Species that exist as two SEPARATE entries, one per sex, because the sexes differ in
# more than colour - different stats, different sprites, sometimes different abilities.
# For these, the name is the answer: a Meowstic Female is female by definition.
#
# Written out rather than inferred from the "-male"/"-female" suffix, because three
# other species carry that suffix WITHOUT being sex-forms - `pyroar-male`,
# `frillish-male` and `jellicent-male` are the sole entry for their species, where the
# female is a cosmetic variant. Reading the suffix alone would pin every Pyroar male,
# and Pyroar is 87.5% female.
SEX_LOCKED_FAMILIES = ('meowstic', 'indeedee', 'basculegion', 'oinkologne')


def declared_gender(species_name):
    """
    The sex a species NAME insists on, or None if the name does not decide it.

    Only the genuine sex-forms count. This exists because the gender_rate column and the
    species name disagreed on every one of them: `meowstic-female` carried a rate of 4,
    so half of all Meowstic Females were rolled male, and `pyroar-male` carried 7, so
    seven in eight "Pyroar Male" were rolled female. The database is corrected by
    migrate_gendered_species.py; this makes the engine right whether or not it has run.
    """
    name = str(species_name or '').lower().strip()
    for family in SEX_LOCKED_FAMILIES:
        if name == f"{family}-male":
            return 'M'
        if name == f"{family}-female":
            return 'F'
    return None


def roll_gender(gender_rate, species_name=None, rng=None) -> str:
    """
    Decide a specimen's sex from its species' gender_rate.

    PokeAPI's `gender_rate` is EIGHTHS FEMALE: 0 is always male, 8 always female, and -1
    means the species has no sex at all. A missing value is treated as an even 4, which
    is what both hand-rolled copies of this already did.

    `species_name` overrides the roll for the species whose NAME states a sex. A
    specimen called Meowstic Female that comes out male is not a rare variant, it is a
    contradiction on the same line of the screen.

    `rng` is a seeded generator, for callers that need a STABLE answer rather than a
    fresh one - the Sector Wardens field a fixed roster and must not flip sex between
    rematches. The Warden builder was already passing one positionally into a function
    that took a single argument, so every Warden entry without an explicit `gender` key
    raised TypeError; supporting it is what that call always meant.

    Returns 'M', 'F' or the literal string 'None' - the last because that is what
    `caught_pokemon.gender` stores for the genderless, and every reader in the codebase
    compares against that string rather than a real None.

    Pulled out of the two places that rolled it so a WILD SPAWN can roll one too: a
    spawn that shows a sex has to hand the same one to the specimen that gets caught,
    and it cannot do that if the roll lives inside the catch.
    """
    fixed = declared_gender(species_name)
    if fixed:
        return fixed

    if gender_rate is None:
        gender_rate = 4
    if gender_rate == -1:
        return 'None'

    source = rng if rng is not None else random
    return 'F' if source.uniform(0, 100) <= (gender_rate / 8.0) * 100 else 'M'


def gender_icon(gender) -> str:
    """The badge shown beside a specimen's name. One spelling, everywhere."""
    return {'M': '♂️', 'F': '♀️'}.get(str(gender or '').strip().upper(), '⚧️')


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


STAT_KEYS = ('hp', 'attack', 'defense', 'sp_atk', 'sp_def', 'speed')


def roll_starter_ivs():
    """
    A starter's genetics: three guaranteed perfect stats, the rest in a narrow band.

    WHICH three is random, so no two starters are alike and nobody can plan around it -
    but every starter is good, which is the whole point. A wild specimen still rolls
    0-31 on all six; this floor exists only for the one Pokemon a trainer is given
    before they have had any chance to earn a better one.
    """
    ivs = {stat: random.randint(STARTER_IV_FLOOR, STARTER_IV_CEILING)
           for stat in STAT_KEYS}
    for stat in random.sample(STAT_KEYS, STARTER_PERFECT_IVS):
        ivs[stat] = STARTER_IV_CEILING
    return ivs


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