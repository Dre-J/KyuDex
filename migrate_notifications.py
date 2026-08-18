"""Adds the per-trainer notification preference.

One column, `users.levelup_pings`, defaulting to 1 - everyone keeps getting level-up
announcements, they just arrive quietly now. The column exists so that a trainer who
talks a lot, and therefore levels a partner constantly, can turn the announcements off
entirely rather than choosing between the noise and un-deploying their partner.

It lives on `users` rather than in a settings table because there is exactly one
preference and a table for one row per user with one boolean in it is a table you
regret. If a second preference arrives, this is the column to sit beside.

Safe to run more than once - an existing column is reported and skipped.

    python migrate_notifications.py
"""
import asyncio

import aiosqlite

from utils.constants import DB_FILE

NEW_COLUMNS = [
    # Default ON. A preference nobody has expressed should behave the way the bot
    # behaved yesterday, or the migration silently turns a feature off for everybody.
    ('levelup_pings', 'INTEGER DEFAULT 1'),
]


async def run_migration():
    async with aiosqlite.connect(DB_FILE) as db:
        print(f"=== NOTIFICATION PREFERENCES MIGRATION on {DB_FILE} ===")

        for column, declaration in NEW_COLUMNS:
            try:
                await db.execute(
                    f"ALTER TABLE users ADD COLUMN {column} {declaration}")
                print(f"Added '{column}' column to users.")
            except aiosqlite.OperationalError as e:
                if 'duplicate column' not in str(e).lower():
                    raise
                print(f"'{column}' already exists. Skipping.")

        # ALTER TABLE ... DEFAULT fills existing rows on SQLite, but a row written by an
        # older build between the ALTER and this line would not be covered, and NULL is
        # not 1. Say what we mean rather than trusting the default to have reached
        # everybody.
        cursor = await db.execute(
            "UPDATE users SET levelup_pings = 1 WHERE levelup_pings IS NULL")
        filled = cursor.rowcount
        await db.commit()

        async with db.execute(
                "SELECT COUNT(*), COALESCE(SUM(levelup_pings), 0) FROM users") as cursor:
            total, opted_in = await cursor.fetchone()

        print(f"{total} trainer(s) registered, {opted_in} receiving level-up notices "
              f"({filled} backfilled by this run).")
        print("Migration complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
