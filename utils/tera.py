"""
Terastallisation: what a specimen counts as once the crystal comes out.

**THE MECHANIC IS TWO RULES AND EVERYTHING ELSE IS PLUMBING.** A Terastallised specimen
IS its Tera type - one type, replacing whatever it was - and its STAB is worked out from
both the old typing and the new one. Both live here so `calculate_damage` gains two calls
rather than two branches.

**A SPECIMEN WITH NO TERA TYPE ON FILE FALLS BACK TO ITS PRIMARY.** That is the games'
rule and it is the friendly one: every specimen can Terastallise into what it already is
from the day the feature lands, and Tera Shards buy a DIFFERENT type rather than buying
the mechanic. `tera_type` being NULL means "the obvious one", not "cannot".

**WHAT THIS DOES NOT REACH.** The typing is returned rather than written onto the
specimen, exactly as `mimicry_types` is and for the same reason - there is nowhere that
would put the original back. So it reaches the damage calculation, which is where the
chart and STAB are read, and NOT the places that read `specimen['types']` directly:
entry hazards most notably, so a Terastallised specimen still takes Stealth Rock as its
original typing. Documented rather than hidden; fixing it means auditing every direct
reader and belongs in its own change.
"""
from utils.constants import ADAPTABILITY_STAB, TYPE_CHART, TERA_SHARD_TYPES

# The flag on a combatant, set when the crystal comes out and never unset - Tera lasts the
# rest of the battle in the games, which is what makes it a decision rather than a toggle.
TERA_MARKER = 'terastallised'

# Same-type attack, once the Tera type and an original type agree. The ordinary bonus is
# 1.5 (2.0 with Adaptability); this is what it becomes when both halves match.
TERA_STAB = 2.0
TERA_STAB_ADAPTABILITY = 2.25

# What it costs to change a specimen's Tera type, in shards of the type being changed TO.
# The games' number. Kept deliberately: it is recognisable, and a smaller one would make
# the choice weightless.
SHARDS_PER_CHANGE = 50

# The key item that gates the mechanic, beside the Mega Bracelet, Dynamax Band and Z-Ring.
TERA_ORB = 'tera-orb'


def shard_for(element):
    """`fire` -> `fire-tera-shard`, or None for anything that is not an element."""
    shard = f"{str(element or '').strip().lower()}-tera-shard"
    return shard if shard in TERA_SHARD_TYPES else None


def element_of(shard):
    """`fire-tera-shard` -> `fire`, or None."""
    return TERA_SHARD_TYPES.get(str(shard or '').strip().lower())


def is_element(element):
    return str(element or '').strip().lower() in TYPE_CHART


def default_tera_type(specimen):
    """
    What this specimen Terastallises into when nothing has been chosen for it.

    Its primary type - the games' rule. A specimen with no typing at all comes back None
    and simply cannot Terastallise, which is a data problem rather than a game rule.
    """
    types = (specimen or {}).get('types') or []
    return types[0] if types else None


def tera_type_of(specimen):
    """
    The type this specimen would become: forced, then chosen, then defaulted.

    A FORCED type outranks whatever is on file. Terapagos is always Stellar and an
    Ogerpon is always its mask's element - neither can be bought out of with shards, and
    a value stored before the rule existed must not win.
    """
    forced = (species_rule(specimen) or {}).get('forced')
    if forced:
        return forced
    stored = str((specimen or {}).get('tera_type') or '').strip().lower()
    if stored and (is_element(stored) or stored == STELLAR):
        return stored
    return default_tera_type(specimen)


def is_terastallised(specimen):
    return bool((specimen or {}).get(TERA_MARKER))


def active_tera_type(specimen):
    """The Tera type IF the crystal is out, else None. The question the rules ask."""
    return tera_type_of(specimen) if is_terastallised(specimen) else None


