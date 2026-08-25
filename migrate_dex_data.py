"""
Load the three things a Pokédex entry needs that this database has never held.

`base_pokemon_species` already carries height, weight, gender rate, capture rate, growth
rate, habitat and abilities. What it has never had is the part a dex is actually FOR:

  1. **Flavour text** - all 14,496 English entries across 35 game versions, tagged with
     which version each came from, so `!dex` can cycle them rather than pick one.
  2. **Egg groups and hatch counter** - for the breeding update, and because "how long
     does this take to hatch" is a dex question whether or not breeding exists yet.
  3. **Genus** - "Seed Pokémon", "Lizard Pokémon". One line, and the dex looks wrong
     without it.

Two tables:

    species_dex(pokedex_id, genus, generation, hatch_counter, base_happiness,
                is_baby, has_gender_differences, egg_group_1, egg_group_2)

    species_flavour(pokedex_id, version_id, version, generation, flavour)

**EGG GROUPS ARE TWO COLUMNS, NOT A JOIN TABLE.** Measured before deciding: every one of
the 1,025 species has one or two, never three, and every read wants both at once. A join
table would be a third query for a fact that fits in the row.

**FLAVOUR TEXT IS STORED PER VERSION, NOT DEDUPED.** A species averages 14 entries and
many are word-for-word repeats - a re-release reuses the text. Collapsing identical text
would lose which versions said it, and "Red, Blue and Yellow all said this" is worth
showing. `utils.dex.flavour_entries` groups them for display instead, so the storage
stays faithful and the reader stays readable.

**THE TEXT NEEDS CLEANING AND THAT IS NOT COSMETIC.** PokeAPI stores the entries with the
games' own line breaks - `\\n` mid-sentence and `\\x0c` where the text box paged - so
printed raw they arrive as ragged three-word lines. Whitespace is collapsed; nothing else
is touched, including the Generation 1-3 habit of writing POKéMON in caps.

**IT IS SAFE TO RUN WITH THE BOT UP.** Two new tables, nothing existing touched.
`utils.dex` answers None for a species it has no row for, so a bot running the new code
before this migration shows a dex without flavour text rather than crashing.

    python migrate_dex_data.py            # report only, writes nothing
    python migrate_dex_data.py --apply    # do it

Idempotent - the tables are rebuilt from the source each time, so re-running after
PokeAPI adds a game picks the new entries up.

The data comes from PokeAPI's CSV dump over the network. Pass `--csv-dir <path>` to use
local copies instead.
"""

import argparse
import csv
import io
import os
import re
import shutil
import sqlite3
import sys
import time
import urllib.request

DB = 'ecosystem.db'
BASE_URL = ('https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/')
ENGLISH = '9'
MAX_BASE_SPECIES = 1025

NEEDED = ('pokemon_species.csv', 'pokemon_species_names.csv',
          'pokemon_species_flavor_text.csv', 'pokemon_egg_groups.csv',
          'egg_group_prose.csv', 'versions.csv', 'version_names.csv',
          'version_groups.csv', 'pokemon.csv')

DEX_TABLE = 'species_dex'
FLAVOUR_TABLE = 'species_flavour'
FORMS_TABLE = 'species_forms'

DEX_SCHEMA = f"""
CREATE TABLE {DEX_TABLE} (
    pokedex_id             INTEGER PRIMARY KEY,
    genus                  TEXT,
    generation             INTEGER,
    hatch_counter          INTEGER,
    base_happiness         INTEGER,
    is_baby                INTEGER DEFAULT 0,
    has_gender_differences INTEGER DEFAULT 0,
    egg_group_1            TEXT,
    egg_group_2            TEXT
)
"""

