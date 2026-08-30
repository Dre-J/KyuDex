"""
Give a specimen more than one label.

**WHAT IS WRONG TODAY.** `caught_pokemon.custom_tag` is a single TEXT column, so a
specimen has exactly one tag. Two consequences, both live:

  * `auto_tag` picks ONE of shiny / mythical / legendary / pseudo / alpha by a priority
    order that exists only because the column holds one value. A shiny alpha legendary
    is filed as `shiny`, and its Alpha marking - 2% of captures - is invisible;
  * a trainer cannot file the same animal under `competitive` and `trade-fodder`.

**WHAT THIS SCRIPT DOES.**

  1. creates `specimen_tags(instance_id, tag, added_at)`, one row per label, with a
     primary key on the pair so the same tag cannot land twice;
  2. indexes `tag`, because "find everything tagged X" is the whole point;
  3. copies every existing non-empty `custom_tag` into it, normalised the way
     `utils.tags.normalise_tag` normalises everything else.

**`custom_tag` IS NOT DROPPED.** The column stays exactly as it is, unread. Dropping it
would make this migration one-way for no benefit, and the rollback - "stop deploying the
new code" - is worth keeping cheap. Nothing writes to it any more.

**WHAT IT DOES NOT DO.** It does not grant the automatic tags a specimen would earn
under the new rules. A shiny alpha caught last week stays tagged `shiny` and does not
gain `alpha` retroactively; only new captures get the full set. That was a deliberate
choice - backfilling would rewrite the filing of every specimen already in the database,
including any a trainer had deliberately renamed.

**IT IS SAFE TO RUN WITH THE BOT UP.** One new table and one index; nothing existing is
altered. Every reader in `utils/tags.py` asks `has_table` first, so a bot running the new
code before this behaves exactly as it does today - no tags, no crash.

    python migrate_specimen_tags.py             # report only
    python migrate_specimen_tags.py --apply     # do it
"""
import argparse
import os
import shutil
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.tags import TABLE, normalise_tag

DB = 'ecosystem.db'

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS {TABLE} (
    instance_id TEXT NOT NULL,
    tag         TEXT NOT NULL,
    added_at    TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (instance_id, tag),
    FOREIGN KEY (instance_id) REFERENCES caught_pokemon(instance_id)
)
"""

# Not UNIQUE - many specimens share a tag, which is the point of having one.
INDEX = f"CREATE INDEX IF NOT EXISTS idx_{TABLE}_tag ON {TABLE} (tag)"


def survey(conn):
    """
    What is in `custom_tag` today, as (rows, unusable).

    `unusable` is the labels that cannot survive normalisation - a purely numeric tag
    collides with a box number, and a tag matching a sub-command word would make
    `!tags add` ambiguous. Reported rather than silently dropped, because a trainer whose
    filing quietly vanished deserves to be told which one.
    """
    rows, unusable = [], []
    for instance_id, raw in conn.execute(
            "SELECT instance_id, custom_tag FROM caught_pokemon "
            "WHERE custom_tag IS NOT NULL AND TRIM(custom_tag) != ''"):
        tag = normalise_tag(raw)
        if tag is None:
            unusable.append((instance_id, raw))
        else:
            rows.append((instance_id, tag, raw))
    return rows, unusable


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
    existing = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (TABLE,)).fetchone() is not None

    if 'custom_tag' not in [r[1] for r in conn.execute("PRAGMA table_info(caught_pokemon)")]:
        print("  caught_pokemon has no custom_tag column - nothing to carry over.")
        rows, unusable = [], []
    else:
        rows, unusable = survey(conn)

    already = 0
    if existing:
        already = conn.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0]
        # Rows already carried over are not carried again. This is what makes a second
        # run a no-op rather than a duplicate-key error.
        present = {(i, t) for i, t in conn.execute(
            f"SELECT instance_id, tag FROM {TABLE}")}
        rows = [r for r in rows if (r[0], r[1]) not in present]

    print(f"\n  table {TABLE}   : {'exists' if existing else 'to be created'}")
    print(f"  rows already in : {already}")
    print(f"  labels to carry : {len(rows)}")
    if unusable:
        print(f"  cannot carry    : {len(unusable)}")
        for instance_id, raw in unusable[:10]:
            print(f"      {instance_id[:8]}  {raw!r}")
        if len(unusable) > 10:
            print(f"      ... and {len(unusable) - 10} more")

    changed = [(raw, tag) for _i, tag, raw in rows if raw.strip().lower() != tag]
    if changed:
        print(f"  normalised      : {len(changed)}")
        for raw, tag in changed[:8]:
            print(f"      {raw!r} -> {tag!r}")

    if not args.apply:
        if not existing or rows:
            print("\n  Nothing was written. Re-run with --apply to make these changes.")
        else:
            print("\n  Nothing to do; the database is already migrated.")
        return 0

    if existing and not rows:
        print("\n  Nothing to do; the database is already migrated.")
        return 0

    backup = f"{args.db}.pre-tags.{int(time.time())}"
    shutil.copy2(args.db, backup)
    print(f"\n  backup written  : {backup}")

    conn.execute(SCHEMA)
    conn.execute(INDEX)
    conn.executemany(
        f"INSERT OR IGNORE INTO {TABLE} (instance_id, tag) VALUES (?, ?)",
        [(instance_id, tag) for instance_id, tag, _raw in rows])
    conn.commit()

    total = conn.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0]
    distinct = conn.execute(f"SELECT COUNT(DISTINCT tag) FROM {TABLE}").fetchone()[0]
    print(f"  carried over    : {len(rows)}")
    print(f"  rows now        : {total}  ({distinct} distinct tags)")
    print("\n  custom_tag is left exactly as it was, unread. Nothing writes to it now.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
