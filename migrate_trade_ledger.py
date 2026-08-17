"""Adds the starter flag and the trade ledger.

Two things, one script, because they answer the same suggestion.

`caught_pokemon.is_starter` is what makes a starter non-tradeable. It has to be a column
rather than a rule, because the rule stops being true the moment the specimen evolves,
levels, or is renamed - and the alt-account farm this exists to stop would evolve it
first if that were all it took.

`trade_logs` is append-only. Nothing in the codebase updates or deletes a row in it;
that is the point. Logs are for reconstructing an incident after the fact, which they
cannot do if the incident could have rewritten them.

The backfill identifies existing starters as "no capture guild, and originally the
owner's own" - a starter is the only specimen inserted without a guild. On this database
that picks out exactly ONE candidate per registered trainer, which is the result you
want from a heuristic before you trust it. It reports what it matched.

Safe to run more than once.

    python migrate_trade_ledger.py
"""
import asyncio

import aiosqlite

from utils.constants import DB_FILE

NEW_COLUMNS = [
    ('caught_pokemon', 'is_starter', 'INTEGER DEFAULT 0'),
]

TRADE_LOGS_SCHEMA = """
CREATE TABLE IF NOT EXISTS trade_logs (
    log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_type  TEXT NOT NULL,          -- gift | trade | gts | gts-swap | market
    guild_id    TEXT,
    user_a      TEXT NOT NULL,
    user_b      TEXT,
    side_a      TEXT,                   -- JSON snapshot, not a live reference
    side_b      TEXT,
    detail      TEXT,
    logged_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

# Read rather than written by anything that could hide a trade.
TRADE_LOG_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_trade_logs_user_a ON trade_logs(user_a)",
    "CREATE INDEX IF NOT EXISTS idx_trade_logs_user_b ON trade_logs(user_b)",
    "CREATE INDEX IF NOT EXISTS idx_trade_logs_when ON trade_logs(logged_at)",
]


async def run_migration():
    async with aiosqlite.connect(DB_FILE) as db:
        print(f"=== TRADE LEDGER MIGRATION on {DB_FILE} ===")

        for table, column, declaration in NEW_COLUMNS:
            try:
                await db.execute(
                    f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")
                print(f"Added '{column}' column to {table}.")
            except aiosqlite.OperationalError as e:
                if 'duplicate column' not in str(e).lower():
                    raise
                print(f"'{column}' already exists. Skipping.")

        await db.execute(TRADE_LOGS_SCHEMA)
        for statement in TRADE_LOG_INDEXES:
            await db.execute(statement)
        print("trade_logs table and indexes ready.")

        # Backfill. A starter is inserted with no capture guild and its owner as its
        # own origin; nothing else is. Only rows still marked 0 are touched, so a
        # second run cannot un-flag anything or re-flag a traded-away specimen.
        # The rule is stated once, in the subquery. It was written out twice at first -
        # once here and once inside - which meant breaking either copy changed nothing,
        # and a rule you cannot break is a rule you cannot test.
        cursor = await db.execute("""
            UPDATE caught_pokemon SET is_starter = 1
            WHERE is_starter = 0
              AND rowid IN (
                  SELECT MIN(rowid) FROM caught_pokemon
                  WHERE caught_in_guild IS NULL AND original_user_id = user_id
                  GROUP BY user_id
              )
        """)
        flagged = cursor.rowcount
        await db.commit()

        async with db.execute(
                "SELECT COUNT(*) FROM caught_pokemon WHERE is_starter = 1") as cursor:
            total = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM trade_logs") as cursor:
            logged = (await cursor.fetchone())[0]

        print(f"\n{flagged} starter(s) flagged by this run, {total} in total.")
        print(f"{logged} trade(s) already on the ledger.")

        async with db.execute("""
            SELECT cp.user_id, s.name, cp.level FROM caught_pokemon cp
            JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
            WHERE cp.is_starter = 1 ORDER BY cp.rowid
        """) as cursor:
            for user_id, name, level in await cursor.fetchall():
                print(f"  {user_id}: {name} (Lv {level})")

        print("\nMigration complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
