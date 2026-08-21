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

EVOLUTION_OBJECTIVE = 'trigger_mutation'
CULL_OBJECTIVE = 'cull_type'


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
