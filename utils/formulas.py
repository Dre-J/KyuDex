import math
import random
from utils.constants import TYPE_CHART, NATURE_MULTIPLIERS, BIOLOGICAL_TRAITS, CONSUMABLE_DATABASE, MULTI_STRIKE_MOVES
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

def calculate_damage(attacker, defender, move, weather='none', target_hazards=None, user_hazards=None):
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

    # 🚨 FAILSAFE: Guarantee both specimens have their volatile dictionaries initialized!
    if 'volatile_statuses' not in attacker:
        attacker['volatile_statuses'] = {}
    if 'volatile_statuses' not in defender:
        defender['volatile_statuses'] = {}

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
            return 0, f"🛡️ **{defender['name'].capitalize()}** protected itself from the attack!", None, [], 0

    # THE FIX 1: Safely catch SQLite NULL values before running string methods!
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
    # PHASE 1: KINETIC & SPECIAL DAMAGE (The Multi-Strike Engine)
    # ==========================================
    if move.get('class') != 'status' and move.get('power', 0) > 0:
        level = attacker.get('level', 50)
        
        def apply_stage(raw_stat, stage):
            if stage > 0: return int(raw_stat * ((2.0 + stage) / 2.0))
            if stage < 0: return int(raw_stat * (2.0 / (2.0 + abs(stage))))
            return raw_stat
            
        atk_stage = attacker.get('stat_stages', {}).get('attack', 0)
        def_stage = defender.get('stat_stages', {}).get('defense', 0)
        spa_stage = attacker.get('stat_stages', {}).get('sp_atk', 0)
        spd_stage = defender.get('stat_stages', {}).get('sp_def', 0)
        
        if move.get('class') == 'physical':
            a = apply_stage(attacker.get('stats', {}).get('attack', 50), atk_stage)
            d = apply_stage(defender.get('stats', {}).get('defense', 50), def_stage)
            if attacker_item == 'choice-band': a = math.floor(a * 1.5)
        else: 
            a = apply_stage(attacker.get('stats', {}).get('sp_atk', 50), spa_stage)
            d = apply_stage(defender.get('stats', {}).get('sp_def', 50), spd_stage)
            if attacker_item == 'choice-specs': a = math.floor(a * 1.5)
            if defender_item == 'assault-vest': d = math.floor(d * 1.5)
            
        # 🚨 THE BATTLE BOND MUTATION
        move_power = move.get('power', 0)
        if move_name == 'water-shuriken' and atk_ability == 'battle-bond':
            move_power = 20

        # 🚨 NEW: KNOCK OFF KINETIC AMPLIFIER
        # Checks if the item exists and isn't a symbiotic un-removable item!
        is_removable = defender_item not in ['none', 'red-orb', 'blue-orb'] and not defender_item.endswith('ite') and not defender_item.endswith('ium-z')
        
        if move_name == 'knock-off' and is_removable:
            move_power = math.floor(move_power * 1.5)

        # 1. Calculate raw structural damage BEFORE random variance and multipliers
        base_damage_unmodified = (((2 * level / 5) + 2) * move_power * (a / max(1, d))) / 50 + 2
        stab = 1.5 if move_type in (attacker.get('types') or []) else 1.0

        weather_mod = 1.0
        if weather == 'sun':
            if move_type == 'fire': weather_mod = 1.5
            elif move_type == 'water': weather_mod = 0.5
        elif weather == 'rain':
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
            is_crit = (random.randint(1, 24) == 1)
            if is_crit: crit_occurred = True
            
            hit_modifier = type_multiplier * stab * weather_mod * ability_mod * random.uniform(0.85, 1.00)
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
            
            # --- E. FOCUS SASH FAILSAFE ---
            target_item = (defender.get('held_item') or "").lower().replace(' ', '-')
            if simulated_hp <= 0 and (simulated_hp + hit_damage) == defender.get('max_hp', 100):
                if target_item == 'focus-sash':
                    simulated_hp = 1
                    total_damage -= 1 
                    defender['held_item'] = 'none'
                    msg += " It hung on using its Focus Sash! "
                    
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
        
        if not is_afflicted:
            chance = move.get('ailment_chance', 0)
            if chance == 0 and move.get('class') == 'status':
                chance = 100
                
            if random.randint(1, 100) <= chance:
                inflicted_status = ailment
        else:
            if move.get('class') == 'status':
                msg += f" But it failed because {defender['name'].capitalize()} is already afflicted!"

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
        'ice-hammer': [('attacker', 'speed', -1)]
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
    else:
        stat_name = move.get('stat_name', 'none')
        stat_change = move.get('stat_change', 0)
        
        if stat_name not in ['none', None] and stat_change != 0:
            chance = move.get('stat_chance', 0)
            if chance == 0 and move_class == 'status':
                chance = 100
                
            # Ensures secondary stat drops from attacks (like Moonblast) only happen if damage > 0
            if random.randint(1, 100) <= chance and (move_class == 'status' or damage > 0):
                target = "attacker" if move.get('target') == 'user' else "defender"
                
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
        defender['stat_stages'] = {'attack': 0, 'defense': 0, 'special-attack': 0, 'special-defense': 0, 'speed': 0}
        msg += f" 🌫️ {defender['name'].capitalize()}'s stat changes were neutralized by the smog!"
        
    elif move_name == 'haze':
        attacker['stat_stages'] = {'attack': 0, 'defense': 0, 'special-attack': 0, 'special-defense': 0, 'speed': 0}
        defender['stat_stages'] = {'attack': 0, 'defense': 0, 'special-attack': 0, 'special-defense': 0, 'speed': 0}
        msg += " 🌫️ All biological stat changes on the field were eliminated by the Haze!"

    # 2. Ecological Equipment Destruction (Knock Off)
    elif move_name == 'knock-off' and damage > 0:
        target_item_check = (defender.get('held_item') or "").lower().replace(' ', '-')
        is_removable = target_item_check not in ['none', 'red-orb', 'blue-orb'] and not target_item_check.endswith('ite') and not target_item_check.endswith('ium-z')
        
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
    # PHASE 4: CELLULAR REGENERATION
    # ==========================================
    if move.get('healing', 0) > 0:
        healing_amount += math.floor(attacker.get('max_hp', 100) * (move['healing'] / 100.0))

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

    return damage, msg.strip(), inflicted_status, stat_changes, healing_amount

def fetch_base_stats(cursor, pokedex_id):
    """Pulls the 6 base stats for a specific species from the database."""
    cursor.execute("SELECT stat_name, base_value FROM base_pokemon_stats WHERE pokedex_id = ?", (pokedex_id,))
    rows = cursor.fetchall()
    
    # Map the API names to our standard dictionary keys
    stat_map = {
        'hp': 'hp', 'attack': 'attack', 'defense': 'defense', 
        'special-attack': 'sp_atk', 'special-defense': 'sp_def', 'speed': 'speed'
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