"""One cascade, two doors.

`/reset` and `/privacy delete` destroy exactly the same things. The only difference is
whether the row in `users` survives at the end, so they share one function with a flag
rather than two lists that drift apart. The owner-only `!wipe` uses it too - it had its
own copy, and that copy had already fallen four tables behind.

Two rules the tables cannot express, written here because they are easy to get wrong:

**A specimen can outlive its trainer.** `gts_deposits`, `active_deployments` and
`global_market` key on an `instance_id`, not on a user. Deleting `caught_pokemon` first
leaves those rows pointing at specimens that no longer exist - the orphaned-row problem.
So instance-keyed rows are cleared BEFORE the specimens they name.

**A traded specimen carries its origin.** `caught_pokemon.original_user_id` names the
trainer who first caught it, and that row may now belong to somebody else entirely.
Deleting by `original_user_id` would destroy another player's Pokemon. Those rows are
anonymised instead: the specimen stays, the name comes off it.

Adding a table? Put it in one of the maps below. `tests/test_account_lifecycle.py`
walks the live schema and fails on any table holding a user column that no map mentions,
so a table added in six months cannot silently escape the cascade.
"""

# Tables that name a trainer directly, and the column that does the naming.
OWNER_COLUMN = {
    'users':              'user_id',
    'caught_pokemon':     'user_id',
    'user_party':         'user_id',
    'user_inventory':     'user_id',
    'user_tms':           'user_id',
    'user_alerts':        'user_id',
    'guild_members':      'user_id',
    'field_directives':   'user_id',
    'active_deployments': 'user_id',
    'gts_deposits':       'user_id',
    'global_market':      'seller_id',
}

# Tables that name a SPECIMEN. Cleared first, while its instance_ids can still be found.
INSTANCE_COLUMN = {
    'user_party':         'instance_id',
    'active_deployments': 'instance_id',
    'gts_deposits':       'instance_id',
    'global_market':      'instance_id',
}

# Columns naming a trainer who no longer owns the row. Anonymised, never deleted.
ANONYMISE = {
    'caught_pokemon': 'original_user_id',
}

# Deliberately survives both doors. A ban that a user could clear by deleting their own
# account and registering again is not a ban. Retaining it is an abuse-prevention
# record rather than game data - worth confirming against your privacy policy.
RETAINED_TABLES = {'banned_personnel'}

# There is deliberately no REFERENCE_TABLES list here. It existed briefly and was
# decoration: nothing read it, so it could be emptied without changing what a wipe did.
# Protection is not a list to keep in step - it is the default. A table is only ever
# touched if it appears in one of the two maps above, and the suite proves that by
# counting every OTHER table in the schema before and after a wipe.

# What a kept account looks like afterwards: a registered trainer with nothing to their
# name. join_date is deliberately NOT reset - the account is the same age it always was.
FRESH_ACCOUNT = {
    'eco_tokens': 0,
    'active_partner': None,
    'unlocked_visas': 'canopy',
    'current_energy': 100,
    'last_energy_tick': 0,
}

# How long a trainer must wait between resets. The column outlives the wipe, which is
# what makes the cooldown enforceable at all.
RESET_COOLDOWN_DAYS = 30


async def _instance_ids(db, user_id):
    """Every specimen tag this trainer owns, before any of them are deleted."""
    async with db.execute(
            "SELECT instance_id FROM caught_pokemon WHERE user_id = ?", (user_id,)) as cursor:
        return [row[0] for row in await cursor.fetchall()]


async def _has_column(db, table, column):
    async with db.execute(f"PRAGMA table_info({table})") as cursor:
        return any(row[1] == column for row in await cursor.fetchall())