def may_terastallise(specimen, key_items=None, adaptation=None):
    """
    Whether the button should be offered.

    Three gates, matching every other gimmick: the trainer holds the key item, the side
    has not spent its adaptation, and the specimen has a type to become.
    """
    if not specimen:
        return False
    if (adaptation or {}).get('used'):
        return False
    if key_items is not None and not (key_items or {}).get(TERA_ORB.replace('-', '_')):
        return False
    return tera_type_of(specimen) is not None


# How far a stat stage may be pushed. Embody Aspect is a +1 like any other, and a
# specimen already at the ceiling gains nothing rather than overflowing.
STAGE_CEILING = 6


def terastallise(specimen):
    """
    Bring the crystal out. Returns the type it became, or None if it could not.

    Nothing is written to `types`: see the module docstring. The marker is what every
    reader asks about.

    **THE SPECIES RULE IS READ FIRST AND APPLIED HERE**, except the form change, which
    needs the database and belongs to the caller - see `form_for`. Reading the rule before
    anything is written matters: it is keyed on the specimen's NAME, and a caller that
    changed the form first would look up a rule for the form it had already become.
    """
    element = tera_type_of(specimen)
    if not specimen or not element:
        return None
    specimen[TERA_MARKER] = True

    rule = species_rule(specimen)
    if rule and rule.get('ability'):
        # **EMBODY ASPECT REPLACES THE ABILITY**, and Teraform Zero replaces Tera Shell.
        # Written onto the specimen rather than returned, because every reader of an
        # ability asks the specimen.
        specimen['ability'] = rule['ability']
    if rule and rule.get('boost'):
        stat, stages = rule['boost']
        current = (specimen.setdefault('stat_stages', {})).get(stat, 0)
        specimen['stat_stages'][stat] = min(STAGE_CEILING, current + stages)
    return element


def form_for(specimen):
    """
    The species row this specimen becomes on Terastallising, or None.

    Only Terapagos has one - `terapagos-terastal` unfolds into `terapagos-stellar`, which
    has been sitting in `base_pokemon_species` since the import. Separated from
    `terastallise` because changing a form needs the database and that function does not.
    """
    return (species_rule(specimen) or {}).get('form')


def species_flavour(specimen):
    """What to say about a species that does more than change type. "" for the rest."""
    return (species_rule(specimen) or {}).get('flavour', '')


def battle_types(specimen, terrain='none'):
    """
    The elements this specimen counts as RIGHT NOW - the door the type chart reads.

    Terastallised typing REPLACES the lot, which is the whole mechanic: a Fire/Flying
    that Teras to Water is Water, singular, and stops being weak to Rock.

    Mimicry is asked second, and only when the crystal is not out - Tera outranks a
    terrain, and asking both would give a Terastallised specimen two typings.
    """
    element = active_tera_type(specimen)
    # **STELLAR IS THE EXCEPTION.** It changes what a specimen HITS with and not what it
    # counts as - a Stellar Terapagos is still whatever it was, defensively.
    if element and element != STELLAR:
        return [element]
    # Imported here rather than at module scope: utils.formulas imports this module, and
    # asking for it at the top would close the circle.
    from utils.formulas import mimicry_types
    return mimicry_types(specimen, terrain)


def stab_multiplier(attacker, move_type, adaptability=False, terrain='none'):
    """
    Same-type attack bonus, with Tera's two-sided rule.

    **IT IS NOT "DOES THE MOVE MATCH MY TYPE" ANY MORE.** A Terastallised specimen keeps
    the bonus on what it USED to be as well as on what it has become, and gets more than
    either when the two agree:

        move matches the Tera type AND an original    2.0   (2.25 with Adaptability)
        move matches one of them                      1.5   (2.0  with Adaptability)
        move matches neither                          1.0

    Read against the ORIGINAL typing rather than `battle_types`, which returns only the
    Tera type once the crystal is out - that is correct for the chart and would lose the
    distinction between the first two rows here.
    """
    stellar = stellar_boost(attacker, move_type, adaptability, terrain)
    if stellar is not None:
        return stellar

    from utils.formulas import mimicry_types
    ordinary = ADAPTABILITY_STAB if adaptability else 1.5

    originals = mimicry_types(attacker, terrain)
    element = active_tera_type(attacker)

    matches_original = move_type in originals
    matches_tera = bool(element) and move_type == element

    if matches_tera and matches_original:
        return TERA_STAB_ADAPTABILITY if adaptability else TERA_STAB
    if matches_tera or matches_original:
        return ordinary
    return 1.0


