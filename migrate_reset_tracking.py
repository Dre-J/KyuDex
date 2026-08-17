"""Adds the two columns the account lifecycle needs.

`last_reset_at` has to survive a wipe, because it is the only thing standing between a
free reset and a player rerolling their starter twenty times in an afternoon. It lives
on `users` for exactly that reason: `/reset` keeps that row.

`needs_starter` answers a question the schema could not otherwise: is this trainer
ENTITLED to a starter, or do they merely happen to have an empty roster? Reset keeps the
licence, so "no specimens" cannot be the test - releasing every Pokemon would look
identical and would turn `!start` into a repeatable grant of tokens and Great Balls.

Safe to run more than once, and safe to re-run now if you have already run the earlier
version of this script - an existing column is reported and skipped.

    python migrate_reset_tracking.py

Note this script reads DB_FILE from utils.constants rather than hardcoding a name.
migrate_genders.py hardcodes "kyusystem.db", which is not the database this bot uses.
"""
import asyncio

import aiosqlite

from utils.constants import DB_FILE

NEW_COLUMNS = [
    ('last_reset_at', 'TIMESTAMP'),
    ('needs_starter', 'INTEGER DEFAULT 0'),
]


async def run_migration():
    async with aiosqlite.connect(DB_FILE) as db:
        print(f"=== ACCOUNT LIFECYCLE MIGRATION on {DB_FILE} ===")

        for column, declaration in NEW_COLUMNS:
            try:
                await db.execute(
                    f"ALTER TABLE users ADD COLUMN {column} {declaration}")
                print(f"Added '{column}' column to users.")
            except aiosqlite.OperationalError as e:
                if 'duplicate column' not in str(e).lower():
                    raise
                print(f"'{column}' already exists. Skipping.")

        # A trainer sitting on an empty roster right now got there by resetting before
        # this column existed - there was no other way to keep a licence with no
        # specimens. Entitle them, or they stay locked out of !start.
        cursor = await db.execute("""
            UPDATE users SET needs_starter = 1
            WHERE needs_starter = 0
              AND user_id NOT IN (SELECT DISTINCT user_id FROM caught_pokemon)
        """)
        stranded = cursor.rowcount
        await db.commit()

        async with db.execute(
                "SELECT COUNT(*), COUNT(last_reset_at), "
                "COALESCE(SUM(needs_starter), 0) FROM users") as cursor:
            total, stamped, awaiting = await cursor.fetchone()

        print(f"{total} trainer(s) registered, {stamped} with a reset on record.")
        print(f"{awaiting} awaiting a starter ({stranded} unlocked by this run).")
        print("Migration complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
