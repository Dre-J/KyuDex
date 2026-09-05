"""
Put Nihil Light in the moves table.

**IT IS A REAL MOVE AND THE DATABASE HAS NEVER HEARD OF IT.** `base_moves` was imported
from PokeAPI before Generation 9's later additions landed, so Mega Zygarde's signature -
an upgrade to Core Enforcer, and the only Dragon attack in the game that a Fairy cannot
refuse - is missing. The engine reads every move's numbers out of that table, so without
a row the move cannot be taught, scored, or thrown.

**WHAT THE ROW SAYS**, from Serebii's AttackDex:

    dragon · special · 100 power · 100% accuracy · 5 PP · priority 0

**SEREBII LISTS THE MOVE TWICE AND THE TWO DISAGREE.** Pokemon Champions has it at 100
power, special; Pokemon Legends: Z-A has it at 200, physical. The Champions line is the
one taken here, for two reasons: `base_moves` is mainline data throughout, and Z-A's 200
is priced against a real-time system with cooldowns instead of PP, so the number does not
mean the same thing in a turn-based engine. It also lands exactly where an upgrade to
Core Enforcer should - same 100 power, same element, single target instead of a spread,
and a bypass Core Enforcer does not have.

The one number neither source gave is **PP**, so 5 is a choice rather than a fact: a
signature attack priced below Core Enforcer's 10. Change it here and re-run if you would
rather it matched.

**THE BYPASS IS NOT IN THIS TABLE.** `base_moves` has no column for "walks through an
immunity", and inventing one for a single move would be a schema change for a fact that
belongs with the other two immunity-piercing rules. It lives in
`utils.constants.IMMUNITY_PIERCING_MOVES`, beside Ring Target and the Iron Ball, and is
read at the one place in `calculate_damage` where the type chart produces a zero.

**WHO CAN LEARN IT IS NOT HERE EITHER.** Movepool data has a door of its own -
`data/movepool_overrides.json`, applied with `!learnset sync` - and writing rows into
`species_movepool` behind its back is exactly what that door exists to prevent. The
override entries for the Zygarde forms ship in this same change; run the sync after this.

**IDEMPOTENT.** A second run reports "already correct" and writes nothing. A row that
exists but disagrees with MOVE is UPDATEd rather than duplicated, because `base_moves`
has no primary key on `name` and an INSERT would quietly give the engine two answers.

    python migrate_nihil_light.py             # report only
    python migrate_nihil_light.py --apply     # do it
"""
import argparse
import os
import shutil
import sqlite3
import time

DB = 'ecosystem.db'
TABLE = 'base_moves'

# Every column `base_moves` has, so the row is complete rather than half NULL. The
# secondary-effect columns are all "none"/0: the Fairy bypass is not an ailment, a stat
# change or a status, and saying so explicitly keeps the engine's `ailment != 'none'`
# branches away from it.
MOVE = {
    'name':           'nihil-light',
    'type':           'dragon',
    'power':          100,
    'accuracy':       100,
    'damage_class':   'special',
    'pp':             5,
    'priority':       0,
    'target':         'selected-pokemon',
    'ailment':        'none',
    'ailment_chance': 0,
    'stat_name':      'none',
    'stat_change':    0,
    'stat_chance':    0,
    'status_type':    'none',
    'status_chance':  0,
    'healing':        0,
    'drain':          0,
}


def existing(conn):
    """The row as it stands, as a dict, or None. Reads only the columns MOVE names."""
    columns = [r[1] for r in conn.execute(f"PRAGMA table_info({TABLE})")]
    wanted = [c for c in MOVE if c in columns]
    row = conn.execute(
        f"SELECT {', '.join(wanted)} FROM {TABLE} WHERE name = ?",
        (MOVE['name'],)).fetchone()
    return (dict(zip(wanted, row)) if row else None), columns


def differences(row):
    """`[(column, is, should_be)]` - empty when the row already says the right thing."""
    return [(column, row.get(column), value)
            for column, value in MOVE.items()
            if column in row and row.get(column) != value]


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
    row, columns = existing(conn)

    missing = [c for c in MOVE if c not in columns]
    if missing:
        # Reported rather than guessed at. A column this script does not know about is
        # harmless - it stays NULL - but a column MOVE names and the table lacks means
        # the schema has moved and the numbers below may no longer land where they mean to.
        print(f"  {TABLE} has no column: {', '.join(missing)}")

    duplicates = conn.execute(
        f"SELECT COUNT(*) FROM {TABLE} WHERE name = ?", (MOVE['name'],)).fetchone()[0]

    print(f"\n  move            : {MOVE['name']}")
    print(f"  rows present    : {duplicates}")

    if row is None:
        print("  status          : missing, to be inserted")
        for column, value in MOVE.items():
            print(f"      {column:<15} {value}")
        drift = []
    else:
        drift = differences(row)
        if drift:
            print("  status          : present but wrong, to be corrected")
            for column, is_now, should_be in drift:
                print(f"      {column:<15} {is_now!r} -> {should_be!r}")
        else:
            print("  status          : already correct")

    if row is not None and not drift and duplicates == 1:
        print("\n  Nothing to do; the database already knows this move.")
        return 0

    if not args.apply:
        print("\n  Nothing was written. Re-run with --apply to make these changes.")
        return 0

    backup = f"{args.db}.pre-nihil.{int(time.time())}"
    shutil.copy2(args.db, backup)
    print(f"\n  backup written  : {backup}")

    writable = [c for c in MOVE if c in columns]
    if duplicates > 1:
        # Two rows for one move is the engine tossing a coin over the move's numbers.
        # Collapse to one rather than updating both and leaving the duplicate.
        print(f"  duplicates      : {duplicates}, collapsing to one")
        conn.execute(f"DELETE FROM {TABLE} WHERE name = ?", (MOVE['name'],))
        duplicates = 0

    if duplicates == 0:
        conn.execute(
            f"INSERT INTO {TABLE} ({', '.join(writable)}) "
            f"VALUES ({', '.join('?' * len(writable))})",
            [MOVE[c] for c in writable])
        print("  inserted        : 1 row")
    else:
        conn.execute(
            f"UPDATE {TABLE} SET {', '.join(f'{c} = ?' for c in writable)} "
            f"WHERE name = ?",
            [MOVE[c] for c in writable] + [MOVE['name']])
        print(f"  corrected       : {len(drift)} column(s)")

    conn.commit()

    check, _ = existing(conn)
    still = differences(check or {})
    print(f"  verified        : {'clean' if check and not still else 'STILL WRONG'}")
    print("\n  Next: `!learnset sync` applies the Zygarde movepool entries that ship "
          "with this change.")
    return 0 if check and not still else 1


if __name__ == '__main__':
    raise SystemExit(main())
