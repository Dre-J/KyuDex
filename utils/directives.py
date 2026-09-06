"""Crediting a field directive, from wherever the thing actually happened.

A directive counts an event, and the event usually has more than one door. Evolution
has three: `!evolve` with a stone, the confirmation button after a battle level-up, and
the confirmation button after a field mission returns. Two of them credited the
Kinetic Maturation Study and the third did not, so a trainer who evolved a specimen
through `!return` watched a directive sit at 0/1 while the same evolution through
`!evolve` ticked over.

Nobody would find that by reading the code, because each copy is correct on its own.
What was missing was a fourth caller of a function that did not exist. So it exists.

The matching rule is worth stating once, since all three copies had it and it is easy
to get subtly wrong: a directive names the species BEFORE it evolved, or the literal
`any`. Charmander evolving into Charmeleon credits a Charmander directive, not a
Charmeleon one - the target is what you had to go and find.

Culling arrived here for the same reason and with the same shape of fault. Its one copy
sat at the point a battle ENDED rather than at the knockout, so it read whichever
specimen happened to be on the field then: in a multi-opponent battle every faint but
the last was free. Ten directives had been issued on the live database and not one had
ever been completed, so the Eco Token grant they exist to pay had never once been paid.
"""

import random

from utils.constants import (BREEDING_ITEMS, EVOLUTION_ITEMS, GRIND_ITEMS,
                             EQUIPMENT_CATALOG)
from utils.tera import shard_for

EVOLUTION_OBJECTIVE = 'trigger_mutation'
CULL_OBJECTIVE = 'cull_type'
SURVEY_OBJECTIVE = 'survey_species'

OBJECTIVES = (CULL_OBJECTIVE, SURVEY_OBJECTIVE, EVOLUTION_OBJECTIVE)


# ==========================================
# 💰 WHAT A DIRECTIVE IS WORTH
# ==========================================
# **THE PAYOUT GAP WAS 10:1 AND IT KILLED THE OTHER TWO DIRECTIVES.** Culling paid
# `required_amount * 250` - 1,250 to 3,000 Eco Tokens for one directive - while a survey
# paid a single Great Ball and an evolution study paid one Rare Candy. No reward tweak
# fixes a ratio like that: players run culling and ignore the rest until the ratio
# changes, so the ratio is what changed.
#
# Culling comes DOWN rather than the others coming up. Raising the other two to match
# would have doubled the money supply, and culling was the inflation source in the first
# place. 50 tokens a kill puts a directive at 250-600 instead of 1,250-3,000, and
# `utils.limits.directive_yield` thins the fifth claim of a day so twenty banked
# directives cannot be cashed at full price in one sitting.
CULL_TOKENS_PER_KILL = 50

# **THE CULL DIRECTIVE IS THE ONLY THING IN THE WORLD THAT NAMES AN ELEMENT AND ASKS FOR
# WORK AGAINST IT.** Field missions pay their habitat's element and battle residue pays
# whatever happened to faint, so both are steered only loosely; a directive that says
# "eight Fire types" is a trainer choosing to chase Fire Shards and being told the price
# up front. The reward is rolled and STORED at issue time, so `!survey` shows
# "Cull 8 Fire -> 8 Fire Shards" before any of the work is done.
#
# Like the token grant, this scales with the work rather than with the tier: twelve
# knockouts is twelve knockouts whatever the roll said. The uncommon tier doubles it,
# which is what a tier is for.
#
# Expected yield is roughly 2-3 shards of a NAMED element per cull directive issued.
# That is deliberately a supplement to the missions rather than a replacement - the
# directive system caps at 4/day and only a third of them are culls.
CULL_SHARDS_PER_KILL = 1
UNCOMMON_SHARD_MULTIPLIER = 2


