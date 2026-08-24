"""
Fix the Kubfu rule that sends the Tower of Waters to the wrong Urshifu.

**WHAT IS WRONG TODAY.** `evolution_rules` holds five routes out of Kubfu, and two of
them claim the same trigger with different answers:

    1460  tower-of-darkness  -> urshifu-single-strike     correct
    1461  tower-of-waters    -> urshifu-single-strike     WRONG
    1567  tower-of-waters    -> urshifu-rapid-strike      correct
    1568  use-item scroll-of-darkness -> urshifu-single-strike
    1569  use-item scroll-of-waters   -> urshifu-rapid-strike

Rule 1461 is the Cubone duplicate all over again: two rules, the same trigger, different
outcomes, and the wrong one wins because it was imported first. Between that and a cog
that took row zero of an unordered query, `!evolve <kubfu> ritual` could only ever
produce Single Strike Urshifu. Rapid Strike was unreachable by rite.

The scroll route was not affected - `scroll-of-waters` names its own item and has always
worked - which is why this only showed up for anyone using the ritual.

**WHAT THIS SCRIPT DOES.** For each correction below it finds the rule that names the
wrong destination. If a rule with the RIGHT destination already exists for that trigger,
the wrong one is deleted; if it does not, the wrong one is repointed instead. A trigger
is never left with no rule at all.

**IT IS SAFE TO RUN WITH THE BOT UP.** It touches one row of static reference data and
nothing a player owns.

    python migrate_ritual_rules.py            # report only, writes nothing
    python migrate_ritual_rules.py --apply    # do it

Idempotent. Running it twice is a no-op the second time.
"""

import argparse
import os
import shutil
import sqlite3
import sys
import time

DB = 'ecosystem.db'

# (base species, trigger, the destination it wrongly names, the one it should name)
#
# Only Kubfu today. Hisuian Qwilfish also has two ritual rules - Strong Style and Use
# Move - but both lead to Overqwil, so which one answers makes no difference and there is
# nothing to correct.
WRONG_RITUAL_RULES = [
    ('kubfu', 'tower-of-waters', 'urshifu-single-strike', 'urshifu-rapid-strike'),
]


def species_id(conn, name):
    row = conn.execute("SELECT pokedex_id FROM base_pokemon_species WHERE name = ?",
                       (name,)).fetchone()
    return row[0] if row else None


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
    problems, deletions, repoints = [], [], []

    for base, trigger, wrong, right in WRONG_RITUAL_RULES:
        base_id = species_id(conn, base)
        wrong_id = species_id(conn, wrong)
        right_id = species_id(conn, right)
        for label, value, name in ((base, base_id, 'base'), (wrong, wrong_id, 'wrong'),
                                   (right, right_id, 'right')):
            if value is None:
                problems.append(f"no species called `{label}`")
        if None in (base_id, wrong_id, right_id):
            continue

        bad = [row[0] for row in conn.execute(
            "SELECT id FROM evolution_rules WHERE base_species_id = ? "
            "AND trigger_name = ? AND evolved_species_id = ?",
            (base_id, trigger, wrong_id))]
        good = [row[0] for row in conn.execute(
            "SELECT id FROM evolution_rules WHERE base_species_id = ? "
            "AND trigger_name = ? AND evolved_species_id = ?",
            (base_id, trigger, right_id))]

        if not bad:
            print(f"  {base} / {trigger}: already correct")
            continue
        if good:
            deletions += [(rule_id, base, trigger, wrong) for rule_id in bad]
        else:
            # Nothing else serves this trigger, so repoint rather than delete - deleting
            # would leave the Tower of Waters with no rule at all, which is a worse
            # database than the one we started with.
            repoints += [(rule_id, base, trigger, wrong, right, right_id)
                         for rule_id in bad]

    print(f"\n  rules to delete  : {len(deletions)}")
    for rule_id, base, trigger, wrong in deletions:
        print(f"    • #{rule_id}  {base} / {trigger} -> {wrong}  (a correct rule "
              f"already exists)")
    print(f"  rules to repoint : {len(repoints)}")
    for rule_id, base, trigger, wrong, right, _rid in repoints:
        print(f"    • #{rule_id}  {base} / {trigger}: {wrong} -> {right}")

    if problems:
        print("\n  PROBLEMS — nothing was changed:")
        for problem in problems:
            print(f"    • {problem}")
        conn.close()
        return 1

    if not deletions and not repoints:
        print("\n  Nothing to do.")
        conn.close()
        return 0

    if not args.apply:
        print("\n  Nothing was written. Re-run with --apply to make these changes.")
        conn.close()
        return 0

    backup = f"{args.db}.pre-ritual.{int(time.time())}"
    shutil.copy2(args.db, backup)
    print(f"\n  backup written  : {backup}")

    try:
        conn.execute("BEGIN")
        for rule_id, _b, _t, _w in deletions:
            conn.execute("DELETE FROM evolution_rules WHERE id = ?", (rule_id,))
        for rule_id, _b, _t, _w, _r, right_id in repoints:
            conn.execute("UPDATE evolution_rules SET evolved_species_id = ? "
                         "WHERE id = ?", (right_id, rule_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"\n  FAILED, nothing changed: {e}")
        print(f"  the backup at {backup} is identical to the database as it stands.")
        conn.close()
        return 1

    print(f"\n  done. {len(deletions)} deleted, {len(repoints)} repointed.")
    print("  The bot picks this up on its next evolution check — no restart needed.")
    conn.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