# WHICH FORMS BELONG TO WHICH SPECIES, which nothing in this database has ever
# recorded. `base_pokemon_species` holds all 1,344 rows flat: `deoxys-attack` sits beside
# `deoxys-normal` with nothing joining them, and `wormadam-sandy` is not even numbered
# above 10000 the way most forms are.
#
# It cannot be derived from the NAME either, and that is the trap worth naming: splitting
# on the first hyphen works for `rotom-heat` and destroys `mr-mime`, `ho-oh`, `type-null`
# and `jangmo-o`. PokeAPI's own pokemon.csv carries the mapping and agrees with every one
# of our 1,344 ids, so it is imported rather than guessed at.
FORMS_SCHEMA = f"""
CREATE TABLE {FORMS_TABLE} (
    pokedex_id      INTEGER PRIMARY KEY,
    base_pokedex_id INTEGER NOT NULL,
    is_default      INTEGER DEFAULT 0
)
"""

FLAVOUR_SCHEMA = f"""
CREATE TABLE {FLAVOUR_TABLE} (
    pokedex_id  INTEGER NOT NULL,
    version_id  INTEGER NOT NULL,
    version     TEXT NOT NULL,
    generation  INTEGER,
    flavour     TEXT NOT NULL,
    PRIMARY KEY (pokedex_id, version_id)
)
"""


def clean(text):
    """
    One paragraph, from text the games broke into a three-line box.

    `\\x0c` is a form feed and marks where the entry paged in-game; `\\n` is a line break
    inside the box; `\\u00ad` is a soft hyphen left over from justification. All three
    are layout for a screen that is not this one.
    """
    return re.sub(r'\s+', ' ', str(text or '').replace('­', '')).strip()


def load(name, csv_dir):
    if csv_dir:
        with open(os.path.join(csv_dir, name), encoding='utf-8') as handle:
            body = handle.read()
    else:
        request = urllib.request.Request(
            BASE_URL + name, headers={'User-Agent': 'KyuDex-migration/1.0'})
        body = urllib.request.urlopen(request, timeout=180).read().decode('utf-8')
    return list(csv.DictReader(io.StringIO(body)))


def build(sources, species):
    """The rows for both tables, and anything wrong with them."""
    problems = []

    version_generation = {row['id']: row['generation_id']
                          for row in sources['version_groups.csv']}
    version_group = {row['id']: row['version_group_id']
                     for row in sources['versions.csv']}
    version_name = {row['version_id']: row['name']
                    for row in sources['version_names.csv']
                    if row['local_language_id'] == ENGLISH}

    egg_label = {row['egg_group_id']: row['name']
                 for row in sources['egg_group_prose.csv']
                 if row['local_language_id'] == ENGLISH}
    eggs = {}
    for row in sources['pokemon_egg_groups.csv']:
        species_id = int(row['species_id'])
        if species_id not in species:
            continue
        eggs.setdefault(species_id, []).append(
            egg_label.get(row['egg_group_id'], row['egg_group_id']))
    too_many = {sid: groups for sid, groups in eggs.items() if len(groups) > 2}
    if too_many:
        problems.append(f"{len(too_many)} species have more than two egg groups, which "
                        f"this schema cannot hold: {sorted(too_many)[:3]}")

    genus = {int(row['pokemon_species_id']): row.get('genus')
             for row in sources['pokemon_species_names.csv']
             if row['local_language_id'] == ENGLISH}

    dex_rows = []
    for row in sources['pokemon_species.csv']:
        species_id = int(row['id'])
        if species_id not in species:
            continue
        groups = eggs.get(species_id, [])
        dex_rows.append((
            species_id,
            clean(genus.get(species_id)) or None,
            int(row['generation_id'] or 0) or None,
            int(row['hatch_counter'] or 0) or None,
            int(row['base_happiness'] or 0),
            1 if row['is_baby'] == '1' else 0,
            1 if row['has_gender_differences'] == '1' else 0,
            groups[0] if groups else None,
            groups[1] if len(groups) > 1 else None,
        ))

    missing_genus = [r[0] for r in dex_rows if not r[1]]
    if missing_genus:
        problems.append(f"{len(missing_genus)} species have no genus, e.g. "
                        f"{missing_genus[:3]}")
    missing_eggs = [r[0] for r in dex_rows if not r[7]]
    if missing_eggs:
        problems.append(f"{len(missing_eggs)} species have no egg group, e.g. "
                        f"{missing_eggs[:3]}")

    flavour_rows, seen = [], set()
    for row in sources['pokemon_species_flavor_text.csv']:
        if row['language_id'] != ENGLISH:
            continue
        species_id = int(row['species_id'])
        if species_id not in species:
            continue
        version_id = int(row['version_id'])
        key = (species_id, version_id)
        if key in seen:
            continue
        text = clean(row['flavor_text'])
        if not text:
            continue
        seen.add(key)
        group = version_group.get(str(version_id))
        flavour_rows.append((
            species_id, version_id,
            version_name.get(str(version_id), f"Version {version_id}"),
            int(version_generation.get(group) or 0) or None,
            text,
        ))

    covered = {row[0] for row in flavour_rows}
    uncovered = sorted(set(species) - covered)
    if uncovered:
        problems.append(f"{len(uncovered)} species have no English flavour text, e.g. "
                        f"{uncovered[:3]}")

    unnamed = sorted({r[2] for r in flavour_rows if r[2].startswith('Version ')})
    if unnamed:
        problems.append(f"versions with no English name: {unnamed}")

    return dex_rows, flavour_rows, problems


