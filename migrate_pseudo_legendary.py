"""Records the pseudo-legendaries in the species table, beside the legendaries.

`base_pokemon_species` already answers "is this legendary?" and "is this mythical?" with
a column each. It had no way to answer "is this a pseudo-legendary?", so the ten 600-BST
finals were drawn from the same 95% pool as a Rattata - in a ground-typed biome, a
Garchomp appeared about as often as a Diglett.

This adds `is_pseudo_legendary` and fills it from `utils.constants.PSEUDO_LEGENDARY_IDS`,
which is deliberately the ONE list. The spawn queries build their filter from that tuple
too, so the column and the engine cannot disagree: this is the tuple written down where
a person reading the database with a SQL client can see it, not a second opinion.

Only the FINAL stages are marked. "Pseudo-legendary" names those Pokemon specifically,
and flagging Gible would have made it unfindable - the whole appeal of the family is
that you can raise one. The megas and Kommo-o's totem form are not marked either: they
have their own pokedex ids, cannot be encountered in the wild, and are already excluded
by the form filter.

Safe to run more than once. It reports what it changed and does nothing on a second
pass. The engine is correct either way - the spawn filters read the tuple, not the
column - so a database that has not had this run still produces the new rarity tier.

    python migrate_pseudo_legendary.py
"""
import asyncio

import aiosqlite

from utils.constants import DB_FILE, PSEUDO_LEGENDARY_IDS

COLUMN = 'is_pseudo_legendary'


async def column_exists(db, table, column):
    async with db.execute(f"PRAGMA table_info({table})") as cursor:
        return any(row[1] == column for row in await cursor.fetchall())


async def run_migration():
    async with aiosqlite.connect(DB_FILE) as db:
        print(f"=== PSEUDO-LEGENDARY MIGRATION on {DB_FILE} ===")

        # ------------------------------------------------------------------
        # 1. The column.
        # ------------------------------------------------------------------
        if await column_exists(db, 'base_pokemon_species', COLUMN):
            print(f"'{COLUMN}' already present.")
        else:
            await db.execute(
                f"ALTER TABLE base_pokemon_species ADD COLUMN {COLUMN} INTEGER DEFAULT 0")
            print(f"Added '{COLUMN}' to base_pokemon_species.")

        # ------------------------------------------------------------------
        # 2. The eleven, and nothing else.
        # ------------------------------------------------------------------
        # Cleared first rather than only set. Running this after the tuple has SHRUNK
        # has to unmark whatever left it, or the column keeps an answer the code no
        # longer gives - which is the exact failure mode a second source of truth has.
        placeholders = ", ".join("?" for _ in PSEUDO_LEGENDARY_IDS)

        cursor = await db.execute(
            f"UPDATE base_pokemon_species SET {COLUMN} = 0 "
            f"WHERE {COLUMN} = 1 AND pokedex_id NOT IN ({placeholders})",
            PSEUDO_LEGENDARY_IDS)
        cleared = cursor.rowcount

        cursor = await db.execute(
            f"UPDATE base_pokemon_species SET {COLUMN} = 1 "
            f"WHERE pokedex_id IN ({placeholders}) AND ({COLUMN} IS NULL OR {COLUMN} = 0)",
            PSEUDO_LEGENDARY_IDS)
        marked = cursor.rowcount

        # Anything else in the table is not a pseudo-legendary and must say so rather
        # than say NULL, which reads as false in Python and as "unknown" in SQL.
        cursor = await db.execute(
            f"UPDATE base_pokemon_species SET {COLUMN} = 0 WHERE {COLUMN} IS NULL")
        filled = cursor.rowcount

        await db.commit()

        # ------------------------------------------------------------------
        # 3. Report what is actually there, so a bad run is visible.
        # ------------------------------------------------------------------
        async with db.execute(
                f"SELECT pokedex_id, name FROM base_pokemon_species "
                f"WHERE {COLUMN} = 1 ORDER BY pokedex_id") as cursor:
            flagged = await cursor.fetchall()

        print()
        print(f"{marked} newly marked, {cleared} unmarked, {filled} NULLs filled in.")
        print(f"{len(flagged)} species carry the flag:")
        for dex, name in flagged:
            print(f"   \U0001f537 {name} ({dex})")

        missing = set(PSEUDO_LEGENDARY_IDS) - {dex for dex, _ in flagged}
        if missing:
            print(f"⚠️  Not present in this database at all: "
                  f"{sorted(missing)} - the spawn filter simply will not match them.")
        print("Migration complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
