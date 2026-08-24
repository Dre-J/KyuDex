"""
What format a duel is fought in, and which specimens each side brings to it.

**1v1 IS A NARROWER ROSTER, NOT A SECOND ENGINE.** Everything a duel does - turn order,
abilities, hazards, items, the forced-swap phase - is the same whether a side has six
specimens or one. Forking the engine to add a format would double the surface every
future battle fix has to land on, and this codebase has already paid that bill several
times over. So a 1v1 duel is an ordinary duel whose roster query returned one row, and
this module owns the single decision that makes it so.

**THE LEAD IS THE SELECTED PARTNER**, not party slot 1 and not a picker. `!select`
already means "this is my Pokemon"; making 1v1 read it keeps one answer to that question
and saves a menu nobody wants to click twice a duel. The partner does NOT have to be in
the party - requiring that would quietly turn 1v1 back into "party slot 1" for anybody
who keeps a favourite out of their fieldwork roster.

**THE FORMATS COMPOSE.** A duel may be capped, solo, both or neither, and the four
combinations are one parser rather than two flags read in two places - `!battle @them
1v1 50` and `!battle @them 50 1v1` are the same duel and must not depend on typing order.

**WARDENS ARE NEVER SOLO.** A Warden fight is a five-specimen gauntlet that gates a
sector visa; letting it be fought one-on-one would make the progression spine cheaper
than the ordinary duels beside it. `!challenge warden` does not parse a format at all,
which is a stronger guarantee than parsing one and rejecting it.
"""

from utils.constants import PVP_LEVEL_CAPS, parse_level_cap
from utils.roster import party_filter

# Spellings people actually type. `1` alone is deliberately included: somebody typing
# `!npcduel 1` means a one-on-one, and reading it as a level cap of 1 would be a
# perverse answer to an obvious request.
SOLO_WORDS = ('1v1', '1vs1', '1-v-1', 'solo', 'single', 'singles', 'one', '1', 'duel1')


def parse_duel_format(text):
    """
    `(level_cap, solo, complaint)` from whatever they typed. Exactly one shape is set.

    Accepts the tokens in ANY ORDER and in any mixture: `50`, `1v1`, `1v1 50`,
    `50 1v1`, or nothing at all for a full-roster duel at real levels. Order-dependence
    here would be a bug nobody reports and everybody hits once.
    """
    raw = str(text or '').strip().lower()
    if not raw:
        return None, False, None

    solo = False
    leftovers = []
    for token in raw.replace(',', ' ').split():
        if token in SOLO_WORDS:
            solo = True
        else:
            leftovers.append(token)

    if not leftovers:
        return None, solo, None
    if len(leftovers) > 1:
        return None, False, (
            f"⚠️ I did not understand `{' '.join(leftovers)}`. A duel is a level cap "
            f"({' or '.join(str(c) for c in PVP_LEVEL_CAPS)}), `1v1`, or both.")

    # THE CAP IS STILL PARSED BY `parse_level_cap`, not by a second copy of the same
    # rules living here. Its complaints are already written and already tested.
    cap, complaint = parse_level_cap(leftovers[0])
    if complaint:
        return None, False, complaint
    return cap, solo, None


def describe_format(level_cap, solo, *, npc=False):
    """A sentence naming the format, or '' when it is the ordinary one.

    Shown on the challenge invitation because agreeing to a six-on-six at your own
    levels and agreeing to a capped 1v1 are different things to agree to.
    """
    bits = []
    if solo:
        bits.append("**1v1** — your selected partner only, no switching")
    if level_cap:
        bits.append(f"every specimen set to **Level {level_cap}** — no experience is "
                    f"earned")
    if not bits:
        return ""
    lead = "📏 **Format:** " if not npc else "📏 "
    return lead + "; ".join(bits) + "."


async def selected_partner(db, user_id):
    """The instance_id of this trainer's selected partner, or None."""
    try:
        async with db.execute("SELECT active_partner FROM users WHERE user_id = ?",
                              (str(user_id),)) as cursor:
            row = await cursor.fetchone()
    except Exception:
        return None
    return (row[0] if row else None) or None


NO_PARTNER = ("⚠️ A 1v1 duel is fought with your **selected partner**, and you have not "
              "selected one. Pick it with `!select <box number>` — or leave `1v1` off "
              "to fight with your whole roster.")

NO_ROSTER = ("⚠️ You must assign at least one specimen to your fieldwork roster using "
             "`!party add 1 [Box Number]` before initiating a spar.")


async def duel_roster(db, user_id, columns, *, solo=False):
    """
    `(rows, complaint)` - the specimens this trainer brings, in slot order.

    `columns` is the CALLER'S OWN select list. The three battle engines read their rows
    by index and their column orders already differ from one another; renumbering them
    is a change this function has no business making, and one this format does not need.
    What it owns is the single decision the format turns on - party or partner - so a
    fourth engine cannot be written that forgets 1v1 exists.

    In solo mode `user_party` is LEFT JOINed rather than required, so a caller selecting
    `up.slot` still resolves. It comes back NULL for a partner that is not in the party,
    which is correct: it has no slot, because it is not in a roster.
    """
    if solo:
        instance_id = await selected_partner(db, user_id)
        if not instance_id:
            return [], NO_PARTNER
        # OWNERSHIP IS CHECKED IN THE QUERY, not assumed from the column. A traded or
        # released partner leaves a stale `active_partner` behind - the wipe cascade
        # anonymises specimens rather than clearing every pointer at them - so a duel
        # that trusted it would field somebody else's Pokemon.
        async with db.execute(f"""
            SELECT {columns}
            FROM caught_pokemon cp
            JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
            LEFT JOIN user_party up
                   ON up.instance_id = cp.instance_id AND up.user_id = cp.user_id
            WHERE cp.instance_id = ? AND cp.user_id = ?
            ORDER BY up.slot IS NULL, up.slot
        """, (instance_id, str(user_id))) as cursor:
            rows = await cursor.fetchall()
        if not rows:
            return [], NO_PARTNER
        # ONE ROW, whatever the join did. A specimen in two rosters would otherwise
        # arrive twice and be fought as a team of two in a format called 1v1 - and
        # WITHOUT the ORDER BY above, which of the two arrived first was down to
        # whatever SQLite felt like, so the same duel could report a different slot
        # each time it started.
        return rows[:1], None

    scope, scope_params = await party_filter(db, user_id)
    async with db.execute(f"""
        SELECT {columns}
        FROM user_party up
        JOIN caught_pokemon cp ON up.instance_id = cp.instance_id
        JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
        WHERE up.user_id = ? {scope}
        ORDER BY up.slot ASC
    """, (str(user_id), *scope_params)) as cursor:
        rows = await cursor.fetchall()
    if not rows:
        return [], NO_ROSTER
    return rows, None


async def can_field_a_side(db, user_id, *, solo=False, who=None):
    """
    `None` if this trainer can fight in this format, or the complaint saying why not.

    Asked BEFORE the invitation goes out, so a duel is not agreed to and then found to
    be unfightable. `who` names the other player when the refusal is about them, since
    "you have not selected a partner" is the wrong sentence to show somebody about
    their opponent.
    """
    rows, complaint = await duel_roster(db, user_id, "cp.instance_id", solo=solo)
    if not complaint:
        return None
    if who is None:
        return complaint
    if solo:
        return (f"⚠️ **{who}** has not selected a partner, so they cannot fight a 1v1 "
                f"duel yet.")
    return f"⚠️ **{who}** does not have a fieldwork roster assembled yet."