async def wipe_user(db, user_id, keep_account=False):
    """
    Destroy everything a trainer owns. Returns a dict of table -> rows removed.

    `keep_account=True` leaves a registered trainer with an empty roster - the `/reset`
    door. `keep_account=False` leaves nothing at all - the `/privacy delete` door.

    Does NOT commit. The caller owns the transaction, so a failure halfway through
    rolls back rather than leaving a half-erased account.
    """
    user_id = str(user_id)
    removed = {}

    # 1. The specimens, noted before anything can delete them.
    tags = await _instance_ids(db, user_id)

    # 2. Rows that point AT those specimens, cleared while the tags still resolve.
    for table, column in INSTANCE_COLUMN.items():
        if not tags:
            continue
        marks = ','.join('?' * len(tags))
        cursor = await db.execute(
            f"DELETE FROM {table} WHERE {column} IN ({marks})", tags)
        removed[f"{table} (by specimen)"] = cursor.rowcount

    # 3. Rows that name the trainer.
    for table, column in OWNER_COLUMN.items():
        if table == 'users':
            continue                      # handled last, and only sometimes
        cursor = await db.execute(f"DELETE FROM {table} WHERE {column} = ?", (user_id,))
        if cursor.rowcount:
            removed[table] = removed.get(table, 0) + cursor.rowcount

    # 4. Specimens somebody else owns that this trainer originally caught. The Pokemon
    #    belongs to the other player now - only the name comes off.
    for table, column in ANONYMISE.items():
        if not await _has_column(db, table, column):
            continue
        cursor = await db.execute(
            f"UPDATE {table} SET {column} = NULL WHERE {column} = ? AND user_id != ?",
            (user_id, user_id))
        if cursor.rowcount:
            removed[f"{table} (origin anonymised)"] = cursor.rowcount

    # 5. The account itself.
    if keep_account:
        columns = ', '.join(f"{name} = ?" for name in FRESH_ACCOUNT)
        await db.execute(f"UPDATE users SET {columns} WHERE user_id = ?",
                         list(FRESH_ACCOUNT.values()) + [user_id])
        if await _has_column(db, 'users', 'last_reset_at'):
            await db.execute(
                "UPDATE users SET last_reset_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                (user_id,))
    else:
        cursor = await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        removed['users'] = cursor.rowcount

    return removed


async def reset_available_at(db, user_id):
    """
    When this trainer may reset again, as (allowed: bool, days_left: int).

    A trainer who has never reset may always reset. The column is read defensively so
    the commands still work on a database where the migration has not been run yet.
    """
    if not await _has_column(db, 'users', 'last_reset_at'):
        return True, 0

    async with db.execute(
            "SELECT CAST(julianday('now') - julianday(last_reset_at) AS INTEGER) "
            "FROM users WHERE user_id = ?", (str(user_id),)) as cursor:
        row = await cursor.fetchone()

    if not row or row[0] is None:
        return True, 0

    days_since = int(row[0])
    if days_since >= RESET_COOLDOWN_DAYS:
        return True, 0
    return False, RESET_COOLDOWN_DAYS - days_since


async def account_summary(db, user_id):
    """
    What a wipe would actually destroy, for the confirmation screen.

    People reset in frustration and regret it an hour later, so the prompt names real
    numbers off their own account rather than a generic warning.
    """
    user_id = str(user_id)
    counts = {}

    async with db.execute(
            "SELECT COUNT(*), COALESCE(SUM(is_shiny), 0), COALESCE(MAX(level), 0) "
            "FROM caught_pokemon WHERE user_id = ?", (user_id,)) as cursor:
        total, shinies, highest = await cursor.fetchone()

    counts['specimens'] = total
    counts['shinies'] = shinies
    counts['highest_level'] = highest

    async with db.execute("SELECT eco_tokens FROM users WHERE user_id = ?",
                          (user_id,)) as cursor:
        row = await cursor.fetchone()
    counts['tokens'] = row[0] if row else 0

    async with db.execute(
            "SELECT COALESCE(SUM(quantity), 0) FROM user_inventory WHERE user_id = ?",
            (user_id,)) as cursor:
        counts['items'] = (await cursor.fetchone())[0]

    async with db.execute("SELECT COUNT(*) FROM global_market WHERE seller_id = ?",
                          (user_id,)) as cursor:
        counts['listings'] = (await cursor.fetchone())[0]

    async with db.execute("SELECT COUNT(*) FROM gts_deposits WHERE user_id = ?",
                          (user_id,)) as cursor:
        counts['gts'] = (await cursor.fetchone())[0]

    async with db.execute("SELECT COUNT(*) FROM active_deployments WHERE user_id = ?",
                          (user_id,)) as cursor:
        counts['deployments'] = (await cursor.fetchone())[0]

    return counts