# ------------------------------------------
# The tiers
# ------------------------------------------
# **A DIRECTIVE THAT MIGHT GIVE SOMETHING GREAT BEATS ONE THAT RELIABLY GIVES 200 TOKENS
# OF VALUE.** Three tiers, rolled per directive at issue time and stored on the row, so
# `!survey` can show what is at stake before the work is done rather than after.
TIER_COMMON = 'common'
TIER_UNCOMMON = 'uncommon'
TIER_RARE = 'rare'
TIER_ORDER = (TIER_COMMON, TIER_UNCOMMON, TIER_RARE)

TIER_BADGES = {TIER_COMMON: '⚪', TIER_UNCOMMON: '🔷', TIER_RARE: '🌟'}

# 80 / 17 / 3, before difficulty moves them.
BASE_TIER_WEIGHTS = {TIER_COMMON: 80, TIER_UNCOMMON: 17, TIER_RARE: 3}

# **DIFFICULTY BUYS ODDS, NOT A DIFFERENT TABLE.** Evolving anything is trivial; culling
# twelve of one element is not, and both paid the same before. A directive at the top of
# its own range moves this many percentage points out of Common, split two-to-one in
# favour of Uncommon - so the hardest cull sits at roughly 65/27/8 and the easiest stays
# at 80/17/3. Weights rather than a separate rare table, because a second table is a
# second thing to keep in step.
DIFFICULTY_TIER_SHIFT = 15

# The range `issue_directive` rolls `required_amount` from, per objective. Stated here
# because difficulty is meaningless without it - "required 3" is hard for a survey and
# would be trivial for a cull.
OBJECTIVE_RANGE = {
    CULL_OBJECTIVE: (5, 12),
    SURVEY_OBJECTIVE: (1, 3),
    EVOLUTION_OBJECTIVE: (1, 1),
}


def difficulty(objective, required_amount):
    """Where this directive sits in its own range, 0.0 to 1.0.

    An objective with no range at all - evolution asks for exactly one - is 0.0 rather
    than a division by zero, and gets the base odds.
    """
    low, high = OBJECTIVE_RANGE.get(objective, (1, 1))
    if high <= low:
        return 0.0
    span = max(0, min(high, int(required_amount or low)) - low)
    return span / float(high - low)


def tier_weights(objective, required_amount):
    """The three tier weights for one directive, after difficulty has had its say."""
    shift = DIFFICULTY_TIER_SHIFT * difficulty(objective, required_amount)
    return {
        TIER_COMMON: BASE_TIER_WEIGHTS[TIER_COMMON] - shift,
        TIER_UNCOMMON: BASE_TIER_WEIGHTS[TIER_UNCOMMON] + shift * (2 / 3.0),
        TIER_RARE: BASE_TIER_WEIGHTS[TIER_RARE] + shift * (1 / 3.0),
    }


def roll_tier(objective, required_amount, rng=random):
    """Which tier this directive's grant comes from."""
    weights = tier_weights(objective, required_amount)
    return rng.choices(TIER_ORDER,
                       weights=[weights[t] for t in TIER_ORDER], k=1)[0]


# ------------------------------------------
# The pools
# ------------------------------------------
# **THE BEST DIRECTIVES REWARD THE LOOP THEY BELONG TO.** Somebody running evolution
# studies is building a collection, so they are handed the next evolution's ingredient;
# somebody surveying species wants to keep catching, so they are handed balls. The old
# tables paid every directive out of the same short list of things the shop already
# sold, which is why the reward was worth less than the effort of reading it.
#
# An entry is `(kind, payload, low, high)`. `payload` is either one item key or a SET of
# them to draw from, so "an evolution item" can be written once rather than listed
# thirty-two times. `low`/`high` bound the quantity - volume is what makes a consumable
# feel like a reward, so vitamins arrive six at a time rather than one.
#
# **EVOLUTION ITEMS ARE THE EVOLUTION STUDY'S COMMON TIER, NOT ITS RARE ONE.** They left
# the shop in this same change, and a route that only opens on a 3% roll is not a route.
# The study that asks you to evolve something is the reliable way to get the next stone.
VITAMINS = frozenset({'protein', 'iron', 'calcium', 'zinc', 'carbos', 'hp-up'})
EV_BERRIES = frozenset({'pomeg-berry', 'kelpsy-berry', 'qualot-berry',
                        'hondew-berry', 'grepa-berry', 'tamato-berry'})
