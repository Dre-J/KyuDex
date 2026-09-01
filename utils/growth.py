"""
What a specimen gains from doing things: experience, and friendship.

Two mechanics that had nothing in common until they turned out to have the same shape -
an amount decided by what happened, bent by what the specimen is holding - and the same
problem: **five places award experience and only one place had ever written to
`happiness`.**

**THE FRIENDSHIP AUDIT, which is what this module was written for.** `caught_pokemon`
has carried a `happiness` column since the beginning. `check_evolution_trigger` gates on
it - Golbat wants 160, Pichu wants 220, Espeon and Umbreon want 160 and a sky - and the
box browser draws a bond meter from it. Exactly one line in the codebase ever raised it:
the EV-lowering berries in `!vitamins`, at a flat +10 apiece. So:

  * a message with a partner out raised nothing
  * winning a battle raised nothing
  * a Rare Candy raised nothing
  * a vitamin raised nothing
  * no Soothe Bell existed to raise anything faster

...which means every friendship evolution in the game was reachable only by feeding one
specimen dozens of bitter berries, and most players would never have seen one fire.

**THE BANDS ARE THE GAMES' OWN.** Friendship gains shrink as friendship grows - a lot at
the bottom, a little at the top - which is what stops the last fifty points arriving as
fast as the first fifty. One table, read by every source, so the berry path and the
battle path cannot come to disagree about what a point is worth.

**THE SOOTHE BELL ROUNDS UP.** The games floor it, which makes the bell a no-op on a
gain of one - and a message is a gain of one. Rounded up instead, so the item a trainer
bought to speed this up always does something.
"""
import math

from utils.constants import MAX_HAPPINESS

# ==========================================
# 🥚 EXPERIENCE
# ==========================================
# Read off the HOLDER, not off the trainer, so a Lucky Egg boosts the one specimen
# carrying it rather than the whole team - which is the difference between an item and a
# server setting.
XP_MULTIPLIER_ITEMS = {'lucky-egg': 1.5}


def normalise_item(item):
    """`'Lucky Egg'`, `'lucky egg'` and `None` all become something comparable."""
    return str(item or 'none').strip().lower().replace(' ', '-')


def xp_multiplier(held_item):
    return XP_MULTIPLIER_ITEMS.get(normalise_item(held_item), 1.0)


def boosted_xp(amount, held_item=None):
    """
    `amount` after whatever the specimen is holding has had its say.

    Floored, and never below the unboosted figure: a multiplier of 1.0 has to be exactly
    a no-op, or every award in the bot would drift by a point depending on rounding.
    """
    amount = int(amount or 0)
    if amount <= 0:
        return amount
    return max(amount, int(amount * xp_multiplier(held_item)))


# ==========================================
# ❤️ FRIENDSHIP
# ==========================================
# The same 255 the bond meter divides by, imported rather than typed again - the column
# is called `happiness` and the mechanic is called friendship, and the one thing that
# must not differ between the two names is the ceiling.
MAX_FRIENDSHIP = MAX_HAPPINESS

# The bands the games use, as (upper bound, index). Under 100 is generous, 100-199 less
# so, 200 and up least of all.
FRIENDSHIP_BANDS = (100, 200, MAX_FRIENDSHIP + 1)

# What each source is worth, per band. Straight out of the games' table for Generation 6
# onwards, with two entries this world had to name for itself:
#
#   walk     the games give +1 for every 128 steps. There is no overworld here, so the
#            equivalent is a message sent with the specimen out as partner - the same
#            trigger passive experience already uses, on the same one-minute cooldown.
#   battle   the games raise friendship on LEVEL UP rather than on winning, and a battle
#            here can pay experience without tipping a level. Winning is the moment a
#            trainer would expect it, so winning is what pays.
FRIENDSHIP_GAINS = {
    'level-up': (3, 2, 2),      # a Rare Candy is a level-up, one per candy
    'vitamin':  (5, 3, 2),      # Protein, Iron, Calcium, Zinc, Carbos, HP Up
    'ev-berry': (10, 5, 2),     # Pomeg, Kelpsy, Qualot, Hondew, Grepa, Tamato
    'walk':     (1, 1, 1),      # a message with the specimen out
    'battle':   (3, 2, 2),      # surviving a won battle
}

# The item that makes all of it faster, and by how much.
SOOTHE_BELL = 'soothe-bell'
SOOTHE_BELL_MULTIPLIER = 1.5


def friendship_band(current):
    """Which of the three bands a specimen at this friendship sits in."""
    current = max(0, min(MAX_FRIENDSHIP, int(current or 0)))
    for index, ceiling in enumerate(FRIENDSHIP_BANDS):
        if current < ceiling:
            return index
    return len(FRIENDSHIP_BANDS) - 1


def friendship_gain(source, current, held_item=None):
    """
    How much friendship one `source` is worth to a specimen at `current`, right now.

    CLAMPED TO THE CEILING here rather than by the caller. Every caller would otherwise
    need the same `min(gain, 255 - current)`, and the one that forgot it would write 260
    into a column the bond meter divides by 255.
    """
    per_band = FRIENDSHIP_GAINS.get(source)
    if not per_band:
        return 0
    gain = per_band[friendship_band(current)]
    if normalise_item(held_item) == SOOTHE_BELL:
        # Rounded UP. Floored, as the games do it, a bell on a gain of one is a bell that
        # does nothing at all, and a message is a gain of one.
        gain = math.ceil(gain * SOOTHE_BELL_MULTIPLIER)
    return max(0, min(gain, MAX_FRIENDSHIP - max(0, int(current or 0))))


def friendship_total(source, current, held_item=None, times=1):
    """
    `times` helpings of one source, banded as it climbs.

    Ten berries at once are not ten times the first berry: the third might cross out of
    the generous band and be worth half as much. Applied one at a time so that a stack
    fed in one command and the same stack fed one at a time come to the same number.
    """
    running = max(0, int(current or 0))
    gained = 0
    for _ in range(max(0, int(times))):
        step = friendship_gain(source, running, held_item)
        if step <= 0:
            break
        running += step
        gained += step
    return gained


async def raise_friendship(db, instance_id, source, current=None, held_item=None,
                           times=1):
    """
    Apply the gain and return it. Does NOT commit - the caller owns the transaction.

    `current` and `held_item` are read from the row when they are not handed in, because
    half the call sites have them already and half do not, and the ones that do should
    not have to pay for a second query.
    """
    if not instance_id:
        return 0
    if current is None or held_item is None:
        async with db.execute(
                "SELECT happiness, held_item FROM caught_pokemon WHERE instance_id = ?",
                (instance_id,)) as cursor:
            row = await cursor.fetchone()
        if not row:
            return 0
        current = row[0] if current is None else current
        held_item = row[1] if held_item is None else held_item

    gained = friendship_total(source, current, held_item, times)
    if gained:
        await db.execute(
            "UPDATE caught_pokemon SET happiness = MIN(?, happiness + ?) "
            "WHERE instance_id = ?", (MAX_FRIENDSHIP, gained, instance_id))
    return gained


def bond_label(happiness):
    """
    The bond meter, in one place.

    Three copies of these four bands existed - the box browser, `!party view` and the
    old `!view` embed - and a fourth was about to be written for the friendship messages
    below.
    """
    happiness = max(0, int(happiness or 0))
    if happiness < 50:
        return "🤍🤍🤍 (Acclimating)"
    if happiness < 150:
        return "❤️🤍🤍 (Trusting)"
    if happiness < 220:
        return "❤️❤️🤍 (Bonded)"
    return "❤️❤️❤️ (Symbiotic)"