def shards_held(inventory, element):
    """How many shards of one element a trainer is holding."""
    shard = shard_for(element)
    return int((inventory or {}).get(shard, 0)) if shard else 0


def change_is_affordable(inventory, element, cost=SHARDS_PER_CHANGE):
    """`(affordable, held, needed)` for changing a specimen to `element`."""
    held = shards_held(inventory, element)
    return held >= cost, held, cost


# ==========================================
# THE STELLAR TYPE
# ==========================================
# **STELLAR IS THE EXCEPTION TO EVERY RULE ABOVE**, which is why it is written out here
# rather than folded into them:
#
#   * it does NOT replace the defensive typing - a Stellar Terapagos is still whatever it
#     was, and takes damage as that;
#   * its offence is a ONE-SHOT per element: the first move of each type gets the boost
#     and every one after it is ordinary;
#   * a Stellar MOVE is super effective against anything that has Terastallised and
#     neutral against everything else - a matchup that lives nowhere in the type chart.
#
# It cannot be bought with shards. Terapagos is the only thing that has it, which is the
# games' rule and the reason `!tera` never offers it.
STELLAR = 'stellar'

# The first move of each element gets this; matching an original type is worth more.
STELLAR_STAB = 2.0
STELLAR_OTHER = 1.2

# Which elements this specimen has already spent its Stellar boost on. Kept ON THE
# SPECIMEN rather than in the battle state, because it belongs to the specimen and has to
# survive a switch out and back the way the Tera marker does.
STELLAR_SPENT = '_stellar_spent'


def is_stellar(specimen):
    """Whether this specimen's Tera type is Stellar, chosen or forced."""
    return tera_type_of(specimen) == STELLAR


def stellar_boost(attacker, move_type, adaptability=False, terrain='none'):
    """
    What Stellar pays for this move, and SPENDS the element if it pays.

    Returns None when Stellar is not in play, so the caller falls through to the ordinary
    rules. Mutates the attacker deliberately: "once per type" has to be remembered
    somewhere, and the specimen is the thing that remembers.
    """
    if not is_terastallised(attacker) or not is_stellar(attacker):
        return None

    from utils.formulas import mimicry_types
    originals = mimicry_types(attacker, terrain)
    spent = attacker.setdefault(STELLAR_SPENT, set())

    if move_type in spent:
        # Already cashed in. From here it is an ordinary move of its own element.
        ordinary = ADAPTABILITY_STAB if adaptability else 1.5
        return ordinary if move_type in originals else 1.0

    spent.add(move_type)
    return STELLAR_STAB if move_type in originals else STELLAR_OTHER


def stellar_effectiveness(move_type, defender):
    """
    What a STELLAR-type move does, which the type chart has no row for.

    Super effective against anything that has Terastallised - the type exists to punish
    the mechanic - and neutral against everything else. None when the move is not Stellar,
    so the caller reads the chart as usual.
    """
    if str(move_type or '').lower() != STELLAR:
        return None
    return 2.0 if is_terastallised(defender) else 1.0


