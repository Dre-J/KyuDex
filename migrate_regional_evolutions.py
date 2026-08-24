"""
Give `evolution_rules` a region, so the regional forms become reachable.

**WHAT IS WRONG TODAY.** Sixteen rules turn an ordinary species into a regional form,
and twelve of those depend on WHERE the trainer is. Nothing in the table records where,
so each of those twelve is indistinguishable from its ordinary twin and the tie falls to
row order - which the ordinary rule always wins, because it was imported first.

Driven against the live database before this migration:

    cubone   L28  -> marowak           (marowak-alola unreachable)
    koffing  L35  -> weezing           (weezing-galar  unreachable)
    quilava  L36  -> typhlosion        (typhlosion-hisui unreachable)
    ... nine more the same way
    dartrix  L36  -> decidueye-HISUI   (fires by accident; see below)

Dartrix is the one that is actively wrong rather than merely missing. Its ordinary rule
is level 34 and the Hisuian one is level 36, and the resolver ranks on `min_level`
descending - so any Dartrix that reaches 36 becomes Hisuian, permanently, with no way
back. It normally evolves at 34 first, which is why nobody has noticed; anything that
delays it (an Everstone, sitting in the PC) flips it.

**WHAT THIS SCRIPT DOES.**

  1. adds `evolution_rules.region`, nullable, meaning "anywhere" when empty;
  2. stamps the region on the twelve rules that need one;
  3. deletes ONE duplicate rule - `cubone -> marowak` exists twice, once with no sky and
     once at night, and the night duplicate is exactly what shadows Alolan Marowak.

**IT IS SAFE TO RUN WITH THE BOT UP.** Nothing here rewrites a row a player owns; it
adds a column and touches thirteen rows of static reference data. `check_evolution_trigger`
and the stone path both ask `has_column` first, so a bot running the new code before the
migration behaves exactly as it did before regional forms existed, and picks the new
behaviour up on its next query afterwards - no restart, no window where evolutions are
broken. Running it against the OLD code is equally safe: the column is simply ignored.

    python migrate_regional_evolutions.py            # report only, writes nothing
    python migrate_regional_evolutions.py --apply    # do it

Idempotent. Running it twice is a no-op the second time.
"""

import argparse
import shutil
import sqlite3
import sys
import time

DB = 'ecosystem.db'

# The twelve, by species NAME rather than by id, because a name is checkable by eye and
# a 10xxx id is not. Every one is verified against the database before anything is
# written - a name that does not resolve stops the migration rather than silently
# skipping a form.
#
# `rockruff -> lycanroc-midnight/dusk` is deliberately NOT here: those are time-of-day
# rules and already work. Neither is `kubfu -> urshifu-rapid-strike`, which is the tower
# choice, a separate mechanic that has never been built.
REGIONAL_RULES = [
    # (base species, evolved species, region)
    ('pikachu',   'raichu-alola',      'alola'),
    ('exeggcute', 'exeggutor-alola',   'alola'),
    ('cubone',    'marowak-alola',     'alola'),

    ('koffing',   'weezing-galar',     'galar'),
    ('mime-jr',   'mr-mime-galar',     'galar'),

    ('quilava',   'typhlosion-hisui',  'hisui'),
    ('dewott',    'samurott-hisui',    'hisui'),
    ('petilil',   'lilligant-hisui',   'hisui'),
    ('rufflet',   'braviary-hisui',    'hisui'),
    ('goomy',     'sliggoo-hisui',     'hisui'),
    ('bergmite',  'avalugg-hisui',     'hisui'),
    ('dartrix',   'decidueye-hisui',   'hisui'),
]

# `cubone -> marowak` is in the table twice: once with no time of day and once at night.
# The second is redundant - a rule with no sky already fires at night - and it is what
# shadows Alolan Marowak, which really is the night evolution. Removing it is a fix in
# its own right and is what makes the Alolan form reachable at the right time.
DUPLICATE_TO_DROP = ('cubone', 'marowak', 'night')


def species_id(conn, name):
    row = conn.execute("SELECT pokedex_id FROM base_pokemon_species WHERE name = ?",
                       (name,)).fetchone()
    return row[0] if row else None


