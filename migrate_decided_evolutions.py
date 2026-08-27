"""
Give the four ambiguous evolutions the conditions the games decide them by.

**WHAT IS WRONG TODAY.** Five species have two or more level-up rules that share every
recorded condition and disagree about the outcome, so the tie falls to row order and one
answer is unreachable:

    cosmoem  L53  -> solgaleo / lunala                    (the games ask the time of day)
    burmy    L20  -> wormadam-plant / mothim              (gender, and where it has been)
    tyrogue  L20  -> hitmonlee / hitmonchan / hitmontop   (Attack against Defence)
    wurmple  L7   -> silcoon / cascoon                    (a value fixed at capture)

Eevee is the fifth and is deliberately left alone: Leafeon and Glaceon are decided by
standing next to a particular rock and Sylveon by affection, none of which this world
has, and Eevee's stone routes already work.

**WHAT THIS SCRIPT DOES.**

  1. adds four nullable columns to evolution_rules - `gender`, `biome`, `stat_rule` and
     `personality`;
  2. stamps the condition each existing rule was always missing;
  3. inserts the TWO Wormadam cloaks that have no rule at all. Only
     `burmy -> wormadam-plant` exists; Sandy and Trash are species in this database that
     nothing could ever produce.

**THE CLOAK IS THE SERVER'S HABITAT.** Burmy's cloak is set in the games by where it last
battled. This world has three habitat biomes and Wormadam has three cloaks, which is a
closer fit than it has any right to be:

    forest  -> Plant        coastal -> Sandy        urban -> Trash

**WURMPLE IS NOT A COIN FLIP.** The games fix the answer at capture and re-checking it
gives the same answer forever. `utils.constants.personality_of` hashes the instance id -
assigned once, never rewritten - so a player who retries an evolution gets the same
Silcoon they would have got the first time.

**IT IS SAFE TO RUN WITH THE BOT UP.** Four nullable columns and a dozen rows of static
reference data. `check_evolution_trigger` asks `has_column` first, so a bot running the
new code before this behaves exactly as it does today.

    python migrate_decided_evolutions.py            # report only, writes nothing
    python migrate_decided_evolutions.py --apply    # do it

Idempotent. Running it twice is a no-op the second time.
"""

import argparse
import os
import shutil
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.constants import HABITAT_BIOMES, PERSONALITY_BUCKETS, STAT_RULES

DB = 'ecosystem.db'
TABLE = 'evolution_rules'

NEW_COLUMNS = (
    ('gender', 'TEXT'),
    ('biome', 'TEXT'),
    ('stat_rule', 'TEXT'),
    ('personality', 'INTEGER'),
)

# (base species, evolved species, {column: value}) - by NAME, because a name is checkable
# by eye and a row id is not. Every one is verified against the database before anything
# is written.
STAMPS = [
    # Cosmoem needs no new column at all: `time_of_day` has been there since the table
    # was built and the resolver has always read it. This is the cheapest of the four.
    ('cosmoem', 'solgaleo', {'time_of_day': 'day'}),
    ('cosmoem', 'lunala', {'time_of_day': 'night'}),

    # Burmy: the sex decides the species, the cloak decides which Wormadam.
    ('burmy', 'wormadam-plant', {'gender': 'f', 'biome': 'forest'}),
    ('burmy', 'mothim', {'gender': 'm'}),

    # Tyrogue's base Attack and Defence are both 35, so this is decided entirely by its
    # IVs, EVs and nature - which is why the resolver computes the real stats.
    ('tyrogue', 'hitmonlee', {'stat_rule': 'attack>defense'}),
    ('tyrogue', 'hitmonchan', {'stat_rule': 'defense>attack'}),
    ('tyrogue', 'hitmontop', {'stat_rule': 'attack=defense'}),

    # The games send the lower half of the personality value to Silcoon.
    ('wurmple', 'silcoon', {'personality': 0}),
    ('wurmple', 'cascoon', {'personality': 1}),
]

# (base, evolved, template evolved, {column: value}) - a rule that does not exist yet,
# copied from a sibling so its level and trigger cannot drift from it.
INSERTS = [
    ('burmy', 'wormadam-sandy', 'wormadam-plant', {'gender': 'f', 'biome': 'coastal'}),
    ('burmy', 'wormadam-trash', 'wormadam-plant', {'gender': 'f', 'biome': 'urban'}),
]

GENDERS = ('m', 'f')


def species_id(conn, name):
    row = conn.execute("SELECT pokedex_id FROM base_pokemon_species WHERE name = ?",
                       (name,)).fetchone()
    return row[0] if row else None


