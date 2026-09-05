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
    """The type this specimen would become, chosen or defaulted."""
    stored = str((specimen or {}).get('tera_type') or '').strip().lower()
    if stored and is_element(stored):
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


def terastallise(specimen):
    """
    Bring the crystal out. Returns the type it became, or None if it could not.

    Nothing is written to `types`: see the module docstring. The marker is what every
    reader asks about.
    """
    element = tera_type_of(specimen)
    if not specimen or not element:
        return None
    specimen[TERA_MARKER] = True
    return element


def battle_types(specimen, terrain='none'):
    """
    The elements this specimen counts as RIGHT NOW - the door the type chart reads.

    Terastallised typing REPLACES the lot, which is the whole mechanic: a Fire/Flying
    that Teras to Water is Water, singular, and stops being weak to Rock.

    Mimicry is asked second, and only when the crystal is not out - Tera outranks a
    terrain, and asking both would give a Terastallised specimen two typings.
    """
    element = active_tera_type(specimen)
    if element:
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