# ==========================================
# WHAT TERASTALLISING CHANGES ABOUT A SPECIES
# ==========================================
# Two species do more than change type, and both were sitting in the database waiting:
# `terapagos-stellar` (10277) and its Teraform Zero have existed since the import, and
# Ogerpon's four masks each have an ability that only appears once the crystal is out.
#
#   forced   the Tera type this species always gets, whatever is on file
#   form     the species row it becomes
#   ability  what it starts answering to
#   boost    (stat, stages) raised on transforming
TERA_SPECIES_RULES = {
    'terapagos-terastal': {
        'forced': STELLAR, 'form': 'terapagos-stellar', 'ability': 'teraform-zero',
        'flavour': 'unfolded into its Stellar Form',
    },
    # **EMBODY ASPECT.** Ogerpon's ability changes the moment it Terastallises, and which
    # stat it raises depends on the mask it wears. Its Tera type is forced to the mask's
    # element - an Ogerpon cannot Terastallise into anything else, which is why no shard
    # buys it one.
    'ogerpon': {
        'forced': 'grass', 'ability': 'embody-aspect-teal',
        'boost': ('speed', 1), 'flavour': 'embodied the Teal Mask',
    },
    'ogerpon-wellspring-mask': {
        'forced': 'water', 'ability': 'embody-aspect-wellspring',
        'boost': ('sp_def', 1), 'flavour': 'embodied the Wellspring Mask',
    },
    'ogerpon-hearthflame-mask': {
        'forced': 'fire', 'ability': 'embody-aspect-hearthflame',
        'boost': ('attack', 1), 'flavour': 'embodied the Hearthflame Mask',
    },
    'ogerpon-cornerstone-mask': {
        'forced': 'rock', 'ability': 'embody-aspect-cornerstone',
        'boost': ('defense', 1), 'flavour': 'embodied the Cornerstone Mask',
    },
}


def species_rule(specimen):
    """The Tera rule for the form this specimen is standing as, or None."""
    return TERA_SPECIES_RULES.get(
        str((specimen or {}).get('name') or '').lower().strip())


# ==========================================
# THE EXCHANGE
# ==========================================
# **THE TWO WAYS TO EARN A SHARD BOTH PAY IN TYPES NOBODY ASKED FOR.** A field mission
# yields its habitat's element and a defeated specimen leaves its own, so a trainer
# chasing fifty Water Shards accumulates piles of Grass and Bug on the way. Without
# somewhere for those to go they are dead weight; with one, every shard is worth
# something even when it is the wrong one.
#
# Four to one, and the loss is the point: the exchange is a floor under bad luck, not a
# way around the fifty. Converting a full fifty of one element into a full fifty of
# another costs two hundred, which is far more than simply going and earning them.
EXCHANGE_RATE = 4


def parse_exchange(text):
    """
    `(from, to, count)` for `grass fire` or `grass fire 3`, else None.

    Read from the RAW words rather than a flattened blueprint name, because
    `!refine grass fire` arrives at the command as `grass-fire` and there is no way back
    from that - `grass-fire` is indistinguishable from a hyphenated blueprint.

    None for anything that is not two elements, which is what lets this share a verb with
    the blueprints: an unrecognised pair simply falls through to the recipe lookup.
    """
    words = str(text or '').replace('-', ' ').split()
    if len(words) not in (2, 3):
        return None

    source, target = words[0].lower(), words[1].lower()
    if not (is_element(source) and is_element(target)):
        return None
    if source == target:
        # Not a refusal to report - a trainer who typed the same element twice meant
        # something, and the command says what. Returned so the caller can say it.
        return source, target, 0

    count = 1
    if len(words) == 3:
        if not words[2].isdigit():
            return None
        count = int(words[2])
    return source, target, count


def exchange_cost(count, rate=EXCHANGE_RATE):
    """How many shards `count` of another element costs."""
    return max(0, int(count)) * rate


# ==========================================
# THE SEED
# ==========================================
# **THE TERA ORB SHIPPED BEHIND A DOOR WITH NO KEY.** `crystal-seed` had a catalogue row
# and a place in `LAB_BLUEPRINTS`, and nothing anywhere in the world granted one - so the
# Orb was uncraftable and the gimmick unreachable by any route.
#
# The other three gimmick materials are anomaly rolls on a PvE victory, and they are rolls
# because Mega, Z and Dynamax have no economy of their own to draw on. Tera does. So its
# material is **made of** the currency it unlocks: one shard of each of the eighteen
# elements, fused.
#
# That makes BREADTH the price rather than luck, which is the one thing this economy
# actually needs. A trainer cannot farm a single habitat to the Orb - and the five
# expedition sectors between them cover all eighteen elements exactly once, so the sector
# map is also the map of what is still missing. Whatever luck is left over is answered by
# the exchange above: four of a drowning element buy the one that never turned up.
#
# Eighteen is deliberately UNDER `SHARDS_PER_CHANGE`. The door costs less than the first
# room, or nobody reaches the mechanic to spend fifty on it.
SEED_ITEM = 'crystal-seed'
SEED_SHARDS_EACH = 1


