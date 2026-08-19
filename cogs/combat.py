import discord
import os
import time
import traceback
from discord.ext import commands
import aiosqlite
import random
import asyncio
import math
from utils.formulas import calculate_damage, calculate_stats, fetch_base_stats, calculate_real_stat, apply_entry_hazards, check_consumables, is_grounded, FORMULA_BYPASS_MOVES, estimate_bypass_payload, resolve_dynamic_power, format_power_hint, describe_power_range, get_effective_priority, DELAYED_ATTACK_MOVES, snapshot_delayed_attack, resolve_delayed_strike, UPROAR_MOVES, ENCORE_IMMUNE_MOVES, is_uproar_active, GUARANTEED_HIT_MOVES, ALWAYS_CRIT_MOVES, SIDE_SCREEN_MOVES, reset_stat_stages, leave_field, baton_pass_state, clear_base_stat_snapshot, get_active_ability, ability_move_would_land, item_move_would_land, get_active_item, snapshot_team_items, resolve_persisted_item, mark_item_consumed, begin_charge, end_charge, break_stale_charge, move_is_restricted, usable_moves, apply_grudge, snapshot_wish, resolve_wish, PARTY_CURE_MOVES, struggle_move, apply_struggle_recoil, is_trapped as specimen_is_trapped, apply_trap, can_be_trapped, COPY_MOVES, resolve_copied_move, ME_FIRST_MULTIPLIER, collected_coins, coin_sources, magic_coat_bounces, snatch_steals, clear_interceptors, apply_healing_wish, AQUA_RING_FRACTION, consume_lock_on, prize_multiplier, CURSE_DRAIN_FRACTION, store_bide_damage, is_infatuated, infatuation_holds_it_back, accuracy_multiplier, battle_speed, is_unburdened, get_stored_item, hit_chance, evasion_multiplier, turn_order_key, priority_tier, blocks_priority_moves, is_dance_move, refuses_volatile, refuses_status, move_family_blocked, refuses_status_moves, smothers_explosion, is_explosive_move, resolve_stat_stages, shrugs_off_intimidate, apply_stat_stage, OHKO_MOVES, paradox_engine_running, paradox_best_stat, resists_forced_switch, intimidate_reversal, wants_to_bail_out, pretty_ability, is_wind_move, refuses_wind, on_hit_reaction, charge_multiplier, crossed_below_half, hp_threshold_stages, flinch_reaction, faint_recoil, hp_form_for, hunger_form_for, stance_form_for, gulp_catch_for, request_form_flip, knockout_boost, mourning_boost, mark_mourned, copies_stat_boosts, fallen_allies, supreme_overlord_multiplier, weather_form_for, truancy_holds_it_back, is_effectively_asleep, apply_berry_effect, harvest_regrows, cud_chew_due, pickup_finds, clear_spent_item_markers, item_is_stuck, is_berry, traced_ability, disguise_model, wear_illusion, drop_illusion, true_pokedex_id, rewrite_plate_type, restore_own_types, apply_transform, set_active_ability, refresh_neutralizing_gas, breaks_moulds, MOLD_BREAKER_IGNORES, personal_weather, battle_bond_form_for, wears_bonded_form, STANDARD_SHIELDS, item_hit_reaction, terrain_seed_fires, sound_move_spray, blunder_policy_fires, room_service_fires, apply_white_herb, apply_mental_herb, spend_item, roll_gender, declared_gender
from utils.constants import DB_FILE, NATURE_MULTIPLIERS, TYPE_CHART, BIOLOGICAL_TRAITS, METRONOME_POOL, WEATHER_CHIP_IMMUNE_ABILITIES, CHOICE_LOCK_ABILITIES, BURN_TOLL_HALVED_BY, shrugs_off_weather, EARLY_BIRD_SLEEP_RATE, ALLY_DODGE_ABILITIES, STAT_STAGE_KEYS, EXPLOSIVE_MOVES, ENTRY_STAT_BOOST_ABILITIES, ENTRY_STAT_DROP_ABILITIES, ONCE_PER_BATTLE_MARKER, DOWNLOAD_ABILITIES, FRISK_ABILITIES, FOREWARN_ABILITIES, ANTICIPATION_ABILITIES, BERRY_BLOCKING_ABILITIES, SCREEN_CLEANING_ABILITIES, SIDE_SCREEN_KEYS, FIELD_NEUTRALISING_ABILITIES, ENTRY_FORM_SHIFTS, RUIN_ABILITIES, ALLY_ONLY_ENTRY_ABILITIES, TERRAIN_SETTER_ABILITIES, PARADOX_ABILITIES, BOOSTER_ENERGY, BOOSTER_SPENT_MARKER, BAIL_OUT_MARKER, HP_THRESHOLD_MARKER, FORM_FLIP_REQUEST, NO_FLEE_MECHANIC_ABILITIES, TARGET_ATTACKER, TARGET_DEFENDER, TARGET_ATTACKER_FROM_FOE, TARGET_DEFENDER_SELF, TARGET_FIELD, HIDDEN_ABILITY_CHANCE, KNOCKOUT_BOOST_ABILITIES, MOURNING_ABILITIES, MOURNED_MARKER, OPPORTUNIST_ABILITIES, SUPREME_OVERLORD_ABILITIES, LEVITATION_ABILITIES, TRUANT_ABILITIES, TRUANT_MARKER, COMATOSE_ABILITIES, WEATHER_FORM_ABILITIES, CLUMSY_ABILITIES, STICKY_HOLD_ABILITIES, GLUTTONY_ABILITIES, RIPEN_ABILITIES, CHEEK_POUCH_ABILITIES, HARVEST_ABILITIES, CUD_CHEW_ABILITIES, PICKUP_ABILITIES, HONEY_GATHER_ABILITIES, AFTER_BATTLE_FIND_CHANCE, HONEY_GATHER_ITEM, PICKUP_POOL, NO_ALLY_ITEM_ABILITIES, NO_BALL_THROW_ABILITIES, TRACE_ABILITIES, IMPOSTER_ABILITIES, ILLUSION_ABILITIES, ILLUSION_MARKER, PLATE_TYPE_ABILITIES, PLATE_BASE_TYPES, ITEM_WELDED_ABILITIES, ALLY_FAINT_ABILITIES, BATTLE_STATE_TEAM_KEYS, MOLD_BREAKING_ABILITIES, MOULD_BROKEN_MARKER, NEUTRALIZING_GAS_ABILITIES, GAS_SUPPRESSED_MARKER, UNAWARE_ABILITIES, PERSONAL_SUN_ABILITIES, DOUBLES_ONLY_ABILITIES, BATTLE_BOND_ABILITIES, BATTLE_BOND_FORM, GIMMICK_LOCKED_FORMS, spawnable_forms, ultra_beasts
from utils.embeds import rebind_image
from utils import checks
import aiohttp
from cogs import battle_render

# The Ecological Gatekeepers
WARDEN_ROSTER = {
    'canopy': {
        'title': 'Canopy Warden',
        'biome_unlocked': 'trench',
        'reward_item': 'encrypted-field-notes',
        'reward_qty': 3,
        'team': [
            {
                'name': 'kleavor',
                'level': 30,
                'nature': 'jolly',
                'ability': 'sharpness',
                'ivs': {'hp': 31, 'attack': 31, 'defense': 31, 'sp_atk': 31, 'sp_def': 31, 'speed': 31},
                'evs': {'hp': 0, 'attack': 252, 'defense': 4, 'sp_atk': 0, 'sp_def': 0, 'speed': 252},
                'types': ['bug', 'rock'],
                'held_item': 'focus-sash',
                'moves': [
                    {'name': 'stone-axe', 'power': 65, 'type': 'rock', 'class': 'physical', 'accuracy': 90, 'pp': 15, 'max_pp': 24},
                    {'name': 'trailblaze', 'power': 50, 'type': 'grass', 'class': 'physical', 'accuracy': 100, 'pp': 20, 'max_pp': 32},
                    {'name': 'swords-dance', 'power': 0, 'type': 'normal', 'class': 'status', 'accuracy': 100, 'pp': 20, 'max_pp': 32},
                    {'name': 'close-combat', 'power': 120, 'type': 'fighting', 'class': 'physical', 'accuracy': 100, 'pp': 5, 'max_pp': 8},
                ]
            },
            {
                'name': 'gligar',
                'level': 30,
                'is_shiny': True,
                'nature': 'impish',
                'ability': 'immunity',
                'ivs': {'hp': 31, 'attack': 31, 'defense': 31, 'sp_atk': 31, 'sp_def': 31, 'speed': 31},
                'evs': {'hp': 252, 'attack': 4, 'defense': 116, 'sp_atk': 0, 'sp_def': 140, 'speed': 0},
                'types': ['ground', 'flying'],
                'held_item': 'liechi-berry',
                'moves': [
                    {'name': 'earthquake', 'power': 100, 'type': 'ground', 'class': 'physical', 'accuracy': 100, 'pp': 10, 'max_pp': 16},
                    {'name': 'roost', 'power': 0, 'type': 'flying', 'class': 'status', 'accuracy': 100, 'pp': 5, 'max_pp': 8},
                    {'name': 'u-turn', 'power': 70, 'type': 'bug', 'class': 'physical', 'accuracy': 100, 'pp': 20, 'max_pp': 32},
                    {'name': 'toxic', 'power': 0, 'type': 'poison', 'class': 'status', 'accuracy': 90, 'pp': 10, 'max_pp': 16},
                ]
            },
            {
                'name': 'nidoking',
                'level': 30,
                'nature': 'timid',
                'ability': 'sheer-force',
                'ivs': {'hp': 31, 'attack': 31, 'defense': 31, 'sp_atk': 31, 'sp_def': 31, 'speed': 31},
                'evs': {'hp': 0, 'attack': 0, 'defense': 0, 'sp_atk': 252, 'sp_def': 4, 'speed': 252},
                'types': ['poison', 'ground'],
                'held_item': 'black-sludge',
                'moves': [
                    {'name': 'sludge-wave', 'power': 95, 'type': 'poison', 'class': 'special', 'accuracy': 100, 'pp': 10, 'max_pp': 16},
                    {'name': 'earth-power', 'power': 90, 'type': 'ground', 'class': 'special', 'accuracy': 100, 'pp': 10, 'max_pp': 16},
                    {'name': 'ice-beam', 'power': 90, 'type': 'ice', 'class': 'special', 'accuracy': 100, 'pp': 10, 'max_pp': 16},
                    {'name': 'flamethrower', 'power': 90, 'type': 'fire', 'class': 'special', 'accuracy': 100, 'pp': 15, 'max_pp': 24},
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
                'is_shiny': True,
                'nature': 'adamant',
                'ability': 'intimidate',
                'ivs': {'hp': 31, 'attack': 31, 'defense': 31, 'sp_atk': 31, 'sp_def': 31, 'speed': 31},
                'evs': {'hp': 0, 'attack': 252, 'defense': 0, 'sp_atk': 0, 'sp_def': 4, 'speed': 252},
                'types': ['water', 'flying'],
                'held_item': 'leftovers',
                'moves': [
                    {'name': 'waterfall', 'power': 80, 'type': 'water', 'class': 'physical', 'accuracy': 100, 'pp': 15, 'max_pp': 24},
                    {'name': 'dragon-dance', 'power': 0, 'type': 'dragon', 'class': 'status', 'accuracy': 100, 'pp': 20, 'max_pp': 32},
                    {'name': 'scale-shot', 'power': 25, 'type': 'dragon', 'class': 'physical', 'accuracy': 90, 'pp': 20, 'max_pp': 32},
                    {'name': 'earthquake', 'power': 100, 'type': 'ground', 'class': 'physical', 'accuracy': 100, 'pp': 10, 'max_pp': 16}
                ]
            },
            {
                'name': 'lapras',
                'level': 40,
                'nature': 'modest',
                'ability': 'shell-armor',
                'ivs': {'hp': 31, 'attack': 31, 'defense': 31, 'sp_atk': 31, 'sp_def': 31, 'speed': 31},
                'evs': {'hp': 0, 'attack': 4, 'defense': 196, 'sp_atk': 252, 'sp_def': 0, 'speed': 60},
                'types': ['water', 'ice'],
                'held_item': 'sitrus-berry',
                'moves': [
                    {'name': 'ice-shard', 'power': 40, 'type': 'ice', 'class': 'physical', 'accuracy': 100, 'pp': 30, 'max_pp': 48},
                    {'name': 'liquidation', 'power': 85, 'type': 'flying', 'class': 'physical', 'accuracy': 100, 'pp': 10, 'max_pp': 16},
                    {'name': 'earthquake', 'power': 100, 'type': 'ground', 'class': 'physical', 'accuracy': 100, 'pp': 10, 'max_pp': 16},
                    {'name': 'dragon-dance', 'power': 0, 'type': 'dragon', 'class': 'status', 'accuracy': 100, 'pp': 20, 'max_pp': 32},
                ]
            },
            {
                'name': 'tentacruel',
                'level': 40,
                'nature': 'timid',
                'ability': 'clear-body',
                'ivs': {'hp': 31, 'attack': 31, 'defense': 31, 'sp_atk': 31, 'sp_def': 31, 'speed': 31},
                'evs': {'hp': 252, 'attack': 0, 'defense': 120, 'sp_atk': 0, 'sp_def': 0, 'speed': 136},
                'types': ['water', 'poison'],
                'held_item': 'leftovers',
                'moves': [
                    {'name': 'acid-spray', 'power': 0, 'type': 'poison', 'class': 'special', 'accuracy': 100, 'pp': 20, 'max_pp': 32},
                    {'name': 'water-pulse', 'power': 60, 'type': 'water', 'class': 'special', 'accuracy': 100, 'pp': 20, 'max_pp': 32},
                    {'name': 'barrier', 'power': 0, 'type': 'psychic', 'class': 'status', 'accuracy': 100, 'pp': 20, 'max_pp': 32},
                    {'name': 'wrap', 'power': 15, 'type': 'normal', 'class': 'special', 'accuracy': 90, 'pp': 20, 'max_pp': 32},
                ]
            },
            {
                'name': 'mantine',
                'level': 40,
                'nature': 'bold',
                'ability': 'water-absorb',
                'ivs': {'hp': 31, 'attack': 31, 'defense': 31, 'sp_atk': 31, 'sp_def': 31, 'speed': 31},
                'evs': {'hp': 248, 'attack': 0, 'defense': 164, 'sp_atk': 0, 'sp_def': 0, 'speed': 96},
                'types': ['water', 'flying'],
                'held_item': 'sitrus-berry',
                'moves': [
                    {'name': 'air-slash', 'power': 75, 'type': 'flying', 'class': 'special', 'accuracy': 95, 'pp': 15, 'max_pp': 24},
                    {'name': 'toxic', 'power': 0, 'type': 'poison', 'class': 'status', 'accuracy': 90, 'pp': 10, 'max_pp': 16},
                    {'name': 'roost', 'power': 0, 'type': 'flying', 'class': 'status', 'accuracy': 100, 'pp': 5, 'max_pp': 8},
                    {'name': 'scald', 'power': 80, 'type': 'water', 'class': 'special', 'accuracy': 100, 'pp': 15, 'max_pp': 24},
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
                'name': 'gigalith',
                'level': 60,
                'is_shiny': True,
                'nature': 'careful',
                'ability': 'sand-stream',
                'ivs': {'hp': 31, 'attack': 31, 'defense': 31, 'sp_atk': 31, 'sp_def': 31, 'speed': 31},
                'evs': {'hp': 252, 'attack': 0, 'defense': 4, 'sp_atk': 0, 'sp_def': 252, 'speed': 0},
                'types': ['rock'],
                'held_item': 'terrain-extender',
                'moves': [
                    {'name': 'stealth-rock', 'power': 0, 'type': 'rock', 'class': 'status', 'accuracy': 100, 'pp': 20, 'max_pp': 32},
                    {'name': 'stone-edge', 'power': 100, 'type': 'rock', 'class': 'physical', 'accuracy': 80, 'pp': 5, 'max_pp': 8},
                    {'name': 'earthquake', 'power': 100, 'type': 'ground', 'class': 'physical', 'accuracy': 100, 'pp': 10, 'max_pp': 16},
                    {'name': 'protect', 'power': 0, 'type': 'normal', 'class': 'status', 'accuracy': 100, 'pp': 10, 'max_pp': 16}
                ]
            },
            {
                'name': 'toxicroak',
                'level': 60,
                'nature': 'careful',
                'ability': 'dry-skin',
                'ivs': {'hp': 31, 'attack': 31, 'defense': 31, 'sp_atk': 31, 'sp_def': 31, 'speed': 31},
                'evs': {'hp': 0, 'attack': 252, 'defense': 0, 'sp_atk': 0, 'sp_def': 4, 'speed': 252},
                'types': ['poison', 'fighting'],
                'held_item': 'life-orb',
                'moves': [
                    {'name': 'sucker-punch', 'power': 70, 'type': 'dark', 'class': 'physical', 'accuracy': 100, 'pp': 5, 'max_pp': 8},
                    {'name': 'gunk-shot', 'power': 120, 'type': 'poison', 'class': 'physical', 'accuracy': 80, 'pp': 5, 'max_pp': 8},
                    {'name': 'close-combat', 'power': 120, 'type': 'fighting', 'class': 'physical', 'accuracy': 100, 'pp': 5, 'max_pp': 8},
                    {'name': 'knock-off', 'power': 65, 'type': 'dark', 'class': 'status', 'accuracy': 100, 'pp': 20, 'max_pp': 32}
                ]
            },
            {
                'name': 'camerupt',
                'level': 60,
                'nature': 'calm',
                'ability': 'solid-rock',
                'ivs': {'hp': 31, 'attack': 31, 'defense': 31, 'sp_atk': 31, 'sp_def': 31, 'speed': 31},
                'evs': {'hp': 252, 'attack': 0, 'defense': 4, 'sp_atk': 0, 'sp_def': 252, 'speed': 0},
                'types': ['fire', 'ground'],
                'held_item': 'leftovers',
                'moves': [
                    {'name': 'earth-power', 'power': 90, 'type': 'ground', 'class': 'special', 'accuracy': 100, 'pp': 10, 'max_pp': 16},
                    {'name': 'lava-plume', 'power': 80, 'type': 'fire', 'class': 'special', 'accuracy': 100, 'pp': 15, 'max_pp': 24},
                    {'name': 'rock-slide', 'power': 75, 'type': 'rock', 'class': 'special', 'accuracy': 90, 'pp': 10, 'max_pp': 16},
                    {'name': 'roar', 'power': 0, 'type': 'normal', 'class': 'status', 'accuracy': 100, 'pp': 20, 'max_pp': 32}
                ]
            },
            {
                'name': 'hawlucha',
                'level': 60,
                'nature': 'adamant',
                'ability': 'limber',
                'ivs': {'hp': 31, 'attack': 31, 'defense': 31, 'sp_atk': 31, 'sp_def': 31, 'speed': 31},
                'evs': {'hp': 72, 'attack': 252, 'defense': 60, 'sp_atk': 0, 'sp_def': 0, 'speed': 124},
                'types': ['fighting', 'flying'],
                'held_item': 'sitrus-berry',
                'moves': [
                    {'name': 'flying-press', 'power': 100, 'type': 'fighting', 'class': 'physical', 'accuracy': 95, 'pp': 10, 'max_pp': 16},
                    {'name': 'roost', 'power': 0, 'type': 'flying', 'class': 'status', 'accuracy': 100, 'pp': 5, 'max_pp': 8},
                    {'name': 'high-jump-kick', 'power': 130, 'type': 'fighting', 'class': 'physical', 'accuracy': 90, 'pp': 10, 'max_pp': 16},
                    {'name': 'swords-dance', 'power': 0, 'type': 'normal', 'class': 'status', 'accuracy': 100, 'pp': 20, 'max_pp': 32}
                ]
            },
            {
                'name': 'coalossal',
                'level': 60,
                'nature': 'adamant',
                'ability': 'flame-body',
                'ivs': {'hp': 31, 'attack': 31, 'defense': 31, 'sp_atk': 31, 'sp_def': 31, 'speed': 31},
                'evs': {'hp': 248, 'attack': 0, 'defense': 252, 'sp_atk': 0, 'sp_def': 8, 'speed': 0},
                'types': ['rock', 'fire'],
                'held_item': 'passho-berry',
                'moves': [
                    {'name': 'flamethrower', 'power': 90, 'type': 'fire', 'class': 'special', 'accuracy': 100, 'pp': 15, 'max_pp': 24},
                    {'name': 'rock-blast', 'power': 25, 'type': 'rock', 'class': 'physical', 'accuracy': 90, 'pp': 10, 'max_pp': 16},
                    {'name': 'rapid-spin', 'power': 50, 'type': 'normal', 'class': 'physical', 'accuracy': 100, 'pp': 40, 'max_pp': 64},
                    {'name': 'spikes', 'power': 0, 'type': 'ground', 'class': 'status', 'accuracy': 100, 'pp': 20, 'max_pp': 32}
                ]
            },
        ]
    },
    'sprawl': {
        'title': 'Sprawl Warden',
        'biome_unlocked': 'apex', 
        'reward_item': 'z-ring',
        'reward_qty': 1,
        'team': [
            {
                'name': 'klefki',
                'level': 75,
                'is_shiny': True,
                'nature': 'calm',
                'ability': 'prankster',
                'ivs': {'hp': 31, 'attack': 31, 'defense': 31, 'sp_atk': 31, 'sp_def': 31, 'speed': 31},
                'evs': {'hp': 252, 'attack': 0, 'defense': 4, 'sp_atk': 0, 'sp_def': 252, 'speed': 0},
                'types': ['steel', 'fairy'],
                'held_item': 'light-clay',
                'moves': [
                    {'name': 'reflect', 'power': 0, 'type': 'psychic', 'class': 'status', 'accuracy': 100, 'pp': 20, 'max_pp': 32},
                    {'name': 'light-screen', 'power': 0, 'type': 'psychic', 'class': 'status', 'accuracy': 100, 'pp': 30, 'max_pp': 48},
                    {'name': 'spikes', 'power': 0, 'type': 'ground', 'class': 'status', 'accuracy': 100, 'pp': 20, 'max_pp': 32},
                    {'name': 'play-rough', 'power': 90, 'type': 'fairy', 'class': 'physical', 'accuracy': 90, 'pp': 10, 'max_pp': 16}
                ]
            },
            {
                'name': 'rotom-wash',
                'level': 75,
                'nature': 'bold',
                'ability': 'levitate',
                'ivs': {'hp': 31, 'attack': 31, 'defense': 31, 'sp_atk': 31, 'sp_def': 31, 'speed': 31},
                'evs': {'hp': 252, 'attack': 0, 'defense': 160, 'sp_atk': 12, 'sp_def': 84, 'speed': 0},
                'types': ['electric', 'water'],
                'held_item': 'leftovers',
                'moves': [
                    {'name': 'volt-switch', 'power': 70, 'type': 'electric', 'class': 'special', 'accuracy': 100, 'pp': 20, 'max_pp': 32},
                    {'name': 'hydro-pump', 'power': 110, 'type': 'water', 'class': 'special', 'accuracy': 80, 'pp': 5, 'max_pp': 8},
                    {'name': 'will-o-wisp', 'power': 0, 'type': 'fire', 'class': 'status', 'accuracy': 85, 'pp': 15, 'max_pp': 24},
                    {'name': 'hex', 'power': 65, 'type': 'ghost', 'class': 'special', 'accuracy': 100, 'pp': 10, 'max_pp': 16}
                ]
            },
            {
                'name': 'dragonite',
                'level': 75,
                'nature': 'jolly',
                'ability': 'multiscale',
                'ivs': {'hp': 31, 'attack': 31, 'defense': 31, 'sp_atk': 31, 'sp_def': 31, 'speed': 31},
                'evs': {'hp': 0, 'attack': 252, 'defense': 4, 'sp_atk': 0, 'sp_def': 0, 'speed': 252},
                'types': ['dragon', 'flying'],
                'held_item': 'sitrus-berry',
                'moves': [
                    {'name': 'dragon-dance', 'power': 0, 'type': 'dragon', 'class': 'status', 'accuracy': 100, 'pp': 20, 'max_pp': 32},
                    {'name': 'extreme-speed', 'power': 80, 'type': 'normal', 'class': 'physical', 'accuracy': 100, 'pp': 5, 'max_pp': 8},
                    {'name': 'earthquake', 'power': 100, 'type': 'ground', 'class': 'physical', 'accuracy': 100, 'pp': 10, 'max_pp': 16},
                    {'name': 'ice-spinner', 'power': 80, 'type': 'ice', 'class': 'physical', 'accuracy': 100, 'pp': 15, 'max_pp': 24}
                ]
            },
            {
                'name': 'gardevoir',
                'level': 75,
                'nature': 'timid',
                'ability': 'trace',
                'ivs': {'hp': 31, 'attack': 31, 'defense': 31, 'sp_atk': 31, 'sp_def': 31, 'speed': 31},
                'evs': {'hp': 0, 'attack': 0, 'defense': 0, 'sp_atk': 252, 'sp_def': 4, 'speed': 252},
                'types': ['psychic', 'fairy'],
                'held_item': 'babiri-berry',
                'moves': [
                    {'name': 'psychic', 'power': 90, 'type': 'psychic', 'class': 'special', 'accuracy': 100, 'pp': 10, 'max_pp': 16},
                    {'name': 'moonblast', 'power': 95, 'type': 'fairy', 'class': 'special', 'accuracy': 100, 'pp': 15, 'max_pp': 24},
                    {'name': 'mystical-fire', 'power': 75, 'type': 'fire', 'class': 'special', 'accuracy': 100, 'pp': 10, 'max_pp': 16},
                    {'name': 'calm-mind', 'power': 0, 'type': 'psychic', 'class': 'status', 'accuracy': 100, 'pp': 20, 'max_pp': 32}
                ]
            },
            {
                'name': 'bisharp',
                'level': 75,
                'nature': 'adamant',
                'ability': 'defiant',
                'ivs': {'hp': 31, 'attack': 31, 'defense': 31, 'sp_atk': 31, 'sp_def': 31, 'speed': 31},
                'evs': {'hp': 80, 'attack': 252, 'defense': 0, 'sp_atk': 0, 'sp_def': 0, 'speed': 176},
                'types': ['dark', 'steel'],
                'held_item': 'chople-berry',
                'moves': [
                    {'name': 'sucker-punch', 'power': 70, 'type': 'dark', 'class': 'physical', 'accuracy': 100, 'pp': 5, 'max_pp': 8},
                    {'name': 'iron-head', 'power': 80, 'type': 'steel', 'class': 'special', 'accuracy': 100, 'pp': 15, 'max_pp': 24},
                    {'name': 'swords-dance', 'power': 0, 'type': 'normal', 'class': 'status', 'accuracy': 100, 'pp': 20, 'max_pp': 32},
                    {'name': 'psycho-cut', 'power': 70, 'type': 'psychic', 'class': 'physical', 'accuracy': 100, 'pp': 20, 'max_pp': 32}
                ]
            },
            {
                'name': 'kingdra',
                'level': 75,
                'nature': 'modest',
                'ability': 'sniper',
                'ivs': {'hp': 31, 'attack': 31, 'defense': 31, 'sp_atk': 31, 'sp_def': 31, 'speed': 31},
                'evs': {'hp': 0, 'attack': 0, 'defense': 0, 'sp_atk': 252, 'sp_def': 4, 'speed': 252},
                'types': ['water', 'dragon'],
                'held_item': 'choice-specs',
                'moves': [
                    {'name': 'surf', 'power': 90, 'type': 'water', 'class': 'special', 'accuracy': 100, 'pp': 15, 'max_pp': 24},
                    {'name': 'ice-beam', 'power': 90, 'type': 'ice', 'class': 'special', 'accuracy': 100, 'pp': 10, 'max_pp': 16},
                    {'name': 'hurricane', 'power': 110, 'type': 'flying', 'class': 'status', 'accuracy': 70, 'pp': 10, 'max_pp': 16},
                    {'name': 'dragon-pulse', 'power': 85, 'type': 'dragon', 'class': 'special', 'accuracy': 100, 'pp': 10, 'max_pp': 16}
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
    'urshifu-single-strike-gmax': {'type': 'dark', 'name': 'G-Max One Blow'},
    'urshifu-rapid-strike-gmax': {'type': 'dark', 'name': 'G-Max Rapid Flow'}
}

# The Biological Payload for Dynamax Particles
MAX_MOVES = {
    'normal': {'name': 'Max Strike', 'stat': 'speed', 'change': -1, 'target': 'defender'},
    'fire': {'name': 'Max Flare', 'weather': 'sun'},
    'water': {'name': 'Max Geyser', 'weather': 'rain'},
    'electric': {'name': 'Max Lightning', 'terrain': 'electric'}, 
    'grass': {'name': 'Max Overgrowth', 'terrain': 'grassy'},
    'ice': {'name': 'Max Hailstorm', 'weather': 'hail'},
    'fighting': {'name': 'Max Knuckle', 'stat': 'attack', 'change': 1, 'target': 'attacker'},
    'poison': {'name': 'Max Ooze', 'stat': 'special-attack', 'change': 1, 'target': 'attacker'},
    'ground': {'name': 'Max Quake', 'stat': 'special-defense', 'change': 1, 'target': 'attacker'},
    'flying': {'name': 'Max Airstream', 'stat': 'speed', 'change': 1, 'target': 'attacker'},
    'psychic': {'name': 'Max Mindstorm', 'terrain': 'psychic'},
    'bug': {'name': 'Max Flutterby', 'stat': 'special-attack', 'change': -1, 'target': 'defender'},
    'rock': {'name': 'Max Rockfall', 'weather': 'sand'},
    'ghost': {'name': 'Max Phantasm', 'stat': 'defense', 'change': -1, 'target': 'defender'},
    'dragon': {'name': 'Max Wyrmwind', 'stat': 'attack', 'change': -1, 'target': 'defender'},
    'dark': {'name': 'Max Darkness', 'stat': 'special-defense', 'change': -1, 'target': 'defender'},
    'steel': {'name': 'Max Steelspike', 'stat': 'defense', 'change': 1, 'target': 'attacker'},
    'fairy': {'name': 'Max Starfall', 'terrain': 'misty'}
}

WEATHER_MOVES = {
    'rain-dance': 'rain',
    'sunny-day': 'sun',
    'sandstorm': 'sand',
    'hail': 'hail',
    'snowscape': 'hail',
    'chilly-reception': 'hail',
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

TWO_TURN_MOVES = {
                            # --- Weather-skippable ---
                            'solar-beam': {'msg': "absorbed light!", 'skip_weather': ['sun', 'extremely-harsh-sunlight']},
                            'solar-blade': {'msg': "absorbed light!", 'skip_weather': ['sun', 'extremely-harsh-sunlight']},
                            'electro-shot': {'msg': "absorbed electricity!", 'boost': ('sp_atk', 1), 'skip_weather': ['rain', 'heavy-rain']},

                            # --- Semi-invulnerable (untargetable during the charge turn) ---
                            'dig': {'msg': "burrowed its way under the ground!", 'invuln': 'underground'},
                            'fly': {'msg': "flew up high!", 'invuln': 'air'},
                            'bounce': {'msg': "sprang up!", 'invuln': 'air'},
                            'dive': {'msg': "hid underwater!", 'invuln': 'underwater'},
                            'phantom-force': {'msg': "vanished instantly!", 'invuln': 'phantom'},
                            'shadow-force': {'msg': "vanished instantly!", 'invuln': 'phantom'},

                            # --- Charge-turn stat boosts ---
                            'meteor-beam': {'msg': "is overflowing with space power!", 'boost': ('sp_atk', 1)},
                            'skull-bash': {'msg': "tucked in its head!", 'boost': ('defense', 1)},
                            'geomancy': {'msg': "is absorbing power!"},

                            # --- Plain charge turns ---
                            'razor-wind': {'msg': "whipped up a whirlwind!"},
                            'sky-attack': {'msg': "became cloaked in a harsh light!"},
                            'freeze-shock': {'msg': "became cloaked in a freezing light!"},
                            'ice-burn': {'msg': "became cloaked in freezing air!"}
                        }

async def persist_sketch(db, pokemon):
    """
    Write a sketched move back to caught_pokemon.

    Sketch is the only move here that survives the battle, so the new movelist has to
    reach the database rather than living in the combat state. The slot is found by
    position so the other three moves are left exactly as they were.
    """
    if not pokemon.get('_sketched') or 'instance_id' not in pokemon:
        return None

    learned = pokemon.pop('_sketched')
    for index, slot in enumerate((pokemon.get('moves') or [])[:4], start=1):
        if slot.get('name') == learned:
            await db.execute(
                "UPDATE caught_pokemon SET move_%d = ? WHERE instance_id = ?" % index,
                (learned, pokemon['instance_id']))
            return learned
    return None


async def fetch_move_payload(move_name):
    """
    Hydrate a move straight from base_moves, in the shape calculate_damage expects.

    Used by the copy family, which only learns which move it is performing partway
    through a turn and so cannot have its payload prepared up front like the rest.
    """
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("""
            SELECT name, type, power, accuracy, damage_class, pp, priority,
                target, ailment, ailment_chance, stat_name, stat_change, stat_chance,
                status_type, status_chance, healing, drain
            FROM base_moves WHERE name = ?
        """, (move_name,)) as cursor:
            row = await cursor.fetchone()

    if not row:
        return None

    return {
        'name': row[0], 'base_name': row[0], 'type': row[1], 'power': row[2] or 0,
        'accuracy': row[3] or 100, 'class': row[4], 'pp': row[5], 'max_pp': row[5],
        'priority': row[6] or 0, 'target': row[7], 'ailment': row[8],
        'ailment_chance': row[9] or 0, 'stat_name': row[10], 'stat_change': row[11] or 0,
        'stat_chance': row[12] or 0, 'status_type': row[13], 'status_chance': row[14] or 0,
        'healing': row[15] or 0, 'drain': row[16] or 0,
    }


pivot_moves = ['u-turn', 'volt-switch', 'flip-turn', 'baton-pass', 'parting-shot',
               'chilly-reception', 'shed-tail', 'teleport']

phaze_moves = ['roar', 'whirlwind', 'dragon-tail', 'circle-throw']

RAMPAGE_MOVES = ['outrage', 'petal-dance', 'thrash', 'raging-fury', 'uproar']

# Uproar locks in like a rampage but runs a fixed 3 turns and skips the confusion
# that normally follows, so it is excluded from the fatigue branch below.
LOCK_IN_NO_FATIGUE = ['uproar']
                    
OHKO_MOVES = ['fissure', 'horn-drill', 'guillotine', 'sheer-cold']

RECHARGE_MOVES = [
                        'hyper-beam', 'giga-impact', 'frenzy-plant', 'blast-burn', 
                        'hydro-cannon', 'roar-of-time', 'rock-wrecker', 'prismatic-laser', 
                        'meteor-assault', 'eternabeam',
                    ]

TERRAIN_MOVES = {
                        'electric-terrain': 'electric',
                        'grassy-terrain': 'grassy',
                        'misty-terrain': 'misty',
                        'psychic-terrain': 'psychic'
                    }

TERRAIN_MESSAGES = {
    'electric': "⚡ An electric current ran across the battlefield!",
    'grassy': "🌿 Grass grew to cover the battlefield!",
    'misty': "🌫️ Mist swirled around the battlefield!",
    'psychic': "👁️ The battlefield got weird!"
}

# ==========================================
# 🌦️ SHARED MOVE AFTERMATH
# ==========================================
# Everything a move does BESIDES rolling damage: weather, terrain, the room and gravity
# toggles, stat stages, and status.
#
# All of this used to live inline in the main turn loop, so only the main turn loop ran
# it. The NPC has two OTHER action paths - its free swing when the player uses an item,
# and its swing at whatever the player swaps in - and both resolved damage and threw the
# rest away. A rival Rain Dance on either path announced itself and changed nothing at
# all; so did Toxic, Swords Dance and Trick Room. Written as functions so the four call
# sites cannot drift apart again.
#
# Entry hazards are deliberately absent: calculate_damage already lays those, so they
# reach every path on their own.

WEATHER_ROCKS = {'sun': 'heat-rock', 'rain': 'damp-rock',
                 'sand': 'smooth-rock', 'hail': 'icy-rock'}

def deploy_weather(state, move_name, attacker, magic_room=False):
    """
    Put a weather setter's climate on the field. Returns '' if the move sets none.

    The exact display name is tried first so a Max move ('Max Geyser') matches, then the
    hyphenated form for an ordinary move ('rain-dance').
    """
    key = str(move_name)
    new_weather = WEATHER_MOVES.get(key) or WEATHER_MOVES.get(key.lower().replace(' ', '-'))
    if not new_weather:
        return ""

    # A primordial climate outranks anything a move can summon
    if state.get('weather', {}).get('primordial', False):
        return f"↳ The extreme weather prevented `{move_name}` from taking effect!\n"

    held = get_active_item(attacker, magic_room)
    duration = 8 if held == WEATHER_ROCKS.get(new_weather) else 5

    state['weather'] = {'type': new_weather, 'duration': duration, 'primordial': False}
    return f"↳ {WEATHER_MESSAGES.get(new_weather, 'The weather changed.')}\n"


def lay_terrain(state, new_terrain, attacker, magic_room=False, standing=()):
    """
    Put a terrain down. The one place a terrain is ever written.

    Extracted from deploy_terrain in Block 11 so the four surge abilities can lay one
    without inventing a move name to look up - the Terrain Extender clause and the
    already-standing check belong to the terrain, not to how it was asked for.
    """
    if not new_terrain:
        return ""

    if 'terrain' not in state:
        state['terrain'] = {'type': 'none', 'duration': 0}
    if state['terrain']['type'] == new_terrain:
        return ""

    duration = 8 if get_active_item(attacker, magic_room) == 'terrain-extender' else 5
    state['terrain'] = {'type': new_terrain, 'duration': duration}
    log = f"↳ {TERRAIN_MESSAGES[new_terrain]}\n"

    # The seeds fire HERE, where the terrain actually lands, rather than at each of the
    # seven places a terrain can be laid from - a move, a Max move, a surge ability and
    # Block 11's field payload all arrive through this function. Passing the specimens
    # standing in it is the caller's job because only the caller knows who they are.
    #
    # Safe to include a specimen that already fired: seed_on_arrival spends the item, so
    # a second call finds empty hands and says nothing.
    return log + seed_the_field(state, *standing)


def deploy_terrain(state, move_name, attacker, magic_room=False, max_move_type=None,
                   standing=()):
    """Lay a terrain, from a terrain move or from the Max move that carries one."""
    new_terrain = TERRAIN_MOVES.get(str(move_name))
    if not new_terrain and max_move_type:
        new_terrain = (MAX_MOVES.get(max_move_type) or {}).get('terrain')
    return lay_terrain(state, new_terrain, attacker, magic_room, standing)


def seed_on_arrival(pokemon, state, owner_str="", magic_room=False):
    """
    Fire a terrain seed for a specimen that has just arrived, or just been stood on.

    One function for both halves on purpose. A seed that only worked on switch-in would
    sit inert through the Grassy Surge it was bought for, and one that only worked when
    the terrain was laid would do nothing for the specimen brought in AFTER it - and
    those are two different bugs that look identical from the outside.

    Grounded-ness is tested here because it is the same rule for both halves: a Flying
    type standing in Electric Terrain is not in Electric Terrain.
    """
    terrain = (state or {}).get('terrain', {}).get('type', 'none')
    if terrain == 'none':
        return ""
    if not is_grounded(pokemon, (state or {}).get('field', {}).get('gravity', 0) > 0):
        return ""

    fired = terrain_seed_fires(pokemon, terrain, magic_room)
    if not fired:
        return ""

    item, stat, stages = fired
    spend_item(pokemon, item)
    log = (f"🌱 **{owner_str.strip()} {pokemon['name'].capitalize()}**'s "
           f"{item.replace('-', ' ').title()} took root in the "
           f"{terrain.capitalize()} Terrain!\n")
    # Through the shared resolver, like every other stage change, so the boost is
    # visible to Opportunist and reported the same way as any other.
    return log + resolve_stat_stages([(pokemon, stat, stages, None)])


# The roster helpers moved to utils/roster.py when `!equip`, `!unequip` and `!party`
# needed the same question answered. Imported under their old names so every call site
# here reads exactly as it did - the point of the move was to stop a SECOND copy being
# written in economy.py, not to rename anything.
from utils.roster import (PARTNER_WORDS, parse_learn_request, locate_specimen,
                          active_party, party_names, party_counts, set_active_party,
                          clean_party_name, has_party_column, DEFAULT_PARTY,
                          PARTY_SLOTS, MAX_PARTIES)

async def party_filter(db, user_id, alias='up'):
    """
    The WHERE fragment and parameters restricting a roster query to the active party.

    Returned as a fragment rather than baked into each query because five separate
    places build a team out of `user_party`, and a sixth would otherwise be written
    without the scope - which is exactly how a trainer would end up fighting with two
    rosters' worth of specimens.

    An un-migrated database has one party and gets an empty fragment, so every one of
    those five keeps working untouched.
    """
    try:
        if await has_party_column(db):
            prefix = f"{alias}." if alias else ""
            return f"AND {prefix}party_name = ?", (await active_party(db, user_id),)
    except Exception:
        pass
    return "", ()


async def assign_to_party(db, user_id, name, targets, start_slot=None):
    """
    Put several specimens into a roster, and report what happened to each.

    Returns `(placed, skipped)` - `placed` is a list of `(slot, species)` and `skipped`
    a list of `(what_they_typed, why)`. Reported rather than raised, because a list of
    six box numbers with one deployed specimen in it should still assign the other five.

    Nothing is committed here; the caller owns the transaction, so a failure halfway
    through leaves the roster as it was rather than half-built.
    """
    taken = {row[0] for row in await party_members(db, user_id, name)}
    held = {row[1] for row in await party_members(db, user_id, name)}
    free = [slot for slot in range(1, PARTY_SLOTS + 1) if slot not in taken]
    if start_slot is not None:
        free = [start_slot]

    placed, skipped = [], []
    for typed in targets:
        if not free:
            skipped.append((typed, "no free slots left"))
            continue

        pokemon, problem = await locate_specimen(
            db, user_id, typed, "cp.instance_id, s.name")
        if problem:
            # The resolver's complaint is already written for a player, but it is a
            # whole sentence and this is a list - so it is summarised here and the
            # detail is what the single-specimen form still gives.
            skipped.append((typed, "not found"))
            continue

        actual_id, poke_name = pokemon

        if actual_id in held:
            skipped.append((typed, f"{poke_name.capitalize()} is already in this roster"))
            continue

        async with db.execute(
                "SELECT start_time FROM active_deployments WHERE instance_id = ?",
                (actual_id,)) as cursor:
            if await cursor.fetchone():
                skipped.append((typed, f"{poke_name.capitalize()} is on a field mission"))
                continue

        slot = free.pop(0)
        try:
            await db.execute("""
                INSERT INTO user_party (user_id, party_name, slot, instance_id)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, party_name, slot) DO UPDATE SET instance_id = excluded.instance_id;
            """, (user_id, name, slot, actual_id))
        except Exception:
            # Un-migrated database: one party, the old shape.
            await db.execute("""
                INSERT INTO user_party (user_id, slot, instance_id)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, slot) DO UPDATE SET instance_id = excluded.instance_id;
            """, (user_id, slot, actual_id))

        held.add(actual_id)
        placed.append((slot, poke_name))

    return placed, skipped


def assignment_report(name, placed, skipped):
    """What a mass add did, as one embed rather than six messages."""
    colour = (discord.Colour.green() if placed and not skipped
              else discord.Colour.orange() if placed else discord.Colour.red())
    embed = discord.Embed(
        title=f"\U0001f4cb Roster: {name}",
        description=(f"**{len(placed)}** specimen(s) assigned."
                     if placed else "Nothing was assigned."),
        colour=colour)
    if placed:
        embed.add_field(
            name="Assigned",
            value="\n".join(f"Slot {slot}: **{species.capitalize()}**"
                             for slot, species in placed)[:1000],
            inline=False)
    if skipped:
        embed.add_field(
            name="Skipped",
            value="\n".join(f"`{typed}` \u2014 {why}" for typed, why in skipped)[:1000],
            inline=False)
    return embed


PARTY_ACTIONS = ('view', 'add', 'set', 'equip', 'remove', 'clear', 'list',
                 'new', 'create', 'switch', 'use', 'delete', 'rename')


def parse_party_request(request):
    """
    `!party [action] [rest]` split into (action, rest).

    The signature used to be `(action, slot: int, tag_id)`, which meant `!party switch
    alpha` failed to convert `alpha` into a slot number before the body ever ran. Every
    action that takes a NAME rather than a slot needed the whole line instead.
    """
    tokens = " ".join(str(request or "").split()).split()
    if not tokens:
        return 'view', []
    action = tokens[0].lower()
    if action not in PARTY_ACTIONS:
        # `!party 3` is a plausible thing to type, and reading it as an unknown action
        # helps nobody. Anything that is not an action is treated as arguments to view.
        return 'view', tokens
    return action, tokens[1:]


async def ensure_party(db, user_id, name):
    """Record that a party exists, so an empty one still has a name."""
    try:
        await db.execute(
            "INSERT OR IGNORE INTO user_parties (user_id, party_name) VALUES (?, ?)",
            (user_id, name))
    except Exception:
        # No parties table: an un-migrated database has exactly one party and does not
        # need to be told about it.
        pass


async def party_members(db, user_id, name):
    """
    The specimens in one party, with their box numbers, ordered by slot.

    The gts_deposits exclusion is not optional. Thirty other places in this codebase
    number the box by "not deployed AND not on the GTS", and the party view was once the
    one that only said "not deployed" - so the moment a player had anything on the GTS,
    the number shown here was one higher than the number every other command accepts.
    """
    query = """
        WITH Roster AS (
            SELECT instance_id, ROW_NUMBER() OVER(ORDER BY rowid ASC) as box_number
            FROM caught_pokemon
            WHERE user_id = ?
            AND instance_id NOT IN (SELECT instance_id FROM active_deployments)
            AND instance_id NOT IN (SELECT instance_id FROM gts_deposits)
        )
        SELECT up.slot, cp.instance_id, s.name, cp.level, cp.happiness,
            cp.move_1, cp.move_2, cp.move_3, cp.move_4, r.box_number
        FROM user_party up
        JOIN caught_pokemon cp ON up.instance_id = cp.instance_id
        JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
        JOIN Roster r ON cp.instance_id = r.instance_id
        WHERE up.user_id = ? {scope}
        ORDER BY up.slot ASC
    """
    try:
        async with db.execute(query.format(scope="AND up.party_name = ?"),
                              (user_id, user_id, name)) as cursor:
            return await cursor.fetchall()
    except Exception:
        async with db.execute(query.format(scope=""), (user_id, user_id)) as cursor:
            return await cursor.fetchall()


async def party_delete_rows(db, user_id, name, slot=None):
    """Empty a party, or one slot of it. Returns how many specimens were unassigned."""
    clauses, params = ["user_id = ?"], [user_id]
    try:
        if await has_party_column(db):
            clauses.append("party_name = ?")
            params.append(name)
    except Exception:
        pass
    if slot is not None:
        clauses.append("slot = ?")
        params.append(slot)

    cursor = await db.execute(
        f"DELETE FROM user_party WHERE {' AND '.join(clauses)}", tuple(params))
    return cursor.rowcount


class PartyClearConfirm(discord.ui.View):
    """Emptying a whole roster asks first. Rebuilding six slots by hand is a chore."""

    def __init__(self, ctx, name, size):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.name = name
        self.size = size

    async def interaction_check(self, interaction):
        return str(interaction.user.id) == str(self.ctx.author.id)

    @discord.ui.button(label="Empty it", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction, button):
        async with aiosqlite.connect(DB_FILE) as db:
            removed = await party_delete_rows(db, str(self.ctx.author.id), self.name)
            await db.commit()
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            content=f"\U0001f9f9 **{self.name}** emptied \u2014 {removed} specimen(s) "
                    f"returned to your notebook. They are all still yours.",
            view=self)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction, button):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            content="Nothing was changed.", view=self)

async def teaching_route(db, user_id, species_name, pokedex_id, level, move):
    """
    How this specimen may learn this move, as (method, complaint).

    `!learn` asked one question - is this move anywhere in the species movepool - and
    taught it if the answer was yes. `species_movepool` holds every route a species has,
    including `machine`, so every TM move in the game was free the moment the species
    could learn it at all. The TM shelf in the market sold what `!learn` gave away.

    The routes are read in the order the games read them:

    - a move it has GROWN INTO is free
    - otherwise, a move that comes off a MACHINE costs the machine
    - otherwise the complaint names the actual obstacle, because "not physically
      capable" is wrong three different ways: too young, tutor-only, and egg-only are
      all things a player can do something about

    A machine route is checked against the TM case but NOT spent here - this only
    answers what is allowed, and the caller spends it inside its own transaction.
    """
    pretty = str(move).replace('-', ' ').title()
    name = str(species_name).replace('-', ' ').capitalize()

    async with db.execute("""
        SELECT learn_method, MIN(level_learned)
        FROM species_movepool
        WHERE pokedex_id = ? AND move_name = ?
        GROUP BY learn_method
    """, (pokedex_id, move)) as cursor:
        routes = {row[0]: (row[1] or 0) for row in await cursor.fetchall()}

    if not routes:
        return None, (f"❌ Biological mismatch: A **{name}** is not physically capable "
                      f"of learning `{pretty}`.")

    if 'level-up' in routes and level >= routes['level-up']:
        return 'level-up', None

    if 'machine' in routes:
        async with db.execute(
                "SELECT quantity FROM user_tms WHERE user_id = ? AND tm_name = ?",
                (user_id, move)) as cursor:
            held = await cursor.fetchone()
        if held and held[0] > 0:
            return 'machine', None
        return None, (f"💿 `{pretty}` is a **TM move** for {name}, and you do not have "
                      f"that TM. Buy it from the TM shelf in `!market`, then try again. "
                      f"`!tech` lists what you already hold.")

    # It DOES learn it by level-up, just not yet - and it has no machine route to skip
    # the wait with.
    if 'level-up' in routes:
        return None, (f"📈 Your **{name}** needs to reach **Level "
                      f"{routes['level-up']}** before it can master `{pretty}`.")

    if 'tutor' in routes:
        return None, (f"🧠 `{pretty}` is a tutor move. Use `!tutor <tag> {move}` — it "
                      f"costs 500 Eco Tokens and a Memory Spore.")

    if 'egg' in routes:
        return None, (f"🥚 `{pretty}` is an egg move for {name}. It is inherited, not "
                      f"taught.")

    return None, (f"❌ Biological mismatch: A **{name}** cannot learn `{pretty}`.")


def floats_on_arrival(pokemon, state, owner_str="", magic_room=False):
    """
    Announce the Air Balloon, once, for a specimen that has just arrived.

    Every other reason a specimen is off the ground says so out loud the moment it
    matters - a Flying type is read off its own type line, Levitate is announced by the
    ability, Magnet Rise says it as it goes up. The balloon said nothing at all until an
    opponent wasted a Ground move on it, which is the one thing the item exists to stop
    the opponent doing.

    Asked the same way the damage branch asks it: the balloon is only announced when it
    is actually holding the specimen up. Under Gravity it is not, and claiming otherwise
    would be a message contradicted by the very next Earthquake.
    """
    if pokemon is None or pokemon.get('current_hp', 0) <= 0:
        return ""
    if get_active_item(pokemon, magic_room) != 'air-balloon':
        return ""
    if is_grounded(pokemon, (state or {}).get('field', {}).get('gravity', 0) > 0):
        return ""

    return (f"🎈 **{owner_str.strip()} {pokemon['name'].capitalize()}** floats in the "
            f"air with its Air Balloon!\n")


def seed_the_field(state, *combatants):
    """Every specimen currently standing in a freshly laid terrain gets its seed."""
    log = ""
    for pokemon in combatants:
        if pokemon is not None and pokemon.get('current_hp', 0) > 0:
            log += seed_on_arrival(pokemon, state)
    return log


def room_service_on_trick_room(state, *combatants):
    """Room Service, for everyone standing under a Trick Room that has just gone up."""
    log = ""
    for pokemon in combatants:
        if pokemon is None or pokemon.get('current_hp', 0) <= 0:
            continue
        fired = room_service_fires(pokemon)
        if not fired:
            continue
        item, (stat, stages) = fired
        spend_item(pokemon, item)
        log += (f"🛎️ **{pokemon['name'].capitalize()}**'s Room Service slowed it to "
                f"suit the twisted dimensions!\n")
        # Self-inflicted, so nothing screens it - which is correct: Clear Body does not
        # stop a specimen putting its own item on.
        log += resolve_stat_stages([(pokemon, stat, stages, None)])
    return log


def blunder_policy_on_miss(attacker):
    """Blunder Policy, after a move misses because of accuracy."""
    fired = blunder_policy_fires(attacker)
    if not fired:
        return ""
    item, (stat, stages) = fired
    spend_item(attacker, item)
    return (f"💨 **{attacker['name'].capitalize()}**'s Blunder Policy sped it up "
            f"after the miss!\n"
            + resolve_stat_stages([(attacker, stat, stages, None)]))


def deploy_field_toggle(state, move_name, attacker, defender, user_hazards, team_label=None):
    """
    Tailwind, Trick Room, Wonder Room, Magic Room and Gravity.

    `user_hazards` is the ATTACKER's own side - Tailwind blows from behind its user, so it
    is the one field effect here that is not global.
    """
    if 'field' not in state:
        state['field'] = {'trick_room': 0, 'wonder_room': 0, 'gravity': 0, 'magic_room': 0}
    field = state['field']

    if move_name == 'tailwind':
        if user_hazards.get('tailwind', 0) > 0:
            return "↳ But it failed! A tailwind is already blowing!\n"
        user_hazards['tailwind'] = 4
        owner = team_label or attacker['name'].capitalize()
        return f"↳ The Tailwind blew from behind {owner}'s team!\n"

    if move_name == 'trick-room':
        if field['trick_room'] > 0:
            field['trick_room'] = 0
            return "↳ The twisted dimensions returned to normal!\n"
        field['trick_room'] = 5
        # Room Service answers the dimensions going up, for BOTH specimens standing in
        # them - it is not the setter's item alone, and a version that only checked the
        # setter would be silently useless to the half of the field it is bought for.
        return (f"↳ **{attacker['name'].capitalize()}** twisted the dimensions!\n"
                + room_service_on_trick_room(state, attacker, defender))

    if move_name == 'wonder-room':
        if field['wonder_room'] > 0:
            field['wonder_room'] = 0
            return "↳ Wonder Room ended, and stats returned to normal!\n"
        field['wonder_room'] = 5
        return "↳ It created a bizarre area in which Defense and Sp. Def stats are swapped!\n"

    if move_name == 'magic-room':
        if field['magic_room'] > 0:
            field['magic_room'] = 0
            return "↳ Magic Room wore off, and held items regained their power!\n"
        field['magic_room'] = 5
        return "↳ It created a bizarre area in which held items lose their effects!\n"

    if move_name == 'gravity':
        if field['gravity'] > 0:
            return "↳ But it failed! Gravity is already intense!\n"
        field['gravity'] = 5
        log = "↳ Gravity intensified!\n"
        # 🚨 KINETIC GROUNDING: anything currently airborne is slammed into the dirt
        for p in [attacker, defender]:
            if p and p.get('volatile_statuses', {}).get('semi_invulnerable') == 'air':
                end_charge(p)
                log += f"↳ **{p['name'].capitalize()}** couldn't stay airborne because of gravity!\n"
        return log

    return ""


def apply_status_outcome(defender, inflicted, move_stats, attacker=None):
    """
    Land whatever condition the move inflicted: flinch first, then the major statuses.

    Flinch is intercepted rather than written to the status slot - it is a volatile that
    lasts only until the target's next attempt to move.

    `attacker` is optional and read by nothing here except Block 17's Opportunist, which
    needs to know who is opposite before it can copy Steadfast's Speed boost. Callers
    that do not pass it simply lose the copy, not the boost.
    """
    flinch_log = ""
    if inflicted == 'flinch':
        inflicted, flinched = None, True
    else:
        payload = move_stats or {}
        flinched = (payload.get('ailment') == 'flinch'
                    and random.randint(1, 100) <= (payload.get('ailment_chance') or 0))

    # Inner Focus refuses to be rattled. Checked here rather than at each flinch source
    # so Stench, King's Rock and an ordinary flinch chance all meet it.
    if flinched and refuses_volatile(defender, 'flinch'):
        flinched = False

    if flinched:
        defender.setdefault('volatile_statuses', {})['flinch'] = True
        # Steadfast answers the flinch itself rather than the move that caused it,
        # so it belongs here - the one place every flinch source arrives at. The
        # boost is its own doing, so nothing screens it.
        _startled = flinch_reaction(defender)
        if _startled:
            _stat, _stages = _startled
            flinch_log = resolve_stat_stages(
                [(defender, _stat, _stages, None)],
                foe_of=foe_finder(defender, attacker) if attacker is not None else None)

    if not inflicted or inflicted == 'none':
        return flinch_log

    duration = random.randint(1, 3) if inflicted == 'sleep' else -1
    defender['status_condition'] = {'name': inflicted, 'duration': duration}
    icons = {'burn': '🔥', 'poison': '☣️', 'paralysis': '⚡', 'sleep': '💤', 'freeze': '🧊'}
    return flinch_log + (f"{icons.get(inflicted, '⚠️')} "
                         f"**{defender['name'].capitalize()}** was afflicted "
                         f"with {inflicted}!\n")


# Where a payload entry lands, and whose doing it was. Two of these are the engine's
# originals; Block 14 added the other two, because 'the attacker's Speed fell, and the
# DEFENDER did it' had no way to be said.
TARGET_ROUTING = {
    TARGET_ATTACKER:           (lambda a, d: a, lambda a, d: None),
    TARGET_DEFENDER:           (lambda a, d: d, lambda a, d: a),
    TARGET_ATTACKER_FROM_FOE:  (lambda a, d: a, lambda a, d: d),
    TARGET_DEFENDER_SELF:      (lambda a, d: d, lambda a, d: None),
}


def deploy_reaction_field(state, request, setter, prefix=""):
    """
    Lay the weather or terrain a Block 14 reaction asked for.

    `request` is 'weather:sand' or 'terrain:grassy'. Routed through the same two
    writers a MOVE uses, so a Sand Spit sandstorm lasts as long as one a move laid and
    a Smooth Rock stretches it the same way.
    """
    if not state or ':' not in str(request):
        return ""

    kind, _, value = str(request).partition(':')
    magic_room = state.get('field', {}).get('magic_room', 0) > 0

    if kind == 'terrain':
        laid = lay_terrain(state, value, setter, magic_room, standing=(setter,))
        return (prefix + laid.lstrip()) if laid else ""

    if kind == 'weather':
        if state.get('weather', {}).get('primordial'):
            return ""
        if state.get('weather', {}).get('type') == value:
            return ""
        rock = WEATHER_ROCKS.get(value)
        duration = 8 if rock and get_active_item(setter, magic_room) == rock else 5
        state['weather'] = {'type': value, 'duration': duration, 'primordial': False}
        return (f"{prefix}\U0001f30a **{setter['name'].capitalize()}** kicked up "
                f"a {value}storm!\n")

    return ""


def apply_stat_changes(attacker, defender, stat_chgs, prefix="", state=None):
    """
    Move every stage the physics engine asked for, and log each one.

    Volatiles arriving disguised as stat changes are intercepted here; the real stages
    are handed to resolve_stat_stages, which is where Block 8's protection and
    retaliation live. `prefix` is stitched onto each line for the PvP engine, whose log
    indents everything under the move that caused it.
    """
    log = ""
    pending = []

    for tgt, s_name, chg in (stat_chgs or []):
        # A field change smuggled through this channel by Block 14's Sand Spit and
        # Seed Sower. calculate_damage is handed the weather as a string and cannot
        # lay a new one; this function has the state and can.
        if tgt == TARGET_FIELD:
            log += deploy_reaction_field(state, s_name, defender, prefix)
            continue

        target_specimen = TARGET_ROUTING[tgt][0](attacker, defender)
        volatiles = target_specimen.setdefault('volatile_statuses', {})

        if s_name == 'flinch':
            volatiles['flinch'] = True
            continue

        # Intercept Custom Pathogens
        if s_name == 'volatile_leech_seed':
            volatiles.setdefault('leech-seed', True)
            continue
        if s_name == 'volatile_perish_song':
            volatiles.setdefault('perish-song', 3)
            continue

        if s_name not in STAT_STAGE_KEYS:
            continue

        # Who is responsible, read off the routing table. The distinction matters
        # because Block 8 screens on it: Close Combat's own Defense drop is nobody's
        # doing but its user's, while Gooey's Speed drop lands on the attacker and IS
        # somebody else's - so Clear Body refuses one and not the other.
        source = TARGET_ROUTING[tgt][1](attacker, defender)
        pending.append((target_specimen, s_name, chg, source))

    # foe_of is what lets Block 17's Opportunist see across the field. Passed from here
    # because this is the channel every move-driven stage change in both engines flows
    # through - one argument instead of a branch at each of them.
    return log + resolve_stat_stages(pending, prefix=prefix,
                                     foe_of=foe_finder(attacker, defender))


# ==========================================
# 🧠 SHARED NPC MOVE SELECTION
# ==========================================
# One scorer for all three PvE paths. The ordinary turn had the full heuristic, the free
# swing after an item had only the damage half, and the swing at a swapped-in specimen had
# no scoring whatsoever - it picked at random, so the rival would happily throw Splash over
# a super-effective attack.

NPC_HEAL_MOVES = ['roost', 'recover', 'soft-boiled', 'slack-off']
NPC_PATHOGEN_MOVES = ['will-o-wisp', 'toxic', 'thunder-wave', 'spore', 'sleep-powder']
# Derived rather than retyped. The hand-written copy read 'king-shield', which is not a
# move - King's Shield is 'kings-shield' - so the AI's anti-spam rule never recognised it
# and a rival Aegislash would raise the same shield every turn for ever. It was also
# missing Baneful Bunker, Obstruct, Silk Trap and Burning Bulwark, which arrived in
# STANDARD_SHIELDS long after this list was typed out.
NPC_PROTECT_MOVES = list(STANDARD_SHIELDS)


def apply_faint_recoil(fainted, killer):
    """
    What a specimen takes with it when it dies. Aftermath and Innards Out.

    Called from the same place as apply_grudge - the faint check both engines already
    run - so neither ability needs a hook of its own. The figures come from the
    formula, which recorded what the specimen was holding before the blow landed;
    reading current_hp here would be too late, because it is already zero.
    """
    if not fainted or not killer or killer.get('current_hp', 0) <= 0:
        return ""

    toll, ability = faint_recoil(fainted, killer, None,
                                 bool(fainted.get('_killed_by_contact')))
    if toll <= 0 or not ability:
        return ""

    killer['current_hp'] = max(0, killer['current_hp'] - toll)
    return (f"\U0001f4a5 **{fainted['name'].capitalize()}**'s "
            f"{pretty_ability(ability)} took **{toll}** HP from "
            f"**{killer['name'].capitalize()}** on the way down!\n")


def party_of(state, combatant):
    """
    The roster the given specimen belongs to, whichever engine's battle state this is.

    Illusion needs the party of whoever just walked in, and the entry hook is shared by
    both engines - it is handed the state and the two combatants, never a side. Membership
    is by IDENTITY: a trainer fielding two of a species is ordinary, and matching on name
    would have one answering for the other.
    """
    for key in BATTLE_STATE_TEAM_KEYS:
        team = state.get(key) or []
        if any(member is combatant for member in team):
            return team
    return []


def foe_finder(one, other):
    """
    A lookup for "who is this specimen facing", for the handful of things that read
    across the field.

    Handed to resolve_stat_stages by every caller that has both sides to hand. Identity,
    not name: two specimens of the same species are a perfectly ordinary matchup, and
    comparing names would have one answering for the other.
    """
    def look(specimen):
        if specimen is one:
            return other
        if specimen is other:
            return one
        return None
    return look


def apply_knockout_reactions(fainted, killer, *witnesses):
    """
    What a faint is worth to whoever is still standing.

    Two different payouts from one moment, kept apart because they answer different
    questions. Moxie and the rest pay the KILLER, and only for a kill it made; Soul-Heart
    pays a WITNESS for the faint itself, whoever caused it - which is why it is also
    asked at the end of the turn, where poison does its killing and there is no killer to
    speak of. The corpse is marked once, so the two call sites cannot both pay for it.

    Called from the same faint check as apply_grudge and apply_faint_recoil.
    """
    if not fainted or fainted.get('current_hp', 0) > 0:
        return ""

    log = ""
    earned = knockout_boost(killer) if killer is not None and killer is not fainted else None
    if earned:
        stat, stages = earned
        log += (f"\U0001f480 **{killer['name'].capitalize()}**'s "
                f"{pretty_ability(get_active_ability(killer))} "
                f"fed on the knockout!\n")
        log += resolve_stat_stages([(killer, stat, stages, None)],
                                   foe_of=foe_finder(killer, fainted))

    # BATTLE BOND. The other thing a knockout is worth, and the half that was missing for
    # eight blocks while the ability was counted as done on a Water Shuriken line.
    # Banked rather than performed, for the reason every form flip here is: deciding is
    # synchronous and cheap, changing shape needs the species tables. Both engines
    # already await resolve_form_flips a few lines after calling this.
    if killer is not None and killer is not fainted:
        _bonded = battle_bond_form_for(killer)
        if _bonded:
            request_form_flip(killer, _bonded, 'burst into its bonded form')

    # Only pay the mourners once, however many times this corpse is looked at.
    if mark_mourned(fainted):
        for witness in witnesses:
            owed = mourning_boost(witness, fainted)
            if not owed:
                continue
            stat, stages = owed
            log += (f"\U0001f5a4 **{witness['name'].capitalize()}**'s "
                    f"{pretty_ability(get_active_ability(witness))} "
                    f"answered the fall of "
                    f"**{fainted['name'].capitalize()}**!\n")
            log += resolve_stat_stages([(witness, stat, stages, None)],
                                       foe_of=foe_finder(witness, fainted))

    return log


def mourn_the_fallen(*combatants):
    """
    Ask the witnesses about any corpse on the field that has not been answered yet.

    Raised at the end of the turn, where residual damage does its killing: a specimen
    that succumbs to poison or a sandstorm never passes the faint check after a blow, so
    without this Soul-Heart would only ever answer deaths by attack.

    Calling this after a knockout is harmless, but the reason is mark_mourned rather
    than anything here: a corpse already paid for hands back nothing. A skip-if-mourned
    test was written into this loop first and taken out again - it changed no outcome,
    which made it a second copy of a rule that only one place should own.
    """
    log = ""
    for fallen in combatants:
        if not fallen or fallen.get('current_hp', 0) > 0:
            continue
        log += apply_knockout_reactions(
            fallen, None, *[c for c in combatants if c is not fallen])
    return log


def end_of_turn_items(state, *sides):
    """
    Everything the ITEM layer owes at the end of a turn, for both sides, in one pass.

    Each `side` is (specimen, foe, owner_label). The order below is the order the effects
    have to happen in, and each step is here rather than inline for the reason the block
    above spells out - written into one engine, it would be inert in the other:

      the sweep   berries whose threshold this turn's residual damage has just crossed.
                  PvE has run this for as long as berries have existed. PvP never had it
                  at all, so in a duel a Sitrus Berry only ever answered a blow, never a
                  burn - which is the same shape of hole the survival pass filled.
      Cud Chew    the berry banked LAST turn comes back up. After the sweep, so a berry
                  eaten during the sweep is banked with its full delay rather than being
                  half spent by the same tick that created it.
      Harvest     regrows the berry into empty hands. After Cud Chew, so a Harvest berry
                  is never eaten on the turn it appears.
      Pickup      takes whatever the specimen opposite SPENT this turn.

    The spent markers are wiped at the end. Left set, one eaten berry would be picked up
    again every turn for the rest of the battle.
    """
    magic_room = state.get('field', {}).get('magic_room', 0) > 0
    weather = (state.get('weather') or {}).get('type', 'none')
    log = ""

    # Mental Herb, before the berries. Mainline fires it the instant the condition is
    # applied; this engine applies Taunt, Encore, Torment, Disable and infatuation from
    # half a dozen places, and a herb wired into each of them is six chances to forget
    # one. Here it is one line that cannot be missed, at the cost of the holder losing
    # the turn it was Taunted on - which is the honest trade and is worth saying out
    # loud rather than pretending the timing is exact.
    for specimen, _foe, _owner in sides:
        log += apply_mental_herb(specimen, magic_room)

    for specimen, foe, owner in sides:
        log += check_consumables(specimen, owner, magic_room, foe)

    for specimen, _foe, owner in sides:
        chewed = cud_chew_due(specimen)
        if chewed:
            log += (f"🐮 {owner} **{specimen['name'].capitalize()}** coughed up its "
                    f"{chewed.replace('-', ' ').title()} and ate it a second time!\n")
            log += apply_berry_effect(specimen, chewed, ignore_threshold=True,
                                      owner_str=owner)

    for specimen, _foe, owner in sides:
        regrown = harvest_regrows(specimen, weather)
        if regrown:
            specimen['held_item'] = regrown
            log += (f"🌾 {owner} **{specimen['name'].capitalize()}**'s Harvest grew "
                    f"back its {regrown.replace('-', ' ').title()}!\n")

    for specimen, foe, owner in sides:
        found = pickup_finds(specimen, foe)
        if found:
            specimen['held_item'] = found
            log += (f"👜 {owner} **{specimen['name'].capitalize()}** picked up the "
                    f"discarded {found.replace('-', ' ').title()}!\n")

    # Block 20. Multitype and RKS System are an ITEM effect wearing a type, so they are
    # re-asked here rather than only on arrival: a Magic Room that comes down, or an
    # Embargo that lapses, changes what Arceus IS. Stated divergence - the games change
    # the type the instant the item does, and this waits for the end of the turn.
    for specimen, _foe, owner in sides:
        became = rewrite_plate_type(specimen, magic_room)
        if became:
            log += (f"🔆 {owner} **{specimen['name'].capitalize()}** shifted to the "
                    f"{became.title()} type!\n")

    clear_spent_item_markers(*[specimen for specimen, _foe, _owner in sides])
    return log


async def collect_field_spoils(executor, team, user_id):
    """
    Pickup and Honey Gather, paid once the battle is over.

    The whole of Honey Gather and the second half of Pickup: neither has anything to do
    during a turn, so both wait for the reward path rather than being faked into one.
    Returns a log fragment; writes straight into the trainer's inventory, which is the
    same upsert the encounter rewards use.

    A fainted specimen finds nothing - it spent the end of the battle unconscious.
    """
    log = ""
    for specimen in team or []:
        if not specimen or specimen.get('current_hp', 0) <= 0:
            continue

        ability = get_active_ability(specimen)
        if ability in HONEY_GATHER_ABILITIES:
            found = HONEY_GATHER_ITEM
        elif ability in PICKUP_ABILITIES:
            found = random.choice(PICKUP_POOL)
        else:
            continue

        if random.random() >= AFTER_BATTLE_FIND_CHANCE:
            continue

        await executor.execute("""
            INSERT INTO user_inventory (user_id, item_name, quantity)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, item_name) DO UPDATE SET quantity = quantity + 1
        """, (user_id, found))
        log += (f"\n🔎 **{specimen['name'].capitalize()}**'s "
                f"{pretty_ability(ability)} turned up a "
                f"**{found.replace('-', ' ').title()}** after the battle!")

    return log


async def end_of_turn_survival(state, *sides):
    """
    Everything that answers what the TURN did to a specimen, rather than what a move did.

    Four blocks' worth of abilities arrive at this one moment, and they arrive here
    rather than at the dozen places damage is applied because this is the single point
    both engines already look at what the turn cost each side:

      Block 17  Soul-Heart, for a specimen the residual damage has just killed. First,
                because nothing after it would ever see that faint - the blow-by-blow
                check only runs after an attack.
      Block 16  the HP-watching form flips, and Morpeko's mood.
      Block 15  Berserk and Anger Shell, which answer HP having CROSSED below half.
      Block 13  Wimp Out and Emergency Exit, which set the pivot flag the swap check
                below already reads.

    Each `side` is (specimen, must_pivot_flag, owner_label). It was PvE-only code until
    this was pulled out: nine abilities across three blocks were inert in PvP, each one
    written into the ordinary turn and never into the duel. Extracted rather than copied
    for exactly that reason - a third copy would have been a third thing to keep in step.
    """
    combatants = [specimen for specimen, _flag, _owner in sides]

    # Block 21, and first for the same reason Soul-Heart is: a gasser that has just been
    # killed by its own poison is not holding anything down any more, and everything
    # below this line reads abilities that were being smothered a moment ago.
    log = refresh_neutralizing_gas(*combatants)
    log += mourn_the_fallen(*combatants)

    # Block 18's Forecast reads the sky rather than the specimen, but it banks the same
    # request and is cashed in by the same resolver, so it is asked here beside the rest.
    request_field_form_flips(
        (state.get('weather') or {}).get('type', 'none'), *combatants)
    request_hp_form_flips(*combatants)
    log += await resolve_form_flips(*combatants)

    # Opportunist reads across the field, so the boosts below need to know who is facing
    # whom. Singles only ever has two, which is what makes this answerable at all.
    look = foe_finder(*combatants) if len(combatants) == 2 else None

    for specimen, _flag, owner in sides:
        if crossed_below_half(specimen):
            specimen[HP_THRESHOLD_MARKER] = True
            log += (f"\U0001f621 {owner} "
                    f"**{specimen['name'].capitalize()}**'s "
                    f"{pretty_ability(get_active_ability(specimen))} "
                    f"flared up!\n")
            log += resolve_stat_stages(
                [(specimen, _stat, _stages, None)
                 for _stat, _stages in hp_threshold_stages(specimen)],
                foe_of=look)

    # Divergence, stated rather than hidden: the games move the specimen the instant its
    # HP crosses below half, mid-turn. Here it leaves at the END of the turn it was hurt
    # in, so it takes the rest of that turn's chip damage first. That reuses the
    # replacement path faint already drives instead of standing up a second, parallel
    # mid-turn pause in each engine.
    for specimen, flag, owner in sides:
        if wants_to_bail_out(specimen):
            specimen[BAIL_OUT_MARKER] = True
            state[flag] = True
            log += (f"🚪 {owner} **{specimen['name'].capitalize()}**'s "
                    f"{pretty_ability(get_active_ability(specimen))} "
                    f"sent it running for the bench!\n")

    return log


async def resolve_form_flips(*combatants):
    """
    Cash in every form change the predicates have banked.

    One database connection for all of them, and one call site per moment that could
    have caused one. The predicates are synchronous and the species tables are not,
    which is the whole reason a request exists rather than the flip happening where it
    was decided.
    """
    owed = [c for c in combatants if c and c.get(FORM_FLIP_REQUEST)]
    if not owed:
        return ""

    log = ""
    try:
        async with aiosqlite.connect(DB_FILE) as db:
            for combatant in owed:
                form, flavour = combatant.pop(FORM_FLIP_REQUEST)
                was = combatant['name'].replace('-', ' ').title()
                if await assume_species_form(db, combatant, form):
                    log += (f"\U0001f504 **{was}** "
                            f"{flavour or 'changed form'} and became "
                            f"**{combatant['name'].replace('-', ' ').title()}**!\n")
    except Exception as e:
        print(f"DEBUG: Form flip failed: {e}")
        for combatant in owed:
            combatant.pop(FORM_FLIP_REQUEST, None)
    return log


def request_field_form_flips(weather, *combatants):
    """
    Ask Castform whether the sky has changed under it.

    Block 16's watchers read the specimen; this one reads the field, so it needs telling
    what the weather is rather than being able to work it out. Banks a request in the
    same place and shape, and the same resolver cashes it in - which is what makes the
    type change free, since the resolver rebuilds the species half from the tables.
    """
    for combatant in combatants:
        if not combatant or combatant.get('current_hp', 0) <= 0:
            continue
        wanted = weather_form_for(combatant, weather)
        if wanted:
            request_form_flip(combatant, wanted, 'transformed with the weather')


def request_hp_form_flips(*combatants):
    """
    Ask the HP-watchers whether they should be wearing something else.

    Raised at the end of the turn, beside Block 13's bail-out and Block 15's Berserk,
    because that is where both engines already look at what the turn did to a
    specimen's HP. Nothing changes here - it only banks the request.
    """
    for combatant in combatants:
        if not combatant or combatant.get('current_hp', 0) <= 0:
            continue
        wanted = hp_form_for(combatant)
        if wanted:
            request_form_flip(combatant, wanted, 'shifted')
        elif hunger_form_for(combatant):
            request_form_flip(combatant, hunger_form_for(combatant), 'changed its mood')


async def pick_npc_move(db, available_moves, npc, foe, state, context='ATTACK'):
    """
    Score every move the NPC could throw and hand back the best of them.

    Returns (chosen_move, score). `npc` is the one acting, `foe` the one it is scoring
    against. A score of -10000 or worse means "do not do this"; the +10000 bonuses are
    the executioner, which outranks everything else on the board.
    """
    best_moves = []
    highest_score = -10000.0

    foe_types = foe.get('types', [])
    npc_types = npc.get('types', [])
    npc_hp_pct = npc['current_hp'] / max(1, npc.get('max_hp', 1))
    magic_room = state.get('field', {}).get('magic_room', 0) > 0

    for m in available_moves:
        async with db.execute(
            "SELECT type, power, damage_class, healing, target FROM base_moves WHERE name = ?",
            (m['name'],)) as cursor:
            m_data = await cursor.fetchone()

        if not m_data:
            continue

        m_type, m_power, m_class, m_heal, m_target = m_data
        m_power = m_power or 0
        m_heal = m_heal or 0

        # HP-scaled moves store the wrong power (0, or a flat 150 for Eruption). Recompute
        # it for this exact matchup so the AI stops firing a full-strength Water Spout at
        # 10% HP.
        scaled_power = resolve_dynamic_power(m['name'], npc, foe)
        if scaled_power is not None:
            m_power = scaled_power

        score = 10.0  # Base minimum score

        # 1. DAMAGE CALCULATION & THE EXECUTIONER
        if m_class != 'status' and m_power > 0:
            multiplier = 1.0
            for foe_type in foe_types:
                multiplier *= TYPE_CHART.get(m_type, {}).get(foe_type, 1.0)

            # STAB (Same Type Attack Bonus) calculation
            if m_type in npc_types:
                multiplier *= 1.5

            estimated_damage = m_power * multiplier
            score += estimated_damage

            # A rough estimate rather than the full physics engine, which would mean
            # running calculate_damage once per candidate move per turn.
            if estimated_damage >= (foe['current_hp'] * 0.8):
                score += 10000.0

        # 1b. FORMULA-BYPASS MOVES
        # Set damage, level damage, HP-fraction cuts, Endeavor and the OHKO family all
        # carry 0 power in the database, so the block above skips them. We score them on
        # the HP they actually remove.
        elif m['name'] in FORMULA_BYPASS_MOVES:
            payload = estimate_bypass_payload(m['name'], m_type, npc, foe)

            if payload <= 0:
                # Immune, out-levelled, or otherwise guaranteed to fail
                score -= 10000.0
            else:
                score += payload

                if payload >= foe['current_hp']:
                    score += 10000.0   # It secures the KO!
                elif m['name'] == 'final-gambit':
                    # Suiciding without landing the kill is a pure loss
                    score -= 5000.0

        # 2. STATUS & UTILITY SCORING
        if m_class == 'status':

            # Self-Preservation (Smart Healing)
            is_recovery = m_heal > 0 or m['name'] in NPC_HEAL_MOVES
            if is_recovery:
                if npc_hp_pct < 0.4: score += 5000.0      # Bleeding out! Panicked healing!
                elif npc_hp_pct > 0.8: score -= 10000.0   # Don't waste a turn overhealing
                else: score += 500.0

            # Pathogen Targeting (Smart Status Conditions)
            if m['name'] in NPC_PATHOGEN_MOVES:
                if foe.get('status_condition'):
                    score -= 10000.0   # Do not try to burn a poisoned target!
                else:
                    score += 800.0

            # Tactical Setup (Swords Dance, Calm Mind).
            # The column holds a name, not the PokeAPI id - this used to compare it
            # against 7 and so never once fired. Recovery is self-targeted too, and it is
            # the one self-targeted thing a dying specimen SHOULD reach for, so it is
            # scored above and excluded here.
            if m_target == 'user' and not is_recovery and m['name'] not in NPC_PROTECT_MOVES:
                if npc_hp_pct > 0.7: score += 400.0       # Healthy? Set up!
                elif npc_hp_pct < 0.3: score -= 5000.0    # Dying? Do NOT set up!

            # Ability manipulation (Gastro Acid, Skill Swap...)
            # Only worth a turn if it would actually land - most of these fail flat
            # against the wrong target.
            would_land = ability_move_would_land(m['name'], npc, foe)
            if would_land is False:
                score -= 10000.0
            elif would_land:
                score += 600.0

            # Item manipulation (Trick, Bestow, Embargo...)
            item_lands = item_move_would_land(m['name'], npc, foe, magic_room)
            if item_lands is False:
                score -= 10000.0
            elif item_lands:
                score += 600.0

            # Stalling (Smart Protect)
            if m['name'] in NPC_PROTECT_MOVES:
                if state.get('npc_used_protect_last_turn'):
                    score -= 10000.0   # Never spam Protect twice
                elif foe.get('status_condition') or 'leech-seed' in foe.get('volatile_statuses', {}):
                    score += 2000.0    # Player is bleeding out. Stall them!

        # Lock in the highest score
        if score > highest_score:
            highest_score = score
            best_moves = [m]
        elif score == highest_score:
            best_moves.append(m)

    chosen = random.choice(best_moves) if best_moves else random.choice(available_moves)

    # Remember if the NPC used Protect so it doesn't spam it next turn
    state['npc_used_protect_last_turn'] = chosen['name'] in NPC_PROTECT_MOVES

    print(f"DEBUG AI [{context}]: Selected '{chosen['name']}' (Score: {highest_score})")
    return chosen, highest_score

# ==========================================
# 🚨 DYNAMAX LOCKOUT
# ==========================================
# Primal Reversion is Groudon's and Kyogre's transformation, and it is mutually exclusive
# with Dynamax/Gigantamax.
PRIMAL_SPECIES = ['groudon', 'kyogre']

# Zacian, Zamazenta and Eternatus cannot Dynamax in the mainline games at all: the first
# two have the Crowned forms instead, and Eternatus is the source of the phenomenon rather
# than a user of it. Matched on the BASE species, so the block holds whether or not they
# have already taken their other form.
NO_DYNAMAX_SPECIES = set(PRIMAL_SPECIES) | {'zacian', 'zamazenta', 'eternatus'}


def can_dynamax(pokemon):
    """False for species that are barred from Dynamaxing, whatever form they are in."""
    full_name = (pokemon.get('name') or '').lower().strip()
    base_name = full_name.split('-')[0].strip()
    # Two questions, not one. The species list bars every form a species has - a Primal
    # Groudon and an ordinary one are both out. The form list bars ONE form, which is
    # what Ash-Greninja needs: splitting on the first hyphen would have read it as
    # `greninja` and locked the perfectly ordinary base species out with it.
    return (base_name not in NO_DYNAMAX_SPECIES
            and full_name not in GIMMICK_LOCKED_FORMS)


def may_mega_evolve(name, held_item, moves=()):
    """
    Whether this specimen may Mega Evolve, ignoring whether the trainer has a Bracelet.

    The ladder was written out twice - once in the PvE dashboard and once in PvP - with
    the Floette and Raichu exceptions duplicated in both. They had not drifted yet; this
    is the edit that would have made them, since Ash-Greninja had to be added to each.

    `has_mega_stone` is a substring test for 'ite', which is how the codebase has always
    identified a stone. It is loose - `Eviolite` is not a mega stone - but tightening it
    is a different change from this one, and the exceptions below are checked after it.
    """
    name = (name or '').lower().strip()
    base_name = name.split('-')[0].strip()
    held_item = (held_item or 'none').lower()

    has_stone = 'ite' in held_item
    has_dragon_ascent = (base_name == 'rayquaza'
                         and any(m.get('name') == 'dragon-ascent' for m in (moves or [])))
    is_eternal = name == 'floette-eternal'
    is_raichu_alola = name == 'raichu-alola'

    # A form that is already a gimmick does not get a second one.
    if name in GIMMICK_LOCKED_FORMS:
        return False, False
    # Ordinary Floettes of every flower colour cannot Mega Evolve; only Eternal can.
    if base_name.startswith('floette') and not is_eternal:
        has_stone = False
    # ...and only Alolan Raichu.
    if base_name.startswith('raichu') and not is_raichu_alola:
        has_stone = False

    return (has_stone or has_dragon_ascent or is_eternal), has_stone


CHOICE_ITEMS = ['choice-band', 'choice-specs', 'choice-scarf']


def locks_into_one_move(held_item, pokemon=None):
    """
    True when this specimen may only repeat the move it opened with.

    Three call sites used to test the item list directly, which is why Gorilla Tactics
    needed one predicate rather than three more `or` clauses: the ability is a Choice
    Band that cannot be knocked off, so the lock, the greyed-out buttons and the PvP menu
    all have to agree about it.
    """
    if held_item in CHOICE_ITEMS:
        return True
    return bool(pokemon) and get_active_ability(pokemon) in CHOICE_LOCK_ABILITIES


def is_dynamax_active(adaptation):
    """
    True while a Dynamax or Gigantamax transformation is live.

    While Dynamaxed every move becomes a Max Move, and Max Moves neither charge for a
    turn (Meteor Beam, Solar Beam, Fly, Dig) nor leave the user recharging afterwards
    (Hyper Beam, Giga Impact). Both engines use this to skip those lockouts.
    """
    if not adaptation:
        return False
    return bool(adaptation.get('active')) and adaptation.get('type') in ['dynamax', 'gmax']


def normalize_gender(value):
    """
    Stored gender -> "M" / "F" / None.

    caught_pokemon.gender holds the literal string "None" for genderless
    species (and for rows captured before the column was populated), so an
    empty result has to be folded back to a real None for the HUD.
    """
    if not value:
        return None
    value = str(value).strip().upper()
    return value if value in ('M', 'F') else None


async def fetch_gender_rate(db, pokedex_id):
    """
    Species gender_rate: eighths-female (0-8), or -1 for genderless.

    Mirrors the roll ecology.py performs at capture time so NPCs, which have no
    caught_pokemon row, still get a plausible gender.
    """
    async with db.execute(
        "SELECT gender_rate FROM base_pokemon_species WHERE pokedex_id = ?", (pokedex_id,)
    ) as cursor:
        row = await cursor.fetchone()
    return row[0] if row and row[0] is not None else 4


async def roll_species_ability(db, pokedex_id, rng=random):
    """
    Pick an ability for a GENERATED specimen, the way a wild capture does.

    The hidden ability comes up one time in five, which is the figure the capture path in
    cogs/ecology.py already uses. Kept to the same odds deliberately: two places that
    disagreed about a specimen's genetics would be worse than either being wrong, and a
    rival should be built from the same rules as something you could have caught.

    The species table stores 'None' as a STRING for a species with no hidden ability,
    which is why that is tested rather than falsiness.
    """
    async with db.execute(
            "SELECT standard_abilities, hidden_ability FROM base_pokemon_species "
            "WHERE pokedex_id = ?", (pokedex_id,)) as cursor:
        row = await cursor.fetchone()

    if not row:
        return 'none'

    standard, hidden = row
    if hidden and str(hidden).strip().lower() not in ('none', ''):
        if rng.random() <= HIDDEN_ABILITY_CHANCE:
            return str(hidden).strip().lower().replace(' ', '-')

    pool = [a.strip().lower().replace(' ', '-')
            for a in str(standard or '').split(',') if a.strip()]
    return rng.choice(pool) if pool else 'none'


# `roll_gender` was defined here as well as in utils/formulas.py, and the two copies had
# already drifted in two ways. This one returned a real None for a genderless specimen
# while the shared one returns the STRING 'None', which is what caught_pokemon.gender
# stores and what every reader compares against; and this one never learned that a
# species named after a sex has to BE that sex, so a Meowstic Female fielded by an NPC
# was still a coin flip. Imported from utils.formulas now, like everything else here.


async def check_for_evolution(db, user_id, specimen, combat_log):
    """
    Checks if a specimen has hit its genetic threshold for level-based evolution.

    Module-level because both battle engines need it: the PvE dashboard is a View and
    the PvP resolver lives on the Combat cog, so neither can reach a method defined on
    the other. Returns (message, (new_pokedex_id, evolved_name)) or (None, None).
    """
    current_pokedex_id = specimen['pokedex_id']
    current_level = specimen['level']
    current_name = specimen['name']

    # 1. Check the Metamorphosis Rulebook for level-based triggers
    async with db.execute("""
        SELECT er.evolved_species_id, s.name
        FROM evolution_rules er
        JOIN base_pokemon_species s ON er.evolved_species_id = s.pokedex_id
        WHERE er.base_species_id = ?
        AND er.trigger_name = 'level-up'
        AND er.min_level <= ?
    """, (current_pokedex_id, current_level)) as cursor:
        evo_data = await cursor.fetchone()

    # 2. If an evolution is found, return the prompt and the new species ID!
    if evo_data:
        new_pokedex_id, evolved_into_name = evo_data

        # Store the base evolution message (This prompts the user, it doesn't confirm it)
        evo_msg = f"🌟 **{current_name.capitalize()}** reached Level {current_level} and is reacting to the accumulated biomass! It looks ready to evolve into **{evolved_into_name.capitalize()}**!\n"

        return evo_msg, (new_pokedex_id, evolved_into_name)

    return None, None # No evolution occurred

def field_of(state):
    """
    The field dictionary, created on first use so every path shares one rather than
    reading a throwaway {} and quietly dropping whatever was written to it.
    """
    return state.setdefault('field', {'trick_room': 0, 'wonder_room': 0,
                                      'gravity': 0, 'magic_room': 0})


def side_of(state, specimen):
    """
    Which side's slot this specimen occupies. Used for effects banked against a side
    rather than a specimen, so they can be paid out from a single shared hook instead
    of at every one of the half-dozen switch-in paths.
    """
    for key in ('player_team', 'npc_team', 'p1_team', 'p2_team'):
        if any(m is specimen for m in (state.get(key) or [])):
            return key[:-5]
    return None


# ==========================================
# ⚔️ THE RUSTED RELICS
# ==========================================
# Zacian and Zamazenta wake up the moment they are handed their old weapon. Unlike a Mega
# Stone this is not a transformation the player triggers - it happens on entry and holds
# for as long as the relic is held, so it belongs beside the Primal hook rather than in
# the transformation menu.
#
# The ability does not change: base and Crowned both carry Intrepid Sword / Dauntless
# Shield in base_pokemon_species. Those are Block 10 and do nothing yet either way.
CROWNED_FORMS = {
    'zacian':    {'item': 'rusted-sword',  'form': 'zacian-crowned',
                  'swap': ('iron-head', 'behemoth-blade'), 'flavour': 'drew its sword'},
    'zamazenta': {'item': 'rusted-shield', 'form': 'zamazenta-crowned',
                  'swap': ('iron-head', 'behemoth-bash'), 'flavour': 'raised its shield'},
}


async def assume_species_form(db, combatant, form_name):
    """
    Rebuild the species-derived half of a combatant in place, for a new form.

    Level, IVs, EVs and the damage already taken all survive: only what the species tables
    decide - dex id, name, types and base stats - is rewritten. HP moves by the DIFFERENCE
    between the two forms' maxima rather than being rescaled, so a wounded specimen stays
    wounded by the same amount rather than being quietly healed or hurt by the change.

    Returns True when the form was found.
    """
    async with db.execute(
        "SELECT pokedex_id, name FROM base_pokemon_species WHERE name = ?", (form_name,)
    ) as cursor:
        row = await cursor.fetchone()

    if not row:
        print(f"⚠️ WARNING: form '{form_name}' is not in base_pokemon_species!")
        return False

    form_id, display = row
    async with db.execute(
        "SELECT stat_name, base_value FROM base_pokemon_stats WHERE pokedex_id = ?", (form_id,)
    ) as cursor:
        bases = {r[0]: r[1] for r in await cursor.fetchall()}
    async with db.execute(
        "SELECT type_name FROM base_pokemon_types WHERE pokedex_id = ?", (form_id,)
    ) as cursor:
        new_types = [r[0] for r in await cursor.fetchall()]

    level = combatant.get('level', 50)
    ivs = combatant.get('ivs') or {}
    evs = combatant.get('evs') or {}

    def derive(stat_key, db_key):
        base = bases.get(db_key, 50)
        iv = ivs.get(stat_key, 15)
        ev = evs.get(stat_key, 0)
        return math.floor((2 * base + iv + math.floor(ev / 4)) * level / 100) + 5

    new_max_hp = math.floor(
        (2 * bases.get('hp', 50) + ivs.get('hp', 15) + math.floor(evs.get('hp', 0) / 4))
        * level / 100) + level + 10

    combatant['current_hp'] = max(1, combatant['current_hp'] + (new_max_hp - combatant.get('max_hp', new_max_hp)))
    combatant['max_hp'] = new_max_hp
    combatant['current_hp'] = min(combatant['current_hp'], new_max_hp)

    combatant['stats'] = {
        'attack':  derive('attack', 'attack'),
        'defense': derive('defense', 'defense'),
        'sp_atk':  derive('sp_atk', 'special-attack'),
        'sp_def':  derive('sp_def', 'special-defense'),
        'speed':   derive('speed', 'speed'),
    }
    combatant['pokedex_id'] = form_id
    combatant['name'] = display
    combatant['types'] = new_types
    return True


async def reshape_move_slot(combatant, old_name, new_name):
    """
    Turn one move slot into another, keeping the PP already spent on it.

    Behemoth Blade is not learned - it IS Iron Head, reshaped by the relic - so the slot
    holds its position and its remaining PP rather than being handed a fresh one. The
    engine re-reads the payload from base_moves by name every turn, so renaming the slot
    is what actually changes the move; the rest is kept in step for the button label.
    """
    payload = await fetch_move_payload(new_name)
    if not payload:
        print(f"⚠️ WARNING: '{new_name}' is not in base_moves!")
        return False

    reshaped = False
    for slot in (combatant.get('moves') or []):
        if (slot.get('name') or '').lower().replace(' ', '-') != old_name:
            continue
        for key in ('name', 'type', 'power', 'accuracy', 'class'):
            if key in payload:
                slot[key] = payload[key]
        reshaped = True
    return reshaped


# ==========================================
# 🚪 BLOCK 10: WHAT THE ARRIVAL READS OFF THE FIELD
# ==========================================
# Three small readers, kept out of the switch-in hook so they can be tested without
# standing a whole battle up around them.

def download_arms(opponent):
    """
    Which attacking stat Download picks, having looked at both of the target's walls.

    Stages are included, because Download reads the wall as it stands rather than as the
    species table describes it. A tie goes to Sp. Atk, which is the rule in the games -
    Attack only wins when Defense is strictly the softer of the two.
    """
    stats = opponent.get('stats') or {}
    stages = opponent.get('stat_stages') or {}
    wall_phys = apply_stat_stage(stats.get('defense', 50), stages.get('defense', 0))
    wall_spec = apply_stat_stage(stats.get('sp_def', 50), stages.get('sp_def', 0))
    return 'attack' if wall_phys < wall_spec else 'special-attack'


def forewarn_pick(opponent):
    """
    The move Forewarn calls out: the heaviest thing on the other side's list.

    A one-hit KO move outranks everything, however little power its row records - which
    is the whole reason it is worth being warned about.
    """
    best, best_score = None, 0
    for m in (opponent.get('moves') or []):
        name = (m.get('name') or '').lower()
        score = 150 if name in OHKO_MOVES else (m.get('power') or 0)
        if score > best_score:
            best, best_score = m, score
    return best


def anticipation_shudders(entering_combatant, opponent):
    """
    Whether Anticipation feels anything: a super-effective move, an OHKO, or an explosion.

    Reads the move's element against the arrival's own types. A status move cannot be
    super effective, so it is skipped rather than run through the chart.
    """
    for m in (opponent.get('moves') or []):
        name = (m.get('name') or '').lower()
        if name in OHKO_MOVES or name in EXPLOSIVE_MOVES:
            return True

        move_type = m.get('type')
        if not move_type or m.get('class') == 'status':
            continue

        multiplier = 1.0
        for own_type in (entering_combatant.get('types') or []):
            multiplier *= TYPE_CHART.get(move_type, {}).get(own_type, 1.0)
        if multiplier > 1.0:
            return True
    return False


def entry_ability_is_spent(combatant, ability):
    """
    Whether a once-per-battle entry ability has already fired for this specimen.

    Recorded on the specimen itself rather than in volatile_statuses, because volatiles
    are wiped on the way out and "once per battle" has to outlive a switch.
    """
    return ability in (combatant.get(ONCE_PER_BATTLE_MARKER) or set())


def spend_entry_ability(combatant, ability):
    combatant.setdefault(ONCE_PER_BATTLE_MARKER, set()).add(ability)


async def trigger_single_entry_ability(entering_combatant, opponent, owner_str, state, combat_log):
    """Executes passive biological traits for a SINGLE specimen entering the biome."""

    # ==========================================
    # 0. AUTOMATIC PRIMAL REVERSION HOOK
    # ==========================================
    # We check the base name before any transformations have occurred
    base_name = entering_combatant['name'].split('-')[0].lower().strip()
    held_item = (entering_combatant.get('held_item') or "").lower().replace(' ', '-')
    
    is_primal_eligible = (base_name == 'groudon' and held_item == 'red-orb') or (base_name == 'kyogre' and held_item == 'blue-orb')
    # 🚨 DEBUG PRINT: Check your console when the battle starts!
    if base_name in ['groudon', 'kyogre']:
        print(f"DEBUG: Found {base_name}. Held Item: '{held_item}'. Eligible for Primal? {is_primal_eligible}")
    # The 'primal' string check prevents recursive stat-stacking if they swap out and back in!
    if is_primal_eligible and 'primal' not in entering_combatant['name'].lower():
        try:
            target_form = f"%{base_name}%primal%"
            
            # Access the database to fetch the prehistoric biology
            # aiosqlite context managers!
            async with aiosqlite.connect(DB_FILE) as db:
                async with db.execute("SELECT pokedex_id, name FROM base_pokemon_species WHERE name LIKE ?", (target_form,)) as cursor:
                    primal_data = await cursor.fetchone()
            
                if primal_data:
                    form_id, form_name = primal_data
                    
                    async with db.execute("SELECT stat_name, base_value FROM base_pokemon_stats WHERE pokedex_id = ?", (form_id,)) as cursor:
                        db_stats_raw = await cursor.fetchall()
                    db_stats = {row[0]: row[1] for row in db_stats_raw}
                    
                    async with db.execute("SELECT type_name FROM base_pokemon_types WHERE pokedex_id = ?", (form_id,)) as cursor:
                        new_types_raw = await cursor.fetchall() # 🚨 3. Await the fetch!
                    new_types = [row[0] for row in new_types_raw]
                    
                    # Apply the stat transformation
                    level = entering_combatant.get('level', 50)
                    base_hp = db_stats.get('hp', 50)
                    new_max_hp = math.floor((2 * base_hp + 15) * level / 100) + level + 10
                    
                    hp_diff = new_max_hp - entering_combatant['max_hp']
                    entering_combatant['max_hp'] = new_max_hp
                    entering_combatant['current_hp'] = max(1, entering_combatant['current_hp'] + hp_diff)
                    
                    # 1. Safely extract their actual genetics and training (default to 15/0 if missing)
                    iv_hp = entering_combatant.get('iv_hp', 15)
                    ev_hp = entering_combatant.get('ev_hp', 0)
                    
                    # 2. Calculate true Primal HP
                    base_hp = db_stats.get('hp', 50)
                    new_max_hp = math.floor((2 * base_hp + iv_hp + math.floor(ev_hp / 4)) * level / 100) + level + 10
                    
                    hp_diff = new_max_hp - entering_combatant['max_hp']
                    entering_combatant['max_hp'] = new_max_hp
                    entering_combatant['current_hp'] = max(1, entering_combatant['current_hp'] + hp_diff)
                    
                    # 🚨 FIX: Safely extract real IVs and EVs from the payload!
                    ivs = entering_combatant.get('ivs', {})
                    evs = entering_combatant.get('evs', {})

                    # 3. Helper to calculate other stats safely
                    def calc_stat(stat_key, db_key):
                        base = db_stats.get(db_key, 50)
                        iv = ivs.get(stat_key, 15)
                        ev = evs.get(stat_key, 0)
                        return math.floor((2 * base + iv + math.floor(ev / 4)) * level / 100) + 5
                    # 4. Apply true Primal Stats
                    # Apply true Primal Stats
                    base_hp = db_stats.get('hp', 50)
                    iv_hp = ivs.get('hp', 15)
                    ev_hp = evs.get('hp', 0)
                    new_max_hp = math.floor((2 * base_hp + iv_hp + math.floor(ev_hp / 4)) * level / 100) + level + 10

                    hp_diff = new_max_hp - entering_combatant['max_hp']
                    entering_combatant['max_hp'] = new_max_hp
                    entering_combatant['current_hp'] = max(1, entering_combatant['current_hp'] + hp_diff)

                    entering_combatant['stats'] = {
                        'attack': calc_stat('attack', 'attack'),
                        'defense': calc_stat('defense', 'defense'),
                        'sp_atk': calc_stat('sp_atk', 'special-attack'),
                        'sp_def': calc_stat('sp_def', 'special-defense'),
                        'speed': calc_stat('speed', 'speed')
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
                else:
                    print(f"DEBUG: Could not find '{target_form}' in the base_pokemon_species table!")
        except Exception as e:
            print(f"DEBUG: Failed Primal Reversion: {e}")

    # ==========================================
    # 0b. THE RUSTED RELICS (Zacian / Zamazenta)
    # ==========================================
    # The 'crowned' guard is the same trick the Primal hook uses: without it, switching
    # out and back in would re-derive the stats from an already-transformed specimen.
    crowned = CROWNED_FORMS.get(base_name)
    if (crowned and held_item == crowned['item']
            and 'crowned' not in entering_combatant['name'].lower()):
        try:
            async with aiosqlite.connect(DB_FILE) as db:
                if await assume_species_form(db, entering_combatant, crowned['form']):
                    old_move, new_move = crowned['swap']
                    await reshape_move_slot(entering_combatant, old_move, new_move)
                    combat_log += (
                        f"⚔️ **{owner_str.strip()} {base_name.capitalize()}** "
                        f"{crowned['flavour']} and became "
                        f"**{entering_combatant['name'].replace('-', ' ').title()}**!\n")
        except Exception as e:
            print(f"DEBUG: Failed Crowned form change: {e}")

    # What it walked on holding, for Unburden: the boost is for having LOST the item, so
    # a specimen that arrives empty-handed never earns it. Re-recorded on every entry, so
    # switching out and back in with nothing does not keep an old boost alive.
    entering_combatant['_entry_item'] = get_stored_item(entering_combatant)

    # A Healing Wish or Lunar Dance left behind by the previous occupant lands here,
    # before anything else the arrival triggers.
    side = side_of(state, entering_combatant)
    if side is not None:
        pending = state.pop(f"{side}_sacrifice", None)
        if pending is not None:
            note = apply_healing_wish(entering_combatant, restores_pp=pending)
            if note:
                combat_log += note + chr(10)

    # ==========================================
    # 0c. TERA SHIFT (Terapagos)
    # ==========================================
    # Same shape as the Rusted Relics above, minus the item: Terapagos rearranges itself
    # on arrival whatever it is holding. Resolved BEFORE the ability is read, because the
    # form it becomes carries a different one - Tera Shell, from Block 9.
    shift = ENTRY_FORM_SHIFTS.get(get_active_ability(entering_combatant))
    if shift and shift['form'] not in entering_combatant['name'].lower():
        try:
            async with aiosqlite.connect(DB_FILE) as db:
                if await assume_species_form(db, entering_combatant, shift['form']):
                    # The new body carries a different trait. Written here rather than
                    # inside assume_species_form so the Crowned forms, which keep theirs,
                    # are not disturbed.
                    if shift.get('becomes_ability'):
                        entering_combatant['ability'] = shift['becomes_ability']
                    combat_log += (
                        f"🔷 **{owner_str.strip()} {shift['species'].capitalize()}** "
                        f"{shift['flavour']} and became "
                        f"**{entering_combatant['name'].replace('-', ' ').title()}**!\n")
        except Exception as e:
            print(f"DEBUG: Failed Tera Shift: {e}")

    # Block 18: Castform arrives wearing whatever the sky is already doing. Asked here as
    # well as at the end of the turn, so it does not spend its first turn being the wrong
    # element while the rain it walked into goes unnoticed.
    request_field_form_flips((state.get('weather') or {}).get('type', 'none'),
                             entering_combatant)
    combat_log += await resolve_form_flips(entering_combatant)

    # ==========================================
    # BLOCK 21: WHO IS STANDING IN THE GAS
    # ==========================================
    # Asked BEFORE the ability is read, and that ordering is the whole point: a specimen
    # walking into a Neutralizing Gas must not get its arrival ability off first. It also
    # covers the other direction for free - a gasser arriving smothers whatever is already
    # standing there - because the answer is recomputed from the field rather than
    # toggled by whoever happens to have moved.
    combat_log += refresh_neutralizing_gas(entering_combatant, opponent)

    ability = get_active_ability(entering_combatant)
    name = entering_combatant['name'].capitalize()
    opp_name = opponent['name'].capitalize()

    # 1. THE INTIMIDATE HOOK
    # Routed through resolve_stat_stages rather than writing the stage itself, so the
    # commonest stat drop in the game meets Clear Body, Hyper Cutter, Mirror Armor and
    # Defiant the same way every other drop does.
    if ability == 'intimidate':
        # Guard Dog is neither cowed nor merely unbothered - it squares up. Asked
        # before the refusals, because gaining a stage is a different outcome from
        # refusing to lose one and a set cannot say which.
        squares_up = intimidate_reversal(opponent)
        if squares_up:
            gained, stages = squares_up
            combat_log += (f"🐺 **{opp_name}**'s "
                           f"{pretty_ability(get_active_ability(opponent))} "
                           f"answered the Intimidate!\n")
            combat_log += resolve_stat_stages(
                [(opponent, gained, stages, None)],
                foe_of=foe_finder(entering_combatant, opponent))
        elif shrugs_off_intimidate(opponent):
            combat_log += (f"😐 **{opp_name}**'s "
                           f"{get_active_ability(opponent).replace('-', ' ').title()} "
                           f"left it unimpressed by the Intimidate!\n")
        else:
            combat_log += f"💢 **{owner_str.strip()} {name}**'s Intimidate glares at {opp_name}!\n"
            combat_log += resolve_stat_stages(
                [(opponent, 'attack', -1, entering_combatant)])

    # ==========================================
    # 1b. THE ARRIVAL'S OWN BOOST (Intrepid Sword, Dauntless Shield)
    # ==========================================
    # Self-inflicted, so it is enqueued with no source and nothing screens it. Once per
    # battle since Gen 9 - switching out and back in does not earn a second one.
    elif ability in ENTRY_STAT_BOOST_ABILITIES:
        if entry_ability_is_spent(entering_combatant, ability):
            print(f"DEBUG ENTRY: {ability} already spent for {name}")
        else:
            spend_entry_ability(entering_combatant, ability)
            stat, amount = ENTRY_STAT_BOOST_ABILITIES[ability]
            combat_log += (f"⚔️ **{owner_str.strip()} {name}**'s "
                           f"{ability.replace('-', ' ').title()} steeled it!\n")
            combat_log += resolve_stat_stages(
                [(entering_combatant, stat, amount, None)],
                foe_of=foe_finder(entering_combatant, opponent))

    # ==========================================
    # 1c. THE ARRIVAL'S OWN DROP AT THE OPPONENT (Supersweet Syrup)
    # ==========================================
    # Inflicted from the other side, so unlike the boost above this one meets Clear Body
    # and Mirror Armor. Also once per battle.
    elif ability in ENTRY_STAT_DROP_ABILITIES:
        if not entry_ability_is_spent(entering_combatant, ability):
            spend_entry_ability(entering_combatant, ability)
            stat, amount = ENTRY_STAT_DROP_ABILITIES[ability]
            combat_log += (f"🍯 **{owner_str.strip()} {name}** spread a sweet syrupy "
                           f"scent over {opp_name}!\n")
            combat_log += resolve_stat_stages(
                [(opponent, stat, amount, entering_combatant)])

    # ==========================================
    # 1d. DOWNLOAD
    # ==========================================
    # Reads both of the target's walls and arms itself against the softer one.
    elif ability in DOWNLOAD_ABILITIES:
        armed = download_arms(opponent)
        combat_log += (f"📡 **{owner_str.strip()} {name}** downloaded "
                       f"{opp_name}'s data!\n")
        combat_log += resolve_stat_stages(
            [(entering_combatant, armed, 1, None)],
            foe_of=foe_finder(entering_combatant, opponent))

    # ==========================================
    # 1e. THE INFORMANTS (Frisk, Forewarn, Anticipation)
    # ==========================================
    # These change what the trainer knows rather than what the battle does. Frisk and
    # Forewarn report; Anticipation only ever says whether it felt something, which is
    # the whole point of it - it names no move.
    elif ability in FRISK_ABILITIES:
        carried = get_stored_item(opponent)
        if carried and carried != 'none':
            combat_log += (f"🔎 **{owner_str.strip()} {name}** frisked {opp_name} "
                           f"and found a **{carried.replace('-', ' ').title()}**!\n")
        else:
            combat_log += (f"🔎 **{owner_str.strip()} {name}** frisked {opp_name}, "
                           f"which is carrying nothing.\n")

    elif ability in FOREWARN_ABILITIES:
        warned = forewarn_pick(opponent)
        if warned:
            combat_log += (f"🔮 **{owner_str.strip()} {name}**'s Forewarn sensed "
                           f"{opp_name}'s **"
                           f"{warned['name'].replace('-', ' ').title()}**!\n")

    elif ability in ANTICIPATION_ABILITIES:
        if anticipation_shudders(entering_combatant, opponent):
            combat_log += f"😨 **{owner_str.strip()} {name}** shuddered with anticipation!\n"

    # ==========================================
    # 1f. UNNERVE
    # ==========================================
    # Announced here, but enforced in check_consumables - asked at the moment a berry
    # would be eaten rather than remembered from now, so it lapses the instant its owner
    # leaves the field.
    elif ability in BERRY_BLOCKING_ABILITIES:
        combat_log += (f"😰 **{owner_str.strip()} {name}** is too intimidating for "
                       f"{opp_name} to eat any Berries!\n")

    # ==========================================
    # 1g. SCREEN CLEANER
    # ==========================================
    # Sweeps BOTH sides. Its owner gives up its own walls to take the opponent's, which
    # is the trade the ability is - so this deliberately does not spare the arrival's.
    elif ability in SCREEN_CLEANING_ABILITIES:
        swept = False
        for hazard_key in ('player_hazards', 'npc_hazards', 'p1_hazards', 'p2_hazards'):
            habitat = state.get(hazard_key)
            if not isinstance(habitat, dict):
                continue
            for screen in SIDE_SCREEN_KEYS:
                if habitat.get(screen):
                    habitat[screen] = 0
                    swept = True
        if swept:
            combat_log += (f"🧹 **{owner_str.strip()} {name}** swept away every "
                           f"screen on the field!\n")

    # ==========================================
    # 1h. TERAFORM ZERO
    # ==========================================
    elif ability in FIELD_NEUTRALISING_ABILITIES:
        flattened = False
        if state.get('weather', {}).get('type', 'none') != 'none':
            state['weather'] = {'type': 'none', 'duration': 0, 'primordial': False}
            flattened = True
        if state.get('terrain', {}).get('type', 'none') != 'none':
            state['terrain'] = {'type': 'none', 'duration': 0}
            flattened = True
        if flattened:
            combat_log += (f"🌀 **{owner_str.strip()} {name}** flattened the weather "
                           f"and the terrain to nothing!\n")

    # ==========================================
    # 1i. THE RUIN QUARTET
    # ==========================================
    # Announcement only. The arithmetic is a standing 0.75x in stat_multiplier_for, not a
    # stage change - which is why Clear Body cannot refuse it and Haze cannot clear it.
    elif ability in RUIN_ABILITIES:
        combat_log += (f"🏺 **{owner_str.strip()} {name}**'s "
                       f"{ability.replace('-', ' ').title()} weakened "
                       f"{opp_name}'s {RUIN_ABILITIES[ability].replace('_', '. ').title()}!\n")

    # ==========================================
    # 1k. THE TERRAIN SURGES
    # ==========================================
    # The terrain twins of the weather setters below. Hadron Engine is in this table too:
    # it lays the Electric Terrain that its own Sp. Atk row then feeds on.
    elif ability in TERRAIN_SETTER_ABILITIES:
        laid = lay_terrain(state, TERRAIN_SETTER_ABILITIES[ability], entering_combatant,
                           state.get('field', {}).get('magic_room', 0) > 0,
                           standing=(entering_combatant, opponent))
        if laid:
            combat_log += (f"⚡ **{owner_str.strip()} {name}**'s "
                           f"{ability.replace('-', ' ').title()} charged the ground!\n")
            combat_log += laid

    # ==========================================
    # 1l. THE PARADOX ENGINES
    # ==========================================
    # Protosynthesis and Quark Drive are read live from the field on every calculation, so
    # nothing has to be written down for the ordinary case - this branch exists for the
    # OTHER way in. When the field will not run the engine, a Booster Energy will, and
    # that one has to be remembered: once drunk the boost holds for the rest of the
    # battle whatever the weather then does.
    elif ability in PARADOX_ABILITIES:
        magic_room = state.get('field', {}).get('magic_room', 0) > 0
        weather_now = state.get('weather', {}).get('type', 'none')
        terrain_now = state.get('terrain', {}).get('type', 'none')

        if paradox_engine_running(entering_combatant, weather_now, terrain_now):
            boosted = paradox_best_stat(entering_combatant)
            combat_log += (f"🔬 **{owner_str.strip()} {name}**'s "
                           f"{ability.replace('-', ' ').title()} raised its "
                           f"{boosted.replace('_', '. ').title()}!\n")
        elif (get_active_item(entering_combatant, magic_room) == BOOSTER_ENERGY
                and not entering_combatant.get(BOOSTER_SPENT_MARKER)):
            entering_combatant[BOOSTER_SPENT_MARKER] = True
            entering_combatant['held_item'] = 'none'
            mark_item_consumed(entering_combatant, BOOSTER_ENERGY)
            boosted = paradox_best_stat(entering_combatant)
            combat_log += (f"🧪 **{owner_str.strip()} {name}** drank its Booster Energy "
                           f"and raised its {boosted.replace('_', '. ').title()}!\n")

    # ==========================================
    # 1j. THE ALLY-ONLY THREE
    # ==========================================
    # Curious Medicine resets an ALLY's stages, Costar copies an ally's, Hospitality heals
    # one. KyuDex is singles, so there is never an ally for any of them to reach. Written
    # as a branch that deliberately does nothing rather than left out, so the next reader
    # finds the decision here instead of wondering whether it was forgotten.
    elif ability in ALLY_ONLY_ENTRY_ABILITIES:
        print(f"DEBUG ENTRY: {ability} needs an ally; singles has none")

    # ==========================================
    # 1k. BLOCK 20: WEARING ANOTHER IDENTITY
    # ==========================================
    # Four ways of arriving as something other than yourself, all off the one hook every
    # entry point in both engines already goes through.
    elif ability in TRACE_ABILITIES:
        borrowed = traced_ability(entering_combatant, opponent)
        if borrowed:
            # Through the accessor, not the raw key: that is what stashes the original
            # so withdrawing hands Trace back rather than making the copy permanent.
            set_active_ability(entering_combatant, borrowed)
            combat_log += (f"🧬 **{owner_str.strip()} {name}**'s Trace copied "
                           f"{pretty_ability(borrowed)}!\n")

    elif ability in IMPOSTER_ABILITIES:
        # Transform, paid on arrival rather than by spending a turn. apply_transform
        # already refuses to copy a copy and already stashes the original whole, so
        # this is one call rather than a second implementation of the same thing.
        note = apply_transform(entering_combatant, opponent)
        if note:
            combat_log += note + "\n"

    elif ability in ILLUSION_ABILITIES:
        # Deliberately silent. Both trainers read the same combat log, so announcing the
        # disguise here would be the one thing the ability exists to prevent - the log
        # simply calls it by the borrowed name until something breaks it.
        wear_illusion(entering_combatant,
                      disguise_model(party_of(state, entering_combatant),
                                     entering_combatant))

    elif ability in PLATE_TYPE_ABILITIES:
        worn = rewrite_plate_type(entering_combatant,
                                  state.get('field', {}).get('magic_room', 0) > 0)
        if worn:
            combat_log += (f"🔆 **{owner_str.strip()} {name}** took on the "
                           f"{worn.title()} type!\n")

    # ==========================================
    # 1l. THE ALLY-FAINT PAIR
    # ==========================================
    # Receiver and Power of Alchemy inherit a fallen ALLY's ability. In singles the
    # specimen that fills a vacated slot is not an ally, it is a successor - there is
    # never a second body on your own side of the field for either to answer. Written as
    # a branch that does nothing, like the ally-only three above, so the next reader
    # finds the decision rather than wondering whether it was forgotten.
    elif ability in ALLY_FAINT_ABILITIES:
        print(f"DEBUG ENTRY: {ability} needs a fallen ally; singles has none")

    # ==========================================
    # 1m. BLOCK 23: THE DOUBLES-ONLY SEVEN
    # ==========================================
    # Plus, Minus, Friend Guard, Healer, Battery, Power Spot and Commander all need a
    # SECOND body on their own side of the field, and KyuDex is singles. Written as a
    # branch that deliberately does nothing, so a reader wondering whether Battery was
    # forgotten finds the decision here rather than an absence.
    elif ability in DOUBLES_ONLY_ABILITIES:
        print(f"DEBUG ENTRY: {ability} is doubles-only; singles has no second body")

    # ==========================================
    # 1z. THE TERRAIN SEEDS (item Phase 2)
    # ==========================================
    # Below the whole ability ladder rather than inside it. Every branch above is an
    # `elif` on the arriving specimen's ABILITY, and a seed is an item - chaining it on
    # would have made an Electric Seed silently depend on its holder not also having
    # Intimidate, which is the kind of coupling nobody would ever think to test for.
    combat_log += seed_on_arrival(entering_combatant, state, owner_str)
    combat_log += floats_on_arrival(entering_combatant, state, owner_str)

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
            held_item = get_active_item(entering_combatant, state.get('field', {}).get('magic_room', 0) > 0)
            duration = 5

            if w_type == 'sun' and held_item == 'heat-rock': duration = 8
            elif w_type == 'rain' and held_item == 'damp-rock': duration = 8
            elif w_type == 'sand' and held_item == 'smooth-rock': duration = 8
            elif w_type == 'hail' and held_item == 'icy-rock': duration = 8

            state['weather'] = {'type': w_type, 'duration': duration, 'primordial': False}
            # Append a newline so the log parses cleanly!
            combat_log += msg.format(owner=owner_str.strip(), name=name) + "\n"

    return combat_log

class EvolutionConfirmView(discord.ui.View):
    def __init__(self, cog, user_id, pokemon_data, target_species_data):
        super().__init__(timeout=120.0)
        self.cog = cog
        self.user_id = user_id
        self.pokemon = pokemon_data
        
        # Unpack the tuple we are now passing in!
        self.target_id = target_species_data[0]
        self.target_name = target_species_data[1]

    @discord.ui.button(label="Allow Mutation", style=discord.ButtonStyle.success, emoji="✨")
    async def confirm_evo(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            print(f"[DEBUG BUTTON] Clicked by: {interaction.user.id} | Expected: {self.user_id}")

            # Prevent other users from clicking the button
            if str(interaction.user.id) != str(self.user_id):
                return await interaction.response.send_message("You cannot interfere with this specimen's ecology!", ephemeral=True)
            
            # Disable buttons so they can't be spammed
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(view=self)
            
            base_name = self.pokemon['name'].lower()
            current_ability = self.pokemon.get('ability', '').lower().replace(' ', '-')
            response_msg = f"🧬 **{self.pokemon['name'].capitalize()}** successfully mutated into **{self.target_name.capitalize()}**!"

            # Apply the permanent evolution to the database
            async with aiosqlite.connect(DB_FILE) as db:
                
                # 1. Fetch pre-evolution abilities to determine the genetic "slot" (Standard 1, Standard 2, or Hidden)
                async with db.execute("SELECT standard_abilities, hidden_ability FROM base_pokemon_species WHERE pokedex_id = ?", (self.pokemon['pokedex_id'],)) as cursor:
                    base_ab_row = await cursor.fetchone()
                
                base_standards = [a.strip().lower().replace(' ', '-') for a in base_ab_row[0].split(',')] if base_ab_row and base_ab_row[0] else []
                base_hiddens = [a.strip().lower().replace(' ', '-') for a in base_ab_row[1].split(',')] if base_ab_row and base_ab_row[1] else []

                slot_type = 'standard'
                slot_index = 0
                if current_ability in base_hiddens:
                    slot_type = 'hidden'
                    slot_index = base_hiddens.index(current_ability)
                elif current_ability in base_standards:
                    slot_type = 'standard'
                    slot_index = base_standards.index(current_ability)

                # 2. Fetch post-evolution abilities
                async with db.execute("SELECT standard_abilities, hidden_ability FROM base_pokemon_species WHERE pokedex_id = ?", (self.target_id,)) as cursor:
                    target_ab_row = await cursor.fetchone()
                
                target_standards = [a.strip().lower().replace(' ', '-') for a in target_ab_row[0].split(',')] if target_ab_row and target_ab_row[0] else []
                target_hiddens = [a.strip().lower().replace(' ', '-') for a in target_ab_row[1].split(',')] if target_ab_row and target_ab_row[1] else []

                # 3. Determine the new ability based on ecological inheritance
                new_ability = None
                if current_ability in target_standards or current_ability in target_hiddens:
                    new_ability = current_ability  # Keep the exact same ability if the new species has it
                elif slot_type == 'hidden' and target_hiddens:
                    new_ability = target_hiddens[min(slot_index, len(target_hiddens) - 1)]  # Inherit corresponding Hidden Ability
                elif target_standards:
                    new_ability = target_standards[min(slot_index, len(target_standards) - 1)]  # Inherit corresponding Standard slot

                # 4. Update the pokedex_id and new ability
                if new_ability:
                    await db.execute(
                        "UPDATE caught_pokemon SET pokedex_id = ?, ability = ? WHERE instance_id = ?", 
                        (self.target_id, new_ability, self.pokemon['instance_id'])
                    )
                    
                    # Optional: Let the user know the ability changed!
                    if new_ability != current_ability:
                        response_msg += f"\n✨ Its ability became **{new_ability.replace('-', ' ').title()}**!"
                else:
                    await db.execute(
                        "UPDATE caught_pokemon SET pokedex_id = ? WHERE instance_id = ?", 
                        (self.target_id, self.pokemon['instance_id'])
                    )
                
                # ==========================================
                # DIRECTIVE TRACKER: KINETIC MATURATION
                # ==========================================
                await db.execute("""
                    UPDATE field_directives
                    SET current_progress = current_progress + 1
                    WHERE user_id = ? AND objective_type = 'trigger_mutation' 
                    AND (target_variable = 'any' OR target_variable = ?) AND is_completed = 0
                """, (self.user_id, base_name))

                async with db.execute("""
                    SELECT required_amount, current_progress 
                    FROM field_directives
                    WHERE user_id = ? AND objective_type = 'trigger_mutation' 
                    AND (target_variable = 'any' OR target_variable = ?) AND is_completed = 0
                """, (self.user_id, base_name)) as cursor:
                    mut_row = await cursor.fetchone()
                
                if mut_row and mut_row[1] == mut_row[0]:
                    response_msg += "\n\n📡 **Directive Complete:** Kinetic Maturation Study concluded! Run `!claim` to receive your funding."

                await db.commit()
            
            await interaction.followup.send(response_msg)
            
        except Exception as e:
            print(f"\n🚨 CRITICAL BUTTON CRASH (confirm_evo): {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send("⚠️ A critical biological error occurred during mutation.", ephemeral=True)

    @discord.ui.button(label="Suppress", style=discord.ButtonStyle.danger, emoji="🛑")
    async def cancel_evo(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # 🚨 THE DEBUG TRACKER:
            print(f"[DEBUG BUTTON] Clicked by: {interaction.user.id} (Type: {type(interaction.user.id)}) | Expected: {self.user_id} (Type: {type(self.user_id)})")

            if str(interaction.user.id) != str(self.user_id):
                return await interaction.response.send_message("This isn't your specimen!", ephemeral=True)
                
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(view=self)
            
            await interaction.followup.send(f"🛑 You halted **{self.pokemon['name'].capitalize()}**'s mutation process. It remains unchanged.")
            
        except Exception as e:
            print(f"\n🚨 CRITICAL BUTTON CRASH (cancel_evo): {e}")
            traceback.print_exc()

class PvPForcedSwapMenu(discord.ui.View):
    def __init__(self, cog, state, player_id):
        super().__init__(timeout=60)
        self.cog = cog
        self.state = state
        self.player_id = player_id
        self.turn_created = state['turn_number']

        is_p1 = (player_id == state['p1_id'])
        team = state['p1_team'] if is_p1 else state['p2_team']

        # Grab the spatial pointer for the specimen currently on the field
        active_idx = state['p1_active_index'] if is_p1 else state['p2_active_index']

        for i, poke in enumerate(team):
            if poke['current_hp'] > 0 and i != active_idx:
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

class MidTurnSwapMenu(discord.ui.View):
    def __init__(self, cog, state, player_id):
        super().__init__(timeout=120) # Give them 2 minutes to think!
        self.cog = cog
        self.state = state
        self.player_id = player_id
        
        # THE SYNCHRONOUS LOCK
        # We use an asyncio Event to pause the main thread until a button is clicked!
        self.swap_event = asyncio.Event()
        self.selected_index = None

        is_p1 = (player_id == state.get('p1_id', player_id)) # Failsafe for PvE vs PvP state dicts
        team_key = 'p1_team' if 'p1_id' in state else 'player_team'
        team = state[team_key]
        
        active_key = 'p1_active_index' if 'p1_id' in state else 'active_player_index'
        active_idx = state[active_key]

        # Draw the healthy bench buttons
        for i, poke in enumerate(team):
            if poke['current_hp'] > 0 and i != active_idx:
                btn = discord.ui.Button(label=f"{poke['name'].capitalize()} (HP: {poke['current_hp']})", style=discord.ButtonStyle.success)
                btn.callback = self.create_swap_callback(i, poke)
                self.add_item(btn)

    def create_swap_callback(self, idx, poke):
        async def swap_callback(interaction: discord.Interaction):
            if str(interaction.user.id) != str(self.player_id):
                return await interaction.response.send_message("⚠️ You cannot make this substitution!", ephemeral=True)
            
            # 1. Lock in the choice and update the Discord message so they know it worked
            self.selected_index = idx
            await interaction.response.edit_message(content=f"🔒 Withdrawing... Deploying **{poke['name'].capitalize()}**!", view=None)
            
            # 2. TRIGGER THE EVENT! This instantly unpauses the handle_move/process_pvp_turn loop!
            self.swap_event.set()
            
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
        view = await PvPMoveMenu.create(self.cog, self.state, user_id, active_poke)
        await interaction.response.send_message(f"Commanding {active_poke['name'].capitalize()}...", view=view, ephemeral=True)

    @discord.ui.button(label="Swap 🔄", style=discord.ButtonStyle.secondary)
    async def swap_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        
        if self.state['commits'][user_id] is not None:
            return await interaction.response.send_message("🔒 You have already locked in your tactical decision!", ephemeral=True)

        # ==========================================
        # 🚨 THE TRAP FIREWALL
        # ==========================================
        # 1. Identify which researcher clicked the button
        is_p1 = (user_id == str(self.state['p1_id']))
        active_idx = self.state['p1_active_index'] if is_p1 else self.state['p2_active_index']
        team_key = 'p1_team' if is_p1 else 'p2_team'
        opp_team_key = 'p2_team' if is_p1 else 'p1_team'
        opp_active_idx = self.state['p2_active_index'] if is_p1 else self.state['p1_active_index']
        
        # 2. Grab their active biological specimen
        active_poke = self.state[team_key][active_idx]
        opp_poke = self.state[opp_team_key][opp_active_idx]
        
        opp_ability = get_active_ability(opp_poke)
        my_types = active_poke.get('types', [])
        volatiles = active_poke.get('volatile_statuses', {})
        
        # 🚨 THE ULTIMATE SPATIAL LOCK (PvP)
        is_trapped = specimen_is_trapped(active_poke, opp_poke)
        if is_trapped:
            return await interaction.response.send_message("⚠️ Your active specimen is trapped and cannot be withdrawn!", ephemeral=True)
        # ==========================================

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

    @classmethod
    async def create(cls, cog, state, player_id, active_poke):
        """Asynchronous factory to safely build and hydrate the view."""
        # 1. Instantiate the class normally
        view = cls(cog, state, player_id, active_poke)
        
        # 2. Await the database calls/button refreshes
        await view.build_ui()
        
        # 3. Return the fully prepared view
        return view
    
    async def build_ui(self):
        """Clears and redraws the buttons dynamically based on toggle states and held items."""
        try:
            print("DEBUG: build_ui() triggered. Clearing old items...")
            self.clear_items()
            
            is_p1 = (self.player_id == self.state['p1_id'])
            adp_state = self.state['p1_adaptation'] if is_p1 else self.state['p2_adaptation']
            key_items = self.state['p1_key_items'] if is_p1 else self.state['p2_key_items']

            # Imprison sits on the OPPONENT, so the button lock needs both sides
            opp_team_key = 'p2_team' if is_p1 else 'p1_team'
            opp_active_idx = self.state['p2_active_index'] if is_p1 else self.state['p1_active_index']
            opp_poke = self.state[opp_team_key][opp_active_idx]
            pvp_can_act = bool(usable_moves(self.active_poke, opp_poke))
            
            held_item = (self.active_poke.get('held_item') or "").lower().replace(' ', '-')
            # THE TEMPORAL LOCK FLAG
            is_charging = self.active_poke.get('volatile_statuses', {}).get('charging')
            is_recharging = self.active_poke.get('volatile_statuses', {}).get('recharging')
            is_rampage = self.active_poke.get('volatile_statuses', {}).get('rampage')

            is_encore = self.active_poke.get('volatile_statuses', {}).get('encore')

            if is_rampage:
                is_charging = is_rampage['move']
            elif is_encore:
                # Encore reuses the single-move UI lock the charge system already provides
                is_charging = is_encore['move']
                
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
            if not is_charging:
                if not adp_state['used']:
                    # ---MEGA & G-MAX DATABASE CHECK ---
                    base_name = self.active_poke['name'].split('-')[0].lower().strip()
                    held_item = self.active_poke.get('held_item', 'none').lower() # Ensure this is declared!
                    
                    async with aiosqlite.connect(DB_FILE) as db:
                        async with db.execute("SELECT pokedex_id, name FROM base_pokemon_species WHERE name LIKE ? OR name LIKE ?", 
                                    (f"{base_name}-mega%", f"{base_name}-gmax%")) as cursor:
                            available_forms = await cursor.fetchall()
                    
                    mega_forms = [f for f in available_forms if '-mega' in f[1]]
                    gmax_form = next((f for f in available_forms if '-gmax' in f[1]), None)

                    # 1. DYNAMAX / GIGANTAMAX (Primal species are locked out)
                    if key_items.get('dynamax_band') and can_dynamax(self.active_poke):
                        has_gmax = self.active_poke.get('gmax_factor', False) or self.active_poke.get('gmax_factor', 0) == 1
                        
                        # Ensure they actually have a G-Max form in the database before labeling it Gigantamax
                        btn_label = "Gigantamax" if (has_gmax and gmax_form) else "Dynamax"
                        
                        dyna_style = discord.ButtonStyle.success if self.pending_transformation == 'dynamax' else discord.ButtonStyle.danger
                        dyna_btn = discord.ui.Button(label=btn_label, style=dyna_style, emoji="🔴", row=0)
                        dyna_btn.callback = self.create_transform_callback('dynamax')
                        self.add_item(dyna_btn)
                        
                    # 2. MEGA EVOLUTION (Requires Mega Bracelet + Stone OR Rayquaza + Dragon Ascent)
                    # One ladder, shared with the PvP dashboard below. The Floette,
                    # Raichu and Ash-Greninja exceptions were written out twice, and
                    # adding a fourth to both is how the two would have drifted.
                    may_mega, has_mega_stone = may_mega_evolve(
                        self.active_poke.get('name'), held_item,
                        self.active_poke.get('moves'))

                    if mega_forms and may_mega and key_items.get('mega_bracelet'):
                        mega_style = discord.ButtonStyle.success if self.pending_transformation == 'mega' else discord.ButtonStyle.danger
                        
                        # 🚨 FIX: Dynamic UI styling for Z-Megas!
                        btn_label = "⚡ Z-Mega Evolve" if held_item.endswith('-z') else "🧬 Mega Evolve"
                        
                        mega_btn = discord.ui.Button(label=btn_label, style=mega_style, row=0)
                        mega_btn.callback = self.create_transform_callback('mega')
                        self.add_item(mega_btn)
                        
                    # 3. Z-MOVES
                    # 🚨 FIX: Ensure Z-Mega stones don't accidentally trigger the standard elemental Z-Move button
                    is_true_z_crystal = held_item.endswith('-z') and not has_mega_stone
                    
                    if key_items.get('z_ring') and allowed_z_type and is_true_z_crystal:
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
            has_choice_item = locks_into_one_move(held_item, self.active_poke)



            print(f"DEBUG UI BUILD: Lock Move is '{choice_lock_move}', Has Choice Item: {has_choice_item}") # Tripwire 4

            # ==========================================
            # 💢 STRUGGLE FALLBACK (PvP)
            # ==========================================
            # Out of PP, or locked out by Disable / Taunt / Torment / Imprison between
            # them. Either way every move button would be dead, so offer the only thing
            # left rather than stranding the player with nothing to click.
            if not pvp_can_act and not is_recharging:
                struggle_btn = discord.ui.Button(
                    label="💢 Struggle",
                    style=discord.ButtonStyle.danger,
                    row=1
                )
                struggle_btn.callback = self.create_move_callback(
                    {'name': 'struggle', 'pp': 1, 'max_pp': 1}, override_name="Struggle"
                )
                self.add_item(struggle_btn)

            for move in self.active_poke['moves']:
                m_type = move.get('type', 'normal')
                move_class = move.get('class')
                is_status = move.get('class') == 'status'
                
                # Calculate the lock state at the top of the loop!
                is_disabled = (move['pp'] <= 0)
                if has_choice_item and choice_lock_move and move['name'] != choice_lock_move:
                    is_disabled = True

                # Disable / Taunt / Torment / Imprison
                if move_is_restricted(self.active_poke, move, opp_poke):
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
                    # Show live power for HP-scaled moves so the player can see Flail spike
                    # as they get worn down, or Water Spout fall off. Blank for everything else.
                    opp_active = self.state['p2_team'][self.state['p2_active_index']] if is_p1 else self.state['p1_team'][self.state['p1_active_index']]
                    power_hint = format_power_hint(move['name'], self.active_poke, opp_active)

                    label_str = f"{move['name'].replace('-', ' ').title()} ({move['pp']}/{move['max_pp']}){power_hint}"
                    override_name = None

                    if is_recharging:
                        # 🚨 THE RECHARGE UI LOCK
                        btn = discord.ui.Button(
                            label="⏳ Exhausted (Must Recharge)", 
                            style=discord.ButtonStyle.danger, 
                            custom_id="move_recharge_dummy",
                            row=1
                        )
                        
                        # We can reuse your existing fallback/Struggle logic to just pass a dummy move payload
                        dummy_move = {'name': 'recharge', 'pp': 1, 'max_pp': 1}
                        btn.callback = self.create_move_callback(dummy_move, override_name="Recharge")
                        self.add_item(btn)
                    
                    # ==========================================
                    # 🚨 THE TEMPORAL UI LOCK OVERRIDE
                    # ==========================================
                    elif is_charging:
                        # If they are charging, disable every button EXCEPT the one they are locked into
                        is_disabled = (move['name'] != is_charging)
                        btn_style = discord.ButtonStyle.danger if not is_disabled else discord.ButtonStyle.secondary
                        label_str = f"⏳ Execute {move['name'].replace('-', ' ').title()}" if not is_disabled else move['name'].capitalize()
                    else:
                        # If they aren't charging, determine style normally!
                        btn_style = discord.ButtonStyle.primary if move['pp'] > 0 else discord.ButtonStyle.secondary
                    # ====

                    btn = discord.ui.Button(
                        label=label_str[:80], 
                        style=btn_style, 
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
                    
                await self.build_ui()
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
                
            await self.build_ui()
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
                # 🚨 TEMPORAL OVERRIDE: TWO-TURN MOVES 
                # ==========================================
                if 'volatile_statuses' not in self.active_poke:
                    self.active_poke['volatile_statuses'] = {}
                    
                is_charging = self.active_poke['volatile_statuses'].get('charging')
                if is_charging:
                    search_name = is_charging # Force the engine to use the charging move!
                    display_name = is_charging.replace('-', ' ').title()
                # ==========================================

                # ==========================================
                # 💢 STRUGGLE
                # ==========================================
                # Built rather than fetched: the stored row is Normal-type, which would
                # let a Ghost shrug Struggle off entirely.
                if search_name == 'struggle':
                    self.state['commits'][self.player_id] = {
                        'type': 'attack', 'data': struggle_move(), 'transform': None
                    }
                    await interaction.response.edit_message(
                        content="🔒 Locked in: **Struggle**!", view=None)
                    return await self.cog.check_pvp_commits(self.state)

                # ==========================================
                # THE 17-VARIABLE PAYLOAD HYDRATION
                # ==========================================
                async with aiosqlite.connect(DB_FILE) as db:
                    async with db.execute("""
                    SELECT name, type, power, accuracy, damage_class, pp, priority,
                        target, ailment, ailment_chance, stat_name, stat_change, stat_chance, 
                        status_type, status_chance, healing, drain
                    FROM base_moves WHERE name = ?
                """, (search_name,)) as cursor:
                        p_row = await cursor.fetchone()
                
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
                held_item = get_active_item(self.active_poke, self.state.get('field', {}).get('magic_room', 0) > 0)
                print(f"DEBUG LOCK 1: Detected held item: {held_item}") # Tripwire 1
                if locks_into_one_move(held_item, self.active_poke):
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
        
        
        try:
            async with aiosqlite.connect(DB_FILE) as db:
                await db.execute("BEGIN TRANSACTION")
                
                # 1. DOUBLE-CHECK INVENTORY (In case they spent it while the menu was open)
                async with db.execute("SELECT eco_tokens FROM users WHERE user_id = ?", (self.user_id,)) as cursor:
                    funds_row = await cursor.fetchone()
                    funds = funds_row[0] if funds_row else 0
                
                async with db.execute("SELECT quantity FROM user_inventory WHERE user_id = ? AND item_name = 'memory-spore'", (self.user_id,)) as cursor:
                    spores_row = await cursor.fetchone()
                    spore_qty = spores_row[0] if spores_row else 0
                
                if funds < 500 or spore_qty < 1:
                    await db.rollback() # Safely abort the transaction
                    return await interaction.followup.send("❌ **Transaction Failed:** You no longer have the required 500 Eco Tokens and 1 Memory Spore.", ephemeral=True)
                
                # 2. DEDUCT THE RESOURCES
                await db.execute("UPDATE users SET eco_tokens = eco_tokens - 500 WHERE user_id = ?", (self.user_id,))
                await db.execute("UPDATE user_inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_name = 'memory-spore'", (self.user_id,))
                
                # 3. OVERWRITE THE GENETIC CODE
                # Using f-strings for the column name is safe here because target_column is strictly generated by our own code ('move_1' to 'move_4')
                await db.execute(f"UPDATE caught_pokemon SET {target_column} = ? WHERE instance_id = ?", (self.new_move, self.instance_id))
                
                await db.commit()
            
            # 4. UPDATE THE UI
            embed = discord.Embed(
                title="🧠 Neural Rewrite Complete", 
                description=f"The `Memory Spore` successfully catalyzed the dormant genetic traits!\n\n**{self.specimen_name.capitalize()}** forgot the old move and learned **{self.new_move.replace('-', ' ').title()}**.",
                color=discord.Color.green()
            )
            await interaction.edit_original_response(embed=embed, view=None)
            
        except Exception as e:
            print(f"Neural Rewrite Error: {e}")
            await interaction.followup.send("❌ A critical laboratory error occurred.", ephemeral=True)

    async def cancel_callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("⚠️ You cannot interact with this console.", ephemeral=True)
            
        await interaction.response.edit_message(content="🛑 **Operation Aborted:** No resources were consumed and the specimen's genetics remain unaltered.", embed=None, view=None)

class TeachMenu(discord.ui.View):
    def __init__(self, cog, user_id, instance_id, poke_name, new_move, current_moves,
                 consumes_tm=True):
        super().__init__(timeout=60)
        self.cog = cog
        self.user_id = user_id
        self.instance_id = instance_id
        self.poke_name = poke_name
        self.new_move = new_move
        self.current_moves = current_moves
        # Whether a TM is actually being spent. `!tm` always is; `!learn` only when the
        # move has no free route, and burning one for a move the specimen would have
        # grown into anyway is a charge nobody agreed to.
        self.consumes_tm = consumes_tm
        
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
        # 🚨 SECURITY FIREWALL: Ensure the user isn't spoofing the button ID!
        if slot_num not in ['1', '2', '3', '4']:
            return await interaction.response.send_message("⚠️ Invalid move slot detected!", ephemeral=True)
        
        forgotten_move = custom_id.split('_')[2]
        
        async with aiosqlite.connect(DB_FILE) as db:
            # 1. Consume the TM, if one is what is paying for this
            if self.consumes_tm:
                await db.execute("UPDATE user_tms SET quantity = quantity - 1 WHERE user_id = ? AND tm_name = ?", (self.user_id, self.new_move))

            # 2. Overwrite the specific move slot
            col_name = f"move_{slot_num}"
            await db.execute(f"UPDATE caught_pokemon SET {col_name} = ? WHERE instance_id = ?", (self.new_move, self.instance_id))
            
            await db.commit()

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
            # HP-scaled moves store 0 (or a misleading flat 150), so show their real band
            scaled_band = describe_power_range(move['name'])
            if scaled_band:
                pwr_display = scaled_band
            else:
                pwr_display = move['power'] if move['power'] and move['power'] > 0 else "-"
            acc_display = f"{move['accuracy']}%" if move['accuracy'] else "-"
            
            desc = f"**Type:** {move['type'].capitalize()} | {dmg_icon} **{move['class'].capitalize()}**\n"
            desc += f"**Power:** {pwr_display} | **Accuracy:** {acc_display} | **PP:** {move['pp']}"
            
            embed.add_field(
                name=f"{move['name'].replace('-', ' ').title()} (Unlocks at Lv. {move['lvl']})", 
                value=desc, 
                inline=False
            )

        embed.set_footer(text=f"Page {self.current_page + 1}/{self.max_pages} | Use !learn [pokemon] [Slot 1-4] [Move Name]")
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
            
            # ==========================================
            # 🚨 NEW: PRIMORDIAL WEATHER VOLUNTARY CLEAR
            # ==========================================
            weather_cleared_msg = ""
            if state.get('weather', {}).get('primordial', False):
                if get_active_ability(p_active) in ['desolate-land', 'primordial-sea', 'delta-stream']:
                    state['weather'] = {'type': 'none', 'duration': 0, 'primordial': False}
                    weather_cleared_msg = f"🌤️ The primordial weather dissipated as {p_active['name'].capitalize()} retreated!\n"
            # ==========================================

            state['active_player_index'] = selected_index
            new_active = state['player_team'][selected_index]
            n_active = state['npc_team'][state['active_npc_index']]

            # Boosts belong to the slot, not the specimen: a Swords Dance does not
            # survive a switch out and back in.
            p_active['volatile_statuses'] = {}
            leave_field(p_active)

            if self.forced:
                combat_log = f"You sent out **{new_active['name'].capitalize()}**!\n"
                
                try:
                    combat_log = await trigger_single_entry_ability(new_active, n_active, "Your", state, combat_log)
                    hazard_log = apply_entry_hazards(new_active, state['player_hazards'], TYPE_CHART, "Your")
                    if hazard_log: combat_log += hazard_log

                    #Did the hazards trigger a berry?
                    berry_log = check_consumables(new_active, "Your", state.get('field', {}).get('magic_room', 0) > 0, n_active)
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
                    n_hazards=state.get('npc_hazards'),
                    p_name=new_active.get('name'), p_level=new_active.get('level'),
                    p_gender=new_active.get('gender'), n_gender=n_active.get('gender'),
                    n_name=n_active.get('name'), n_level=n_active.get('level'),
                    p_aura=battle_render.aura_for(state.get('adaptation'), new_active),
                    biome=state.get('warden_biome')
                )
                # Attach the newly generated image to the state so render_dashboard can use it!
                self.main_battle_view.current_battle_file = battle_file
                print("DEBUG: Handoff to main_battle_view.render_dashboard (Forced Swap)")
                return await self.main_battle_view.render_dashboard(interaction, combat_log)
                
            else:
                combat_log = f"**Turn {state['turn_number']}**\n\n"
                combat_log += f"You recalled your specimen and sent out **{new_active['name'].capitalize()}**!\n"
                if weather_cleared_msg:
                    combat_log += weather_cleared_msg
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
                    n_hazards=state.get('npc_hazards'),
                    p_name=new_active.get('name'), p_level=new_active.get('level'),
                    p_gender=new_active.get('gender'), n_gender=n_active.get('gender'),
                    n_name=n_active.get('name'), n_level=n_active.get('level'),
                    p_aura=battle_render.aura_for(state.get('adaptation'), new_active),
                    biome=state.get('warden_biome')
                )
                # Because process_turn_end generates its OWN image later in Phase 5, we actually 
                # don't need to assign this to self.main_battle_view.current_battle_file right here.
                # However, generating it prevents the pointer corruption bug before the handoff!
                #    
                try:
                    combat_log = await trigger_single_entry_ability(new_active, n_active, "Your", state, combat_log)
                    hazard_log = apply_entry_hazards(new_active, state['player_hazards'], TYPE_CHART, "Your")
                    if hazard_log: combat_log += hazard_log
                    # Did the hazards trigger a berry?
                    berry_log = check_consumables(new_active, "Your", state.get('field', {}).get('magic_room', 0) > 0, n_active)
                    if berry_log: combat_log += berry_log
                except Exception as e:
                    print(f"DEBUG: Error applying voluntary swap hazards/abilities: {e}")

                if new_active['current_hp'] > 0:
                    available_moves = usable_moves(n_active, p_active)
                    if available_moves:
                        async with aiosqlite.connect(DB_FILE) as db:
                            # Scored against p_active, the specimen that was standing there
                            # when the NPC committed - a switch does not let the opponent
                            # re-pick in the mainline games either. The blow still lands on
                            # whoever came in.
                            chosen_move, _score = await pick_npc_move(
                                db, available_moves, n_active, p_active, state,
                                context='SWAP-IN SWING')
                            chosen_move['pp'] -= 1

                            async with db.execute("""
                            SELECT type, power, accuracy, damage_class, target, ailment, ailment_chance,
                                stat_name, stat_change, stat_chance, healing, drain, name, priority
                            FROM base_moves WHERE name = ?
                        """, (chosen_move['name'],)) as cursor:
                                n_row = await cursor.fetchone()

                        if n_row:
                            # Perfectly mapped all 14 variables
                            n_move_stats = {
                                'type': n_row[0], 'power': n_row[1] or 0, 'accuracy': n_row[2] or 100, 'class': n_row[3],
                                'target': n_row[4], 'ailment': n_row[5], 'ailment_chance': n_row[6] or 0,
                                'stat_name': n_row[7], 'stat_change': n_row[8] or 0, 'stat_chance': n_row[9] or 0,
                                'healing': n_row[10] or 0, 'drain': n_row[11] or 0,
                                'name': n_row[12], 'priority': n_row[13] or 0
                            }
                            
                            # Now that this path scores its move properly it can pick a
                            # status move, which nothing "strikes" anybody with.
                            move_label = chosen_move['name'].replace('-', ' ').title()
                            if n_move_stats['class'] == 'status':
                                combat_log += f"🔴 The rival's **{n_active['name'].capitalize()}** used `{move_label}`!\n"
                            else:
                                combat_log += f"🔴 The rival's **{n_active['name'].capitalize()}** struck the incoming Pokémon with `{move_label}`!\n"
                            
                            if random.randint(1, 100) > n_move_stats['accuracy']:
                                combat_log += "The attack missed!\n"
                            else:
                                dmg, msg, inf_status, stat_chgs, heal_amt = calculate_damage(
                                    n_active, new_active, n_move_stats, 
                                    weather=state.get('weather', {'type': 'none'})['type'], 
                                    target_hazards=state['player_hazards'], # The NPC attacks the Player's habitat
                                    user_hazards=state['npc_hazards'],
                                    user_party=state['npc_team'],
                                    terrain=state.get('terrain', {'type': 'none'})['type'],
                                    wonder_room=state.get('field', {}).get('wonder_room', 0) > 0,
                                    gravity=state.get('field', {}).get('gravity', 0) > 0,
                                    magic_room=state.get('field', {}).get('magic_room', 0) > 0,
                                    field=field_of(state)
                                )
                                new_active['current_hp'] = max(0, new_active['current_hp'] - dmg)
                                if msg: combat_log += f"*{msg}*\n"
                                # Tell the UI to actually announce the damage!
                                if dmg > 0: combat_log += f"↳ Dealt **{dmg}** damage.\n"

                                if heal_amt > 0:
                                    n_active['current_hp'] = min(n_active.get('max_hp', 100),
                                                                 n_active['current_hp'] + heal_amt)
                                    combat_log += f"💚 **{n_active['name'].capitalize()}** recovered health!\n"

                                # ==========================================
                                # 🌦️ THE REST OF THE MOVE
                                # ==========================================
                                # This swing at the incoming specimen used to resolve damage
                                # and discard everything else, so a rival Rain Dance, Toxic or
                                # Swords Dance thrown here did nothing whatsoever.
                                combat_log += apply_stat_changes(n_active, new_active, stat_chgs, state=state)
                                combat_log += apply_status_outcome(new_active, inf_status, n_move_stats, n_active)

                                magic_room_on = state.get('field', {}).get('magic_room', 0) > 0
                                move_name_used = chosen_move['name']
                                combat_log += deploy_weather(state, move_name_used, n_active, magic_room_on)
                                combat_log += deploy_terrain(state, move_name_used, n_active, magic_room_on,
                                                             standing=(n_active, new_active))
                                combat_log += deploy_field_toggle(state, move_name_used, n_active,
                                                                  new_active, state['npc_hazards'])
                else:
                    combat_log += f"💀 Your **{new_active['name'].capitalize()}** couldn't survive the treacherous habitat!\n"

                await self.main_battle_view.refresh_buttons()
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
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute("UPDATE user_inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_name = ?", (self.user_id, selected_item))
            await db.commit()

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

class ForfeitConfirm(discord.ui.View):
    """
    Second step on abandoning an expedition. A single mis-click on the dashboard would
    otherwise throw away a whole battle, so the actual teardown lives behind this.
    """

    def __init__(self, dashboard):
        super().__init__(timeout=60)
        self.dashboard = dashboard

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.dashboard.user_id:
            await interaction.response.send_message(
                "⚠️ This is not your field expedition!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="🏳️ Confirm Forfeit", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = self.dashboard.cog.active_battles.pop(self.dashboard.user_id, None)

        for child in self.dashboard.children:
            child.disabled = True
        self.dashboard.stop()

        # Leave the battle message on screen but visibly finished
        try:
            if state and state.get('message_obj'):
                await state['message_obj'].edit(
                    content="🏳️ **Expedition abandoned.** No research funding was recovered.",
                    view=self.dashboard, attachments=[])
        except Exception as e:
            print(f"DEBUG: Could not tidy up the forfeited battle message: {e}")

        await interaction.response.edit_message(
            content="🏳️ You withdrew from the expedition.", view=None)

    @discord.ui.button(label="↩️ Keep Fighting", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="💪 You stayed in the field.", view=None)


class BattleDashboard(discord.ui.View):
    def __init__(self, cog, user_id, ctx):
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = str(user_id)
        self.ctx = ctx
    
    @classmethod
    async def create(cls, cog, user_id, ctx):
        """Asynchronous factory to safely build and hydrate the view."""
        # 1. Instantiate the class normally
        view = cls(cog, user_id, ctx)
        
        # 2. Await the database calls/button refreshes
        await view.refresh_buttons()
        
        # 3. Return the fully prepared view
        return view

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
            n_hazards=state.get('npc_hazards'),
            p_name=p_active.get('name'), p_level=p_active.get('level'),
            p_gender=p_active.get('gender'), n_gender=n_active.get('gender'),
            n_name=n_active.get('name'), n_level=n_active.get('level'),
            p_aura=battle_render.aura_for(state.get('adaptation'), p_active),
            biome=state.get('warden_biome')
        )
        # ==========================================
        await self.refresh_buttons()
        # Dynamically grab the new randomized filename!
        if battle_file:
                embed.set_image(url=f"attachment://{battle_file.filename}")
                await interaction.edit_original_response(embed=embed, view=self, attachments=[battle_file])
        else:
            await interaction.edit_original_response(embed=embed, view=self, attachments=[])

    async def check_for_evolution(self, db, user_id, specimen, combat_log):
        """Thin wrapper so existing PvE call sites keep working. See the module-level
        implementation, which the PvP resolver on the Combat cog also uses."""
        return await check_for_evolution(db, user_id, specimen, combat_log)


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
                await self.refresh_buttons()
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
            # The transformed form becomes the new baseline, so discard any pending
            # Guard Split / Power Trick snapshot rather than reverting to it later.
            clear_base_stat_snapshot(p_active)

            state['adaptation']['backup'] = {
                'name': p_active['name'],
                'pokedex_id': p_active['pokedex_id'],
                'max_hp': p_active['max_hp'],
                'stats': p_active['stats'].copy(),
                'types': list(p_active.get('types', []))
            }
            
            # 🚨 PRIMAL FIREWALL: reject a stale Dynamax/G-Max button server-side
            if not can_dynamax(p_active) and (form_name == 'dynamax' or 'gmax' in str(form_name).lower()):
                return await interaction.followup.send(
                    f"⚠️ **{p_active['name'].capitalize()}** channels Primal energy and cannot Dynamax!",
                    ephemeral=True
                )

            # 2. APPLY THE ADAPTATION (Dynamax vs Mega/Gmax)
            if form_name == 'dynamax':
                print("DEBUG: Applying generic Dynamax logic...")
                hp_boost = math.floor(p_active['max_hp'] * 0.5)
                p_active['max_hp'] += hp_boost
                p_active['current_hp'] += hp_boost
                p_active['name'] = f"{old_name} (Dynamax)"
                
                # `holder` is which SPECIMEN spent it. Without it the badge belongs to
                # the trainer, and a transformed specimen that fainted handed its aura
                # to whatever was sent out next.
                state['adaptation'].update({'used': True, 'active': True, 'type': 'dynamax', 'turns': 3,
                                            'holder': battle_render.adaptation_holder(p_active)})
                log_msg = f"🔴 **{old_name.capitalize()}** absorbed Galar particles and Dynamaxed!"
                
            else:
                print("DEBUG: Applying Mega/G-Max logic. Connecting to DB...")
                async with aiosqlite.connect(DB_FILE) as db:
                    # Fetch Stats
                    async with db.execute("SELECT stat_name, base_value FROM base_pokemon_stats WHERE pokedex_id = ?", (form_id,)) as cursor:
                        raw_stats = await cursor.fetchall()
                    
                    # Fetch Types
                    async with db.execute("SELECT type_name FROM base_pokemon_types WHERE pokedex_id = ?", (form_id,)) as cursor:
                        type_rows = await cursor.fetchall()
                        new_types = [row[0] for row in type_rows]
                    
                    #  Fetch the mutated biological ability!
                    try:
                        # Query the species table directly to extract the genetic trait!
                        async with db.execute("SELECT standard_abilities FROM base_pokemon_species WHERE pokedex_id = ?", (form_id,)) as cursor:
                            ab_data = await cursor.fetchone()
                        
                        # Ensure we actually grabbed a valid string before mutating the state
                        if ab_data and ab_data[0]:
                            # Slice the string at the comma, grab the first ability, and sanitize it!
                            raw_ability = ab_data[0].split(',')[0].strip()
                            p_active['ability'] = raw_ability.lower().replace(' ', '-')
                    except Exception as e:
                        print(f"DEBUG: Could not fetch Mega Ability: {e}")
                
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
                    'turns': 3 if is_gmax else -1,
                    # Recorded BEFORE anything else reads it: the specimen's name and dex
                    # id have already been rewritten above, and instance_id is the one
                    # handle a Mega Evolution does not change.
                    'holder': battle_render.adaptation_holder(p_active),
                })
                
                transform_type = "Gigantamaxed" if is_gmax else "Mega Evolved"
                log_msg = f"✨ **{old_name.capitalize()}** achieved Hyper-Adaptation and {transform_type} into **{form_name.replace('-', ' ').title()}**!\n"
                
                # Trigger the biological entry hook so Snow Warning/Drought activates instantly!
                try:
                    log_msg = await trigger_single_entry_ability(p_active, n_active, "Your", state, log_msg)
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
                n_hazards=state.get('npc_hazards'),
                p_name=p_active.get('name'), p_level=p_active.get('level'),
                p_gender=p_active.get('gender'), n_gender=n_active.get('gender'),
                n_name=n_active.get('name'), n_level=n_active.get('level'),
                p_aura=battle_render.aura_for(state.get('adaptation'), p_active),
                biome=state.get('warden_biome')
            )
            
            # Dynamically grab the new randomized filename!
            if battle_file:
                embed.set_image(url=f"attachment://{battle_file.filename}")
            await self.refresh_buttons() 
            
            await interaction.edit_original_response(embed=embed, view=self, attachments=[battle_file])
            print("=== DEBUG: handle_transformation COMPLETE ===")

        except Exception as e:
            print("\n🚨 CRITICAL CRASH IN HANDLE_TRANSFORMATION 🚨")
            traceback.print_exc()
            await interaction.followup.send("A critical engine failure occurred during Hyper-Adaptation.", ephemeral=True)


    async def refresh_buttons(self):
        """Dynamically builds the UI buttons so they can be easily redrawn after a faint."""
        self.clear_items()
        state = self.cog.active_battles[self.user_id]
        p_active = state['player_team'][state['active_player_index']]

        n_active = state['npc_team'][state['active_npc_index']]

        # Check if the specimen has ANY energy left across all moves
        total_pp = sum(m['pp'] for m in p_active['moves'])

        # Properly format the string with hyphens!
        held_item = p_active.get('held_item', 'none').lower().replace(' ', '-')
        z_crystal_type = Z_CRYSTAL_TYPES.get(held_item)
        z_primed = state['adaptation'].get('z_toggled', False)

        # Set up the Choice Lock variables
        choice_lock_move = p_active.get('volatile_statuses', {}).get('choice_lock')
        has_choice_item = locks_into_one_move(held_item, p_active)

        # THE TEMPORAL LOCK FLAG
        is_charging = p_active.get('volatile_statuses', {}).get('charging')
        is_recharging = p_active.get('volatile_statuses', {}).get('recharging')

        # Encore borrows the same single-move lock
        _encore = p_active.get('volatile_statuses', {}).get('encore')
        if _encore and not is_charging:
            is_charging = _encore['move']

        
        # ==========================================
        # 1. Draw Combat Behaviors (Row 0)
        # ==========================================
        # Check if the specimen is currently expanded!
        is_maxed = state['adaptation'].get('active') and state['adaptation'].get('type') in ['dynamax', 'gmax']


        # 🚨 THE RECHARGE UI LOCK
        if is_recharging:
            recharge_btn = discord.ui.Button(
                label="⏳ Exhausted (Must Recharge)", 
                style=discord.ButtonStyle.danger, 
                custom_id="move_recharge_dummy" 
            )
            recharge_btn.callback = self.handle_move
            self.add_item(recharge_btn)
            
        elif total_pp <= 0 or not usable_moves(p_active, n_active):
            # Exhausted, or every move locked away by Disable / Taunt / Torment /
            # Imprison. Either way the only thing left is Struggle - without this second
            # case a fully restricted specimen would face a grid of dead buttons.
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

                # Disable / Taunt / Torment / Imprison
                restriction = move_is_restricted(p_active, move_dict, n_active)
                if restriction:
                    is_disabled = True

                # --- ASSAULT VEST FIREWALL ---
                if held_item == 'assault-vest' and move_class == 'status':
                    is_disabled = True

                
                # If EITHER the type or class is missing from an older save state, fetch them!
                if not move_element or not move_class:
                    async with aiosqlite.connect(DB_FILE) as db:
                        async with db.execute("SELECT type, damage_class FROM base_moves WHERE name = ?", (move_name,)) as cursor:
                            db_res = await cursor.fetchone()
                    
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
                    # Standard UI - HP-scaled moves append their live power (blank otherwise)
                    power_hint = format_power_hint(move_name, p_active, n_active)
                    btn_label = f"{move_name.replace('-', ' ').title()} ({curr_pp}/{max_pp}){power_hint}"
                    btn_style = discord.ButtonStyle.primary if curr_pp > 0 else discord.ButtonStyle.secondary
                    custom_id = f"move_{i}_{move_name}"
                    disabled_flag = is_disabled # 🚨 Mapped!

                # ==========================================
                # 🚨 THE TEMPORAL UI LOCK OVERRIDE
                # ==========================================
                if is_charging:
                    disabled_flag = (move_name != is_charging)
                    btn_style = discord.ButtonStyle.danger if not disabled_flag else discord.ButtonStyle.secondary
                    btn_label = f"⏳ Execute {move_name.replace('-', ' ').title()}" if not disabled_flag else move_name.capitalize()
                # ==========================================

                btn = discord.ui.Button(label=btn_label, style=btn_style, custom_id=custom_id, row=0, disabled=disabled_flag)
                
                # Only wire the callback if it's an actual, clickable attack
                if not disabled_flag and not custom_id.startswith('locked'):
                    btn.callback = self.handle_move
                    
                self.add_item(btn)

        if not is_charging and not is_recharging:

            # 2. Draw Medical Supplies (Row 1)
            bag_btn = discord.ui.Button(label="🎒 Open Bag", style=discord.ButtonStyle.success, custom_id="action_bag", row=1)
            bag_btn.callback = self.open_bag
            self.add_item(bag_btn)

            # --- The Swap Button ---
            # We disable it if there are no other healthy specimens on the team!
            healthy_bench = [p for i, p in enumerate(state['player_team']) if p['current_hp'] > 0 and i != state['active_player_index']]
            # 🚨 THE ULTIMATE SPATIAL LOCK (Player UI)
            opp_ability = get_active_ability(n_active)
            my_types = p_active.get('types', [])
            volatiles = p_active.get('volatile_statuses', {})

            is_trapped = specimen_is_trapped(p_active, n_active)
            swap_btn = discord.ui.Button(label="🔄 Swap Specimen", style=discord.ButtonStyle.secondary, custom_id="action_swap", row=1)
            swap_btn.disabled = len(healthy_bench) == 0 or is_trapped
            swap_btn.callback = self.handle_swap
            self.add_item(swap_btn)

            # --- The Forfeit Button ---
            # Wild and NPC expeditions can be walked away from; the confirmation step
            # lives in ForfeitConfirm so a stray click cannot end the battle.
            forfeit_btn = discord.ui.Button(label="🏳️ Forfeit",
                                            style=discord.ButtonStyle.danger,
                                            custom_id="action_forfeit", row=1)
            forfeit_btn.callback = self.handle_forfeit
            self.add_item(forfeit_btn)

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

                # A. Z-MOVE CHECK (Requires Z-Ring and Z-crystal)
                if held_item.endswith('-z') and z_crystal_type and key_items.get('z_ring'):
                    if state['adaptation'].get('z_toggled', False):
                        btn = discord.ui.Button(label="🔄 Cancel Z-Power", style=discord.ButtonStyle.secondary, custom_id="transform_0_zmove", row=2)
                    else:
                        btn = discord.ui.Button(label="🌟 Unleash Z-Move", style=discord.ButtonStyle.primary, custom_id="transform_0_zmove", row=2)
                    btn.callback = self.handle_transformation
                    self.add_item(btn)
                    gimmick_found = True

                # B. MEGA & G-MAX DATABASE CHECK
                async with aiosqlite.connect(DB_FILE) as db:
                    async with db.execute("SELECT pokedex_id, name FROM base_pokemon_species WHERE name LIKE ? OR name LIKE ?", 
                                (f"{base_name}-mega%", f"{base_name}-gmax%")) as cursor:
                        available_forms = await cursor.fetchall()
                
                mega_forms = [f for f in available_forms if '-mega' in f[1]]
                gmax_form = next((f for f in available_forms if '-gmax' in f[1]), None)

                # 1. MEGA EVOLUTION (Requires Mega Bracelet + Stone OR Rayquaza + Dragon Ascent)
                # The same shared ladder the PvE dashboard uses. The Floette, Raichu
                # and Ash-Greninja exceptions were written out twice, and adding a
                # fourth to both copies is how the two would have drifted.
                may_mega, has_mega_stone = may_mega_evolve(
                    p_active.get('name'), held_item, p_active.get('moves'))

                if mega_forms and may_mega and key_items.get('mega_bracelet'):
                    form_id, form_name = mega_forms[0]
                    
                    # 🚨 FIX 2: Added routing for the Z-Mega forms!
                    if held_item.endswith('-x'):
                        target = next((f for f in mega_forms if '-mega-x' in f[1]), mega_forms[0])
                        form_id, form_name = target
                    elif held_item.endswith('-y'):
                        target = next((f for f in mega_forms if '-mega-y' in f[1]), mega_forms[0])
                        form_id, form_name = target
                    elif held_item.endswith('-z'):
                        target = next((f for f in mega_forms if '-mega-z' in f[1]), mega_forms[0])
                        form_id, form_name = target
                        
                    # Dynamic button styling based on whether it's a Z-Mega or Standard Mega
                    btn_label = "⚡ Z-Mega Evolve" if held_item.endswith('-z') else "🧬 Mega Evolve"
                    
                    btn = discord.ui.Button(label=btn_label, style=discord.ButtonStyle.danger, custom_id=f"transform_{form_id}_{form_name}", row=2)
                    
                    btn.callback = self.handle_transformation
                    self.add_item(btn)
                    gimmick_found = True
                
                # 2. GIGANTAMAX (Requires Dynamax Band; Primal species are locked out)
                if gmax_form and gmax_factor and key_items.get('dynamax_band') and can_dynamax(p_active):
                    form_id, form_name = gmax_form
                    btn = discord.ui.Button(label=f"🌪️ Gigantamax", style=discord.ButtonStyle.danger, custom_id=f"transform_{form_id}_{form_name}", row=2)
                    btn.callback = self.handle_transformation
                    self.add_item(btn)
                    gimmick_found = True
                    
                # 3. GENERIC DYNAMAX (Requires Dynamax Band, only spawns if no other gimmick
                # is ready; Primal species are locked out)
                if not gimmick_found and key_items.get('dynamax_band') and can_dynamax(p_active):
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
                                    p_hazards=None, n_hazards=None,
                                    p_name=None, p_level=None, n_name=None, n_level=None,
                                    p_gender=None, n_gender=None,
                                    p_aura=None, n_aura=None, biome=None):
        """
        Maps battle state onto the scene renderer in cogs/battle_render.py and
        returns the result as a Discord attachment.

        Sprite loading and compositing cost ~200ms of pure CPU, which is long
        enough to stall the gateway heartbeat, so the whole job is handed to a
        worker thread. Returns None if rendering fails; every call site already
        guards for that.
        """

        def _render():
            player = battle_render.Combatant(
                name=p_name or f"#{player_id}",
                level=p_level,
                hp=p_hp, max_hp=p_max_hp,
                status=battle_render.normalize_status(p_status),
                gender=p_gender,
                # The gender reaches the sprite loader as well as the HP panel now, so
                # the hundred-odd species with a distinct female image show it.
                sprite=battle_render.load_sprite(player_id, player_shiny, p_gender),
                aura=p_aura,
                hazards=p_hazards or {},
            )
            opponent = battle_render.Combatant(
                name=n_name or f"#{npc_id}",
                level=n_level,
                hp=n_hp, max_hp=n_max_hp,
                status=battle_render.normalize_status(n_status),
                gender=n_gender,
                sprite=battle_render.load_sprite(npc_id, npc_shiny, n_gender),
                aura=n_aura,
                hazards=n_hazards or {},
            )
            return battle_render.render_png(
                player, opponent,
                biome=battle_render.normalize_biome(biome),
                weather=battle_render.normalize_weather(weather),
            )

        started = time.perf_counter()
        try:
            buffer = await asyncio.to_thread(_render)
        except Exception as e:
            print(f"⚠️ Battle scene render failed: {e}")
            traceback.print_exc()
            return None

        # Set KYU_TRACE_RENDER=1 to print what each frame actually cost. Off by default
        # so it costs a perf_counter call and nothing else.
        #
        # Read this alongside the wall-clock time of the send that follows: if a frame
        # renders in 130ms but the turn still takes two seconds, the time is going to the
        # upload rather than to us, and the next thing worth cutting is how MANY frames a
        # turn sends - not how fast each one is built.
        if os.getenv("KYU_TRACE_RENDER"):
            elapsed = (time.perf_counter() - started) * 1000
            size_kb = buffer.getbuffer().nbytes / 1024
            print(f"⏱️ frame: {elapsed:.0f}ms  {size_kb:.1f}KB")

        # Randomize the filename to bust Discord's aggressive image cache!
        # Extension follows the renderer, so switching format does not silently ship a
        # WebP wearing a .png name.
        new_filename = f"battle_{random.randint(10000, 99999)}.{battle_render.IMAGE_EXTENSION}"
        return discord.File(fp=buffer, filename=new_filename)

    async def handle_forfeit(self, interaction: discord.Interaction):
        """Offer to abandon the expedition. The teardown itself is behind a confirm."""
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message(
                "⚠️ This is not your field expedition!", ephemeral=True)

        await interaction.response.send_message(
            "🏳️ Abandon this expedition? You will not recover any research "
            "funding or experience from it.",
            view=ForfeitConfirm(self), ephemeral=True)

    async def open_bag(self, interaction: discord.Interaction):
        """Queries the user's inventory for medical supplies and opens the Dropdown UI."""
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("⚠️ This is not your field expedition!", ephemeral=True)
        
        # Fetch any items classified as medical supplies that the user actually owns
        medical_items = ('potion', 'super-potion', 'hyper-potion', 'max-potion', 'full-restore', 'revive', 'full-heal')
        placeholders = ','.join('?' * len(medical_items))
        
        query = f"SELECT item_name, quantity FROM user_inventory WHERE user_id = ? AND item_name IN ({placeholders}) AND quantity > 0"
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute(query, (self.user_id, *medical_items)) as cursor:
                inventory_data = await cursor.fetchall()
        
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
                async with aiosqlite.connect(DB_FILE) as db:
                    # ==========================================
                    # 1. REGISTER THE PLAYER'S PAYLOAD
                    # ==========================================
                    custom_id = interaction.data['custom_id']
                    is_z_move = custom_id.endswith('_z')
                    is_max_move = custom_id.endswith('_max')
                    
                    # --- FIREWALL: KEY ITEM AUTHORIZATION ---
                    if is_max_move and not state.get('key_items', {}).get('dynamax_band'):
                        return await interaction.response.send_message("❌ Authorization denied. You do not possess a Dynamax Band.", ephemeral=True)
                        
                    if is_z_move and not state.get('key_items', {}).get('z_ring'):
                        return await interaction.response.send_message("❌ Authorization denied. You do not possess a Z-Ring.", ephemeral=True)

                    raw_id_parts = custom_id.split('_')
                    move_name = raw_id_parts[2]

                    # ==========================================
                    # 🚨 TEMPORAL OVERRIDE: TWO-TURN MOVES 
                    # ==========================================
                    if 'volatile_statuses' not in p_active:
                        p_active['volatile_statuses'] = {}
                        
                    is_charging = p_active['volatile_statuses'].get('charging')
                    is_rampage = p_active['volatile_statuses'].get('rampage')
                    
                    is_encore = p_active['volatile_statuses'].get('encore')

                    if is_charging:
                        move_name = is_charging # Force the engine to use the charging move!
                    elif is_rampage:
                        move_name = is_rampage['move'] # Force the rampage move!
                    elif is_encore:
                        move_name = is_encore['move'] # Encore forces a repeat!

                    # APPLY THE PVE CHOICE LOCK 🚨
                    held_item = get_active_item(p_active, state.get('field', {}).get('magic_room', 0) > 0)
                    if locks_into_one_move(held_item, p_active):
                        if 'volatile_statuses' not in p_active:
                            p_active['volatile_statuses'] = {}
                        if not p_active['volatile_statuses'].get('choice_lock'):
                            p_active['volatile_statuses']['choice_lock'] = move_name
                    # ------------------------------------------

                    p_available_moves = usable_moves(p_active, n_active)
                    p_z_display = ""
                    
                    # --- STRUGGLE OVERRIDE (PLAYER) ---
                    if not p_available_moves:
                        move_name = 'struggle'
                        p_move_stats = struggle_move()
                        combat_log += f"⚠️ Your **{p_active['name'].capitalize()}** has no energy left!\n"
                    else:
                        for m in p_active['moves']:
                            if m['name'] == move_name:
                                m['pp'] -= 1
                                break
                                
                        
                        # Fetch Player Move Data
                    # Pull all 17 variables in the exact order of the DB Schema!
                        async with db.execute("""
                            SELECT name, type, power, accuracy, damage_class, pp, priority,
                                target, ailment, ailment_chance, stat_name, stat_change, stat_chance, 
                                status_type, status_chance, healing, drain
                            FROM base_moves WHERE name = ?
                        """, (move_name,)) as cursor:
                            p_row = await cursor.fetchone()
                        
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
                                elif p_z_display in ['G-Max Wildfire', 'G-Max Vine Lash', 'G-Max Cannonade', 'G-Max Volcalith']:
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
                    available_moves = usable_moves(n_active, p_active)
                    n_move_stats = None
                    npc_move_name = None
                    
                    # THE NPC TEMPORAL & SPATIAL LOCKS
                    npc_is_charging = n_active.get('volatile_statuses', {}).get('charging')
                    npc_is_rampage = n_active.get('volatile_statuses', {}).get('rampage') 


                    opp_ability = get_active_ability(p_active)
                    npc_types = n_active.get('types', [])
                    npc_volatiles = n_active.get('volatile_statuses', {})

                    npc_is_trapped = specimen_is_trapped(n_active, p_active)
                    # --- PHASE 2 - VOLUNTARY FLIGHT AI ---
                    # 1. Gather the benched team
                    alive_bench = [i for i, p in enumerate(state['npc_team']) if p['current_hp'] > 0 and i != state['active_npc_index']]
                    is_swapping = False
                    
                    print(f"DEBUG AI [FLIGHT]: Alive bench indices: {alive_bench}")
                    
                    # Only consider fleeing if we actually have backup AND they are not locked/trapped!
                    if alive_bench and not npc_is_charging and not npc_is_rampage and not npc_is_trapped and not n_active.get('volatile_statuses', {}).get('encore'):
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
                                if swap_target_idx is not None and best_score > 1.0:
                                    print(f"DEBUG AI [FLIGHT]: SUCCESS! Swapping to Index {swap_target_idx} (Score: {best_score}).")
                                    
                                    # ==========================================
                                    # 🚨 THE PVE PURSUIT INTERCEPTOR
                                    # ==========================================
                                    pursuit_faint = False # 🚨 NEW: Local tracking flag
                                    
                                    if move_name == 'pursuit':
                                        n_active['volatile_statuses']['is_switching'] = True
                                        combat_log += f"⚔️ {n_active['name'].capitalize()} is trying to retreat, but was Pursued by your {p_active['name'].capitalize()}!\n"
                                        
                                        # Force the physics engine to calculate the hit immediately!
                                        dmg, msg, inf_status, stat_chgs, heal_amt = calculate_damage(
                                            p_active, n_active, p_move_stats, 
                                            weather=state.get('weather', {'type': 'none'})['type'],
                                            target_hazards=state['npc_hazards'],
                                            user_hazards=state['player_hazards'],
                                            user_party=state['player_team'],
                                            wonder_room=state.get('field', {}).get('wonder_room', 0) > 0,
                                            gravity=state.get('field', {}).get('gravity', 0) > 0,
                                            magic_room=state.get('field', {}).get('magic_room', 0) > 0,
                                    field=field_of(state)
                                        )
                                        
                                        n_active['current_hp'] = max(0, n_active['current_hp'] - dmg)
                                        if msg: combat_log += f"*{msg}*\n"
                                        if dmg > 0: combat_log += f"Dealt **{dmg}** damage.\n"
                                        
                                        # We clear the player's move so it doesn't fire a second time in the main queue!
                                        p_move_stats = None 
                                        
                                        if n_active['current_hp'] <= 0:
                                            combat_log += f"💀 {n_active['name'].capitalize()} fainted before it could escape!\n"
                                            pursuit_faint = True # 🚨 Trigger the flag!
                                    # ==========================================
                                    
                                    # 🚨 NEW: Only mutate the state if they survived the Pursuit!
                                    if not pursuit_faint:
                                        combat_log += f"🔄 **Tactical Retreat!** The rival recalled **{n_active['name'].capitalize()}**!\n"
                                        
                                        # Update the state memory
                                        state['active_npc_index'] = swap_target_idx
                                        n_active = state['npc_team'][swap_target_idx]
                                        combat_log += f"The rival deployed **{n_active['name'].capitalize()}**!\n\n"
                                        
                                        # Trigger Entry Hazards / Abilities for the new arrival!
                                        combat_log = await trigger_single_entry_ability(n_active, p_active, "The rival's", state, combat_log)
                                        
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
                        
                        if npc_is_charging:
                            # Force the AI to finish its attack!
                            npc_move_name = npc_is_charging
                            print(f"DEBUG AI [ATTACK]: NPC is locked into charging move '{npc_move_name}'!")
                        elif n_active.get('volatile_statuses', {}).get('encore'):
                            npc_move_name = n_active['volatile_statuses']['encore']['move']
                            print(f"DEBUG AI [ATTACK]: NPC is locked into encored move '{npc_move_name}'!")
                        elif npc_is_rampage:
                            # 🚨 NEW: Force the AI to continue its rampage!
                            # Rampage is stored as a dict: {'move': 'outrage', 'turns': 2}
                            npc_move_name = npc_is_rampage['move'] 
                            print(f"DEBUG AI [ATTACK]: NPC is locked into rampage move '{npc_move_name}'!")
                        else:
                            print("DEBUG AI [ATTACK]: Engaging offensive move selection...")

                            # --- STRUGGLE OVERRIDE ---
                            if not available_moves:
                                npc_move_name = 'struggle'
                                n_move_stats = struggle_move()
                                combat_log += f"⚠️ The rival's **{n_active['name'].capitalize()}** has no energy left!\n"
                            else:
                                # --- TACTICAL PRIORITY FILTER (PHASE 3 UTILITY AI) ---
                                chosen_move, _score = await pick_npc_move(
                                    db, available_moves, n_active, p_active, state)

                                npc_move_name = chosen_move['name']
                                chosen_move['pp'] -= 1 
                                
                                async with db.execute("""
                                    SELECT type, power, accuracy, damage_class, target, ailment, ailment_chance,
                                        stat_name, stat_change, stat_chance, healing, drain, name, priority,
                                        status_type, status_chance
                                FROM base_moves WHERE name = ?
                                """, (npc_move_name,)) as cursor:
                                    n_row = await cursor.fetchone()

                                if n_row:
                                    n_move_stats = {
                                        'type': n_row[0], 'power': n_row[1] or 0, 'accuracy': n_row[2] or 100, 'class': n_row[3],
                                        'target': n_row[4], 'ailment': n_row[5], 'ailment_chance': n_row[6] or 0,
                                        'stat_name': n_row[7], 'stat_change': n_row[8] or 0, 'stat_chance': n_row[9] or 0,
                                        'healing': n_row[10] or 0, 'drain': n_row[11] or 0,
                                        'name': n_row[12],
                                        'priority': n_row[13] or 0,
                                        # Flinch lives here - without it NPC moves could never flinch
                                        'status_type': n_row[14] or 'none',
                                        'status_chance': n_row[15] or 0
                                    }
                                else:
                                    print(f"⚠️ WARNING: NPC move '{npc_move_name}' not found in DB! Using typeless fallback.")
                                    n_move_stats = {
                                        'type': 'typeless', 'power': 0, 'accuracy': 100, 'class': 'status',
                                        'target': 'defender', 'ailment': 'none', 'ailment_chance': 0,
                                        'stat_name': 'none', 'stat_change': 0, 'stat_chance': 0,
                                        'healing': 0, 'drain': 0, 'name': npc_move_name, 'priority': 0
                                    }

                # ==========================================
                # 🔒 HYDRATE A LOCKED-IN MOVE
                # ==========================================
                # The charge, Encore and rampage branches above only decide a NAME - the
                # payload is fetched inside the ordinary-selection branch they skip past.
                # Left unhydrated, n_move_stats stays None and the queue below drops the
                # NPC's action entirely: it silently forfeits the turn, and a charge it
                # was locked into is then broken by the end-of-turn sweep as though
                # something had stopped it.
                if npc_move_name and n_move_stats is None:
                    n_move_stats = await fetch_move_payload(npc_move_name)
                    if n_move_stats is None:
                        print(f"⚠️ WARNING: locked NPC move '{npc_move_name}' not found in DB!")

                # ==========================================
                # 3. KINETIC SPEED CHECK (PvE)
                # ==========================================
                def get_true_speed(specimen, has_tailwind=False):
                    """Thin wrapper so the two engines share one speed calculation."""
                    return battle_speed(
                        specimen, has_tailwind,
                        weather=state.get('weather', {'type': 'none'})['type'],
                        terrain=state.get('terrain', {'type': 'none'})['type'],
                        magic_room=state.get('field', {}).get('magic_room', 0) > 0)

                # Fetch Tailwind Statuses
                p_has_tailwind = state.get('player_hazards', {}).get('tailwind', 0) > 0
                n_has_tailwind = state.get('npc_hazards', {}).get('tailwind', 0) > 0

                p_speed = get_true_speed(p_active, p_has_tailwind)
                n_speed = get_true_speed(n_active, n_has_tailwind)

                
                # Sucker Punch reads these: the queue already knows both moves, so the
                # class of whatever each side locked in is available before either lands.
                p_active['_committed_move'] = (p_move_stats or {}).get('class')
                n_active['_committed_move'] = (n_move_stats or {}).get('class')
                # Me First needs the name too, not just the class
                p_active['_committed_move_name'] = move_name
                n_active['_committed_move_name'] = npc_move_name

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
                        # Terrain can shift a bracket (Grassy Glide on Grassy Terrain)
                        active_terrain = state.get('terrain', {'type': 'none'})['type']
                        p_prio = get_effective_priority(p_move_stats.get('name'), p_move_stats.get('priority'), p_active, active_terrain, p_move_stats)
                        n_prio = get_effective_priority(n_move_stats.get('name'), n_move_stats.get('priority'), n_active, active_terrain, n_move_stats)

                        # Bracket, then tier inside it (Quick Draw / Stall), then speed -
                        # with Trick Room inverting the speed component only. All three
                        # live in turn_order_key so both engines cannot disagree; PvE used
                        # to compute a trick_room flag here and then never consult it.
                        is_trick_room = state.get('field', {}).get('trick_room', 0) > 0
                        p_key = turn_order_key(p_prio, priority_tier(p_active, p_move_stats),
                                               p_speed, is_trick_room)
                        n_key = turn_order_key(n_prio, priority_tier(n_active, n_move_stats),
                                               n_speed, is_trick_room)

                        if p_key > n_key:
                            action_queue = [player_action, npc_action]
                        elif n_key > p_key:
                            action_queue = [npc_action, player_action]
                        else:
                            # Absolute tie! Coin flip.
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
                # 🚨 TURN-ORDER TRACKING (Bolt Beak / Fishious Rend)
                # Cleared for every specimen so a switch-in starts the turn "not yet acted".
                for _side in [state.get('player_team', []), state.get('npc_team', [])]:
                    for _mon in _side:
                        _mon['acted_this_turn'] = False

                for attacker, defender, move_stats, raw_move_name, is_player, z_disp, is_z_action, is_max_action in action_queue:
                    print(f"DEBUG 2: Now processing turn for: {attacker['name']} using {raw_move_name}")

                    # Mark BEFORE resolving: a target that is about to act has not acted yet,
                    # so the faster attacker still earns the ambush bonus.
                    attacker['acted_this_turn'] = True

                    if attacker['current_hp'] <= 0:
                        continue
                    if defender['current_hp'] <= 0:
                        combat_log += f"But there was no target for **{attacker['name'].capitalize()}** to attack!\n"
                        # ==========================================
                        # DESTINY BOND RESOLUTION
                        # ==========================================
                        if defender.get('volatile_statuses', {}).get('destiny-bond'):
                            attacker['current_hp'] = 0
                            combat_log += f"👻 **Your** {attacker['name'].capitalize()} took its attacker down with it!\n"

                        continue

                    status = attacker.get('status_condition', {})
                    owner_prefix = "Your " if is_player else "The rival's "
                    
                    # --- VOLATILE STATUS: CONFUSION CHECK ---
                    can_attack = True
                    volatiles = attacker.get('volatile_statuses', {})

                    if 'glaive_rush' in volatiles:
                        del volatiles['glaive_rush']

                    # ==========================================
                    # 🚨 REACTIVE STATUS ANOMALY: DESTINY BOND
                    # ==========================================
                    if raw_move_name == 'destiny-bond':
                        if 'volatile_statuses' not in attacker:
                            attacker['volatile_statuses'] = {}
                        attacker['volatile_statuses']['destiny-bond'] = True
                        combat_log += f"👻 {owner_prefix.strip()} **{attacker['name'].capitalize()}** is hoping to take its attacker down with it!\n"
                        continue

                    # ==========================================
                    # 🚨 THE RECHARGE ENFORCER
                    # ==========================================
                    if volatiles.get('recharging'):
                        combat_log += f"⏳ **{owner_prefix}** {attacker['name'].capitalize()} must recharge!\n"
                        
                        # Clear the tag so they can move normally on the NEXT turn
                        del attacker['volatile_statuses']['recharging']
                        continue # Abort the entire turn right here!

                    # 💘 Infatuation: half the time it cannot bring itself to attack.
                    if infatuation_holds_it_back(attacker):
                        combat_log += f"💘 **{attacker['name'].capitalize()}** is immobilised by love!\n"
                        can_attack = False
                    elif is_infatuated(attacker):
                        combat_log += f"💘 **{attacker['name'].capitalize()}** is in love with its opponent!\n"

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
                                user_hazards=state['player_hazards'] if is_player else state['npc_hazards'],
                            user_party=state['player_team'] if is_player else state['npc_team'],
                                terrain=state.get('terrain', {'type': 'none'})['type'],
                                wonder_room=state.get('field', {}).get('wonder_room', 0) > 0,
                                gravity=state.get('field', {}).get('gravity', 0) > 0,
                                magic_room=state.get('field', {}).get('magic_room', 0) > 0,
                                    field=field_of(state)
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
                            # Early Bird burns through sleep at twice the rate
                            status['duration'] -= (EARLY_BIRD_SLEEP_RATE
                                                   if get_active_ability(attacker) == 'early-bird'
                                                   else 1)
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

                    if volatiles.get('flinch'):
                        combat_log += f"🚫 **{attacker['name'].capitalize()}** flinched and couldn't move!\n"
                        volatiles.pop('flinch', None)
                        can_attack = False

                    # Block 18: Truant loafs on alternate turns. Asked LAST of the
                    # incapacity checks, and only if nothing else has already stopped the
                    # specimen - asking ADVANCES the rhythm, so a Slaking that spent this
                    # turn asleep must not also spend its loaf on it.
                    if can_attack and truancy_holds_it_back(attacker):
                        combat_log += (f"😴 **{attacker['name'].capitalize()}** "
                                       f"is loafing about!\n")
                        can_attack = False

                    # 🚨 STOMPING TANTRUM MEMORY
                    # Being unable to act at all - paralysis, sleep, freeze, flinch, or a
                    # confusion self-hit - counts as the move having failed.
                    if not can_attack:
                        attacker['last_move_failed'] = True

                    if can_attack:
                        # Prevent double-printing if Max Guard or Status Z-Moves already announced themselves in Phase 1
                        # ==========================================
                        # ⏱️ QUEENLY MAJESTY / DAZZLING / ARMOR TAIL
                        # ==========================================
                        # Refused outright rather than merely slowed: a raised bracket is
                        # what they answer, so the check reads the EFFECTIVE priority,
                        # which is what Gale Wings and Triage have already lifted.
                        _prio = get_effective_priority(
                            raw_move_name, move_stats.get('priority'), attacker,
                            state.get('terrain', {'type': 'none'})['type'], move_stats)
                        if _prio > 0 and blocks_priority_moves(defender):
                            combat_log += (f"🛡️ **{defender['name'].capitalize()}**'s "
                                           f"{get_active_ability(defender).replace('-', ' ').title()} "
                                           f"forbade the priority move!\n")
                            continue

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
                        
                        # ==========================================
                        # 🪞 REDIRECTION: Magic Coat and Snatch
                        # ==========================================
                        # Both were set up at +4 priority, so they are already standing.
                        # Swapping the pair here means everything downstream - accuracy,
                        # the damage formula, the log - sees the corrected owner.
                        if magic_coat_bounces(defender, move_stats):
                            defender['volatile_statuses'].pop('magic_coat', None)
                            combat_log += (f"\U0001fa9e **{defender['name'].capitalize()}** bounced "
                                           f"back the {raw_move_name.replace('-', ' ').title()}!\n")
                            attacker, defender = defender, attacker
                            is_player = not is_player
                            owner_prefix = "Your " if is_player else "The rival's "

                        elif snatch_steals(defender, move_stats):
                            defender['volatile_statuses'].pop('snatch', None)
                            combat_log += (f"\U0001f91a **{defender['name'].capitalize()}** snatched "
                                           f"the {raw_move_name.replace('-', ' ').title()}!\n")
                            attacker, defender = defender, attacker
                            is_player = not is_player
                            owner_prefix = "Your " if is_player else "The rival's "

                        # ==========================================
                        # 🎭 COPY MOVES: perform something else entirely
                        # ==========================================
                        if raw_move_name in COPY_MOVES:
                            own_party = state['player_team'] if is_player else state['npc_team']
                            chosen, why = resolve_copied_move(
                                raw_move_name, attacker, defender,
                                party=own_party,
                                last_move_overall=state.get('last_move_overall'),
                                pool=METRONOME_POOL,
                                terrain=state.get('terrain', {'type': 'none'})['type'])

                            if not chosen:
                                combat_log += f"⚠️ {why}\n"
                                continue

                            copied_stats = await fetch_move_payload(chosen)
                            if not copied_stats:
                                combat_log += "⚠️ But it failed! The copied move fizzled out!\n"
                                continue

                            if raw_move_name == 'me-first':
                                copied_stats['power'] = math.floor(copied_stats['power'] * ME_FIRST_MULTIPLIER)

                            combat_log += f"🎭 It became **{chosen.replace('-', ' ').title()}**!\n"
                            raw_move_name = chosen
                            move_stats = copied_stats

                        # ==========================================
                        # 🚨 TWO-TURN CHARGING & INVULNERABILITY LOGIC (PvE)
                        # ==========================================

                        is_currently_charging = attacker.get('volatile_statuses', {}).get('charging') == raw_move_name
                        held_item = get_active_item(attacker, state.get('field', {}).get('magic_room', 0) > 0)

                        # Only the player can Dynamax in PvE, so the NPC never qualifies
                        attacker_is_maxed = bool(is_max_action) or (is_player and is_dynamax_active(state.get('adaptation')))

                        if raw_move_name in TWO_TURN_MOVES and not is_currently_charging:
                            charge_data = TWO_TURN_MOVES[raw_move_name]
                            # Block 22: the sky the THROWER reads, so a Mega Sol's Solar
                            # Beam fires on the spot whatever is actually overhead.
                            current_weather = personal_weather(
                                attacker, state.get('weather', {'type': 'none'})['type'])

                            # 1. Biological Bypasses (Max Moves, Harsh Sunlight & Power Herbs)
                            if attacker_is_maxed:
                                # Dynamaxed specimens fire Max Moves, which never charge
                                combat_log += f"🌪️ {owner_prefix.strip()} **{attacker['name'].capitalize()}** unleashed the attack instantly through its Max form!\n"
                            elif current_weather in charge_data.get('skip_weather', []):
                                pass # Skip the charge turn and fire immediately!
                            elif held_item == 'power-herb':
                                combat_log += f"🌿 **{attacker['name'].capitalize()}** became fully charged due to its Power Herb!\n"
                                mark_item_consumed(attacker, held_item)
                                attacker['held_item'] = 'none' 
                            else:
                                # 2. Lock in the Charge state!
                                begin_charge(attacker, raw_move_name, charge_data.get('invuln'))
                                combat_log += f"⏳ {owner_prefix.strip()} **{attacker['name'].capitalize()}** {charge_data['msg']}\n"
                                
                                # 3. Apply Turn-1 Stat Boosts (Meteor Beam / Skull Bash)
                                if 'boost' in charge_data:
                                    stat_name, amt = charge_data['boost']
                                    if 'stat_stages' not in attacker: attacker['stat_stages'] = {'attack': 0, 'defense': 0, 'sp_atk': 0, 'sp_def': 0, 'speed': 0}
                                    attacker['stat_stages'][stat_name] = min(6, attacker['stat_stages'].get(stat_name, 0) + amt)
                                    combat_log += f"📈 **{attacker['name'].capitalize()}**'s {stat_name.replace('_', ' ')} rose!\n"
                                    
                                # (Semi-invulnerability for Dig / Fly is applied by begin_charge)

                                # 🚨 ABORT THE REST OF THE TURN!
                                continue 
                                
                        # ==========================================
                        # 🚨 DELAYED STRIKES (Future Sight / Doom Desire) - PvE
                        # ==========================================
                        if raw_move_name == 'encore':
                            victim_volatiles = defender.setdefault('volatile_statuses', {})
                            copied = defender.get('last_move_used')

                            if victim_volatiles.get('encore'):
                                combat_log += f"⚠️ But it failed! **{defender['name'].capitalize()}** is already encored!\n"
                            elif not copied or copied in ENCORE_IMMUNE_MOVES:
                                combat_log += "⚠️ But it failed! There was no performance to repeat!\n"
                            else:
                                victim_volatiles['encore'] = {'move': copied, 'turns': 3}
                                combat_log += f"👏 **{defender['name'].capitalize()}** received an encore and must repeat **{copied.replace('-', ' ').title()}**!\n"
                            continue

                        if raw_move_name == 'wish':
                            wish_slot = 'player_wish' if is_player else 'npc_wish'
                            if state.get(wish_slot):
                                combat_log += "⚠️ But it failed! A wish is already pending!\n"
                            else:
                                state[wish_slot] = snapshot_wish(attacker)
                                combat_log += f"⭐ {owner_prefix.strip()} **{attacker['name'].capitalize()}** made a wish!\n"
                            continue

                        if raw_move_name in DELAYED_ATTACK_MOVES:
                            target_slot = 'npc_future' if is_player else 'player_future'
                            launcher = owner_prefix.strip() or ("Your" if is_player else "The rival's")

                            if state.get(target_slot):
                                combat_log += "⚠️ But it failed! A strike is already converging on that side!\n"
                            else:
                                state[target_slot] = snapshot_delayed_attack(raw_move_name, attacker, move_stats, launcher)
                                combat_log += f"🔮 {launcher} **{attacker['name'].capitalize()}** foresaw an attack!\n"
                            continue

                        # If we reach this point and THEY WERE CHARGING, clear the tags so the attack can land!
                        if is_currently_charging:
                            end_charge(attacker)
                        # ==========================================
                        
                        # ==========================================
                        # 🚨 ACCURACY, EVASION, & OHKO BYPASS
                        # ==========================================
                        is_ohko = raw_move_name in OHKO_MOVES and not attacker_is_maxed

                        # Shared with the physics engine so the two copies cannot drift
                        # A standing Lock-On is spent here and guarantees this one attack
                        is_guaranteed = (raw_move_name in GUARANTEED_HIT_MOVES
                                         or consume_lock_on(attacker))

                        # Safely fetch abilities
                        atk_ability = get_active_ability(attacker)
                        def_ability = get_active_ability(defender)
                        has_no_guard = (atk_ability == 'no-guard' or def_ability == 'no-guard')
                        target_is_vulnerable = defender.get('volatile_statuses', {}).get('glaive_rush')
                        
                        move_acc = move_stats['accuracy']
                        if not isinstance(move_acc, int): move_acc = 100 

                        if not is_ohko and not has_no_guard and not target_is_vulnerable and not is_guaranteed:
                            
                            # Stages, the accuracy and evasion abilities, and Wonder Skin
                            # all live in one shared function so the two engines' copies
                            # of this cannot drift apart.
                            final_acc = hit_chance(
                                attacker, defender, move_stats,
                                weather=state.get('weather', {'type': 'none'})['type'])

                            # 3. Roll the dice!
                            if random.uniform(0, 100) > final_acc:
                                combat_log += "💨 The attack missed!\n"

                                # 🚨 STOMPING TANTRUM MEMORY: a whiff counts as a failure
                                attacker['last_move_failed'] = True

                                # Blunder Policy answers an ACCURACY miss, which is
                                # precisely what this branch is - a protect, an immunity
                                # or a failed status move is not a blunder.
                                combat_log += blunder_policy_on_miss(attacker)

                                # 🚨 CRASH DAMAGE (Miss)
                                if raw_move_name in ['jump-kick', 'high-jump-kick']:
                                    crash_dmg = max(1, math.floor(attacker.get('max_hp', 100) / 2))
                                    attacker['current_hp'] = max(0, attacker['current_hp'] - crash_dmg)
                                    combat_log += f"💥 {attacker['name'].capitalize()} kept going and crashed! (-{crash_dmg} HP)\n"

                                # If a Rampage move misses, the rampage is disrupted!
                                if 'rampage' in attacker.get('volatile_statuses', {}):
                                    del attacker['volatile_statuses']['rampage']
                                continue

                        # 🚨 LAST RESPECTS TALLY: refresh the attacker's casualty count so the
                        # physics engine can price the move without needing team access.
                        own_team = state['player_team'] if is_player else state['npc_team']
                        attacker['fainted_allies'] = sum(1 for p in own_team if p['current_hp'] <= 0)

                        print(f"DEBUG 3: {attacker['name']} passed status checks. Calling physics engine...")
                        dmg, msg, inf_status, stat_chgs, heal_amt = calculate_damage(
                            attacker, defender, move_stats, 
                            weather=state.get('weather', {'type': 'none'})['type'],
                            target_hazards=state['npc_hazards'] if is_player else state['player_hazards'],
                            user_hazards=state['player_hazards'] if is_player else state['npc_hazards'],
                            user_party=state['player_team'] if is_player else state['npc_team'],
                            terrain=state.get('terrain', {'type': 'none'})['type'],
                            wonder_room=state.get('field', {}).get('wonder_room', 0) > 0,
                            gravity=state.get('field', {}).get('gravity', 0) > 0,
                            magic_room=state.get('field', {}).get('magic_room', 0) > 0,
                                    field=field_of(state)
                        )
                        print(f"DEBUG 4: Physics engine success! Damage calculated: {dmg}")
                        
                        # Apply HP modifications

                        defender['current_hp'] = max(0, defender['current_hp'] - dmg)

                        # ==========================================
                        # 🚨 RAMPAGE MOVES (Outrage, Petal Dance, Thrash)
                        # ==========================================
                        # Outrage thrown as Max Wyrmwind does not lock the user in - the
                        # Max move keeps none of the base move's secondary effects.
                        if raw_move_name in RAMPAGE_MOVES and not attacker_is_maxed:
                            if dmg > 0: # The attack successfully landed!
                                if 'rampage' not in attacker['volatile_statuses']:
                                    # Start the rampage (Locks in for 2 to 3 turns)
                                    attacker['volatile_statuses']['rampage'] = {
                                        'move': raw_move_name,
                                        # Uproar is a fixed 3 attacks; the others roll 2-3
                                        'turns': 2 if raw_move_name in UPROAR_MOVES else random.randint(1, 2)
                                    }
                                else:
                                    # Decrement the rampage timer
                                    attacker['volatile_statuses']['rampage']['turns'] -= 1
                                    if attacker['volatile_statuses']['rampage']['turns'] <= 0:
                                        del attacker['volatile_statuses']['rampage']
                                        
                                        # Rampage ends, apply confusion! (Own Tempo grants immunity)
                                        atk_ability = get_active_ability(attacker)
                                        if atk_ability != 'own-tempo' and raw_move_name not in LOCK_IN_NO_FATIGUE:
                                            attacker['volatile_statuses']['confusion'] = random.randint(2, 5)
                                            combat_log += f"💫 {owner_prefix.strip()} **{attacker['name'].capitalize()}** became confused due to fatigue!\n"
                            else:
                                # If the rampage dealt 0 damage (Protect, Immunity, Faint), it is disrupted!
                                if 'rampage' in attacker.get('volatile_statuses', {}):
                                    del attacker['volatile_statuses']['rampage']

                        # ==========================================
                        # DAMAGE MEMORY (For Retaliation Moves)
                        # ==========================================
                        if dmg > 0:
                            defender['last_damage_taken'] = dmg
                            defender['last_damage_class'] = move_stats.get('class', 'physical')
                            # A biding target banks whatever it just absorbed
                            store_bide_damage(defender, dmg)

                            # 🚨 RAGE FIST TALLY: counts individual strikes (a 5-hit move advances
                            # it by 5) and rides on the specimen, so it survives switching.
                            defender['times_hit'] = defender.get('times_hit', 0) + defender.get('last_hit_count', 1)

                        # 🚨 STOMPING TANTRUM MEMORY
                        # A damaging move that connected for nothing (immunity, Protect, a
                        # failed condition) counts as a failure; anything else resets the flag.
                        if move_stats.get('class') != 'status' and dmg <= 0:
                            attacker['last_move_failed'] = True
                        else:
                            attacker['last_move_failed'] = False

                        # Encore copies whatever actually resolved here; Conversion 2
                        # reads the element off it.
                        attacker['last_move_used'] = raw_move_name
                        attacker['last_move_type'] = move_stats.get('type')
                        # A sacrifice move banks its wish against the SIDE, so whoever
                        # fills the vacated slot collects it - see trigger_single_entry_ability.
                        if '_sacrifice_wish' in attacker:
                            _side = side_of(state, attacker)
                            if _side is not None:
                                state[f"{_side}_sacrifice"] = attacker.pop('_sacrifice_wish')

                        state['last_move_overall'] = raw_move_name   # Copycat reads this

                        # Grudge: if that blow was the one that finished the target, the
                        # move that did it loses every last PP.
                        if defender['current_hp'] <= 0:
                            grudge_log = apply_grudge(defender, attacker)
                            combat_log += apply_faint_recoil(defender, attacker)
                            # Block 17: the killer collects, and anything still standing
                            # answers the fall.
                            combat_log += apply_knockout_reactions(defender, attacker,
                                                                  attacker)
                            if grudge_log:
                                combat_log += grudge_log.strip() + "\n"

                        if msg: combat_log += f"*{msg}*\n"
                        if dmg > 0: combat_log += f"Dealt **{dmg}** damage.\n"
                        
                        #Check if the damage pushed them below the berry threshold!
                        berry_log = check_consumables(defender, owner_prefix, state.get('field', {}).get('magic_room', 0) > 0, attacker)
                        if berry_log: combat_log += berry_log

                        if heal_amt > 0:
                            attacker['current_hp'] = min(attacker.get('max_hp', 100), attacker['current_hp'] + heal_amt)
                            combat_log += f"💚 **{attacker['name'].capitalize()}** recovered health!\n"
                            
                        # --- STRUGGLE RECOIL INTERCEPTOR ---
                        if raw_move_name == 'struggle':
                            recoil_dmg = apply_struggle_recoil(attacker)
                            combat_log += f"💥 **{attacker['name'].capitalize()}** took recoil damage from thrashing about! (-{recoil_dmg} HP)\n"
                        
                        # ==========================================
                        # PHASE 1 & 2: THE FLINCH INTERCEPTOR
                        # ==========================================
                        # Flinch interception + standard pathogens (Burn, Poison, etc.)
                        combat_log += apply_status_outcome(defender, inf_status, move_stats, attacker)

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
                        combat_log += apply_stat_changes(attacker, defender, stat_chgs, state=state)
                        # ...and cash in any form change the move provoked.
                        combat_log += await resolve_form_flips(attacker, defender)

                        # ==========================================
                        # 💃 DANCER
                        # ==========================================
                        # The onlooker copies the dance the moment it finishes. Unlike the
                        # copy family this is not a re-dispatch of the attacker's action -
                        # it is a whole extra move by the DEFENDER, so it resolves here
                        # rather than by swapping the queue entry.
                        if (is_dance_move(raw_move_name)
                                and get_active_ability(defender) == 'dancer'
                                and defender['current_hp'] > 0
                                and not attacker.get('_dancer_echo')):
                            echo = await fetch_move_payload(raw_move_name)
                            if echo:
                                # Marked so a Dancer copying another Dancer cannot loop
                                defender['_dancer_echo'] = True
                                d_dmg, d_msg, d_status, d_stats, d_heal = calculate_damage(
                                    defender, attacker, echo,
                                    weather=state.get('weather', {'type': 'none'})['type'],
                                    terrain=state.get('terrain', {'type': 'none'})['type'],
                                    target_hazards=state['player_hazards'] if is_player else state['npc_hazards'],
                                    user_hazards=state['npc_hazards'] if is_player else state['player_hazards'],
                                    user_party=state['npc_team'] if is_player else state['player_team'],
                                    wonder_room=state.get('field', {}).get('wonder_room', 0) > 0,
                                    gravity=state.get('field', {}).get('gravity', 0) > 0,
                                    magic_room=state.get('field', {}).get('magic_room', 0) > 0,
                                    field=field_of(state))
                                defender.pop('_dancer_echo', None)

                                combat_log += (f"💃 **{defender['name'].capitalize()}** "
                                               f"joined in with `{raw_move_name.replace('-', ' ').title()}`!\n")
                                if d_dmg > 0:
                                    attacker['current_hp'] = max(0, attacker['current_hp'] - d_dmg)
                                    combat_log += f"↳ Dealt **{d_dmg}** damage.\n"
                                if d_heal > 0:
                                    defender['current_hp'] = min(defender.get('max_hp', 100),
                                                                 defender['current_hp'] + d_heal)
                                combat_log += apply_stat_changes(defender, attacker, d_stats, state=state)
                                combat_log += apply_status_outcome(attacker, d_status, echo, defender)

                        # Only apply the exhaustion tag if the attack actually dealt damage,
                        # and never while Dynamaxed - Max Moves leave no recharge window.
                        if raw_move_name in RECHARGE_MOVES and dmg > 0 and not attacker_is_maxed:
                            if 'volatile_statuses' not in attacker:
                                attacker['volatile_statuses'] = {}
                            attacker['volatile_statuses']['recharging'] = True

                        # ==========================================
                        # SYNCHRONOUS PIVOT OVERRIDE (PvE)
                        # ==========================================
                        # A Max move carries none of the base move's secondary effects, so
                        # U-turn thrown as Max Strike hits and stays put. Stated explicitly
                        # rather than relying on effective_move_name being a display string
                        # that happens not to match the list.
                        if effective_move_name in pivot_moves and not attacker_is_maxed and attacker['current_hp'] > 0 and (dmg > 0 or move_stats['class'] == 'status'):
                            
                            # Verify they actually have a living bench specimen to swap into!
                            if is_player:
                                active_idx = state['active_player_index']
                                has_bench = any(i != active_idx and p['current_hp'] > 0 for i, p in enumerate(state['player_team']))
                            else:
                                active_idx = state['active_npc_index']
                                has_bench = any(i != active_idx and p['current_hp'] > 0 for i, p in enumerate(state['npc_team']))
                            
                            if has_bench:
                                # Biologically flush the outgoing specimen's stat mutations.
                                # Baton Pass is exempt because it hands them to the
                                # replacement instead - see baton_pass_state below.
                                if effective_move_name != 'baton-pass':
                                    leave_field(attacker)
                                    attacker['volatile_statuses'] = {}
                                    
                                combat_log += f"💨 {owner_prefix.strip()} **{attacker['name'].capitalize()}** retreated to the bench!\n"
                                
                                # ==========================================
                                # 🚨 PAUSE THE ENGINE: WAIT FOR USER INPUT
                                # ==========================================
                                if is_player:
                                    # Send the special menu to the user using the existing interaction!
                                    embed = discord.Embed(title="⚠️ Mid-Turn Substitution!", description=f"{combat_log}\nChoose your replacement quickly!", color=discord.Color.orange())
                                    swap_view = MidTurnSwapMenu(self.cog, state, self.user_id)
                                    
                                    # Use edit_original_response instead of searching the state dict!
                                    await interaction.edit_original_response(embed=embed, attachments=[], view=swap_view)
                                    
                                    # 🛑 FREEZE THE THREAD UNTIL THEY CLICK A BUTTON
                                    await swap_view.swap_event.wait()
                                    
                                    # 🟢 RESUME! Grab the index they selected
                                    new_idx = swap_view.selected_index
                                    state['active_player_index'] = new_idx
                                    new_active = state['player_team'][new_idx]
                                    
                                else:
                                    npc_bench = [i for i, p in enumerate(state['npc_team']) if p['current_hp'] > 0 and i != state['active_npc_index']]
                                    new_idx = random.choice(npc_bench)
                                    state['active_npc_index'] = new_idx
                                    new_active = state['npc_team'][new_idx]
                                    
                                # 🚨 BATON PASS: hand the built-up state to the replacement
                                if effective_move_name == 'baton-pass':
                                    baton_pass_state(attacker, new_active)
                                    combat_log += f"🎽 {owner_prefix.strip()} **{attacker['name'].capitalize()}** passed the baton!\n"

                                # ==========================================
                                # RESUME COMBAT: INJECT THE NEW POKEMON INTO THE TIMELINE
                                # ==========================================
                                combat_log += f"\n{owner_prefix.strip()} sent out **{new_active['name'].capitalize()}**!\n"
                                
                                # Trigger Entry Hazards / Abilities for the new arrival!
                                combat_log = await trigger_single_entry_ability(new_active, defender, owner_prefix, state, combat_log)
                                hazard_log = apply_entry_hazards(new_active, state['player_hazards'] if is_player else state['npc_hazards'], TYPE_CHART, owner_prefix)
                                if hazard_log: combat_log += hazard_log
                                
                                # UPDATE THE POINTERS SO THE OPPONENT HITS THE NEW POKEMON!
                                if is_player:
                                    p_active = new_active # Update the global pointer
                                    attacker = new_active # Update the local loop pointer
                                else:
                                    n_active = new_active
                                    attacker = new_active
                                    
                                # Rebuild the opponent's action tuple because Python tuples are immutable!
                                for idx in range(len(action_queue)):
                                    other_act = action_queue[idx]
                                    
                                    # Index 4 holds the 'is_player' boolean. If it's different, it's the opponent!
                                    if other_act[4] != is_player:
                                        # Construct a new tuple, seamlessly injecting the new_active specimen into Index 1 (the defender slot)
                                        action_queue[idx] = (
                                            other_act[0],  # attacker
                                            new_active,    # 🚨 NEW DEFENDER
                                            other_act[2],  # move_stats
                                            other_act[3],  # raw_move_name
                                            other_act[4],  # is_player
                                            other_act[5],  # z_disp
                                            other_act[6],  # is_z_action
                                            other_act[7]   # is_max_action
                                        )
                        # ==========================================

                        # CLIMATOLOGICAL OVERRIDES / TERRAIN / FIELD DEPLOYMENT (PvE)
                        magic_room_on = state.get('field', {}).get('magic_room', 0) > 0
                        combat_log += deploy_weather(state, effective_move_name, attacker, magic_room_on)
                        combat_log += deploy_terrain(
                            state, effective_move_name, attacker, magic_room_on,
                            max_move_type=move_stats['type'] if (is_player and is_max_action) else None,
                            standing=(attacker, defender))
                        combat_log += deploy_field_toggle(
                            state, raw_move_name, attacker, defender,
                            state['player_hazards'] if is_player else state['npc_hazards'])

                        # ==========================================
                        # PHAZING ANOMALIES (PvE Forced Swaps)
                        # ==========================================
                        # Dragon Tail thrown as Max Wyrmwind deals its damage and nothing
                        # else: a Max move keeps none of the base move's secondary effects,
                        # so nobody is dragged out.
                        _is_phazing = (raw_move_name in phaze_moves and not attacker_is_maxed
                              and defender['current_hp'] > 0
                              and (dmg > 0 or move_stats['class'] == 'status'))
                        # Suction Cups and Guard Dog plant themselves. Answered before the bench
                        # search so the refusal is reported for the right reason - "it failed,
                        # no bench" would be a different and wrong explanation.
                        if _is_phazing and resists_forced_switch(defender):
                            combat_log += (f"🦶 **{defender['name'].capitalize()}**'s "
                                           f"{pretty_ability(get_active_ability(defender))} "
                                           f"kept it rooted to the spot!\n")
                        elif _is_phazing:
                            
                            # 1. Find valid benched targets for the DEFENDER
                            if is_player: # The Player is attacking the NPC
                                opp_bench = [i for i, p in enumerate(state['npc_team']) if p['current_hp'] > 0 and i != state['active_npc_index']]
                            else:         # The NPC is attacking the Player
                                opp_bench = [i for i, p in enumerate(state['player_team']) if p['current_hp'] > 0 and i != state['active_player_index']]
                            
                            if opp_bench:
                                forced_idx = random.choice(opp_bench)
                                
                                # 2. Mutate the state and grab the new victim
                                if is_player:
                                    state['active_npc_index'] = forced_idx
                                    forced_in_poke = state['npc_team'][forced_idx]
                                else:
                                    state['active_player_index'] = forced_idx
                                    forced_in_poke = state['player_team'][forced_idx]
                                    
                                # Biologically flush the outgoing specimen's stat mutations
                                leave_field(defender)
                                defender['volatile_statuses'] = {}
                                
                                target_prefix = "The rival's" if is_player else "Your"
                                combat_log += f"🌪️ {target_prefix} **{defender['name'].capitalize()}** was forced out of the battlefield!\n"
                                combat_log += f"↳ **{forced_in_poke['name'].capitalize()}** was dragged into the fight!\n"
                                
                                # 3. Trigger Entry Hazards / Abilities for the dragged-in Pokémon!
                                try:
                                    combat_log = await trigger_single_entry_ability(forced_in_poke, attacker, f"{target_prefix} ", state, combat_log)
                                    hazard_log = apply_entry_hazards(forced_in_poke, state['npc_hazards'] if is_player else state['player_hazards'], TYPE_CHART, f"{target_prefix} ")
                                    if hazard_log: combat_log += hazard_log
                                except Exception as e:
                                    print(f"DEBUG: PvE Phaze Entry Hook Failed: {e}")
                                    
                                # 4. 🚨 CRITICAL: UPDATE THE POINTERS
                                if is_player:
                                    n_active = forced_in_poke
                                    defender = forced_in_poke
                                else:
                                    p_active = forced_in_poke
                                    defender = forced_in_poke
                                    
                                # 5. Cancel any pending actions for the dragged-in Pokémon!
                                for idx in range(len(action_queue)):
                                    if action_queue[idx][4] != is_player: 
                                        # We replace their action with a dummy 'pass' so they don't attack this turn
                                        action_queue[idx] = (forced_in_poke, attacker, {'class': 'status', 'power': 0}, 'pass', not is_player, "", False, False)
                            else:
                                combat_log += "↳ But it failed! The target has no benched Pokémon to drag out!\n"

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

        try:
            # --- 1. NPC THREAT ASSESSMENT ---
            available_moves = usable_moves(n_active, p_active)
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
                            
                            combat_log = await trigger_single_entry_ability(n_active, p_active, "The rival's", state, combat_log)
                            
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
                # ==========================================
                # 🚨 LOCK HANDLING (free actions honour the same locks as a real turn)
                # ==========================================
                # This is the NPC's free swing when the player uses an item or swaps out,
                # and it used to pick a move from scratch. Mid-Fly that meant wandering off
                # to something else and never clearing 'charging' - which in turn strands
                # 'semi_invulnerable', because the end-of-turn sweep only drops that flag
                # when nothing is charging. The NPC then sat underground/airborne for the
                # rest of the battle, untouchable by anything but a Max move.
                retaliation_volatiles = n_active.setdefault('volatile_statuses', {})
                npc_is_charging = retaliation_volatiles.get('charging')
                npc_encore = retaliation_volatiles.get('encore') or {}
                npc_rampage = retaliation_volatiles.get('rampage') or {}

                forced_move = npc_is_charging or npc_encore.get('move') or npc_rampage.get('move')
                if forced_move:
                    locked_in = [m for m in available_moves if m['name'] == forced_move]
                    if locked_in:
                        available_moves = locked_in

                # The charge is spent either way. Even if the locked move has no PP left and
                # the NPC falls back to something else, the flags must not survive the swing.
                if npc_is_charging:
                    end_charge(n_active)

                if not available_moves:
                    npc_move_name = 'struggle'
                    n_move_stats = struggle_move()
                else:
                    async with aiosqlite.connect(DB_FILE) as db:
                        chosen_move, _score = await pick_npc_move(
                            db, available_moves, n_active, p_active, state,
                            context='FREE SWING')
                        npc_move_name = chosen_move['name']
                        chosen_move['pp'] -= 1
                        
                        # Fetch the complete 17-variable payload
                        async with db.execute("""
                            SELECT name, type, power, accuracy, damage_class, pp, priority,
                                target, ailment, ailment_chance, stat_name, stat_change, stat_chance, 
                                status_type, status_chance, healing, drain
                            FROM base_moves WHERE name = ?
                        """, (npc_move_name,)) as cursor:
                            n_row = await cursor.fetchone()
                        
                        if n_row:
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
                                    user_hazards=state['npc_hazards'],
                                    user_party=state['npc_team'],
                                    terrain=state.get('terrain', {'type': 'none'})['type'],
                                    wonder_room=state.get('field', {}).get('wonder_room', 0) > 0,
                                    gravity=state.get('field', {}).get('gravity', 0) > 0,
                                    magic_room=state.get('field', {}).get('magic_room', 0) > 0,
                                    field=field_of(state)
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

            # Block 18: Truant, on the third of the three paths a specimen can try to move
            # down. Left off here and a Slaking would never loaf on the turn it swings at a
            # replacement - which is exactly the shape of gap this project keeps finding, so
            # all three are filled at once.
            if can_attack and truancy_holds_it_back(n_active):
                combat_log += (f"😴 The rival's "
                               f"**{n_active['name'].capitalize()}** is loafing about!\n")
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
                            user_hazards=state['npc_hazards'],       # NPC's own side
                            user_party=state['npc_team'],
                            terrain=state.get('terrain', {'type': 'none'})['type'],
                            wonder_room=state.get('field', {}).get('wonder_room', 0) > 0,
                            gravity=state.get('field', {}).get('gravity', 0) > 0,
                            magic_room=state.get('field', {}).get('magic_room', 0) > 0,
                                    field=field_of(state)
                        )
                        
                        p_active['current_hp'] = max(0, p_active['current_hp'] - dmg)
                        if msg: combat_log += f"*{msg}*\n"
                        if dmg > 0: combat_log += f"You took **{dmg}** damage.\n"

                        # Did the attack trigger the player's Sitrus Berry?
                        berry_log = check_consumables(p_active, "Your", state.get('field', {}).get('magic_room', 0) > 0, n_active)
                        if berry_log: combat_log += berry_log


                        if heal_amt > 0:
                            n_active['current_hp'] = min(n_active.get('max_hp', 100), n_active['current_hp'] + heal_amt)
                            combat_log += f"💚 **{n_active['name'].capitalize()}** recovered health!\n"

                        # ==========================================
                        # 🌦️ THE REST OF THE MOVE
                        # ==========================================
                        # A free swing is still a real move: it sets weather, lays terrain,
                        # shifts stat stages and inflicts status exactly as it would on the
                        # NPC's ordinary turn. Without this the rival's Rain Dance announced
                        # itself here and changed nothing at all.
                        combat_log += apply_stat_changes(n_active, p_active, stat_chgs, state=state)
                        combat_log += apply_status_outcome(p_active, inf_status, n_move_stats, n_active)

                        magic_room_on = state.get('field', {}).get('magic_room', 0) > 0
                        combat_log += deploy_weather(state, npc_move_name, n_active, magic_room_on)
                        combat_log += deploy_terrain(state, npc_move_name, n_active, magic_room_on,
                                                     standing=(n_active, p_active))
                        combat_log += deploy_field_toggle(state, npc_move_name, n_active,
                                                          p_active, state['npc_hazards'])

            await self.process_turn_end(interaction, combat_log)

        except Exception as e:
            import traceback
            print(f"Retaliation Engine Error:")
            traceback.print_exc()
            await self.process_turn_end(interaction, combat_log)

    async def process_turn_end(self, interaction, combat_log):
        """The Central Engine: Handles NPC retaliation, hazards, faints, and UI rendering."""
        print("\n=== DEBUG: process_turn_end triggered ===")

        try:
            state = self.cog.active_battles[self.user_id]
            p_active = state['player_team'][state['active_player_index']]
            n_active = state['npc_team'][state['active_npc_index']]
            
            print("DEBUG 6: Entering Phase 3 (Weather & Pathogens)")

            # --- PHASE 3: POST-TURN ENVIRONMENTAL DAMAGE (PvE) ---
            combat_log += "\n"

            # ==========================================
            # 🚨 LOCK-IN UPKEEP (Encore decay / Uproar insomnia) - PvE
            # ==========================================
            for mon, owner_str in [(p_active, "Your"), (n_active, "The rival's")]:
                enc = (mon.get('volatile_statuses') or {}).get('encore')
                if enc:
                    enc['turns'] -= 1
                    if enc['turns'] <= 0:
                        del mon['volatile_statuses']['encore']
                        combat_log += f"👏 {owner_str} **{mon['name'].capitalize()}**'s encore ended!\n"

                dis = (mon.get('volatile_statuses') or {}).get('disable')
                if dis:
                    dis['turns'] -= 1
                    if dis['turns'] <= 0:
                        del mon['volatile_statuses']['disable']
                        combat_log += f"🔓 {owner_str} **{mon['name'].capitalize()}** is no longer disabled!\n"

                if (mon.get('volatile_statuses') or {}).get('taunt'):
                    mon['volatile_statuses']['taunt'] -= 1
                    if mon['volatile_statuses']['taunt'] <= 0:
                        del mon['volatile_statuses']['taunt']
                        combat_log += f"😌 {owner_str} **{mon['name'].capitalize()}**'s taunt wore off!\n"

            # An active Uproar jolts anything already asleep back awake
            if is_uproar_active(p_active, n_active):
                for mon, owner_str in [(p_active, "Your"), (n_active, "The rival's")]:
                    status = mon.get('status_condition') or {}
                    if status.get('name') == 'sleep':
                        mon['status_condition'] = None
                        combat_log += f"📢 {owner_str} **{mon['name'].capitalize()}** was jolted awake by the uproar!\n"

            # ==========================================
            # 🚨 DELAYED STRIKES LANDING (Future Sight / Doom Desire) - PvE
            # ==========================================
            for slot_key, victim, victim_label in [('player_future', p_active, "Your"),
                                                   ('npc_future', n_active, "The rival's")]:
                pending = state.get(slot_key)
                if not pending:
                    continue

                # Skip the tick on the turn it was queued so two full turns elapse
                if pending.get('just_queued'):
                    pending['just_queued'] = False
                    continue

                pending['turns'] -= 1
                if pending['turns'] > 0:
                    continue

                state[slot_key] = None
                if victim['current_hp'] <= 0:
                    continue

                strike_dmg, strike_msg = resolve_delayed_strike(
                    pending, victim,
                    weather=state.get('weather', {'type': 'none'})['type'],
                    terrain=state.get('terrain', {'type': 'none'})['type']
                )
                victim['current_hp'] = max(0, victim['current_hp'] - strike_dmg)

                combat_log += f"🔮 {victim_label} **{victim['name'].capitalize()}** took the {pending['move'].replace('-', ' ').title()} attack! (-{strike_dmg} HP)\n"
                if strike_msg:
                    combat_log += f"*{strike_msg}*\n"

            # ==========================================
            # 🚨 WISHES COMING TRUE - PvE
            # ==========================================
            # Banked on the wisher, paid out to whoever holds the slot a turn later, so a
            # Wish passed to a switch-in heals the replacement rather than the wisher.
            for wish_key, patient in [('player_wish', p_active), ('npc_wish', n_active)]:
                pending_wish = state.get(wish_key)
                if not pending_wish:
                    continue

                # Skip the tick on the turn it was made so a full turn elapses
                if pending_wish.get('just_queued'):
                    pending_wish['just_queued'] = False
                    continue

                pending_wish['turns'] -= 1
                if pending_wish['turns'] > 0:
                    continue

                state[wish_key] = None
                _, wish_msg = resolve_wish(pending_wish, patient)
                if wish_msg:
                    combat_log += wish_msg + "\n"

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
                                chip_weather = weather['type']
                                if weather['type'] == 'sand' and any(t in ['rock', 'ground', 'steel'] for t in c_types):
                                    is_immune = True
                                if weather['type'] == 'hail' and 'ice' in c_types:
                                    is_immune = True
                                # Sand Force, Sand Veil and Snow Cloak each weather their
                                # OWN storm - a Sand Veil is no help in hail.
                                if shrugs_off_weather(get_active_ability(combatant), chip_weather):
                                    is_immune = True


                                if not is_immune:
                                    chip_dmg = max(1, math.floor(combatant['max_hp'] / 16))
                                    combatant['current_hp'] = max(0, combatant['current_hp'] - chip_dmg)
                                    icon = "🌪️" if weather['type'] == 'sand' else "❄️"
                                    combat_log += f"{icon} {owner_str} **{combatant['name'].capitalize()}** is buffeted by the {weather['type']}! (-{chip_dmg} HP)\n"

                    # Dry Skin Atmospheric Reactions
                    for combatant, owner_str in [(p_active, "Your"), (n_active, "The rival's")]: # Remove the '_' in PvE!
                        if combatant['current_hp'] > 0 and get_active_ability(combatant) == 'dry-skin':
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

            # 1.5 Global Biome Effects (Terrains)
            if 'terrain' not in state: state['terrain'] = {'type': 'none', 'duration': 0}
            
            if state['terrain']['type'] != 'none':
                state['terrain']['duration'] -= 1
                if state['terrain']['duration'] <= 0:
                    terrain_clear_msgs = {
                        'electric': "The electricity disappeared from the battlefield.",
                        'grassy': "The grass disappeared from the battlefield.",
                        'misty': "The mist disappeared from the battlefield.",
                        'psychic': "The weirdness disappeared from the battlefield."
                    }
                    combat_log += f"✨ {terrain_clear_msgs.get(state['terrain']['type'])}\n"
                    state['terrain']['type'] = 'none'
                else:
                    # Grassy Terrain Healing!
                    if state['terrain']['type'] == 'grassy':
                        # (Note: Use `for combatant, _, owner_str in combatants:` in PvP)
                        for combatant, owner_str in [(p_active, "Your"), (n_active, "The rival's")]: 
                            if combatant['current_hp'] > 0 and combatant['current_hp'] < combatant.get('max_hp', 100) and is_grounded(combatant):
                                heal = max(1, math.floor(combatant.get('max_hp', 100) / 16))
                                combatant['current_hp'] = min(combatant.get('max_hp', 100), combatant['current_hp'] + heal)
                                combat_log += f"🌿 {owner_str.strip()} **{combatant['name'].capitalize()}** had its HP restored by the Grassy Terrain! (+{heal} HP)\n"

            # ==========================================
            # 1.5 PERSISTENT HELD ITEMS (Status Orbs)
            # ==========================================
            for combatant, owner_str in [(p_active, "Your"), (n_active, "The rival's")]:
                if combatant['current_hp'] > 0 and not combatant.get('status_condition'):
                    orb_item = get_active_item(combatant, state.get('field', {}).get('magic_room', 0) > 0)
                    
                    if orb_item == 'flame-orb' and 'fire' not in combatant.get('types', []):
                        combatant['status_condition'] = {'name': 'burn', 'duration': -1}
                        combat_log += f"🔥 {owner_str} **{combatant['name'].capitalize()}** was burned by its Flame Orb!\n"
                        
                    elif orb_item == 'toxic-orb' and 'poison' not in combatant.get('types', []) and 'steel' not in combatant.get('types', []):
                        combatant['status_condition'] = {'name': 'poison', 'duration': -1}
                        combat_log += f"☣️ {owner_str} **{combatant['name'].capitalize()}** was badly poisoned by its Toxic Orb!\n"

            # 2. Pathogen Damage (Burn/Poison)
            for combatant, owner_str in [(p_active, "Your"), (n_active, "The rival's")]:
                ability = get_active_ability(combatant)
                if combatant['current_hp'] > 0 and combatant.get('status_condition'):
                    status = combatant['status_condition']['name']
                    if status == 'burn':
                        burn_divisor = 32 if ability in BURN_TOLL_HALVED_BY else 16
                        burn_dmg = max(1, math.floor(combatant['max_hp'] / burn_divisor))
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
                    item = get_active_item(combatant, state.get('field', {}).get('magic_room', 0) > 0)
                    max_hp = combatant.get('max_hp', 100)
                    
                    if item == 'leftovers':
                        # 🚨 FIX: Only trigger if they are missing HP!
                        if combatant['current_hp'] < max_hp:
                            heal_qty = max(1, math.floor(max_hp / 16))
                            combatant['current_hp'] = min(max_hp, combatant['current_hp'] + heal_qty)
                            combat_log += f"🍎 **{owner_str} {combatant['name'].capitalize()}** restored a little HP using its Leftovers! (+{heal_qty})\n"

                    elif item == 'black-sludge':
                        if 'poison' in combatant.get('types', []):
                            # 🚨 FIX: Only heal Poison types if they are missing HP!
                            if combatant['current_hp'] < max_hp:
                                heal_qty = max(1, math.floor(max_hp / 16))
                                combatant['current_hp'] = min(max_hp, combatant['current_hp'] + heal_qty)
                                combat_log += f"🧪 **{owner_str} {combatant['name'].capitalize()}** restored HP via its Black Sludge! (+{heal_qty})\n"
                        else:
                            # Damages non-poison types regardless of current HP
                            sludge_dmg = max(1, math.floor(max_hp / 8))
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
            # Carries the opponent too: Bad Dreams is the one trait here that reaches
            # across the field rather than acting on its own owner.
            for combatant, foe, owner_str in [(p_active, n_active, "Your"),
                                              (n_active, p_active, "The rival's")]:
                if combatant['current_hp'] > 0:
                    ability = get_active_ability(combatant)
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

                        # Solar Power's price for the Sp. Atk it grants
                        elif eot_trait['type'] == 'weather_toll':
                            current_weather = state.get('weather', {}).get('type', 'none')
                            if current_weather in eot_trait['weather']:
                                toll = max(1, math.floor(combatant.get('max_hp', 100) / eot_trait['denominator']))
                                combatant['current_hp'] = max(0, combatant['current_hp'] - toll)
                                combat_log += f"☀️ {owner_str.strip()} **{combatant['name'].capitalize()}** was scorched by its {ability_name}! (-{toll} HP)\n"

                        # Weather-gated cure (Hydration) - Shed Skin's certain cousin
                        elif eot_trait['type'] == 'weather_cure':
                            current_weather = state.get('weather', {}).get('type', 'none')
                            if current_weather in eot_trait['weather'] and combatant.get('status_condition'):
                                washed = combatant['status_condition']['name']
                                combatant['status_condition'] = None
                                combat_log += f"💧 {owner_str.strip()} **{combatant['name'].capitalize()}** washed away its {washed} with {ability_name}!\n"

                        # Bad Dreams - aimed at the OPPONENT, and only while it sleeps
                        elif eot_trait['type'] == 'sleep_drain':
                            # Comatose counts as asleep here - it is a sleep its owner
                            # walks around in, and Bad Dreams asks about the sleeping
                            # rather than about the motionless.
                            if foe and foe['current_hp'] > 0 and is_effectively_asleep(foe):
                                bite = max(1, math.floor(foe.get('max_hp', 100) / eot_trait['denominator']))
                                foe['current_hp'] = max(0, foe['current_hp'] - bite)
                                combat_log += f"😈 **{foe['name'].capitalize()}** is tormented by {combatant['name'].capitalize()}'s {ability_name}! (-{bite} HP)\n"

            # 3. Parasitic Drain (Leech Seed & Perish Song)
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

                # MULTI-HIT TRAP DAMAGE
                # One more turn survived out here, which is what disarms Fake Out
                if combatant['current_hp'] > 0:
                    combatant['turns_on_field'] = combatant.get('turns_on_field', 0) + 1

                if combatant['current_hp'] > 0 and combatant.get('volatile_statuses', {}).get('fairy_lock'):
                    combatant['volatile_statuses']['fairy_lock'] -= 1
                    if combatant['volatile_statuses']['fairy_lock'] <= 0:
                        del combatant['volatile_statuses']['fairy_lock']
                        combat_log += f"🔓 **{combatant['name'].capitalize()}** is free to move again!\n"

                if combatant['current_hp'] > 0 and 'partially_trapped' in combatant.get('volatile_statuses', {}):
                    # Traps deal exactly 1/8th of Maximum HP per turn
                    trap_dmg = max(1, math.floor(combatant.get('max_hp', 100) / 8))
                    combatant['current_hp'] = max(0, combatant['current_hp'] - trap_dmg)
                    combat_log += f"🌪️ {owner_str.strip()} **{combatant['name'].capitalize()}** is hurt by the trap! (-{trap_dmg} HP)\n"
                    
                    # Decay the trap timer!
                    combatant['volatile_statuses']['partially_trapped'] -= 1
                    if combatant['volatile_statuses']['partially_trapped'] <= 0:
                        del combatant['volatile_statuses']['partially_trapped']
                        combat_log += f"💨 {owner_str.strip()} **{combatant['name'].capitalize()}** was freed from the trap!\n"

            # ==========================================
            # 🚨 INGRAIN & OCTOLOCK (End of Turn)
            # ==========================================
            for combatant, opponent, owner_str in [(p_active, n_active, "Your"), (n_active, p_active, "The rival's")]:
                if combatant['current_hp'] > 0:
                    volatiles = combatant.get('volatile_statuses', {})
                    
                    # Aqua Ring trickles back the same share Ingrain does
                    if 'aqua_ring' in volatiles and combatant['current_hp'] < combatant.get('max_hp', 100):
                        ring_qty = max(1, math.floor(combatant.get('max_hp', 100) / AQUA_RING_FRACTION))
                        combatant['current_hp'] = min(combatant.get('max_hp', 100),
                                                      combatant['current_hp'] + ring_qty)
                        combat_log += f"\U0001f4a7 {owner_str.strip()} **{combatant['name'].capitalize()}** was restored by its veil of water! (+{ring_qty} HP)\n"

                    # A Ghost's Curse bleeds a quarter of the maximum away every turn
                    if 'curse' in volatiles:
                        curse_qty = max(1, math.floor(combatant.get('max_hp', 100) * CURSE_DRAIN_FRACTION))
                        combatant['current_hp'] = max(0, combatant['current_hp'] - curse_qty)
                        combat_log += f"\U0001f47b {owner_str.strip()} **{combatant['name'].capitalize()}** was hurt by the curse! (-{curse_qty} HP)\n"

                    # Ingrain Healing (1/16th Max HP)
                    if 'ingrain' in volatiles and combatant['current_hp'] < combatant.get('max_hp', 100):
                        heal_qty = max(1, math.floor(combatant.get('max_hp', 100) / 16))
                        combatant['current_hp'] = min(combatant.get('max_hp', 100), combatant['current_hp'] + heal_qty)
                        combat_log += f"🌱 {owner_str.strip()} **{combatant['name'].capitalize()}** absorbed nutrients from its roots! (+{heal_qty} HP)\n"
                        
                    # Octolock Decay (-1 Def, -1 SpD)
                    if 'octolock' in volatiles:
                        if 'stat_stages' not in combatant:
                            combatant['stat_stages'] = {'attack': 0, 'defense': 0, 'sp_atk': 0, 'sp_def': 0, 'speed': 0}
                        
                        combatant['stat_stages']['defense'] = max(-6, combatant['stat_stages'].get('defense', 0) - 1)
                        combatant['stat_stages']['sp_def'] = max(-6, combatant['stat_stages'].get('sp_def', 0) - 1)
                        combat_log += f"🐙 {owner_str.strip()} **{combatant['name'].capitalize()}**'s Def and Sp. Def were lowered by Octolock!\n"

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
            
            # 5. Barrier Decay (Screens)
            for hazards, owner_str in [(state['player_hazards'], "Your"), (state['npc_hazards'], "The rival's")]: 
                for screen in SIDE_SCREEN_MOVES:
                    if hazards.get(screen, 0) > 0:
                        hazards[screen] -= 1
                        if hazards[screen] <= 0:
                            del hazards[screen]
                            combat_log += f"✨ {owner_str} team's {screen.replace('-', ' ').title()} wore off!\n"

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

            # --- PHASE 3.8: KINETIC STUN, SHIELD & MEMORY CLEANUP ---
            # Wipe temporary flinch, protection flags, and short-term memory before the next round begins
            for combatant in [p_active, n_active]:
                
                # 1. Clear Short-Term Damage Memory
                combatant.pop('last_damage_taken', None)
                combatant.pop('last_damage_class', None)
                
                # 2. Clear Volatile Flags and Curses
                if 'volatile_statuses' in combatant:
                    combatant['volatile_statuses'].pop('flinch', None)
                    combatant['volatile_statuses'].pop('protected', None)
                    combatant['volatile_statuses'].pop('protect_type', None)
                    combatant['volatile_statuses'].pop('destiny-bond', None)
                    combatant['volatile_statuses'].pop('is_switching', None)
                    combatant['volatile_statuses'].pop('stats_lowered_this_turn', None)
                    combatant['volatile_statuses'].pop('electrified', None)
                    clear_interceptors(combatant)

                    # Magnet Rise and Telekinesis run their own clocks
                    for lift in ('magnet_rise', 'telekinesis'):
                        if combatant['volatile_statuses'].get(lift):
                            combatant['volatile_statuses'][lift] -= 1
                            if combatant['volatile_statuses'][lift] <= 0:
                                del combatant['volatile_statuses'][lift]
                                combat_log += f"🪂 **{combatant['name'].capitalize()}** drifted back to the ground!\n"

                    # Embargo runs on its own five-turn clock rather than being wiped
                    if combatant['volatile_statuses'].get('embargo'):
                        combatant['volatile_statuses']['embargo'] -= 1
                        if combatant['volatile_statuses']['embargo'] <= 0:
                            del combatant['volatile_statuses']['embargo']
                            combat_log += f"✨ **{combatant['name'].capitalize()}** is free of its Embargo!\n"

                    # A charge that was pending and did NOT fire this turn means the
                    # user was stopped, so the move fails and it comes back down.
                    broken = break_stale_charge(combatant)
                    if broken:
                        combat_log += f"✨ **{combatant['name'].capitalize()}**'s {broken.replace('-', ' ').title()} was interrupted!\n"
                    
            print("DEBUG 8: Entering Phase 4 (Survival & Swap Checks)")

            # --- END-OF-TURN ITEM PASS ---
            # Was an inline berry sweep here and nowhere else, which is exactly how the
            # survival pass below came to be PvE-only. Block 19 hangs four more things
            # off the same moment, so it went shared before it grew rather than after.
            combat_log += end_of_turn_items(
                state,
                (p_active, n_active, "Your"),
                (n_active, p_active, "The rival's"))

            # 🚨 FIELD STATE DECAY
            if 'field' in state:
                # The sports and the deluge are added to the field only when used, so
                # these are read with .get rather than indexed - the dictionary is built
                # with the four rooms alone.
                for field_state in ['trick_room', 'wonder_room', 'gravity', 'magic_room',
                                    'mud_sport', 'water_sport', 'ion_deluge']:
                    if state['field'].get(field_state, 0) > 0:
                        state['field'][field_state] -= 1
                        if state['field'][field_state] == 0:
                            msgs = {
                                'trick_room': "The twisted dimensions returned to normal!",
                                'wonder_room': "Wonder Room wore off, and stats returned to normal!",
                                'gravity': "Gravity returned to normal!",
                                'magic_room': "Magic Room wore off, and held items regained their power!",
                                'mud_sport': "The mud washed away, and Electric moves regained their power!",
                                'water_sport': "The water dried up, and Fire moves regained their power!",
                                'ion_deluge': "The ion deluge cleared, and Normal moves stayed Normal!"
                            }
                            combat_log += f"✨ {msgs[field_state]}\n"
                            
            # 🚨 TAILWIND DECAY
            for hazards, owner_str in [(p_active, "Your"), (n_active, "The rival's")]:
                if hazards.get('tailwind', 0) > 0:
                    hazards['tailwind'] -= 1
                    if hazards['tailwind'] <= 0:
                        del hazards['tailwind']
                        combat_log += f"✨ {owner_str} team's Tailwind petered out!\n"

            # --- PHASE 4: SURVIVAL & SWAP CHECK ---
            # Four blocks' worth of end-of-turn reactions, in one shared call. This was
            # written inline here and nowhere else, which is how nine abilities across
            # Blocks 13, 15 and 16 came to be inert in PvP.
            combat_log += await end_of_turn_survival(
                state,
                (p_active, 'player_must_pivot', 'Your'),
                (n_active, 'npc_must_pivot', "The rival's"))

            n_needs_swap = n_active['current_hp'] <= 0 or state.get('npc_must_pivot')
            p_needs_swap = p_active['current_hp'] <= 0 or state.get('player_must_pivot')
            
            # ==========================================
            # 🚨 NEW: PRIMORDIAL WEATHER FAINT/PIVOT CLEAR
            # ==========================================
            weather = state.get('weather', {})
            if weather.get('primordial'):
                p_is_setter = p_needs_swap and get_active_ability(p_active) in ['desolate-land', 'primordial-sea', 'delta-stream']
                n_is_setter = n_needs_swap and get_active_ability(n_active) in ['desolate-land', 'primordial-sea', 'delta-stream']
                
                if p_is_setter or n_is_setter:
                    state['weather'] = {'type': 'none', 'duration': 0, 'primordial': False}
                    combat_log += "\n🌤️ The primordial weather dissipated as its creator left the field!\n"
            # ==========================================

            if n_needs_swap:
                if n_active['current_hp'] <= 0:
                    combat_log += f"\n💀 The rival's **{n_active['name'].capitalize()}** is unable to continue!"
                else:
                    combat_log += f"\n💨 The rival's **{n_active['name'].capitalize()}** retreated to the bench!"
                    state['npc_must_pivot'] = False # Flush the memory flag

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
                    combat_log = await trigger_single_entry_ability(n_active, p_active, "The rival's", state, combat_log)
                else:
                    # ==========================================
                    # THE WARDEN VICTORY INTERCEPTOR
                    # ==========================================
                    if state.get('is_warden'):
                        async with aiosqlite.connect(DB_FILE) as db:
                            await db.execute("BEGIN TRANSACTION")
                            
                            biome = state.get('warden_biome')
                            w_data = WARDEN_ROSTER[biome]
                            next_biome = w_data['biome_unlocked']
                            r_item = w_data['reward_item']
                            r_qty = w_data['reward_qty']
                            
                            # 1. Upgrade the Researcher's Visa
                            async with db.execute("SELECT unlocked_visas FROM users WHERE user_id = ?", (self.user_id,)) as cursor:
                                user_data = await cursor.fetchone()
                            
                            current_visas = user_data[0] if user_data and user_data[0] else "canopy"
                            
                            # --- THE ANTI-FARMING LOGIC ---
                            if next_biome not in current_visas.split(','):
                                # FIRST TIME CLEAR!
                                new_visas = f"{current_visas},{next_biome}"
                                await db.execute("UPDATE users SET unlocked_visas = ? WHERE user_id = ?", (new_visas, self.user_id))
                                
                                await db.execute("""
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
                                await db.execute("UPDATE users SET eco_tokens = eco_tokens + 500 WHERE user_id = ?", (self.user_id,))
                                
                                rewards_log = f"\n\n🎖️ **WARDEN DEFEATED!** You proved your continued mastery against the {w_data['title']}!\n"
                                rewards_log += "💰 You received **500 Eco Tokens** for the sparring session.\n"
                                rewards_log += "*(Note: Sector Visas and unique equipment are only granted on the first clear.)*"
                            
                            await db.commit() # Lock the transaction!
                        
                        # 3. Clean up and print the Victory UI!
                        del self.cog.active_battles[self.user_id]
                        embed = discord.Embed(title="🛡️ Sector Secured!", description=combat_log + rewards_log, color=discord.Color.purple())
                        return await interaction.edit_original_response(embed=embed, view=None, attachments=[])
                    
                    # ==========================================
                    # THE ECOLOGICAL REWARDS ENGINE
                    # ==========================================
                    # Initialize an empty UI view to hold our buttons
                    post_battle_view = None 

                    # 1. Calculate Research Funding (Eco Tokens)
                    tokens_earned = 100 + (len(state['npc_team']) * 250)

                    # Happy Hour doubles the battle's takings. Applied to the reward
                    # itself and not to the scattered coins, which are picked up rather
                    # than won.
                    happy_multiplier = prize_multiplier(state.get('player_hazards'))
                    tokens_earned *= happy_multiplier

                    # Pay Day, Make It Rain and G-Max Gold Rush all scatter coins
                    # mid-battle; they are picked up here and credited to whichever of
                    # them actually did it.
                    coin_bonus = collected_coins(state['player_team'])
                    coin_credit = coin_sources(state['player_team'])
                    tokens_earned += coin_bonus
                    
                    # 2. Calculate Biomass/Experience Accumulation
                    total_exp_yield = sum([p.get('level', 50) * 15 for p in state['npc_team']])
                    
                    # 3. Distribute EXP
                    surviving_team = [p for p in state['player_team'] if p['current_hp'] > 0]
                    exp_per_specimen = math.floor(total_exp_yield / max(1, len(surviving_team)))
                    
                    rewards_log: str = f"\n\n💰 You earned **{tokens_earned} Eco Tokens** for your research!\n"
                    if coin_bonus:
                        credited = " and ".join(coin_credit) if coin_credit else "your team"
                        rewards_log += f"🪙 **{coin_bonus}** of that was loose change scattered by {credited}!\n"
                    if happy_multiplier > 1:
                        rewards_log += f"🎉 Happy Hour **doubled** the reward!\n"
                    rewards_log += f"📈 Surviving team members gained **{exp_per_specimen} EXP**!\n\n"
                    
                    # 🚨 ASYNCHRONOUS DATABASE TRANSACTION
                    async with aiosqlite.connect(DB_FILE) as db:
                        await db.execute("BEGIN TRANSACTION")
                        
                        # 4. Update the User's Bank Account
                        await db.execute("UPDATE users SET eco_tokens = eco_tokens + ? WHERE user_id = ?", (tokens_earned, self.user_id))
                        
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
                                    # What it will KEEP, not what a Trick happens to have
                                    # left in its hands at the final bell.
                                    held_item = resolve_persisted_item(p).lower().replace(' ', '-')

                                    # Block 1: The Everstone Suppressant
                                    if held_item == 'everstone':
                                        rewards_log += f"🪨 **{p['name'].capitalize()}**'s biological mutation was suppressed by its Everstone!\n"
                                    
                                    # Block 2: Check for Mutation
                                    else:
                                        print(f"\n[DEBUG EVO PvE] 1. Checking evolution for {p['name']} (Level {p['level']})")
                                        try:
                                            evo_msg, target_species = await self.check_for_evolution(db, self.user_id, p, combat_log)
                                            print(f"[DEBUG EVO PvE] 2. check_for_evolution returned -> msg: {bool(evo_msg)}, target: {target_species}")
                                            
                                            if evo_msg:
                                                rewards_log += evo_msg
                                            
                                            if target_species and post_battle_view is None:
                                                print(f"[DEBUG EVO PvE] 3. Instantiating EvolutionConfirmView for {target_species}...")
                                                post_battle_view = EvolutionConfirmView(self.cog, self.user_id, p, target_species)
                                                print(f"[DEBUG EVO PvE] 4. View created successfully: {post_battle_view}")
                                        except Exception as e:
                                            print(f"[DEBUG EVO PvE] 🚨 CRASH inside evolution check: {e}")
                                # -----------------------------
                                
                        # Save the entire team's updated state
                        for p in state['player_team']:
                            if 'instance_id' in p:
                                await db.execute("""
                                    UPDATE caught_pokemon 
                                    SET level = ?, experience = ?, held_item = ?
                                    WHERE instance_id = ?
                                """, (p['level'], p['experience'], resolve_persisted_item(p), p['instance_id']))

                                sketched = await persist_sketch(db, p)
                                if sketched:
                                    rewards_log += f"\n✏️ **{p['name'].capitalize()}** permanently learned {sketched.replace('-', ' ').title()}!"

                        # Block 19: Pickup and Honey Gather, the two halves that have
                        # nothing to do during a turn.
                        rewards_log += await collect_field_spoils(
                            db, state['player_team'], self.user_id)

                        # ==========================================
                        # DIRECTIVE TRACKER: INVASIVE CULLING
                        # ==========================================
                        defeated_types = n_active.get('types', [])
                        for p_type in defeated_types:
                            # 1. Increment progress
                            await db.execute("""
                                UPDATE field_directives
                                SET current_progress = current_progress + 1
                                WHERE user_id = ? AND objective_type = 'cull_type' AND target_variable = ? AND is_completed = 0
                            """, (self.user_id, p_type))

                            # 2. Check if maxed out
                            async with db.execute("""
                                SELECT required_amount, current_progress 
                                FROM field_directives
                                WHERE user_id = ? AND objective_type = 'cull_type' AND target_variable = ? AND is_completed = 0
                            """, (self.user_id, p_type)) as cursor:
                                row = await cursor.fetchone()
                                
                            if row and row[1] == row[0]: 
                                rewards_log += f"\n📡 **Directive Complete:** You successfully culled the invasive {p_type.capitalize()}-type population! Use `!claim` to receive your funding."

                        # ==========================================
                        # GEOLOGICAL ANOMALY: METEOR SHOWER
                        # ==========================================
                        if random.random() <= 0.05: 
                            await db.execute("""
                                INSERT INTO user_inventory (user_id, item_name, quantity) 
                                VALUES (?, 'raw-keystone', 1) 
                                ON CONFLICT(user_id, item_name) 
                                DO UPDATE SET quantity = quantity + 1
                            """, (self.user_id,))
                            rewards_log += "\n🌠 **ANOMALY DETECTED:** A localized meteor shower occurred during the skirmish! You recovered a `Raw Keystone` from the crater."

                        # ==========================================
                        # BIOLOGICAL ANOMALY: MYCELIAL BLOOM
                        # ==========================================
                        if random.random() <= 0.15: 
                            await db.execute("""
                                INSERT INTO user_inventory (user_id, item_name, quantity) 
                                VALUES (?, 'memory-spore', 1) 
                                ON CONFLICT(user_id, item_name) 
                                DO UPDATE SET quantity = quantity + 1
                            """, (self.user_id,))
                            rewards_log += "\n🍄 **ANOMALY DETECTED:** The combat disturbed a localized mycelial network! You recovered a `Memory Spore`."

                        # ==========================================
                        # FIELD DATA RECOVERY: ENCRYPTED NOTES
                        # ==========================================
                        if random.random() <= 0.10: 
                            await db.execute("""
                                INSERT INTO user_inventory (user_id, item_name, quantity) 
                                VALUES (?, 'encrypted-field-notes', 1) 
                                ON CONFLICT(user_id, item_name) 
                                DO UPDATE SET quantity = quantity + 1
                            """, (self.user_id,))
                            rewards_log += "\n📝 **DATA RECOVERED:** You found some `Encrypted Field Notes` dropped in the brush! Run `!analyze notes` to decode them."

                        # ==========================================
                        # RADIANT ANOMALY: SOLAR FLARE
                        # ==========================================
                        if random.random() <= 0.07: 
                            await db.execute("""
                                INSERT INTO user_inventory (user_id, item_name, quantity) 
                                VALUES (?, 'sparkling-stone', 1) 
                                ON CONFLICT(user_id, item_name) 
                                DO UPDATE SET quantity = quantity + 1
                            """, (self.user_id,))
                            rewards_log += "\n☀️ **ANOMALY DETECTED:** A sudden burst of radiant energy crystallized the local soil! You extracted a `Sparkling Stone`."

                        # ==========================================
                        # ATMOSPHERIC ANOMALY: ENERGY SMOG
                        # ==========================================
                        if random.random() <= 0.08: 
                            await db.execute("""
                                INSERT INTO user_inventory (user_id, item_name, quantity) 
                                VALUES (?, 'wishing-fragment', 1) 
                                ON CONFLICT(user_id, item_name) 
                                DO UPDATE SET quantity = quantity + 1
                            """, (self.user_id,))
                            rewards_log += "\n🌫️ **ANOMALY DETECTED:** A dense cluster of reactive energy passed over the area! You collected a volatile `Wishing Fragment` from the fallout."

                        await db.commit() # 🚨 Lock in all the rewards at once!
                        
                    # 6. Shut down the engine and print the victory screen!
                    del self.cog.active_battles[self.user_id]
                    
                    embed = discord.Embed(title="🏆 Field Duel Victorious!", description=combat_log + rewards_log, color=discord.Color.gold())
                    print(f"[DEBUG EVO PvE] 5. Final UI Dispatch. Passing view: {post_battle_view}")
                    return await interaction.edit_original_response(embed=embed, view=post_battle_view, attachments=[])

            # --- PLAYER SURVIVAL CHECK ---
            p_needs_swap = p_active['current_hp'] <= 0 or state.get('player_must_pivot')
            
            if p_needs_swap:
                if p_active['current_hp'] <= 0:
                    combat_log += f"\n⚠️ Your **{p_active['name'].capitalize()}** requires immediate medical attention!"
                else:
                    combat_log += f"\n💨 Your **{p_active['name'].capitalize()}** is preparing to pivot out!"
                    state['player_must_pivot'] = False # Flush the memory flag
                
                # Ensure they actually have a living bench specimen to swap into!
                has_survivors = any(p['current_hp'] > 0 and i != state['active_player_index'] for i, p in enumerate(state['player_team']))
                
                if has_survivors:
                    combat_log += "\n**Who will you send out next?**"
                    
                    # We pass `forced=True` to hide the cancel button!
                    swap_view = SwapMenu(self.cog, self.user_id, self.ctx, self, forced=True)
                    
                    embed = discord.Embed(title="⚠️ Tactical Swap Required!", description=combat_log, color=discord.Color.orange())
                    return await interaction.edit_original_response(embed=embed, view=swap_view, attachments=[])
                else:
                    if p_active['current_hp'] <= 0:
                        del self.cog.active_battles[self.user_id]
                        embed = discord.Embed(title="💥 Field Duel Lost", description=combat_log, color=discord.Color.dark_red())
                        return await interaction.edit_original_response(embed=embed, view=None, attachments=[])
                    else:
                        combat_log += "\n*...But there were no healthy specimens left to deploy!*"

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
                n_hazards=state.get('npc_hazards'),
                p_name=p_active.get('name'), p_level=p_active.get('level'),
                p_gender=p_active.get('gender'), n_gender=n_active.get('gender'),
                n_name=n_active.get('name'), n_level=n_active.get('level'),
                p_aura=battle_render.aura_for(state.get('adaptation'), p_active),
                biome=state.get('warden_biome')
            )
            # ==========================================
            await self.refresh_buttons()
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
        
    async def check_and_consume_energy(self, user_id: str, cost: int = 10) -> tuple[bool, str]:
        """
        Lazy-evaluates stamina regeneration and attempts to consume the required cost.
        Returns (Success_Boolean, Status_Message).
        """
        MAX_ENERGY = 100
        REGEN_PER_HOUR = 10
        SECONDS_IN_HOUR = 3600
        
        
        try:
            async with aiosqlite.connect(DB_FILE) as db:
                async with db.execute("SELECT current_energy, last_energy_tick FROM users WHERE user_id = ?", (user_id,)) as cursor:
                    row = await cursor.fetchone()
            
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
                    
                await db.execute("""
                        UPDATE users 
                        SET current_energy = ?, last_energy_tick = ? 
                        WHERE user_id = ?
                    """, (current_energy, last_tick, user_id))
                    
                await db.commit()
                
                return True, f"🔋 Spent **{cost} Energy** (Remaining: {current_energy}/{MAX_ENERGY})"
            
        except Exception as e:
            print(f"Energy System Error: {e}")
            return False, "❌ A critical error occurred while processing your stamina."

    async def build_npc_combatant(self, db, pokedex_id, name, level, moves, types):
        """
        Generates a wild ecological variant for the rival team.

        Reported bug: an Eelektross shrugged off Mud Shot in PvP and ate it in PvE. The
        cause was not Levitate and not the engines diverging - it was this builder, which
        never gave the specimen an ability at all. get_active_ability read a missing key
        as 'none', so EVERY ability was inert on a generated rival, and the gym-leader
        rosters only worked because they name theirs by hand.

        volatile_statuses is here for the same reason the player's dict carries it: the
        engines subscript it directly in dozens of places, and those were only safe while
        no generated rival had an ability capable of reaching them.
        """
        base_stats = await fetch_base_stats(db, pokedex_id)

        ivs = {stat: random.randint(0, 31) for stat in ['hp', 'attack', 'defense', 'sp_atk', 'sp_def', 'speed']}
        evs = {stat: 0 for stat in ['hp', 'attack', 'defense', 'sp_atk', 'sp_def', 'speed']}
        nature = random.choice(list(NATURE_MULTIPLIERS.keys()))

        final_stats = calculate_stats(base_stats, ivs, evs, level, nature)
        gender = roll_gender(await fetch_gender_rate(db, pokedex_id), species_name=name)
        ability = await roll_species_ability(db, pokedex_id)

        return {
            'pokedex_id': pokedex_id, 'name': name, 'level': level, 'types': types,
            'max_hp': final_stats['hp'], 'current_hp': final_stats['hp'],
            'stats': final_stats, 'moves': moves, 'status_condition': None,
            'gender': gender,
            'ability': ability,
            'volatile_statuses': {},
            'held_item': 'none',
            # Read by the Primal and Crowned form changes, which re-derive the stats
            'ivs': ivs, 'evs': evs, 'nature': nature,
        }
    
    @commands.command(name="tutor", aliases=["relearn", "teach_move"])
    @checks.has_started()
    @checks.is_authorized()
    @checks.is_not_in_trade()
    @checks.is_not_in_combat()
    @checks.partner_not_deployed()
    async def tutor_move(self, ctx, instance_id: str, *, move_name: str):
        """Stimulates dormant genetic pathways to teach a specimen a new move."""
        user_id = str(ctx.author.id)
        requested_move = move_name.lower().replace(" ", "-")

        try:
            async with aiosqlite.connect(DB_FILE) as db:
                
                # ==========================================
                # 1. SPECIMEN RETRIEVAL (Partial Tag Matching)
                # ==========================================
                # We append the % wildcard to the user's input
                search_tag = f"{instance_id}%"
                
                async with db.execute("""
                    SELECT cp.instance_id, cp.pokedex_id, s.name, cp.level, 
                           cp.move_1, cp.move_2, cp.move_3, cp.move_4
                    FROM caught_pokemon cp
                    JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                    WHERE cp.user_id = ? AND cp.instance_id LIKE ?
                """, (user_id, search_tag)) as cursor:
                    # Fetch ALL matching rows
                    matching_specimens = await cursor.fetchall()
                
                if len(matching_specimens) == 0:
                    return await ctx.send(f"⚠️ **Asset Not Found:** You do not own a specimen with a tag starting with `{instance_id}`.")
                    
                if len(matching_specimens) > 1:
                    # If the prefix is too short and matches multiple IDs, force them to be specific!
                    matched_tags = ", ".join([f"`{row[0][:6]}` ({row[2].capitalize()})" for row in matching_specimens])
                    return await ctx.send(f"🔍 **Ambiguous Tag:** `{instance_id}` matches multiple specimens in your PC:\n{matched_tags}\n\nPlease provide a few more characters of the ID to confirm the target.")
                    
                # If exactly ONE match is found, we safely unpack it
                specimen_data = matching_specimens[0]
                
                # We overwrite the user's short input with the actual full database ID!
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
                async with db.execute("""
                    SELECT learn_method, level_learned 
                    FROM species_movepool 
                    WHERE pokedex_id = ? AND move_name = ? 
                    AND learn_method IN ('level-up', 'tutor')
                """, (p_id, requested_move)) as cursor:
                    pool_data = await cursor.fetchone()
                
                if not pool_data:
                    return await ctx.send(f"🧬 **Genetic Incompatibility:** **{species_name.capitalize()}** is biologically incapable of learning `{requested_move.replace('-', ' ').title()}` via tutoring.")
                    
                learn_method, level_learned = pool_data
                
                if learn_method == 'level-up' and current_level < level_learned:
                    return await ctx.send(f"⚠️ **Maturation Error:** **{species_name.capitalize()}** must reach Level {level_learned} before its biology can support `{requested_move.replace('-', ' ').title()}`.")

                # ==========================================
                # 4. RESOURCE VERIFICATION
                # ==========================================
                async with db.execute("SELECT eco_tokens FROM users WHERE user_id = ?", (user_id,)) as cursor:
                    funds_row = await cursor.fetchone()
                    funds = funds_row[0] if funds_row else 0
                
                async with db.execute("SELECT quantity FROM user_inventory WHERE user_id = ? AND item_name = 'memory-spore'", (user_id,)) as cursor:
                    spores_row = await cursor.fetchone()
                    spore_qty = spores_row[0] if spores_row else 0
                
                if funds < 500 or spore_qty < 1:
                    return await ctx.send("❌ **Insufficient Resources:** The laboratory requires **500 Eco Tokens** and **1x Memory Spore** to perform a neural rewrite.")

                # ==========================================
                # 5. EXECUTION PIPELINE
                # ==========================================
                if len(current_moves) < 4:
                    # Target the exact column that needs to be filled
                    empty_slot = f"move_{len(current_moves) + 1}"
                    
                    await db.execute("BEGIN TRANSACTION")
                    await db.execute("UPDATE users SET eco_tokens = eco_tokens - 500 WHERE user_id = ?", (user_id,))
                    await db.execute("UPDATE user_inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_name = 'memory-spore'", (user_id,))
                    # Safe to use an f-string here since empty_slot is strictly derived from our internal len() calculation
                    await db.execute(f"UPDATE caught_pokemon SET {empty_slot} = ? WHERE instance_id = ?", (requested_move, actual_instance_id))
                    
                    await db.commit() # 🚨 Lock in the changes!
                    
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
            # We no longer need `if conn.in_transaction: conn.rollback()` because aiosqlite handles uncommitted block exits automatically!
            print(f"Tutor Command Error: {e}")
            await ctx.send("❌ A critical laboratory error occurred while accessing the neural database.")

    @commands.command(name="learn")
    @checks.has_started()
    @checks.is_authorized()
    @checks.is_not_in_combat()
    @checks.partner_not_deployed()
    async def learn_move(self, ctx, *, request: str = None):
        """Teaches a move. `!learn tackle` uses your selected partner and a free slot."""
        user_id = str(ctx.author.id)

        USAGE = ("⚠️ Usage: `!learn <move>` teaches your selected partner. Add a "
                 "slot to choose what it forgets, or a box number or tag to name a "
                 "different specimen.\n"
                 "For example: `!learn earthquake`, `!learn 2 earthquake`, or "
                 "`!learn 4 2 earthquake`.")

        parsed = parse_learn_request(request)
        if not parsed:
            return await ctx.send(USAGE)
        target, slot, move_name = parsed

        # 1. Validate the Slot. None is allowed now - it means "wherever there is room",
        #    which is what `!tm` always did and what somebody with an empty slot means.
        if slot is not None and slot not in [1, 2, 3, 4]:
            return await ctx.send("⚠️ Specimens can only retain 4 active behaviors at a time. Please specify a slot between 1 and 4.")

        formatted_move = move_name.lower().replace(" ", "-")

        try:
            async with aiosqlite.connect(DB_FILE) as db:
                # 2. Determine the Target Specimen. `target` of None means the one they
                #    already selected with `!partner`, which is the common case and used
                #    to be the one spelling this command would not accept.
                pokemon_data, problem = await locate_specimen(
                    db, user_id, target,
                    "cp.instance_id, cp.pokedex_id, cp.level, s.name, "
                    "cp.move_1, cp.move_2, cp.move_3, cp.move_4")
                if problem:
                    return await ctx.send(problem)

                db_tag_id, poke_id, level, poke_name, m1, m2, m3, m4 = pokemon_data
                current_moves = [m1, m2, m3, m4]
                known = [m for m in current_moves if m and m != 'none']

                # 3. Check for Duplicates
                if formatted_move in current_moves:
                    return await ctx.send(f"⚠️ Your **{poke_name.capitalize()}** already has `{formatted_move.replace('-', ' ').title()}` equipped in its active behaviors!")

                # 4. HOW it may learn it, which used to be "is it in the movepool at
                #    all" - and a TM move is in the movepool, so every one of them was
                #    free. A machine route now costs the machine.
                route, problem = await teaching_route(
                    db, user_id, poke_name, poke_id, level, formatted_move)
                if problem:
                    return await ctx.send(problem)

                # 5. No slot named and no room: ask which move to forget rather than
                #    picking one. The TM is spent by the menu, on confirmation, so
                #    backing out here costs nothing.
                if slot is None and len(known) >= 4:
                    note = ("\n\n*Your TM is only spent if you confirm.*"
                            if route == 'machine' else "")
                    embed = discord.Embed(
                        title="⚠️ Neural Capacity Reached",
                        description=f"**{poke_name.capitalize()}** already knows four "
                                    f"moves. Which should it forget to learn "
                                    f"`{formatted_move.replace('-', ' ').title()}`?"
                                    + note,
                        color=discord.Color.orange())
                    view = TeachMenu(self, user_id, db_tag_id, poke_name,
                                     formatted_move, known,
                                     consumes_tm=(route == 'machine'))
                    return await ctx.send(embed=embed, view=view)

                if slot is None:
                    # The first genuinely empty slot.
                    slot = next(i + 1 for i, m in enumerate(current_moves)
                                if not m or m == 'none')

                # 6. Execute the Training (Update the specific slot)
                column_to_update = f"move_{slot}"

                await db.execute(f"""
                    UPDATE caught_pokemon
                    SET {column_to_update} = ?
                    WHERE instance_id = ?
                """, (formatted_move, db_tag_id))

                # The machine is consumed in the SAME transaction as the move it taught,
                # so a failure cannot leave somebody holding the move and the TM, or
                # neither.
                if route == 'machine':
                    await db.execute(
                        "UPDATE user_tms SET quantity = quantity - 1 "
                        "WHERE user_id = ? AND tm_name = ?", (user_id, formatted_move))

                await db.commit()

                replaced_move = current_moves[slot - 1]
                replaced_text = f" It forgot `{replaced_move.replace('-', ' ').title()}` to make room." if replaced_move and replaced_move != 'none' else ""

                embed = discord.Embed(title="🧠 Behavioral Training Successful!", color=discord.Color.blue())
                embed.description = (f"**{ctx.author.name}** spent time training their "
                                     f"**{poke_name.capitalize()}**.\n\nIt successfully "
                                     f"mastered **{formatted_move.replace('-', ' ').title()}**!"
                                     f"{replaced_text}")
                if route == 'machine':
                    embed.description += "\n\n💿 The TM was consumed."
                embed.set_footer(text=f"Tag ID: {str(db_tag_id)[:8]} | Slot {slot} Updated")

                await ctx.send(embed=embed)

        except Exception as e:
            print(f"Learn error: {e}")
            await ctx.send("A data corruption error occurred during training.")

    @commands.command(name="battle", aliases=["duel", "spar"])
    @checks.has_started()
    @checks.is_authorized()
    @checks.is_not_in_combat()
    @checks.partner_not_deployed()
    async def challenge_player(self, ctx, opponent: discord.Member = None):
        """Issues a formal Ecological Field Duel invitation to another researcher."""
        challenger_id = str(ctx.author.id)
        
        if not opponent:
            return await ctx.send("⚠️ You must ping the researcher you wish to spar with! Usage: `!battle @User`")
            
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
            
        # 2. ROSTER CHECK: Do both players have teams?
        async with aiosqlite.connect(DB_FILE) as db:
            scope, scope_params = await party_filter(db, challenger_id, alias=None)
            async with db.execute(
                    f"SELECT COUNT(*) FROM user_party WHERE user_id = ? {scope}",
                    (challenger_id, *scope_params)) as cursor:
                if (await cursor.fetchone())[0] == 0:
                    return await ctx.send("⚠️ You must assign at least one specimen to your roster using `!party add 1 [Box Number]` before initiating a spar.")

            scope, scope_params = await party_filter(db, opponent_id, alias=None)
            async with db.execute(
                    f"SELECT COUNT(*) FROM user_party WHERE user_id = ? {scope}",
                    (opponent_id, *scope_params)) as cursor:
                if (await cursor.fetchone())[0] == 0:
                    return await ctx.send(f"⚠️ **{opponent.display_name}** does not have a fieldwork roster assembled yet.")

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
            teams = {}
            key_items = {}

            async with aiosqlite.connect(DB_FILE) as db:
                async with db.cursor() as cursor:
                    # 1. Fetch Biology and Loadout for BOTH players
                    for uid in [p1_id, p2_id]:
                        print(f"\n--- DEBUG: Extracting Roster for User {uid} ---")
                        
                        
                        scope, scope_params = await party_filter(db, uid)
                        async with db.execute(f"""
                            SELECT cp.instance_id, cp.pokedex_id, s.name, cp.level, cp.nature,
                                cp.iv_hp, cp.iv_attack, cp.iv_defense, cp.iv_sp_atk, cp.iv_sp_def, cp.iv_speed,
                                cp.ev_hp, cp.ev_attack, cp.ev_defense, cp.ev_sp_atk, cp.ev_sp_def, cp.ev_speed,
                                cp.move_1, cp.move_2, cp.move_3, cp.move_4, cp.is_shiny, cp.held_item, cp.gmax_factor, cp.ability, cp.experience, up.slot, cp.gender, cp.happiness
                            FROM user_party up
                            JOIN caught_pokemon cp ON up.instance_id = cp.instance_id
                            JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                            WHERE up.user_id = ? {scope}
                            ORDER BY up.slot ASC
                        """, (uid, *scope_params)) as roster_cursor:
                            rows = await roster_cursor.fetchall()
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
                                # 🚨 `target` decides whether a stat change lands on the user or the
                                # opponent, and status_type/status_chance carry flinch. Without all
                                # three, PvP sent every self-buff to the wrong side and no move
                                # could ever flinch.
                                async with db.execute("""
                                    SELECT type, power, accuracy, damage_class, pp,
                                        ailment, ailment_chance, stat_name, stat_change,
                                        stat_chance, drain, healing, priority,
                                        target, status_type, status_chance
                                    FROM base_moves WHERE name = ?
                                """, (m_name,)) as cursor:
                                    m_data = await cursor.fetchone()


                                if m_data:
                                    (m_type, m_power, m_acc, m_class, m_pp, m_ail, m_ail_c, m_stat,
                                     m_stat_c, m_stat_ch, m_drain, m_heal, m_prio,
                                     m_target, m_status_type, m_status_chance) = m_data
                                    p_moves.append({
                                        'name': m_name, 'type': m_type, 'power': m_power, 'accuracy': m_acc,
                                        'class': m_class, 'pp': m_pp, 'max_pp': m_pp, 'ailment': m_ail,
                                        'ailment_chance': m_ail_c, 'stat_name': m_stat, 'stat_change': m_stat_c,
                                        'stat_chance': m_stat_ch, 'drain': m_drain, 'healing': m_heal,
                                        'priority': m_prio,
                                        'target': m_target,
                                        'status_type': m_status_type or 'none',
                                        'status_chance': m_status_chance or 0
                                    })
                                else:
                                    p_moves.append({'name': m_name, 'pp': 5, 'max_pp': 5, 'priority': 0})

                            # Fetch Elemental Typing
                            async with db.execute("SELECT type_name FROM base_pokemon_types WHERE pokedex_id = ?", (poke_id,)) as cursor:
                                p_types = [t[0] for t in await cursor.fetchall()]
                            
                            # Calculate True Stats
                            p_base = await fetch_base_stats(db, poke_id)
                            p_final_stats = calculate_stats(p_base, p_ivs, p_evs, p_lvl, p_nature)
                            
                            player_team.append({
                                'instance_id': tag, 'pokedex_id': poke_id, 'name': p_name, 'level': p_lvl,
                                'max_hp': p_final_stats['hp'], 'current_hp': p_final_stats['hp'],
                                'stats': p_final_stats, 'moves': p_moves, 'status_condition': None, 
                                'is_shiny': row[21], 'held_item': row[22], 'gmax_factor': row[23], 
                                'ability': row[24], 'types': p_types, 'experience': row[25], 'volatile_statuses': {},
                                'gender': normalize_gender(row[27]),
                                # Appended last in the SELECT, so it is read off the end
                                # rather than renumbering every index above it.
                                'happiness': row[-1]
                            })
                            
                        teams[uid] = player_team
                        print(f"--- DEBUG: Team load complete for {uid}. Total size: {len(player_team)} ---")
                        
                        # Key Item Scanner
                        async with db.execute("""
                            SELECT item_name FROM user_inventory 
                            WHERE user_id = ? AND item_name IN ('dynamax-band', 'z-ring', 'mega-bracelet') AND quantity > 0
                        """, (uid,)) as cursor:
                            owned_key_items = [r[0] for r in await cursor.fetchall()]
                        
                        
                        key_items[uid] = {
                            'dynamax_band': 'dynamax-band' in owned_key_items,
                            'z_ring': 'z-ring' in owned_key_items,
                            'mega_bracelet': 'mega-bracelet' in owned_key_items
                        }
            print("DEBUG: Database extraction complete. Building Shared State...")

            # 2. Build the Shared Memory Reference (The PvP Ecosystem)
            shared_state = {
                'is_pvp': True,
                'p1_id': p1_id,
                'p2_id': p2_id,
                'p1': p1, 
                'p2': p2,
                
                'p1_team': snapshot_team_items(teams[p1_id]),
                'p2_team': snapshot_team_items(teams[p2_id]),
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
                'p2_hazards': {'stealth-rock': False, 'spikes': 0, 'toxic-spikes': 0, 'sticky-web': False},

                # Pending Future Sight / Doom Desire strikes, keyed by the side they will HIT
                'p1_future': None,
                'p2_future': None,

                # Pending Wishes, keyed by the side they will HEAL
                'p1_wish': None,
                'p2_wish': None
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
            
            combat_log = await trigger_single_entry_ability(p1_lead, p2_lead, f"{p1.display_name}'s", shared_state, combat_log)
            combat_log = await trigger_single_entry_ability(p2_lead, p1_lead, f"{p2.display_name}'s", shared_state, combat_log)

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
                n_hazards=shared_state['p2_hazards'],
                p_name=p1_lead.get('name'), p_level=p1_lead.get('level'),
                p_gender=p1_lead.get('gender'), n_gender=p2_lead.get('gender'),
                n_name=p2_lead.get('name'), n_level=p2_lead.get('level'),
                p_aura=battle_render.aura_for(shared_state.get('p1_adaptation'), p1_lead),
                n_aura=battle_render.aura_for(shared_state.get('p2_adaptation'), p2_lead)
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

                # Passing the attachments back was half the answer. The other half is
                # that a FETCHED embed's image url is a signed CDN link, not
                # `attachment://battle.png` - and editing re-issues the attachment under
                # a new signature, leaving the embed pointing at a dead one. That is why
                # the scene vanished the moment the first player locked in a move.
                # Rebind by NAME, which cannot expire.
                keep = rebind_image(embed, fresh_msg)
                await fresh_msg.edit(embed=embed, attachments=keep)
                
                # Update our state cache so it stops lagging behind
                state['message_obj'] = fresh_msg 

            except Exception as e:
                print(f"DEBUG: Footer update failed: {e}")

    async def process_pvp_turn(self, state):
        """Resolves the double-blind commits, executes the physics, and redraws the UI."""
        print("\n=== DEBUG: process_pvp_turn triggered ===")
        
        p1_id = state['p1_id']
        p2_id = state['p2_id']
        
        # Initialize Pivot Trackers for the turn!
        state['p1_must_pivot'] = False
        state['p2_must_pivot'] = False

        # 🚨 TURN-ORDER TRACKING (Bolt Beak / Fishious Rend)
        # Cleared for every specimen so a switch-in starts the turn "not yet acted".
        for _side in ['p1_team', 'p2_team']:
            for _mon in state.get(_side, []):
                _mon['acted_this_turn'] = False

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
            async with aiosqlite.connect(DB_FILE) as db:
                async with db.cursor() as cursor:
            
                    for pid, commit, active_poke, adp_state in [
                        (p1_id, c1, p1_active, state['p1_adaptation']),
                        (p2_id, c2, p2_active, state['p2_adaptation'])
                    ]:
                        if commit['type'] == 'attack' and commit.get('transform'):
                            form = commit['transform']
                            owner_name = state['p1'].display_name if pid == p1_id else state['p2'].display_name

                            # 🚨 PRIMAL FIREWALL: reject a stale Dynamax commit server-side
                            if form == 'dynamax' and not can_dynamax(active_poke):
                                combat_log += f"⚠️ **{owner_name}'s** {active_poke['name'].capitalize()} channels Primal energy and cannot Dynamax!\n"
                                continue

                            # 1. Create Biological Backup
                            # The transformed form becomes the new baseline
                            clear_base_stat_snapshot(active_poke)

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
                                    async with db.execute("SELECT pokedex_id FROM base_pokemon_species WHERE name = ?", (f"{base_name}-gmax",)) as cursor:
                                        gmax_data = await cursor.fetchone()
                                    
                                    if gmax_data:
                                        active_poke['pokedex_id'] = gmax_data[0] # Update the ID for the visual renderer!
                                        
                                    active_poke['name'] = f"{active_poke['name']} (Gigantamax)"
                                    combat_log += f"🔴 **{owner_name}'s** specimen absorbed Galar particles and Gigantamaxed into **{active_poke['name'].capitalize()}**!\n"
                                else:
                                    active_poke['name'] = f"{active_poke['name']} (Dynamax)"
                                    combat_log += f"🔴 **{owner_name}'s** specimen absorbed Galar particles and Dynamaxed into **{active_poke['name'].capitalize()}**!\n"
                                    
                                adp_state.update({'used': True, 'active': True, 'type': 'dynamax', 'turns': 3,
                                                  'holder': battle_render.adaptation_holder(active_poke)})

                            # 3. Apply Mega Evolution
                            elif form == 'mega':
                                # 🚨 FIX: Clean the base name AND grab the held item!
                                base_name = active_poke['name'].split('-')[0]
                                held_item = active_poke.get('held_item', 'none').lower()
                                
                                # Query ALL mega forms for this species using the LIKE operator
                                async with db.execute("SELECT pokedex_id, name FROM base_pokemon_species WHERE name LIKE ?", (f"{base_name}-mega%",)) as cursor:
                                    mega_forms = await cursor.fetchall()
                                
                                if mega_forms:
                                    # Default fallback to standard mega
                                    form_id, form_name = mega_forms[0] 
                                    
                                    # 🚨 FIX: Route the X, Y, and Z forms based on the held item!
                                    if held_item.endswith('-x'):
                                        target = next((f for f in mega_forms if '-mega-x' in f[1]), mega_forms[0])
                                        form_id, form_name = target
                                    elif held_item.endswith('-y'):
                                        target = next((f for f in mega_forms if '-mega-y' in f[1]), mega_forms[0])
                                        form_id, form_name = target
                                    elif held_item.endswith('-z'):
                                        target = next((f for f in mega_forms if '-mega-z' in f[1]), mega_forms[0])
                                        form_id, form_name = target
                                    
                                    # Fetch new stats and types
                                    async with db.execute("SELECT stat_name, base_value FROM base_pokemon_stats WHERE pokedex_id = ?", (form_id,)) as cursor:
                                        db_stats = {row[0]: row[1] for row in await cursor.fetchall()}

                                    async with db.execute("SELECT type_name FROM base_pokemon_types WHERE pokedex_id = ?", (form_id,)) as cursor:
                                        new_types = [row[0] for row in await cursor.fetchall()]
                                    
                                    # 🧬 PARITY FIX: Fetch the mutated biological ability so it works in PvP!
                                    async with db.execute("SELECT standard_abilities FROM base_pokemon_species WHERE pokedex_id = ?", (form_id,)) as cursor:
                                        ab_data = await cursor.fetchone()
                                    if ab_data and ab_data[0]:
                                        raw_ability = ab_data[0].split(',')[0].strip()
                                        active_poke['ability'] = raw_ability.lower().replace(' ', '-')

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
                                    
                                    adp_state.update({'used': True, 'active': True, 'type': 'mega', 'turns': -1,
                                                      'holder': battle_render.adaptation_holder(active_poke)})
                                    
                                    # 🚨 Dynamic Log Message
                                    transform_type = "Z-Mega Evolved" if held_item.endswith('-z') else "Mega Evolved"
                                    combat_log += f"✨ **{owner_name}'s** specimen achieved Hyper-Adaptation and {transform_type} into **{form_name.replace('-', ' ').title()}**!\n"
                                else:
                                    combat_log += f"⚠️ **{owner_name}'s** {active_poke['name'].capitalize()} tried to Mega Evolve, but its genetic data was missing from the database!\n"


                            # 4. Apply Z-Move Marker
                            elif form == 'zmove':
                                adp_state.update({'used': True, 'active': True, 'type': 'zmove', 'turns': 1,
                                                  'holder': battle_render.adaptation_holder(active_poke)})
                                combat_log += f"💎 **{owner_name}'s** {active_poke['name'].capitalize()} surrounded itself with its Z-Power!\n"

            # ==========================================
            # PHASE 1: TURN ORDER & SPEED RESOLUTION
            # ==========================================
            print("DEBUG: Resolving turn order...")

            # ==========================================
            # 🚨 TEMPORAL OVERRIDE: CHARGING & RAMPAGE
            # Force the locked move data into the player's commit BEFORE speed calculation!
            # ==========================================
            for p_tag, commit, active_poke in [('p1', c1, p1_active), ('p2', c2, p2_active)]:
                if 'volatile_statuses' not in active_poke: active_poke['volatile_statuses'] = {}
                
                is_charging = active_poke['volatile_statuses'].get('charging')
                is_rampage = active_poke['volatile_statuses'].get('rampage')
                
                is_encore = active_poke['volatile_statuses'].get('encore')

                forced_move_name = None
                if is_charging: forced_move_name = is_charging
                elif is_rampage: forced_move_name = is_rampage['move']
                elif is_encore: forced_move_name = is_encore['move']
                
                if forced_move_name:
                    # Look up the forced move in their biological database payload
                    forced_move_data = next((m for m in active_poke['moves'] if m.get('base_name', m['name']) == forced_move_name), None)
                    
                    if forced_move_data:
                        # Overwrite their commit with the forced attack!
                        commit['type'] = 'attack'
                        commit['data'] = forced_move_data
            # ==========================================
            # 🚨 THE PURSUIT INTERCEPTOR & SWAP TRACKER
            p1_is_swapping = c1['type'] == 'swap'
            p2_is_swapping = c2['type'] == 'swap'

            # Tag the biology so calculate_damage knows they are fleeing!
            if p1_is_swapping: p1_active['volatile_statuses']['is_switching'] = True
            if p2_is_swapping: p2_active['volatile_statuses']['is_switching'] = True

            def get_action_priority(commit, opp_swapping, mover):
                if commit['type'] == 'swap':
                    return 6
                if commit['type'] == 'attack':
                    # Pursuit intercepts the swap by jumping to Priority 7!
                    if commit['data']['name'].lower() == 'pursuit' and opp_swapping:
                        return 7

                    # Terrain can shift a bracket (Grassy Glide on Grassy Terrain)
                    return get_effective_priority(
                        commit['data'].get('name'),
                        commit['data'].get('priority', 0),
                        mover,
                        state.get('terrain', {'type': 'none'})['type'],
                        commit['data']
                    )
                return 0
            
            # KINETIC SPEED CHECK (PvP)
            def get_combat_speed(pokemon, has_tailwind=False):
                """Thin wrapper so the two engines share one speed calculation."""
                return battle_speed(
                    pokemon, has_tailwind,
                    weather=state.get('weather', {'type': 'none'})['type'],
                    terrain=state.get('terrain', {'type': 'none'})['type'],
                    magic_room=state.get('field', {}).get('magic_room', 0) > 0)

            # Sucker Punch reads these - see the PvE side for the reasoning
            p1_active['_committed_move'] = (c1.get('data') or {}).get('class') if c1.get('type') == 'attack' else None
            p2_active['_committed_move'] = (c2.get('data') or {}).get('class') if c2.get('type') == 'attack' else None
            # Me First needs the name too, not just the class
            p1_active['_committed_move_name'] = (c1.get('data') or {}).get('base_name') if c1.get('type') == 'attack' else None
            p2_active['_committed_move_name'] = (c2.get('data') or {}).get('base_name') if c2.get('type') == 'attack' else None

            p1_prio = get_action_priority(c1, p2_is_swapping, p1_active)
            p2_prio = get_action_priority(c2, p1_is_swapping, p2_active)

            # Fetch Tailwind Statuses
            p1_has_tailwind = state.get('p1_hazards', {}).get('tailwind', 0) > 0
            p2_has_tailwind = state.get('p2_hazards', {}).get('tailwind', 0) > 0
            
            spd1 = get_combat_speed(p1_active, p1_has_tailwind)
            spd2 = get_combat_speed(p2_active, p2_has_tailwind)
            is_trick_room = state.get('field', {}).get('trick_room', 0) > 0

            # Bracket, then tier inside it (Quick Draw / Stall), then speed - with Trick
            # Room inverting the speed component only. Shared with PvE so the two engines
            # cannot order a turn differently.
            _p1_move = c1.get('data') if c1.get('type') == 'attack' else None
            _p2_move = c2.get('data') if c2.get('type') == 'attack' else None
            key1 = turn_order_key(p1_prio, priority_tier(p1_active, _p1_move), spd1, is_trick_room)
            key2 = turn_order_key(p2_prio, priority_tier(p2_active, _p2_move), spd2, is_trick_room)

            if key1 > key2:
                p1_goes_first = True
            elif key2 > key1:
                p1_goes_first = False
            else:
                p1_goes_first = random.choice([True, False])

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
                #defender = action['opp_active'] 
                
                # Always grab the defender directly from the live state memory!
                defender = state[f"{opp_tag}_team"][state[f"{opp_tag}_active_index"]]

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

                    # ==========================================
                    # 🚨 NEW: PRIMORDIAL WEATHER VOLUNTARY CLEAR
                    # ==========================================
                    weather_cleared_msg = ""
                    if state.get('weather', {}).get('primordial', False):
                        if get_active_ability(attacker) in ['desolate-land', 'primordial-sea', 'delta-stream']:
                            state['weather'] = {'type': 'none', 'duration': 0, 'primordial': False}
                            weather_cleared_msg = f"🌤️ The primordial weather dissipated as {attacker['name'].capitalize()} retreated!\n"
                    # ==========================================
                    
                    # 2. STATE MUTATION: Only update the index if the specimen is alive!
                    # Boosts belong to the slot: flush the outgoing specimen so a Swords
                    # Dance cannot be parked on the bench and brought back.
                    leave_field(attacker)
                    attacker['volatile_statuses'] = {}

                    state[f"{player_tag}_active_index"] = bench_idx
                    
                    combat_log += f"🔄 **{owner_name}** withdrew {attacker['name'].capitalize()} and sent out **{new_active['name'].capitalize()}**!\n"
                    
                    try:
                        hazard_log = apply_entry_hazards(new_active, state[f"{player_tag}_hazards"], TYPE_CHART, f"{owner_name}'s")
                        if hazard_log: combat_log += hazard_log
                    except Exception as e:
                        print(f"DEBUG WARNING: Hazard application failed: {e}")
                    
                    if new_active['current_hp'] > 0:
                        try:
                            combat_log = await trigger_single_entry_ability(new_active, defender, f"{owner_name}'s", state, combat_log)
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

                    # Mark BEFORE resolving, so the faster attacker still sees the target
                    # as "not yet acted" and earns the ambush bonus. A swap does not count.
                    attacker['acted_this_turn'] = True

                    if defender['current_hp'] <= 0:
                        combat_log += f"💥 **{owner_name}'s** {attacker['name'].capitalize()} used **{move['name'].replace('-', ' ').title()}**, but there was no target!\n"
                        
                        # ==========================================
                        # DESTINY BOND RESOLUTION
                        # ==========================================
                        if defender.get('volatile_statuses', {}).get('destiny-bond'):
                            attacker['current_hp'] = 0
                            combat_log += f"👻 **{owner_name}'s** {attacker['name'].capitalize()} took its attacker down with it!\n"
                        
                        continue
                    
                    can_attack = True
                    volatiles = attacker.get('volatile_statuses', {})

                    if 'glaive_rush' in volatiles:
                        del volatiles['glaive_rush']

                    raw_move_name = move.get('base_name', move['name']).lower().replace(' ', '-')

                    # ==========================================
                    # 🚨 REACTIVE STATUS ANOMALY: DESTINY BOND
                    # ==========================================
                    if raw_move_name == 'destiny-bond':
                        if 'volatile_statuses' not in attacker:
                            attacker['volatile_statuses'] = {}
                        attacker['volatile_statuses']['destiny-bond'] = True
                        combat_log += f"👻 {owner_name.strip()} **{attacker['name'].capitalize()}** is hoping to take its attacker down with it!\n"
                        continue

                    # ==========================================
                    # 🚨 THE RECHARGE ENFORCER
                    # ==========================================
                    if volatiles.get('recharging'):
                        combat_log += f"⏳ **{owner_name}'s** {attacker['name'].capitalize()} must recharge!\n"
                        
                        # Clear the tag so they can move normally on the NEXT turn
                        del attacker['volatile_statuses']['recharging']
                        continue # Abort the entire turn right here!

                    # 1. VOLATILE STATUS: CONFUSION CHECK
                    # 💘 Infatuation: half the time it cannot bring itself to attack.
                    if infatuation_holds_it_back(attacker):
                        combat_log += f"💘 **{attacker['name'].capitalize()}** is immobilised by love!\n"
                        can_attack = False
                    elif is_infatuated(attacker):
                        combat_log += f"💘 **{attacker['name'].capitalize()}** is in love with its opponent!\n"

                    if 'confusion' in volatiles:
                        volatiles['confusion'] -= 1
                        if volatiles['confusion'] <= 0:
                            del volatiles['confusion']
                            combat_log += f"💫 **{owner_name}'s** {attacker['name'].capitalize()} snapped out of its confusion!\n"
                        else:
                            combat_log += f"💫 **{owner_name}'s** {attacker['name'].capitalize()} is confused...\n"
                            if random.randint(1, 100) <= 33: 
                                conf_dmg, conf_msg, _, _, _ = calculate_damage(
                                    attacker, attacker, {'name': 'confusion-snap', 'class': 'physical', 'power': 40, 'type': 'typeless'})
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
                            # Early Bird burns through sleep at twice the rate
                            status['duration'] -= (EARLY_BIRD_SLEEP_RATE
                                                   if get_active_ability(attacker) == 'early-bird'
                                                   else 1)
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

                    # Block 18: Truant loafs on alternate turns. Asked LAST of the
                    # incapacity checks, and only if nothing else has already stopped the
                    # specimen - asking ADVANCES the rhythm, so a Slaking that spent this
                    # turn asleep must not also spend its loaf on it. PvP checks flinch
                    # BEFORE status and PvE checks it after, so "last" is a different line
                    # in each; it is the position that matters, not the line number.
                    if can_attack and truancy_holds_it_back(attacker):
                        combat_log += (f"😴 **{owner_name}'s** "
                                       f"{attacker['name'].capitalize()} is loafing about!\n")
                        can_attack = False

                    # If the attacker is stunned by ANY of the above, skip the attack phase!
                    if not can_attack:
                        # 🚨 STOMPING TANTRUM MEMORY: being unable to act at all - paralysis,
                        # sleep, freeze, flinch, or a confusion self-hit - is a failed move.
                        attacker['last_move_failed'] = True
                        continue
                        
                    # Deduct the PP using the base_name!
                    for actual_move in attacker['moves']:
                        if actual_move['name'] == move.get('base_name', move['name']):
                            actual_move['pp'] = max(0, actual_move['pp'] - 1)
                            break

                    # ==========================================
                    # 🚨 THE ATTACK ANNOUNCEMENT & PURSUIT LOGIC
                    # ==========================================
                    # Bind the ACTIVE attacker's adaptation here. Without this, adp_state is
                    # still whatever the transformation loop above left behind (always p2),
                    # so p1's announcements and gimmick checks read the wrong player.
                    adp_state = state[f"{player_tag}_adaptation"]
                    attacker_is_maxed = is_dynamax_active(adp_state)

                    is_status_gimmick = (adp_state['active'] and adp_state['type'] in ['zmove', 'dynamax']) and move.get('class') == 'status'
                    
                    if not is_status_gimmick:
                        if adp_state['active'] and adp_state['type'] == 'zmove':
                            combat_log += f"🌟 **{owner_name}'s** {attacker['name'].capitalize()} unleashed its full-force Z-Move!\n"
                        elif adp_state['active'] and adp_state['type'] == 'dynamax':
                            combat_log += f"🌪️ **{owner_name}'s** {attacker['name'].capitalize()} warped reality with **{move['name'].replace('-', ' ').title()}**!\n"
                        else:
                            combat_log += f"💥 **{owner_name}'s** {attacker['name'].capitalize()} used **{move['name'].replace('-', ' ').title()}**!\n"
                            
                            # 🚨 THE PVP PURSUIT MESSAGE
                            if raw_move_name == 'pursuit' and defender.get('volatile_statuses', {}).get('is_switching'):
                                combat_log += f"⚔️ {defender['name'].capitalize()} is trying to retreat, but was brutally Pursued by {attacker['name'].capitalize()}!\n"
                    # ==========================================
                    
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
                                            elif move['name'] in ['G-Max Wildfire', 'G-Max Vine Lash', 'G-Max Cannonade', 'G-Max Volcalith']:
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

                    # ==========================================
                    # 🪞 REDIRECTION: Magic Coat and Snatch
                    # ==========================================
                    if magic_coat_bounces(defender, move):
                        defender['volatile_statuses'].pop('magic_coat', None)
                        combat_log += (f"\U0001fa9e **{defender['name'].capitalize()}** bounced back "
                                       f"the {raw_move_name.replace('-', ' ').title()}!\n")
                        attacker, defender = defender, attacker

                    elif snatch_steals(defender, move):
                        defender['volatile_statuses'].pop('snatch', None)
                        combat_log += (f"\U0001f91a **{defender['name'].capitalize()}** snatched the "
                                       f"{raw_move_name.replace('-', ' ').title()}!\n")
                        attacker, defender = defender, attacker

                    # ==========================================
                    # 🎭 COPY MOVES: perform something else entirely
                    # ==========================================
                    if raw_move_name in COPY_MOVES:
                        chosen, why = resolve_copied_move(
                            raw_move_name, attacker, defender,
                            party=state[f"{player_tag}_team"],
                            last_move_overall=state.get('last_move_overall'),
                            pool=METRONOME_POOL)

                        if not chosen:
                            combat_log += f"⚠️ {why}\n"
                            continue

                        copied_stats = await fetch_move_payload(chosen)
                        if not copied_stats:
                            combat_log += "⚠️ But it failed! The copied move fizzled out!\n"
                            continue

                        if raw_move_name == 'me-first':
                            copied_stats['power'] = math.floor(copied_stats['power'] * ME_FIRST_MULTIPLIER)

                        combat_log += f"🎭 It became **{chosen.replace('-', ' ').title()}**!\n"
                        raw_move_name = chosen
                        move = copied_stats

                    # ==========================================
                    # 🚨 TWO-TURN CHARGING & INVULNERABILITY LOGIC (PvP)
                    # ==========================================

                    raw_move_name = move.get('base_name', move['name']).lower().replace(' ', '-')
                    is_currently_charging = attacker.get('volatile_statuses', {}).get('charging') == raw_move_name
                    held_item_check = get_active_item(attacker, state.get('field', {}).get('magic_room', 0) > 0)

                    if raw_move_name in TWO_TURN_MOVES and not is_currently_charging:
                        charge_data = TWO_TURN_MOVES[raw_move_name]
                        # Block 22: the sky the THROWER reads, exactly as PvE does.
                        current_weather = personal_weather(
                            attacker, state.get('weather', {'type': 'none'})['type'])

                        # 1. Biological Bypasses (Max Moves, Harsh Sunlight & Power Herbs)
                        if attacker_is_maxed:
                            # Dynamaxed specimens fire Max Moves, which never charge
                            combat_log += f"🌪️ **{owner_name}'s** {attacker['name'].capitalize()} unleashed the attack instantly through its Max form!\n"
                        elif current_weather in charge_data.get('skip_weather', []):
                            pass # Skip the charge turn and fire immediately!
                        elif held_item_check == 'power-herb':
                            combat_log += f"🌿 **{owner_name}'s** {attacker['name'].capitalize()} became fully charged due to its Power Herb!\n"
                            mark_item_consumed(attacker, held_item_check)
                            attacker['held_item'] = 'none'
                        else:
                            # 2. Lock in the Charge state!
                            begin_charge(attacker, raw_move_name, charge_data.get('invuln'))
                            combat_log += f"⏳ **{owner_name}'s** {attacker['name'].capitalize()} {charge_data['msg']}\n"
                            
                            # 3. Apply Turn-1 Stat Boosts
                            if 'boost' in charge_data:
                                stat_name, amt = charge_data['boost']
                                if 'stat_stages' not in attacker: attacker['stat_stages'] = {'attack': 0, 'defense': 0, 'sp_atk': 0, 'sp_def': 0, 'speed': 0}
                                attacker['stat_stages'][stat_name] = min(6, attacker['stat_stages'].get(stat_name, 0) + amt)
                                combat_log += f"📈 **{owner_name}'s** {attacker['name'].capitalize()}'s {stat_name.replace('_', ' ')} rose!\n"
                                
                            # (Semi-invulnerability for Dig / Fly is applied by begin_charge)

                            # 🚨 ABORT THE REST OF THE TURN!
                            continue 
                            
                    # ==========================================
                    # 🚨 DELAYED STRIKES (Future Sight / Doom Desire) - PvP
                    # ==========================================
                    if raw_move_name == 'encore':
                        victim_volatiles = defender.setdefault('volatile_statuses', {})
                        copied = defender.get('last_move_used')

                        if victim_volatiles.get('encore'):
                            combat_log += f"⚠️ But it failed! **{opp_name}'s** {defender['name'].capitalize()} is already encored!\n"
                        elif not copied or copied in ENCORE_IMMUNE_MOVES:
                            combat_log += "⚠️ But it failed! There was no performance to repeat!\n"
                        else:
                            victim_volatiles['encore'] = {'move': copied, 'turns': 3}
                            combat_log += f"👏 **{opp_name}'s** {defender['name'].capitalize()} received an encore and must repeat **{copied.replace('-', ' ').title()}**!\n"
                        continue

                    if raw_move_name == 'wish':
                        wish_slot = f"{player_tag}_wish"
                        if state.get(wish_slot):
                            combat_log += "⚠️ But it failed! A wish is already pending!\n"
                        else:
                            state[wish_slot] = snapshot_wish(attacker)
                            combat_log += f"⭐ **{owner_name}'s** {attacker['name'].capitalize()} made a wish!\n"
                        continue

                    if raw_move_name in DELAYED_ATTACK_MOVES:
                        target_slot = f"{opp_tag}_future"

                        if state.get(target_slot):
                            combat_log += f"⚠️ But it failed! A strike is already converging on **{opp_name}'s** side!\n"
                        else:
                            state[target_slot] = snapshot_delayed_attack(raw_move_name, attacker, move, owner_name)
                            combat_log += f"🔮 **{owner_name}'s** {attacker['name'].capitalize()} foresaw an attack against **{opp_name}**!\n"
                        continue

                    # If we reach this point and THEY WERE CHARGING, clear the tags so the attack can land!
                    if is_currently_charging:
                        end_charge(attacker)
                        # ==========================================
                        
                        # ==========================================
                        # 🚨 ACCURACY, EVASION, & OHKO BYPASS
                        # ==========================================
                        is_ohko = raw_move_name in OHKO_MOVES and not attacker_is_maxed

                        # Shared with the physics engine so the two copies cannot drift
                        # A standing Lock-On is spent here and guarantees this one attack
                        is_guaranteed = (raw_move_name in GUARANTEED_HIT_MOVES
                                         or consume_lock_on(attacker))

                        # Safely fetch abilities
                        atk_ability = get_active_ability(attacker)
                        def_ability = get_active_ability(defender)
                        has_no_guard = (atk_ability == 'no-guard' or def_ability == 'no-guard')
                        target_is_vulnerable = defender.get('volatile_statuses', {}).get('glaive_rush')
                        
                        move_acc = move.get('accuracy', 0)
                        if not isinstance(move_acc, int): move_acc = 100 

                        if not is_ohko and not has_no_guard and not target_is_vulnerable and not is_guaranteed:
                            
                            # Stages, the accuracy and evasion abilities, and Wonder Skin
                            # all live in one shared function so the two engines' copies
                            # of this cannot drift apart.
                            final_acc = hit_chance(
                                attacker, defender, move_stats,
                                weather=state.get('weather', {'type': 'none'})['type'])

                            # 3. Roll the dice!
                            if random.uniform(0, 100) > final_acc:
                                combat_log += "💨 The attack missed!\n"

                                # 🚨 STOMPING TANTRUM MEMORY: a whiff counts as a failure
                                attacker['last_move_failed'] = True

                                # Blunder Policy answers an ACCURACY miss, which is
                                # precisely what this branch is - a protect, an immunity
                                # or a failed status move is not a blunder.
                                combat_log += blunder_policy_on_miss(attacker)

                                # 🚨 CRASH DAMAGE (Miss)
                                if raw_move_name in ['jump-kick', 'high-jump-kick']:
                                    crash_dmg = max(1, math.floor(attacker.get('max_hp', 100) / 2))
                                    attacker['current_hp'] = max(0, attacker['current_hp'] - crash_dmg)
                                    combat_log += f"💥 {attacker['name'].capitalize()} kept going and crashed! (-{crash_dmg} HP)\n"

                                # If a Rampage move misses, the rampage is disrupted!
                                if 'rampage' in attacker.get('volatile_statuses', {}):
                                    del attacker['volatile_statuses']['rampage']
                                continue

                    # 🚨 LAST RESPECTS TALLY: refresh the attacker's casualty count so the
                    # physics engine can price the move without needing team access.
                    own_team = state[f"{player_tag}_team"]
                    attacker['fainted_allies'] = sum(1 for p in own_team if p['current_hp'] <= 0)

                    print(f"DEBUG: Firing Physics Engine. Attacker: {attacker['name']} | Defender: {defender['name']} | Move Data: {move}")
                    dmg, msg, status, stat_changes, heal = calculate_damage(
                        attacker, defender, move, 
                        weather=state['weather']['type'], 
                        target_hazards=state[f"{opp_tag}_hazards"],
                        user_hazards=state[f"{player_tag}_hazards"],
                        user_party=state[f"{player_tag}_team"],
                        terrain=state.get('terrain', {'type': 'none'})['type'],
                        wonder_room=state.get('field', {}).get('wonder_room', 0) > 0,
                        gravity=state.get('field', {}).get('gravity', 0) > 0,
                        magic_room=state.get('field', {}).get('magic_room', 0) > 0,
                                    field=field_of(state)
                    )

                    print(f"DEBUG: Result -> Dmg: {dmg}, Heal: {heal}, Stat Chgs: {stat_changes}")
                    
                    # Apply HP modifications
                    defender['current_hp'] = max(0, defender['current_hp'] - dmg)

                    # ==========================================
                    # 🚨 RAMPAGE MOVES (Outrage, Petal Dance, Thrash)
                    # ==========================================
                    # As in PvE: a Max move does not lock the user into a rampage.
                    if raw_move_name in RAMPAGE_MOVES and not attacker_is_maxed:
                        if dmg > 0: # The attack successfully landed!
                            if 'rampage' not in attacker['volatile_statuses']:
                                # Start the rampage (Locks in for 2 to 3 turns)
                                attacker['volatile_statuses']['rampage'] = {
                                        'move': raw_move_name,
                                        # Uproar is a fixed 3 attacks; the others roll 2-3
                                        'turns': 2 if raw_move_name in UPROAR_MOVES else random.randint(1, 2)
                                    }
                            else:
                                # Decrement the rampage timer
                                attacker['volatile_statuses']['rampage']['turns'] -= 1
                                if attacker['volatile_statuses']['rampage']['turns'] <= 0:
                                    del attacker['volatile_statuses']['rampage']
                                    
                                    # Rampage ends, apply confusion! (Own Tempo grants immunity)
                                    atk_ability = get_active_ability(attacker)
                                    if atk_ability != 'own-tempo' and raw_move_name not in LOCK_IN_NO_FATIGUE:
                                        attacker['volatile_statuses']['confusion'] = random.randint(2, 5)
                                        combat_log += f"💫 {owner_name.strip()} **{attacker['name'].capitalize()}** became confused due to fatigue!\n"
                        else:
                            # If the rampage dealt 0 damage (Protect, Immunity, Faint), it is disrupted!
                            if 'rampage' in attacker.get('volatile_statuses', {}):
                                del attacker['volatile_statuses']['rampage']

                    # ==========================================
                    # DAMAGE MEMORY (For Retaliation Moves)
                    # ==========================================
                    if dmg > 0:
                        defender['last_damage_taken'] = dmg
                        defender['last_damage_class'] = move.get('class', 'physical')
                        # A biding target banks whatever it just absorbed
                        store_bide_damage(defender, dmg)

                        # 🚨 RAGE FIST TALLY: counts individual strikes, and rides on the
                        # specimen across switches
                        defender['times_hit'] = defender.get('times_hit', 0) + defender.get('last_hit_count', 1)

                    # 🚨 STOMPING TANTRUM MEMORY
                    # A damaging move that connected for nothing (immunity, Protect, a
                    # failed condition) counts as a failure; anything else resets the flag.
                    if move.get('class') != 'status' and dmg <= 0:
                        attacker['last_move_failed'] = True
                    else:
                        attacker['last_move_failed'] = False

                    # Encore copies whatever actually resolved here; Conversion 2
                    # reads the element off it.
                    attacker['last_move_used'] = raw_move_name
                    attacker['last_move_type'] = move.get('type')
                    # A sacrifice move banks its wish against the SIDE, so whoever
                    # fills the vacated slot collects it - see trigger_single_entry_ability.
                    if '_sacrifice_wish' in attacker:
                        _side = side_of(state, attacker)
                        if _side is not None:
                            state[f"{_side}_sacrifice"] = attacker.pop('_sacrifice_wish')

                    state['last_move_overall'] = raw_move_name   # Copycat reads this
                    # ==========================================

                    # --- STRUGGLE RECOIL INTERCEPTOR ---
                    if raw_move_name == 'struggle':
                        recoil_dmg = apply_struggle_recoil(attacker)
                        combat_log += f"💥 **{attacker['name'].capitalize()}** took recoil damage from thrashing about! (-{recoil_dmg} HP)\n"

                    if heal > 0:
                        attacker['current_hp'] = min(attacker.get('max_hp', 100), attacker['current_hp'] + heal)
                       
                    # Grudge: if that blow was the one that finished the target, the move
                    # that did it loses every last PP.
                    if defender['current_hp'] <= 0:
                        grudge_log = apply_grudge(defender, attacker)
                        combat_log += apply_faint_recoil(defender, attacker)
                        # Block 17: the killer collects, and anything still standing
                        # answers the fall.
                        combat_log += apply_knockout_reactions(defender, attacker,
                                                               attacker)
                        if grudge_log:
                            combat_log += grudge_log.strip() + "\n"

                    # Print out the damage and physics engine messages!
                    if msg: combat_log += f"↳ {msg}\n"
                    if dmg > 0: combat_log += f"↳ Dealt **{dmg}** damage.\n"
                    
                    # Check if the damage pushed them below the berry threshold!
                    berry_log = check_consumables(defender, f"{opp_name}'s", state.get('field', {}).get('magic_room', 0) > 0, attacker)
                    if berry_log: combat_log += berry_log

                    # Apply Stat Changes (Swords Dance, Max Strike speed drop, etc.)
                    # PvP kept its own copy of this loop, which had drifted: it knew only
                    # about real stages, so the volatiles the physics engine smuggles
                    # through this channel - Leech Seed and Perish Song - were dropped on
                    # the floor here. The shared helper handles both, and brings Block 8's
                    # stage protection with it.
                    combat_log += apply_stat_changes(attacker, defender, stat_changes,
                                                     prefix="↳ ", state=state)
                    combat_log += await resolve_form_flips(attacker, defender)

                    if status and  status != 'none':
                        defender['status_condition'] = {'name': status, 'duration': -1}
                        combat_log += f"↳ **{opp_name}'s** {defender['name'].capitalize()} was afflicted with {status}!\n"

                    # Only apply the exhaustion tag if the attack actually dealt damage,
                    # and never while Dynamaxed - Max Moves leave no recharge window.
                    if raw_move_name in RECHARGE_MOVES and dmg > 0 and not attacker_is_maxed:
                        if 'volatile_statuses' not in attacker:
                            attacker['volatile_statuses'] = {}
                        attacker['volatile_statuses']['recharging'] = True

                    # ==========================================
                    # SYNCHRONOUS PIVOT OVERRIDE (PvP)
                    # ==========================================
                    # Ensure the attacker survived recoil/helmets and actually dealt damage (or used a status pivot)
                    # As in PvE: a Max move keeps none of the base move's secondary
                    # effects, so U-turn thrown as Max Strike hits and stays put.
                    if raw_move_name in pivot_moves and not attacker_is_maxed and attacker['current_hp'] > 0 and (dmg > 0 or move.get('class') == 'status'):
                        
                        # Verify they actually have a living bench specimen to swap into!
                        active_idx = state[f"{player_tag}_active_index"]
                        has_bench = any(i != active_idx and p['current_hp'] > 0 for i, p in enumerate(state[f"{player_tag}_team"]))
                        
                        if has_bench:
                            # Biologically flush the outgoing specimen's stat mutations.
                            # Baton Pass is exempt because it hands them to the replacement.
                            if raw_move_name != 'baton-pass':
                                leave_field(attacker)
                                attacker['volatile_statuses'] = {}
                                
                            combat_log += f"💨 {owner_name}'s **{attacker['name'].capitalize()}** retreated to the bench!\n"

                            # ==========================================
                            # 🚨 PAUSE THE ENGINE: WAIT FOR USER INPUT
                            # ==========================================
                            # 1. Update the main channel so both players know the engine is waiting
                            embed = discord.Embed(title="⚠️ Mid-Turn Substitution!", description=f"{combat_log}\nWaiting for {owner_name} to deploy a replacement...", color=discord.Color.orange())
                            await state['message_obj'].edit(embed=embed, attachments=[], view=None)
                            
                            # 2. Spawn the menu and send it to the specific player's DMs!
                            player_id_to_ping = state[f"{player_tag}_id"]
                            swap_view = MidTurnSwapMenu(self, state, player_id_to_ping)
                            
                            # Ping the user directly (identical to your faint_swap logic)
                            await state[player_tag].send(f"⚠️ **{attacker['name'].capitalize()}** is pivoting out! Select a replacement quickly:", view=swap_view)
                            
                            # 3. 🛑 FREEZE THE THREAD UNTIL THEY CLICK A BUTTON IN THEIR DMS
                            await swap_view.swap_event.wait()
                            
                            # 4. 🟢 RESUME! Grab the index they selected and mutate the state
                            new_idx = swap_view.selected_index
                            state[f"{player_tag}_active_index"] = new_idx
                            new_active = state[f"{player_tag}_team"][new_idx]

                            # 🚨 BATON PASS: hand the built-up state to the replacement
                            if raw_move_name == 'baton-pass':
                                baton_pass_state(attacker, new_active)
                                combat_log += f"🎽 **{attacker['name'].capitalize()}** passed the baton!\n"

                            combat_log += f"\n{owner_name} sent out **{new_active['name'].capitalize()}**!\n"
                            
                            # 5. Trigger Entry Hazards / Abilities for the new arrival!
                            try:
                                combat_log = await trigger_single_entry_ability(new_active, defender, f"{owner_name}'s", state, combat_log)
                                hazard_log = apply_entry_hazards(new_active, state[f"{player_tag}_hazards"], TYPE_CHART, f"{owner_name}'s")
                                if hazard_log: combat_log += hazard_log
                            except Exception as e:
                                print(f"DEBUG: PvP Mid-Turn Entry Hook Failed: {e}")
                    
                    # ==========================================
                    #  PHAZING ANOMALIES (Forced Swaps)
                    # ==========================================
                    # Ensure the move successfully executed (either dealing damage or landing a status)
                    # As in PvE: Dragon Tail thrown as Max Wyrmwind drags nobody out.
                    _is_phazing = (raw_move_name in phaze_moves and not attacker_is_maxed
                          and defender['current_hp'] > 0
                          and (dmg > 0 or move.get('class') == 'status'))
                    # Suction Cups and Guard Dog plant themselves. Answered before the bench
                    # search so the refusal is reported for the right reason - "it failed,
                    # no bench" would be a different and wrong explanation.
                    if _is_phazing and resists_forced_switch(defender):
                        combat_log += (f"🦶 **{defender['name'].capitalize()}**'s "
                                       f"{pretty_ability(get_active_ability(defender))} "
                                       f"kept it rooted to the spot!\n")
                    elif _is_phazing:
                        
                        # 1. Find valid benched targets for the DEFENDER
                        opp_active_idx = state[f"{opp_tag}_active_index"]
                        opp_bench = [i for i, p in enumerate(state[f"{opp_tag}_team"]) if p['current_hp'] > 0 and i != opp_active_idx]
                        
                        if opp_bench:
                            # 2. Randomly select a victim and force the state mutation
                            forced_idx = random.choice(opp_bench)
                            state[f"{opp_tag}_active_index"] = forced_idx
                            forced_in_poke = state[f"{opp_tag}_team"][forced_idx]
                            
                            # Biologically flush the outgoing specimen's stat mutations
                            leave_field(defender)
                            defender['volatile_statuses'] = {}
                            
                            combat_log += f"🌪️ **{opp_name}'s** {defender['name'].capitalize()} was forced out of the battlefield!\n"
                            combat_log += f"↳ **{opp_name}** was dragged into the fight with **{forced_in_poke['name'].capitalize()}**!\n"
                            
                            # 3. Trigger Entry Hazards / Abilities for the dragged-in Pokémon!
                            try:
                                combat_log = await trigger_single_entry_ability(forced_in_poke, attacker, f"{opp_name}'s", state, combat_log)
                                hazard_log = apply_entry_hazards(forced_in_poke, state[f"{opp_tag}_hazards"], TYPE_CHART, f"{opp_name}'s")
                                if hazard_log: combat_log += hazard_log
                            except Exception as e:
                                print(f"DEBUG: Phaze Entry Hook Failed: {e}")
                                
                            # 4. 🚨 CRITICAL: UPDATE THE POINTERS FOR ANY REMAINING ACTIONS
                            defender = forced_in_poke
                            
                            for other_action in execution_queue:
                                if other_action['player'] == opp_tag:
                                    other_action['active'] = forced_in_poke
                                else:
                                    other_action['opp_active'] = forced_in_poke
                                    
                        else:
                            combat_log += "↳ But it failed! The target has no benched Pokémon to drag out!\n"
                    # ==========================================
                    
                    # ==========================================
                    # ==========================================
                    # CLIMATOLOGICAL OVERRIDES (Weather Moves) PvP
                    # ==========================================
                    effective_move_name = move.get('base_name', move['name'])
                    magic_room_on = state.get('field', {}).get('magic_room', 0) > 0

                    combat_log += deploy_weather(state, effective_move_name, attacker, magic_room_on)

                    if defender['current_hp'] <= 0:
                        combat_log += f"💀 **{opp_name}'s** {defender['name'].capitalize()} fainted!\n\n"
                    
                    # ==========================================
                    # TERRAIN DEPLOYMENT
                    # ==========================================
                    combat_log += deploy_terrain(
                        state, effective_move_name, attacker, magic_room_on,
                        max_move_type=move.get('type') if (adp_state['active'] and is_max_move) else None,
                        standing=(attacker, defender))
            
                    # ==========================================
                    # 🚨 FIELD STATE DEPLOYMENT
                    # ==========================================
                    combat_log += deploy_field_toggle(
                        state, raw_move_name, attacker, defender,
                        state['p1_hazards'] if player_tag == 'p1' else state['p2_hazards'],
                        team_label=owner_name)

            # ==========================================
            # PHASE 3: POST-TURN ENVIRONMENTAL DAMAGE & CLEANUP (PvP)
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

            # ==========================================
            # 🚨 LOCK-IN UPKEEP (Encore decay / Uproar insomnia) - PvP
            # ==========================================
            for mon, _opp, owner_str in combatants:
                enc = (mon.get('volatile_statuses') or {}).get('encore')
                if enc:
                    enc['turns'] -= 1
                    if enc['turns'] <= 0:
                        del mon['volatile_statuses']['encore']
                        combat_log += f"👏 {owner_str} **{mon['name'].capitalize()}**'s encore ended!\n"

                dis = (mon.get('volatile_statuses') or {}).get('disable')
                if dis:
                    dis['turns'] -= 1
                    if dis['turns'] <= 0:
                        del mon['volatile_statuses']['disable']
                        combat_log += f"🔓 {owner_str} **{mon['name'].capitalize()}** is no longer disabled!\n"

                if (mon.get('volatile_statuses') or {}).get('taunt'):
                    mon['volatile_statuses']['taunt'] -= 1
                    if mon['volatile_statuses']['taunt'] <= 0:
                        del mon['volatile_statuses']['taunt']
                        combat_log += f"😌 {owner_str} **{mon['name'].capitalize()}**'s taunt wore off!\n"

            # An active Uproar jolts anything already asleep back awake
            if is_uproar_active(new_p1_active, new_p2_active):
                for mon, _opp, owner_str in combatants:
                    status = mon.get('status_condition') or {}
                    if status.get('name') == 'sleep':
                        mon['status_condition'] = None
                        combat_log += f"📢 {owner_str} **{mon['name'].capitalize()}** was jolted awake by the uproar!\n"

            # ==========================================
            # 🚨 DELAYED STRIKES LANDING (Future Sight / Doom Desire) - PvP
            # ==========================================
            # Resolved against whoever currently holds the slot, which may not be the
            # specimen that was targeted when the strike was queued.
            for slot_tag, victim in [('p1', new_p1_active), ('p2', new_p2_active)]:
                pending = state.get(f"{slot_tag}_future")
                if not pending:
                    continue

                # Skip the tick on the turn it was queued so two full turns elapse
                if pending.get('just_queued'):
                    pending['just_queued'] = False
                    continue

                pending['turns'] -= 1
                if pending['turns'] > 0:
                    continue

                state[f"{slot_tag}_future"] = None
                if victim['current_hp'] <= 0:
                    continue

                strike_dmg, strike_msg = resolve_delayed_strike(
                    pending, victim,
                    weather=state['weather']['type'],
                    terrain=state.get('terrain', {'type': 'none'})['type']
                )
                victim['current_hp'] = max(0, victim['current_hp'] - strike_dmg)

                combat_log += f"🔮 **{victim['name'].capitalize()}** took the {pending['move'].replace('-', ' ').title()} attack! (-{strike_dmg} HP)\n"
                if strike_msg:
                    combat_log += f"↳ {strike_msg}\n"

            # ==========================================
            # 🚨 WISHES COMING TRUE - PvP
            # ==========================================
            # Banked on the wisher, paid out to whoever holds the slot a turn later, so a
            # Wish passed to a switch-in heals the replacement rather than the wisher.
            for wish_tag, patient in [('p1', new_p1_active), ('p2', new_p2_active)]:
                pending_wish = state.get(f"{wish_tag}_wish")
                if not pending_wish:
                    continue

                # Skip the tick on the turn it was made so a full turn elapses
                if pending_wish.get('just_queued'):
                    pending_wish['just_queued'] = False
                    continue

                pending_wish['turns'] -= 1
                if pending_wish['turns'] > 0:
                    continue

                state[f"{wish_tag}_wish"] = None
                _, wish_msg = resolve_wish(pending_wish, patient)
                if wish_msg:
                    combat_log += wish_msg + "\n"

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
                                
                                chip_weather = state['weather']['type']
                                if state['weather']['type'] == 'sand' and any(t in ['rock', 'ground', 'steel'] for t in c_types):
                                    is_immune = True
                                if state['weather']['type'] == 'hail' and 'ice' in c_types:
                                    is_immune = True
                                # Sand Force, Sand Veil and Snow Cloak each weather their
                                # OWN storm - a Sand Veil is no help in hail.
                                if shrugs_off_weather(get_active_ability(combatant), chip_weather):
                                    is_immune = True


                                if not is_immune:
                                    chip_dmg = max(1, math.floor(combatant['max_hp'] / 16))
                                    combatant['current_hp'] = max(0, combatant['current_hp'] - chip_dmg)
                                    icon = "🌪️" if state['weather']['type'] == 'sand' else "❄️"
                                    combat_log += f"{icon} {owner_str} **{combatant['name'].capitalize()}** is buffeted by the {state['weather']['type']}! (-{chip_dmg} HP)\n"
                    # Dry Skin Atmospheric Reactions
                    for combatant, _, owner_str in combatants: # Remove the '_' in PvE!
                        if combatant['current_hp'] > 0 and get_active_ability(combatant) == 'dry-skin':
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

            # 1.5 Global Biome Effects (Terrains)
            if 'terrain' not in state: state['terrain'] = {'type': 'none', 'duration': 0}
            
            if state['terrain']['type'] != 'none':
                state['terrain']['duration'] -= 1
                if state['terrain']['duration'] <= 0:
                    terrain_clear_msgs = {
                        'electric': "The electricity disappeared from the battlefield.",
                        'grassy': "The grass disappeared from the battlefield.",
                        'misty': "The mist disappeared from the battlefield.",
                        'psychic': "The weirdness disappeared from the battlefield."
                    }
                    combat_log += f"✨ {terrain_clear_msgs.get(state['terrain']['type'])}\n"
                    state['terrain']['type'] = 'none'
                else:
                    # Grassy Terrain Healing!
                    if state['terrain']['type'] == 'grassy':
                        # (Note: Use `for combatant, _, owner_str in combatants:` in PvP)
                        for combatant, _, owner_str in combatants: 
                            if combatant['current_hp'] > 0 and combatant['current_hp'] < combatant.get('max_hp', 100) and is_grounded(combatant):
                                heal = max(1, math.floor(combatant.get('max_hp', 100) / 16))
                                combatant['current_hp'] = min(combatant.get('max_hp', 100), combatant['current_hp'] + heal)
                                combat_log += f"🌿 {owner_str.strip()} **{combatant['name'].capitalize()}** had its HP restored by the Grassy Terrain! (+{heal} HP)\n"
            
            # 🚨 FIELD STATE DECAY
            if 'field' in state:
                # The sports and the deluge are added to the field only when used, so
                # these are read with .get rather than indexed - the dictionary is built
                # with the four rooms alone.
                for field_state in ['trick_room', 'wonder_room', 'gravity', 'magic_room',
                                    'mud_sport', 'water_sport', 'ion_deluge']:
                    if state['field'].get(field_state, 0) > 0:
                        state['field'][field_state] -= 1
                        if state['field'][field_state] == 0:
                            msgs = {
                                'trick_room': "The twisted dimensions returned to normal!",
                                'wonder_room': "Wonder Room wore off, and stats returned to normal!",
                                'gravity': "Gravity returned to normal!",
                                'magic_room': "Magic Room wore off, and held items regained their power!",
                                'mud_sport': "The mud washed away, and Electric moves regained their power!",
                                'water_sport': "The water dried up, and Fire moves regained their power!",
                                'ion_deluge': "The ion deluge cleared, and Normal moves stayed Normal!"
                            }
                            combat_log += f"✨ {msgs[field_state]}\n"
                            
            # 🚨 TAILWIND DECAY
            for hazards, owner_str in [(state['p1_hazards'], f"{state['p1'].display_name}'s"), (state['p2_hazards'], f"{state['p2'].display_name}'s")]:
                if hazards.get('tailwind', 0) > 0:
                    hazards['tailwind'] -= 1
                    if hazards['tailwind'] <= 0:
                        del hazards['tailwind']
                        combat_log += f"✨ {owner_str} team's Tailwind petered out!\n"

            # ==========================================
            # 1.5 PERSISTENT HELD ITEMS (Status Orbs)
            # ==========================================
            for combatant, _, owner_str in combatants: # Use just 'combatant, owner_str' in PvE!
                if combatant['current_hp'] > 0 and not combatant.get('status_condition'):
                    orb_item = get_active_item(combatant, state.get('field', {}).get('magic_room', 0) > 0)
                    
                    if orb_item == 'flame-orb' and 'fire' not in combatant.get('types', []):
                        combatant['status_condition'] = {'name': 'burn', 'duration': -1}
                        combat_log += f"🔥 {owner_str} **{combatant['name'].capitalize()}** was burned by its Flame Orb!\n"
                        
                    elif orb_item == 'toxic-orb' and 'poison' not in combatant.get('types', []) and 'steel' not in combatant.get('types', []):
                        combatant['status_condition'] = {'name': 'poison', 'duration': -1}
                        combat_log += f"☣️ {owner_str} **{combatant['name'].capitalize()}** was badly poisoned by its Toxic Orb!\n"

            # 2. Pathogen Damage (Burn/Poison)
            for combatant, _, owner_str in combatants:
                ability = get_active_ability(combatant)
                if combatant['current_hp'] > 0 and combatant.get('status_condition'):
                    status_name = combatant['status_condition']['name']
                    if status_name == 'burn':
                        burn_divisor = 32 if ability in BURN_TOLL_HALVED_BY else 16
                        burn_dmg = max(1, math.floor(combatant['max_hp'] / burn_divisor))
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
            for combatant, _, owner_str in combatants:
                if combatant['current_hp'] > 0:
                    item = get_active_item(combatant, state.get('field', {}).get('magic_room', 0) > 0)
                    max_hp = combatant.get('max_hp', 100)
                    
                    if item == 'leftovers':
                        # 🚨 FIX: Only trigger if they are missing HP!
                        if combatant['current_hp'] < max_hp:
                            heal_qty = max(1, math.floor(max_hp / 16))
                            combatant['current_hp'] = min(max_hp, combatant['current_hp'] + heal_qty)
                            combat_log += f"🍎 **{owner_str} {combatant['name'].capitalize()}** restored a little HP using its Leftovers! (+{heal_qty})\n"
                            
                    elif item == 'black-sludge':
                        if 'poison' in combatant.get('types', []):
                            # 🚨 FIX: Only heal Poison types if they are missing HP!
                            if combatant['current_hp'] < max_hp:
                                heal_qty = max(1, math.floor(max_hp / 16))
                                combatant['current_hp'] = min(max_hp, combatant['current_hp'] + heal_qty)
                                combat_log += f"🧪 **{owner_str} {combatant['name'].capitalize()}** restored HP via its Black Sludge! (+{heal_qty})\n"
                        else:
                            sludge_dmg = max(1, math.floor(max_hp / 8))
                            combatant['current_hp'] = max(0, combatant['current_hp'] - sludge_dmg)
                            combat_log += f"🧪 **{owner_str} {combatant['name'].capitalize()}** is buffeted by its Black Sludge! (-{sludge_dmg})\n"


            # ==========================================
            # 2.8 BIOLOGICAL END-OF-TURN HOOKS 
            # ==========================================
            # The middle slot is the opponent: Bad Dreams is the one trait here that
            # reaches across the field rather than acting on its own owner.
            for combatant, foe, owner_str in combatants:
                if combatant['current_hp'] > 0:
                    ability = get_active_ability(combatant)
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

                        # Solar Power's price for the Sp. Atk it grants
                        elif eot_trait['type'] == 'weather_toll':
                            current_weather = state.get('weather', {}).get('type', 'none')
                            if current_weather in eot_trait['weather']:
                                toll = max(1, math.floor(combatant.get('max_hp', 100) / eot_trait['denominator']))
                                combatant['current_hp'] = max(0, combatant['current_hp'] - toll)
                                combat_log += f"☀️ {owner_str.strip()} **{combatant['name'].capitalize()}** was scorched by its {ability_name}! (-{toll} HP)\n"

                        # Weather-gated cure (Hydration) - Shed Skin's certain cousin
                        elif eot_trait['type'] == 'weather_cure':
                            current_weather = state.get('weather', {}).get('type', 'none')
                            if current_weather in eot_trait['weather'] and combatant.get('status_condition'):
                                washed = combatant['status_condition']['name']
                                combatant['status_condition'] = None
                                combat_log += f"💧 {owner_str.strip()} **{combatant['name'].capitalize()}** washed away its {washed} with {ability_name}!\n"

                        # Bad Dreams - aimed at the OPPONENT, and only while it sleeps
                        elif eot_trait['type'] == 'sleep_drain':
                            # Comatose counts as asleep here - it is a sleep its owner
                            # walks around in, and Bad Dreams asks about the sleeping
                            # rather than about the motionless.
                            if foe and foe['current_hp'] > 0 and is_effectively_asleep(foe):
                                bite = max(1, math.floor(foe.get('max_hp', 100) / eot_trait['denominator']))
                                foe['current_hp'] = max(0, foe['current_hp'] - bite)
                                combat_log += f"😈 **{foe['name'].capitalize()}** is tormented by {combatant['name'].capitalize()}'s {ability_name}! (-{bite} HP)\n"

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

                # MULTI-HIT TRAP DAMAGE
                # One more turn survived out here, which is what disarms Fake Out
                if combatant['current_hp'] > 0:
                    combatant['turns_on_field'] = combatant.get('turns_on_field', 0) + 1

                if combatant['current_hp'] > 0 and combatant.get('volatile_statuses', {}).get('fairy_lock'):
                    combatant['volatile_statuses']['fairy_lock'] -= 1
                    if combatant['volatile_statuses']['fairy_lock'] <= 0:
                        del combatant['volatile_statuses']['fairy_lock']
                        combat_log += f"🔓 **{combatant['name'].capitalize()}** is free to move again!\n"

                if combatant['current_hp'] > 0 and 'partially_trapped' in combatant.get('volatile_statuses', {}):
                    # Traps deal exactly 1/8th of Maximum HP per turn
                    trap_dmg = max(1, math.floor(combatant.get('max_hp', 100) / 8))
                    combatant['current_hp'] = max(0, combatant['current_hp'] - trap_dmg)
                    combat_log += f"🌪️ {owner_str.strip()} **{combatant['name'].capitalize()}** is hurt by the trap! (-{trap_dmg} HP)\n"
                    
                    # Decay the trap timer!
                    combatant['volatile_statuses']['partially_trapped'] -= 1
                    if combatant['volatile_statuses']['partially_trapped'] <= 0:
                        del combatant['volatile_statuses']['partially_trapped']
                        combat_log += f"💨 {owner_str.strip()} **{combatant['name'].capitalize()}** was freed from the trap!\n"
            
            # ==========================================
            # 🚨 INGRAIN & OCTOLOCK (End of Turn)
            # ==========================================
            for combatant, _, owner_str in combatants:
                if combatant['current_hp'] > 0:
                    volatiles = combatant.get('volatile_statuses', {})
                    
                    # Aqua Ring trickles back the same share Ingrain does
                    if 'aqua_ring' in volatiles and combatant['current_hp'] < combatant.get('max_hp', 100):
                        ring_qty = max(1, math.floor(combatant.get('max_hp', 100) / AQUA_RING_FRACTION))
                        combatant['current_hp'] = min(combatant.get('max_hp', 100),
                                                      combatant['current_hp'] + ring_qty)
                        combat_log += f"\U0001f4a7 {owner_str.strip()} **{combatant['name'].capitalize()}** was restored by its veil of water! (+{ring_qty} HP)\n"

                    # A Ghost's Curse bleeds a quarter of the maximum away every turn
                    if 'curse' in volatiles:
                        curse_qty = max(1, math.floor(combatant.get('max_hp', 100) * CURSE_DRAIN_FRACTION))
                        combatant['current_hp'] = max(0, combatant['current_hp'] - curse_qty)
                        combat_log += f"\U0001f47b {owner_str.strip()} **{combatant['name'].capitalize()}** was hurt by the curse! (-{curse_qty} HP)\n"

                    # Ingrain Healing (1/16th Max HP)
                    if 'ingrain' in volatiles and combatant['current_hp'] < combatant.get('max_hp', 100):
                        heal_qty = max(1, math.floor(combatant.get('max_hp', 100) / 16))
                        combatant['current_hp'] = min(combatant.get('max_hp', 100), combatant['current_hp'] + heal_qty)
                        combat_log += f"🌱 {owner_str.strip()} **{combatant['name'].capitalize()}** absorbed nutrients from its roots! (+{heal_qty} HP)\n"
                        
                    # Octolock Decay (-1 Def, -1 SpD)
                    if 'octolock' in volatiles:
                        if 'stat_stages' not in combatant:
                            combatant['stat_stages'] = {'attack': 0, 'defense': 0, 'sp_atk': 0, 'sp_def': 0, 'speed': 0}
                        
                        combatant['stat_stages']['defense'] = max(-6, combatant['stat_stages'].get('defense', 0) - 1)
                        combatant['stat_stages']['sp_def'] = max(-6, combatant['stat_stages'].get('sp_def', 0) - 1)
                        combat_log += f"🐙 {owner_str.strip()} **{combatant['name'].capitalize()}**'s Def and Sp. Def were lowered by Octolock!\n"

            # 4. G-Max Ecological Disasters (Wildfire, Vine Lash, Cannonade, volcalith)
            # Match the active Pokémon with the hazards currently polluting THEIR side of the field
            for p_active, hazards, owner_str in combatants:
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


            # 5. Barrier Decay (Screens)
            # (Note: Map the hazards and names properly depending on PvE or PvP!)
            for hazards, owner_str in [(state['p1_hazards'], f"{state['p1'].display_name}'s"),
                (state['p2_hazards'], f"{state['p2'].display_name}'s")]: 
                for screen in SIDE_SCREEN_MOVES:
                    if hazards.get(screen, 0) > 0:
                        hazards[screen] -= 1
                        if hazards[screen] <= 0:
                            del hazards[screen]
                            combat_log += f"✨ {owner_str} team's {screen.replace('-', ' ').title()} wore off!\n"

            # 4. Kinetic Stun & Shield Cleanup
            for p_active in [new_p1_active, new_p2_active]:
                # Flush the short-term damage memory and curses!
                p_active.pop('last_damage_taken', None)
                p_active.pop('last_damage_class', None)

                if 'volatile_statuses' in p_active:
                    p_active['volatile_statuses'].pop('flinch', None)
                    p_active['volatile_statuses'].pop('protected', None)
                    p_active['volatile_statuses'].pop('protect_type', None)
                    p_active['volatile_statuses'].pop('destiny-bond', None)
                    p_active['volatile_statuses'].pop('is_switching', None)
                    p_active['volatile_statuses'].pop('stats_lowered_this_turn', None)
                    p_active['volatile_statuses'].pop('electrified', None)
                    clear_interceptors(p_active)

                    # Magnet Rise and Telekinesis run their own clocks
                    for lift in ('magnet_rise', 'telekinesis'):
                        if p_active['volatile_statuses'].get(lift):
                            p_active['volatile_statuses'][lift] -= 1
                            if p_active['volatile_statuses'][lift] <= 0:
                                del p_active['volatile_statuses'][lift]
                                combat_log += f"🪂 **{p_active['name'].capitalize()}** drifted back to the ground!\n"

                    # A charge that was pending and did NOT fire this turn means the user
                    # was stopped, so the move fails and it comes back down. PvP had no
                    # sweep for this at all.
                    broken = break_stale_charge(p_active)
                    if broken:
                        combat_log += f"✨ **{p_active['name'].capitalize()}**'s {broken.replace('-', ' ').title()} was interrupted!\n"

                    # Embargo runs on its own five-turn clock rather than being wiped
                    if p_active['volatile_statuses'].get('embargo'):
                        p_active['volatile_statuses']['embargo'] -= 1
                        if p_active['volatile_statuses']['embargo'] <= 0:
                            del p_active['volatile_statuses']['embargo']
                            combat_log += f"✨ **{p_active['name'].capitalize()}** is free of its Embargo!\n"
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
                post_battle_view = None # Initialize empty view for potential evolutions
                
                async with aiosqlite.connect(DB_FILE) as db:
                    async with db.cursor() as cursor:

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
                                            held_item = resolve_persisted_item(p).lower().replace(' ', '-')
                                            
                                            # Block 1: The Everstone Suppressant
                                            if held_item == 'everstone':
                                                rewards_log += f"\n🪨 **{p['name'].capitalize()}**'s biological mutation was suppressed by its Everstone!"
                                                
                                            # Block 2: Check for Mutation
                                            else:
                                                try:
                                                    # NOTE: this runs on the Combat cog itself, so there is no
                                                    # `self.cog` here, and check_for_evolution is not a Combat
                                                    # method either - it lives at module level for both engines.
                                                    evo_msg, target_species = await check_for_evolution(db, user_id, p, combat_log)

                                                    if evo_msg:
                                                        rewards_log += evo_msg

                                                    # Attach the confirmation view if a mutation is pending!
                                                    if target_species and post_battle_view is None:
                                                        post_battle_view = EvolutionConfirmView(self, user_id, p, target_species)
                                                except Exception as e:
                                                    print(f"DEBUG: Evolution check failed in PvP: {e}")

                            # 3. Sync the complete team state to the database! (Levels, EXP, and consumed items)
                            for p in p_team:
                                if 'instance_id' in p:
                                    # 🚨 This line permanently deletes any Berries/Sashes consumed during the fight!
                                    await cursor.execute("""
                                        UPDATE caught_pokemon
                                        SET level = ?, experience = ?, held_item = ?
                                        WHERE instance_id = ?
                                    """, (p['level'], p['experience'], resolve_persisted_item(p), p['instance_id']))

                                    sketched = await persist_sketch(cursor, p)
                                    if sketched:
                                        rewards_log += f"\n✏️ **{p['name'].capitalize()}** permanently learned {sketched.replace('-', ' ').title()}!"

                            # Block 19: the same after-battle find PvE pays, for each
                            # duellist's own team.
                            rewards_log += await collect_field_spoils(
                                cursor, p_team, user_id)

                        await db.commit()

                embed = discord.Embed(title="🏁 Ecological Duel Concluded!", description=f"{combat_log}\n{result_str}{rewards_log}", color=discord.Color.gold())
                self.active_battles.pop(p1_id, None)
                self.active_battles.pop(p2_id, None)
                
                embed = discord.Embed(title="🏁 Ecological Duel Concluded!", description=f"{combat_log}\n{result_str}{rewards_log}", color=discord.Color.gold())
                self.active_battles.pop(p1_id, None)
                self.active_battles.pop(p2_id, None)
                return await state['message_obj'].edit(embed=embed, attachments=[], view=post_battle_view)

            # ==========================================
            # PHASE 4: FAINT & PIVOT CHECKS
            # ==========================================
            print("DEBUG: Preparing UI Redraw...")
            state['turn_number'] += 1
            state['commits'] = {p1_id: None, p2_id: None}
            
            # Re-verify the active Pokémon after Phase 3 environmental damage!
            new_p1_active = state['p1_team'][state['p1_active_index']]
            new_p2_active = state['p2_team'][state['p2_active_index']]

            # The end-of-turn item pass, from the same shared call PvE makes. The berry
            # sweep inside it is new to PvP: until this existed a duel only ever ate a
            # berry in answer to a BLOW, so a Sitrus Berry sat untouched while its
            # holder burned to death.
            combat_log += end_of_turn_items(
                state,
                (new_p1_active, new_p2_active, f"{state['p1'].display_name}'s"),
                (new_p2_active, new_p1_active, f"{state['p2'].display_name}'s"))

            # The same four blocks of end-of-turn reactions PvE runs, from the same
            # shared call - Soul-Heart, the HP-watching form flips, Berserk and Anger
            # Shell, and the Wimp Out pivot the swap check just below already reads.
            combat_log += await end_of_turn_survival(
                state,
                (new_p1_active, 'p1_must_pivot', f"{state['p1'].display_name}'s"),
                (new_p2_active, 'p2_must_pivot', f"{state['p2'].display_name}'s"))

            p1_needs_swap = new_p1_active['current_hp'] <= 0 or state.get('p1_must_pivot')
            p2_needs_swap = new_p2_active['current_hp'] <= 0 or state.get('p2_must_pivot')

            # ==========================================
            # 🚨 NEW: PRIMORDIAL WEATHER FAINT/PIVOT CLEAR
            # ==========================================
            weather = state.get('weather', {})
            if weather.get('primordial'):
                p1_is_setter = p1_needs_swap and get_active_ability(new_p1_active) in ['desolate-land', 'primordial-sea', 'delta-stream']
                p2_is_setter = p2_needs_swap and get_active_ability(new_p2_active) in ['desolate-land', 'primordial-sea', 'delta-stream']
                
                if p1_is_setter or p2_is_setter:
                    state['weather'] = {'type': 'none', 'duration': 0, 'primordial': False}
                    combat_log += "\n🌤️ The primordial weather dissipated as its creator left the field!\n"
            # ==========================================

            if p1_needs_swap or p2_needs_swap:
                print("DEBUG: Tactical Swap Required. Entering Recovery Phase.")
                # Flush the pivot flags. PvE does this as it announces the retreat;
                # PvP had nowhere to do it because nothing had ever set them, so a
                # Wimp Out here would have pivoted again every turn for the rest of
                # the battle. A faint does not need flushing - the corpse is replaced.
                state['p1_must_pivot'] = False
                state['p2_must_pivot'] = False
                state['phase'] = 'faint_swap' # Piggyback on your existing recovery engine!
                state['commits'] = {p1_id: None, p2_id: None}
                
                embed = discord.Embed(title="⚠️ Tactical Swap Required!", description=f"{combat_log}\nWaiting for researchers to deploy replacements...", color=discord.Color.orange())
                await state['message_obj'].edit(embed=embed, attachments=[], view=None)
                
                # Ping P1 if they triggered a swap, otherwise auto-ready them!
                if p1_needs_swap:
                    view1 = PvPForcedSwapMenu(self, state, p1_id)
                    reason = "fainted" if new_p1_active['current_hp'] <= 0 else "is pivoting out"
                    await state['p1'].send(f"⚠️ Your active specimen {reason}! Select a replacement:", view=view1)
                else:
                    state['commits'][p1_id] = {'type': 'pass'}
                    
                # Ping P2 if they triggered a swap, otherwise auto-ready them!
                if p2_needs_swap:
                    view2 = PvPForcedSwapMenu(self, state, p2_id)
                    reason = "fainted" if new_p2_active['current_hp'] <= 0 else "is pivoting out"
                    await state['p2'].send(f"⚠️ Your active specimen {reason}! Select a replacement:", view=view2)
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
                    n_hazards=state['p2_hazards'],
                    p_name=new_p1_active.get('name'), p_level=new_p1_active.get('level'),
                    p_gender=new_p1_active.get('gender'), n_gender=new_p2_active.get('gender'),
                    n_name=new_p2_active.get('name'), n_level=new_p2_active.get('level'),
                    p_aura=battle_render.aura_for(state.get('p1_adaptation'), new_p1_active),
                    n_aura=battle_render.aura_for(state.get('p2_adaptation'), new_p2_active)
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
                leave_field(state['p1_team'][state['p1_active_index']])
                state['p1_active_index'] = bench_idx
                new_p1 = state['p1_team'][bench_idx]
                leave_field(new_p1)
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
                        combat_log = await trigger_single_entry_ability(new_p1, state['p2_team'][state['p2_active_index']], f"{state['p1'].display_name}'s", state, combat_log)
                except Exception as e:
                    print(f"DEBUG: P1 Ability crash ignored: {e}")

            # --- Process Player 2's Replacement ---
            if c2 and c2['type'] == 'forced_swap':
                bench_idx = c2['data']
                leave_field(state['p2_team'][state['p2_active_index']])
                state['p2_active_index'] = bench_idx
                new_p2 = state['p2_team'][bench_idx]
                leave_field(new_p2)
                combat_log += f"🔄 **{state['p2'].display_name}** deployed **{new_p2['name'].capitalize()}**!\n"
                
                try:
                    if 'TYPE_CHART' in globals():
                        hz_log = apply_entry_hazards(new_p2, state['p2_hazards'], TYPE_CHART, f"{state['p2'].display_name}'s")
                        if hz_log: combat_log += hz_log
                except Exception as e:
                    print(f"DEBUG: P2 Hazard crash ignored: {e}")

                try:
                    if new_p2['current_hp'] > 0:
                        combat_log = await trigger_single_entry_ability(new_p2, state['p1_team'][state['p1_active_index']], f"{state['p2'].display_name}'s", state, combat_log)
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
                    p_hazards=state['p1_hazards'], n_hazards=state['p2_hazards'],
                    p_name=p1_active.get('name'), p_level=p1_active.get('level'),
                    p_gender=p1_active.get('gender'), n_gender=p2_active.get('gender'),
                    n_name=p2_active.get('name'), n_level=p2_active.get('level'),
                    p_aura=battle_render.aura_for(state.get('p1_adaptation'), p1_active),
                    n_aura=battle_render.aura_for(state.get('p2_adaptation'), p2_active)
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
    @checks.partner_not_deployed()
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
        
        try:
            async with aiosqlite.connect(DB_FILE) as db:
                # 1. Progression Check: Do they have the Visa?
                async with db.execute("SELECT unlocked_visas FROM users WHERE user_id = ?", (user_id,)) as cursor:
                    user_data = await cursor.fetchone()
                    visas = user_data[0] if user_data and user_data[0] else "canopy"
                    
                    if biome not in visas.split(','):
                        return await ctx.send(f"⛔ **ACCESS DENIED:** You lack the clearance to challenge the {warden_data['title']}. Obtain the Visa for this sector first.")
                    
                    # 2. Compile the Warden's Tactical Team (Hydrating the roster)
                    compiled_team = []
                    for pkmn in warden_data['team']:
                        async with db.execute("""
                        SELECT stat_name, base_value, pokedex_id
                        FROM base_pokemon_stats 
                        WHERE pokedex_id = (SELECT pokedex_id FROM base_pokemon_species WHERE name = ?)
                    """, (pkmn['name'],)) as cursor:
                            rows = await cursor.fetchall()
                        if not rows:
                            continue # Skip if database error
                        
                        stats = {row[0]: row[1] for row in rows}
                        p_id = rows[0][2]
                        
                        nature = pkmn.get('nature', 'hardy').lower()
                        inc_stat, dec_stat = NATURE_MULTIPLIERS.get(nature, (None, None))
                        
                        def apply_nature(stat_name, val):
                            if stat_name == inc_stat: return math.floor(val * 1.1)
                            if stat_name == dec_stat: return math.floor(val * 0.9)
                            return val
                        
                        real_hp = calculate_real_stat('hp', stats.get('hp', 0), pkmn['ivs']['hp'], pkmn['evs']['hp'], pkmn['level'])
                        real_atk = apply_nature('attack', calculate_real_stat('attack', stats.get('attack', 0), pkmn['ivs']['attack'], pkmn['evs']['attack'], pkmn['level']))
                        real_def = apply_nature('defense', calculate_real_stat('defense', stats.get('defense', 0), pkmn['ivs']['defense'], pkmn['evs']['defense'], pkmn['level']))
                        real_spa = apply_nature('special-attack', calculate_real_stat('special-attack', stats.get('special-attack', 0), pkmn['ivs']['sp_atk'], pkmn['evs']['sp_atk'], pkmn['level']))
                        real_spd = apply_nature('special-defense', calculate_real_stat('special-defense', stats.get('special-defense', 0), pkmn['ivs']['sp_def'], pkmn['evs']['sp_def'], pkmn['level']))
                        real_spe = apply_nature('speed', calculate_real_stat('speed', stats.get('speed', 0), pkmn['ivs']['speed'], pkmn['evs']['speed'], pkmn['level']))
                        
                        # Make sure the moves have 'max_pp'
                        hydrated_moves = []
                        for m in pkmn['moves']:
                            hydrated_moves.append({'name': m['name'], 'pp': m['pp'], 'max_pp': m['max_pp']})

                        # Wardens field a fixed roster, so their genders are seeded on the
                        # sector + species instead of rerolled -- otherwise the same
                        # Warden's Pokemon would flip gender between rematches. A roster
                        # entry can pin it explicitly with a 'gender' key.
                        w_gender = pkmn.get('gender')
                        if w_gender is None:
                            w_gender = roll_gender(
                                await fetch_gender_rate(db, p_id),
                                species_name=pkmn['name'],
                                rng=random.Random(
                                    f"{biome}:{pkmn['name']}:{pkmn['level']}"))

                        compiled_member = {
                            'pokedex_id': p_id,
                            'name': pkmn['name'],
                            'level': pkmn['level'],
                            'types': pkmn['types'],
                            'held_item': pkmn['held_item'],
                            'nature': nature.capitalize(),
                            'gender': normalize_gender(w_gender),
                            'max_hp': real_hp, 'current_hp': real_hp,
                            'stats': {'hp': real_hp, 'attack': real_atk, 'defense': real_def, 'sp_atk': real_spa, 'sp_def': real_spd, 'speed': real_spe},
                            'moves': hydrated_moves,
                            'status_condition': None,
                            'volatile_statuses': {},
                            'is_shiny': pkmn.get('is_shiny', False),
                            'ability': pkmn.get('ability', 'pressure'), # Default to Pressure if none is assigned!
                            'gmax_factor': 0
                        }
                        compiled_team.append(compiled_member)

                    # 3. Load the Player's Team (Identical to npc_encounter)
                    player_team = []
                    scope, scope_params = await party_filter(db, user_id)
                    async with db.execute(f"""
                    SELECT cp.instance_id, cp.pokedex_id, s.name, cp.level, cp.nature,
                        cp.iv_hp, cp.iv_attack, cp.iv_defense, cp.iv_sp_atk, cp.iv_sp_def, cp.iv_speed,
                        cp.ev_hp, cp.ev_attack, cp.ev_defense, cp.ev_sp_atk, cp.ev_sp_def, cp.ev_speed,
                        cp.move_1, cp.move_2, cp.move_3, cp.move_4, cp.is_shiny, cp.held_item, cp.gmax_factor, cp.ability, cp.experience, cp.gender, cp.happiness
                    FROM user_party up
                    JOIN caught_pokemon cp ON up.instance_id = cp.instance_id
                    JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                    WHERE up.user_id = ? {scope}
                    ORDER BY up.slot ASC
                """, (user_id, *scope_params)) as cursor:
                        party_rows = await cursor.fetchall()
                    if not party_rows:
                        return await ctx.send("⚠️ You must assign at least one specimen to your fieldwork roster using `!party add 1 [Tag ID]` before engaging a Warden!")

                    for row in party_rows:
                        tag, p_id, p_name, p_lvl, p_nature = row[0:5]
                        p_ivs = {'hp': row[5], 'attack': row[6], 'defense': row[7], 'sp_atk': row[8], 'sp_def': row[9], 'speed': row[10]}
                        p_evs = {'hp': row[11], 'attack': row[12], 'defense': row[13], 'sp_atk': row[14], 'sp_def': row[15], 'speed': row[16]}
                        raw_moves = [m for m in row[17:21] if m and m != 'none']
                        p_moves = []
                        for m_name in raw_moves:
                            async with db.execute("SELECT pp FROM base_moves WHERE name = ?", (m_name,)) as cursor:
                                pp_row = await cursor.fetchone()
                            pp_val = pp_row[0] if pp_row else 5 
                            p_moves.append({'name': m_name, 'pp': pp_val, 'max_pp': pp_val})

                        async with db.execute("SELECT type_name FROM base_pokemon_types WHERE pokedex_id = ?", (p_id,)) as cursor:
                            p_types = [t[0] for t in await cursor.fetchall()]

                        is_shiny = row[21]
                        held_item = row[22]
                        gmax_factor = row[23]
                        ability = row[24]
                        experience = row[25]
                        
                        p_base = await fetch_base_stats(db, p_id)
                        p_final_stats = calculate_stats(p_base, p_ivs, p_evs, p_lvl, p_nature)
                        
                        player_team.append({
                            'instance_id': tag, 'pokedex_id': p_id, 'name': p_name, 'level': p_lvl,
                            'max_hp': p_final_stats['hp'], 'current_hp': p_final_stats['hp'],
                            'stats': p_final_stats, 'moves': p_moves, 'status_condition': None, 'is_shiny': is_shiny, 
                            'held_item': held_item, 'gmax_factor': gmax_factor, 'ability': ability, 'types': p_types,
                            'experience': experience, 'volatile_statuses': {},
                            'gender': normalize_gender(row[26]),
                            # Appended last in the SELECT, so it is read off the end
                            # rather than renumbering every index above it.
                            'happiness': row[-1]
                        })

                    # ==========================================
                    # REGULATION CHECK: SECTOR LEVEL CAPS
                    # ==========================================
                    SECTOR_CAPS = {
                        'canopy': 30, #100 for testing purposes
                        'trench': 45,
                        'core': 60,
                        'sprawl': 75
                    }
                    
                    max_allowed_level = SECTOR_CAPS.get(biome, 100) # Fallback to 100
                    
                    # Scan the player's active party for violations
                    overleveled_specimens = [p for p in player_team if p['level'] > max_allowed_level]
                    
                    if overleveled_specimens:
                        names = ", ".join([p['name'].capitalize() for p in overleveled_specimens])
                        return await ctx.send(f"⛔ **ECOLOGICAL REGULATION:** Your roster contains specimens that exceed the Sector Level Cap (Lv. {max_allowed_level}).\n\nViolating Specimens: **{names}**.\n\nPlease deposit them in your PC or swap them out before engaging the {warden_data['title']}.")
                    # ==========================================

                    # 4. Key Item Scanner
                    async with db.execute("""
                    SELECT item_name FROM user_inventory 
                    WHERE user_id = ? AND item_name IN ('dynamax-band', 'z-ring', 'mega-bracelet') AND quantity > 0
                """, (user_id,)) as cursor:
                        owned_key_items = [row[0] for row in await cursor.fetchall()]
                access_ledger = {
                    'dynamax_band': 'dynamax-band' in owned_key_items,
                    'z_ring': 'z-ring' in owned_key_items,
                    'mega_bracelet': 'mega-bracelet' in owned_key_items
                    }

            
            # 5. Initialize the Battle State Memory
            self.active_battles[user_id] = {
                'player_team': snapshot_team_items(player_team),
                'npc_team': compiled_team,
                'active_player_index': 0, # Slot 1
                'active_npc_index': 0,    # Slot 1
                'turn_number': 1,
                'weather': {'type': 'none', 'duration': 0},
                'adaptation': {'used': False, 'active': False, 'type': 'none', 'turns': 0, 'backup': {}},
                'key_items': access_ledger,
                'is_warden': True,
                'warden_biome': biome,
                
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
            combat_log = await trigger_single_entry_ability(p_lead, n_lead, "Your", state, combat_log)
            combat_log = await trigger_single_entry_ability(n_lead, p_lead, "The Warden's", state, combat_log)

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
                n_hazards=state.get('npc_hazards'),
                p_name=p_lead.get('name'), p_level=p_lead.get('level'),
                p_gender=p_lead.get('gender'), n_gender=n_lead.get('gender'),
                n_name=n_lead.get('name'), n_level=n_lead.get('level'),
                p_aura=battle_render.aura_for(state.get('adaptation'), p_lead),
                biome=state.get('warden_biome')
            )

            # Dynamically grab the new randomized filename!
            if battle_file:
                embed.set_image(url=f"attachment://{battle_file.filename}")
            
            dashboard_view = await BattleDashboard.create(self, user_id, ctx)
            await ctx.send(embed=embed, files=[battle_file], view=dashboard_view)

        except Exception as e:
            print("\n🚨 CRITICAL CRASH IN WARDEN INITIALIZATION 🚨")
            import traceback
            traceback.print_exc()
            await ctx.send("⚠️ A critical failure occurred while engaging the Warden. Check the console.")

    @commands.command(name="tech", aliases=["techmoves"])
    @checks.has_started()
    @checks.is_authorized()
    async def view_tms(self, ctx):
        """Displays all Technical Machines (TMs) currently in your field notebook."""
        user_id = str(ctx.author.id)
        
        try:
            # Fetch TMs from the database
            async with aiosqlite.connect(DB_FILE) as db:
                async with db.execute("SELECT tm_name FROM user_tms WHERE user_id = ?", (user_id,)) as cursor:
                    tms = await cursor.fetchall()
            
            if not tms:
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

    @commands.command(name="tm")
    @checks.has_started()
    @checks.is_authorized()
    @checks.partner_not_deployed()
    async def teach_move(self, ctx, box_number: str, *, tm_name: str):
        """Teaches a new move to a specific specimen using a TM."""
        try:
            user_id = str(ctx.author.id)
            clean_tm_name = tm_name.lower().replace(" ", "-")

            if not box_number.isdigit():
                return await ctx.send("⚠️ Please use the specimen's Box Number (e.g., `!tm 4 earthquake`).")

            async with aiosqlite.connect(DB_FILE) as db:
                
                # ==========================================
                # 1. VERIFY OWNERSHIP & APPLY SOFT HIDE
                # ==========================================
                async with db.execute("""
                    WITH Roster AS (
                        SELECT cp.pokedex_id, s.name, cp.level, cp.move_1, cp.move_2, cp.move_3, cp.move_4, cp.instance_id,
                               ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                        FROM caught_pokemon cp
                        JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                        WHERE cp.user_id = ?
                        AND cp.instance_id NOT IN (SELECT instance_id FROM active_deployments)
                        AND cp.instance_id NOT IN (SELECT instance_id FROM gts_deposits)
                    )
                    SELECT pokedex_id, name, level, move_1, move_2, move_3, move_4, instance_id
                    FROM Roster WHERE box_number = ?
                """, (user_id, int(box_number))) as cursor:
                    specimen = await cursor.fetchone()

                if not specimen:
                    return await ctx.send(f"❌ Could not find a specimen in Box `#{box_number}`. Are they currently deployed?")

                p_id, p_name, p_level, m1, m2, m3, m4, exact_instance_id = specimen
                current_moves = [m for m in [m1, m2, m3, m4] if m and m != 'none']

                # ==========================================
                # 2. VERIFY DUPLICATION
                # ==========================================
                if clean_tm_name in current_moves:
                    return await ctx.send(f"⚠️ **{p_name.capitalize()}** already knows `{clean_tm_name.replace('-', ' ').title()}`!")

                # ==========================================
                # 3. THE SAME QUESTION `!learn` ASKS
                # ==========================================
                # Ownership, compatibility and maturity were three checks here and a
                # different three in `!learn`. One function answers all of it now, so
                # the two front doors cannot disagree about what a move costs - and a
                # move this specimen would have grown into anyway does not burn a TM.
                route, problem = await teaching_route(
                    db, user_id, p_name, p_id, p_level, clean_tm_name)
                if problem:
                    return await ctx.send(problem)

                # ==========================================
                # 4. EXECUTE THE GENETIC OVERWRITE
                # ==========================================
                if len(current_moves) < 4:
                    empty_col = "move_1" if not m1 or m1 == 'none' else \
                                "move_2" if not m2 or m2 == 'none' else \
                                "move_3" if not m3 or m3 == 'none' else "move_4"

                    if route == 'machine':
                        await db.execute("UPDATE user_tms SET quantity = quantity - 1 WHERE user_id = ? AND tm_name = ?", (user_id, clean_tm_name))
                    await db.execute(f"UPDATE caught_pokemon SET {empty_col} = ? WHERE instance_id = ?", (clean_tm_name, exact_instance_id))
                    await db.commit()

                    return await ctx.send(f"💿 You booted up the TM!\n✨ **{p_name.capitalize()}** learned `{clean_tm_name.replace('-', ' ').title()}`!")

            # If they already have 4 moves, spawn the Overwrite UI!
            embed = discord.Embed(
                title="⚠️ Genetic Capacity Reached",
                description=f"**{p_name.capitalize()}** wants to learn `{clean_tm_name.replace('-', ' ').title()}`, but it already knows 4 moves.\n\nWhich move should it forget?",
                color=discord.Color.orange()
            )
            
            view = TeachMenu(self, user_id, exact_instance_id, p_name, clean_tm_name,
                             current_moves, consumes_tm=(route == 'machine'))
            await ctx.send(embed=embed, view=view)

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
        
        try:
            async with aiosqlite.connect(DB_FILE) as db:
                pokemon_data = None
                
                # 1. Resolve Target (Empty or Partner)
                if not tag_id or tag_id.lower() in ["partner", "lead", "active"]:
                    async with db.execute("SELECT active_partner FROM users WHERE user_id = ?", (user_id,)) as cursor:
                        partner_data = await cursor.fetchone()

                    if partner_data and partner_data[0]:
                        # Fetch the partner directly using their UUID
                        async with db.execute("""
                            WITH Roster AS (
                                SELECT cp.instance_id, cp.level, s.name, cp.move_1, cp.move_2, cp.move_3, cp.move_4,
                                    ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                                FROM caught_pokemon cp JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                                WHERE cp.user_id = ?
                                AND cp.instance_id NOT IN (SELECT instance_id FROM active_deployments)
                                AND cp.instance_id NOT IN (SELECT instance_id FROM gts_deposits)
                            ) 
                            SELECT * FROM Roster WHERE instance_id = ?
                        """, (user_id, partner_data[0])) as cursor:
                            pokemon_data = await cursor.fetchone()
                    else:
                        return await ctx.send("⚠️ You don't have an Active Partner equipped! Specify a Box Number.")

                # 2. Fast Database Query for "Latest"
                elif tag_id.lower() in ["new", "latest", "last"]:
                    async with db.execute("""
                        WITH Roster AS (
                            SELECT cp.instance_id, cp.level, s.name, cp.move_1, cp.move_2, cp.move_3, cp.move_4,
                                ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                            FROM caught_pokemon cp JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                            WHERE cp.user_id = ?
                            AND cp.instance_id NOT IN (SELECT instance_id FROM active_deployments)
                            AND cp.instance_id NOT IN (SELECT instance_id FROM gts_deposits)
                        ) 
                        SELECT * FROM Roster ORDER BY box_number DESC LIMIT 1
                    """, (user_id,)) as cursor:
                        pokemon_data = await cursor.fetchone()
                    
                # 3. Box Number Lookup
                elif tag_id.isdigit() and len(tag_id) <= 6:
                    async with db.execute("""
                        WITH Roster AS (
                            SELECT cp.instance_id, cp.level, s.name, cp.move_1, cp.move_2, cp.move_3, cp.move_4,
                                ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                            FROM caught_pokemon cp JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                            WHERE cp.user_id = ?
                                AND cp.instance_id NOT IN (SELECT instance_id FROM active_deployments)
                                AND cp.instance_id NOT IN (SELECT instance_id FROM gts_deposits)
                        ) 
                        SELECT * FROM Roster WHERE box_number = ?
                    """, (user_id, int(tag_id))) as cursor:
                        pokemon_data = await cursor.fetchone()
                
                else:
                    return await ctx.send("⚠️ Please use a valid Box Number (e.g., `!moves 4`) or leave it blank for your partner.")
                    
                if not pokemon_data:
                    return await ctx.send("❌ Could not locate that specimen. Are they currently deployed?")
                
                # Unpack the 8 variables we selected in the CTE
                actual_tag, level, name, m1, m2, m3, m4, box_number = pokemon_data
                
                # 4. Build the Lightweight UI
                embed = discord.Embed(title=f"⚔️ Active Behaviors: {name.capitalize()}", color=discord.Color.green())
                embed.description = f"**Level {level}** | Box `#{box_number}` | Tag ID: `{actual_tag[:8]}`"
                
                equipped_moves = [m1, m2, m3, m4]
                for i, move_name in enumerate(equipped_moves, start=1):
                    display = f"**{move_name.replace('-', ' ').title()}**" if move_name and move_name != 'none' else "*Empty Slot*"
                    embed.add_field(name=f"Slot {i}", value=display, inline=False)
                    
                embed.set_footer(text="Use !moveset [Box Number] for detailed stats and learnable moves.")
                await ctx.send(embed=embed)

        except Exception as e:
            print(f"Moves Command Error: {e}")
            await ctx.send("❌ A database error occurred while fetching behavioral data.")

    @commands.command(name="moveset", aliases=["movedata"])
    @checks.has_started()
    @checks.is_authorized()
    async def detailed_moveset(self, ctx, tag_id: str = None):
        """Analyzes biological movepool potential with full statistics."""
        user_id = str(ctx.author.id)
        
        try:
            async with aiosqlite.connect(DB_FILE) as db:
                pokemon_data = None
                
                # 1. Resolve Target (Empty or Partner)
                if not tag_id or tag_id.lower() in ["partner", "lead", "active"]:
                    async with db.execute("SELECT active_partner FROM users WHERE user_id = ?", (user_id,)) as cursor:
                        partner_data = await cursor.fetchone()

                    if partner_data and partner_data[0]:
                        # 🚨 FIX: Number the entire PC first, then filter by UUID!
                        async with db.execute("""
                            WITH Roster AS (
                                SELECT cp.instance_id, cp.pokedex_id, cp.level, s.name,
                                    ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                                FROM caught_pokemon cp JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                                WHERE cp.user_id = ?
                                AND cp.instance_id NOT IN (SELECT instance_id FROM active_deployments)
                                AND cp.instance_id NOT IN (SELECT instance_id FROM gts_deposits)
                            ) 
                            SELECT instance_id, pokedex_id, level, name, box_number FROM Roster WHERE instance_id = ?
                        """, (user_id, partner_data[0])) as cursor:
                            pokemon_data = await cursor.fetchone()
                    else:
                        return await ctx.send("⚠️ You don't have an Active Partner equipped! Specify a Box Number.")

                # 2. Fast Database Query for "Latest"
                elif tag_id.lower() in ["new", "latest", "last"]:
                    async with db.execute("""
                        WITH Roster AS (
                            SELECT cp.instance_id, cp.pokedex_id, cp.level, s.name,
                                ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                            FROM caught_pokemon cp JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                            WHERE cp.user_id = ?
                            AND cp.instance_id NOT IN (SELECT instance_id FROM active_deployments)
                            AND cp.instance_id NOT IN (SELECT instance_id FROM gts_deposits)
                        ) 
                        SELECT instance_id, pokedex_id, level, name, box_number FROM Roster ORDER BY box_number DESC LIMIT 1
                    """, (user_id,)) as cursor:
                        pokemon_data = await cursor.fetchone()
                    
                # 3. Box Number Lookup
                elif tag_id.isdigit() and len(tag_id) <= 6:
                    async with db.execute("""
                        WITH Roster AS (
                            SELECT cp.instance_id, cp.pokedex_id, cp.level, s.name,
                                ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                            FROM caught_pokemon cp JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                            WHERE cp.user_id = ?
                                AND cp.instance_id NOT IN (SELECT instance_id FROM active_deployments)
                                AND cp.instance_id NOT IN (SELECT instance_id FROM gts_deposits)
                        ) 
                        SELECT instance_id, pokedex_id, level, name, box_number FROM Roster WHERE box_number = ?
                    """, (user_id, int(tag_id))) as cursor:
                        pokemon_data = await cursor.fetchone()
                
                else:
                    return await ctx.send("⚠️ Please use a valid Box Number (e.g., `!moveset 4`) or leave it blank for your partner.")
                    
                if not pokemon_data:
                    return await ctx.send("❌ Could not locate that specimen. Check your Box Number or ensure they aren't deployed.")
                
                # Unpack the variables safely!
                actual_tag, poke_id, level, name, box_number = pokemon_data
                
                # 2. Advanced Analytics Query: Includes Learn Method and Sorting!
                async with db.execute("""
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
                """, (poke_id,)) as cursor:
                    raw_movepool = await cursor.fetchall()

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

                if not move_data_list:
                    return await ctx.send(f"⚠️ Biological anomaly: No learnable behaviors found in the database for **{name.capitalize()}**.")

                # 4. Trigger the Paginator
                view = DetailedMovepoolPaginator(ctx, poke_info, move_data_list)
                await ctx.send(embed=view.create_embed(), view=view)
                
        except Exception as e:
            print(f"Moveset Error: {e}")
            await ctx.send("❌ A critical database error occurred while fetching behavioral data.")

    @commands.command(name="party", aliases=["team", "roster"])
    @checks.has_started()
    @checks.is_authorized()
    async def manage_party(self, ctx, *, request: str = None):
        """Your battle rosters. `!party list`, `!party switch <name>`, `!party clear`."""
        # \U0001f9ea SAFETY NET: Wraps the entire command to catch silent crashes!
        try:
            user_id = str(ctx.author.id)
            action, args = parse_party_request(request)

            async with aiosqlite.connect(DB_FILE) as db:
                current = await active_party(db, user_id)
                await ensure_party(db, user_id, current)

                # --- ACTION: LIST EVERY PARTY ---
                if action == 'list':
                    names = await party_names(db, user_id)
                    counts = await party_counts(db, user_id)
                    embed = discord.Embed(
                        title=f"\U0001f4cb {ctx.author.name}'s Rosters",
                        description="`!party switch <name>` to work on a different one.",
                        colour=discord.Colour.blue())
                    for name in names:
                        filled = counts.get(name, 0)
                        marker = " \u2b50 *active*" if name == current else ""
                        embed.add_field(
                            name=f"{name}{marker}",
                            value=f"{filled}/{PARTY_SLOTS} slots filled",
                            inline=False)
                    embed.set_footer(text=f"{len(names)}/{MAX_PARTIES} rosters")
                    return await ctx.send(embed=embed)

                # --- ACTION: MAKE A NEW ONE ---
                if action in ('new', 'create'):
                    name = clean_party_name(" ".join(args))
                    if not name:
                        return await ctx.send(
                            "\u26a0\ufe0f Give the roster a short name: "
                            "`!party new rain team`.")
                    names = await party_names(db, user_id)
                    if name in names:
                        return await ctx.send(f"\u26a0\ufe0f You already have a roster called **{name}**.")
                    if len(names) >= MAX_PARTIES:
                        return await ctx.send(
                            f"\u26a0\ufe0f You already have {MAX_PARTIES} rosters. "
                            f"Delete one with `!party delete <name>` first.")
                    await ensure_party(db, user_id, name)
                    await set_active_party(db, user_id, name)
                    await db.commit()
                    return await ctx.send(
                        f"\U0001f4cb Roster **{name}** created, and you are now working "
                        f"on it. `!party add 1 <box number>` to fill it.")

                # --- ACTION: SWITCH ---
                if action in ('switch', 'use'):
                    name = clean_party_name(" ".join(args))
                    names = await party_names(db, user_id)
                    if not name or name not in names:
                        listed = ", ".join(f"`{n}`" for n in names)
                        return await ctx.send(
                            f"\u26a0\ufe0f You have no roster called that. "
                            f"You have: {listed}. `!party new <name>` makes another.")
                    if not await set_active_party(db, user_id, name):
                        return await ctx.send(
                            "\u26a0\ufe0f Multiple rosters need the database migration "
                            "run first. Ask an administrator for `migrate_multi_party.py`.")
                    await db.commit()
                    return await ctx.send(f"\u2705 Now working on roster **{name}**.")

                # --- ACTION: DELETE A WHOLE ROSTER ---
                if action == 'delete':
                    name = clean_party_name(" ".join(args)) or current
                    if name == DEFAULT_PARTY:
                        return await ctx.send(
                            f"\u26a0\ufe0f **{DEFAULT_PARTY}** cannot be deleted \u2014 "
                            f"it is the one every trainer has. `!party clear` empties it.")
                    names = await party_names(db, user_id)
                    if name not in names:
                        return await ctx.send(f"\u26a0\ufe0f You have no roster called **{name}**.")

                    await party_delete_rows(db, user_id, name)
                    try:
                        await db.execute(
                            "DELETE FROM user_parties WHERE user_id = ? AND party_name = ?",
                            (user_id, name))
                    except Exception:
                        pass
                    if current == name:
                        await set_active_party(db, user_id, DEFAULT_PARTY)
                    await db.commit()
                    return await ctx.send(
                        f"\U0001f5d1\ufe0f Roster **{name}** deleted. The specimens in it "
                        f"are untouched \u2014 only the roster is gone.")

                # --- ACTION: ADD TO PARTY ---
                if action in ("add", "set", "equip"):
                    if not args:
                        return await ctx.send(
                            "\u26a0\ufe0f Usage: `!party add [slot 1-6] [Box Number]`, "
                            "or `!party add 1 2 3 4 5 6` to fill the free slots at once.")

                    # ONE specimen is one sentence, whether or not a slot was named.
                    # `!party add 4 2` puts box 2 in slot 4, exactly as it always did;
                    # `!party add 2` puts it wherever there is room. Three or more
                    # arguments never meant anything before - the old signature read two
                    # and ignored the rest - so a list of specimens can take that
                    # spelling without changing what anybody already types.
                    single = (len(args) == 1
                              or (len(args) == 2 and args[0].isdigit()))
                    if single:
                        slot = int(args[0]) if len(args) == 2 else None
                        target = args[-1]
                        if slot is not None and (slot < 1 or slot > PARTY_SLOTS):
                            return await ctx.send(f"\u26a0\ufe0f A fieldwork roster can only hold up to {PARTY_SLOTS} specimens.")
                        placed, skipped = await assign_to_party(
                            db, user_id, current, [target], start_slot=slot)

                        # A single add says one sentence rather than drawing a table,
                        # and gives the resolver's full complaint when it fails.
                        if not placed:
                            # `target`, not `args[1]` - the single form takes one
                            # argument when no slot is named, and there is no args[1].
                            pokemon, problem = await locate_specimen(
                                db, user_id, target, "cp.instance_id, s.name")
                            if problem:
                                return await ctx.send(problem)
                            return await ctx.send(
                                f"\u26a0\ufe0f {skipped[0][1]}." if skipped
                                else "\u26a0\ufe0f Nothing was assigned.")

                        await db.commit()
                        return await ctx.send(
                            f"\u2705 **{placed[0][1].capitalize()}** has been assigned "
                            f"to slot {placed[0][0]} of **{current}**!")

                    # The mass form: fill the free slots, in the order given.
                    placed, skipped = await assign_to_party(db, user_id, current, args)
                    await db.commit()
                    return await ctx.send(
                        embed=assignment_report(current, placed, skipped))

                # --- ACTION: REMOVE ONE, OR EMPTY THE LOT ---
                if action in ("remove", "clear"):
                    # `!party clear 3` still clears slot three, because that is what it
                    # has always done and people have the habit. `!party clear` with no
                    # slot is the new thing: empty the whole roster.
                    if args and args[0].isdigit():
                        slot = int(args[0])
                        removed = await party_delete_rows(db, user_id, current, slot=slot)
                        await db.commit()
                        if not removed:
                            return await ctx.send(f"\U0001f9f9 Slot {slot} of **{current}** was already empty.")
                        return await ctx.send(f"\U0001f9f9 Slot {slot} of **{current}** has been cleared.")

                    name = clean_party_name(" ".join(args)) or current
                    members = await party_members(db, user_id, name)
                    if not members:
                        return await ctx.send(f"\U0001f9f9 **{name}** is already empty.")

                    return await ctx.send(
                        f"\u267b\ufe0f Empty **{name}** entirely? "
                        f"{len(members)} specimen(s) would be unassigned. "
                        f"They stay in your notebook.",
                        view=PartyClearConfirm(ctx, name, len(members)))

                # --- ACTION: VIEW ---
                if action == 'view':
                    name = clean_party_name(" ".join(args)) or current
                    names = await party_names(db, user_id)
                    if name not in names:
                        listed = ", ".join(f"`{n}`" for n in names)
                        return await ctx.send(
                            f"\u26a0\ufe0f You have no roster called **{name}**. "
                            f"You have: {listed}")

                    party_data = await party_members(db, user_id, name)

                    if not party_data:
                        return await ctx.send(
                            f"Roster **{name}** is empty! Use `!party add 1 [Box Number]` "
                            f"to start assembling your team.")

                    embed = discord.Embed(
                        title=f"\U0001f4cb {ctx.author.name}'s Roster: {name}",
                        color=discord.Color.blue())

                    # Track active slots to show empty ones
                    filled_slots = {row[0]: row for row in party_data}

                    for i in range(1, PARTY_SLOTS + 1):
                        if i in filled_slots:
                            slot, tag, name_, level, happiness, m1, m2, m3, m4, box_number = filled_slots[i]
                            moves = [m.replace('-', ' ').title() for m in [m1, m2, m3, m4] if m and m != 'none']
                            move_str = ", ".join(moves) if moves else "*No learned behaviors*"

                            # Visual bond indicator
                            bond = "\u2764\ufe0f\u2764\ufe0f\u2764\ufe0f" if happiness >= 220 else "\u2764\ufe0f\u2764\ufe0f\U0001f90d" if happiness >= 150 else "\u2764\ufe0f\U0001f90d\U0001f90d" if happiness >= 50 else "\U0001f90d\U0001f90d\U0001f90d"

                            embed.add_field(
                                name=f"Slot {i}: {name_.capitalize()} (Lv. {level})",
                                value=f"**Box `#{box_number}`** | **Tag:** `{tag[:8]}` | **Bond:** {bond}\n**Moves:** {move_str}",
                                inline=False
                            )
                        else:
                            embed.add_field(name=f"Slot {i}", value="*Empty*", inline=False)

                    embed.set_footer(text=f"!party list \u00b7 !party switch <name> \u00b7 !party clear")
                    return await ctx.send(embed=embed)

                await ctx.send(
                    "\u26a0\ufe0f Invalid action. `!party view`, `!party add <slot> <box>`, "
                    "`!party remove <slot>`, `!party clear`, `!party list`, "
                    "`!party new <name>`, `!party switch <name>`, `!party delete <name>`.")

        except Exception as e:
            # \U0001f6a8 THIS CATCHES THE SILENT CRASH! \U0001f6a8
            print("\n\U0001f6a8 CRITICAL EXCEPTION IN !PARTY \U0001f6a8")
            import traceback
            traceback.print_exc()
            await ctx.send(f"\U0001f6a8 **Engine Crash Detected!**\n```py\n{e}\n```\nCheck your terminal for the full traceback.")

    @commands.command(name="movedex", aliases=["move", "attackinfo", "technique"])
    @checks.has_started()
    @checks.is_authorized()
    async def move_lookup(self, ctx, *, move_name: str):
        # Format the user's input to match the database standard (e.g., "Solar Beam" -> "solar-beam")
        formatted_name = move_name.lower().replace(" ", "-")
        
        async with aiosqlite.connect(DB_FILE) as db:

            # Query the universal move dictionary
            async with db.execute("""
                SELECT name, type, power, accuracy, damage_class, pp 
                FROM base_moves 
                WHERE name = ?
            """, (formatted_name,)) as cursor:
                move_data = await cursor.fetchone()
        
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
    @checks.partner_not_deployed()
    async def npc_encounter(self, ctx):
        user_id = str(ctx.author.id)
        
        # Prevent parallel skirmishes
        if hasattr(self, 'active_battles') and user_id in self.active_battles:
            return await ctx.send("🛑 **Tactical Override:** You are already engaged in an active skirmish! Finish it or flee before starting a new one.")
        

        # ==========================================
        # ECOLOGICAL STAMINA CHECK
        # ==========================================
        success, msg = await self.check_and_consume_energy(user_id, cost=10)

        if not success:
            # Player is out of energy! Send the error and cancel the battle.
            return await ctx.send(msg)
        
        # If success is True, the energy was successfully deducted. 
        # We can append the remaining energy text to the start of the battle log!
        combat_log = f"*{msg}*\n\n"
        # ==========================================

        try:
            async with aiosqlite.connect(DB_FILE) as db:
                async with db.cursor() as cursor:
                    # 1. Read the Player's Roster and calculate the Ecosystem Scale (Average Level)
                    scope, scope_params = await party_filter(db, user_id)
                    async with db.execute(f"""
                    SELECT cp.level
                    FROM user_party up
                    JOIN caught_pokemon cp ON up.instance_id = cp.instance_id
                    WHERE up.user_id = ? {scope}
                """, (user_id, *scope_params)) as cursor:
                        party_data = await cursor.fetchall()
                    
                    if not party_data:
                        await ctx.send("⚠️ You must assign at least one specimen to your fieldwork roster using `!party add 1 [Tag ID]` before engaging a rival team!")
                        return

                    team_size = len(party_data)
                    # Calculate the average level, ensuring it never drops below 1
                    avg_level = max(1, sum(row[0] for row in party_data) // team_size)

                    # 2. Generate the Rival Team Roster
                    # We exclude Legendaries, Mythicals and Ultra Beasts to ensure standard
                    # biological encounters. The Ultra Beast list is written out in
                    # constants rather than expressed as 793-806, because three of the ids
                    # in that range - Necrozma, Magearna and Marshadow - are not Ultra
                    # Beasts, and are already excluded here by the legendary/mythical test.
                    async with db.execute(f"""
                    SELECT pokedex_id, name
                    FROM base_pokemon_species
                    WHERE is_legendary = 0 AND is_mythical = 0 AND {ultra_beasts(negate=True)} AND {spawnable_forms()}
                    ORDER BY RANDOM() LIMIT ?
                """, (team_size,)) as cursor:
                        npc_species = await cursor.fetchall()
                    
                    npc_team = []
                    
                    # 3. Equip and Calculate the Rival Team
                    for poke_id, name in npc_species:
                        # Fetch Moves (Your existing code)
                        async with db.execute("""
                        SELECT move_name 
                        FROM species_movepool 
                        WHERE pokedex_id = ? AND learn_method = 'level-up' AND level_learned <= ? AND level_learned > 0
                        GROUP BY move_name ORDER BY MIN(level_learned) DESC LIMIT 4
                    """, (poke_id, avg_level)) as cursor:
                            raw_moves = [row[0] for row in await cursor.fetchall()]
                        while len(raw_moves) < 4:
                            if "tackle" not in raw_moves: raw_moves.append("tackle")
                            else: break 
                        

                        # --- Convert NPC moves to PP Dictionaries ---
                        npc_moves = []
                        for m_name in raw_moves:
                            async with db.execute("SELECT pp FROM base_moves WHERE name = ?", (m_name,)) as cursor:
                                pp_row = await cursor.fetchone()
                            pp_val = pp_row[0] if pp_row and pp_row[0] else 5
                            npc_moves.append({'name': m_name, 'pp': pp_val, 'max_pp': pp_val})

                        async with db.execute("SELECT type_name FROM base_pokemon_types WHERE pokedex_id = ?", (poke_id,)) as cursor:
                            npc_types = [row[0] for row in await cursor.fetchall()]
                                
                        # Pass the new dictionary array (npc_moves) into your builder!
                        combatant = await self.build_npc_combatant(db, poke_id, name, avg_level, npc_moves, npc_types)
                        npc_team.append(combatant)

                    # 4. Load the Player's Team and Calculate their Exact Stats
                    player_team = []
                    scope, scope_params = await party_filter(db, user_id)
                    async with db.execute(f"""
                    SELECT cp.instance_id, cp.pokedex_id, s.name, cp.level, cp.nature,
                        cp.iv_hp, cp.iv_attack, cp.iv_defense, cp.iv_sp_atk, cp.iv_sp_def, cp.iv_speed,
                        cp.ev_hp, cp.ev_attack, cp.ev_defense, cp.ev_sp_atk, cp.ev_sp_def, cp.ev_speed,
                        cp.move_1, cp.move_2, cp.move_3, cp.move_4, cp.is_shiny, cp.held_item, cp.gmax_factor, cp.ability, cp.experience, cp.gender, cp.happiness
                    FROM user_party up
                    JOIN caught_pokemon cp ON up.instance_id = cp.instance_id
                    JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                    WHERE up.user_id = ? {scope}
                    ORDER BY up.slot ASC
                """, (user_id, *scope_params)) as cursor:
                        for row in await cursor.fetchall():
                            tag, p_id, p_name, p_lvl, p_nature = row[0:5]
                            p_ivs = {'hp': row[5], 'attack': row[6], 'defense': row[7], 'sp_atk': row[8], 'sp_def': row[9], 'speed': row[10]}
                            p_evs = {'hp': row[11], 'attack': row[12], 'defense': row[13], 'sp_atk': row[14], 'sp_def': row[15], 'speed': row[16]}
                            raw_moves = [m for m in row[17:21] if m and m != 'none']
                            p_moves = []
                            for m_name in raw_moves:
                                async with db.execute("SELECT pp FROM base_moves WHERE name = ?", (m_name,)) as cursor:
                                    pp_row = await cursor.fetchone()
                                pp_val = pp_row[0] if pp_row and pp_row[0] else 5
                                p_moves.append({'name': m_name, 'pp': pp_val, 'max_pp': pp_val})

                            # Fetch the player's elemental typing for STAB and Defense!
                            async with db.execute("SELECT type_name FROM base_pokemon_types WHERE pokedex_id = ?", (p_id,)) as cursor:
                                p_types = [t[0] for t in await cursor.fetchall()]

                            is_shiny = row[21]
                            held_item = row[22]
                            gmax_factor = row[23]
                            ability = row[24]
                            experience = row[25]
                            
                            p_base = await fetch_base_stats(db, p_id)
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
                                'volatile_statuses': {},   # <--- GUARANTEES PARASITES HAVE A HOST!
                                'ivs': p_ivs,
                                'evs': p_evs,
                                'gender': normalize_gender(row[26]),
                                # Appended last in the SELECT, so it is read off the end
                                # rather than renumbering every index above it.
                                'happiness': row[-1]
                            })
                    
                    # ==========================================
                    # KEY ITEM SCANNER
                    # ==========================================
                        async with db.execute("""
                    SELECT item_name FROM user_inventory 
                    WHERE user_id = ? AND item_name IN ('dynamax-band', 'z-ring', 'mega-bracelet') AND quantity > 0
                """, (user_id,)) as cursor:
                            owned_key_items = [row[0] for row in await cursor.fetchall()]
                        
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
            return

        # 5. Initialize the Temporary Battle State Memory
        print("DEBUG: Database closed. Entering Step 5: State Initialization...")
        try:
            self.active_battles[user_id] = {
                'player_team': snapshot_team_items(player_team),
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
            combat_log = await trigger_single_entry_ability(p_lead, n_lead, "Your", state, combat_log)

            # 2. Fire the NPC's ability hook
            combat_log = await trigger_single_entry_ability(n_lead, p_lead, "The rival's", state, combat_log)
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
                n_hazards=state.get('npc_hazards'),
                p_name=p_lead.get('name'), p_level=p_lead.get('level'),
                p_gender=p_lead.get('gender'), n_gender=n_lead.get('gender'),
                n_name=n_lead.get('name'), n_level=n_lead.get('level'),
                p_aura=battle_render.aura_for(state.get('adaptation'), p_lead),
                biome=state.get('warden_biome')
            )

            # Attach the file to the embed
            # Dynamically grab the new randomized filename!
            if battle_file:
                embed.set_image(url=f"attachment://{battle_file.filename}")
            print("DEBUG: Battle scene generated and attached.")

            print("file generated and attached")
            
            print("DEBUG: Sending final payload to Discord...")
            dashboard_view = await BattleDashboard.create(self, user_id, ctx)
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