def build_forms(sources, every_species):
    """
    Which base species each form belongs to. `every_species` is ALL of ours, not just
    the base 1,025 - the whole point is to reach the 10xxx rows.
    """
    rows, problems = [], []
    mapping = {int(row['id']): (int(row['species_id']), row['is_default'] == '1')
               for row in sources['pokemon.csv']}

    unknown = sorted(set(every_species) - set(mapping))
    if unknown:
        problems.append(f"{len(unknown)} of our species are not in pokemon.csv, so "
                        f"their forms cannot be grouped: {unknown[:5]}")
    for pokedex_id in sorted(every_species):
        if pokedex_id not in mapping:
            continue
        base, default = mapping[pokedex_id]
        if base not in every_species:
            problems.append(f"form {pokedex_id} belongs to species {base}, which this "
                            f"database does not have")
            continue
        rows.append((pokedex_id, base, 1 if default else 0))

    # Every group needs exactly one default, or the form button has no home to return to.
    defaults = {}
    for pokedex_id, base, default in rows:
        if default:
            defaults[base] = defaults.get(base, 0) + 1
    grouped = {base for _p, base, _d in rows}
    missing = sorted(base for base in grouped if defaults.get(base, 0) != 1)
    if missing:
        problems.append(f"{len(missing)} species do not have exactly one default form: "
                        f"{missing[:5]}")
    return rows, problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default=DB, help="path to ecosystem.db")
    parser.add_argument('--apply', action='store_true',
                        help="actually write; without it this only reports")
    parser.add_argument('--csv-dir', default=None,
                        help="a directory of PokeAPI CSVs instead of the network")
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"  no database at {args.db}")
        return 1

    conn = sqlite3.connect(args.db)
    species = {row[0] for row in conn.execute(
        "SELECT pokedex_id FROM base_pokemon_species WHERE pokedex_id <= ?",
        (MAX_BASE_SPECIES,))}
    every_species = {row[0] for row in conn.execute(
        "SELECT pokedex_id FROM base_pokemon_species")}
    print(f"\n  base species in this database : {len(species)} "
          f"({len(every_species)} counting forms)")

    have = {name: conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = ?",
        (name,)).fetchone()[0] > 0
        for name in (DEX_TABLE, FLAVOUR_TABLE, FORMS_TABLE)}
    for name, present in have.items():
        rows = conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0] if present \
            else 0
        print(f"  {name:<16} : {'present' if present else 'absent'} ({rows} rows)")

    try:
        sources = {name: load(name, args.csv_dir) for name in NEEDED}
    except Exception as e:
        print(f"\n  could not read the source data: {e}")
        print("  Pass --csv-dir <path> to use local PokeAPI CSVs.")
        conn.close()
        return 1
    print(f"  source files read            : {len(sources)}")

    dex_rows, flavour_rows, problems = build(sources, species)
    form_rows, form_problems = build_forms(sources, every_species)
    problems += form_problems

    versions = {row[2] for row in flavour_rows}
    print(f"\n  dex rows      : {len(dex_rows)}")
    print(f"  flavour rows  : {len(flavour_rows)} across {len(versions)} versions")
    if flavour_rows:
        per = {}
        for row in flavour_rows:
            per[row[0]] = per.get(row[0], 0) + 1
        print(f"  entries per species: min {min(per.values())} "
              f"max {max(per.values())} mean {sum(per.values()) / len(per):.1f}")
        longest = max(flavour_rows, key=lambda r: len(r[4]))
        print(f"  longest entry : {len(longest[4])} chars")
    pairs = sum(1 for row in dex_rows if row[8])
    print(f"  species with two egg groups: {pairs}")
    grouped = len({row[1] for row in form_rows})
    print(f"  form rows     : {len(form_rows)} across {grouped} species "
          f"({len(form_rows) - grouped} are alternate forms)")

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

    backup = f"{args.db}.pre-dex.{int(time.time())}"
    shutil.copy2(args.db, backup)
    print(f"\n  backup written  : {backup}")

    try:
        conn.execute("BEGIN")
        conn.execute(f"DROP TABLE IF EXISTS {DEX_TABLE}")
        conn.execute(f"DROP TABLE IF EXISTS {FLAVOUR_TABLE}")
        conn.execute(f"DROP TABLE IF EXISTS {FORMS_TABLE}")
        conn.execute(DEX_SCHEMA)
        conn.execute(FLAVOUR_SCHEMA)
        conn.execute(FORMS_SCHEMA)
        conn.executemany(
            f"INSERT INTO {DEX_TABLE} (pokedex_id, genus, generation, hatch_counter, "
            f"base_happiness, is_baby, has_gender_differences, egg_group_1, "
            f"egg_group_2) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", dex_rows)
        conn.executemany(
            f"INSERT INTO {FLAVOUR_TABLE} "
            f"(pokedex_id, version_id, version, generation, flavour) "
            f"VALUES (?, ?, ?, ?, ?)", flavour_rows)
        # Every read is "one species, in version order", so that is the index.
        conn.executemany(
            f"INSERT INTO {FORMS_TABLE} "
            f"(pokedex_id, base_pokedex_id, is_default) VALUES (?, ?, ?)", form_rows)
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{FLAVOUR_TABLE}_species "
                     f"ON {FLAVOUR_TABLE} (pokedex_id, version_id)")
        # The form button asks "everything that shares my base", which without this is a
        # scan of all 1,344 rows on every press.
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{FORMS_TABLE}_base "
                     f"ON {FORMS_TABLE} (base_pokedex_id)")
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"\n  FAILED, nothing changed: {e}")
        print(f"  the backup at {backup} is identical to the database as it stands.")
        conn.close()
        return 1

    dex_count = conn.execute(f"SELECT COUNT(*) FROM {DEX_TABLE}").fetchone()[0]
    flavour_count = conn.execute(f"SELECT COUNT(*) FROM {FLAVOUR_TABLE}").fetchone()[0]
    form_count = conn.execute(f"SELECT COUNT(*) FROM {FORMS_TABLE}").fetchone()[0]
    print(f"\n  done. {dex_count} dex rows, {flavour_count} flavour entries, "
          f"{form_count} forms mapped.")
    print("  The bot picks this up on its next lookup — no restart needed.")
    conn.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
