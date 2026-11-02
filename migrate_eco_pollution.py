"""
The tables Phase 1 of the ecosystem rework runs on, and the backfill that carries nine
months of `servers.ecosystem_score` into them.

**WHAT IS WRONG TODAY.** `servers.ecosystem_score` is a single 0-100 integer that the
spawn roll decrements by 15-30 on a 10% "ecological disaster" chance and `!clean` nudges
back up by 2-5. Nothing records WHO caused a change, so nothing can tell a server why
its number moved; nothing scales to population, so a five-person server and a
three-hundred-person server live under the same arithmetic; and the only way to find out
what happened yesterday is to not have been asleep.

**WHAT THIS SCRIPT DOES.**

  1. creates the six `eco_*` tables and their four indexes (see `utils/eco_config.py`,
     which owns the definitions this imports);
  2. gives every row in `servers` an `eco_guild` row whose pollution is the pollution
     behind the score it has today, so no server's displayed number moves on the day
     this runs;
  3. gives every `(guild_id, user_id)` pair in `guild_members` an `eco_user` row with
     `first_seen_at = 0`.

**WHY THE `eco_user` SEEDING IS NOT OPTIONAL.** §3.4 gives a member's first 48 hours half
pollution, measured from `first_seen_at`. A row created on demand would stamp that field
with the moment of a trainer's first polluting action - so every existing player, some of
whom have been here since March, would be handed a new-member discount the day the engine
ships. Seeding them at 0 reads as "known before the ledger began", which is both true and
the only value that cannot be mistaken for a timestamp.

**WHY CAPACITY IS SEEDED AT THE FLOOR.** Capacity is `200 + 120 * AU7` and AU7 is a count
of distinct users active in the last seven days - which nothing has been recording, so it
cannot be computed for a day that has already happened. Every row therefore starts at the
AU7 = 1 floor with `capacity_updated_at = 0`, which the first tick reads as "recompute
me". The real AU7 is at least 1, so that recompute can only RAISE capacity, and raising
capacity with pollution held constant can only raise the score. **No server can be
migrated into a worse state than it was in**, which is the one property worth insisting on
in a script that touches every guild at once.

**WHAT IT DOES NOT DO.**

  * It does not touch `servers`. `ecosystem_score`, `pollution_type` and `active_biome`
    keep their current values and every reader of them keeps working - the spawn table,
    `!habitat`, `!rates`. Retiring that column is a later PR's job, and until it happens
    the old system is still the one in charge.
  * It does not write `critical`, `pristine` or `wasteland` into `state`. Phase 1 has no
    rules for those bands, so a server at score 12 is seeded `strained`; Phase 2
    reclassifies it on its first tick. See `eco_config.state_for_score`.
  * It does not backfill the ledger. There is nothing to backfill it from - no record of
    who caused any of the decay in the current scores exists, and inventing one would put
    debt on names that never earned it.

**IT IS SAFE TO RUN WITH THE BOT UP**, and safe to run twice. Six new tables, four new
indexes, nothing existing altered; rows already present are left exactly as they are.

    python migrate_eco_pollution.py             # report only
    python migrate_eco_pollution.py --apply     # do it
"""
import argparse
import os
import shutil
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.eco_config import (ACTIVITY_TABLE, DEPLOY_TABLE, GUILD_TABLE, INDEX_NAMES,
                              INDEXES, LEDGER_TABLE, SCHEMA, TABLES, TUNING_TABLE,
                              USER_TABLE, capacity_for, pollution_for_score, score_for,
                              state_for_score)

DB = 'ecosystem.db'

# What a fresh row's capacity is, and the only AU7 this script can honestly assume.
SEED_AU7 = 1


def table_set(conn):
    return {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}


