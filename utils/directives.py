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
"""

EVOLUTION_OBJECTIVE = 'trigger_mutation'


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