def has_region_column(conn):
    return any(r[1] == 'region'
               for r in conn.execute("PRAGMA table_info(evolution_rules)"))


def plan(conn):
    """Everything this migration would do, and every reason it could not."""
    problems, stamps = [], []

    for base, evolved, region in REGIONAL_RULES:
        base_id, evolved_id = species_id(conn, base), species_id(conn, evolved)
        if base_id is None:
            problems.append(f"no species called `{base}`")
            continue
        if evolved_id is None:
            problems.append(f"no species called `{evolved}`")
            continue
        rows = conn.execute(
            "SELECT id FROM evolution_rules WHERE base_species_id = ? "
            "AND evolved_species_id = ?", (base_id, evolved_id)).fetchall()
        if not rows:
            problems.append(f"no rule turning `{base}` into `{evolved}`")
            continue
        for (rule_id,) in rows:
            stamps.append((rule_id, base, evolved, region))

    # The duplicate, identified precisely rather than by "the second one".
    base, evolved, when = DUPLICATE_TO_DROP
    base_id, evolved_id = species_id(conn, base), species_id(conn, evolved)
    duplicates = []
    if base_id and evolved_id:
        duplicates = [r[0] for r in conn.execute(
            "SELECT id FROM evolution_rules WHERE base_species_id = ? "
            "AND evolved_species_id = ? AND time_of_day = ?",
            (base_id, evolved_id, when)).fetchall()]
        siblings = conn.execute(
            "SELECT COUNT(*) FROM evolution_rules WHERE base_species_id = ? "
            "AND evolved_species_id = ? AND COALESCE(time_of_day, '') = ''",
            (base_id, evolved_id)).fetchone()[0]
        if duplicates and not siblings:
            # Refuse rather than guess. Deleting the night rule is only safe BECAUSE an
            # unrestricted one exists to cover it; without that sibling this would be
            # removing the only way to get a Marowak at all.
            problems.append(
                f"`{base} -> {evolved}` has a night rule but no unrestricted one, "
                f"so removing the night rule would make it unobtainable")
            duplicates = []
    return stamps, duplicates, problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true',
                        help='actually write. Without it, nothing is changed.')
    parser.add_argument('--db', default=DB)
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    already = has_region_column(conn)
    stamps, duplicates, problems = plan(conn)

    print(f"\n  database        : {args.db}")
    print(f"  region column   : {'already present' if already else 'to be added'}")
    print(f"  rules to stamp  : {len(stamps)}")
    print(f"  duplicates      : {len(duplicates)} to remove")

    by_region = {}
    for _id, base, evolved, region in stamps:
        by_region.setdefault(region, []).append(f"{base} -> {evolved}")
    for region in sorted(by_region):
        print(f"\n  {region}:")
        for line in by_region[region]:
            print(f"    {line}")

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

    # A COPY FIRST. This edits reference data in place and there is no undo; the backup
    # costs a few megabytes and one second.
    backup = f"{args.db}.pre-regions.{int(time.time())}"
    shutil.copy2(args.db, backup)
    print(f"\n  backup written  : {backup}")

    try:
        conn.execute("BEGIN")
        if not already:
            conn.execute("ALTER TABLE evolution_rules ADD COLUMN region TEXT")
        for rule_id, _base, _evolved, region in stamps:
            conn.execute("UPDATE evolution_rules SET region = ? WHERE id = ?",
                         (region, rule_id))
        for rule_id in duplicates:
            conn.execute("DELETE FROM evolution_rules WHERE id = ?", (rule_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"\n  FAILED, nothing changed: {e}")
        print(f"  the backup at {backup} is identical to the database as it stands.")
        conn.close()
        return 1

    stamped = conn.execute(
        "SELECT COUNT(*) FROM evolution_rules WHERE region IS NOT NULL "
        "AND region != ''").fetchone()[0]
    print(f"\n  done. {stamped} rule(s) now carry a region.")
    print("  The bot picks this up on its next evolution check — no restart needed.")
    conn.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