def index_set(conn):
    return {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index'")}


def survey_guilds(conn, existing_tables):
    """
    One `(guild_id, score, pollution, capacity, state)` per guild that needs a row.

    A guild that already has an `eco_guild` row is left out entirely rather than
    recomputed - its pollution is live data by then, and the score it was migrated from
    stopped being the truth the first time anything absorbed or polluted.
    """
    already = set()
    if GUILD_TABLE in existing_tables:
        already = {row[0] for row in conn.execute(
            f"SELECT guild_id FROM {GUILD_TABLE}")}

    rows = []
    for guild_id, raw_score in conn.execute(
            "SELECT guild_id, ecosystem_score FROM servers"):
        if guild_id is None or str(guild_id) in already:
            continue
        # The column defaults to 50 but is nullable, and a NULL here would otherwise
        # become a score of 0 - a server migrated straight into the worst band it has.
        score = 50 if raw_score is None else max(0, min(100, int(raw_score)))
        capacity = capacity_for(SEED_AU7)
        pollution = pollution_for_score(score, capacity)
        rows.append((str(guild_id), score, pollution, capacity,
                     state_for_score(score)))
    return rows, len(already)


def survey_members(conn, existing_tables):
    """Every `(guild_id, user_id)` pair that has no `eco_user` row yet."""
    already = set()
    if USER_TABLE in existing_tables:
        already = {(row[0], row[1]) for row in conn.execute(
            f"SELECT guild_id, user_id FROM {USER_TABLE}")}

    pairs = []
    for user_id, guild_id in conn.execute(
            "SELECT DISTINCT user_id, guild_id FROM guild_members "
            "WHERE user_id IS NOT NULL AND guild_id IS NOT NULL"):
        pair = (str(guild_id), str(user_id))
        if pair not in already:
            pairs.append(pair)
    return pairs, len(already)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument('--db', default=DB, help="path to ecosystem.db")
    parser.add_argument('--apply', action='store_true',
                        help="actually write; without it this only reports")
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"  no database at {args.db}")
        return 1

    conn = sqlite3.connect(args.db)
    tables = table_set(conn)
    indexes = index_set(conn)

    if 'servers' not in tables:
        print("  this database has no `servers` table - wrong file?")
        return 1

    missing_tables = [t for t in TABLES if t not in tables]
    missing_indexes = [name for name in INDEX_NAMES if name not in indexes]
    guilds, guilds_already = survey_guilds(conn, tables)
    members, members_already = survey_members(conn, tables)
    journal = conn.execute("PRAGMA journal_mode").fetchone()[0]

    print(f"\n=== ECOSYSTEM POLLUTION MIGRATION on {args.db} ===")
    print(f"\n  journal mode    : {journal}"
          f"{'' if journal.lower() == 'wal' else '  (§8 wants WAL - will be set)'}")
    for table in TABLES:
        state = 'exists' if table in tables else 'to be created'
        print(f"  {table:<16}: {state}")
    print(f"  indexes         : {len(INDEXES) - len(missing_indexes)}/{len(INDEXES)}"
          f" present")

    print(f"\n  eco_guild rows  : {guilds_already} already, {len(guilds)} to seed")
    for guild_id, score, pollution, capacity, state in guilds:
        # The score is printed back out of the seeded numbers rather than echoed from
        # `servers`, so the line is evidence that the round trip holds rather than a
        # restatement of the input.
        print(f"      {guild_id:<20} score {score:>3} -> pollution "
              f"{pollution:>8.2f} / capacity {capacity:g}  "
              f"= {score_for(pollution, capacity):>5.1f}  [{state}]")
    print(f"  eco_user rows   : {members_already} already, {len(members)} to seed"
          f"  (first_seen_at = 0, so no new-member discount)")

    nothing_to_do = not missing_tables and not missing_indexes and not guilds \
        and not members and journal.lower() == 'wal'

    if not args.apply:
        if nothing_to_do:
            print("\n  Nothing to do; the database is already migrated.")
        else:
            print("\n  Nothing was written. Re-run with --apply to make these changes.")
        return 0

    if nothing_to_do:
        print("\n  Nothing to do; the database is already migrated.")
        return 0

    backup = f"{args.db}.pre-eco.{int(time.time())}"
    shutil.copy2(args.db, backup)
    print(f"\n  backup written  : {backup}")

    # WAL before the writes rather than after, because §8's reason for wanting it is
    # that a reader must not block on the tick's writes - and the tick starts the moment
    # the new code is deployed, which may well be before anybody reads this output.
    if journal.lower() != 'wal':
        conn.execute("PRAGMA journal_mode=WAL")
        print(f"  journal mode    : "
              f"{conn.execute('PRAGMA journal_mode').fetchone()[0]}")

    for statement in SCHEMA.values():
        conn.execute(statement)
    for statement in INDEXES:
        conn.execute(statement)

    now = int(time.time())

    # `last_tick = now`, NOT 0. The tick prorates absorption against the time since the
    # last one, so a zero here is 1970 and the first tick would absorb fifty-six years
    # of capacity in one go - every migrated server at score 100 before anybody saw the
    # number it was supposed to have been carried over with.
    conn.executemany(
        f"INSERT OR IGNORE INTO {GUILD_TABLE} "
        f"(guild_id, pollution, capacity, capacity_updated_at, state, state_since, "
        f" last_tick, paused) VALUES (?, ?, ?, 0, ?, ?, ?, 0)",
        [(guild_id, pollution, capacity, state, now, now)
         for guild_id, _score, pollution, capacity, state in guilds])

    conn.executemany(
        f"INSERT OR IGNORE INTO {USER_TABLE} (guild_id, user_id, first_seen_at) "
        f"VALUES (?, ?, 0)", members)

    conn.commit()

    seeded = conn.execute(f"SELECT COUNT(*) FROM {GUILD_TABLE}").fetchone()[0]
    users = conn.execute(f"SELECT COUNT(*) FROM {USER_TABLE}").fetchone()[0]
    tables_now = table_set(conn)
    indexes_now = index_set(conn)

    print(f"\n  tables created  : {len(missing_tables)} "
          f"({', '.join(missing_tables) if missing_tables else 'none needed'})")
    print(f"  indexes created : {len(missing_indexes)}")
    print(f"  {GUILD_TABLE} rows  : {seeded}")
    print(f"  {USER_TABLE} rows   : {users}")

    still_missing = [t for t in TABLES if t not in tables_now] + \
                    [s.split()[5] for s in INDEXES if s.split()[5] not in indexes_now]
    if still_missing:
        print(f"\n  ⚠️  STILL MISSING: {', '.join(still_missing)}")
        return 1

    print(f"\n  {LEDGER_TABLE}, {DEPLOY_TABLE}, {ACTIVITY_TABLE} and {TUNING_TABLE} "
          f"are empty by design - nothing to backfill them from.")
    print("  `servers.ecosystem_score` is untouched and is still the number the bot "
          "reads.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
