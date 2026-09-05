"""
Give every specimen somewhere to record its Tera type.

**ONE COLUMN, AND DELIBERATELY LEFT EMPTY.** `caught_pokemon.tera_type` is NULL for every
specimen after this runs, and that is the finished state rather than a job half done:
`utils.tera.tera_type_of` reads NULL as "its primary type", which is the games' rule. So
every specimen can Terastallise into what it already is from the moment the feature lands,
and Tera Shards buy a DIFFERENT type rather than buying the mechanic.

**BACKFILLING WOULD BE WORSE THAN NOTHING.** Writing each specimen's primary type into the
column looks tidier and is a lie: it cannot then be told apart from a type somebody chose
and paid fifty shards for, so `!tera` could not say whether a specimen had ever been
changed. NULL means "never chosen", which is a fact worth keeping.

**IT IS SAFE TO RUN WITH THE BOT UP.** One added column, defaulting to NULL. Code that has
not been deployed yet neither reads nor writes it.

    python migrate_tera_types.py             # report only
    python migrate_tera_types.py --apply     # do it
"""
import argparse
import os
import shutil
import sqlite3
import time

DB = 'ecosystem.db'
TABLE = 'caught_pokemon'
COLUMN = 'tera_type'


def columns(conn, table):
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]


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
    held = columns(conn, TABLE)
    specimens = conn.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0]

    print(f"\n  table              : {TABLE}")
    print(f"  specimens          : {specimens:,}")
    print(f"  column {COLUMN:<12}: {'present' if COLUMN in held else 'to be added'}")

    if COLUMN in held:
        chosen = conn.execute(
            f"SELECT COUNT(*) FROM {TABLE} "
            f"WHERE {COLUMN} IS NOT NULL AND TRIM({COLUMN}) != ''").fetchone()[0]
        print(f"  types chosen       : {chosen:,} "
              f"({specimens - chosen:,} still on their primary)")
        print("\n  Nothing to do; the column is already there.")
        return 0

    if not args.apply:
        print("\n  Nothing was written. Re-run with --apply to add it.")
        return 0

    backup = f"{args.db}.pre-tera.{int(time.time())}"
    shutil.copy2(args.db, backup)
    print(f"\n  backup written     : {backup}")

    conn.execute(f"ALTER TABLE {TABLE} ADD COLUMN {COLUMN} TEXT")
    conn.commit()

    print(f"  column added       : {COLUMN} TEXT, NULL for all {specimens:,}")
    print("\n  NULL means 'its primary type', which is what every specimen "
          "Terastallises into\n  until somebody spends fifty shards to change it.")
    return 0 if COLUMN in columns(conn, TABLE) else 1


if __name__ == '__main__':
    raise SystemExit(main())