HEALING = frozenset({'potion', 'super-potion', 'hyper-potion', 'full-restore',
                     'revive'})

LOOT_TABLES = {
    CULL_OBJECTIVE: {
        # Culling stays the cash directive. It simply stops being the ONLY one worth
        # running, and stops paying five times what the work is worth.
        TIER_COMMON: [
            ('eco_tokens', None, 1, 1),
            ('item', HEALING, 3, 5),
            ('item', 'ultraball', 3, 5),
            # A shard of the element the directive NAMED - the payload is decided at
            # grant time from `target_variable`, which is why this entry carries no
            # payload of its own.
            ('shard', None, 1, 1),
        ],
        TIER_UNCOMMON: [
            ('item', VITAMINS, 3, 6),
            ('item', EV_BERRIES, 3, 6),
            ('item', 'rare-candy', 3, 5),
            ('shard', None, 1, 1),
        ],
        TIER_RARE: [
            ('item', GRIND_ITEMS, 1, 1),
            ('item', BREEDING_ITEMS, 1, 1),
            ('item', 'masterball', 1, 1),
        ],
    },
    SURVEY_OBJECTIVE: {
        # Catching-focused players want more catching.
        TIER_COMMON: [
            ('item', 'greatball', 5, 10),
            ('item', 'ultraball', 3, 6),
            ('item', HEALING, 3, 5),
        ],
        TIER_UNCOMMON: [
            ('item', VITAMINS, 3, 6),
            ('item', 'rare-candy', 3, 5),
            ('item', EVOLUTION_ITEMS, 1, 1),
        ],
        TIER_RARE: [
            ('item', 'masterball', 1, 1),
            ('item', GRIND_ITEMS, 1, 1),
            ('item', BREEDING_ITEMS, 1, 1),
        ],
    },
    EVOLUTION_OBJECTIVE: {
        TIER_COMMON: [
            ('item', EVOLUTION_ITEMS, 1, 1),
            ('item', 'rare-candy', 5, 10),
        ],
        TIER_UNCOMMON: [
            ('item', EVOLUTION_ITEMS, 2, 3),
            ('item', BREEDING_ITEMS, 1, 1),
            ('item', VITAMINS, 3, 6),
        ],
        TIER_RARE: [
            ('item', GRIND_ITEMS, 1, 1),
            ('item', 'masterball', 1, 1),
        ],
    },
}


def _pick_payload(payload, rng):
    """One item key, whether the entry named one or a set to draw from."""
    if isinstance(payload, str):
        return payload
    return rng.choice(sorted(payload))


