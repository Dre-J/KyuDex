"""
Give fused specimens somewhere to live.

**WHAT THIS IS FOR.** Kyurem-White is a Kyurem that absorbed a Reshiram, and that
Reshiram had its own IVs, EVs, nickname, moves and shininess. When the pair separates it
has to come back exactly as it was, so fusing cannot delete it - it has to park it.

This adds one table:

    fused_specimens(host_instance_id, item_name, base_pokedex_id, payload, fused_at)

`payload` is the absorbed specimen's whole caught_pokemon row as JSON. A column list
would have to be kept in step with a 40-column table that has been ALTERed a dozen
times; JSON cannot drift, and `separate` restores whichever columns still exist.

**THERE IS NO user_id COLUMN AND THAT IS DELIBERATE.** The owner is whoever owns the
host right now, so a fused Kyurem trades like any other specimen and the new owner gets
the Reshiram when they separate it. None of the nine ownership-transfer sites in the
repo needed a line changed.

**WHY A TABLE RATHER THAN A FLAG.** The alternative was leaving the absorbed specimen in
caught_pokemon with a "hidden" marker. 66 places in this repo SELECT from that table, and
one missed filter means a fused Reshiram that can still be traded, released or sent into
battle. A row that is not in the table cannot be any of those.

**IT IS SAFE TO RUN WITH THE BOT UP.** It creates a table and touches nothing that
exists. `utils.forms.fusion_record` returns None when the table is absent, so a bot
running the new code before this migration simply has no fusions - `!form` refuses to
fuse and everything else behaves as it does today.

    python migrate_form_items.py            # report only, writes nothing
    python migrate_form_items.py --apply    # do it

Idempotent. Running it twice is a no-op the second time.
"""

import argparse
import os
import shutil
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.forms import FORM_ITEMS, FUSION_TABLE, HELD_FORM_ITEMS, FUSION

DB = 'ecosystem.db'

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS {FUSION_TABLE} (
    host_instance_id  TEXT PRIMARY KEY,
    item_name         TEXT NOT NULL,
    base_pokedex_id   INTEGER NOT NULL,
    payload           TEXT NOT NULL,
    fused_at          TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (host_instance_id) REFERENCES caught_pokemon(instance_id)
)
"""


def every_species(spec):
    """Every species name a form item mentions."""
    names = set()
    for ring in spec.get('rings', ()):
        names.update(ring)
    names.update(spec.get('grid', {}).values())
    if spec['kind'] == FUSION:
        names.add(spec['host'])
        names.update(spec['fusions'])
        names.update(spec['fusions'].values())
    return names


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default=DB, help="path to ecosystem.db")
    parser.add_argument('--apply', action='store_true',
                        help="actually write; without it this only reports")
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"  no database at {args.db}")
        return 1

    conn = sqlite3.connect(args.db)
    already = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = ?",
        (FUSION_TABLE,)).fetchone()[0] > 0
    print(f"\n  {FUSION_TABLE} already exists : {'yes' if already else 'no'}")

    # EVERY FORM THESE ITEMS CAN REACH MUST BE A SPECIES THIS DATABASE HAS. An item
    # naming a form that is not there is a command that fails at the moment a player
    # uses it, which is the worst time to find out.
    known = {row[0] for row in conn.execute(
        "SELECT name FROM base_pokemon_species WHERE name IS NOT NULL")}
    problems = []
    wanted = set()
    for key, spec in FORM_ITEMS.items():
        missing = sorted(every_species(spec) - known)
        wanted |= every_species(spec)
        if missing:
            problems.append(f"`{key}` names {len(missing)} species this database "
                            f"does not have: {missing}")
    for key, (species, _desc) in HELD_FORM_ITEMS.items():
        wanted.add(species)
        if species not in known:
            problems.append(f"`{key}` is for `{species}`, which is not in the database")

    print(f"  form items                   : "
          f"{len(FORM_ITEMS)} used from the bag, {len(HELD_FORM_ITEMS)} held")
    print(f"  species they reach           : {len(wanted)}, all present"
          if not problems else "")

    fused = 0
    if already:
        fused = conn.execute(f"SELECT COUNT(*) FROM {FUSION_TABLE}").fetchone()[0]
        print(f"  fusions currently parked     : {fused}")
        # An orphan means a host was deleted while holding a fusion, which is what the
        # release guard exists to prevent. Reported rather than cleaned: the specimen
        # inside is recoverable by hand and silently dropping it would not be.
        orphans = conn.execute(f"""
            SELECT COUNT(*) FROM {FUSION_TABLE} f
            LEFT JOIN caught_pokemon c ON c.instance_id = f.host_instance_id
            WHERE c.instance_id IS NULL
        """).fetchone()[0]
        if orphans:
            print(f"  ⚠️  {orphans} parked specimen(s) whose host no longer exists")

    if problems:
        print("\n  PROBLEMS — nothing was changed:")
        for problem in problems:
            print(f"    • {problem}")
        conn.close()
        return 1

    if already:
        print("\n  Nothing to do.")
        conn.close()
        return 0

    if not args.apply:
        print(f"\n  Would create `{FUSION_TABLE}`.")
        print("  Nothing was written. Re-run with --apply to make these changes.")
        conn.close()
        return 0

    backup = f"{args.db}.pre-forms.{int(time.time())}"
    shutil.copy2(args.db, backup)
    print(f"\n  backup written  : {backup}")

    try:
        conn.execute("BEGIN")
        conn.execute(SCHEMA)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"\n  FAILED, nothing changed: {e}")
        print(f"  the backup at {backup} is identical to the database as it stands.")
        conn.close()
        return 1

    print(f"\n  done. `{FUSION_TABLE}` created.")
    print("  The bot picks this up on its next fusion — no restart needed.")
    conn.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