def validate(values):
    """Anything wrong with the values a stamp wants to write."""
    problems = []
    if 'gender' in values and values['gender'] not in GENDERS:
        problems.append(f"`{values['gender']}` is not a sex this database records")
    if 'biome' in values and values['biome'] not in HABITAT_BIOMES:
        problems.append(f"`{values['biome']}` is not a habitat biome "
                        f"({', '.join(HABITAT_BIOMES)})")
    if 'stat_rule' in values and values['stat_rule'] not in STAT_RULES:
        problems.append(f"`{values['stat_rule']}` is not a comparison the resolver "
                        f"understands ({', '.join(STAT_RULES)})")
    if 'personality' in values and not (
            0 <= values['personality'] < PERSONALITY_BUCKETS):
        problems.append(f"personality {values['personality']} is outside the "
                        f"{PERSONALITY_BUCKETS} buckets personality_of produces")
    return problems


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
    existing = [row[1] for row in conn.execute(f"PRAGMA table_info({TABLE})")]
    to_add = [(name, kind) for name, kind in NEW_COLUMNS if name not in existing]
    print(f"\n  columns to add : {[name for name, _k in to_add] or 'none'}")

    problems, stamps, inserts = [], [], []

    for base, evolved, values in STAMPS:
        problems += [f"{base} -> {evolved}: {note}" for note in validate(values)]
        base_id, evolved_id = species_id(conn, base), species_id(conn, evolved)
        if base_id is None:
            problems.append(f"no species called `{base}`")
            continue
        if evolved_id is None:
            problems.append(f"no species called `{evolved}`")
            continue
        rows = [row[0] for row in conn.execute(
            f"SELECT id FROM {TABLE} WHERE base_species_id = ? "
            f"AND evolved_species_id = ?", (base_id, evolved_id))]
        if len(rows) != 1:
            problems.append(f"{base} -> {evolved} has {len(rows)} rules, expected "
                            f"exactly one")
            continue

        # ALREADY CORRECT IS NOTHING TO DO. Without this the second run re-stamps every
        # rule with the value it already has, takes a backup to do it, and reports work
        # it did not need - which is not what "idempotent" means to anyone reading the
        # output. Skipped only when EVERY column already matches; a partially-stamped
        # rule is still stamped.
        if not to_add:
            current = conn.execute(
                f"SELECT {', '.join(values)} FROM {TABLE} WHERE id = ?",
                (rows[0],)).fetchone()
            if current and list(current) == list(values.values()):
                continue
        stamps.append((rows[0], base, evolved, values))

    for base, evolved, template, values in INSERTS:
        problems += [f"{base} -> {evolved}: {note}" for note in validate(values)]
        base_id = species_id(conn, base)
        evolved_id = species_id(conn, evolved)
        template_id = species_id(conn, template)
        if None in (base_id, evolved_id, template_id):
            problems.append(f"{base} -> {evolved}: a species in this row is missing")
            continue
        already = conn.execute(
            f"SELECT COUNT(*) FROM {TABLE} WHERE base_species_id = ? "
            f"AND evolved_species_id = ?", (base_id, evolved_id)).fetchone()[0]
        if already:
            continue
        source = conn.execute(
            f"SELECT id FROM {TABLE} WHERE base_species_id = ? "
            f"AND evolved_species_id = ?", (base_id, template_id)).fetchone()
        if not source:
            problems.append(f"{base} -> {evolved}: no `{template}` rule to copy from")
            continue
        inserts.append((source[0], base, evolved, evolved_id, values))

    print(f"  rules to stamp : {len(stamps)}")
    for _id, base, evolved, values in stamps:
        print(f"    • {base:10} -> {evolved:16} "
              f"{', '.join(f'{k}={v}' for k, v in values.items())}")
    print(f"  rules to add   : {len(inserts)}")
    for _src, base, evolved, _eid, values in inserts:
        print(f"    • {base:10} -> {evolved:16} "
              f"{', '.join(f'{k}={v}' for k, v in values.items())}")

    if not to_add and not stamps and not inserts:
        print("\n  Nothing to do.")
        conn.close()
        return 0

    if problems:
        print("\n  PROBLEMS — nothing was changed:")
        for problem in problems:
            print(f"    • {problem}")
        conn.close()
        return 1

    if not args.apply:
        print("\n  Nothing was written. Re-run with --apply to make these changes.")
        conn.close()
        return 0

    backup = f"{args.db}.pre-decided.{int(time.time())}"
    shutil.copy2(args.db, backup)
    print(f"\n  backup written  : {backup}")

    try:
        conn.execute("BEGIN")
        for name, kind in to_add:
            conn.execute(f"ALTER TABLE {TABLE} ADD COLUMN {name} {kind}")
        for rule_id, _b, _e, values in stamps:
            assignments = ", ".join(f"{column} = ?" for column in values)
            conn.execute(f"UPDATE {TABLE} SET {assignments} WHERE id = ?",
                         (*values.values(), rule_id))
        for source_id, _b, _e, evolved_id, values in inserts:
            # Copied column by column from the sibling rather than written out, so the
            # new rule cannot disagree with it about the level or the trigger.
            columns = [row[1] for row in conn.execute(f"PRAGMA table_info({TABLE})")
                       if row[1] != 'id']
            row = conn.execute(
                f"SELECT {', '.join(columns)} FROM {TABLE} WHERE id = ?",
                (source_id,)).fetchone()
            fresh = dict(zip(columns, row))
            fresh['evolved_species_id'] = evolved_id
            fresh.update(values)
            conn.execute(
                f"INSERT INTO {TABLE} ({', '.join(fresh)}) "
                f"VALUES ({', '.join('?' for _ in fresh)})", tuple(fresh.values()))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"\n  FAILED, nothing changed: {e}")
        print(f"  the backup at {backup} is identical to the database as it stands.")
        conn.close()
        return 1

    gated = conn.execute(
        f"SELECT COUNT(*) FROM {TABLE} WHERE gender IS NOT NULL OR biome IS NOT NULL "
        f"OR stat_rule IS NOT NULL OR personality IS NOT NULL").fetchone()[0]
    print(f"\n  done. {gated} rule(s) now carry a condition the games decide by.")
    print("  The bot picks this up on its next evolution check — no restart needed.")
    conn.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