def roll_reward(objective, required_amount, rng=random, target=None):
    """
    What one directive pays, as `(reward_type, reward_payload, amount, tier)`.

    `reward_payload` keeps the shape the column has always held: the item key for an
    item, and the TOKEN FIGURE as a string for cash. That is deliberate - 110 directives
    already exist on the live database and every one of them is a row of the old shape,
    so the new `reward_amount` column carries the quantity for items and is simply 1 for
    a cash grant rather than the two fields having to be read together.

    **A SHARD ENTRY RESOLVES AGAINST `target`, AND LEAVES AS AN ORDINARY ITEM ROW.** The
    cull directive already names an element in `target_variable`; the shard is that
    element's. Nothing downstream learns a new reward type - `!survey`, `!claim` and
    `describe_reward` all keep reading an item key and a quantity - which is the whole
    reason this is worth doing here rather than at the grant.

    A `target` that is not an element takes the shard entries off the table rather than
    producing a broken row. No caller does that today; culls always name one.
    """
    tier = roll_tier(objective, required_amount, rng)
    table = LOOT_TABLES.get(objective) or LOOT_TABLES[SURVEY_OBJECTIVE]

    shard = shard_for(target)
    entries = [e for e in table[tier] if shard or e[0] != 'shard']
    kind, payload, low, high = rng.choice(entries)

    if kind == 'eco_tokens':
        # Cash scales with the work rather than with the tier: twelve knockouts is
        # twelve knockouts whatever the roll said.
        return 'eco_tokens', str(int(required_amount) * CULL_TOKENS_PER_KILL), 1, tier

    if kind == 'shard':
        # Shards scale with the work for the same reason cash does, and the tier is what
        # doubles them rather than a second range to keep in step with the first.
        amount = max(1, int(required_amount) * CULL_SHARDS_PER_KILL)
        if tier != TIER_COMMON:
            amount *= UNCOMMON_SHARD_MULTIPLIER
        return 'item', shard, amount, tier

    return 'item', _pick_payload(payload, rng), rng.randint(low, high), tier


def describe_reward(reward_type, reward_payload, amount=1, tier=None):
    """
    One line for a grant, used by every place that shows one.

    `!analyze`'s summary, `!survey`'s page and `!claim`'s receipt each wrote this out,
    and all three hard-coded `1x` - so a reward of six vitamins would have read as one
    in all three the moment quantities existed.
    """
    badge = f"{TIER_BADGES.get(tier, '')} " if tier else ""
    if reward_type == 'eco_tokens':
        return f"{badge}💰 {int(reward_payload or 0):,} Eco Tokens"

    count = max(1, int(amount or 1))
    meta = EQUIPMENT_CATALOG.get(str(reward_payload or ''))
    name = meta['name'] if meta else str(reward_payload or '').replace('-', ' ').title()
    emoji = (meta or {}).get('emoji', '📦')
    return f"{badge}{emoji} {count}x {name}"


# ==========================================
# 🗄️ THE TWO NEW COLUMNS, ON A TABLE THAT ALREADY HAS ROWS IN IT
# ==========================================
# A quantity and a tier. `reward_payload` alone could not say "six vitamins", so every
# place that showed a grant hard-coded `1x` - and 110 directives already exist on the
# live database, so the columns arrive by ALTER rather than by rebuilding the table.
#
# **A READ MUST NEVER MIGRATE.** `ensure_column` says so and means it, so the writer
# adds these and every reader asks first and falls back to the defaults. That matters
# for exactly one window - between deploying this and the first `!analyze` on a given
# database - but in that window `!survey` and `!claim` have to keep working on rows that
# predate the change.
REWARD_EXTRAS = ('reward_amount', 'reward_tier')
REWARD_DEFAULTS = {'reward_amount': 1, 'reward_tier': None}

# Everything a reader needs about a directive, by NAME. It was seven columns unpacked
# positionally into `d_id, obj_type, target, req_amt, curr_prog, rev_type, rev_payload`
# in two places, and widening a positional row is precisely how this repo has broken a
# suite before.
DIRECTIVE_COLUMNS = ('directive_id', 'objective_type', 'target_variable',
                     'required_amount', 'current_progress', 'reward_type',
                     'reward_payload')


async def ensure_reward_columns(db):
    """Add the quantity and tier columns. Write paths only. Does NOT commit."""
    from utils.db_manager import ensure_column
    ok = await ensure_column(db, 'field_directives', 'reward_amount',
                             'INTEGER DEFAULT 1')
    return await ensure_column(db, 'field_directives', 'reward_tier', 'TEXT') and ok