def seed_elements():
    """Every element a seed wants, which is every element a shard exists for."""
    return sorted(TERA_SHARD_TYPES.values())


def parse_seed(text):
    """
    How many seeds `seed`, `seeds 2` or `crystal seed` asks for, else None.

    Shares `!refine` with the blueprints and the exchange, and cannot collide with
    either: `crystal-seed` is a MATERIAL rather than a recipe, so no blueprint answers to
    this name, and neither word is an element.
    """
    words = str(text or '').replace('-', ' ').lower().split()
    if words[:1] == ['crystal']:
        words = words[1:]
    if words[:1] not in (['seed'], ['seeds']):
        return None

    if len(words) == 1:
        return 1
    if len(words) == 2 and words[1].isdigit():
        return int(words[1])
    return None


def seed_recipe(count=1, each=SEED_SHARDS_EACH):
    """`{element: shards}` for `count` seeds - one of everything, times the count."""
    wanted = max(0, int(count)) * each
    return {element: wanted for element in seed_elements()}


def seed_shortfall(held, count=1, each=SEED_SHARDS_EACH):
    """
    `[(element, has, needs)]` for every element the ledger is short of.

    `held` is keyed by ITEM NAME, the shape a `user_inventory` read returns, rather than
    by element - so the caller passes the rows straight in.
    """
    short = []
    for element, needed in sorted(seed_recipe(count, each).items()):
        has = int(held.get(shard_for(element), 0) or 0)
        if has < needed:
            short.append((element, has, needed))
    return short


# ==========================================
# WHAT A WARDEN IS WORTH IN SHARDS
# ==========================================
# **THE SECTORS ARE ALREADY A MAP OF THE ELEMENTS.** `EXPEDITION_BIOMES` gives each of the
# five a tuple of types, and between them those tuples cover all eighteen exactly once -
# no duplicates and none missing. So a Warden needs no element invented for it: it pays
# its sector's, and which sector to go and beat for a given element is a thing a trainer
# can look up rather than guess.
#
# That makes apex - dragon, and nothing else at all - the reliable route to the element
# that is otherwise the hardest to steer towards. Which is the right shape for the last
# sector a Warden opens.
#
# **PER ELEMENT, NOT PER BUNDLE.** Sprawl has six elements and apex has one, so a fixed
# total per Warden would make apex six times better per element - and fifty of ONE is
# what a type change costs. Equal per element is the only rule that treats the five
# sectors alike.
#
# A first clear is the large one. Repeat clears - the sparring loop that already pays 500
# tokens - pay a quarter of it, which keeps a Warden worth re-fighting without turning
# the deepest sector into a shard farm: fifty Dragon is seventeen apex clears at that
# rate, against a real team, and energy is spent on every one of them.
WARDEN_FIRST_CLEAR_SHARDS = 12
WARDEN_REPEAT_SHARDS = 3


def warden_bundle(biome, first_clear=True):
    """`{shard: quantity}` a sector's Warden pays, or `{}` for a sector with no map."""
    from utils.constants import EXPEDITION_BIOMES

    sector = EXPEDITION_BIOMES.get(str(biome or '').strip().lower())
    if not sector:
        return {}

    each = WARDEN_FIRST_CLEAR_SHARDS if first_clear else WARDEN_REPEAT_SHARDS
    return {shard_for(element): each for element in sorted(sector['types'])
            if shard_for(element)}


def describe_bundle(bundle):
    """`12x Water · 12x Ice`, for the victory screen."""
    return " · ".join(f"{qty}x {(element_of(shard) or '').title()} Shards"
                      for shard, qty in bundle.items())
