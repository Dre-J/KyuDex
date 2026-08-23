"""
Trainer levels, derived from fieldwork already counted.

**NOTHING HERE IS STORED.** A trainer's level is a pure function of their lifetime
contribution points, recomputed on every read. That is the same discipline
`expedition_yield` and `energy_yield` follow, and for the same reason: a stored level is
a second copy of a number the database already holds, and two copies of one number drift.
There is no migration, no backfill, and no column that can disagree with the ledger.

**WHY CONTRIBUTION AND NOT A NEW CURRENCY.** `guild_members.contribution_points` is
already written from five places and already populated for every registered trainer:

    clearing a hazard   +10
    purifying pollution  +5
    planting             +1
    cleaning             +1
    catching             +1

That is habitat fieldwork, which is what the game is about, and it means levels arrive
with history rather than starting everybody at zero on the day the feature ships.

**WHY NOT DIRECTIVES.** They were the obvious candidate and they are the wrong one.
Directives are issued from `encrypted-field-notes`, a ten-percent drop off an NPC duel,
so tying levels to them gates progress behind an RNG item - a player can duel for an
hour and gain nothing. They are also already paid, in tokens or items, so levelling off
them would quietly make the level the real prize and devalue the reward attached. They
are worth a BONUS (see DIRECTIVE_CONTRIBUTION) and not worth being the axis.

**THE SCOPE FIX.** Contribution is stored per guild, and a trainer card is per person -
the same trainer would otherwise hold a different level in every server they play in.
`total_contribution` sums across guilds, which is exactly what `!leaderboard global`
already computes.
"""

import math

# ==========================================
# THE CURVE
# ==========================================
# level = floor(sqrt(total)), so the threshold for level N is N*N. Square-root shaped
# because the early levels should arrive quickly enough to feel like a system that is
# working, and the late ones should cost real time:
#
#     Lv 1 at 1        Lv 10 at 100      Lv 22 at 484
#     Lv 50 at 2,500   Lv 100 at 10,000
#
# The busiest trainer on the live database sits on 490 points, which lands at Lv 22 and
# leaves the top three-quarters of the range still ahead of them.
MAX_TRAINER_LEVEL = 100

# What a completed field directive is worth. Set to the largest single action in the
# table above so a directive is the efficient route to a level without being the only
# one - somebody who never finds a Field Note still levels, just more slowly.
DIRECTIVE_CONTRIBUTION = 25


def level_for(contribution):
    """The trainer level a lifetime contribution total earns. Never raises."""
    total = max(0, int(contribution or 0))
    return min(MAX_TRAINER_LEVEL, int(math.isqrt(total)))


def contribution_for_level(level):
    """The lifetime total needed to REACH `level`. The inverse of `level_for`."""
    return max(0, int(level)) ** 2


def progress(contribution):
    """
    `(level, into_level, span)` - a level and how far through it the trainer is.

    `into_level` and `span` are the numerator and denominator of the XP bar, so the bar
    measures progress through the CURRENT level rather than towards an absolute total.
    A bar that filled against the lifetime figure would crawl more slowly every level,
    which is the opposite of what a progress bar is for.

    At the cap the bar is shown full rather than empty, because there is nothing left to
    fill and an empty bar at level 100 reads as a bug.
    """
    total = max(0, int(contribution or 0))
    level = level_for(total)
    if level >= MAX_TRAINER_LEVEL:
        span = contribution_for_level(MAX_TRAINER_LEVEL) - contribution_for_level(
            MAX_TRAINER_LEVEL - 1)
        return level, span, span

    floor_ = contribution_for_level(level)
    ceiling = contribution_for_level(level + 1)
    return level, total - floor_, ceiling - floor_


# ==========================================
# TITLES
# ==========================================
# Read from the level, never stored. Lowest first; `title_for` takes the last one whose
# threshold has been passed, so adding a rank is one line and needs no migration.
TRAINER_TITLES = (
    (0,  "Field Volunteer"),
    (3,  "Survey Assistant"),
    (6,  "Field Researcher"),
    (10, "Habitat Steward"),
    (15, "Ecologist"),
    (22, "Senior Ecologist"),
    (30, "Regional Warden"),
    (40, "Conservation Lead"),
    (55, "Biome Custodian"),
    (70, "Principal Ecologist"),
    (85, "Ecosystem Architect"),
    (100, "Apex Custodian"),
)


def title_for(level):
    """The rank a level carries."""
    level = max(0, int(level or 0))
    earned = TRAINER_TITLES[0][1]
    for threshold, name in TRAINER_TITLES:
        if level >= threshold:
            earned = name
        else:
            break
    return earned


# ==========================================
# WHAT A LEVEL IS FOR
# ==========================================
# A level that gates nothing is decoration, and this game already has a progression
# spine that gates content: the visas. So the level buys a bigger ENERGY RESERVE - it
# does not unlock anything new, it lets somebody who has done the fieldwork bank more of
# their time before it stops accruing.
#
# THE BASE IS WHAT EVERYONE ALREADY HAS. 200 is the current flat cap, so nobody is
# nerfed by this landing; the tiers are all upside.
ENERGY_BANK_BASE = 200
ENERGY_BANK_PER_TIER = 25
ENERGY_BANK_TIER_EVERY = 5      # levels per tier
ENERGY_BANK_CEILING = 400       # eight tiers, reached at level 40


def energy_bank_cap(level):
    """
    How much Field Energy this trainer can bank, given their level.

    Bounded at both ends on purpose: nobody starts below today's cap, and nobody ends up
    with a reserve so deep that the meter stops meaning anything.
    """
    tiers = max(0, int(level or 0)) // ENERGY_BANK_TIER_EVERY
    return min(ENERGY_BANK_CEILING, ENERGY_BANK_BASE + ENERGY_BANK_PER_TIER * tiers)


def next_bank_tier(level):
    """
    `(level_needed, cap_then)` for the next reserve increase, or None at the ceiling.

    So the profile can say what the next level is actually worth, rather than leaving a
    player to work out that the number only moves every fifth level.
    """
    level = max(0, int(level or 0))
    if energy_bank_cap(level) >= ENERGY_BANK_CEILING:
        return None
    needed = (level // ENERGY_BANK_TIER_EVERY + 1) * ENERGY_BANK_TIER_EVERY
    return needed, energy_bank_cap(needed)


# ==========================================
# READING THE LEDGER
# ==========================================
async def total_contribution(db, user_id):
    """
    A trainer's lifetime contribution across every server they play in.

    SUMMED, not read from one guild. Contribution is stored per guild because the local
    leaderboard needs it that way; a trainer is one person, and a level that changed
    depending on which server you typed `!profile` in would be the same defect the
    timezone work removed from evolutions.
    """
    try:
        async with db.execute(
                "SELECT COALESCE(SUM(contribution_points), 0) FROM guild_members "
                "WHERE user_id = ?", (str(user_id),)) as cursor:
            row = await cursor.fetchone()
    except Exception:
        return 0
    return int(row[0] or 0) if row else 0


async def trainer_level(db, user_id):
    """`(level, title, contribution)` for one trainer. One read, no writes."""
    total = await total_contribution(db, user_id)
    level = level_for(total)
    return level, title_for(level), total
