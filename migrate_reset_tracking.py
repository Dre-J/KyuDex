"""Adds the one column the reset cooldown needs.

`last_reset_at` has to survive a wipe, because it is the only thing standing between a
free reset and a player rerolling their starter twenty times in an afternoon. It lives
on `users` for exactly that reason: `/reset` keeps that row.

Safe to run more than once - an existing column is reported and skipped.

    python migrate_reset_tracking.py

Note this script reads DB_FILE from utils.constants rather than hardcoding a name.
migrate_genders.py hardcodes "kyusystem.db", which is not the database this bot uses.
"""
import asyncio

import aiosqlite

from utils.constants import DB_FILE


async def run_migration():
    async with aiosqlite.connect(DB_FILE) as db:
        print(f"=== RESET TRACKING MIGRATION on {DB_FILE} ===")

        try:
            await db.execute("ALTER TABLE users ADD COLUMN last_reset_at TIMESTAMP")
            print("Added 'last_reset_at' column to users.")
        except aiosqlite.OperationalError as e:
            if 'duplicate column' not in str(e).lower():
                raise
            print("'last_reset_at' already exists. Skipping.")

        await db.commit()

        # Existing trainers have never reset, so the column stays NULL and
        # reset_available_at() reads that as "may reset now". Nothing to backfill.
        async with db.execute(
                "SELECT COUNT(*), COUNT(last_reset_at) FROM users") as cursor:
            total, stamped = await cursor.fetchone()

        print(f"{total} trainer(s) registered, {stamped} with a reset on record.")
        print("Migration complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