async def directive_rows(db, where, params):
    """
    Directive rows as dicts, with the reward columns defaulted when they do not exist.

    Dicts rather than tuples on purpose: the two readers of this table each unpacked a
    seven-column row by position, so adding a column meant finding both. By name, a
    reader that does not care about the tier simply never mentions it.
    """
    from utils.db_manager import has_column
    present = [column for column in REWARD_EXTRAS
               if await has_column(db, 'field_directives', column)]
    columns = list(DIRECTIVE_COLUMNS) + present

    async with db.execute(
            f"SELECT {', '.join(columns)} FROM field_directives "
            f"WHERE {where} ORDER BY directive_id ASC", params) as cursor:
        found = await cursor.fetchall()

    rows = []
    for row in found:
        entry = dict(zip(columns, row))
        for column in REWARD_EXTRAS:
            if entry.get(column) is None:
                entry[column] = REWARD_DEFAULTS[column]
        rows.append(entry)
    return rows


def reward_line(entry):
    """`describe_reward` fed straight from a row dict."""
    return describe_reward(entry['reward_type'], entry['reward_payload'],
                           entry.get('reward_amount', 1), entry.get('reward_tier'))


async def credit_directive(db, user_id, objective, target, amount=1):
    """
    Advance every matching open directive, and report whether one just finished.

    Returns (progressed, completed): whether anything moved, and whether any directive
    reached its required amount as a result. Does NOT commit - the caller owns the
    transaction, so a directive cannot tick over for an evolution that then rolls back.
    """
    user_id = str(user_id)
    target = str(target or '').lower()

    cursor = await db.execute(f"""
        UPDATE field_directives
        SET current_progress = current_progress + ?
        WHERE user_id = ? AND objective_type = ?
          AND (target_variable = 'any' OR target_variable = ?)
          AND is_completed = 0
    """, (amount, user_id, objective, target))
    progressed = bool(cursor.rowcount)

    if not progressed:
        return False, False

    async with db.execute("""
        SELECT required_amount, current_progress
        FROM field_directives
        WHERE user_id = ? AND objective_type = ?
          AND (target_variable = 'any' OR target_variable = ?)
          AND is_completed = 0
    """, (user_id, objective, target)) as cursor:
        rows = await cursor.fetchall()

    # `>=` rather than `==`. A directive that overshot - two evolutions racing, or a
    # required amount edited downwards - would otherwise never announce itself and sit
    # at 3/2 forever, claimable but never mentioned.
    completed = any(current >= required for required, current in rows)
    return True, completed


async def credit_evolution(db, user_id, species_name):
    """
    Credit a Kinetic Maturation Study for evolving `species_name`.

    `species_name` is the species as it was BEFORE the evolution.
    """
    return await credit_directive(
        db, user_id, EVOLUTION_OBJECTIVE, species_name)


async def credit_cull(db, user_id, types):
    """
    Credit an Invasive Species Management directive for one defeated specimen.

    `types` is the defeated specimen's elemental typing. A dual-type counts for BOTH of
    its types, which is how the old copy behaved and is the reading that matches the
    brief: a Gyarados genuinely is one fewer Water-type and one fewer Flying-type in the
    habitat. Two directives can therefore tick from a single knockout - a Water one and
    a Flying one - and the duplicate guard below stops a specimen listed as the same
    type twice crediting twice.

    One knockout would credit a `target_variable = 'any'` cull directive once per type,
    which would be wrong. There is no such thing: `issue_directive` always names a
    concrete element for a cull. Worth knowing before anyone adds a wildcard one.

    Returns (progressed, [type names whose directive just finished]). Does NOT commit.

    The old copy lived at the point the battle ENDED and read whichever specimen was on
    the field then, so in a multi-opponent battle only the final knockout ever counted.
    Called from the faint itself, every knockout counts and the credit no longer depends
    on the battle being won afterwards.
    """
    finished = []
    progressed = False

    for element in dict.fromkeys(t for t in (types or []) if t):
        moved, done = await credit_directive(db, user_id, CULL_OBJECTIVE, element)
        progressed = progressed or moved
        if done:
            finished.append(element)

    return progressed, finished
