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
    # The roster NAMES, which are a separate table from the roster contents so that an
    # empty roster still exists. They are text a trainer chose and typed, so they leave
    # with the trainer - the guard in test_account_lifecycle is what noticed this one.
    'user_parties':       'user_id',
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

# Rows that name TWO trainers, where deleting the row would destroy somebody ELSE's
# record of something they took part in.
#
# `trade_logs` is the case: a row says "A gave B this". Deleting every row naming A also
# deletes B's only evidence of a trade B made, which is the same failure the
# original_user_id rule exists to prevent, one table over. So the row survives and the
# name comes off - the trade remains reconstructable, and the erased trainer is no
# longer in it.
#
# This map exists because the ledger was added in the trade-ledger change and QUIETLY
# ESCAPED the cascade: the schema guard looks for columns called user_id, seller_id and
# the like, and `user_a`/`user_b` matched none of them, so nothing asked the question.
# The guard knows those spellings now.
ANONYMISE_PAIRED = {
    'trade_logs': ('user_a', 'user_b'),
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
# name. join_date is deliberately NOT reset - the account is the same age it always was,
# and neither is levelup_pings: it is a preference about how the bot talks to somebody,
# not something they earned, so wiping their Pokemon should not start pinging them again.
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


async def _has_table(db, table):
    async with db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
            (table,)) as cursor:
        return await cursor.fetchone() is not None


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

    # 4b. Rows naming two trainers. The row stays so the OTHER party keeps their record;
    #     only the erased trainer's name comes off it.
    for table, columns in ANONYMISE_PAIRED.items():
        if not await _has_table(db, table):
            continue
        for column in columns:
            if not await _has_column(db, table, column):
                continue
            cursor = await db.execute(
                f"UPDATE {table} SET {column} = NULL WHERE {column} = ?", (user_id,))
            if cursor.rowcount:
                removed[f"{table}.{column} (anonymised)"] = cursor.rowcount

    # 5. The account itself.
    if keep_account:
        columns = ', '.join(f"{name} = ?" for name in FRESH_ACCOUNT)
        await db.execute(f"UPDATE users SET {columns} WHERE user_id = ?",
                         list(FRESH_ACCOUNT.values()) + [user_id])
        if await _has_column(db, 'users', 'last_reset_at'):
            await db.execute(
                "UPDATE users SET last_reset_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                (user_id,))
        # The licence survives, so "has no specimens" cannot be what !start tests -
        # it has to be told that this particular empty roster is owed a partner.
        if await _has_column(db, 'users', 'needs_starter'):
            await db.execute(
                "UPDATE users SET needs_starter = 1 WHERE user_id = ?", (user_id,))
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


async def may_choose_starter(db, user_id):
    """
    Whether this trainer may pick a starter, as (allowed: bool, reason: str).

    Three states, and the middle one is the whole reason this function exists:

    - `new`        - no licence at all. The ordinary first run.
    - `reset`      - a licence with `needs_starter` set. Reset keeps the row, so
                     without this flag `!start` refused and the account was stranded
                     with no Pokemon and no way to get one.
    - `has_roster` - already holds specimens. Refused.
    - `spent`      - an empty roster that is NOT owed a partner, which is what
                     releasing every specimen looks like. Refused, because otherwise
                     the starter kit becomes a repeatable grant of tokens and balls.

    On a database where the migration has not been run, an empty roster is treated as
    entitlement: unbricking accounts matters more than the farm, and the farm needs a
    player to release their entire collection each time.
    """
    user_id = str(user_id)

    async with db.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)) as cursor:
        if not await cursor.fetchone():
            return True, 'new'

    async with db.execute(
            "SELECT COUNT(*) FROM caught_pokemon WHERE user_id = ?", (user_id,)) as cursor:
        if (await cursor.fetchone())[0]:
            return False, 'has_roster'

    if not await _has_column(db, 'users', 'needs_starter'):
        return True, 'reset'

    async with db.execute(
            "SELECT COALESCE(needs_starter, 0) FROM users WHERE user_id = ?",
            (user_id,)) as cursor:
        row = await cursor.fetchone()

    return (True, 'reset') if row and row[0] else (False, 'spent')


async def grant_starter_licence(db, user_id, tokens, items, machines=()):
    """
    Register the trainer and hand over the onboarding kit, for a new OR reset account.

    An upsert rather than an insert, because a reset trainer already has the row - the
    plain INSERT this replaced raised IntegrityError and told them they were already
    registered, which was true and unhelpful.

    `machines` is a handful of TMs. They cost almost nothing, which is not why they are
    here: a new trainer does not know TMs EXIST, and six of them in the notebook teaches
    that in a way no shop listing does.
    """
    user_id = str(user_id)

    await db.execute("""
        INSERT INTO users (user_id, eco_tokens, unlocked_visas)
        VALUES (?, ?, 'canopy')
        ON CONFLICT(user_id) DO UPDATE SET
            eco_tokens = eco_tokens + excluded.eco_tokens,
            unlocked_visas = COALESCE(users.unlocked_visas, 'canopy')
    """, (user_id, tokens))

    for item_name, quantity in items.items():
        await db.execute("""
            INSERT INTO user_inventory (user_id, item_name, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, item_name) DO UPDATE SET
                quantity = quantity + excluded.quantity
        """, (user_id, item_name, quantity))

    # A TM is owned or it is not, so a reset trainer who already holds one is left
    # exactly as they were rather than handed a second copy of a permanent thing.
    for move in machines:
        await db.execute("""
            INSERT INTO user_tms (user_id, tm_name, quantity)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, tm_name) DO NOTHING
        """, (user_id, move))

    # Entitlement spent. Without this the kit could be claimed again from a stale menu.
    if await _has_column(db, 'users', 'needs_starter'):
        await db.execute("UPDATE users SET needs_starter = 0 WHERE user_id = ?",
                         (user_id,))


async def levelup_pings_enabled(db, user_id):
    """
    Whether this trainer wants to hear about their partner levelling up.

    Defaults to True in every uncertain case - no column, no row, a NULL. A preference
    that has never been expressed must behave the way the bot behaved before the
    preference existed, or a migration that has not been run quietly turns a feature
    off for the entire server.
    """
    if not await _has_column(db, 'users', 'levelup_pings'):
        return True

    async with db.execute("SELECT levelup_pings FROM users WHERE user_id = ?",
                          (str(user_id),)) as cursor:
        row = await cursor.fetchone()

    if not row or row[0] is None:
        return True
    return bool(row[0])


async def set_levelup_pings(db, user_id, enabled):
    """
    Record the preference. Returns False if the database cannot hold it yet.

    Reporting the failure rather than swallowing it is the point: a toggle that says
    "done" and changes nothing is worse than one that admits the migration is missing.

    Does NOT commit; the caller owns the transaction.
    """
    if not await _has_column(db, 'users', 'levelup_pings'):
        return False

    await db.execute("UPDATE users SET levelup_pings = ? WHERE user_id = ?",
                     (1 if enabled else 0, str(user_id)))
    return True


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
