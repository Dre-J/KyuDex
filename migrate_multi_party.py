"""Gives every trainer more than one battle roster.

`user_party` was `(user_id, slot, instance_id)` with `PRIMARY KEY (user_id, slot)` - one
team per person, six slots, no way to keep a second. Anybody who wanted a different team
for a different opponent had to dismantle the first one and rebuild it afterwards.

Three changes, and the first is the only one that needs a rebuild:

**`user_party` gains `party_name`**, and the primary key becomes
`(user_id, party_name, slot)`. SQLite cannot alter a primary key in place, so the table
is rebuilt - which is why this is a script you run rather than a column added at boot
like `guild_config`. Every existing row is filed under `main`, so every trainer keeps
the team they already had, in the slots they already had it in.

**`user_parties` is new**, and records a party that EXISTS. A party with nothing in it
yet is still a thing somebody made and named, and a name that only exists as a side
effect of a row in `user_party` would vanish the moment they emptied it.

**`users` gains `active_party`**, the one the party commands act on. Defaulting to
`main` means a trainer who never touches any of this behaves exactly as before.

Safe to run more than once - it reports what it changed and does nothing on a second
pass. The bot degrades to a single party without it: `utils/roster.py` answers `main` to
every question when the column is missing.

    python migrate_multi_party.py
"""
import asyncio

import aiosqlite

from utils.constants import DB_FILE
from utils.roster import DEFAULT_PARTY


async def columns_of(db, table):
    async with db.execute(f"PRAGMA table_info({table})") as cursor:
        return [row[1] for row in await cursor.fetchall()]


async def run_migration():
    async with aiosqlite.connect(DB_FILE) as db:
        print(f"=== MULTI-PARTY MIGRATION on {DB_FILE} ===")

        # ------------------------------------------------------------------
        # 1. user_party: rebuilt, because the primary key changes.
        # ------------------------------------------------------------------
        if 'party_name' in await columns_of(db, 'user_party'):
            print("'user_party.party_name' already present.")
        else:
            async with db.execute("SELECT COUNT(*) FROM user_party") as cursor:
                before = (await cursor.fetchone())[0]

            # Foreign keys off for the swap: the old table is referenced by nothing, but
            # it references caught_pokemon, and a rebuild that trips a constraint
            # halfway would leave a trainer with no roster at all.
            await db.execute("PRAGMA foreign_keys = OFF")
            await db.execute("BEGIN")
            try:
                await db.execute("""
                    CREATE TABLE user_party_new (
                        user_id TEXT,
                        party_name TEXT NOT NULL DEFAULT 'main',
                        slot INTEGER,
                        instance_id TEXT,
                        PRIMARY KEY (user_id, party_name, slot),
                        FOREIGN KEY (instance_id) REFERENCES caught_pokemon(instance_id)
                    )
                """)
                await db.execute(
                    "INSERT INTO user_party_new (user_id, party_name, slot, instance_id) "
                    "SELECT user_id, ?, slot, instance_id FROM user_party",
                    (DEFAULT_PARTY,))
                await db.execute("DROP TABLE user_party")
                await db.execute("ALTER TABLE user_party_new RENAME TO user_party")
                await db.commit()
            except Exception:
                await db.rollback()
                raise
            finally:
                await db.execute("PRAGMA foreign_keys = ON")

            async with db.execute("SELECT COUNT(*) FROM user_party") as cursor:
                after = (await cursor.fetchone())[0]
            print(f"Rebuilt user_party: {before} row(s) in, {after} out, "
                  f"all filed under '{DEFAULT_PARTY}'.")
            if before != after:
                print(f"⚠️  ROW COUNT CHANGED ({before} -> {after}). Investigate before "
                      f"anybody plays.")

        # ------------------------------------------------------------------
        # 2. The parties themselves, so an empty one still exists.
        # ------------------------------------------------------------------
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_parties (
                user_id TEXT,
                party_name TEXT,
                PRIMARY KEY (user_id, party_name)
            )
        """)
        cursor = await db.execute(
            "INSERT OR IGNORE INTO user_parties (user_id, party_name) "
            "SELECT DISTINCT user_id, party_name FROM user_party")
        named = cursor.rowcount

        # Everybody registered gets a `main`, whether or not they have ever put
        # anything in it - otherwise `!party list` is empty for a new trainer.
        cursor = await db.execute(
            "INSERT OR IGNORE INTO user_parties (user_id, party_name) "
            "SELECT user_id, ? FROM users", (DEFAULT_PARTY,))
        seeded = cursor.rowcount
        print(f"Registered {named} existing party name(s), seeded {seeded} '{DEFAULT_PARTY}'.")

        # ------------------------------------------------------------------
        # 3. Which party a trainer is currently building.
        # ------------------------------------------------------------------
        if 'active_party' in await columns_of(db, 'users'):
            print("'users.active_party' already present.")
        else:
            await db.execute(
                f"ALTER TABLE users ADD COLUMN active_party TEXT DEFAULT '{DEFAULT_PARTY}'")
            print("Added 'users.active_party'.")

        cursor = await db.execute(
            "UPDATE users SET active_party = ? WHERE active_party IS NULL", (DEFAULT_PARTY,))
        filled = cursor.rowcount

        await db.commit()

        # ------------------------------------------------------------------
        # 4. Report the shape that is actually there.
        # ------------------------------------------------------------------
        async with db.execute(
                "SELECT COUNT(DISTINCT user_id), COUNT(*) FROM user_parties") as cursor:
            trainers, parties = await cursor.fetchone()

        print()
        print(f"{filled} trainer(s) pointed at '{DEFAULT_PARTY}'.")
        print(f"{trainers} trainer(s) hold {parties} party/parties between them.")
        print("Migration complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
